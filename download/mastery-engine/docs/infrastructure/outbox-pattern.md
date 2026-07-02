# Outbox Pattern

> How the transactional outbox ensures reliable domain event delivery.

---

## Problem

When a command handler updates the database and then publishes an event, two things can go wrong:
1. **Database commit succeeds, event publish fails** — the event is lost; subscribers never see it.
2. **Event publish succeeds, database commit fails** — subscribers see an event for a change that didn't happen.

The transactional outbox pattern solves both by writing the event to the database in the same transaction as the domain changes.

## Solution

```
1. Begin transaction
2. UPDATE domain tables (users, attempts, mastery_scores, etc.)
3. INSERT event into outbox_events table (same transaction)
4. COMMIT transaction (both domain changes and event are durable)
5. Background dispatcher polls outbox → delivers to subscribers
6. Dispatcher marks event as dispatched
```

If step 4 fails, both the domain changes and the event are rolled back — no inconsistency.

If step 5 fails (dispatcher down), events accumulate in the outbox and are delivered when the dispatcher resumes.

## Outbox Table

```sql
CREATE TABLE infrastructure.outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,              -- e.g., "AttemptRecorded"
    aggregate_id UUID NOT NULL,            -- the aggregate's UUID
    aggregate_type TEXT NOT NULL,          -- e.g., "Attempt"
    actor_user_id UUID,                    -- who triggered the event
    payload JSONB NOT NULL,               -- serialized event data
    payload_schema_version TEXT NOT NULL DEFAULT '1',
    originating_schema TEXT NOT NULL,      -- which context raised it
    status TEXT NOT NULL DEFAULT 'pending', -- pending/dispatched/dead_lettered
    dispatch_attempt_count INTEGER NOT NULL DEFAULT 0,
    last_dispatch_error TEXT,
    dispatched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## Event Serialization

Events are serialized to JSON via `EventSerializer`:

```json
{
  "event_type": "AttemptRecorded",
  "event_id": "550e8400-...",
  "occurred_at": "2026-07-02T14:30:00+00:00",
  "aggregate_id": "660e8400-...",
  "payload": {
    "attempt_id": "660e8400-...",
    "learner_enrollment_id": "770e8400-...",
    "scoring_outcome": "correct",
    "content_version_id": "880e8400-...",
    "template_version_id": "990e8400-...",
    "algorithm_version_id": "aa0e8400-...",
    "hint_used": false,
    "attempt_intent": "practice"
  },
  "payload_schema_version": "1",
  "metadata": {
    "actor_user_id": "bb0e8400-...",
    "correlation_id": "cc0e8400-...",
    "originating_schema": "assessment"
  }
}
```

## Dispatcher

The `OutboxDispatcher` runs as a background worker:

1. **Poll**: `SELECT * FROM outbox_events WHERE status = 'pending' ORDER BY created_at LIMIT 100`
2. **Deliver**: for each event, call registered subscriber handlers.
3. **Ack**: `UPDATE outbox_events SET status = 'dispatched', dispatched_at = now()`
4. **Retry**: on failure, increment `dispatch_attempt_count`; after 5 attempts, mark as `dead_lettered`.

### Subscriber Registration

```python
dispatcher.subscribe("AttemptRecorded", mastery_update_handler)
dispatcher.subscribe("AttemptRecorded", analytics_handler)
dispatcher.subscribe("MasteryUpdated", scheduler_queue_regenerator)
```

### Replay

The dispatcher supports replay for recovery or new subscriber backfill:

```python
await dispatcher.replay_events(
    event_type="AttemptRecorded",
    from_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
)
```

## Delivery Guarantees

- **At-least-once**: events may be delivered multiple times (dispatcher retry, subscriber restart).
- **Idempotent subscribers**: subscribers must handle redelivery gracefully (dedup by event_id).
- **Ordering**: events for the same aggregate are delivered in creation order (dispatcher processes in `created_at` order).
- **No global ordering**: events for different aggregates may arrive out of order.
