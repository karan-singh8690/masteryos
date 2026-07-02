"""Tests for the User aggregate (Identity context)."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from app.domain.identity.user import User
from app.domain.identity.events import (
    AccountDeletionCancelled,
    AccountDeletionRequested,
    EmailVerified,
    MFADisabled,
    MFAEnabled,
    UserAnonymized,
    UserProfileUpdated,
    UserRegistered,
    UserReactivated,
    UserSuspended,
)
from app.domain.identity.exceptions import (
    CannotSuspendAdmin,
    EmailNotVerified,
)
from app.domain.shared.ids import UserId
from app.domain.shared.kernel import (
    InvalidStateTransition,
    UserStatus,
)
from app.domain.shared.value_objects import Email


class TestUserRegistration:
    """Tests for User.register() factory."""

    def test_register_creates_user_with_pending_verification(self) -> None:
        user = User.register(
            email=Email("alex@example.com"),
            password_hash="argon2id$hashed",
            display_name="Alex Chen",
        )
        assert user.status == UserStatus.PENDING_VERIFICATION
        assert user.email.value == "alex@example.com"
        assert user.email_verified_at is None

    def test_register_records_user_registered_event(self) -> None:
        user = User.register(
            email=Email("alex@example.com"),
            password_hash="hashed",
            display_name="Alex",
        )
        events = user.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], UserRegistered)
        assert events[0].email == "alex@example.com"

    def test_register_assigns_user_id(self) -> None:
        user = User.register(
            email=Email("alex@example.com"),
            password_hash="hashed",
            display_name="Alex",
        )
        assert isinstance(user.id, UserId)
        assert user.id.value is not None


class TestUserEmailVerification:
    """Tests for verify_email()."""

    def test_verify_email_transitions_to_active(self) -> None:
        user = User.register(
            email=Email("alex@example.com"),
            password_hash="hashed",
            display_name="Alex",
        )
        user.collect_events()  # clear registration event

        user.verify_email()

        assert user.status == UserStatus.ACTIVE
        assert user.email_verified_at is not None

    def test_verify_email_records_event(self) -> None:
        user = User.register(
            email=Email("alex@example.com"),
            password_hash="hashed",
            display_name="Alex",
        )
        user.collect_events()

        user.verify_email()

        events = user.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], EmailVerified)

    def test_verify_email_on_active_user_is_idempotent(self) -> None:
        """Re-verifying an already-verified email should not fail."""
        user = User.register(
            email=Email("alex@example.com"),
            password_hash="hashed",
            display_name="Alex",
        )
        user.verify_email()
        user.collect_events()

        # Second verification should not raise
        user.verify_email()
        assert user.status == UserStatus.ACTIVE


class TestUserSuspension:
    """Tests for suspend() and reactivate()."""

    def test_suspend_active_user(self) -> None:
        user = self._make_active_user()
        user.collect_events()

        user.suspend(reason="abuse")

        assert user.status == UserStatus.SUSPENDED
        events = user.collect_events()
        assert any(isinstance(e, UserSuspended) for e in events)

    def test_suspend_admin_user_raises(self) -> None:
        user = self._make_active_user(is_admin=True)
        with pytest.raises(CannotSuspendAdmin):
            user.suspend(reason="test")

    def test_suspend_already_suspended_is_idempotent(self) -> None:
        user = self._make_active_user()
        user.suspend(reason="abuse")
        user.collect_events()

        # Second suspension should not raise
        user.suspend(reason="still suspended")
        assert user.status == UserStatus.SUSPENDED

    def test_reactivate_suspended_user(self) -> None:
        user = self._make_active_user()
        user.suspend(reason="abuse")
        user.collect_events()

        user.reactivate()

        assert user.status == UserStatus.ACTIVE
        events = user.collect_events()
        assert any(isinstance(e, UserReactivated) for e in events)

    def test_reactivate_active_user_raises(self) -> None:
        user = self._make_active_user()
        with pytest.raises(InvalidStateTransition):
            user.reactivate()

    @staticmethod
    def _make_active_user(is_admin: bool = False) -> User:
        user = User.register(
            email=Email("alex@example.com"),
            password_hash="hashed",
            display_name="Alex",
            is_admin=is_admin,
        )
        user.verify_email()
        return user


class TestUserAccountDeletion:
    """Tests for the GDPR deletion flow."""

    def test_request_deletion_transitions_to_pending_deletion(self) -> None:
        user = self._make_active_user()
        user.collect_events()

        user.request_deletion()

        assert user.status == UserStatus.PENDING_DELETION
        events = user.collect_events()
        assert any(isinstance(e, AccountDeletionRequested) for e in events)

    def test_cancel_deletion_within_grace(self) -> None:
        user = self._make_active_user()
        user.request_deletion()
        user.collect_events()

        user.cancel_deletion()

        assert user.status == UserStatus.ACTIVE
        events = user.collect_events()
        assert any(isinstance(e, AccountDeletionCancelled) for e in events)

    def test_anonymize_after_grace_period(self) -> None:
        user = self._make_active_user()
        user.request_deletion()
        # Simulate grace period elapsed by setting the timestamp in the past
        user._deletion_requested_at = datetime.now(timezone.utc) - timedelta(days=15)
        user.collect_events()

        user.anonymize()

        assert user.status == UserStatus.ANONYMIZED
        events = user.collect_events()
        assert any(isinstance(e, UserAnonymized) for e in events)

    def test_anonymize_before_grace_raises(self) -> None:
        user = self._make_active_user()
        user.request_deletion()
        # Grace period not elapsed
        with pytest.raises(InvalidStateTransition):
            user.anonymize()

    def test_anonymize_without_requesting_deletion_raises(self) -> None:
        user = self._make_active_user()
        with pytest.raises(InvalidStateTransition):
            user.anonymize()

    @staticmethod
    def _make_active_user() -> User:
        user = User.register(
            email=Email("alex@example.com"),
            password_hash="hashed",
            display_name="Alex",
        )
        user.verify_email()
        return user


class TestUserMFA:
    """Tests for MFA enable/disable."""

    def test_enable_mfa(self) -> None:
        user = self._make_active_user()
        user.collect_events()

        user.enable_mfa(secret_encrypted=b"encrypted_secret")

        assert user.mfa_enabled is True
        events = user.collect_events()
        assert any(isinstance(e, MFAEnabled) for e in events)

    def test_disable_mfa(self) -> None:
        user = self._make_active_user()
        user.enable_mfa(secret_encrypted=b"secret")
        user.collect_events()

        user.disable_mfa()

        assert user.mfa_enabled is False
        events = user.collect_events()
        assert any(isinstance(e, MFADisabled) for e in events)

    def test_disable_mfa_for_admin_raises(self) -> None:
        user = User.register(
            email=Email("admin@example.com"),
            password_hash="hashed",
            display_name="Admin",
            is_admin=True,
        )
        user.verify_email()
        user.enable_mfa(secret_encrypted=b"secret")

        with pytest.raises(InvalidStateTransition, match="admin"):
            user.disable_mfa()

    @staticmethod
    def _make_active_user() -> User:
        user = User.register(
            email=Email("alex@example.com"),
            password_hash="hashed",
            display_name="Alex",
        )
        user.verify_email()
        return user


class TestUserEventCollection:
    """Tests for aggregate event collection."""

    def test_collect_events_returns_and_clears(self) -> None:
        user = User.register(
            email=Email("alex@example.com"),
            password_hash="hashed",
            display_name="Alex",
        )
        user.verify_email()

        events = user.collect_events()
        assert len(events) == 2  # UserRegistered + EmailVerified

        # Second call returns empty (cleared)
        assert user.collect_events() == []

    def test_clear_events(self) -> None:
        user = User.register(
            email=Email("alex@example.com"),
            password_hash="hashed",
            display_name="Alex",
        )
        user.clear_events()
        assert user.collect_events() == []
