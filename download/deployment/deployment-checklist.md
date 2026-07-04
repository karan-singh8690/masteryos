# Deployment Checklist — Mastery Engine Closed Beta

> **Audience:** DevOps / SRE engineers performing the first production deployment.
> **Scope:** Full platform — backend, frontend, workers, PostgreSQL, Redis, Nginx, monitoring, Closed Beta.
> **Status:** Production-grade. Suitable for a real 20-user Closed Beta launch.
> **Last updated:** 2026-07-03

---

## 0. How To Use This Document

This is the **master deployment checklist**. It is organised in execution order — every checkbox must be ticked in sequence. Sections 1–7 are pre-launch (provisioning → build → config → deploy → verify). Sections 8–10 are launch-day and post-launch.

Symbols:

- ☐ — Action required
- 🔴 — Blocker: launch is impossible without this
- 🟠 — High-risk gap; launch possible but with documented risk
- 🟢 — Recommended hardening; not a blocker

---

## 1. Pre-Flight: Server & Access Provisioning

### 1.1 Host requirements

| Resource | Minimum | Recommended (Closed Beta) |
|---|---|---|
| vCPU | 2 | 4 |
| RAM | 4 GB | 8 GB |
| Disk (SSD) | 40 GB | 80 GB |
| OS | Ubuntu 22.04 LTS / Debian 12 | Ubuntu 24.04 LTS |
| Docker | 24.0+ | 26.0+ |
| Docker Compose | v2.20+ | v2.26+ |

- ☐ 🟢 Provision a dedicated VM or bare-metal host. Do **not** co-locate with other production services.
- ☐ 🔴 Create a non-root deployer account (`deployer`) with passwordless sudo. **Never run the stack as root.**
- ☐ 🟢 Configure SSH key-only login; disable password auth (`PasswordAuthentication no` in `/etc/ssh/sshd_config`).
- ☐ 🟢 Configure firewall (UFW) — allow only `22/tcp`, `80/tcp`, `443/tcp`. Block `5432`, `6379`, `8000`, `3000`, `9090`, `3001` from the public internet.
- ☐ 🟢 Configure swap (2 GB) to absorb memory spikes: `fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile`.
- ☐ 🟢 Set the server timezone to UTC: `sudo timedatectl set-timezone UTC`.
- ☐ 🟢 Install baseline tooling: `apt update && apt install -y ca-certificates curl gnupg lsb-release jq awscli openssl`.
- ☐ 🟢 Configure NTP: `apt install -y chrony && systemctl enable --now chrony`.

### 1.2 DNS

- ☐ 🔴 Register the production domain (e.g. `masteryengine.com`).
- ☐ 🔴 Create DNS A records:
  - `app.masteryengine.com` → server public IP (frontend + API on the same host via Nginx)
  - `api.masteryengine.com` → server public IP (alternative, optional — Nginx can serve both on the same host)
  - `grafana.masteryengine.com` → server public IP (or private IP if monitoring is internal-only)
- ☐ 🟢 Set TTL to 300s during launch week; raise to 3600s after stabilisation.
- ☐ 🟢 Verify DNS propagation: `dig +short app.masteryengine.com` from at least 3 geographic locations.

### 1.3 Secrets store

- ☐ 🟢 Choose a secrets backend **before** generating any secrets:
  - Option A (simple): `sops` + age-encrypted `.env.production` committed to a private ops repo
  - Option B (recommended): HashiCorp Vault or AWS Secrets Manager
  - Option C (Docker native): Docker Secrets (works with Swarm) or `docker compose secrets` (Compose v2.23+)
- ☐ 🟢 Document who has access to the secrets store; enforce MFA on the secrets backend.

---

## 2. Source Code & Build

### 2.1 Repository

- ☐ 🔴 Clone the Mastery Engine repository to `/opt/mastery-engine/`:
  ```bash
  sudo mkdir -p /opt/mastery-engine
  sudo chown deployer:deployer /opt/mastery-engine
  git clone <repo-url> /opt/mastery-engine
  cd /opt/mastery-engine
  ```
- ☐ 🔴 Checkout the tagged release (e.g. `git checkout v1.0.0-beta`). **Never deploy from `main`.**
- ☐ 🟢 Verify the working tree is clean: `git status` must show nothing.

### 2.2 Docker images

- ☐ 🔴 Build production images:
  ```bash
  docker compose -f docker-compose.prod.yml build
  ```
