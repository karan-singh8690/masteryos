"""Mastery context — domain events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.domain.shared.kernel import (
    ConceptState,
    DomainEvent,
    ReviewPriority,
    ScoringOutcome,
    WeaknessSeverity,
)


@dataclass(frozen=True, kw_only=True)
class MasteryUpdated(DomainEvent):
    """A mastery score was updated after an attempt."""

    mastery_score_id: UUID
    learner_enrollment_id: UUID
    concept_id: UUID
    memory_score: float
    durable_mastery_score: float
    mastery_score_combined: float
    algorithm_version_id: UUID


@dataclass(frozen=True, kw_only=True)
class ConceptStateChanged(DomainEvent):
    """A concept's mastery state transitioned."""

    learner_enrollment_id: UUID
    concept_id: UUID
    old_state: ConceptState
    new_state: ConceptState


@dataclass(frozen=True, kw_only=True)
class WeakConceptDetected(DomainEvent):
    """A concept fell below the mastery threshold."""

    learner_enrollment_id: UUID
    concept_id: UUID
    severity: WeaknessSeverity


@dataclass(frozen=True, kw_only=True)
class ReviewScheduled(DomainEvent):
    """A review was scheduled for a concept."""

    review_id: UUID
    learner_enrollment_id: UUID
    concept_id: UUID
    due_at: datetime
    priority: ReviewPriority
    interval_days: int


@dataclass(frozen=True, kw_only=True)
class AlgorithmVersionPublished(DomainEvent):
    """A new mastery algorithm version was promoted to production."""

    algorithm_version_id: UUID
    version_number: int
    previous_version_number: int | None


@dataclass(frozen=True, kw_only=True)
class LearnerMisconceptionCleared(DomainEvent):
    """A learner's misconception was cleared (mastery demonstrated)."""

    learner_misconception_id: UUID
