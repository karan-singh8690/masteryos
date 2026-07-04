"""Production authentication service — wires together all security services.

This is the application-layer facade that combines:
- PasswordService (Argon2id)
- JWTService (RS256)
- TokenService (verification + reset tokens)
- SessionService (refresh token rotation)
- MFAService (TOTP + recovery codes)
- AuthorizationService (RBAC)

…with the auth repositories (verification_tokens, password_reset_tokens,
refresh_tokens, mfa_secrets, mfa_recovery_codes, security_incidents,
auth_audit_logs) and the Unit of Work.

The service is the single entry point for all authentication operations.
Each method:
1. Validates input.
2. Performs the operation (with the appropriate security service).
3. Writes audit logs + security incidents (same transaction).
4. Returns a typed result.

NO SHA256, NO HS256, NO fake verification, NO fake sessions.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from datetime import timezone as tz_utc
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.shared.value_objects import Email
from app.infrastructure.database.orm.identity import (
    SessionModel,
    UserCredentialModel,
    UserModel,
    UserProfileModel,
)
from app.infrastructure.database.orm.auth import (
    AuthAuditLogModel,
    MfaRecoveryCodeModel,
    MfaSecretModel,
    RefreshTokenModel,
)
from app.infrastructure.database.repositories.auth import (
    AuthAuditLogRepository,
    MfaRecoveryCodeRepository,
    MfaSecretRepository,
    PasswordResetTokenRepository,
    RefreshTokenRepository,
    SecurityIncidentRepository,
    VerificationTokenRepository,
    _hash_token,
)
from app.infrastructure.security import (
    AuthorizationDenied,
    AuthorizationService,
    AuthContext,
    JWTService,
    MFAService,
    PasswordService,
    ROLE_LEARNER,
    SessionService,
    TokenService,
    TokenType,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


def _utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(tz_utc.utc)


def _ensure_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (assume UTC if naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz_utc.utc)
    return dt


# ============================================================
# Constants
# ============================================================

VERIFICATION_TOKEN_TTL = timedelta(hours=24)
PASSWORD_RESET_TOKEN_TTL = timedelta(minutes=15)
SESSION_ABSOLUTE_TIMEOUT = timedelta(days=30)
SESSION_IDLE_TIMEOUT = timedelta(hours=1)
RESEND_THROTTLE = timedelta(minutes=2)  # min 2 min between resends
FORGOT_PASSWORD_THROTTLE = timedelta(minutes=2)
MAX_LOGIN_FAILURES_PER_IP = 10  # per 5 minutes
MAX_LOGIN_FAILURES_PER_USER = 5  # per 5 minutes


# ============================================================
# Result Types
# ============================================================


@dataclass
class AuthenticationResult:
    """Result of a successful authentication operation."""

    access_token: str
    refresh_token: str
    expires_in: int
    user_id: UUID
    session_id: UUID
    user: dict[str, Any]  # user info dict


@dataclass
class LoginAttemptResult:
    """Result of a login attempt — may require MFA."""

    success: bool
    requires_mfa: bool = False
    mfa_session_token: str | None = None  # Short-lived token to complete MFA
    auth: AuthenticationResult | None = None
    error: str | None = None
    error_code: str | None = None


@dataclass
class RefreshResult:
    """Result of refresh token rotation."""

    success: bool
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    error: str | None = None
    session_revoked: bool = False  # True if reuse detected


# ============================================================
# Production Authentication Service
# ============================================================


class ProductionAuthService:
    """The single entry point for all authentication operations.

    All methods accept an AsyncSession (from the UoW) and perform their
    work within the caller's transaction. The caller is responsible for
    committing.

    Usage:
        async with uow as uow:
            session = uow._session
            result = await auth_service.login(session, email, password, ...)
            if result.success:
                await uow.commit()
    """

    def __init__(
        self,
        password_service: PasswordService | None = None,
        jwt_service: JWTService | None = None,
        mfa_service: MFAService | None = None,
    ) -> None:
        self._password_service = password_service or PasswordService(
            memory_cost=1024,  # Lower for tests; production uses 19456
            time_cost=1,
            parallelism=1,
        )
        self._jwt_service = jwt_service or JWTService()
        self._mfa_service = mfa_service or MFAService()

    # ============================================================
    # Properties (for tests / external access)
    # ============================================================

    @property
    def password_service(self) -> PasswordService:
        return self._password_service

    @property
    def jwt_service(self) -> JWTService:
        return self._jwt_service

    @property
    def mfa_service(self) -> MFAService:
        return self._mfa_service

    # ============================================================
    # Registration
    # ============================================================

    async def register(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        display_name: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        timezone: str = "UTC",
        locale: str = "en-US",
    ) -> tuple[UserModel, str, str]:
        """Register a new user.

        Returns (user_model, raw_verification_token, ...).
        The verification token is returned ONCE — it must be sent via email.
        The user is created in PENDING_VERIFICATION status.

        Raises:
            ValueError: If the email is already registered or password is weak.
        """
        # Validate email
        try:
            email_vo = Email(email)
        except Exception as exc:
            raise ValueError(f"Invalid email: {exc}") from exc

        # Validate password strength
        if not password or len(password) < 12:
            raise ValueError("Password must be at least 12 characters")

        # Check for existing user
        stmt = select(UserModel).where(
            UserModel.email == email_vo.value,
            UserModel.deleted_at.is_(None),
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            raise ValueError("EMAIL_ALREADY_REGISTERED")

        # Hash password with Argon2id
        password_hash = self._password_service.hash_password(password)

        # Create user
        user_id = uuid4()
        now = datetime.now(tz_utc.utc)
        user_model = UserModel(
            id=user_id,
            email=email_vo.value,
            email_verified_at=None,
            status="pending_verification",
            mfa_enabled=False,
        )
        session.add(user_model)
        # Flush to INSERT the user row immediately so foreign key constraints
        # on verification_tokens, user_credentials, etc. can be satisfied.
        await session.flush()

        # Create profile
        profile_model = UserProfileModel(
            user_id=user_id,
            display_name=display_name,
            timezone=timezone,
            locale=locale,
        )
        session.add(profile_model)

        # Create credential (Argon2id hash)
        credential_model = UserCredentialModel(
            id=uuid4(),
            user_id=user_id,
            credential_type="password",
            password_hash=password_hash,
        )
        session.add(credential_model)
        await session.flush()

        # Create verification token
        raw_verification_token = secrets.token_urlsafe(32)
        verification_repo = VerificationTokenRepository(session)
        await verification_repo.create(
            user_id=user_id,
            raw_token=raw_verification_token,
            expires_at=now + VERIFICATION_TOKEN_TTL,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Audit log
        audit_repo = AuthAuditLogRepository(session)
        await audit_repo.record(
            action="USER_REGISTERED",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": email_vo.value},
        )

        await session.flush()
        logger.info("user_registered", user_id=str(user_id), email=email_vo.value)
        return user_model, raw_verification_token, password_hash

    async def issue_tokens_for_user(
        self,
        session: AsyncSession,
        user_id: UUID,
        roles: list[str] | None = None,
        device_fingerprint: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthenticationResult:
        """Issue access + refresh tokens and create a session.

        Used by register(), login() (after MFA if needed), and OAuth flows.
        """
        roles = roles or [ROLE_LEARNER]
        now = datetime.now(tz_utc.utc)

        # Get user info
        user_model = await session.get(UserModel, user_id)
        if user_model is None:
            raise ValueError(f"User not found: {user_id}")

        # Issue access token (RS256 JWT)
        access_token = self._jwt_service.issue_access_token(
            user_id=user_id, roles=roles, token_version=1
        )

        # Create session record
        session_id = uuid4()
        token_family_id = uuid4()
        raw_refresh_token = secrets.token_urlsafe(32)
        refresh_token_hash = _hash_token(raw_refresh_token)

        session_model = SessionModel(
            id=session_id,
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            token_family_id=token_family_id,
            device_fingerprint=device_fingerprint,
            last_ip=ip_address,
            user_agent=user_agent,
            expires_at=now + SESSION_ABSOLUTE_TIMEOUT,
            last_seen_at=now,
        )
        session.add(session_model)

        # Also record in refresh_tokens table (for rotation tracking)
        refresh_repo = RefreshTokenRepository(session)
        await refresh_repo.create(
            user_id=user_id,
            session_id=session_id,
            raw_token=raw_refresh_token,
            token_family_id=token_family_id,
            expires_at=now + SESSION_ABSOLUTE_TIMEOUT,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        user_info = {
            "id": str(user_model.id),
            "email": user_model.email,
            "status": user_model.status,
            "mfa_enabled": user_model.mfa_enabled,
            "email_verified_at": user_model.email_verified_at.isoformat()
            if user_model.email_verified_at
            else None,
            "created_at": user_model.created_at.isoformat() if user_model.created_at else None,
        }

        return AuthenticationResult(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            expires_in=15 * 60,
            user_id=user_id,
            session_id=session_id,
            user=user_info,
        )

    # ============================================================
    # Login
    # ============================================================

    async def login(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        mfa_code: str | None = None,
        recovery_code: str | None = None,
        device_fingerprint: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginAttemptResult:
        """Authenticate a user with email + password (+ MFA if enabled).

        Returns:
            LoginAttemptResult with success=True (and tokens) on success,
            or success=True with requires_mfa=True if MFA is needed,
            or success=False with error on failure.
        """
        audit_repo = AuthAuditLogRepository(session)
        security_repo = SecurityIncidentRepository(session)

        # Look up user
        try:
            email_vo = Email(email)
        except Exception:
            await audit_repo.record(
                action="LOGIN_FAILURE",
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "invalid_email_format", "email": email},
            )
            return LoginAttemptResult(
                success=False, error="Invalid email or password", error_code="INVALID_CREDENTIALS"
            )

        stmt = select(UserModel).where(
            UserModel.email == email_vo.value,
            UserModel.deleted_at.is_(None),
        )
        user_model = (await session.execute(stmt)).scalar_one_or_none()

        # Constant-time-ish: even if user not found, do a dummy verify
        if user_model is None:
            # Do a dummy hash to keep timing similar
            self._password_service.hash_password("dummy_password_for_timing")
            await audit_repo.record(
                action="LOGIN_FAILURE",
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "user_not_found", "email": email_vo.value},
            )
            return LoginAttemptResult(
                success=False, error="Invalid email or password", error_code="INVALID_CREDENTIALS"
            )

        # Check user status
        if user_model.status in ("suspended",):
            await audit_repo.record(
                action="LOGIN_FAILURE",
                user_id=user_model.id,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "account_suspended"},
            )
            return LoginAttemptResult(
                success=False,
                error="Account is suspended",
                error_code="ACCOUNT_SUSPENDED",
            )
        if user_model.status in ("pending_deletion",):
            await audit_repo.record(
                action="LOGIN_FAILURE",
                user_id=user_model.id,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "account_pending_deletion"},
            )
            return LoginAttemptResult(
                success=False,
                error="Account is pending deletion",
                error_code="ACCOUNT_PENDING_DELETION",
            )

        # Look up password credential
        cred_stmt = select(UserCredentialModel).where(
            UserCredentialModel.user_id == user_model.id,
            UserCredentialModel.credential_type == "password",
        )
        cred_model = (await session.execute(cred_stmt)).scalar_one_or_none()

        if cred_model is None or cred_model.password_hash is None:
            await audit_repo.record(
                action="LOGIN_FAILURE",
                user_id=user_model.id,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "no_password_credential"},
            )
            return LoginAttemptResult(
                success=False, error="Invalid email or password", error_code="INVALID_CREDENTIALS"
            )

        # Verify password with Argon2id (verify_and_upgrade for transparent rehash)
        verified, new_hash = self._password_service.verify_and_upgrade(
            password, cred_model.password_hash
        )
        if not verified:
            await audit_repo.record(
                action="LOGIN_FAILURE",
                user_id=user_model.id,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "invalid_password"},
            )
            # Check for brute-force pattern
            recent_failures = await audit_repo.count_recent_failures(
                user_id=user_model.id, since=datetime.now(tz_utc.utc) - timedelta(minutes=5)
            )
            if recent_failures >= MAX_LOGIN_FAILURES_PER_USER:
                await security_repo.record(
                    incident_type="login_brute_force",
                    severity="warning",
                    description=f"Multiple login failures for user {user_model.id}",
                    user_id=user_model.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            return LoginAttemptResult(
                success=False, error="Invalid email or password", error_code="INVALID_CREDENTIALS"
            )

        # Upgrade hash if needed (transparent)
        if new_hash:
            cred_model.password_hash = new_hash
            await session.flush()
            logger.info("password_hash_upgraded", user_id=str(user_model.id))

        # If MFA is enabled, require MFA code
        if user_model.mfa_enabled:
            if mfa_code is None and recovery_code is None:
                # Return MFA challenge
                mfa_session_token = secrets.token_urlsafe(32)
                await audit_repo.record(
                    action="LOGIN_FAILURE",
                    user_id=user_model.id,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "mfa_required"},
                )
                return LoginAttemptResult(
                    success=True,
                    requires_mfa=True,
                    mfa_session_token=mfa_session_token,
                )

            # Verify MFA
            mfa_secret_repo = MfaSecretRepository(session)
            secret_model = await mfa_secret_repo.get_active(user_model.id)
            if secret_model is None:
                # MFA flag is set but no active secret — security incident
                await security_repo.record(
                    incident_type="other",
                    severity="critical",
                    description="MFA enabled but no active secret found",
                    user_id=user_model.id,
                    ip_address=ip_address,
                )
                return LoginAttemptResult(
                    success=False, error="MFA configuration error", error_code="MFA_MISCONFIGURED"
                )

            # Decrypt secret (in production: use KMS; here we use the raw bytes for simplicity)
            # For this implementation, secret_encrypted stores the raw secret
            # (production would use envelope encryption)
            secret = secret_model.secret_encrypted.decode() if isinstance(
                secret_model.secret_encrypted, bytes
            ) else str(secret_model.secret_encrypted)

            if mfa_code:
                if not self._mfa_service.verify_totp(secret, mfa_code):
                    await audit_repo.record(
                        action="LOGIN_FAILURE",
                        user_id=user_model.id,
                        success=False,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        details={"reason": "invalid_mfa_code"},
                    )
                    return LoginAttemptResult(
                        success=False, error="Invalid MFA code", error_code="INVALID_MFA_CODE"
                    )
                await audit_repo.record(
                    action="MFA_VERIFIED",
                    user_id=user_model.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"context": "login"},
                )
            elif recovery_code:
                recovery_repo = MfaRecoveryCodeRepository(session)
                code_model = await recovery_repo.find_by_raw_code(user_model.id, recovery_code)
                if code_model is None:
                    await audit_repo.record(
                        action="LOGIN_FAILURE",
                        user_id=user_model.id,
                        success=False,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        details={"reason": "invalid_recovery_code"},
                    )
                    return LoginAttemptResult(
                        success=False,
                        error="Invalid recovery code",
                        error_code="INVALID_RECOVERY_CODE",
                    )
                await recovery_repo.consume(code_model.id, ip_address=ip_address)
                remaining = await recovery_repo.count_active(user_model.id)
                await audit_repo.record(
                    action="MFA_RECOVERY_CODE_USED",
                    user_id=user_model.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"remaining_codes": remaining},
                )

        # Issue tokens + create session
        # Task 025-deploy: read role from the user record so admin tokens
        # carry the administrator role for RBAC enforcement downstream.
        user_roles = [user_model.role] if getattr(user_model, "role", None) else [ROLE_LEARNER]
        auth_result = await self.issue_tokens_for_user(
            session=session,
            user_id=user_model.id,
            roles=user_roles,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Audit log
        await audit_repo.record(
            action="LOGIN_SUCCESS",
            user_id=user_model.id,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=auth_result.session_id,
        )

        return LoginAttemptResult(success=True, auth=auth_result)

    # ============================================================
    # Refresh
    # ============================================================

    async def refresh(
        self,
        session: AsyncSession,
        raw_refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RefreshResult:
        """Rotate a refresh token.

        1. Look up the token by hash.
        2. If not found → invalid (could be reuse, but we can't tell without family lookup).
        3. If found and consumed/revoked → REUSE DETECTED → revoke family.
        4. If valid → rotate (consume old, issue new in same family).
        5. Issue new access token.
        """
        audit_repo = AuthAuditLogRepository(session)
        security_repo = SecurityIncidentRepository(session)
        refresh_repo = RefreshTokenRepository(session)

        token_model = await refresh_repo.get_by_raw_token(raw_refresh_token)
        if token_model is None:
            await audit_repo.record(
                action="REFRESH_REUSE_DETECTED",
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "token_not_found"},
            )
            return RefreshResult(success=False, error="Invalid refresh token")

        # Check if already consumed (reuse detection)
        if token_model.consumed_at is not None or token_model.revoked_at is not None:
            # Reuse detected — revoke entire family
            family_count = await refresh_repo.revoke_family(
                token_model.token_family_id, reason="reuse_detected"
            )
            await security_repo.record(
                incident_type="refresh_token_reuse",
                severity="critical",
                description=f"Refresh token reuse detected for user {token_model.user_id}",
                user_id=token_model.user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"family_id": str(token_model.token_family_id), "revoked_count": family_count},
            )
            await audit_repo.record(
                action="REFRESH_REUSE_DETECTED",
                user_id=token_model.user_id,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "family_id": str(token_model.token_family_id),
                    "revoked_count": family_count,
                },
            )
            return RefreshResult(
                success=False,
                error="Refresh token reuse detected — session revoked",
                session_revoked=True,
            )

        # Check expiration
        if _utcnow() > _ensure_aware(token_model.expires_at):
            await refresh_repo.revoke_token(token_model.id, reason="expired")
            return RefreshResult(success=False, error="Refresh token expired")

        # Issue new tokens
        new_raw_refresh = secrets.token_urlsafe(32)
        rotated = await refresh_repo.rotate(token_model.id, new_raw_refresh)
        if not rotated:
            # Race condition — token was consumed by another request
            return RefreshResult(success=False, error="Refresh token race condition")

        # Create new refresh token record (same family)
        await refresh_repo.create(
            user_id=token_model.user_id,
            session_id=token_model.session_id,
            raw_token=new_raw_refresh,
            token_family_id=token_model.token_family_id,
            expires_at=datetime.now(tz_utc.utc) + SESSION_ABSOLUTE_TIMEOUT,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Issue new access token
        # Task 025-deploy: read the user's role from the DB so the new
        # access token carries the correct role claims for RBAC.
        user_for_role = await session.get(UserModel, token_model.user_id)
        if user_for_role is None:
            # User was deleted between token issue and refresh — refuse.
            return RefreshResult(
                success=False,
                error="User not found",
                session_revoked=False,
            )
        user_roles = [getattr(user_for_role, "role", None) or ROLE_LEARNER]
        access_token = self._jwt_service.issue_access_token(
            user_id=token_model.user_id,
            roles=user_roles,
            token_version=getattr(user_for_role, "token_version", 1),
        )

        # Update session last_seen_at
        await session.execute(
            update(SessionModel)
            .where(SessionModel.id == token_model.session_id)
            .values(last_seen_at=datetime.now(tz_utc.utc), last_ip=ip_address)
        )

        # Audit log
        await audit_repo.record(
            action="REFRESH_ROTATED",
            user_id=token_model.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=token_model.session_id,
            details={"token_family_id": str(token_model.token_family_id)},
        )

        return RefreshResult(
            success=True,
            access_token=access_token,
            refresh_token=new_raw_refresh,
            expires_in=15 * 60,
        )

    # ============================================================
    # Logout
    # ============================================================

    async def logout(
        self,
        session: AsyncSession,
        raw_refresh_token: str | None,
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """Logout — revoke the current session only."""
        audit_repo = AuthAuditLogRepository(session)
        refresh_repo = RefreshTokenRepository(session)

        if raw_refresh_token is None:
            # No refresh token — nothing to revoke
            if user_id:
                await audit_repo.record(
                    action="LOGOUT",
                    user_id=user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            return True

        token_model = await refresh_repo.get_by_raw_token(raw_refresh_token)
        if token_model is None:
            return False

        # Revoke the token
        await refresh_repo.revoke_token(token_model.id, reason="logout")

        # Revoke the session
        await session.execute(
            update(SessionModel)
            .where(SessionModel.id == token_model.session_id)
            .values(revoked_at=datetime.now(tz_utc.utc), revoke_reason="logout")
        )

        await audit_repo.record(
            action="LOGOUT",
            user_id=token_model.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=token_model.session_id,
        )
        return True

    async def logout_all(
        self,
        session: AsyncSession,
        user_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> int:
        """Logout all devices — revoke every session for the user."""
        audit_repo = AuthAuditLogRepository(session)
        refresh_repo = RefreshTokenRepository(session)

        # Revoke all refresh tokens
        token_count = await refresh_repo.revoke_all_for_user(user_id, reason="logout_all")

        # Revoke all sessions
        result = await session.execute(
            update(SessionModel)
            .where(
                SessionModel.user_id == user_id,
                SessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(tz_utc.utc), revoke_reason="logout_all")
        )
        session_count = result.rowcount

        await audit_repo.record(
            action="LOGOUT_ALL",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"revoked_sessions": session_count, "revoked_tokens": token_count},
        )
        return session_count

    # ============================================================
    # Email Verification
    # ============================================================

    async def verify_email(
        self,
        session: AsyncSession,
        raw_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Verify a user's email with a verification token.

        Returns user info dict on success.
        Raises ValueError on invalid/expired/used tokens.
        """
        audit_repo = AuthAuditLogRepository(session)
        token_repo = VerificationTokenRepository(session)

        token_model = await token_repo.get_by_raw_token(raw_token)
        if token_model is None:
            raise ValueError("Invalid verification token")

        if token_model.consumed_at is not None:
            raise ValueError("Token already used")

        if _utcnow() > _ensure_aware(token_model.expires_at):
            raise ValueError("Token expired")

        # Consume the token
        await token_repo.consume(token_model.id)

        # Update user status
        user_model = await session.get(UserModel, token_model.user_id)
        if user_model is None:
            raise ValueError("User not found")

        user_model.email_verified_at = datetime.now(tz_utc.utc)
        user_model.status = "active"

        await audit_repo.record(
            action="EMAIL_VERIFIED",
            user_id=user_model.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await session.flush()
        return {
            "id": str(user_model.id),
            "email": user_model.email,
            "status": user_model.status,
            "mfa_enabled": user_model.mfa_enabled,
            "email_verified_at": user_model.email_verified_at.isoformat(),
            "created_at": user_model.created_at.isoformat() if user_model.created_at else None,
        }

    async def resend_verification(
        self,
        session: AsyncSession,
        email: str,
        ip_address: str | None = None,
    ) -> str | None:
        """Resend the verification email (throttled).

        Returns the raw verification token (to be emailed) or None if:
        - User not found (do not leak existence)
        - Email already verified
        - Throttled (too soon since last resend)
        """
        audit_repo = AuthAuditLogRepository(session)
        token_repo = VerificationTokenRepository(session)

        try:
            email_vo = Email(email)
        except Exception:
            return None

        user_model = await self._get_user_by_email(session, email_vo)
        if user_model is None:
            return None
        if user_model.email_verified_at is not None:
            return None

        # Throttle: max 1 resend per 2 minutes
        recent_count = await token_repo.count_recent_tokens(
            user_model.id, datetime.now(tz_utc.utc) - RESEND_THROTTLE
        )
        if recent_count > 0:
            return None

        # Create new token
        raw_token = secrets.token_urlsafe(32)
        await token_repo.create(
            user_id=user_model.id,
            raw_token=raw_token,
            expires_at=datetime.now(tz_utc.utc) + VERIFICATION_TOKEN_TTL,
            ip_address=ip_address,
        )

        await audit_repo.record(
            action="VERIFICATION_EMAIL_RESENT",
            user_id=user_model.id,
            ip_address=ip_address,
        )
        return raw_token

    # ============================================================
    # Password Reset
    # ============================================================

    async def forgot_password(
        self,
        session: AsyncSession,
        email: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> str | None:
        """Request a password reset email.

        Returns the raw reset token (to be emailed) or None if the user
        does not exist (do not leak account existence).
        """
        audit_repo = AuthAuditLogRepository(session)
        token_repo = PasswordResetTokenRepository(session)

        try:
            email_vo = Email(email)
        except Exception:
            await audit_repo.record(
                action="PASSWORD_RESET_REQUESTED",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": email, "result": "invalid_email"},
            )
            return None

        user_model = await self._get_user_by_email(session, email_vo)
        if user_model is None:
            # Don't leak — log as if successful
            await audit_repo.record(
                action="PASSWORD_RESET_REQUESTED",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": email_vo.value, "result": "user_not_found"},
            )
            return None

        # Throttle: max 1 reset per 2 minutes
        recent_count = await token_repo.count_recent_tokens(
            user_model.id, datetime.now(tz_utc.utc) - FORGOT_PASSWORD_THROTTLE
        )
        if recent_count > 0:
            return None

        raw_token = secrets.token_urlsafe(32)
        await token_repo.create(
            user_id=user_model.id,
            raw_token=raw_token,
            expires_at=datetime.now(tz_utc.utc) + PASSWORD_RESET_TOKEN_TTL,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await audit_repo.record(
            action="PASSWORD_RESET_REQUESTED",
            user_id=user_model.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return raw_token

    async def reset_password(
        self,
        session: AsyncSession,
        raw_token: str,
        new_password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UUID:
        """Reset password with a token.

        Returns the user_id on success.
        Raises ValueError on invalid/expired/used tokens or weak password.
        """
        audit_repo = AuthAuditLogRepository(session)
        token_repo = PasswordResetTokenRepository(session)
        refresh_repo = RefreshTokenRepository(session)

        if not new_password or len(new_password) < 12:
            raise ValueError("Password must be at least 12 characters")

        token_model = await token_repo.get_by_raw_token(raw_token)
        if token_model is None:
            raise ValueError("Invalid reset token")

        if token_model.consumed_at is not None:
            raise ValueError("Token already used")

        if _utcnow() > _ensure_aware(token_model.expires_at):
            raise ValueError("Token expired")

        # Consume the token
        await token_repo.consume(token_model.id)

        # Update password
        new_hash = self._password_service.hash_password(new_password)
        await session.execute(
            update(UserCredentialModel)
            .where(
                UserCredentialModel.user_id == token_model.user_id,
                UserCredentialModel.credential_type == "password",
            )
            .values(password_hash=new_hash)
        )

        # Revoke all refresh tokens + sessions for this user
        revoked_tokens = await refresh_repo.revoke_all_for_user(
            token_model.user_id, reason="password_reset"
        )
        await session.execute(
            update(SessionModel)
            .where(
                SessionModel.user_id == token_model.user_id,
                SessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(tz_utc.utc), revoke_reason="password_reset")
        )

        # Invalidate any other password reset tokens for this user
        await token_repo.invalidate_user_tokens(token_model.user_id)

        await audit_repo.record(
            action="PASSWORD_RESET",
            user_id=token_model.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"revoked_tokens": revoked_tokens},
        )

        await session.flush()
        return token_model.user_id

    async def change_password(
        self,
        session: AsyncSession,
        user_id: UUID,
        current_password: str,
        new_password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """Change password (while authenticated).

        Requires the current password. Revokes all other sessions.
        """
        audit_repo = AuthAuditLogRepository(session)
        refresh_repo = RefreshTokenRepository(session)

        if not new_password or len(new_password) < 12:
            raise ValueError("Password must be at least 12 characters")

        # Look up credential
        cred_stmt = select(UserCredentialModel).where(
            UserCredentialModel.user_id == user_id,
            UserCredentialModel.credential_type == "password",
        )
        cred_model = (await session.execute(cred_stmt)).scalar_one_or_none()
        if cred_model is None or cred_model.password_hash is None:
            raise ValueError("No password credential found")

        # Verify current password
        verified, _ = self._password_service.verify_and_upgrade(
            current_password, cred_model.password_hash
        )
        if not verified:
            await audit_repo.record(
                action="PASSWORD_CHANGE_FAILED",
                user_id=user_id,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "invalid_current_password"},
            )
            raise ValueError("Current password is incorrect")

        # Update password
        new_hash = self._password_service.hash_password(new_password)
        cred_model.password_hash = new_hash

        # Revoke all sessions + refresh tokens (force re-login on all devices)
        revoked_tokens = await refresh_repo.revoke_all_for_user(user_id, reason="password_change")
        await session.execute(
            update(SessionModel)
            .where(
                SessionModel.user_id == user_id,
                SessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(tz_utc.utc), revoke_reason="password_change")
        )

        await audit_repo.record(
            action="PASSWORD_CHANGED",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"revoked_tokens": revoked_tokens},
        )
        await session.flush()
        return True

    # ============================================================
    # MFA
    # ============================================================

    async def setup_mfa(
        self,
        session: AsyncSession,
        user_id: UUID,
        user_email: str,
    ) -> dict[str, Any]:
        """Initiate MFA setup — generates secret + QR URI + recovery codes.

        Returns {secret, qr_code_uri, recovery_codes}.
        The secret is stored as 'pending' until enable_mfa() is called.
        The recovery codes are stored hashed (only returned raw ONCE).
        """
        audit_repo = AuthAuditLogRepository(session)
        secret_repo = MfaSecretRepository(session)
        recovery_repo = MfaRecoveryCodeRepository(session)

        # Generate via MFAService
        setup = self._mfa_service.setup_mfa(user_email)

        # Store secret as pending (encrypted — here we store as bytes for simplicity)
        await secret_repo.create_pending(user_id, setup.secret.encode())

        # Store recovery codes (hashed)
        await recovery_repo.create_many(user_id, setup.recovery_codes)

        await audit_repo.record(
            action="MFA_SETUP_INITIATED",
            user_id=user_id,
        )
        return {
            "secret": setup.secret,
            "qr_code_uri": setup.qr_code_uri,
            "recovery_codes": setup.recovery_codes,
        }

    async def enable_mfa(
        self,
        session: AsyncSession,
        user_id: UUID,
        totp_code: str,
        pending_secret: str,
    ) -> bool:
        """Enable MFA — verifies the first TOTP code against the pending secret.

        Raises ValueError if the code is invalid or no pending secret exists.
        """
        audit_repo = AuthAuditLogRepository(session)
        secret_repo = MfaSecretRepository(session)

        # Verify the TOTP code against the provided pending secret
        if not self._mfa_service.verify_totp(pending_secret, totp_code):
            raise ValueError("Invalid TOTP code")

        # Activate the pending secret
        pending_model = await secret_repo.get_pending(user_id)
        if pending_model is None:
            raise ValueError("No pending MFA secret found")

        # Verify the pending secret matches what was provided
        stored_secret = pending_model.secret_encrypted.decode() if isinstance(
            pending_model.secret_encrypted, bytes
        ) else str(pending_model.secret_encrypted)
        if stored_secret != pending_secret:
            raise ValueError("Pending secret mismatch")

        await secret_repo.activate(pending_model.id)

        # Set mfa_enabled on user
        await session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(mfa_enabled=True)
        )

        await audit_repo.record(
            action="MFA_ENABLED",
            user_id=user_id,
        )
        return True

    async def disable_mfa(
        self,
        session: AsyncSession,
        user_id: UUID,
        password: str,
        is_admin: bool = False,
    ) -> bool:
        """Disable MFA — requires current password for verification.

        Admins cannot disable MFA.
        """
        audit_repo = AuthAuditLogRepository(session)
        secret_repo = MfaSecretRepository(session)
        recovery_repo = MfaRecoveryCodeRepository(session)

        if is_admin:
            raise ValueError("Cannot disable MFA for admin accounts")

        # Verify password
        cred_stmt = select(UserCredentialModel).where(
            UserCredentialModel.user_id == user_id,
            UserCredentialModel.credential_type == "password",
        )
        cred_model = (await session.execute(cred_stmt)).scalar_one_or_none()
        if cred_model is None or cred_model.password_hash is None:
            raise ValueError("No password credential found")

        verified, _ = self._password_service.verify_and_upgrade(password, cred_model.password_hash)
        if not verified:
            raise ValueError("Password is incorrect")

        # Revoke secrets + delete recovery codes
        await secret_repo.revoke_all_for_user(user_id)
        await recovery_repo.delete_all_for_user(user_id)

        # Set mfa_enabled = False
        await session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(mfa_enabled=False)
        )

        await audit_repo.record(
            action="MFA_DISABLED",
            user_id=user_id,
        )
        return True

    async def verify_mfa(
        self,
        session: AsyncSession,
        user_id: UUID,
        code: str,
        context: str = "login",
    ) -> bool:
        """Verify a TOTP code."""
        audit_repo = AuthAuditLogRepository(session)
        secret_repo = MfaSecretRepository(session)

        secret_model = await secret_repo.get_active(user_id)
        if secret_model is None:
            return False

        secret = secret_model.secret_encrypted.decode() if isinstance(
            secret_model.secret_encrypted, bytes
        ) else str(secret_model.secret_encrypted)

        if not self._mfa_service.verify_totp(secret, code):
            return False

        await audit_repo.record(
            action="MFA_VERIFIED",
            user_id=user_id,
            details={"context": context},
        )
        return True

    async def use_recovery_code(
        self,
        session: AsyncSession,
        user_id: UUID,
        recovery_code: str,
        ip_address: str | None = None,
    ) -> tuple[bool, int]:
        """Use a recovery code. Returns (success, remaining_count)."""
        audit_repo = AuthAuditLogRepository(session)
        recovery_repo = MfaRecoveryCodeRepository(session)

        code_model = await recovery_repo.find_by_raw_code(user_id, recovery_code)
        if code_model is None:
            return (False, 0)

        await recovery_repo.consume(code_model.id, ip_address=ip_address)
        remaining = await recovery_repo.count_active(user_id)

        await audit_repo.record(
            action="MFA_RECOVERY_CODE_USED",
            user_id=user_id,
            ip_address=ip_address,
            details={"remaining_codes": remaining},
        )
        return (True, remaining)

    # ============================================================
    # Helpers
    # ============================================================

    async def _get_user_by_email(
        self, session: AsyncSession, email: Email
    ) -> UserModel | None:
        stmt = select(UserModel).where(
            UserModel.email == email.value,
            UserModel.deleted_at.is_(None),
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_user_sessions(
        self, session: AsyncSession, user_id: UUID
    ) -> list[dict[str, Any]]:
        """List all active sessions for a user (for security dashboard)."""
        stmt = (
            select(SessionModel)
            .where(
                SessionModel.user_id == user_id,
                SessionModel.revoked_at.is_(None),
            )
            .order_by(SessionModel.last_seen_at.desc())
        )
        result = await session.execute(stmt)
        models = result.scalars().all()
        return [
            {
                "id": str(m.id),
                "device_fingerprint": m.device_fingerprint,
                "last_ip": m.last_ip,
                "user_agent": m.user_agent,
                "expires_at": m.expires_at.isoformat() if m.expires_at else None,
                "last_seen_at": m.last_seen_at.isoformat() if m.last_seen_at else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in models
        ]

    async def get_security_dashboard(
        self, session: AsyncSession, user_id: UUID
    ) -> dict[str, Any]:
        """Get the user's security dashboard."""
        user_model = await session.get(UserModel, user_id)
        if user_model is None:
            raise ValueError("User not found")

        # Active sessions
        sessions = await self.get_user_sessions(session, user_id)

        # Recovery codes remaining
        recovery_repo = MfaRecoveryCodeRepository(session)
        recovery_count = await recovery_repo.count_active(user_id)

        # Recent security events
        audit_repo = AuthAuditLogRepository(session)
        recent_audits = await audit_repo.list_by_user(user_id, limit=20)
        recent_events = [
            {
                "action": a.action,
                "success": a.success,
                "ip_address": a.ip_address,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in recent_audits
        ]

        # Password last changed (look at last PASSWORD_CHANGED audit entry)
        password_changes = [
            a for a in recent_audits if a.action == "PASSWORD_CHANGED"
        ] + [a for a in recent_audits if a.action == "PASSWORD_RESET"]
        password_last_changed = (
            password_changes[0].created_at.isoformat()
            if password_changes
            else None
        )

        return {
            "mfa_enabled": user_model.mfa_enabled,
            "email_verified": user_model.email_verified_at is not None,
            "password_last_changed_at": password_last_changed,
            "active_sessions": sessions,
            "recovery_codes_remaining": recovery_count,
            "recent_security_events": recent_events,
        }


__all__ = ["ProductionAuthService", "AuthenticationResult", "LoginAttemptResult", "RefreshResult"]
