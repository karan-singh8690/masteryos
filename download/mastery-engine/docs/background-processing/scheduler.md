# Scheduler

> **Component:** SchedulerProcessor + ScheduledJobRepository

## Overview

The scheduler executes recurring background jobs (cleanup, analytics, reminders). Jobs are defined in the `scheduled_jobs` table and executed by the `SchedulerProcessor`.

## Job Definition

```python
ScheduledJobModel(
    name="cleanup_expired_sessions",
    description="Remove expired + old revoked sessions",
    handler_name="cleanup_expired_sessions_handler",
    schedule_type="interval",     # or "cron" or "one_time"
    schedule_expr="3600",         # Every 3600 seconds (1 hour)
    status="active",              # or "paused" or "disabled"
    next_run_at=datetime.now() + timedelta(minutes=5),
    max_runtime_seconds=300,      # Kill if runs > 5 min
    retry_count=3,                # Retries on failure
)
```

## Schedule Types

### Interval

```python
schedule_type="interval"
schedule_expr="3600"  # Every 3600 seconds
```

### Cron

```python
schedule_type="cron"
schedule_expr="0 2 * * *"  # 2 AM daily (standard cron syntax)
```

### One-Time

```python
schedule_type="one_time"
schedule_expr="2024-01-15T10:00:00Z"  # Run once at this time
```

## Default Jobs

The following jobs are created at worker startup:

| Job Name | Schedule | Description |
|---|---|---|
| `cleanup_expired_sessions` | Every 1 hour | Remove expired + old revoked sessions |
| `cleanup_expired_tokens` | Every 1 hour | Remove expired verification + reset tokens |
| `cleanup_expired_refresh_tokens` | Every 1 day | Remove expired refresh tokens |
| `cleanup_expired_notifications` | Every 30 min | Mark expired notifications as failed |
| `cleanup_old_audit_logs` | Every 1 week | Delete audit logs older than 1 year |
| `heartbeat_check` | Every 1 minute | Detect dead workers + release their leases |
| `daily_analytics` | 2 AM daily | Generate daily analytics |
| `weekly_summary` | 3 AM Monday | Generate weekly summaries |

## Job Execution Flow

```
1. Poll scheduled_jobs for due, unlocked jobs
   - WHERE status='active' AND next_run_at <= now AND locked_by IS NULL
   - ORDER BY next_run_at ASC
   - LIMIT 10

2. For each due job:
   a. Acquire a lock (optimistic concurrency)
      - UPDATE scheduled_jobs SET locked_by='worker-1', lock_expires_at=now+5min
      - WHERE id=? AND (locked_by IS NULL OR lock_expires_at < now)
   b. If lock acquired:
      - Look up the handler by name
      - Execute: await handler(context)
      - Record result (success/failure, duration, error)
      - Compute next_run_at (based on schedule)
      - Release lock
   c. If lock not acquired: skip (another worker got it)
```

## Job Handlers

Job handlers are async callables registered at startup:

```python
scheduler = SchedulerProcessor(session_factory, worker_id="w1")

# Register handlers
scheduler.register_handler("cleanup_expired_sessions_handler", cleanup_handler)
scheduler.register_handler("daily_analytics_handler", analytics_handler)

# Add to worker host
host.register_processor(scheduler)
```

### Handler Signature

```python
async def my_handler(context: dict) -> dict:
    """
    Args:
        context: {
            "job_id": str,
            "job_name": str,
            "schedule_expr": str,
            "session_factory": async_sessionmaker,
        }
    Returns:
        dict with result metrics (e.g., {"deleted": 42})
    """
    session_factory = context["session_factory"]
    async with session_factory() as session:
        # Do work
        pass
    return {"deleted": 42}
```

## Job Locking

Only one worker can execute a job at a time:

```sql
-- Acquire lock
UPDATE scheduled_jobs
SET locked_by = 'worker-1', locked_at = now(), lock_expires_at = now() + interval '5 minutes'
WHERE id = ? AND (locked_by IS NULL OR lock_expires_at < now());

-- If rowcount > 0, lock acquired
```

If a worker crashes mid-execution, the lock expires (after 5 minutes) and another worker can pick it up.

## Pause / Resume

```python
# Pause a job (stops scheduling)
await repo.pause(job_id)
# status = 'paused'

# Resume a paused job
await repo.resume(job_id)
# status = 'active'
```

## Manual Execution

Via the admin API:

```bash
POST /api/v1/admin/bg/jobs/run
{"job_name": "cleanup_expired_sessions"}
```

This executes the job immediately (regardless of `next_run_at`), without acquiring a lock.

## Failure Handling

- If a handler raises an exception, `last_run_status = "failed"` and `last_run_error` is recorded.
- `consecutive_failures` is incremented.
- The job is rescheduled (next_run_at is updated).
- After 3 consecutive failures, the job is automatically paused (configurable).

## Related

- [worker-architecture.md](worker-architecture.md) — How the scheduler runs as part of the WorkerHost
- [operations.md](operations.md) — Monitoring scheduled jobs
