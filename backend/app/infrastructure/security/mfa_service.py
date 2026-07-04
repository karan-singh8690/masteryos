"""MFA service — TOTP-based multi-factor authentication.

Features:
- TOTP (Time-based One-Time Password) per RFC 6238
- QR code generation for authenticator apps
- Recovery codes (one-time use)
- Enable/disable MFA
- Verify TOTP codes
- Regenerate recovery codes

Per ADR-0013: MFA required for admin accounts; optional for learners.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Any

import pyotp
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Recovery code settings
RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_LENGTH = 16  # characters

# TOTP settings
TOTP_ISSUER = "Mastery Engine"
TOTP_DIGITS = 6
TOTP_INTERVAL = 30  # seconds


@dataclass(frozen=True)
class MFASetupResult:
    """Result of MFA setup initiation."""

    secret: str
    qr_code_uri: str
    recovery_codes: list[str]


@dataclass(frozen=True)
class MFAVerifyResult:
    """Result of MFA verification."""

    verified: bool
    remaining_recovery_codes: list[str] | None = None
    used_recovery_code: bool = False


class MFAService:
    """TOTP-based MFA service.

    Usage:
        mfa = MFAService()

        # Setup
        setup = mfa.setup_mfa(user_id)
        # User scans QR code, enters first code
        verified = mfa.verify_totp(setup.secret, "123456")
        if verified:
            # Store secret + recovery codes for user

        # Login
        verified = mfa.verify_totp(stored_secret, user_provided_code)

        # Recovery
        result = mfa.use_recovery_code(user_provided_code, stored_recovery_codes)
    """

    def __init__(self, issuer: str = TOTP_ISSUER) -> None:
        self._issuer = issuer

    def setup_mfa(self, user_email: str) -> MFASetupResult:
        """Initiate MFA setup — generates secret, QR URI, and recovery codes.

        Args:
            user_email: The user's email (for QR code label)

        Returns:
            MFASetupResult with secret, QR URI, and recovery codes.
            The secret and recovery codes must be stored encrypted.
        """
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
        qr_uri = totp.provisioning_uri(name=user_email, issuer_name=self._issuer)
        recovery_codes = self._generate_recovery_codes()

        logger.info("mfa_setup_initiated")

        return MFASetupResult(
            secret=secret,
            qr_code_uri=qr_uri,
            recovery_codes=recovery_codes,
        )

    def verify_totp(self, secret: str, code: str) -> bool:
        """Verify a TOTP code against the secret.

        Uses a ±1 window (allows 1 interval of clock drift).
        Constant-time comparison via pyotp/hmac.
        """
        if not secret or not code:
            return False

        try:
            totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
            # valid_window=1 allows ±30 seconds of clock drift
            return totp.verify(code, valid_window=1)
        except Exception as exc:
            logger.warning("totp_verification_error", error=str(exc))
            return False

    def use_recovery_code(
        self,
        provided_code: str,
        stored_codes: list[str],
    ) -> MFAVerifyResult:
        """Attempt to use a recovery code.

        Recovery codes are one-time use. If matched, the code is removed
        from the stored list.

        Args:
            provided_code: The code the user entered.
            stored_codes: The list of valid recovery codes (will be modified).

        Returns:
            MFAVerifyResult with verified=True and remaining codes if matched.
        """
        if not provided_code or not stored_codes:
            return MFAVerifyResult(verified=False)

        # Constant-time comparison
        for i, stored in enumerate(stored_codes):
            if hmac.compare_digest(provided_code.strip().upper(), stored.upper()):
                # Remove the used code
                remaining = stored_codes[:i] + stored_codes[i + 1:]
                logger.info("recovery_code_used", remaining_count=len(remaining))
                return MFAVerifyResult(
                    verified=True,
                    remaining_recovery_codes=remaining,
                    used_recovery_code=True,
                )

        return MFAVerifyResult(verified=False)

    def regenerate_recovery_codes(self) -> list[str]:
        """Generate a new set of recovery codes.

        Previous codes are invalidated (caller must overwrite stored codes).
        """
        new_codes = self._generate_recovery_codes()
        logger.info("recovery_codes_regenerated", count=len(new_codes))
        return new_codes

    def _generate_recovery_codes(self) -> list[str]:
        """Generate cryptographically secure recovery codes."""
        codes: list[str] = []
        for _ in range(RECOVERY_CODE_COUNT):
            # Format: XXXX-XXXX-XXXX-XXXX (16 chars, 4 groups)
            raw = secrets.token_hex(RECOVERY_CODE_LENGTH // 2)
            formatted = "-".join(
                raw[i:i + 4] for i in range(0, len(raw), 4)
            )
            codes.append(formatted.upper())
        return codes

    def generate_backup_code(self) -> str:
        """Generate a single backup code (for testing)."""
        raw = secrets.token_hex(8)
        return "-".join(raw[i:i + 4] for i in range(0, len(raw), 4)).upper()
