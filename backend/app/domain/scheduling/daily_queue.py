"""Scheduling context — DailyQueue aggregate root.

The :class:`DailyQueue` is the aggregate root of a single learner's
question queue for a single day. It pins, for a given
:class:`LearnerEnrollmentId` and ``queue_date``, the ordered set of
``(template_version_id, question_seed)`` pairs that the scheduler chose,
plus the set of completed item IDs as the learner works through them.

Lifecycle (state machine)::

    active ──mark_completed()──► completed
        │
        └──expire()────────────► expired

Both ``completed`` and ``expired`` are terminal. Once a queue is in
either state, no further items may be added.

Invariants enforced:
- The number of ``(template_version_id, seed)`` pairs must be in
  ``[10, 30]`` (the per-day attention budget).
- ``question_template_version_ids`` and ``question_seeds`` must be the
  same length (they are parallel arrays).
- ``add_completed_item`` cannot be called once the queue is in a
  terminal state.

The queue is **immutable in shape** once generated: the
``(template_version_id, seed)`` pairs are pinned for reproducibility
(ADR-0011). Only ``completed_items``, ``status``, and the
``completed_at`` timestamp are mutable.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from app.domain.scheduling.events import (
    DailyQueueCompleted,
    DailyQueueExpired,
    DailyQueueGenerated,
)
from app.domain.scheduling.exceptions import (
    InvalidQueueSize,
    SchedulingError,
)
from app.domain.shared.ids import DailyQueueId, LearnerEnrollmentId
from app.domain.shared.kernel import (
    AggregateRoot,
    InvalidStateTransition,
    InvariantViolation,
)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class DailyQueueStatus:
    """Status of a daily queue (string constants, not an enum)."""

    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"

    _TERMINAL: frozenset[str] = frozenset({COMPLETED, EXPIRED})


class DailyQueue(AggregateRoot):
    """The DailyQueue aggregate root.

    Holds the queue's identity, the pinned ``(template_version_id,
    seed)`` pairs, the running set of completed item IDs, and lifecycle
    state. All mutations go through methods on this class, which
    enforce invariants and emit domain events via
    :meth:`AggregateRoot._record_event`.

    The public constructor is intended for **reconstitution** from
    persistence. To create a *new* queue, use :meth:`DailyQueue.generate`.
    """

    #: Inclusive bounds on the number of items in a queue.
    MIN_QUEUE_SIZE: int = 10
    MAX_QUEUE_SIZE: int = 30

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: DailyQueueId,
        learner_enrollment_id: LearnerEnrollmentId,
        queue_date: date,
        question_template_version_ids: list[UUID] | None = None,
        question_seeds: list[int] | None = None,
        completed_items: list[Any] | None = None,
        status: str = DailyQueueStatus.ACTIVE,
        generated_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self._id: DailyQueueId = id
        self._learner_enrollment_id: LearnerEnrollmentId = learner_enrollment_id
        self._queue_date: date = queue_date
        self._question_template_version_ids: list[UUID] = list(
            question_template_version_ids or []
        )
        self._question_seeds: list[int] = list(question_seeds or [])
        self._completed_items: list[Any] = list(completed_items or [])
        self._status: str = status
        self._generated_at: datetime = generated_at or _utcnow()
        self._completed_at: datetime | None = completed_at
        self._validate_invariants()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def generate(
        cls,
        enrollment_id: LearnerEnrollmentId,
        queue_date: date,
        template_version_ids: list[UUID],
        seeds: list[int],
    ) -> DailyQueue:
        """Generate a new DailyQueue for an enrollment on a given date.

        Args:
            enrollment_id: The learner enrollment this queue belongs to.
            queue_date: The calendar date the queue is for (UTC).
            template_version_ids: Ordered list of question-template
                version IDs to draw from.
            seeds: Ordered list of parameter seeds — the i-th seed
                materialises the i-th template version. Must be the
                same length as ``template_version_ids``.

        Returns:
            A newly created, un-persisted :class:`DailyQueue` in
            ``active`` status. The caller must add it to the repository
            and call :meth:`collect_events` to publish the recorded
            events.

        Raises:
            InvalidQueueSize: If the number of items is out of bounds.
            InvariantViolation: If the two arrays have different
                lengths.
        """
        queue_id = DailyQueueId.generate()
        queue = cls(
            id=queue_id,
            learner_enrollment_id=enrollment_id,
            queue_date=queue_date,
            question_template_version_ids=list(template_version_ids),
            question_seeds=list(seeds),
            completed_items=[],
            status=DailyQueueStatus.ACTIVE,
        )
        queue._record_event(
            DailyQueueGenerated(
                queue_id=queue.id,
                learner_enrollment_id=enrollment_id,
                queue_date=queue_date,
                question_template_version_ids=tuple(queue._question_template_version_ids),
                question_seeds=tuple(queue._question_seeds),
            )
        )
        return queue

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> DailyQueueId:
        """The queue's unique identifier."""
        return self._id

    @property
    def learner_enrollment_id(self) -> LearnerEnrollmentId:
        """The enrollment this queue belongs to."""
        return self._learner_enrollment_id

    @property
    def queue_date(self) -> date:
        """The calendar date this queue is for."""
        return self._queue_date

    @property
    def question_template_version_ids(self) -> list[UUID]:
        """A copy of the pinned template-version list."""
        return list(self._question_template_version_ids)

    @property
    def question_seeds(self) -> list[int]:
        """A copy of the pinned seed list."""
        return list(self._question_seeds)

    @property
    def completed_items(self) -> list[Any]:
        """A copy of the completed-item list."""
        return list(self._completed_items)

    @property
    def status(self) -> str:
        """The queue's lifecycle status."""
        return self._status

    @property
    def generated_at(self) -> datetime:
        """When this queue was generated."""
        return self._generated_at

    @property
    def completed_at(self) -> datetime | None:
        """When this queue was marked completed (or ``None``)."""
        return self._completed_at

    @property
    def is_active(self) -> bool:
        """True if the queue is still accepting completions."""
        return self._status == DailyQueueStatus.ACTIVE

    @property
    def is_terminal(self) -> bool:
        """True if the queue is in a terminal state (completed/expired)."""
        return self._status in DailyQueueStatus._TERMINAL

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants; raise on failure."""
        if len(self._question_template_version_ids) != len(self._question_seeds):
            raise InvariantViolation(
                "DailyQueue",
                "question_template_version_ids and question_seeds must have the same length "
                f"({len(self._question_template_version_ids)} vs {len(self._question_seeds)})",
            )
        size = len(self._question_template_version_ids)
        if not (self.MIN_QUEUE_SIZE <= size <= self.MAX_QUEUE_SIZE):
            raise InvalidQueueSize(
                size,
                min_size=self.MIN_QUEUE_SIZE,
                max_size=self.MAX_QUEUE_SIZE,
            )
        for seed in self._question_seeds:
            if not isinstance(seed, int) or isinstance(seed, bool):
                raise InvariantViolation(
                    "DailyQueue",
                    f"question seeds must be ints, got {type(seed).__name__}: {seed!r}",
                )
        if self._status not in (
            DailyQueueStatus.ACTIVE,
            DailyQueueStatus.COMPLETED,
            DailyQueueStatus.EXPIRED,
        ):
            raise InvariantViolation(
                "DailyQueue",
                f"unknown status {self._status!r}",
            )

    def _assert_active(self, action: str) -> None:
        """Raise :class:`InvalidStateTransition` unless the queue is active."""
        if self._status != DailyQueueStatus.ACTIVE:
            raise InvalidStateTransition(
                entity="DailyQueue",
                current_state=self._status,
                attempted_action=action,
            )

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def add_completed_item(self, item_id: Any) -> None:
        """Record that a queue item has been completed.

        Idempotent — adding an already-completed item is a no-op (no
        event recorded). Only valid while the queue is in ``active``
        status.

        Raises:
            InvalidStateTransition: If the queue is in a terminal state.
        """
        self._assert_active("add_completed_item")
        if item_id in self._completed_items:
            return
        self._completed_items.append(item_id)

    def mark_completed(self, now: datetime | None = None) -> None:
        """Transition the queue from ``active`` to ``completed``.

        Pre-state: ``active``.
        Post-state: ``completed`` with ``completed_at`` set.

        Raises:
            InvalidStateTransition: If the queue is already in a
                terminal state.
        """
        if self._status == DailyQueueStatus.COMPLETED:
            return  # idempotent
        self._assert_active("mark_completed")
        timestamp = now or _utcnow()
        self._status = DailyQueueStatus.COMPLETED
        self._completed_at = timestamp
        self._record_event(
            DailyQueueCompleted(
                queue_id=self._id,
                learner_enrollment_id=self._learner_enrollment_id,
                completed_at=timestamp,
            )
        )

    def expire(self, now: datetime | None = None) -> None:
        """Transition the queue from ``active`` to ``expired``.

        Used when the queue's calendar day has elapsed without
        completion. The queue becomes terminal; any unanswered items
        are abandoned (subscribers record missed-evidence).

        Pre-state: ``active``.
        Post-state: ``expired``.

        Raises:
            InvalidStateTransition: If the queue is already in a
                terminal state.
        """
        if self._status == DailyQueueStatus.EXPIRED:
            return  # idempotent
        if self._status == DailyQueueStatus.COMPLETED:
            raise SchedulingError(
                f"Cannot expire already-completed DailyQueue {self._id}",
                code="CANNOT_EXPIRE_COMPLETED_QUEUE",
            )
        self._assert_active("expire")
        timestamp = now or _utcnow()
        self._status = DailyQueueStatus.EXPIRED
        self._record_event(
            DailyQueueExpired(
                queue_id=self._id,
                learner_enrollment_id=self._learner_enrollment_id,
                expired_at=timestamp,
            )
        )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"DailyQueue(id={self._id}, "
            f"enrollment_id={self._learner_enrollment_id}, "
            f"date={self._queue_date}, status={self._status!r}, "
            f"size={len(self._question_template_version_ids)})"
        )


__all__ = ["DailyQueue", "DailyQueueStatus"]
