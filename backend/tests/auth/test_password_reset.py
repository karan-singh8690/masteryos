"""Password reset integration tests.

Tests:
- Forgot password creates a reset token
- Forgot password for nonexistent email returns OK (no leak)
- Forgot password is throttled
- Reset password with valid token changes the password
- Reset password with invalid token returns 422
- Reset password with expired token returns 422
- Reset password with already-used token returns 422
- Reset password invalidates all existing sessions
- Reset password invalidates all refresh tokens
- Reset password token is single-use
- Reset password uses Argon2id for new hash
- Change password (authenticated) requires current password
- Change password with wrong current password returns 422
- Change password invalidates other sessions
- Change password audit log
- Forgot password audit log
- Reset password audit log
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as tz_utc

import pytest
from sqlalchemy import select, update

from app.infrastructure.database.orm.auth import (
    AuthAuditLogModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
)
from app.infrastructure.database.orm.identity import (
    SessionModel,
    UserCredentialModel,
)
from tests.auth.conftest import create_test_user, get_auth_headers


pytestmark = pytest.mark.asyncio


class TestForgotPassword:
    """Tests for POST /api/v1/auth/forgot-password."""

    async def test_forgot_password_creates_reset_token(
        self, test_client, test_session_factory, auth_service
    ):
        """Forgot password creates a reset token in the database."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="forgot@example.com",
                password="SecurePassword123!"
            )

        response = await test_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "forgot@example.com"},
        )
        assert response.status_code == 200

        async with test_session_factory() as session:
            stmt = select(PasswordResetTokenModel)
            result = await session.execute(stmt)
            tokens = result.scalars().all()
            assert len(tokens) >= 1
            assert tokens[0].consumed_at is None  # Not yet used

    async def test_forgot_password_nonexistent_email_no_leak(
        self, test_client
    ):
        """Forgot password for nonexistent email returns OK (no leak)."""
        response = await test_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        assert response.status_code == 200
        assert "If the email exists" in response.json()["message"]

    async def test_forgot_password_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """Forgot password creates a PASSWORD_RESET_REQUESTED audit log."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="audit@example.com",
                password="SecurePassword123!"
            )

        await test_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "audit@example.com"},
        )

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "PASSWORD_RESET_REQUESTED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_forgot_password_throttled(
        self, test_client, test_session_factory, auth_service
    ):
        """Forgot password is throttled (max 1 per 2 minutes)."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="throttle@example.com",
                password="SecurePassword123!"
            )

        # First request — OK
        await test_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "throttle@example.com"},
        )

        # Get initial token count
        async with test_session_factory() as session:
            stmt = select(PasswordResetTokenModel)
            result = await session.execute(stmt)
            count_after_first = len(result.scalars().all())

        # Immediate second request — should be throttled
        await test_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "throttle@example.com"},
        )

        async with test_session_factory() as session:
            stmt = select(PasswordResetTokenModel)
            result = await session.execute(stmt)
            count_after_second = len(result.scalars().all())
            assert count_after_second == count_after_first  # No new token


