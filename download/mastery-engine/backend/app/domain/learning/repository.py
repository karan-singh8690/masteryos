"""Learning context — abstract repository interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date

from app.domain.learning.achievement import Achievement
from app.domain.learning.enrollment import LearnerEnrollment
from app.domain.learning.learning_goal import LearningGoal
from app.domain.learning.recommendation import Recommendation
from app.domain.learning.streak import Streak
from app.domain.learning.study_session import StudySession
from app.domain.shared.ids import (
    AchievementTypeId,
    LearnerEnrollmentId,
    LearningGoalId,
    RecommendationId,
    StudySessionId,
    SubjectId,
    UserId,
)


class EnrollmentRepository(ABC):
    """Abstract repository for LearnerEnrollment aggregates."""

    @abstractmethod
    async def get_by_id(self, id: LearnerEnrollmentId) -> LearnerEnrollment | None:
        ...

    @abstractmethod
    async def get_by_user_and_subject(
        self, user_id: UserId, subject_id: SubjectId
    ) -> LearnerEnrollment | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: UserId) -> Sequence[LearnerEnrollment]:
        ...

    @abstractmethod
    async def add(self, enrollment: LearnerEnrollment) -> LearnerEnrollment:
        ...

    @abstractmethod
    async def save(self, enrollment: LearnerEnrollment) -> None:
        ...


class StudySessionRepository(ABC):
    """Abstract repository for StudySession aggregates."""

    @abstractmethod
    async def get_by_id(self, id: StudySessionId) -> StudySession | None:
        ...

    @abstractmethod
    async def get_active_by_enrollment(
        self, enrollment_id: LearnerEnrollmentId
    ) -> StudySession | None:
        ...

    @abstractmethod
    async def list_by_enrollment(
        self,
        enrollment_id: LearnerEnrollmentId,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[StudySession]:
        ...

    @abstractmethod
    async def add(self, session: StudySession) -> StudySession:
        ...

    @abstractmethod
    async def save(self, session: StudySession) -> None:
        ...


class LearningGoalRepository(ABC):
    """Abstract repository for LearningGoal aggregates."""

    @abstractmethod
    async def get_by_id(self, id: LearningGoalId) -> LearningGoal | None:
        ...

    @abstractmethod
    async def get_active_by_enrollment(
        self, enrollment_id: LearnerEnrollmentId
    ) -> Sequence[LearningGoal]:
        ...

    @abstractmethod
    async def add(self, goal: LearningGoal) -> LearningGoal:
        ...

    @abstractmethod
    async def save(self, goal: LearningGoal) -> None:
        ...


class RecommendationRepository(ABC):
    """Abstract repository for Recommendation aggregates."""

    @abstractmethod
    async def get_by_id(self, id: RecommendationId) -> Recommendation | None:
        ...

    @abstractmethod
    async def list_by_enrollment(
        self,
        enrollment_id: LearnerEnrollmentId,
        active_only: bool = False,
    ) -> Sequence[Recommendation]:
        ...

    @abstractmethod
    async def add(self, recommendation: Recommendation) -> Recommendation:
        ...

    @abstractmethod
    async def save(self, recommendation: Recommendation) -> None:
        ...


class AchievementRepository(ABC):
    """Abstract repository for Achievement aggregates."""

    @abstractmethod
    async def get_by_enrollment_and_type(
        self,
        enrollment_id: LearnerEnrollmentId,
        achievement_type_id: AchievementTypeId,
    ) -> Achievement | None:
        ...

    @abstractmethod
    async def list_by_enrollment(
        self, enrollment_id: LearnerEnrollmentId
    ) -> Sequence[Achievement]:
        ...

    @abstractmethod
    async def add(self, achievement: Achievement) -> Achievement:
        ...


class StreakRepository(ABC):
    """Abstract repository for Streak aggregates."""

    @abstractmethod
    async def get_by_enrollment(
        self, enrollment_id: LearnerEnrollmentId
    ) -> Streak | None:
        ...

    @abstractmethod
    async def save(self, streak: Streak) -> None:
        ...
