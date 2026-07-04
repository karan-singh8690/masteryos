# Invite System

> Technical documentation for the beta invitation system.

## Overview

The invite system controls access to the Mastery Engine during closed beta. It uses cryptographically secure tokens that are validated during registration.

## Database Schema

```sql
CREATE TABLE identity.beta_invites (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL,
    invite_token    TEXT NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    used_at         TIMESTAMPTZ,
    created_by      UUID NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## Token Lifecycle

```
Created (admin creates invite)
    ↓
Valid (unused + not expired)
    ↓
Used (user registers with token)
    ↓
Invalid (cannot be reused)

OR

Created
    ↓
Valid
    ↓
Expired (past expires_at)
    ↓
Invalid (admin can resend → new token)
```

## Validation Rules

Registration with an invite token must pass ALL checks:

1. **Beta is enabled** — `CLOSED_BETA_ENABLED=true`
2. **User limit not reached** — `count(users) < MAX_BETA_USERS`
3. **Token exists** — Found in `beta_invites` table
4. **Token unused** — `used_at IS NULL`
5. **Token not expired** — `expires_at > now()`
6. **Email matches** — `invite.email == registration.email` (case-insensitive)

If any check fails, registration returns `403 BETA_REGISTRATION_DENIED` with a descriptive message.

## Admin API

### Create Invite

```
POST /api/v1/admin/beta/invites
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "email": "newuser@example.com",
  "notes": "Beta tester from Python community"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "email": "newuser@example.com",
  "invite_token": "kXp9mQ...long-token...",
  "expires_at": "2024-12-31T00:00:00Z",
  "used_at": null,
  "is_used": false,
  "is_expired": false,
  "is_valid": true
}
```

### List Invites

```
GET /api/v1/admin/beta/invites?include_used=false
```

Returns all invites (unused by default).

### Delete Invite

```
DELETE /api/v1/admin/beta/invites/{invite_id}
```

Only unused invites can be deleted.

### Resend Invite

```
POST /api/v1/admin/beta/invites/resend
{
  "invite_id": "uuid"
}
```

Generates a new token and extends the expiry. Only works for unused invites.

## Registration Integration

The registration endpoint (`POST /api/v1/auth/register`) accepts an optional `invite_token` field:

```json
{
  "email": "newuser@example.com",
  "password": "SecurePassword123!",
  "display_name": "New User",
  "invite_token": "kXp9mQ...long-token..."
}
```

When beta is enabled, the `invite_token` is required. After successful registration, the invite is marked as used (`used_at = now()`).

## Security Considerations

1. **Token generation**: Uses `secrets.token_urlsafe(32)` — 256 bits of entropy
2. **Token uniqueness**: Enforced by database unique constraint
3. **Token expiry**: Default 7 days (configurable via `BETA_INVITE_TOKEN_TTL_HOURS`)
4. **Single use**: Once `used_at` is set, the token cannot be reused
5. **Email matching**: Token is bound to a specific email address
6. **Admin-only creation**: Only authenticated admins can create invites
7. **No token enumeration**: Invalid tokens return the same error message

## Email Integration

When an invite is created, an invitation email should be sent using the `beta_invitation` template:

```python
await email_service.send_template(
    to=invite.email,
    template_name="beta_invitation",
    context={
        "register_url": f"https://app.masteryengine.com/register?token={invite.invite_token}",
        "email": invite.email,
        "expires_at": invite.expires_at.strftime("%B %d, %Y"),
    },
)
```

The `BetaInvitationEmailTemplate` is registered in the email service's template registry.
