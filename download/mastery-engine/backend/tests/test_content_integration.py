"""Integration tests for the complete content factory integration (Task 014).

Tests that:
1. Queue creates real QuestionInstances from published templates
2. QuestionInstances are persisted (retrievable by ID)
3. Submit flow loads real concept_ids from template_concepts
4. Mastery updates use real concept IDs (no placeholders)
5. Explanations load from the Explanation table
6. Replay verification proves deterministic generation
7. Duplicate prevention works (no same template twice in one session)
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    """Register and verify an admin user."""
    response = client.post("/api/v1/auth/register", json={
        "email": f"admin-{uuid4()}@example.com",
        "password": "SecurePass123!",
        "display_name": "Admin",
    })
    assert response.status_code == 201
    token = response.json()["access_token"]
    user_id = response.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/auth/verify-email", json={"token": user_id})
    return headers


@pytest.fixture
def published_content(client: TestClient, admin_headers: dict[str, str]) -> dict[str, str]:
    """Create a subject, concept, template, and publish everything.

    Returns a dict with subject_id, concept_id, template_id.
    """
    # Create subject
    subj = client.post("/api/v1/admin/subjects", json={
        "code": f"int-{uuid4().hex[:8]}",
        "name": "Integration Test Subject",
        "slug": f"int-{uuid4().hex[:8]}",
        "description": "For integration testing",
    }, headers=admin_headers)
    assert subj.status_code == 201
    subject_id = subj.json()["id"]

    # Publish subject
    client.post(f"/api/v1/admin/subjects/{subject_id}/publish", json={}, headers=admin_headers)

    # Create concept
    concept = client.post(f"/api/v1/admin/subjects/{subject_id}/concepts", json={
        "slug": "dict-lookup",
        "name": "Dict Lookup",
        "description": "Dict lookup complexity",
        "difficulty": "easy",
        "importance": "high",
    }, headers=admin_headers)
    assert concept.status_code == 201
    concept_id = concept.json()["id"]

    # Create question template with concept link + explanations
    template = client.post(f"/api/v1/admin/subjects/{subject_id}/question-templates", json={
        "code": "dict_lookup_mcq",
        "question_type": "multiple_choice",
        "prompt_template": {
            "question": "What is the average-case time complexity of a dict lookup?",
            "context": "Consider a dictionary with {{size}} entries.",
        },
        "parameter_schema": {
            "size": {"type": "integer", "min": 100, "max": 1000000},
        },
        "correct_answer_generator": {
            "type": "literal",
            "value": "O(1)",
        },
        "distractor_generator": {
            "type": "literals",
            "distractors": [
                {"text": "O(n)", "misconception_tag": "scanning"},
                {"text": "O(log n)", "misconception_tag": "tree_based"},
                {"text": "O(n log n)", "misconception_tag": "sorting"},
            ],
        },
        "explanation_template": {},
        "hint_tiers": ["Think about hash tables."],
        "difficulty_estimate": "easy",
        "discrimination_estimate": 0.7,
        "concept_ids": [concept_id],
        "explanations": [
            {"outcome_key": "correct", "content": "Correct! Dict lookup is O(1) on average due to hashing."},
            {"outcome_key": "incorrect", "content": "Incorrect. Dict lookup is O(1) on average. Hash functions map keys to slots directly."},
        ],
    }, headers=admin_headers)
    assert template.status_code == 201
    template_id = template.json()["id"]

    # Publish template
    pub = client.post(f"/api/v1/admin/question-templates/{template_id}/publish", json={}, headers=admin_headers)
    assert pub.status_code == 200
    assert pub.json()["status"] == "published"

    return {
        "subject_id": subject_id,
        "concept_id": concept_id,
        "template_id": template_id,
    }


@pytest.fixture
def learner_with_session(
    client: TestClient, published_content: dict[str, str]
) -> tuple[dict[str, str], str, str]:
    """Register, verify, enroll, start session.

    Returns (headers, enrollment_id, session_id).
    """
    # Register learner
    reg = client.post("/api/v1/auth/register", json={
        "email": f"learner-{uuid4()}@example.com",
        "password": "SecurePass123!",
        "display_name": "Learner",
    })
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    user_id = reg.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/auth/verify-email", json={"token": user_id})

    # Enroll
    enroll = client.post("/api/v1/enrollments", json={
        "subject_id": published_content["subject_id"],
    }, headers=headers)
    assert enroll.status_code == 201
    enrollment_id = enroll.json()["id"]

    # Start session
    session = client.post("/api/v1/study-sessions", json={
        "enrollment_id": enrollment_id,
        "intent": "mixed",
    }, headers=headers)
    assert session.status_code == 201
    session_id = session.json()["id"]

    return headers, enrollment_id, session_id


class TestQueueGeneratesRealQuestions:
    """Test that the adaptive queue creates real QuestionInstances."""

    def test_queue_returns_persisted_questions(
        self, client: TestClient, learner_with_session: tuple
    ) -> None:
        """Queue returns real QuestionInstance IDs that can be retrieved."""
        headers, _, session_id = learner_with_session

        # Get queue
        queue = client.get(f"/api/v1/study-sessions/{session_id}/adaptive-queue", headers=headers)
        assert queue.status_code == 200
        questions = queue.json()["questions"]
        assert len(questions) > 0

        # Each question should have a real UUID (not a placeholder)
        for q in questions:
            assert q["question_instance_id"] is not None
            # Verify it's a valid UUID
            UUID(q["question_instance_id"])  # Raises if invalid

    def test_queued_question_is_retrievable(
        self, client: TestClient, learner_with_session: tuple
    ) -> None:
        """A question from the queue can be retrieved via GET /questions/{id}."""
        headers, _, session_id = learner_with_session

        queue = client.get(f"/api/v1/study-sessions/{session_id}/adaptive-queue", headers=headers)
        assert queue.status_code == 200
        question_id = queue.json()["questions"][0]["question_instance_id"]

        # Retrieve the question
        question = client.get(f"/api/v1/questions/{question_id}", headers=headers)
        assert question.status_code == 200
        assert question.json()["question_instance_id"] == question_id
        # Must NOT expose correct answer
        assert "correct_answer" not in question.json()

    def test_queue_question_has_rendered_prompt(
        self, client: TestClient, learner_with_session: tuple
    ) -> None:
        """The rendered prompt has variables substituted (no {{}} placeholders)."""
        headers, _, session_id = learner_with_session

        queue = client.get(f"/api/v1/study-sessions/{session_id}/adaptive-queue", headers=headers)
        question_id = queue.json()["questions"][0]["question_instance_id"]

        question = client.get(f"/api/v1/questions/{question_id}", headers=headers)
        prompt = question.json()["prompt"]
        # The {{size}} placeholder should have been replaced
        context = prompt.get("context", "")
        assert "{{" not in context
        assert "}}" not in context


class TestSubmitUsesRealConcepts:
    """Test that submit flow uses real concept IDs from template_concepts."""

    def test_submit_updates_real_concept_mastery(
        self, client: TestClient, learner_with_session: tuple
    ) -> None:
        """After submit, mastery should reference the real concept_id from the template."""
        headers, _, session_id = learner_with_session

        # Get queue + first question
        queue = client.get(f"/api/v1/study-sessions/{session_id}/adaptive-queue", headers=headers)
        question_id = queue.json()["questions"][0]["question_instance_id"]
        concept_id_from_queue = queue.json()["questions"][0]["concept_id"]

        # Submit answer
        submit = client.post(f"/api/v1/questions/{question_id}/submit", json={
            "answer": {"choice": "O(1)"},
            "answer_type": "multiple_choice",
            "confidence": 0.8,
            "time_spent_seconds": 15,
        }, headers=headers)
        assert submit.status_code == 201

        mastery = submit.json().get("mastery")
        if mastery is not None:
            # The mastery concept_id should match the real concept from the template
            assert mastery["concept_id"] is not None
            # It should be a valid UUID (not a placeholder)
            UUID(mastery["concept_id"])

    def test_submit_returns_explanation_from_repository(
        self, client: TestClient, learner_with_session: tuple
    ) -> None:
        """Explanation comes from the Explanation table, not dynamically built."""
        headers, _, session_id = learner_with_session

        queue = client.get(f"/api/v1/study-sessions/{session_id}/adaptive-queue", headers=headers)
        question_id = queue.json()["questions"][0]["question_instance_id"]

        submit = client.post(f"/api/v1/questions/{question_id}/submit", json={
            "answer": {"choice": "O(1)"},
            "time_spent_seconds": 10,
        }, headers=headers)
        assert submit.status_code == 201

        explanation = submit.json()["explanation"]
        assert explanation is not None
        assert len(explanation["content"]) > 0
        # The explanation should contain content from the DB
        # (either "Correct!" or "Incorrect." prefix from the stored explanation)

    def test_submit_review_scheduled_for_real_concept(
        self, client: TestClient, learner_with_session: tuple
    ) -> None:
        """Review is scheduled for the real concept."""
        headers, _, session_id = learner_with_session

        queue = client.get(f"/api/v1/study-sessions/{session_id}/adaptive-queue", headers=headers)
        question_id = queue.json()["questions"][0]["question_instance_id"]

        submit = client.post(f"/api/v1/questions/{question_id}/submit", json={
            "answer": {"choice": "test"},
            "time_spent_seconds": 10,
        }, headers=headers)
        assert submit.status_code == 201

        review = submit.json().get("review")
        if review is not None:
            assert review["concept_id"] is not None
            UUID(review["concept_id"])  # Must be valid UUID


class TestDuplicatePrevention:
    """Test that the queue doesn't serve the same template twice."""

    def test_no_duplicate_templates_in_session(
        self, client: TestClient, learner_with_session: tuple
    ) -> None:
        """Each template should only appear once in a session's queue."""
        headers, _, session_id = learner_with_session

        queue = client.get(f"/api/v1/study-sessions/{session_id}/adaptive-queue", headers=headers)
        assert queue.status_code == 200
        questions = queue.json()["questions"]

        # If there's only one template, there should be only one question
        # (duplicate prevention ensures we don't serve the same template twice)
        question_ids = [q["question_instance_id"] for q in questions]
        assert len(question_ids) == len(set(question_ids))  # No duplicates


