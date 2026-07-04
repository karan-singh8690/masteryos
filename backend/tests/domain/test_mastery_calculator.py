"""Comprehensive unit tests for the MasteryCalculator domain service.

Tests cover:
- Determinism: same inputs → same outputs (M1, ASD 6.8)
- Memory score computation (boost on correct, drop on incorrect,
  hint penalty, time decay)
- Durable mastery computation (EMA, slower to rise than fall)
- Combined score (weighted average with algorithm weights)
- Confidence interval narrows with evidence
- Review interval expansion/contraction
- Hint penalty reduces effective credit
- Empty attempt list returns zero scores

These tests exercise only the pure-Python domain layer — no database,
HTTP or infrastructure.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.assessment.attempt import Attempt
from app.domain.mastery.algorithm_version import AlgorithmVersion
from app.domain.mastery.mastery_calculator import MasteryCalculator, MasteryComputation
from app.domain.shared.ids import (
    AlgorithmVersionId,
    ContentVersionId,
    LearnerEnrollmentId,
    QuestionInstanceId,
    StudySessionId,
    TemplateVersionId,
)
from app.domain.shared.kernel import AttemptIntent, ScoringOutcome
from app.domain.shared.value_objects import Duration, ReviewInterval, VersionNumber


# ============================================================
# Helpers
# ============================================================


def _algorithm(**overrides: object) -> AlgorithmVersion:
    """Build an AlgorithmVersion with default parameters, overridable per test."""
    params: dict[str, object] = {
        "memory_decay_rate_per_day": 0.05,
        "mastery_consolidation_rate": 0.10,
        "review_interval_expansion_factor": 2.5,
        "review_interval_contraction_factor": 0.3,
        "hint_usage_mastery_penalty": 0.30,
    }
    params.update(overrides)
    return AlgorithmVersion.create(
        version_number=VersionNumber(1),
        name="test-algo",
        parameters=params,  # type: ignore[arg-type]
    )


def _attempt(
    *,
    outcome: ScoringOutcome = ScoringOutcome.CORRECT,
    partial_credit: float | None = None,
    hint_used: bool = False,
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
        time_to_answer=Duration(30),
        hint_used=hint_used,
        hint_tiers_used=[],
        attempt_intent=AttemptIntent.PRACTICE,
        partial_credit=partial_credit,
        concept_ids=(uuid4(),),
        # created_at is set internally; we can't pass it. Tests that need
        # control of ``created_at`` should patch the module-level ``now``
        # or use ``datetime`` arithmetic relative to the attempt's own
        # ``created_at`` field after construction.
    ) if created_at is None else _attempt_with_time(
        outcome=outcome,
        partial_credit=partial_credit,
        hint_used=hint_used,
        created_at=created_at,
    )


def _attempt_with_time(
    *,
    outcome: ScoringOutcome = ScoringOutcome.CORRECT,
    partial_credit: float | None = None,
    hint_used: bool = False,
    created_at: datetime,
) -> Attempt:
    """Construct an Attempt whose ``created_at`` is the given timestamp.

    ``Attempt.record`` does not accept ``created_at`` directly; we construct
    via the public factory then poke the field (the Attempt is otherwise
    immutable, but ``created_at`` is needed for decay math).
    """
    a = Attempt.record(
        question_instance_id=QuestionInstanceId.generate(),
        learner_enrollment_id=LearnerEnrollmentId.generate(),
        study_session_id=StudySessionId.generate(),
        content_version_id=ContentVersionId.generate(),
        template_version_id=TemplateVersionId.generate(),
        algorithm_version_id=AlgorithmVersionId.generate(),
        scoring_outcome=outcome,
        time_to_answer=Duration(30),
        hint_used=hint_used,
        hint_tiers_used=[],
        attempt_intent=AttemptIntent.PRACTICE,
        partial_credit=partial_credit,
        concept_ids=(uuid4(),),
    )
    # Bypass the (lack of) ``created_at`` parameter
    object.__setattr__(a, "created_at", created_at)
    a.clear_events()
    return a


def _compute(
    attempts: list[Attempt],
    *,
    algorithm: AlgorithmVersion | None = None,
    current_interval: ReviewInterval | None = None,
    previous_memory: float = 0.0,
    previous_durable: float = 0.0,
    current_time: datetime | None = None,
) -> MasteryComputation:
    calc = MasteryCalculator()
    return calc.compute(
        attempts=attempts,
        algorithm=algorithm or _algorithm(),
        current_review_interval=current_interval or ReviewInterval(7),
        previous_memory_score=previous_memory,
        previous_durable_mastery=previous_durable,
        current_time=current_time,
    )


# ============================================================
# Determinism
# ============================================================


class TestMasteryCalculatorDeterminism:
    """M1 (ASD 6.8): same inputs → same outputs."""

    def test_same_inputs_produce_same_outputs(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        algo = _algorithm()
        interval = ReviewInterval(7)

        r1 = _compute(
            [attempt],
            algorithm=algo,
            current_interval=interval,
            previous_memory=0.3,
            previous_durable=0.3,
            current_time=ts + timedelta(days=1),
        )
        r2 = _compute(
            [attempt],
            algorithm=algo,
            current_interval=interval,
            previous_memory=0.3,
            previous_durable=0.3,
            current_time=ts + timedelta(days=1),
        )
        assert r1 == r2

    def test_different_previous_memory_produces_different_outputs(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        r1 = _compute([attempt], previous_memory=0.1, current_time=ts)
        r2 = _compute([attempt], previous_memory=0.9, current_time=ts)
        assert r1.memory_score != r2.memory_score

    def test_different_current_time_produces_different_outputs(self) -> None:
        """A later ``current_time`` produces more decay → lower memory."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        # Higher previous_memory to make decay visible
        r1 = _compute(
            [attempt],
            previous_memory=0.9,
            current_time=ts + timedelta(days=1),
        )
        r2 = _compute(
            [attempt],
            previous_memory=0.9,
            current_time=ts + timedelta(days=30),
        )
        assert r2.memory_score < r1.memory_score


