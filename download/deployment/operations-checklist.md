# Operations Checklist — Mastery Engine Closed Beta

> **Audience:** On-call SRE, daily operations engineer.
> **Scope:** Daily, weekly, and incident-driven operational tasks for keeping the Closed Beta healthy.
> **Last updated:** 2026-07-03

---

## 0. How To Use This Document

This is the **operational runbook**. It is structured around three time horizons:

- **§1 Daily checks** — perform every morning before user activity peaks (~08:00 UTC)
- **§2 Weekly checks** — perform every Monday morning
- **§3 Incident response** — perform when an alert fires or a user reports an issue
- **§4 Maintenance windows** — perform during scheduled downtime
- **§5 Capacity review** — perform before any user-count expansion

Each task has:
- **Frequency** — when to run it
- **Command** — exact shell command or API call
- **Expected result** — what "healthy" looks like
- **If unhealthy** — link to `troubleshooting.md` section

---

## 1. Daily Operations Checks (≈15 minutes)

### 1.1 Container health

**Frequency:** Daily 08:00 UTC, plus any time an alert fires.

```bash
cd /opt/mastery-engine
docker compose -f docker-compose.prod.yml ps
```

**Expected:** All 7 containers (postgres, redis, backend, worker, frontend, nginx, prometheus, grafana) show `Up` and `healthy`.

**If unhealthy:** See `troubleshooting.md` §1.

---

### 1.2 Backend health

```bash
curl -sf https://app.masteryengine.com/api/v1/health | jq .
curl -sf https://app.masteryengine.com/api/v1/health/ready | jq .
```

**Expected:**
- `/health` returns `{"status":"healthy","app":"mastery-engine","version":"0.1.0","timestamp":...}`
- `/health/ready` returns `{"status":"ready","checks":[{"name":"database","status":"healthy","latency_ms":<50},{"name":"redis","status":"healthy","latency_ms":<10}]}`

**If unhealthy:** See `troubleshooting.md` §2 (backend down) or §3 (DB/Redis issues).

---

### 1.3 Worker health

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT worker_id, worker_type, status,
         EXTRACT(EPOCH FROM (now() - last_seen_at))::int AS seconds_since_seen,
         jobs_processed, jobs_failed
  FROM infrastructure.worker_heartbeats
  ORDER BY started_at DESC;
"
```

**Expected:**
- At least 1 row
- `status = 'running'`
- `seconds_since_seen < 30`
- `jobs_failed` is small relative to `jobs_processed` (ratio < 5%)

**If unhealthy:** See `troubleshooting.md` §4 (worker issues).

---

### 1.4 Outbox backlog

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT
    count(*) AS total,
    count(*) FILTER (WHERE consumed_at IS NULL) AS pending,
    count(*) FILTER (WHERE consumed_at IS NULL AND created_at < now() - interval '5 minutes') AS pending_over_5min,
    count(*) FILTER (WHERE next_retry_at IS NOT NULL) AS scheduled_for_retry
  FROM infrastructure.outbox_events;
"
```

**Expected:**
- `pending = 0` (or trending to 0)
- `pending_over_5min = 0`
- `scheduled_for_retry = 0`

**If unhealthy:** See `troubleshooting.md` §5 (outbox backlog).

---

### 1.5 Dead letter queue

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT id, event_type, severity, created_at,
         retry_history::text AS history
  FROM infrastructure.dead_letter_events
  WHERE resolved_at IS NULL
  ORDER BY created_at DESC LIMIT 10;
"
```

**Expected:** Empty result set.

**If non-empty:** See `troubleshooting.md` §6 (dead letter events).

---

### 1.6 Scheduled jobs

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT name, schedule_type, status,
         last_run_at, next_run_at,
         consecutive_failures, last_error
  FROM infrastructure.scheduled_jobs
  WHERE status = 'active'
  ORDER BY next_run_at;
"
```

**Expected:**
- All `status = 'active'`
- `consecutive_failures = 0` (or < 3)
- `last_error` is NULL
- `next_run_at` is in the future for non-due jobs

**If unhealthy:** See `troubleshooting.md` §7 (scheduler issues).

---

