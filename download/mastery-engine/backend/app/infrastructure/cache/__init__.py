"""Cache abstractions for Redis and local caching.

The application layer depends on the Cache interface, not on Redis directly.
This allows swapping cache implementations without affecting the application.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Cache(ABC):
    """Abstract cache interface."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get a value from the cache. Returns None if not found."""
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Set a value in the cache with an optional TTL."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value from the cache."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        ...

    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter in the cache. Returns the new value."""
        ...

    @abstractmethod
    async def expire(self, key: str, ttl_seconds: int) -> None:
        """Set a TTL on an existing key."""
        ...


class RedisCache(Cache):
    """Redis-backed cache implementation.

    Uses redis-py's async client. The connection is configured from settings.
    """

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    async def get(self, key: str) -> Any | None:
        import json
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        import json
        serialized = json.dumps(value, default=str)
        if ttl_seconds:
            await self._redis.setex(key, ttl_seconds, serialized)
        else:
            await self._redis.set(key, serialized)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._redis.exists(key))

    async def increment(self, key: str, amount: int = 1) -> int:
        return await self._redis.incrby(key, amount)

    async def expire(self, key: str, ttl_seconds: int) -> None:
        await self._redis.expire(key, ttl_seconds)


class LocalCache(Cache):
    """In-memory cache for testing or single-instance development.

    Not suitable for production multi-instance deployments.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float | None]] = {}
        import time
        self._time = time.time

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and self._time() > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        expires_at = self._time() + ttl_seconds if ttl_seconds else None
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._store

    async def increment(self, key: str, amount: int = 1) -> int:
        current = (await self.get(key)) or 0
        new_value = current + amount
        await self.set(key, new_value)
        return new_value

    async def expire(self, key: str, ttl_seconds: int) -> None:
        if key in self._store:
            value, _ = self._store[key]
            self._store[key] = (value, self._time() + ttl_seconds)
