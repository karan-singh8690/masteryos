# Operations

> **Component:** Admin API + Metrics + Monitoring

## Admin API

### Workers

```bash
# List all workers (active + recently dead)
GET /api/v1/admin/bg/workers

# Get background metrics
GET /api/v1/admin/bg/workers/metrics
```

### Outbox

```bash
# List outbox events (filter by status, event_type)
GET /api/v1/admin/bg/outbox?status=pending&event_type=UserRegistered

# Get outbox statistics
GET /api/v1/admin/bg/outbox/stats

# Get a single outbox event
GET /api/v1/admin/bg/outbox/{event_id}

# Replay a single event (resets to pending)
POST /api/v1/admin/bg/outbox/{event_id}/replay
```

### Dead Letters

```bash
# List unresolved dead letters
GET /api/v1/admin/bg/dead-letters

# List resolved dead letters (for audit)
GET /api/v1/admin/bg/dead-letters?resolved=true

# Retry a dead-lettered event (creates a new outbox entry)
POST /api/v1/admin/bg/dead-letters/{id}/retry

# Resolve without retrying
POST /api/v1/admin/bg/dead-letters/{id}/resolve?notes=Fixed
```

### Notifications

```bash
# List all notifications (filter by status, user_id)
GET /api/v1/admin/bg/notifications?status=queued
```

### Scheduled Jobs

```bash
# List all scheduled jobs
GET /api/v1/admin/bg/jobs

# Manually run a job
POST /api/v1/admin/bg/jobs/run
{"job_name": "cleanup_expired_sessions"}

# Pause a job
POST /api/v1/admin/bg/jobs/{job_id}/pause

# Resume a paused job
POST /api/v1/admin/bg/jobs/{job_id}/resume
```

## Metrics

`GET /api/v1/admin/bg/workers/metrics` returns:

```json
{
  "outbox": {
    "pending": 5,
    "dispatched": 1234,
    "dead_lettered": 2,
    "in_progress": 1,
    "oldest_pending_age_seconds": 30.5,
    "avg_dispatch_latency_seconds": 1.2
  },
  "workers": {
    "active": 3,
    "dead": 0,
    "total_processed": 5678,
    "total_failed": 12
  },
  "retries": {
    "events_being_retried": 1
  },
  "dead_letters": {
    "unresolved": 2
  },
  "email": {
    "sent": 890,
    "failed": 3,
    "bounced": 1,
    "pending_retry": 2
  },
  "notifications": {
    "queued": 10,
    "sent": 456,
    "delivered": 450,
    "failed": 6,
    "avg_latency_seconds": 0.5
  },
  "throughput_per_minute": 12.5,
  "collected_at": "2024-01-15T10:00:00Z"
}
```

## Monitoring Checklist

### Daily Checks

- [ ] `outbox.pending` is low (< 100)
- [ ] `outbox.oldest_pending_age_seconds` is low (< 60s)
- [ ] `dead_letters.unresolved` is 0 (or being investigated)
- [ ] `workers.active` matches expected worker count
- [ ] `workers.dead` is 0
- [ ] `email.failed` rate is low (< 1%)

### Alerting Thresholds

| Metric | Warning | Critical |
|---|---|---|
| `outbox.pending` | > 100 | > 1000 |
| `outbox.oldest_pending_age_seconds` | > 60 | > 300 |
| `dead_letters.unresolved` | > 0 | > 10 |
| `workers.dead` | > 0 | > 0 (immediate) |
| `email.failed` (per hour) | > 10 | > 50 |
| `notifications.failed` (per hour) | > 5 | > 20 |

## Deployment

### Starting Workers

```bash
# Start a single worker
python -m app.workers.worker_main

# Start multiple workers (e.g., via systemd, supervisor, Kubernetes)
python -m app.workers.worker_main &  # worker-1
python -m app.workers.worker_main &  # worker-2
python -m app.workers.worker_main &  # worker-3
```

### Graceful Shutdown

Workers handle SIGTERM/SIGINT for graceful shutdown:

1. Stop accepting new work.
2. Wait for in-progress tasks (up to 30 seconds).
3. Write final heartbeat with `status="stopped"`.
4. Exit.

```bash
# Send SIGTERM
kill -TERM <worker_pid>

# Or via systemd
systemctl stop mastery-worker
```

### Health Check

Workers write heartbeats every 10 seconds. A worker is "dead" if its heartbeat is older than 60 seconds.

```bash
# Check worker health via admin API
curl http://localhost:8000/api/v1/admin/bg/workers | jq '.[] | {worker_id, status, is_stale}'
```

## Troubleshooting

### Outbox Backlog Growing

**Symptom**: `outbox.pending` is increasing over time.

**Causes**:
1. Subscribers are slow (can't keep up with event rate).
2. Subscribers are failing (events are being retried).
3. Not enough workers.

**Solutions**:
1. Check `avg_dispatch_latency_seconds` — if high, subscribers are slow.
2. Check `events_being_retried` — if high, subscribers are failing.
3. Scale up workers (add more worker processes).
4. Optimize subscribers (make them faster).

### High Dead Letter Count

**Symptom**: `dead_letters.unresolved` is increasing.

**Causes**:
1. A subscriber has a bug (always fails for certain events).
2. A subscriber is not registered.
3. Event payloads are invalid.

**Solutions**:
1. Inspect the dead letter record (`GET /api/v1/admin/bg/dead-letters/{id}`).
2. Check the `error_message` and `stack_trace`.
3. Fix the underlying issue.
4. Replay the dead-lettered events (`POST /api/v1/admin/bg/dead-letters/{id}/retry`).

### Workers Marked as Dead

**Symptom**: `workers.dead` > 0.

**Causes**:
1. Worker process crashed.
2. Worker is hung (deadlock, infinite loop).
3. Network issue (worker can't write heartbeat).

**Solutions**:
1. Check worker logs for errors.
2. Restart the worker process.
3. If the worker was processing an event, the lease will expire (after 30s) and another worker will pick it up.

### Email Delivery Failures

**Symptom**: `email.failed` rate is high.

**Causes**:
1. SMTP server is down.
2. SMTP credentials are invalid.
3. Recipient email is invalid (hard bounce).
4. Rate limit exceeded.

**Solutions**:
1. Check `email_delivery_log.error_message` for details.
2. Verify SMTP configuration (`SMTP_HOST`, `SMTP_PORT`, etc.).
3. For hard bounces: mark the user's email as undeliverable.
4. For rate limit: increase `rate_limit_per_minute` or scale up email workers.

## Backup + Recovery

### Database Backup

The outbox, dead letters, notifications, and audit logs are in PostgreSQL. Standard PostgreSQL backup procedures apply:

```bash
pg_dump mastery_engine > backup.sql
```

### Event Replay

If subscribers miss events (e.g., during a deployment), events can be replayed:

```python
# Replay all events of a type
await dispatcher.replay_events(event_type="UserRegistered")

# Replay events in a date range
await dispatcher.replay_events(from_date=datetime(2024, 1, 1))
```

## Related

- [worker-architecture.md](worker-architecture.md) — Worker process details
- [dead-letter-queue.md](dead-letter-queue.md) — Dead letter handling
- [outbox-pattern.md](outbox-pattern.md) — Outbox pattern
