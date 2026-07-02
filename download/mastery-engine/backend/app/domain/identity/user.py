"""Identity context — User aggregate root.

The :class:`User` is the aggregate root of the Identity context. It owns
its :class:`UserProfile` and one or more :class:`UserCredential` entities.
All changes to the aggregate go through the root, which enforces
invariants and records domain events.

Lifecycle (state machine)::

    PENDING_VERIFICATION
           │  verify_email()
           ▼
         ACTIVE ◄────────────► SUSPENDED
           │  suspend()            ▲  reactivate()
           │  request_deletion()   │
           ▼                        │
     PENDING_DELETION ──────────────┘
           │  cancel_deletion()   (within grace period)
           │  anonymize()
           ▼
       ANONYMIZED  (terminal)

Invariants enforced:
- Email must be verified before status can go ACTIVE.
- An administrative account cannot be suspended (caller passes ``is_admin``).
- An administrative account cannot have MFA disabled.
- Anonymization requires the account to be in PENDING_DELETION.
- Cancel-deletion is only allowed before ``scheduled_anonymization_at``.
- MFA cannot be enabled twice; cannot be disabled if not enabled.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.domain.identity.credential import UserCredential
from app.domain.identity.events import (
    AccountDeletionCancelled,
    AccountDeletionRequested,
    EmailVerified,
    MFADisabled,
    MFAEnabled,
    UserAnonymized,
    UserProfileUpdated,
    UserReactivated,
    UserRegistered,
    UserSuspended,
)
from app.domain.identity.exceptions import (
    AlreadyPendingDeletion,
    CannotCancelDeletionPastGrace,
    CannotDisableMFAForAdmin,
    CannotSuspendAdmin,
    MFAAlreadyEnabled,
    MFANotEnabled,
)
from app.domain.identity.profile import UserProfile
from app.domain.shared.ids import UserId
from app.domain.shared.kernel import (
    AggregateRoot,
    InvalidStateTransition,
    UserStatus,
)
from app.domain.shared.value_objects import Email


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class User(AggregateRoot):
    """The User aggregate root.

    Holds the user's identity (id, email, status), authentication state
    (MFA flag, credentials), and profile. All mutations go through
    methods on this class, which enforce invariants and emit domain
    events via :meth:`AggregateRoot._record_event`.

    The public constructor is intended for **reconstitution** from
    persistence (the repository uses it to rebuild an aggregate from
    stored state). To create a *new* user, use :meth:`User.register`.
    """

    #: Default grace period between a deletion request and forced anonymization.
    #: During this window the user may cancel. Configurable per call.
    DELETION_GRACE_PERIOD: timedelta = timedelta(days=30)

    #: Placeholder email used after anonymization. The ``.invalid`` TLD
    #: guarantees it can never collide with a real address.
    _ANONYMIZED_EMAIL_DOMAIN: str = "anonymized.invalid"

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: UserId,
        email: Email,
        status: UserStatus,
        mfa_enabled: bool = False,
        email_verified_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        deleted_at: datetime | None = None,
        anonymized_at: datetime | None = None,
        scheduled_anonymization_at: datetime | None = None,
        suspension_reason: str | None = None,
        profile: UserProfile,
        credentials: list[UserCredential] | None = None,
    ) -> None:
        super().__init__()
        self._id: UserId = id
        self._email: Email = email
        self._status: UserStatus = status
        self._mfa_enabled: bool = bool(mfa_enabled)
        self._email_verified_at: datetime | None = email_verified_at
        self._created_at: datetime = created_at or _utcnow()
        self._updated_at: datetime = updated_at or self._created_at
        self._deleted_at: datetime | None = deleted_at
        self._anonymized_at: datetime | None = anonymized_at
        self._scheduled_anonymization_at: datetime | None = scheduled_anonymization_at
        self._suspension_reason: str | None = suspension_reason
        self._profile: UserProfile = profile
        self._credentials: list[UserCredential] = list(credentials) if credentials else []

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def register(
        cls,
        email: Email,
        password_hash: str,
        display_name: str,
    ) -> User:
        """Register a new user.

        Creates a User in ``PENDING_VERIFICATION`` status with a single
        PASSWORD credential and a default profile. The caller is
        responsible for sending a verification email (typically by
        subscribing to the emitted :class:`UserRegistered` event).

        Args:
            email: The user's email address (validated by :class:`Email`).
            password_hash: A pre-hashed password. The domain never accepts
                plaintext — hashing is an infrastructure concern.
            display_name: The user's display name (1–100 chars).

        Returns:
            A newly created, un-persisted :class:`User`. The caller (an
            application service) must add it to the repository and then
            call :meth:`collect_events` to publish the recorded events.

        Raises:
            InvariantViolation: If ``display_name`` or ``password_hash``
                fails validation (via the nested entities).
        """
        user_id = UserId.generate()
        now = _utcnow()
        profile = UserProfile(
            user_id=user_id,
            display_name=display_name,
        )
        credential = UserCredential.for_password(
            user_id=user_id,
            password_hash=password_hash,
        )
        user = cls(
            id=user_id,
            email=email,
            status=UserStatus.PENDING_VERIFICATION,
            mfa_enabled=False,
            email_verified_at=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
            anonymized_at=None,
            scheduled_anonymization_at=None,
            suspension_reason=None,
            profile=profile,
            credentials=[credential],
        )
        user._record_event(UserRegistered(user_id=user.id, email=user.email))
        return user

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> UserId:
        """The user's unique identifier."""
        return self._id

    @property
    def email(self) -> Email:
        """The user's email address (anonymized placeholder after deletion)."""
        return self._email

    @property
    def status(self) -> UserStatus:
        """The user's current lifecycle status."""
        return self._status

    @property
    def mfa_enabled(self) -> bool:
        """Whether multi-factor authentication is enabled."""
        return self._mfa_enabled

    @property
    def email_verified_at(self) -> datetime | None:
        """When the user verified their email, or ``None`` if unverified."""
        return self._email_verified_at

    @property
    def created_at(self) -> datetime:
        """When the user account was created."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """When the user account was last modified."""
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        """When deletion was requested (set in PENDING_DELETION state)."""
        return self._deleted_at

    @property
    def anonymized_at(self) -> datetime | None:
        """When the user was anonymized (terminal state)."""
        return self._anonymized_at

    @property
    def scheduled_anonymization_at(self) -> datetime | None:
        """When the pending deletion will become irreversible."""
        return self._scheduled_anonymization_at

    @property
    def suspension_reason(self) -> str | None:
        """The reason for the current/most recent suspension."""
        return self._suspension_reason

    @property
    def profile(self) -> UserProfile:
        """The user's profile (mutable local entity)."""
        return self._profile

    @property
    def credentials(self) -> list[UserCredential]:
        """A snapshot list of the user's credentials.

        Returns a copy so callers cannot mutate the aggregate's internal
        list directly — credential changes must go through aggregate
        methods.
        """
        return list(self._credentials)

    @property
    def is_active(self) -> bool:
        """True if the user is in the ACTIVE status."""
        return self._status == UserStatus.ACTIVE

    @property
    def is_pending_deletion(self) -> bool:
        """True if the user has requested deletion and is in the grace window."""
        return self._status == UserStatus.PENDING_DELETION

    @property
    def is_anonymized(self) -> bool:
        """True if the user has been anonymized (terminal state)."""
        return self._status == UserStatus.ANONYMIZED

    @property
    def email_verified(self) -> bool:
        """True if the email has been verified at any point."""
        return self._email_verified_at is not None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _touch(self, now: datetime | None = None) -> None:
        """Update the ``updated_at`` timestamp."""
        self._updated_at = now or _utcnow()

    def _assert_status(self, expected: UserStatus, action: str) -> None:
        """Raise :class:`InvalidStateTransition` unless in ``expected`` status."""
        if self._status != expected:
            raise InvalidStateTransition(
                entity="User",
                current_state=self._status.value,
                attempted_action=action,
            )

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    def verify_email(self, now: datetime | None = None) -> None:
        """Verify the user's email and transition to ACTIVE.

        Pre-state: ``PENDING_VERIFICATION``.
        Post-state: ``ACTIVE`` with ``email_verified_at`` set.

        Raises:
            InvalidStateTransition: If the user is not in
                ``PENDING_VERIFICATION`` (e.g., already active or anonymized).
        """
        self._assert_status(UserStatus.PENDING_VERIFICATION, "verify_email")
        timestamp = now or _utcnow()
        self._email_verified_at = timestamp
        self._status = UserStatus.ACTIVE
        self._touch(timestamp)
        self._record_event(EmailVerified(user_id=self._id))

    # ------------------------------------------------------------------
    # Suspension
    # ------------------------------------------------------------------

    def suspend(self, reason: str, *, is_admin: bool = False, now: datetime | None = None) -> None:
        """Suspend an active user account.

        Pre-state: ``ACTIVE``.
        Post-state: ``SUSPENDED`` with ``suspension_reason`` recorded.

        Args:
            reason: A human-readable reason for the suspension (audit log).
            is_admin: Must be ``True`` if the target account is an
                administrator. Passing ``True`` causes suspension to be
                refused — admins must be demoted before suspension.
            now: Optional timestamp (for testing); defaults to UTC now.

        Raises:
            CannotSuspendAdmin: If ``is_admin`` is ``True``.
            InvalidStateTransition: If the user is not in ``ACTIVE`` status.
        """
        if is_admin:
            raise CannotSuspendAdmin(self._id)
        self._assert_status(UserStatus.ACTIVE, "suspend")
        if not reason or not isinstance(reason, str):
            raise InvalidStateTransition(
                entity="User",
                current_state=self._status.value,
                attempted_action="suspend_without_reason",
            )
        timestamp = now or _utcnow()
        self._status = UserStatus.SUSPENDED
        self._suspension_reason = reason
        self._touch(timestamp)
        self._record_event(UserSuspended(user_id=self._id, reason=reason))

    def reactivate(self, now: datetime | None = None) -> None:
        """Reactivate a previously suspended account.

        Pre-state: ``SUSPENDED``.
        Post-state: ``ACTIVE`` with ``suspension_reason`` cleared.

        Raises:
            InvalidStateTransition: If the user is not in ``SUSPENDED``.
        """
        self._assert_status(UserStatus.SUSPENDED, "reactivate")
        timestamp = now or _utcnow()
        self._status = UserStatus.ACTIVE
        self._suspension_reason = None
        self._touch(timestamp)
        self._record_event(UserReactivated(user_id=self._id))

    # ------------------------------------------------------------------
    # Deletion lifecycle
    # ------------------------------------------------------------------

    def request_deletion(
        self,
        *,
        scheduled_anonymization_at: datetime | None = None,
        now: datetime | None = None,
    ) -> None:
        """Request account deletion, entering the grace window.

        Pre-state: ``ACTIVE``.
        Post-state: ``PENDING_DELETION`` with ``deleted_at`` and
        ``scheduled_anonymization_at`` set.

        Args:
            scheduled_anonymization_at: When the grace period ends and the
                account becomes eligible for anonymization. Defaults to
                ``now + DELETION_GRACE_PERIOD``.
            now: Optional timestamp (for testing); defaults to UTC now.

        Raises:
            AlreadyPendingDeletion: If already in ``PENDING_DELETION``.
            InvalidStateTransition: If not in ``ACTIVE`` status.
        """
        if self._status == UserStatus.PENDING_DELETION:
            raise AlreadyPendingDeletion(self._id)
        self._assert_status(UserStatus.ACTIVE, "request_deletion")

        timestamp = now or _utcnow()
        scheduled = scheduled_anonymization_at or (timestamp + self.DELETION_GRACE_PERIOD)
        if scheduled <= timestamp:
            raise InvalidStateTransition(
                entity="User",
                current_state=self._status.value,
                attempted_action="request_deletion_with_past_scheduled_anonymization",
            )

        self._status = UserStatus.PENDING_DELETION
        self._deleted_at = timestamp
        self._scheduled_anonymization_at = scheduled
        self._touch(timestamp)
        self._record_event(
            AccountDeletionRequested(
                user_id=self._id,
                scheduled_anonymization_at=scheduled,
            )
        )

    def cancel_deletion(self, now: datetime | None = None) -> None:
        """Cancel a pending deletion, returning the account to ACTIVE.

        Pre-state: ``PENDING_DELETION``, and ``now`` must be before
        ``scheduled_anonymization_at``.
        Post-state: ``ACTIVE`` with deletion metadata cleared.

        Args:
            now: Optional timestamp (for testing); defaults to UTC now.

        Raises:
            CannotCancelDeletionPastGrace: If ``now`` is on or after
                ``scheduled_anonymization_at``.
            InvalidStateTransition: If not in ``PENDING_DELETION``.
        """
        self._assert_status(UserStatus.PENDING_DELETION, "cancel_deletion")
        timestamp = now or _utcnow()
        scheduled = self._scheduled_anonymization_at
        # ``scheduled`` must have been set when entering PENDING_DELETION;
        # guard defensively against corrupt state.
        if scheduled is not None and timestamp >= scheduled:
            raise CannotCancelDeletionPastGrace(self._id, scheduled)

        self._status = UserStatus.ACTIVE
        self._deleted_at = None
        self._scheduled_anonymization_at = None
        self._touch(timestamp)
        self._record_event(AccountDeletionCancelled(user_id=self._id))

    def anonymize(self, now: datetime | None = None) -> None:
        """Irreversibly anonymize the account.

        Pre-state: ``PENDING_DELETION``.
        Post-state: ``ANONYMIZED`` (terminal). PII is scrubbed: the email
        is replaced with a placeholder, the profile display name is
        cleared, and preferences are dropped. Credentials are also
        discarded — an anonymized account cannot authenticate.

        Args:
            now: Optional timestamp (for testing); defaults to UTC now.

        Raises:
            InvalidStateTransition: If not in ``PENDING_DELETION``.
        """
        self._assert_status(UserStatus.PENDING_DELETION, "anonymize")
        timestamp = now or _utcnow()

        # Scrub PII. Use a deterministic, type-stable placeholder so that
        # downstream projections can detect anonymized accounts without
        # parsing strings.
        anonymized_email = Email(
            f"anonymized+{self._id.value}@{self._ANONYMIZED_EMAIL_DOMAIN}"
        )
        self._email = anonymized_email
        self._profile = UserProfile(
            user_id=self._id,
            display_name="Anonymized User",
            timezone="UTC",
            locale="en-US",
            avatar_url=None,
            preferences={},
        )
        self._credentials = []

        self._status = UserStatus.ANONYMIZED
        self._anonymized_at = timestamp
        self._mfa_enabled = False
        self._suspension_reason = None
        self._touch(timestamp)
        self._record_event(UserAnonymized(user_id=self._id))

    # ------------------------------------------------------------------
    # MFA
    # ------------------------------------------------------------------

    def enable_mfa(self, now: datetime | None = None) -> None:
        """Enable multi-factor authentication for the user.

        Raises:
            MFAAlreadyEnabled: If MFA is already enabled.
        """
        if self._mfa_enabled:
            raise MFAAlreadyEnabled(self._id)
        timestamp = now or _utcnow()
        self._mfa_enabled = True
        self._touch(timestamp)
        self._record_event(MFAEnabled(user_id=self._id))

    def disable_mfa(self, *, is_admin: bool = False, now: datetime | None = None) -> None:
        """Disable multi-factor authentication for the user.

        Args:
            is_admin: Must be ``True`` if the target account is an
                administrator. Passing ``True`` causes disablement to be
                refused — admins must always have MFA enabled.
            now: Optional timestamp (for testing); defaults to UTC now.

        Raises:
            CannotDisableMFAForAdmin: If ``is_admin`` is ``True``.
            MFANotEnabled: If MFA is not currently enabled.
        """
        if is_admin:
            raise CannotDisableMFAForAdmin(self._id)
        if not self._mfa_enabled:
            raise MFANotEnabled(self._id)
        timestamp = now or _utcnow()
        self._mfa_enabled = False
        self._touch(timestamp)
        self._record_event(MFADisabled(user_id=self._id))

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def update_profile(
        self,
        display_name: str | None = None,
        timezone: str | None = None,
        *,
        locale: str | None = None,
        avatar_url: str | None = None,
        preferences: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> None:
        """Update the user's profile fields.

        Only fields explicitly passed (not ``None``) are considered for
        update. A :class:`UserProfileUpdated` event is recorded iff at
        least one field actually changed.

        Args:
            display_name: New display name (1–100 chars).
            timezone: New IANA timezone string.
            locale: New BCP 47 locale tag.
            avatar_url: New avatar URL (pass empty string to clear).
            preferences: New preferences dict (replaces existing).
            now: Optional timestamp (for testing).

        Raises:
            InvalidStateTransition: If the user is anonymized (profile is
                frozen in that state).
            InvariantViolation: If any new field value fails validation.
        """
        # Anonymized accounts have a frozen, scrubbed profile.
        if self._status == UserStatus.ANONYMIZED:
            raise InvalidStateTransition(
                entity="User",
                current_state=self._status.value,
                attempted_action="update_profile",
            )

        changed = self._profile.update(
            display_name=display_name,
            timezone=timezone,
            locale=locale,
            avatar_url=avatar_url,
            preferences=preferences,
        )
        if changed:
            timestamp = now or _utcnow()
            self._touch(timestamp)
            self._record_event(
                UserProfileUpdated(user_id=self._id, changed_fields=changed)
            )

    # ------------------------------------------------------------------
    # Credentials (read-only access; helpers for the aggregate)
    # ------------------------------------------------------------------

    def get_password_credential(self) -> UserCredential | None:
        """Return the user's PASSWORD credential, if any."""
        for c in self._credentials:
            if c.is_password:
                return c
        return None

    def get_oauth_credential(self, provider: str) -> UserCredential | None:
        """Return the user's OAuth credential for ``provider``, if any."""
        for c in self._credentials:
            if c.is_oauth and c.provider == provider:
                return c
        return None

    def has_password_credential(self) -> bool:
        """True if the user has a password credential set."""
        return self.get_password_credential() is not None

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"User(id={self._id}, email={self._email.value!r}, "
            f"status={self._status.value!r}, mfa={self._mfa_enabled})"
        )


__all__ = ["User"]
