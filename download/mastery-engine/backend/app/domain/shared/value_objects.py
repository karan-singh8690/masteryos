"""Shared value objects — immutable, compared by value, no identity.

All value objects use ``@dataclass(frozen=True)`` for immutability.
Validation happens in ``__post_init__``; invalid values raise ``InvariantViolation``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TypeVar

from app.domain.shared.kernel import Difficulty, InvariantViolation, ValueObject

T = TypeVar("T", bound="Percentage")


# ============================================================
# Score Value Objects (per ADR-0008)
# ============================================================


@dataclass(frozen=True)
class MasteryValue(ValueObject):
    """A durable mastery score in the range [0.0, 1.0].

    Represents the Engine's estimate of a learner's durable understanding
    of a concept. Slower to rise and slower to fall than MemoryValue.
    Drives long-term decisions (graduation, interview readiness).
    """

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise InvariantViolation("MasteryValue", f"Must be between 0.0 and 1.0, got {self.value}")

    @classmethod
    def zero(cls) -> MasteryValue:
        return cls(0.0)

    @classmethod
    def full(cls) -> MasteryValue:
        return cls(1.0)

    def is_above(self, threshold: float) -> bool:
        return self.value >= threshold

    def is_below(self, threshold: float) -> bool:
        return self.value < threshold

    def clamp(self, min_val: float = 0.0, max_val: float = 1.0) -> MasteryValue:
        return MasteryValue(max(min_val, min(max_val, self.value)))


@dataclass(frozen=True)
class MemoryValue(ValueObject):
    """A short-term memory score in the range [0.0, 1.0].

    Represents the Engine's estimate of the probability that a learner
    can correctly recall a concept right now. Highly sensitive to recent
    attempts and decays sharply with time. Drives short-term scheduling
    decisions (drill again today, schedule a review).
    """

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise InvariantViolation("MemoryValue", f"Must be between 0.0 and 1.0, got {self.value}")

    @classmethod
    def zero(cls) -> MemoryValue:
        return cls(0.0)

    @classmethod
    def full(cls) -> MemoryValue:
        return cls(1.0)

    def is_below(self, threshold: float) -> bool:
        return self.value < threshold

    def decay(self, rate_per_day: float, days: float) -> MemoryValue:
        """Apply exponential decay over a time period."""
        if rate_per_day < 0:
            raise InvariantViolation("MemoryValue", "Decay rate must be non-negative")
        if days < 0:
            raise InvariantViolation("MemoryValue", "Days must be non-negative")
        decayed = self.value * (rate_per_day ** days)
        return MemoryValue(max(0.0, decayed))


@dataclass(frozen=True)
class Confidence(ValueObject):
    """A confidence interval around a mastery estimate.

    A narrower interval means the Engine is more certain about the estimate.
    Widens with sparse data; narrows with consistent evidence.
    """

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise InvariantViolation("Confidence", f"Must be between 0.0 and 1.0, got {self.value}")

    @classmethod
    def full(cls) -> Confidence:
        """Maximum uncertainty (interval covers the full range)."""
        return cls(1.0)

    @classmethod
    def none(cls) -> Confidence:
        """No uncertainty (exact estimate)."""
        return cls(0.0)

    def is_significant(self, threshold: float = 0.15) -> bool:
        """True if the confidence interval is narrow enough for reliable decisions."""
        return self.value < threshold


# ============================================================
# Quantitative Value Objects
# ============================================================


@dataclass(frozen=True)
class Percentage(ValueObject):
    """A percentage value in the range [0.0, 100.0]."""

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 100.0:
            raise InvariantViolation("Percentage", f"Must be between 0.0 and 100.0, got {self.value}")

    @classmethod
    def from_fraction(cls, fraction: float) -> Percentage:
        """Create from a fraction [0.0, 1.0]."""
        return cls(fraction * 100.0)

    def to_fraction(self) -> float:
        return self.value / 100.0


@dataclass(frozen=True)
class Duration(ValueObject):
    """A time duration in seconds. Always non-negative."""

    seconds: int

    def __post_init__(self) -> None:
        if self.seconds < 0:
            raise InvariantViolation("Duration", f"Must be non-negative, got {self.seconds}s")

    @classmethod
    def from_milliseconds(cls, ms: int) -> Duration:
        return cls(ms // 1000)

    @classmethod
    def from_minutes(cls, minutes: int) -> Duration:
        return cls(minutes * 60)

    @classmethod
    def from_hours(cls, hours: int) -> Duration:
        return cls(hours * 3600)

    @property
    def milliseconds(self) -> int:
        return self.seconds * 1000

    @property
    def minutes(self) -> float:
        return self.seconds / 60.0

    @property
    def hours(self) -> float:
        return self.seconds / 3600.0

    def __add__(self, other: Duration) -> Duration:
        return Duration(self.seconds + other.seconds)

    def __sub__(self, other: Duration) -> Duration:
        return Duration(max(0, self.seconds - other.seconds))


@dataclass(frozen=True)
class ReviewInterval(ValueObject):
    """The duration between a review and the next scheduled review.

    Expands on successful attempts; contracts on failures.
    Bounded by minimum and maximum values.
    """

    days: int

    MIN_DAYS = 1
    MAX_DAYS = 365

    def __post_init__(self) -> None:
        if self.days < self.MIN_DAYS:
            raise InvariantViolation("ReviewInterval", f"Must be >= {self.MIN_DAYS} days")
        if self.days > self.MAX_DAYS:
            raise InvariantViolation("ReviewInterval", f"Must be <= {self.MAX_DAYS} days")

    @classmethod
    def minimum(cls) -> ReviewInterval:
        return cls(cls.MIN_DAYS)

    @classmethod
    def maximum(cls) -> ReviewInterval:
        return cls(cls.MAX_DAYS)

    def expand(self, factor: float) -> ReviewInterval:
        """Expand the interval by a factor (e.g., 2.5 for spaced repetition)."""
        new_days = int(self.days * factor)
        return ReviewInterval(min(new_days, self.MAX_DAYS))

    def contract(self, factor: float) -> ReviewInterval:
        """Contract the interval by a factor (e.g., 0.3 for failure)."""
        new_days = max(int(self.days * factor), self.MIN_DAYS)
        return ReviewInterval(new_days)

    def to_timedelta(self) -> timedelta:
        return timedelta(days=self.days)


# ============================================================
# Identity Value Objects
# ============================================================


_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@dataclass(frozen=True)
class Email(ValueObject):
    """A validated email address (case-insensitive)."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _EMAIL_PATTERN.match(normalized):
            raise InvariantViolation("Email", f"Invalid email format: {self.value}")
        object.__setattr__(self, "value", normalized)

    @property
    def domain(self) -> str:
        return self.value.split("@")[1]

    @property
    def local_part(self) -> str:
        return self.value.split("@")[0]


