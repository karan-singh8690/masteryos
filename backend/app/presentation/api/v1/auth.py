"""Production authentication API routes — full vertical slice.

Implements every authentication endpoint per the OpenAPI contract (Task 006):
- POST /auth/register — Argon2id + verification token + access/refresh
- POST /auth/login — Argon2id verify + MFA + session + tokens
- POST /auth/refresh — single-use rotation + reuse detection
- POST /auth/logout — current device only
- POST /auth/logout-all — all devices
- POST /auth/verify-email — single-use verification token
- POST /auth/resend-verification — throttled
- POST /auth/forgot-password — throttled, no email existence leak
- POST /auth/reset-password — single-use, short TTL, Argon2id, revoke sessions
- POST /auth/change-password — requires current password, revoke other sessions
- POST /auth/mfa/setup — TOTP secret + QR URI + recovery codes
- POST /auth/mfa/verify — verify a TOTP code
- POST /auth/mfa/enable — finalize MFA setup (verify first code)
- POST /auth/mfa/disable — requires password, admins exempt
- POST /auth/mfa/recovery — use a recovery code

All endpoints use the production security services from Task 015:
- Argon2id (NO SHA256)
- RS256 JWT (NO HS256)
- Real verification tokens (NO fake verification)
- Real session management (NO fake sessions)
- Audit logging on every operation
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from app.application.identity.auth_service import ProductionAuthService
from app.presentation.dependencies import (
    get_auth_service,
    get_current_user_id,
    get_idempotency_key,
    get_request_ip,
    get_request_user_agent,
    get_uow,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================
# Request / Response Models (match OpenAPI contract — Task 006)
# ============================================================


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, description="Strong password (>= 12 chars)")
    display_name: str = Field(min_length=1, max_length=100)
    timezone: str = Field(default="UTC")
    locale: str = Field(default="en-US")
    invite_token: str | None = Field(default=None, description="Required when closed beta is enabled")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_code: str | None = Field(default=None, description="TOTP code (if MFA enabled)")
    recovery_code: str | None = Field(default=None, description="Recovery code (if MFA enabled)")


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=12)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12)


class MfaSetupResponse(BaseModel):
    secret: str
    qr_code_uri: str
    recovery_codes: list[str]


class MfaVerifyRequest(BaseModel):
    code: str
    context: str = Field(default="login")


class MfaEnableRequest(BaseModel):
    totp_code: str
    pending_secret: str


class MfaDisableRequest(BaseModel):
    password: str


class MfaRecoveryRequest(BaseModel):
    recovery_code: str


class UserDTO(BaseModel):
    id: UUID
    email: str
    status: str
    mfa_enabled: bool
    email_verified_at: str | None
    created_at: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int
    token_type: str = "Bearer"
    user: UserDTO | None = None
    requires_mfa: bool = False
    mfa_session_token: str | None = None


class MessageResponse(BaseModel):
    message: str
    code: str = "OK"


# ============================================================
# Helpers
# ============================================================


def _user_dto_from_dict(user: dict[str, Any]) -> UserDTO:
    """Build a UserDTO from the dict returned by auth_service."""
    return UserDTO(
        id=UUID(user["id"]),
        email=user["email"],
        status=user["status"],
        mfa_enabled=user["mfa_enabled"],
        email_verified_at=user.get("email_verified_at"),
        created_at=user.get("created_at") or "",
    )


def _build_auth_response(auth_result) -> AuthResponse:
    """Build AuthResponse from AuthenticationResult."""
    return AuthResponse(
        access_token=auth_result.access_token,
        refresh_token=auth_result.refresh_token,
        expires_in=auth_result.expires_in,
        user=_user_dto_from_dict(auth_result.user),
    )


# ============================================================
# Registration
# ============================================================


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    request: RegisterRequest,
    raw_request: Request,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> AuthResponse:
    """Register a new user account.

    Flow:
    1. Validate request
    2. Argon2id hash password
    3. Create User + UserCredential + verification token (transactional)
    4. Issue access token + refresh token
    5. Return verification_required state
    """
    ip = get_request_ip(raw_request)
    user_agent = get_request_user_agent(raw_request)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]

        # ============================================================
        # Closed Beta Registration Guard
        # ============================================================
        from app.application.beta import get_beta_service
        beta_service = get_beta_service()
        if beta_service.is_beta_enabled:
            allowed, error_msg = await beta_service.check_registration_allowed(
                session=session,
                email=request.email,
                invite_token=request.invite_token,
            )
            if not allowed:
                raise HTTPException(
                    status_code=403,
                    detail={"code": "BETA_REGISTRATION_DENIED", "message": error_msg},
                )

        try:
            user_model, verification_token, _ = await auth_service.register(
                session=session,
                email=request.email,
                password=request.password,
                display_name=request.display_name,
                ip_address=ip,
                user_agent=user_agent,
                timezone=request.timezone,
                locale=request.locale,
            )
            # Mark invite as used after successful registration
            if beta_service.is_beta_enabled and request.invite_token:
                await beta_service.mark_invite_used(session, request.invite_token)
            # Issue tokens
            auth_result = await auth_service.issue_tokens_for_user(
                session=session,
                user_id=user_model.id,
                roles=["learner"],
                device_fingerprint=None,
                ip_address=ip,
                user_agent=user_agent,
            )
            await _uow.commit()
        except ValueError as exc:
            if "EMAIL_ALREADY_REGISTERED" in str(exc):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "EMAIL_ALREADY_REGISTERED", "message": "Email already registered"},
                )
            raise HTTPException(
                status_code=422,
                detail={"code": "VALIDATION_FAILED", "message": str(exc)},
            )
        except HTTPException:
            raise
        except Exception as exc:
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail={"code": "INTERNAL_ERROR", "message": f"Registration failed: {exc}"},
            )

    # NOTE: In production, verification_token is sent via email asynchronously.
    # We do NOT return it in the response (security: don't expose the token).
    return _build_auth_response(auth_result)


# ============================================================
# Login
# ============================================================


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with email/password",
)
async def login(
    request: LoginRequest,
    raw_request: Request,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
) -> AuthResponse:
    """Login with email and password.

    If MFA is enabled, returns requires_mfa=true with a mfa_session_token.
    The client re-submits with mfa_code or recovery_code + mfa_session_token.

    Flow:
    1. Validate credentials
    2. PasswordService.verify_and_upgrade() (Argon2id)
    3. Upgrade hash if needed
    4. If MFA: require MFA code
    5. Create Session
    6. Issue JWT (RS256) + Refresh Token
    7. Audit log (LOGIN_SUCCESS or LOGIN_FAILURE)
    8. Publish UserLoggedIn
    """
    ip = get_request_ip(raw_request)
    user_agent = get_request_user_agent(raw_request)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await auth_service.login(
            session=session,
            email=request.email,
            password=request.password,
            mfa_code=request.mfa_code,
            recovery_code=request.recovery_code,
            device_fingerprint=None,
            ip_address=ip,
            user_agent=user_agent,
        )
        await _uow.commit()

    if not result.success:
        raise HTTPException(
            status_code=401,
            detail={"code": result.error_code or "INVALID_CREDENTIALS", "message": result.error or "Invalid credentials"},
        )

    if result.requires_mfa:
        return AuthResponse(
            access_token="",
            expires_in=0,
            requires_mfa=True,
            mfa_session_token=result.mfa_session_token,
        )

    return _build_auth_response(result.auth)


# ============================================================
# Refresh
# ============================================================


@router.post(
    "/refresh",
    response_model=AuthResponse,
    summary="Refresh access token (single-use rotation)",
)
async def refresh(
    request: RefreshRequest,
    raw_request: Request,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
) -> AuthResponse:
    """Rotate a refresh token.

    - Old refresh token is invalidated (single-use)
    - New refresh token is issued (same family)
    - New access token is issued
    - If an already-rotated token is presented → reuse detected → family revoked
    """
    ip = get_request_ip(raw_request)
    user_agent = get_request_user_agent(raw_request)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await auth_service.refresh(
            session=session,
            raw_refresh_token=request.refresh_token,
            ip_address=ip,
            user_agent=user_agent,
        )
        await _uow.commit()

    if not result.success:
        if result.session_revoked:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "REFRESH_REUSE_DETECTED",
                    "message": result.error or "Session revoked due to reuse detection",
                },
            )
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": result.error or "Invalid refresh token"},
        )

    return AuthResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_in=result.expires_in or 0,
    )


# ============================================================
# Logout (current device)
# ============================================================


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (current device only)",
)
async def logout(
    raw_request: Request,
    request: RefreshRequest | None = Body(default=None),
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
    user_id: UUID | None = Depends(get_current_user_id),
) -> MessageResponse:
    """Logout — revoke the current session only.

    The refresh_token in the body identifies the session to revoke.
    """
    ip = get_request_ip(raw_request)
    user_agent = get_request_user_agent(raw_request)

    refresh_token = request.refresh_token if request else None

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        await auth_service.logout(
            session=session,
            raw_refresh_token=refresh_token,
            user_id=user_id,
            ip_address=ip,
            user_agent=user_agent,
        )
        await _uow.commit()

    return MessageResponse(message="Logged out", code="OK")


# ============================================================
# Logout All (every device)
# ============================================================


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Logout all devices",
)
async def logout_all(
    raw_request: Request,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
    user_id: UUID = Depends(get_current_user_id),
) -> MessageResponse:
    """Logout all devices — revoke every session for the user."""
    ip = get_request_ip(raw_request)
    user_agent = get_request_user_agent(raw_request)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        count = await auth_service.logout_all(
            session=session,
            user_id=user_id,
            ip_address=ip,
            user_agent=user_agent,
        )
        await _uow.commit()

    return MessageResponse(message=f"Logged out from {count} devices", code="OK")


# ============================================================
# Email Verification
# ============================================================


@router.post(
    "/verify-email",
    response_model=UserDTO,
    summary="Verify email address",
)
async def verify_email(
    request: VerifyEmailRequest,
    raw_request: Request,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
) -> UserDTO:
    """Verify a user's email with a verification token.

    Tokens are single-use, expiring (24h default).
    """
    ip = get_request_ip(raw_request)
    user_agent = get_request_user_agent(raw_request)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        try:
            user_dict = await auth_service.verify_email(
                session=session,
                raw_token=request.token,
                ip_address=ip,
                user_agent=user_agent,
            )
            await _uow.commit()
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_TOKEN", "message": str(exc)},
            )

    return _user_dto_from_dict(user_dict)


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification email",
)
async def resend_verification(
    request: ResendVerificationRequest,
    raw_request: Request,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Resend the verification email (throttled).

    Always returns OK (does not leak whether the email exists).
    """
    ip = get_request_ip(raw_request)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        await auth_service.resend_verification(
            session=session,
            email=request.email,
            ip_address=ip,
        )
        await _uow.commit()

    return MessageResponse(
        message="If the email exists and is unverified, a verification email has been sent.",
        code="OK",
    )


