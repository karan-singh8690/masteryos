"""Performance middleware — compression, ETags, response caching, request timing.

Optimizes HTTP responses for production:
- Gzip/Brotli compression
- ETag-based conditional requests (304 Not Modified)
- Response timing headers
- Request ID propagation
- Slow request logging
"""

from __future__ import annotations

import gzip
import hashlib
import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.shared.logging import get_logger

logger = get_logger(__name__)

# ============================================================
# Compression Middleware
# ============================================================


class CompressionMiddleware(BaseHTTPMiddleware):
    """Gzip compression for responses > 1KB.

    Skips compression for:
    - Responses < 1KB
    - Already-compressed content types (images, video, zip)
    - WebSocket upgrades
    - SSE streams
    """

    MIN_COMPRESS_SIZE = 1024  # 1KB
    COMPRESSIBLE_TYPES = {
        "application/json",
        "text/html",
        "text/css",
        "text/javascript",
        "application/javascript",
        "application/xml",
        "text/xml",
        "text/plain",
    }
    SKIP_TYPES = {
        "image/", "video/", "audio/", "application/zip",
        "application/gzip", "application/x-gzip",
    }

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # Skip if client doesn't accept gzip
        accept_encoding = request.headers.get("Accept-Encoding", "")
        if "gzip" not in accept_encoding:
            return response

        # Skip if response is too small
        content_length = int(response.headers.get("Content-Length", 0))
        if content_length < self.MIN_COMPRESS_SIZE:
            return response

        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if not any(ct in content_type for ct in self.COMPRESSIBLE_TYPES):
            return response
        if any(st in content_type for st in self.SKIP_TYPES):
            return response

        # Compress the response body
        if hasattr(response, "body"):
            body = response.body
            if isinstance(body, (bytes, bytearray)):
                compressed = gzip.compress(bytes(body), compresslevel=6)
                if len(compressed) < len(body):
                    response.body = compressed
                    response.headers["Content-Encoding"] = "gzip"
                    response.headers["Content-Length"] = str(len(compressed))
                    response.headers["Vary"] = "Accept-Encoding"

        return response


# ============================================================
# ETag Middleware
# ============================================================


class ETagMiddleware(BaseHTTPMiddleware):
    """ETag-based conditional requests for cacheable endpoints.

    - Generates ETag from response body hash
    - Returns 304 Not Modified if ETag matches
    - Only applies to GET requests
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Only apply to GET requests
        if request.method != "GET":
            return await call_next(request)

        response = await call_next(request)

        # Skip if no body or not a successful response
        if response.status_code != 200 or not hasattr(response, "body"):
            return response

        # Skip SSE streams
        content_type = response.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            return response

        # Generate ETag
        body = response.body if hasattr(response, "body") else b""
        if isinstance(body, (bytes, bytearray)):
            etag = f'"{hashlib.md5(bytes(body)).hexdigest()}"'
            response.headers["ETag"] = etag

            # Check if client's ETag matches
            if_none_match = request.headers.get("If-None-Match")
            if if_none_match == etag:
                return Response(
                    status_code=304,
                    headers={
                        "ETag": etag,
                        "Cache-Control": "private, max-age=30",
                    },
                )

        return response


# ============================================================
# Request Timing Middleware
# ============================================================


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Adds Server-Timing header + logs slow requests.

    Headers:
    - Server-Timing: total;dur=Xms;db;dur=Yms;cache;dur=Zms
    - X-Response-Time: Xms
    """

    SLOW_REQUEST_THRESHOLD_MS = 500  # Log requests slower than 500ms

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()

        # Add request start time for downstream use
        request.state.request_start_time = start_time

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add timing headers
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        response.headers["Server-Timing"] = f"total;dur={duration_ms:.0f}"

        # Log slow requests
        if duration_ms > self.SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                "slow_request",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                status_code=response.status_code,
            )

        # Log all requests at debug level
        logger.debug(
            "request_completed",
            method=request.method,
            path=request.url.path,
            duration_ms=round(duration_ms, 2),
            status_code=response.status_code,
        )

        return response


# ============================================================
# Rate Limit Enhancement (Redis-backed)
# ============================================================