- ☐ 🟠 **Inspect `infrastructure/docker/backend.Dockerfile`**: the runtime stage currently installs `pip install -e ".[dev]"`. For Closed Beta this is acceptable but should be hardened before public launch. Track as a post-launch follow-up.
- ☐ 🟠 **Inspect `infrastructure/docker/frontend.Dockerfile`**: it uses `npm install` (not `npm ci`). For reproducible builds, switch to `npm ci` after the first successful launch.
- ☐ 🟢 Verify image sizes: backend should be < 600 MB, frontend < 250 MB. If larger, audit layers.
- ☐ 🟢 Tag images with the git SHA: `docker tag mastery-engine-backend:latest registry.example.com/mastery-backend:$(git rev-parse --short HEAD)`.

### 2.3 Known build-time gaps (do NOT block launch, but track)

These were identified during code inspection and **must be remediated before public GA**, but are acceptable for a 20-user Closed Beta:

| Gap | File | Risk | Mitigation for Closed Beta |
|---|---|---|---|
| `curl` missing in backend & frontend runtime images | `*.Dockerfile` | Compose healthchecks use `curl -f`; they will fail silently | Override healthcheck in compose to use `python -c` (backend) and `wget` (frontend) — see §4.3 |
| No `output: 'standalone'` in `next.config.js` | `frontend/next.config.js` | Frontend image may be larger than needed; standalone build is faster | Acceptable; frontend image still works |
| `pip install -e ".[dev]"` ships dev deps to prod | `backend.Dockerfile` | Increased attack surface | Acceptable for beta; remediate post-launch |

---

## 3. TLS Certificates & JWT Keys

### 3.1 TLS certificates for Nginx

- ☐ 🔴 Obtain TLS certificates. **Recommended for Closed Beta: Let's Encrypt via certbot** (free, 90-day validity, auto-renew):
  ```bash
  sudo apt install -y certbot
  sudo certbot certonly --standalone -d app.masteryengine.com -d api.masteryengine.com
  ```
  Certificates land in `/etc/letsencrypt/live/app.masteryengine.com/`.
- ☐ 🔴 Create the Nginx SSL directory and link the certs:
  ```bash
  sudo mkdir -p /opt/mastery-engine/infrastructure/nginx/ssl
  sudo cp /etc/letsencrypt/live/app.masteryengine.com/fullchain.pem /opt/mastery-engine/infrastructure/nginx/ssl/fullchain.pem
  sudo cp /etc/letsencrypt/live/app.masteryengine.com/privkey.pem  /opt/mastery-engine/infrastructure/nginx/ssl/privkey.pem
  sudo chown -R deployer:deployer /opt/mastery-engine/infrastructure/nginx/ssl
  sudo chmod 600 /opt/mastery-engine/infrastructure/nginx/ssl/privkey.pem
  ```
- ☐ 🔴 Configure auto-renewal:
  ```bash
  sudo crontab -e
  # Add: 0 3 * * * certbot renew --quiet --post-hook "cp /etc/letsencrypt/live/app.masteryengine.com/*.pem /opt/mastery-engine/infrastructure/nginx/ssl/ && docker compose -f /opt/mastery-engine/docker-compose.prod.yml exec nginx nginx -s reload"
  ```

### 3.2 TLS certificates for PostgreSQL (in-container)

- ☐ 🟠 The `postgresql.conf` enables `ssl=on` and references `/etc/ssl/certs/postgres.pem` and `/etc/ssl/private/postgres-key.pem`, but the prod compose does **not** mount these files. Postgres will refuse to start.
- ☐ 🟠 **Two remediation options** — pick one **before** first boot:

  **Option A (recommended for beta): disable SSL in Postgres.**
  Edit `infrastructure/postgres/postgresql.conf` and set `ssl=off`. The Nginx → Postgres traffic stays on the private Docker network; SSL is not required for inter-container traffic on a single host.

  **Option B (recommended for prod): generate and mount Postgres certs.**
  ```bash
  mkdir -p /opt/mastery-engine/infrastructure/postgres/ssl
  openssl req -new -x509 -days 3650 -nodes \
    -out /opt/mastery-engine/infrastructure/postgres/ssl/postgres.pem \
    -keyout /opt/mastery-engine/infrastructure/postgres/ssl/postgres-key.pem \
    -subj "/CN=postgres"
  chmod 600 /opt/mastery-engine/infrastructure/postgres/ssl/postgres-key.pem
  ```
  Then add to `docker-compose.prod.yml` postgres service:
  ```yaml
  volumes:
    - ./infrastructure/postgres/ssl/postgres.pem:/etc/ssl/certs/postgres.pem:ro
    - ./infrastructure/postgres/ssl/postgres-key.pem:/etc/ssl/private/postgres-key.pem:ro
  ```

### 3.3 RS256 JWT keypair

