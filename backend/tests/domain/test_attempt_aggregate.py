"""Tests for the Attempt aggregate (Assessment context)."""

from __future__ import annotations

import pytest
from uuid import uuid4

from app.domain.assessment.attempt import Attempt
from app.domain.assessment.events import AttemptRecorded
from app.domain.shared.ids import (
    AlgorithmVersionId,
    AttemptId,
    ContentVersionId,
    LearnerEnrollmentId,
    MisconceptionId,
    QuestionInstanceId,
    StudySessionId,
    TemplateVersionId,
)
from app.domain.shared.kernel import (
    AttemptIntent,
    InvariantViolation,
    ScoringOutcome,
)
from app.domain.shared.value_objects import Duration


class TestAttemptRecord:
    """Tests for Attempt.record() factory."""

    def test_record_creates_attempt_with_correct_fields(self) -> None:
        attempt = self._make_attempt(outcome=ScoringOutcome.CORRECT)
        assert attempt.scoring_outcome == ScoringOutcome.CORRECT
        assert attempt.hint_used is False
        assert attempt.attempt_intent == AttemptIntent.PRACTICE
        assert attempt.partial_credit is None
        assert attempt.created_at is not None

    def test_record_generates_attempt_id(self) -> None:
        attempt = self._make_attempt()
        assert isinstance(attempt.id, AttemptId)
        assert attempt.id.value is not None

    def test_record_for_correct_outcome_has_no_partial_credit(self) -> None:
        attempt = self._make_attempt(outcome=ScoringOutcome.CORRECT)
        assert attempt.partial_credit is None

    def test_record_for_incorrect_outcome_has_no_partial_credit(self) -> None:
        attempt = self._make_attempt(outcome=ScoringOutcome.INCORRECT)
        assert attempt.partial_credit is None

    def test_record_for_partial_requires_partial_credit(self) -> None:
        with pytest.raises(InvariantViolation, match="partial_credit must be set"):
            self._make_attempt(outcome=ScoringOutcome.PARTIAL, partial_credit=None)

    def test_record_for_partial_with_credit(self) -> None:
        attempt = self._make_attempt(
            outcome=ScoringOutcome.PARTIAL, partial_credit=0.6
        )
        assert attempt.partial_credit == 0.6

    def test_record_for_non_partial_with_credit_raises(self) -> None:
        with pytest.raises(InvariantViolation, match="partial_credit must be None"):
            self._make_attempt(
                outcome=ScoringOutcome.CORRECT, partial_credit=0.5
            )

    def test_partial_credit_must_be_in_range(self) -> None:
        with pytest.raises(InvariantViolation, match="0.0"):
            self._make_attempt(
                outcome=ScoringOutcome.PARTIAL, partial_credit=1.5
            )

    def test_negative_time_to_answer_raises(self) -> None:
        with pytest.raises(InvariantViolation, match="non-negative"):
            Attempt.record(
                question_instance_id=QuestionInstanceId.generate(),
                learner_enrollment_id=LearnerEnrollmentId.generate(),
                study_session_id=StudySessionId.generate(),
                content_version_id=ContentVersionId.generate(),
                template_version_id=TemplateVersionId.generate(),
                algorithm_version_id=AlgorithmVersionId.generate(),
                scoring_outcome=ScoringOutcome.CORRECT,
                time_to_answer=Duration(-1),
                hint_used=False,
                hint_tiers_used=[],
                attempt_intent=AttemptIntent.PRACTICE,
            )

    def test_triple_versioning_fields_are_set(self) -> None:
        cv_id = ContentVersionId.generate()
        tv_id = TemplateVersionId.generate()
        av_id = AlgorithmVersionId.generate()

        attempt = self._make_attempt(
            content_version_id=cv_id,
            template_version_id=tv_id,
            algorithm_version_id=av_id,
        )

        assert attempt.content_version_id == cv_id
        assert attempt.template_version_id == tv_id
        assert attempt.algorithm_version_id == av_id

    def test_attempt_records_domain_event(self) -> None:
        concept_id = uuid4()
        attempt = self._make_attempt(concept_ids=(concept_id,))

        events = attempt.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], AttemptRecorded)
        assert events[0].scoring_outcome == ScoringOutcome.CORRECT
        assert concept_id in events[0].concept_ids


class TestAttemptImmutability:
    """Tests that attempts are immutable (append-only by design)."""

    def test_attempt_has_no_modification_methods(self) -> None:
        """The Attempt class should have no methods that modify state."""
        attempt = self._make_attempt()
        # The only methods should be queries (is_correct, is_incorrect, etc.)
        # and collect_events (from AggregateRoot)
        public_methods = [
            m for m in dir(attempt)
            if not m.startswith("_") and callable(getattr(attempt, m))
        ]
        # Should NOT have update/save/modify/edit methods
        for method in public_methods:
            assert not method.startswith("update"), f"Found mutation method: {method}"
            assert not method.startswith("modify"), f"Found mutation method: {method}"
            assert method not in ("save", "edit", "change", "set_outcome")


class TestAttemptQueries:
    """Tests for Attempt query properties."""

    def test_is_correct(self) -> None:
        assert self._make_attempt(outcome=ScoringOutcome.CORRECT).is_correct

    def test_is_incorrect(self) -> None:
        assert self._make_attempt(outcome=ScoringOutcome.INCORRECT).is_incorrect

    def test_is_partial(self) -> None:
        assert self._make_attempt(
            outcome=ScoringOutcome.PARTIAL, partial_credit=0.5
        ).is_partial

    def test_effective_credit_correct(self) -> None:
        assert self._make_attempt(outcome=ScoringOutcome.CORRECT).effective_credit == 1.0

    def test_effective_credit_incorrect(self) -> None:
        assert self._make_attempt(outcome=ScoringOutcome.INCORRECT).effective_credit == 0.0

    def test_effective_credit_partial(self) -> None:
        attempt = self._make_attempt(
            outcome=ScoringOutcome.PARTIAL, partial_credit=0.7
        )
        assert attempt.effective_credit == 0.7

    def test_is_review(self) -> None:
        attempt = self._make_attempt(intent=AttemptIntent.REVIEW)
        assert attempt.is_review

    def test_is_diagnostic(self) -> None:
        attempt = self._make_attempt(intent=AttemptIntent.DIAGNOSTIC)
        assert attempt.is_diagnostic

    @staticmethod
    def _make_attempt(
        outcome: ScoringOutcome = ScoringOutcome.CORRECT,
        partial_credit: float | None = None,
        hint_used: bool = False,
        intent: AttemptIntent = AttemptIntent.PRACTICE,
        content_version_id: ContentVersionId | None = None,
        template_version_id: TemplateVersionId | None = None,
        algorithm_version_id: AlgorithmVersionId | None = None,
        concept_ids: tuple = (),
    ) -> Attempt:
        return Attempt.record(
            question_instance_id=QuestionInstanceId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            study_session_id=StudySessionId.generate(),
            content_version_id=content_version_id or ContentVersionId.generate(),
            template_version_id=template_version_id or TemplateVersionId.generate(),
            algorithm_version_id=algorithm_version_id or AlgorithmVersionId.generate(),
            scoring_outcome=outcome,
            time_to_answer=Duration(15000),
            hint_used=hint_used,
            hint_tiers_used=[1] if hint_used else [],
            attempt_intent=intent,
            partial_credit=partial_credit,
            concept_ids=concept_ids,
        )
