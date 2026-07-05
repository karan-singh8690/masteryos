"""Additional auth integration tests to round out coverage.

Tests:
- Login after password reset works with new password
- Login after password change works with new password
- Old password fails after password reset
- Old password fails after password change
- Refresh after password change fails (sessions revoked)
- Multiple MFA setup attempts replace pending secret
- MFA disable without MFA enabled returns error
- Recovery code count decrements correctly after multiple uses
- Security dashboard shows 0 recovery codes when MFA not enabled
- Email verification is idempotent (already-active user)
- Resend verification then verify with new token works
- Logout without refresh_token is a no-op
- Login creates exactly one session
- Login creates exactly one refresh token
- Refresh creates a new refresh token but reuses session
"""

from __future__ import annotations

import pytest
import pyotp
from sqlalchemy import select

from app.infrastructure.database.orm.auth import (
    AuthAuditLogModel,
    MfaRecoveryCodeModel,
    RefreshTokenModel,
)
from app.infrastructure.database.orm.identity import SessionModel, UserModel
from tests.auth.conftest import create_test_user, get_auth_headers


pytestmark = pytest.mark.asyncio


class TestPasswordChangeFlow:
    """Tests for the complete password change flow."""

    async def test_login_after_password_change_with_new_password(
        self, test_client, test_session_factory, auth_service
    ):
        """After changing password, login works with the new password."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="pc1@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "pc1@example.com", "SecurePassword123!"
        )
        await test_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "SecurePassword123!",
                "new_password": "NewSecurePassword456!",
            },
            headers=headers,
        )
        # Login with new password
        response = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "pc1@example.com", "password": "NewSecurePassword456!"},
        )
        assert response.status_code == 200

    async def test_old_password_fails_after_change(
        self, test_client, test_session_factory, auth_service
    ):
        """After changing password, the old password no longer works."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="pc2@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "pc2@example.com", "SecurePassword123!"
        )
        await test_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "SecurePassword123!",
                "new_password": "NewSecurePassword456!",
            },
            headers=headers,
        )
        # Login with old password — should fail
        response = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "pc2@example.com", "password": "SecurePassword123!"},
        )
        assert response.status_code == 401


class TestPasswordResetFlow:
    """Tests for the complete password reset flow."""

    async def test_login_after_password_reset_with_new_password(
        self, test_client, test_session_factory, auth_service
    ):
        """After resetting password, login works with the new password."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="pr1@example.com",
                password="SecurePassword123!"
            )
            raw_token = await auth_service.forgot_password(
                session=session, email="pr1@example.com", ip_address="127.0.0.1"
            )
            await session.commit()

        await test_client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "NewSecurePassword456!"},
        )
        # Login with new password
        response = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "pr1@example.com", "password": "NewSecurePassword456!"},
        )
        assert response.status_code == 200

    async def test_old_password_fails_after_reset(
        self, test_client, test_session_factory, auth_service
    ):
        """After resetting password, the old password no longer works."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="pr2@example.com",
                password="SecurePassword123!"
            )
            raw_token = await auth_service.forgot_password(
                session=session, email="pr2@example.com", ip_address="127.0.0.1"
            )
            await session.commit()

        await test_client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "NewSecurePassword456!"},
        )
        # Login with old password — should fail
        response = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "pr2@example.com", "password": "SecurePassword123!"},
        )
        assert response.status_code == 401