### 1.7 Email delivery

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT status, count(*),
         round(100.0 * count(*) / sum(count(*)) over (), 2) AS pct
  FROM infrastructure.email_delivery_log
  WHERE created_at > now() - interval '24 hours'
  GROUP BY status
  ORDER BY count(*) DESC;
"
```

**Expected:**
- `sent` or `delivered` dominate (> 95%)
- `bounced` < 1%
- `failed` = 0

**If unhealthy:** See `troubleshooting.md` §8 (email issues).

---

### 1.8 Beta engagement snapshot

```bash
ADMIN_TOKEN=<your-admin-token>
curl -sf https://app.masteryengine.com/api/v1/beta/analytics \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '{
    total_users: .total_users,
    open_feedback: .open_feedback,
    events_last_24h: (.events_by_type | to_entries | map(.value) | add)
  }'
```

**Expected:** Snapshot matches recent trends. Sudden drops in events signal user-facing issues.

**If anomalous:** See `troubleshooting.md` §9 (engagement drop).

---

### 1.9 Sentry errors

**Frequency:** Daily, plus any time Sentry emails an alert.

Open `https://sentry.io/organizations/<org>/projects/mastery-engine/`.

**Expected:**
- No new `fatal` or `error` events in the last 24 hours
- Any new events have been triaged (assigned, resolved, or ignored with a reason)

**If new errors:** See `troubleshooting.md` §10 (Sentry triage).

---

### 1.10 Disk space

```bash
df -h / /var/lib/docker
du -sh /opt/mastery-engine/backups/
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c \
  "SELECT pg_size_pretty(pg_database_size('mastery_engine'));"
```

**Expected:**
- `/` usage < 70%
- `/var/lib/docker` usage < 70%
- Backup directory < 5 GB (30-day retention × ~150 MB per backup)
- Database size < 5 GB (for 20 beta users, expect 100–500 MB)

**If unhealthy:** See `troubleshooting.md` §11 (disk full).

---

### 1.11 Backup verification (daily)

```bash
# Verify the most recent backup
ls -lh /opt/mastery-engine/backups/ | tail -5

# Integrity check (does NOT require decryption if encrypted)
tar tzf /opt/mastery-engine/backups/mastery_engine_$(date +%Y%m%d)*.tar.gz* 2>&1 | tail -5
```

**Expected:** Latest backup exists, is non-zero size, and `tar tzf` lists files without error.

For encrypted backups:
```bash
openssl enc -d -aes-256-cbc -pbkdf2 -pass pass:$BACKUP_ENCRYPTION_KEY \
  -in /opt/mastery-engine/backups/mastery_engine_$(date +%Y%m%d)*.tar.gz.enc \
  | tar tzf - | tail -5
```

**If unhealthy:** See `troubleshooting.md` §12 (backup issues).

---

### 1.12 Daily check summary

Print this summary after all checks pass:

```
[2026-07-03 08:15 UTC] Daily check — ALL GREEN
  Containers: 7/7 healthy
  Backend:    healthy (latency 23ms)
  Worker:     running (jobs_processed: 1247, jobs_failed: 2)
  Outbox:     pending=0
  Dead letters: 0
  Scheduler:  all jobs active, no consecutive failures
  Email:      98% delivered, 0 failed
  Beta:       17 users, 4 open feedback items
  Sentry:     0 new errors
  Disk:       / at 42%, db at 312 MB
  Backup:     2026-07-03.tar.gz.enc verified (147 MB)
```

Post this to the `#beta-status` Slack channel.

---

## 2. Weekly Operations Checks (≈45 minutes)

### 2.1 Capacity review

```bash
# CPU average (last 7 days)
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Postgres connection stats
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT count(*), state FROM pg_stat_activity GROUP BY state;
"

# Redis memory
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" info memory | \
  grep -E 'used_memory_human|maxmemory_human|used_memory_peak_human'

# Redis keyspace
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" info keyspace

# Slow queries (last 7 days, top 10)
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT query, calls, mean_exec_time, total_exec_time
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC LIMIT 10;
"
```

**Action:** Compare with last week's numbers. Investigate any:
- CPU > 60% sustained
- Memory > 80%
- Postgres connections > 100 (50% of max)
- Slow queries regressing > 2x

