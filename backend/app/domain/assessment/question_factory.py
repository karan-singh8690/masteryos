"""QuestionFactory — generates deterministic QuestionInstances from QuestionTemplates.

The factory is the bridge between content (QuestionTemplate + TemplateVersion)
and assessment (QuestionInstance). It:

1. Takes a TemplateVersion (the immutable specification).
2. Takes a seed (for deterministic variable generation).
3. Generates variables using VariableGenerator.
4. Renders the prompt using TemplateEngine.
5. Computes the correct answer.
6. Generates distractors.
7. Builds the explanation reference.
8. Returns a QuestionInstance (immutable, replayable).

Same TemplateVersion + same seed → identical QuestionInstance (invariant I3).

This factory is a pure domain service — no I/O, no database calls.
The application layer loads the TemplateVersion from the database,
passes it to the factory, and persists the resulting QuestionInstance.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.domain.assessment.question_instance import QuestionInstance
from app.domain.assessment.template_engine import TemplateEngine
from app.domain.assessment.variable_generator import GeneratedVariables, VariableGenerator
from app.domain.shared.ids import (
    ContentVersionId,
    LearnerEnrollmentId,
    QuestionInstanceId,
    StudySessionId,
    TemplateVersionId,
)
from app.domain.shared.kernel import Difficulty


@dataclass(frozen=True)
class TemplateVersionData:
    """Data transfer object for a TemplateVersion.

    The application layer loads this from the database and passes it
    to the factory. The factory never touches the ORM.
    """

    id: UUID
    template_id: UUID
    version_number: int
    parameter_schema: dict[str, Any]
    prompt_template: dict[str, Any]
    correct_answer_generator: dict[str, Any]
    distractor_generator: dict[str, Any] | None
    explanation_template: dict[str, Any]
    hint_tiers: list[str]
    difficulty_estimate: str
    discrimination_estimate: float
    concept_ids: list[UUID]


@dataclass(frozen=True)
class GeneratedQuestion:
    """The result of generating a question from a template + seed."""

    question_instance: QuestionInstance
    variables: dict[str, Any]
    render_hash: str
    concept_ids: list[UUID]


class QuestionFactory:
    """Generates QuestionInstances from TemplateVersions + seeds.

    Pure domain service — no I/O, no database calls.
    Same TemplateVersion + same seed → identical QuestionInstance.

    Usage (from the application layer):
        factory = QuestionFactory()
        result = factory.generate(
            template_version=loaded_from_db,
            seed=42,
            content_version_id=...,
            learner_enrollment_id=...,
            study_session_id=...,
        )
        # result.question_instance is a ready-to-serve QuestionInstance
        # result.variables contains the generated variables (for logging/analytics)
        # result.render_hash enables replay verification
        # result.concept_ids are the real concept IDs (no more placeholders!)
    """

    def __init__(self) -> None:
        self._template_engine = TemplateEngine()

    def generate(
        self,
        template_version: TemplateVersionData,
        seed: int,
        content_version_id: ContentVersionId,
        learner_enrollment_id: LearnerEnrollmentId,
        study_session_id: StudySessionId,
    ) -> GeneratedQuestion:
        """Generate a QuestionInstance from a TemplateVersion + seed.

        This is the core method that replaces ALL placeholder UUIDs:
        - Real concept_ids come from template_version.concept_ids
        - Real prompt comes from rendering template_version.prompt_template
        - Real correct_answer comes from template_version.correct_answer_generator
        - Real distractors come from template_version.distractor_generator
        - Real explanation reference comes from template_version.explanation_template

        The result is fully deterministic: same template + same seed → same question.
        """
        # 1. Generate variables from the parameter schema
        generator = VariableGenerator(seed=seed)
        variables = generator.generate_from_schema(template_version.parameter_schema)

        # 2. Render the prompt using the template engine
        rendered_prompt = self._template_engine.render_dict(
            template_version.prompt_template,
            variables.values,
        )

        # 3. Compute the correct answer
        correct_answer = self._compute_correct_answer(
            template_version.correct_answer_generator,
            variables,
        )

        # 4. Generate distractors (if multiple_choice)
        rendered_choices: list[dict[str, Any]] | None = None
        distractors_with_tags: list[dict[str, Any]] | None = None
        if template_version.distractor_generator is not None:
            rendered_choices, distractors_with_tags = self._generate_distractors(
                template_version.distractor_generator,
                correct_answer,
                variables,
                seed,
            )

        # 5. Compute render hash (for replay verification)
        render_hash = self._compute_render_hash(
            template_version.id,
            seed,
            variables.values,
            rendered_prompt,
            correct_answer,
        )

        # 6. Create the QuestionInstance (immutable, replayable)
        instance = QuestionInstance.serve(
            template_version_id=TemplateVersionId(template_version.id),
            content_version_id=content_version_id,
            learner_enrollment_id=learner_enrollment_id,
            study_session_id=study_session_id,
            parameter_seed=seed,
            parameter_values=variables.values,
            rendered_prompt=rendered_prompt,
            correct_answer=correct_answer,
            rendered_choices=rendered_choices,
            distractors_with_tags=distractors_with_tags,
        )

        return GeneratedQuestion(
            question_instance=instance,
            variables=variables.values,
            render_hash=render_hash,
            concept_ids=template_version.concept_ids,
        )

    def replay(
        self,
        template_version: TemplateVersionData,
        seed: int,
        content_version_id: ContentVersionId,
        learner_enrollment_id: LearnerEnrollmentId,
        study_session_id: StudySessionId,
    ) -> GeneratedQuestion:
        """Replay a question generation — must produce identical output.

        This is the same as generate(); it exists as a separate method
        to make replay intent explicit in the codebase.
        """
        return self.generate(
            template_version=template_version,
            seed=seed,
            content_version_id=content_version_id,
            learner_enrollment_id=learner_enrollment_id,
            study_session_id=study_session_id,
        )

    # ============================================================
    # Internal computation (pure functions)
    # ============================================================

    def _compute_correct_answer(
        self,
        generator_spec: dict[str, Any],
        variables: GeneratedVariables,
    ) -> dict[str, Any]:
        """Compute the correct answer from the generator spec + variables.

        The generator_spec defines how to compute the answer:
        - {"type": "literal", "value": "O(1)"} — static answer
        - {"type": "variable", "name": "correct_choice"} — from generated variables
        - {"type": "expression", "expression": "{{x}} + {{y}}"} — rendered expression
        """
        gen_type = generator_spec.get("type", "literal")

        if gen_type == "literal":
            return {"answer": generator_spec.get("value", "")}

        if gen_type == "variable":
            var_name = generator_spec.get("name", "answer")
            value = variables.get(var_name)
            return {"answer": str(value) if value is not None else ""}

        if gen_type == "expression":
            expr = generator_spec.get("expression", "")
            rendered = self._template_engine.render(expr, variables.values)
            return {"answer": rendered}

        if gen_type == "choice_index":
            # For multiple choice: the correct answer is the index of the right option
            choices = generator_spec.get("choices", [])
            correct_index = generator_spec.get("correct_index", 0)
            if 0 <= correct_index < len(choices):
                rendered_choices = [
                    self._template_engine.render(c, variables.values) for c in choices
                ]
                return {
                    "answer": rendered_choices[correct_index],
                    "choices": rendered_choices,
                    "correct_index": correct_index,
                }

        # Default: return the spec as-is
        return {"answer": str(generator_spec)}

    def _generate_distractors(
        self,
        generator_spec: dict[str, Any],
        correct_answer: dict[str, Any],
        variables: GeneratedVariables,
        seed: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Generate distractor choices for multiple-choice questions.

        Returns:
            (rendered_choices, distractors_with_tags)
            - rendered_choices: the choices to show the learner (shuffled)
            - distractors_with_tags: each distractor with its misconception tag
        """
        distractor_type = generator_spec.get("type", "literal")

        if distractor_type in ("literals", "literal"):
            # Static distractors with optional misconception tags.
            # Supports both "distractors" key (list of strings/dicts) and
            # "items" key (same format, used by some seed scripts).
            raw_distractors = generator_spec.get("distractors") or generator_spec.get("items") or []
            rendered: list[dict[str, Any]] = []

            for d in raw_distractors:
                if isinstance(d, dict):
                    text = self._template_engine.render(d.get("text", ""), variables.values)
                    tag = d.get("misconception_tag", "none")
                    rendered.append({"text": text, "tag": tag})
                else:
                    text = self._template_engine.render(str(d), variables.values)
                    rendered.append({"text": text, "tag": "none"})

            # Build the full choice list (correct + distractors)
            correct_text = correct_answer.get("answer", "")
            choices: list[dict[str, Any]] = [
                {"id": "correct", "text": correct_text, "is_correct": True},
            ]
            for i, d in enumerate(rendered):
                choices.append({
                    "id": f"distractor_{i}",
                    "text": d["text"],
                    "is_correct": False,
                    "misconception_tag": d["tag"],
                })

            # Shuffle deterministically based on seed
            import random
            rng = random.Random(seed)
            rng.shuffle(choices)

            # Assign letter labels (A, B, C, D...)
            labeled_choices = []
            tags = []
            for i, choice in enumerate(choices):
                label = chr(65 + i)  # A, B, C, D...
                labeled_choices.append({"id": label, "text": choice["text"]})
                tags.append({
                    "choice_id": label,
                    "is_correct": choice.get("is_correct", False),
                    "misconception_tag": choice.get("misconception_tag", "none"),
                })

            return labeled_choices, tags

        # Default: no distractors
        return [], []

    @staticmethod
    def _compute_render_hash(
        template_version_id: UUID,
        seed: int,
        variables: dict[str, Any],
        rendered_prompt: dict[str, Any],
        correct_answer: dict[str, Any],
    ) -> str:
        """Compute a SHA-256 hash of the rendered question for replay verification.

        If two QuestionInstances have the same render_hash, they are identical.
        """
        hash_input = json.dumps({
            "template_version_id": str(template_version_id),
            "seed": seed,
            "variables": variables,
            "rendered_prompt": rendered_prompt,
            "correct_answer": correct_answer,
        }, sort_keys=True, default=str)
        return hashlib.sha256(hash_input.encode()).hexdigest()
