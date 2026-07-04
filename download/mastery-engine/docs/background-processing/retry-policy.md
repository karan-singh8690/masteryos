# Retry Policy

> **Component:** RetryEngine + RETRY_SCHEDULE

## Overview

Failed operations are retried with exponential backoff. The retry schedule is designed to balance:
- **Fast recovery** for transient failures (1 minute)
- **Avoiding thundering herd** (jitter)
- **Eventual resolution** (24 hours max)
- **Dead-lettering** unrecoverable events (after 6 retries)

## Retry Schedule

The default schedule (per Task 017 spec):

| Attempt | Delay | Cumulative |
|---|---|---|
| 1 (initial) | — | 0 |
| 2 (retry 1) | 1 minute | 1 min |
| 3 (retry 2) | 5 minutes | 6 min |
| 4 (retry 3) | 15 minutes | 21 min |
| 5 (retry 4) | 1 hour | 1h 21min |
| 6 (retry 5) | 6 hours | 7h 21min |
| 7 (retry 6) | 24 hours | 31h 21min |
| 8 | — | **Dead-lettered** |

```python
RETRY_SCHEDULE = [
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
    timedelta(hours=6),
    timedelta(hours=24),
]
```

## Jitter

To avoid thundering herd (all retries happening at the same time), ±10% jitter is added to each delay:

```python
import random
jitter_factor = 0.9 + (random.random() * 0.2)  # 0.9 to 1.1
delay = base_delay * jitter_factor
```

Jitter can be disabled (for deterministic tests):

```python
engine = RetryEngine(jitter=False)
```

## RetryEngine

### Inline Retries (Blocking)

For cases where the caller can block (e.g., a worker processing a job):

```python
engine = RetryEngine()

result = await engine.execute_with_retry(
    func=my_async_func,
    args=(arg1, arg2),
    kwargs={"key": "value"},
    retryable_exceptions=(ValueError, ConnectionError),
)

if not result.success:
    # Move to dead letter queue
    ...
```

### Compute Next Retry Time (Non-Blocking)

For the outbox dispatcher (which schedules retries via `next_retry_at`):

```python
engine = RetryEngine()

if engine.should_retry(attempt_count):
    next_retry = engine.get_next_retry_time(attempt_count)
    # UPDATE outbox_events SET next_retry_at = next_retry WHERE id = ?
```

## Fast Retry Schedule

For transient failures (e.g., SMTP), a faster schedule is used:

```python
FAST_RETRY_SCHEDULE = [
    timedelta(seconds=5),
    timedelta(seconds=30),
    timedelta(minutes=2),
    timedelta(minutes=10),
    timedelta(hours=1),
]
```

```python
email_retry_engine = RetryEngine(schedule=FAST_RETRY_SCHEDULE)
```

## Custom Schedules

```python
custom_engine = RetryEngine(
    schedule=[
        timedelta(seconds=1),
        timedelta(seconds=10),
        timedelta(minutes=1),
    ],
    max_retries=3,
    jitter=False,
)
```

## Retryable Exceptions

Not all exceptions should be retried. For example:
- `ValueError` (invalid input) → Retry (might be transient)
- `ConnectionError` (network issue) → Retry (definitely transient)
- `TypeError` (programming error) → Don't retry (won't fix itself)

```python
result = await engine.execute_with_retry(
    func=my_func,
    retryable_exceptions=(ValueError, ConnectionError, TimeoutError),
)
```

Non-retryable exceptions propagate immediately (the function raises).

## Retry History

Each retry is recorded in the event's `retry_history` (JSONB):

```json
[
  {
    "attempt": 1,
    "timestamp": "2024-01-15T10:00:00Z",
    "error": "Connection refused",
    "error_type": "ConnectionError",
    "worker_id": "worker-1"
  },
  {
    "attempt": 2,
    "timestamp": "2024-01-15T10:01:00Z",
    "error": "Connection refused",
    "error_type": "ConnectionError",
    "worker_id": "worker-2"
  }
]
```

This history is stored in both `outbox_events.retry_history` and `dead_letter_events.retry_history`.

## Max Retries

The default `max_retries` is 6 (matching the schedule length). After 6 retries, the event is dead-lettered.

```python
engine = RetryEngine(max_retries=3)  # Only 3 retries
```

## Related

- [outbox-pattern.md](outbox-pattern.md) — Where retries happen
- [dead-letter-queue.md](dead-letter-queue.md) — What happens after max retries
- [dispatcher.md](dispatcher.md) — The dispatcher that schedules retries