---

### 2.2 Security audit

```bash
# Failed login attempts (last 7 days)
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT count(*), date_trunc('day', created_at) AS day
  FROM identity.auth_audit_logs
  WHERE action = 'LOGIN_FAILED' AND created_at > now() - interval '7 days'
  GROUP BY day ORDER BY day;
"

# Suspicious IPs (multiple failed logins)
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT (details->>'ip_address')::inet AS ip, count(*) AS attempts
  FROM identity.auth_audit_logs
  WHERE action = 'LOGIN_FAILED' AND created_at > now() - interval '24 hours'
  GROUP BY ip HAVING count(*) > 5
  ORDER BY attempts DESC LIMIT 10;
"

# Security incidents
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT incident_type, severity, created_at, resolved_at
  FROM identity.security_incidents
  WHERE created_at > now() - interval '7 days' OR resolved_at IS NULL
  ORDER BY created_at DESC;
"

# Refresh token reuse detections (high-severity incident)
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT count(*) FROM identity.security_incidents
  WHERE incident_type = 'refresh_token_reuse' AND created_at > now() - interval '7 days';
"
```

**Action:** For each unresolved security incident, follow the incident response procedure (§3). For each suspicious IP, consider rate-limiting at the Nginx layer (`deny <ip>;` in `nginx.conf`).

---

### 2.3 Backup restore drill

**Frequency:** Weekly (Sunday).

```bash
# 1. Spin up a staging postgres container
docker run -d --name staging-pg -e POSTGRES_PASSWORD=test postgres:16-alpine

# 2. Restore the latest encrypted backup
LATEST_BACKUP=$(ls -t /opt/mastery-engine/backups/mastery_engine_*.tar.gz.enc | head -1)
openssl enc -d -aes-256-cbc -pbkdf2 -pass pass:$BACKUP_ENCRYPTION_KEY \
  -in "$LATEST_BACKUP" | tar xzf - -O postgres.dump \
  | docker exec -i staging-pg pg_restore -U postgres -d postgres --clean --if-exists

# 3. Verify the restored DB
docker exec staging-pg psql -U postgres -d postgres -c "
  SELECT count(*) FROM identity.users;
  SELECT count(*) FROM identity.beta_invites WHERE used_at IS NOT NULL;
"

# 4. Tear down
docker rm -f staging-pg
```

**Expected:** Restore completes without errors. User count matches production.

**If restore fails:** This is a SEV-1 — your disaster recovery is broken. See `troubleshooting.md` §12 immediately.

---

### 2.4 Log review

```bash
# Backend errors (last 7 days)
docker compose -f docker-compose.prod.yml logs backend --since 168h 2>&1 | \
  grep -iE 'error|critical|exception' | grep -v 'ERROR 200' | head -50

# Worker errors
docker compose -f docker-compose.prod.yml logs worker --since 168h 2>&1 | \
  grep -iE 'error|critical|exception' | head -50

# Nginx 5xx responses
docker compose -f docker-compose.prod.yml logs nginx --since 168h 2>&1 | \
  grep -E ' 5[0-9]{2} ' | awk '{print $7, $9}' | sort | uniq -c | sort -rn | head -20
```

**Action:** For each unique error, file a ticket. For 5xx responses, identify the endpoint and check the backend logs around the same timestamp.

---

### 2.5 Grafana dashboard review

Open Grafana → "Mastery Engine — Production Overview" dashboard.

Review the last 7 days for:
- **Request rate** — should follow a daily pattern (peak during user waking hours). Anomalous flatlines = frontend/backend down.
- **Response time p95** — should be < 200 ms. Sustained > 500 ms = performance regression.
- **Error rate** — should be < 0.1%. Sustained > 1% = backend bug.
- **Active sessions** — should match `current_user_count` from beta status.
- **WebSocket connections** — should be > 0 during user activity hours.
- **Outbox pending** — should be 0 with brief spikes during traffic bursts.
- **Workers active/dead** — should be 1 active, 0 dead.
- **Cache hit rate** — should be > 80%. Drops indicate cache misconfiguration.
- **Questions/min** — should be > 0 during user activity hours.
- **AI latency** — only relevant if AI is enabled.

