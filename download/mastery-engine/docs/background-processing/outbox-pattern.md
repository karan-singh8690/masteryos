# Transactional Outbox Pattern

> **ADR:** ADR-0012 — Transactional Outbox
> **Component:** OutboxEventModel + OutboxDispatcherProcessor

## Overview

The transactional outbox pattern ensures domain events are reliably delivered to subscribers, even if the message broker or subscriber is temporarily unavailable.

## Problem

Without the outbox pattern:
1. A command handler writes to the database.
2. The handler publishes events to a message broker.
3. If step 2 fails, the events are lost (the database write already committed).

This leads to inconsistency between the database state and the event-driven side effects.

## Solution

With the outbox pattern:
1. A command handler writes to the database **and** to the outbox table **in the same transaction**.
2. A background dispatcher polls the outbox and delivers events to subscribers.
3. If delivery fails, the event remains in the outbox and is retried.

```
┌─────────────┐
│ HTTP Request│
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│ Command Handler                 │
│  1. Modify domain aggregate     │
│  2. Collect domain events       │
│  3. Write to outbox (same txn)  │
│  4. Commit transaction          │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Database (single transaction)   │
│  - users table (modified)       │
│  - outbox_events table (new)    │
└─────────────────────────────────┘
       │
       ▼ (async, separate process)
┌─────────────────────────────────┐
│ Outbox Dispatcher               │
│  1. Poll outbox for pending     │
│  2. Acquire lease (visibility)  │
│  3. Deliver to subscribers      │
│  4. Mark as dispatched          │
│  5. Release lease               │
└─────────────────────────────────┘
```

## Outbox Table Schema

```sql
CREATE TABLE infrastructure.outbox_events (
    id                      UUID PRIMARY KEY,
    event_type              VARCHAR(100) NOT NULL,
    aggregate_id            UUID NOT NULL,
    aggregate_type          VARCHAR(50) NOT NULL,
    actor_user_id           UUID,
    payload                 JSONB NOT NULL,
    payload_schema_version  VARCHAR(10) NOT NULL DEFAULT '1',
    originating_schema      VARCHAR(50) NOT NULL,
    status                  VARCHAR(20) NOT NULL DEFAULT 'pending',
    dispatch_attempt_count  INTEGER NOT NULL DEFAULT 0,
    last_dispatch_error     TEXT,
    dispatched_at           TIMESTAMPTZ,
    -- Task 017 additions:
    leased_until            TIMESTAMPTZ,  -- Visibility timeout
    leased_by               VARCHAR(100), -- Worker that holds the lease
    next_retry_at           TIMESTAMPTZ,  -- When to retry (after backoff)
    retry_history           JSONB NOT NULL DEFAULT '[]',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_outbox_status CHECK (status IN ('pending', 'dispatched', 'dead_lettered'))
);
```

## Key Features

### 1. Atomic Write

Events are written in the same transaction as the domain change. If the transaction commits, the event is guaranteed to be in the outbox.

### 2. At-Least-Once Delivery

Events may be delivered multiple times (e.g., if a worker crashes after delivering but before marking as dispatched). Subscribers must be idempotent.

### 3. Visibility Timeout (Lease)

When a worker picks up an event, it acquires a lease (default 30 seconds). Other workers skip leased events. If the worker crashes, the lease expires and another worker can pick it up.

### 4. Retry with Exponential Backoff

Failed events are retried with increasing delays:
- Attempt 1 fails → retry after 1 minute
- Attempt 2 fails → retry after 5 minutes
- Attempt 3 fails → retry after 15 minutes
- Attempt 4 fails → retry after 1 hour
- Attempt 5 fails → retry after 6 hours
- Attempt 6 fails → dead-lettered

### 5. Dead Letter Queue

After 6 failed attempts, the event is moved to `dead_letter_events` for manual inspection/replay.

### 6. Ordering Guarantees

Events are processed in `created_at` order (oldest first). Per-aggregate ordering is maintained because events are delivered one at a time.

## Worker Locking

Multiple workers can poll the outbox concurrently. On PostgreSQL, `SELECT FOR UPDATE SKIP LOCKED` ensures:
- Each event is claimed by exactly one worker.
- Other workers skip locked events (no blocking).

On SQLite (tests), a simpler approach is used (no row locking).

## Replay Support

Events can be replayed for recovery or new-subscriber backfill:

```python
# Replay a single event
await dispatcher.replay_event(event_id)

# Replay all events of a type
await dispatcher.replay_events(event_type="UserRegistered")

# Replay events in a date range
await dispatcher.replay_events(from_date=datetime(2024, 1, 1))

# Replay a dead-lettered event
await dispatcher.replay_dead_letter(dead_letter_id)
```

## Metrics

- `outbox_pending` — Count of pending events
- `outbox_dispatched` — Count of dispatched events
- `outbox_dead_lettered` — Count of dead-lettered events
- `outbox_in_progress` — Count of leased events (being processed)
- `outbox_oldest_pending_age_seconds` — Age of the oldest pending event
- `avg_dispatch_latency_seconds` — Average time from creation to dispatch
- `throughput_per_minute` — Events dispatched per minute

## Related

- [dispatcher.md](dispatcher.md) — The dispatcher implementation
- [dead-letter-queue.md](dead-letter-queue.md) — Handling unrecoverable events
- [retry-policy.md](retry-policy.md) — Retry schedule + backoff
