"""Tests for the correlation middleware."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestCorrelationMiddleware:
    """Tests for request/correlation ID middleware."""

    def test_response_has_request_id(self) -> None:
        """Response includes X-Request-ID header."""
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert "X-Request-ID" in response.headers

    def test_response_has_correlation_id(self) -> None:
        """Response includes X-Correlation-ID header."""
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert "X-Correlation-ID" in response.headers

    def test_client_correlation_id_is_preserved(self) -> None:
        """Client-provided X-Correlation-ID is echoed back."""
        client = TestClient(app)
        response = client.get(
            "/api/v1/health",
            headers={"X-Correlation-ID": "test-correlation-123"},
        )
        assert response.headers["X-Correlation-ID"] == "test-correlation-123"

    def test_client_request_id_is_preserved(self) -> None:
        """Client-provided X-Request-ID is echoed back."""
        client = TestClient(app)
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "test-request-456"},
        )
        assert response.headers["X-Request-ID"] == "test-request-456"

    def test_unique_request_ids_when_not_provided(self) -> None:
        """Each request gets a unique request ID when not provided."""
        client = TestClient(app)
        response1 = client.get("/api/v1/health")
        response2 = client.get("/api/v1/health")
        assert response1.headers["X-Request-ID"] != response2.headers["X-Request-ID"]