Take a screenshot and attach to the weekly report.

---

### 2.6 Dependency updates check

```bash
# Backend Python dependencies
docker compose -f docker-compose.prod.yml exec backend pip list --outdated 2>/dev/null | head -30

# Frontend npm dependencies
docker compose -f docker-compose.prod.yml exec frontend npm outdated 2>/dev/null || true

# Docker image base layers
docker compose -f docker-compose.prod.yml images
```

**Action:** For each outdated package, evaluate:
- Is it a security update? If yes, schedule within 7 days.
- Is it a major version bump? If yes, test on staging first.
- Is it a minor/patch? Schedule within 30 days.

Use Dependabot or Renovate for automated PRs if not already configured.

---

### 2.7 SSL certificate expiry check

```bash
echo | openssl s_client -connect app.masteryengine.com:443 -servername app.masteryengine.com 2>/dev/null \
  | openssl x509 -noout -dates
```

**Expected:** `notAfter` is at least 30 days in the future.

**Action:** If < 14 days, manually renew: `sudo certbot renew`. Verify auto-renewal cron is set.

---

## 3. Incident Response Procedures

### 3.1 Severity definitions

| Severity | Definition | Response time | Examples |
|---|---|---|---|
| SEV-1 | Platform down or major data loss | 15 min | Backend 5xx for all users; DB corrupted; backup restore fails |
| SEV-2 | Major feature broken for > 50% of users | 1 hour | Login broken; study sessions can't be started; email delivery down |
| SEV-3 | Minor feature broken or single-user issue | 4 hours | One user can't submit feedback; admin dashboard slow; MFA setup flaky |
| SEV-4 | Cosmetic or low-impact | 1 week | Typo in UI; non-critical analytics event missing |

### 3.2 SEV-1 response procedure

1. **Acknowledge** in `#beta-status` Slack: "🚨 SEV-1: [brief description]. IC: [your name]. Investigating."
2. **Identify scope**: Is it all users or a subset? All endpoints or specific ones?
3. **Check the dashboard**: Grafana → look for the start of the anomaly.
4. **Check logs**:
   ```bash
   docker compose -f docker-compose.prod.yml logs --since 30m backend worker nginx
   ```
5. **Check Sentry**: filter by time window.
6. **If rollback is faster than fix**: follow `production-launch.md` §8.2 (code rollback).
7. **Communicate every 30 min** to `#beta-status` with status update.
8. **Once resolved**: post a postmortem within 48 hours (template in §3.4).
9. **Notify affected users** via email if the incident lasted > 1 hour.

### 3.3 Common incident playbooks

#### 3.3.1 Backend 5xx spike

```bash
# 1. Identify the failing endpoints
docker compose -f docker-compose.prod.yml logs backend --since 15m | grep -E 'ERROR|5[0-9]{2}' | head -20

# 2. Check Sentry for the underlying exception
# (open Sentry UI, filter by environment=production, last 15 min)

# 3. Common causes:
#    - DB connection pool exhausted → check DATABASE_POOL_SIZE, restart backend
#    - Redis down → check redis health, restart if needed
#    - Bad deploy → rollback per production-launch.md §8.2
#    - Schema mismatch → run pending migrations or rollback

# 4. Mitigation: scale backend horizontally
docker compose -f docker-compose.prod.yml up -d --scale backend=2
```

#### 3.3.2 Database connection exhaustion

```bash
# 1. Check current connections
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT state, count(*), wait_event_type
  FROM pg_stat_activity
  WHERE datname = 'mastery_engine'
  GROUP BY state, wait_event_type;
"

# 2. Identify long-running queries
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT pid, state, now() - query_start AS duration, query
  FROM pg_stat_activity
  WHERE state != 'idle' AND now() - query_start > interval '30 seconds'
  ORDER BY duration DESC;
"

# 3. Terminate runaway queries
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity
  WHERE state = 'active' AND now() - query_start > interval '5 minutes';
"

# 4. If pool exhausted, restart backend (releases all connections)
docker compose -f docker-compose.prod.yml restart backend
```

