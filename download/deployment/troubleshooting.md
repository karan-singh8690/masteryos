# Troubleshooting Guide — Mastery Engine Closed Beta

> **Audience:** On-call SRE, support engineer.
> **Scope:** Resolution procedures for every failure mode observed or anticipated in the Closed Beta.
> **Last updated:** 2026-07-03

---

## 0. How To Use This Document

Each section is structured as:

1. **Symptom** — what you observe
2. **Likely cause** — ranked by probability
3. **Diagnosis** — exact commands to confirm
4. **Fix** — step-by-step resolution
5. **Prevention** — how to avoid recurrence

If multiple symptoms match, start with the highest-probability cause.

---

## 1. Container Issues

### 1.1 Symptom: Container exits immediately after start

**Likely cause:**
1. Missing required env var (`${VAR:?}` guard in compose)
2. Missing required file mount (e.g. JWT keys, TLS certs)
3. Application startup exception

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml logs <service-name> --tail 100
```

**Fix:**

- **Missing env var**: compose prints `Set DATABASE_PASSWORD` (or similar). Set the variable in `.env.production` and restart.
- **Missing file mount**:
  ```bash
  # Check what's expected
  docker compose -f docker-compose.prod.yml config | grep -A5 volumes
  # Verify the file exists
  ls -la keys/ infrastructure/nginx/ssl/
  ```
- **Application exception**: read the stack trace. Common causes:
  - `JWT_KEYS_DIR` set but `/app/keys/jwt-private.pem` missing → generate keys per `deployment-checklist.md` §3.3
  - `init_database()` failure → DB not reachable or schema permissions wrong

### 1.2 Symptom: Container status `Up (unhealthy)`

**Likely cause:**
1. Healthcheck command fails (curl missing, endpoint wrong)
2. Service is alive but a dependency is down

**Diagnosis:**
```bash
# Check the last healthcheck result
docker inspect --format '{{json .State.Health}}' <container-name> | jq

# Run the healthcheck command manually
docker compose -f docker-compose.prod.yml exec <service> <healthcheck-cmd>
```

**Fix:**

- **Curl missing in image** (the most common cause for backend/frontend): override the healthcheck per `deployment-checklist.md` §4.3.
- **Endpoint wrong**: verify the path. Backend health is at `/api/v1/health/ready`, frontend at `/api/v1/health`.
- **Dependency down**: fix the dependency first (e.g. Postgres down → backend unhealthy).

### 1.3 Symptom: Container OOM-killed

**Likely cause:**
1. Memory leak in the application
2. Container memory limit too low
3. Postgres `shared_buffers` + connection pool too large for the host

**Diagnosis:**
```bash
# Check OOM kills
docker compose -f docker-compose.prod.yml ps -a | grep -i exited
docker inspect <container> | grep -i oomkilled

# Check current memory usage
docker stats --no-stream
```

**Fix:**
- Raise the memory limit in `docker-compose.prod.yml` for the affected service.
- For Postgres: if `shared_buffers=1GB` + `max_connections=200 × work_mem=16MB` exceeds host RAM, reduce `work_mem` to `8MB` in `postgresql.conf`.
- For backend: look for memory leaks (unclosed SQLAlchemy sessions, growing caches). Check Sentry for `MemoryError`.

### 1.4 Symptom: Container restarts in a loop

**Likely cause:**
1. Startup exception that exits the process
2. Healthcheck failing repeatedly causing compose to restart
3. Dependency flapping (e.g. Postgres restarting)

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml events --since 30m
```

**Fix:**
- Read the logs of the restarting container to find the exception.
- If the dependency is flapping, fix that first.
- If healthcheck is the cause, the service is actually running but failing the check — override the healthcheck (§1.2).

---

## 2. Backend Issues

### 2.1 Symptom: Backend returns 502 Bad Gateway

**Likely cause:**
1. Backend container is down
2. Backend is up but uvicorn worker died
3. Nginx can't reach the backend on the docker network

**Diagnosis:**
```bash
# 1. Is the container up?
docker compose -f docker-compose.prod.yml ps backend

# 2. Can nginx reach it?
docker compose -f docker-compose.prod.yml exec nginx curl -sf http://backend:8000/api/v1/health

# 3. Backend logs
docker compose -f docker-compose.prod.yml logs backend --tail 50
```

**Fix:**
- Container down: `docker compose -f docker-compose.prod.yml up -d backend`
- Uvicorn worker died: restart the container; investigate the stack trace in logs.
- Network issue: `docker network inspect masteryengine_default` — verify both nginx and backend are on the same network.

### 2.2 Symptom: Backend returns 503 Service Unavailable

**Likely cause:**
1. AI endpoint hit when `AI_ENABLED=false`
2. Rate limiter returning 503 (unlikely — should be 429)
3. Backend startup not complete

**Diagnosis:**
```bash
# Check the response body for a hint
curl -v https://app.masteryengine.com/api/v1/ai/explain 2>&1 | head -30
```

**Fix:**
- If AI: enable `AI_ENABLED=true` (and configure a provider) OR stop calling the AI endpoints from the frontend.
- If startup: wait for `/api/v1/health/ready` to return 200.

### 2.3 Symptom: Backend returns 504 Gateway Timeout

**Likely cause:**
1. Slow query in Postgres (default Nginx timeout is 60s)
2. External API call hanging (e.g. AI provider)
3. Deadlock in the database

