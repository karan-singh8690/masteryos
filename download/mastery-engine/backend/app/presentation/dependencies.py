"""FastAPI dependency injection — wires infrastructure to application layer.

This module provides FastAPI dependencies that:
1. Create and provide the AsyncUnitOfWork (with a real PostgreSQL session).
2. Create and provide the EventPublisher (writes to the outbox after commit).
3. Provide the current authenticated user (from JWT).
4. Provide the active algorithm version (for mastery computations).

Usage in routes:
    @router.post("/users")
    async def register(
        request: RegisterRequest,
        uow: UnitOfWork = Depends(get_uow),
        publisher: EventPublisher = Depends(get_event_publisher),
    ):
        handler = RegisterUserHandler(uow, publisher)
        result = await handler.handle(command)
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.shared import (
    AuthorizationDenied,
    CurrentUserProvider,
    EventPublisher,
    UnitOfWork,
)
from app.domain.shared.kernel import DomainEvent
from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.database.unit_of_work import AsyncUnitOfWork, OutboxEventWriter
from app.shared.config import get_settings
from app.shared.logging import get_logger

import jwt
import uuid as uuid_mod

logger = get_logger(__name__)


# ============================================================
# Unit of Work Dependency
# ============================================================


async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    """Provide a Unit of Work with a real PostgreSQL session.

    Yields an AsyncUnitOfWork that manages a single transaction.
    The route handler uses it within `async with uow:` blocks.
    """
    session_factory = await get_session_factory()
    uow = AsyncUnitOfWork(session_factory=session_factory)
    yield uow


# ============================================================
# Event Publisher Dependency
# ============================================================


class OutboxEventPublisher:
    """Event publisher that writes events to the outbox table.

    This implementation does NOT publish events immediately — it collects
    them and writes them to the outbox when the UoW commits. The outbox
    dispatcher (background worker) delivers them to subscribers.

    Usage:
        publisher = OutboxEventPublisher()
        # ... command handler runs, calls publisher.publish_many(events) ...
        # ... but events are only queued in memory ...
        # After commit:
        await publisher.flush_to_outbox(uow._session, originating_schema="identity")
    """

    def __init__(self) -> None:
        self._events: list[tuple[DomainEvent, str]] = []

    async def publish(self, event: DomainEvent, originating_schema: str = "unknown") -> None:
        """Queue an event for publishing."""
        self._events.append((event, originating_schema))

    async def publish_many(
        self, events: list[DomainEvent], originating_schema: str = "unknown"
    ) -> None:
        """Queue multiple events for publishing."""
        for event in events:
            self._events.append((event, originating_schema))

    async def flush_to_outbox(
        self,
        session: AsyncSession,
        actor_user_id: UUID | None = None,
    ) -> None:
        """Write all queued events to the outbox table.

        Must be called within the UoW's transaction, before commit.
        """
        for event, originating_schema in self._events:
            await OutboxEventWriter.write_events(
                session,
                [event],
                originating_schema=originating_schema,
                actor_user_id=actor_user_id,
            )
        self._events.clear()


async def get_event_publisher() -> OutboxEventPublisher:
    """Provide an event publisher that writes to the outbox."""
    return OutboxEventPublisher()


# ============================================================
# Authentication Dependency
# ============================================================


class JWTCurrentUserProvider:
    """Extracts the current user from a JWT access token.

    In development mode, email verification may be bypassed via a feature flag.
    """

    def __init__(self, token: str | None) -> None:
        self._token = token

    async def get_current_user_id(self) -> UUID | None:
        if self._token is None:
            return None

        try:
            settings = get_settings()
            payload = jwt.decode(
                self._token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                audience="mastery-engine-api",
            )
            user_id_str = payload.get("sub")
            if user_id_str is None:
                return None
            return UUID(user_id_str)
        except jwt.PyJWTError:
            return None

    async def get_current_user_roles(self) -> list[str]:
        if self._token is None:
            return []
        try:
            settings = get_settings()
            payload = jwt.decode(
                self._token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                audience="mastery-engine-api",
            )
            return payload.get("scope", "").split(",")
        except jwt.PyJWTError:
            return []


def create_access_token(user_id: UUID, roles: list[str] | None = None) -> str:
    """Create a JWT access token for a user.

    Used by the login/register endpoints to issue tokens.
    """
    settings = get_settings()
    import time
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iss": "https://api.masteryengine.com",
        "aud": "mastery-engine-api",
        "iat": now,
        "exp": now + settings.jwt_access_token_expire_minutes * 60,
        "jti": str(uuid_mod.uuid4()),
        "scope": ",".join(roles or ["learner"]),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user_id(
    authorization: str | None = Header(None),
) -> UUID:
    """FastAPI dependency that extracts the user ID from the Authorization header.

    Raises HTTPException(401) if no valid token is present.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Missing or invalid Authorization header"},
        )

    token = authorization.split(" ", 1)[1]
    provider = JWTCurrentUserProvider(token)
    user_id = await provider.get_current_user_id()

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Invalid or expired token"},
        )

    return user_id


async def get_optional_user_id(
    authorization: str | None = Header(None),
) -> UUID | None:
    """FastAPI dependency that optionally extracts the user ID.

    Returns None if no token is present (for public endpoints).
    """
    if authorization is None or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1]
    provider = JWTCurrentUserProvider(token)
    return await provider.get_current_user_id()


# ============================================================
# Idempotency Key Dependency
# ============================================================


async def get_idempotency_key(
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> str | None:
    """Extract the Idempotency-Key header if present."""
    return idempotency_key