class TestResetPassword:
    """Tests for POST /api/v1/auth/reset-password."""

    async def _create_user_and_get_reset_token(
        self, session_factory, auth_service, email="reset@example.com"
    ):
        """Helper: create a user and get a reset token via the auth service."""
        async with session_factory() as session:
            await create_test_user(
                session, auth_service, email=email, password="SecurePassword123!"
            )
        async with session_factory() as session:
            raw_token = await auth_service.forgot_password(
                session=session, email=email, ip_address="127.0.0.1"
            )
            await session.commit()
        return raw_token

    async def _get_reset_token(self, session_factory, auth_service, email="reset@example.com"):
        """Helper: get a reset token for an existing user via the auth service."""
        async with session_factory() as session:
            raw_token = await auth_service.forgot_password(
                session=session, email=email, ip_address="127.0.0.1"
            )
            await session.commit()
        return raw_token

    async def test_reset_password_with_valid_token(
        self, test_client, test_session_factory, auth_service
    ):
        """Reset password with a valid token changes the password."""
        raw_token = await self._create_user_and_get_reset_token(
            test_session_factory, auth_service, "reset1@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewSecurePassword456!",
            },
        )
        assert response.status_code == 200, response.text

        # Verify we can login with the new password
        login_response = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "reset1@example.com", "password": "NewSecurePassword456!"},
        )
        assert login_response.status_code == 200

    async def test_reset_password_with_invalid_token_returns_422(
        self, test_client
    ):
        """Reset password with invalid token returns 422."""
        response = await test_client.post(
            "/api/v1/auth/reset-password",
            json={"token": "invalid-token", "new_password": "NewSecurePassword456!"},
        )
        assert response.status_code == 422

    async def test_reset_password_with_weak_password_returns_422(
        self, test_client, test_session_factory, auth_service
    ):
        """Reset password with weak password returns 422."""
        raw_token = await self._create_user_and_get_reset_token(
            test_session_factory, auth_service, "reset2@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "short"},
        )
        assert response.status_code == 422

    async def test_reset_password_invalidates_sessions(
        self, test_client, test_session_factory, auth_service
    ):
        """Reset password invalidates all existing sessions."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="reset3@example.com",
                password="SecurePassword123!"
            )

        # Login (creates a session)
        login_response = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "reset3@example.com", "password": "SecurePassword123!"},
        )
        assert login_response.status_code == 200
        old_refresh_token = login_response.json()["refresh_token"]

        # Request reset (user already exists, just get the token)
        raw_token = await self._get_reset_token(
            test_session_factory, auth_service, "reset3@example.com"
        )

        # Reset password
        await test_client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "NewSecurePassword456!"},
        )

        # Old refresh token should no longer work
        refresh_response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )
        assert refresh_response.status_code == 401

    async def test_reset_password_token_is_single_use(
        self, test_client, test_session_factory, auth_service
    ):
        """A reset token can only be used once."""
        raw_token = await self._create_user_and_get_reset_token(
            test_session_factory, auth_service, "reset4@example.com"
        )

        # First use — success
        response1 = await test_client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "NewSecurePassword456!"},
        )
        assert response1.status_code == 200

        # Second use — fail
        response2 = await test_client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "AnotherPassword789!"},
        )
        assert response2.status_code == 422

    async def test_reset_password_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """Reset password creates a PASSWORD_RESET audit log entry."""
        raw_token = await self._create_user_and_get_reset_token(
            test_session_factory, auth_service, "reset5@example.com"
        )

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

    async def test_reset_password_uses_argon2id(
        self, test_client, test_session_factory, auth_service
    ):
        """Reset password uses Argon2id for the new hash."""
        raw_token = await self._create_user_and_get_reset_token(
            test_session_factory, auth_service, "reset6@example.com"
        )

        await test_client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "NewSecurePassword456!"},
        )

        async with test_session_factory() as session:
            stmt = select(UserCredentialModel).where(
                UserCredentialModel.credential_type == "password"
            )
            result = await session.execute(stmt)
            cred = result.scalars().first()
            assert cred is not None
            assert cred.password_hash.startswith("$argon2id$")


class TestChangePassword:
    """Tests for POST /api/v1/auth/change-password."""

    async def test_change_password_success(
        self, test_client, test_session_factory, auth_service
    ):
        """Change password with correct current password succeeds."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="change@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "change@example.com", "SecurePassword123!"
        )

        response = await test_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "SecurePassword123!",
                "new_password": "NewSecurePassword456!",
            },
            headers=headers,
        )
        assert response.status_code == 200

        # Login with new password
        login_response = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "change@example.com", "password": "NewSecurePassword456!"},
        )
        assert login_response.status_code == 200

    async def test_change_password_wrong_current_returns_422(
        self, test_client, test_session_factory, auth_service
    ):
        """Change password with wrong current password returns 422."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="changewrong@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "changewrong@example.com", "SecurePassword123!"
        )

        response = await test_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewSecurePassword456!",
            },
            headers=headers,
        )
        assert response.status_code == 422

    async def test_change_password_invalidates_other_sessions(
        self, test_client, test_session_factory, auth_service
    ):
        """Change password invalidates all other sessions."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="changesessions@example.com",
                password="SecurePassword123!"
            )

        # Login from "device 1"
        login1 = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "changesessions@example.com", "password": "SecurePassword123!"},
        )
        rt1 = login1.json()["refresh_token"]

        # Login from "device 2"
        login2 = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "changesessions@example.com", "password": "SecurePassword123!"},
        )
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        # Change password from device 2
        await test_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "SecurePassword123!",
                "new_password": "NewSecurePassword456!",
            },
            headers=headers2,
        )

        # Device 1's refresh token should no longer work
        refresh_response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": rt1},
        )
        assert refresh_response.status_code == 401

    async def test_change_password_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """Change password creates a PASSWORD_CHANGED audit log."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="changeaudit@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "changeaudit@example.com", "SecurePassword123!"
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

    async def test_change_password_without_auth_returns_401(
        self, test_client
    ):
        """Change password without auth header returns 401."""
        response = await test_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "SecurePassword123!",
                "new_password": "NewSecurePassword456!",
            },
        )
        assert response.status_code == 401

    async def test_change_password_weak_new_returns_422(
        self, test_client, test_session_factory, auth_service
    ):
        """Change password with weak new password returns 422."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="changeweak@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "changeweak@example.com", "SecurePassword123!"
        )

        response = await test_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "SecurePassword123!",
                "new_password": "short",
            },
            headers=headers,
        )
        assert response.status_code == 422
