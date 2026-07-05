"""User profile + security dashboard integration tests.

Tests:
- GET /users/me returns user + profile + roles + permissions
- GET /users/me requires authentication
- PATCH /users/me updates display_name
- PATCH /users/me updates timezone
- PATCH /users/me updates locale
- PATCH /users/me updates avatar_url
- PATCH /users/me updates preferences
- PATCH /users/me creates PROFILE_UPDATED audit log
- PATCH /users/me requires authentication
- GET /users/me/security returns security dashboard
- GET /users/me/security includes active sessions
- GET /users/me/security includes MFA status
- GET /users/me/security includes recovery codes count
- GET /users/me/security includes recent events
- GET /users/me/security requires authentication
- JWT validation: expired token returns 401
- JWT validation: invalid signature returns 401
- JWT validation: HS256 token rejected (only RS256 allowed)
- JWT validation: missing token returns 401
- JWT validation: malformed token returns 401
"""

from __future__ import annotations

import time
import jwt as jwt_lib
import pytest
from sqlalchemy import select

from app.infrastructure.database.orm.auth import AuthAuditLogModel
from app.infrastructure.database.orm.identity import UserProfileModel
from tests.auth.conftest import create_test_user, get_auth_headers


pytestmark = pytest.mark.asyncio


class TestGetCurrentUser:
    """Tests for GET /api/v1/users/me."""

    async def test_get_current_user_returns_user_and_profile(
        self, test_client, test_session_factory, auth_service
    ):
        """GET /users/me returns the user's identity + profile."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="me@example.com",
                password="SecurePassword123!", display_name="My Name"
            )

        headers = await get_auth_headers(
            test_client, "me@example.com", "SecurePassword123!"
        )

        response = await test_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["user"]["email"] == "me@example.com"
        assert data["profile"]["display_name"] == "My Name"
        assert "roles" in data
        assert "permissions" in data
        assert "learner" in data["roles"]

    async def test_get_current_user_requires_auth(self, test_client):
        """GET /users/me without auth returns 401."""
        response = await test_client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_get_current_user_includes_email_verified_at(
        self, test_client, test_session_factory, auth_service
    ):
        """GET /users/me includes email_verified_at."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="verified@example.com",
                password="SecurePassword123!", verified=True
            )

        headers = await get_auth_headers(
            test_client, "verified@example.com", "SecurePassword123!"
        )

        response = await test_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["user"]["email_verified_at"] is not None

    async def test_get_current_user_includes_mfa_enabled(
        self, test_client, test_session_factory, auth_service
    ):
        """GET /users/me includes mfa_enabled flag."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="mfacheck@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "mfacheck@example.com", "SecurePassword123!"
        )

        response = await test_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["user"]["mfa_enabled"] is False

    async def test_get_current_user_includes_permissions(
        self, test_client, test_session_factory, auth_service
    ):
        """GET /users/me includes permissions derived from roles."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="perms@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "perms@example.com", "SecurePassword123!"
        )

        response = await test_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        permissions = response.json()["permissions"]
        # Learner role should have at least these permissions
        assert "identity:user:read_self" in permissions
        assert "identity:user:update_self" in permissions


