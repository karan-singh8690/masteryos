# 09 — Webhooks

> Webhook contracts for partner integrations, signing, verification, retry.

---

## 1. Webhook Overview

Webhooks deliver domain events to partner endpoints (e.g., an organization's LMS, a partner analytics platform). Webhooks are HTTP POST requests with a JSON payload, signed by the platform.

### When Webhooks Are Used

Webhooks are for **external** consumers (partners, integrations). Internal consumers use the outbox + event bus (per Task 005). Webhooks are not for the frontend (the frontend uses the API directly or WebSocket for real-time updates).

### Subscribing to Webhooks

Partners register a webhook URL via the admin portal (or a future `/webhooks/subscriptions` endpoint). They select which event types to receive.

---

## 2. Webhook Events

### AchievementUnlocked

```json
{
  "event_type": "achievement_unlocked",
  "event_id": "550e8400-...",
  "created_at": "2026-07-02T14:30:00Z",
  "data": {
    "user_id": "...",
    "learner_enrollment_id": "...",
    "subject_id": "...",
    "achievement_type_code": "first_concept_mastered",
    "category": "milestone",
    "awarded_at": "2026-07-02T14:30:00Z"
  }
}
```

### SubscriptionUpdated

```json
{
  "event_type": "subscription_updated",
  "event_id": "...",
  "created_at": "...",
  "data": {
    "user_id": "...",
    "subscription_id": "...",
    "old_plan": "free",
    "new_plan": "pro",
    "status": "active",
    "updated_at": "..."
  }
}
```

### OrganizationEvent

```json
{
  "event_type": "organization_member_added",
  "event_id": "...",
  "created_at": "...",
  "data": {
    "organization_id": "...",
    "user_id": "...",
    "role": "member",
    "added_at": "..."
  }
}
```

### ContentPublished

```json
{
  "event_type": "content_published",
  "event_id": "...",
  "created_at": "...",
  "data": {
    "subject_id": "...",
    "content_version_id": "...",
    "version_number": 3,
    "published_at": "..."
  }
}
```

### AlgorithmVersionReleased

```json
{
  "event_type": "algorithm_version_released",
  "event_id": "...",
  "created_at": "...",
  "data": {
    "algorithm_version_id": "...",
    "version_number": 2,
    "previous_version_number": 1,
    "released_at": "..."
  }
}
```

### NotificationDelivered

```json
{
  "event_type": "notification_delivered",
  "event_id": "...",
  "created_at": "...",
  "data": {
    "user_id": "...",
    "notification_id": "...",
    "notification_type": "review_reminder",
    "channel": "email",
    "delivered_at": "..."
  }
}
```

---

## 3. Signing

Every webhook is signed with HMAC-SHA256 using the partner's webhook secret.

### Headers

| Header | Description |
|---|---|
| `X-Webhook-Id` | Unique event ID (UUID). |
| `X-Webhook-Timestamp` | Unix timestamp (seconds). |
| `X-Webhook-Signature` | `HMAC-SHA256(secret, "{timestamp}.{body}")` in hex. |
| `X-Webhook-Event-Type` | Event type (e.g., `achievement_unlocked`). |

### Verification (Partner Side)

```python
import hmac, hashlib, time

def verify_webhook(body, signature, timestamp, secret, tolerance=300):
    if abs(time.time() - int(timestamp)) > tolerance:
        raise ValueError("Timestamp out of tolerance")
    expected = hmac.new(
        secret.encode(),
        f"{timestamp}.{body}".encode(),
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Invalid signature")
```

### Timestamp Tolerance

Partners should reject webhooks with timestamps > 5 minutes old (replay attack prevention).

---

## 4. Retry Strategy

- **Delivery**: the platform POSTs to the partner's URL; expects `2xx` within 10 seconds.
- **Retry on failure** (non-2xx or timeout): exponential backoff.
- **Retry schedule**: 1m, 5m, 30m, 2h, 6h, 12h, 24h (7 attempts over 24 hours).
- **Dead-letter**: after 7 failures, the webhook is marked `failed`; the partner is notified (email) and can manually retry via the admin portal.

---

## 5. Idempotency

Partners must handle webhooks idempotently (the platform may retry on timeout, even if the partner already processed the webhook). The `X-Webhook-Id` header is the deduplication key.

---

## 6. Ordering

Webhooks for the same aggregate (e.g., the same user's achievements) are delivered in order. Webhooks for different aggregates may arrive out of order. Partners should not assume global ordering.

---

## 7. Webhook Management

### Subscribe

Partners register webhook URLs via the admin portal (future: `/webhooks/subscriptions` endpoint).

### List Deliveries

```
GET /webhooks/events?event_type=achievement_unlocked
```

Returns recent deliveries with status (delivered/failed).

### Retry a Failed Delivery

```
POST /webhooks/events/{event_id}/retry
```

Re-sends the webhook.

---

*End of Webhooks.*
