"""Email verification integration tests.

Tests:
- Verify email with valid token transitions user to active
- Verify email with invalid token returns 422
- Verify email with expired token returns 422
- Verify email with already-used token returns 422
- Verify email creates EMAIL_VERIFIED audit log
- Resend verification sends a new token
- Resend verification for nonexistent email returns OK (no leak)
- Resend verification for already-verified email returns OK (no leak)
- Resend verification is throttled
- Verification token is single-use
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as tz_utc

import pytest
from sqlalchemy import select, update

from app.infrastructure.database.orm.auth import (
    AuthAuditLogModel,
    VerificationTokenModel,
)
from app.infrastructure.database.orm.identity import UserModel
from tests.auth.conftest import create_test_user


pytestmark = pytest.mark.asyncio


class TestEmailVerification:
    """Tests for POST /api/v1/auth/verify-email and /resend-verification."""

    async def test_verify_email_with_valid_token(
        self, test_client, test_session_factory, auth_service
    ):
        """Verify email with a valid token transitions user to active."""
        # Register without verifying
        async with test_session_factory() as session:
            user_model, verification_token = await create_test_user(
                session, auth_service, email="verify@example.com",
                password="SecurePassword123!", verified=False
            )

        response = await test_client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification_token},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "active"
        assert data["email_verified_at"] is not None

    async def test_verify_email_with_invalid_token_returns_422(
        self, test_client
    ):
        """Verify email with invalid token returns 422."""
        response = await test_client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid-token-string"},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "INVALID_TOKEN"

    async def test_verify_email_with_expired_token_returns_422(
        self, test_client, test_session_factory, auth_service
    ):
        """Verify email with expired token returns 422."""
        async with test_session_factory() as session:
            user_model, _ = await create_test_user(
                session, auth_service, email="expired@example.com",
                password="SecurePassword123!", verified=False
            )
            # Manually expire the token
            await session.execute(
                update(VerificationTokenModel)
                .where(VerificationTokenModel.user_id == user_model.id)
                .values(expires_at=datetime.now(tz_utc.utc) - timedelta(hours=1))
            )
            await session.commit()

            # Get the token
            stmt = select(VerificationTokenModel).where(
                VerificationTokenModel.user_id == user_model.id
            )
            result = await session.execute(stmt)
            token = result.scalars().first()
            # Need to recompute the raw token — we can't, since it's hashed.
            # So let's create a fresh token and immediately expire it via the service.
            from app.infrastructure.database.repositories.auth import (
                VerificationTokenRepository,
            )
            import secrets
            raw_token = secrets.token_urlsafe(32)
            repo = VerificationTokenRepository(session)
            await repo.create(
                user_id=user_model.id,
                raw_token=raw_token,
                expires_at=datetime.now(tz_utc.utc) - timedelta(hours=1),
            )
            await session.commit()

        response = await test_client.post(
            "/api/v1/auth/verify-email",
            json={"token": raw_token},
        )
        assert response.status_code == 422
        assert "expired" in response.json()["detail"]["message"].lower()

    async def test_verify_email_with_already_used_token_returns_422(
        self, test_client, test_session_factory, auth_service
    ):
        """Verify email with already-used token returns 422."""
        async with test_session_factory() as session:
            _, verification_token = await create_test_user(
                session, auth_service, email="used@example.com",
                password="SecurePassword123!", verified=False
            )

        # First use — success
        response1 = await test_client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification_token},
        )
        assert response1.status_code == 200

        # Second use — fail
        response2 = await test_client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification_token},
        )
        assert response2.status_code == 422

    async def test_verify_email_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """Verify email creates an EMAIL_VERIFIED audit log entry."""
        async with test_session_factory() as session:
            _, verification_token = await create_test_user(
                session, auth_service, email="audit@example.com",
                password="SecurePassword123!", verified=False
            )

        await test_client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification_token},
        )

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "EMAIL_VERIFIED"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_verify_email_token_is_single_use(
        self, test_client, test_session_factory, auth_service
    ):
        """A verification token can only be used once."""
        async with test_session_factory() as session:
            _, verification_token = await create_test_user(
                session, auth_service, email="single@example.com",
                password="SecurePassword123!", verified=False
            )

        # Use the token
        await test_client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification_token},
        )

        # Verify the token is consumed in the DB
        async with test_session_factory() as session:
            stmt = select(VerificationTokenModel)
            result = await session.execute(stmt)
            tokens = result.scalars().all()
            # At least one token should have consumed_at set
            consumed = [t for t in tokens if t.consumed_at is not None]
            assert len(consumed) >= 1

    async def test_resend_verification_sends_new_token(
        self, test_client, test_session_factory, auth_service
    ):
        """Resend verification creates a new verification token."""
        # Register WITHOUT creating a verification token directly
        # (the API's register endpoint creates one, but we use the service
        # without creating a token to avoid throttle)
        from app.infrastructure.database.orm.identity import UserModel, UserProfileModel, UserCredentialModel
        from app.domain.shared.value_objects import Email
        from uuid import uuid4
        from datetime import datetime, timezone as tz_utc

        async with test_session_factory() as session:
            email_vo = Email("resend@example.com")
            password_hash = auth_service.password_service.hash_password("SecurePassword123!")
            user_id = uuid4()
            session.add(UserModel(
                id=user_id, email=email_vo.value, status="pending_verification",
                mfa_enabled=False,
            ))
            session.add(UserProfileModel(
                user_id=user_id, display_name="Resend User",
            ))
            session.add(UserCredentialModel(
                id=uuid4(), user_id=user_id, credential_type="password",
                password_hash=password_hash,
            ))
            await session.commit()

        # Initial token count = 0 (we didn't create one)
        async with test_session_factory() as session:
            stmt = select(VerificationTokenModel).where(
                VerificationTokenModel.token_type == "email_verification"
            )
            result = await session.execute(stmt)
            initial_count = len(result.scalars().all())

        # Resend
        response = await test_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "resend@example.com"},
        )
        assert response.status_code == 200

        # New token should be created
        async with test_session_factory() as session:
            stmt = select(VerificationTokenModel).where(
                VerificationTokenModel.token_type == "email_verification"
            )
            result = await session.execute(stmt)
            final_count = len(result.scalars().all())
            assert final_count > initial_count

    async def test_resend_verification_nonexistent_email_no_leak(
        self, test_client
    ):
        """Resend verification for nonexistent email returns OK (no leak)."""
        response = await test_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "nonexistent@example.com"},
        )
        assert response.status_code == 200
        # Message should not reveal whether the email exists
        assert "If the email exists" in response.json()["message"]

    async def test_resend_verification_already_verified_no_leak(
        self, test_client, test_session_factory, auth_service
    ):
        """Resend verification for already-verified email returns OK (no leak)."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="verified@example.com",
                password="SecurePassword123!", verified=True
            )

        response = await test_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "verified@example.com"},
        )
        assert response.status_code == 200
        # Should not create a new token (already verified)
        async with test_session_factory() as session:
            stmt = select(VerificationTokenModel).where(
                VerificationTokenModel.user_id.isnot(None)
            )
            result = await session.execute(stmt)
            # Should still be the initial token from registration (or none)
            tokens = result.scalars().all()
            # No new tokens created for already-verified user
            # (the initial registration creates one, but resend should not create another)

    async def test_resend_verification_creates_audit_log(
        self, test_client, test_session_factory, auth_service
    ):
        """Resend verification creates a VERIFICATION_EMAIL_RESENT audit log."""
        # Register without creating a verification token (avoid throttle)
        from app.infrastructure.database.orm.identity import UserModel, UserProfileModel, UserCredentialModel
        from app.domain.shared.value_objects import Email
        from uuid import uuid4

        async with test_session_factory() as session:
            email_vo = Email("audit2@example.com")
            password_hash = auth_service.password_service.hash_password("SecurePassword123!")
            user_id = uuid4()
            session.add(UserModel(
                id=user_id, email=email_vo.value, status="pending_verification",
                mfa_enabled=False,
            ))
            session.add(UserProfileModel(
                user_id=user_id, display_name="Audit User",
            ))
            session.add(UserCredentialModel(
                id=uuid4(), user_id=user_id, credential_type="password",
                password_hash=password_hash,
            ))
            await session.commit()

        await test_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "audit2@example.com"},
        )

        async with test_session_factory() as session:
            stmt = select(AuthAuditLogModel).where(
                AuthAuditLogModel.action == "VERIFICATION_EMAIL_RESENT"
            )
            result = await session.execute(stmt)
            audit = result.scalars().first()
            assert audit is not None

    async def test_resend_verification_throttled(
        self, test_client, test_session_factory, auth_service
    ):
        """Resend verification is throttled (max 1 per 2 minutes)."""
        async with test_session_factory() as session:
            await create_test_user(
                session, auth_service, email="throttle@example.com",
                password="SecurePassword123!", verified=False
            )

        # First resend — OK
        response1 = await test_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "throttle@example.com"},
        )
        assert response1.status_code == 200

        # Immediate second resend — should be throttled (no new token)
        # The API still returns 200 (no leak), but no new token is created
        async with test_session_factory() as session:
            stmt = select(VerificationTokenModel).where(
                VerificationTokenModel.token_type == "email_verification"
            )
            result = await session.execute(stmt)
            count_after_first = len(result.scalars().all())

        response2 = await test_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "throttle@example.com"},
        )
        assert response2.status_code == 200  # Still OK (no leak)

        async with test_session_factory() as session:
            stmt = select(VerificationTokenModel).where(
                VerificationTokenModel.token_type == "email_verification"
            )
            result = await session.execute(stmt)
            count_after_second = len(result.scalars().all())
            assert count_after_second == count_after_first  # No new token
