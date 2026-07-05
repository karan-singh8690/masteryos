"""Application layer shared abstractions.

This module contains the foundational types for the application layer:
- Base Command, CommandResult, CommandHandler
- Base Query, QueryHandler
- Application exceptions
- Unit of Work interface
- Event Publisher interface
- Authorization interfaces
- Repository factory port

All are abstract — no infrastructure implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Generic, Protocol, TypeVar
from uuid import UUID

from app.domain.shared.kernel import DomainEvent

# ============================================================
# Generic Type Variables
# ============================================================

TCommand = TypeVar("TCommand", bound="Command")
TResult = TypeVar("TResult")
TQuery = TypeVar("TQuery", bound="Query")
TResponse = TypeVar("TResponse")

# ============================================================
# Base Command
# ============================================================


@dataclass(frozen=True)
class Command:
    """Base class for all commands.

    Commands are immutable requests to mutate state.
    Every command has exactly one handler.
    Subclasses use ``@dataclass(frozen=True)``.
    """


@dataclass(frozen=True)
class CommandResult(Generic[TResult]):
    """The result of executing a command.

    Wraps the result value and indicates success or failure.
    """

    success: bool
    value: TResult | None = None
    error: str | None = None
    error_code: str | None = None
    events: list[DomainEvent] = field(default_factory=list)

    @classmethod
    def ok(cls, value: TResult, events: list[DomainEvent] | None = None) -> CommandResult[TResult]:
        """Create a successful result."""
        return cls(success=True, value=value, events=events or [])

    @classmethod
    def fail(cls, error: str, error_code: str = "APPLICATION_ERROR") -> CommandResult[TResult]:
        """Create a failed result."""
        return cls(success=False, error=error, error_code=error_code)


# ============================================================
# Base Command Handler
# ============================================================


class CommandHandler(ABC, Generic[TCommand, TResult]):
    """Base class for all command handlers.

    A command handler:
    1. Validates the command (application-level validation).
    2. Loads aggregates through repository interfaces (via Unit of Work).
    3. Calls domain behavior (entities, domain services).
    4. Persists through the Unit of Work.
    5. Collects domain events.
    6. Publishes events through the Event Publisher.
    7. Returns a CommandResult.

    Handlers must NEVER contain business rules that belong in the domain.
    """

    @abstractmethod
    async def handle(self, command: TCommand) -> CommandResult[TResult]:
        """Execute the command and return the result."""
        ...


# ============================================================
# Base Query
# ============================================================


@dataclass(frozen=True)
class Query:
    """Base class for all queries.

    Queries are immutable read-only requests.
    Every query has exactly one handler.
    """


# ============================================================
# Base Query Handler
# ============================================================


class QueryHandler(ABC, Generic[TQuery, TResponse]):
    """Base class for all query handlers.

    A query handler:
    1. Reads from repositories (via Unit of Work or direct repository access).
    2. Builds DTOs.
    3. Applies authorization checks.
    4. Returns the response.

    Query handlers NEVER modify state.
    """

    @abstractmethod
    async def handle(self, query: TQuery) -> TResponse:
        """Execute the query and return the response."""
        ...


# ============================================================
# Application Exceptions
# ============================================================


class ApplicationError(Exception):
    """Base exception for all application-layer errors."""

    def __init__(self, message: str, *, code: str = "APPLICATION_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ValidationFailed(ApplicationError):
    """Raised when application-level validation fails."""

    def __init__(self, errors: dict[str, str], *, code: str = "VALIDATION_FAILED") -> None:
        super().__init__(f"Validation failed: {errors}", code=code)
        self.errors = errors


class AuthorizationDenied(ApplicationError):
    """Raised when the current user is not authorized for the operation."""

    def __init__(self, action: str, resource: str | None = None, *, code: str = "AUTHORIZATION_DENIED") -> None:
        msg = f"Authorization denied for action: {action}"
        if resource:
            msg += f" on resource: {resource}"
        super().__init__(msg, code=code)
        self.action = action
        self.resource = resource


class ConcurrencyConflict(ApplicationError):
    """Raised when optimistic concurrency check fails."""

    def __init__(self, aggregate: str, *, code: str = "CONCURRENCY_CONFLICT") -> None:
        super().__init__(f"Concurrency conflict on {aggregate}", code=code)
        self.aggregate = aggregate


class ResourceMissing(ApplicationError):
    """Raised when a required resource is not found."""

    def __init__(self, resource_type: str, resource_id: Any, *, code: str = "RESOURCE_MISSING") -> None:
        super().__init__(f"{resource_type} not found: {resource_id}", code=code)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ApplicationConflict(ApplicationError):
    """Raised when a command conflicts with current application state."""

    def __init__(self, detail: str, *, code: str = "APPLICATION_CONFLICT") -> None:
        super().__init__(detail, code=code)


# ============================================================
# Unit of Work Interface
# ============================================================


class UnitOfWork(ABC):
    """Abstract Unit of Work — defines transaction boundaries.

    The Unit of Work pattern ensures that all changes within a command
    handler are committed atomically. If any part fails, the entire
    transaction rolls back.

    Usage in a command handler:
        async with self.uow as uow:
            user = await uow.users.get_by_id(user_id)
            user.verify_email()
            await uow.users.save(user)
            events = user.collect_events()
            await uow.commit()

    The ``commit()`` method:
    1. Flushes all pending changes.
    2. Commits the transaction.
    3. Returns collected domain events for publishing.

    The ``rollback()`` method discards all changes.
    """

    @abstractmethod
    async def __aenter__(self) -> UnitOfWork:
        """Begin a transaction."""
        ...

    @abstractmethod
    async def __aexit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object | None) -> None:
        """End the transaction (commit on success, rollback on exception)."""
        ...

    @abstractmethod
    async def commit(self) -> list[DomainEvent]:
        """Commit the transaction and return collected domain events."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the transaction."""
        ...

    # Repository access — each context's repositories are accessible via the UoW.
    # Subclasses (implementations) provide concrete repository instances.
    # The properties below are typed as Any because the domain layer's
    # repository interfaces are the contract; the UoW provides access to them.

    @property
    @abstractmethod
    def users(self) -> Any:
        """Identity: UserRepository."""
        ...

    @property
    @abstractmethod
    def enrollments(self) -> Any:
        """Learning: EnrollmentRepository."""
        ...

    @property
    @abstractmethod
    def study_sessions(self) -> Any:
        """Learning: StudySessionRepository."""
        ...

    @property
    @abstractmethod
    def question_instances(self) -> Any:
        """Assessment: QuestionInstanceRepository."""
        ...

    @property
    @abstractmethod
    def attempts(self) -> Any:
        """Assessment: AttemptRepository."""
        ...

    @property
    @abstractmethod
    def mastery_scores(self) -> Any:
        """Mastery: MasteryScoreRepository."""
        ...

    @property
    @abstractmethod
    def reviews(self) -> Any:
        """Mastery: ReviewRepository."""
        ...

    @property
    @abstractmethod
    def algorithm_versions(self) -> Any:
        """Mastery: AlgorithmVersionRepository."""
        ...

    @property
    @abstractmethod
    def subjects(self) -> Any:
        """Content: SubjectRepository."""
        ...

    @property
    @abstractmethod
    def concepts(self) -> Any:
        """Content: ConceptRepository."""
        ...

    @property
    @abstractmethod
    def question_templates(self) -> Any:
        """Content: QuestionTemplateRepository."""
        ...

    @property
    @abstractmethod
    def content_packs(self) -> Any:
        """Content: ContentPackRepository."""
        ...

    @property
    @abstractmethod
    def content_versions(self) -> Any:
        """Content: ContentVersionRepository."""
        ...

    @property
    @abstractmethod
    def recommendations(self) -> Any:
        """Learning: RecommendationRepository."""
        ...

    @property
    @abstractmethod
    def achievements(self) -> Any:
        """Learning: AchievementRepository."""
        ...

    @property
    @abstractmethod
    def streaks(self) -> Any:
        """Learning: StreakRepository."""
        ...

    @property
    @abstractmethod
    def learning_goals(self) -> Any:
        """Learning: LearningGoalRepository."""
        ...

    @property
    @abstractmethod
    def subscriptions(self) -> Any:
        """Billing: SubscriptionRepository."""
        ...

    @property
    @abstractmethod
    def billing_plans(self) -> Any:
        """Billing: BillingPlanRepository."""
        ...

    @property
    @abstractmethod
    def invoices(self) -> Any:
        """Billing: InvoiceRepository."""
        ...

    @property
    @abstractmethod
    def notifications(self) -> Any:
        """Administration: NotificationRepository."""
        ...

    @property
    @abstractmethod
    def feature_flags(self) -> Any:
        """Administration: FeatureFlagRepository."""
        ...

    @property
    @abstractmethod
    def audit_logs(self) -> Any:
        """Administration: AuditLogRepository."""
        ...

    @property
    @abstractmethod
    def organizations(self) -> Any:
        """Administration: OrganizationRepository."""
        ...

    @property
    @abstractmethod
    def scheduling_configs(self) -> Any:
        """Scheduling: SchedulingConfigRepository."""
        ...

    @property
    @abstractmethod
    def daily_queues(self) -> Any:
        """Scheduling: DailyQueueRepository."""
        ...


