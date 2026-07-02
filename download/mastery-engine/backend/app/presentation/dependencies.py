"""FastAPI dependency injection — wires production security services.

This module provides FastAPI dependencies that:
1. Create and provide the AsyncUnitOfWork (with a real PostgreSQL session).
2. Create and provide the EventPublisher (writes to the outbox after commit).
3. Provide the current authenticated user (from RS256 JWT).
4. Provide the production auth service (Argon2 + RS256 + session + MFA).
5. Provide the authorization service (RBAC).

NO SHA256, NO HS256, NO fake verification, NO fake sessions.
All authentication uses the production services from Task 015.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Any
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
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
from app.infrastructure.security import (
    AuthContext,
    AuthorizationService,
    JWTService,
    MFAService,
    PasswordService,
    ROLE_ADMINISTRATOR,
    ROLE_LEARNER,
    SessionService,
    TokenService,
)
from app.shared.config import get_settings
from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Unit of Work Dependency
# ============================================================


async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    """Provide a Unit of Work with a real PostgreSQL session."""
    session_factory = await get_session_factory()
    uow = AsyncUnitOfWork(session_factory=session_factory)
    yield uow


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a raw AsyncSession (for services that need direct access)."""
    session_factory = await get_session_factory()
    async with session_factory() as session:
        yield session


# ============================================================
# Event Publisher Dependency
# ============================================================


class OutboxEventPublisher:
    """Event publisher that writes events to the outbox table."""

    def __init__(self) -> None:
        self._events: list[tuple[DomainEvent, str]] = []

    async def publish(self, event: DomainEvent, originating_schema: str = "unknown") -> None:
        self._events.append((event, originating_schema))

    async def publish_many(
        self, events: list[DomainEvent], originating_schema: str = "unknown"
    ) -> None:
        for event in events:
            self._events.append((event, originating_schema))

    async def flush_to_outbox(
        self,
        session: AsyncSession,
        actor_user_id: UUID | None = None,
    ) -> None:
        for event, originating_schema in self._events:
            await OutboxEventWriter.write_events(
                session,
                [event],
                originating_schema=originating_schema,
                actor_user_id=actor_user_id,
            )
        self._events.clear()


async def get_event_publisher() -> OutboxEventPublisher:
    return OutboxEventPublisher()


# ============================================================
# Production Security Service Singletons
# ============================================================


@lru_cache
def get_password_service() -> PasswordService:
    """Provide the Argon2id password service (singleton)."""
    settings = get_settings()
    return PasswordService(
        memory_cost=settings.argon2_memory_cost,
        time_cost=settings.argon2_time_cost,
        parallelism=settings.argon2_parallelism,
    )


