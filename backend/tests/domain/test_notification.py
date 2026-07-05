"""Comprehensive unit tests for the Notification aggregate (Administration context).

Tests cover:
- ``Notification.queue()`` factory creates a QUEUED notification
- State machine:
  - queued → sent → delivered → opened/dismissed (terminal)
  - queued → failed (terminal, raises ``NotificationFailedError``)
- Invalid transitions raise ``NotificationNotTransitionable``
- Terminal states cannot transition further
- Domain events for each transition
- Field validation (non-empty type, payload dict, channel enum)

These tests exercise only the pure-Python domain layer — no database,
HTTP or infrastructure.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.administration.events import (
    NotificationDelivered,
    NotificationDismissed,
    NotificationFailed,
    NotificationOpened,
    NotificationQueued,
    NotificationSent,
)
from app.domain.administration.exceptions import (
    NotificationFailedError,
    NotificationNotTransitionable,
)
from app.domain.administration.notification import Notification
from app.domain.shared.ids import NotificationId, UserId
from app.domain.shared.kernel import (
    InvariantViolation,
    NotificationChannel,
    NotificationStatus,
)


# ============================================================
# Helpers
# ============================================================


def _user_id() -> UserId:
    return UserId.generate()


def _queue(
    *,
    notification_type: str = "streak.at_risk",
    channel: NotificationChannel = NotificationChannel.EMAIL,
    payload: dict[str, object] | None = None,
    scheduled_at: datetime | None = None,
) -> Notification:
    return Notification.queue(
        user_id=_user_id(),
        notification_type=notification_type,
        channel=channel,
        payload=payload or {"message": "Your streak is at risk!"},
        scheduled_at=scheduled_at,
    )


# ============================================================
# Factory
# ============================================================


class TestNotificationQueue:
    """Tests for the ``Notification.queue()`` factory."""

    def test_queue_creates_queued_notification(self) -> None:
        n = _queue()
        assert n.status == NotificationStatus.QUEUED
        assert n.is_queued is True

    def test_queue_generates_id(self) -> None:
        n = _queue()
        assert isinstance(n.id, NotificationId)

    def test_queue_sets_user_id(self) -> None:
        uid = _user_id()
        n = Notification.queue(
            user_id=uid,
            notification_type="x",
            channel=NotificationChannel.EMAIL,
        )
        assert n.user_id == uid

    def test_queue_sets_notification_type(self) -> None:
        n = _queue(notification_type="billing.payment_failed")
        assert n.notification_type == "billing.payment_failed"

    def test_queue_sets_channel(self) -> None:
        n = _queue(channel=NotificationChannel.PUSH)
        assert n.channel == NotificationChannel.PUSH

    def test_queue_sets_payload(self) -> None:
        payload = {"message": "hi", "streak": 5}
        n = _queue(payload=payload)
        assert n.payload == payload

    def test_queue_default_payload_is_empty_dict(self) -> None:
        n = Notification.queue(
            user_id=_user_id(),
            notification_type="x",
            channel=NotificationChannel.EMAIL,
        )
        assert n.payload == {}

    def test_queue_default_scheduled_at_is_now(self) -> None:
        before = datetime.now(UTC)
        n = _queue()
        after = datetime.now(UTC)
        assert before <= n.scheduled_at <= after

    def test_queue_records_notification_queued_event(self) -> None:
        n = _queue()
        events = n.collect_events()
        assert len(events) == 1
        evt = events[0]
        assert isinstance(evt, NotificationQueued)
        assert evt.notification_id == n.id
        assert evt.user_id == n.user_id

    def test_queue_rejects_empty_notification_type(self) -> None:
        with pytest.raises(InvariantViolation):
            _queue(notification_type="")

    def test_queue_rejects_whitespace_only_notification_type(self) -> None:
        with pytest.raises(InvariantViolation):
            _queue(notification_type="   ")

    def test_queue_strips_whitespace_around_type(self) -> None:
        n = _queue(notification_type="  billing.payment_failed  ")
        assert n.notification_type == "billing.payment_failed"


# ============================================================
# mark_sent
# ============================================================


class TestNotificationMarkSent:
    """Tests for ``mark_sent()``."""

    def test_mark_sent_transitions_to_sent(self) -> None:
        n = _queue()
        n.mark_sent()
        assert n.status == NotificationStatus.SENT
        assert n.is_sent is True

    def test_mark_sent_sets_sent_at(self) -> None:
        n = _queue()
        when = datetime(2024, 6, 1, tzinfo=UTC)
        n.mark_sent(now=when)
        assert n.sent_at == when

    def test_mark_sent_records_event(self) -> None:
        n = _queue()
        n.clear_events()
        n.mark_sent()
        events = n.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], NotificationSent)

    def test_mark_sent_when_sent_raises(self) -> None:
        n = _queue()
        n.mark_sent()
        with pytest.raises(NotificationNotTransitionable):
            n.mark_sent()

    def test_mark_sent_when_delivered_raises(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        with pytest.raises(NotificationNotTransitionable):
            n.mark_sent()

    def test_mark_sent_when_failed_raises(self) -> None:
        n = _queue()
        try:
            n.mark_failed("provider error")
        except NotificationFailedError:
            pass
        with pytest.raises(NotificationNotTransitionable):
            n.mark_sent()


# ============================================================
# mark_delivered
# ============================================================


class TestNotificationMarkDelivered:
    """Tests for ``mark_delivered()``."""

    def test_mark_delivered_transitions_to_delivered(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        assert n.status == NotificationStatus.DELIVERED
        assert n.is_delivered is True

    def test_mark_delivered_sets_delivered_at(self) -> None:
        n = _queue()
        n.mark_sent()
        when = datetime(2024, 6, 1, tzinfo=UTC)
        n.mark_delivered(now=when)
        assert n.delivered_at == when

    def test_mark_delivered_records_event(self) -> None:
        n = _queue()
        n.mark_sent()
        n.clear_events()
        n.mark_delivered()
        events = n.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], NotificationDelivered)

    def test_mark_delivered_when_queued_raises(self) -> None:
        n = _queue()
        with pytest.raises(NotificationNotTransitionable):
            n.mark_delivered()

    def test_mark_delivered_when_delivered_raises(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        with pytest.raises(NotificationNotTransitionable):
            n.mark_delivered()


# ============================================================
# mark_opened
# ============================================================


class TestNotificationMarkOpened:
    """Tests for ``mark_opened()`` (terminal)."""

    def test_mark_opened_transitions_to_opened(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        n.mark_opened()
        assert n.status == NotificationStatus.OPENED
        assert n.is_opened is True
        assert n.is_terminal is True

    def test_mark_opened_sets_opened_at(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        when = datetime(2024, 6, 1, tzinfo=UTC)
        n.mark_opened(now=when)
        assert n.opened_at == when

    def test_mark_opened_records_event(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        n.clear_events()
        n.mark_opened()
        events = n.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], NotificationOpened)

    def test_mark_opened_when_queued_raises(self) -> None:
        n = _queue()
        with pytest.raises(NotificationNotTransitionable):
            n.mark_opened()

    def test_mark_opened_when_delivered_then_dismissed_raises(self) -> None:
        """Once dismissed, the notification cannot be opened."""
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        n.dismiss()
        with pytest.raises(NotificationNotTransitionable):
            n.mark_opened()

    def test_mark_opened_when_already_opened_raises(self) -> None:
        """Terminal state: cannot transition further."""
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        n.mark_opened()
        with pytest.raises(NotificationNotTransitionable):
            n.mark_opened()


# ============================================================
# dismiss
# ============================================================


class TestNotificationDismiss:
    """Tests for ``dismiss()`` (terminal)."""

    def test_dismiss_transitions_to_dismissed(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        n.dismiss()
        assert n.status == NotificationStatus.DISMISSED
        assert n.is_dismissed is True
        assert n.is_terminal is True

    def test_dismiss_sets_dismissed_at(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        when = datetime(2024, 6, 1, tzinfo=UTC)
        n.dismiss(now=when)
        assert n.dismissed_at == when

    def test_dismiss_records_event(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        n.clear_events()
        n.dismiss()
        events = n.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], NotificationDismissed)

    def test_dismiss_when_queued_raises(self) -> None:
        n = _queue()
        with pytest.raises(NotificationNotTransitionable):
            n.dismiss()

    def test_dismiss_when_opened_raises(self) -> None:
        """Already terminal — cannot dismiss."""
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        n.mark_opened()
        with pytest.raises(NotificationNotTransitionable):
            n.dismiss()


# ============================================================
# mark_failed
# ============================================================


class TestNotificationMarkFailed:
    """Tests for ``mark_failed()`` (terminal, raises after recording)."""

    def test_mark_failed_transitions_to_failed(self) -> None:
        n = _queue()
        with pytest.raises(NotificationFailedError):
            n.mark_failed("provider 500")
        assert n.status == NotificationStatus.FAILED
        assert n.is_failed is True
        assert n.is_terminal is True

    def test_mark_failed_sets_failed_at_and_reason(self) -> None:
        n = _queue()
        when = datetime(2024, 6, 1, tzinfo=UTC)
        with pytest.raises(NotificationFailedError):
            n.mark_failed("bounced", now=when)
        assert n.failed_at == when
        assert n.failure_reason == "bounced"

    def test_mark_failed_records_event(self) -> None:
        """The ``NotificationFailed`` event is recorded *before* the
        ``NotificationFailedError`` is raised."""
        n = _queue()
        n.clear_events()
        with pytest.raises(NotificationFailedError):
            n.mark_failed("bounced")
        events = n.collect_events()
        assert len(events) == 1
        evt = events[0]
        assert isinstance(evt, NotificationFailed)
        assert evt.reason == "bounced"

    def test_mark_failed_when_sent_raises_no_state_change(self) -> None:
        """A SENT notification cannot fail — only QUEUED can."""
        n = _queue()
        n.mark_sent()
        with pytest.raises(NotificationNotTransitionable):
            n.mark_failed("x")
        # Status unchanged
        assert n.status == NotificationStatus.SENT

    def test_mark_failed_when_already_failed_raises(self) -> None:
        """Calling mark_failed on an already-failed notification raises
        ``NotificationNotTransitionable`` (not ``NotificationFailedError``)."""
        n = _queue()
        with pytest.raises(NotificationFailedError):
            n.mark_failed("first failure")
        with pytest.raises(NotificationNotTransitionable):
            n.mark_failed("second failure")


# ============================================================
# Predicates
# ============================================================


class TestNotificationPredicates:
    """Tests for the ``is_*`` and ``is_terminal`` predicates."""

    def test_is_queued_true_initially(self) -> None:
        assert _queue().is_queued is True

    def test_is_sent_true_after_mark_sent(self) -> None:
        n = _queue()
        n.mark_sent()
        assert n.is_sent is True

    def test_is_delivered_true_after_mark_delivered(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        assert n.is_delivered is True

    def test_is_opened_true_after_mark_opened(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        n.mark_opened()
        assert n.is_opened is True

    def test_is_dismissed_true_after_dismiss(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        n.dismiss()
        assert n.is_dismissed is True

    def test_is_failed_true_after_mark_failed(self) -> None:
        n = _queue()
        try:
            n.mark_failed("x")
        except NotificationFailedError:
            pass
        assert n.is_failed is True

    @pytest.mark.parametrize(
        "setup,expected",
        [
            (lambda n: None, False),  # QUEUED
            (lambda n: n.mark_sent(), False),
            (lambda n: (n.mark_sent(), n.mark_delivered()), False),
            (lambda n: (n.mark_sent(), n.mark_delivered(), n.mark_opened()), True),
            (lambda n: (n.mark_sent(), n.mark_delivered(), n.dismiss()), True),
        ],
    )
    def test_is_terminal_only_in_terminal_states(self, setup, expected) -> None:
        n = _queue()
        setup(n)
        assert n.is_terminal is expected

    def test_is_terminal_true_when_failed(self) -> None:
        n = _queue()
        try:
            n.mark_failed("x")
        except NotificationFailedError:
            pass
        assert n.is_terminal is True


# ============================================================
# Event sequence
# ============================================================


class TestNotificationEventSequence:
    """End-to-end event sequence tests."""

    def test_queue_to_opened_event_sequence(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        n.mark_opened()
        events = n.collect_events()
        types = [type(e).__name__ for e in events]
        assert types == [
            "NotificationQueued",
            "NotificationSent",
            "NotificationDelivered",
            "NotificationOpened",
        ]

    def test_queue_to_dismissed_event_sequence(self) -> None:
        n = _queue()
        n.mark_sent()
        n.mark_delivered()
        n.dismiss()
        events = n.collect_events()
        types = [type(e).__name__ for e in events]
        assert types == [
            "NotificationQueued",
            "NotificationSent",
            "NotificationDelivered",
            "NotificationDismissed",
        ]

    def test_queue_to_failed_event_sequence(self) -> None:
        n = _queue()
        try:
            n.mark_failed("x")
        except NotificationFailedError:
            pass
        events = n.collect_events()
        types = [type(e).__name__ for e in events]
        assert types == ["NotificationQueued", "NotificationFailed"]

    def test_collect_events_clears_internal_list(self) -> None:
        n = _queue()
        first = n.collect_events()
        second = n.collect_events()
        assert len(first) == 1
        assert second == []


# ============================================================
# Channel support
# ============================================================


class TestNotificationChannels:
    """Tests that the aggregate supports all three channels."""

    @pytest.mark.parametrize(
        "channel",
        [
            NotificationChannel.EMAIL,
            NotificationChannel.PUSH,
            NotificationChannel.IN_APP,
        ],
    )
    def test_each_channel_can_queue_and_send(self, channel) -> None:
        n = _queue(channel=channel)
        assert n.channel == channel
        n.mark_sent()
        assert n.is_sent is True
