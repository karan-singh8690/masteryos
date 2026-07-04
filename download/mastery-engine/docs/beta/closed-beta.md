# Closed Beta Platform Guide

> **Status:** v1.0 — Closed Beta configuration and operation
> **Task:** 025 — Closed Beta Platform

## Overview

The Mastery Engine supports a Closed Beta mode that restricts registration to invited users only. This is controlled by a simple configuration flag — no code changes required to enable/disable.

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `CLOSED_BETA_ENABLED` | `false` | When `true`, registration requires a valid invite token |
| `MAX_BETA_USERS` | `20` | Maximum number of registered users during closed beta |
| `BETA_INVITE_TOKEN_TTL_HOURS` | `168` (7 days) | How long invite tokens remain valid |

### Beta Feature Flags

| Flag | Default | Description |
|---|---|---|
| `BETA_FLAG_LEARNING_ENABLED` | `true` | Enable study sessions, questions, mastery |
| `BETA_FLAG_CONTENT_AUTHORING_ENABLED` | `true` | Enable content authoring portal |
| `BETA_FLAG_AI_ENABLED` | `false` | Enable AI features (explanations, coach) |
| `BETA_FLAG_NOTIFICATIONS_ENABLED` | `true` | Enable notification system |
| `BETA_FLAG_ANALYTICS_ENABLED` | `true` | Enable analytics tracking |
| `BETA_FLAG_ADMIN_CONSOLE_ENABLED` | `true` | Enable admin portal |

### Example `.env` for Closed Beta

```bash
CLOSED_BETA_ENABLED=true
MAX_BETA_USERS=20
BETA_INVITE_TOKEN_TTL_HOURS=168
BETA_FLAG_LEARNING_ENABLED=true
BETA_FLAG_CONTENT_AUTHORING_ENABLED=true
BETA_FLAG_AI_ENABLED=false
BETA_FLAG_NOTIFICATIONS_ENABLED=true
BETA_FLAG_ANALYTICS_ENABLED=true
BETA_FLAG_ADMIN_CONSOLE_ENABLED=true
```

## How It Works

### Registration Flow (Beta Enabled)

```
User receives invite email with token
        ↓
User visits /register?token=abc123
        ↓
Frontend sends: POST /api/v1/auth/register
  { email, password, display_name, invite_token: "abc123" }
        ↓
Backend checks:
  1. Is beta enabled? → Yes
  2. User count < MAX_BETA_USERS? → Yes
  3. Token valid? → Yes
  4. Token unused? → Yes
  5. Token not expired? → Yes
  6. Email matches invite? → Yes
        ↓
Registration proceeds (Argon2id + verification token)
        ↓
Invite marked as used
        ↓
Welcome email sent
        ↓
User redirected to welcome flow
```

### Registration Flow (Beta Disabled)

Standard registration — no invite token required.

### API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/beta/status` | Public | Get beta status + feature flags |
| POST | `/api/v1/beta/feedback` | User | Submit feedback |
| GET | `/api/v1/beta/feedback` | Admin | List all feedback |
| POST | `/api/v1/beta/track` | User | Track analytics event |
| GET | `/api/v1/beta/analytics` | Admin | Get beta analytics |
| POST | `/api/v1/admin/beta/invites` | Admin | Create invite |
| GET | `/api/v1/admin/beta/invites` | Admin | List invites |
| DELETE | `/api/v1/admin/beta/invites/{id}` | Admin | Delete invite |
| POST | `/api/v1/admin/beta/invites/resend` | Admin | Resend invite |

## Beta User Experience

### Beta Banner
A "Closed Beta" banner appears at the top of every page showing version + environment.

### Feedback Button
A floating feedback button (bottom-right) opens a modal with:
- Star rating (1-5)
- Category dropdown (bug, feature request, UI/UX, content, performance, other)
- Comment textarea (5000 char limit)
- Auto-captured context (browser, platform, route, correlation ID)

### Welcome Flow
First-time users see a 4-step wizard:
1. **Profile** — display name + timezone
2. **Learning Goal** — daily question target
3. **Subject Selection** — choose a subject to study
4. **Tutorial** — overview of key features

## Email Templates

| Template | Trigger | Description |
|---|---|---|
| `beta_invitation` | Admin creates invite | Sent to invitee with registration link |
| `beta_welcome` | User completes registration | Welcome + getting started guide |
| `beta_reminder` | User inactive >7 days | "We miss you" + continue learning link |

## Database Tables

### `identity.beta_invites`
| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| email | TEXT | Invitee email |
| invite_token | TEXT | Unique token (URL-safe) |
| expires_at | TIMESTAMPTZ | Token expiry |
| used_at | TIMESTAMPTZ | When used (NULL = unused) |
| created_by | UUID | Admin who created the invite |
| notes | TEXT | Admin notes |

### `identity.beta_feedback`
| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | Submitter |
| rating | INTEGER | 1-5 stars |
| category | TEXT | bug/feature_request/ui_ux/content/performance/other |
| comment | TEXT | Feedback text |
| screenshot_url | TEXT | Optional screenshot |
| correlation_id | TEXT | Request correlation ID |
| browser | TEXT | Auto-captured |
| platform | TEXT | Auto-captured |
| route | TEXT | Current route |
| status | TEXT | open/acknowledged/resolved/closed |

### `analytics.beta_events`
| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | User (nullable) |
| event_type | TEXT | Event type |
| event_data | JSONB | Event payload |
| session_id | TEXT | Study session ID |
| correlation_id | TEXT | Request correlation ID |

## Architectural Decisions

1. **Beta guard in registration endpoint** — Not middleware, because the guard needs access to the request body (invite_token) and the database (to validate the token). Placing it inside the register endpoint keeps the logic co-located with the registration flow.

2. **Invite tokens are opaque** — Using `secrets.token_urlsafe(32)` for cryptographic randomness. Tokens are stored as-is in the database (no hashing needed because they're single-use and short-lived).

3. **Feature flags via environment variables** — Simple, no database reads needed. For dynamic flag changes without restart, the frontend polls `/api/v1/beta/status` which returns current flag values.

4. **Feedback auto-captures context** — Browser, platform, route, and correlation ID are captured on the frontend and sent with the feedback. This ensures bug reports have enough context for debugging.

5. **Analytics events are append-only** — The `beta_events` table never receives UPDATE or DELETE. This ensures an accurate audit trail of user behavior during the beta.

## Transitioning Out of Beta

To open registration to the public:

1. Set `CLOSED_BETA_ENABLED=false`
2. Restart the backend
3. Registration is now open (no invite required)
4. All existing users continue to work
5. All beta data (invites, feedback, events) remains in the database

No data migration needed — the beta tables are additive.
