"""Learning bounded context — domain layer.

Contains: LearnerEnrollment, StudySession, LearningGoal, Recommendation,
Achievement, Streak aggregates.
Pure Python; no I/O, no framework dependencies.
"""

from app.domain.learning.achievement import Achievement
from app.domain.learning.enrollment import LearnerEnrollment
from app.domain.learning.events import (
    AchievementGranted,
    LearnerEnrolled,
    LearnerUnenrolled,
    LearningGoalCleared,
    LearningGoalSet,
    OnboardingCompleted,
    RecommendationDismissed,
    RecommendationGenerated,
    StreakReset,
    StreakUpdated,
    StudySessionAbandoned,
    StudySessionEnded,
    StudySessionPaused,
    StudySessionResumed,
    StudySessionStarted,
)
from app.domain.learning.exceptions import (
    AchievementAlreadyGranted,
    ActiveSessionExists,
    AlreadyEnrolled,
    DuplicateRecommendation,
    LearningError,
    MultipleTimeBoundGoals,
    OnboardingAlreadyComplete,
    RecommendationNotDismissable,
    SessionExpired,
    SessionNotActive,
)
from app.domain.learning.learning_goal import LearningGoal
from app.domain.learning.recommendation import Recommendation
from app.domain.learning.repository import (
    AchievementRepository,
    EnrollmentRepository,
    LearningGoalRepository,
    RecommendationRepository,
    StreakRepository,
    StudySessionRepository,
)
from app.domain.learning.streak import Streak
from app.domain.learning.study_session import StudySession

__all__ = [
    "LearnerEnrollment",
    "StudySession",
    "LearningGoal",
    "Recommendation",
    "Achievement",
    "Streak",
    "EnrollmentRepository",
    "StudySessionRepository",
    "LearningGoalRepository",
    "RecommendationRepository",
    "AchievementRepository",
    "StreakRepository",
    "LearningError",
    "AlreadyEnrolled",
    "ActiveSessionExists",
    "SessionNotActive",
    "SessionExpired",
    "OnboardingAlreadyComplete",
    "MultipleTimeBoundGoals",
    "AchievementAlreadyGranted",
    "RecommendationNotDismissable",
    "DuplicateRecommendation",
    "LearnerEnrolled",
    "OnboardingCompleted",
    "LearnerUnenrolled",
    "StudySessionStarted",
    "StudySessionPaused",
    "StudySessionResumed",
    "StudySessionEnded",
    "StudySessionAbandoned",
    "LearningGoalSet",
    "LearningGoalCleared",
    "RecommendationGenerated",
    "RecommendationDismissed",
    "AchievementGranted",
    "StreakUpdated",
    "StreakReset",
]