# ============================================================
# Empty attempt list
# ============================================================


class TestMasteryCalculatorEmptyAttempts:
    """Behaviour when ``attempts`` is empty."""

    def test_empty_attempts_returns_zero_scores(self) -> None:
        result = _compute([])
        assert result.memory_score == 0.0
        assert result.durable_mastery_score == 0.0
        assert result.mastery_score_combined == 0.0

    def test_empty_attempts_returns_full_uncertainty(self) -> None:
        result = _compute([])
        assert result.confidence_interval == 1.0

    def test_empty_attempts_returns_zero_evidence(self) -> None:
        result = _compute([])
        assert result.evidence_count == 0

    def test_empty_attempts_preserves_review_interval(self) -> None:
        interval = ReviewInterval(14)
        result = _compute([], current_interval=interval)
        assert result.new_review_interval.days == 14


# ============================================================
# Memory score
# ============================================================


class TestMemoryScoreComputation:
    """Tests for the short-term memory score computation."""

    def test_correct_attempt_boosts_memory(self) -> None:
        """A correct attempt moves memory sharply upward."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            previous_memory=0.2,
            current_time=ts,
        )
        # 0.7 * 1.0 + 0.3 * (0.2 * 0.05^0) = 0.7 + 0.3 * 0.2 = 0.76
        assert result.memory_score == pytest.approx(0.76, abs=0.001)

    def test_incorrect_attempt_drops_memory(self) -> None:
        """An incorrect attempt drops memory to <= previous * 0.5."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.INCORRECT,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            previous_memory=0.8,
            current_time=ts,
        )
        # new_memory = 0.7 * 0 + 0.3 * 0.8 = 0.24
        # Then min(0.24, 0.8 * 0.5) = min(0.24, 0.4) = 0.24
        assert result.memory_score <= 0.8 * 0.5
        assert result.memory_score == pytest.approx(0.24, abs=0.001)

    def test_partial_attempt_gives_moderate_boost(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.PARTIAL,
            partial_credit=0.5,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            previous_memory=0.4,
            current_time=ts,
        )
        # 0.7 * 0.5 + 0.3 * 0.4 = 0.35 + 0.12 = 0.47
        assert result.memory_score == pytest.approx(0.47, abs=0.001)

    def test_hint_penalty_reduces_effective_credit(self) -> None:
        """A correct attempt WITH a hint produces a lower memory boost
        than one without."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        with_hint = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            hint_used=True,
            created_at=ts,
        )
        without_hint = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            hint_used=False,
            created_at=ts,
        )
        r_with = _compute([with_hint], previous_memory=0.2, current_time=ts)
        r_without = _compute([without_hint], previous_memory=0.2, current_time=ts)
        assert r_with.memory_score < r_without.memory_score

    def test_hint_penalty_magnitude(self) -> None:
        """With a 30% hint penalty, the credit is 0.7 instead of 1.0."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            hint_used=True,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            previous_memory=0.0,
            current_time=ts,
        )
        # 0.7 * (1.0 * (1 - 0.30)) + 0.3 * 0 = 0.7 * 0.7 = 0.49
        assert result.memory_score == pytest.approx(0.49, abs=0.001)

    def test_memory_score_clamped_to_one(self) -> None:
        """A correct attempt with high previous memory never exceeds 1.0."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            previous_memory=1.0,
            current_time=ts,
        )
        assert result.memory_score <= 1.0

    def test_memory_score_never_negative(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.INCORRECT,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            previous_memory=0.0,
            current_time=ts,
        )
        assert result.memory_score >= 0.0

    def test_decay_reduces_memory_over_time(self) -> None:
        """With a long gap since the last attempt, the decayed previous
        memory contributes less."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        soon = _compute(
            [attempt],
            previous_memory=0.9,
            current_time=ts + timedelta(days=1),
        )
        later = _compute(
            [attempt],
            previous_memory=0.9,
            current_time=ts + timedelta(days=30),
        )
        assert later.memory_score < soon.memory_score


