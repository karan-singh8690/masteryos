"""Integration tests for the Content System (Task 013).

Tests the complete content pipeline:
  Create Subject → Create Concept → Create Objective → Create Misconception →
  Create Question Template → Publish → QuestionFactory generates QuestionInstance →
  Verify determinism → Verify replay

Plus: Content admin CRUD, template versioning, concept mapping.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.domain.assessment.question_factory import QuestionFactory, TemplateVersionData
from app.domain.assessment.variable_generator import VariableGenerator
from app.domain.assessment.template_engine import TemplateEngine
from app.domain.shared.ids import (
    ContentVersionId,
    LearnerEnrollmentId,
    StudySessionId,
    TemplateVersionId,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    """Register and return auth headers for an admin user."""
    response = client.post("/api/v1/auth/register", json={
        "email": f"admin-{uuid4()}@example.com",
        "password": "SecurePass123!",
        "display_name": "Admin",
    })
    assert response.status_code == 201
    token = response.json()["access_token"]
    user_id = response.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    # Verify email
    client.post("/api/v1/auth/verify-email", json={"token": user_id})
    return headers


# ============================================================
# Content Admin CRUD Tests
# ============================================================


class TestContentAdmin:
    """Tests for the content administration API."""

    def test_create_subject(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        response = client.post("/api/v1/admin/subjects", json={
            "code": f"python-{uuid4().hex[:8]}",
            "name": "Python Interview Prep",
            "slug": f"python-{uuid4().hex[:8]}",
            "description": "Python technical interview preparation",
        }, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "draft"
        assert "id" in data

    def test_publish_subject(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        # Create
        create = client.post("/api/v1/admin/subjects", json={
            "code": f"pub-{uuid4().hex[:8]}",
            "name": "Publishable Subject",
            "slug": f"pub-{uuid4().hex[:8]}",
        }, headers=admin_headers)
        subject_id = create.json()["id"]

        # Publish
        response = client.post(f"/api/v1/admin/subjects/{subject_id}/publish", json={}, headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "published"

    def test_list_subjects(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        response = client.get("/api/v1/admin/subjects", headers=admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_concept(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        # Create subject first
        subj = client.post("/api/v1/admin/subjects", json={
            "code": f"c-{uuid4().hex[:8]}",
            "name": "Test",
            "slug": f"c-{uuid4().hex[:8]}",
        }, headers=admin_headers)
        subject_id = subj.json()["id"]

        # Create concept
        response = client.post(f"/api/v1/admin/subjects/{subject_id}/concepts", json={
            "slug": "list-mutability",
            "name": "List Mutability",
            "description": "Lists are mutable in Python",
            "difficulty": "easy",
            "importance": "high",
        }, headers=admin_headers)
        assert response.status_code == 201
        assert response.json()["name"] == "List Mutability"

    def test_create_objective(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        # Create subject + concept
        subj = client.post("/api/v1/admin/subjects", json={
            "code": f"o-{uuid4().hex[:8]}", "name": "T", "slug": f"o-{uuid4().hex[:8]}",
        }, headers=admin_headers)
        concept = client.post(f"/api/v1/admin/subjects/{subj.json()['id']}/concepts", json={
            "slug": "test", "name": "Test", "description": "Test concept",
        }, headers=admin_headers)

        # Create objective
        response = client.post(f"/api/v1/admin/concepts/{concept.json()['id']}/objectives", json={
            "statement": "The learner can identify when a list mutation aliases another reference",
        }, headers=admin_headers)
        assert response.status_code == 201
        assert "statement" in response.json()

    def test_create_misconception(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        subj = client.post("/api/v1/admin/subjects", json={
            "code": f"m-{uuid4().hex[:8]}", "name": "T", "slug": f"m-{uuid4().hex[:8]}",
        }, headers=admin_headers)
        concept = client.post(f"/api/v1/admin/subjects/{subj.json()['id']}/concepts", json={
            "slug": "test", "name": "Test", "description": "Test",
        }, headers=admin_headers)

        response = client.post(f"/api/v1/admin/concepts/{concept.json()['id']}/misconceptions", json={
            "name": "Reassignment creates new list",
            "description": "Thinking lst[0] = x creates a new list",
            "remediation": "Explain that lists are mutable and modified in place",
        }, headers=admin_headers)
        assert response.status_code == 201
        assert response.json()["name"] == "Reassignment creates new list"


# ============================================================
# Question Template Tests
# ============================================================


class TestQuestionTemplate:
    """Tests for creating and publishing question templates."""

    def test_create_template_with_concepts(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Create a template with concept links, explanations, and distractors."""
        # Setup: subject + concept
        subj = client.post("/api/v1/admin/subjects", json={
            "code": f"qt-{uuid4().hex[:8]}", "name": "T", "slug": f"qt-{uuid4().hex[:8]}",
        }, headers=admin_headers)
        subject_id = subj.json()["id"]

        concept = client.post(f"/api/v1/admin/subjects/{subject_id}/concepts", json={
            "slug": "dict-lookup", "name": "Dict Lookup", "description": "Dict lookup complexity",
        }, headers=admin_headers)
        concept_id = concept.json()["id"]

        # Create template
        response = client.post(f"/api/v1/admin/subjects/{subject_id}/question-templates", json={
            "code": "dict_lookup_mcq",
            "question_type": "multiple_choice",
            "prompt_template": {
                "question": "What is the average-case time complexity of a dict lookup in Python?",
                "context": "Consider a dictionary with {{size}} entries.",
            },
            "parameter_schema": {
                "size": {"type": "integer", "min": 100, "max": 1000000}
            },
            "correct_answer_generator": {
                "type": "literal",
                "value": "O(1)",
            },
            "distractor_generator": {
                "type": "literals",
                "distractors": [
                    {"text": "O(n)", "misconception_tag": "scanning_keys"},
                    {"text": "O(log n)", "misconception_tag": "tree_based"},
                    {"text": "O(n log n)", "misconception_tag": "sorting_based"},
                ],
            },
            "explanation_template": {"correct": "Correct! Dict lookup is O(1) on average."},
            "hint_tiers": ["Think about how dicts are implemented internally.", "Consider hash tables."],
            "difficulty_estimate": "easy",
            "discrimination_estimate": 0.7,
            "concept_ids": [concept_id],
            "explanations": [
                {"outcome_key": "correct", "content": "Correct! Dict lookup is O(1) on average due to hashing."},
                {"outcome_key": "incorrect", "content": "Incorrect. Dict lookup is O(1) on average. The hash function maps keys to slots directly."},
            ],
        }, headers=admin_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "dict_lookup_mcq"
        assert data["status"] == "draft"
        assert data["current_version_id"] is not None

    def test_publish_template(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Publish a template — makes it available for question generation."""
        subj = client.post("/api/v1/admin/subjects", json={
            "code": f"pub-{uuid4().hex[:8]}", "name": "T", "slug": f"pub-{uuid4().hex[:8]}",
        }, headers=admin_headers)
        template = client.post(f"/api/v1/admin/subjects/{subj.json()['id']}/question-templates", json={
            "code": "test_template",
            "prompt_template": {"question": "What is 2+2?"},
            "correct_answer_generator": {"type": "literal", "value": "4"},
        }, headers=admin_headers)

        response = client.post(
            f"/api/v1/admin/question-templates/{template.json()['id']}/publish",
            json={}, headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "published"

    def test_get_template_detail(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Get template detail including version and concept links."""
        subj = client.post("/api/v1/admin/subjects", json={
            "code": f"dt-{uuid4().hex[:8]}", "name": "T", "slug": f"dt-{uuid4().hex[:8]}",
        }, headers=admin_headers)
        concept = client.post(f"/api/v1/admin/subjects/{subj.json()['id']}/concepts", json={
            "slug": "test", "name": "Test", "description": "Test",
        }, headers=admin_headers)
        template = client.post(f"/api/v1/admin/subjects/{subj.json()['id']}/question-templates", json={
            "code": "detail_test",
            "prompt_template": {"question": "Test question?"},
            "correct_answer_generator": {"type": "literal", "value": "yes"},
            "concept_ids": [concept.json()["id"]],
        }, headers=admin_headers)

        response = client.get(
            f"/api/v1/admin/question-templates/{template.json()['id']}",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version_number"] == 1
        assert concept.json()["id"] in data["concept_ids"]


# ============================================================
# QuestionFactory Tests (pure domain service)
# ============================================================


class TestQuestionFactory:
    """Tests for the QuestionFactory — deterministic question generation."""

    def _make_template_version(self) -> TemplateVersionData:
        """Create a test TemplateVersionData."""
        return TemplateVersionData(
            id=uuid4(),
            template_id=uuid4(),
            version_number=1,
            parameter_schema={
                "size": {"type": "integer", "min": 100, "max": 1000000},
            },
            prompt_template={
                "question": "What is the average-case time complexity of a dict lookup?",
                "context": "Consider a dictionary with {{size}} entries.",
            },
            correct_answer_generator={
                "type": "literal",
                "value": "O(1)",
            },
            distractor_generator={
                "type": "literals",
                "distractors": [
                    {"text": "O(n)", "misconception_tag": "scanning"},
                    {"text": "O(log n)", "misconception_tag": "tree_based"},
                    {"text": "O(n log n)", "misconception_tag": "sorting"},
                ],
            },
            explanation_template={"correct": "Dict lookup is O(1) on average."},
            hint_tiers=["Think about hash tables."],
            difficulty_estimate="easy",
            discrimination_estimate=0.7,
            concept_ids=[uuid4()],
        )

    def test_generate_produces_question_instance(self) -> None:
        """The factory generates a QuestionInstance from a template + seed."""
        factory = QuestionFactory()
        tv = self._make_template_version()

        result = factory.generate(
            template_version=tv,
            seed=42,
            content_version_id=ContentVersionId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            study_session_id=StudySessionId.generate(),
        )

        assert result.question_instance is not None
        assert result.question_instance.status == "served"
        assert result.render_hash is not None
        assert len(result.concept_ids) == 1  # Real concept ID, not placeholder

    def test_deterministic_same_seed_same_output(self) -> None:
        """Same template + same seed → identical QuestionInstance."""
        factory = QuestionFactory()
        tv = self._make_template_version()

        result1 = factory.generate(
            template_version=tv, seed=42,
            content_version_id=ContentVersionId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            study_session_id=StudySessionId.generate(),
        )
        result2 = factory.generate(
            template_version=tv, seed=42,
            content_version_id=ContentVersionId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            study_session_id=StudySessionId.generate(),
        )

        # Render hashes must match (deterministic)
        assert result1.render_hash == result2.render_hash
        # Variables must match
        assert result1.variables == result2.variables
        # Prompts must match
        assert result1.question_instance.rendered_prompt == result2.question_instance.rendered_prompt
        # Correct answers must match
        assert result1.question_instance.correct_answer == result2.question_instance.correct_answer

    def test_different_seed_different_output(self) -> None:
        """Different seeds → different variables (but same template structure)."""
        factory = QuestionFactory()
        tv = self._make_template_version()

        result1 = factory.generate(
            template_version=tv, seed=42,
            content_version_id=ContentVersionId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            study_session_id=StudySessionId.generate(),
        )
        result2 = factory.generate(
            template_version=tv, seed=99,
            content_version_id=ContentVersionId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            study_session_id=StudySessionId.generate(),
        )

        # Variables differ
        assert result1.variables != result2.variables
        # Render hashes differ
        assert result1.render_hash != result2.render_hash
        # But the correct answer is the same (literal "O(1)")
        assert result1.question_instance.correct_answer == result2.question_instance.correct_answer

    def test_replay_reconstructs_identical_question(self) -> None:
        """Replay with same template + seed → identical question."""
        factory = QuestionFactory()
        tv = self._make_template_version()

        original = factory.generate(
            template_version=tv, seed=123,
            content_version_id=ContentVersionId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            study_session_id=StudySessionId.generate(),
        )
        replayed = factory.replay(
            template_version=tv, seed=123,
            content_version_id=ContentVersionId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            study_session_id=StudySessionId.generate(),
        )

        assert original.render_hash == replayed.render_hash
        assert original.variables == replayed.variables
        assert original.question_instance.rendered_prompt == replayed.question_instance.rendered_prompt
        assert original.question_instance.correct_answer == replayed.question_instance.correct_answer

    def test_prompt_renders_variables(self) -> None:
        """The rendered prompt has variables substituted."""
        factory = QuestionFactory()
        tv = self._make_template_version()

        result = factory.generate(
            template_version=tv, seed=42,
            content_version_id=ContentVersionId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            study_session_id=StudySessionId.generate(),
        )

        prompt = result.question_instance.rendered_prompt
        # The {{size}} placeholder should be replaced with an actual number
        assert "{{size}}" not in prompt.get("context", "")
        assert str(result.variables["size"]) in prompt.get("context", "")

    def test_distractors_generated(self) -> None:
        """Multiple-choice questions have generated distractors."""
        factory = QuestionFactory()
        tv = self._make_template_version()

        result = factory.generate(
            template_version=tv, seed=42,
            content_version_id=ContentVersionId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            study_session_id=StudySessionId.generate(),
        )

        assert result.question_instance.rendered_choices is not None
        assert len(result.question_instance.rendered_choices) == 4  # 1 correct + 3 distractors
        assert result.question_instance.distractors_with_tags is not None
        assert len(result.question_instance.distractors_with_tags) == 4

    def test_concept_ids_are_real(self) -> None:
        """Concept IDs come from the template, not placeholder UUIDs."""
        factory = QuestionFactory()
        real_concept_id = uuid4()
        tv = TemplateVersionData(
            id=uuid4(), template_id=uuid4(), version_number=1,
            parameter_schema={}, prompt_template={"q": "Test?"},
            correct_answer_generator={"type": "literal", "value": "yes"},
            distractor_generator=None, explanation_template={}, hint_tiers=[],
            difficulty_estimate="medium", discrimination_estimate=0.5,
            concept_ids=[real_concept_id],
        )

        result = factory.generate(
            template_version=tv, seed=1,
            content_version_id=ContentVersionId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            study_session_id=StudySessionId.generate(),
        )

        assert result.concept_ids == [real_concept_id]
        assert real_concept_id in result.concept_ids


# ============================================================
# Variable Generator Tests
# ============================================================


class TestVariableGenerator:
    """Tests for deterministic variable generation."""

    def test_same_seed_same_values(self) -> None:
        gen1 = VariableGenerator(seed=42)
        gen2 = VariableGenerator(seed=42)

        gen1.integer("x", 1, 100)
        gen2.integer("x", 1, 100)

        assert gen1.values["x"] == gen2.values["x"]

    def test_different_seed_different_values(self) -> None:
        gen1 = VariableGenerator(seed=42)
        gen2 = VariableGenerator(seed=99)

        gen1.integer("x", 1, 100)
        gen2.integer("x", 1, 100)

        assert gen1.values["x"] != gen2.values["x"]

    def test_generate_from_schema(self) -> None:
        gen = VariableGenerator(seed=42)
        result = gen.generate_from_schema({
            "x": {"type": "integer", "min": 1, "max": 10},
            "name": {"type": "variable_name"},
            "flag": {"type": "boolean"},
            "my_list": {"type": "list", "size": 3, "element_type": "int", "min": 0, "max": 5},
        })

        assert "x" in result.values
        assert 1 <= result.values["x"] <= 10
        assert isinstance(result.values["name"], str)
        assert isinstance(result.values["flag"], bool)
        assert len(result.values["my_list"]) == 3

    def test_list_generation_deterministic(self) -> None:
        gen1 = VariableGenerator(seed=42)
        gen2 = VariableGenerator(seed=42)

        gen1.list("lst", size=5, element_type="int", min_val=0, max_val=100)
        gen2.list("lst", size=5, element_type="int", min_val=0, max_val=100)

        assert gen1.values["lst"] == gen2.values["lst"]


# ============================================================
# Template Engine Tests
# ============================================================


class TestTemplateEngine:
    """Tests for deterministic template rendering."""

    def test_render_simple_placeholder(self) -> None:
        engine = TemplateEngine()
        result = engine.render("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_render_multiple_placeholders(self) -> None:
        engine = TemplateEngine()
        result = engine.render("{{x}} + {{y}} = {{z}}", {"x": 1, "y": 2, "z": 3})
        assert result == "1 + 2 = 3"

    def test_render_dict(self) -> None:
        engine = TemplateEngine()
        result = engine.render_dict(
            {"question": "What is {{x}}?", "answer": "{{x}}"},
            {"x": 42},
        )
        assert result["question"] == "What is 42?"
        assert result["answer"] == "42"

    def test_render_if_block_true(self) -> None:
        engine = TemplateEngine()
        result = engine.render("{{#if flag}}shown{{/if}}", {"flag": True})
        assert result == "shown"

    def test_render_if_block_false(self) -> None:
        engine = TemplateEngine()
        result = engine.render("{{#if flag}}shown{{/if}}", {"flag": False})
        assert result == ""

    def test_render_each_block(self) -> None:
        engine = TemplateEngine()
        result = engine.render("{{#each items}}{{item}},{{/each}}", {"items": [1, 2, 3]})
        assert result == "1,2,3,"

    def test_unresolvable_placeholder_left_as_is(self) -> None:
        engine = TemplateEngine()
        result = engine.render("Hello {{unknown}}!", {})
        assert result == "Hello {{unknown}}!"

    def test_deterministic_rendering(self) -> None:
        """Same template + same variables → same output."""
        engine = TemplateEngine()
        template = "What is the time complexity of {{operation}} on a {{structure}}?"
        variables = {"operation": "lookup", "structure": "dict"}

        result1 = engine.render(template, variables)
        result2 = engine.render(template, variables)

        assert result1 == result2
