"""Infrastructure repositories for authentication tables.

Each repository provides typed access to one auth-related table:
- VerificationTokenRepository
- PasswordResetTokenRepository
- RefreshTokenRepository
- MfaSecretRepository
- MfaRecoveryCodeRepository
- SecurityIncidentRepository
- AuthAuditLogRepository

All repositories share the AsyncSession from the Unit of Work, ensuring
atomicity with domain changes.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.orm.auth import (
    AuthAuditLogModel,
    MfaRecoveryCodeModel,
    MfaSecretModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    SecurityIncidentModel,
    VerificationTokenModel,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


def _hash_token(raw: str) -> str:
    """Hash a token for storage. Only the hash is stored."""
    return hashlib.sha256(raw.encode()).hexdigest()


# ============================================================
# Verification Token Repository
# ============================================================


class VerificationTokenRepository:
    """Repository for identity.verification_tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: UUID,
        raw_token: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
        token_type: str = "email_verification",
    ) -> VerificationTokenModel:
        """Create a new verification token (hashed)."""
        model = VerificationTokenModel(
            id=uuid4(),
            user_id=user_id,
            token_hash=_hash_token(raw_token),
            token_type=token_type,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_raw_token(self, raw_token: str) -> VerificationTokenModel | None:
        """Look up a token by its raw value (hashes internally)."""
        token_hash = _hash_token(raw_token)
        stmt = select(VerificationTokenModel).where(
            VerificationTokenModel.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def consume(self, token_id: UUID) -> bool:
        """Mark a token as consumed (single-use)."""
        stmt = (
            update(VerificationTokenModel)
            .where(
                VerificationTokenModel.id == token_id,
                VerificationTokenModel.consumed_at.is_(None),
            )
            .values(consumed_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def invalidate_user_tokens(self, user_id: UUID) -> int:
        """Invalidate all unconsumed tokens for a user."""
        stmt = (
            update(VerificationTokenModel)
            .where(
                VerificationTokenModel.user_id == user_id,
                VerificationTokenModel.consumed_at.is_(None),
            )
            .values(consumed_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def count_recent_tokens(
        self, user_id: UUID, since: datetime
    ) -> int:
        """Count tokens created for a user since a given time (for throttling)."""
        stmt = (
            select(func.count())
            .select_from(VerificationTokenModel)
            .where(
                VerificationTokenModel.user_id == user_id,
                VerificationTokenModel.created_at >= since,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()


# ============================================================
# Password Reset Token Repository
# ============================================================


class PasswordResetTokenRepository:
    """Repository for identity.password_reset_tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: UUID,
        raw_token: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> PasswordResetTokenModel:
        model = PasswordResetTokenModel(
            id=uuid4(),
            user_id=user_id,
            token_hash=_hash_token(raw_token),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_raw_token(self, raw_token: str) -> PasswordResetTokenModel | None:
        token_hash = _hash_token(raw_token)
        stmt = select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def consume(self, token_id: UUID) -> bool:
        stmt = (
            update(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.id == token_id,
                PasswordResetTokenModel.consumed_at.is_(None),
            )
            .values(consumed_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def invalidate_user_tokens(self, user_id: UUID) -> int:
        stmt = (
            update(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.user_id == user_id,
                PasswordResetTokenModel.consumed_at.is_(None),
            )
            .values(consumed_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def count_recent_tokens(self, user_id: UUID, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.user_id == user_id,
                PasswordResetTokenModel.created_at >= since,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()


# ============================================================
# Refresh Token Repository
# ============================================================


class RefreshTokenRepository:
    """Repository for identity.refresh_tokens.

    Tracks every refresh token issued, with family-based rotation tracking.
    Used for:
    - Single-use enforcement (consumed_at set on rotation)
    - Reuse detection (presenting an already-consumed token triggers family revocation)
    - Audit trail (immutable record of every refresh token lifecycle)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: UUID,
        session_id: UUID,
        raw_token: str,
        token_family_id: UUID,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RefreshTokenModel:
        model = RefreshTokenModel(
            id=uuid4(),
            user_id=user_id,
            session_id=session_id,
            token_hash=_hash_token(raw_token),
            token_family_id=token_family_id,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_raw_token(self, raw_token: str) -> RefreshTokenModel | None:
        token_hash = _hash_token(raw_token)
        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def rotate(
        self,
        old_token_id: UUID,
        new_raw_token: str,
    ) -> bool:
        """Mark an old refresh token as consumed (rotated) and link to the new one.

        Returns True if the rotation was applied, False if the token was
        already consumed (reuse detection signal).
        """
        new_hash = _hash_token(new_raw_token)
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.id == old_token_id,
                RefreshTokenModel.consumed_at.is_(None),
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(
                consumed_at=datetime.now(timezone.utc),
                rotated_to_token_hash=new_hash,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def revoke_token(self, token_id: UUID, reason: str) -> bool:
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.id == token_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(
                revoked_at=datetime.now(timezone.utc),
                revoke_reason=reason,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def revoke_family(self, token_family_id: UUID, reason: str) -> int:
        """Revoke every unconsumed, unrevoked token in a family (reuse detection)."""
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.token_family_id == token_family_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(
                revoked_at=datetime.now(timezone.utc),
                revoke_reason=reason,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def revoke_all_for_user(self, user_id: UUID, reason: str) -> int:
        """Revoke every active refresh token for a user (logout-all / password change)."""
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(
                revoked_at=datetime.now(timezone.utc),
                revoke_reason=reason,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount


# ============================================================
# MFA Secret Repository
# ============================================================


class MfaSecretRepository:
    """Repository for identity.mfa_secrets.

    Stores TOTP secrets (encrypted). A user has at most one active secret.
    Pending secrets (during setup, before verification) coexist with the
    active secret.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending(self, user_id: UUID, secret_encrypted: bytes) -> MfaSecretModel:
        # Delete any existing pending secret for this user first
        await self._session.execute(
            delete(MfaSecretModel).where(
                MfaSecretModel.user_id == user_id,
                MfaSecretModel.status == "pending",
            )
        )
        model = MfaSecretModel(
            id=uuid4(),
            user_id=user_id,
            secret_encrypted=secret_encrypted,
            status="pending",
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_pending(self, user_id: UUID) -> MfaSecretModel | None:
        stmt = select(MfaSecretModel).where(
            MfaSecretModel.user_id == user_id,
            MfaSecretModel.status == "pending",
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active(self, user_id: UUID) -> MfaSecretModel | None:
        stmt = select(MfaSecretModel).where(
            MfaSecretModel.user_id == user_id,
            MfaSecretModel.status == "active",
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def activate(self, secret_id: UUID) -> bool:
        """Promote a pending secret to active (after first TOTP verification)."""
        stmt = (
            update(MfaSecretModel)
            .where(
                MfaSecretModel.id == secret_id,
                MfaSecretModel.status == "pending",
            )
            .values(
                status="active",
                enabled_at=datetime.now(timezone.utc),
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        """Revoke all secrets (pending + active) for a user."""
        stmt = (
            update(MfaSecretModel)
            .where(
                MfaSecretModel.user_id == user_id,
                MfaSecretModel.status.in_(["pending", "active"]),
            )
            .values(
                status="revoked",
                revoked_at=datetime.now(timezone.utc),
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount


# ============================================================
# MFA Recovery Code Repository
# ============================================================


class MfaRecoveryCodeRepository:
    """Repository for identity.mfa_recovery_codes.

    Stores SHA-256 hashes of recovery codes (the raw codes are never persisted).
    A user has up to 10 active codes; consumed codes are retained for audit
    but marked consumed_at.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(
        self, user_id: UUID, raw_codes: list[str]
    ) -> list[MfaRecoveryCodeModel]:
        # Delete all existing unconsumed codes first (regenerate flow)
        await self._session.execute(
            delete(MfaRecoveryCodeModel).where(
                MfaRecoveryCodeModel.user_id == user_id,
                MfaRecoveryCodeModel.consumed_at.is_(None),
            )
        )
        models = [
            MfaRecoveryCodeModel(
                id=uuid4(),
                user_id=user_id,
                code_hash=_hash_token(code),
            )
            for code in raw_codes
        ]
        for m in models:
            self._session.add(m)
        await self._session.flush()
        return models

    async def find_by_raw_code(
        self, user_id: UUID, raw_code: str
    ) -> MfaRecoveryCodeModel | None:
        """Find an unconsumed recovery code by its raw value."""
        code_hash = _hash_token(raw_code)
        stmt = select(MfaRecoveryCodeModel).where(
            MfaRecoveryCodeModel.user_id == user_id,
            MfaRecoveryCodeModel.code_hash == code_hash,
            MfaRecoveryCodeModel.consumed_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def consume(self, code_id: UUID, ip_address: str | None = None) -> bool:
        stmt = (
            update(MfaRecoveryCodeModel)
            .where(
                MfaRecoveryCodeModel.id == code_id,
                MfaRecoveryCodeModel.consumed_at.is_(None),
            )
            .values(
                consumed_at=datetime.now(timezone.utc),
                consumed_ip=ip_address,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def count_active(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(MfaRecoveryCodeModel)
            .where(
                MfaRecoveryCodeModel.user_id == user_id,
                MfaRecoveryCodeModel.consumed_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete_all_for_user(self, user_id: UUID) -> int:
        stmt = delete(MfaRecoveryCodeModel).where(
            MfaRecoveryCodeModel.user_id == user_id
        )
        result = await self._session.execute(stmt)
        return result.rowcount


# ============================================================
# Security Incident Repository
# ============================================================


class SecurityIncidentRepository:
    """Repository for identity.security_incidents.

    Append-only log of security incidents. Used for forensics and
    automated response.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        incident_type: str,
        severity: str,
        description: str,
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityIncidentModel:
        model = SecurityIncidentModel(
            id=uuid4(),
            user_id=user_id,
            incident_type=incident_type,
            severity=severity,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_=metadata or {},
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_by_user(
        self, user_id: UUID, limit: int = 50
    ) -> Sequence[SecurityIncidentModel]:
        stmt = (
            select(SecurityIncidentModel)
            .where(SecurityIncidentModel.user_id == user_id)
            .order_by(SecurityIncidentModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_unresolved(self, user_id: UUID | None = None) -> int:
        stmt = (
            select(func.count())
            .select_from(SecurityIncidentModel)
            .where(SecurityIncidentModel.resolved_at.is_(None))
        )
        if user_id is not None:
            stmt = stmt.where(SecurityIncidentModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()


# ============================================================
# Auth Audit Log Repository
# ============================================================


class AuthAuditLogRepository:
    """Repository for identity.auth_audit_logs.

    Immutable append-only audit trail. Every authentication operation
    writes exactly one audit record.

    Audit actions (per CHECK constraint):
    LOGIN_SUCCESS, LOGIN_FAILURE, LOGOUT, LOGOUT_ALL,
    PASSWORD_CHANGED, PASSWORD_CHANGE_FAILED, PASSWORD_RESET, PASSWORD_RESET_REQUESTED,
    EMAIL_VERIFIED, VERIFICATION_EMAIL_RESENT,
    MFA_ENABLED, MFA_DISABLED, MFA_SETUP_INITIATED, MFA_VERIFIED,
    MFA_RECOVERY_CODE_USED, MFA_RECOVERY_CODES_REGENERATED,
    REFRESH_ROTATED, REFRESH_REUSE_DETECTED,
    SESSION_REVOKED, SESSION_EXPIRED,
    SECURITY_INCIDENT, USER_REGISTERED, PROFILE_UPDATED
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        action: str,
        user_id: UUID | None = None,
        success: bool = True,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: UUID | None = None,
        correlation_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuthAuditLogModel:
        model = AuthAuditLogModel(
            id=uuid4(),
            user_id=user_id,
            action=action,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            correlation_id=correlation_id,
            details=details or {},
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_by_user(
        self, user_id: UUID, limit: int = 50
    ) -> Sequence[AuthAuditLogModel]:
        stmt = (
            select(AuthAuditLogModel)
            .where(AuthAuditLogModel.user_id == user_id)
            .order_by(AuthAuditLogModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_by_action(
        self, action: str, limit: int = 100
    ) -> Sequence[AuthAuditLogModel]:
        stmt = (
            select(AuthAuditLogModel)
            .where(AuthAuditLogModel.action == action)
            .order_by(AuthAuditLogModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_recent_failures(
        self,
        user_id: UUID | None = None,
        ip_address: str | None = None,
        since: datetime | None = None,
    ) -> int:
        """Count recent LOGIN_FAILURE entries (for brute-force detection)."""
        stmt = (
            select(func.count())
            .select_from(AuthAuditLogModel)
            .where(
                AuthAuditLogModel.action == "LOGIN_FAILURE",
                AuthAuditLogModel.success.is_(False),
            )
        )
        if user_id is not None:
            stmt = stmt.where(AuthAuditLogModel.user_id == user_id)
        if ip_address is not None:
            stmt = stmt.where(AuthAuditLogModel.ip_address == ip_address)
        if since is not None:
            stmt = stmt.where(AuthAuditLogModel.created_at >= since)
        result = await self._session.execute(stmt)
        return result.scalar_one()


__all__ = [
    "VerificationTokenRepository",
    "PasswordResetTokenRepository",
    "RefreshTokenRepository",
    "MfaSecretRepository",
    "MfaRecoveryCodeRepository",
    "SecurityIncidentRepository",
    "AuthAuditLogRepository",
]
