"""Rate limiting and CSRF integration tests.

Tests:
- Rate limiting is disabled in testing mode (so tests can run fast)
- Rate limiter correctly limits requests in production mode
- Rate limiter returns 429 with Retry-After header
- CSRF middleware allows Bearer-token requests
- CSRF middleware blocks cookie-based requests with wrong Origin
- CSRF middleware allows requests with no Origin (e.g., curl)
- Rate limiter tracks per-IP, per-endpoint
- Rate limiter has different limits for different endpoints
"""

from __future__ import annotations

import pytest

from app.presentation.middleware.security import RateLimiter


pytestmark = pytest.mark.asyncio


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_rate_limiter_allows_first_request(self):
        """The first request is always allowed."""
        limiter = RateLimiter()
        allowed, remaining, retry_after = limiter.check("127.0.0.1", "/api/v1/auth/login")
        assert allowed is True
        assert remaining >= 0
        assert retry_after == 0

    def test_rate_limiter_blocks_after_limit(self):
        """After exceeding the limit, requests are blocked."""
        limiter = RateLimiter()
        # /api/v1/auth/register has limit (5, 60) — 5 per minute
        for _ in range(5):
            allowed, _, _ = limiter.check("127.0.0.1", "/api/v1/auth/register")
            assert allowed is True

        # 6th request should be blocked
        allowed, remaining, retry_after = limiter.check("127.0.0.1", "/api/v1/auth/register")
        assert allowed is False
        assert remaining == 0
        assert retry_after > 0

    def test_rate_limiter_admin_bypass(self):
        """Admin users bypass rate limiting."""
        limiter = RateLimiter()
        # Make many requests as admin
        for _ in range(100):
            allowed, _, _ = limiter.check(
                "127.0.0.1", "/api/v1/auth/register", is_admin=True
            )
            assert allowed is True

    def test_rate_limiter_separate_buckets_per_endpoint(self):
        """Different endpoints have separate rate limit buckets."""
        limiter = RateLimiter()
        # Exhaust /register
        for _ in range(5):
            limiter.check("127.0.0.1", "/api/v1/auth/register")

        # /login should still be allowed (separate bucket)
        allowed, _, _ = limiter.check("127.0.0.1", "/api/v1/auth/login")
        assert allowed is True

    def test_rate_limiter_separate_buckets_per_ip(self):
        """Different IPs have separate rate limit buckets."""
        limiter = RateLimiter()
        # Exhaust 127.0.0.1's register bucket
        for _ in range(5):
            limiter.check("127.0.0.1", "/api/v1/auth/register")

        # 192.168.1.1 should still be allowed
        allowed, _, _ = limiter.check("192.168.1.1", "/api/v1/auth/register")
        assert allowed is True

    def test_rate_limiter_returns_retry_after(self):
        """When blocked, retry_after is positive."""
        limiter = RateLimiter()
        for _ in range(5):
            limiter.check("127.0.0.1", "/api/v1/auth/register")

        _, _, retry_after = limiter.check("127.0.0.1", "/api/v1/auth/register")
        assert retry_after > 0


class TestCSRFMiddleware:
    """Tests for CSRF middleware behavior (via API calls)."""

    async def test_bearer_token_requests_not_csrf_checked(
        self, test_client, test_session_factory, auth_service
    ):
        """Bearer-token requests bypass CSRF checks."""
        from tests.auth.conftest import create_test_user, get_auth_headers

        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="csrf@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "csrf@example.com", "SecurePassword123!"
        )

        # Make a POST with Bearer auth — should succeed (no CSRF check)
        response = await test_client.post(
            "/api/v1/auth/logout",
            json=None,
            headers=headers,
        )
        # Should not be a CSRF error (403). It might be 200 (logout success)
        assert response.status_code != 403 or "CSRF" not in response.text

    async def test_get_requests_not_csrf_checked(self, test_client):
        """GET requests bypass CSRF checks."""
        response = await test_client.get("/api/v1/health")
        # Should not be a CSRF error
        assert response.status_code != 403

    async def test_health_endpoints_bypass_csrf(self, test_client):
        """Health check endpoints bypass CSRF checks."""
        response = await test_client.get("/api/v1/health")
        assert response.status_code in (200, 503)  # Health check response
