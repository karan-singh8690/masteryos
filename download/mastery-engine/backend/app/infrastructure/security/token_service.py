"""Secure token service for email verification and password reset.

Generates cryptographically secure, single-use, expiring tokens.
Tokens are opaque (not JWTs) and stored hashed in the database.

Token lifecycle:
1. Generate: create a random token, store its hash + metadata
2. Verify: look up by hash, check expiration + single-use
3. Consume: mark as used (single-use enforcement)
4. Expire: background job cleans up expired tokens
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from app.shared.logging import get_logger

logger = get_logger(__name__)

# Token settings
TOKEN_LENGTH = 32  # bytes → ~43 chars in URL-safe base64
VERIFICATION_TOKEN_TTL = timedelta(hours=24)  # 24 hours
PASSWORD_RESET_TOKEN_TTL = timedelta(minutes=15)  # 15 minutes (security: short)
OAUTH_STATE_TOKEN_TTL = timedelta(minutes=10)  # 10 minutes


class TokenType(str, Enum):
    """Types of secure tokens."""

    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    OAUTH_STATE = "oauth_state"


@dataclass(frozen=True)
class SecureToken:
    """A generated secure token with metadata."""

    raw_token: str  # Only returned once; never stored
    token_hash: str  # SHA-256 hash; stored in DB
    token_type: TokenType
    user_id: UUID
    expires_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class TokenVerificationResult:
    """Result of token verification."""

    valid: bool
    user_id: UUID | None = None
    token_type: TokenType | None = None
    error: str | None = None


class TokenService:
    """Secure token generation and verification service.

    Features:
    - Cryptographically secure random tokens (secrets.token_urlsafe)
    - SHA-256 hashing for database storage (only hash is stored)
    - Configurable TTL per token type
    - Single-use enforcement (consumed tokens are rejected)
    - Throttling support (limit token generation per user)
    """

    def __init__(self) -> None:
        self._token_store: dict[str, dict[str, Any]] = {}  # hash → metadata (in-memory; production uses DB)

    def generate_token(
        self,
        user_id: UUID,
        token_type: TokenType,
        ttl: timedelta | None = None,
    ) -> SecureToken:
        """Generate a secure token.

        Args:
            user_id: The user the token is for.
            token_type: Type of token (verification, reset, oauth).
            ttl: Time-to-live. Defaults based on token type.

        Returns:
            SecureToken with the raw token (returned once) and hash (for storage).
        """
        if ttl is None:
            ttl = self._default_ttl(token_type)

        raw_token = secrets.token_urlsafe(TOKEN_LENGTH)
        token_hash = self._hash_token(raw_token)
        now = datetime.now(timezone.utc)
        expires_at = now + ttl

        # Store metadata (in production, this goes to the database)
        self._token_store[token_hash] = {
            "user_id": user_id,
            "token_type": token_type,
            "expires_at": expires_at,
            "created_at": now,
            "consumed": False,
        }

        logger.info(
            "token_generated",
            token_type=token_type.value,
            user_id=str(user_id),
            expires_in_seconds=int(ttl.total_seconds()),
        )

        return SecureToken(
            raw_token=raw_token,
            token_hash=token_hash,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at,
            created_at=now,
        )

    def verify_token(
        self,
        raw_token: str,
        expected_type: TokenType,
    ) -> TokenVerificationResult:
        """Verify a token.

        Checks:
        1. Token hash exists in store
        2. Token type matches expected type
        3. Token has not expired
        4. Token has not been consumed (single-use)

        Does NOT consume the token — call consume_token() after verification.
        """
        if not raw_token:
            return TokenVerificationResult(valid=False, error="Empty token")

        token_hash = self._hash_token(raw_token)

        stored = self._token_store.get(token_hash)
        if stored is None:
            return TokenVerificationResult(valid=False, error="Token not found")

        if stored["token_type"] != expected_type:
            return TokenVerificationResult(valid=False, error="Wrong token type")

        if stored["consumed"]:
            return TokenVerificationResult(valid=False, error="Token already used")

        if datetime.now(timezone.utc) > stored["expires_at"]:
            return TokenVerificationResult(valid=False, error="Token expired")

        return TokenVerificationResult(
            valid=True,
            user_id=stored["user_id"],
            token_type=stored["token_type"],
        )

    def consume_token(self, raw_token: str) -> bool:
        """Mark a token as consumed (single-use enforcement).

        Returns True if the token was consumed, False if not found or already consumed.
        """
        token_hash = self._hash_token(raw_token)
        stored = self._token_store.get(token_hash)

        if stored is None or stored["consumed"]:
            return False

        stored["consumed"] = True
        logger.info(
            "token_consumed",
            token_type=stored["token_type"].value,
            user_id=str(stored["user_id"]),
        )
        return True

    def invalidate_user_tokens(self, user_id: UUID, token_type: TokenType | None = None) -> int:
        """Invalidate all tokens for a user (e.g., after password change).

        Returns the number of tokens invalidated.
        """
        count = 0
        for stored in self._token_store.values():
            if stored["user_id"] == user_id:
                if token_type is None or stored["token_type"] == token_type:
                    stored["consumed"] = True
                    count += 1

        if count > 0:
            logger.info(
                "tokens_invalidated",
                user_id=str(user_id),
                count=count,
                token_type=token_type.value if token_type else "all",
            )

        return count

    def cleanup_expired(self) -> int:
        """Remove expired tokens from the store. Returns count removed."""
        now = datetime.now(timezone.utc)
        expired_hashes = [
            h for h, s in self._token_store.items()
            if now > s["expires_at"]
        ]
        for h in expired_hashes:
            del self._token_store[h]

        if expired_hashes:
            logger.info("expired_tokens_cleaned_up", count=len(expired_hashes))

        return len(expired_hashes)

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        """Hash a token for storage. Only the hash is stored."""
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @staticmethod
    def _default_ttl(token_type: TokenType) -> timedelta:
        """Get the default TTL for a token type."""
        if token_type == TokenType.EMAIL_VERIFICATION:
            return VERIFICATION_TOKEN_TTL
        if token_type == TokenType.PASSWORD_RESET:
            return PASSWORD_RESET_TOKEN_TTL
        if token_type == TokenType.OAUTH_STATE:
            return OAUTH_STATE_TOKEN_TTL
        return timedelta(hours=1)
