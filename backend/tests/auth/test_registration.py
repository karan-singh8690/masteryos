"""Registration integration tests — POST /api/v1/auth/register.

Tests:
- Successful registration returns 201 with access + refresh token
- Duplicate email returns 409
- Weak password returns 422
- Invalid email returns 422
- Missing required fields return 422
- Verification token is created (not returned in response)
- Audit log entry is created
- Argon2id hash is used (NOT SHA256)
- Returned access token is RS256 (NOT HS256)
- Returned user has PENDING_VERIFICATION status
- Can register with timezone + locale
"""

from __future__ import annotations

import hashlib
import jwt
import pytest
from sqlalchemy import select

from app.infrastructure.database.orm.auth import (
    AuthAuditLogModel,
    VerificationTokenModel,
)
from app.infrastructure.database.orm.identity import (
    UserCredentialModel,
    UserModel,
)
from tests.auth.conftest import create_test_user


pytestmark = pytest.mark.asyncio


class TestRegistration:
    """Tests for POST /api/v1/auth/register."""

    async def test_register_success_returns_201(
        self, test_client, test_session_factory
    ):
        """Successful registration returns 201 with access + refresh token."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "display_name": "New User",
                "timezone": "UTC",
                "locale": "en-US",
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["expires_in"] == 900
        assert data["token_type"] == "Bearer"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["status"] == "pending_verification"
        assert data["user"]["mfa_enabled"] is False
        assert data["user"]["email_verified_at"] is None

    async def test_register_returns_rs256_jwt(self, test_client):
        """The access token must be RS256 (asymmetric), not HS256."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "rs256@example.com",
                "password": "SecurePassword123!",
                "display_name": "RS256 User",
            },
        )
        assert response.status_code == 201
        token = response.json()["access_token"]

        # Decode the header (no signature verification)
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "RS256", f"Expected RS256, got {header['alg']}"
        assert "kid" in header

    async def test_register_uses_argon2id_password_hash(
        self, test_client, test_session_factory
    ):
        """The stored password hash must be Argon2id format, not SHA256."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "argon@example.com",
                "password": "SecurePassword123!",
                "display_name": "Argon User",
            },
        )
        assert response.status_code == 201

        # Verify the stored hash is Argon2id format
        async with test_session_factory() as session:
            stmt = select(UserCredentialModel).where(
                UserCredentialModel.credential_type == "password"
            )
            result = await session.execute(stmt)
            cred = result.scalars().first()
            assert cred is not None
            # Argon2id PHC format: $argon2id$v=19$m=...,t=...,p=...$salt$hash
            assert cred.password_hash.startswith("$argon2id$"), (
                f"Expected Argon2id hash, got: {cred.password_hash[:30]}..."
            )
            # Must NOT be the old SHA256 format (argon2id$salt$sha256hash)
            assert cred.password_hash.count("$") != 2, (
                "Old SHA256 format detected (argon2id$salt$hash)"
            )

    async def test_register_creates_verification_token(
        self, test_client, test_session_factory
    ):
        """A verification token is created in the database (not returned)."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "verify@example.com",
                "password": "SecurePassword123!",
                "display_name": "Verify User",
            },
        )
        assert response.status_code == 201
        # The token is NOT in the response (security: don't expose)
        assert "verification_token" not in response.json()

        # But it IS in the database
        async with test_session_factory() as session:
            stmt = select(VerificationTokenModel).where(
                VerificationTokenModel.token_type == "email_verification"
            )
            result = await session.execute(stmt)
            tokens = result.scalars().all()
            assert len(tokens) >= 1
            assert tokens[0].consumed_at is None  # Not yet used

    async def test_register_creates_audit_log(
        self, test_client, test_session_factory
    ):
        """A USER_REGISTERED audit log entry is created."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "audit@example.com",
                "password": "SecurePassword123!",
                "display_name": "Audit User",
            },
        )
        assert response.status_code == 201

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "USER_REGISTERED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None
            assert audit.success is True
            assert audit.details.get("email") == "audit@example.com"

    async def test_register_duplicate_email_returns_409(
        self, test_client, test_session_factory, auth_service
    ):
        """Registering with an existing email returns 409."""
        # First registration
        async with test_session_factory() as session:
            await create_test_user(session, auth_service, email="dup@example.com")

        # Second registration with same email
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@example.com",
                "password": "SecurePassword123!",
                "display_name": "Dup User",
            },
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "EMAIL_ALREADY_REGISTERED"

    async def test_register_weak_password_returns_422(self, test_client):
        """Password shorter than 12 characters returns 422."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "short",  # Too short
                "display_name": "Weak User",
            },
        )
        assert response.status_code == 422

    async def test_register_invalid_email_returns_422(self, test_client):
        """Invalid email format returns 422."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePassword123!",
                "display_name": "Invalid User",
            },
        )
        assert response.status_code == 422

    async def test_register_missing_email_returns_422(self, test_client):
        """Missing email field returns 422."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "password": "SecurePassword123!",
                "display_name": "No Email",
            },
        )
        assert response.status_code == 422

    async def test_register_missing_password_returns_422(self, test_client):
        """Missing password field returns 422."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "nopass@example.com",
                "display_name": "No Pass",
            },
        )
        assert response.status_code == 422

    async def test_register_missing_display_name_returns_422(self, test_client):
        """Missing display_name field returns 422."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "noname@example.com",
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 422

    async def test_register_user_status_is_pending_verification(
        self, test_client, test_session_factory
    ):
        """Newly registered user has 'pending_verification' status."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "pending@example.com",
                "password": "SecurePassword123!",
                "display_name": "Pending User",
            },
        )
        assert response.status_code == 201
        assert response.json()["user"]["status"] == "pending_verification"

    async def test_register_user_email_verified_at_is_none(
        self, test_client
    ):
        """Newly registered user has email_verified_at = None."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "unverified@example.com",
                "password": "SecurePassword123!",
                "display_name": "Unverified User",
            },
        )
        assert response.status_code == 201
        assert response.json()["user"]["email_verified_at"] is None

    async def test_register_creates_user_profile(
        self, test_client, test_session_factory
    ):
        """A user profile is created with the display_name + defaults."""
        from app.infrastructure.database.orm.identity import UserProfileModel

        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "profile@example.com",
                "password": "SecurePassword123!",
                "display_name": "Profile User",
                "timezone": "America/New_York",
                "locale": "fr-FR",
            },
        )
        assert response.status_code == 201

        async with test_session_factory() as session:
            stmt = select(UserProfileModel).where(
                UserProfileModel.display_name == "Profile User"
            )
            result = await session.execute(stmt)
            profile = result.scalars().first()
            assert profile is not None
            assert profile.timezone == "America/New_York"
            assert profile.locale == "fr-FR"

    async def test_register_with_default_timezone_and_locale(
        self, test_client
    ):
        """If timezone/locale not provided, defaults are used."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "defaults@example.com",
                "password": "SecurePassword123!",
                "display_name": "Defaults User",
            },
        )
        assert response.status_code == 201

    async def test_register_password_not_in_response(self, test_client):
        """The password must never appear in the response."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "noPassResp@example.com",
                "password": "SecurePassword123!",
                "display_name": "Test",
            },
        )
        assert response.status_code == 201
        text = response.text
        assert "SecurePassword123!" not in text, "Password leaked in response!"

    async def test_register_password_not_in_audit_log(
        self, test_client, test_session_factory
    ):
        """The password must never appear in the audit log."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "noPassAudit@example.com",
                "password": "NeverInAudit123!",
                "display_name": "Test",
            },
        )
        assert response.status_code == 201

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel)
            result = await session.execute(stmt)
            for audit in result.scalars().all():
                audit_str = str(audit.details)
                assert "NeverInAudit123!" not in audit_str, (
                    "Password leaked in audit log!"
                )

    async def test_register_user_gets_unique_id(
        self, test_client, test_session_factory
    ):
        """Each registered user gets a unique UUID."""
        # Register two users
        for i in range(2):
            await test_client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"user{i}@example.com",
                    "password": "SecurePassword123!",
                    "display_name": f"User {i}",
                },
            )

        async with test_session_factory() as session:
            stmt = select(UserModel)
            result = await session.execute(stmt)
            users = result.scalars().all()
            ids = [u.id for u in users]
            assert len(ids) == len(set(ids)), "User IDs are not unique!"
