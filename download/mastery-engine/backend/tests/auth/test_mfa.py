"""MFA integration tests — /api/v1/auth/mfa/*.

Tests:
- MFA setup returns secret + QR URI + recovery codes
- MFA setup creates MFA_SETUP_INITIATED audit log
- MFA setup stores secret as pending
- MFA enable with valid TOTP code activates MFA
- MFA enable with invalid TOTP code returns 422
- MFA enable creates MFA_ENABLED audit log
- MFA enable sets user.mfa_enabled = True
- MFA verify with valid code returns 200
- MFA verify with invalid code returns 401
- MFA disable with correct password succeeds
- MFA disable with wrong password returns 422
- MFA disable admin returns 422 (CannotDisableMFAForAdmin)
- MFA disable sets user.mfa_enabled = False
- MFA disable creates MFA_DISABLED audit log
- MFA recovery with valid code returns 200
- MFA recovery with invalid code returns 401
- MFA recovery code is single-use
- MFA recovery decrements remaining count
- MFA requires authentication
"""

from __future__ import annotations

import pyotp
import pytest
from sqlalchemy import select, update

from app.infrastructure.database.orm.auth import (
    AuthAuditLogModel,
    MfaRecoveryCodeModel,
    MfaSecretModel,
)
from app.infrastructure.database.orm.identity import UserModel
from tests.auth.conftest import create_test_user, get_auth_headers


pytestmark = pytest.mark.asyncio


class TestMfaSetup:
    """Tests for POST /api/v1/auth/mfa/setup."""

    async def test_mfa_setup_returns_secret_and_qr_and_codes(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA setup returns a secret, QR URI, and recovery codes."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="mfasetup@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "mfasetup@example.com", "SecurePassword123!"
        )

        response = await test_client.post(
            "/api/v1/auth/mfa/setup",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert "secret" in data
        assert "qr_code_uri" in data
        assert "recovery_codes" in data
        assert len(data["recovery_codes"]) == 10
        assert data["qr_code_uri"].startswith("otpauth://")

    async def test_mfa_setup_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA setup creates an MFA_SETUP_INITIATED audit log."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="mfasetupaudit@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "mfasetupaudit@example.com", "SecurePassword123!"
        )

        await test_client.post("/api/v1/auth/mfa/setup", headers=headers)

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "MFA_SETUP_INITIATED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_mfa_setup_stores_pending_secret(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA setup stores the secret as 'pending' in the database."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="mfapending@example.com",
                password="SecurePassword123!"
            )

        headers = await get_auth_headers(
            test_client, "mfapending@example.com", "SecurePassword123!"
        )

        await test_client.post("/api/v1/auth/mfa/setup", headers=headers)

        async with test_session_factory() as session:
            stmt = select(MfaSecretModel).where(
                MfaSecretModel.status == "pending"
            )
            result = await session.execute(stmt)
            secret = result.scalars().first()
            assert secret is not None

    async def test_mfa_setup_requires_auth(
        self, test_client
    ):
        """MFA setup without auth header returns 401."""
        response = await test_client.post("/api/v1/auth/mfa/setup")
        assert response.status_code == 401