# ============================================================
# Password Reset
# ============================================================


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset email",
)
async def forgot_password(
    request: ForgotPasswordRequest,
    raw_request: Request,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Request a password reset email.

    Always returns OK (does not leak whether the email exists).
    Throttled: max 1 request per 2 minutes per user.
    """
    ip = get_request_ip(raw_request)
    user_agent = get_request_user_agent(raw_request)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        await auth_service.forgot_password(
            session=session,
            email=request.email,
            ip_address=ip,
            user_agent=user_agent,
        )
        await _uow.commit()

    return MessageResponse(
        message="If the email exists, a password reset link has been sent.",
        code="OK",
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with a token",
)
async def reset_password(
    request: ResetPasswordRequest,
    raw_request: Request,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Reset password with a single-use, short-TTL token.

    - Argon2id hash the new password
    - Revoke all sessions + refresh tokens
    - Invalidate all other reset tokens for the user
    """
    ip = get_request_ip(raw_request)
    user_agent = get_request_user_agent(raw_request)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        try:
            await auth_service.reset_password(
                session=session,
                raw_token=request.token,
                new_password=request.new_password,
                ip_address=ip,
                user_agent=user_agent,
            )
            await _uow.commit()
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_TOKEN", "message": str(exc)},
            )

    return MessageResponse(message="Password reset successfully", code="OK")


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password (while authenticated)",
)
async def change_password(
    request: ChangePasswordRequest,
    raw_request: Request,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
    user_id: UUID = Depends(get_current_user_id),
) -> MessageResponse:
    """Change password (requires current password).

    - Verify current password (Argon2id)
    - Hash new password (Argon2id)
    - Revoke all other sessions + refresh tokens
    - Audit log
    """
    ip = get_request_ip(raw_request)
    user_agent = get_request_user_agent(raw_request)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        try:
            await auth_service.change_password(
                session=session,
                user_id=user_id,
                current_password=request.current_password,
                new_password=request.new_password,
                ip_address=ip,
                user_agent=user_agent,
            )
            await _uow.commit()
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "VALIDATION_FAILED", "message": str(exc)},
            )

    return MessageResponse(message="Password changed. Please log in again on all devices.", code="OK")