class TestUpdateProfile:
    """Tests for PATCH /api/v1/users/me."""

    async def test_update_profile_display_name(
        self, test_client, test_session_factory, auth_service
    ):
        """PATCH /users/me updates display_name."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="update@example.com",
                password="SecurePassword123!", display_name="Old Name"
            )

        headers = await get_auth_headers(
            test_client, "update@example.com", "SecurePassword123!"
        )

        response = await test_client.patch(
            "/api/v1/users/me",
            json={"display_name": "New Name"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["profile"]["display_name"] == "New Name"

    async def test_update_profile_timezone(
        self, test_client, test_session_factory, auth_service
    ):
        """PATCH /users/me updates timezone."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="tz@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "tz@example.com", "SecurePassword123!"
        )

        response = await test_client.patch(
            "/api/v1/users/me",
            json={"timezone": "America/New_York"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["profile"]["timezone"] == "America/New_York"

    async def test_update_profile_locale(
        self, test_client, test_session_factory, auth_service
    ):
        """PATCH /users/me updates locale."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="locale@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "locale@example.com", "SecurePassword123!"
        )

        response = await test_client.patch(
            "/api/v1/users/me",
            json={"locale": "fr-FR"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["profile"]["locale"] == "fr-FR"

    async def test_update_profile_avatar_url(
        self, test_client, test_session_factory, auth_service
    ):
        """PATCH /users/me updates avatar_url."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="avatar@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "avatar@example.com", "SecurePassword123!"
        )

        response = await test_client.patch(
            "/api/v1/users/me",
            json={"avatar_url": "https://example.com/avatar.png"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["profile"]["avatar_url"] == "https://example.com/avatar.png"

    async def test_update_profile_preferences(
        self, test_client, test_session_factory, auth_service
    ):
        """PATCH /users/me updates preferences."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="prefs@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "prefs@example.com", "SecurePassword123!"
        )

        response = await test_client.patch(
            "/api/v1/users/me",
            json={"preferences": {"theme": "dark", "notifications": True}},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["profile"]["preferences"]["theme"] == "dark"

    async def test_update_profile_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """PATCH /users/me creates a PROFILE_UPDATED audit log."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="auditprofile@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "auditprofile@example.com", "SecurePassword123!"
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

    async def test_update_profile_requires_auth(self, test_client):
        """PATCH /users/me without auth returns 401."""
        response = await test_client.patch(
            "/api/v1/users/me",
            json={"display_name": "New Name"},
        )
        assert response.status_code == 401


class TestSecurityDashboard:
    """Tests for GET /api/v1/users/me/security."""

    async def test_security_dashboard_returns_data(
        self, test_client, test_session_factory, auth_service
    ):
        """GET /users/me/security returns the security dashboard."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="dashboard@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "dashboard@example.com", "SecurePassword123!"
        )

        response = await test_client.get("/api/v1/users/me/security", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert "mfa_enabled" in data
        assert "email_verified" in data
        assert "active_sessions" in data
        assert "recovery_codes_remaining" in data
        assert "recent_security_events" in data

    async def test_security_dashboard_includes_active_sessions(
        self, test_client, test_session_factory, auth_service
    ):
        """Security dashboard includes the active session."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="sessions@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "sessions@example.com", "SecurePassword123!"
        )

        response = await test_client.get("/api/v1/users/me/security", headers=headers)
        assert response.status_code == 200
        sessions = response.json()["active_sessions"]
        assert len(sessions) >= 1
        assert "id" in sessions[0]
        assert "expires_at" in sessions[0]

    async def test_security_dashboard_includes_mfa_status(
        self, test_client, test_session_factory, auth_service
    ):
        """Security dashboard includes the MFA enabled flag."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="mfastatus@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "mfastatus@example.com", "SecurePassword123!"
        )

        response = await test_client.get("/api/v1/users/me/security", headers=headers)
        assert response.status_code == 200
        assert response.json()["mfa_enabled"] is False

    async def test_security_dashboard_includes_recovery_codes_count(
        self, test_client, test_session_factory, auth_service
    ):
        """Security dashboard includes recovery codes remaining count."""
        async with test_session_factory() as session:
            user_model, _ = await create_test_user(
                session, auth_service, email="recoverycount@example.com",
                password="SecurePassword123!"
            )
        # Login BEFORE enabling MFA
        headers = await get_auth_headers(
            test_client, "recoverycount@example.com", "SecurePassword123!"
        )
        async with test_session_factory() as session:
            setup = await auth_service.setup_mfa(
                session=session, user_id=user_model.id,
                user_email="recoverycount@example.com"
            )
            import pyotp
            totp = pyotp.TOTP(setup["secret"])
            code = totp.now()
            await auth_service.enable_mfa(
                session=session, user_id=user_model.id,
                totp_code=code, pending_secret=setup["secret"]
            )
            await session.commit()

        response = await test_client.get("/api/v1/users/me/security", headers=headers)
        assert response.status_code == 200
        assert response.json()["recovery_codes_remaining"] == 10

    async def test_security_dashboard_includes_recent_events(
        self, test_client, test_session_factory, auth_service
    ):
        """Security dashboard includes recent security events."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="events@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "events@example.com", "SecurePassword123!"
        )

        response = await test_client.get("/api/v1/users/me/security", headers=headers)
        assert response.status_code == 200
        events = response.json()["recent_security_events"]
        assert isinstance(events, list)
        # Should include the LOGIN_SUCCESS event
        assert any(e["action"] == "LOGIN_SUCCESS" for e in events)

    async def test_security_dashboard_requires_auth(self, test_client):
        """GET /users/me/security without auth returns 401."""
        response = await test_client.get("/api/v1/users/me/security")
        assert response.status_code == 401


class TestJwtValidation:
    """Tests for JWT validation in authentication."""

    async def test_expired_token_returns_401(
        self, test_client, test_session_factory, auth_service
    ):
        """An expired access token returns 401."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="expired@example.com",
                password="SecurePassword123!"
            )

        # Issue a token that expires in 1 second
        from app.presentation.dependencies import get_jwt_service
        from app.infrastructure.database.orm.identity import UserModel
        from sqlalchemy import select as sel

        async with test_session_factory() as session:
            stmt = sel(UserModel).where(UserModel.email == "expired@example.com")
            user = (await session.execute(stmt)).scalar_one()

        jwt_service = get_jwt_service()
        token = jwt_service.issue_access_token(
            user_id=user.id, roles=["learner"], expires_in=1
        )

        # Wait for it to expire (need to exceed clock skew tolerance too)
        time.sleep(35)  # 30s clock skew + 5s buffer

        response = await test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    async def test_invalid_signature_token_returns_401(
        self, test_client, test_session_factory, auth_service
    ):
        """A token signed with a different key returns 401."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="sig@example.com",
                password="SecurePassword123!"
            )

        # Create a token signed with a different key
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import jwt as jwt_lib

        # Generate a different RSA key
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Issue a token with this different key
        payload = {
            "sub": str(__import__("uuid").uuid4()),
            "iss": "https://api.masteryengine.com",
            "aud": "mastery-engine-api",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "jti": "test",
            "typ": "access",
            "ver": 1,
            "scope": "learner",
        }
        headers = {"kid": "different-key", "alg": "RS256", "typ": "JWT"}
        token = jwt_lib.encode(payload, pem, algorithm="RS256", headers=headers)

        response = await test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    async def test_hs256_token_rejected(
        self, test_client, test_session_factory, auth_service
    ):
        """An HS256 token is rejected (only RS256 allowed)."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="hs256@example.com",
                password="SecurePassword123!"
            )

        # Create an HS256 token
        token = jwt_lib.encode(
            {
                "sub": str(__import__("uuid").uuid4()),
                "iss": "https://api.masteryengine.com",
                "aud": "mastery-engine-api",
                "iat": int(time.time()),
                "exp": int(time.time()) + 3600,
                "jti": "test",
                "typ": "access",
                "ver": 1,
                "scope": "learner",
            },
            "some-secret-key",
            algorithm="HS256",
        )

        response = await test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    async def test_missing_token_returns_401(self, test_client):
        """A request without Authorization header returns 401."""
        response = await test_client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_malformed_token_returns_401(self, test_client):
        """A malformed token returns 401."""
        response = await test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer not-a-jwt"},
        )
        assert response.status_code == 401

    async def test_wrong_scheme_returns_401(self, test_client):
        """A non-Bearer authorization scheme returns 401."""
        response = await test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Basic some-token"},
        )
        assert response.status_code == 401

    async def test_empty_bearer_returns_401(self, test_client):
        """An empty Bearer token returns 401."""
        response = await test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 401
