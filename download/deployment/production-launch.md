# Production Launch Procedure — Mastery Engine Closed Beta

> **Audience:** SRE / DevOps engineer performing the first production launch.
> **Prerequisite:** `deployment-checklist.md` sections 1–4 must be complete (server provisioned, code cloned, certs obtained, `.env.production` written).
> **Estimated time:** 4–6 hours for first launch; 1–2 hours for subsequent re-deploys.
> **Last updated:** 2026-07-03

---

## 0. Pre-Launch Verification

Before starting, verify:

- [ ] `deployment-checklist.md` §1–4 complete
- [ ] `.env.production` exists at `/opt/mastery-engine/.env.production` with `chmod 600`
- [ ] TLS certs present at `/opt/mastery-engine/infrastructure/nginx/ssl/`
- [ ] JWT RSA keypair present at `/opt/mastery-engine/keys/`
- [ ] DNS A records point to this server
- [ ] You are SSH'd in as the `deployer` user (not root)
- [ ] You have a second terminal open for log tailing

```bash
cd /opt/mastery-engine
ls -la .env.production keys/ infrastructure/nginx/ssl/
# All files must exist. .env.production and keys/jwt-private.pem must be 0600.
```

---

## 1. Stage 1 — Infrastructure Containers (Postgres + Redis)

### 1.1 Start Postgres and Redis

```bash
cd /opt/mastery-engine
docker compose --env-file .env.production -f docker-compose.prod.yml up -d postgres redis
```

### 1.2 Wait for healthchecks

```bash
# Poll until both are healthy (max 60s)
for i in {1..12}; do
  status=$(docker compose -f docker-compose.prod.yml ps --format json postgres redis | jq -r '.Health' | sort -u)
  echo "[$i] $status"
  if [[ "$status" == "healthy" ]]; then break; fi
  sleep 5
done
```

### 1.3 Verify Postgres

```bash
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U mastery -d mastery_engine
# Expected: /var/run/postgresql:5432 - accepting connections

docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "SELECT version();"
# Expected: PostgreSQL 16.x
```

### 1.4 Verify Redis

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" ping
# Expected: PONG
# (Warning about using password on command line is normal)
```

### 1.5 Verify init scripts ran

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "\dn"
# Expected: 10 schemas — identity, content, learning, assessment, mastery,
#           scheduling, analytics, billing, administration, infrastructure
```

If schemas are missing, the init scripts failed. Check:
```bash
docker compose -f docker-compose.prod.yml logs postgres | grep -i 'error\|FATAL'
```

---

## 2. Stage 2 — Backend (creates base tables)

### 2.1 Start backend

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d backend
```

### 2.2 Watch startup logs

```bash
docker compose -f docker-compose.prod.yml logs -f backend
```

Wait for: `INFO: Uvicorn running on http://0.0.0.0:8000` (Press Ctrl+C to stop tailing once you see it.)

### 2.3 Verify backend health

```bash
# From inside the container (bypasses Nginx, which isn't up yet)
docker compose -f docker-compose.prod.yml exec backend curl -sf http://localhost:8000/api/v1/health
# Expected: {"status":"healthy","app":"mastery-engine","version":"0.1.0","timestamp":...}

docker compose -f docker-compose.prod.yml exec backend curl -sf http://localhost:8000/api/v1/health/ready
# Expected: {"status":"ready","checks":[{"name":"database","status":"healthy",...},{"name":"redis","status":"healthy",...}]}
```

### 2.4 Trigger base table creation

The backend's `lifespan` hook calls `init_database()` on startup, which runs `Base.metadata.create_all()`. This creates the ORM-mapped tables (e.g. `identity.users`, `identity.sessions`, `infrastructure.outbox_events`) that the init scripts expect.

Verify:
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "\dt identity.*"
# Expected: includes identity.users, identity.sessions, plus the auth tables from 02-auth-tables.sql
```

### 2.5 Re-run any failed init scripts

If `02-auth-tables.sql`, `03-background-tables.sql`, or `04-beta-tables.sql` failed on first boot (due to the chicken-and-egg dependency on `identity.users`), re-run them now:

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -f /docker-entrypoint-initdb.d/02-auth-tables.sql
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -f /docker-entrypoint-initdb.d/03-background-tables.sql
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -f /docker-entrypoint-initdb.d/04-beta-tables.sql
```