#### 3.3.3 Worker death

```bash
# 1. Check worker logs
docker compose -f docker-compose.prod.yml logs worker --since 30m | tail -100

# 2. Check if worker process crashed
docker compose -f docker-compose.prod.yml ps worker

# 3. Restart
docker compose -f docker-compose.prod.yml restart worker

# 4. Verify recovery
sleep 30
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT worker_id, status, last_seen_at FROM infrastructure.worker_heartbeats ORDER BY started_at DESC LIMIT 5;
"

# 5. If workers keep dying, scale up
docker compose -f docker-compose.prod.yml up -d --scale worker=2

# 6. Investigate root cause — likely an unhandled exception in a job handler.
#    Check dead_letter_events for the specific event type.
```

#### 3.3.4 Outbox backlog growth

```bash
# 1. Quantify
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT count(*) FROM infrastructure.outbox_events WHERE consumed_at IS NULL;
"

# 2. Check if dispatcher is running
docker compose -f docker-compose.prod.yml logs worker --since 10m | grep -i 'outbox\|dispatcher'

# 3. Check for stuck leases
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT * FROM infrastructure.outbox_leases WHERE released_at IS NULL AND expires_at < now();
"

# 4. Release stuck leases
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  UPDATE infrastructure.outbox_leases
  SET released_at = now(), release_reason = 'lease_expired'
  WHERE released_at IS NULL AND expires_at < now();
"

# 5. Restart worker to kick the dispatcher
docker compose -f docker-compose.prod.yml restart worker
```

#### 3.3.5 Redis unavailable

```bash
# 1. Check Redis health
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" ping
# If "Could not connect" → Redis is down

# 2. Check Redis logs
docker compose -f docker-compose.prod.yml logs redis --since 30m

# 3. Common cause: maxmemory exceeded
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" info memory | grep -E 'used_memory|maxmemory|evicted'

# 4. Restart Redis (data persists in the volume)
docker compose -f docker-compose.prod.yml restart redis

# 5. If data is corrupted, restore from backup
# (see troubleshooting.md §13)
```

#### 3.3.6 Email delivery failure

```bash
# 1. Check recent failures
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT to_email, status, bounce_type, reason, created_at
  FROM infrastructure.email_delivery_log
  WHERE status IN ('failed', 'bounced') AND created_at > now() - interval '24 hours'
  ORDER BY created_at DESC LIMIT 20;
"

# 2. If SMTP provider is down, check status page
# (Postmark: https://status.postmark.com, SES: https://health.aws.amazon.com)

# 3. If it's a config issue, verify SMTP credentials:
docker compose -f docker-compose.prod.yml exec backend python -c "
import smtplib
s = smtplib.SMTP('$SMTP_HOST', $SMTP_PORT)
s.starttls()
s.login('$SMTP_USERNAME', '$SMTP_PASSWORD')
print('SMTP login OK')
s.quit()
"

# 4. Requeue failed emails (if your system supports it)
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  UPDATE infrastructure.email_delivery_log
  SET status = 'queued', next_retry_at = now(), attempt_count = attempt_count + 1
  WHERE status = 'failed' AND attempt_count < 3;
"
```

### 3.4 Postmortem template

```markdown
# Postmortem: [Incident title]

**Date:** YYYY-MM-DD
**Severity:** SEV-N
**Duration:** Xh Ym
**Incident Commander:** [name]
**Responders:** [names]

## Summary
[1-2 sentence description]

## Timeline
- T+0:00 — [detection]
- T+0:05 — [acknowledgement]
- T+0:15 — [investigation step]
- T+0:45 — [mitigation applied]
- T+1:30 — [resolved]

## Impact
- Users affected: [N / 20]
- Features degraded: [list]
- Data loss: [yes/no, scope]
- Revenue impact: [n/a for beta]

## Root cause
[Technical explanation]

## Contributing factors
- [Factor 1]
- [Factor 2]

## What went well
- [Thing 1]

## What went badly
- [Thing 1]

## Action items
- [ ] [Action] — [owner] — [due date]
- [ ] [Action] — [owner] — [due date]

## Lessons learned
- [Lesson]
```

