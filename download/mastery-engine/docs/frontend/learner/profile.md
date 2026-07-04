# Profile

> User profile and account management.

## Pages (from Task 018)

### Profile (`/profile`)
- Update display name
- Update timezone
- Update locale
- Update avatar URL
- Uses React Hook Form + Zod validation

### Security (`/security`)
- Security status (email verified, MFA enabled, password last changed, recovery codes)
- Active sessions list (device, IP, last seen, expiry)
- Change password form (with confirmation + logout after change)

### Settings (`/settings`)
- Theme selection (light/dark/system)
- Notification preferences (email, in-app, push, SMS)
- Category toggles (security, achievement, marketing, reminder)
- Quiet hours (start/end time)
- Digest frequency

### MFA
- Setup MFA (QR code + recovery codes)
- Verify MFA code
- Disable MFA (requires password)
- Use recovery code

## Account Management

### Sessions
- View all active sessions
- Logout current device
- Logout all devices

### Delete Account
- Request account deletion (GDPR right to erasure)
- Grace period before anonymization
- Cancel deletion within grace period

## Data Sources

- `GET /users/me` — Current user profile + roles + permissions
- `PATCH /users/me` — Update profile
- `GET /users/me/security` — Security dashboard
- `POST /auth/change-password` — Change password
- `POST /auth/mfa/*` — MFA operations
- `POST /auth/logout` — Logout current device
- `POST /auth/logout-all` — Logout all devices
