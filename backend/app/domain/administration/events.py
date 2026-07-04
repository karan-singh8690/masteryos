"""Administration context — domain events.

Domain events are immutable records of something that *happened* in the
Administration context. They are named in past tense and carry all the
data a subscriber needs to react.

All events inherit from :class:`DomainEvent` (which provides ``event_id``
and ``occurred_at``) and use ``@dataclass(frozen=True, kw_only=True)``
so that required fields can follow the inherited defaulted fields
without ordering issues.

These events are *pure data*. They contain no behaviour and no side
effects. Subscribers (notification dispatchers, audit-log writers,
flag-evaluation cache invalidators) live in the application and
infrastructure layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.shared.ids import (
    AuditLogId,
    FeatureFlagId,
    NotificationId,
    OrganizationId,
    UserId,
)
from app.domain.shared.kernel import (
    DomainEvent,
    NotificationChannel,
    NotificationStatus,
)


# ============================================================
# Notification events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class NotificationQueued(DomainEvent):
    """Emitted when a new notification is queued for a user.

    Fired by :meth:`Notification.queue`. Subscribers (the notification
    dispatcher) pick up the queued notification and send it via the
    chosen channel.
    """

    notification_id: NotificationId
    user_id: UserId
    notification_type: str
    channel: NotificationChannel
    scheduled_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class NotificationSent(DomainEvent):
    """Emitted when a notification is dispatched to the provider.

    Fired by :meth:`Notification.mark_sent`. The provider has accepted
    the message; delivery confirmation (``mark_delivered``) follows
    asynchronously.
    """

    notification_id: NotificationId
    user_id: UserId
    sent_at: datetime


@dataclass(frozen=True, kw_only=True)
class NotificationDelivered(DomainEvent):
    """Emitted when a notification is confirmed delivered by the provider.

    Fired by :meth:`Notification.mark_delivered`. Subscribers may now
    show the notification in the in-app inbox or update the delivery
    analytics.
    """

    notification_id: NotificationId
    user_id: UserId
    delivered_at: datetime


@dataclass(frozen=True, kw_only=True)
class NotificationOpened(DomainEvent):
    """Emitted when a user opens a delivered notification.

    Fired by :meth:`Notification.mark_opened`. Subscribers may record
    engagement metrics.
    """

    notification_id: NotificationId
    user_id: UserId
    opened_at: datetime


@dataclass(frozen=True, kw_only=True)
class NotificationDismissed(DomainEvent):
    """Emitted when a user dismisses a delivered notification.

    Fired by :meth:`Notification.dismiss`. Subscribers should stop any
    in-app display of the notification.
    """

    notification_id: NotificationId
    user_id: UserId
    dismissed_at: datetime


@dataclass(frozen=True, kw_only=True)
class NotificationFailed(DomainEvent):
    """Emitted when a notification transitions to ``failed``.

    Fired by :meth:`Notification.mark_failed`. The provider rejected
    the message (or the dispatcher gave up retrying). The notification
    is now terminal; subscribers should record the failure and alert
    on-call if the failure rate exceeds SLO.
    """

    notification_id: NotificationId
    user_id: UserId
    failed_at: datetime
    reason: str


# ============================================================
# FeatureFlag events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class FeatureFlagCreated(DomainEvent):
    """Emitted when a new FeatureFlag is created.

    Fired by :meth:`FeatureFlag.create`. The flag starts in ``active``
    status with no targeting rules. Subscribers (the flag-evaluation
    cache) should warm the flag's value so the first evaluation does
    not hit a cold path.
    """

    flag_id: FeatureFlagId
    key: str
    description: str
    owner: str
    default_value: Any


@dataclass(frozen=True, kw_only=True)
class FeatureFlagUpdated(DomainEvent):
    """Emitted when a FeatureFlag's targeting rules or default are updated.

    Fired by :meth:`FeatureFlag.update`. Subscribers must invalidate
    any cached flag evaluation; the next evaluation will re-read the
    new targeting rules.
    """

    flag_id: FeatureFlagId
    key: str
    changed_fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class FeatureFlagRetired(DomainEvent):
    """Emitted when a FeatureFlag is retired.

    Fired by :meth:`FeatureFlag.retire`. The flag is now immutable —
    evaluations should fall back to the ``default_value`` snapshot
    captured at retirement time. Subscribers may purge the flag from
    hot caches after a grace period.
    """

    flag_id: FeatureFlagId
    key: str
    retired_at: datetime


# ============================================================
# Organization events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class OrganizationCreated(DomainEvent):
    """Emitted when a new Organization is created.

    Fired by :meth:`Organization.create`. Subscribers may provision
    per-organization infrastructure (search index shard, analytics
    partition, billing account) keyed by ``organization_id``.
    """

    organization_id: OrganizationId
    name: str


@dataclass(frozen=True, kw_only=True)
class OrganizationSuspended(DomainEvent):
    """Emitted when an active Organization is suspended.

    Fired by :meth:`Organization.suspend`. Subscribers should revoke
    access for the organization's members (typically by invalidating
    their sessions) and pause any scheduled jobs scoped to the
    organization.
    """

    organization_id: OrganizationId
    suspended_at: datetime


@dataclass(frozen=True, kw_only=True)
class OrganizationReactivated(DomainEvent):
    """Emitted when a suspended Organization is returned to active status.

    Fired by :meth:`Organization.reactivate`. Subscribers may resume
    scheduled jobs and notify members that access has been restored.
    """

    organization_id: OrganizationId
    reactivated_at: datetime


@dataclass(frozen=True, kw_only=True)
class OrganizationDissolved(DomainEvent):
    """Emitted when an Organization is dissolved (terminal).

    Fired by :meth:`Organization.dissolve`. The organization is now
    non-functional — its members can no longer authenticate, and its
    data is queued for archival. Subscribers must trigger the
    data-retention workflow (archive, then erase after the legal
    retention window).
    """

    organization_id: OrganizationId
    dissolved_at: datetime


# ============================================================
# AuditLog events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class AuditLogRecorded(DomainEvent):
    """Emitted when a new AuditLog entry is recorded.

    Fired by :meth:`AuditLog.record`. Because audit logs are
    append-only, this event fires exactly once per entry. Subscribers
    may forward the entry to a tamper-evident store (e.g., a
    hash-chained log) and to long-term cold storage for compliance.
    """

    audit_log_id: AuditLogId
    actor_user_id: UUID | None
    action: str
    target_type: str
    target_id: UUID | None
    outcome: str


__all__ = [
    "AuditLogRecorded",
    "FeatureFlagCreated",
    "FeatureFlagRetired",
    "FeatureFlagUpdated",
    "NotificationDelivered",
    "NotificationDismissed",
    "NotificationFailed",
    "NotificationOpened",
    "NotificationQueued",
    "NotificationSent",
    "OrganizationCreated",
    "OrganizationDissolved",
    "OrganizationReactivated",
    "OrganizationSuspended",
]
