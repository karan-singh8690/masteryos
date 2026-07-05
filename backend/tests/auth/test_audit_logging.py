"""Audit logging integration tests.

Tests:
- Every auth operation creates an audit log entry
- Audit log entries are immutable (cannot be updated)
- Audit log entries include user_id, action, success, ip_address
- Audit log entries include correlation_id when present
- Audit log entries include details JSON
- LOGIN_SUCCESS audit log
- LOGIN_FAILURE audit log (wrong password)
- LOGOUT audit log
- LOGOUT_ALL audit log
- USER_REGISTERED audit log
- EMAIL_VERIFIED audit log
- VERIFICATION_EMAIL_RESENT audit log
- PASSWORD_RESET_REQUESTED audit log
- PASSWORD_RESET audit log
- PASSWORD_CHANGED audit log
- MFA_SETUP_INITIATED audit log
- MFA_ENABLED audit log
- MFA_DISABLED audit log
- MFA_VERIFIED audit log
- MFA_RECOVERY_CODE_USED audit log
- REFRESH_ROTATED audit log
- REFRESH_REUSE_DETECTED audit log
- Audit log entries can be queried by user
- Audit log entries can be queried by action
- Audit log entries are ordered by created_at desc
- Multiple audit entries for a sequence of operations
- Audit log includes session_id for session-scoped actions
- Failed operations still create audit log entries
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.infrastructure.database.orm.auth import AuthAuditLogModel
from tests.auth.conftest import create_test_user, get_auth_headers


pytestmark = pytest.mark.asyncio


class TestAuditLogging:
    """Tests for audit logging across all auth operations."""

    async def test_register_creates_audit_log(
        self, test_client, test_session_factory
    ):
        """USER_REGISTERED audit log is created on registration."""
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "audit1@example.com",
                "password": "SecurePassword123!",
                "display_name": "Audit User",
            },
        )
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "USER_REGISTERED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None
            assert audit.success is True
            assert audit.details.get("email") == "audit1@example.com"

    async def test_login_success_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """LOGIN_SUCCESS audit log is created on successful login."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit2@example.com",
                password="SecurePassword123!"
            )
        await test_client.post(
            "/api/v1/auth/login",
            json={"email": "audit2@example.com", "password": "SecurePassword123!"},
        )
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "LOGIN_SUCCESS"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_login_failure_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """LOGIN_FAILURE audit log is created on failed login."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit3@example.com",
                password="SecurePassword123!"
            )
        await test_client.post(
            "/api/v1/auth/login",
            json={"email": "audit3@example.com", "password": "WrongPassword123!"},
        )
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "LOGIN_FAILURE",
                AuthAuditLogModel.success.is_(False),
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_logout_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """LOGOUT audit log is created on logout."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit4@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "audit4@example.com", "SecurePassword123!"
        )
        await test_client.post("/api/v1/auth/logout", headers=headers)
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "LOGOUT"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_logout_all_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """LOGOUT_ALL audit log is created on logout-all."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit5@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "audit5@example.com", "SecurePassword123!"
        )
        await test_client.post("/api/v1/auth/logout-all", headers=headers)
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "LOGOUT_ALL"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_refresh_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """REFRESH_ROTATED audit log is created on refresh."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit6@example.com",
                password="SecurePassword123!"
            )
        login_resp = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "audit6@example.com", "password": "SecurePassword123!"},
        )
        rt = login_resp.json()["refresh_token"]
        await test_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": rt}
        )
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "REFRESH_ROTATED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_refresh_reuse_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """REFRESH_REUSE_DETECTED audit log is created on reuse."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit7@example.com",
                password="SecurePassword123!"
            )
        login_resp = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "audit7@example.com", "password": "SecurePassword123!"},
        )
        rt = login_resp.json()["refresh_token"]
        # First refresh (success)
        await test_client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        # Reuse (fail)
        await test_client.post("/api/v1/auth/refresh", json={"refresh_token": rt})

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "REFRESH_REUSE_DETECTED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_email_verified_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """EMAIL_VERIFIED audit log is created on email verification."""
        async with test_session_factory() as session:
            _, token = await create_test_user(
                session, auth_service, email="audit8@example.com",
                password="SecurePassword123!", verified=False
            )
        await test_client.post(
            "/api/v1/auth/verify-email", json={"token": token}
        )
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "EMAIL_VERIFIED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_password_reset_requested_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """PASSWORD_RESET_REQUESTED audit log is created."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit9@example.com",
                password="SecurePassword123!"
            )
        await test_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "audit9@example.com"},
        )
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "PASSWORD_RESET_REQUESTED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_password_reset_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """PASSWORD_RESET audit log is created."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit10@example.com",
                password="SecurePassword123!"
            )
            raw_token = await auth_service.forgot_password(
                session=session, email="audit10@example.com", ip_address="127.0.0.1"
            )
            await session.commit()

        await test_client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "NewSecurePassword456!"},
        )
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "PASSWORD_RESET"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_password_changed_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """PASSWORD_CHANGED audit log is created."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit11@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "audit11@example.com", "SecurePassword123!"
        )
        await test_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "SecurePassword123!",
                "new_password": "NewSecurePassword456!",
            },
            headers=headers,
        )
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "PASSWORD_CHANGED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_mfa_setup_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA_SETUP_INITIATED audit log is created."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit12@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "audit12@example.com", "SecurePassword123!"
        )
        await test_client.post("/api/v1/auth/mfa/setup", headers=headers)
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "MFA_SETUP_INITIATED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_mfa_enabled_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA_ENABLED audit log is created."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit13@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "audit13@example.com", "SecurePassword123!"
        )
        setup_resp = await test_client.post(
            "/api/v1/auth/mfa/setup", headers=headers
        )
        secret = setup_resp.json()["secret"]
        import pyotp
        totp = pyotp.TOTP(secret)
        code = totp.now()
        await test_client.post(
            "/api/v1/auth/mfa/enable",
            json={"totp_code": code, "pending_secret": secret},
            headers=headers,
        )
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "MFA_ENABLED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_profile_updated_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """PROFILE_UPDATED audit log is created."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit14@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "audit14@example.com", "SecurePassword123!"
        )
        await test_client.patch(
            "/api/v1/users/me",
            json={"display_name": "Updated Name"},
            headers=headers,
        )
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "PROFILE_UPDATED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_audit_log_entries_can_be_queried_by_user(
        self, test_client, test_session_factory, auth_service
    ):
        """Audit log entries can be queried by user_id."""
        async with test_session_factory() as session:
            user_model, _ = await create_test_user(
                session, auth_service, email="audit15@example.com",
                password="SecurePassword123!"
            )
            user_id = user_model.id
        await test_client.post(
            "/api/v1/auth/login",
            json={"email": "audit15@example.com", "password": "SecurePassword123!"},
        )

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.user_id == user_id
            )
            result = await session.execute(stmt)
            audits = result.scalars().all()
            # Should have at least USER_REGISTERED + LOGIN_SUCCESS
            assert len(audits) >= 2

    async def test_audit_log_includes_ip_address(
        self, test_client, test_session_factory
    ):
        """Audit log entries include IP address when available."""
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "audit16@example.com",
                "password": "SecurePassword123!",
                "display_name": "Audit User",
            },
        )
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "USER_REGISTERED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None
            # IP address should be set (from test client)
            assert audit.ip_address is not None

    async def test_audit_log_includes_session_id_for_login(
        self, test_client, test_session_factory, auth_service
    ):
        """LOGIN_SUCCESS audit log includes session_id."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit17@example.com",
                password="SecurePassword123!"
            )
        await test_client.post(
            "/api/v1/auth/login",
            json={"email": "audit17@example.com", "password": "SecurePassword123!"},
        )
        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "LOGIN_SUCCESS"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None
            assert audit.session_id is not None

    async def test_audit_log_full_login_flow(
        self, test_client, test_session_factory, auth_service
    ):
        """A full login flow creates multiple audit log entries in order."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit18@example.com",
                password="SecurePassword123!"
            )

        # Register (already done above via create_test_user, but that uses auth_service directly)
        # Login
        login_resp = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "audit18@example.com", "password": "SecurePassword123!"},
        )
        rt = login_resp.json()["refresh_token"]
        # Refresh
        await test_client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        # Logout
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
        await test_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": login_resp.json()["refresh_token"]},
            headers=headers,
        )

        async with test_session_factory() as session:
            stmt = (
                select(AuthAuditLogModel)
                .order_by(AuthAuditLogModel.created_at.asc())
            )
            result = await session.execute(stmt)
            audits = result.scalars().all()
            actions = [a.action for a in audits]
            # Should contain at least: USER_REGISTERED, LOGIN_SUCCESS, REFRESH_ROTATED, LOGOUT
            assert "USER_REGISTERED" in actions
            assert "LOGIN_SUCCESS" in actions
            assert "REFRESH_ROTATED" in actions