# ============================================================
# Event Publisher Interface
# ============================================================


class EventPublisher(ABC):
    """Abstract event publisher — publishes domain events to the outbox.

    The application layer calls ``publish_events`` after a successful
    command handler transaction. The infrastructure implementation writes
    events to the outbox table (ADR-0012) and the outbox dispatcher
    delivers them to subscribers asynchronously.
    """

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publish a single domain event."""
        ...

    @abstractmethod
    async def publish_many(self, events: Sequence[DomainEvent]) -> None:
        """Publish multiple domain events."""
        ...


# ============================================================
# Authorization Interfaces
# ============================================================


class CurrentUserProvider(ABC):
    """Provides the current authenticated user's context.

    The infrastructure implementation extracts the user from the JWT
    or session. The application layer uses this to identify the actor.
    """

    @abstractmethod
    async def get_current_user_id(self) -> UUID | None:
        """Return the current user's ID, or None if unauthenticated."""
        ...

    @abstractmethod
    async def get_current_user_roles(self) -> list[str]:
        """Return the current user's roles (e.g., ['learner', 'instructor'])."""
        ...


class PermissionChecker(ABC):
    """Checks whether a user has permission for an action."""

    @abstractmethod
    async def can(self, user_id: UUID, action: str, resource_type: str, resource_id: UUID | None = None) -> bool:
        """Return True if the user can perform the action on the resource."""
        ...

    @abstractmethod
    async def has_role(self, user_id: UUID, role: str, scope: UUID | None = None) -> bool:
        """Return True if the user has the given role (optionally scoped)."""
        ...


class AuthorizationService(ABC):
    """High-level authorization service combining user context and permissions."""

    @abstractmethod
    async def require_authenticated(self) -> UUID:
        """Return the current user ID or raise AuthorizationDenied."""
        ...

    @abstractmethod
    async def require_role(self, role: str, scope: UUID | None = None) -> UUID:
        """Require the current user to have a role. Returns user ID."""
        ...

    @abstractmethod
    async def require_owner_or_admin(self, resource_owner_id: UUID) -> UUID:
        """Require the current user to be the resource owner or an admin."""
        ...


# ============================================================
# Repository Factory Port
# ============================================================


class RepositoryFactory(Protocol):
    """Protocol for creating repository instances within a UoW.

    The infrastructure layer provides a concrete factory that creates
    SQLAlchemy-backed repositories sharing the same async session.
    """

    def create_user_repository(self) -> Any: ...
    def create_enrollment_repository(self) -> Any: ...
    def create_study_session_repository(self) -> Any: ...
    def create_attempt_repository(self) -> Any: ...
    def create_mastery_score_repository(self) -> Any: ...
    def create_review_repository(self) -> Any: ...
    def create_algorithm_version_repository(self) -> Any: ...
    # ... (all repositories)
