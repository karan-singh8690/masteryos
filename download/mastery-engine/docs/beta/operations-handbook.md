# Operations Handbook — Mastery Engine Closed Beta

> **Audience:** On-call SRE, operations engineer.
> **Scope:** Daily, weekly, and incident-driven operational tasks for the Closed Beta.
> **Source of truth:** `/admin/beta-ops/operations` page; `GET /api/v1/admin/beta-ops/operations` API.
> **Last updated:** 2026-07-03 (Task 026)

---

## 0. The Operations Mission

Keep the platform **available, correct, and observable** for 20-100 beta users. The bar is:
- **Uptime**: 99.5% (allows ~50 min downtime/week)
- **p95 latency**: < 500ms
- **Error rate**: < 0.1%
- **Recovery time**: < 30 minutes from incident detection

---

## 1. Daily Operations (15 minutes)

### 1.1 Open the Operations Page

URL: `https://app.masteryengine.com/admin/beta-ops/operations`

Check the 12 health cards:

| Card | What to check | Action if red |
|---|---|---|
| Platform Health | Status = `healthy` | Investigate downstream cards |
| Worker Health | All workers `running`, `last_seen` < 60s | Restart stale workers |
| Background Jobs | No `failing` jobs | Check job's `last_error` |
| Queue Status | `pending` < 100 | See §3.4 (outbox backlog) |
| Email Delivery | `failed` < 1% of total | See §3.6 (email issues) |
| Notification Delivery | `failed` < 5% | Check notification subscriber logs |
| Database Health | `connections` < 100 | See §3.2 (DB connections) |
| Redis Health | (via Prometheus) | See §3.3 (Redis issues) |
| Storage Usage | `database_mb` growing linearly | See §3.7 (disk full) |
| API Latency | `avg_ms_24h` < 500 | See §3.5 (slow API) |
| AI Usage | (informational) | N/A |
| Cost Metrics | (informational) | N/A |

### 1.2 Check Sentry

Open `https://sentry.io/organizations/<org>/projects/mastery-engine/`

- Any new `fatal` or `error` events in the last 24 hours?
- Triage each: assign, resolve, or ignore with a reason

### 1.3 Check Slack Alerts

- `#beta-alerts` — any critical alerts?
- `#beta-status` — any incident reports?

### 1.4 Daily Summary

Post to `#beta-status`:
```
[2026-07-03 08:15 UTC] Daily ops check — ALL GREEN
  Platform: healthy
  Workers: 2/2 running
  Outbox: pending=0
  Dead letters: 0
  Email: 98% delivered
  DB: 23 connections, 312 MB
  Sentry: 0 new errors
```

---

## 2. Weekly Operations (45 minutes)

### 2.1 Capacity Review

```bash
# CPU average (last 7 days)
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Postgres connections
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT count(*), state FROM pg_stat_activity GROUP BY state;
"

# Redis memory
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" info memory | grep used_memory_human

# Slow queries
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT query, calls, mean_exec_time, total_exec_time
  FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
"
```

Investigate any:
- CPU > 60% sustained
- Memory > 80%
- Postgres connections > 100 (50% of max)
- Slow queries regressing > 2x

### 2.2 Backup Restore Drill

```bash
# Restore the latest backup to a staging container
docker run -d --name staging-pg -e POSTGRES_PASSWORD=test postgres:16-alpine
LATEST_BACKUP=$(ls -t /opt/mastery-engine/backups/mastery_engine_*.tar.gz.enc | head -1)
openssl enc -d -aes-256-cbc -pbkdf2 -pass pass:$BACKUP_ENCRYPTION_KEY \
  -in "$LATEST_BACKUP" | tar xzf - -O postgres.dump \
  | docker exec -i staging-pg pg_restore -U postgres -d postgres --clean --if-exists
docker exec staging-pg psql -U postgres -d postgres -c "SELECT count(*) FROM identity.users;"
docker rm -f staging-pg
```

If restore fails → SEV-1. See `troubleshooting.md` §12.

### 2.3 Log Review