# ============================================================
# Durable mastery
# ============================================================


class TestDurableMasteryComputation:
    """Tests for the long-term durable mastery computation (EMA)."""

    def test_single_correct_attempt_raises_durable_slightly(self) -> None:
        """With consolidation rate 0.10, a single correct attempt from
        0.0 produces 0.10 durable."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            previous_durable=0.0,
            current_time=ts,
        )
        assert result.durable_mastery_score == pytest.approx(0.10, abs=0.001)

    def test_single_incorrect_attempt_does_not_crash_durable(self) -> None:
        """Durable mastery falls slowly — a single incorrect from 0.5
        produces a small drop (2x consolidation rate)."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.INCORRECT,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            previous_durable=0.5,
            current_time=ts,
        )
        # score += 0.20 * (0 - 0.5) = -0.10 → 0.40
        assert result.durable_mastery_score == pytest.approx(0.40, abs=0.001)

    def test_durable_rises_slower_than_it_falls(self) -> None:
        """From 0.5, a correct (credit=1.0) rises by 0.10 * 0.5 = 0.05
        to 0.55. An incorrect (credit=0.0) falls by 0.20 * 0.5 = 0.10
        to 0.40. Falls twice as fast."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        correct = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        incorrect = _attempt_with_time(
            outcome=ScoringOutcome.INCORRECT,
            created_at=ts,
        )
        r_up = _compute([correct], previous_durable=0.5, current_time=ts)
        r_down = _compute([incorrect], previous_durable=0.5, current_time=ts)
        up_delta = r_up.durable_mastery_score - 0.5
        down_delta = 0.5 - r_down.durable_mastery_score
        assert up_delta == pytest.approx(0.05, abs=0.001)
        assert down_delta == pytest.approx(0.10, abs=0.001)
        assert down_delta > up_delta

    def test_durable_clamped_to_unit_interval(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        # Many correct attempts from 0.0 should saturate at 1.0
        attempts = [
            _attempt_with_time(
                outcome=ScoringOutcome.CORRECT,
                created_at=ts,
            )
            for _ in range(200)
        ]
        result = _compute(attempts, previous_durable=0.0, current_time=ts)
        assert 0.0 <= result.durable_mastery_score <= 1.0

    def test_durable_with_hint_penalty(self) -> None:
        """A correct-with-hint attempt raises durable less than without."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        with_hint = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            hint_used=True,
            created_at=ts,
        )
        without_hint = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            hint_used=False,
            created_at=ts,
        )
        r_with = _compute([with_hint], previous_durable=0.0, current_time=ts)
        r_without = _compute([without_hint], previous_durable=0.0, current_time=ts)
        assert r_with.durable_mastery_score < r_without.durable_mastery_score


