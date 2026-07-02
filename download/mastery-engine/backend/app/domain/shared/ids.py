"""Typed identifiers for all domain entities.

Each ID is a frozen value object wrapping a UUID, providing type safety
that prevents mixing up IDs of different entities (e.g., passing a
ConceptId where a UserId is expected).

Usage:
    user_id = UserId.generate()
    concept_id = ConceptId.generate()
    # user_id == concept_id  → TypeError (different types)
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.shared.kernel import ValueObject


@dataclass(frozen=True)
class _BaseId(ValueObject):
    """Base for all typed identifiers."""

    value: UUID

    @classmethod
    def generate(cls) -> _BaseId:
        """Generate a new random ID."""
        return cls(uuid4())

    @classmethod
    def from_string(cls, raw: str) -> _BaseId:
        """Create an ID from a UUID string."""
        return cls(UUID(raw))

    def __str__(self) -> str:
        return str(self.value)


# ============================================================
# Identity Context
# ============================================================


@dataclass(frozen=True)
class UserId(_BaseId):
    """Unique identifier for a User."""


@dataclass(frozen=True)
class SessionId(_BaseId):
    """Unique identifier for an authenticated Session."""


@dataclass(frozen=True)
class CredentialId(_BaseId):
    """Unique identifier for a UserCredential."""


# ============================================================
# Content Context
# ============================================================


@dataclass(frozen=True)
class TenantId(_BaseId):
    """Unique identifier for a Tenant."""


@dataclass(frozen=True)
class SubjectId(_BaseId):
    """Unique identifier for a Subject."""


@dataclass(frozen=True)
class LearningPathId(_BaseId):
    """Unique identifier for a LearningPath."""


@dataclass(frozen=True)
class ConceptId(_BaseId):
    """Unique identifier for a Concept."""


@dataclass(frozen=True)
class LearningObjectiveId(_BaseId):
    """Unique identifier for a LearningObjective."""


@dataclass(frozen=True)
class MisconceptionId(_BaseId):
    """Unique identifier for a Misconception."""


@dataclass(frozen=True)
class QuestionTemplateId(_BaseId):
    """Unique identifier for a QuestionTemplate."""


@dataclass(frozen=True)
class TemplateVersionId(_BaseId):
    """Unique identifier for a TemplateVersion."""


@dataclass(frozen=True)
class ContentVersionId(_BaseId):
    """Unique identifier for a ContentVersion."""


@dataclass(frozen=True)
class ContentPackId(_BaseId):
    """Unique identifier for a ContentPack."""


# ============================================================
# Learning Context
# ============================================================


@dataclass(frozen=True)
class LearnerEnrollmentId(_BaseId):
    """Unique identifier for a LearnerEnrollment."""


@dataclass(frozen=True)
class StudySessionId(_BaseId):
    """Unique identifier for a StudySession."""


@dataclass(frozen=True)
class LearningSessionId(_BaseId):
    """Unique identifier for a LearningSession."""


@dataclass(frozen=True)
class LearningGoalId(_BaseId):
    """Unique identifier for a LearningGoal."""


@dataclass(frozen=True)
class StudyPlanId(_BaseId):
    """Unique identifier for a StudyPlan."""


@dataclass(frozen=True)
class RecommendationId(_BaseId):
    """Unique identifier for a Recommendation."""


@dataclass(frozen=True)
class AchievementId(_BaseId):
    """Unique identifier for an Achievement."""


@dataclass(frozen=True)
class AchievementTypeId(_BaseId):
    """Unique identifier for an AchievementType."""


# ============================================================
# Assessment Context
# ============================================================


@dataclass(frozen=True)
class QuestionInstanceId(_BaseId):
    """Unique identifier for a QuestionInstance."""


@dataclass(frozen=True)
class AttemptId(_BaseId):
    """Unique identifier for an Attempt."""


@dataclass(frozen=True)
class AnswerId(_BaseId):
    """Unique identifier for an Answer."""


# ============================================================
# Mastery Context
# ============================================================


@dataclass(frozen=True)
class MasteryScoreId(_BaseId):
    """Unique identifier for a MasteryScore."""


@dataclass(frozen=True)
class ReviewId(_BaseId):
    """Unique identifier for a Review."""


@dataclass(frozen=True)
class AlgorithmVersionId(_BaseId):
    """Unique identifier for an AlgorithmVersion."""


@dataclass(frozen=True)
class LearnerMisconceptionId(_BaseId):
    """Unique identifier for a LearnerMisconception."""


# ============================================================
# Scheduling Context
# ============================================================


@dataclass(frozen=True)
class SchedulingConfigId(_BaseId):
    """Unique identifier for a SchedulingConfig."""


@dataclass(frozen=True)
class DailyQueueId(_BaseId):
    """Unique identifier for a DailyQueue."""


# ============================================================
# Billing Context
# ============================================================


@dataclass(frozen=True)
class BillingPlanId(_BaseId):
    """Unique identifier for a BillingPlan."""


@dataclass(frozen=True)
class SubscriptionId(_BaseId):
    """Unique identifier for a Subscription."""


@dataclass(frozen=True)
class InvoiceId(_BaseId):
    """Unique identifier for an Invoice."""


# ============================================================
# Administration Context
# ============================================================


@dataclass(frozen=True)
class AuditLogId(_BaseId):
    """Unique identifier for an AuditLog entry."""


@dataclass(frozen=True)
class FeatureFlagId(_BaseId):
    """Unique identifier for a FeatureFlag."""


@dataclass(frozen=True)
class GdprRequestId(_BaseId):
    """Unique identifier for a GdprRequest."""


@dataclass(frozen=True)
class OrganizationId(_BaseId):
    """Unique identifier for an Organization."""


@dataclass(frozen=True)
class NotificationId(_BaseId):
    """Unique identifier for a Notification."""
