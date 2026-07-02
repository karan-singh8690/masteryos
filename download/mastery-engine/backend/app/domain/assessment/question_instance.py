"""QuestionInstance — a concrete, instantiated question served to a learner.

A QuestionInstance is produced by the QuestionFactory from a QuestionTemplate,
a parameter seed, and a ContentVersion. It is immutable once served; if a
template is edited after a question was served, the served question is
preserved verbatim for replay (ADR-0011, triple versioning).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.shared.ids import (
    ContentVersionId,
    LearnerEnrollmentId,
    QuestionInstanceId,
    StudySessionId,
    TemplateVersionId,
)
from app.domain.shared.kernel import (
    AggregateRoot,
    DomainEvent,
    InvalidStateTransition,
    InvariantViolation,
)
from app.domain.assessment.events import (
    QuestionInstanceAbandoned,
    QuestionInstanceAnswered,
    QuestionInstanceServed,
)
from app.domain.assessment.exceptions import (
    QuestionAlreadyAnswered,
    QuestionInstanceNotServed,
)


class QuestionInstanceStatus:
    """Status of a question instance (not an enum — simple string constants)."""

    SERVED = "served"
    ANSWERED = "answered"
    ABANDONED = "abandoned"


class QuestionInstance(AggregateRoot):
    """A concrete question served to a learner.

    Aggregate root — the unit of assessment. Once served, the instance is
    immutable. It can transition to ``answered`` (via an attempt) or
    ``abandoned`` (via timeout or explicit abandonment), but the rendered
    prompt, choices, and correct answer never change.

    Invariants:
    - Cannot answer an already-answered instance.
    - Cannot abandon an answered instance.
    - ``answered_at`` is set only when status is ``answered``.
    """

    def __init__(
        self,
        id: QuestionInstanceId,
        template_version_id: TemplateVersionId,
        content_version_id: ContentVersionId,
        learner_enrollment_id: LearnerEnrollmentId,
        study_session_id: StudySessionId,
        parameter_seed: int,
        parameter_values: dict[str, Any],
        rendered_prompt: dict[str, Any],
        correct_answer: dict[str, Any],
        rendered_choices: list[dict[str, Any]] | None = None,
        distractors_with_tags: list[dict[str, Any]] | None = None,
        served_at: datetime | None = None,
        answered_at: datetime | None = None,
        status: str = QuestionInstanceStatus.SERVED,
    ) -> None:
        super().__init__()
        self.id = id
        self.template_version_id = template_version_id
        self.content_version_id = content_version_id
        self.learner_enrollment_id = learner_enrollment_id
        self.study_session_id = study_session_id
        self.parameter_seed = parameter_seed
        self.parameter_values = parameter_values
        self.rendered_prompt = rendered_prompt
        self.correct_answer = correct_answer
        self.rendered_choices = rendered_choices
        self.distractors_with_tags = distractors_with_tags
        self.served_at = served_at or datetime.now(timezone.utc)
        self.answered_at = answered_at
        self.status = status

    # ============================================================
    # Factory
    # ============================================================

    @classmethod
    def serve(
        cls,
        template_version_id: TemplateVersionId,
        content_version_id: ContentVersionId,
        learner_enrollment_id: LearnerEnrollmentId,
        study_session_id: StudySessionId,
        parameter_seed: int,
        parameter_values: dict[str, Any],
        rendered_prompt: dict[str, Any],
        correct_answer: dict[str, Any],
        rendered_choices: list[dict[str, Any]] | None = None,
        distractors_with_tags: list[dict[str, Any]] | None = None,
    ) -> QuestionInstance:
        """Create and serve a new question instance to a learner."""
        instance = cls(
            id=QuestionInstanceId.generate(),
            template_version_id=template_version_id,
            content_version_id=content_version_id,
            learner_enrollment_id=learner_enrollment_id,
            study_session_id=study_session_id,
            parameter_seed=parameter_seed,
            parameter_values=parameter_values,
            rendered_prompt=rendered_prompt,
            correct_answer=correct_answer,
            rendered_choices=rendered_choices,
            distractors_with_tags=distractors_with_tags,
        )
        instance._record_event(
            QuestionInstanceServed(
                instance_id=instance.id.value,
                learner_enrollment_id=learner_enrollment_id.value,
                template_version_id=template_version_id.value,
            )
        )
        return instance

    # ============================================================
    # State Transitions
    # ============================================================

    def mark_answered(self, attempt_id: UUID) -> None:
        """Mark this instance as answered by an attempt.

        Raises:
            QuestionAlreadyAnswered: if already answered.
        """
        if self.status == QuestionInstanceStatus.ANSWERED:
            raise QuestionAlreadyAnswered(self.id)
        if self.status == QuestionInstanceStatus.ABANDONED:
            raise InvalidStateTransition(
                "QuestionInstance", self.status, "mark_answered"
            )
        self.status = QuestionInstanceStatus.ANSWERED
        self.answered_at = datetime.now(timezone.utc)
        self._record_event(
            QuestionInstanceAnswered(
                instance_id=self.id.value,
                attempt_id=attempt_id,
                scoring_outcome=__import__(
                    "app.domain.shared.kernel", fromlist=["ScoringOutcome"]
                ).ScoringOutcome.CORRECT,  # placeholder; real outcome set by attempt
            )
        )

    def abandon(self) -> None:
        """Mark this instance as abandoned (no attempt recorded).

        Raises:
            InvalidStateTransition: if already answered or abandoned.
        """
        if self.status == QuestionInstanceStatus.ANSWERED:
            raise InvalidStateTransition(
                "QuestionInstance", self.status, "abandon"
            )
        if self.status == QuestionInstanceStatus.ABANDONED:
            return  # idempotent
        self.status = QuestionInstanceStatus.ABANDONED
        self._record_event(
            QuestionInstanceAbandoned(instance_id=self.id.value)
        )

    # ============================================================
    # Queries
    # ============================================================

    @property
    def is_answered(self) -> bool:
        return self.status == QuestionInstanceStatus.ANSWERED

    @property
    def is_abandoned(self) -> bool:
        return self.status == QuestionInstanceStatus.ABANDONED

    @property
    def is_served(self) -> bool:
        return self.status == QuestionInstanceStatus.SERVED

    @property
    def time_since_served(self) -> float:
        """Seconds since this instance was served."""
        return (datetime.now(timezone.utc) - self.served_at).total_seconds()
