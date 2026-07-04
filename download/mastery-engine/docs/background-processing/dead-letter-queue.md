# Dead Letter Queue

> **Component:** DeadLetterEventModel + DeadLetterEventRepository

## Overview

The dead letter queue (DLQ) captures events that have exhausted all retry attempts. These events require manual inspection and either replay or resolution.

## When Events Are Dead-Lettered

An event is moved to the DLQ after `max_retries` (default: 6) failed dispatch attempts:

| Attempt | Delay | Action |
|---|---|---|
| 1 | 1 minute | Retry |
| 2 | 5 minutes | Retry |
| 3 | 15 minutes | Retry |
| 4 | 1 hour | Retry |
| 5 | 6 hours | Retry |
| 6 | 24 hours | Retry |
| 7 | — | **Dead-letter** |

## Dead Letter Record

```sql
CREATE TABLE infrastructure.dead_letter_events (
    id                      UUID PRIMARY KEY,
    original_event_id       UUID NOT NULL,      -- The outbox event ID
    event_type              VARCHAR(100) NOT NULL,
    aggregate_id            UUID NOT NULL,
    aggregate_type          VARCHAR(50) NOT NULL,
    actor_user_id           UUID,
    payload                 JSONB NOT NULL,     -- Original event payload
    originating_schema      VARCHAR(50) NOT NULL,
    error_message           TEXT NOT NULL,      -- Final error
    error_type              VARCHAR(200) NOT NULL,
    stack_trace             TEXT,               -- Full traceback
    retry_count             INTEGER NOT NULL,
    retry_history           JSONB NOT NULL,     -- [{attempt, timestamp, error}, ...]
    subscriber_handler      VARCHAR(255),
    final_worker_id         VARCHAR(100),
    severity                VARCHAR(20) NOT NULL DEFAULT 'error',
    resolved_at             TIMESTAMPTZ,
    resolved_by             UUID,
    resolution_notes        TEXT,
    replayed_as_event_id    UUID,               -- If replayed, the new event ID
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## Severity Levels

| Severity | Use Case |
|---|---|
| `warning` | Transient failures (e.g., email verification, password reset) |
| `error` | Standard failures (most events) |
| `critical` | Security events (e.g., `SecurityIncidentDetected`, `RefreshTokenReuseDetected`) |

Critical dead letters should be investigated immediately.

## Admin API

### List Dead Letters

```bash
# List unresolved dead letters (default)
GET /api/v1/admin/bg/dead-letters

# List resolved dead letters (for audit)
GET /api/v1/admin/bg/dead-letters?resolved=true

# Filter by event type
GET /api/v1/admin/bg/dead-letters?event_type=UserRegistered
```

### Retry a Dead Letter

```bash
POST /api/v1/admin/bg/dead-letters/{id}/retry
```

This creates a NEW outbox event (with a new ID) from the dead letter record. The dead letter is marked as resolved with `replayed_as_event_id` pointing to the new event.

### Resolve (Without Retry)

```bash
POST /api/v1/admin/bg/dead-letters/{id}/resolve?notes=Fixed%20in%20v1.2.3
```

Use this when the event should not be retried (e.g., the underlying issue has been resolved, or the event is no longer relevant).

## Replay Process

```
1. Admin calls POST /api/v1/admin/bg/dead-letters/{id}/retry

2. Dispatcher:
   a. Reads the dead letter record
   b. Creates a new outbox event with the same payload
   c. Marks the dead letter as resolved:
      - resolved_at = now()
      - replayed_as_event_id = new_event.id
   d. Commits

3. The new outbox event is picked up by the dispatcher on the next poll.
   (It goes through the normal dispatch + retry flow.)
```

## Automatic Cleanup

The `cleanup_old_audit_logs` scheduled job deletes resolved dead letters older than 1 year (configurable).

## Monitoring

Metrics exposed via `GET /api/v1/admin/bg/workers/metrics`:

```json
{
  "dead_letters": {
    "unresolved": 5
  }
}
```

A high `unresolved` count indicates a systemic issue (e.g., a subscriber is broken).

## Common Causes

| Cause | Resolution |
|---|---|
| Subscriber raises exception | Fix the subscriber bug, then replay |
| Database connection issue | Transient — replay after the issue is resolved |
| Invalid event payload | Fix the payload in the dead letter record, then replay |
| Subscriber not registered | Register the subscriber, then replay |
| Poison message (always fails) | Resolve without retry; investigate the root cause |

## Related

- [outbox-pattern.md](outbox-pattern.md) — Where dead-lettered events come from
- [retry-policy.md](retry-policy.md) — The retry schedule that precedes dead-lettering
- [operations.md](operations.md) — Monitoring + troubleshooting