# ============================================================
# MFA
# ============================================================


@router.post(
    "/mfa/setup",
    response_model=MfaSetupResponse,
    summary="Initiate MFA setup",
)
async def mfa_setup(
    raw_request: Request,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
    user_id: UUID = Depends(get_current_user_id),
) -> MfaSetupResponse:
    """Initiate MFA setup — generates secret + QR URI + recovery codes.

    The secret is stored as 'pending' until /mfa/enable is called with a valid TOTP code.
    Recovery codes are returned ONCE — the user must save them.
    """
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        # Get user email
        from app.infrastructure.database.orm.identity import UserModel
        from sqlalchemy import select
        user_model = (await session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )).scalar_one_or_none()
        if user_model is None:
            raise HTTPException(status_code=404, detail="User not found")

        result = await auth_service.setup_mfa(
            session=session,
            user_id=user_id,
            user_email=user_model.email,
        )
        await _uow.commit()

    return MfaSetupResponse(
        secret=result["secret"],
        qr_code_uri=result["qr_code_uri"],
        recovery_codes=result["recovery_codes"],
    )


@router.post(
    "/mfa/verify",
    response_model=MessageResponse,
    summary="Verify a TOTP code",
)
async def mfa_verify(
    request: MfaVerifyRequest,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
    user_id: UUID = Depends(get_current_user_id),
) -> MessageResponse:
    """Verify a TOTP code (e.g., for sensitive actions)."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        ok = await auth_service.verify_mfa(
            session=session,
            user_id=user_id,
            code=request.code,
            context=request.context,
        )
        await _uow.commit()

    if not ok:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_MFA_CODE", "message": "Invalid or expired TOTP code"},
        )

    return MessageResponse(message="MFA code verified", code="OK")


@router.post(
    "/mfa/enable",
    response_model=MessageResponse,
    summary="Enable MFA (finalize setup)",
)
async def mfa_enable(
    request: MfaEnableRequest,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
    user_id: UUID = Depends(get_current_user_id),
) -> MessageResponse:
    """Finalize MFA setup — verify the first TOTP code and activate the secret."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        try:
            await auth_service.enable_mfa(
                session=session,
                user_id=user_id,
                totp_code=request.totp_code,
                pending_secret=request.pending_secret,
            )
            await _uow.commit()
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "MFA_ENABLE_FAILED", "message": str(exc)},
            )

    return MessageResponse(message="MFA enabled successfully", code="OK")


