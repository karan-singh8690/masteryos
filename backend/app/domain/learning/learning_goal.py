"""LearningGoal — a learner-declared target that influences scheduling."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.domain.shared.ids import LearnerEnrollmentId, LearningGoalId
from app.domain.shared.kernel import (
    AggregateRoot,
    GoalStatus,
    GoalType,
    InvariantViolation,
)
from app.domain.learning.events import LearningGoalCleared, LearningGoalSet


class LearningGoal(AggregateRoot):
    """A learner-declared goal that modulates scheduling.

    Invariants:
    - target_date must be in the future for time-bound goals.
    - A learner has at most one active time-bound goal per enrollment.
    - Abandoned goals are archived for analytics.
    """

    def __init__(
        self,
        id: LearningGoalId,
        learner_enrollment_id: LearnerEnrollmentId,
        goal_type: GoalType,
        target_date: date | None = None,
        parameters: dict[str, Any] | None = None,
        status: GoalStatus = GoalStatus.ACTIVE,
        created_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.learner_enrollment_id = learner_enrollment_id
        self.goal_type = goal_type
        self.target_date = target_date
        self.parameters = parameters or {}
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)
        self.completed_at = completed_at

    @classmethod
    def set(
        cls,
        learner_enrollment_id: LearnerEnrollmentId,
        goal_type: GoalType,
        target_date: date | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> LearningGoal:
        """Set a new learning goal."""
        if goal_type == GoalType.INTERVIEW_DATE:
            if target_date is None:
                raise InvariantViolation("LearningGoal", "interview_date goal requires target_date")
            if target_date <= date.today():
                raise InvariantViolation("LearningGoal", "target_date must be in the future")

        goal = cls(
            id=LearningGoalId.generate(),
            learner_enrollment_id=learner_enrollment_id,
            goal_type=goal_type,
            target_date=target_date,
            parameters=parameters,
        )
        goal._record_event(
            LearningGoalSet(
                goal_id=goal.id.value,
                enrollment_id=learner_enrollment_id.value,
                goal_type=goal_type,
                target_date=target_date,
            )
        )
        return goal

    def complete(self) -> None:
        """Mark the goal as completed."""
        if self.status != GoalStatus.ACTIVE:
            return
        self.status = GoalStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def abandon(self) -> None:
        """Abandon the goal (archived for analytics)."""
        if self.status != GoalStatus.ACTIVE:
            return
        self.status = GoalStatus.ABANDONED
        self._record_event(LearningGoalCleared(goal_id=self.id.value))

    @property
    def is_active(self) -> bool:
        return self.status == GoalStatus.ACTIVE

    @property
    def is_time_bound(self) -> bool:
        return self.goal_type == GoalType.INTERVIEW_DATE
