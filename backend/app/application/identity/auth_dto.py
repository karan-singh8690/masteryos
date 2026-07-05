"""Identity context — authentication DTOs.

DTOs for authentication commands and queries. These are the wire
representation — they never expose domain entities directly. Mappers
convert between DTOs and domain objects (or infrastructure services).

Each command corresponds to exactly one handler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


# ============================================================
# Registration
# ============================================================


@dataclass(frozen=True)
class RegisterUserCommand:
    """Command: Register a new user.

    The handler:
    1. Validates email + password strength.
    2. Hashes password with Argon2id.
    3. Creates User aggregate (PENDING_VERIFICATION status).
    4. Persists transactionally (user + credential + verification token).
    5. Writes UserRegistered event to outbox.
    6. Returns access + refresh token + verification_required flag.
    """

    email: str
    password: str
    display_name: str
    timezone: str = "UTC"
    locale: str = "en-US"
    ip_address: str | None = None
    user_agent: str | None = None


# ============================================================
# Login
# ============================================================


@dataclass(frozen=True)
class LoginCommand:
    """Command: Authenticate with email/password (+ MFA if enabled).

    The handler:
    1. Looks up user by email.
    2. Verifies password with Argon2id (constant-time).
    3. Upgrades hash if parameters changed (transparent).
    4. If MFA enabled: requires mfa_code or recovery_code; returns MFA_REQUIRED if missing.
    5. Creates a Session + issues access + refresh token.
    6. Writes audit log (LOGIN_SUCCESS or LOGIN_FAILURE).
    7. Publishes UserLoggedIn event.
    """

    email: str
    password: str
    mfa_code: str | None = None
    recovery_code: str | None = None
    device_fingerprint: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class LoginResult:
    """Result of LoginCommand — either full tokens or MFA challenge."""

    requires_mfa: bool = False
    mfa_session_token: str | None = None  # Short-lived token to complete MFA
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int = 0
    user: Any | None = None  # UserDTO


# ============================================================
# Refresh
# ============================================================


@dataclass(frozen=True)
class RefreshTokenCommand:
    """Command: Rotate a refresh token.

    The handler:
    1. Looks up the refresh token by hash.
    2. If not found but family has other tokens → REUSE DETECTED → revoke family.
    3. If found and valid → invalidate old, issue new (same family).
    4. Issues a new access token.
    5. Updates session last_seen_at.
    6. Writes audit log (REFRESH_ROTATED or REFRESH_REUSE_DETECTED).
    """

    refresh_token: str
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class RefreshResult:
    """Result of RefreshTokenCommand."""

    success: bool
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    error: str | None = None
    session_revoked: bool = False  # True if reuse detected


# ============================================================
# Logout
# ============================================================


@dataclass(frozen=True)
class LogoutCommand:
    """Command: Logout (revoke current session only)."""

    refresh_token: str | None = None  # Optional: identifies the session to revoke
    user_id: UUID | None = None  # From JWT
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class LogoutAllCommand:
    """Command: Logout all devices (revoke every session for the user)."""

    user_id: UUID
    ip_address: str | None = None
    user_agent: str | None = None


# ============================================================
# Email Verification
# ============================================================


@dataclass(frozen=True)
class VerifyEmailCommand:
    """Command: Verify email with a token (single-use, expiring)."""

    token: str
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class ResendVerificationCommand:
    """Command: Resend the verification email (throttled)."""

    email: str
    ip_address: str | None = None


# ============================================================
# Password Reset
# ============================================================


@dataclass(frozen=True)
class ForgotPasswordCommand:
    """Command: Request a password reset email.

    Always returns success (do not leak account existence).
    """

    email: str
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class ResetPasswordCommand:
    """Command: Reset password with a token (single-use, short TTL).

    All existing sessions for the user are revoked.
    """

    token: str
    new_password: str
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class ChangePasswordCommand:
    """Command: Change password (while authenticated).

    Requires the current password. All other sessions are revoked.
    """

    user_id: UUID
    current_password: str
    new_password: str
    ip_address: str | None = None
    user_agent: str | None = None


# ============================================================
# MFA
# ============================================================


@dataclass(frozen=True)
class SetupMfaCommand:
    """Command: Initiate MFA setup — generates secret + QR URI + recovery codes."""

    user_id: UUID


@dataclass(frozen=True)
class EnableMfaCommand:
    """Command: Enable MFA after setup — verifies the first TOTP code.

    Requires the pending secret (from SetupMfa) and a valid TOTP code.
    On success, the secret is activated and recovery codes are persisted.
    """

    user_id: UUID
    totp_code: str
    pending_secret: str  # Returned by SetupMfa, kept client-side until verification


@dataclass(frozen=True)
class DisableMfaCommand:
    """Command: Disable MFA — requires current password for verification.

    Admins cannot disable MFA (CannotDisableMFAForAdmin).
    """

    user_id: UUID
    password: str


@dataclass(frozen=True)
class VerifyMfaCommand:
    """Command: Verify a TOTP code (e.g., during login or sensitive action)."""

    user_id: UUID
    code: str
    context: str = "login"  # "login", "setup", "sensitive_action"


@dataclass(frozen=True)
class UseRecoveryCodeCommand:
    """Command: Use a recovery code to bypass MFA (one-time use)."""

    user_id: UUID
    recovery_code: str
    ip_address: str | None = None


@dataclass(frozen=True)
class MFASetupResult:
    """Result of MFA setup initiation."""

    secret: str
    qr_code_uri: str
    recovery_codes: list[str]


# ============================================================
# User Profile / Security Dashboard
# ============================================================


@dataclass(frozen=True)
class GetCurrentUserQuery:
    """Query: Get the current user's profile + roles + permissions."""

    user_id: UUID


