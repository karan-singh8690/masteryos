"""Identity context — command handlers.

Each handler:
1. Validates the command (application-level).
2. Loads aggregates via UoW repositories.
3. Calls domain behavior.
4. Persists via UoW.
5. Collects and publishes events.
6. Returns a CommandResult with a DTO.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.infrastructure.security import PasswordService

from app.application.shared import (
    ApplicationConflict,
    AuthorizationDenied,
    CommandHandler,
    CommandResult,
    EventPublisher,
    ResourceMissing,
    UnitOfWork,
    ValidationFailed,
)
from app.application.identity.dto import (
    CancelAccountDeletionCommand,
    RequestAccountDeletionCommand,
    RequestPasswordResetCommand,
    ResetPasswordCommand,
    SuspendUserCommand,
    ReactivateUserCommand,
    AnonymizeUserCommand,
    RegisterUserCommand,
    UserDTO,
    VerifyEmailCommand,
)
from app.application.identity.mappers import UserMapper
from app.domain.identity.exceptions import (
    CannotSuspendAdmin,
    EmailAlreadyRegistered,
)
from app.domain.identity.user import User
from app.domain.shared.kernel import InvalidStateTransition
from app.domain.shared.value_objects import Email


class RegisterUserHandler(CommandHandler[RegisterUserCommand, UserDTO]):
    """Handler for RegisterUserCommand.

    Uses the production Argon2id PasswordService from Task 015.
    NO SHA256, NO simplified hashing.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        event_publisher: EventPublisher,
        password_service: PasswordService | None = None,
    ) -> None:
        self._uow = uow
        self._event_publisher = event_publisher
        # Use lower cost for tests; production uses OWASP defaults via get_password_service()
        self._password_service = password_service or PasswordService(
            memory_cost=1024, time_cost=1, parallelism=1
        )

    async def handle(self, command: RegisterUserCommand) -> CommandResult[UserDTO]:
        # 1. Application-level validation
        errors: dict[str, str] = {}
        if not command.email or "@" not in command.email:
            errors["email"] = "Invalid email format"
        if not command.password or len(command.password) < 12:
            errors["password"] = "Password must be at least 12 characters"
        if not command.display_name or len(command.display_name) > 100:
            errors["display_name"] = "Display name must be 1-100 characters"
        if errors:
            return CommandResult.fail(str(ValidationFailed(errors)), "VALIDATION_FAILED")

        # 2. Check for existing user
        try:
            email_vo = Email(command.email)
        except Exception as exc:
            return CommandResult.fail(str(exc), "INVALID_EMAIL")

        async with self._uow as uow:
            existing = await uow.users.get_by_email(email_vo)
            if existing is not None:
                return CommandResult.fail(
                    str(EmailAlreadyRegistered(command.email)),
                    "EMAIL_ALREADY_REGISTERED",
                )

            # 3. Create domain aggregate
            password_hash = self._hash_password(command.password)
            user = User.register(
                email=email_vo,
                password_hash=password_hash,
                display_name=command.display_name,
            )

            # 4. Persist
            await uow.users.add(user)
            events = user.collect_events()
            await uow.commit()

        # 5. Publish events
        await self._event_publisher.publish_many(events)

        # 6. Return DTO
        return CommandResult.ok(UserMapper.to_dto(user), events)

    def _hash_password(self, password: str) -> str:
        """Hash a password with Argon2id (production)."""
        return self._password_service.hash_password(password)


