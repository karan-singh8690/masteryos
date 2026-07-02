"""Learning context — exceptions."""

from __future__ import annotations

from app.domain.shared.kernel import DomainError


class LearningError(DomainError):
    """Base for all learning domain errors."""


class AlreadyEnrolled(LearningError):
    def __init__(self, user_id: object, subject_id: object) -> None:
        super().__init__(
            f"User {user_id} is already enrolled in subject {subject_id}",
            code="ALREADY_ENROLLED",
        )


class ActiveSessionExists(LearningError):
    def __init__(self, enrollment_id: object) -> None:
        super().__init__(
            f"An active study session already exists for enrollment {enrollment_id}",
            code="ACTIVE_SESSION_EXISTS",
        )


class SessionNotActive(LearningError):
    def __init__(self, session_id: object, status: str) -> None:
        super().__init__(
            f"Study session {session_id} is not active (status: {status})",
            code="SESSION_NOT_ACTIVE",
        )


class SessionExpired(LearningError):
    def __init__(self, session_id: object) -> None:
        super().__init__(
            f"Study session {session_id} has expired (past 24h resumption window)",
            code="SESSION_EXPIRED",
        )


class OnboardingAlreadyComplete(LearningError):
    def __init__(self, enrollment_id: object) -> None:
        super().__init__(
            f"Onboarding already complete for enrollment {enrollment_id}",
            code="ONBOARDING_ALREADY_COMPLETE",
        )


class MultipleTimeBoundGoals(LearningError):
    def __init__(self, enrollment_id: object) -> None:
        super().__init__(
            f"Only one active time-bound goal allowed for enrollment {enrollment_id}",
            code="MULTIPLE_TIME_BOUND_GOALS",
        )


class AchievementAlreadyGranted(LearningError):
    def __init__(self, enrollment_id: object, achievement_type_id: object) -> None:
        super().__init__(
            f"Achievement {achievement_type_id} already granted to enrollment {enrollment_id}",
            code="ACHIEVEMENT_ALREADY_GRANTED",
        )


class RecommendationNotDismissable(LearningError):
    def __init__(self, recommendation_id: object, status: str) -> None:
        super().__init__(
            f"Recommendation {recommendation_id} in status '{status}' cannot be dismissed",
            code="RECOMMENDATION_NOT_DISMISSABLE",
        )


class DuplicateRecommendation(LearningError):
    def __init__(self, enrollment_id: object, recommendation_type: str) -> None:
        super().__init__(
            f"Duplicate recommendation ({recommendation_type}) for enrollment {enrollment_id} within cooldown window",
            code="DUPLICATE_RECOMMENDATION",
        )