- ☐ 🔴 The backend uses `JWT_ALGORITHM=RS256` in production. Generate the RSA keypair:
  ```bash
  mkdir -p /opt/mastery-engine/keys
  openssl genrsa -out /opt/mastery-engine/keys/jwt-private.pem 4096
  openssl rsa -in /opt/mastery-engine/keys/jwt-private.pem -pubout -out /opt/mastery-engine/keys/jwt-public.pem
  chmod 600 /opt/mastery-engine/keys/jwt-private.pem
  chmod 644 /opt/mastery-engine/keys/jwt-public.pem
  ```
- ☐ 🔴 The prod compose mounts `./keys:/app/keys:ro` on the backend service. Verify the path matches (`JWT_KEYS_DIR=/app/keys`).
- ☐ 🟢 Back up the **private** key to the secrets store immediately. If lost, all user sessions are invalidated.

---

## 4. Environment Configuration

### 4.1 Create the production env file

- ☐ 🔴 Copy the template:
  ```bash
  cp .env.example .env.production
  ```
- ☐ 🔴 Edit `.env.production` and set **every** variable per `environment-reference.md`. The most critical are:

  | Variable | Required value |
  |---|---|
  | `APP_ENV` | `production` |
  | `DATABASE_PASSWORD` | 32+ char random (`openssl rand -base64 32`) |
  | `DATABASE_URL` | `postgresql+asyncpg://mastery:${DATABASE_PASSWORD}@postgres:5432/mastery_engine` |
  | `REDIS_PASSWORD` | 32+ char random (`openssl rand -base64 32`) |
  | `JWT_ALGORITHM` | `RS256` (do **not** use `HS256` — `.env.example` ships with HS256, which is wrong for prod) |
  | `JWT_KEYS_DIR` | `/app/keys` |
  | `JWT_ISSUER` | `https://app.masteryengine.com` |
  | `JWT_AUDIENCE` | `mastery-engine-api` |
  | `CORS_ORIGINS` | `https://app.masteryengine.com` |
  | `ENABLE_DOCS` | `false` |
  | `CLOSED_BETA_ENABLED` | `true` |
  | `MAX_BETA_USERS` | `20` |
  | `BETA_INVITE_TOKEN_TTL_HOURS` | `168` (7 days) |
  | `BETA_FLAG_AI_ENABLED` | `false` (unless AI is intended for beta) |
  | `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` | Real SMTP provider (Postmark, SES, etc.) |
  | `SENTRY_DSN` | Project DSN from Sentry |
  | `GRAFANA_PASSWORD` | 24+ char random |
  | `BACKUP_ENCRYPTION_KEY` | 32+ char random (`openssl rand -base64 32`) |

- ☐ 🔴 File permissions: `chmod 600 .env.production && chown deployer:deployer .env.production`.
- ☐ 🟢 Verify the file is in `.gitignore` (it should be — confirm with `git status`).

### 4.2 AI provider keys (optional for Closed Beta)

- ☐ 🟢 If `BETA_FLAG_AI_ENABLED=true`:
  - ☐ Provision an Ollama instance (CPU is fine for beta; GPU recommended for prod).
  - ☐ Set `OLLAMA_HOST=http://ollama:11434` (or remote URL).
  - ☐ Set `OLLAMA_MODEL=qwen2.5:7b` (default; smaller is faster).
  - ☐ If using OpenAI instead: set `OPENAI_API_KEY=sk-...`.
  - ☐ If using Gemini: set `GEMINI_API_KEY=...`.
- ☐ 🟢 If `BETA_FLAG_AI_ENABLED=false`: leave all AI keys unset. The AI router will return 503 gracefully.

### 4.3 Fix compose healthchecks (REQUIRED before `up`)

The prod compose uses `curl -f` for backend and frontend healthchecks, but `curl` is **not installed** in the runtime images. Apply this override **before** first boot:

- ☐ 🔴 Edit `docker-compose.prod.yml`. For the **backend** service, replace the healthcheck with:
  ```yaml
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/api/v1/health/ready').status==200 else sys.exit(1)"]
    interval: 15s
    timeout: 10s
    retries: 3
    start_period: 60s
  ```
- ☐ 🔴 For the **frontend** service, replace with:
  ```yaml
  healthcheck:
    test: ["CMD", "node", "-e", "require('http').get('http://localhost:3000/api/v1/health', r => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"]
    interval: 15s
    timeout: 10s
    retries: 3
    start_period: 30s
  ```
- ☐ 🟠 For the **worker** service, replace `python -c "import requests; ..."` with the equivalent `urllib` version (no external dep):
  ```yaml
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://backend:8000/api/v1/admin/bg/workers').status==200 else sys.exit(1)"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
  ```

### 4.4 Realise HA replicas (optional for beta)

