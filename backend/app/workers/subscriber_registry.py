"""Subscriber registry — maps domain event types to handler functions.

Each domain event type can have multiple subscribers. The registry
provides a clean API for registering handlers and looking them up
by event type.

Supported event types (per Task 017 spec):
- UserRegistered
- UserLoggedIn
- UserLoggedOut
- AttemptRecorded
- MasteryUpdated
- WeakConceptDetected
- ReviewScheduled
- RecommendationGenerated
- AchievementUnlocked
- NotificationRequested
- EmailVerificationRequested
- PasswordResetRequested
- SubscriptionChanged
- OrganizationCreated
- ContentPublished
- AlgorithmPublished
- SecurityIncidentDetected

Handlers are async callables: async def handler(payload: dict) -> None

The registry is used by the OutboxDispatcher to look up handlers when
an event is dispatched. Handlers are registered at application startup
(in the worker process).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Types
# ============================================================


EventHandler = Callable[[dict[str, Any]], Awaitable[None]]
"""Async event handler signature."""


# ============================================================
# Known Event Types (canonical list)
# ============================================================


# Identity context
USER_REGISTERED = "UserRegistered"
USER_LOGGED_IN = "UserLoggedIn"
USER_LOGGED_OUT = "UserLoggedOut"
EMAIL_VERIFICATION_REQUESTED = "EmailVerificationRequested"
PASSWORD_RESET_REQUESTED = "PasswordResetRequested"

# Assessment + Mastery context
ATTEMPT_RECORDED = "AttemptRecorded"
MASTERY_UPDATED = "MasteryUpdated"
WEAK_CONCEPT_DETECTED = "WeakConceptDetected"

# Scheduling + Learning context
REVIEW_SCHEDULED = "ReviewScheduled"
RECOMMENDATION_GENERATED = "RecommendationGenerated"
ACHIEVEMENT_UNLOCKED = "AchievementUnlocked"

# Notification context
NOTIFICATION_REQUESTED = "NotificationRequested"

# Billing + Administration context
SUBSCRIPTION_CHANGED = "SubscriptionChanged"
ORGANIZATION_CREATED = "OrganizationCreated"
CONTENT_PUBLISHED = "ContentPublished"
ALGORITHM_PUBLISHED = "AlgorithmPublished"

# Security context
SECURITY_INCIDENT_DETECTED = "SecurityIncidentDetected"


ALL_EVENT_TYPES: list[str] = [
    USER_REGISTERED,
    USER_LOGGED_IN,
    USER_LOGGED_OUT,
    EMAIL_VERIFICATION_REQUESTED,
    PASSWORD_RESET_REQUESTED,
    ATTEMPT_RECORDED,
    MASTERY_UPDATED,
    WEAK_CONCEPT_DETECTED,
    REVIEW_SCHEDULED,
    RECOMMENDATION_GENERATED,
    ACHIEVEMENT_UNLOCKED,
    NOTIFICATION_REQUESTED,
    SUBSCRIPTION_CHANGED,
    ORGANIZATION_CREATED,
    CONTENT_PUBLISHED,
    ALGORITHM_PUBLISHED,
    SECURITY_INCIDENT_DETECTED,
]


# ============================================================
# Subscriber Registry
# ============================================================


class SubscriberRegistry:
    """Registry of event type → handler mappings.

    This is a thin wrapper around a dict that provides:
    - Type-safe registration
    - Handler naming (for logging/debugging)
    - Bulk registration (register multiple handlers at once)
    - Lookup by event type

    The registry is populated at worker startup. The OutboxDispatcher
    uses it to look up handlers when an event is dispatched.

    Usage:
        registry = SubscriberRegistry()
        registry.register(USER_REGISTERED, send_verification_email)
        registry.register(USER_REGISTERED, send_welcome_email)
        registry.register(ATTEMPT_RECORDED, update_mastery)

        dispatcher.subscribe_all(registry)
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[tuple[str, EventHandler]]] = {}

    def register(
        self,
        event_type: str,
        handler: EventHandler,
        handler_name: str | None = None,
    ) -> None:
        """Register a handler for an event type.

        Args:
            event_type: The domain event type (e.g., USER_REGISTERED).
            handler: Async callable that takes the event payload.
            handler_name: Optional name (defaults to handler.__name__).
        """
        if event_type not in ALL_EVENT_TYPES:
            logger.warning(
                "registering_unknown_event_type",
                event_type=event_type,
                known_types=ALL_EVENT_TYPES,
            )

        name = handler_name or getattr(handler, "__name__", "anonymous")
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((name, handler))

        logger.info(
            "handler_registered",
            event_type=event_type,
            handler=name,
            total_for_type=len(self._handlers[event_type]),
        )

    def register_many(
        self,
        event_type: str,
        handlers: list[EventHandler],
    ) -> None:
        """Register multiple handlers for an event type."""
        for handler in handlers:
            self.register(event_type, handler)

    def get_handlers(self, event_type: str) -> list[tuple[str, EventHandler]]:
        """Return all handlers for an event type."""
        return self._handlers.get(event_type, [])

    def get_handler_count(self, event_type: str) -> int:
        """Return the number of handlers for an event type."""
        return len(self._handlers.get(event_type, []))

    def get_registered_event_types(self) -> list[str]:
        """Return event types that have at least one handler."""
        return list(self._handlers.keys())

    def get_stats(self) -> dict[str, int]:
        """Return stats: handler count per event type."""
        return {et: len(hs) for et, hs in self._handlers.items()}

    def clear(self) -> None:
        """Clear all handlers (for testing)."""
        self._handlers.clear()


# ============================================================
# Default handler implementations (wired in worker_main)
# ============================================================


async def noop_handler(payload: dict[str, Any]) -> None:
    """No-op handler — does nothing. Used as a placeholder."""
    pass


async def log_event_handler(payload: dict[str, Any]) -> None:
    """Log the event payload (for debugging)."""
    logger.info("event_received", payload_keys=list(payload.keys()))


__all__ = [
    "SubscriberRegistry",
    "EventHandler",
    "ALL_EVENT_TYPES",
    # Event type constants
    "USER_REGISTERED",
    "USER_LOGGED_IN",
    "USER_LOGGED_OUT",
    "EMAIL_VERIFICATION_REQUESTED",
    "PASSWORD_RESET_REQUESTED",
    "ATTEMPT_RECORDED",
    "MASTERY_UPDATED",
    "WEAK_CONCEPT_DETECTED",
    "REVIEW_SCHEDULED",
    "RECOMMENDATION_GENERATED",
    "ACHIEVEMENT_UNLOCKED",
    "NOTIFICATION_REQUESTED",
    "SUBSCRIPTION_CHANGED",
    "ORGANIZATION_CREATED",
    "CONTENT_PUBLISHED",
    "ALGORITHM_PUBLISHED",
    "SECURITY_INCIDENT_DETECTED",
]