All scripts use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` — safe to re-run.

### 2.6 Final schema verification

```bash
# All beta tables
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT table_schema, table_name
  FROM information_schema.tables
  WHERE table_name LIKE 'beta_%' OR table_name IN ('users','sessions','outbox_events','refresh_tokens','mfa_secrets','scheduled_jobs','worker_heartbeats')
  ORDER BY 1,2;
"
```

Expected: at least 15 rows including `identity.beta_invites`, `identity.beta_feedback`, `analytics.beta_events`, `identity.users`, `identity.sessions`, `identity.refresh_tokens`, `identity.mfa_secrets`, `infrastructure.outbox_events`, `infrastructure.scheduled_jobs`, `infrastructure.worker_heartbeats`.

---

## 3. Stage 3 — Worker

### 3.1 Start worker

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d worker
```

### 3.2 Verify worker is registered

```bash
sleep 15  # Give the worker time to register its heartbeat

docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT worker_id, worker_type, status, last_seen_at
  FROM infrastructure.worker_heartbeats
  ORDER BY started_at DESC LIMIT 5;
"
```

Expected: at least 1 row with `status='running'` and `last_seen_at` within the last 30 seconds.

### 3.3 Verify scheduler picked up jobs

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT name, schedule_type, status, next_run_at
  FROM infrastructure.scheduled_jobs
  ORDER BY next_run_at LIMIT 10;
"
```

### 3.4 Verify outbox dispatcher is draining

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
  SELECT
    count(*) FILTER (WHERE consumed_at IS NULL) AS pending,
    count(*) FILTER (WHERE consumed_at IS NOT NULL) AS consumed,
    count(*) AS total
  FROM infrastructure.outbox_events;
"
```

`pending` should be 0 (or trending to 0 within seconds of an event being created).

---

## 4. Stage 4 — Frontend

### 4.1 Build & start frontend

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build frontend
```

The `--build` flag is required on first launch because the frontend Dockerfile bakes `NEXT_PUBLIC_API_URL` into the JS bundle at build time.

### 4.2 Verify

```bash
docker compose -f docker-compose.prod.yml exec frontend wget -qO- http://localhost:3000/api/v1/health
# Expected: {"status":"healthy",...}
```

### 4.3 Check the build included the correct API URL

```bash
docker compose -f docker-compose.prod.yml exec frontend sh -c 'grep -o "NEXT_PUBLIC_API_URL[^,]*" /app/.next/required-server-files.json | head -1'
# Or check the standalone bundle:
docker compose -f docker-compose.prod.yml exec frontend sh -c 'grep -c "masteryengine.com" /app/.next/static/*/*.js | head -5'
```

If the bundle contains `localhost:8000`, the build args weren't passed correctly. Rebuild with:
```bash
docker compose --env-file .env.production -f docker-compose.prod.yml build --no-cache frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

---

## 5. Stage 5 — Nginx

### 5.1 Start Nginx

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d nginx
```

### 5.2 Verify TLS

```bash
curl -sI https://app.masteryengine.com/ | head -10
# Expected:
# HTTP/2 200
# server: nginx
# content-type: text/html

curl -sI http://app.masteryengine.com/ | head -5
# Expected:
# HTTP/1.1 301 Moved Permanently
# location: https://app.masteryengine.com/
```

### 5.3 Verify security headers

```bash
curl -sI https://app.masteryengine.com/ | grep -iE 'strict-transport|x-frame|x-content|content-security|referrer-policy|permissions-policy'
```

Expected output:
```
strict-transport-security: max-age=31536000; includeSubDomains; preload
x-frame-options: DENY
x-content-type-options: nosniff
referrer-policy: strict-origin-when-cross-origin
permissions-policy: geolocation=(), microphone=(), camera=(), payment=(), usb=()
content-security-policy: default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
```

### 5.4 Verify API proxying

```bash
curl -sf https://app.masteryengine.com/api/v1/health | jq .
# Expected: {"status":"healthy","app":"mastery-engine",...}

