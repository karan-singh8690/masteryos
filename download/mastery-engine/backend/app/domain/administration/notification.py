"""Administration context — Notification aggregate root.

The :class:`Notification` is the aggregate root of a single
notification message queued for a user. It tracks the message's
identity, target user, notification type, channel, payload, lifecycle
state, and the timestamps for each lifecycle transition.

Lifecycle (state machine)::

    QUEUED ──mark_sent()──► SENT ──mark_delivered()──► DELIVERED
                                                       │
                                  ┌────────────────────┼────────────────────┐
                                  │                    │                    │
                                  ▼                    ▼                    ▼
                              OPENED              DISMISSED             (terminal)
                              (terminal)          (terminal)

    QUEUED ──mark_failed(reason)──► FAILED  (terminal)

Once a notification has reached ``OPENED``, ``DISMISSED``, or
``FAILED``, it is terminal — no further transitions are allowed.

Invariants enforced:
- ``notification_type`` is a non-empty string (1–128 chars).
- ``payload`` is a dict (may be empty).
- ``scheduled_at`` is set at queue time and never modified.
- State transitions follow the state machine above. Any other
  transition raises :class:`NotificationNotTransitionable`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

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
from app.domain.shared.ids import NotificationId, UserId
from app.domain.shared.kernel import (
    AggregateRoot,
    InvariantViolation,
    NotificationChannel,
    NotificationStatus,
)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class Notification(AggregateRoot):
    """The Notification aggregate root.

    Holds the notification's identity, target user, type, channel,
    payload, lifecycle state, and timestamps. All mutations go through
    methods on this class, which enforce the state machine and emit
    domain events.

    The public constructor is intended for **reconstitution** from
    persistence. To create a *new* notification, use
    :meth:`Notification.queue`.
    """

    #: Maximum length of the ``notification_type`` code.
    MAX_NOTIFICATION_TYPE_LENGTH: int = 128

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: NotificationId,
        user_id: UserId,
        notification_type: str,
        channel: NotificationChannel,
        payload: dict[str, Any] | None = None,
        status: NotificationStatus = NotificationStatus.QUEUED,
        scheduled_at: datetime | None = None,
        sent_at: datetime | None = None,
        delivered_at: datetime | None = None,
        opened_at: datetime | None = None,
        dismissed_at: datetime | None = None,
        failed_at: datetime | None = None,
        failure_reason: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self._id: NotificationId = id
        self._user_id: UserId = user_id
        self._notification_type: str = notification_type
        self._channel: NotificationChannel = channel
        self._payload: dict[str, Any] = dict(payload) if payload else {}
        self._status: NotificationStatus = status
        now = _utcnow()
        self._scheduled_at: datetime = scheduled_at or now
        self._sent_at: datetime | None = sent_at
        self._delivered_at: datetime | None = delivered_at
        self._opened_at: datetime | None = opened_at
        self._dismissed_at: datetime | None = dismissed_at
        self._failed_at: datetime | None = failed_at
        self._failure_reason: str | None = failure_reason
        self._created_at: datetime = created_at or now
        self._validate_invariants()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def queue(
        cls,
        user_id: UserId,
        notification_type: str,
        channel: NotificationChannel,
        payload: dict[str, Any] | None = None,
        scheduled_at: datetime | None = None,
    ) -> Notification:
        """Queue a new notification for a user.

        Args:
            user_id: The user the notification is for.
            notification_type: A stable type code (e.g.,
                ``"streak.at_risk"``, ``"billing.payment_failed"``).
            channel: The channel to send via
                (:class:`NotificationChannel.EMAIL`, ``PUSH``, or
                ``IN_APP``).
            payload: A free-form dict carrying the message content and
                template parameters.
            scheduled_at: When the notification should be sent. Defaults
                to ``now`` (immediate dispatch).

        Returns:
            A newly created, un-persisted :class:`Notification` in
            ``queued`` status. The caller must add it to the repository
            and call :meth:`collect_events` to publish the recorded
            events.

        Raises:
            InvariantViolation: If any field fails validation.
        """
        notification_id = NotificationId.generate()
        notification = cls(
            id=notification_id,
            user_id=user_id,
            notification_type=notification_type,
            channel=channel,
            payload=payload,
            status=NotificationStatus.QUEUED,
            scheduled_at=scheduled_at,
        )
        notification._record_event(
            NotificationQueued(
                notification_id=notification.id,
                user_id=user_id,
                notification_type=notification_type,
                channel=channel,
                scheduled_at=notification.scheduled_at,
                payload=dict(notification.payload),
            )
        )
        return notification

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> NotificationId:
        """The notification's unique identifier."""
        return self._id

    @property
    def user_id(self) -> UserId:
        """The user the notification is for."""
        return self._user_id

    @property
    def notification_type(self) -> str:
        """The stable type code."""
        return self._notification_type

    @property
    def channel(self) -> NotificationChannel:
        """The channel to send via."""
        return self._channel

    @property
    def payload(self) -> dict[str, Any]:
        """The message content / template params. Returns a copy."""
        return dict(self._payload)

    @property
    def status(self) -> NotificationStatus:
        """The notification's lifecycle status."""
        return self._status

    @property
    def scheduled_at(self) -> datetime:
        """When the notification was (or will be) dispatched."""
        return self._scheduled_at

    @property
    def sent_at(self) -> datetime | None:
        """When the notification was sent, or ``None``."""
        return self._sent_at

    @property
    def delivered_at(self) -> datetime | None:
        """When the notification was delivered, or ``None``."""
        return self._delivered_at

    @property
    def opened_at(self) -> datetime | None:
        """When the user opened the notification, or ``None``."""
        return self._opened_at

    @property
    def dismissed_at(self) -> datetime | None:
        """When the user dismissed the notification, or ``None``."""
        return self._dismissed_at

    @property
    def failed_at(self) -> datetime | None:
        """When the notification failed (terminal), or ``None``."""
        return self._failed_at

    @property
    def failure_reason(self) -> str | None:
        """The failure reason, or ``None``."""
        return self._failure_reason

    @property
    def created_at(self) -> datetime:
        """When this notification was created."""
        return self._created_at

    @property
    def is_queued(self) -> bool:
        """True if the notification is still queued (not yet sent)."""
        return self._status == NotificationStatus.QUEUED

    @property
    def is_sent(self) -> bool:
        """True if the notification has been sent (but not yet delivered)."""
        return self._status == NotificationStatus.SENT

    @property
    def is_delivered(self) -> bool:
        """True if the notification has been delivered."""
        return self._status == NotificationStatus.DELIVERED

    @property
    def is_opened(self) -> bool:
        """True if the user opened the notification (terminal)."""
        return self._status == NotificationStatus.OPENED

    @property
    def is_dismissed(self) -> bool:
        """True if the user dismissed the notification (terminal)."""
        return self._status == NotificationStatus.DISMISSED

    @property
    def is_failed(self) -> bool:
        """True if the notification failed (terminal)."""
        return self._status == NotificationStatus.FAILED

    @property
    def is_terminal(self) -> bool:
        """True if the notification is in a terminal state."""
        return self._status in (
            NotificationStatus.OPENED,
            NotificationStatus.DISMISSED,
            NotificationStatus.FAILED,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants; raise on failure."""
        if not isinstance(self._user_id, UserId):
            raise InvariantViolation(
                "Notification",
                f"user_id must be a UserId, got {type(self._user_id).__name__}",
            )
        if not isinstance(self._notification_type, str) or not self._notification_type.strip():
            raise InvariantViolation(
                "Notification",
                "notification_type must be a non-empty string",
            )
        if len(self._notification_type) > self.MAX_NOTIFICATION_TYPE_LENGTH:
            raise InvariantViolation(
                "Notification",
                f"notification_type must be at most {self.MAX_NOTIFICATION_TYPE_LENGTH} characters",
            )
        self._notification_type = self._notification_type.strip()
        if not isinstance(self._channel, NotificationChannel):
            raise InvariantViolation(
                "Notification",
                f"channel must be a NotificationChannel, got {type(self._channel).__name__}",
            )
        if not isinstance(self._status, NotificationStatus):
            raise InvariantViolation(
                "Notification",
                f"status must be a NotificationStatus, got {type(self._status).__name__}",
            )
        if not isinstance(self._payload, dict):
            raise InvariantViolation("Notification", "payload must be a dict")

    def _assert_status(
        self,
        expected: NotificationStatus,
        action: str,
    ) -> None:
        """Raise :class:`NotificationNotTransitionable` unless in ``expected`` status."""
        if self._status != expected:
            raise NotificationNotTransitionable(
                notification_id=self._id,
                current_status=self._status.value,
                attempted_action=action,
            )

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def mark_sent(self, now: datetime | None = None) -> None:
        """Transition from ``queued`` to ``sent``.

        Pre-state: ``queued``.
        Post-state: ``sent`` with ``sent_at`` set.

        Raises:
            NotificationNotTransitionable: If the notification is not
                in ``queued`` status.
        """
        self._assert_status(NotificationStatus.QUEUED, "mark_sent")
        timestamp = now or _utcnow()
        self._status = NotificationStatus.SENT
        self._sent_at = timestamp
        self._record_event(
            NotificationSent(
                notification_id=self._id,
                user_id=self._user_id,
                sent_at=timestamp,
            )
        )

    def mark_delivered(self, now: datetime | None = None) -> None:
        """Transition from ``sent`` to ``delivered``.

        Pre-state: ``sent``.
        Post-state: ``delivered`` with ``delivered_at`` set.

        Raises:
            NotificationNotTransitionable: If the notification is not
                in ``sent`` status.
        """
        self._assert_status(NotificationStatus.SENT, "mark_delivered")
        timestamp = now or _utcnow()
        self._status = NotificationStatus.DELIVERED
        self._delivered_at = timestamp
        self._record_event(
            NotificationDelivered(
                notification_id=self._id,
                user_id=self._user_id,
                delivered_at=timestamp,
            )
        )

    def mark_opened(self, now: datetime | None = None) -> None:
        """Transition from ``delivered`` to ``opened`` (terminal).

        Pre-state: ``delivered``.
        Post-state: ``opened`` (terminal) with ``opened_at`` set.

        Raises:
            NotificationNotTransitionable: If the notification is not
                in ``delivered`` status.
        """
        self._assert_status(NotificationStatus.DELIVERED, "mark_opened")
        timestamp = now or _utcnow()
        self._status = NotificationStatus.OPENED
        self._opened_at = timestamp
        self._record_event(
            NotificationOpened(
                notification_id=self._id,
                user_id=self._user_id,
                opened_at=timestamp,
            )
        )

    def dismiss(self, now: datetime | None = None) -> None:
        """Transition from ``delivered`` to ``dismissed`` (terminal).

        Pre-state: ``delivered``.
        Post-state: ``dismissed`` (terminal) with ``dismissed_at`` set.

        Raises:
            NotificationNotTransitionable: If the notification is not
                in ``delivered`` status.
        """
        self._assert_status(NotificationStatus.DELIVERED, "dismiss")
        timestamp = now or _utcnow()
        self._status = NotificationStatus.DISMISSED
        self._dismissed_at = timestamp
        self._record_event(
            NotificationDismissed(
                notification_id=self._id,
                user_id=self._user_id,
                dismissed_at=timestamp,
            )
        )

    def mark_failed(self, reason: str, now: datetime | None = None) -> None:
        """Transition from ``queued`` to ``failed`` (terminal).

        Pre-state: ``queued``.
        Post-state: ``failed`` (terminal) with ``failed_at`` and
        ``failure_reason`` set.

        Args:
            reason: A non-empty reason for the failure.

        Raises:
            NotificationNotTransitionable: If the notification is not
                in ``queued`` status.
            NotificationFailedError: Wraps the failure reason for
                callers that want the failure to bubble.
        """
        self._assert_status(NotificationStatus.QUEUED, "mark_failed")
        if not isinstance(reason, str) or not reason.strip():
            raise InvariantViolation(
                "Notification",
                "failure reason must be a non-empty string",
            )
        timestamp = now or _utcnow()
        self._status = NotificationStatus.FAILED
        self._failed_at = timestamp
        self._failure_reason = reason
        self._record_event(
            NotificationFailed(
                notification_id=self._id,
                user_id=self._user_id,
                failed_at=timestamp,
                reason=reason,
            )
        )
        # Surface the failure to callers that want it to bubble.
        raise NotificationFailedError(self._id, reason)

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Notification(id={self._id}, user_id={self._user_id}, "
            f"type={self._notification_type!r}, channel={self._channel.value!r}, "
            f"status={self._status.value!r})"
        )


__all__ = ["Notification"]
