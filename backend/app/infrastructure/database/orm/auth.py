"""ORM models for authentication security tables.

Maps to the `identity` PostgreSQL schema.
Tables:
- verification_tokens (email verification tokens)
- password_reset_tokens (password reset tokens)
- refresh_tokens (rotating refresh tokens with family tracking)
- mfa_secrets (TOTP secrets, encrypted)
- mfa_recovery_codes (one-time recovery codes)
- security_incidents (security event log)
- auth_audit_logs (immutable audit trail)

These tables complement the existing `users`, `user_profiles`,
`user_credentials`, and `sessions` tables.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index

from app.infrastructure.database.orm.base import Base, TimestampMixin


# ============================================================
# Email Verification Tokens
# ============================================================


class VerificationTokenModel(Base, TimestampMixin):
    """ORM model for identity.verification_tokens.

    Single-use, expiring tokens used to verify email ownership on registration.
    Tokens are stored as SHA-256 hashes (the raw token is never persisted).
    """

    __tablename__ = "verification_tokens"
    __table_args__ = (
        CheckConstraint(
            "token_type IN ('email_verification', 'email_change')",
            name="chk_verification_tokens_type",
        ),
        CheckConstraint("expires_at IS NOT NULL", name="chk_verification_tokens_expires"),
        Index(
            "idx_verification_tokens_user_active",
            "user_id",
            postgresql_where=text("consumed_at IS NULL"),
        ),
        Index(
            "idx_verification_tokens_hash",
            "token_hash",
            unique=True,
        ),
        {"schema": "identity"},
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    token_type: Mapped[str] = mapped_column(String(50), nullable=False, default="email_verification")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)


# ============================================================
# Password Reset Tokens
# ============================================================


class PasswordResetTokenModel(Base, TimestampMixin):
    """ORM model for identity.password_reset_tokens.

    Single-use, short-TTL tokens for password reset flows.
    TTL: 15 minutes (configurable via settings).
    """

    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        CheckConstraint("expires_at IS NOT NULL", name="chk_password_reset_tokens_expires"),
        Index(
            "idx_password_reset_tokens_user_active",
            "user_id",
            postgresql_where=text("consumed_at IS NULL"),
        ),
        Index(
            "idx_password_reset_tokens_hash",
            "token_hash",
            unique=True,
        ),
        {"schema": "identity"},
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)


# ============================================================
# Refresh Tokens (rotation tracking, with token family)
# ============================================================


class RefreshTokenModel(Base, TimestampMixin):
    """ORM model for identity.refresh_tokens.

    Tracks every refresh token issued. Used for:
    - Single-use enforcement (consumed_at is set on rotation)
    - Reuse detection (a token presented again after rotation triggers family revocation)
    - Audit trail (every refresh token lifecycle is recorded)

    A token_family_id groups tokens issued from the same login. If any
    already-rotated token in a family is presented again, the entire family
    is revoked (assumed compromise).
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        CheckConstraint(
            "(revoked_at IS NULL) OR (revoke_reason IS NOT NULL)",
            name="chk_refresh_tokens_revoke_reason",
        ),
        Index("idx_refresh_tokens_hash", "token_hash", unique=True),
        Index("idx_refresh_tokens_family", "token_family_id"),
        Index(
            "idx_refresh_tokens_user_active",
            "user_id",
            postgresql_where=text("revoked_at IS NULL AND consumed_at IS NULL"),
        ),
        {"schema": "identity"},
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    token_family_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rotated_to_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)


# ============================================================
# MFA Secrets (TOTP)
# ============================================================


class MfaSecretModel(Base):
    """ORM model for identity.mfa_secrets.

    Stores the TOTP secret for a user. The secret is stored encrypted
    (application-layer encryption; not raw). A user has at most one
    active secret — but pending secrets (during setup, before verification)
    are stored alongside the active secret.

    Lifecycle:
    1. setup_mfa: insert row with status=pending
    2. enable_mfa (after first TOTP verification): status=active
    3. disable_mfa: row deleted (or status=revoked)
    """

    __tablename__ = "mfa_secrets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'active', 'revoked')",
            name="chk_mfa_secrets_status",
        ),
        Index(
            "idx_mfa_secrets_user_active",
            "user_id",
            "status",
            postgresql_where=text("status = 'active'"),
        ),
        {"schema": "identity"},
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    secret_encrypted: Mapped[bytes] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ============================================================
# MFA Recovery Codes
# ============================================================


