"""Shared kernel — base types, primitives, and cross-cutting domain concepts.

This module contains the foundation of the domain layer:
- Base types: Entity, AggregateRoot, ValueObject
- Typed identifiers
- Shared value objects
- Exception hierarchy
- Base domain event
- Shared enums

Everything in this module is pure Python with NO framework dependencies.
The domain layer must compile and test independently of infrastructure.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, TypeVar
from uuid import UUID, uuid4

# ============================================================
# Base Types
# ============================================================


class ValueObject:
    """Base class for all value objects.

    Value objects are immutable, compared by value (not identity),
    and have no lifecycle of their own. Subclasses should use
    ``@dataclass(frozen=True)`` to enforce immutability.

    Example:
        @dataclass(frozen=True)
        class Email(ValueObject):
            value: str
    """


class Entity:
    """Base class for all entities.

    Entities have identity (a UUID) that persists across state changes.
    Two entities are equal if they have the same ID, even if their
    attributes differ. Entities are mutable within their invariant boundaries.

    Subclasses should define their identity via the ``id`` property
    or override ``__eq__`` and ``__hash__``.
    """

    @property
    def _identity_key(self) -> Any:
        """Return the value used for identity comparison.

        Override in subclasses if identity is not ``self.id``.
        """
        return getattr(self, "id", None)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        if type(self) is not type(other):
            return False
        return self._identity_key == other._identity_key

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._identity_key))


class AggregateRoot(Entity):
    """Base class for aggregate roots.

    Aggregate roots are the entry point to an aggregate — a cluster of
    domain objects treated as a single consistency boundary. Only the
    aggregate root's repository loads and saves the aggregate.

    Aggregate roots collect domain events that are emitted when invariants
    are enforced or state transitions occur. The application layer retrieves
    these events after a successful operation and publishes them via the
    outbox pattern.
    """

    def __init__(self) -> None:
        self._domain_events: list[DomainEvent] = []

    def _record_event(self, event: DomainEvent) -> None:
        """Record a domain event to be published after persistence."""
        if not hasattr(self, "_domain_events") or self._domain_events is None:
            self._domain_events = []
        self._domain_events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        """Return all recorded domain events and clear the internal list.

        Called by the application layer after successfully persisting
        the aggregate's changes.
        """
        events = getattr(self, "_domain_events", []) or []
        self._domain_events = []
        return list(events)

    def clear_events(self) -> None:
        """Clear all recorded events without returning them."""
        self._domain_events = []


# ============================================================
# Base Domain Event
# ============================================================


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events.

    Domain events are immutable records of something that happened in the domain.
    They are named in past tense (e.g., ``AttemptRecorded``, not ``RecordAttempt``)
    and carry all the information needed for subscribers to process them.

    Subclasses should use ``@dataclass(frozen=True)`` and include only
    the fields relevant to the event.
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        """Return the event type name (class name)."""
        return type(self).__name__


# ============================================================
# Exception Hierarchy
# ============================================================


class DomainError(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, *, code: str = "DOMAIN_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class InvariantViolation(DomainError):
    """Raised when an aggregate invariant is violated."""

    def __init__(self, aggregate: str, invariant: str, *, code: str = "INVARIANT_VIOLATION") -> None:
        super().__init__(
            f"Invariant violated in {aggregate}: {invariant}",
            code=code,
        )
        self.aggregate = aggregate
        self.invariant = invariant


class BusinessRuleViolation(DomainError):
    """Raised when a business rule is violated."""

    def __init__(self, rule: str, detail: str, *, code: str = "BUSINESS_RULE_VIOLATION") -> None:
        super().__init__(f"Business rule '{rule}' violated: {detail}", code=code)
        self.rule = rule
        self.detail = detail


class EntityNotFound(DomainError):
    """Raised when an entity cannot be found."""

    def __init__(self, entity_type: str, entity_id: Any, *, code: str = "ENTITY_NOT_FOUND") -> None:
        super().__init__(f"{entity_type} not found: {entity_id}", code=code)
        self.entity_type = entity_type
        self.entity_id = entity_id


class InvalidStateTransition(DomainError):
    """Raised when an invalid state transition is attempted."""

    def __init__(
        self,
        entity: str,
        current_state: str,
        attempted_action: str,
        *,
        code: str = "INVALID_STATE_TRANSITION",
    ) -> None:
        super().__init__(
            f"Cannot {attempted_action} {entity} in state '{current_state}'",
            code=code,
        )
        self.entity = entity
        self.current_state = current_state
        self.attempted_action = attempted_action


class DuplicateEntity(DomainError):
    """Raised when a duplicate entity is created."""

    def __init__(self, entity_type: str, key: str, *, code: str = "DUPLICATE_ENTITY") -> None:
        super().__init__(f"Duplicate {entity_type}: {key}", code=code)
        self.entity_type = entity_type
        self.key = key


# ============================================================
# Shared Enums
# ============================================================


class ConceptState(str, Enum):
    """The mastery state of a concept for a learner."""

    UNSEEN = "unseen"
    NOVICE = "novice"
    DEVELOPING = "developing"
    PROFICIENT = "proficient"
    MASTERED = "mastered"
    DECAYED = "decayed"


class Difficulty(str, Enum):
    """Difficulty level of a concept or question."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Importance(str, Enum):
    """Curriculum importance of a concept."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WeaknessSeverity(str, Enum):
    """Severity of a weak concept."""

    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class ScoringOutcome(str, Enum):
    """The outcome of scoring an attempt."""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIAL = "partial"


class AttemptIntent(str, Enum):
    """The intent behind an attempt."""

    PRACTICE = "practice"
    REVIEW = "review"
    DIAGNOSTIC = "diagnostic"


class SessionIntent(str, Enum):
    """The intent of a study session."""

    DRILL = "drill"
    DIAGNOSTIC = "diagnostic"
    REVIEW = "review"
    MIXED = "mixed"


class SessionStatus(str, Enum):
    """The status of a study session."""

    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    ABANDONED = "abandoned"


class QuestionType(str, Enum):
    """The type of a question."""

    MULTIPLE_CHOICE = "multiple_choice"
    CODE_EXECUTION = "code_execution"
    FREE_RESPONSE = "free_response"


class AnswerType(str, Enum):
    """The type of an answer."""

    MULTIPLE_CHOICE = "multiple_choice"
    CODE = "code"
    FREE_RESPONSE = "free_response"


class ContentStatus(str, Enum):
    """The lifecycle status of content artifacts."""

    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


class DependencyType(str, Enum):
    """The type of a concept dependency."""

    PREREQUISITE = "prerequisite"
    RELATED = "related"
    REINFORCES = "reinforces"


class DependencyWeight(str, Enum):
    """The weight of a concept dependency."""

    WEAK = "weak"
    STRONG = "strong"


class ReviewPriority(str, Enum):
    """Priority of a scheduled review."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationStatus(str, Enum):
    """The status of a recommendation."""

    PENDING = "pending"
    PRESENTED = "presented"
    ACCEPTED = "accepted"
    DEFERRED = "deferred"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class AchievementCategory(str, Enum):
    """The category of an achievement."""

    MILESTONE = "milestone"
    GRADUATION = "graduation"
    STREAK = "streak"
    SPECIAL = "special"


