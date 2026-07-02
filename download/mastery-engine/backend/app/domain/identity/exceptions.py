"""Identity context — domain-specific exceptions.

These exceptions are raised by the User aggregate when invariants are
violated or invalid state transitions are attempted. They are *narrow*
subclasses of :class:`DomainError` so that callers can catch a specific
failure mode without inspecting error messages.

All exceptions are pure Python and carry no framework dependencies.
"""

from __future__ import annotations

from typing import Any

from app.domain.shared.kernel import DomainError


class IdentityError(DomainError):
    """Base class for all Identity-context domain errors.

    Catch this to handle any identity-specific failure generically.
    """


class EmailAlreadyRegistered(IdentityError):
    """Raised when registering a user with an email that already exists.

    Invariant: email addresses are unique within the system. The repository
    enforces this with a unique constraint, but the domain also raises this
    when a duplicate is detected at registration time.
    """

    def __init__(self, email: str) -> None:
        super().__init__(
            f"Email already registered: {email}",
            code="EMAIL_ALREADY_REGISTERED",
        )
        self.email = email


class EmailNotVerified(IdentityError):
    """Raised when an operation requires a verified email but none is on record.

    Invariant: certain operations (e.g., escalating to ACTIVE status) require
    that the user has verified ownership of their email address.
    """

    def __init__(self, user_id: Any) -> None:
        super().__init__(
            f"Email is not verified for user {user_id}",
            code="EMAIL_NOT_VERIFIED",
        )
        self.user_id = user_id


class CannotSuspendAdmin(IdentityError):
    """Raised when an attempt is made to suspend an administrative account.

    Invariant: administrative accounts cannot be suspended through the normal
    suspension flow. They must be demoted first, or handled via a separate
    administrative procedure. This prevents accidental lockout of operators
    who can recover the system.
    """

    def __init__(self, user_id: Any) -> None:
        super().__init__(
            f"Cannot suspend admin account {user_id}; demote before suspending",
            code="CANNOT_SUSPEND_ADMIN",
        )
        self.user_id = user_id


class CannotDisableMFAForAdmin(IdentityError):
    """Raised when an attempt is made to disable MFA on an administrative account.

    Invariant: administrative accounts must always have MFA enabled. This is
    a hard security control — admins cannot disable MFA on their own account
    to prevent privileged-account compromise.
    """

    def __init__(self, user_id: Any) -> None:
        super().__init__(
            f"Cannot disable MFA for admin account {user_id}",
            code="CANNOT_DISABLE_MFA_FOR_ADMIN",
        )
        self.user_id = user_id


class CannotCancelDeletionPastGrace(IdentityError):
    """Raised when cancellation of a pending deletion is attempted past the grace period.

    Invariant: account deletion enters a ``pending_deletion`` state with a
    scheduled anonymization timestamp. Once that timestamp has passed, the
    deletion can no longer be cancelled — the data is queued for anonymization
    to satisfy GDPR right-to-erasure workflows.
    """

    def __init__(self, user_id: Any, scheduled_anonymization_at: Any) -> None:
        super().__init__(
            f"Cannot cancel deletion for user {user_id}; grace period ended at "
            f"{scheduled_anonymization_at}",
            code="CANNOT_CANCEL_DELETION_PAST_GRACE",
        )
        self.user_id = user_id
        self.scheduled_anonymization_at = scheduled_anonymization_at


class AlreadyPendingDeletion(IdentityError):
    """Raised when deletion is requested for an account already pending deletion.

    Invariant: an account can only be in ``pending_deletion`` once. Repeated
    requests must be rejected — the original schedule stands.
    """

    def __init__(self, user_id: Any) -> None:
        super().__init__(
            f"User {user_id} is already pending deletion",
            code="ALREADY_PENDING_DELETION",
        )
        self.user_id = user_id


class MFAAlreadyEnabled(IdentityError):
    """Raised when enabling MFA on an account that already has it enabled.

    Invariant: MFA is a boolean flag — it cannot be enabled twice. The second
    enablement attempt indicates a caller bug or stale UI state.
    """

    def __init__(self, user_id: Any) -> None:
        super().__init__(
            f"MFA is already enabled for user {user_id}",
            code="MFA_ALREADY_ENABLED",
        )
        self.user_id = user_id


class MFANotEnabled(IdentityError):
    """Raised when disabling MFA on an account that does not have it enabled.

    Invariant: MFA cannot be disabled if it was never enabled. This guards
    against no-op calls masking caller bugs.
    """

    def __init__(self, user_id: Any) -> None:
        super().__init__(
            f"MFA is not enabled for user {user_id}",
            code="MFA_NOT_ENABLED",
        )
        self.user_id = user_id


__all__ = [
    "AlreadyPendingDeletion",
    "CannotCancelDeletionPastGrace",
    "CannotDisableMFAForAdmin",
    "CannotSuspendAdmin",
    "EmailAlreadyRegistered",
    "EmailNotVerified",
    "IdentityError",
    "MFAAlreadyEnabled",
    "MFANotEnabled",
]