# ============================================================
# Combined score
# ============================================================


class TestCombinedScore:
    """Tests for the combined mastery score (per ADR-0008)."""

    def test_combined_is_weighted_average_default(self) -> None:
        """Default weights: 0.4 memory + 0.6 durable."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        # Force previous values that, after a single correct attempt,
        # give predictable memory and durable:
        # memory = 0.7 * 1.0 + 0.3 * 0.0 = 0.7
        # durable = 0.0 + 0.1 * (1.0 - 0.0) = 0.1
        # combined = 0.4*0.7 + 0.6*0.1 = 0.28 + 0.06 = 0.34
        result = _compute(
            [attempt],
            previous_memory=0.0,
            previous_durable=0.0,
            current_time=ts,
        )
        assert result.memory_score == pytest.approx(0.7, abs=0.001)
        assert result.durable_mastery_score == pytest.approx(0.1, abs=0.001)
        assert result.mastery_score_combined == pytest.approx(0.34, abs=0.001)

    def test_combined_respects_custom_weights(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        algo = _algorithm(memory_weight=0.5, durable_weight=0.5)  # type: ignore[arg-type]
        result = _compute(
            [attempt],
            algorithm=algo,
            previous_memory=0.0,
            previous_durable=0.0,
            current_time=ts,
        )
        # memory=0.7, durable=0.1, combined = 0.5*0.7 + 0.5*0.1 = 0.40
        assert result.mastery_score_combined == pytest.approx(0.40, abs=0.001)

    def test_combined_clamped_to_unit_interval(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            previous_memory=1.0,
            previous_durable=1.0,
            current_time=ts,
        )
        assert 0.0 <= result.mastery_score_combined <= 1.0


# ============================================================
# Confidence interval
# ============================================================


class TestConfidenceComputation:
    """Tests for the confidence interval (narrows with evidence)."""

    def test_zero_evidence_returns_full_uncertainty(self) -> None:
        result = _compute([])
        assert result.confidence_interval == 1.0

    def test_one_attempt_returns_high_uncertainty(self) -> None:
        """With 1 attempt: 1 / (1 + 1 * 0.1) ≈ 0.909."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(outcome=ScoringOutcome.CORRECT, created_at=ts)
        result = _compute([attempt], current_time=ts)
        assert result.confidence_interval == pytest.approx(1 / 1.1, abs=0.001)

    def test_ten_attempts_returns_about_half(self) -> None:
        """With 10 attempts: 1 / (1 + 10 * 0.1) = 0.5."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempts = [
            _attempt_with_time(outcome=ScoringOutcome.CORRECT, created_at=ts)
            for _ in range(10)
        ]
        result = _compute(attempts, current_time=ts)
        assert result.confidence_interval == pytest.approx(0.5, abs=0.001)

    def test_thirty_attempts_returns_about_quarter(self) -> None:
        """With 30 attempts: 1 / (1 + 30 * 0.1) ≈ 0.25."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempts = [
            _attempt_with_time(outcome=ScoringOutcome.CORRECT, created_at=ts)
            for _ in range(30)
        ]
        result = _compute(attempts, current_time=ts)
        assert result.confidence_interval == pytest.approx(0.25, abs=0.001)

    def test_confidence_monotonically_narrows_with_evidence(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        prev = 1.0
        for n in range(1, 11):
            attempts = [
                _attempt_with_time(outcome=ScoringOutcome.CORRECT, created_at=ts)
                for _ in range(n)
            ]
            result = _compute(attempts, current_time=ts)
            assert result.confidence_interval < prev
            prev = result.confidence_interval


# ============================================================
# Review interval
# ============================================================


class TestReviewIntervalComputation:
    """Tests for the new review interval (expand on success, contract on fail)."""

    def test_correct_attempt_expands_interval(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            current_interval=ReviewInterval(10),
            current_time=ts,
        )
        # 10 * 2.5 = 25
        assert result.new_review_interval.days == 25

    def test_incorrect_attempt_contracts_interval(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.INCORRECT,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            current_interval=ReviewInterval(10),
            current_time=ts,
        )
        # int(10 * 0.3) = 3
        assert result.new_review_interval.days == 3

    def test_correct_attempt_clamps_to_max(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            current_interval=ReviewInterval(300),
            current_time=ts,
        )
        # 300 * 2.5 = 750 → clamped to MAX_DAYS (365)
        assert result.new_review_interval.days == ReviewInterval.MAX_DAYS

    def test_incorrect_attempt_clamps_to_min(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.INCORRECT,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            current_interval=ReviewInterval(2),
            current_time=ts,
        )
        # int(2 * 0.3) = 0 → clamped to MIN_DAYS (1)
        assert result.new_review_interval.days == ReviewInterval.MIN_DAYS

    def test_partial_attempt_slightly_expands(self) -> None:
        """Partial credit gives a partial expansion (proportional to credit)."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.PARTIAL,
            partial_credit=1.0,  # full partial credit
            created_at=ts,
        )
        result = _compute(
            [attempt],
            current_interval=ReviewInterval(10),
            current_time=ts,
        )
        # factor = 1 + (1.0 * (2.5 - 1) * 0.5) = 1.75
        # 10 * 1.75 = 17.5 → int = 17
        assert result.new_review_interval.days == 17

    def test_partial_zero_credit_uses_default_half_credit(self) -> None:
        """A PARTIAL attempt with ``partial_credit=0.0`` is treated by the
        calculator as if ``partial_credit=0.5`` (the ``or 0.5`` fallback in
        :meth:`_compute_review_interval`). Factor = 1 + 0.5 * 1.5 * 0.5 = 1.375."""
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.PARTIAL,
            partial_credit=0.0,
            created_at=ts,
        )
        result = _compute(
            [attempt],
            current_interval=ReviewInterval(10),
            current_time=ts,
        )
        # factor = 1 + (0.5 * (2.5 - 1) * 0.5) = 1.375 → 10 * 1.375 = 13.75 → int = 13
        assert result.new_review_interval.days == 13


# ============================================================
# Result structure
# ============================================================


class TestMasteryComputationResult:
    """Tests for the ``MasteryComputation`` result dataclass."""

    def test_result_has_all_expected_fields(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(
            outcome=ScoringOutcome.CORRECT,
            created_at=ts,
        )
        result = _compute([attempt], current_time=ts)
        assert hasattr(result, "memory_score")
        assert hasattr(result, "durable_mastery_score")
        assert hasattr(result, "mastery_score_combined")
        assert hasattr(result, "confidence_interval")
        assert hasattr(result, "evidence_count")
        assert hasattr(result, "new_review_interval")
        assert hasattr(result, "last_attempt_at")

    def test_evidence_count_matches_attempt_list_length(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempts = [
            _attempt_with_time(outcome=ScoringOutcome.CORRECT, created_at=ts)
            for _ in range(5)
        ]
        result = _compute(attempts, current_time=ts)
        assert result.evidence_count == 5

    def test_last_attempt_at_is_latest_attempt_created_at(self) -> None:
        ts1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        ts2 = ts1 + timedelta(days=1)
        a1 = _attempt_with_time(outcome=ScoringOutcome.CORRECT, created_at=ts1)
        a2 = _attempt_with_time(outcome=ScoringOutcome.CORRECT, created_at=ts2)
        result = _compute([a1, a2], current_time=ts2)
        assert result.last_attempt_at == ts2

    def test_result_is_immutable(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        attempt = _attempt_with_time(outcome=ScoringOutcome.CORRECT, created_at=ts)
        result = _compute([attempt], current_time=ts)
        with pytest.raises(Exception):
            result.memory_score = 0.99  # type: ignore[misc]