@lru_cache
def get_jwt_service() -> JWTService:
    """Provide the RS256 JWT service (singleton)."""
    settings = get_settings()
    return JWTService(
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


@lru_cache
def get_mfa_service() -> MFAService:
    """Provide the TOTP MFA service (singleton)."""
    return MFAService()


@lru_cache
def get_session_service() -> SessionService:
    """Provide the session management service (singleton)."""
    return SessionService()


@lru_cache
def get_token_service() -> TokenService:
    """Provide the secure token service (singleton)."""
    return TokenService()


# ============================================================
# Production Auth Service Dependency
# ============================================================


def get_auth_service() -> "ProductionAuthService":
    """Provide the production authentication service.

    Lazily imports to avoid circular imports.
    """
    from app.application.identity.auth_service import ProductionAuthService

    return ProductionAuthService(
        password_service=get_password_service(),
        jwt_service=get_jwt_service(),
        mfa_service=get_mfa_service(),
    )


# ============================================================
# Authentication Dependencies (RS256 JWT)
# ============================================================


async def get_current_user_id(
    authorization: str | None = Header(None),
) -> UUID:
    """FastAPI dependency that extracts the user ID from the RS256 JWT.

    Uses the production JWTService — NO HS256, NO simplified tokens.

    Raises HTTPException(401) if no valid token is present.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Missing or invalid Authorization header"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1]
    jwt_service = get_jwt_service()
    claims = jwt_service.verify_access_token(token)

    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return claims.user_id


async def get_optional_user_id(
    authorization: str | None = Header(None),
) -> UUID | None:
    """FastAPI dependency that optionally extracts the user ID.

    Returns None if no token is present (for public endpoints).
    """
    if authorization is None or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1]
    jwt_service = get_jwt_service()
    claims = jwt_service.verify_access_token(token)
    return claims.user_id if claims else None


async def get_current_user_claims(
    authorization: str | None = Header(None),
) -> "TokenClaims":
    """FastAPI dependency that extracts full JWT claims.

    Returns the TokenClaims dataclass with user_id, roles, token_version, etc.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Missing or invalid Authorization header"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1]
    jwt_service = get_jwt_service()
    claims = jwt_service.verify_access_token(token)

    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return claims


async def get_current_auth_context(
    authorization: str | None = Header(None),
) -> AuthContext:
    """FastAPI dependency that provides the authorization context.

    The AuthContext is built from JWT claims and carries the user's
    roles + permissions for fine-grained RBAC.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Missing or invalid Authorization header"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1]
    jwt_service = get_jwt_service()
    claims = jwt_service.verify_access_token(token)

    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthContext.from_jwt_claims(claims.user_id, claims.roles)


# Alias for shorter name
get_auth_context = get_current_auth_context


async def get_authorization_service(
    ctx: AuthContext = Depends(get_current_auth_context),
) -> AuthorizationService:
    """FastAPI dependency that provides the authorization service."""
    return AuthorizationService(ctx)


def require_permission(permission: str):
    """Dependency factory: require a specific permission.

    Usage:
        @router.get("/admin/users", dependencies=[Depends(require_permission(PERM_USER_READ_ALL))])
        async def list_users(...): ...
    """
    from app.infrastructure.security.authorization import AuthorizationDenied

    async def _checker(
        auth: AuthorizationService = Depends(get_authorization_service),
    ) -> AuthorizationService:
        auth.require_permission(permission)
        return auth

    return _checker


def require_role(role: str):
    """Dependency factory: require a specific role."""
    async def _checker(
        auth: AuthorizationService = Depends(get_authorization_service),
    ) -> AuthorizationService:
        auth.require_role(role)
        return auth

    return _checker


def require_any_role(*roles: str):
    """Dependency factory: require any of the specified roles."""
    async def _checker(
        auth: AuthorizationService = Depends(get_authorization_service),
    ) -> AuthorizationService:
        auth.require_any_role(*roles)
        return auth

    return _checker


# ============================================================
# Request Context (IP, User-Agent)
# ============================================================


def get_request_ip(request: Request) -> str | None:
    """Extract the client IP, honoring X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Use the first IP in the chain
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_request_user_agent(request: Request) -> str | None:
    """Extract the User-Agent header."""
    return request.headers.get("User-Agent")


# ============================================================
# Idempotency Key Dependency
# ============================================================


async def get_idempotency_key(
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> str | None:
    """Extract the Idempotency-Key header if present."""
    return idempotency_key


# ============================================================
# Backward-compat exports
# ============================================================

# These are kept for any code that still references them, but they
# delegate to the production services.

def create_access_token(user_id: UUID, roles: list[str] | None = None) -> str:
    """Create a JWT access token using the production RS256 service.

    Kept for backward-compatibility with code that issues tokens directly.
    New code should use ProductionAuthService.issue_tokens_for_user() instead.
    """
    jwt_service = get_jwt_service()
    return jwt_service.issue_access_token(
        user_id=user_id, roles=roles or [ROLE_LEARNER], token_version=1
    )


# Re-export TokenClaims for type hints
from app.infrastructure.security.jwt_service import TokenClaims  # noqa: E402

__all__ = [
    # UoW
    "get_uow",
    "get_db_session",
    # Event publisher
    "OutboxEventPublisher",
    "get_event_publisher",
    # Security services
    "get_password_service",
    "get_jwt_service",
    "get_mfa_service",
    "get_session_service",
    "get_token_service",
    "get_auth_service",
    # Authentication
    "get_current_user_id",
    "get_optional_user_id",
    "get_current_user_claims",
    "get_current_auth_context",
    "get_authorization_service",
    "require_permission",
    "require_role",
    "require_any_role",
    # Request context
    "get_request_ip",
    "get_request_user_agent",
    # Idempotency
    "get_idempotency_key",
    # Backward-compat
    "create_access_token",
    # Types
    "TokenClaims",
]
