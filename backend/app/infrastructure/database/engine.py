"""Database engine and session factory.

Provides async SQLAlchemy 2.x engine creation, session management,
connection pooling, retry strategy, and health checks.

This module is the single point of contact between the application
and PostgreSQL. All other infrastructure modules use the session
factory provided here.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.shared.config import get_settings
from app.shared.logging import get_logger

# Import Base + all ORM models so create_all() can detect them
from app.infrastructure.database.orm.base import Base  # noqa: E402
# Import all ORM modules to populate Base.metadata
from app.infrastructure.database.orm import (  # noqa: E402, F401
    identity,
    auth,
    background,
    beta,
    beta_ops,
    core,
    content,
    billing,
)

logger = get_logger(__name__)

# Module-level engine and session factory
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def get_engine() -> AsyncEngine:
    """Return the async engine, creating it if necessary.

    The engine is configured with:
    - Connection pooling (pool_size + max_overflow from settings)
    - Statement timeout (30s) to prevent runaway queries
    - Idle transaction timeout (60s) to prevent connection leaks
    - SQL echo in development
    - Prepared statement cache for asyncpg
    """
    global _engine  # noqa: PLW0603
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,  # Check connection health before checkout
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=settings.database_echo,
            echo_pool=settings.is_development,
            connect_args={
                "server_settings": {
                    "statement_timeout": "30000",  # 30 seconds
                    "idle_in_transaction_session_timeout": "60000",  # 60 seconds
                    "application_name": f"{settings.app_name}_{settings.app_env.value}",
                },
                "prepared_statement_cache_size": 100,
            },
        )

        # Set up SQL timing logging
        @event.listens_for(_engine.sync_engine, "before_cursor_execute")
        def _before_cursor_execute(
            conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool
        ) -> None:
            context._query_start_time = asyncio.get_event_loop().time()  # type: ignore[attr-defined]

        @event.listens_for(_engine.sync_engine, "after_cursor_execute")
        def _after_cursor_execute(
            conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool
        ) -> None:
            duration = asyncio.get_event_loop().time() - context._query_start_time  # type: ignore[attr-defined]
            if duration > 0.1:  # Log queries slower than 100ms
                logger.warning(
                    "slow_query",
                    duration_ms=round(duration * 1000, 2),
                    statement=statement[:200],
                )
            else:
                logger.debug(
                    "query_executed",
                    duration_ms=round(duration * 1000, 2),
                )

        logger.info(
            "database_engine_created",
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
        )

    return _engine


async def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory, creating it if necessary."""
    global _session_factory  # noqa: PLW0603
    if _session_factory is None:
        engine = await get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Critical: don't expire after commit (we access after)
            autoflush=False,  # Explicit flush for control
            autocommit=False,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Usage in routes:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    factory = await get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_database() -> None:
    """Initialize database connections. Called at application startup.

    Also creates any missing schemas + tables as a safety net.
    """
    global _engine, _session_factory
    _engine = await get_engine()
    _session_factory = await get_session_factory()

    # Safety net: create schemas + any tables that don't exist yet.
    try:
        async with _engine.begin() as conn:
            # Create all schemas first
            from sqlalchemy import text
            schemas = [
                "identity", "content", "learning", "assessment", "mastery",
                "scheduling", "administration", "analytics", "billing",
                "infrastructure",
            ]
            for schema in schemas:
                await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {schema}'))
            # Then create all tables from ORM models
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database_tables_verified")
    except Exception as exc:
        logger.warning("database_table_creation_skipped", error=str(exc))

    logger.info("database_initialized")


async def close_database() -> None:
    """Close database connections. Called at application shutdown."""
    global _engine, _session_factory  # noqa: PLW0603
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("database_closed")


async def check_database_health(session: AsyncSession) -> bool:
    """Check if the database is healthy (used by /health/ready)."""
    try:
        result = await session.execute(text("SELECT 1"))
        return result.scalar() == 1
    except Exception as exc:
        logger.warning("database_health_check_failed", error=str(exc))
        return False


async def check_database_health_with_retry(
    session: AsyncSession, max_retries: int = 3, delay: float = 0.5
) -> bool:
    """Check database health with retry on failure."""
    for attempt in range(max_retries):
        if await check_database_health(session):
            return True
        if attempt < max_retries - 1:
            await asyncio.sleep(delay * (attempt + 1))
    return False
