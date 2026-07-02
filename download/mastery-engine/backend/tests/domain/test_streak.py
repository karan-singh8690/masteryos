"""Tests for the Streak aggregate (Learning context)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.domain.learning.streak import Streak
from app.domain.learning.events import StreakReset, StreakUpdated
from app.domain.shared.ids import LearnerEnrollmentId


class TestStreak:
    """Tests for the Streak aggregate."""

    def test_first_study_sets_streak_to_one(self) -> None:
        enrollment_id = LearnerEnrollmentId.generate()
        streak = Streak(learner_enrollment_id=enrollment_id)
        streak.collect_events()

        streak.record_study(date(2026, 7, 1))

        assert streak.current_streak == 1
        assert streak.longest_streak == 1
        assert streak.last_study_date == date(2026, 7, 1)

    def test_consecutive_day_increments(self) -> None:
        enrollment_id = LearnerEnrollmentId.generate()
        streak = Streak(
            learner_enrollment_id=enrollment_id,
            current_streak=3,
            longest_streak=5,
            last_study_date=date(2026, 7, 1),
        )
        streak.collect_events()

        streak.record_study(date(2026, 7, 2))

        assert streak.current_streak == 4
        assert streak.longest_streak == 5  # not exceeded

    def test_gap_resets_streak(self) -> None:
        enrollment_id = LearnerEnrollmentId.generate()
        streak = Streak(
            learner_enrollment_id=enrollment_id,
            current_streak=10,
            longest_streak=10,
            last_study_date=date(2026, 7, 1),
        )
        streak.collect_events()

        streak.record_study(date(2026, 7, 5))  # 4-day gap

        assert streak.current_streak == 1
        assert streak.longest_streak == 10  # unchanged
        events = streak.collect_events()
        assert any(isinstance(e, StreakReset) for e in events)

    def test_same_day_no_change(self) -> None:
        enrollment_id = LearnerEnrollmentId.generate()
        streak = Streak(
            learner_enrollment_id=enrollment_id,
            current_streak=5,
            longest_streak=7,
            last_study_date=date(2026, 7, 1),
        )

        streak.record_study(date(2026, 7, 1))  # same day

        assert streak.current_streak == 5  # unchanged

    def test_new_longest_streak_recorded(self) -> None:
        enrollment_id = LearnerEnrollmentId.generate()
        streak = Streak(
            learner_enrollment_id=enrollment_id,
            current_streak=7,
            longest_streak=7,
            last_study_date=date(2026, 7, 1),
        )
        streak.collect_events()

        streak.record_study(date(2026, 7, 2))

        assert streak.current_streak == 8
        assert streak.longest_streak == 8  # new record

    def test_events_recorded(self) -> None:
        enrollment_id = LearnerEnrollmentId.generate()
        streak = Streak(learner_enrollment_id=enrollment_id)

        streak.record_study(date(2026, 7, 1))

        events = streak.collect_events()
        assert any(isinstance(e, StreakUpdated) for e in events)

    def test_negative_streak_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            Streak(
                learner_enrollment_id=LearnerEnrollmentId.generate(),
                current_streak=-1,
            )

    def test_longest_less_than_current_rejected(self) -> None:
        with pytest.raises(ValueError, match="longest_streak must be >= current_streak"):
            Streak(
                learner_enrollment_id=LearnerEnrollmentId.generate(),
                current_streak=5,
                longest_streak=3,
            )