---

## 4. Maintenance Windows

### 4.1 Scheduled maintenance procedure

For planned downtime (DB migration, schema change, dependency upgrade):

1. **Announce 48 hours in advance** to all beta users via email:
   > Subject: Scheduled maintenance — [date] [time]
   >
   > The Mastery Engine will be unavailable on [date] from [start] to [end] UTC for [reason].
   > We expect downtime of [duration]. Thank you for your patience.

2. **Pick a low-traffic window** — typically 02:00–04:00 UTC Sunday.

3. **Take a backup immediately before** the maintenance:
   ```bash
   /opt/mastery-engine/scripts/backup.sh
   ```

4. **Display maintenance banner**: set `BETA_FLAG_NOTIFICATIONS_ENABLED=false` won't help — instead, set the frontend to maintenance mode (if supported) or display a banner via Nginx:
   ```nginx
   # In nginx.conf, temporarily add:
   location / {
     return 503;
   }
   error_page 503 /maintenance.html;
   ```

5. **Perform the maintenance**.

6. **Verify** with the daily check list (§1).

7. **Announce completion** to users.

### 4.2 Database migration procedure

When Alembic migrations are introduced (post-beta):

```bash
# 1. Backup
./scripts/backup.sh

# 2. Apply migration on a staging copy first
docker compose -f docker-compose.staging.yml exec backend alembic upgrade head

# 3. Verify staging
# [... smoke tests ...]

# 4. Apply on production
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 5. Verify production
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "\dt"

# 6. If rollback needed:
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1
```

### 4.3 Docker image upgrade

```bash
# 1. Pull the new image
docker compose --env-file .env.production -f docker-compose.prod.yml pull

# 2. Verify the digest
docker images | grep mastery

# 3. Rolling restart (one service at a time, in dependency order)
docker compose -f docker-compose.prod.yml up -d --no-deps worker
docker compose -f docker-compose.prod.yml up -d --no-deps backend
docker compose -f docker-compose.prod.yml up -d --no-deps frontend

# 4. Verify after each
curl -sf https://app.masteryengine.com/api/v1/health/ready | jq .
```

### 4.4 Certbot renewal (every 60 days, automatic)

The cron job in `deployment-checklist.md` §3.1 handles this automatically. Verify quarterly:

```bash
sudo certbot certificates
# Should show "NEXT RENEWAL" at least 30 days in the future
```

---

## 5. Capacity Review (Before User-Count Expansion)

Before raising `MAX_BETA_USERS`, complete this checklist:

### 5.1 Database capacity

- [ ] `pg_database_size('mastery_engine')` < 5 GB
- [ ] Active connections average < 50 (25% of `max_connections=200`)
- [ ] No queries averaging > 100 ms in `pg_stat_statements`
- [ ] Autovacuum keeping up (check `pg_stat_user_tables.last_autovacuum` — should be within last 24h for high-churn tables)
- [ ] WAL generation rate stable (check `pg_stat_bgwriter`)

### 5.2 Redis capacity

- [ ] `used_memory` < 60% of `maxmemory` (512 MB prod default → use < 300 MB)
- [ ] `evicted_keys` low (cache misses are OK; eviction storms are not)
- [ ] `connected_clients` < 100
- [ ] `rejected_connections` = 0

### 5.3 Backend capacity

- [ ] CPU average < 50% (sustained)
- [ ] Memory average < 60% of container limit
- [ ] p95 response time < 200 ms
- [ ] Error rate < 0.1%
- [ ] No 5xx spikes during peak hours

### 5.4 Worker capacity

- [ ] Outbox pending < 10 (sustained)
- [ ] Worker CPU < 50%
- [ ] `jobs_processed / jobs_failed` ratio > 95%
- [ ] No `consecutive_failures` > 3 on any scheduled job

### 5.5 Network capacity

- [ ] Inbound bandwidth < 50% of NIC capacity
- [ ] Outbound bandwidth < 50%
- [ ] No packet loss on `eth0`

### 5.6 Backup capacity

- [ ] Backup directory < 70% of disk
- [ ] S3 bucket storage < budget (typically $5–10/month for beta)
- [ ] Restore drill completed within the last week

