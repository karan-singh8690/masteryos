"""Identity context — DTOs for commands and queries.

DTOs are the wire representation of data. They never expose domain entities.
Mappers convert between DTOs and domain objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


# ============================================================
# Command DTOs
# ============================================================


@dataclass(frozen=True)
class RegisterUserCommand:
    """Command: Register a new user."""

    email: str
    password: str
    display_name: str
    timezone: str = "UTC"
    locale: str = "en-US"


@dataclass(frozen=True)
class VerifyEmailCommand:
    """Command: Verify a user's email address."""

    token: str


@dataclass(frozen=True)
class AuthenticateUserCommand:
    """Command: Authenticate a user with email/password."""

    email: str
    password: str
    mfa_code: str | None = None


@dataclass(frozen=True)
class RequestPasswordResetCommand:
    """Command: Request a password reset email."""

    email: str


@dataclass(frozen=True)
class ResetPasswordCommand:
    """Command: Reset password with a token."""

    token: str
    new_password: str


@dataclass(frozen=True)
class LogoutUserCommand:
    """Command: Logout (revoke current session)."""

    user_id: UUID
    session_id: UUID


@dataclass(frozen=True)
class RequestAccountDeletionCommand:
    """Command: Request account deletion (GDPR)."""

    user_id: UUID
    confirm_email: str


@dataclass(frozen=True)
class CancelAccountDeletionCommand:
    """Command: Cancel a pending account deletion."""

    user_id: UUID


@dataclass(frozen=True)
class SuspendUserCommand:
    """Command: Suspend a user (admin action)."""

    admin_user_id: UUID
    target_user_id: UUID
    reason: str


@dataclass(frozen=True)
class ReactivateUserCommand:
    """Command: Reactivate a suspended user."""

    admin_user_id: UUID
    target_user_id: UUID


@dataclass(frozen=True)
class AnonymizeUserCommand:
    """Command: Anonymize a user (system, after grace period)."""

    user_id: UUID


# ============================================================
# Response DTOs
# ============================================================


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
    """Read model: user + profile."""

    user: UserDTO
    profile: UserProfileDTO


@dataclass(frozen=True)
class AuthResultDTO:
    """Response: authentication result."""

    access_token: str
    expires_in: int
    user: UserDTO


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


# ============================================================
# Summary / List DTOs
# ============================================================


@dataclass(frozen=True)
class UserSummaryDTO:
    """Summary model: minimal user info for lists."""

    id: UUID
    email: str
    status: str
    created_at: datetime
