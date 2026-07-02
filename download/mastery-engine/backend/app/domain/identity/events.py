"""Identity context — domain events.

Domain events are immutable records of something that *happened* in the
Identity context. They are named in past tense and carry all the data a
subscriber needs to react.

All events inherit from :class:`DomainEvent` (which provides ``event_id``
and ``occurred_at``) and use ``@dataclass(frozen=True, kw_only=True)`` so
that required fields like ``user_id`` can follow the inherited defaulted
fields without ordering issues.

These events are *pure data*. They contain no behaviour and no side effects.
Subscribers (notification, audit, projection) live in the application and
infrastructure layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.shared.ids import UserId
from app.domain.shared.kernel import DomainEvent
from app.domain.shared.value_objects import Email


@dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    """Emitted when a new user account is created.

    Fired by :meth:`User.register`. The account is in
    ``pending_verification`` status at this point — the email has not yet
    been verified. Subscribers typically send a verification email.
    """

    user_id: UserId
    email: Email


@dataclass(frozen=True, kw_only=True)
class EmailVerified(DomainEvent):
    """Emitted when a user confirms ownership of their email address.

    Fired by :meth:`User.verify_email`. The account transitions from
    ``pending_verification`` to ``active``. Subscribers may grant initial
    entitlements or send a welcome notification.
    """

    user_id: UserId


@dataclass(frozen=True, kw_only=True)
class UserSuspended(DomainEvent):
    """Emitted when an active account is suspended.

    Fired by :meth:`User.suspend`. The account transitions from ``active``
    to ``suspended``. The reason is recorded for audit. Subscribers should
    revoke active sessions and refresh tokens.
    """

    user_id: UserId
    reason: str


@dataclass(frozen=True, kw_only=True)
class UserReactivated(DomainEvent):
    """Emitted when a suspended account is returned to active status.

    Fired by :meth:`User.reactivate`. The account transitions from
    ``suspended`` to ``active``. Subscribers may notify the user that
    access has been restored.
    """

    user_id: UserId


@dataclass(frozen=True, kw_only=True)
class AccountDeletionRequested(DomainEvent):
    """Emitted when a user (or admin) requests account deletion.

    Fired by :meth:`User.request_deletion`. The account transitions to
    ``pending_deletion`` and ``scheduled_anonymization_at`` is set. A
    grace period begins during which the user may cancel. After that
    timestamp, the account will be anonymized.

    Subscribers should send a cancellation link and schedule a job to
    perform the anonymization at ``scheduled_anonymization_at``.
    """

    user_id: UserId
    scheduled_anonymization_at: datetime


@dataclass(frozen=True, kw_only=True)
class AccountDeletionCancelled(DomainEvent):
    """Emitted when a pending deletion is cancelled within the grace period.

    Fired by :meth:`User.cancel_deletion`. The account returns to
    ``active`` status. Subscribers should cancel any scheduled
    anonymization jobs and notify the user.
    """

    user_id: UserId


@dataclass(frozen=True, kw_only=True)
class UserAnonymized(DomainEvent):
    """Emitted when a pending-deletion account is irreversibly anonymized.

    Fired by :meth:`User.anonymize`. The account transitions to
    ``anonymized`` — a terminal state. PII is replaced with placeholders.
    Subscribers must scrub downstream copies (backups, search indexes,
    analytics warehouses) per the GDPR right-to-erasure workflow.
    """

    user_id: UserId


@dataclass(frozen=True, kw_only=True)
class MFAEnabled(DomainEvent):
    """Emitted when multi-factor authentication is enabled on an account.

    Fired by :meth:`User.enable_mfa`. Subscribers should invalidate
    existing sessions (except the one performing the change) so that the
    user must re-authenticate with the second factor.
    """

    user_id: UserId


@dataclass(frozen=True, kw_only=True)
class MFADisabled(DomainEvent):
    """Emitted when multi-factor authentication is disabled on an account.

    Fired by :meth:`User.disable_mfa`. Subscribers should invalidate all
    sessions and notify the user that the security posture of the account
    has changed.
    """

    user_id: UserId


@dataclass(frozen=True, kw_only=True)
class UserProfileUpdated(DomainEvent):
    """Emitted when a user's profile fields are changed.

    Fired by :meth:`User.update_profile`. ``changed_fields`` is a mapping
    of field name → new value for any field that actually changed. This
    lets subscribers react only to relevant changes (e.g., timezone
    changes affect scheduling).
    """

    user_id: UserId
    changed_fields: dict[str, object] = field(default_factory=dict)


__all__ = [
    "AccountDeletionCancelled",
    "AccountDeletionRequested",
    "EmailVerified",
    "MFADisabled",
    "MFAEnabled",
    "UserAnonymized",
    "UserProfileUpdated",
    "UserReactivated",
    "UserRegistered",
    "UserSuspended",
]
