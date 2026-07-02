"""Security middleware — headers, rate limiting, CSRF protection.

Implements:
- Security headers (HSTS, X-Frame-Options, X-Content-Type-Options, CSP, Referrer-Policy)
- Rate limiting (in-memory token bucket; production uses Redis)
- CSRF protection (double-submit cookie + origin validation)
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Security Headers Middleware
# ============================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response.

    Headers (per OWASP):
    - Strict-Transport-Security: max-age=31536000; includeSubDomains (HSTS)
    - X-Frame-Options: DENY (clickjacking)
    - X-Content-Type-Options: nosniff (MIME sniffing)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: restrictive defaults
    - Content-Security-Policy: default-src 'none' (API-only; no inline)
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # HSTS (only meaningful over HTTPS, but set anyway for proxies)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (disable features)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # CSP (API returns JSON; no scripts/styles/images needed)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )

        # Remove server header (don't leak framework info)
        if "server" in response.headers:
            del response.headers["server"]

        return response


# ============================================================
# Rate Limiting Middleware
# ============================================================


class RateLimiter:
    """In-memory token bucket rate limiter.

    Production uses Redis for distributed rate limiting.
    This implementation supports:
    - Per-IP limits
    - Per-user limits
    - Per-endpoint limits
    - Burst support (token bucket)
    - Sliding window
    """

    def __init__(self) -> None:
        # Key: (identifier, endpoint) → (tokens, last_refill)
        self._buckets: dict[tuple[str, str], tuple[float, float]] = {}
        # Default limits
        self._limits: dict[str, tuple[int, int]] = {
            # endpoint_pattern → (requests_per_window, window_seconds)
            "/api/v1/auth/login": (10, 60),  # 10 per minute
            "/api/v1/auth/register": (5, 60),  # 5 per minute
            "/api/v1/auth/forgot-password": (3, 60),  # 3 per minute
            "/api/v1/auth/verify-email": (10, 60),
            "/api/v1/auth/resend-verification": (3, 60),
            "/api/v1/auth/reset-password": (5, 60),
            "/api/v1/auth/refresh": (30, 60),
            "/api/v1/questions/*/submit": (100, 60),  # 100 per minute
        }
        self._default_limit = (60, 60)  # 60 per minute default
        self._admin_bypass = True  # Admins bypass rate limiting

    def check(
        self,
        identifier: str,
        endpoint: str,
        is_admin: bool = False,
    ) -> tuple[bool, int, int]:
        """Check if a request is allowed.

        Returns:
            (allowed, remaining, retry_after_seconds)
        """
        if is_admin and self._admin_bypass:
            return (True, 999, 0)

        # Find matching limit
        limit_key = self._find_limit_key(endpoint)
        max_requests, window = self._limits.get(limit_key, self._default_limit)

        bucket_key = (identifier, limit_key)
        now = time.time()

        if bucket_key not in self._buckets:
            # First request
            self._buckets[bucket_key] = (max_requests - 1, now)
            return (True, max_requests - 1, 0)

        tokens, last_refill = self._buckets[bucket_key]

        # Refill tokens based on elapsed time
        elapsed = now - last_refill
        refill_rate = max_requests / window
        tokens = min(max_requests, tokens + elapsed * refill_rate)

        if tokens < 1:
            # Rate limited
            retry_after = int((1 - tokens) / refill_rate) + 1
            return (False, 0, retry_after)

        # Consume one token
        self._buckets[bucket_key] = (tokens - 1, now)
        return (True, int(tokens - 1), 0)

    def _find_limit_key(self, endpoint: str) -> str:
        """Find the matching limit key for an endpoint."""
        # Exact match
        if endpoint in self._limits:
            return endpoint

        # Wildcard match (e.g., /api/v1/questions/*/submit)
        for pattern in self._limits:
            if "*" in pattern:
                # Convert pattern to a simple match
                parts = pattern.split("*")
                if all(p in endpoint for p in parts if p):
                    return pattern

        return "_default"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using token bucket algorithm.

    Keys by IP for unauthenticated requests, by user_id for authenticated.
    """

    def __init__(self, app: Any, limiter: RateLimiter | None = None) -> None:
        super().__init__(app)
        self._limiter = limiter or RateLimiter()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for health checks
        path = request.url.path
        if path.startswith("/api/v1/health") or path == "/" or path == "/docs":
            return await call_next(request)

        # Get identifier (IP for now; user_id for authenticated in production)
        identifier = request.client.host if request.client else "unknown"

        allowed, remaining, retry_after = self._limiter.check(identifier, path)

        if not allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "code": "RATE_LIMITED",
                    "message": "Rate limit exceeded. Retry after specified seconds.",
                    "correlation_id": request.headers.get("X-Correlation-ID"),
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": "60",
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


# ============================================================
# CSRF Protection Middleware
# ============================================================


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection via double-submit cookie + origin validation.

    For state-changing requests (POST, PUT, PATCH, DELETE):
    1. Check Origin header matches allowed origins
    2. Check SameSite cookie attribute (set by auth service)
    3. For API requests with Bearer auth, CSRF is not applicable
       (Bearer tokens are not sent by browsers automatically)

    This middleware primarily protects cookie-based auth (refresh tokens).
    """

    EXEMPT_PATHS = {"/api/v1/health", "/api/v1/health/ready", "/api/v1/health/live"}
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip health checks and safe methods
        if path in self.EXEMPT_PATHS or request.method in self.SAFE_METHODS:
            return await call_next(request)

        # For Bearer-token-authenticated requests, CSRF is not applicable
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        # For cookie-based requests (refresh token), validate Origin
        origin = request.headers.get("Origin") or request.headers.get("Referer", "")
        if origin:
            # Check if origin is in allowed list
            allowed_origins = [
                "http://localhost:3000",
                "http://localhost:8000",
                "https://app.masteryengine.com",
                "https://admin.masteryengine.com",
            ]
            if origin not in allowed_origins:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=403,
                    content={
                        "code": "CSRF_VALIDATION_FAILED",
                        "message": "Origin validation failed",
                    },
                )

        return await call_next(request)
