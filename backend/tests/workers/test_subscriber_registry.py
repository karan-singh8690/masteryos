"""Tests for the subscriber registry.

Tests:
- Register a handler for an event type
- Register multiple handlers for the same event type
- Get handlers for an event type
- Get handler count
- Get registered event types
- Get stats
- Clear all handlers
- All 17 event types are defined
"""

from __future__ import annotations

import pytest

from app.workers.subscriber_registry import (
    ALL_EVENT_TYPES,
    SubscriberRegistry,
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


def test_all_17_event_types_defined():
    """All 17 event types from the spec are defined."""
    assert len(ALL_EVENT_TYPES) == 17
    assert USER_REGISTERED in ALL_EVENT_TYPES
    assert USER_LOGGED_IN in ALL_EVENT_TYPES
    assert USER_LOGGED_OUT in ALL_EVENT_TYPES
    assert EMAIL_VERIFICATION_REQUESTED in ALL_EVENT_TYPES
    assert PASSWORD_RESET_REQUESTED in ALL_EVENT_TYPES
    assert ATTEMPT_RECORDED in ALL_EVENT_TYPES
    assert MASTERY_UPDATED in ALL_EVENT_TYPES
    assert WEAK_CONCEPT_DETECTED in ALL_EVENT_TYPES
    assert REVIEW_SCHEDULED in ALL_EVENT_TYPES
    assert RECOMMENDATION_GENERATED in ALL_EVENT_TYPES
    assert ACHIEVEMENT_UNLOCKED in ALL_EVENT_TYPES
    assert NOTIFICATION_REQUESTED in ALL_EVENT_TYPES
    assert SUBSCRIPTION_CHANGED in ALL_EVENT_TYPES
    assert ORGANIZATION_CREATED in ALL_EVENT_TYPES
    assert CONTENT_PUBLISHED in ALL_EVENT_TYPES
    assert ALGORITHM_PUBLISHED in ALL_EVENT_TYPES
    assert SECURITY_INCIDENT_DETECTED in ALL_EVENT_TYPES


def test_event_type_names_are_correct():
    """Event type constants match their string values."""
    assert USER_REGISTERED == "UserRegistered"
    assert USER_LOGGED_IN == "UserLoggedIn"
    assert USER_LOGGED_OUT == "UserLoggedOut"
    assert ATTEMPT_RECORDED == "AttemptRecorded"
    assert MASTERY_UPDATED == "MasteryUpdated"
    assert WEAK_CONCEPT_DETECTED == "WeakConceptDetected"
    assert REVIEW_SCHEDULED == "ReviewScheduled"
    assert RECOMMENDATION_GENERATED == "RecommendationGenerated"
    assert ACHIEVEMENT_UNLOCKED == "AchievementUnlocked"
    assert NOTIFICATION_REQUESTED == "NotificationRequested"
    assert EMAIL_VERIFICATION_REQUESTED == "EmailVerificationRequested"
    assert PASSWORD_RESET_REQUESTED == "PasswordResetRequested"
    assert SUBSCRIPTION_CHANGED == "SubscriptionChanged"
    assert ORGANIZATION_CREATED == "OrganizationCreated"
    assert CONTENT_PUBLISHED == "ContentPublished"
    assert ALGORITHM_PUBLISHED == "AlgorithmPublished"
    assert SECURITY_INCIDENT_DETECTED == "SecurityIncidentDetected"


class TestSubscriberRegistry:
    """Tests for the SubscriberRegistry class."""

    def test_register_single_handler(self):
        """Registering a handler adds it to the registry."""
        registry = SubscriberRegistry()

        async def handler(payload):
            pass

        registry.register(USER_REGISTERED, handler)
        assert registry.get_handler_count(USER_REGISTERED) == 1

    def test_register_multiple_handlers_same_event(self):
        """Multiple handlers can be registered for the same event type."""
        registry = SubscriberRegistry()

        async def handler_1(payload):
            pass

        async def handler_2(payload):
            pass

        registry.register(USER_REGISTERED, handler_1, "handler_1")
        registry.register(USER_REGISTERED, handler_2, "handler_2")
        assert registry.get_handler_count(USER_REGISTERED) == 2

    def test_get_handlers_returns_all(self):
        """get_handlers returns all registered handlers."""
        registry = SubscriberRegistry()

        async def handler_1(payload):
            pass

        async def handler_2(payload):
            pass

        registry.register(ATTEMPT_RECORDED, handler_1, "h1")
        registry.register(ATTEMPT_RECORDED, handler_2, "h2")

        handlers = registry.get_handlers(ATTEMPT_RECORDED)
        assert len(handlers) == 2
        names = [h[0] for h in handlers]
        assert "h1" in names
        assert "h2" in names

    def test_get_handlers_unknown_event_returns_empty(self):
        """get_handlers returns empty list for unknown event type."""
        registry = SubscriberRegistry()
        assert registry.get_handlers("UnknownEvent") == []

    def test_get_registered_event_types(self):
        """get_registered_event_types returns event types with handlers."""
        registry = SubscriberRegistry()

        async def handler(payload):
            pass

        registry.register(USER_REGISTERED, handler)
        registry.register(ATTEMPT_RECORDED, handler)

        event_types = registry.get_registered_event_types()
        assert USER_REGISTERED in event_types
        assert ATTEMPT_RECORDED in event_types
        assert len(event_types) == 2

    def test_get_stats(self):
        """get_stats returns handler count per event type."""
        registry = SubscriberRegistry()

        async def handler(payload):
            pass

        registry.register(USER_REGISTERED, handler)
        registry.register(ATTEMPT_RECORDED, handler)
        registry.register(ATTEMPT_RECORDED, handler, "h2")

        stats = registry.get_stats()
        assert stats[USER_REGISTERED] == 1
        assert stats[ATTEMPT_RECORDED] == 2

    def test_clear(self):
        """clear removes all handlers."""
        registry = SubscriberRegistry()

        async def handler(payload):
            pass

        registry.register(USER_REGISTERED, handler)
        registry.clear()
        assert registry.get_handler_count(USER_REGISTERED) == 0

    def test_register_many(self):
        """register_many adds multiple handlers at once."""
        registry = SubscriberRegistry()

        async def handler_1(payload):
            pass

        async def handler_2(payload):
            pass

        registry.register_many(USER_LOGGED_IN, [handler_1, handler_2])
        assert registry.get_handler_count(USER_LOGGED_IN) == 2

    def test_register_unknown_event_type_logs_warning(self):
        """Registering an unknown event type doesn't raise (just warns)."""
        registry = SubscriberRegistry()

        async def handler(payload):
            pass

        # Should not raise
        registry.register("UnknownEvent", handler)
        assert registry.get_handler_count("UnknownEvent") == 1

    def test_handler_name_defaults_to_function_name(self):
        """Handler name defaults to the function's __name__."""
        registry = SubscriberRegistry()

        async def my_handler(payload):
            pass

        registry.register(USER_REGISTERED, my_handler)
        handlers = registry.get_handlers(USER_REGISTERED)
        assert handlers[0][0] == "my_handler"
