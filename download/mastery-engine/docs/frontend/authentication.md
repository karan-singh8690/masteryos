# Authentication

> JWT-based authentication with refresh token rotation + MFA.

## Token Strategy

- **Access token**: RS256 JWT, 15-minute expiry, stored in `localStorage`
- **Refresh token**: Opaque string, 30-day expiry, stored in `localStorage`
- **Token refresh**: Automatic via Axios interceptor on 401

## Login Flow

1. User enters email + password
2. `authApi.login()` sends credentials to `/auth/login`
3. Backend returns access + refresh tokens
4. Tokens stored in `localStorage` via `tokenStorage`
5. `AuthProvider` fetches `/users/me` to get user data
6. User redirected to dashboard

### MFA Flow

If MFA is enabled, the login response includes `requiresMfa: true`:

1. User enters email + password
2. Backend returns `requiresMfa: true` + `mfaSessionToken`
3. Frontend shows MFA code input
4. User enters 6-digit TOTP code
5. `authApi.login()` called again with `mfaCode`
6. Backend returns tokens

## Refresh Token Handling

The Axios response interceptor automatically refreshes on 401:

```
Request → 401 → refreshAccessToken() → retry with new token
```

If refresh fails, tokens are cleared + user redirected to `/session-expired`.

## Logout

- `logout(false)` — Logout current device (revoke current session)
- `logout(true)` — Logout all devices (revoke all sessions)

## Pages

| Page | Route | Purpose |
|---|---|---|
| Login | `/login` | Email/password + MFA |
| Register | `/register` | Registration with password strength |
| Forgot Password | `/forgot-password` | Request reset link |
| Reset Password | `/reset-password` | Reset with token |
| Verify Email | `/verify-email` | Verify email with token |
| MFA Setup | `/mfa/setup` | QR code + recovery codes |
| MFA Verify | `/mfa/verify` | Verify TOTP code |
| Recovery Codes | `/recovery-codes` | Use recovery code |
| Session Expired | `/session-expired` | Token expired |

## API Integration

```typescript
import { authApi } from '@/lib/api-client'

// Login
await authApi.login({ email, password, mfaCode })

// Refresh
await authApi.refresh(refreshToken)

// Logout
await authApi.logout(refreshToken)
await authApi.logoutAll()
```