If all green, scale up by 50% (e.g. 20 → 30 → 45 → 70 → 100). Do not jump directly to 100 users.

---

## 6. On-Call Rotation

### 6.1 Schedule

For the Closed Beta, the on-call rotation is:

| Week | Primary | Secondary |
|---|---|---|
| Week 1 (launch) | SRE 1 | SRE 2 |
| Week 2 | SRE 2 | SRE 1 |
| Week 3 | SRE 1 | SRE 2 |
| ... | ... | ... |

The **primary** responds to alerts within 15 minutes (SEV-1/2) or 4 hours (SEV-3/4). The **secondary** is the escalation point if the primary doesn't respond within 15 minutes.

### 6.2 Handoff procedure

At the end of each on-call week (Friday 17:00 UTC):

1. **Primary writes a handoff doc**:
   ```markdown
   # On-call handoff — Week of [date]

   ## Open issues
   - [Issue 1] — current status, next step
   - [Issue 2] — current status, next step

   ## Recent incidents
   - [Incident] — resolved/postmortem link

   ## Things to watch
   - [Anomaly 1]
   - [Anomaly 2]

   ## Backup status
   - Last successful: [date]
   - Last verified: [date]
   ```

2. **Handoff meeting** (15 min) — primary walks secondary through the doc.

3. **Secondary acknowledges** in `#beta-status` Slack.

### 6.3 Alert routing

- **Slack**: `#beta-alerts` (non-paging)
- **PagerDuty** (or phone call for beta): SEV-1 only
- **Email**: SEV-2 and above

---

## 7. Quick Reference: Daily Check Script

Save this as `/opt/mastery-engine/scripts/daily-check.sh` and run via cron at 08:00 UTC:

```bash
#!/usr/bin/env bash
set -u

cd /opt/mastery-engine
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
ALERT_WEBHOOK="${SLACK_WEBHOOK:-}"

check() {
  local name="$1" cmd="$2" expected="$3"
  local result
  result=$(eval "$cmd" 2>&1)
  if echo "$result" | grep -qE "$expected"; then
    echo "✅ $name"
  else
    echo "❌ $name"
    echo "  Expected: $expected"
    echo "  Got: $result" | head -5
    # Post to Slack
    if [ -n "$ALERT_WEBHOOK" ]; then
      curl -s -X POST -H 'Content-Type: application/json' \
        --data "{\"text\":\"❌ Daily check failed: $name\"}" \
        "$ALERT_WEBHOOK" >/dev/null
    fi
  fi
}

check "Backend health" \
  "curl -sf https://app.masteryengine.com/api/v1/health | jq -r .status" \
  "healthy"

check "Backend ready" \
  "curl -sf https://app.masteryengine.com/api/v1/health/ready | jq -r .status" \
  "ready"

check "Postgres" \
  "docker compose -f docker-compose.prod.yml exec -T postgres pg_isready -U mastery" \
  "accepting connections"

check "Redis" \
  "docker compose -f docker-compose.prod.yml exec -T redis redis-cli -a \${REDIS_PASSWORD} ping" \
  "PONG"

check "Outbox pending" \
  "docker compose -f docker-compose.prod.yml exec -T postgres psql -U mastery -d mastery_engine -t -c 'SELECT count(*) FROM infrastructure.outbox_events WHERE consumed_at IS NULL'" \
  "^0$"

check "Dead letters" \
  "docker compose -f docker-compose.prod.yml exec -T postgres psql -U mastery -d mastery_engine -t -c 'SELECT count(*) FROM infrastructure.dead_letter_events WHERE resolved_at IS NULL'" \
  "^0$"

check "Disk space" \
  "df --output=pcent / | tail -1 | tr -d ' '" \
  "^[0-6][0-9]%$"
```

Make it executable: `chmod +x /opt/mastery-engine/scripts/daily-check.sh`

Cron:
```
0 8 * * * /opt/mastery-engine/scripts/daily-check.sh >> /var/log/mastery-daily-check.log 2>&1
```

---

**End of operations checklist.** Next: read `troubleshooting.md` for resolution procedures for every failure mode referenced above.