```bash
docker compose -f docker-compose.prod.yml logs backend --since 168h 2>&1 | grep -iE 'error|critical' | head -50
docker compose -f docker-compose.prod.yml logs worker --since 168h 2>&1 | grep -iE 'error|critical' | head -50
docker compose -f docker-compose.prod.yml logs nginx --since 168h 2>&1 | grep -E ' 5[0-9]{2} ' | head -20
```

### 2.4 SSL Certificate Check

```bash
echo | openssl s_client -connect app.masteryengine.com:443 2>/dev/null | openssl x509 -noout -dates
```

If `notAfter` < 14 days → `sudo certbot renew`.

---

## 3. Incident Playbooks

### 3.1 SEV-1: Backend 5xx Spike

1. Check `/admin/beta-ops/operations` → Platform Health
2. Check Sentry for the underlying exception
3. Common causes:
   - DB connection pool exhausted → restart backend
   - Redis down → restart Redis
   - Bad deploy → rollback per `release-management.md` §5
4. Mitigate: `docker compose -f docker-compose.prod.yml up -d --scale backend=2`

### 3.2 SEV-1: Database Connection Exhaustion

```bash
# Check current connections
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT state, count(*), wait_event_type
  FROM pg_stat_activity WHERE datname = 'mastery_engine'
  GROUP BY state, wait_event_type;
"

# Terminate long-running queries
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity
  WHERE state = 'active' AND now() - query_start > interval '5 minutes';
"

# Restart backend (releases all connections)
docker compose -f docker-compose.prod.yml restart backend
```

### 3.3 SEV-1: Redis Down

```bash
# Check Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" ping

# Check logs
docker compose -f docker-compose.prod.yml logs redis --since 30m

# Common cause: maxmemory exceeded
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" info memory | grep -E 'used_memory|maxmemory|evicted'

# Restart
docker compose -f docker-compose.prod.yml restart redis
```

### 3.4 SEV-2: Outbox Backlog Growth

```bash
# Quantify
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT count(*) FROM infrastructure.outbox_events WHERE consumed_at IS NULL;
"

# Check for stuck leases
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT * FROM infrastructure.outbox_leases WHERE released_at IS NULL AND expires_at < now();
"

# Release stuck leases
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  UPDATE infrastructure.outbox_leases SET released_at = now(), release_reason = 'lease_expired'
  WHERE released_at IS NULL AND expires_at < now();
"

# Restart worker
docker compose -f docker-compose.prod.yml restart worker
```

### 3.5 SEV-2: Slow API

```bash
# Check slow queries
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT pid, state, now() - query_start AS duration, query
  FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '5 seconds'
  ORDER BY duration DESC;
"

# Check Grafana for p95 latency spikes
# Check if it's a specific endpoint:
docker compose -f docker-compose.prod.yml logs backend --since 15m | grep -E 'ERROR|5[0-9]{2}'
```

### 3.6 SEV-2: Email Delivery Failure

```bash
# Check recent failures
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT to_email, status, bounce_type, reason, created_at
  FROM infrastructure.email_delivery_log
  WHERE status IN ('failed', 'bounced') AND created_at > now() - interval '24 hours'
  ORDER BY created_at DESC LIMIT 20;
"

# Test SMTP
docker compose -f docker-compose.prod.yml exec backend python -c "
import smtplib; s = smtplib.SMTP('$SMTP_HOST', $SMTP_PORT); s.starttls()
s.login('$SMTP_USERNAME', '$SMTP_PASSWORD'); print('OK'); s.quit()
"
```

### 3.7 SEV-1: Disk Full

```bash
df -h
du -sh /var/lib/docker/*
docker compose -f docker-compose.prod.yml exec postgres du -sh /var/lib/postgresql/data/log/

# Clear old logs
docker compose -f docker-compose.prod.yml exec postgres rm -f /var/lib/postgresql/data/log/postgres-*.log.*.gz
truncate -s 0 /var/lib/docker/containers/*/*-json.log
```

### 3.8 SEV-1: Worker Death

```bash
# Check worker logs
docker compose -f docker-compose.prod.yml logs worker --since 30m | tail -100

# Restart
docker compose -f docker-compose.prod.yml restart worker

# If workers keep dying, scale up
docker compose -f docker-compose.prod.yml up -d --scale worker=2
```

---

## 4. Operational KPIs

Track these weekly:

| KPI | Target | How to measure |
|---|---|---|
| Uptime | 99.5% | UptimeRobot or Grafana |
| MTTR | < 30 min | Time from alert to resolution |
| p50 latency | < 100ms | Grafana → Request Rate panel |
| p95 latency | < 500ms | Grafana → Response Time p95 |
| p99 latency | < 2000ms | Grafana |
| Error rate (5xx) | < 0.1% | Grafana → Error Rate |
| Outbox pending | 0 sustained | `/admin/beta-ops/operations` |
| Dead letters/week | < 5 | `/admin/beta-ops/operations` |
| Email delivery rate | > 95% | `/admin/beta-ops/operations` |
| DB connections avg | < 50 | `/admin/beta-ops/operations` |
| Redis memory | < 60% of max | Grafana → Redis panel |
| CPU average | < 50% | `docker stats` |
| Memory average | < 60% | `docker stats` |
| Disk usage | < 70% | `df -h` |

---

## 5. On-Call Rotation

| Week | Primary | Secondary |
|---|---|---|
| Week 1 | SRE 1 | SRE 2 |
| Week 2 | SRE 2 | SRE 1 |

- **Primary** responds to SEV-1/2 alerts within 15 min
- **Secondary** is the escalation point if primary doesn't respond within 15 min
- Handoff: Friday 17:00 UTC, with a 15-min handoff meeting

---

## 6. Alert Routing

- **Slack `#beta-alerts`**: All alerts (non-paging)
- **PagerDuty / phone**: SEV-1 only
- **Email**: SEV-2 and above

Configure via `infrastructure/monitoring/alertmanager/alertmanager.yml`.

---

## 7. Maintenance Windows

### 7.1 Scheduled Maintenance

1. Announce 48 hours in advance via email to all beta users
2. Pick a low-traffic window (02:00-04:00 UTC Sunday)
3. Take a backup immediately before
4. Display maintenance banner via Nginx (return 503)
5. Perform the maintenance
6. Verify with the daily check list
7. Announce completion

### 7.2 Database Migration

```bash
# Backup first
make backup

# Apply on staging
docker compose -f docker-compose.staging.yml exec backend alembic upgrade head
# Verify staging

# Apply on production
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# If rollback needed:
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1
```

---

## 8. Quick Reference: Health Check Script

Save as `/opt/mastery-engine/scripts/health-check.sh` and run via cron every 5 min:

```bash
#!/bin/bash
set -u
cd /opt/mastery-engine
PASS=0; FAIL=0

check() {
  local name="$1" cmd="$2" pattern="$3"
  local result
  result=$(eval "$cmd" 2>&1)
  if echo "$result" | grep -qE "$pattern"; then
    echo "✅ $name"; PASS=$((PASS+1))
  else
    echo "❌ $name"; FAIL=$((FAIL+1))
  fi
}

check "Backend" "curl -sf https://app.masteryengine.com/api/v1/health | jq -r .status" "^healthy$"
check "Postgres" "docker compose -f docker-compose.prod.yml exec -T postgres pg_isready -U mastery" "accepting"
check "Redis" "docker compose -f docker-compose.prod.yml exec -T redis redis-cli -a \${REDIS_PASSWORD} ping" "^PONG$"
check "Workers" "docker compose -f docker-compose.prod.yml exec -T postgres psql -U mastery -d mastery_engine -t -c \"SELECT count(*) FROM infrastructure.worker_heartbeats WHERE last_seen_at > now() - interval '1 minute'\"" "^[1-9]"
check "Outbox" "docker compose -f docker-compose.prod.yml exec -T postgres psql -U mastery -d mastery_engine -t -c \"SELECT count(*) FROM infrastructure.outbox_events WHERE consumed_at IS NULL AND created_at > now() - interval '5 minutes'\"" "^0$"
check "Dead letters" "docker compose -f docker-compose.prod.yml exec -T postgres psql -U mastery -d mastery_engine -t -c \"SELECT count(*) FROM infrastructure.dead_letter_events WHERE resolved_at IS NULL\"" "^0$"

echo "PASS: $PASS  FAIL: $FAIL"
[ "$FAIL" -eq 0 ]
```

---

**Next:** Read `support-playbook.md` for handling user support requests, or `product-validation.md` for the overall validation framework.
