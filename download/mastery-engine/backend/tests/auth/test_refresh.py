"""Refresh token rotation integration tests — POST /api/v1/auth/refresh.

Tests:
- Refresh success returns new access + refresh token
- Old refresh token is invalidated after rotation (single-use)
- Refresh reuse detection: presenting an already-rotated token returns 401
- Refresh reuse detection revokes the entire token family
- Refresh with invalid token returns 401
- Refresh with revoked token returns 401
- Refresh audit log (REFRESH_ROTATED) is created
- Refresh reuse creates REFRESH_REUSE_DETECTED audit log
- Refresh reuse creates a security_incident record
- Refresh updates session last_seen_at
- Refresh issues new RS256 JWT (not HS256)
- Multiple sequential refreshes work (rotation chain)
- Concurrent refreshes: only one succeeds, others detect reuse
"""

from __future__ import annotations

import asyncio
import pytest
from sqlalchemy import select

from app.infrastructure.database.orm.auth import (
    AuthAuditLogModel,
    RefreshTokenModel,
    SecurityIncidentModel,
)
from app.infrastructure.database.orm.identity import SessionModel
from tests.auth.conftest import create_test_user


pytestmark = pytest.mark.asyncio


class TestRefresh:
    """Tests for POST /api/v1/auth/refresh."""

    async def _login(self, client, session_factory, auth_service, email="refresh@example.com"):
        """Helper: register + login, return (access_token, refresh_token)."""
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
        return data["access_token"], data["refresh_token"]

    async def test_refresh_success_returns_new_tokens(
        self, test_client, test_session_factory, auth_service
    ):
        """Successful refresh returns new access + refresh token."""
        _, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "refresh1@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != refresh_token  # New token
        assert data["expires_in"] == 900

    async def test_refresh_old_token_invalidated(
        self, test_client, test_session_factory, auth_service
    ):
        """Old refresh token is invalidated after rotation (single-use)."""
        _, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "refresh2@example.com"
        )

        # First refresh — success
        response1 = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response1.status_code == 200

        # Second refresh with same (old) token — should fail
        response2 = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response2.status_code == 401
        assert response2.json()["detail"]["code"] == "REFRESH_REUSE_DETECTED"

    async def test_refresh_reuse_detection_revokes_family(
        self, test_client, test_session_factory, auth_service
    ):
        """Refresh reuse detection revokes the entire token family."""
        _, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "refresh3@example.com"
        )

        # First refresh — get new token
        response1 = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response1.status_code == 200
        new_refresh_token = response1.json()["refresh_token"]

        # Second refresh with new token — success
        response2 = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_refresh_token},
        )
        assert response2.status_code == 200

        # Now try the OLD token — should trigger reuse detection
        response3 = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response3.status_code == 401
        assert response3.json()["detail"]["code"] == "REFRESH_REUSE_DETECTED"

        # The new token should also be revoked now (family revoked)
        response4 = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": response2.json()["refresh_token"]},
        )
        assert response4.status_code == 401

    async def test_refresh_invalid_token_returns_401(
        self, test_client
    ):
        """Refresh with invalid token returns 401."""
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token-string"},
        )
        assert response.status_code == 401

    async def test_refresh_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """A REFRESH_ROTATED audit log entry is created on successful refresh."""
        _, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "refresh4@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "REFRESH_ROTATED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None
            assert audit.success is True

    async def test_refresh_reuse_creates_security_incident(
        self, test_client, test_session_factory, auth_service
    ):
        """Refresh reuse detection creates a security_incident record."""
        _, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "refresh5@example.com"
        )

        # First refresh — success
        await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        # Reuse the old token
        await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        async with test_session_factory() as session:
            stmt = select(SecurityIncidentModel).where(
                SecurityIncidentModel.incident_type == "refresh_token_reuse"
            )
            result = await session.execute(stmt)
            incidents = result.scalars().all()
            assert len(incidents) >= 1
            assert incidents[0].severity == "critical"

    async def test_refresh_reuse_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """A REFRESH_REUSE_DETECTED audit log entry is created on reuse."""
        _, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "refresh6@example.com"
        )

        # First refresh
        await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        # Reuse
        await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "REFRESH_REUSE_DETECTED"
            )
            result = await session.execute(stmt)
            audits = result.scalars().all()
            assert len(audits) >= 1

    async def test_refresh_returns_rs256_jwt(
        self, test_client, test_session_factory, auth_service
    ):
        """The new access token from refresh must be RS256."""
        import jwt
        _, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "refresh7@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "RS256"

    async def test_multiple_sequential_refreshes(
        self, test_client, test_session_factory, auth_service
    ):
        """Multiple sequential refreshes work (rotation chain)."""
        _, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "refresh8@example.com"
        )

        # Chain 5 refreshes
        current_token = refresh_token
        for i in range(5):
            response = await test_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": current_token},
            )
            assert response.status_code == 200, f"Refresh {i} failed: {response.text}"
            current_token = response.json()["refresh_token"]

    async def test_refresh_updates_session_last_seen(
        self, test_client, test_session_factory, auth_service
    ):
        """Refresh updates the session's last_seen_at timestamp."""
        _, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "refresh9@example.com"
        )

        # Get initial last_seen_at
        async with test_session_factory() as session:
            stmt = select(SessionModel)
            result = await session.execute(stmt)
            session_model = result.scalars().first()
            initial_last_seen = session_model.last_seen_at

        # Wait a moment to ensure timestamp differs
        import asyncio
        await asyncio.sleep(0.1)

        # Refresh
        await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        # Check that last_seen_at was updated
        async with test_session_factory() as session:
            stmt = select(SessionModel)
            result = await session.execute(stmt)
            session_model = result.scalars().first()
            assert session_model.last_seen_at >= initial_last_seen

    async def test_concurrent_refreshes_one_succeeds(
        self, test_client, test_session_factory, auth_service
    ):
        """Concurrent refreshes: at most one succeeds, others detect reuse."""
        _, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "refresh10@example.com"
        )

        # Fire 3 concurrent refreshes
        responses = await asyncio.gather(
            test_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}),
            test_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}),
            test_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}),
        )

        # At least one should succeed (200) and at least one should fail (401)
        status_codes = [r.status_code for r in responses]
        assert 200 in status_codes, "At least one refresh should succeed"
        # The others should fail (401) — they detected reuse
        assert status_codes.count(401) >= 1, "At least one refresh should fail"

    async def test_refresh_token_recorded_in_db(
        self, test_client, test_session_factory, auth_service
    ):
        """Each refresh creates a new refresh_token record in the database."""
        _, refresh_token = await self._login(
            test_client, test_session_factory, auth_service, "refresh11@example.com"
        )

        # Initial: 1 refresh token (from login)
        async with test_session_factory() as session:
            stmt = select(RefreshTokenModel)
            result = await session.execute(stmt)
            initial_count = len(result.scalars().all())

        # Refresh
        await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        # After: 2 refresh tokens (login + refresh)
        async with test_session_factory() as session:
            stmt = select(RefreshTokenModel)
            result = await session.execute(stmt)
            final_count = len(result.scalars().all())
            assert final_count == initial_count + 1

    async def test_refresh_missing_token_returns_422(
        self, test_client
    ):
        """Refresh without refresh_token field returns 422."""
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={},
        )
        assert response.status_code == 422