**Diagnosis:**
```bash
# Check active queries
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT pid, state, now() - query_start AS duration, query
  FROM pg_stat_activity
  WHERE state = 'active' AND now() - query_start > interval '5 seconds'
  ORDER BY duration DESC;
"

# Check Nginx upstream timing
docker compose -f docker-compose.prod.yml logs nginx --since 10m | grep 'upstream timed out'
```

**Fix:**
- **Slow query**: identify and optimise. Common cause in beta: missing index on a filtered column. Check the query plan with `EXPLAIN ANALYZE`.
- **External API**: add a timeout to the HTTP client call in the application code.
- **Deadlock**: identify the contending queries in `pg_stat_activity` and terminate one with `pg_terminate_backend(pid)`. Investigate the application code to prevent recurrence.

### 2.4 Symptom: All API requests return 401 Unauthorized

**Likely cause:**
1. JWT signing key changed (users' tokens are invalid)
2. `JWT_ISSUER` or `JWT_AUDIENCE` changed
3. System clock drifted significantly (>30s)

**Diagnosis:**
```bash
# Check clock sync
docker compose -f docker-compose.prod.yml exec backend date -u
docker compose -f docker-compose.prod.yml exec postgres date -u
# Both should be within 1 second of each other and of `date -u` on the host

# Try to refresh — does it work?
curl -X POST https://app.masteryengine.com/api/v1/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<valid-token>"}' -i | head -20
```

**Fix:**
- If keys changed: users need to log in again. This is expected after a key rotation.
- If issuer/audience changed: same — re-login required. Revert if unintended.
- If clock drifted: `sudo systemctl restart chrony` on the host.

### 2.5 Symptom: All API requests return 403 Forbidden

**Likely cause:**
1. CSRF token mismatch (for POST/PUT/DELETE)
2. Closed Beta registration denied (registration endpoint only)
3. RBAC role check failed (admin endpoints)

**Diagnosis:**
```bash
# Check response body for the specific error code
curl -v -X POST https://app.masteryengine.com/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"x@y.com","password":"x"}' 2>&1 | grep -A5 'error\|detail\|message'
```

**Fix:**
- **CSRF**: the frontend should be sending `X-CSRF-Token` header. Verify the CSRF middleware is configured to accept same-origin requests.
- **Beta**: verify `CLOSED_BETA_ENABLED=true` and the invite token is valid, unused, and unexpired.
- **RBAC**: verify the user has the `administrator` role (`SELECT role FROM identity.users WHERE email='...'`).

### 2.6 Symptom: Backend response time degrades over time

**Likely cause:**
1. Database connection pool leak (connections not returned)
2. Memory leak in the Python process
3. Redis connection leak
4. Cache hit rate dropping (every request hits DB)

**Diagnosis:**
```bash
# 1. Backend memory growth
docker stats --no-stream masteryengine-backend-1
# Check 'MEM USAGE' — if growing linearly, leak.

# 2. DB connections
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT count(*), state FROM pg_stat_activity WHERE datname='mastery_engine' GROUP BY state;
"
# If 'idle in transaction' > 5, there's a transaction leak.

# 3. Cache hit rate (Grafana)
# Look at the "Cache Hit Rate" panel — drops below 80% indicate cache issues.

# 4. Redis connections
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" info clients | grep connected_clients
```

**Fix:**
- Restart the backend container as immediate mitigation: `docker compose -f docker-compose.prod.yml restart backend`.
- For root cause: investigate SQLAlchemy session handling — look for `session.execute()` calls without proper `async with` context managers.
- For Redis: check that `redis.from_url(...)` calls have `await client.aclose()` in finally blocks.

---

## 3. Database Issues

### 3.1 Symptom: Postgres won't start

**Likely cause:**
1. SSL cert files missing (`postgresql.conf` has `ssl=on` but certs not mounted)
2. Data directory corrupted (unclean shutdown)
3. Insufficient shared memory

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml logs postgres --tail 50
```

Common error messages:
- `could not access private key file "/etc/ssl/private/postgres-key.pem"` → SSL cert issue
- `PANIC: could not write to file` → disk full or corruption
- `could not create shared memory segment` → host kernel limits

**Fix:**
- **SSL certs**: see `deployment-checklist.md` §3.2 — disable SSL or mount the certs.
- **Corruption**: restore from backup (§3.4 below).
- **Shared memory**: increase kernel params:
  ```bash
  sudo sysctl -w kernel.shmmax=1073741824
  sudo sysctl -w kernel.shmall=262144
  ```

### 3.2 Symptom: Database connections exhausted

**Likely cause:**
1. Connection pool too large for `max_connections`
2. Connection leak in the application
3. Long-running transaction holding connections

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT count(*), state, wait_event_type
  FROM pg_stat_activity WHERE datname='mastery_engine'
  GROUP BY state, wait_event_type;
"

# Find idle-in-transaction (potential leak)
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT pid, usename, application_name, client_addr, state,
         now() - query_start AS query_duration,
         now() - state_change AS state_duration,
         left(query, 80) AS query
  FROM pg_stat_activity
  WHERE datname='mastery_engine' AND state = 'idle in transaction'
  ORDER BY state_duration DESC;
"
```

**Fix:**
- **Pool too large**: reduce `DATABASE_POOL_SIZE` or `DATABASE_MAX_OVERFLOW` in `.env.production`. Formula: `(pool_size + max_overflow) × num_backend_instances + num_worker_instances + admin_connections < 150`.
- **Connection leak**: restart the backend to release all connections, then investigate.
- **Idle in transaction**: terminate the offending PIDs:
  ```bash
  docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
    SELECT pg_terminate_backend(pid) FROM pg_stat_activity
    WHERE state = 'idle in transaction' AND state_change < now() - interval '5 minutes';
  "
  ```

### 3.3 Symptom: Query performance regressed

**Likely cause:**
1. Missing index (schema drift, or new query pattern)
2. Statistics out of date (autovacuum not keeping up)
3. Table bloat
4. Lock contention

**Diagnosis:**
```bash
# 1. Find slow queries
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT query, calls, mean_exec_time, total_exec_time, rows
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC LIMIT 10;
"

# 2. EXPLAIN ANALYZE the slowest one
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  EXPLAIN (ANALYZE, BUFFERS) <paste-slow-query>;
"

# 3. Check table bloat
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT relname, n_live_tup, n_dead_tup,
         round(100.0 * n_dead_tup / NULLIF(n_live_tup, 0), 2) AS dead_pct
  FROM pg_stat_user_tables
  WHERE n_dead_tup > 1000
  ORDER BY dead_pct DESC LIMIT 10;
"

# 4. Check locks
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT relation::regclass, pid, mode, granted, query
  FROM pg_locks l JOIN pg_stat_activity a ON l.pid = a.pid
  WHERE NOT granted;
"
```

**Fix:**
- **Missing index**: identify the column being filtered on. Add an index: `CREATE INDEX CONCURRENTLY idx_<table>_<col> ON <schema>.<table>(<col>);` (use `CONCURRENTLY` to avoid lock).
- **Stats stale**: `ANALYZE <schema>.<table>;` for the affected table.
- **Bloat**: `VACUUM (VERBOSE, ANALYZE) <schema>.<table>;` (or `VACUUM FULL` for severe bloat — locks the table).
- **Locks**: terminate the blocking PID with `pg_terminate_backend(pid)`.

### 3.4 Symptom: Database corruption / data loss

**Likely cause:**
1. Hardware failure (disk)
2. Force-kill of Postgres during write
3. Out-of-disk during WAL write

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml logs postgres --since 1h | grep -iE 'fatal|panic|corrupt'
```

**Fix:**
1. **Stop the platform**:
   ```bash
   docker compose -f docker-compose.prod.yml down
   ```
2. **Restore from the most recent backup**:
   ```bash
   ./scripts/backup.sh --restore /opt/mastery-engine/backups/mastery_engine_<latest>.tar.gz.enc
   ```
3. **Verify integrity**:
   ```bash
   docker compose -f docker-compose.prod.yml up -d postgres
   docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
     SELECT count(*) FROM identity.users;
     SELECT count(*) FROM identity.beta_invites WHERE used_at IS NOT NULL;
   "
   ```
4. **Restart the platform** per `production-launch.md` §1–6.
5. **Notify users** if any data was lost (e.g. study sessions since the last backup).

### 3.5 Symptom: Alembic migration fails

**Likely cause:**
1. Migration script bug
2. Schema already partially applied
3. Permission denied (mastery user lacks CREATE on schema)

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head 2>&1 | tail -30
```

**Fix:**
- **Migration bug**: fix the script, then `alembic stamp <revision>` to mark the current state.
- **Partial apply**: `alembic downgrade -1` to roll back the partial migration, then re-apply.
- **Permission**: the init SQL only grants `USAGE` (not `CREATE`) on schemas. Run as superuser:
  ```bash
  docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
    GRANT CREATE ON SCHEMA identity, content, learning, assessment, mastery, scheduling, analytics, billing, administration, infrastructure TO mastery;
  "
  ```

---

## 4. Worker Issues

### 4.1 Symptom: Worker not picking up jobs

**Likely cause:**
1. Worker process crashed
2. Worker can't connect to Postgres
3. Scheduler is paused
4. Job is locked by another (dead) worker

**Diagnosis:**
```bash
# 1. Worker status
docker compose -f docker-compose.prod.yml ps worker
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT worker_id, status, last_seen_at, current_job
  FROM infrastructure.worker_heartbeats ORDER BY started_at DESC LIMIT 5;
"

# 2. Worker logs
docker compose -f docker-compose.prod.yml logs worker --tail 50

# 3. Scheduled jobs
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT name, status, locked_by, lock_expires_at, next_run_at
  FROM infrastructure.scheduled_jobs WHERE status = 'active';
"

# 4. Stuck locks
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT * FROM infrastructure.scheduled_jobs
  WHERE locked_by IS NOT NULL AND lock_expires_at < now();
"
```

**Fix:**
- **Crashed**: `docker compose -f docker-compose.prod.yml restart worker`
- **DB issue**: fix per §3
- **Stuck locks**: release them:
  ```bash
  docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
    UPDATE infrastructure.scheduled_jobs
    SET locked_by = NULL, lock_expires_at = NULL
    WHERE lock_expires_at < now();
  "
  ```

### 4.2 Symptom: Worker CPU at 100%

**Likely cause:**
1. Runaway job (infinite loop, expensive query)
2. Too many jobs queued simultaneously
3. Background metric collection spinning

**Diagnosis:**
```bash
docker stats --no-stream masteryengine-worker-1
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT worker_id, current_job, jobs_processed, jobs_failed, last_seen_at
  FROM infrastructure.worker_heartbeats;
"
```

**Fix:**
- Identify `current_job` — if it's been the same for > 5 min, the job is stuck.
- Restart the worker: `docker compose -f docker-compose.prod.yml restart worker`
- Scale up if load is genuinely high: `docker compose -f docker-compose.prod.yml up -d --scale worker=2`

### 4.3 Symptom: Worker OOM-killed

**Likely cause:**
1. Job processing a huge result set (loading entire table into memory)
2. Memory leak in a job handler

**Fix:**
- Raise the worker memory limit in `docker-compose.prod.yml`:
  ```yaml
  worker:
    deploy:
      resources:
        limits:
          memory: 1G  # was 512M
  ```
- Investigate the failing job — look at the `current_job` field in the heartbeat right before the crash.
- Add pagination/chunking to the offending job handler.

---

## 5. Outbox Issues

### 5.1 Symptom: Outbox pending count growing

**Likely cause:**
1. Outbox dispatcher not running
2. Subscribers throwing exceptions (events get retried indefinitely)
3. Stuck leases preventing dispatch

**Diagnosis:**
```bash
# 1. Pending count and trend
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT
    count(*) FILTER (WHERE consumed_at IS NULL) AS pending,
    count(*) FILTER (WHERE consumed_at IS NULL AND created_at < now() - interval '5 minutes') AS old_pending,
    count(*) FILTER (WHERE next_retry_at IS NOT NULL AND next_retry_at > now()) AS awaiting_retry
  FROM infrastructure.outbox_events;
"

# 2. Recent failures
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT event_type, retry_history::text
  FROM infrastructure.outbox_events
  WHERE consumed_at IS NULL AND array_length(retry_history::json->'attempts') > 0
  ORDER BY created_at DESC LIMIT 5;
"

# 3. Stuck leases
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT * FROM infrastructure.outbox_leases WHERE released_at IS NULL AND expires_at < now();
"
```

**Fix:**
1. Release stuck leases:
   ```bash
   docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
     UPDATE infrastructure.outbox_leases
     SET released_at = now(), release_reason = 'lease_expired_manual'
     WHERE released_at IS NULL AND expires_at < now();
   "
   ```
2. Restart the worker to kick the dispatcher: `docker compose -f docker-compose.prod.yml restart worker`
3. Investigate the failing subscribers — check worker logs for the exception stack trace.
4. If a specific event type is consistently failing, consider moving it to the dead letter queue manually:
   ```bash
   docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
     INSERT INTO infrastructure.dead_letter_events (event_id, originating_schema, event_type, payload, severity, retry_history)
     SELECT id, 'infrastructure', event_type, payload::text, 'warning', retry_history
     FROM infrastructure.outbox_events
     WHERE consumed_at IS NULL AND created_at < now() - interval '1 hour';

     UPDATE infrastructure.outbox_events
     SET consumed_at = now()
     WHERE consumed_at IS NULL AND created_at < now() - interval '1 hour';
   "
   ```

### 5.2 Symptom: Events being delivered multiple times (duplicates)

**Likely cause:**
1. Subscriber not idempotent
2. Lease expired mid-processing and another worker picked it up

**Fix:**
- Subscribers MUST be idempotent (use the event ID as a deduplication key).
- Increase the lease timeout if processing takes longer than the default:
  ```bash
  docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
    -- Find the dispatcher config — typically in the worker settings
    -- Or extend lease on individual events:
    UPDATE infrastructure.outbox_events
    SET leased_until = now() + interval '10 minutes'
    WHERE id IN (...);
  "
  ```

---

## 6. Dead Letter Queue Issues

### 6.1 Symptom: Dead letter events accumulating

**Likely cause:**
1. A subscriber keeps failing and exhausting retries
2. A bug in event serialization

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT event_type, severity, count(*), max(created_at) AS latest
  FROM infrastructure.dead_letter_events
  WHERE resolved_at IS NULL
  GROUP BY event_type, severity
  ORDER BY count(*) DESC;
"

# Inspect a sample
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT id, event_type, severity, retry_history, payload
  FROM infrastructure.dead_letter_events
  WHERE resolved_at IS NULL
  ORDER BY created_at DESC LIMIT 1;
"
```

**Fix:**
1. Identify the failing event type.
2. Read the `retry_history` JSON — it contains the exception messages from each retry.
3. Fix the root cause in the subscriber code.
4. Replay the dead-lettered events:
   ```bash
   curl -X POST https://app.masteryengine.com/api/v1/admin/bg/dead-letters/<id>/replay \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```
   Or via SQL (manual replay):
   ```bash
   docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
     -- Move back to outbox
     INSERT INTO infrastructure.outbox_events (event_type, payload, created_at)
     SELECT event_type, payload, created_at
     FROM infrastructure.dead_letter_events WHERE id = '<id>';

     UPDATE infrastructure.dead_letter_events
     SET resolved_at = now(), resolution_notes = 'Replayed after fix in PR #123'
     WHERE id = '<id>';
   "
   ```

---

## 7. Scheduler Issues

### 7.1 Symptom: Scheduled jobs not running

**Likely cause:**
1. Scheduler process not running (worker down)
2. Job is locked by a dead worker
3. `next_run_at` is in the future due to a calculation bug
4. Job is paused

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT name, schedule_type, status, next_run_at, last_run_at,
         locked_by, lock_expires_at, consecutive_failures, last_error
  FROM infrastructure.scheduled_jobs
  ORDER BY next_run_at;
"
```

**Fix:**
- **Paused**: `UPDATE infrastructure.scheduled_jobs SET status = 'active' WHERE name = '<job>';`
- **Locked by dead worker**: release the lock (same as §4.1)
- **Failure**: read `last_error`, fix the root cause, reset `consecutive_failures = 0`

### 7.2 Symptom: Job running too frequently

**Likely cause:**
1. `next_run_at` not being updated after a run
2. Cron expression wrong
3. Multiple scheduler instances (HA without coordination)

**Fix:**
- Check the scheduler processor code — verify `next_run_at` is updated to the next calculated time after each run.
- For HA: ensure only one scheduler instance runs (use a distributed lock via Redis, or run the scheduler only on the worker — not on multiple workers).

---

## 8. Email Issues

### 8.1 Symptom: No emails being sent

**Likely cause:**
1. SMTP not configured (see `environment-reference.md` §8 — Settings class doesn't have SMTP vars)
2. SMTP provider down
3. Worker not processing email jobs

**Diagnosis:**
```bash
# 1. Check email delivery log
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT status, count(*), max(created_at) AS latest
  FROM infrastructure.email_delivery_log
  WHERE created_at > now() - interval '24 hours'
  GROUP BY status;
"

# 2. Check worker is processing email jobs
docker compose -f docker-compose.prod.yml logs worker --since 30m | grep -i 'email\|smtp'

# 3. Test SMTP manually
docker compose -f docker-compose.prod.yml exec backend python -c "
import smtplib
s = smtplib.SMTP('$SMTP_HOST', $SMTP_PORT, timeout=10)
s.starttls()
s.login('$SMTP_USERNAME', '$SMTP_PASSWORD')
print('SMTP login OK')
s.quit()
"
```

**Fix:**
- **SMTP not configured**: the `Settings` class doesn't have SMTP vars — patch `ProductionSmtpClient` to read from env, or hardcode in `email/service.py` as a temporary measure.
- **SMTP provider down**: check the provider's status page. If prolonged, switch to a backup provider.
- **Worker not processing**: check the worker is running (§4.1).

### 8.2 Symptom: Emails bouncing

**Likely cause:**
1. Recipient address invalid
2. Sender domain not verified (SPF/DKIM missing)
3. Rate limited by provider

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT to_email, bounce_type, reason, count(*)
  FROM infrastructure.email_delivery_log
  WHERE status = 'bounced' AND created_at > now() - interval '7 days'
  GROUP BY to_email, bounce_type, reason
  ORDER BY count(*) DESC LIMIT 20;
"
```

**Fix:**
- **Invalid recipient**: remove the user from the email list, or correct the address.
- **SPF/DKIM**: add DNS records for your sending domain:
  - SPF: `masteryengine.com. IN TXT "v=spf1 include:spf.postmarkapp.com ~all"`
  - DKIM: follow provider's instructions to add the CNAME/TXT record.
- **Rate limited**: check provider dashboard for limits. Upgrade plan or throttle sending.

### 8.3 Symptom: Beta invitation emails not being sent

**Likely cause:**
1. Email dispatch not wired in `create_invite` / `resend_invite` (current state per code inspection)

**Diagnosis:**
```bash
# After creating an invite, check the email log
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT * FROM infrastructure.email_delivery_log
  WHERE to_email = '<invited-email>' AND created_at > now() - interval '5 minutes';
"
```

If empty, the email was never queued.

**Fix:**
Two options:

**Option A (manual, immediate):** Send the email yourself using the rendered template:
```bash
docker compose -f docker-compose.prod.yml exec backend python -c "
from app.infrastructure.email.beta_templates import BetaInvitationEmailTemplate
import asyncio
async def send():
    tpl = BetaInvitationEmailTemplate()
    html, text = tpl.render(register_url='https://app.masteryengine.com/register?invite_token=...', email='user@example.com', expires_at='2026-07-10T12:00:00Z')
    # Send via SMTP manually
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    msg = MIMEMultipart('alternative')
    msg['Subject'] = tpl.subject
    msg['From'] = '$SMTP_FROM_EMAIL'
    msg['To'] = 'user@example.com'
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))
    with smtplib.SMTP('$SMTP_HOST', $SMTP_PORT) as s:
        s.starttls()
        s.login('$SMTP_USERNAME', '$SMTP_PASSWORD')
        s.send_message(msg)
    print('Sent')
asyncio.run(send())
"
```

**Option B (recommended, permanent):** Patch `app/presentation/api/v1/beta.py` to inject `EmailService` and call `send_template(...)` inside `create_invite` and `resend_invite`.

---

## 9. Frontend Issues

### 9.1 Symptom: Frontend shows blank page

**Likely cause:**
1. JavaScript bundle failed to load (CDN issue, build mismatch)
2. React error boundary caught an unhandled exception
3. CSP blocking inline scripts

**Diagnosis:**
- Open browser DevTools → Console tab. Look for errors.
- Open Network tab → reload → check for failed requests (red).
- Check `curl -sI https://app.masteryengine.com/` — should return 200 with `content-type: text/html`.

**Fix:**
- **CSP**: the current CSP is `default-src 'self'` which may block Next.js inline scripts. Check the browser console for CSP violations. If found, add `'unsafe-inline'` to `script-src` and `style-src` in `nginx.conf` (or implement a nonce pipeline).
- **Build mismatch**: rebuild the frontend image:
  ```bash
  docker compose --env-file .env.production -f docker-compose.prod.yml build --no-cache frontend
  docker compose -f docker-compose.prod.yml up -d frontend
  ```
- **Bundle 404**: verify the static files are present in the container:
  ```bash
  docker compose -f docker-compose.prod.yml exec frontend ls /app/.next/static
  ```

### 9.2 Symptom: WebSocket connection fails

**Likely cause:**
1. Nginx not proxying `/ws` correctly
2. Backend WebSocket endpoint down
3. Authentication issue (no token in connection)

**Diagnosis:**
```bash
# Test WebSocket via wscat (install: npm install -g wscat)
wscat -c "wss://app.masteryengine.com/ws" -H "Authorization: Bearer <token>"

# Check Nginx logs for /ws requests
docker compose -f docker-compose.prod.yml logs nginx --since 10m | grep '/ws'
```

**Fix:**
- **Nginx**: verify `nginx.conf` has the `/ws` location block with `proxy_http_version 1.1` and `Upgrade` / `Connection` headers.
- **Backend**: check the WebSocket endpoint is registered. Restart backend if needed.
- **Auth**: the WebSocket connection must include a valid JWT (typically as a query param `?token=...` or in a sub-protocol header).

### 9.3 Symptom: "Network error" toasts on every action

**Likely cause:**
1. Backend down
2. CORS misconfigured (origin not allowed)
3. CSRF token missing

**Diagnosis:**
```bash
# Browser DevTools → Network tab → look for failed requests
# Check the response headers for CORS errors
curl -v -X OPTIONS https://app.masteryengine.com/api/v1/auth/login \
  -H 'Origin: https://app.masteryengine.com' \
  -H 'Access-Control-Request-Method: POST' 2>&1 | grep -i 'access-control'
```

**Fix:**
- **Backend down**: see §2.1
- **CORS**: verify `CORS_ORIGINS` in `.env.production` includes `https://app.masteryengine.com`. Restart backend.
- **CSRF**: the frontend should auto-fetch a CSRF token on page load. If not, check the auth provider implementation.

### 9.4 Symptom: Beta banner or feedback button not showing

**Likely cause:**
1. Components not rendered in the layout
2. JavaScript error preventing render
3. Feature flag disabled (feedback button respects `BETA_FLAG_*`?)

**Diagnosis:**
- Browser DevTools → Console → look for errors
- Browser DevTools → Elements → search for `beta-banner` or `feedback-button` class
- Check `GET /api/v1/beta/status` response in Network tab

**Fix:**
- The beta banner shows on every authenticated learner page if it's in the layout. Verify `app/(learner)/layout.tsx` includes `<BetaBanner />`.
- The feedback button is a floating component — verify it's in the layout or in `production-providers.tsx`.
- If feature flags are off, the components may be conditionally hidden. Check the `FeatureFlagProvider` consumption.

---

## 10. Sentry Issues

### 10.1 Symptom: Sentry not receiving events

**Likely cause:**
1. `SENTRY_DSN` not set or wrong
2. Sentry SDK not initialised
3. Network blocking the Sentry ingest endpoint

**Diagnosis:**
```bash
# Test from the backend container
docker compose -f docker-compose.prod.yml exec backend python -c "
import sentry_sdk
sentry_sdk.init(dsn='$SENTRY_DSN', environment='production')
sentry_sdk.capture_message('Manual test from ops')
print('Captured. Check Sentry UI.')
"

# Check network
docker compose -f docker-compose.prod.yml exec backend curl -sfI https://o<org>.ingest.sentry.io/api/1/store/ | head -5
```

**Fix:**
- Verify `SENTRY_DSN` is set in `.env.production` and matches a valid Sentry project.
- If network is blocked, allow `*.ingest.sentry.io` in the firewall.

### 10.2 Symptom: Too many Sentry events (event spam)

**Likely cause:**
1. A recurring error firing on every request
2. Misconfigured sampling (100% sample rate in prod)

**Fix:**
- In Sentry UI → Project Settings → Inbound Filters → ignore specific error messages.
- Set `traces_sample_rate` to 0.1 (10%) in production code.
- Fix the root cause of the recurring error.

### 10.3 Triage workflow

For each new Sentry event:

1. **Read the title and stack trace.**
2. **Check frequency** — is this a one-off or recurring?
3. **Check affected users** — how many?
4. **Assign severity**:
   - `fatal` → SEV-1, investigate immediately
   - `error` → SEV-2/3, investigate within 24h
   - `warning` → SEV-3/4, batch-triage weekly
5. **Link to a ticket** in your issue tracker.
6. **Resolve** in Sentry when the fix is deployed.

---

## 11. Disk & Resource Issues

### 11.1 Symptom: Disk full

**Likely cause:**
1. Postgres WAL files accumulating (archive_command failing)
2. Docker log files growing unbounded
3. Backups not being cleaned up
4. Postgres `log/` directory growing (logging_collector=on)

**Diagnosis:**
```bash
df -h
du -sh /var/lib/docker/* 2>/dev/null | sort -h
docker compose -f docker-compose.prod.yml exec postgres du -sh /var/lib/postgresql/data/log/
docker compose -f docker-compose.prod.yml exec postgres du -sh /var/lib/postgresql/data/pg_wal/
```

**Fix:**
- **Docker logs**: rotate via the `json-file` driver config in `docker-compose.prod.yml` (already configured: `max-size: 100m, max-file: 10`).
- **Postgres logs**: configure log rotation in `postgresql.conf` (already configured: 1 day or 100 MB).
- **WAL**: check `archive_command` if WAL archiving is enabled. If not needed, disable.
- **Backups**: verify the retention cleanup runs (`find ... -mtime +30 -delete`).
- **Emergency**: clear old logs:
  ```bash
  docker compose -f docker-compose.prod.yml exec postgres rm -f /var/lib/postgresql/data/log/postgres-*.log.*.gz
  truncate -s 0 /var/lib/docker/containers/*/*-json.log
  ```

### 11.2 Symptom: High CPU usage

**Likely cause:**
1. runaway query
2. Crypto operation (Argon2id is CPU-intensive)
3. Background job spike

**Diagnosis:**
```bash
top -b -n 1 | head -20
docker stats --no-stream
```

**Fix:**
- Identify the consuming container, then the process inside it.
- For Argon2id spikes: many concurrent logins can saturate CPU. Reduce `ARGON2_PARALLELISM` if needed.
- For query spikes: see §3.3.
- For job spikes: see §4.2.

---

## 12. Backup Issues

### 12.1 Symptom: Backup fails

**Likely cause:**
1. `BACKUP_ENCRYPTION_KEY` not set
2. `aws` CLI not installed or not configured
3. Postgres dump fails (DB unreachable, permissions)
4. Redis BGSAVE fails (no auth, wrong path)

**Diagnosis:**
```bash
/opt/mastery-engine/scripts/backup.sh 2>&1 | tee /tmp/backup-debug.log
```

**Fix:**
- **Missing encryption key**: set `BACKUP_ENCRYPTION_KEY` in the env before running.
- **AWS CLI**: `sudo apt install awscli && aws configure`.
- **Postgres**: verify `DATABASE_PASSWORD` is correct, `pg_dump` works manually.
- **Redis**: see §12.2 below.

### 12.2 Symptom: Redis backup fails

**Likely cause:**
1. `REDIS_PASSWORD` not passed to `redis-cli BGSAVE`
2. `dump.rdb` path wrong (Docker volume, not host path)
3. Redis is busy and BGSAVE times out

**Fix:**
The backup script has known bugs (per `deployment-checklist.md` §8.1). Workaround:

```bash
# Manually trigger BGSAVE with auth
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" BGSAVE

# Wait for it to complete (poll LASTSAVE)
LASTSAVE_BEFORE=$(docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" LASTSAVE)
while true; do
  LASTSAVE_NOW=$(docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" LASTSAVE)
  [[ "$LASTSAVE_NOW" != "$LASTSAVE_BEFORE" ]] && break
  sleep 2
done

# Copy the dump out of the container
docker cp masteryengine-redis-1:/data/dump.rdb /opt/mastery-engine/backups/redis_dump_$(date +%Y%m%d).rdb
```

Patch `scripts/backup.sh` to use this flow.

### 12.3 Symptom: Restore fails

**Likely cause:**
1. Encryption key wrong
2. Backup file corrupted
3. Postgres version mismatch (backup from PG 16, restoring to PG 14)

**Diagnosis:**
```bash
# Decrypt manually and check
openssl enc -d -aes-256-cbc -pbkdf2 -pass pass:$BACKUP_ENCRYPTION_KEY \
  -in <backup-file>.enc -out /tmp/backup.tar.gz 2>&1

# Try to list
tar tzf /tmp/backup.tar.gz | head -10

# Try pg_restore
pg_restore -l /tmp/postgres.dump | head -20
```

**Fix:**
- **Wrong key**: locate the correct key in your secrets store. If lost, the backup is unrecoverable.
- **Corrupted**: try a different backup. If all are corrupted, the backup system itself is broken — investigate.
- **Version mismatch**: deploy a Postgres container matching the backup version, restore there, then dump/restore to the new version.

---

## 13. Redis Issues

### 13.1 Symptom: Redis OOM (eviction storm)

**Likely cause:**
1. `maxmemory` too low for the workload
2. Cache hit rate dropping (everything is being cached but evicted before reuse)

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" info memory | \
  grep -E 'used_memory_human|maxmemory_human|evicted_keys|mem_fragmentation_ratio'

docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" info stats | \
  grep -E 'evicted_keys|keyspace_hits|keyspace_misses'
```

**Fix:**
- Raise `maxmemory` in the compose command:
  ```yaml
  redis:
    command: ["redis-server", "--maxmemory", "1gb", "--maxmemory-policy", "allkeys-lru", ...]
  ```
- Restart Redis: `docker compose -f docker-compose.prod.yml restart redis`
- Investigate cache usage patterns — are you caching too much? TTLs too long?

### 13.2 Symptom: Redis latency spikes

**Likely cause:**
1. `BGSAVE` blocking (synchronous fork)
2. Large keys being read/written atomically
3. Slow commands (`KEYS *`, `SMEMBERS` on huge sets)

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" --latency
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" slowlog get 10
```

**Fix:**
- **BGSAVE**: schedule backups during low-traffic windows. Or use AOF instead.
- **Large keys**: identify with `redis-cli --bigkeys`. Split into smaller keys.
- **Slow commands**: avoid `KEYS *` — use `SCAN` instead.

### 13.3 Symptom: Redis data lost after restart

**Likely cause:**
1. Persistence disabled or misconfigured
2. Volume not mounted correctly

**Diagnosis:**
```bash
# Check persistence config
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" config get save
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" config get appendonly

# Check volume
docker compose -f docker-compose.prod.yml exec redis ls -la /data
```

**Fix:**
- The prod compose should mount `redis_data:/data`. Verify.
- The `save` config should be set (RDB snapshots) — the prod compose uses `--save 900 1 --save 300 10 --save 60 10000` defaults.
- For maximum durability, enable AOF: `--appendonly yes`.

---

## 14. Closed Beta Specific Issues

### 14.1 Symptom: Registration returns 403 BETA_REGISTRATION_DENIED

**Likely cause:**
1. Invite token invalid, expired, or already used
2. Email doesn't match the invite email
3. User count has reached `MAX_BETA_USERS`

**Diagnosis:**
```bash
# Check the invite
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT email, used_at, expires_at, now() < expires_at AS still_valid
  FROM identity.beta_invites WHERE invite_token = '<token>';
"

# Check user count
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT count(*) FROM identity.users WHERE role != 'administrator';
"
```

**Fix:**
- If expired: resend the invite (§2.5 of `beta-launch-guide.md`)
- If used: the user already registered — they should log in instead
- If count full: raise `MAX_BETA_USERS` or remove an inactive user

### 14.2 Symptom: Beta banner shows even when `CLOSED_BETA_ENABLED=false`

**Likely cause:**
The `BetaBanner` component doesn't check the `closed_beta_enabled` flag — it always renders when included in the layout.

**Fix:**
Either:
- Conditionally render `<BetaBanner />` in the layout based on `/api/v1/beta/status` response
- Or remove `<BetaBanner />` from the layout when transitioning out of beta

### 14.3 Symptom: Welcome wizard doesn't save user data

**Likely cause:**
The wizard is purely client-side — it doesn't POST to any backend endpoint.

**Fix:**
This is a known issue (`deployment-checklist.md` Appendix A). Workaround: users can manually update their profile at `/settings`. Track as P2 fix.

### 14.4 Symptom: Admin endpoints accessible by non-admins

**Likely cause:**
The beta admin endpoints (`/api/v1/admin/beta/invites*`) only depend on `get_current_user_id` — no role check is enforced.

**Fix:**
Patch `app/presentation/api/v1/beta.py` to enforce the admin role:
```python
from app.infrastructure.security.authorization import require_admin

@router.post("/admin/beta/invites", status_code=201)
async def create_invite(
    request: CreateInviteRequest,
    user_id: UUID = Depends(require_admin),  # was: get_current_user_id
    ...
):
```

Until fixed, mitigate by limiting who can register (via the invite flow).

---

## 15. Diagnostic Cheat Sheet

When in doubt, run these in order:

```bash
# 1. Overall health
docker compose -f docker-compose.prod.yml ps
curl -sf https://app.masteryengine.com/api/v1/health/ready | jq .

# 2. Resource usage
docker stats --no-stream
df -h /

# 3. Recent errors
docker compose -f docker-compose.prod.yml logs --since 30m backend worker | grep -iE 'error|critical|exception' | tail -30

# 4. Database state
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT
    (SELECT count(*) FROM identity.users) AS users,
    (SELECT count(*) FROM infrastructure.outbox_events WHERE consumed_at IS NULL) AS outbox_pending,
    (SELECT count(*) FROM infrastructure.dead_letter_events WHERE resolved_at IS NULL) AS dead_letters,
    (SELECT count(*) FROM infrastructure.scheduled_jobs WHERE consecutive_failures > 0) AS failing_jobs,
    (SELECT count(*) FROM infrastructure.worker_heartbeats WHERE last_seen_at > now() - interval '1 minute') AS active_workers;
"

# 5. Recent Sentry events (if Sentry CLI is installed)
sentry-cli issues list --project mastery-engine

# 6. SSL cert expiry
echo | openssl s_client -connect app.masteryengine.com:443 -servername app.masteryengine.com 2>/dev/null | openssl x509 -noout -dates
```

If all of these return green, the platform is healthy. If any return red, follow the corresponding section above.

---

## 16. Escalation

If you cannot resolve an issue within the SLA for its severity:

| Severity | Escalate to | After |
|---|---|---|
| SEV-1 | Engineering lead + Product manager | 30 minutes |
| SEV-2 | Engineering lead | 2 hours |
| SEV-3 | On-call buddy | 8 hours |
| SEV-4 | Triage in next sprint planning | 1 week |

When escalating, provide:
- Incident summary (1-2 sentences)
- Current status (what you've tried)
- Specific ask (e.g. "Need a domain expert in SQLAlchemy")
- Logs / Sentry links
- Time since impact started

---

**End of troubleshooting guide.** Next: read `deployment-diagrams.md` for visual reference of the platform architecture, and `post-launch-monitoring.md` for the long-term monitoring strategy.
