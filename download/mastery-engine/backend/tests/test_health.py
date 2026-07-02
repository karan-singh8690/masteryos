"""Tests for health check endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /api/v1/health."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health endpoint returns 200 with service info."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_returns_app_name(self, client: TestClient) -> None:
        """Health response includes the application name."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "app" in data
        assert data["status"] == "healthy"

    def test_health_returns_version(self, client: TestClient) -> None:
        """Health response includes the version."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "version" in data

    def test_health_returns_timestamp(self, client: TestClient) -> None:
        """Health response includes a timestamp."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"] > 0


class TestLiveEndpoint:
    """Tests for GET /api/v1/health/live."""

    def test_live_returns_200(self, client: TestClient) -> None:
        """Live endpoint returns 200."""
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200

    def test_live_returns_healthy(self, client: TestClient) -> None:
        """Live endpoint returns healthy status."""
        response = client.get("/api/v1/health/live")
        data = response.json()
        assert data["status"] == "healthy"


class TestRootEndpoint:
    """Tests for GET /."""

    def test_root_returns_200(self, client: TestClient) -> None:
        """Root endpoint returns 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_service_info(self, client: TestClient) -> None:
        """Root endpoint returns service information."""
        response = client.get("/")
        data = response.json()
        assert "service" in data
        assert "version" in data