class UserStatus(str, Enum):
    """The status of a user account."""

    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
    PENDING_DELETION = "pending_deletion"
    ANONYMIZED = "anonymized"


class CredentialType(str, Enum):
    """The type of a user credential."""

    PASSWORD = "password"
    OAUTH = "oauth"


class SubscriptionStatus(str, Enum):
    """The status of a subscription."""

    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class BillingPeriod(str, Enum):
    """The billing period of a plan."""

    MONTHLY = "monthly"
    ANNUAL = "annual"


class ReviewStage(str, Enum):
    """The stage of a content review."""

    PEER_REVIEW = "peer_review"
    EDITORIAL_REVIEW = "editorial_review"
    QA_PILOT = "qa_pilot"


class ReviewDecision(str, Enum):
    """The decision of a content review."""

    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"


class NotificationChannel(str, Enum):
    """The channel of a notification."""

    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatus(str, Enum):
    """The status of a notification."""

    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    DISMISSED = "dismissed"
    FAILED = "failed"


class EnrollmentStatus(str, Enum):
    """The status of a learner enrollment."""

    PENDING_ONBOARDING = "pending_onboarding"
    ACTIVE = "active"
    DORMANT = "dormant"
    UNENROLLED = "unenrolled"
    ANONYMIZED = "anonymized"


class GoalType(str, Enum):
    """The type of a learning goal."""

    INTERVIEW_DATE = "interview_date"
    DAILY_COMMITMENT = "daily_commitment"
    SESSION_INTENT = "session_intent"
    MASTERY_TARGET = "mastery_target"


class GoalStatus(str, Enum):
    """The status of a learning goal."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class FeasibilityStatus(str, Enum):
    """The feasibility of a study plan."""

    FEASIBLE = "feasible"
    AT_RISK = "at_risk"
    INFEASIBLE = "infeasible"
