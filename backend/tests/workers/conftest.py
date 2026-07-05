"""Pytest configuration for background processing tests.

Sets up:
- In-memory SQLite database (with schema stripping for SQLite compat)
- Test fixtures for the WorkerHost, OutboxDispatcher, NotificationService, etc.
- Helper functions for creating test events + notifications
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncGenerator
from datetime import datetime, timezone as tz_utc
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Ensure backend/ is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Set test environment variables
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ARGON2_MEMORY_COST", "1024")
os.environ.setdefault("ARGON2_TIME_COST", "1")
os.environ.setdefault("ARGON2_PARALLELISM", "1")

# Import all ORM models to ensure they're registered with Base.metadata
from app.infrastructure.database.orm.base import Base  # noqa: E402
from app.infrastructure.database.orm import core as _core  # noqa: E402, F401
from app.infrastructure.database.orm import content as _content  # noqa: E402, F401
from app.infrastructure.database.orm import auth as _auth  # noqa: E402, F401
from app.infrastructure.database.orm import background as _bg  # noqa: E402, F401


# ============================================================
# Database Fixtures
# ============================================================


@pytest_asyncio.fixture
async def test_engine():
    """Create an in-memory SQLite engine for tests."""
    # Strip schemas + patch PG types for SQLite
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    def _visit_INET(self, type_, **kw):
        return "VARCHAR(45)"

    def _visit_JSONB(self, type_, **kw):
        return "JSON"

    def _visit_UUID(self, type_, **kw):
        return "VARCHAR(36)"

    SQLiteTypeCompiler.visit_INET = _visit_INET
    SQLiteTypeCompiler.visit_JSONB = _visit_JSONB
    SQLiteTypeCompiler.visit_UUID = _visit_UUID

    for table in list(Base.metadata.tables.values()):
        table.schema = None

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
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
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def test_session(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        yield session


# ============================================================
# Service Fixtures
# ============================================================


@pytest.fixture
def email_service():
    """Provide an EmailService with an in-memory SMTP client."""
    from app.infrastructure.email.service import EmailService, InMemorySmtpClient
    return EmailService(smtp_client=InMemorySmtpClient())


@pytest.fixture
def in_memory_queue():
    """Provide an in-memory job queue."""
    from app.infrastructure.queue.job_queue import InMemoryJobQueue
    return InMemoryJobQueue()


@pytest.fixture
def retry_engine():
    """Provide a retry engine with fast schedule for tests."""
    from app.workers.retry_engine import RetryEngine
    from datetime import timedelta
    return RetryEngine(
        schedule=[
            timedelta(seconds=0.01),
            timedelta(seconds=0.05),
            timedelta(seconds=0.1),
        ],
        jitter=False,
    )


# ============================================================
# Helper Functions
# ============================================================


async def create_test_outbox_event(
    session: AsyncSession,
    event_type: str = "TestEvent",
    payload: dict[str, Any] | None = None,
    status: str = "pending",
    aggregate_id: UUID | None = None,
) -> Any:
    """Create a test outbox event."""
    from app.infrastructure.database.orm.core import OutboxEventModel

    event = OutboxEventModel(
        id=uuid4(),
        event_type=event_type,
        aggregate_id=aggregate_id or uuid4(),
        aggregate_type="TestAggregate",
        actor_user_id=None,
        payload=payload or {"test": True},
        payload_schema_version="1",
        originating_schema="test",
        status=status,
        dispatch_attempt_count=0,
    )
    session.add(event)
    await session.flush()
    return event


async def create_test_user(
    session: AsyncSession,
    email: str = "test@example.com",
    display_name: str = "Test User",
    user_id: UUID | None = None,
) -> UUID:
    """Create a test user. Returns the user_id."""
    from app.infrastructure.database.orm.identity import (
        UserModel,
        UserProfileModel,
        UserCredentialModel,
    )
    import hashlib
    import secrets

    user_id = user_id or uuid4()
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}password".encode()).hexdigest()

    session.add(UserModel(
        id=user_id,
        email=email,
        email_verified_at=datetime.now(tz_utc.utc),
        status="active",
        mfa_enabled=False,
    ))
    session.add(UserProfileModel(
        user_id=user_id,
        display_name=display_name,
    ))
    session.add(UserCredentialModel(
        id=uuid4(),
        user_id=user_id,
        credential_type="password",
        password_hash=f"argon2id${salt}${hashed}",
    ))
    await session.flush()
    return user_id


# ============================================================
# Pytest Configuration
# ============================================================


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as asyncio")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
