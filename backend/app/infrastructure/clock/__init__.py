"""Injectable clock abstraction.

Avoids direct datetime.now() inside infrastructure code, enabling
deterministic testing by injecting a fixed clock.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone


class Clock(ABC):
    """Abstract clock for getting the current time."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current UTC datetime."""
        ...

    @abstractmethod
    def utcnow(self) -> datetime:
        """Return the current UTC datetime (alias for now())."""
        ...


class SystemClock(Clock):
    """Production clock — uses the system clock."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def utcnow(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock(Clock):
    """Test clock — returns a fixed time. Useful for deterministic tests."""

    def __init__(self, fixed_time: datetime) -> None:
        self._fixed_time = fixed_time

    def now(self) -> datetime:
        return self._fixed_time

    def utcnow(self) -> datetime:
        return self._fixed_time

    def advance(self, seconds: int = 0, minutes: int = 0, hours: int = 0, days: int = 0) -> None:
        """Advance the fixed time by the given duration."""
        from datetime import timedelta
        self._fixed_time += timedelta(seconds=seconds, minutes=minutes, hours=hours, days=days)

    def set(self, new_time: datetime) -> None:
        """Set the fixed time to a new value."""
        self._fixed_time = new_time
