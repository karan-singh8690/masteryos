# 04 — Authentication

> JWT flow, refresh tokens, OAuth, MFA, session management.

---

## Authentication Overview

The Mastery Engine uses **JWT-based authentication** (per ADR-0013):

- **Access tokens**: short-lived (15 min), RS256-signed, in `Authorization: Bearer` header.
- **Refresh tokens**: long-lived (30 days sliding), opaque, in HttpOnly Secure SameSite=Lax cookie.
- **OAuth**: Google, GitHub.
- **MFA**: TOTP (required for admins; optional for learners).
- **Session management**: server-side session records; revocable; "log out everywhere" supported.

---

## 1. JWT Access Token

### Structure

Standard JWT with three parts: header, payload, signature.

**Header**:
```json
{ "alg": "RS256", "typ": "JWT", "kid": "key-2026-q3" }
```

**Payload** (claims):
```json
{
  "sub": "user-uuid",
  "iss": "https://api.masteryengine.com",
  "aud": "mastery-engine-api",
  "iat": 1719900000,
  "exp": 1719900900,
  "jti": "token-uuid",
  "scope": "learner",
  "enrollments": ["enrollment-uuid-1"]
}
```

### Claims

| Claim | Description |
|---|---|
| `sub` | User ID. |
| `iss` | Issuer (the API server). |
| `aud` | Audience (the API). |
| `iat` | Issued at. |
| `exp` | Expiration (15 min after `iat`). |
| `jti` | Unique token ID (for revocation lists). |
| `scope` | Role: `learner`, `instructor`, `administrator`. |
| `enrollments` | Active enrollment IDs (for fast authorization). |

### Storage

- **Never in localStorage or cookies** — stored in JavaScript memory only.
- **Sent on every authenticated request** in `Authorization: Bearer <token>`.
- **Cleared on logout** or on app refresh (then refreshed via the refresh token).

### Expiration

- Access tokens expire 15 minutes after issuance.
- The frontend attempts a refresh on 401 responses (per the flow below).
- If refresh fails, the user is redirected to login.

---

## 2. Refresh Token

### Properties

- **Format**: opaque random string (256 bits), stored as a salted hash in `sessions` table.
- **Lifetime**: 30 days sliding (each refresh extends by 30 days from the refresh time).
- **Storage**: HttpOnly, Secure, SameSite=Lax cookie (`refresh_token`).
- **Rotation**: rotated on every use; the old token is invalid; replay detection via `token_family_id`.

### Refresh Flow

```
1. Client makes API request with access_token.
2. API returns 401 (token expired).
3. Client calls POST /auth/refresh (refresh token in cookie).
4. Server validates refresh token; checks rotation anomaly.
5. Server issues new access_token; rotates refresh_token (new cookie).
6. Client retries original request with new access_token.
```

### Rotation Anomaly Detection

Each session has a `token_family_id`. On refresh:
- The old refresh token is invalidated.
- A new refresh token is issued with the same `token_family_id`.

If an **old** (already-used) refresh token is presented:
- The server detects the anomaly (the token is in the family but already rotated).
- The **entire session family is revoked** (assumed compromised).
- The user must re-authenticate.

This prevents refresh token theft: an attacker who steals a refresh token gets at most one use before the legitimate user's next refresh reveals the theft.

---

## 3. Login Flow

### Email/Password Login

```
POST /auth/login
{ "email": "alex@example.com", "password": "SecurePass123!", "mfa_code": "123456" }

200 OK
Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Lax; Path=/auth; Max-Age=2592000
{ "access_token": "eyJ...", "expires_in": 900, "user": {...} }
```

If MFA is enabled and `mfa_code` is missing:
```
401 Unauthorized
{ "code": "MFA_REQUIRED", "message": "MFA code required." }
```

### OAuth Login