class MfaRecoveryCodeModel(Base, TimestampMixin):
    """ORM model for identity.mfa_recovery_codes.

    One-time-use recovery codes for bypassing MFA when the user loses
    their TOTP device. Stored as SHA-256 hashes (the raw code is never
    persisted). A user has up to 10 active recovery codes.

    Lifecycle:
    1. setup_mfa: 10 codes generated, stored as hashes
    2. use_recovery_code: row marked consumed_at (single-use)
    3. regenerate: all unconsumed codes deleted, 10 new ones generated
    """

    __tablename__ = "mfa_recovery_codes"
    __table_args__ = (
        Index(
            "idx_mfa_recovery_codes_user_active",
            "user_id",
            postgresql_where=text("consumed_at IS NULL"),
        ),
        Index("idx_mfa_recovery_codes_hash", "code_hash", unique=True),
        {"schema": "identity"},
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_ip: Mapped[str | None] = mapped_column(INET, nullable=True)


# ============================================================
# Security Incidents
# ============================================================


class SecurityIncidentModel(Base, TimestampMixin):
    """ORM model for identity.security_incidents.

    Records security-relevant events that may require investigation:
    - Refresh token reuse detected
    - Multiple failed login attempts
    - MFA brute force attempt
    - Suspicious IP activity
    - Account takeover attempt

    These are immutable (append-only) and used by the security team for
    forensics and automated response.
    """

    __tablename__ = "security_incidents"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="chk_security_incidents_severity",
        ),
        CheckConstraint(
            "incident_type IN ("
            "'refresh_token_reuse', 'login_brute_force', 'mfa_brute_force', "
            "'suspicious_ip', 'account_takeover_attempt', 'password_spray', "
            "'session_hijack_attempt', 'rate_limit_violation', 'other')",
            name="chk_security_incidents_type",
        ),
        Index("idx_security_incidents_user", "user_id"),
        Index("idx_security_incidents_type_created", "incident_type", "created_at"),
        Index("idx_security_incidents_unresolved", "resolved_at"),
        {"schema": "identity"},
    )

    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    incident_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ============================================================
# Auth Audit Log (immutable)
# ============================================================


class AuthAuditLogModel(Base, TimestampMixin):
    """ORM model for identity.auth_audit_logs.

    Immutable audit trail for every authentication operation:
    - LOGIN_SUCCESS, LOGIN_FAILURE
    - LOGOUT, LOGOUT_ALL
    - PASSWORD_CHANGED, PASSWORD_RESET
    - EMAIL_VERIFIED
    - MFA_ENABLED, MFA_DISABLED
    - REFRESH_ROTATED
    - SESSION_REVOKED
    - SECURITY_INCIDENT

    This is the system-of-record for compliance and forensics.
    Never updated — only inserted.
    """

    __tablename__ = "auth_audit_logs"
    __table_args__ = (
        CheckConstraint(
            "action IN ("
            "'LOGIN_SUCCESS', 'LOGIN_FAILURE', 'LOGOUT', 'LOGOUT_ALL', "
            "'PASSWORD_CHANGED', 'PASSWORD_CHANGE_FAILED', 'PASSWORD_RESET', 'PASSWORD_RESET_REQUESTED', "
            "'EMAIL_VERIFIED', 'VERIFICATION_EMAIL_RESENT', "
            "'MFA_ENABLED', 'MFA_DISABLED', 'MFA_SETUP_INITIATED', 'MFA_VERIFIED', "
            "'MFA_RECOVERY_CODE_USED', 'MFA_RECOVERY_CODES_REGENERATED', "
            "'REFRESH_ROTATED', 'REFRESH_REUSE_DETECTED', "
            "'SESSION_REVOKED', 'SESSION_EXPIRED', "
            "'SECURITY_INCIDENT', 'USER_REGISTERED', 'PROFILE_UPDATED')",
            name="chk_auth_audit_logs_action",
        ),
        Index("idx_auth_audit_logs_user_created", "user_id", "created_at"),
        Index("idx_auth_audit_logs_action_created", "action", "created_at"),
        Index("idx_auth_audit_logs_correlation", "correlation_id"),
        {"schema": "identity"},
    )

    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


__all__ = [
    "VerificationTokenModel",
    "PasswordResetTokenModel",
    "RefreshTokenModel",
    "MfaSecretModel",
    "MfaRecoveryCodeModel",
    "SecurityIncidentModel",
    "AuthAuditLogModel",
]