curl -sf https://app.masteryengine.com/api/v1/beta/status | jq .
# Expected: {"closed_beta_enabled":true,"max_beta_users":20,"current_user_count":0,"feature_flags":{...}}
```

### 5.5 SSL Labs grade

Open `https://www.ssllabs.com/ssltest/analyze.html?d=app.masteryengine.com` in a browser. Target grade: **A+**.

If grade is lower than A, common causes:
- Missing intermediate cert → re-issue with fullchain.pem including intermediates
- Old TLS versions enabled → `nginx.conf` already restricts to TLS 1.2/1.3 — verify no override
- Weak ciphers → `nginx.conf` already uses modern GCM ciphers

---

## 6. Stage 6 — Monitoring

### 6.1 Start Prometheus and Grafana

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d prometheus grafana
```

### 6.2 Verify Prometheus

```bash
curl -sf http://localhost:9090/-/healthy
# Expected: Prometheus is Healthy.

curl -sf http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health}'
```

Expected targets (assuming you removed the 3 missing exporters per `deployment-checklist.md` §9.1 Option A):
- `mastery-backend` → UP
- `mastery-workers` → UP
- `mastery-frontend` → UP

If any target is DOWN, check:
- The target service is healthy
- The metrics endpoint is reachable from the Prometheus container
- For `mastery-workers`: the admin endpoint may require auth — see `post-launch-monitoring.md` §2

### 6.3 Verify Grafana

```bash
# Wait for Grafana to start
sleep 20

# Health check
curl -sf http://localhost:3001/api/health
# Expected: {"database":"ok","version":"10.x.x"}
```

Log in to Grafana at `http://<server-ip>:3001` (or `https://grafana.masteryengine.com` if you've configured DNS) with username `admin` and the `GRAFANA_PASSWORD` from `.env.production`.

Verify:
- [ ] Data source "Prometheus" shows as connected (Configuration → Data Sources)
- [ ] Dashboard "Mastery Engine — Production Overview" loads with live data (Dashboards → Mastery Engine)

If the dashboard is missing, import it manually:
1. Dashboards → New → Import
2. Upload `infrastructure/monitoring/grafana/dashboards/production-overview.json`
3. Select Prometheus as the data source

### 6.4 Create alerts.yml (if not already done)

```bash
# See post-launch-monitoring.md §3 for the full alerts.yml content
cat > infrastructure/monitoring/prometheus/alerts.yml <<'EOF'
groups:
  - name: mastery-engine
    rules:
      # ... copy from post-launch-monitoring.md
EOF

docker compose -f docker-compose.prod.yml restart prometheus
```

---

## 7. Stage 7 — Admin Bootstrap & First Invite

### 7.1 Bootstrap the first admin user

```bash
# 1. Temporarily disable closed beta (so you can register without an invite)
sed -i 's/CLOSED_BETA_ENABLED=true/CLOSED_BETA_ENABLED=false/' .env.production
docker compose -f docker-compose.prod.yml restart backend worker

# 2. Wait for backend to be ready
sleep 20

# 3. Register the admin user
ADMIN_TOKEN=$(curl -s -X POST https://app.masteryengine.com/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "admin@masteryengine.com",
    "password": "<strong-admin-password>",
    "display_name": "Platform Admin"
  }' | jq -r '.access_token')

# 4. Verify email
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c \
  "SELECT id, email, role, email_verified FROM identity.users WHERE email='admin@masteryengine.com';"

# 5. Promote to administrator
docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c \
  "UPDATE identity.users SET role='administrator', email_verified=true WHERE email='admin@masteryengine.com';"

# 6. Re-enable closed beta
sed -i 's/CLOSED_BETA_ENABLED=false/CLOSED_BETA_ENABLED=true/' .env.production
docker compose -f docker-compose.prod.yml restart backend worker

# 7. Verify admin can log in
ADMIN_TOKEN=$(curl -s -X POST https://app.masteryengine.com/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "admin@masteryengine.com",
    "password": "<strong-admin-password>"
  }' | jq -r '.access_token')

echo "Admin token: $ADMIN_TOKEN"
```

### 7.2 Verify the admin can access beta admin endpoints