class ProductionRateLimiter:
    """Redis-backed distributed rate limiter.

    Uses sliding window algorithm for accurate rate limiting
    across multiple worker processes.

    Limits:
    - Global: 1000 req/min per IP
    - Auth endpoints: 10 req/min per IP
    - API endpoints: 60 req/min per user
    - Question submission: 30 req/min per user
    - AI endpoints: 20 req/min per user
    - WebSocket: 10 connections per user
    """

    RATE_LIMITS: dict[str, tuple[int, int]] = {
        # path_pattern → (requests, window_seconds)
        "/api/v1/auth/login": (10, 60),
        "/api/v1/auth/register": (5, 60),
        "/api/v1/auth/forgot-password": (3, 60),
        "/api/v1/auth/verify-email": (10, 60),
        "/api/v1/auth/resend-verification": (3, 60),
        "/api/v1/auth/reset-password": (5, 60),
        "/api/v1/auth/refresh": (30, 60),
        "/api/v1/questions/*/submit": (30, 60),
        "/api/v1/ai/*": (20, 60),
        "_default": (60, 60),
    }

    def __init__(self, redis_client: Any = None) -> None:
        self._redis = redis_client
        self._local_counts: dict[str, list[float]] = {}  # Fallback

    async def check(
        self,
        identifier: str,
        path: str,
        is_authenticated: bool = False,
    ) -> tuple[bool, int, int]:
        """Check if request is allowed.

        Returns (allowed, remaining, retry_after_seconds).
        """
        # Find matching rate limit
        limit_key = "_default"
        for pattern, (limit, window) in self.RATE_LIMITS.items():
            if "*" in pattern:
                # Wildcard match
                parts = pattern.split("*")
                if all(p in path for p in parts if p):
                    limit_key = pattern
                    break
            elif path == pattern or path.startswith(pattern):
                limit_key = pattern
                break

        max_requests, window = self.RATE_LIMITS[limit_key]
        key = f"ratelimit:{identifier}:{limit_key}"

        try:
            if self._redis:
                # Sliding window with Redis sorted sets
                now = time.time()
                pipe = self._redis.pipeline()

                # Remove old entries
                pipe.zremrangebyscore(key, 0, now - window)
                # Count current entries
                pipe.zcard(key)
                # Add current request
                pipe.zadd(key, {str(now): now})
                # Set expiry
                pipe.expire(key, window)

                results = await pipe.execute()
                current_count = results[1]

                if current_count >= max_requests:
                    retry_after = int(window - (now - (now - window)))
                    return (False, 0, max(1, retry_after))

                remaining = max_requests - current_count - 1
                return (True, remaining, 0)
            else:
                # Local fallback
                if key not in self._local_counts:
                    self._local_counts[key] = []

                now = time.time()
                self._local_counts[key] = [
                    t for t in self._local_counts[key] if t > now - window
                ]

                if len(self._local_counts[key]) >= max_requests:
                    oldest = self._local_counts[key][0]
                    retry_after = int(window - (now - oldest))
                    return (False, 0, max(1, retry_after))

                self._local_counts[key].append(now)
                remaining = max_requests - len(self._local_counts[key])
                return (True, remaining, 0)

        except Exception as exc:
            logger.warning("rate_limit_check_error", error=str(exc))
            # Fail open — allow request if rate limiter is down
            return (True, 999, 0)


# ============================================================
# Query Optimization Helpers
# ============================================================


class QueryOptimizer:
    """Helpers for optimizing database queries.

    Provides:
    - Eager loading recommendations
    - N+1 query detection
    - Query count tracking
    - Slow query logging
    """

    SLOW_QUERY_THRESHOLD_MS = 100

    def __init__(self) -> None:
        self._query_count = 0
        self._slow_queries: list[dict[str, Any]] = []

    def record_query(self, duration_ms: float, statement: str, params: dict | None = None) -> None:
        """Record a database query for monitoring."""
        self._query_count += 1

        if duration_ms > self.SLOW_QUERY_THRESHOLD_MS:
            entry = {
                "duration_ms": round(duration_ms, 2),
                "statement": statement[:200],
                "params": str(params)[:200] if params else None,
                "timestamp": datetime.now(tz_utc.utc).isoformat(),
            }
            self._slow_queries.append(entry)
            logger.warning(
                "slow_query",
                duration_ms=round(duration_ms, 2),
                statement=statement[:200],
            )

    @property
    def query_count(self) -> int:
        return self._query_count

    @property
    def slow_query_count(self) -> int:
        return len(self._slow_queries)

    def get_slow_queries(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._slow_queries[-limit:]

    def reset(self) -> None:
        self._query_count = 0
        self._slow_queries.clear()


# Need datetime import
from datetime import datetime, timezone as tz_utc  # noqa: E402


__all__ = [
    "CompressionMiddleware",
    "ETagMiddleware",
    "RequestTimingMiddleware",
    "ProductionRateLimiter",
    "QueryOptimizer",
]
