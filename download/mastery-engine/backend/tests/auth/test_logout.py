"""Logout integration tests — POST /api/v1/auth/logout and /logout-all.

Tests:
- Logout (current device) revokes the current session
- Logout invalidates the refresh token
- Logout creates LOGOUT audit log
- Logout without refresh token still works (no-op)
- Logout-all revokes every session for the user
- Logout-all invalidates every refresh token
- Logout-all creates LOGOUT_ALL audit log
- Logout-all returns count of revoked sessions
- After logout, refresh token no longer works
- After logout-all, all refresh tokens no longer work
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.infrastructure.database.orm.auth import (
    AuthAuditLogModel,
    RefreshTokenModel,
)
from app.infrastructure.database.orm.identity import SessionModel
from tests.auth.conftest import create_test_user, get_auth_headers


pytestmark = pytest.mark.asyncio


class TestLogout:
    """Tests for POST /api/v1/auth/logout."""

    async def _login(self, client, session_factory, auth_service, email="logout@example.com"):
        """Helper: register + login, return (headers, refresh_token)."""
        async with session_factory() as session:
            await create_test_user(
                session, auth_service, email=email, password="SecurePassword123!"
            )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecurePassword123!"},
        )
        assert response.status_code == 200
        data = response.json()
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        return headers, data["refresh_token"]

    async def test_logout_revokes_session(
        self, test_client, test_session_factory, auth_service
    ):
        """Logout revokes the current session."""
        headers, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "logout1@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=headers,
        )
        assert response.status_code == 200

        # Verify session is revoked
        async with test_session_factory() as session:
            stmt = select(SessionModel)
            result = await session.execute(stmt)
            sessions = result.scalars().all()
            assert len(sessions) >= 1
            assert all(s.revoked_at is not None for s in sessions)

    async def test_logout_invalidates_refresh_token(
        self, test_client, test_session_factory, auth_service
    ):
        """Logout invalidates the refresh token."""
        headers, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "logout2@example.com"
        )

        # Logout
        await test_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=headers,
        )

        # Try to refresh with the logged-out token — should fail
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 401

    async def test_logout_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """Logout creates a LOGOUT audit log entry."""
        headers, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "logout3@example.com"
        )

        await test_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=headers,
        )

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "LOGOUT"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None
            assert audit.success is True

    async def test_logout_without_refresh_token(
        self, test_client, test_session_factory, auth_service
    ):
        """Logout without a refresh token still succeeds (no-op)."""
        headers, _ = await self._login(
            test_client, test_session_factory, auth_service, "logout4@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/logout",
            json=None,
            headers=headers,
        )
        assert response.status_code == 200

    async def test_logout_without_auth_returns_401(
        self, test_client
    ):
        """Logout without auth header returns 401."""
        response = await test_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "some-token"},
        )
        assert response.status_code == 401


class TestLogoutAll:
    """Tests for POST /api/v1/auth/logout-all."""

    async def _login_multiple_devices(
        self, client, session_factory, auth_service, email="logoutall@example.com"
    ):
        """Login the same user from multiple 'devices' (multiple login calls)."""
        async with session_factory() as session:
            await create_test_user(
                session, auth_service, email=email, password="SecurePassword123!"
            )

        # First login
        response1 = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecurePassword123!"},
        )
        # Second login (different "device")
        response2 = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecurePassword123!"},
        )

        return (
            {"Authorization": f"Bearer {response1.json()['access_token']}"},
            response1.json()["refresh_token"],
            response2.json()["refresh_token"],
        )

    async def test_logout_all_revokes_every_session(
        self, test_client, test_session_factory, auth_service
    ):
        """Logout-all revokes every session for the user."""
        headers, rt1, rt2 = await self._login_multiple_devices(
            test_client, test_session_factory, auth_service, "logoutall1@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/logout-all",
            headers=headers,
        )
        assert response.status_code == 200

        # All sessions should be revoked
        async with test_session_factory() as session:
            stmt = select(SessionModel)
            result = await session.execute(stmt)
            sessions = result.scalars().all()
            assert len(sessions) >= 2
            assert all(s.revoked_at is not None for s in sessions)

    async def test_logout_all_invalidates_all_refresh_tokens(
        self, test_client, test_session_factory, auth_service
    ):
        """Logout-all invalidates every refresh token."""
        headers, rt1, rt2 = await self._login_multiple_devices(
            test_client, test_session_factory, auth_service, "logoutall2@example.com"
        )

        await test_client.post(
            "/api/v1/auth/logout-all",
            headers=headers,
        )

        # Both refresh tokens should fail
        r1 = await test_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": rt1}
        )
        r2 = await test_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": rt2}
        )
        assert r1.status_code == 401
        assert r2.status_code == 401

    async def test_logout_all_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """Logout-all creates a LOGOUT_ALL audit log entry."""
        headers, _, _ = await self._login_multiple_devices(
            test_client, test_session_factory, auth_service, "logoutall3@example.com"
        )

        await test_client.post(
            "/api/v1/auth/logout-all",
            headers=headers,
        )

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "LOGOUT_ALL"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_logout_all_returns_count(
        self, test_client, test_session_factory, auth_service
    ):
        """Logout-all returns the count of revoked sessions."""
        headers, _, _ = await self._login_multiple_devices(
            test_client, test_session_factory, auth_service, "logoutall4@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/logout-all",
            headers=headers,
        )
        assert response.status_code == 200
        # The message includes the count
        assert "Logged out from" in response.json()["message"]
        assert "2" in response.json()["message"]  # 2 devices

    async def test_logout_all_without_auth_returns_401(
        self, test_client
    ):
        """Logout-all without auth header returns 401."""
        response = await test_client.post("/api/v1/auth/logout-all")
        assert response.status_code == 401
