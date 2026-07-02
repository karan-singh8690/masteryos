"""Comprehensive unit tests for the MasteryScore aggregate (Mastery context).

Tests cover:
- ``MasteryScore.initialize()`` factory creates an UNSEEN concept with
  zero scores and full uncertainty
- ``apply_update()`` updates scores and derives concept_state and
  weakness_severity
- State transitions: unseen → novice → developing → proficient → mastered
- Optimistic concurrency: ``version`` increments on each update
- Domain events: ``MasteryUpdated``, ``ConceptStateChanged``,
  ``WeakConceptDetected``
- Invariants: all scores bounded [0.0, 1.0]

These tests exercise only the pure-Python domain layer — no database,
HTTP or infrastructure.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.mastery.events import (
    ConceptStateChanged,
    MasteryUpdated,
    WeakConceptDetected,
)
from app.domain.mastery.mastery_score import MasteryScore
from app.domain.shared.ids import (
    AlgorithmVersionId,
    ConceptId,
    LearnerEnrollmentId,
    MasteryScoreId,
)
from app.domain.shared.kernel import ConceptState, InvariantViolation, WeaknessSeverity


# ============================================================
# Helpers
# ============================================================


def _initialize_score() -> MasteryScore:
    return MasteryScore.initialize(
        learner_enrollment_id=LearnerEnrollmentId.generate(),
        concept_id=ConceptId.generate(),
        algorithm_version_id=AlgorithmVersionId.generate(),
    )


# ============================================================
# Factory
# ============================================================


class TestMasteryScoreInitialize:
    """Tests for the ``MasteryScore.initialize()`` factory."""

    def test_initialize_creates_aggregate_with_id(self) -> None:
        score = _initialize_score()
        assert isinstance(score.id, MasteryScoreId)

    def test_initialize_starts_in_unseen_state(self) -> None:
        score = _initialize_score()
        assert score.concept_state == ConceptState.UNSEEN

    def test_initialize_starts_with_zero_memory(self) -> None:
        score = _initialize_score()
        assert score.memory_score == 0.0

    def test_initialize_starts_with_zero_durable_mastery(self) -> None:
        score = _initialize_score()
        assert score.durable_mastery_score == 0.0

    def test_initialize_starts_with_zero_combined(self) -> None:
        score = _initialize_score()
        assert score.mastery_score_combined == 0.0

    def test_initialize_starts_with_full_uncertainty(self) -> None:
        score = _initialize_score()
        assert score.confidence_interval == 1.0

    def test_initialize_starts_with_zero_evidence(self) -> None:
        score = _initialize_score()
        assert score.evidence_count == 0

    def test_initialize_starts_with_none_weakness(self) -> None:
        score = _initialize_score()
        assert score.weakness_severity == WeaknessSeverity.NONE
        assert score.is_weak is False

    def test_initialize_starts_at_version_one(self) -> None:
        score = _initialize_score()
        assert score.version == 1

    def test_initialize_records_no_events(self) -> None:
        """Initialization itself emits no domain events — events fire on
        the first ``apply_update()``."""
        score = _initialize_score()
        assert score.collect_events() == []


# ============================================================
# Invariants on construction
# ============================================================


class TestMasteryScoreConstructionInvariants:
    """Tests for the invariants enforced by the constructor."""

    def _make(
        self,
        *,
        memory: float = 0.0,
        durable: float = 0.0,
        combined: float = 0.0,
        confidence: float = 1.0,
    ) -> MasteryScore:
        return MasteryScore(
            id=MasteryScoreId.generate(),
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            concept_id=ConceptId.generate(),
            algorithm_version_id=AlgorithmVersionId.generate(),
            memory_score=memory,
            durable_mastery_score=durable,
            mastery_score_combined=combined,
            confidence_interval=confidence,
            evidence_count=0,
            concept_state=ConceptState.UNSEEN,
            weakness_severity=WeaknessSeverity.NONE,
        )

    def test_rejects_memory_below_zero(self) -> None:
        with pytest.raises(InvariantViolation):
            self._make(memory=-0.01)

    def test_rejects_memory_above_one(self) -> None:
        with pytest.raises(InvariantViolation):
            self._make(memory=1.01)

    def test_rejects_durable_below_zero(self) -> None:
        with pytest.raises(InvariantViolation):
            self._make(durable=-0.01)

    def test_rejects_durable_above_one(self) -> None:
        with pytest.raises(InvariantViolation):
            self._make(durable=1.01)

    def test_rejects_combined_below_zero(self) -> None:
        with pytest.raises(InvariantViolation):
            self._make(combined=-0.01)

    def test_rejects_combined_above_one(self) -> None:
        with pytest.raises(InvariantViolation):
            self._make(combined=1.01)

    def test_rejects_confidence_below_zero(self) -> None:
        with pytest.raises(InvariantViolation):
            self._make(confidence=-0.01)

    def test_rejects_confidence_above_one(self) -> None:
        with pytest.raises(InvariantViolation):
            self._make(confidence=1.01)

    def test_accepts_all_zero_scores(self) -> None:
        score = self._make(memory=0.0, durable=0.0, combined=0.0, confidence=0.0)
        assert score.memory_score == 0.0

    def test_accepts_all_full_scores(self) -> None:
        score = self._make(memory=1.0, durable=1.0, combined=1.0, confidence=1.0)
        assert score.mastery_score_combined == 1.0


# ============================================================
# apply_update — basic
# ============================================================


class TestMasteryScoreApplyUpdate:
    """Tests for ``apply_update()`` — score updates and event recording."""

    def test_apply_update_records_mastery_updated_event(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.5,
            new_durable_mastery_score=0.4,
            new_mastery_score_combined=0.45,
            new_confidence_interval=0.5,
            new_evidence_count=1,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        events = score.collect_events()
        types = [type(e).__name__ for e in events]
        assert "MasteryUpdated" in types

    def test_apply_update_increments_version(self) -> None:
        score = _initialize_score()
        assert score.version == 1
        score.apply_update(
            new_memory_score=0.5,
            new_durable_mastery_score=0.5,
            new_mastery_score_combined=0.5,
            new_confidence_interval=0.5,
            new_evidence_count=1,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.version == 2

    def test_apply_update_increments_version_each_call(self) -> None:
        score = _initialize_score()
        for _ in range(3):
            score.apply_update(
                new_memory_score=0.5,
                new_durable_mastery_score=0.5,
                new_mastery_score_combined=0.5,
                new_confidence_interval=0.5,
                new_evidence_count=1,
                algorithm_version_id=AlgorithmVersionId.generate(),
            )
        assert score.version == 4  # 1 + 3

    def test_apply_update_sets_new_scores(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.7,
            new_durable_mastery_score=0.6,
            new_mastery_score_combined=0.65,
            new_confidence_interval=0.4,
            new_evidence_count=5,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.memory_score == 0.7
        assert score.durable_mastery_score == 0.6
        assert score.mastery_score_combined == 0.65
        assert score.confidence_interval == 0.4
        assert score.evidence_count == 5

    def test_apply_update_rejects_invalid_memory(self) -> None:
        score = _initialize_score()
        with pytest.raises(InvariantViolation):
            score.apply_update(
                new_memory_score=1.5,
                new_durable_mastery_score=0.5,
                new_mastery_score_combined=0.5,
                new_confidence_interval=0.5,
                new_evidence_count=1,
                algorithm_version_id=AlgorithmVersionId.generate(),
            )

    def test_apply_update_rejects_invalid_combined(self) -> None:
        score = _initialize_score()
        with pytest.raises(InvariantViolation):
            score.apply_update(
                new_memory_score=0.5,
                new_durable_mastery_score=0.5,
                new_mastery_score_combined=-0.1,
                new_confidence_interval=0.5,
                new_evidence_count=1,
                algorithm_version_id=AlgorithmVersionId.generate(),
            )

    def test_apply_update_sets_last_attempt_at(self) -> None:
        score = _initialize_score()
        ts = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        score.apply_update(
            new_memory_score=0.5,
            new_durable_mastery_score=0.5,
            new_mastery_score_combined=0.5,
            new_confidence_interval=0.5,
            new_evidence_count=1,
            algorithm_version_id=AlgorithmVersionId.generate(),
            last_attempt_at=ts,
        )
        assert score.last_attempt_at == ts

    def test_apply_update_updates_algorithm_version(self) -> None:
        score = _initialize_score()
        new_av = AlgorithmVersionId.generate()
        score.apply_update(
            new_memory_score=0.5,
            new_durable_mastery_score=0.5,
            new_mastery_score_combined=0.5,
            new_confidence_interval=0.5,
            new_evidence_count=1,
            algorithm_version_id=new_av,
        )
        assert score.algorithm_version_id == new_av


# ============================================================
# Concept state derivation
# ============================================================


class TestConceptStateDerivation:
    """Tests for the derived ``concept_state`` after ``apply_update()``."""

    def _update(self, score: MasteryScore, *, combined: float, memory: float = 0.7) -> None:
        """Apply an update that produces the given combined score."""
        score.apply_update(
            new_memory_score=memory,
            new_durable_mastery_score=combined,  # for simplicity
            new_mastery_score_combined=combined,
            new_confidence_interval=0.5,
            new_evidence_count=1,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )

    def test_low_combined_becomes_novice(self) -> None:
        """combined in (0.0, 0.40) → NOVICE."""
        score = _initialize_score()
        self._update(score, combined=0.20, memory=0.7)
        assert score.concept_state == ConceptState.NOVICE

    def test_combined_at_0_40_becomes_developing(self) -> None:
        """combined >= 0.40 → DEVELOPING (when < proficient)."""
        score = _initialize_score()
        self._update(score, combined=0.40, memory=0.7)
        assert score.concept_state == ConceptState.DEVELOPING

    def test_combined_just_below_proficient_stays_developing(self) -> None:
        score = _initialize_score()
        self._update(score, combined=0.69, memory=0.7)
        assert score.concept_state == ConceptState.DEVELOPING

    def test_combined_at_proficient_threshold_becomes_proficient(self) -> None:
        """combined >= 0.70 with sufficient memory → PROFICIENT."""
        score = _initialize_score()
        self._update(score, combined=0.70, memory=0.7)
        assert score.concept_state == ConceptState.PROFICIENT

    def test_combined_just_below_mastered_stays_proficient(self) -> None:
        score = _initialize_score()
        self._update(score, combined=0.84, memory=0.7)
        assert score.concept_state == ConceptState.PROFICIENT

    def test_combined_at_mastered_threshold_becomes_mastered(self) -> None:
        """combined >= 0.85 with sufficient memory → MASTERED."""
        score = _initialize_score()
        self._update(score, combined=0.85, memory=0.7)
        assert score.concept_state == ConceptState.MASTERED

    def test_combined_full_with_full_memory_is_mastered(self) -> None:
        score = _initialize_score()
        self._update(score, combined=1.0, memory=1.0)
        assert score.concept_state == ConceptState.MASTERED

    def test_high_combined_but_low_memory_becomes_decayed(self) -> None:
        """combined >= mastered but memory < memory_threshold → DECAYED."""
        score = _initialize_score()
        self._update(score, combined=0.90, memory=0.30)
        assert score.concept_state == ConceptState.DECAYED

    def test_proficient_combined_but_low_memory_becomes_decayed(self) -> None:
        score = _initialize_score()
        self._update(score, combined=0.75, memory=0.40)
        assert score.concept_state == ConceptState.DECAYED

    def test_zero_combined_stays_unseen(self) -> None:
        """combined == 0.0 → UNSEEN (regardless of memory)."""
        score = _initialize_score()
        self._update(score, combined=0.0, memory=0.5)
        assert score.concept_state == ConceptState.UNSEEN


class TestConceptStateTransitions:
    """Tests for the full progression unseen → mastered."""

    def test_full_progression_unseen_to_mastered(self) -> None:
        score = _initialize_score()
        assert score.concept_state == ConceptState.UNSEEN

        # Small initial evidence → NOVICE
        score.apply_update(
            new_memory_score=0.3,
            new_durable_mastery_score=0.20,
            new_mastery_score_combined=0.20,
            new_confidence_interval=0.9,
            new_evidence_count=1,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.concept_state == ConceptState.NOVICE

        # More progress → DEVELOPING
        score.apply_update(
            new_memory_score=0.5,
            new_durable_mastery_score=0.45,
            new_mastery_score_combined=0.45,
            new_confidence_interval=0.7,
            new_evidence_count=5,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.concept_state == ConceptState.DEVELOPING

        # Cross proficient threshold → PROFICIENT
        score.apply_update(
            new_memory_score=0.75,
            new_durable_mastery_score=0.72,
            new_mastery_score_combined=0.72,
            new_confidence_interval=0.5,
            new_evidence_count=10,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.concept_state == ConceptState.PROFICIENT

        # Cross mastered threshold → MASTERED
        score.apply_update(
            new_memory_score=0.9,
            new_durable_mastery_score=0.88,
            new_mastery_score_combined=0.88,
            new_confidence_interval=0.3,
            new_evidence_count=20,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.concept_state == ConceptState.MASTERED
        assert score.is_mastered is True
        assert score.is_proficient_or_above is True

    def test_state_can_decay_from_mastered(self) -> None:
        score = _initialize_score()
        # Reach MASTERED
        score.apply_update(
            new_memory_score=0.9,
            new_durable_mastery_score=0.88,
            new_mastery_score_combined=0.88,
            new_confidence_interval=0.3,
            new_evidence_count=20,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.concept_state == ConceptState.MASTERED

        # Memory drops below threshold (e.g., long gap) → DECAYED
        score.apply_update(
            new_memory_score=0.30,
            new_durable_mastery_score=0.88,
            new_mastery_score_combined=0.88,
            new_confidence_interval=0.3,
            new_evidence_count=21,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.concept_state == ConceptState.DECAYED


# ============================================================
# Weakness severity derivation
# ============================================================


class TestWeaknessSeverityDerivation:
    """Tests for the derived ``weakness_severity`` after ``apply_update()``."""

    def _update(
        self,
        score: MasteryScore,
        *,
        durable: float,
        memory: float = 0.7,
    ) -> None:
        score.apply_update(
            new_memory_score=memory,
            new_durable_mastery_score=durable,
            new_mastery_score_combined=durable,
            new_confidence_interval=0.5,
            new_evidence_count=1,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )

    def test_durable_at_proficient_no_weakness(self) -> None:
        score = _initialize_score()
        self._update(score, durable=0.70)
        assert score.weakness_severity == WeaknessSeverity.NONE
        assert score.is_weak is False

    def test_durable_above_proficient_no_weakness(self) -> None:
        score = _initialize_score()
        self._update(score, durable=0.85)
        assert score.weakness_severity == WeaknessSeverity.NONE

    def test_durable_below_0_20_is_severe(self) -> None:
        score = _initialize_score()
        self._update(score, durable=0.10, memory=0.7)
        assert score.weakness_severity == WeaknessSeverity.SEVERE
        assert score.is_weak is True

    def test_durable_at_0_20_is_moderate(self) -> None:
        """At exactly 0.20 the durable check (``< 0.20``) is False, so the
        next band applies."""
        score = _initialize_score()
        self._update(score, durable=0.20, memory=0.7)
        assert score.weakness_severity == WeaknessSeverity.MODERATE

    def test_durable_below_0_35_is_moderate(self) -> None:
        score = _initialize_score()
        self._update(score, durable=0.30, memory=0.7)
        assert score.weakness_severity == WeaknessSeverity.MODERATE

    def test_durable_between_0_35_and_proficient_with_low_memory_is_mild(self) -> None:
        """0.35 <= durable < proficient AND memory < memory_threshold → MILD."""
        score = _initialize_score()
        self._update(score, durable=0.50, memory=0.30)
        assert score.weakness_severity == WeaknessSeverity.MILD

    def test_durable_between_0_35_and_proficient_with_ok_memory_no_weakness(self) -> None:
        score = _initialize_score()
        self._update(score, durable=0.50, memory=0.7)
        assert score.weakness_severity == WeaknessSeverity.NONE


# ============================================================
# Domain events
# ============================================================


class TestMasteryScoreEvents:
    """Tests for the events recorded by ``apply_update()``."""

    def test_mastery_updated_event_carries_scores(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.7,
            new_durable_mastery_score=0.6,
            new_mastery_score_combined=0.65,
            new_confidence_interval=0.4,
            new_evidence_count=5,
            algorithm_version_id=score.algorithm_version_id,
        )
        events = score.collect_events()
        evt = next(e for e in events if isinstance(e, MasteryUpdated))
        assert evt.memory_score == 0.7
        assert evt.durable_mastery_score == 0.6
        assert evt.mastery_score_combined == 0.65
        assert evt.concept_id == score.concept_id.value
        assert evt.learner_enrollment_id == score.learner_enrollment_id.value

    def test_concept_state_changed_event_on_transition(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.3,
            new_durable_mastery_score=0.2,
            new_mastery_score_combined=0.2,
            new_confidence_interval=0.9,
            new_evidence_count=1,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        events = score.collect_events()
        evt = next(e for e in events if isinstance(e, ConceptStateChanged))
        assert evt.old_state == ConceptState.UNSEEN
        assert evt.new_state == ConceptState.NOVICE

    def test_no_concept_state_changed_event_when_state_unchanged(self) -> None:
        score = _initialize_score()
        # First update moves UNSEEN → NOVICE
        score.apply_update(
            new_memory_score=0.3,
            new_durable_mastery_score=0.2,
            new_mastery_score_combined=0.2,
            new_confidence_interval=0.9,
            new_evidence_count=1,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        score.clear_events()
        # Second update stays in NOVICE
        score.apply_update(
            new_memory_score=0.35,
            new_durable_mastery_score=0.25,
            new_mastery_score_combined=0.25,
            new_confidence_interval=0.85,
            new_evidence_count=2,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        events = score.collect_events()
        assert not any(isinstance(e, ConceptStateChanged) for e in events)

    def test_weak_concept_detected_event_when_weak(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.1,
            new_durable_mastery_score=0.05,
            new_mastery_score_combined=0.05,
            new_confidence_interval=0.9,
            new_evidence_count=1,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        events = score.collect_events()
        weak_events = [e for e in events if isinstance(e, WeakConceptDetected)]
        assert len(weak_events) == 1
        assert weak_events[0].severity == WeaknessSeverity.SEVERE

    def test_no_weak_concept_detected_event_when_not_weak(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.9,
            new_durable_mastery_score=0.88,
            new_mastery_score_combined=0.88,
            new_confidence_interval=0.3,
            new_evidence_count=20,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        events = score.collect_events()
        assert not any(isinstance(e, WeakConceptDetected) for e in events)

    def test_collect_events_clears_internal_list(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.5,
            new_durable_mastery_score=0.5,
            new_mastery_score_combined=0.5,
            new_confidence_interval=0.5,
            new_evidence_count=1,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        first = score.collect_events()
        second = score.collect_events()
        assert len(first) >= 1
        assert second == []


# ============================================================
# Convenience predicates
# ============================================================


class TestMasteryScorePredicates:
    """Tests for ``is_weak``, ``is_mastered``, ``is_proficient_or_above``."""

    def test_is_weak_true_when_severity_not_none(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.1,
            new_durable_mastery_score=0.05,
            new_mastery_score_combined=0.05,
            new_confidence_interval=0.9,
            new_evidence_count=1,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.is_weak is True

    def test_is_weak_false_when_severity_none(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.9,
            new_durable_mastery_score=0.88,
            new_mastery_score_combined=0.88,
            new_confidence_interval=0.3,
            new_evidence_count=20,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.is_weak is False

    def test_is_mastered_true_only_in_mastered_state(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.9,
            new_durable_mastery_score=0.88,
            new_mastery_score_combined=0.88,
            new_confidence_interval=0.3,
            new_evidence_count=20,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.is_mastered is True

    def test_is_mastered_false_in_proficient(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.75,
            new_durable_mastery_score=0.72,
            new_mastery_score_combined=0.72,
            new_confidence_interval=0.5,
            new_evidence_count=10,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.is_mastered is False

    def test_is_proficient_or_above_in_proficient(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.75,
            new_durable_mastery_score=0.72,
            new_mastery_score_combined=0.72,
            new_confidence_interval=0.5,
            new_evidence_count=10,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.is_proficient_or_above is True

    def test_is_proficient_or_above_in_mastered(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.9,
            new_durable_mastery_score=0.88,
            new_mastery_score_combined=0.88,
            new_confidence_interval=0.3,
            new_evidence_count=20,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.is_proficient_or_above is True

    def test_is_proficient_or_above_false_in_developing(self) -> None:
        score = _initialize_score()
        score.apply_update(
            new_memory_score=0.5,
            new_durable_mastery_score=0.5,
            new_mastery_score_combined=0.5,
            new_confidence_interval=0.5,
            new_evidence_count=5,
            algorithm_version_id=AlgorithmVersionId.generate(),
        )
        assert score.is_proficient_or_above is False
