"""Assessment context — domain events (immutable, past-tense records of occurrences)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.shared.kernel import DomainEvent, ScoringOutcome, AttemptIntent


@dataclass(frozen=True, kw_only=True)
class QuestionInstanceServed(DomainEvent):
    """A question was served to a learner."""

    instance_id: UUID
    learner_enrollment_id: UUID
    template_version_id: UUID


@dataclass(frozen=True, kw_only=True)
class QuestionInstanceAnswered(DomainEvent):
    """A learner answered a question."""

    instance_id: UUID
    attempt_id: UUID
    scoring_outcome: ScoringOutcome


@dataclass(frozen=True, kw_only=True)
class QuestionInstanceAbandoned(DomainEvent):
    """A learner abandoned a question."""

    instance_id: UUID


@dataclass(frozen=True, kw_only=True)
class AttemptRecorded(DomainEvent):
    """An attempt was recorded (the atomic unit of learning evidence).

    This is the most critical event in the system. It carries the triple
    versioning references (content_version_id, template_version_id,
    algorithm_version_id) for historical reproducibility (ADR-0011).
    """

    attempt_id: UUID
    learner_enrollment_id: UUID
    concept_ids: tuple[UUID, ...]
    scoring_outcome: ScoringOutcome
    content_version_id: UUID
    template_version_id: UUID
    algorithm_version_id: UUID
    hint_used: bool
    attempt_intent: AttemptIntent
