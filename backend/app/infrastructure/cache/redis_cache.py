"""Redis caching layer with intelligent cache invalidation.

Features:
- Query result caching (with TTL per cache type)
- Session caching
- Rate limit state
- Feature flag caching
- Dashboard data caching
- Cache invalidation patterns (tag-based, pattern-based)
- Cache-aside pattern with async support
- Cache warming
- Cache statistics + hit rate tracking
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone as tz_utc
from typing import Any, TypeVar
from uuid import UUID

from app.shared.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


# ============================================================
# Cache Configuration
# ============================================================


@dataclass(frozen=True)
class CachePolicy:
    """Cache policy for a specific data type."""
    name: str
    ttl_seconds: int
    invalidation_tags: list[str] = field(default_factory=list)
    compress: bool = False
    max_entries: int = 10000  # Per cache type


# Cache policies by data type
CACHE_POLICIES: dict[str, CachePolicy] = {
    # Dashboard data — short TTL (30s) for near-real-time
    "dashboard": CachePolicy(
        name="dashboard",
        ttl_seconds=30,
        invalidation_tags=["user:{user_id}", "dashboard"],
    ),
    # Mastery scores — medium TTL (5min), invalidated on new attempt
    "mastery": CachePolicy(
        name="mastery",
        ttl_seconds=300,
        invalidation_tags=["user:{user_id}", "enrollment:{enrollment_id}", "mastery"],
    ),
    # Adaptive queue — very short TTL (10s) for fresh data
    "adaptive_queue": CachePolicy(
        name="adaptive_queue",
        ttl_seconds=10,
        invalidation_tags=["session:{session_id}", "queue"],
    ),
    # Question instance — cached for session duration
    "question": CachePolicy(
        name="question",
        ttl_seconds=600,
        invalidation_tags=["question:{question_id}", "question"],
    ),
    # Subject list — long TTL (1h), invalidated on content changes
    "subjects": CachePolicy(
        name="subjects",
        ttl_seconds=3600,
        invalidation_tags=["subjects", "content"],
    ),
    # Concept list — long TTL (1h)
    "concepts": CachePolicy(
        name="concepts",
        ttl_seconds=3600,
        invalidation_tags=["concepts:{subject_id}", "content"],
    ),
    # Templates — long TTL (1h)
    "templates": CachePolicy(
        name="templates",
        ttl_seconds=3600,
        invalidation_tags=["templates:{subject_id}", "content"],
    ),
    # User profile — medium TTL (5min)
    "user_profile": CachePolicy(
        name="user_profile",
        ttl_seconds=300,
        invalidation_tags=["user:{user_id}", "profile"],
    ),
    # Security dashboard — medium TTL (5min)
    "security_dashboard": CachePolicy(
        name="security_dashboard",
        ttl_seconds=300,
        invalidation_tags=["user:{user_id}", "security"],
    ),
    # Notifications — short TTL (30s)
    "notifications": CachePolicy(
        name="notifications",
        ttl_seconds=30,
        invalidation_tags=["user:{user_id}", "notifications"],
    ),
    # Admin metrics — short TTL (15s)
    "admin_metrics": CachePolicy(
        name="admin_metrics",
        ttl_seconds=15,
        invalidation_tags=["admin", "metrics"],
    ),
    # Feature flags — medium TTL (2min)
    "feature_flags": CachePolicy(
        name="feature_flags",
        ttl_seconds=120,
        invalidation_tags=["feature_flags"],
    ),
    # AI responses — long TTL (24h) since they're expensive
    "ai_response": CachePolicy(
        name="ai_response",
        ttl_seconds=86400,
        invalidation_tags=["ai:{request_hash}", "ai"],
        compress=True,
    ),
}


# ============================================================
# Cache Statistics
# ============================================================


@dataclass
class CacheStats:
    """Cache hit/miss statistics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_latency_ms: float = 0
    _count: int = 0  # For avg calculation

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0

    @property
    def avg_latency_ms(self) -> float:
        return (self.total_latency_ms / self._count) if self._count > 0 else 0

    def record_hit(self, latency_ms: float) -> None:
        self.hits += 1
        self.total_latency_ms += latency_ms
        self._count += 1

    def record_miss(self, latency_ms: float) -> None:
        self.misses += 1
        self.total_latency_ms += latency_ms
        self._count += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "hit_rate": round(self.hit_rate, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


# ============================================================
# Cache Key Builder
# ============================================================


class CacheKeyBuilder:
    """Builds consistent cache keys."""

    @staticmethod
    def build(cache_type: str, **identifiers: Any) -> str:
        """Build a cache key from type + identifiers."""
        parts = [cache_type]
        for key in sorted(identifiers.keys()):
            value = identifiers[key]
            if isinstance(value, (list, dict)):
                value = hashlib.sha256(
                    json.dumps(value, sort_keys=True, default=str).encode()
                ).hexdigest()[:16]
            parts.append(f"{key}:{value}")
        return ":".join(parts)

    @staticmethod
    def build_tag(tag_template: str, **identifiers: Any) -> str:
        """Build a cache invalidation tag."""
        try:
            return tag_template.format(**identifiers)
        except KeyError:
            return tag_template

    @staticmethod
    def build_pattern(cache_type: str, **identifiers: Any) -> str:
        """Build a pattern for bulk invalidation."""
        parts = [cache_type]
        for key in sorted(identifiers.keys()):
            parts.append(f"{key}:{identifiers[key]}")
        # Add wildcard for remaining keys
        parts.append("*")
        return ":".join(parts)


# ============================================================
# Redis Cache (Production)
# ============================================================


class RedisCache:
    """Production Redis cache with tag-based invalidation.

    Uses Redis SET + EXPIRE for TTL-based caching.
    Uses Redis SETS for tag-based invalidation (each tag maintains
    a set of keys that should be invalidated when the tag is triggered).
    """

    def __init__(self, redis_client: Any = None) -> None:
        self._redis = redis_client
        self._stats: dict[str, CacheStats] = {}  # cache_type → stats
        self._local_fallback: dict[str, tuple[Any, float]] = {}  # Fallback when Redis is down

    async def get(self, cache_type: str, key: str) -> Any | None:
        """Get a value from cache."""
        stats = self._get_stats(cache_type)
        start = time.time()

        try:
            if self._redis:
                full_key = f"mastery:{cache_type}:{key}"
                data = await self._redis.get(full_key)
                if data is not None:
                    latency = (time.time() - start) * 1000
                    stats.record_hit(latency)
                    return json.loads(data) if isinstance(data, str) else data
                latency = (time.time() - start) * 1000
                stats.record_miss(latency)
                return None
            else:
                # Fallback to local cache
                if key in self._local_fallback:
                    value, expires_at = self._local_fallback[key]
                    if time.time() < expires_at:
                        latency = (time.time() - start) * 1000
                        stats.record_hit(latency)
                        return value
                    del self._local_fallback[key]
                latency = (time.time() - start) * 1000
                stats.record_miss(latency)
                return None
        except Exception as exc:
            stats.errors += 1
            logger.warning("cache_get_error", cache_type=cache_type, error=str(exc))
            return None

    async def set(
        self,
        cache_type: str,
        key: str,
        value: Any,
        ttl: int | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Set a value in cache with TTL and invalidation tags."""
        stats = self._get_stats(cache_type)
        policy = CACHE_POLICIES.get(cache_type)
        actual_ttl = ttl or (policy.ttl_seconds if policy else 300)

        try:
            if self._redis:
                full_key = f"mastery:{cache_type}:{key}"
                data = json.dumps(value, default=str) if not isinstance(value, str) else value
                await self._redis.setex(full_key, actual_ttl, data)

                # Register key with invalidation tags
                if tags:
                    for tag in tags:
                        tag_key = f"mastery:tag:{tag}"
                        await self._redis.sadd(tag_key, full_key)
                        await self._redis.expire(tag_key, actual_ttl + 60)  # Tags live slightly longer
            else:
                self._local_fallback[key] = (value, time.time() + actual_ttl)

            stats.sets += 1
        except Exception as exc:
            stats.errors += 1
            logger.warning("cache_set_error", cache_type=cache_type, error=str(exc))

    async def delete(self, cache_type: str, key: str) -> None:
        """Delete a specific key."""
        stats = self._get_stats(cache_type)
        try:
            if self._redis:
                full_key = f"mastery:{cache_type}:{key}"
                await self._redis.delete(full_key)
            else:
                self._local_fallback.pop(key, None)
            stats.deletes += 1
        except Exception as exc:
            stats.errors += 1
            logger.warning("cache_delete_error", cache_type=cache_type, error=str(exc))

    async def invalidate_tag(self, tag: str) -> int:
        """Invalidate all keys associated with a tag.

        Returns the number of keys invalidated.
        """
        count = 0
        try:
            if self._redis:
                tag_key = f"mastery:tag:{tag}"
                keys = await self._redis.smembers(tag_key)
                if keys:
                    for key in keys:
                        if isinstance(key, bytes):
                            key = key.decode()
                        await self._redis.delete(key)
                        count += 1
                    await self._redis.delete(tag_key)
                    logger.info("cache_tag_invalidated", tag=tag, count=count)
            else:
                # Local fallback — invalidate by pattern
                to_delete = [k for k in self._local_fallback if tag in k]
                for key in to_delete:
                    del self._local_fallback[key]
                    count += 1
        except Exception as exc:
            logger.warning("cache_invalidate_tag_error", tag=tag, error=str(exc))
        return count

    async def invalidate_user(self, user_id: UUID | str) -> int:
        """Invalidate all cache entries for a user."""
        tag = f"user:{user_id}"
        return await self.invalidate_tag(tag)

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern."""
        count = 0
        try:
            if self._redis:
                full_pattern = f"mastery:{pattern}"
                # Use SCAN for non-blocking pattern matching
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(
                        cursor=cursor, match=full_pattern, count=100
                    )
                    if keys:
                        for key in keys:
                            if isinstance(key, bytes):
                                key = key.decode()
                            await self._redis.delete(key)
                            count += 1
                    if cursor == 0:
                        break
            else:
                to_delete = [k for k in self._local_fallback if pattern in k]
                for key in to_delete:
                    del self._local_fallback[key]
                    count += 1
        except Exception as exc:
            logger.warning("cache_invalidate_pattern_error", pattern=pattern, error=str(exc))
        return count

    async def clear_all(self) -> int:
        """Clear all cache entries (use with caution)."""
        count = 0
        try:
            if self._redis:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(
                        cursor=cursor, match="mastery:*", count=100
                    )
                    if keys:
                        for key in keys:
                            await self._redis.delete(key)
                            count += 1
                    if cursor == 0:
                        break
            else:
                count = len(self._local_fallback)
                self._local_fallback.clear()
            logger.info("cache_cleared_all", count=count)
        except Exception as exc:
            logger.warning("cache_clear_all_error", error=str(exc))
        return count

    def get_stats(self, cache_type: str | None = None) -> dict[str, Any]:
        """Get cache statistics."""
        if cache_type:
            return self._get_stats(cache_type).to_dict()
        return {ct: s.to_dict() for ct, s in self._stats.items()}

    def _get_stats(self, cache_type: str) -> CacheStats:
        if cache_type not in self._stats:
            self._stats[cache_type] = CacheStats()
        return self._stats[cache_type]


# ============================================================
# Cache-Aside Pattern
# ============================================================


class CacheAside:
    """Cache-aside pattern: check cache → if miss, fetch from DB → populate cache.

    Usage:
        result = await cache_aside.get_or_set(
            cache_type="dashboard",
            key=CacheKeyBuilder.build("dashboard", user_id=user_id),
            fetch_fn=lambda: fetch_dashboard_from_db(user_id),
            tags=[f"user:{user_id}"],
        )
    """

    def __init__(self, cache: RedisCache) -> None:
        self._cache = cache

    async def get_or_set(
        self,
        cache_type: str,
        key: str,
        fetch_fn: Callable[[], Awaitable[T]],
        tags: list[str] | None = None,
        ttl: int | None = None,
    ) -> T:
        """Get from cache or fetch from source and cache the result."""
        # Check cache
        cached = await self._cache.get(cache_type, key)
        if cached is not None:
            return cached  # type: ignore

        # Cache miss — fetch from source
        result = await fetch_fn()

        # Populate cache
        await self._cache.set(cache_type, key, result, ttl=ttl, tags=tags)

        return result

    async def invalidate(self, cache_type: str, key: str) -> None:
        """Invalidate a specific cache entry."""
        await self._cache.delete(cache_type, key)

    async def invalidate_tag(self, tag: str) -> int:
        """Invalidate all entries with a tag."""
        return await self._cache.invalidate_tag(tag)


# ============================================================
# Cache Manager (Singleton)
# ============================================================


_cache: RedisCache | None = None
_cache_aside: CacheAside | None = None


def get_cache() -> RedisCache:
    """Get the singleton cache instance."""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


def get_cache_aside() -> CacheAside:
    """Get the singleton cache-aside instance."""
    global _cache_aside
    if _cache_aside is None:
        _cache_aside = CacheAside(get_cache())
    return _cache_aside


def init_cache(redis_client: Any) -> None:
    """Initialize the cache with a Redis client."""
    global _cache, _cache_aside
    _cache = RedisCache(redis_client)
    _cache_aside = CacheAside(_cache)
    logger.info("cache_initialized", redis=bool(redis_client))


__all__ = [
    "CachePolicy",
    "CACHE_POLICIES",
    "CacheStats",
    "CacheKeyBuilder",
    "RedisCache",
    "CacheAside",
    "get_cache",
    "get_cache_aside",
    "init_cache",
]
