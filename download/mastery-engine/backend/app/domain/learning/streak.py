"""Streak — a decorative engagement metric. Never a mastery signal.

Per Task 002: streaks are decorative; they do not affect scheduling or mastery.
They are tracked separately to reinforce this distinction.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.domain.shared.ids import LearnerEnrollmentId
from app.domain.shared.kernel import AggregateRoot
from app.domain.learning.events import StreakReset, StreakUpdated

# Streak resets if no study for more than 24 hours
STREAK_RESET_WINDOW_HOURS = 24


class Streak(AggregateRoot):
    """A learner's study streak (current and longest).

    Invariants:
    - Streaks are decorative; they do not affect scheduling or mastery.
    - current_streak <= longest_streak.
    - Streak increments only once per calendar day.
    """

    def __init__(
        self,
        learner_enrollment_id: LearnerEnrollmentId,
        current_streak: int = 0,
        longest_streak: int = 0,
        last_study_date: date | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__()
        if current_streak < 0:
            raise ValueError("current_streak must be non-negative")
        if longest_streak < current_streak:
            raise ValueError("longest_streak must be >= current_streak")
        self.learner_enrollment_id = learner_enrollment_id
        self.current_streak = current_streak
        self.longest_streak = longest_streak
        self.last_study_date = last_study_date
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def record_study(self, study_date: date | None = None) -> None:
        """Record a study session for streak purposes.

        Called when a study session ends. Increments the streak if the
        study date is consecutive with the last study date.
        """
        study_date = study_date or date.today()

        # Already counted today
        if self.last_study_date == study_date:
            return

        if self.last_study_date is None:
            # First study ever
            self.current_streak = 1
        elif (study_date - self.last_study_date).days == 1:
            # Consecutive day
            self.current_streak += 1
        elif (study_date - self.last_study_date).days > 1:
            # Gap — reset
            if self.current_streak > 0:
                self._record_event(
                    StreakReset(
                        enrollment_id=self.learner_enrollment_id.value,
                        previous_streak=self.current_streak,
                    )
                )
            self.current_streak = 1

        self.last_study_date = study_date
        self.updated_at = datetime.now(timezone.utc)

        # Update longest
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

        self._record_event(
            StreakUpdated(
                enrollment_id=self.learner_enrollment_id.value,
                current_streak=self.current_streak,
                longest_streak=self.longest_streak,
            )
        )

    def reset_if_stale(self, current_date: date | None = None) -> bool:
        """Reset the streak if the learner has been inactive too long.

        Returns True if the streak was reset.
        """
        current_date = current_date or date.today()
        if self.last_study_date is None:
            return False
        gap_hours = (datetime.now(timezone.utc).date() - self.last_study_date).days * 24
        if gap_hours >= STREAK_RESET_WINDOW_HOURS and self.current_streak > 0:
            self._record_event(
                StreakReset(
                    enrollment_id=self.learner_enrollment_id.value,
                    previous_streak=self.current_streak,
                )
            )
            self.current_streak = 0
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False
