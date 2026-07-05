"""Identity context — authentication domain events.

These events complement the core identity events in events.py and cover
authentication-specific actions: login, logout, refresh rotation, password
change/reset, MFA setup/verify, and security incidents.

All events are immutable records of something that *happened*. They are
named in past tense and carry the data a subscriber needs to react.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.shared.ids import UserId
from app.domain.shared.kernel import DomainEvent


# ============================================================
# Authentication Events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class UserLoggedIn(DomainEvent):
    """Emitted when a user successfully authenticates.

    Fired by the LoginHandler after password verification (and MFA, if enabled).
    Subscribers may send a "new login" notification email if the IP/device
    is unrecognized.
    """

    user_id: UserId
    session_id: UUID
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True, kw_only=True)
class UserLoginFailed(DomainEvent):
    """Emitted when a login attempt fails.

    Fired by the LoginHandler on invalid credentials, suspended account,
    or unverified email. Subscribers may increment a failed-attempt counter
    and trigger lockout after a threshold.
    """

    email: str
    reason: str  # "invalid_credentials", "account_suspended", "email_not_verified"
    ip_address: str | None = None


@dataclass(frozen=True, kw_only=True)
class UserLoggedOut(DomainEvent):
    """Emitted when a user logs out (single device)."""

    user_id: UserId
    session_id: UUID


@dataclass(frozen=True, kw_only=True)
class UserLoggedOutAll(DomainEvent):
    """Emitted when a user logs out all devices.

    Every active session for the user is revoked.
    """

    user_id: UserId
    revoked_session_count: int


# ============================================================
# Refresh Token Events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class RefreshTokenRotated(DomainEvent):
    """Emitted when a refresh token is rotated.

    Fired by the RefreshTokenHandler. The old refresh token is invalidated
    and a new one issued (same token family).
    """

    user_id: UserId
    session_id: UUID
    token_family_id: UUID


@dataclass(frozen=True, kw_only=True)
class RefreshTokenReuseDetected(DomainEvent):
    """Emitted when an already-rotated refresh token is presented again.

    This is a security incident: the entire token family is revoked
    (assumed compromise). Subscribers should:
    1. Record a SECURITY_INCIDENT audit log
    2. Notify the user
    3. Optionally force password reset
    """

    user_id: UserId
    session_id: UUID
    token_family_id: UUID
    ip_address: str | None = None


# ============================================================
# Session Events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class SessionRevoked(DomainEvent):
    """Emitted when a session is revoked (logout, password change, admin action)."""

    user_id: UserId
    session_id: UUID
    reason: str  # "logout", "password_change", "admin_revoke", "reuse_detected"


@dataclass(frozen=True, kw_only=True)
class SessionExpired(DomainEvent):
    """Emitted when a session expires (absolute or idle timeout)."""

    user_id: UserId
    session_id: UUID
    reason: str  # "absolute_timeout", "idle_timeout"


# ============================================================
# Password Events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class PasswordChanged(DomainEvent):
    """Emitted when a user changes their password (while authenticated)."""

    user_id: UserId
    revoked_session_count: int = 0


@dataclass(frozen=True, kw_only=True)
class PasswordResetRequested(DomainEvent):
    """Emitted when a user requests a password reset email.

    Fired even if the email does not match an account (do not leak
    account existence). Subscribers send the reset email only if the
    account exists.
    """

    email: str
    ip_address: str | None = None


@dataclass(frozen=True, kw_only=True)
class PasswordReset(DomainEvent):
    """Emitted when a password is reset using a reset token.

    All existing sessions for the user are revoked.
    """

    user_id: UserId
    revoked_session_count: int = 0


# ============================================================
# Verification Events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class VerificationEmailRequested(DomainEvent):
    """Emitted when a verification email is (re)sent.

    Throttled: only one resend per N minutes per user.
    """

    user_id: UserId
    email: str


# ============================================================
# MFA Events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class MFASetupInitiated(DomainEvent):
    """Emitted when a user starts MFA setup (secret generated, QR code shown).

    The secret is in 'pending' state until the user verifies their first
    TOTP code (MFAEnabled event).
    """

    user_id: UserId


@dataclass(frozen=True, kw_only=True)
class MFAVerified(DomainEvent):
    """Emitted when a user provides a valid TOTP code (login or setup)."""

    user_id: UserId
    context: str  # "login", "setup", "sensitive_action"


@dataclass(frozen=True, kw_only=True)
class MFARecoveryCodeUsed(DomainEvent):
    """Emitted when a user uses a recovery code to bypass MFA."""

    user_id: UserId
    remaining_codes: int


@dataclass(frozen=True, kw_only=True)
class MFARecoveryCodesRegenerated(DomainEvent):
    """Emitted when a user regenerates their recovery codes.

    All previous unconsumed codes are invalidated.
    """

    user_id: UserId


# ============================================================
# Security Incident Events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class SecurityIncidentDetected(DomainEvent):
    """Emitted when a security incident is detected.

    Examples:
    - Refresh token reuse detected
    - Login brute force detected
    - MFA brute force detected
    - Suspicious IP activity

    Subscribers record an immutable security_incidents row and may
    trigger automated response (account lockout, IP ban, notification).
    """

    user_id: UserId | None
    incident_type: str
    severity: str  # "info", "warning", "critical"
    description: str
    metadata: dict[str, object] = field(default_factory=dict)


__all__ = [
    "UserLoggedIn",
    "UserLoginFailed",
    "UserLoggedOut",
    "UserLoggedOutAll",
    "RefreshTokenRotated",
    "RefreshTokenReuseDetected",
    "SessionRevoked",
    "SessionExpired",
    "PasswordChanged",
    "PasswordResetRequested",
    "PasswordReset",
    "VerificationEmailRequested",
    "MFASetupInitiated",
    "MFAVerified",
    "MFARecoveryCodeUsed",
    "MFARecoveryCodesRegenerated",
    "SecurityIncidentDetected",
]
