"""Pytest configuration for production authentication integration tests.

Sets up:
- An in-memory SQLite database (via aiosqlite) for fast tests
- Test fixtures for the FastAPI TestClient
- Production security services (Argon2id with low cost for speed)
- Helper functions for test flows
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Ensure backend/ is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Set test environment variables BEFORE importing app modules
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ARGON2_MEMORY_COST", "1024")  # Fast for tests
os.environ.setdefault("ARGON2_TIME_COST", "1")
os.environ.setdefault("ARGON2_PARALLELISM", "1")

# Now import app modules
from app.infrastructure.database.orm.base import Base  # noqa: E402
from app.infrastructure.database.orm.identity import (  # noqa: E402
    SessionModel,
    UserCredentialModel,
    UserModel,
    UserProfileModel,
)
from app.infrastructure.database.orm.auth import (  # noqa: E402
    AuthAuditLogModel,
    MfaRecoveryCodeModel,
    MfaSecretModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    SecurityIncidentModel,
    VerificationTokenModel,
)
# Import everything to ensure all tables are registered with Base.metadata
from app.infrastructure.database.orm import core as _core  # noqa: E402, F401
from app.infrastructure.database.orm import content as _content  # noqa: E402, F401


# ============================================================
# Database Fixtures
# ============================================================


@pytest_asyncio.fixture
async def test_engine():
    """Create an in-memory SQLite engine for tests.

    SQLite doesn't support schemas or PG-specific types (UUID, INET, JSONB).
    We:
    1. Strip the 'schema' attribute from all tables.
    2. Override PG-specific types (UUID, INET, JSONB) to use SQLite-friendly
       types (String, String, JSON).
    """
    from sqlalchemy.dialects.postgresql import UUID as PGUUID, INET, JSONB
    from sqlalchemy import String, JSON, types as sa_types

    # Override PG types to use SQLite-friendly equivalents.
    # This works by replacing the dialect_impl method on the PG types
    # to return String/JSON when compiled for SQLite.
    class _SQLiteCompat(sa_types.TypeDecorator):
        """A type that uses String/JSON for SQLite and the original PG type for PG."""
        impl = String
        cache_ok = True

    # Patch the PG types' __visit_name__ for the SQLite dialect
    # The simplest way: register a custom compiler for INET/JSONB/UUID
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
    from sqlalchemy import types as t

    # Override the type compiler to handle PG types
    def _visit_INET(self, type_, **kw):
        return "VARCHAR(45)"  # IPv6 max length
    def _visit_JSONB(self, type_, **kw):
        return "JSON"
    def _visit_UUID(self, type_, **kw):
        return "VARCHAR(36)"

    SQLiteTypeCompiler.visit_INET = _visit_INET
    SQLiteTypeCompiler.visit_JSONB = _visit_JSONB
    SQLiteTypeCompiler.visit_UUID = _visit_UUID

    # Strip schemas from all tables in the metadata (idempotent)
    for table in list(Base.metadata.tables.values()):
        table.schema = None

    # Use StaticPool so the in-memory database is shared across connections
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            # Fall back to one-by-one creation (some CHECK constraints may fail)
            import logging
            logging.warning(f"create_all failed: {e}; trying one-by-one")
            from sqlalchemy.schema import CreateTable
            for table in Base.metadata.sorted_tables:
                try:
                    await conn.execute(CreateTable(table, if_not_exists=True))
                except Exception as te:
                    logging.warning(f"Failed to create {table.name}: {te}")

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine):
    """Create a session factory bound to the test engine."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def test_session(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with test_session_factory() as session:
        yield session


# ============================================================
# App + Client Fixtures
# ============================================================


@pytest_asyncio.fixture
async def test_client(test_session_factory) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX AsyncClient bound to the FastAPI app.

    Overrides the UoW dependency to use the test database.
    """
    from app.main import app
    from app.presentation.dependencies import get_uow
    from app.infrastructure.database.unit_of_work import AsyncUnitOfWork

    async def override_get_uow():
        uow = AsyncUnitOfWork(session_factory=test_session_factory)
        yield uow

    app.dependency_overrides[get_uow] = override_get_uow

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ============================================================
# Auth Service Fixture
# ============================================================


@pytest.fixture
def auth_service():
    """Provide a ProductionAuthService with low-cost Argon2id for tests."""
    from app.application.identity.auth_service import ProductionAuthService
    from app.infrastructure.security import (
        JWTService,
        MFAService,
        PasswordService,
    )

    return ProductionAuthService(
        password_service=PasswordService(memory_cost=1024, time_cost=1, parallelism=1),
        jwt_service=JWTService(),
        mfa_service=MFAService(),
    )


# ============================================================
# Helper Functions
# ============================================================


async def create_test_user(
    session: AsyncSession,
    auth_service,
    email: str = "test@example.com",
    password: str = "SecurePassword123!",
    display_name: str = "Test User",
    verified: bool = True,
) -> tuple[Any, str]:
    """Create a test user and return (user_model, verification_token).

    If verified=True, also mark the email as verified.
    """
    user_model, verification_token, _ = await auth_service.register(
        session=session,
        email=email,
        password=password,
        display_name=display_name,
    )

    if verified:
        from sqlalchemy import update
        await session.execute(
            update(UserModel)
            .where(UserModel.id == user_model.id)
            .values(
                email_verified_at=datetime.now(timezone.utc),
                status="active",
            )
        )
        await session.flush()

    await session.commit()
    return user_model, verification_token


async def get_auth_headers(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    """Login and return the Authorization headers."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# Pytest Configuration
# ============================================================


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "asyncio: mark test as asyncio")


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