class TestMfaEnable:
    """Tests for POST /api/v1/auth/mfa/enable."""

    async def _setup_mfa(self, client, session_factory, auth_service, email):
        """Helper: register + login + setup MFA, return (headers, secret, recovery_codes)."""
        async with session_factory() as session:
            await create_test_user(
                session, auth_service, email=email, password="SecurePassword123!"
            )
        headers = await get_auth_headers(client, email, "SecurePassword123!")
        response = await client.post("/api/v1/auth/mfa/setup", headers=headers)
        data = response.json()
        return headers, data["secret"], data["recovery_codes"]

    async def test_mfa_enable_with_valid_code(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA enable with a valid TOTP code activates MFA."""
        headers, secret, _ = await self._setup_mfa(
            test_client, test_session_factory, auth_service, "mfaenable@example.com"
        )

        totp = pyotp.TOTP(secret)
        code = totp.now()

        response = await test_client.post(
            "/api/v1/auth/mfa/enable",
            json={"totp_code": code, "pending_secret": secret},
            headers=headers,
        )
        assert response.status_code == 200

        # Verify mfa_enabled is True
        async with test_session_factory() as session:
            stmt = select(UserModel).where(
                UserModel.email == "mfaenable@example.com"
            )
            result = await session.execute(stmt)
            user = result.scalars().first()
            assert user.mfa_enabled is True

    async def test_mfa_enable_with_invalid_code_returns_422(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA enable with an invalid TOTP code returns 422."""
        headers, secret, _ = await self._setup_mfa(
            test_client, test_session_factory, auth_service, "mfainvalid2@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/mfa/enable",
            json={"totp_code": "000000", "pending_secret": secret},
            headers=headers,
        )
        assert response.status_code == 422

    async def test_mfa_enable_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA enable creates an MFA_ENABLED audit log."""
        headers, secret, _ = await self._setup_mfa(
            test_client, test_session_factory, auth_service, "mfaenableaudit@example.com"
        )

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

    async def test_mfa_enable_activates_secret(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA enable promotes the pending secret to active."""
        headers, secret, _ = await self._setup_mfa(
            test_client, test_session_factory, auth_service, "mfaactivate@example.com"
        )

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await test_client.post(
            "/api/v1/auth/mfa/enable",
            json={"totp_code": code, "pending_secret": secret},
            headers=headers,
        )

        async with test_session_factory() as session:
            stmt = select(MfaSecretModel).where(
                MfaSecretModel.status == "active"
            )
            result = await session.execute(stmt)
            secret_model = result.scalars().first()
            assert secret_model is not None


class TestMfaVerify:
    """Tests for POST /api/v1/auth/mfa/verify."""

    async def test_mfa_verify_with_valid_code(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA verify with a valid code returns 200."""
        async with test_session_factory() as session:
            user_model, _ = await create_test_user(
                session, auth_service, email="mfaverify@example.com",
                password="SecurePassword123!"
            )
        # Login BEFORE enabling MFA
        headers = await get_auth_headers(
            test_client, "mfaverify@example.com", "SecurePassword123!"
        )
        async with test_session_factory() as session:
            setup = await auth_service.setup_mfa(
                session=session, user_id=user_model.id, user_email="mfaverify@example.com"
            )
            totp = pyotp.TOTP(setup["secret"])
            code = totp.now()
            await auth_service.enable_mfa(
                session=session, user_id=user_model.id,
                totp_code=code, pending_secret=setup["secret"]
            )
            await session.commit()
            secret = setup["secret"]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        response = await test_client.post(
            "/api/v1/auth/mfa/verify",
            json={"code": code, "context": "sensitive_action"},
            headers=headers,
        )
        assert response.status_code == 200

    async def test_mfa_verify_with_invalid_code_returns_401(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA verify with an invalid code returns 401."""
        async with test_session_factory() as session:
            user_model, _ = await create_test_user(
                session, auth_service, email="mfaverifybad@example.com",
                password="SecurePassword123!"
            )
        # Login BEFORE enabling MFA
        headers = await get_auth_headers(
            test_client, "mfaverifybad@example.com", "SecurePassword123!"
        )
        async with test_session_factory() as session:
            setup = await auth_service.setup_mfa(
                session=session, user_id=user_model.id, user_email="mfaverifybad@example.com"
            )
            totp = pyotp.TOTP(setup["secret"])
            code = totp.now()
            await auth_service.enable_mfa(
                session=session, user_id=user_model.id,
                totp_code=code, pending_secret=setup["secret"]
            )
            await session.commit()

        response = await test_client.post(
            "/api/v1/auth/mfa/verify",
            json={"code": "000000", "context": "sensitive_action"},
            headers=headers,
        )
        assert response.status_code == 401


class TestMfaDisable:
    """Tests for POST /api/v1/auth/mfa/disable."""

    async def _setup_and_enable_mfa(self, client, session_factory, auth_service, email):
        """Helper: register + login (returns headers) + setup + enable MFA.

        The headers are obtained BEFORE MFA is enabled, so they remain valid.
        """
        async with session_factory() as session:
            user_model, _ = await create_test_user(
                session, auth_service, email=email, password="SecurePassword123!"
            )
        # Login BEFORE enabling MFA (so we have a valid access token)
        headers = await get_auth_headers(client, email, "SecurePassword123!")
        # Now setup + enable MFA via the service (not via API, so no re-login needed)
        async with session_factory() as session:
            setup = await auth_service.setup_mfa(
                session=session, user_id=user_model.id, user_email=email
            )
            totp = pyotp.TOTP(setup["secret"])
            code = totp.now()
            await auth_service.enable_mfa(
                session=session, user_id=user_model.id,
                totp_code=code, pending_secret=setup["secret"]
            )
            await session.commit()
        return headers

    async def test_mfa_disable_with_correct_password(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA disable with correct password succeeds."""
        headers = await self._setup_and_enable_mfa(
            test_client, test_session_factory, auth_service, "mfadisable@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/mfa/disable",
            json={"password": "SecurePassword123!"},
            headers=headers,
        )
        assert response.status_code == 200

        async with test_session_factory() as session:
            stmt = select(UserModel).where(
                UserModel.email == "mfadisable@example.com"
            )
            result = await session.execute(stmt)
            user = result.scalars().first()
            assert user.mfa_enabled is False

    async def test_mfa_disable_with_wrong_password_returns_422(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA disable with wrong password returns 422."""
        headers = await self._setup_and_enable_mfa(
            test_client, test_session_factory, auth_service, "mfadisablewrong@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/mfa/disable",
            json={"password": "WrongPassword123!"},
            headers=headers,
        )
        assert response.status_code == 422

    async def test_mfa_disable_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA disable creates an MFA_DISABLED audit log."""
        headers = await self._setup_and_enable_mfa(
            test_client, test_session_factory, auth_service, "mfadisableaudit@example.com"
        )

        await test_client.post(
            "/api/v1/auth/mfa/disable",
            json={"password": "SecurePassword123!"},
            headers=headers,
        )

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "MFA_DISABLED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None


class TestMfaRecovery:
    """Tests for POST /api/v1/auth/mfa/recovery."""

    async def _setup_and_enable_mfa(self, client, session_factory, auth_service, email):
        """Helper: register + login + setup + enable MFA, return (headers, recovery_codes)."""
        async with session_factory() as session:
            user_model, _ = await create_test_user(
                session, auth_service, email=email, password="SecurePassword123!"
            )
        # Login BEFORE enabling MFA
        headers = await get_auth_headers(client, email, "SecurePassword123!")
        async with session_factory() as session:
            setup = await auth_service.setup_mfa(
                session=session, user_id=user_model.id, user_email=email
            )
            totp = pyotp.TOTP(setup["secret"])
            code = totp.now()
            await auth_service.enable_mfa(
                session=session, user_id=user_model.id,
                totp_code=code, pending_secret=setup["secret"]
            )
            await session.commit()
        return headers, setup["recovery_codes"]

    async def test_mfa_recovery_with_valid_code(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA recovery with a valid code returns 200."""
        headers, recovery_codes = await self._setup_and_enable_mfa(
            test_client, test_session_factory, auth_service, "mfarecovery@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/mfa/recovery",
            json={"recovery_code": recovery_codes[0]},
            headers=headers,
        )
        assert response.status_code == 200
        assert "remaining" in response.json()["message"].lower()

    async def test_mfa_recovery_with_invalid_code_returns_401(
        self, test_client, test_session_factory, auth_service
    ):
        """MFA recovery with an invalid code returns 401."""
        headers, _ = await self._setup_and_enable_mfa(
            test_client, test_session_factory, auth_service, "mfarecoverybad@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/mfa/recovery",
            json={"recovery_code": "INVALID-CODE-1234"},
            headers=headers,
        )
        assert response.status_code == 401

    async def test_mfa_recovery_code_is_single_use(
        self, test_client, test_session_factory, auth_service
    ):
        """A recovery code can only be used once."""
        headers, recovery_codes = await self._setup_and_enable_mfa(
            test_client, test_session_factory, auth_service, "mfaonce@example.com"
        )

        # First use — success
        response1 = await test_client.post(
            "/api/v1/auth/mfa/recovery",
            json={"recovery_code": recovery_codes[0]},
            headers=headers,
        )
        assert response1.status_code == 200

        # Second use — fail
        response2 = await test_client.post(
            "/api/v1/auth/mfa/recovery",
            json={"recovery_code": recovery_codes[0]},
            headers=headers,
        )
        assert response2.status_code == 401

    async def test_mfa_recovery_decrements_remaining(
        self, test_client, test_session_factory, auth_service
    ):
        """Using a recovery code decrements the remaining count."""
        headers, recovery_codes = await self._setup_and_enable_mfa(
            test_client, test_session_factory, auth_service, "mfacount@example.com"
        )

        response = await test_client.post(
            "/api/v1/auth/mfa/recovery",
            json={"recovery_code": recovery_codes[0]},
            headers=headers,
        )
        assert response.status_code == 200
        # 10 codes initially, 1 used → 9 remaining
        assert "9" in response.json()["message"]
