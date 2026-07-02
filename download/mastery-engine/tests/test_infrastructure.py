"""
End-to-end infrastructure tests.

These tests verify that the Docker Compose stack starts correctly
and that the health endpoints respond.

Run with: pytest tests/ -m integration
"""

import subprocess
import time

import httpx
import pytest


BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"


def docker_compose_is_running() -> bool:
    """Check if Docker Compose services are running."""
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and "mastery" in result.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture(scope="session")
def ensure_services_running():
    """Ensure Docker Compose services are running before tests."""
    if not docker_compose_is_running():
        pytest.skip("Docker Compose services are not running. Run 'docker compose up -d' first.")
    # Give services time to be ready
    for _ in range(30):
        try:
            response = httpx.get(f"{BACKEND_URL}/api/v1/health", timeout=2)
            if response.status_code == 200:
                return
        except httpx.ConnectError:
            pass
        time.sleep(2)
    pytest.fail("Services did not become healthy in time.")


@pytest.mark.integration
class TestBackendHealth:
    """Tests for backend health endpoints."""

    def test_health_returns_200(self, ensure_services_running):
        """GET /api/v1/health returns 200."""
        response = httpx.get(f"{BACKEND_URL}/api/v1/health")
        assert response.status_code == 200

    def test_health_returns_healthy(self, ensure_services_running):
        """GET /api/v1/health returns status=healthy."""
        response = httpx.get(f"{BACKEND_URL}/api/v1/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_live_returns_200(self, ensure_services_running):
        """GET /api/v1/health/live returns 200."""
        response = httpx.get(f"{BACKEND_URL}/api/v1/health/live")
        assert response.status_code == 200

    def test_correlation_header(self, ensure_services_running):
        """Response includes X-Correlation-ID header."""
        response = httpx.get(
            f"{BACKEND_URL}/api/v1/health",
            headers={"X-Correlation-ID": "test-integration-123"},
        )
        assert response.headers.get("X-Correlation-ID") == "test-integration-123"

    def test_request_id_header(self, ensure_services_running):
        """Response includes X-Request-ID header."""
        response = httpx.get(f"{BACKEND_URL}/api/v1/health")
        assert "X-Request-ID" in response.headers


@pytest.mark.integration
class TestFrontend:
    """Tests for frontend availability."""

    def test_frontend_returns_200(self, ensure_services_running):
        """Frontend root returns 200."""
        response = httpx.get(FRONTEND_URL, timeout=10)
        assert response.status_code == 200
