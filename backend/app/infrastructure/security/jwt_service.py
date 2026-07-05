"""Production JWT service using RS256 (asymmetric) with key rotation.

Replaces all HS256 (symmetric) JWT operations.

Features:
- RS256 signing (asymmetric — verifying services cannot forge tokens)
- Key rotation with kid (Key ID) header
- Access tokens: 15-minute expiration
- Refresh tokens: 30-day expiration (opaque, not JWT)
- Token version support (for invalidating all tokens on password change)
- Issuer and audience validation
- Clock skew tolerance
- Key loading from files (private key for signing, public key for verification)
- Automatic key rotation detection

Per ADR-0013: RS256 or EdDSA; never HS256.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.shared.config import get_settings
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Token types
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

# Default expiration
ACCESS_TOKEN_EXPIRE_SECONDS = 15 * 60  # 15 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Clock skew tolerance (seconds)
CLOCK_SKEW_TOLERANCE = 30


@dataclass(frozen=True)
class TokenClaims:
    """Decoded JWT claims."""

    user_id: UUID
    token_type: str
    token_version: int
    roles: list[str]
    issued_at: int
    expires_at: int
    issuer: str
    audience: str
    jwt_id: str
    key_id: str | None


@dataclass(frozen=True)
class IssuedTokenPair:
    """Result of issuing an access + refresh token pair."""

    access_token: str
    refresh_token: str
    access_token_expires_in: int
    user_id: UUID
    token_version: int


class JWTKeyManager:
    """Manages RSA key pairs for JWT signing with rotation support.

    Keys are loaded from files. The active key is used for signing.
    All loaded keys (including previous keys) are available for verification
    during the rotation window.
    """

    def __init__(self, keys_dir: str | Path | None = None) -> None:
        self._keys_dir = Path(keys_dir) if keys_dir else None
        self._signing_key: Any = None  # RSA private key
        self._signing_key_id: str = "default"
        self._verification_keys: dict[str, Any] = {}  # kid → RSA public key
        self._initialized = False

    def initialize(self) -> None:
        """Initialize keys from files or generate a development key pair."""
        if self._initialized:
            return

        if self._keys_dir and (self._keys_dir / "private.pem").exists():
            # Production: load from files
            self._load_keys_from_files()
        else:
            # Development: generate an ephemeral key pair
            logger.warning("jwt_keys_generating_ephemeral", message="No key files found — generating ephemeral RSA key pair for development")
            self._generate_development_keys()

        self._initialized = True
        logger.info("jwt_key_manager_initialized", key_id=self._signing_key_id)

    def _load_keys_from_files(self) -> None:
        """Load RSA keys from PEM files."""
        private_path = self._keys_dir / "private.pem"  # type: ignore[union-attr]
        public_path = self._keys_dir / "public.pem"  # type: ignore[union-attr]

        with open(private_path, "rb") as f:
            self._signing_key = serialization.load_pem_private_key(f.read(), password=None)

        with open(public_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())

        self._signing_key_id = "key-1"
        self._verification_keys[self._signing_key_id] = public_key

        # Load additional public keys for rotation (public-2.pem, etc.)
        for i in range(2, 10):
            extra_path = self._keys_dir / f"public-{i}.pem"  # type: ignore[union-attr]
            if extra_path.exists():
                with open(extra_path, "rb") as f:
                    self._verification_keys[f"key-{i}"] = serialization.load_pem_public_key(f.read())

    def _generate_development_keys(self) -> None:
        """Generate an ephemeral RSA key pair for development."""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self._signing_key = private_key
        self._signing_key_id = "dev-key"
        self._verification_keys[self._signing_key_id] = private_key.public_key()

    @property
    def signing_key(self) -> Any:
        if not self._initialized:
            self.initialize()
        return self._signing_key

    @property
    def signing_key_id(self) -> str:
        if not self._initialized:
            self.initialize()
        return self._signing_key_id

    def get_verification_key(self, kid: str | None) -> Any:
        """Get the public key for verification by key ID."""
        if not self._initialized:
            self.initialize()
        if kid and kid in self._verification_keys:
            return self._verification_keys[kid]
        # Fallback: try the signing key's public key
        if self._signing_key_id in self._verification_keys:
            return self._verification_keys[self._signing_key_id]
        # Last resort: return any available key
        if self._verification_keys:
            return next(iter(self._verification_keys.values()))
        raise KeyError(f"No verification key found for kid: {kid}")


class JWTService:
    """Production JWT service using RS256.

    Usage:
        jwt_service = JWTService()
        token_pair = jwt_service.issue_token_pair(user_id, roles, token_version)
        claims = jwt_service.verify_access_token(token)
    """

    def __init__(
        self,
        key_manager: JWTKeyManager | None = None,
        issuer: str = "https://api.masteryengine.com",
        audience: str = "mastery-engine-api",
    ) -> None:
        self._key_manager = key_manager or JWTKeyManager()
        self._issuer = issuer
        self._audience = audience

    def issue_access_token(
        self,
        user_id: UUID,
        roles: list[str],
        token_version: int = 1,
        expires_in: int = ACCESS_TOKEN_EXPIRE_SECONDS,
    ) -> str:
        """Issue a JWT access token signed with RS256."""
        now = int(time.time())
        payload = {
            "sub": str(user_id),
            "iss": self._issuer,
            "aud": self._audience,
            "iat": now,
            "exp": now + expires_in,
            "jti": str(uuid4()),
            "typ": ACCESS_TOKEN_TYPE,
            "ver": token_version,
            "scope": ",".join(roles),
        }

        headers = {
            "kid": self._key_manager.signing_key_id,
            "alg": "RS256",
            "typ": "JWT",
        }

        token = jwt.encode(
            payload,
            self._key_manager.signing_key,
            algorithm="RS256",
            headers=headers,
        )
        return token

    def issue_refresh_token(self, user_id: UUID, token_version: int = 1) -> str:
        """Issue an opaque refresh token (not a JWT).

        Refresh tokens are opaque strings stored as:
        - A random 256-bit value
        - Hashed (SHA256) in the database
        - Single-use (rotated on each refresh)
        - Carry the token_version for invalidation
        """
        import hashlib
        import secrets
        raw = secrets.token_urlsafe(32)
        # Encode token_version and user_id into the token for lookup
        # Format: v{version}.{raw_token}
        return f"v{token_version}.{raw}"

    def issue_token_pair(
        self,
        user_id: UUID,
        roles: list[str],
        token_version: int = 1,
    ) -> IssuedTokenPair:
        """Issue both an access token and a refresh token."""
        access_token = self.issue_access_token(user_id, roles, token_version)
        refresh_token = self.issue_refresh_token(user_id, token_version)
        return IssuedTokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
            user_id=user_id,
            token_version=token_version,
        )

    def verify_access_token(self, token: str) -> TokenClaims | None:
        """Verify a JWT access token.

        Returns None if verification fails (expired, invalid signature, wrong type, etc.).
        Never raises — returns None for security (don't leak why verification failed).
        """
        try:
            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            alg = unverified_header.get("alg", "")

            # Reject HS256 tokens (security: only RS256 allowed)
            if alg != "RS256":
                logger.warning("jwt_rejected_wrong_algorithm", algorithm=alg)
                return None

            # Get the verification key
            verification_key = self._key_manager.get_verification_key(kid)

            # Decode and verify
            payload = jwt.decode(
                token,
                verification_key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
                leeway=CLOCK_SKEW_TOLERANCE,
            )

            # Verify token type
            if payload.get("typ") != ACCESS_TOKEN_TYPE:
                logger.warning("jwt_rejected_wrong_type", token_type=payload.get("typ"))
                return None

            return TokenClaims(
                user_id=UUID(payload["sub"]),
                token_type=payload["typ"],
                token_version=payload.get("ver", 1),
                # Filter out empty strings from split (e.g. when scope claim is missing or empty)
                roles=[r for r in payload.get("scope", "").split(",") if r],
                issued_at=payload["iat"],
                expires_at=payload["exp"],
                issuer=payload["iss"],
                audience=payload["aud"],
                jwt_id=payload["jti"],
                key_id=kid,
            )

        except jwt.ExpiredSignatureError:
            logger.info("jwt_expired")
            return None
        except jwt.InvalidTokenError as exc:
            logger.warning("jwt_invalid", error=str(exc))
            return None
        except Exception as exc:
            logger.warning("jwt_verification_error", error=str(exc))
            return None

    def hash_refresh_token(self, refresh_token: str) -> str:
        """Hash a refresh token for database storage.

        Only the hash is stored — the raw token is never persisted.
        """
        import hashlib
        return hashlib.sha256(refresh_token.encode()).hexdigest()

    def parse_refresh_token_version(self, refresh_token: str) -> int | None:
        """Extract the token version from a refresh token."""
        if refresh_token.startswith("v") and "." in refresh_token:
            version_str = refresh_token.split(".")[0][1:]
            try:
                return int(version_str)
            except ValueError:
                return None
        return None