- ☐ 🟢 The prod compose declares `deploy.replicas: 2` for backend and worker. Plain `docker compose up` **ignores** `deploy.replicas` (Swarm-only). For Closed Beta, single instances are acceptable. For HA, use explicit scale:
  ```bash
  docker compose -f docker-compose.prod.yml up -d --scale backend=2 --scale worker=2
  ```

---

## 5. Database Initialization

### 5.1 First-boot prerequisites

- ☐ 🔴 The 4 init scripts under `infrastructure/postgres/init/` (sorted `01` → `04`) run automatically on the first start of the postgres container (empty data volume).
- ☐ 🟠 **Chicken-and-egg caveat (HIGH PRIORITY)**: `02-auth-tables.sql` ALTERs and references `identity.users` and `identity.sessions`, but those tables are **not** created by any init script — they are created by the application via SQLAlchemy `Base.metadata.create_all()` at backend startup. **Order of operations must be:**
  1. Start postgres container (init scripts run, but `02` will FAIL on the FK to `identity.users`).
  2. **OR** pre-seed the base tables: run `docker compose -f docker-compose.prod.yml exec backend python -c "from app.infrastructure.database.engine import init_database; import asyncio; asyncio.run(init_database())"` to create the base tables first.
  3. Then re-run any failed init scripts manually: `docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -f /docker-entrypoint-initdb.d/02-auth-tables.sql`.

  **Recommended workflow**: see `production-launch.md` §3 for the exact boot sequence that avoids this.

### 5.2 Verify schema

- ☐ 🔴 After first boot, verify all 10 schemas exist:
  ```bash
  docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "\dn"
  ```
  Expected: `identity, content, learning, assessment, mastery, scheduling, analytics, billing, administration, infrastructure`.

- ☐ 🔴 Verify all beta tables exist:
  ```bash
  docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_name LIKE 'beta_%'
    ORDER BY 1,2;
  "
  ```
  Expected: 3 rows — `identity.beta_invites`, `identity.beta_feedback`, `analytics.beta_events`.

- ☐ 🔴 Verify extensions:
  ```bash
  docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c "SELECT extname FROM pg_extension ORDER BY 1;"
  ```
  Expected: `citext, pg_trgm, btree_gin, uuid-ossp, plpgsql`.

### 5.3 Migrations

- ☐ 🟠 The `backend/alembic/` directory exists but contains **no migration files**. `target_metadata = None` in `env.py` means autogenerate is not wired. For Closed Beta this is acceptable — the init SQL scripts are the source of truth. **Track as post-launch follow-up:** generate an initial Alembic migration capturing the current schema so future changes are versioned.

---

## 6. Service Startup Sequence

### 6.1 Order

Start services in this exact order to avoid race conditions:

1. ☐ 🔴 Postgres + Redis (with healthcheck wait):
   ```bash
   docker compose -f docker-compose.prod.yml up -d postgres redis
   docker compose -f docker-compose.prod.yml exec postgres pg_isready -U mastery -d mastery_engine
   docker compose -f docker-compose.prod.yml exec redis redis-cli -a ${REDIS_PASSWORD} ping
   ```
2. ☐ 🔴 Backend (creates base tables via `init_database()`):
   ```bash
   docker compose -f docker-compose.prod.yml up -d backend
   sleep 10
   docker compose -f docker-compose.prod.yml logs backend | tail -50
   ```
3. ☐ 🔴 Re-run any failed init scripts (see §5.1):
   ```bash
   docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -f /docker-entrypoint-initdb.d/02-auth-tables.sql
   docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -f /docker-entrypoint-initdb.d/03-background-tables.sql
   docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -f /docker-entrypoint-initdb.d/04-beta-tables.sql
   ```
4. ☐ 🔴 Worker (scheduler, outbox dispatcher, notifications, email):
   ```bash
   docker compose -f docker-compose.prod.yml up -d worker
   ```
5. ☐ 🔴 Frontend:
   ```bash
   docker compose -f docker-compose.prod.yml up -d frontend
   ```
6. ☐ 🔴 Nginx:
   ```bash
   docker compose -f docker-compose.prod.yml up -d nginx
   ```
7. ☐ 🟢 Prometheus + Grafana:
   ```bash
   docker compose -f docker-compose.prod.yml up -d prometheus grafana
   ```

### 6.2 Post-start verification

- ☐ 🔴 Verify all containers are `Up (healthy)`:
  ```bash
  docker compose -f docker-compose.prod.yml ps
  ```
- ☐ 🔴 Verify backend liveness:
  ```bash
  curl -sf https://app.masteryengine.com/api/v1/health | jq .
  ```
  Expected: `{"status":"healthy","app":"mastery-engine","version":"0.1.0","timestamp":...}`.