```
POST /auth/oauth/google/login
{ "code": "oauth-code-from-google", "redirect_uri": "https://app.masteryengine.com/auth/callback" }

200 OK (existing user) or 201 Created (new user)
Set-Cookie: refresh_token=...
{ "access_token": "eyJ...", "expires_in": 900, "user": {...} }
```

---

## 4. Logout

```
POST /auth/logout
Authorization: Bearer <access_token>

204 No Content
Set-Cookie: refresh_token=; Max-Age=0
```

Logout revokes the current session. The access token remains valid until it expires (15 min); the frontend clears it from memory immediately.

---

## 5. Password Reset

### Request

```
POST /auth/password-reset/request
{ "email": "alex@example.com" }

202 Accepted
```

Always returns 202 (no email enumeration). If the email is registered, a reset email is sent.

### Confirm

```
POST /auth/password-reset/confirm
{ "token": "reset-token-from-email", "new_password": "NewSecurePass456!" }

200 OK
```

On success, all sessions are revoked (the user must log in again with the new password).

---

## 6. Email Verification

After registration, the user receives a verification email with a link:
```
https://app.masteryengine.com/auth/verify-email?token=...
```

The frontend extracts the token and calls:
```
POST /auth/verify-email
{ "token": "..." }

200 OK
{ "id": "...", "status": "active", "email_verified_at": "2026-07-02T14:30:00Z" }
```

Until verified, the user cannot enroll in subjects (returns `403 EMAIL_NOT_VERIFIED`).

---

## 7. MFA (TOTP)

### Enable MFA

1. User calls `POST /auth/mfa/enable` (initiates); server returns a TOTP secret + QR code.
2. User adds to their authenticator app; enters the first code.
3. User calls `POST /auth/mfa/enable` with `{ "totp_code": "123456" }`.
4. Server verifies; MFA enabled; backup codes generated.

### Login with MFA

If MFA is enabled, login requires the `mfa_code` field. Missing code → `401 MFA_REQUIRED`. Wrong code → `401 INVALID_CREDENTIALS`.

### Disable MFA

`POST /auth/mfa/disable` with password or current TOTP code. Admin accounts cannot disable MFA (policy).

---

## 8. OAuth Readiness

### Supported Providers

- **Google** (`/auth/oauth/google/login`)
- **GitHub** (`/auth/oauth/github/login`)

### Linking/Unlinking

Authenticated users can link additional OAuth providers or unlink them (via future endpoints), provided they retain at least one credential.

### Future Providers

The OAuth flow is provider-agnostic; adding Microsoft, Apple, etc. is a configuration change, not an API change.

---

## 9. Session Management

### List Sessions

```
GET /auth/sessions
Authorization: Bearer <access_token>

200 OK
[
  { "id": "...", "device_fingerprint": "...", "last_ip": "1.2.3.4", "expires_at": "...", "last_seen_at": "..." }
]
```

### Revoke a Session

```
POST /auth/sessions/{session_id}/revoke
204 No Content
```

### Revoke All Sessions

```
POST /auth/sessions/revoke-all
204 No Content
```

Used after password change, security incident, or manually by the user.

---

## 10. Token Security

### Signing

- **Algorithm**: RS256 (asymmetric; verifying services cannot forge tokens).
- **Key rotation**: quarterly; old keys retained for verification until tokens expire.
- **Key storage**: KMS-managed (per ASD Section 12.6).

### Revocation

Access tokens are stateless (no server-side check per request). For immediate revocation:
- A **revocation list** (JTI blacklist) is checked for admin-sensitive operations.
- For learner accounts, the 15-minute expiration is the revocation window.
- Refresh tokens are revoked immediately (server-side session record).

### Token Leakage Prevention

- Access tokens never logged (logging middleware redacts `Authorization`).
- Refresh tokens in HttpOnly cookies (not accessible to JavaScript).
- `SameSite=Lax` prevents CSRF on refresh.
- HTTPS enforced; HSTS enabled.

---

*End of Authentication.*