@dataclass(frozen=True)
class CorrelationId(ValueObject):
    """A correlation ID for tracing requests across services."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise InvariantViolation("CorrelationId", "Must not be empty")


@dataclass(frozen=True)
class RequestId(ValueObject):
    """A unique request ID for tracing."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise InvariantViolation("RequestId", "Must not be empty")


# ============================================================
# Versioning Value Objects
# ============================================================


@dataclass(frozen=True)
class VersionNumber(ValueObject):
    """A monotonically increasing version number. Starts at 1."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise InvariantViolation("VersionNumber", f"Must be >= 1, got {self.value}")

    def next(self) -> VersionNumber:
        return VersionNumber(self.value + 1)

    def is_after(self, other: VersionNumber) -> bool:
        return self.value > other.value


# ============================================================
# Money Value Object
# ============================================================


@dataclass(frozen=True)
class Money(ValueObject):
    """A monetary amount with currency. Stored as integer cents to avoid float issues."""

    cents: int
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.cents < 0:
            raise InvariantViolation("Money", f"Amount must be non-negative, got {self.cents}")
        if len(self.currency) != 3:
            raise InvariantViolation("Money", f"Currency must be ISO 4217 (3 chars), got {self.currency}")

    @classmethod
    def from_dollars(cls, dollars: float, currency: str = "USD") -> Money:
        return cls(int(dollars * 100), currency)

    def to_dollars(self) -> float:
        return self.cents / 100.0

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise InvariantViolation("Money", f"Cannot add {self.currency} and {other.currency}")
        return Money(self.cents + other.cents, self.currency)

    def __sub__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise InvariantViolation("Money", f"Cannot subtract {self.currency} and {other.currency}")
        return Money(max(0, self.cents - other.cents), self.currency)


# ============================================================
# Date Range Value Object
# ============================================================


@dataclass(frozen=True)
class DateRange(ValueObject):
    """An inclusive date range [start_date, end_date]."""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise InvariantViolation(
                "DateRange",
                f"Start date {self.start_date} is after end date {self.end_date}",
            )

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def contains(self, d: date) -> bool:
        return self.start_date <= d <= self.end_date

    def overlaps(self, other: DateRange) -> bool:
        return self.start_date <= other.end_date and other.start_date <= self.end_date


# ============================================================
# Difficulty Estimate Value Object
# ============================================================


@dataclass(frozen=True)
class DifficultyEstimate(ValueObject):
    """An authored prior estimate of a question's difficulty.

    Used by the scheduler before sufficient attempt data accumulates.
    """

    level: Difficulty

    @classmethod
    def easy(cls) -> DifficultyEstimate:
        return cls(Difficulty.EASY)

    @classmethod
    def medium(cls) -> DifficultyEstimate:
        return cls(Difficulty.MEDIUM)

    @classmethod
    def hard(cls) -> DifficultyEstimate:
        return cls(Difficulty.HARD)

    @property
    def numeric(self) -> float:
        """Return a numeric representation for sorting."""
        mapping = {Difficulty.EASY: 0.25, Difficulty.MEDIUM: 0.50, Difficulty.HARD: 0.75}
        return mapping[self.level]


# ============================================================
# Discrimination Estimate Value Object
# ============================================================


@dataclass(frozen=True)
class DiscriminationEstimate(ValueObject):
    """An authored prior on how well a template separates mastered from non-mastered learners."""

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise InvariantViolation("DiscriminationEstimate", f"Must be 0.0–1.0, got {self.value}")
