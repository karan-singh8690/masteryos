# Outbox Dispatcher

> **Component:** OutboxDispatcherProcessor

## Overview

The OutboxDispatcherProcessor is a background worker that polls the outbox table and delivers events to registered subscribers.

## Configuration

```python
dispatcher = OutboxDispatcherProcessor(
    session_factory=session_factory,
    worker_id="worker-1",
    batch_size=100,             # Events per batch
    visibility_timeout=30s,     # Lease duration
    max_retries=6,              # Before dead-lettering
)
```

## Polling Loop

```
1. Reclaim expired leases (from crashed workers)
2. Acquire a batch of pending events (with lease)
   - SELECT ... FOR UPDATE SKIP LOCKED (PostgreSQL)
   - Filter: status='pending' AND (leased_until IS NULL OR leased_until < now)
   - Filter: next_retry_at IS NULL OR next_retry_at <= now
   - Order by created_at ASC
   - Limit by batch_size
3. For each event:
   a. Deliver to all registered subscribers
   b. On success: mark as 'dispatched', release lease
   c. On failure: increment attempt_count, schedule retry (or dead-letter)
4. Commit transaction
5. If no events processed: sleep 1 second
6. Repeat
```

## Subscriber Registration

```python
dispatcher = OutboxDispatcherProcessor(session_factory, worker_id="w1")

# Register a subscriber for an event type
dispatcher.subscribe("UserRegistered", send_verification_email)
dispatcher.subscribe("UserRegistered", send_welcome_email)
dispatcher.subscribe("AttemptRecorded", update_mastery)

# With a custom handler name (for logging)
dispatcher.subscribe("SecurityIncidentDetected", alert_security_team, "alert_security")
```

## Event Delivery

When an event is dispatched, ALL registered subscribers are called in sequence:

```python
for handler_name, handler in self._subscribers[event.event_type]:
    await handler(event.payload)  # If this raises, the event fails
```

If ANY subscriber fails, the entire event is marked as failed and retried. On retry, ALL subscribers are called again (this is why subscribers must be idempotent).

### Why Not Per-Subscriber Retry?

Per-subscriber retry would require tracking which subscribers succeeded. This adds complexity:
- Need a separate table for subscriber-level state.
- Need to skip already-succeeded subscribers on retry.
- Need to handle partial failures.

The simpler approach (retry the entire event) is preferred. Subscribers must be idempotent anyway (at-least-once delivery).

## Lease Management

### Acquiring a Lease

```python
# UPDATE outbox_events SET leased_by='worker-1', leased_until=now+30s
# WHERE id IN (selected event IDs)
```

### Releasing a Lease

On success:
```python
# UPDATE outbox_events SET leased_by=NULL, leased_until=NULL, status='dispatched'
# WHERE id = ?
```

On failure:
```python
# UPDATE outbox_events SET leased_by=NULL, leased_until=NULL,
#   dispatch_attempt_count = attempt_count + 1,
#   next_retry_at = now + backoff_delay
# WHERE id = ?
```

### Reclaiming Expired Leases

If a worker crashes mid-processing, its lease will expire. The dispatcher reclaims these:

```python
# Find leases where expires_at < now AND released_at IS NULL
# Mark them as 'timed_out'
# Reset the outbox event's leased_until so it can be re-acquired
```

## Failure Handling

### Subscriber Raises Exception

```python
try:
    await handler(event.payload)
except Exception as exc:
    # Propagate to failure handler
    raise
```

The failure handler:
1. Increments `dispatch_attempt_count`.
2. Records the error in `retry_history` (JSONB).
3. Schedules `next_retry_at` using exponential backoff.
4. If `attempt_count >= max_retries`: moves to dead-letter queue.

### Dead Lettering

After 6 failed attempts, the event is moved to `dead_letter_events`:

```python
DeadLetterEventModel(
    original_event_id=event.id,
    event_type=event.event_type,
    payload=event.payload,
    error_message=str(error),
    error_type=type(error).__name__,
    stack_trace=traceback.format_exc(),
    retry_count=event.dispatch_attempt_count,
    retry_history=event.retry_history,
    final_worker_id=self.worker_id,
    severity="error",  # or "critical" for security events
)
```

The outbox event is marked as `dead_lettered` (not deleted — for audit trail).

## Replay

### Replay a Single Event

```python
await dispatcher.replay_event(event_id)
# Resets: status='pending', attempt_count=0, next_retry_at=NULL, retry_history=[]
```

### Replay by Criteria

```python
await dispatcher.replay_events(
    event_type="UserRegistered",
    from_date=datetime(2024, 1, 1),
    to_date=datetime(2024, 1, 31),
)
```

### Replay a Dead-Lettered Event

```python
await dispatcher.replay_dead_letter(dead_letter_id)
# Creates a NEW outbox event (with a new ID) from the dead letter record
# Marks the dead letter as resolved
```

## Metrics

See [operations.md](operations.md) for the full metrics list.

## Related

- [outbox-pattern.md](outbox-pattern.md) — The pattern
- [retry-policy.md](retry-policy.md) — Retry schedule
- [dead-letter-queue.md](dead-letter-queue.md) — Dead letter handling
