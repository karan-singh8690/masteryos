# Background Processing — README

> **Status:** v1.0 — Production background processing infrastructure
> **Task:** 017 — Background Processing, Outbox Dispatcher & Notification Platform

## Overview

The Mastery Engine uses an event-driven architecture where domain events flow through a transactional outbox and are processed by background workers. This decouples HTTP request handling from background work (notifications, emails, analytics, cleanup).

## Architecture

```
HTTP Request → Command Handler → Domain Aggregate → Domain Events
                                                         │
                                                         ▼
                                               Transactional Outbox
                                               (same DB transaction)
                                                         │
                                                         ▼
                                               Background Workers
                                               ┌─────────────────┐
                                               │ Outbox Dispatcher│
                                               │ Scheduler        │
                                               │ Notification Proc│
                                               │ Email Processor  │
                                               │ Cleanup Processor│
                                               └─────────────────┘
                                                         │
                                                         ▼
                                               Subscribers + Handlers
                                               (Notifications, Emails,
                                                Analytics, Scheduling)
```

## Components

| Component | Purpose | Document |
|---|---|---|
| Transactional Outbox | Stores domain events in the same transaction as the write | [outbox-pattern.md](outbox-pattern.md) |
| Outbox Dispatcher | Polls the outbox and delivers events to subscribers | [dispatcher.md](dispatcher.md) |
| Worker Host | Coordinates multiple background processors | [worker-architecture.md](worker-architecture.md) |
| Scheduler | Executes recurring jobs (cleanup, analytics) | [scheduler.md](scheduler.md) |
| Notification Service | Creates + delivers in-app + email notifications | [notifications.md](notifications.md) |
| Email Service | SMTP abstraction with templates | [email.md](email.md) |
| Dead Letter Queue | Captures unrecoverable events | [dead-letter-queue.md](dead-letter-queue.md) |
| Retry Engine | Exponential backoff for failed operations | [retry-policy.md](retry-policy.md) |
| Operations | Deployment, monitoring, troubleshooting | [operations.md](operations.md) |

## Quick Start

### Running the Worker Process

```bash
# Start the worker process (runs all background processors)
python -m app.workers.worker_main

# The worker will:
# 1. Write a heartbeat to the database every 10 seconds
# 2. Poll the outbox for pending events
# 3. Execute scheduled jobs
# 4. Process queued notifications + emails
# 5. Clean up expired data
```

### Admin API

```bash
# List all workers
curl http://localhost:8000/api/v1/admin/bg/workers

# Get background metrics
curl http://localhost:8000/api/v1/admin/bg/workers/metrics

# List outbox events
curl http://localhost:8000/api/v1/admin/bg/outbox

# Replay a failed event
curl -X POST http://localhost:8000/api/v1/admin/bg/outbox/{event_id}/replay

# List dead-lettered events
curl http://localhost:8000/api/v1/admin/bg/dead-letters

# Retry a dead-lettered event
curl -X POST http://localhost:8000/api/v1/admin/bg/dead-letters/{id}/retry

# List scheduled jobs
curl http://localhost:8000/api/v1/admin/bg/jobs

# Manually run a job
curl -X POST http://localhost:8000/api/v1/admin/bg/jobs/run -d '{"job_name": "cleanup_expired_sessions"}'
```

## Key Design Decisions

1. **At-least-once delivery**: Events may be delivered multiple times; subscribers must be idempotent.
2. **Transactional outbox**: Events are written in the same transaction as the domain change (no lost events).
3. **Visibility timeout**: Workers lease events; if a worker crashes, the lease expires and another worker picks it up.
4. **Exponential backoff**: Failed events are retried with increasing delays (1m, 5m, 15m, 1h, 6h, 24h).
5. **Dead letter queue**: Events that exhaust retries are moved to a separate table for manual inspection/replay.
6. **Heartbeat-based liveness**: Workers write heartbeats every 10 seconds; stale heartbeats indicate a crashed worker.

## Test Coverage

- 176 background processing tests (workers/)
- 259 auth + security tests (auth/, security/)
- **Total: 435 tests**

## Files

```
backend/
├── app/
│   ├── workers/                          # Worker process
│   │   ├── __init__.py
│   │   ├── host.py                       # WorkerHost + HeartbeatService
│   │   ├── outbox_dispatcher.py          # Production outbox dispatcher
│   │   ├── subscriber_registry.py        # Event type → handler registry
│   │   ├── retry_engine.py               # Exponential backoff
│   │   ├── processors.py                 # Notification + Email + Cleanup processors
│   │   ├── metrics.py                    # Background metrics collector
│   │   └── worker_main.py                # Entry point
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── orm/background.py         # 7 new ORM models
│   │   │   └── repositories/background.py # 7 new repositories
│   │   ├── notifications/service.py      # NotificationService
│   │   ├── email/service.py              # EmailService + 10 templates
│   │   ├── scheduler/processor.py        # SchedulerProcessor + 8 handlers
│   │   ├── queue/job_queue.py            # In-memory + Redis job queue
│   │   ├── redis/__init__.py             # Redis client factory
│   │   └── events/subscribers/           # Event subscriber handlers
│   └── presentation/api/v1/admin.py      # Admin API (14 endpoints)
├── tests/workers/                        # 176 tests
└── ...

infrastructure/postgres/init/03-background-tables.sql  # Migration
```
