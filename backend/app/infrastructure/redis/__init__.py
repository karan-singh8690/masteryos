"""Redis infrastructure package.

Provides a pluggable Redis client for:
- Job queue (RedisJobQueue)
- Rate limiting (distributed)
- Caching (shared cache)
- Pub/sub (for real-time notifications)

When Redis is unavailable, falls back to in-memory implementations.
"""

from __future__ import annotations

from typing import Any

from app.shared.config import get_settings
from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Redis Client Factory
# ============================================================


_redis_client: Any = None


async def get_redis_client() -> Any | None:
    """Get the Redis client (singleton).

    Returns None if Redis is not available (development/testing).
    In production, this returns an aioredis client.
    """
    global _redis_client  # noqa: PLW0603
    if _redis_client is not None:
        return _redis_client

    settings = get_settings()
    try:
        # Try to import aioredis/redis-py async
        import redis.asyncio as redis_async

        _redis_client = redis_async.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test the connection
        await _redis_client.ping()
        logger.info("redis_connected", url=settings.redis_url.split("@")[-1])
        return _redis_client
    except ImportError:
        logger.warning("redis_not_installed")
        return None
    except Exception as exc:
        logger.warning("redis_connection_failed", error=str(exc))
        return None


async def close_redis_client() -> None:
    """Close the Redis client (called at shutdown)."""
    global _redis_client  # noqa: PLW0603
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None


__all__ = ["get_redis_client", "close_redis_client"]
