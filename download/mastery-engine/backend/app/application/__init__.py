"""Application layer — use case orchestration, DTOs, transaction boundaries.

This layer:
- Receives commands and queries from the presentation layer.
- Validates command shape and application-level constraints.
- Loads aggregates via repository interfaces (through the Unit of Work).
- Calls domain behavior — entities, domain services.
- Persists via the Unit of Work (transactional).
- Collects and publishes domain events via the Event Publisher.
- Returns DTOs — never domain entities.

Dependencies: Domain Layer only. No infrastructure, no web framework.
"""

from app.application.shared import (
    ApplicationConflict,
    ApplicationError,
    AuthorizationDenied,
    Command,
    CommandHandler,
    CommandResult,
    ConcurrencyConflict,
    CurrentUserProvider,
    EventPublisher,
    PermissionChecker,
    AuthorizationService,
    Query,
    QueryHandler,
    ResourceMissing,
    UnitOfWork,
    ValidationFailed,
)

__all__ = [
    # Base types
    "Command",
    "CommandResult",
    "CommandHandler",
    "Query",
    "QueryHandler",
    # Abstractions
    "UnitOfWork",
    "EventPublisher",
    "CurrentUserProvider",
    "PermissionChecker",
    "AuthorizationService",
    # Exceptions
    "ApplicationError",
    "ValidationFailed",
    "AuthorizationDenied",
    "ConcurrencyConflict",
    "ResourceMissing",
    "ApplicationConflict",
]
