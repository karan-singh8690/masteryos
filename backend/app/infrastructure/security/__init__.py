"""Security infrastructure package — production authentication, authorization, and security services.

Modules:
- password_service.py: Argon2id password hashing (replaces SHA256)
- jwt_service.py: RS256 JWT with key rotation (replaces HS256)
- token_service.py: Secure tokens for email verification + password reset
- session_service.py: Session management with refresh token rotation
- mfa_service.py: TOTP-based MFA with recovery codes
- authorization.py: Fine-grained RBAC with object-level checks
"""

from app.infrastructure.security.password_service import PasswordService
from app.infrastructure.security.jwt_service import (
    JWTKeyManager,
    JWTService,
    TokenClaims,
    IssuedTokenPair,
)
from app.infrastructure.security.token_service import (
    SecureToken,
    TokenService,
    TokenVerificationResult,
    TokenType,
)
from app.infrastructure.security.session_service import (
    SessionInfo,
    SessionService,
    RefreshResult,
)
from app.infrastructure.security.mfa_service import (
    MFAService,
    MFASetupResult,
    MFAVerifyResult,
)
from app.infrastructure.security.authorization import (
    AuthContext,
    AuthorizationDenied,
    AuthorizationService,
    ROLE_LEARNER,
    ROLE_INSTRUCTOR,
    ROLE_CONTENT_EDITOR,
    ROLE_ORGANIZATION_ADMIN,
    ROLE_ADMINISTRATOR,
    ROLE_SYSTEM_ADMIN,
    ALL_ROLES,
    ROLE_PERMISSIONS,
)

__all__ = [
    # Password
    "PasswordService",
    # JWT
    "JWTKeyManager",
    "JWTService",
    "TokenClaims",
    "IssuedTokenPair",
    # Tokens
    "SecureToken",
    "TokenService",
    "TokenVerificationResult",
    "TokenType",
    # Sessions
    "SessionInfo",
    "SessionService",
    "RefreshResult",
    # MFA
    "MFAService",
    "MFASetupResult",
    "MFAVerifyResult",
    # Authorization
    "AuthContext",
    "AuthorizationDenied",
    "AuthorizationService",
    "ROLE_LEARNER",
    "ROLE_INSTRUCTOR",
    "ROLE_CONTENT_EDITOR",
    "ROLE_ORGANIZATION_ADMIN",
    "ROLE_ADMINISTRATOR",
    "ROLE_SYSTEM_ADMIN",
    "ALL_ROLES",
    "ROLE_PERMISSIONS",
]
