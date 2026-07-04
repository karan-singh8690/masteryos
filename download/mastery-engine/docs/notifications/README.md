# Notifications Documentation

> **Status:** v1.0 — Notification system documentation
> **Task:** 017

## Overview

This directory contains documentation for the notification system, which delivers messages to users via in-app, email, push, and SMS channels.

## Documents

- See [../background-processing/notifications.md](../background-processing/notifications.md) for the full notification system documentation.

## Quick Reference

### Notification Channels

| Channel | Status | Description |
|---|---|---|
| `in_app` | ✅ Implemented | Stored in DB; frontend polls |
| `email` | ✅ Implemented | Sent via SMTP (EmailService) |
| `push` | 🚧 Future | Not yet implemented |
| `sms` | 🚧 Future | Not yet implemented |

### Notification Categories

| Category | Bypasses Preferences | Description |
|---|---|---|
| `security` | ✅ Yes | Security alerts (mandatory) |
| `achievement` | ❌ No | Achievement unlocked |
| `marketing` | ❌ No | Marketing (opt-in) |
| `reminder` | ❌ No | Review reminders |
| `system` | ❌ No | System notifications |

### Priorities

| Priority | Bypasses Quiet Hours | Description |
|---|---|---|
| `low` | ❌ No | Low priority (digest) |
| `normal` | ❌ No | Standard priority |
| `high` | ❌ No | High priority |
| `urgent` | ✅ Yes | Urgent (bypasses quiet hours) |

### API Endpoints

```
GET  /api/v1/admin/bg/notifications          # List all notifications
```

### Creating Notifications

```python
from app.infrastructure.notifications.service import NotificationService

service = NotificationService(session)
await service.create_notification(
    user_id=user_id,
    notification_type="achievement_unlocked",
    title="Achievement Unlocked!",
    body="You mastered Python decorators.",
    channel="in_app",
    category="achievement",
    priority="normal",
    dedup_key="achievement-123",
)
```