- ☐ 🔴 Verify backend readiness (DB + Redis):
  ```bash
  curl -sf https://app.masteryengine.com/api/v1/health/ready | jq .
  ```
  Expected: `{"status":"ready","checks":[{"name":"database","status":"healthy",...},{"name":"redis","status":"healthy",...}]}`.
- ☐ 🔴 Verify frontend:
  ```bash
  curl -sfI https://app.masteryengine.com/ | head -5
  ```
  Expected: `HTTP/2 200`, `server: nginx`, `content-type: text/html`.
- ☐ 🔴 Verify HTTPS redirect:
  ```bash
  curl -sI http://app.masteryengine.com/ | head -3
  ```
  Expected: `HTTP/1.1 301 Moved Permanently`, `location: https://app.masteryengine.com/`.
- ☐ 🔴 Verify security headers:
  ```bash
  curl -sI https://app.masteryengine.com/ | grep -iE 'strict-transport|x-frame|x-content|content-security|referrer-policy|permissions-policy'
  ```
  Expected: 6 security headers present.

---

## 7. Closed Beta Configuration

### 7.1 Admin user bootstrap

- ☐ 🔴 Create the first admin user. There is no CLI for this — use the API:
  ```bash
  # 1. Register a normal user (CLOSED_BETA_ENABLED must be temporarily false OR use an invite)
  curl -X POST https://app.masteryengine.com/api/v1/auth/register \
    -H 'Content-Type: application/json' \
    -d '{"email":"admin@masteryengine.com","password":"<strong-password>","display_name":"Admin","invite_token":"<token-if-beta-on>"}'

  # 2. Promote to administrator directly in the DB
  docker compose -f docker-compose.prod.yml exec postgres psql -U mastery -d mastery_engine -c \
    "UPDATE identity.users SET role = 'administrator' WHERE email = 'admin@masteryengine.com';"
  ```
- ☐ 🟠 **RBAC gap**: the closed-beta admin endpoints (`/api/v1/admin/beta/invites*`) currently use `get_current_user_id` but do **not** enforce the admin role — there is a `# In production, add role check here` TODO. Until this is fixed, any authenticated user can create invites. **Mitigation**: leave `CLOSED_BETA_ENABLED=true` and limit who can register via the invite flow. Track as a launch-blocker if external auditors are involved.

### 7.2 Email integration

- ☐ 🟠 The `beta_invitation` email template exists and is registered in the `TEMPLATES` dict, but the `create_invite` and `resend_invite` endpoints in `beta.py` contain `# In production: send invitation email here` comments — **email dispatch is not wired**. **Two options:**
  - **Option A (manual):** create invites via the API, then manually send the invitation email via your SMTP provider using the rendered template.
  - **Option B (recommended):** patch `app/presentation/api/v1/beta.py` to inject `EmailService` and call `email_service.send_template(to=invite.email, template_name="beta_invitation", context={...})` inside `create_invite` and `resend_invite`. This is a small, low-risk change.

### 7.3 Create the 20 invites

- ☐ 🔴 After the admin user is bootstrapped and authenticated, create exactly 20 invites:
  ```bash
  for email in user1@example.com user2@example.com ... user20@example.com; do
    curl -X POST https://app.masteryengine.com/api/v1/admin/beta/invites \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H 'Content-Type: application/json' \
      -d "{\"email\":\"$email\",\"notes\":\"Closed Beta cohort 1\"}"
  done
  ```
- ☐ 🔴 Verify invite count:
  ```bash
  curl -sf https://app.masteryengine.com/api/v1/admin/beta/invites \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq 'length'
  ```
  Expected: `20`.
- ☐ 🔴 Verify beta status:
  ```bash
  curl -sf https://app.masteryengine.com/api/v1/beta/status | jq .
  ```
  Expected: `{"closed_beta_enabled":true,"max_beta_users":20,"current_user_count":0,"feature_flags":{...}}`.

### 7.4 Feature flags

- ☐ 🟢 Default Closed Beta flags (recommended starting point):

  | Flag | Value | Rationale |
  |---|---|---|
  | `BETA_FLAG_LEARNING_ENABLED` | `true` | Core feature |
  | `BETA_FLAG_CONTENT_AUTHORING_ENABLED` | `true` | Needed for content authoring portal |
  | `BETA_FLAG_AI_ENABLED` | `false` | Start without AI to keep cost & latency predictable; enable after beta stabilises |
  | `BETA_FLAG_NOTIFICATIONS_ENABLED` | `true` | Email + in-app notifications |
  | `BETA_FLAG_ANALYTICS_ENABLED` | `true` | Needed to measure engagement |
  | `BETA_FLAG_ADMIN_CONSOLE_ENABLED` | `true` | Admin portal for the 1–2 admins |

