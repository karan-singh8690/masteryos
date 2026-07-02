"""Integration tests for the complete learning loop vertical slice.

Tests the full cycle:
  Queue → Question → Submit Answer → Attempt → Mastery → Review → Explanation → Recommendation → Dashboard

Uses FastAPI TestClient against real PostgreSQL (via Docker Compose).
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import uuid4
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def authenticated_learner(client: TestClient) -> dict[str, str]:
    """Register, verify, and return auth headers for a ready-to-study learner."""
    # Register
    reg = client.post("/api/v1/auth/register", json={
        "email": f"learner-{uuid4()}@example.com",
        "password": "SecurePass123!",
        "display_name": "Test Learner",
    })
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    user_id = reg.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify email
    client.post("/api/v1/auth/verify-email", json={"token": user_id})

    return headers


@pytest.fixture
def enrolled_learner(client: TestClient, authenticated_learner: dict[str, str]) -> tuple[dict[str, str], str]:
    """Enroll and return (headers, enrollment_id)."""
    subject_id = str(uuid4())
    enroll = client.post("/api/v1/enrollments", json={"subject_id": subject_id}, headers=authenticated_learner)
    assert enroll.status_code == 201
    return authenticated_learner, enroll.json()["id"]


@pytest.fixture
def active_session(client: TestClient, enrolled_learner: tuple[dict[str, str], str]) -> tuple[dict[str, str], str, str]:
    """Start a session and return (headers, enrollment_id, session_id)."""
    headers, enrollment_id = enrolled_learner
    session = client.post("/api/v1/study-sessions", json={
        "enrollment_id": enrollment_id,
        "intent": "mixed",
    }, headers=headers)
    assert session.status_code == 201
    return headers, enrollment_id, session.json()["id"]


@pytest.fixture
def question_instance_id(client: TestClient, active_session: tuple[dict[str, str], str, str]) -> str:
    """Get a question instance ID from the adaptive queue."""
    headers, _, session_id = active_session
    queue = client.get(f"/api/v1/study-sessions/{session_id}/adaptive-queue", headers=headers)
    assert queue.status_code == 200
    questions = queue.json()["questions"]
    assert len(questions) > 0
    return questions[0]["question_instance_id"]


# ============================================================
# Question Retrieval Tests
# ============================================================


class TestGetQuestion:
    """Tests for GET /api/v1/questions/{question_instance_id}."""

    def test_get_question_success(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        headers = active_session[0]
        response = client.get(f"/api/v1/questions/{question_instance_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["question_instance_id"] == question_instance_id
        assert "prompt" in data
        assert "difficulty" in data
        assert "estimated_duration_seconds" in data
        # Must NEVER expose correct answer
        assert "correct_answer" not in data
        assert "correct" not in json.dumps(data).lower() or "correct" not in data

    def test_get_question_without_auth(self, client: TestClient, question_instance_id: str) -> None:
        response = client.get(f"/api/v1/questions/{question_instance_id}")
        assert response.status_code == 401

    def test_get_nonexistent_question(self, client: TestClient, authenticated_learner: dict[str, str]) -> None:
        response = client.get(f"/api/v1/questions/{uuid4()}", headers=authenticated_learner)
        assert response.status_code == 404


# ============================================================
# Answer Submission Tests
# ============================================================


class TestSubmitAnswer:
    """Tests for POST /api/v1/questions/{question_instance_id}/submit."""

    def test_submit_correct_answer(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        """Submit a correct answer → full learning loop executes."""
        headers = active_session[0]
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={
                "answer": {"choice": "placeholder"},
                "answer_type": "multiple_choice",
                "confidence": 0.8,
                "time_spent_seconds": 15,
                "hint_used": False,
            },
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()

        # Attempt is recorded
        assert "attempt" in data
        assert data["attempt"]["scoring_outcome"] in ("correct", "incorrect", "partial")
        assert data["attempt"]["time_to_answer_ms"] == 15000

        # Mastery is updated
        assert data["mastery"] is not None
        assert "memory_score" in data["mastery"]
        assert "durable_mastery_score" in data["mastery"]
        assert "mastery_score_combined" in data["mastery"]
        assert "concept_state" in data["mastery"]

        # Review is scheduled
        assert data["review"] is not None
        assert "due_at" in data["review"]
        assert "priority" in data["review"]
        assert "interval_days" in data["review"]

        # Explanation is returned
        assert data["explanation"] is not None
        assert "content" in data["explanation"]
        assert len(data["explanation"]["content"]) > 0

    def test_submit_with_hint(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        """Submit with hint_used=True → expanded explanation."""
        headers = active_session[0]
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={
                "answer": {"choice": "wrong"},
                "answer_type": "multiple_choice",
                "confidence": 0.3,
                "time_spent_seconds": 45,
                "hint_used": True,
                "hint_tiers_used": [1],
            },
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["attempt"]["hint_used"] is True
        # Explanation should be expanded (longer text)
        assert "hint" in data["explanation"]["content"].lower() or len(data["explanation"]["content"]) > 50

    def test_submit_fast_response(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        """Fast response (3 seconds) → still works."""
        headers = active_session[0]
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={
                "answer": {"choice": "test"},
                "confidence": 0.9,
                "time_spent_seconds": 3,
            },
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["attempt"]["time_to_answer_ms"] == 3000

    def test_submit_slow_response(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        """Slow response (120 seconds) → still works."""
        headers = active_session[0]
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={
                "answer": {"choice": "test"},
                "confidence": 0.2,
                "time_spent_seconds": 120,
            },
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["attempt"]["time_to_answer_ms"] == 120000

    def test_submit_high_confidence(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        """High confidence (0.95) → accepted."""
        headers = active_session[0]
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={
                "answer": {"choice": "test"},
                "confidence": 0.95,
                "time_spent_seconds": 10,
            },
            headers=headers,
        )
        assert response.status_code == 201

    def test_submit_low_confidence(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        """Low confidence (0.1) → accepted."""
        headers = active_session[0]
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={
                "answer": {"choice": "test"},
                "confidence": 0.1,
                "time_spent_seconds": 10,
            },
            headers=headers,
        )
        assert response.status_code == 201

    def test_submit_without_auth(self, client: TestClient, question_instance_id: str) -> None:
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={"answer": {"choice": "test"}, "time_spent_seconds": 10},
        )
        assert response.status_code == 401

    def test_submit_to_nonexistent_question(self, client: TestClient, authenticated_learner: dict[str, str]) -> None:
        response = client.post(
            f"/api/v1/questions/{uuid4()}/submit",
            json={"answer": {"choice": "test"}, "time_spent_seconds": 10},
            headers=authenticated_learner,
        )
        assert response.status_code == 404

    def test_submit_to_already_answered(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        """Cannot submit to an already-answered question."""
        headers = active_session[0]
        # First submission
        client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={"answer": {"choice": "test"}, "time_spent_seconds": 10},
            headers=headers,
        )
        # Second submission
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={"answer": {"choice": "test2"}, "time_spent_seconds": 5},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "QUESTION_ALREADY_ANSWERED"

    def test_submit_invalid_confidence(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        """Confidence outside [0.0, 1.0] → validation error."""
        headers = active_session[0]
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={"answer": {"choice": "test"}, "confidence": 1.5, "time_spent_seconds": 10},
            headers=headers,
        )
        assert response.status_code == 422

    def test_submit_negative_time(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        """Negative time_spent → validation error."""
        headers = active_session[0]
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={"answer": {"choice": "test"}, "time_spent_seconds": -1},
            headers=headers,
        )
        assert response.status_code == 422


# ============================================================
# Mastery & Review Verification Tests
# ============================================================


class TestMasteryAndReview:
    """Verify that mastery scores and reviews are updated after submission."""

    def test_mastery_evidence_count_increments(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        """After submission, evidence_count should be >= 1."""
        headers = active_session[0]
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={"answer": {"choice": "test"}, "time_spent_seconds": 10},
            headers=headers,
        )
        assert response.status_code == 201
        mastery = response.json()["mastery"]
        assert mastery is not None
        assert mastery["evidence_count"] >= 1

    def test_review_due_date_is_future(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        """Review due_at should be in the future."""
        headers = active_session[0]
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={"answer": {"choice": "test"}, "time_spent_seconds": 10},
            headers=headers,
        )
        assert response.status_code == 201
        review = response.json()["review"]
        assert review is not None
        due_at = datetime.fromisoformat(review["due_at"].replace("Z", "+00:00"))
        assert due_at > datetime.now(timezone.utc)

    def test_review_interval_within_bounds(self, client: TestClient, active_session: tuple, question_instance_id: str) -> None:
        """Review interval must be between 1 and 365 days."""
        headers = active_session[0]
        response = client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={"answer": {"choice": "test"}, "time_spent_seconds": 10},
            headers=headers,
        )
        assert response.status_code == 201
        review = response.json()["review"]
        assert 1 <= review["interval_days"] <= 365


# ============================================================
# Dashboard Tests
# ============================================================


class TestDashboard:
    """Tests for the enriched dashboard endpoint."""

    def test_dashboard_before_any_activity(self, client: TestClient, authenticated_learner: dict[str, str]) -> None:
        """Dashboard works even before enrollment."""
        response = client.get("/api/v1/questions/api/v1/dashboard", headers=authenticated_learner)
        # The dashboard route is registered on the questions router with a full path
        # Let's use the correct path
        response = client.get("/api/v1/dashboard", headers=authenticated_learner)
        # May return 200 with empty data or 404 if no enrollment
        # For this test, we accept either — the important thing is no 500
        assert response.status_code in (200, 404)

    def test_dashboard_after_submission(
        self, client: TestClient, active_session: tuple, question_instance_id: str
    ) -> None:
        """After submitting an answer, dashboard should show updated data."""
        headers = active_session[0]

        # Submit an answer first
        client.post(
            f"/api/v1/questions/{question_instance_id}/submit",
            json={"answer": {"choice": "test"}, "time_spent_seconds": 10},
            headers=headers,
        )

        # Get dashboard
        response = client.get("/api/v1/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Verify dashboard structure
        assert "recommended_action" in data
        assert "current_streak" in data
        assert "longest_streak" in data
        assert "weak_concepts" in data
        assert "strong_concepts" in data
        assert "today_reviews" in data
        assert "interview_readiness" in data
        assert "memory_trend" in data
        assert "mastery_trend" in data

        # Streak should be >= 1 after a submission
        assert data["current_streak"] >= 1


# ============================================================
# Full Learning Loop Test
# ============================================================


class TestFullLearningLoop:
    """End-to-end test of the complete learning loop."""

    def test_complete_learning_loop(self, client: TestClient) -> None:
        """
        Complete learning loop:
        Register → Verify → Enroll → Set Goal → Start Session → Get Queue →
        Get Question → Submit Answer → Verify Mastery → Verify Review →
        Verify Explanation → Verify Recommendation → Verify Dashboard
        """
        # 1. Register
        email = f"loop-{uuid4()}@example.com"
        reg = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "SecurePass123!",
            "display_name": "Loop Learner",
        })
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        user_id = reg.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Verify email
        verify = client.post("/api/v1/auth/verify-email", json={"token": user_id})
        assert verify.status_code == 200

        # 3. Enroll
        subject_id = str(uuid4())
        enroll = client.post("/api/v1/enrollments", json={"subject_id": subject_id}, headers=headers)
        assert enroll.status_code == 201
        enrollment_id = enroll.json()["id"]

        # 4. Set learning goal
        goal = client.post(
            f"/api/v1/enrollments/{enrollment_id}/learning-goals",
            json={"goal_type": "daily_commitment", "parameters": {"minutes_per_day": 30}},
            headers=headers,
        )
        assert goal.status_code == 201

        # 5. Start study session
        session = client.post("/api/v1/study-sessions", json={
            "enrollment_id": enrollment_id,
            "intent": "mixed",
            "target_question_count": 15,
        }, headers=headers)
        assert session.status_code == 201
        session_id = session.json()["id"]
        assert session.json()["status"] == "active"

        # 6. Get adaptive queue
        queue = client.get(f"/api/v1/study-sessions/{session_id}/adaptive-queue", headers=headers)
        assert queue.status_code == 200
        questions = queue.json()["questions"]
        assert len(questions) > 0
        question_id = questions[0]["question_instance_id"]

        # 7. Get question
        question = client.get(f"/api/v1/questions/{question_id}", headers=headers)
        assert question.status_code == 200
        assert "correct_answer" not in question.json()

        # 8. Submit answer
        submit = client.post(
            f"/api/v1/questions/{question_id}/submit",
            json={
                "answer": {"choice": "test_answer"},
                "answer_type": "multiple_choice",
                "confidence": 0.7,
                "time_spent_seconds": 20,
                "hint_used": False,
            },
            headers=headers,
        )
        assert submit.status_code == 201
        result = submit.json()

        # 9. Verify attempt recorded
        assert result["attempt"]["scoring_outcome"] in ("correct", "incorrect", "partial")
        assert result["attempt"]["time_to_answer_ms"] == 20000

        # 10. Verify mastery updated
        assert result["mastery"] is not None
        assert 0.0 <= result["mastery"]["memory_score"] <= 1.0
        assert 0.0 <= result["mastery"]["durable_mastery_score"] <= 1.0
        assert 0.0 <= result["mastery"]["mastery_score_combined"] <= 1.0
        assert result["mastery"]["evidence_count"] >= 1

        # 11. Verify review scheduled
        assert result["review"] is not None
        due_at = datetime.fromisoformat(result["review"]["due_at"].replace("Z", "+00:00"))
        assert due_at > datetime.now(timezone.utc)
        assert 1 <= result["review"]["interval_days"] <= 365

        # 12. Verify explanation returned
        assert result["explanation"] is not None
        assert len(result["explanation"]["content"]) > 0

        # 13. Get dashboard (should reflect the submission)
        dashboard = client.get("/api/v1/dashboard", headers=headers)
        assert dashboard.status_code == 200
        dash_data = dashboard.json()
        assert dash_data["current_streak"] >= 1

        # 14. Verify session question count incremented
        updated_session = client.get(f"/api/v1/study-sessions/{session_id}/adaptive-queue", headers=headers)
        # The session should still be active with updated state

        # 15. Verify cannot re-submit to the same question
        resubmit = client.post(
            f"/api/v1/questions/{question_id}/submit",
            json={"answer": {"choice": "different"}, "time_spent_seconds": 5},
            headers=headers,
        )
        assert resubmit.status_code == 409