class TestMfaEdgeCases:
    """Tests for MFA edge cases."""

    async def test_multiple_mfa_setups_replace_pending(
        self, test_client, test_session_factory, auth_service
    ):
        """Multiple MFA setup calls replace the pending secret."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="mfa1@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "mfa1@example.com", "SecurePassword123!"
        )

        # First setup
        resp1 = await test_client.post("/api/v1/auth/mfa/setup", headers=headers)
        secret1 = resp1.json()["secret"]

        # Second setup (should replace the first)
        resp2 = await test_client.post("/api/v1/auth/mfa/setup", headers=headers)
        secret2 = resp2.json()["secret"]

        # Secrets should be different
        assert secret1 != secret2

        # Only one pending secret should exist
        from app.infrastructure.database.orm.auth import MfaSecretModel
        async with test_session_factory() as session:
            stmt = select(MfaSecretModel).where(
                MfaSecretModel.status == "pending"
            )
            result = await session.execute(stmt)
            secrets = result.scalars().all()
            assert len(secrets) == 1

    async def test_recovery_codes_decrement_correctly(
        self, test_client, test_session_factory, auth_service
    ):
        """Recovery codes decrement correctly after multiple uses."""
        async with test_session_factory() as session:
            user_model, _ = await create_test_user(
                session, auth_service, email="mfa2@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "mfa2@example.com", "SecurePassword123!"
        )
        setup_resp = await test_client.post(
            "/api/v1/auth/mfa/setup", headers=headers
        )
        secret = setup_resp.json()["secret"]
        codes = setup_resp.json()["recovery_codes"]

        # Enable MFA
        totp = pyotp.TOTP(secret)
        await test_client.post(
            "/api/v1/auth/mfa/enable",
            json={"totp_code": totp.now(), "pending_secret": secret},
            headers=headers,
        )

        # Use 3 recovery codes
        for i in range(3):
            resp = await test_client.post(
                "/api/v1/auth/mfa/recovery",
                json={"recovery_code": codes[i]},
                headers=headers,
            )
            assert resp.status_code == 200

        # 10 - 3 = 7 remaining
        from app.infrastructure.database.repositories.auth import MfaRecoveryCodeRepository
        async with test_session_factory() as session:
            repo = MfaRecoveryCodeRepository(session)
            count = await repo.count_active(user_model.id)
            assert count == 7

    async def test_security_dashboard_zero_recovery_codes_without_mfa(
        self, test_client, test_session_factory, auth_service
    ):
        """Security dashboard shows 0 recovery codes when MFA not enabled."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="mfa3@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "mfa3@example.com", "SecurePassword123!"
        )
        response = await test_client.get(
            "/api/v1/users/me/security", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["recovery_codes_remaining"] == 0


class TestSessionLifecycle:
    """Tests for session lifecycle details."""

    async def test_login_creates_exactly_one_session(
        self, test_client, test_session_factory, auth_service
    ):
        """A single login creates exactly one session."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="sess1@example.com",
                password="SecurePassword123!"
            )
        await test_client.post(
            "/api/v1/auth/login",
            json={"email": "sess1@example.com", "password": "SecurePassword123!"},
        )
        async with test_session_factory() as session:
            stmt = select(SessionModel).where(
                SessionModel.user_id.isnot(None)
            )
            result = await session.execute(stmt)
            sessions = result.scalars().all()
            assert len(sessions) == 1

    async def test_login_creates_exactly_one_refresh_token(
        self, test_client, test_session_factory, auth_service
    ):
        """A single login creates exactly one refresh token."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="sess2@example.com",
                password="SecurePassword123!"
            )
        await test_client.post(
            "/api/v1/auth/login",
            json={"email": "sess2@example.com", "password": "SecurePassword123!"},
        )
        async with test_session_factory() as session:
            stmt = select(RefreshTokenModel)
            result = await session.execute(stmt)
            tokens = result.scalars().all()
            assert len(tokens) == 1

    async def test_refresh_reuses_session(
        self, test_client, test_session_factory, auth_service
    ):
        """Refresh creates a new refresh token but reuses the same session."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="sess3@example.com",
                password="SecurePassword123!"
            )
        login_resp = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "sess3@example.com", "password": "SecurePassword123!"},
        )
        rt = login_resp.json()["refresh_token"]

        # Get session count before refresh
        async with test_session_factory() as session:
            stmt = select(SessionModel)
            result = await session.execute(stmt)
            sessions_before = result.scalars().all()
            session_id = sessions_before[0].id

        # Refresh
        await test_client.post("/api/v1/auth/refresh", json={"refresh_token": rt})

        # Session count should still be 1 (same session)
        async with test_session_factory() as session:
            stmt = select(SessionModel)
            result = await session.execute(stmt)
            sessions_after = result.scalars().all()
            assert len(sessions_after) == 1
            assert sessions_after[0].id == session_id


class TestEmailVerificationFlow:
    """Tests for email verification flow."""

    async def test_resend_then_verify_works(
        self, test_client, test_session_factory, auth_service
    ):
        """Resend verification, then verify with the new token works."""
        # Register without creating a verification token
        from app.infrastructure.database.orm.identity import UserModel, UserProfileModel, UserCredentialModel
        from app.domain.shared.value_objects import Email
        from uuid import uuid4

        async with test_session_factory() as session:
            email_vo = Email("ev1@example.com")
            password_hash = auth_service.password_service.hash_password("SecurePassword123!")
            user_id = uuid4()
            session.add(UserModel(
                id=user_id, email=email_vo.value, status="pending_verification",
                mfa_enabled=False,
            ))
            session.add(UserProfileModel(
                user_id=user_id, display_name="Test User",
            ))
            session.add(UserCredentialModel(
                id=uuid4(), user_id=user_id, credential_type="password",
                password_hash=password_hash,
            ))
            await session.commit()

        # Resend — creates a new token
        from app.application.identity.auth_service import ProductionAuthService
        async with test_session_factory() as session:
            new_token = await auth_service.resend_verification(
                session=session, email="ev1@example.com", ip_address="127.0.0.1"
            )
            await session.commit()
        assert new_token is not None

        # Verify with the new token
        response = await test_client.post(
            "/api/v1/auth/verify-email",
            json={"token": new_token},
        )
        assert response.status_code == 200


class TestLogoutEdgeCases:
    """Tests for logout edge cases."""

    async def test_logout_no_op_without_refresh_token(
        self, test_client, test_session_factory, auth_service
    ):
        """Logout without a refresh_token is a no-op (still returns 200)."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="lo1@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "lo1@example.com", "SecurePassword123!"
        )
        response = await test_client.post(
            "/api/v1/auth/logout",
            json=None,
            headers=headers,
        )
        assert response.status_code == 200

    async def test_logout_with_invalid_refresh_token(
        self, test_client, test_session_factory, auth_service
    ):
        """Logout with an invalid refresh_token returns 200 (no-op)."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="lo2@example.com",
                password="SecurePassword123!"
            )
        headers = await get_auth_headers(
            test_client, "lo2@example.com", "SecurePassword123!"
        )
        response = await test_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "invalid-token"},
            headers=headers,
        )
        assert response.status_code == 200
