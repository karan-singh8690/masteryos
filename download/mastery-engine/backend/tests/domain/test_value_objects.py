"""Comprehensive tests for shared value objects."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.domain.shared.kernel import Difficulty, InvariantViolation
from app.domain.shared.value_objects import (
    Confidence,
    DateRange,
    DifficultyEstimate,
    DiscriminationEstimate,
    Duration,
    Email,
    MasteryValue,
    MemoryValue,
    Money,
    Percentage,
    ReviewInterval,
    VersionNumber,
)


class TestMasteryValue:
    """Tests for MasteryValue — the durable mastery score."""

    def test_valid_value(self) -> None:
        mv = MasteryValue(0.75)
        assert mv.value == 0.75

    def test_zero(self) -> None:
        assert MasteryValue.zero().value == 0.0

    def test_full(self) -> None:
        assert MasteryValue.full().value == 1.0

    def test_below_zero_rejected(self) -> None:
        with pytest.raises(InvariantViolation, match="Must be between 0.0 and 1.0"):
            MasteryValue(-0.01)

    def test_above_one_rejected(self) -> None:
        with pytest.raises(InvariantViolation, match="Must be between 0.0 and 1.0"):
            MasteryValue(1.01)

    def test_is_above(self) -> None:
        assert MasteryValue(0.75).is_above(0.70)
        assert not MasteryValue(0.65).is_above(0.70)

    def test_is_below(self) -> None:
        assert MasteryValue(0.65).is_below(0.70)
        assert not MasteryValue(0.75).is_below(0.70)

    def test_clamp(self) -> None:
        assert MasteryValue(0.5).clamp(0.0, 1.0).value == 0.5

    def test_immutability(self) -> None:
        mv = MasteryValue(0.5)
        with pytest.raises(AttributeError):
            mv.value = 0.6  # type: ignore[misc]


class TestMemoryValue:
    """Tests for MemoryValue — the short-term memory score."""

    def test_valid_value(self) -> None:
        mem = MemoryValue(0.80)
        assert mem.value == 0.80

    def test_zero_and_full(self) -> None:
        assert MemoryValue.zero().value == 0.0
        assert MemoryValue.full().value == 1.0

    def test_below_zero_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            MemoryValue(-0.1)

    def test_above_one_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            MemoryValue(1.5)

    def test_decay(self) -> None:
        """Decay reduces the memory value over time."""
        mem = MemoryValue(0.90)
        decayed = mem.decay(rate_per_day=0.95, days=7)
        assert decayed.value < 0.90
        assert decayed.value > 0.0

    def test_decay_zero_days(self) -> None:
        """Decay with zero days returns the same value."""
        mem = MemoryValue(0.80)
        decayed = mem.decay(rate_per_day=0.95, days=0)
        assert decayed.value == 0.80

    def test_immutability(self) -> None:
        mem = MemoryValue(0.5)
        with pytest.raises(AttributeError):
            mem.value = 0.9  # type: ignore[misc]


class TestConfidence:
    """Tests for Confidence — the uncertainty around a mastery estimate."""

    def test_valid_value(self) -> None:
        c = Confidence(0.15)
        assert c.value == 0.15

    def test_full_uncertainty(self) -> None:
        assert Confidence.full().value == 1.0

    def test_no_uncertainty(self) -> None:
        assert Confidence.none().value == 0.0

    def test_is_significant(self) -> None:
        assert Confidence(0.10).is_significant()
        assert not Confidence(0.20).is_significant()

    def test_above_one_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            Confidence(1.5)


class TestPercentage:
    """Tests for Percentage."""

    def test_valid_value(self) -> None:
        p = Percentage(75.0)
        assert p.value == 75.0

    def test_from_fraction(self) -> None:
        p = Percentage.from_fraction(0.75)
        assert p.value == 75.0

    def test_to_fraction(self) -> None:
        assert Percentage(50.0).to_fraction() == 0.5

    def test_below_zero_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            Percentage(-1.0)

    def test_above_hundred_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            Percentage(101.0)


class TestDuration:
    """Tests for Duration."""

    def test_from_seconds(self) -> None:
        d = Duration(3600)
        assert d.seconds == 3600

    def test_from_milliseconds(self) -> None:
        d = Duration.from_milliseconds(5000)
        assert d.seconds == 5

    def test_from_minutes(self) -> None:
        d = Duration.from_minutes(30)
        assert d.seconds == 1800

    def test_from_hours(self) -> None:
        d = Duration.from_hours(2)
        assert d.seconds == 7200

    def test_milliseconds_property(self) -> None:
        assert Duration(10).milliseconds == 10000

    def test_minutes_property(self) -> None:
        assert Duration(60).minutes == 1.0

    def test_hours_property(self) -> None:
        assert Duration(3600).hours == 1.0

    def test_addition(self) -> None:
        assert (Duration(100) + Duration(200)).seconds == 300

    def test_subtraction(self) -> None:
        assert (Duration(300) - Duration(100)).seconds == 200

    def test_subtraction_clamped_to_zero(self) -> None:
        assert (Duration(100) - Duration(200)).seconds == 0

    def test_negative_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            Duration(-1)


class TestReviewInterval:
    """Tests for ReviewInterval."""

    def test_valid_days(self) -> None:
        ri = ReviewInterval(7)
        assert ri.days == 7

    def test_minimum(self) -> None:
        assert ReviewInterval.minimum().days == ReviewInterval.MIN_DAYS

    def test_maximum(self) -> None:
        assert ReviewInterval.maximum().days == ReviewInterval.MAX_DAYS

    def test_below_minimum_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            ReviewInterval(0)

    def test_above_maximum_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            ReviewInterval(400)

    def test_expand(self) -> None:
        ri = ReviewInterval(7)
        expanded = ri.expand(2.5)
        assert expanded.days == 17  # 7 * 2.5 = 17.5 → 17

    def test_contract(self) -> None:
        ri = ReviewInterval(10)
        contracted = ri.contract(0.3)
        assert contracted.days == 3  # 10 * 0.3 = 3

    def test_expand_capped_at_maximum(self) -> None:
        ri = ReviewInterval(300)
        expanded = ri.expand(10.0)
        assert expanded.days == ReviewInterval.MAX_DAYS

    def test_contract_floored_at_minimum(self) -> None:
        ri = ReviewInterval(2)
        contracted = ri.contract(0.1)
        assert contracted.days == ReviewInterval.MIN_DAYS

    def test_to_timedelta(self) -> None:
        assert ReviewInterval(7).to_timedelta() == timedelta(days=7)


class TestEmail:
    """Tests for Email value object."""

    def test_valid_email(self) -> None:
        e = Email("Alex@example.com")
        assert e.value == "alex@example.com"  # normalized to lowercase

    def test_strips_whitespace(self) -> None:
        e = Email("  alex@example.com  ")
        assert e.value == "alex@example.com"

    def test_domain(self) -> None:
        assert Email("alex@example.com").domain == "example.com"

    def test_local_part(self) -> None:
        assert Email("alex@example.com").local_part == "alex"

    def test_invalid_email_rejected(self) -> None:
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "alex@",
            "alex@.com",
            "alex@example",
            "",
        ]
        for invalid in invalid_emails:
            with pytest.raises(InvariantViolation):
                Email(invalid)

    def test_immutability(self) -> None:
        e = Email("alex@example.com")
        with pytest.raises(AttributeError):
            e.value = "bob@example.com"  # type: ignore[misc]


class TestVersionNumber:
    """Tests for VersionNumber."""

    def test_valid_version(self) -> None:
        v = VersionNumber(1)
        assert v.value == 1

    def test_zero_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            VersionNumber(0)

    def test_negative_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            VersionNumber(-1)

    def test_next(self) -> None:
        assert VersionNumber(1).next().value == 2

    def test_is_after(self) -> None:
        assert VersionNumber(2).is_after(VersionNumber(1))
        assert not VersionNumber(1).is_after(VersionNumber(2))


class TestMoney:
    """Tests for Money value object."""

    def test_from_dollars(self) -> None:
        m = Money.from_dollars(19.99)
        assert m.cents == 1999

    def test_to_dollars(self) -> None:
        assert Money(1999).to_dollars() == 19.99

    def test_addition(self) -> None:
        assert (Money(1000) + Money(500)).cents == 1500

    def test_subtraction(self) -> None:
        assert (Money(1000) - Money(300)).cents == 700

    def test_currency_mismatch_addition_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            Money(100, "USD") + Money(100, "EUR")

    def test_negative_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            Money(-100)

    def test_invalid_currency_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            Money(100, "DOLLAR")


class TestDateRange:
    """Tests for DateRange."""

    def test_valid_range(self) -> None:
        dr = DateRange(date(2026, 1, 1), date(2026, 1, 31))
        assert dr.days == 31

    def test_same_day(self) -> None:
        dr = DateRange(date(2026, 1, 1), date(2026, 1, 1))
        assert dr.days == 1

    def test_start_after_end_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            DateRange(date(2026, 2, 1), date(2026, 1, 1))

    def test_contains(self) -> None:
        dr = DateRange(date(2026, 1, 1), date(2026, 1, 31))
        assert dr.contains(date(2026, 1, 15))
        assert not dr.contains(date(2026, 2, 1))

    def test_overlaps(self) -> None:
        dr1 = DateRange(date(2026, 1, 1), date(2026, 1, 15))
        dr2 = DateRange(date(2026, 1, 10), date(2026, 1, 20))
        dr3 = DateRange(date(2026, 2, 1), date(2026, 2, 15))
        assert dr1.overlaps(dr2)
        assert not dr1.overlaps(dr3)


class TestDifficultyEstimate:
    """Tests for DifficultyEstimate."""

    def test_easy(self) -> None:
        assert DifficultyEstimate.easy().level == Difficulty.EASY

    def test_medium(self) -> None:
        assert DifficultyEstimate.medium().level == Difficulty.MEDIUM

    def test_hard(self) -> None:
        assert DifficultyEstimate.hard().level == Difficulty.HARD

    def test_numeric_easy(self) -> None:
        assert DifficultyEstimate.easy().numeric == 0.25

    def test_numeric_hard(self) -> None:
        assert DifficultyEstimate.hard().numeric == 0.75


class TestDiscriminationEstimate:
    """Tests for DiscriminationEstimate."""

    def test_valid_value(self) -> None:
        de = DiscriminationEstimate(0.65)
        assert de.value == 0.65

    def test_below_zero_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            DiscriminationEstimate(-0.1)

    def test_above_one_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            DiscriminationEstimate(1.1)
