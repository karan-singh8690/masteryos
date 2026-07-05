"""Redis Cache Middleware — cache GET responses for hot endpoints.

Wraps GET requests to specific endpoints and caches the response in Redis.
Uses cache-aside pattern with tag-based invalidation.
"""

from __future__ import annotations

import json
import hashlib
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.shared.logging import get_logger

logger = get_logger(__name__)

# Endpoints to cache with their TTLs (in seconds)
CACHE_POLICIES: dict[str, int] = {
    "/api/v1/health": 10,                    # 10 seconds
    "/api/v1/health/ready": 10,
    "/api/v1/health/live": 10,
    "/api/v1/beta/status": 60,               # 1 minute
    "/api/v1/billing/plans": 300,            # 5 minutes
    "/api/v1/admin/feature-flags": 60,
    "/api/v1/feature-flags": 60,
    "/api/v1/ai/status": 30,
    "/api/v1/metrics": 15,
}


class CacheMiddleware(BaseHTTPMiddleware):
    """Redis-backed response cache for GET requests."""

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self._redis = redis_client

    async def dispatch(self, request: Request, call_next):
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)

        # Check if this path should be cached
        path = request.url.path
        ttl = self._get_ttl(path)
        if ttl is None:
            return await call_next(request)

        # Don't cache if Redis isn't available
        if not self._redis:
            return await call_next(request)

        # Generate cache key
        cache_key = self._generate_key(request)

        # Try to get from cache
        try:
            cached = await self._redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return JSONResponse(
                    content=data["body"],
                    status_code=data["status"],
                    headers={
                        **data.get("headers", {}),
                        "X-Cache": "HIT",
                        "X-Cache-TTL": str(ttl),
                    },
                )
        except Exception as exc:
            logger.warning("cache_read_failed", error=str(exc))

        # Cache miss — call the endpoint
        response = await call_next(request)

        # Only cache successful responses
        if response.status_code == 200:
            try:
                # Read response body
                body_bytes = b""
                async for chunk in response.body_iterator:
                    body_bytes += chunk

                body = json.loads(body_bytes)

                # Store in Redis
                cache_data = {
                    "body": body,
                    "status": response.status_code,
                    "headers": dict(response.headers),
                }
                await self._redis.setex(
                    cache_key,
                    ttl,
                    json.dumps(cache_data),
                )

                # Reconstruct response
                return JSONResponse(
                    content=body,
                    status_code=response.status_code,
                    headers={**dict(response.headers), "X-Cache": "MISS"},
                )
            except Exception as exc:
                logger.warning("cache_write_failed", error=str(exc))

        return response

    def _get_ttl(self, path: str) -> int | None:
        """Get cache TTL for a path."""
        for pattern, ttl in CACHE_POLICIES.items():
            if path == pattern or path.startswith(pattern + "/"):
                return ttl
        return None

    def _generate_key(self, request: Request) -> str:
        """Generate a cache key from the request."""
        key_parts = [
            request.method,
            request.url.path,
            str(request.query_params),
        ]
        # Include user ID in cache key if authenticated
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            # Hash the token to avoid storing it
            key_parts.append(hashlib.sha256(auth.encode()).hexdigest()[:16])

        key_string = ":".join(key_parts)
        return f"masteryos:cache:{hashlib.sha256(key_string.encode()).hexdigest()}"
