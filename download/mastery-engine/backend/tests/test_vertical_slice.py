"""Integration tests for the first vertical slice: learner onboarding & session bootstrap.

Tests the complete flow:
1. Register a user
2. Verify email (or auto-verify in development)
3. Enroll in a subject
4. Set a learning goal
5. Start a study session
6. Get the adaptive queue

Uses FastAPI TestClient + real PostgreSQL (via Docker Compose).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Register a user and return auth headers."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"test-{uuid4()}@example.com",
            "password": "SecurePass123!",
            "display_name": "Test User",
            "timezone": "UTC",
            "locale": "en-US",
        },
    )
    assert response.status_code == 201, f"Registration failed: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def verified_user(client: TestClient, auth_headers: dict[str, str]) -> dict[str, str]:
    """Register + verify email, return auth headers."""
    # Get user ID from the registration response
    # In development mode, we can auto-verify via the verify-email endpoint
    # using the user's ID as the token (simplified for this slice)
    user_id = client.get("/api/v1/users/me", headers=auth_headers).json().get("id")
    if user_id:
        # Auto-verify email (simplified: token = user_id)
        client.post(
            "/api/v1/auth/verify-email",
            json={"token": user_id},
            headers=auth_headers,
        )
    return auth_headers


class TestHealthEndpoints:
    """Verify the API is running before testing business flows."""

    def test_health(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_docs_available(self, client: TestClient) -> None:
        response = client.get("/docs")
        assert response.status_code == 200


class TestUserRegistration:
    """Tests for POST /api/v1/auth/register."""

    def test_register_success(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"register-{uuid4()}@example.com",
                "password": "SecurePass123!",
                "display_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["expires_in"] == 900
        assert data["user"]["status"] == "pending_verification"
        assert data["user"]["email"].endswith("@example.com")

    def test_register_weak_password(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"weak-{uuid4()}@example.com",
                "password": "short",
                "display_name": "Weak",
            },
        )
        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "display_name": "Bad Email",
            },
        )
        assert response.status_code == 422

    def test_register_duplicate_email(self, client: TestClient) -> None:
        email = f"dup-{uuid4()}@example.com"
        # First registration
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecurePass123!",
                "display_name": "First",
            },
        )
        # Second registration with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecurePass123!",
                "display_name": "Second",
            },
        )
        assert response.status_code == 409

    def test_register_returns_correlation_id(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"corr-{uuid4()}@example.com",
                "password": "SecurePass123!",
                "display_name": "Corr",
            },
        )
        assert "X-Correlation-ID" in response.headers
        assert "X-Request-ID" in response.headers


class TestEmailVerification:
    """Tests for POST /api/v1/auth/verify-email."""

    def test_verify_email_success(self, client: TestClient) -> None:
        # Register
        reg_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"verify-{uuid4()}@example.com",
                "password": "SecurePass123!",
                "display_name": "Verify",
            },
        )
        user_id = reg_response.json()["user"]["id"]

        # Verify
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": user_id},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_verify_email_invalid_token(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid-uuid"},
        )
        assert response.status_code == 404


class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    def test_login_success(self, client: TestClient) -> None:
        email = f"login-{uuid4()}@example.com"
        password = "SecurePass123!"

        # Register
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "display_name": "Login User",
            },
        )

        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client: TestClient) -> None:
        email = f"wrong-{uuid4()}@example.com"

        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecurePass123!",
                "display_name": "Wrong",
            },
        )

        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword456!"},
        )
        assert response.status_code == 401


class TestEnrollment:
    """Tests for POST /api/v1/enrollments."""

    def test_enroll_success(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        subject_id = str(uuid4())
        response = client.post(
            "/api/v1/enrollments",
            json={"subject_id": subject_id},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending_onboarding"
        assert data["subject_id"] == subject_id

    def test_enroll_without_auth(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/enrollments",
            json={"subject_id": str(uuid4())},
        )
        assert response.status_code == 401

    def test_enroll_duplicate(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        subject_id = str(uuid4())
        # First enrollment
        client.post(
            "/api/v1/enrollments",
            json={"subject_id": subject_id},
            headers=auth_headers,
        )
        # Second enrollment (same subject)
        response = client.post(
            "/api/v1/enrollments",
            json={"subject_id": subject_id},
            headers=auth_headers,
        )
        assert response.status_code == 409


class TestStudySession:
    """Tests for POST /api/v1/study-sessions."""

    def test_start_session_success(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        # Enroll first
        enroll_response = client.post(
            "/api/v1/enrollments",
            json={"subject_id": str(uuid4())},
            headers=auth_headers,
        )
        enrollment_id = enroll_response.json()["id"]

        # Start session
        response = client.post(
            "/api/v1/study-sessions",
            json={
                "enrollment_id": enrollment_id,
                "intent": "drill",
                "target_question_count": 10,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "active"
        assert data["intent"] == "drill"
        assert data["question_count"] == 0

    def test_start_session_duplicate(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        enrollment_response = client.post(
            "/api/v1/enrollments",
            json={"subject_id": str(uuid4())},
            headers=auth_headers,
        )
        enrollment_id = enrollment_response.json()["id"]

        # First session
        client.post(
            "/api/v1/study-sessions",
            json={"enrollment_id": enrollment_id},
            headers=auth_headers,
        )

        # Second session (active exists)
        response = client.post(
            "/api/v1/study-sessions",
            json={"enrollment_id": enrollment_id},
            headers=auth_headers,
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "ACTIVE_SESSION_EXISTS"

    def test_start_session_invalid_intent(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        enrollment_response = client.post(
            "/api/v1/enrollments",
            json={"subject_id": str(uuid4())},
            headers=auth_headers,
        )
        enrollment_id = enrollment_response.json()["id"]

        response = client.post(
            "/api/v1/study-sessions",
            json={"enrollment_id": enrollment_id, "intent": "invalid"},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestAdaptiveQueue:
    """Tests for GET /api/v1/study-sessions/{id}/adaptive-queue."""

    def test_get_queue_success(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        # Enroll + start session
        enrollment_response = client.post(
            "/api/v1/enrollments",
            json={"subject_id": str(uuid4())},
            headers=auth_headers,
        )
        enrollment_id = enrollment_response.json()["id"]

        session_response = client.post(
            "/api/v1/study-sessions",
            json={"enrollment_id": enrollment_id, "intent": "mixed"},
            headers=auth_headers,
        )
        session_id = session_response.json()["id"]

        # Get queue
        response = client.get(
            f"/api/v1/study-sessions/{session_id}/adaptive-queue",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["study_session_id"] == session_id
        assert data["current_position"] == 0
        assert len(data["questions"]) > 0

        # Verify queue item structure
        item = data["questions"][0]
        assert "question_instance_id" in item
        assert "concept_id" in item
        assert "difficulty" in item
        assert "estimated_duration_seconds" in item
        assert "recommendation_score" in item
        assert "reason" in item

    def test_get_queue_nonexistent_session(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get(
            f"/api/v1/study-sessions/{uuid4()}/adaptive-queue",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_get_queue_without_auth(self, client: TestClient) -> None:
        response = client.get(
            f"/api/v1/study-sessions/{uuid4()}/adaptive-queue",
        )
        assert response.status_code == 401


class TestFullOnboardingFlow:
    """End-to-end test of the complete onboarding flow."""

    def test_complete_onboarding_flow(self, client: TestClient) -> None:
        """Register → Verify → Enroll → Set Goal → Start Session → Get Queue."""
        # 1. Register
        email = f"e2e-{uuid4()}@example.com"
        reg_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecurePass123!",
                "display_name": "E2E User",
                "timezone": "Asia/Kolkata",
            },
        )
        assert reg_response.status_code == 201
        token = reg_response.json()["access_token"]
        user_id = reg_response.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Verify email
        verify_response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": user_id},
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["status"] == "active"

        # 3. Enroll
        subject_id = str(uuid4())
        enroll_response = client.post(
            "/api/v1/enrollments",
            json={"subject_id": subject_id},
            headers=headers,
        )
        assert enroll_response.status_code == 201
        enrollment_id = enroll_response.json()["id"]

        # 4. Set learning goal
        goal_response = client.post(
            f"/api/v1/enrollments/{enrollment_id}/learning-goals",
            json={
                "goal_type": "daily_commitment",
                "parameters": {"minutes_per_day": 30},
            },
            headers=headers,
        )
        assert goal_response.status_code == 201

        # 5. Start study session
        session_response = client.post(
            "/api/v1/study-sessions",
            json={
                "enrollment_id": enrollment_id,
                "intent": "mixed",
                "target_question_count": 15,
            },
            headers=headers,
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]
        assert session_response.json()["status"] == "active"

        # 6. Get adaptive queue
        queue_response = client.get(
            f"/api/v1/study-sessions/{session_id}/adaptive-queue",
            headers=headers,
        )
        assert queue_response.status_code == 200
        queue_data = queue_response.json()
        assert len(queue_data["questions"]) > 0

        # Verify the queue is deterministic (same request → same items)
        queue_response_2 = client.get(
            f"/api/v1/study-sessions/{session_id}/adaptive-queue",
            headers=headers,
        )
        assert queue_response_2.status_code == 200
        queue_data_2 = queue_response_2.json()

        # Same number of items
        assert len(queue_data["questions"]) == len(queue_data_2["questions"])
        # Same concepts (deterministic)
        concepts_1 = [q["concept_id"] for q in queue_data["questions"]]
        concepts_2 = [q["concept_id"] for q in queue_data_2["questions"]]
        assert concepts_1 == concepts_2
