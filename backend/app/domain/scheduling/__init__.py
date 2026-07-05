"""Scheduling bounded context — domain layer.

Contains: aggregates, entities, value objects, domain services, domain events,
context-specific exceptions, and the abstract repository contracts.

This package is pure Python — no I/O, no framework dependencies. All
imports are from :mod:`app.domain.shared` (the shared kernel) or from
within this package.

Public surface:

- **Aggregates**: :class:`DailyQueue`
- **Entities**: :class:`SchedulingConfig`
- **Events**: :class:`DailyQueueGenerated`, :class:`DailyQueueCompleted`,
  :class:`DailyQueueExpired`, :class:`SchedulingConfigCreated`,
  :class:`SchedulingConfigUpdated`, :class:`SchedulingConfigDeactivated`
- **Exceptions**: :class:`SchedulingError` and its subclasses
- **Repositories**: :class:`SchedulingConfigRepository`,
  :class:`DailyQueueRepository`
"""

from __future__ import annotations

from app.domain.scheduling.daily_queue import DailyQueue, DailyQueueStatus
from app.domain.scheduling.events import (
    DailyQueueCompleted,
    DailyQueueExpired,
    DailyQueueGenerated,
    SchedulingConfigCreated,
    SchedulingConfigDeactivated,
    SchedulingConfigUpdated,
)
from app.domain.scheduling.exceptions import (
    InvalidCooldownDuration,
    InvalidQueueSize,
    InvalidThresholdRange,
    SchedulingError,
)
from app.domain.scheduling.repository import (
    DailyQueueRepository,
    SchedulingConfigRepository,
)
from app.domain.scheduling.scheduling_config import SchedulingConfig

__all__ = [
    # Aggregates / entities
    "DailyQueue",
    "DailyQueueStatus",
    "SchedulingConfig",
    # Events
    "DailyQueueCompleted",
    "DailyQueueExpired",
    "DailyQueueGenerated",
    "SchedulingConfigCreated",
    "SchedulingConfigDeactivated",
    "SchedulingConfigUpdated",
    # Exceptions
    "InvalidCooldownDuration",
    "InvalidQueueSize",
    "InvalidThresholdRange",
    "SchedulingError",
    # Repositories
    "DailyQueueRepository",
    "SchedulingConfigRepository",
]
