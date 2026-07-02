"""Administration context — domain-specific exceptions.

These exceptions are raised by the Administration-context aggregates
when invariants are violated or invalid state transitions are
attempted. They are *narrow* subclasses of :class:`DomainError` so that
callers can catch a specific failure mode without inspecting error
messages.

All exceptions are pure Python and carry no framework dependencies.
"""

from __future__ import annotations

from typing import Any

from app.domain.shared.kernel import DomainError


class AdministrationError(DomainError):
    """Base class for all Administration-context domain errors.

    Catch this to handle any administration-specific failure generically.
    """


class NotificationFailedError(AdministrationError):
    """Raised when a notification cannot transition out of ``queued``.

    Carries the provider-side failure reason. The aggregate records the
    failure and transitions to ``failed`` (terminal); this exception is
    raised when the failure should bubble to the caller.
    """

    def __init__(self, notification_id: Any, reason: str) -> None:
        super().__init__(
            f"Notification {notification_id} failed: {reason}",
            code="NOTIFICATION_FAILED",
        )
        self.notification_id = notification_id
        self.reason = reason


class FeatureFlagAlreadyExists(AdministrationError):
    """Raised when creating a FeatureFlag whose key already exists.

    Invariant: feature-flag keys are unique within the system. A
    duplicate key indicates either a typo or a missing lookup before
    creation — the caller should retrieve the existing flag instead.
    """

    def __init__(self, key: str) -> None:
        super().__init__(
            f"FeatureFlag with key {key!r} already exists",
            code="FEATURE_FLAG_ALREADY_EXISTS",
        )
        self.key = key


class FeatureFlagNotActive(AdministrationError):
    """Raised when operating on a FeatureFlag that is not active.

    Invariant: updates and targeting-rule changes may only be applied
    to active flags. Retired flags are immutable — to change behaviour,
    create a new flag with a different key.
    """

    def __init__(self, key: str) -> None:
        super().__init__(
            f"FeatureFlag {key!r} is not active (retired or never activated)",
            code="FEATURE_FLAG_NOT_ACTIVE",
        )
        self.key = key


class CannotDissolveOrganization(AdministrationError):
    """Raised when dissolving an Organization in a non-dissolvable state.

    Invariant: an Organization may only be dissolved from the
    ``active`` or ``suspended`` state. Dissolving an already-dissolved
    organization is rejected (the operation is idempotent at the
    application layer; the aggregate surfaces it as an error).
    """

    def __init__(self, organization_id: Any, current_status: Any) -> None:
        super().__init__(
            f"Cannot dissolve Organization {organization_id} in status {current_status!r}",
            code="CANNOT_DISSOLVE_ORGANIZATION",
        )
        self.organization_id = organization_id
        self.current_status = current_status


class CannotSuspendOrganization(AdministrationError):
    """Raised when suspending an Organization that is not active."""

    def __init__(self, organization_id: Any, current_status: Any) -> None:
        super().__init__(
            f"Cannot suspend Organization {organization_id} in status {current_status!r}",
            code="CANNOT_SUSPEND_ORGANIZATION",
        )
        self.organization_id = organization_id
        self.current_status = current_status


class CannotReactivateOrganization(AdministrationError):
    """Raised when reactivating an Organization that is not suspended."""

    def __init__(self, organization_id: Any, current_status: Any) -> None:
        super().__init__(
            f"Cannot reactivate Organization {organization_id} in status {current_status!r}",
            code="CANNOT_REACTIVATE_ORGANIZATION",
        )
        self.organization_id = organization_id
        self.current_status = current_status


class NotificationNotTransitionable(AdministrationError):
    """Raised when a notification state transition is invalid.

    Invariant: the notification state machine is::

        QUEUED → SENT → DELIVERED → (OPENED | DISMISSED)
        QUEUED → FAILED  (terminal)

    Calling e.g. :meth:`Notification.mark_opened` on a notification
    that is still ``queued`` (not yet ``delivered``) raises this.
    """

    def __init__(self, notification_id: Any, current_status: Any, attempted_action: str) -> None:
        super().__init__(
            f"Cannot {attempted_action} notification {notification_id} in status {current_status!r}",
            code="NOTIFICATION_NOT_TRANSITIONABLE",
        )
        self.notification_id = notification_id
        self.current_status = current_status
        self.attempted_action = attempted_action


__all__ = [
    "AdministrationError",
    "CannotDissolveOrganization",
    "CannotReactivateOrganization",
    "CannotSuspendOrganization",
    "FeatureFlagAlreadyExists",
    "FeatureFlagNotActive",
    "NotificationFailedError",
    "NotificationNotTransitionable",
]