@router.post(
    "/mfa/disable",
    response_model=MessageResponse,
    summary="Disable MFA",
)
async def mfa_disable(
    request: MfaDisableRequest,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
    user_id: UUID = Depends(get_current_user_id),
) -> MessageResponse:
    """Disable MFA — requires current password for verification."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        try:
            await auth_service.disable_mfa(
                session=session,
                user_id=user_id,
                password=request.password,
            )
            await _uow.commit()
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "MFA_DISABLE_FAILED", "message": str(exc)},
            )

    return MessageResponse(message="MFA disabled", code="OK")


@router.post(
    "/mfa/recovery",
    response_model=MessageResponse,
    summary="Use a recovery code",
)
async def mfa_recovery(
    request: MfaRecoveryRequest,
    raw_request: Request,
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
    user_id: UUID = Depends(get_current_user_id),
) -> MessageResponse:
    """Use a recovery code (one-time use)."""
    ip = get_request_ip(raw_request)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        ok, remaining = await auth_service.use_recovery_code(
            session=session,
            user_id=user_id,
            recovery_code=request.recovery_code,
            ip_address=ip,
        )
        await _uow.commit()

    if not ok:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_RECOVERY_CODE", "message": "Invalid or already used recovery code"},
        )

    return MessageResponse(
        message=f"Recovery code used. {remaining} codes remaining.",
        code="OK",
    )


__all__ = ["router"]
