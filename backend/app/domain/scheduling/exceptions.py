"""Scheduling context — domain-specific exceptions.

These exceptions are raised by the Scheduling-context aggregates when
invariants are violated or invalid state transitions are attempted.
They are *narrow* subclasses of :class:`DomainError` so that callers can
catch a specific failure mode without inspecting error messages.

All exceptions are pure Python and carry no framework dependencies.
"""

from __future__ import annotations

from typing import Any

from app.domain.shared.kernel import DomainError


class SchedulingError(DomainError):
    """Base class for all Scheduling-context domain errors.

    Catch this to handle any scheduling-specific failure generically.
    """


class InvalidQueueSize(SchedulingError):
    """Raised when a DailyQueue is generated with an out-of-bounds size.

    Invariant: a daily queue must contain between 10 and 30 question
    items (inclusive). Smaller queues do not produce enough evidence for
    mastery recompute; larger queues exceed the per-session attention
    budget and inflate the review backlog.
    """

    def __init__(self, size: int, *, min_size: int = 10, max_size: int = 30) -> None:
        super().__init__(
            f"Invalid daily queue size {size}: must be between {min_size} and {max_size}",
            code="INVALID_QUEUE_SIZE",
        )
        self.size = size
        self.min_size = min_size
        self.max_size = max_size


class InvalidCooldownDuration(SchedulingError):
    """Raised when a cooldown duration falls outside the allowed range.

    Invariant: the cooldown between two attempts on the same concept
    must be between 5 and 240 minutes (inclusive). Shorter cooldowns
    enable brute-force memorisation attacks on the mastery signal;
    longer cooldowns starve the spaced-repetition scheduler of signal.
    """

    def __init__(self, minutes: int, *, min_minutes: int = 5, max_minutes: int = 240) -> None:
        super().__init__(
            f"Invalid cooldown duration {minutes}m: must be between "
            f"{min_minutes}m and {max_minutes}m",
            code="INVALID_COOLDOWN_DURATION",
        )
        self.minutes = minutes
        self.min_minutes = min_minutes
        self.max_minutes = max_minutes


class InvalidThresholdRange(SchedulingError):
    """Raised when a mastery/memory threshold is outside [0.0, 1.0].

    Invariant: mastery and memory thresholds are probabilities and must
    lie in the closed interval [0.0, 1.0]. Additionally, the
    ``mastered`` threshold must strictly exceed the ``proficient``
    threshold (graduation is a stronger bar than proficiency).
    """

    def __init__(self, name: str, value: Any, *, reason: str | None = None) -> None:
        detail = reason or f"{name}={value} is out of range [0.0, 1.0]"
        super().__init__(
            f"Invalid threshold {detail}",
            code="INVALID_THRESHOLD_RANGE",
        )
        self.name = name
        self.value = value
        self.reason = reason


__all__ = [
    "InvalidCooldownDuration",
    "InvalidQueueSize",
    "InvalidThresholdRange",
    "SchedulingError",
]
