"""Scheduling context — domain events.

Domain events are immutable records of something that *happened* in the
Scheduling context. They are named in past tense and carry all the data
a subscriber needs to react.

All events inherit from :class:`DomainEvent` (which provides ``event_id``
and ``occurred_at``) and use ``@dataclass(frozen=True, kw_only=True)``
so that required fields can follow the inherited defaulted fields
without ordering issues.

These events are *pure data*. They contain no behaviour and no side
effects. Subscribers (queue materialisation, scheduling analytics,
audit) live in the application and infrastructure layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from app.domain.shared.ids import (
    DailyQueueId,
    LearnerEnrollmentId,
    SchedulingConfigId,
    SubjectId,
)
from app.domain.shared.kernel import DomainEvent


# ============================================================
# DailyQueue events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class DailyQueueGenerated(DomainEvent):
    """Emitted when a new DailyQueue is generated for an enrollment.

    Fired by :meth:`DailyQueue.generate`. The queue is in ``active``
    status. The scheduler materialises the question instances for the
    listed ``(template_version_id, seed)`` pairs on demand; subscribers
    may pre-warm the rendered-question cache for the seeds.

    ``question_template_version_ids`` and ``question_seeds`` are parallel
    arrays — the i-th seed materialises the i-th template version.
    """

    queue_id: DailyQueueId
    learner_enrollment_id: LearnerEnrollmentId
    queue_date: date
    question_template_version_ids: tuple[UUID, ...] = field(default_factory=tuple)
    question_seeds: tuple[int, ...] = field(default_factory=tuple)


@dataclass(frozen=True, kw_only=True)
class DailyQueueCompleted(DomainEvent):
    """Emitted when a DailyQueue transitions to ``completed``.

    Fired by :meth:`DailyQueue.mark_completed`. Subscribers may release
    any per-queue computation state and record streak evidence.
    """

    queue_id: DailyQueueId
    learner_enrollment_id: LearnerEnrollmentId
    completed_at: datetime


@dataclass(frozen=True, kw_only=True)
class DailyQueueExpired(DomainEvent):
    """Emitted when a DailyQueue transitions to ``expired`` without completion.

    Fired by :meth:`DailyQueue.expire`. The queue's window has elapsed
    and any unanswered items are abandoned. Subscribers may record
    missed-evidence for the scheduling model.
    """

    queue_id: DailyQueueId
    learner_enrollment_id: LearnerEnrollmentId
    expired_at: datetime


# ============================================================
# SchedulingConfig events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class SchedulingConfigCreated(DomainEvent):
    """Emitted when a new SchedulingConfig is created for a Subject.

    Fired by :meth:`SchedulingConfig.create`. The config starts at
    version 1 in ``active`` status. Subscribers may warm the scheduling
    cache for the Subject and notify the enrolment projection.
    """

    config_id: SchedulingConfigId
    subject_id: SubjectId
    version: int


@dataclass(frozen=True, kw_only=True)
class SchedulingConfigUpdated(DomainEvent):
    """Emitted when a SchedulingConfig's parameters are updated.

    Fired by :meth:`SchedulingConfig.update_parameters`. Updating the
    parameters bumps the version — old versions remain immutable so the
    scheduling history is reproducible (ADR-0011, triple versioning).

    ``changed_fields`` maps field name → new value for any field that
    actually changed. Subscribers (scheduling workers) may need to
    re-pull the config to pick up new bounds or thresholds.
    """

    config_id: SchedulingConfigId
    subject_id: SubjectId
    new_version: int
    previous_version: int
    changed_fields: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class SchedulingConfigDeactivated(DomainEvent):
    """Emitted when a SchedulingConfig is deactivated.

    Fired by :meth:`SchedulingConfig.deactivate`. Deactivation pauses
    new queue generation for the Subject without destroying the config
    — historical queues remain reproducible from their stored parameters.
    """

    config_id: SchedulingConfigId
    subject_id: SubjectId
    deactivated_at: datetime


__all__ = [
    "DailyQueueCompleted",
    "DailyQueueExpired",
    "DailyQueueGenerated",
    "SchedulingConfigCreated",
    "SchedulingConfigDeactivated",
    "SchedulingConfigUpdated",
]
