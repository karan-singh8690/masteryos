"""Event subscribers package.

Contains handlers for domain events. Each handler is an async callable
that takes a dict payload. Handlers are registered with the
OutboxDispatcher at worker startup.

Modules:
- notification_handlers: Create notifications in response to events
- email_handlers: Send emails in response to events
- analytics_handlers: Update analytics in response to events
"""

from app.workers.subscriber_registry import (
    SubscriberRegistry,
    ALL_EVENT_TYPES,
    # Event type constants
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
)

__all__ = [
    "SubscriberRegistry",
    "ALL_EVENT_TYPES",
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