- ☐ 🟢 Changing a flag requires restarting **both** `backend` and `worker` (settings are `@lru_cache`'d per process):
  ```bash
  # Edit .env.production, then:
  docker compose -f docker-compose.prod.yml restart backend worker
  ```

---

## 8. Backup & Disaster Recovery

### 8.1 Configure backup script

- ☐ 🔴 Edit `scripts/backup.sh` environment. Set in the crontab or a wrapper:
  ```bash
  BACKUP_DIR=/opt/mastery-engine/backups
  RETENTION_DAYS=30
  BACKUP_ENCRYPTION_KEY=<from-secrets-store>
  DATABASE_HOST=localhost
  DATABASE_PORT=5432
  DATABASE_NAME=mastery_engine
  DATABASE_USER=mastery
  DATABASE_PASSWORD=<from-secrets-store>
  REDIS_HOST=localhost
  REDIS_PORT=6379
  S3_BACKUP_BUCKET=mastery-engine-backups
  SLACK_WEBHOOK=<optional>
  ```
- ☐ 🟠 **Backup script bugs to be aware of** (do NOT launch without understanding):
  - `--verify` and `--restore` flags are checked **after** a full backup runs. Run them as separate commands.
  - Redis backup uses host path `/var/lib/redis/dump.rdb` — does **not** work when Redis runs in a Docker volume. **Workaround**: before running backup, `docker compose exec redis redis-cli -a $REDIS_PASSWORD BGSAVE` then `docker cp mastery-engine-redis-1:/data/dump.rdb /tmp/redis_dump.rdb` and modify the script to read from `/tmp/redis_dump.rdb`.
  - Redis `BGSAVE` does not authenticate — pass `-a $REDIS_PASSWORD` in the script.
  - `.env.production` is included in the tar **before** encryption. If `BACKUP_ENCRYPTION_KEY` is empty, secrets leak at rest. **Always set the encryption key.**

### 8.2 Schedule

- ☐ 🔴 Install cron:
  ```bash
  sudo crontab -e
  # Daily 02:00 UTC backup
  0 2 * * * /opt/mastery-engine/scripts/backup.sh >> /var/log/mastery-backup.log 2>&1
  ```
- ☐ 🟢 Weekly verify:
  ```bash
  # Sunday 03:00 UTC verify
  0 3 * * 0 /opt/mastery-engine/scripts/backup.sh --verify >> /var/log/mastery-backup-verify.log 2>&1
  ```

### 8.3 Restore drill (MUST be performed pre-launch)

- ☐ 🔴 Perform a full restore to a **staging** instance:
  ```bash
  ./scripts/backup.sh --restore /opt/mastery-engine/backups/mastery_engine_<latest>.tar.gz.enc
  ```
- ☐ 🔴 Verify the restored DB has all beta tables and the admin user.
- ☐ 🔴 Document the restore time. Target RTO: **< 2 hours**.
- ☐ 🔴 Document the data loss window. Current RPO: **≤ 24 hours** (daily cron). If tighter RPO is needed, enable Postgres WAL archiving (out of scope for beta).

---

## 9. Monitoring & Alerting

### 9.1 Prometheus

- ☐ 🔴 Verify Prometheus is up: `curl -sf http://localhost:9090/-/healthy` → `Prometheus is Healthy.`
- ☐ 🟠 **Missing exporters**: `prometheus.yml` references `postgres-exporter:9187`, `redis-exporter:9121`, `nginx-exporter:9113` — **none are deployed**. The corresponding scrape jobs will be permanently down. **Options:**
  - **Option A (acceptable for beta):** remove those 3 scrape jobs from `prometheus.yml`. Backend + worker + frontend metrics are sufficient.
  - **Option B (recommended):** add the 3 exporters to `docker-compose.prod.yml`:
    ```yaml
    postgres-exporter:
      image: prometheuscommunity/postgres-exporter:v0.15.0
      environment:
        DATA_SOURCE_NAME: "postgresql://mastery:${DATABASE_PASSWORD}@postgres:5432/mastery_engine?sslmode=disable"
      ports: ["9187:9187"]
      networks: [default]
    redis-exporter:
      image: oliver006/redis_exporter:v1.59.0
      command: ["--redis.addr", "redis:6379", "--redis.password", "${REDIS_PASSWORD}"]
      ports: ["9121:9121"]
    nginx-exporter:
      image: nginx/nginx-prometheus-exporter:v1.1.0
      command: ["-nginx.scrape-uri", "http://nginx:80/stub_status"]
      ports: ["9113:9113"]
    ```
    Also add `stub_status on;` to the nginx config inside a `location /stub_status { }` block.

### 9.2 Alerting rules

- ☐ 🟠 `prometheus.yml` references `alerts.yml` via `rule_files`, but **no `alerts.yml` file exists**. Prometheus will emit a warning but still start. **Create `infrastructure/monitoring/prometheus/alerts.yml`** with the rules in `post-launch-monitoring.md` §3. Without this, no alerts will fire.

### 9.3 Alertmanager

- ☐ 🟠 `prometheus.yml` references `alertmanager:9093` but **no alertmanager service is deployed**. Alerts cannot be routed. **For Closed Beta options:**
  - **Option A:** remove the `alerting:` block from `prometheus.yml`. Alerts will be visible in the Prometheus UI only.
  - **Option B (recommended):** deploy Alertmanager and route critical alerts to Slack/PagerDuty. See `post-launch-monitoring.md` §4.

### 9.4 Grafana

- ☐ 🔴 Change the default Grafana admin password on first login (the prod compose defaults to `admin` if `GRAFANA_PASSWORD` is unset — make sure it is set in `.env.production`).
- ☐ 🔴 Verify the production dashboard is loaded: `https://app.masteryengine.com:3001/dashboards` → "Mastery Engine — Production Overview".
- ☐ 🟢 If the dashboard JSON does not auto-provision (the file is wrapped under a top-level `"dashboard"` key), import it manually via the Grafana UI: Dashboards → New → Import → upload `infrastructure/monitoring/grafana/dashboards/production-overview.json`.

### 9.5 Sentry

- ☐ 🟢 Verify `SENTRY_DSN` is set in `.env.production` and that events flow:
  ```bash
  curl -X POST https://app.masteryengine.com/api/v1/admin/_test-sentry  # if such an endpoint exists
  # Or trigger a test exception from the backend container:
  docker compose -f docker-compose.prod.yml exec backend python -c "import sentry_sdk; sentry_sdk.capture_message('Deployment test'); print('captured')"
  ```

---

## 10. Pre-Launch Smoke Test

Run this **immediately before** announcing the beta to users. Every checkbox must pass.

### 10.1 Infrastructure

- ☐ `docker compose ps` shows all containers `Up (healthy)`
- ☐ `curl https://app.masteryengine.com/api/v1/health` → 200, `status: healthy`
- ☐ `curl https://app.masteryengine.com/api/v1/health/ready` → 200, all checks `healthy`
- ☐ `docker compose exec postgres pg_isready -U mastery` → "accepting connections"
- ☐ `docker compose exec redis redis-cli -a $REDIS_PASSWORD ping` → PONG
- ☐ `docker compose logs backend --tail 50` → no ERROR/CRITICAL lines
- ☐ `docker compose logs worker --tail 50` → "Worker started" with no exceptions

### 10.2 Authentication

- ☐ Register a test user with a valid invite token → 201 Created
- ☐ Register with an invalid invite token → 403 BETA_REGISTRATION_DENIED
- ☐ Register with an expired invite → 403
- ☐ Register when user count == 20 → 403 BETA_FULL
- ☐ Login with correct credentials → 200, returns access + refresh tokens
- ☐ Login with wrong password → 401
- ☐ Refresh token rotation works (POST `/api/v1/auth/refresh`, old refresh becomes invalid)
- ☐ Logout invalidates the refresh token
- ☐ MFA setup (TOTP) works end-to-end
- ☐ Password reset email arrives and the reset link works

### 10.3 Core flows

- ☐ Learner dashboard loads (`/dashboard`) with no console errors
- ☐ Subject listing works (`/subjects`)
- ☐ Study session can be started (`/study/start`)
- ☐ At least one question of each type renders (multiple choice, code, etc.)
- ☐ Question submission produces a mastery update
- ☐ Mastery page shows updated scores
- ☐ WebSocket connection establishes and receives a real-time event
- ☐ Content authoring portal: create a template, save, publish
- ☐ Admin portal: dashboard loads, users list works

### 10.4 Closed Beta specifically

- ☐ `GET /api/v1/beta/status` returns `closed_beta_enabled: true`
- ☐ Beta banner is visible on the learner dashboard
- ☐ Floating feedback button is visible on all learner pages
- ☐ Submitting feedback returns 201 and the feedback appears in `GET /api/v1/beta/feedback`
- ☐ Welcome wizard runs on first login (4 steps, "Get Started" routes to `/dashboard`)
- ☐ Creating an invite generates a unique token
- ☐ Resending an invite generates a new token and extends TTL
- ☐ Deleting an unused invite returns 200; deleting a used invite returns 404

### 10.5 Notifications & Email

- ☐ Send a test email via SMTP (e.g. password reset) → email arrives within 60 seconds
- ☐ In-app notification appears in the bell icon
- ☐ Email delivery log entry exists in `infrastructure.email_delivery_log`

### 10.6 Background workers

- ☐ Outbox dispatcher is processing events (`SELECT count(*) FROM infrastructure.outbox_events WHERE consumed_at IS NULL` should trend to 0)
- ☐ Scheduler picks up due jobs (`SELECT * FROM infrastructure.scheduled_jobs WHERE next_run_at < now()`)
- ☐ No events in dead letter queue (`SELECT count(*) FROM infrastructure.dead_letter_events WHERE resolved_at IS NULL` should be 0)

### 10.7 Monitoring

- ☐ Prometheus UI loads at `http://localhost:9090`
- ☐ All scrape targets (minus the 3 missing exporters if you skipped them) show `UP`
- ☐ Grafana dashboard renders with live data
- ☐ Sentry test event appears in the Sentry dashboard

### 10.8 Security headers (final verification)

- ☐ `curl -sI https://app.masteryengine.com/` shows all of:
  - `strict-transport-security: max-age=31536000; includeSubDomains; preload`
  - `x-frame-options: DENY`
  - `x-content-type-options: nosniff`
  - `referrer-policy: strict-origin-when-cross-origin`
  - `permissions-policy: geolocation=(), microphone=(), camera=(), payment=(), usb=()`
  - `content-security-policy: default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`
- ☐ TLS grade A+ on SSL Labs (`https://www.ssllabs.com/ssltest/`)

---

## 11. Launch Day

- ☐ 🔴 All Section 10 smoke tests passed within the last hour.
- ☐ 🔴 Backup verified in the last 24 hours.
- ☐ 🔴 Restore drill completed within the last week.
- ☐ 🔴 20 invites created and emails dispatched.
- ☐ 🔴 On-call rotation confirmed (at least one engineer on-call for the first 72 hours).
- ☐ 🔴 Status page configured (or a simple Slack channel `#beta-status`).
- ☐ 🔴 Rollback plan documented (see `production-launch.md` §8).
- ☐ 🔴 Announce the beta to the first 5 users (canary cohort). Wait 4 hours. If no critical issues, send the remaining 15 invites.

---

## 12. Post-Launch (first 72 hours)

- ☐ Check Sentry for any new errors every 4 hours.
- ☐ Check Prometheus for any rule firings every 4 hours.
- ☐ Check `infrastructure.dead_letter_events` for accumulating events.
- ☐ Check `infrastructure.outbox_events` for backlog growth.
- ☐ Daily: review `analytics.beta_events` for engagement metrics (DAU, session duration, completion rate).
- ☐ Daily: review `identity.beta_feedback` and respond to bugs within 24 hours.
- ☐ After 72 hours with no SEV-1 incidents: declare Closed Beta stable.

---

## Appendix A: Gap Summary (tracked for post-launch)

| Gap | Severity | Action |
|---|---|---|
| `curl` missing in runtime images; compose healthchecks fail | 🟠 | Override healthchecks in compose (done in §4.3) |
| No Alembic migrations; schema via init SQL only | 🟠 | Generate initial Alembic migration post-launch |
| SSL certs not mounted for Postgres | 🟠 | Disable Postgres SSL OR mount certs (§3.2) |
| `alerts.yml` missing | 🟠 | Create per `post-launch-monitoring.md` §3 |
| Alertmanager not deployed | 🟠 | Deploy OR remove `alerting:` block (§9.3) |
| 3 Prometheus exporters missing | 🟠 | Add to compose OR remove scrape jobs (§9.1) |
| Backup script bugs (Redis path, flag handling) | 🟠 | Patch script or follow workarounds (§8.1) |
| Admin RBAC not enforced on beta endpoints | 🟠 | Patch `beta.py` to enforce role check (§7.1) |
| Email dispatch not wired in `create_invite` / `resend_invite` | 🟠 | Inject `EmailService` and call `send_template` (§7.2) |
| Welcome wizard doesn't persist data | 🟢 | Wire to `/api/v1/users/profile` post-launch |
| `pip install -e ".[dev]"` in prod image | 🟢 | Split Dockerfile into dev/prod targets |
| `npm install` instead of `npm ci` | 🟢 | Switch to `npm ci` |
| CSP may block Next.js inline scripts | 🟢 | Add `'unsafe-inline'` or nonce pipeline |
| `auth_audit_logs` not actually immutable | 🟢 | Revoke UPDATE/DELETE grants or add trigger |
| No retention for `beta_events`, `email_delivery_log`, `auth_audit_logs` | 🟢 | Add partitioning or cron purge |

---

**End of deployment checklist.** Next: read `production-launch.md` for the step-by-step launch procedure, and `beta-launch-guide.md` for the admin onboarding walkthrough.
