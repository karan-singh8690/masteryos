"""Security documentation — production authentication, authorization, and security architecture."""

# Security Architecture

> **Status:** v1.0 — Production security implementation per ADR-0013.
> **Replaces:** All development-only auth (SHA256, HS256, simplified login).

## Overview

The Mastery Engine implements defense-in-depth security across six layers:

1. **Password Security** — Argon2id (replaces SHA256)
2. **JWT** — RS256 with key rotation (replaces HS256)
3. **Session Management** — Refresh token rotation with reuse detection
4. **MFA** — TOTP with recovery codes
5. **Authorization** — Fine-grained RBAC with object-level checks
6. **Transport Security** — HSTS, CSP, CSRF, rate limiting

## Password Security

### Algorithm: Argon2id (RFC 9106)

| Parameter | Value | Rationale |
|---|---|---|
| memory_cost | 19456 KB (19 MB) | OWASP 2024 recommendation |
| time_cost | 2 iterations | Balance security vs. latency |
| parallelism | 1 thread | Single-user server |
| hash_len | 32 bytes | 256-bit hash |
| salt_len | 16 bytes | 128-bit salt |

### Features
- **Automatic rehash detection**: if parameters change, password is rehashed on next login (transparent upgrade)
- **Constant-time verification**: via argon2-cffi
- **No SHA256**: old SHA256 hashes are detected and rejected (forces password reset)
- **Password upgrade on login**: `verify_and_upgrade()` returns new hash if rehash needed

## JWT

### Algorithm: RS256 (asymmetric)

| Property | Value |
|---|---|
| Signing key | RSA private key (2048-bit) |
| Verification key | RSA public key |
| Key ID (kid) | In JWT header for rotation |
| Issuer | `https://api.masteryengine.com` |
| Audience | `mastery-engine-api` |
| Access token TTL | 15 minutes |
| Clock skew | 30 seconds |
| Token version | In payload (for invalidation) |

### Key Rotation
1. Generate new RSA key pair
2. Add new public key to verification keys (under new kid)
3. Switch signing key to new private key
4. Old tokens remain valid until expiration (verified with old public key)
5. After all old tokens expire, remove old public key

### Token Types
- **Access token**: JWT, 15min, carries user_id + roles + permissions
- **Refresh token**: Opaque random string, 30 days, single-use (rotated)

## Session Management

### Refresh Token Rotation
1. Login → issue access + refresh token
2. Refresh → old refresh token invalidated, new one issued
3. **Reuse detection**: if an old (already-rotated) refresh token is presented → entire token family revoked (assumed compromise)
4. Logout → revoke session
5. Password change → revoke all sessions

### Session Model
- Multiple device sessions per user
- Device metadata: fingerprint, IP, user-agent
- Absolute timeout: 30 days
- Idle timeout: configurable (default 1 hour)
- Revocation: single session or all sessions

## MFA (TOTP)

### Setup
1. Generate random base32 secret
2. Generate QR code URI (otpauth://)
3. Generate 10 recovery codes (XXXX-XXXX-XXXX-XXXX format)
4. User scans QR code with authenticator app
5. User enters first TOTP code to verify
6. Secret + recovery codes stored encrypted

### Verification
- 6-digit TOTP code
- ±30 seconds window (1 interval drift)
- Constant-time comparison

### Recovery Codes
- 10 codes per setup
- One-time use (consumed on use)
- Can be regenerated
- Format: XXXX-XXXX-XXXX-XXXX (16 chars)

## Authorization (RBAC)

### Roles
| Role | Scope | Key Permissions |
|---|---|---|
| learner | per-subject | study, view own progress |
| instructor | per-subject | author/review content |
| content_editor | platform-wide | edit/publish content |
| organization_admin | per-org | manage org members |
| administrator | platform-wide | full access |
| system_admin | platform-wide | admin + manage admins |

### Permission Model
- Fine-grained: `context:resource:action` (e.g., `content:concept:create`)
- Object-level: ownership checks (e.g., "is this your enrollment?")
- Admin override: admins bypass ownership checks
- Permission cache: computed from roles at token issuance

## Security Headers
| Header | Value |
|---|---|
| Strict-Transport-Security | max-age=31536000; includeSubDomains; preload |
| X-Frame-Options | DENY |
| X-Content-Type-Options | nosniff |
| Referrer-Policy | strict-origin-when-cross-origin |
| Permissions-Policy | geolocation=(), microphone=(), camera=() |
| Content-Security-Policy | default-src 'none'; frame-ancestors 'none' |

## Rate Limiting
| Endpoint | Limit | Window |
|---|---|---|
| /auth/login | 10 | per minute |
| /auth/register | 5 | per minute |
| /auth/forgot-password | 3 | per minute |
| /auth/refresh | 30 | per minute |
| /questions/*/submit | 100 | per minute |
| Default | 60 | per minute |

Admins bypass rate limiting.

## CSRF Protection
- Bearer-token-authenticated requests: not vulnerable (tokens not sent by browsers)
- Cookie-based requests (refresh): Origin validation + SameSite=Lax
- Double-submit cookie pattern for form submissions (future)

## Audit Logging
Every security-sensitive action generates an immutable audit log:
- login, logout, password change, password reset
- email verification, MFA enable/disable
- role changes, permission changes
- OAuth linking, token refresh
- session revoke, administrator actions

## API Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | /auth/register | Register with Argon2id |
| POST | /auth/login | Login with password (+ MFA) |
| POST | /auth/logout | Revoke current session |
| POST | /auth/logout-all | Revoke all sessions |
| POST | /auth/refresh | Rotate refresh token |
| POST | /auth/verify-email | Verify with secure token |
| POST | /auth/resend-verification | Resend verification email |
| POST | /auth/forgot-password | Request password reset |
| POST | /auth/reset-password | Reset with secure token |
| POST | /auth/change-password | Change password (auth required) |
| POST | /auth/mfa/setup | Initiate MFA (get QR + recovery codes) |
| POST | /auth/mfa/verify | Verify TOTP code |
| POST | /auth/mfa/enable | Enable MFA |
| POST | /auth/mfa/disable | Disable MFA |
| POST | /auth/mfa/recovery | Regenerate recovery codes |
| GET | /auth/sessions | List active sessions |
| DELETE | /auth/sessions/{id} | Revoke a session |
| GET | /users/me | Get current user |
| PATCH | /users/me | Update profile |
| GET | /users/me/security | Get security info (MFA, sessions) |

## Threat Model
| Threat | Mitigation |
|---|---|
| Password brute force | Argon2id (memory-hard) + rate limiting |
| Token theft | RS256 (verifiers can't forge) + short TTL |
| Refresh token replay | Rotation + reuse detection + family revocation |
| Session hijacking | HttpOnly + Secure + SameSite cookies |
| CSRF | Origin validation + Bearer tokens |
| XSS | CSP (default-src 'none') + no inline scripts |
| Clickjacking | X-Frame-Options: DENY |
| MIME sniffing | X-Content-Type-Options: nosniff |
| Timing attacks | Constant-time comparison (argon2, TOTP, recovery codes) |
| Key compromise | Key rotation + kid header |
| Privilege escalation | Object-level authorization + ownership checks |
