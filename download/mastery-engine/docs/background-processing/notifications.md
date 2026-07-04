# Notifications

> **Component:** NotificationService + NotificationProcessor + NotificationRepository

## Overview

The notification system delivers messages to users via in-app, email, push, and SMS channels. Notifications are created in response to domain events and delivered by a background processor.

## Notification Lifecycle

```
QUEUED ──mark_sent()──► SENT ──mark_delivered()──► DELIVERED
                                                       │
                                  ┌────────────────────┼────────────────────┐
                                  │                    │                    │
                                  ▼                    ▼                    ▼
                              OPENED              DISMISSED             (terminal)
                              (terminal)          (terminal)

QUEUED ──mark_failed(reason)──► FAILED  (terminal)
```

## Creating Notifications

```python
service = NotificationService(session)

result = await service.create_notification(
    user_id=user_id,
    notification_type="achievement_unlocked",
    title="Achievement Unlocked!",
    body="You mastered Python decorators.",
    channel="in_app",           # or "email", "push", "sms"
    priority="normal",          # or "low", "high", "urgent"
    category="achievement",     # for preference filtering
    payload={"achievement_id": "..."},
    dedup_key="achievement-123",  # Prevent duplicates
    related_aggregate_id=achievement_id,
    related_aggregate_type="Achievement",
)
```

## Channels

### In-App

- Stored in the `notifications` table.
- The frontend polls for unread notifications.
- Delivered instantly (marked as `sent` + `delivered` immediately).

### Email

- The `NotificationProcessor` (background worker) picks up queued email notifications.
- Looks up the user's email address.
- Renders the appropriate email template.
- Sends via the `EmailService` (SMTP).
- Records the result in `email_delivery_log`.

### Push / SMS

- Not yet implemented (future work).
- The notification is marked as `failed` with reason "Channel not supported".

## Preferences

Each user has notification preferences:

```python
NotificationPreferenceModel(
    user_id=user_id,
    email_enabled=True,
    in_app_enabled=True,
    push_enabled=False,
    sms_enabled=False,
    security_notifications_enabled=True,     # Always True (mandatory)
    achievement_notifications_enabled=True,
    marketing_notifications_enabled=False,
    reminder_notifications_enabled=True,
    digest_frequency="immediate",            # or "hourly", "daily", "weekly", "never"
    quiet_hours_start="22:00",               # HH:MM in user's timezone
    quiet_hours_end="07:00",
    timezone="America/New_York",
)
```

### Preference Checks

When creating a notification, the service checks:
1. **Channel enabled**: Is the channel (email, in_app, etc.) enabled?
2. **Category enabled**: Is the category (achievement, marketing, etc.) enabled?
3. **Quiet hours**: Is the user currently in quiet hours? (non-urgent notifications are deferred)

### Security Notifications

Security notifications (`category="security"`) bypass ALL preference checks — they are always delivered. This ensures users always receive security alerts (e.g., "New login from unknown device").

## Deduplication

Notifications can have a `dedup_key` to prevent duplicates:

```python
# This notification is created once per (user, type, dedup_key)
await service.create_notification(
    user_id=user_id,
    notification_type="review_due",
    dedup_key="concept-123-2024-01-15",  # One per concept per day
    ...
)
```

If a notification with the same `(user_id, notification_type, dedup_key)` already exists, the new one is suppressed (returns `None`).

## Priority

| Priority | Behavior |
|---|---|
| `low` | Delivered in batches (digest) |
| `normal` | Delivered immediately |
| `high` | Delivered immediately + bypasses quiet hours |
| `urgent` | Delivered immediately + bypasses ALL preferences (security alerts) |

## Expiration

Notifications can have an `expires_at` timestamp:

```python
await service.create_notification(
    ...
    expires_at=datetime.now() + timedelta(hours=24),
)
```

Expired notifications are marked as `failed` by the `cleanup_expired_notifications` scheduled job.

## Digest Notifications

Users can choose to receive notifications in digests (hourly, daily, weekly):

- `immediate`: Each notification is delivered separately.
- `hourly`: Notifications are batched into an hourly digest.
- `daily`: Notifications are batched into a daily digest.
- `weekly`: Notifications are batched into a weekly digest.
- `never`: Notifications are suppressed (only stored in-app).

Digest delivery is handled by the `NotificationProcessor` (future work — currently all notifications are delivered immediately).

## Notification Processor

The `NotificationProcessor` is a background worker that:

1. Polls `notifications` for queued, due notifications.
2. For in-app: marks as `sent` + `delivered`.
3. For email: sends via `EmailService`, records in `email_delivery_log`.
4. For push/SMS: marks as `failed` (not yet implemented).

```python
processor = NotificationProcessor(
    session_factory=session_factory,
    worker_id="notif-1",
    batch_size=50,
    email_service=email_service,
)
host.register_processor(processor)
```

## Admin API

```bash
# List all notifications
GET /api/v1/admin/bg/notifications

# Filter by status
GET /api/v1/admin/bg/notifications?status=queued

# Filter by user
GET /api/v1/admin/bg/notifications?user_id=...
```

## Related

- [email.md](email.md) — Email service + templates
- [operations.md](operations.md) — Monitoring notifications
