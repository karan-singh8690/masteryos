"""Production Argon2id password hashing service.

Replaces all SHA256 password hashing with Argon2id (RFC 9106).

Features:
- Configurable memory cost, iterations, parallelism
- Automatic rehash detection (if parameters change, rehash on next login)
- Constant-time verification via argon2-cffi
- Password upgrade on login (transparent to the user)

No SHA256 anywhere in the password pipeline.
"""

from __future__ import annotations

import secrets
from typing import Any

from passlib.context import CryptContext
from passlib.hash import argon2

from app.shared.logging import get_logger

logger = get_logger(__name__)


class PasswordService:
    """Production password hashing service using Argon2id.

    Configuration (sensible defaults per OWASP 2024):
    - memory_cost: 19456 KB (19 MB)
    - time_cost: 2 iterations
    - parallelism: 1 thread
    - hash_len: 32 bytes
    - salt_len: 16 bytes

    These parameters can be overridden via settings for environments
    with different performance characteristics.
    """

    def __init__(
        self,
        memory_cost: int = 19456,
        time_cost: int = 2,
        parallelism: int = 1,
    ) -> None:
        self._memory_cost = memory_cost
        self._time_cost = time_cost
        self._parallelism = parallelism

        # Configure passlib with Argon2id
        self._ctx = CryptContext(
            schemes=["argon2"],
            deprecated="auto",
            argon2__memory_cost=memory_cost,
            argon2__time_cost=time_cost,
            argon2__parallelism=parallelism,
            argon2__hash_len=32,
            argon2__salt_len=16,
        )

        logger.info(
            "password_service_initialized",
            memory_cost=memory_cost,
            time_cost=time_cost,
            parallelism=parallelism,
        )

    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2id.

        Returns a PHC-formatted string:
        $argon2id$v=19$m=19456,t=2,p=1$<salt>$<hash>

        This replaces the old SHA256 format:
        argon2id$<salt>$<sha256_hash>
        """
        if not password:
            raise ValueError("Password must not be empty")
        return self._ctx.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against an Argon2id hash.

        Uses constant-time comparison (via argon2-cffi).
        Returns False if verification fails (never raises).
        """
        if not password or not password_hash:
            return False

        # Detect old SHA256 format and reject (force password reset)
        if password_hash.startswith("argon2id$") and "$" in password_hash:
            parts = password_hash.split("$")
            if len(parts) == 3:
                # Old format: argon2id$salt$sha256hash — not real Argon2id
                logger.warning("old_sha256_hash_detected")
                return False

        try:
            return self._ctx.verify(password, password_hash)
        except Exception as exc:
            logger.warning("password_verification_error", error=str(exc))
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        """Check if a hash needs rehashing (parameters changed).

        Called after successful login. If True, the password is rehashed
        with current parameters (transparent upgrade).
        """
        if not password_hash:
            return False

        # Old SHA256 format always needs rehash
        if password_hash.startswith("argon2id$") and password_hash.count("$") == 2:
            return True

        try:
            return self._ctx.needs_update(password_hash)
        except Exception:
            return False

    def verify_and_upgrade(
        self, password: str, password_hash: str
    ) -> tuple[bool, str | None]:
        """Verify password and upgrade hash if needed.

        Returns:
            (verified, new_hash_or_none)
            - verified: True if password matches
            - new_hash: New Argon2id hash if upgrade needed, None otherwise

        Usage:
            verified, new_hash = password_service.verify_and_upgrade(password, stored_hash)
            if verified and new_hash:
                # Save new_hash to database (transparent upgrade)
                await user_repository.update_password_hash(user_id, new_hash)
        """
        if not self.verify_password(password, password_hash):
            return (False, None)

        if self.needs_rehash(password_hash):
            new_hash = self.hash_password(password)
            logger.info("password_hash_upgraded")
            return (True, new_hash)

        return (True, None)

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a cryptographically secure random token.

        Used for:
        - Email verification tokens
        - Password reset tokens
        - OAuth state tokens
        - Session tokens
        """
        return secrets.token_urlsafe(length)

    def generate_numeric_code(self, length: int = 6) -> str:
        """Generate a cryptographically secure numeric code.

        Used for:
        - MFA backup codes
        - Verification codes
        """
        return "".join(secrets.choice("0123456789") for _ in range(length))