```bash
curl -sf https://app.masteryengine.com/api/v1/admin/beta/invites \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .
# Expected: [] (empty list — no invites yet)
```

### 7.3 Create the first 5 invites (canary cohort)

```bash
for email in beta1@example.com beta2@example.com beta3@example.com beta4@example.com beta5@example.com; do
  curl -s -X POST https://app.masteryengine.com/api/v1/admin/beta/invites \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"notes\":\"Closed Beta canary cohort\"}" \
    | jq -c '{email: .email, token: .invite_token, expires_at: .expires_at}'
done
```

⚠️ **Email dispatch is not wired** in the current backend. The invite tokens are returned in the API response — you must manually email them to users (or implement the email dispatch per `deployment-checklist.md` §7.2). Each invite URL is:

```
https://app.masteryengine.com/register?invite_token=<token>&email=<email>
```

### 7.4 Verify the canary registration flow

Using one of the 5 canary invite tokens:

```bash
curl -s -X POST https://app.masteryengine.com/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "beta1@example.com",
    "password": "TestPassword123!",
    "display_name": "Beta User 1",
    "invite_token": "<token-from-step-7.3>"
  }' | jq .
```

Expected: 201 Created with access + refresh tokens.

Verify:
```bash
curl -sf https://app.masteryengine.com/api/v1/beta/status | jq .
# Expected: current_user_count: 1

docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c \
  "SELECT email, used_at FROM identity.beta_invites WHERE email='beta1@example.com';"
# Expected: used_at is NOT NULL
```

### 7.5 Create the remaining 15 invites

After the canary user has successfully logged in, started a study session, and submitted feedback, create the remaining 15 invites:

```bash
for email in beta6@example.com ... beta20@example.com; do
  curl -s -X POST https://app.masteryengine.com/api/v1/admin/beta/invites \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"notes\":\"Closed Beta cohort 1\"}" \
    | jq -c '{email: .email, token: .invite_token, expires_at: .expires_at}'
done
```

---

## 8. Rollback Procedure

If anything goes wrong, here's the rollback sequence.

### 8.1 Quick rollback (config change)

If a config change broke something (e.g. a feature flag flip):

```bash
# 1. Edit .env.production back to the previous value
# 2. Restart the affected services
docker compose -f docker-compose.prod.yml restart backend worker
```

### 8.2 Code rollback (bad deployment)

If a new code deployment is broken:

```bash
# 1. Find the previous good git tag
git tag --sort=-creatordate | head -5

# 2. Checkout the previous tag
git checkout v1.0.0-beta-prev

# 3. Rebuild and restart
docker compose --env-file .env.production -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### 8.3 Database rollback (migration issue)

There are no Alembic migrations yet (see `deployment-checklist.md` §5.3). If a future migration breaks the schema:

```bash
# 1. Identify the broken migration
docker compose -f docker-compose.prod.yml exec backend alembic history

# 2. Downgrade to the previous revision
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1

# 3. If the DB is unrecoverable, restore from the latest backup
./scripts/backup.sh --restore /opt/mastery-engine/backups/mastery_engine_<latest>.tar.gz.enc
```

### 8.4 Full disaster recovery

If the entire server is lost:

1. Provision a new server (per `deployment-checklist.md` §1).
2. Install Docker + clone the repo + copy `.env.production` from secrets store.
3. Restore the latest backup (per `scripts/backup.sh --restore`).
4. Start services in the order: postgres+redis → backend → worker → frontend → nginx → prometheus+grafana.
5. Verify health endpoints.
6. Update DNS to point to the new server IP.
7. Notify beta users of the disruption.

**Target RTO**: 2 hours. **Current RPO**: 24 hours (daily backup cron).

---

## 9. Post-Launch Verification

Immediately after the launch, complete the smoke test in `deployment-checklist.md` §10. The most critical checks:

```bash
# All containers healthy
docker compose -f docker-compose.prod.yml ps

# Backend healthy
curl -sf https://app.masteryengine.com/api/v1/health/ready | jq '.status'
# Expected: "ready"

# Beta status
curl -sf https://app.masteryengine.com/api/v1/beta/status | jq .
# Expected: closed_beta_enabled: true, max_beta_users: 20, current_user_count: <N>

