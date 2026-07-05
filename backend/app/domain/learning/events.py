"""Learning context — domain events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from app.domain.shared.kernel import (
    DomainEvent,
    EnrollmentStatus,
    GoalType,
    RecommendationStatus,
    SessionIntent,
    SessionStatus,
)


@dataclass(frozen=True, kw_only=True)
class LearnerEnrolled(DomainEvent):
    """A user enrolled as a learner in a subject."""

    enrollment_id: UUID
    user_id: UUID
    subject_id: UUID


@dataclass(frozen=True, kw_only=True)
class OnboardingCompleted(DomainEvent):
    """A learner completed subject onboarding (diagnostic)."""

    enrollment_id: UUID


@dataclass(frozen=True, kw_only=True)
class LearnerUnenrolled(DomainEvent):
    """A learner unenrolled from a subject."""

    enrollment_id: UUID


@dataclass(frozen=True, kw_only=True)
class StudySessionStarted(DomainEvent):
    """A study session was started."""

    session_id: UUID
    enrollment_id: UUID
    intent: SessionIntent


@dataclass(frozen=True, kw_only=True)
class StudySessionPaused(DomainEvent):
    """A study session was paused."""

    session_id: UUID


@dataclass(frozen=True, kw_only=True)
class StudySessionResumed(DomainEvent):
    """A study session was resumed."""

    session_id: UUID


@dataclass(frozen=True, kw_only=True)
class StudySessionEnded(DomainEvent):
    """A study session was ended."""

    session_id: UUID
    question_count: int
    duration_seconds: int


@dataclass(frozen=True, kw_only=True)
class StudySessionAbandoned(DomainEvent):
    """A study session was abandoned (timeout)."""

    session_id: UUID


@dataclass(frozen=True, kw_only=True)
class LearningGoalSet(DomainEvent):
    """A learning goal was set."""

    goal_id: UUID
    enrollment_id: UUID
    goal_type: GoalType
    target_date: date | None


@dataclass(frozen=True, kw_only=True)
class LearningGoalCleared(DomainEvent):
    """A learning goal was cleared (abandoned)."""

    goal_id: UUID


@dataclass(frozen=True, kw_only=True)
class RecommendationGenerated(DomainEvent):
    """A recommendation was generated for a learner."""

    recommendation_id: UUID
    enrollment_id: UUID
    recommendation_type: str
    score: float


@dataclass(frozen=True, kw_only=True)
class RecommendationDismissed(DomainEvent):
    """A recommendation was dismissed by the learner."""

    recommendation_id: UUID


@dataclass(frozen=True, kw_only=True)
class AchievementGranted(DomainEvent):
    """An achievement was granted to a learner."""

    achievement_id: UUID
    enrollment_id: UUID
    achievement_type_id: UUID
    achievement_code: str


@dataclass(frozen=True, kw_only=True)
class StreakUpdated(DomainEvent):
    """A learner's streak was updated."""

    enrollment_id: UUID
    current_streak: int
    longest_streak: int


@dataclass(frozen=True, kw_only=True)
class StreakReset(DomainEvent):
    """A learner's streak was reset (inactivity)."""

    enrollment_id: UUID
    previous_streak: int
