"""MasteryScore — the Engine's authoritative estimate of a learner's mastery.

Per ADR-0008, MasteryScore combines a short-term MemoryValue (decays fast)
with a durable mastery value (decays slow) into a combined estimate.
The MasteryScore is the single most queried aggregate in the learning loop
(the Scheduler reads it for every queue generation).

Invariants:
- Only the Mastery Engine (via UpdateMastery command) writes MasteryScores.
- Optimistic concurrency: the ``version`` column prevents lost updates
  when two concurrent attempts update the same learner-concept score.
- All score values are bounded [0.0, 1.0].
- ``concept_state`` and ``weakness_severity`` are derived from the scores
  and the active algorithm version's thresholds.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.shared.ids import (
    AlgorithmVersionId,
    ConceptId,
    LearnerEnrollmentId,
    MasteryScoreId,
)
from app.domain.shared.kernel import (
    AggregateRoot,
    ConceptState,
    InvariantViolation,
    WeaknessSeverity,
)
from app.domain.shared.value_objects import Confidence, MasteryValue, MemoryValue
from app.domain.mastery.events import (
    ConceptStateChanged,
    MasteryUpdated,
    WeakConceptDetected,
)


class MasteryScore(AggregateRoot):
    """Per-learner, per-concept mastery estimate.

    This is a pure domain object. The MasteryCalculator domain service
    computes the new scores from attempt history; this aggregate stores
    them and enforces invariants.

    The ``version`` field is for optimistic concurrency control (ASD 17.8).
    The application layer reads the version, computes new scores, and writes
    with ``WHERE version = $read_version``; on conflict, it retries.
    """

    def __init__(
        self,
        id: MasteryScoreId,
        learner_enrollment_id: LearnerEnrollmentId,
        concept_id: ConceptId,
        algorithm_version_id: AlgorithmVersionId,
        memory_score: float,
        durable_mastery_score: float,
        mastery_score_combined: float,
        confidence_interval: float,
        evidence_count: int,
        concept_state: ConceptState,
        weakness_severity: WeaknessSeverity,
        version: int = 1,
        last_attempt_at: datetime | None = None,
        last_updated_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.learner_enrollment_id = learner_enrollment_id
        self.concept_id = concept_id
        self.algorithm_version_id = algorithm_version_id
        self._memory_score = self._validate_score(memory_score, "memory_score")
        self._durable_mastery_score = self._validate_score(durable_mastery_score, "durable_mastery_score")
        self._mastery_score_combined = self._validate_score(mastery_score_combined, "mastery_score_combined")
        self._confidence_interval = self._validate_score(confidence_interval, "confidence_interval")
        self.evidence_count = evidence_count
        self.concept_state = concept_state
        self.weakness_severity = weakness_severity
        self.version = version
        self.last_attempt_at = last_attempt_at
        self.last_updated_at = last_updated_at or datetime.now(timezone.utc)
        self.created_at = created_at or datetime.now(timezone.utc)

    @staticmethod
    def _validate_score(value: float, name: str) -> float:
        if not 0.0 <= value <= 1.0:
            raise InvariantViolation("MasteryScore", f"{name} must be 0.0–1.0, got {value}")
        return value

    # ============================================================
    # Factory
    # ============================================================

    @classmethod
    def initialize(
        cls,
        learner_enrollment_id: LearnerEnrollmentId,
        concept_id: ConceptId,
        algorithm_version_id: AlgorithmVersionId,
    ) -> MasteryScore:
        """Initialize a new mastery score (unseen concept, zero evidence)."""
        return cls(
            id=MasteryScoreId.generate(),
            learner_enrollment_id=learner_enrollment_id,
            concept_id=concept_id,
            algorithm_version_id=algorithm_version_id,
            memory_score=0.0,
            durable_mastery_score=0.0,
            mastery_score_combined=0.0,
            confidence_interval=1.0,
            evidence_count=0,
            concept_state=ConceptState.UNSEEN,
            weakness_severity=WeaknessSeverity.NONE,
        )

    # ============================================================
    # State Update (called by the application layer after MasteryCalculator computes new scores)
    # ============================================================

    def apply_update(
        self,
        new_memory_score: float,
        new_durable_mastery_score: float,
        new_mastery_score_combined: float,
        new_confidence_interval: float,
        new_evidence_count: int,
        algorithm_version_id: AlgorithmVersionId,
        mastered_threshold: float = 0.85,
        proficient_threshold: float = 0.70,
        memory_threshold: float = 0.50,
        last_attempt_at: datetime | None = None,
    ) -> None:
        """Apply a mastery update computed by the MasteryCalculator.

        This method:
        1. Validates the new scores.
        2. Updates the scores and derived fields.
        3. Detects concept state changes and records events.
        4. Detects weakness and records events.
        5. Increments the optimistic concurrency version.
        6. Records the MasteryUpdated event.

        The MasteryCalculator (domain service) computes the new scores;
        this method applies them and manages the aggregate's invariants
        and events.
        """
        old_state = self.concept_state

        self._memory_score = self._validate_score(new_memory_score, "memory_score")
        self._durable_mastery_score = self._validate_score(new_durable_mastery_score, "durable_mastery_score")
        self._mastery_score_combined = self._validate_score(new_mastery_score_combined, "mastery_score_combined")
        self._confidence_interval = self._validate_score(new_confidence_interval, "confidence_interval")
        self.evidence_count = new_evidence_count
        self.algorithm_version_id = algorithm_version_id
        self.last_attempt_at = last_attempt_at or datetime.now(timezone.utc)
        self.last_updated_at = datetime.now(timezone.utc)
        self.version += 1

        # Derive concept_state from scores
        new_state = self._derive_concept_state(
            new_mastery_score_combined,
            new_memory_score,
            mastered_threshold,
            proficient_threshold,
            memory_threshold,
        )
        self.concept_state = new_state

        # Derive weakness_severity
        self.weakness_severity = self._derive_weakness_severity(
            new_durable_mastery_score,
            new_memory_score,
            proficient_threshold,
            memory_threshold,
        )

        # Record events
        self._record_event(
            MasteryUpdated(
                mastery_score_id=self.id.value,
                learner_enrollment_id=self.learner_enrollment_id.value,
                concept_id=self.concept_id.value,
                memory_score=new_memory_score,
                durable_mastery_score=new_durable_mastery_score,
                mastery_score_combined=new_mastery_score_combined,
                algorithm_version_id=algorithm_version_id.value,
            )
        )

        if new_state != old_state:
            self._record_event(
                ConceptStateChanged(
                    learner_enrollment_id=self.learner_enrollment_id.value,
                    concept_id=self.concept_id.value,
                    old_state=old_state,
                    new_state=new_state,
                )
            )

        if self.weakness_severity != WeaknessSeverity.NONE:
            self._record_event(
                WeakConceptDetected(
                    learner_enrollment_id=self.learner_enrollment_id.value,
                    concept_id=self.concept_id.value,
                    severity=self.weakness_severity,
                )
            )

    @staticmethod
    def _derive_concept_state(
        mastery_combined: float,
        memory: float,
        mastered_threshold: float,
        proficient_threshold: float,
        memory_threshold: float,
    ) -> ConceptState:
        """Derive the concept state from the mastery and memory scores."""
        if mastery_combined >= mastered_threshold:
            if memory < memory_threshold:
                return ConceptState.DECAYED
            return ConceptState.MASTERED
        if mastery_combined >= proficient_threshold:
            if memory < memory_threshold:
                return ConceptState.DECAYED
            return ConceptState.PROFICIENT
        if mastery_combined > 0.0:
            if mastery_combined >= 0.40:
                return ConceptState.DEVELOPING
            return ConceptState.NOVICE
        return ConceptState.UNSEEN

    @staticmethod
    def _derive_weakness_severity(
        durable_mastery: float,
        memory: float,
        proficient_threshold: float,
        memory_threshold: float,
    ) -> WeaknessSeverity:
        """Derive weakness severity from scores."""
        if durable_mastery >= proficient_threshold:
            return WeaknessSeverity.NONE
        if durable_mastery < 0.20:
            return WeaknessSeverity.SEVERE
        if durable_mastery < 0.35:
            return WeaknessSeverity.MODERATE
        if memory < memory_threshold:
            return WeaknessSeverity.MILD
        return WeaknessSeverity.NONE

    # ============================================================
    # Queries
    # ============================================================

    @property
    def memory_score(self) -> float:
        return self._memory_score

    @property
    def durable_mastery_score(self) -> float:
        return self._durable_mastery_score

    @property
    def mastery_score_combined(self) -> float:
        return self._mastery_score_combined

    @property
    def confidence_interval(self) -> float:
        return self._confidence_interval

    @property
    def is_weak(self) -> bool:
        return self.weakness_severity != WeaknessSeverity.NONE

    @property
    def is_mastered(self) -> bool:
        return self.concept_state == ConceptState.MASTERED

    @property
    def is_proficient_or_above(self) -> bool:
        return self.concept_state in (ConceptState.PROFICIENT, ConceptState.MASTERED)
