"""Attempt — the atomic unit of learning evidence. The data moat.

An Attempt is **append-only**: once created, it is never modified.
Corrections (e.g., a scoring bug discovered later) are made by appending
a compensating attempt, not by editing the original. This immutability
is the foundation of the project's competitive advantage — historical
evidence cannot be retroactively edited.

Every Attempt carries triple versioning references (content_version_id,
template_version_id, algorithm_version_id) for historical reproducibility
(ADR-0011).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.shared.ids import (
    AlgorithmVersionId,
    AnswerId,
    AttemptId,
    ContentVersionId,
    LearnerEnrollmentId,
    MisconceptionId,
    QuestionInstanceId,
    StudySessionId,
    TemplateVersionId,
)
from app.domain.shared.kernel import (
    AggregateRoot,
    AttemptIntent,
    InvariantViolation,
    ScoringOutcome,
)
from app.domain.shared.value_objects import Duration
from app.domain.assessment.answer import Answer
from app.domain.assessment.events import AttemptRecorded


class Attempt(AggregateRoot):
    """An atomic learning evidence record. Append-only by design.

    Invariants:
    - Immutable after creation (no methods modify state).
    - ``partial_credit`` is set only when ``scoring_outcome`` is ``PARTIAL``.
    - ``time_to_answer`` must be non-negative.
    - ``algorithm_version_id`` records the version under which the resulting
      mastery was computed (for triple versioning).
    - ``content_version_id`` and ``template_version_id`` record the versions
      under which the question was served.

    This aggregate has NO methods that modify state. It is created once
    via the ``record`` factory and never changed. This is intentional —
    the Attempt is the data moat, and its immutability is the guarantee
    that historical evidence is trustworthy.
    """

    def __init__(
        self,
        id: AttemptId,
        question_instance_id: QuestionInstanceId,
        learner_enrollment_id: LearnerEnrollmentId,
        study_session_id: StudySessionId,
        content_version_id: ContentVersionId,
        template_version_id: TemplateVersionId,
        algorithm_version_id: AlgorithmVersionId,
        scoring_outcome: ScoringOutcome,
        time_to_answer: Duration,
        hint_used: bool,
        hint_tiers_used: list[int],
        attempt_intent: AttemptIntent,
        answer: Answer | None = None,
        partial_credit: float | None = None,
        misconception_id: MisconceptionId | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.question_instance_id = question_instance_id
        self.learner_enrollment_id = learner_enrollment_id
        self.study_session_id = study_session_id
        self.content_version_id = content_version_id
        self.template_version_id = template_version_id
        self.algorithm_version_id = algorithm_version_id
        self.scoring_outcome = scoring_outcome
        self.time_to_answer = time_to_answer
        self.hint_used = hint_used
        self.hint_tiers_used = hint_tiers_used
        self.attempt_intent = attempt_intent
        self.answer = answer
        self.partial_credit = partial_credit
        self.misconception_id = misconception_id
        self.created_at = created_at or datetime.now(timezone.utc)

    # ============================================================
    # Factory
    # ============================================================

    @classmethod
    def record(
        cls,
        question_instance_id: QuestionInstanceId,
        learner_enrollment_id: LearnerEnrollmentId,
        study_session_id: StudySessionId,
        content_version_id: ContentVersionId,
        template_version_id: TemplateVersionId,
        algorithm_version_id: AlgorithmVersionId,
        scoring_outcome: ScoringOutcome,
        time_to_answer: Duration,
        hint_used: bool,
        hint_tiers_used: list[int],
        attempt_intent: AttemptIntent,
        answer: Answer | None = None,
        partial_credit: float | None = None,
        misconception_id: MisconceptionId | None = None,
        concept_ids: tuple[UUID, ...] = (),
    ) -> Attempt:
        """Record a new attempt. This is the only way to create an Attempt.

        Args:
            concept_ids: The concept IDs tested by this attempt's template.
                Used in the AttemptRecorded event for downstream consumers
                (mastery engine, analytics).
        """
        # Validate invariants
        if scoring_outcome == ScoringOutcome.PARTIAL and partial_credit is None:
            raise InvariantViolation(
                "Attempt",
                "partial_credit must be set when scoring_outcome is PARTIAL",
            )
        if scoring_outcome != ScoringOutcome.PARTIAL and partial_credit is not None:
            raise InvariantViolation(
                "Attempt",
                "partial_credit must be None when scoring_outcome is not PARTIAL",
            )
        if partial_credit is not None and not 0.0 <= partial_credit <= 1.0:
            raise InvariantViolation(
                "Attempt",
                f"partial_credit must be 0.0–1.0, got {partial_credit}",
            )
        if time_to_answer.seconds < 0:
            raise InvariantViolation("Attempt", "time_to_answer must be non-negative")

        attempt = cls(
            id=AttemptId.generate(),
            question_instance_id=question_instance_id,
            learner_enrollment_id=learner_enrollment_id,
            study_session_id=study_session_id,
            content_version_id=content_version_id,
            template_version_id=template_version_id,
            algorithm_version_id=algorithm_version_id,
            scoring_outcome=scoring_outcome,
            time_to_answer=time_to_answer,
            hint_used=hint_used,
            hint_tiers_used=hint_tiers_used,
            attempt_intent=attempt_intent,
            answer=answer,
            partial_credit=partial_credit,
            misconception_id=misconception_id,
        )

        # Attach answer to attempt if provided
        if answer is not None:
            answer = answer.attach_to_attempt(attempt.id)
            attempt.answer = answer

        # Record the domain event
        attempt._record_event(
            AttemptRecorded(
                attempt_id=attempt.id.value,
                learner_enrollment_id=learner_enrollment_id.value,
                concept_ids=concept_ids,
                scoring_outcome=scoring_outcome,
                content_version_id=content_version_id.value,
                template_version_id=template_version_id.value,
                algorithm_version_id=algorithm_version_id.value,
                hint_used=hint_used,
                attempt_intent=attempt_intent,
            )
        )

        return attempt

    # ============================================================
    # Queries (read-only — attempts are immutable)
    # ============================================================

    @property
    def is_correct(self) -> bool:
        return self.scoring_outcome == ScoringOutcome.CORRECT

    @property
    def is_incorrect(self) -> bool:
        return self.scoring_outcome == ScoringOutcome.INCORRECT

    @property
    def is_partial(self) -> bool:
        return self.scoring_outcome == ScoringOutcome.PARTIAL

    @property
    def is_review(self) -> bool:
        return self.attempt_intent == AttemptIntent.REVIEW

    @property
    def is_diagnostic(self) -> bool:
        return self.attempt_intent == AttemptIntent.DIAGNOSTIC

    @property
    def effective_credit(self) -> float:
        """The effective mastery credit from this attempt (1.0 for correct, 0.0 for incorrect, partial_credit for partial)."""
        if self.is_correct:
            return 1.0
        if self.is_incorrect:
            return 0.0
        return self.partial_credit or 0.0
