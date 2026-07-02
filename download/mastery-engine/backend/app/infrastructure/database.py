"""Database infrastructure — async SQLAlchemy session management.

This module provides:
- Async engine creation from settings
- Async session factory
- FastAPI dependency for injecting database sessions
- Database lifecycle management (init/shutdown)

No models are defined here yet (per Task 007: no business logic).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.shared.config import get_settings
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Module-level engine and session factory (lazily initialized)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def get_engine() -> AsyncEngine:
    """Return the async engine, creating it if necessary."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.database_echo,
        )
        logger.info("database_engine_created", url=settings.database_url.split("@")[-1])
    return _engine


async def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory, creating it if necessary."""
    global _session_factory  # noqa: PLW0603
    if _session_factory is None:
        engine = await get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Usage:
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
    """Initialize database connections. Called at application startup."""
    await get_engine()
    logger.info("database_initialized")


async def close_database() -> None:
    """Close database connections. Called at application shutdown."""
    global _engine, _session_factory  # noqa: PLW0603
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("database_closed")