class VerifyEmailHandler(CommandHandler[VerifyEmailCommand, UserDTO]):
    """Handler for VerifyEmailCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: VerifyEmailCommand) -> CommandResult[UserDTO]:
        async with self._uow as uow:
            # In a real implementation, the token maps to a user_id
            # For this scaffold, we assume the token IS the user_id
            try:
                user_id = UUID(command.token)
            except ValueError:
                return CommandResult.fail("Invalid verification token", "INVALID_TOKEN")

            user = await uow.users.get_by_id(user_id)
            if user is None:
                return CommandResult.fail(
                    str(ResourceMissing("User", user_id)),
                    "USER_NOT_FOUND",
                )

            try:
                user.verify_email()
            except InvalidStateTransition:
                pass  # Idempotent: already verified

            await uow.users.save(user)
            events = user.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(UserMapper.to_dto(user), events)


class RequestAccountDeletionHandler(CommandHandler[RequestAccountDeletionCommand, UserDTO]):
    """Handler for RequestAccountDeletionCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: RequestAccountDeletionCommand) -> CommandResult[UserDTO]:
        async with self._uow as uow:
            user = await uow.users.get_by_id(command.user_id)
            if user is None:
                return CommandResult.fail(
                    str(ResourceMissing("User", command.user_id)),
                    "USER_NOT_FOUND",
                )

            # Verify confirmation email matches
            if user.email.value != command.confirm_email.lower():
                return CommandResult.fail("Email confirmation does not match", "EMAIL_MISMATCH")

            try:
                user.request_deletion()
            except InvalidStateTransition as exc:
                return CommandResult.fail(str(exc), "INVALID_STATE_TRANSITION")

            await uow.users.save(user)
            events = user.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(UserMapper.to_dto(user), events)


class CancelAccountDeletionHandler(CommandHandler[CancelAccountDeletionCommand, UserDTO]):
    """Handler for CancelAccountDeletionCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: CancelAccountDeletionCommand) -> CommandResult[UserDTO]:
        async with self._uow as uow:
            user = await uow.users.get_by_id(command.user_id)
            if user is None:
                return CommandResult.fail(
                    str(ResourceMissing("User", command.user_id)),
                    "USER_NOT_FOUND",
                )

            try:
                user.cancel_deletion()
            except InvalidStateTransition as exc:
                return CommandResult.fail(str(exc), "INVALID_STATE_TRANSITION")

            await uow.users.save(user)
            events = user.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(UserMapper.to_dto(user), events)


class SuspendUserHandler(CommandHandler[SuspendUserCommand, UserDTO]):
    """Handler for SuspendUserCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: SuspendUserCommand) -> CommandResult[UserDTO]:
        async with self._uow as uow:
            user = await uow.users.get_by_id(command.target_user_id)
            if user is None:
                return CommandResult.fail(
                    str(ResourceMissing("User", command.target_user_id)),
                    "USER_NOT_FOUND",
                )

            try:
                user.suspend(command.reason, is_admin=False)
            except CannotSuspendAdmin as exc:
                return CommandResult.fail(str(exc), "CANNOT_SUSPEND_ADMIN")
            except InvalidStateTransition as exc:
                return CommandResult.fail(str(exc), "INVALID_STATE_TRANSITION")

            await uow.users.save(user)
            events = user.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(UserMapper.to_dto(user), events)


class ReactivateUserHandler(CommandHandler[ReactivateUserCommand, UserDTO]):
    """Handler for ReactivateUserCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: ReactivateUserCommand) -> CommandResult[UserDTO]:
        async with self._uow as uow:
            user = await uow.users.get_by_id(command.target_user_id)
            if user is None:
                return CommandResult.fail(
                    str(ResourceMissing("User", command.target_user_id)),
                    "USER_NOT_FOUND",
                )

            try:
                user.reactivate()
            except InvalidStateTransition as exc:
                return CommandResult.fail(str(exc), "INVALID_STATE_TRANSITION")

            await uow.users.save(user)
            events = user.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(UserMapper.to_dto(user), events)


class AnonymizeUserHandler(CommandHandler[AnonymizeUserCommand, UserDTO]):
    """Handler for AnonymizeUserCommand (system, after grace period)."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: AnonymizeUserCommand) -> CommandResult[UserDTO]:
        async with self._uow as uow:
            user = await uow.users.get_by_id(command.user_id)
            if user is None:
                return CommandResult.fail(
                    str(ResourceMissing("User", command.user_id)),
                    "USER_NOT_FOUND",
                )

            try:
                user.anonymize()
            except InvalidStateTransition as exc:
                return CommandResult.fail(str(exc), "INVALID_STATE_TRANSITION")

            await uow.users.save(user)
            events = user.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(UserMapper.to_dto(user), events)
