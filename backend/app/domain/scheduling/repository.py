"""Scheduling context — abstract repository interfaces.

This module defines the *contracts* for loading and persisting the
Scheduling-context aggregates and entities. Each interface is an
abstract base class — no implementation is provided here. Concrete
implementations live in the infrastructure layer.

Keeping the interfaces in the domain layer ensures that application
services depend only on the domain, not on infrastructure details.

Async contract:
- All methods are ``async`` to match the async SQLAlchemy pattern the
  rest of the backend uses.
- The application layer ``await``s repository calls inside an async
  unit-of-work.

Concurrency contract:
- Implementations should enforce optimistic concurrency for
  :class:`SchedulingConfig` via the ``version`` field. A stale-version
  save must raise a domain error.
- :class:`DailyQueue` is mutated within a single day; implementations
  should still enforce optimistic concurrency via the ``status`` and
  ``completed_items`` fields.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date

from app.domain.scheduling.daily_queue import DailyQueue
from app.domain.scheduling.scheduling_config import SchedulingConfig
from app.domain.shared.ids import (
    DailyQueueId,
    LearnerEnrollmentId,
    SchedulingConfigId,
    SubjectId,
)
from app.domain.shared.kernel import EntityNotFound


# ============================================================
# SchedulingConfig
# ============================================================


class SchedulingConfigRepository(ABC):
    """Abstract repository for the :class:`SchedulingConfig` entity.

    Implementations must:
    - Load the :class:`SchedulingConfig` (including its version and
      active flag) or return ``None``.
    - Persist the entity on :meth:`save`, bumping the version column
      atomically and rejecting stale versions.
    - Enforce at most one ``active`` config per Subject (the storage
      layer should surface a unique partial index on
      ``(subject_id) WHERE is_active``).
    """

    @abstractmethod
    async def get_by_id(self, config_id: SchedulingConfigId) -> SchedulingConfig | None:
        """Load a SchedulingConfig by ID.

        Returns the :class:`SchedulingConfig`, or ``None`` if no config
        exists with that ID.
        """

    @abstractmethod
    async def get_active_by_subject(self, subject_id: SubjectId) -> SchedulingConfig | None:
        """Load the currently-active SchedulingConfig for a Subject.

        At most one config per Subject is ``active`` at any time. Older
        versions remain in storage for historical reproducibility.

        Args:
            subject_id: The Subject to look up the active config for.

        Returns:
            The active :class:`SchedulingConfig`, or ``None`` if the
            Subject has no active config (e.g., it has been
            deactivated, or never had one).
        """

    @abstractmethod
    async def get_by_subject_and_version(
        self,
        subject_id: SubjectId,
        version: int,
    ) -> SchedulingConfig | None:
        """Load a specific historical version of a Subject's config.

        Used to reproduce a historical DailyQueue deterministically —
        the queue pins the config version it was generated under.

        Args:
            subject_id: The Subject to scope the lookup to.
            version: The version number to load (>= 1).

        Returns:
            The :class:`SchedulingConfig` at that version, or ``None``
            if no such version exists for the Subject.
        """

    @abstractmethod
    async def add(self, config: SchedulingConfig) -> None:
        """Add a *new* SchedulingConfig to the repository.

        Use this for configs that have never been persisted (i.e.,
        created via :meth:`SchedulingConfig.create`). For configs loaded
        via ``get_by_*`` and then modified, use :meth:`save`.

        Args:
            config: The new :class:`SchedulingConfig` to persist.

        Raises:
            DuplicateEntity: If a config with the same Subject already
                exists at the same version, or if a config is already
                active for the Subject.
        """

    @abstractmethod
    async def save(self, config: SchedulingConfig) -> None:
        """Persist changes to an *existing* SchedulingConfig.

        Args:
            config: The modified :class:`SchedulingConfig` to persist.

        Raises:
            EntityNotFound: If the config has been deleted by another
                transaction since it was loaded.
            DuplicateEntity: If the version is stale (concurrent
                modification by another transaction).
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, config_id: SchedulingConfigId) -> SchedulingConfig:
        """Load a SchedulingConfig by ID, raising :class:`EntityNotFound` if absent."""
        config = await self.get_by_id(config_id)
        if config is None:
            raise EntityNotFound("SchedulingConfig", config_id)
        return config


# ============================================================
# DailyQueue
# ============================================================


class DailyQueueRepository(ABC):
    """Abstract repository for the :class:`DailyQueue` aggregate.

    Implementations must:
    - Load the full :class:`DailyQueue` aggregate (root + the pinned
      ``(template_version_id, seed)`` pairs + completed items) or
      return ``None``.
    - Persist the full aggregate on :meth:`save`, including the
      completed-items collection.
    - Enforce uniqueness of ``(learner_enrollment_id, queue_date)`` —
      each enrollment has at most one queue per calendar day.
    """

    @abstractmethod
    async def get_by_id(self, queue_id: DailyQueueId) -> DailyQueue | None:
        """Load a DailyQueue by ID.

        Returns the fully reconstituted :class:`DailyQueue` aggregate,
        or ``None`` if no queue exists with that ID.
        """

    @abstractmethod
    async def get_by_enrollment_and_date(
        self,
        enrollment_id: LearnerEnrollmentId,
        queue_date: date,
    ) -> DailyQueue | None:
        """Load a learner's DailyQueue for a specific date.

        Args:
            enrollment_id: The learner enrollment to scope the lookup to.
            queue_date: The calendar date to look up.

        Returns:
            The matching :class:`DailyQueue`, or ``None`` if no queue
            was generated for that enrollment on that date.
        """

    @abstractmethod
    async def list_by_enrollment(
        self,
        enrollment_id: LearnerEnrollmentId,
        *,
        limit: int = 30,
        offset: int = 0,
    ) -> Sequence[DailyQueue]:
        """List a learner's most recent DailyQueues, newest first.

        Args:
            enrollment_id: The learner enrollment to list queues for.
            limit: Maximum number of queues to return (default 30).
            offset: Pagination offset.

        Returns:
            A sequence of :class:`DailyQueue` aggregates, ordered by
            ``queue_date`` descending. Empty if the learner has no
            queues (or the offset is past the end).
        """

    @abstractmethod
    async def add(self, queue: DailyQueue) -> None:
        """Add a *new* DailyQueue to the repository.

        Args:
            queue: The new :class:`DailyQueue` aggregate to persist.

        Raises:
            DuplicateEntity: If a queue already exists for the same
                ``(enrollment_id, queue_date)`` pair.
        """

    @abstractmethod
    async def save(self, queue: DailyQueue) -> None:
        """Persist changes to an *existing* DailyQueue.

        Args:
            queue: The modified :class:`DailyQueue` aggregate to persist.

        Raises:
            EntityNotFound: If the queue has been deleted by another
                transaction since it was loaded.
            DuplicateEntity: If the version is stale.
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, queue_id: DailyQueueId) -> DailyQueue:
        """Load a DailyQueue by ID, raising :class:`EntityNotFound` if absent."""
        queue = await self.get_by_id(queue_id)
        if queue is None:
            raise EntityNotFound("DailyQueue", queue_id)
        return queue


__all__ = [
    "DailyQueueRepository",
    "SchedulingConfigRepository",
]