@dataclass(frozen=True)
class UpdateProfileCommand:
    """Command: Update the current user's profile."""

    user_id: UUID
    display_name: str | None = None
    timezone: str | None = None
    locale: str | None = None
    avatar_url: str | None = None
    preferences: dict[str, Any] | None = None


@dataclass(frozen=True)
class GetSecurityDashboardQuery:
    """Query: Get the current user's security dashboard.

    Includes: active sessions, MFA enabled, password last changed,
    recent security events, recovery codes remaining.
    """

    user_id: UUID


# ============================================================
# Response DTOs
# ============================================================


@dataclass(frozen=True)
class AuthResultDTO:
    """Response: full authentication result (access + refresh + user)."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: Any | None = None  # UserDTO


@dataclass(frozen=True)
class UserDTO:
    """Read model: a user's identity."""

    id: UUID
    email: str
    status: str
    mfa_enabled: bool
    email_verified_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class UserProfileDTO:
    """Read model: a user's profile."""

    display_name: str
    timezone: str
    locale: str
    avatar_url: str | None
    preferences: dict[str, Any]


@dataclass(frozen=True)
class UserWithProfileDTO:
    """Read model: user + profile + roles."""

    user: UserDTO
    profile: UserProfileDTO
    roles: list[str]
    permissions: list[str]


@dataclass(frozen=True)
class SessionDTO:
    """Read model: an authenticated session."""

    id: UUID
    device_fingerprint: str | None
    last_ip: str | None
    user_agent: str | None
    expires_at: datetime
    last_seen_at: datetime
    created_at: datetime
    is_current: bool = False


@dataclass(frozen=True)
class SecurityDashboardDTO:
    """Read model: the user's security dashboard."""

    mfa_enabled: bool
    email_verified: bool
    password_last_changed_at: datetime | None
    active_sessions: list[SessionDTO]
    recovery_codes_remaining: int
    recent_security_events: list[dict[str, Any]]


__all__ = [
    # Registration
    "RegisterUserCommand",
    # Login
    "LoginCommand",
    "LoginResult",
    # Refresh
    "RefreshTokenCommand",
    "RefreshResult",
    # Logout
    "LogoutCommand",
    "LogoutAllCommand",
    # Email verification
    "VerifyEmailCommand",
    "ResendVerificationCommand",
    # Password reset
    "ForgotPasswordCommand",
    "ResetPasswordCommand",
    "ChangePasswordCommand",
    # MFA
    "SetupMfaCommand",
    "EnableMfaCommand",
    "DisableMfaCommand",
    "VerifyMfaCommand",
    "UseRecoveryCodeCommand",
    "MFASetupResult",
    # Profile / Dashboard
    "GetCurrentUserQuery",
    "UpdateProfileCommand",
    "GetSecurityDashboardQuery",
    # Response
    "AuthResultDTO",
    "UserDTO",
    "UserProfileDTO",
    "UserWithProfileDTO",
    "SessionDTO",
    "SecurityDashboardDTO",
]