# SSL grade
# Open https://www.ssllabs.com/ssltest/analyze.html?d=app.masteryengine.com

# Sentry receiving events
docker compose -f docker-compose.prod.yml exec backend python -c \
  "import sentry_sdk; sentry_sdk.capture_message('Launch verification'); print('captured')"
```

---

## 10. Launch Communication

### 10.1 Internal announcement

Send to the team Slack/Teams channel:

> 🚀 Mastery Engine Closed Beta is live.
> - URL: https://app.masteryengine.com
> - Admin portal: https://app.masteryengine.com/admin
> - Monitoring: http://<server>:3001 (Grafana)
> - On-call: <engineer-name> for the next 72 hours
> - Status: `#beta-status` Slack channel
> - 5 canary invites sent; 15 remaining pending canary sign-off

### 10.2 External announcement (canary cohort)

Send to the 5 canary users:

> Subject: You're invited to the Mastery Engine Closed Beta
>
> Hi {name},
>
> You've been selected as one of the first 5 canary users for the Mastery Engine Closed Beta — a Python interview prep platform that adapts to what you already know.
>
> Your invite link (valid for 7 days):
> https://app.masteryengine.com/register?invite_token={token}&email={email}
>
> What to expect:
> - 5–10 minute onboarding wizard on first login
> - Floating feedback button on every page — please use it liberally
> - Email replies to feedback within 24 hours
>
> Thanks for helping us shape the platform.
>
> — The Mastery Engine team

### 10.3 Canary sign-off (4 hours after launch)

After 4 hours with no SEV-1 issues from the canary cohort:

- [ ] All 5 canary users have registered
- [ ] At least 3 canary users have started a study session
- [ ] No 5xx error spikes in Grafana
- [ ] No new Sentry events above warning level
- [ ] Outbox queue is draining
- [ ] No dead-letter events

If all green, send the remaining 15 invites.

---

## 11. First 72 Hours On-Call Protocol

| Time | Action |
|---|---|
| T+0h | Launch complete; canary invites sent |
| T+1h | Check Grafana for error rate; check Sentry; respond to feedback |
| T+4h | Canary sign-off; send remaining 15 invites |
| T+8h | Daily metrics review (DAU, sessions, completion rate) |
| T+24h | First daily backup verify; first feedback triage |
| T+48h | Mid-beta health check; review `beta_events` for engagement patterns |
| T+72h | Declare beta stable; rotate off on-call |

For each on-call check, follow the runbook in `operations-checklist.md`.

---

## 12. Known Launch Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Postgres fails to start due to missing SSL certs | High (if SSL left on) | Service down | Disable Postgres SSL OR mount certs per `deployment-checklist.md` §3.2 |
| Nginx fails to start due to missing TLS certs | High | Service down | Certs provisioned per `deployment-checklist.md` §3.1 |
| Compose healthchecks fail (curl missing) | High | Containers marked unhealthy; compose may not start dependent services | Override healthchecks per `deployment-checklist.md` §4.3 |
| Init script chicken-and-egg failure | Medium | Beta tables missing; registration fails | Re-run init scripts after backend starts per §2.5 |
| Email service cannot send (SMTP not in Settings) | High | Password reset, beta invites broken | Patch `ProductionSmtpClient` to read env vars OR send invites manually |
| Admin RBAC not enforced on beta endpoints | Medium | Any user can create invites | Limit who can register via invite flow; track as P1 fix |
| Welcome wizard doesn't persist | Low | UX issue; users re-onboard each session | Track as P2 fix; not a launch blocker |
| Grafana dashboard doesn't auto-provision | Low | Empty Grafana | Import manually per §6.3 |
| `alerts.yml` missing | Medium | No alerts fire | Create per `post-launch-monitoring.md` §3 before launch |
| 3 Prometheus exporters missing | Low | 3 scrape targets show DOWN | Remove scrape jobs OR add exporters per `deployment-checklist.md` §9.1 |

---

**End of launch procedure.** Next: read `beta-launch-guide.md` for the admin onboarding walkthrough, and `operations-checklist.md` for the daily operations runbook.
