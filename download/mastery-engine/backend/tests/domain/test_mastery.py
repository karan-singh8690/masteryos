"""Tests for the MasteryScore aggregate and MasteryCalculator domain service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from uuid import uuid4

from app.domain.assessment.attempt import Attempt
from app.domain.mastery.algorithm_version import AlgorithmVersion
from app.domain.mastery.mastery_calculator import MasteryCalculator
from app.domain.mastery.mastery_score import MasteryScore
from app.domain.mastery.events import (
    ConceptStateChanged,
    MasteryUpdated,
    WeakConceptDetected,
)
from app.domain.shared.ids import (
    AlgorithmVersionId,
    ConceptId,
    LearnerEnrollmentId,
    MasteryScoreId,
    QuestionInstanceId,
    StudySessionId,
    ContentVersionId,
    TemplateVersionId,
)
from app.domain.shared.kernel import (
    ConceptState,
    ScoringOutcome,
    AttemptIntent,
    VersionNumber,
    WeaknessSeverity,
)
from app.domain.shared.value_objects import Duration, ReviewInterval


class TestMasteryScoreInitialization:
    """Tests for MasteryScore.initialize()."""

    def test_initialize_creates_unseen_concept(self) -> None:
        enrollment_id = LearnerEnrollmentId.generate()
        concept_id = ConceptId.generate()
        algo_id = AlgorithmVersionId.generate()

        score = MasteryScore.initialize(enrollment_id, concept_id, algo_id)

        assert score.concept_state == ConceptState.UNSEEN
        assert score.memory_score == 0.0
        assert score.durable_mastery_score == 0.0
        assert score.mastery_score_combined == 0.0
        assert score.evidence_count == 0
        assert score.weakness_severity == WeaknessSeverity.NONE
        assert score.version == 1

    def test_initialize_generates_id(self) -> None:
        score = self._make_score()
        assert isinstance(score.id, MasteryScoreId)


class TestMasteryScoreUpdate:
    """Tests for apply_update()."""

    def test_update_increments_version(self) -> None:
        score = self._make_score()
        original_version = score.version

        score.apply_update(
            new_memory_score=0.8,
            new_durable_mastery_score=0.5,
            new_mastery_score_combined=0.62,
            new_confidence_interval=0.3,
            new_evidence_count=1,
            algorithm_version_id=score.algorithm_version_id,
        )

        assert score.version == original_version + 1

    def test_update_changes_scores(self) -> None:
        score = self._make_score()

        score.apply_update(
            new_memory_score=0.85,
            new_durable_mastery_score=0.45,
            new_mastery_score_combined=0.60,
            new_confidence_interval=0.25,
            new_evidence_count=3,
            algorithm_version_id=score.algorithm_version_id,
        )

        assert score.memory_score == 0.85
        assert score.durable_mastery_score == 0.45
        assert score.mastery_score_combined == 0.60
        assert score.evidence_count == 3

    def test_update_records_mastery_updated_event(self) -> None:
        score = self._make_score()

        score.apply_update(
            new_memory_score=0.8,
            new_durable_mastery_score=0.5,
            new_mastery_score_combined=0.62,
            new_confidence_interval=0.3,
            new_evidence_count=1,
            algorithm_version_id=score.algorithm_version_id,
        )

        events = score.collect_events()
        assert any(isinstance(e, MasteryUpdated) for e in events)

    def test_state_transition_from_unseen_to_novice(self) -> None:
        score = self._make_score()

        score.apply_update(
            new_memory_score=0.8,
            new_durable_mastery_score=0.15,
            new_mastery_score_combined=0.38,
            new_confidence_interval=0.5,
            new_evidence_count=1,
            algorithm_version_id=score.algorithm_version_id,
        )

        assert score.concept_state == ConceptState.NOVICE
        events = score.collect_events()
        assert any(isinstance(e, ConceptStateChanged) for e in events)

    def test_state_transition_to_proficient(self) -> None:
        score = self._make_score()

        score.apply_update(
            new_memory_score=0.9,
            new_durable_mastery_score=0.75,
            new_mastery_score_combined=0.80,
            new_confidence_interval=0.15,
            new_evidence_count=10,
            algorithm_version_id=score.algorithm_version_id,
        )

        assert score.concept_state == ConceptState.PROFICIENT

    def test_state_transition_to_mastered(self) -> None:
        score = self._make_score()

        score.apply_update(
            new_memory_score=0.95,
            new_durable_mastery_score=0.88,
            new_mastery_score_combined=0.90,
            new_confidence_interval=0.10,
            new_evidence_count=15,
            algorithm_version_id=score.algorithm_version_id,
        )

        assert score.concept_state == ConceptState.MASTERED

    def test_weak_concept_detected_event(self) -> None:
        score = self._make_score()

        score.apply_update(
            new_memory_score=0.3,
            new_durable_mastery_score=0.15,
            new_mastery_score_combined=0.20,
            new_confidence_interval=0.5,
            new_evidence_count=1,
            algorithm_version_id=score.algorithm_version_id,
        )

        events = score.collect_events()
        assert any(isinstance(e, WeakConceptDetected) for e in events)

    def test_invalid_score_rejected(self) -> None:
        score = self._make_score()
        from app.domain.shared.kernel import InvariantViolation

        with pytest.raises(InvariantViolation):
            score.apply_update(
                new_memory_score=1.5,
                new_durable_mastery_score=0.5,
                new_mastery_score_combined=0.62,
                new_confidence_interval=0.3,
                new_evidence_count=1,
                algorithm_version_id=score.algorithm_version_id,
            )

    @staticmethod
    def _make_score() -> MasteryScore:
        return MasteryScore.initialize(
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            concept_id=ConceptId.generate(),
            algorithm_version_id=AlgorithmVersionId.generate(),
        )


class TestMasteryCalculator:
    """Tests for the MasteryCalculator domain service — the heart of the engine."""

    def _make_algorithm(self) -> AlgorithmVersion:
        return AlgorithmVersion.create(
            version_number=VersionNumber(1),
            name="Deterministic v1",
            parameters={
                "memory_decay_rate_per_day": 0.95,
                "mastery_consolidation_rate": 0.10,
                "review_interval_expansion_factor": 2.5,
                "review_interval_contraction_factor": 0.3,
                "mastery_threshold_proficient": 0.70,
                "mastery_threshold_mastered": 0.85,
                "memory_threshold": 0.50,
                "hint_usage_mastery_penalty": 0.30,
                "memory_weight": 0.40,
                "durable_weight": 0.60,
            },
        )

    def _make_attempt(
        self,
        outcome: ScoringOutcome = ScoringOutcome.CORRECT,
        hint_used: bool = False,
        partial_credit: float | None = None,
        created_at: datetime | None = None,
    ) -> Attempt:
        return Attempt.record(
            question_instance_id=QuestionInstanceId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            study_session_id=StudySessionId.generate(),
            content_version_id=ContentVersionId.generate(),
            template_version_id=TemplateVersionId.generate(),
            algorithm_version_id=AlgorithmVersionId.generate(),
            scoring_outcome=outcome,
            time_to_answer=Duration(15000),
            hint_used=hint_used,
            hint_tiers_used=[1] if hint_used else [],
            attempt_intent=AttemptIntent.PRACTICE,
            partial_credit=partial_credit,
            created_at=created_at or datetime.now(timezone.utc),
        )

    def test_determinism_same_inputs_same_outputs(self) -> None:
        """The MasteryCalculator is deterministic (ADR-0007, invariant M1)."""
        calc = MasteryCalculator()
        algo = self._make_algorithm()
        now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)

        attempt = self._make_attempt(
            created_at=now - timedelta(hours=1)
        )

        result1 = calc.compute(
            attempts=[attempt],
            algorithm=algo,
            current_review_interval=ReviewInterval(7),
            previous_memory_score=0.5,
            previous_durable_mastery=0.3,
            current_time=now,
        )

        result2 = calc.compute(
            attempts=[attempt],
            algorithm=algo,
            current_review_interval=ReviewInterval(7),
            previous_memory_score=0.5,
            previous_durable_mastery=0.3,
            current_time=now,
        )

        assert result1.memory_score == result2.memory_score
        assert result1.durable_mastery_score == result2.durable_mastery_score
        assert result1.mastery_score_combined == result2.mastery_score_combined

    def test_correct_attempt_boosts_memory(self) -> None:
        calc = MasteryCalculator()
        algo = self._make_algorithm()
        now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)

        attempt = self._make_attempt(
            outcome=ScoringOutcome.CORRECT,
            created_at=now - timedelta(hours=1),
        )

        result = calc.compute(
            attempts=[attempt],
            algorithm=algo,
            current_review_interval=ReviewInterval(7),
            previous_memory_score=0.3,
            previous_durable_mastery=0.2,
            current_time=now,
        )

        assert result.memory_score > 0.3  # memory should increase

    def test_incorrect_attempt_drops_memory(self) -> None:
        calc = MasteryCalculator()
        algo = self._make_algorithm()
        now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)

        attempt = self._make_attempt(
            outcome=ScoringOutcome.INCORRECT,
            created_at=now - timedelta(hours=1),
        )

        result = calc.compute(
            attempts=[attempt],
            algorithm=algo,
            current_review_interval=ReviewInterval(7),
            previous_memory_score=0.8,
            previous_durable_mastery=0.5,
            current_time=now,
        )

        assert result.memory_score < 0.8  # memory should decrease

    def test_hint_penalty_reduces_credit(self) -> None:
        calc = MasteryCalculator()
        algo = self._make_algorithm()
        now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)

        # Correct with hint
        attempt_with_hint = self._make_attempt(
            outcome=ScoringOutcome.CORRECT,
            hint_used=True,
            created_at=now - timedelta(hours=1),
        )
        result_with_hint = calc.compute(
            attempts=[attempt_with_hint],
            algorithm=algo,
            current_review_interval=ReviewInterval(7),
            previous_memory_score=0.5,
            previous_durable_mastery=0.3,
            current_time=now,
        )

        # Correct without hint
        attempt_no_hint = self._make_attempt(
            outcome=ScoringOutcome.CORRECT,
            hint_used=False,
            created_at=now - timedelta(hours=1),
        )
        result_no_hint = calc.compute(
            attempts=[attempt_no_hint],
            algorithm=algo,
            current_review_interval=ReviewInterval(7),
            previous_memory_score=0.5,
            previous_durable_mastery=0.3,
            current_time=now,
        )

        # Memory score with hint should be lower than without
        assert result_with_hint.memory_score < result_no_hint.memory_score

    def test_review_interval_expands_on_success(self) -> None:
        calc = MasteryCalculator()
        algo = self._make_algorithm()
        now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)

        attempt = self._make_attempt(
            outcome=ScoringOutcome.CORRECT,
            created_at=now - timedelta(hours=1),
        )

        result = calc.compute(
            attempts=[attempt],
            algorithm=algo,
            current_review_interval=ReviewInterval(7),
            previous_memory_score=0.5,
            previous_durable_mastery=0.3,
            current_time=now,
        )

        # 7 * 2.5 = 17.5 → 17
        assert result.new_review_interval.days > 7

    def test_review_interval_contracts_on_failure(self) -> None:
        calc = MasteryCalculator()
        algo = self._make_algorithm()
        now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)

        attempt = self._make_attempt(
            outcome=ScoringOutcome.INCORRECT,
            created_at=now - timedelta(hours=1),
        )

        result = calc.compute(
            attempts=[attempt],
            algorithm=algo,
            current_review_interval=ReviewInterval(10),
            previous_memory_score=0.5,
            previous_durable_mastery=0.3,
            current_time=now,
        )

        # 10 * 0.3 = 3
        assert result.new_review_interval.days < 10

    def test_confidence_narrows_with_evidence(self) -> None:
        calc = MasteryCalculator()
        algo = self._make_algorithm()
        now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)

        # With 1 attempt
        attempts_1 = [self._make_attempt(created_at=now - timedelta(days=1))]
        result_1 = calc.compute(
            attempts=attempts_1,
            algorithm=algo,
            current_review_interval=ReviewInterval(7),
            previous_memory_score=0.5,
            previous_durable_mastery=0.3,
            current_time=now,
        )

        # With 10 attempts
        attempts_10 = [
            self._make_attempt(created_at=now - timedelta(days=10 - i))
            for i in range(10)
        ]
        result_10 = calc.compute(
            attempts=attempts_10,
            algorithm=algo,
            current_review_interval=ReviewInterval(7),
            previous_memory_score=0.5,
            previous_durable_mastery=0.3,
            current_time=now,
        )

        # More evidence → narrower confidence interval
        assert result_10.confidence_interval < result_1.confidence_interval

    def test_empty_attempts_returns_zero_scores(self) -> None:
        calc = MasteryCalculator()
        algo = self._make_algorithm()

        result = calc.compute(
            attempts=[],
            algorithm=algo,
            current_review_interval=ReviewInterval(7),
            previous_memory_score=0.0,
            previous_durable_mastery=0.0,
        )

        assert result.memory_score == 0.0
        assert result.durable_mastery_score == 0.0
        assert result.evidence_count == 0

    def test_all_scores_bounded_zero_to_one(self) -> None:
        """All computed scores must be in [0.0, 1.0]."""
        calc = MasteryCalculator()
        algo = self._make_algorithm()
        now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)

        # Extreme case: perfect prior scores, correct attempt
        attempt = self._make_attempt(
            outcome=ScoringOutcome.CORRECT,
            created_at=now,
        )
        result = calc.compute(
            attempts=[attempt],
            algorithm=algo,
            current_review_interval=ReviewInterval(7),
            previous_memory_score=1.0,
            previous_durable_mastery=1.0,
            current_time=now,
        )

        assert 0.0 <= result.memory_score <= 1.0
        assert 0.0 <= result.durable_mastery_score <= 1.0
        assert 0.0 <= result.mastery_score_combined <= 1.0
        assert 0.0 <= result.confidence_interval <= 1.0