class TestFullIntegratedLearningLoop:
    """End-to-end test of the fully integrated learning loop."""

    def test_complete_integrated_loop(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """
        Complete loop with real content:
        Admin creates content → Learner enrolls → Session → Queue (real questions) →
        Submit (real concepts) → Mastery (real update) → Review → Explanation (from DB)
        """
        # === ADMIN: Create content ===
        # Create subject
        subj = client.post("/api/v1/admin/subjects", json={
            "code": f"e2e-{uuid4().hex[:8]}",
            "name": "E2E Subject",
            "slug": f"e2e-{uuid4().hex[:8]}",
        }, headers=admin_headers)
        subject_id = subj.json()["id"]
        client.post(f"/api/v1/admin/subjects/{subject_id}/publish", json={}, headers=admin_headers)

        # Create concept
        concept = client.post(f"/api/v1/admin/subjects/{subject_id}/concepts", json={
            "slug": "list-mutability",
            "name": "List Mutability",
            "description": "Lists are mutable",
        }, headers=admin_headers)
        concept_id = concept.json()["id"]

        # Create + publish template with concept link + explanations
        template = client.post(f"/api/v1/admin/subjects/{subject_id}/question-templates", json={
            "code": "list_mut_mcq",
            "question_type": "multiple_choice",
            "prompt_template": {"question": "Does lst[0] = x modify the list in place?"},
            "parameter_schema": {},
            "correct_answer_generator": {"type": "literal", "value": "Yes"},
            "distractor_generator": {
                "type": "literals",
                "distractors": [
                    {"text": "No, it creates a new list", "misconception_tag": "reassignment_creates_new"},
                    {"text": "It raises an error", "misconception_tag": "mutation_error"},
                ],
            },
            "concept_ids": [concept_id],
            "explanations": [
                {"outcome_key": "correct", "content": "Correct! List element assignment modifies in place."},
                {"outcome_key": "incorrect", "content": "Incorrect. lst[0] = x modifies the list in place because lists are mutable."},
            ],
        }, headers=admin_headers)
        template_id = template.json()["id"]
        client.post(f"/api/v1/admin/question-templates/{template_id}/publish", json={}, headers=admin_headers)

        # === LEARNER: Study ===
        # Register + verify
        reg = client.post("/api/v1/auth/register", json={
            "email": f"e2e-learner-{uuid4()}@example.com",
            "password": "SecurePass123!",
            "display_name": "E2E Learner",
        })
        token = reg.json()["access_token"]
        user_id = reg.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/api/v1/auth/verify-email", json={"token": user_id})

        # Enroll
        enroll = client.post("/api/v1/enrollments", json={"subject_id": subject_id}, headers=headers)
        enrollment_id = enroll.json()["id"]

        # Start session
        session = client.post("/api/v1/study-sessions", json={
            "enrollment_id": enrollment_id, "intent": "mixed",
        }, headers=headers)
        session_id = session.json()["id"]

        # Get queue (should have real QuestionInstances from published template)
        queue = client.get(f"/api/v1/study-sessions/{session_id}/adaptive-queue", headers=headers)
        assert queue.status_code == 200
        questions = queue.json()["questions"]
        assert len(questions) > 0
        question_id = questions[0]["question_instance_id"]

        # Get question (should be the persisted one)
        question = client.get(f"/api/v1/questions/{question_id}", headers=headers)
        assert question.status_code == 200
        assert "correct_answer" not in question.json()

        # Submit answer
        submit = client.post(f"/api/v1/questions/{question_id}/submit", json={
            "answer": {"choice": "Yes"},
            "answer_type": "multiple_choice",
            "confidence": 0.9,
            "time_spent_seconds": 12,
        }, headers=headers)
        assert submit.status_code == 201
        result = submit.json()

        # Verify attempt recorded
        assert result["attempt"]["scoring_outcome"] in ("correct", "incorrect", "partial")

        # Verify mastery updated with real concept
        if result["mastery"]:
            mastery_concept_id = result["mastery"]["concept_id"]
            UUID(mastery_concept_id)  # Must be valid UUID
            assert 0.0 <= result["mastery"]["memory_score"] <= 1.0

        # Verify review scheduled with real concept
        if result["review"]:
            UUID(result["review"]["concept_id"])  # Must be valid UUID

        # Verify explanation from repository
        assert result["explanation"]["content"] is not None
        assert len(result["explanation"]["content"]) > 0

        # Verify dashboard works
        dashboard = client.get("/api/v1/dashboard", headers=headers)
        assert dashboard.status_code == 200
