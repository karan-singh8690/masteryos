"""Tests for the Identity context command handlers."""

from __future__ import annotations

import pytest
from uuid import uuid4

from app.application.identity.dto import (
    RegisterUserCommand,
    VerifyEmailCommand,
    RequestAccountDeletionCommand,
    CancelAccountDeletionCommand,
    SuspendUserCommand,
)
from app.application.identity.handlers import (
    RegisterUserHandler,
    VerifyEmailHandler,
    RequestAccountDeletionHandler,
    CancelAccountDeletionHandler,
    SuspendUserHandler,
)
from app.domain.identity.events import (
    AccountDeletionCancelled,
    AccountDeletionRequested,
    EmailVerified,
    UserRegistered,
    UserSuspended,
)
from tests.application.fakes import FakeUnitOfWork, FakeEventPublisher


class TestRegisterUserHandler:
    """Tests for RegisterUserHandler."""

    @pytest.fixture
    def setup(self) -> tuple[RegisterUserHandler, FakeUnitOfWork, FakeEventPublisher]:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()
        handler = RegisterUserHandler(uow, publisher)
        return handler, uow, publisher

    @pytest.mark.asyncio
    async def test_register_user_success(self, setup: tuple) -> None:
        handler, uow, publisher = setup
        command = RegisterUserCommand(
            email="alex@example.com",
            password="SecurePass123!",
            display_name="Alex Chen",
        )

        result = await handler.handle(command)

        assert result.success
        assert result.value is not None
        assert result.value.email == "alex@example.com"
        assert result.value.status == "pending_verification"
        assert any(isinstance(e, UserRegistered) for e in publisher.published_events)

    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self, setup: tuple) -> None:
        handler, _, _ = setup
        command = RegisterUserCommand(
            email="not-an-email",
            password="SecurePass123!",
            display_name="Alex",
        )

        result = await handler.handle(command)

        assert not result.success
        assert result.error_code == "VALIDATION_FAILED"

    @pytest.mark.asyncio
    async def test_register_user_weak_password(self, setup: tuple) -> None:
        handler, _, _ = setup
        command = RegisterUserCommand(
            email="alex@example.com",
            password="short",
            display_name="Alex",
        )

        result = await handler.handle(command)

        assert not result.success
        assert result.error_code == "VALIDATION_FAILED"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, setup: tuple) -> None:
        handler, uow, _ = setup
        command = RegisterUserCommand(
            email="alex@example.com",
            password="SecurePass123!",
            display_name="Alex",
        )

        # First registration
        await handler.handle(command)

        # Second registration with same email
        result = await handler.handle(command)

        assert not result.success
        assert result.error_code == "EMAIL_ALREADY_REGISTERED"


class TestVerifyEmailHandler:
    """Tests for VerifyEmailHandler."""

    @pytest.mark.asyncio
    async def test_verify_email_success(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        # Register a user first
        reg_handler = RegisterUserHandler(uow, publisher)
        reg_result = await reg_handler.handle(
            RegisterUserCommand(
                email="alex@example.com",
                password="SecurePass123!",
                display_name="Alex",
            )
        )
        user_id = reg_result.value.id
        publisher.reset()

        # Verify email
        verify_handler = VerifyEmailHandler(uow, publisher)
        result = await verify_handler.handle(VerifyEmailCommand(token=str(user_id)))

        assert result.success
        assert result.value.status == "active"
        assert any(isinstance(e, EmailVerified) for e in publisher.published_events)


class TestAccountDeletionHandler:
    """Tests for the GDPR deletion flow."""

    @pytest.mark.asyncio
    async def test_request_and_cancel_deletion(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        # Register and verify
        reg_handler = RegisterUserHandler(uow, publisher)
        reg_result = await reg_handler.handle(
            RegisterUserCommand(
                email="alex@example.com",
                password="SecurePass123!",
                display_name="Alex",
            )
        )
        user_id = reg_result.value.id

        verify_handler = VerifyEmailHandler(uow, publisher)
        await verify_handler.handle(VerifyEmailCommand(token=str(user_id)))
        publisher.reset()

        # Request deletion
        del_handler = RequestAccountDeletionHandler(uow, publisher)
        result = await del_handler.handle(
            RequestAccountDeletionCommand(user_id=user_id, confirm_email="alex@example.com")
        )

        assert result.success
        assert result.value.status == "pending_deletion"
        assert any(isinstance(e, AccountDeletionRequested) for e in publisher.published_events)

        # Cancel deletion
        publisher.reset()
        cancel_handler = CancelAccountDeletionHandler(uow, publisher)
        result = await cancel_handler.handle(CancelAccountDeletionCommand(user_id=user_id))

        assert result.success
        assert result.value.status == "active"
        assert any(isinstance(e, AccountDeletionCancelled) for e in publisher.published_events)

    @pytest.mark.asyncio
    async def test_request_deletion_email_mismatch(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        reg_handler = RegisterUserHandler(uow, publisher)
        reg_result = await reg_handler.handle(
            RegisterUserCommand(
                email="alex@example.com",
                password="SecurePass123!",
                display_name="Alex",
            )
        )
        user_id = reg_result.value.id

        del_handler = RequestAccountDeletionHandler(uow, publisher)
        result = await del_handler.handle(
            RequestAccountDeletionCommand(user_id=user_id, confirm_email="wrong@example.com")
        )

        assert not result.success
        assert result.error_code == "EMAIL_MISMATCH"


class TestSuspendUserHandler:
    """Tests for SuspendUserHandler."""

    @pytest.mark.asyncio
    async def test_suspend_user(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        reg_handler = RegisterUserHandler(uow, publisher)
        reg_result = await reg_handler.handle(
            RegisterUserCommand(
                email="alex@example.com",
                password="SecurePass123!",
                display_name="Alex",
            )
        )
        user_id = reg_result.value.id

        verify_handler = VerifyEmailHandler(uow, publisher)
        await verify_handler.handle(VerifyEmailCommand(token=str(user_id)))
        publisher.reset()

        suspend_handler = SuspendUserHandler(uow, publisher)
        result = await suspend_handler.handle(
            SuspendUserCommand(
                admin_user_id=uuid4(),
                target_user_id=user_id,
                reason="abuse",
            )
        )

        assert result.success
        assert result.value.status == "suspended"
        assert any(isinstance(e, UserSuspended) for e in publisher.published_events)
