"""Authentication API routes — register, verify email, login.

Maps to the OpenAPI contract (Task 006):
- POST /auth/register
- POST /auth/verify-email
- POST /auth/login (simplified for this slice)
"""

from __future__ import annotations

from uuid import UUID

import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, EmailStr, Field

from app.application.identity.dto import (
    RegisterUserCommand,
    VerifyEmailCommand,
)
from app.application.identity.handlers import (
    RegisterUserHandler,
    VerifyEmailHandler,
)
from app.application.shared import CommandResult, EventPublisher, UnitOfWork
from app.domain.identity.user import User
from app.domain.shared.kernel import UserStatus
from app.presentation.dependencies import (
    OutboxEventPublisher,
    create_access_token,
    get_event_publisher,
    get_idempotency_key,
    get_uow,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================
# Request/Response Models (match OpenAPI contract)
# ============================================================


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, description="Strong password")
    display_name: str = Field(min_length=1, max_length=100)
    timezone: str = Field(default="UTC")
    locale: str = Field(default="en-US")


class AuthResponse(BaseModel):
    access_token: str
    expires_in: int
    user: "UserDTO"


class UserDTO(BaseModel):
    id: UUID
    email: str
    status: str
    mfa_enabled: bool
    email_verified_at: str | None
    created_at: str


class VerifyEmailRequest(BaseModel):
    token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ============================================================
# Endpoints
# ============================================================


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    request: RegisterRequest,
    uow: UnitOfWork = Depends(get_uow),
    publisher: OutboxEventPublisher = Depends(get_event_publisher),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> AuthResponse:
    """Register a new user account."""
    handler = RegisterUserHandler(uow, publisher)

    command = RegisterUserCommand(
        email=request.email,
        password=request.password,
        display_name=request.display_name,
        timezone=request.timezone,
        locale=request.locale,
    )

    result = await handler.handle(command)

    if not result.success:
        # Map error codes to HTTP status
        if result.error_code == "EMAIL_ALREADY_REGISTERED":
            raise HTTPException(status_code=409, detail={
                "code": result.error_code,
                "message": result.error,
            })
        raise HTTPException(status_code=422, detail={
            "code": result.error_code or "VALIDATION_FAILED",
            "message": result.error,
        })

    # Flush events to outbox before commit
    async with uow as _uow:
        await publisher.flush_to_outbox(_uow._session)  # type: ignore[union-attr]
        await _uow.commit()

    # Issue access token
    user = result.value
    token = create_access_token(user.id, roles=["learner"])

    return AuthResponse(
        access_token=token,
        expires_in=900,
        user=UserDTO(
            id=user.id,
            email=user.email,
            status=user.status,
            mfa_enabled=user.mfa_enabled,
            email_verified_at=user.email_verified_at.isoformat() if user.email_verified_at else None,
            created_at=user.created_at.isoformat(),
        ),
    )


@router.post(
    "/verify-email",
    response_model=UserDTO,
    summary="Verify email address",
)
async def verify_email(
    request: VerifyEmailRequest,
    uow: UnitOfWork = Depends(get_uow),
    publisher: OutboxEventPublisher = Depends(get_event_publisher),
) -> UserDTO:
    """Verify a user's email address."""
    handler = VerifyEmailHandler(uow, publisher)

    command = VerifyEmailCommand(token=request.token)
    result = await handler.handle(command)

    if not result.success:
        if result.error_code == "USER_NOT_FOUND":
            raise HTTPException(status_code=404, detail={
                "code": result.error_code,
                "message": result.error,
            })
        raise HTTPException(status_code=422, detail={
            "code": result.error_code or "VALIDATION_FAILED",
            "message": result.error,
        })

    async with uow as _uow:
        await publisher.flush_to_outbox(_uow._session)  # type: ignore[union-attr]
        await _uow.commit()

    user = result.value
    return UserDTO(
        id=user.id,
        email=user.email,
        status=user.status,
        mfa_enabled=user.mfa_enabled,
        email_verified_at=user.email_verified_at.isoformat() if user.email_verified_at else None,
        created_at=user.created_at.isoformat(),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with email/password",
)
async def login(
    request: LoginRequest,
    uow: UnitOfWork = Depends(get_uow),
) -> AuthResponse:
    """Login with email and password.

    For this vertical slice, login is simplified:
    1. Look up user by email.
    2. Verify password hash.
    3. Issue access token.

    MFA, OAuth, and refresh tokens will be added in a later slice.
    """
    from app.domain.shared.value_objects import Email
    from app.infrastructure.database.orm.identity import UserModel, UserCredentialModel
    from sqlalchemy import select

    async with uow as _uow:
        # Look up user by email
        email_vo = Email(request.email)
        stmt = select(UserModel).where(
            UserModel.email == email_vo.value,
            UserModel.deleted_at.is_(None),
        )
        result = await _uow._session.execute(stmt)  # type: ignore[union-attr]
        user_model = result.scalar_one_or_none()

        if user_model is None:
            raise HTTPException(status_code=401, detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid email or password",
            })

        # Check user status
        if user_model.status == UserStatus.SUSPENDED.value:
            raise HTTPException(status_code=403, detail={
                "code": "ACCOUNT_SUSPENDED",
                "message": "Account is suspended",
            })
        if user_model.status == UserStatus.PENDING_DELETION.value:
            raise HTTPException(status_code=403, detail={
                "code": "ACCOUNT_PENDING_DELETION",
                "message": "Account is pending deletion",
            })

        # Verify password (simplified — in production, use passlib/argon2)
        cred_stmt = select(UserCredentialModel).where(
            UserCredentialModel.user_id == user_model.id,
            UserCredentialModel.credential_type == "password",
        )
        cred_result = await _uow._session.execute(cred_stmt)  # type: ignore[union-attr]
        cred_model = cred_result.scalar_one_or_none()

        if cred_model is None or cred_model.password_hash is None:
            raise HTTPException(status_code=401, detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid email or password",
            })

        # Verify password hash (simplified)
        parts = cred_model.password_hash.split("$")
        if len(parts) == 3:
            salt, stored_hash = parts[1], parts[2]
            computed_hash = hashlib.sha256(f"{salt}{request.password}".encode()).hexdigest()
            if computed_hash != stored_hash:
                raise HTTPException(status_code=401, detail={
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                })
        else:
            raise HTTPException(status_code=401, detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid email or password",
            })

        # Issue token
        token = create_access_token(user_model.id, roles=["learner"])

        return AuthResponse(
            access_token=token,
            expires_in=900,
            user=UserDTO(
                id=user_model.id,
                email=user_model.email,
                status=user_model.status,
                mfa_enabled=user_model.mfa_enabled,
                email_verified_at=user_model.email_verified_at.isoformat() if user_model.email_verified_at else None,
                created_at=user_model.created_at.isoformat(),
            ),
        )


# Forward reference resolution
AuthResponse.model_rebuild()
