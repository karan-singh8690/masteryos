"""Achievement — an engine-recognized learner accomplishment.

Includes milestones, graduations, streaks, and special recognitions.
Achievements are irreversible: once awarded, always awarded.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.domain.shared.ids import (
    AchievementId,
    AchievementTypeId,
    LearnerEnrollmentId,
)
from app.domain.shared.kernel import (
    AggregateRoot,
    AchievementCategory,
    DuplicateEntity,
)
from app.domain.learning.events import AchievementGranted


class Achievement(AggregateRoot):
    """An earned achievement.

    Invariants:
    - Irreversible (once awarded, always awarded).
    - One per (enrollment, achievement_type).
    - Awarded automatically when criteria are met (no manual award).
    - ``criteria_snapshot`` captures the criteria at award time (historical accuracy).
    """

    def __init__(
        self,
        id: AchievementId,
        learner_enrollment_id: LearnerEnrollmentId,
        achievement_type_id: AchievementTypeId,
        achievement_code: str,
        name: str,
        category: AchievementCategory,
        criteria_snapshot: dict[str, Any],
        awarded_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.learner_enrollment_id = learner_enrollment_id
        self.achievement_type_id = achievement_type_id
        self.achievement_code = achievement_code
        self.name = name
        self.category = category
        self.criteria_snapshot = criteria_snapshot
        self.awarded_at = awarded_at or datetime.now(timezone.utc)

    @classmethod
    def grant(
        cls,
        learner_enrollment_id: LearnerEnrollmentId,
        achievement_type_id: AchievementTypeId,
        achievement_code: str,
        name: str,
        category: AchievementCategory,
        criteria_snapshot: dict[str, Any],
    ) -> Achievement:
        """Grant an achievement to a learner.

        The application layer must check for existing awards before calling
        this method (unique constraint on (enrollment, type)).
        """
        achievement = cls(
            id=AchievementId.generate(),
            learner_enrollment_id=learner_enrollment_id,
            achievement_type_id=achievement_type_id,
            achievement_code=achievement_code,
            name=name,
            category=category,
            criteria_snapshot=criteria_snapshot,
        )
        achievement._record_event(
            AchievementGranted(
                achievement_id=achievement.id.value,
                enrollment_id=learner_enrollment_id.value,
                achievement_type_id=achievement_type_id.value,
                achievement_code=achievement_code,
            )
        )
        return achievement

    @property
    def is_milestone(self) -> bool:
        return self.category == AchievementCategory.MILESTONE

    @property
    def is_graduation(self) -> bool:
        return self.category == AchievementCategory.GRADUATION
