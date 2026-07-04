# Environment Variable Reference — Mastery Engine Closed Beta

> **Audience:** DevOps engineers, SREs, system administrators.
> **Scope:** Every environment variable read by the Mastery Engine platform in production.
> **Source of truth:** `backend/app/shared/config.py` (`Settings` class) + `docker-compose.prod.yml` + `.env.example` + `infrastructure/*` configs.
> **Last updated:** 2026-07-03

---

## How To Read This Document

Each variable is documented with the following fields:

- **Name** — the env var name (case-insensitive; Pydantic Settings normalises)
- **Required** — `🔴 YES` / `🟠 recommended` / `🟢 optional`
- **Default** — what the app uses if the var is unset
- **Type** — string / int / bool / list / enum / URL
- **Dev value** — value used by `docker-compose.yml` (development)
- **Production example** — a realistic, safe example value
- **Description** — what the variable controls
- **Security note** — secrets-handling guidance

Variables are grouped by subsystem. **Secrets** (must never be committed) are marked with 🔐.

---

## 1. Application Core

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 1.1 | `APP_ENV` | 🔴 YES | `development` | enum: `development`/`testing`/`staging`/`production` |
| 1.2 | `APP_NAME` | 🟢 | `mastery-engine` | string |
| 1.3 | `APP_PORT` | 🟢 | `8000` | int |
| 1.4 | `APP_LOG_LEVEL` | 🟢 | `INFO` | enum: `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` |
| 1.5 | `ENABLE_DOCS` | 🔴 YES | `true` | bool |

### 1.1 `APP_ENV`

- **Default**: `development`
- **Dev**: `development`
- **Prod**: `production`
- **Description**: Selects the runtime mode. Affects: log verbosity, error detail in responses, settings validation strictness.
- **Security**: In `production`, stack traces are not returned to clients. In `development`/`testing`, they are. **Never ship `APP_ENV=development` to production.**

### 1.2 `APP_NAME`

- **Default**: `mastery-engine`
- **Description**: Service identifier used in logs, Sentry tags, and the `/api/v1/health` response.

### 1.3 `APP_PORT`

- **Default**: `8000`
- **Description**: Port the uvicorn process listens on inside the container. Rarely needs changing — Nginx routes traffic via the docker network.

### 1.4 `APP_LOG_LEVEL`

- **Default**: `INFO`
- **Prod**: `INFO` (or `WARNING` for quieter logs)
- **Description**: Python logging level. `DEBUG` is appropriate only for troubleshooting — it emits SQL queries and PII (emails, user IDs) to logs.

### 1.5 `ENABLE_DOCS`

- **Default**: `true` ⚠️
- **Prod**: `false`
- **Description**: When `true`, FastAPI serves `/docs` (Swagger UI), `/redoc`, and `/openapi.json`. **Set to `false` in production** to avoid leaking the API surface to attackers.

---

## 2. Database (PostgreSQL)

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 2.1 | `DATABASE_URL` | 🔴 YES | `postgresql+asyncpg://mastery:changeme_in_production@localhost:5432/mastery_engine` | URL |
| 2.2 | `DATABASE_POOL_SIZE` | 🟢 | `10` | int |
| 2.3 | `DATABASE_MAX_OVERFLOW` | 🟢 | `20` | int |
| 2.4 | `DATABASE_ECHO` | 🟢 | `false` | bool |
| 2.5 | `DATABASE_USER` | 🟢 | `mastery` | string |
| 2.6 | `DATABASE_PASSWORD` | 🔴 YES | (none) | string 🔐 |
| 2.7 | `DATABASE_NAME` | 🟢 | `mastery_engine` | string |
| 2.8 | `POSTGRES_HOST` | 🟢 | `localhost` | string |
| 2.9 | `POSTGRES_PORT` | 🟢 | `5432` | int |
| 2.10 | `POSTGRES_DB` | 🟢 | `mastery_engine` | string |
| 2.11 | `POSTGRES_USER` | 🟢 | `mastery` | string |
| 2.12 | `POSTGRES_PASSWORD` | 🔴 YES | (none) | string 🔐 |

### 2.1 `DATABASE_URL` 🔐

- **Default**: ⚠️ `postgresql+asyncpg://mastery:changeme_in_production@localhost:5432/mastery_engine`
- **Dev**: `postgresql+asyncpg://mastery:changeme_in_production@postgres:5432/mastery_engine`
- **Prod example**: `postgresql+asyncpg://mastery:${DATABASE_PASSWORD}@postgres:5432/mastery_engine`
- **Description**: SQLAlchemy async connection URL. The driver MUST be `asyncpg` (not `psycopg2`) — the entire data layer is async.
- **Security**: This URL contains the password. In `.env.production`, prefer constructing it from `DATABASE_PASSWORD` rather than hardcoding. The default value ships with `changeme_in_production` — **always override**.
- **Note**: The `docker-compose.prod.yml` constructs this URL from `${DATABASE_PASSWORD:?Set DATABASE_PASSWORD}`. The `:?` syntax forces the variable to be present (compose will refuse to start otherwise).

### 2.2 `DATABASE_POOL_SIZE`

- **Default**: `10`
- **Description**: Persistent connections per async engine. With 1 backend container + 1 worker container = 20 total connections. Postgres is tuned for `max_connections=200`, so plenty of headroom. If scaling to N backend replicas, ensure `N * (pool_size + max_overflow) < 150` (leave 50 for admin/superuser).

### 2.3 `DATABASE_MAX_OVERFLOW`

- **Default**: `20`
- **Description**: Additional connections allowed beyond `pool_size` under load. Total ceiling per process = `pool_size + max_overflow = 30`.

### 2.4 `DATABASE_ECHO`

- **Default**: `false`
- **Prod**: `false`
- **Description**: When `true`, every SQL statement is logged. Useful for debugging, **never** enable in production — it logs query parameters including PII.

### 2.5–2.12 Postgres credentials

- The prod compose uses `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME` to initialise the postgres container (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` are the postgres image's canonical vars — they must match).
- **Password generation**: `openssl rand -base64 32`. Minimum 24 characters. **Rotate annually.**

---

## 3. Redis

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 3.1 | `REDIS_HOST` | 🟢 | `localhost` | string |
| 3.2 | `REDIS_PORT` | 🟢 | `6379` | int |
| 3.3 | `REDIS_PASSWORD` | 🟠 rec | (empty) | string 🔐 |
| 3.4 | `REDIS_DB` | 🟢 | `0` | int |

### 3.1–3.4 Redis connection

- **Dev**: `REDIS_HOST=redis`, `REDIS_PASSWORD=` (empty — dev Redis has no auth)
- **Prod**: `REDIS_HOST=redis`, `REDIS_PASSWORD=<32-char random>`
- **Description**: Redis is used for: cache (tag-based invalidation), rate limiting (sliding window), session storage (refresh token family tracking), job queue, pub/sub for WebSocket fan-out, distributed locks for scheduler.
- **Security**: **Always set `REDIS_PASSWORD` in production.** The prod compose passes it via `--requirepass ${REDIS_PASSWORD:-}` to the Redis server. If empty, Redis accepts unauthenticated connections — combined with `bind 0.0.0.0` (in `redis.conf`), this is a critical exposure.
- **Construction**: The `Settings` class exposes a `redis_url` property that builds `redis://[:password@]host:port/db`. The cache, queue, and session modules all use this.
- **Memory**: The prod compose sets `--maxmemory 512mb --maxmemory-policy allkeys-lru`. For 20 beta users this is more than enough (typical usage: 50–100 MB).

---

## 4. JWT & Authentication

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 4.1 | `JWT_ALGORITHM` | 🔴 YES | `RS256` | enum: `HS256`/`RS256` |
| 4.2 | `JWT_ISSUER` | 🟢 | `https://api.masteryengine.com` | string (URL) |
| 4.3 | `JWT_AUDIENCE` | 🟢 | `mastery-engine-api` | string |
| 4.4 | `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 🟢 | `15` | int |
| 4.5 | `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | 🟢 | `30` | int |
| 4.6 | `JWT_KEYS_DIR` | 🔴 YES (RS256) | `None` ⚠️ | path |
| 4.7 | `JWT_CLOCK_SKEW_SECONDS` | 🟢 | `30` | int |
| 4.8 | `JWT_SECRET_KEY` | 🟠 (HS256 only) | `changeme_in_production_use_a_long_random_string` | string 🔐 |

### 4.1 `JWT_ALGORITHM`

- **Default**: `RS256` (in `Settings`)
- **`.env.example` value**: ⚠️ `HS256` — **conflict**. The `.env.example` ships with `HS256`, but the prod compose and `Settings` default to `RS256`. **Always set `JWT_ALGORITHM=RS256` explicitly in `.env.production`.**
- **Description**: `RS256` = asymmetric RSA. Private key signs tokens; public key verifies. More secure than `HS256` (symmetric) because the verifying party (frontend, other services) cannot forge tokens.
- **Security**: RS256 is mandatory for production. HS256 is acceptable for testing only.

### 4.2–4.3 `JWT_ISSUER` / `JWT_AUDIENCE`

- **Default**: `https://api.masteryengine.com` / `mastery-engine-api`
- **Prod**: `https://app.masteryengine.com` (set to your actual domain)
- **Description**: The `iss` and `aud` claims in JWTs. The backend validates them on every authenticated request. If you change them post-launch, all existing tokens are invalidated.

### 4.4–4.5 Token TTLs

- **Access token**: 15 minutes (default). Short-lived; rotated via refresh token.
- **Refresh token**: 30 days. Allows users to stay logged in for a month without re-entering credentials.
- **Security**: The refresh token implements family-based rotation — if a stolen token is reused, the entire family is revoked (detected via `token_family_id` in `identity.refresh_tokens`).

### 4.6 `JWT_KEYS_DIR`

- **Default**: `None` ⚠️
- **Prod**: `/app/keys`
- **Description**: Directory containing `jwt-private.pem` and `jwt-public.pem`. **If `None` in RS256 mode, the backend generates an ephemeral in-memory keypair per process** — this means:
  - Tokens signed by process A cannot be verified by process B (multi-worker / multi-replica breaks).
  - All sessions are invalidated on every restart.
- **Security**: **Must be set in production.** Generate the keypair with:
  ```bash
  openssl genrsa -out keys/jwt-private.pem 4096
  openssl rsa -in keys/jwt-private.pem -pubout -out keys/jwt-public.pem
  chmod 600 keys/jwt-private.pem
  ```
- **Mount**: The prod compose mounts `./keys:/app/keys:ro` on the backend service.

### 4.7 `JWT_CLOCK_SKEW_SECONDS`

- **Default**: `30`
- **Description**: Tolerance for clock drift between issuer and verifier. 30s is standard. Lower if all servers use NTP (recommended).

### 4.8 `JWT_SECRET_KEY`

- **Default**: ⚠️ `changeme_in_production_use_a_long_random_string`
- **Description**: Only used when `JWT_ALGORITHM=HS256`. **Ignored in RS256 mode.**
- **Security**: If you accidentally deploy with `HS256`, this secret must be at least 256 bits. Generate with `openssl rand -base64 64`.

---

## 5. Argon2id Password Hashing

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 5.1 | `ARGON2_MEMORY_COST` | 🟢 | `19456` | int (KB) |
| 5.2 | `ARGON2_TIME_COST` | 🟢 | `2` | int (iterations) |
| 5.3 | `ARGON2_PARALLELISM` | 🟢 | `1` | int (lanes) |

### 5.1–5.3 Argon2id parameters

- **Defaults**: per OWASP 2024 recommendations (19 MB memory, 2 iterations, 1 lane).
- **Description**: Argon2id is the password hashing algorithm. These parameters control the trade-off between security and login latency.
- **Tuning**: With the defaults, a single login attempt takes ~100–200 ms. If login feels slow on your hardware, reduce `ARGON2_MEMORY_COST` to `12288` (12 MB). If you have spare CPU/RAM, raise `ARGON2_TIME_COST` to `3`.
- **Security**: Never set `ARGON2_MEMORY_COST` below `8192` (8 MB) — below that, GPU cracking becomes feasible.
- **Rehashing**: Existing hashes are not auto-upgraded when parameters change. New passwords and password changes use the new parameters.

---

## 6. Token TTLs (email verification, password reset, sessions)

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 6.1 | `EMAIL_VERIFICATION_TOKEN_TTL_HOURS` | 🟢 | `24` | int |
| 6.2 | `PASSWORD_RESET_TOKEN_TTL_MINUTES` | 🟢 | `15` | int |
| 6.3 | `SESSION_IDLE_TIMEOUT_MINUTES` | 🟢 | `60` | int |
| 6.4 | `SESSION_ABSOLUTE_TIMEOUT_DAYS` | 🟢 | `30` | int |

### 6.1 Email verification

- **Default**: 24 hours. Verification emails expire after 1 day. Users who don't verify within 24 h must request a new link.

### 6.2 Password reset

- **Default**: 15 minutes. Short window to limit the attack surface of leaked reset links. Users must complete the reset flow within 15 minutes of requesting it.

### 6.3–6.4 Session timeouts

- **Idle**: 60 minutes. If a user is inactive for 1 hour, their access token expires (but the refresh token still works).
- **Absolute**: 30 days. After 30 days from session creation, the user must re-authenticate regardless of activity.

---

## 7. CORS & Frontend

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 7.1 | `CORS_ORIGINS` | 🔴 YES | `http://localhost:3000,http://localhost:8000` | list (comma or JSON) |
| 7.2 | `NEXT_PUBLIC_API_URL` | 🔴 YES | `http://localhost:8000` | URL |
| 7.3 | `NEXT_PUBLIC_APP_NAME` | 🟢 | `Mastery Engine` | string |

### 7.1 `CORS_ORIGINS`

- **Dev**: `http://localhost:3000,http://localhost:8000`
- **Prod**: `https://app.masteryengine.com`
- **Description**: Comma-separated (or JSON-encoded) list of allowed origins for cross-origin requests. The backend sets `Access-Control-Allow-Origin` to the matching origin and `Access-Control-Allow-Credentials: true`.
- **Security**: In production, list exactly one origin (your frontend URL). Do not use `*` — it's incompatible with `allow_credentials=True` and would silently break auth.
- **Format**: Both `https://a.com,https://b.com` and `["https://a.com","https://b.com"]` are accepted by the Settings parser.

### 7.2 `NEXT_PUBLIC_API_URL`

- **Dev**: `http://localhost:8000`
- **Prod**: `https://app.masteryengine.com` (same as frontend — Nginx routes `/api/*` to the backend)
- **Description**: The backend API base URL exposed to the browser. In production, this should be the **same origin** as the frontend (Nginx proxies `/api/*`). This avoids CORS complexity entirely.
- **Note**: Must be set at **build time** (it's inlined into the JS bundle). Changing it requires a frontend rebuild.

### 7.3 `NEXT_PUBLIC_APP_NAME`

- **Default**: `Mastery Engine`
- **Description**: Display name shown in the UI header, emails, and browser tab title.

---

## 8. SMTP / Email

> ⚠️ **No SMTP settings exist in the `Settings` class.** The `ProductionSmtpClient` in `backend/app/infrastructure/email/service.py` uses hardcoded `localhost:587`. **This is a deployment blocker** — the email service will not work out of the box. The recommended remediation is to extend the `Settings` class with the variables below and update `ProductionSmtpClient` to read from settings.

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 8.1 | `SMTP_HOST` | 🔴 YES | (not in Settings) | string |
| 8.2 | `SMTP_PORT` | 🔴 YES | `587` | int |
| 8.3 | `SMTP_USERNAME` | 🔴 YES | (not in Settings) | string 🔐 |
| 8.4 | `SMTP_PASSWORD` | 🔴 YES | (not in Settings) | string 🔐 |
| 8.5 | `SMTP_USE_TLS` | 🟢 | `true` | bool |
| 8.6 | `SMTP_FROM_EMAIL` | 🔴 YES | (not in Settings) | string (email) |
| 8.7 | `SMTP_FROM_NAME` | 🟢 | `Mastery Engine` | string |

### 8.1–8.7 SMTP configuration

- **Recommended providers for Closed Beta**:
  - **Postmark** — dedicated transactional email, generous free tier (100 emails/month free)
  - **AWS SES** — cheap ($0.10 per 1000 emails), requires production access request
  - **Resend** — modern developer-focused, 3000 emails/month free
- **Workaround for the missing Settings**: set these vars in `.env.production` anyway. They will be picked up if you patch `ProductionSmtpClient` to read from `os.environ` (a 5-line change). Until then, the email service cannot send real email and the welcome / password-reset / beta-invitation flows are broken.
- **Test**: After configuring, trigger a password reset email and verify arrival within 60 seconds. Check the `infrastructure.email_delivery_log` table for the delivery record.

---

## 9. AI Providers (Optional — Closed Beta)

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 9.1 | `AI_ENABLED` | 🟢 | `false` | bool |
| 9.2 | `OLLAMA_HOST` | 🟢 | `http://ollama:11434` | URL |
| 9.3 | `OLLAMA_MODEL` | 🟢 | `qwen2.5:7b` | string |
| 9.4 | `OPENAI_API_KEY` | 🟢 | (none) | string 🔐 |
| 9.5 | `GEMINI_API_KEY` | 🟢 | (none) | string 🔐 |
| 9.6 | `ANTHROPIC_API_KEY` | 🟢 | (none) | string 🔐 |

### 9.1 `AI_ENABLED`

- **Default**: `false` (also enforced by `BETA_FLAG_AI_ENABLED=false`)
- **Description**: Master switch for the AI router. When `false`, all `/api/v1/ai/*` endpoints return 503 Service Unavailable.
- **For Closed Beta**: leave disabled unless you've validated the AI cost & quality with a small cohort.

### 9.2–9.3 Ollama (default provider)

- **Description**: Self-hosted Ollama running a Qwen model. Cheapest option (no per-token cost) but requires GPU for acceptable latency.
- **Hardware**: CPU-only Ollama with `qwen2.5:7b` gives ~5–15 tokens/sec — acceptable for non-realtime use (explanations, feedback). For chat-like UX, use a GPU.
- **Setup**: `ollama serve` on a separate host, then set `OLLAMA_HOST=http://<ollama-host>:11434`.

### 9.4–9.6 Cloud AI providers

- **Description**: OpenAI, Gemini, Anthropic API keys. The AI router tries them in order of cost (cheapest first) unless overridden per request.
- **Cost control**: Set per-provider monthly spend limits in your provider dashboard. For Closed Beta with 20 users, $20–50/month should be plenty.
- **Security**: Rotate keys every 90 days. Use restricted keys (project-scoped) where possible.

---

## 10. Closed Beta Configuration

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 10.1 | `CLOSED_BETA_ENABLED` | 🔴 YES | `false` | bool |
| 10.2 | `MAX_BETA_USERS` | 🟢 | `20` | int |
| 10.3 | `BETA_INVITE_TOKEN_TTL_HOURS` | 🟢 | `168` (7 days) | int |
| 10.4 | `BETA_FLAG_LEARNING_ENABLED` | 🟢 | `true` | bool |
| 10.5 | `BETA_FLAG_CONTENT_AUTHORING_ENABLED` | 🟢 | `true` | bool |
| 10.6 | `BETA_FLAG_AI_ENABLED` | 🟢 | `false` | bool |
| 10.7 | `BETA_FLAG_NOTIFICATIONS_ENABLED` | 🟢 | `true` | bool |
| 10.8 | `BETA_FLAG_ANALYTICS_ENABLED` | 🟢 | `true` | bool |
| 10.9 | `BETA_FLAG_ADMIN_CONSOLE_ENABLED` | 🟢 | `true` | bool |

### 10.1 `CLOSED_BETA_ENABLED`

- **Default**: `false`
- **Prod (beta)**: `true`
- **Description**: Master switch. When `true`, the registration endpoint requires a valid `invite_token` in the request body, and the total registered user count cannot exceed `MAX_BETA_USERS`.
- **Transitioning out of beta**: set back to `false` and restart backend + worker. No migration needed (beta tables are additive).

### 10.2 `MAX_BETA_USERS`

- **Default**: `20`
- **Description**: Hard cap on the number of registered users. Once reached, additional registration attempts return `403 BETA_FULL`.
- **Tuning**: For the closed beta, keep at 20. To expand, raise to 30/50/100 in stages. Each increase should be accompanied by a capacity review (DB, Redis, workers).

### 10.3 `BETA_INVITE_TOKEN_TTL_HOURS`

- **Default**: `168` (7 days)
- **Description**: How long an invite token remains valid. After expiry, the invite must be resent (generates a new token).
- **Tuning**: 7 days is a good balance. Shorter (24–72h) for high-security cohorts; longer (14–30 days) for low-urgency invites.

### 10.4–10.9 Feature flags

- **Description**: Six independent toggles controlling which subsystems are visible/active. The frontend polls `GET /api/v1/beta/status` at runtime to read these.
- **Hot reload**: NOT supported. Changing a flag requires restarting **both** `backend` and `worker` containers (the `Settings` object is `@lru_cache`'d per process).
- **Recommendation for Closed Beta launch**: all flags `true` except `BETA_FLAG_AI_ENABLED` (leave `false` until the AI cost/quality is validated separately).

---

## 11. Observability

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 11.1 | `SENTRY_DSN` | 🟠 rec | (none) | URL 🔐 |
| 11.2 | `PROMETHEUS_PORT` | 🟢 | `9090` | int |
| 11.3 | `GRAFANA_PORT` | 🟢 | `3001` | int |
| 11.4 | `GRAFANA_PASSWORD` | 🔴 YES | ⚠️ `admin` | string 🔐 |

### 11.1 `SENTRY_DSN`

- **Default**: none
- **Prod**: `https://<key>@o<org>.ingest.sentry.io/<project>`
- **Description**: Sentry project DSN. When set, unhandled exceptions and 5xx responses are reported to Sentry with full stack trace, request context, and user info.
- **Security**: The DSN contains a public key (safe to expose in the browser) but should still be kept in `.env.production` not committed.

### 11.4 `GRAFANA_PASSWORD`

- **Default**: ⚠️ `admin` (in `docker-compose.prod.yml`: `${GRAFANA_PASSWORD:-admin}`)
- **Prod**: 24+ char random (`openssl rand -base64 24`)
- **Description**: Admin password for the Grafana UI. **Always override.** Grafana is exposed on port 3001 — if this port is publicly reachable, a weak password is a critical exposure.
- **Security**: Restrict port 3001 to a VPN or private IP via UFW. Change the password on first login even if you set it via env.

---

## 12. Nginx / Reverse Proxy

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 12.1 | `NGINX_PORT` | 🟢 | `80` | int |
| 12.2 | `NGINX_SSL_PORT` | 🟢 | `443` | int |

### 12.1–12.2 Nginx ports

- **Description**: HTTP and HTTPS ports Nginx listens on. Rarely need changing.
- **Note**: Nginx config (`infrastructure/nginx/nginx.conf`) hardcodes `listen 80` and `listen 443 ssl http2`. Changing these env vars alone will **not** change the actual listening ports — edit `nginx.conf` directly.

---

## 13. Backup & Recovery

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 13.1 | `BACKUP_DIR` | 🟢 | `/opt/mastery-engine/backups` | path |
| 13.2 | `RETENTION_DAYS` | 🟢 | `30` | int |
| 13.3 | `BACKUP_ENCRYPTION_KEY` | 🔴 YES | (none) | string 🔐 |
| 13.4 | `S3_BACKUP_BUCKET` | 🟠 rec | (none) | string |
| 13.5 | `SLACK_WEBHOOK` | 🟢 | (none) | URL 🔐 |

### 13.1 `BACKUP_DIR`

- **Description**: Local directory where backups are stored before (optional) S3 upload. Must exist and be writable by the user running `backup.sh`.

### 13.2 `RETENTION_DAYS`

- **Default**: `30`
- **Description**: Backups older than this are deleted by the cleanup step. For Closed Beta, 30 days is sufficient. For production, 90 days with monthly offsite archives is recommended.

### 13.3 `BACKUP_ENCRYPTION_KEY` 🔐

- **Description**: Passphrase for `openssl enc -aes-256-cbc -salt -pbkdf2`. When set, backups are encrypted at rest.
- **Security**: **Always set in production.** Without it, the `.env.production` file (containing all secrets) is included in plaintext in the backup tarball.
- **Generation**: `openssl rand -base64 32`
- **Storage**: Store in your secrets manager (NOT in the same backup). If lost, all historical backups are unrecoverable.

### 13.4 `S3_BACKUP_BUCKET`

- **Description**: S3 bucket name for offsite backup storage. Backups are uploaded with `--storage-class STANDARD_IA` (infrequent access, cheaper).
- **Prerequisite**: `aws` CLI configured with credentials that have `s3:PutObject` on the bucket.
- **Alternative**: any S3-compatible storage (MinIO, Backblaze B2, Wasabi).

### 13.5 `SLACK_WEBHOOK`

- **Description**: Slack incoming webhook URL for backup success/failure notifications. When set, the backup script posts a summary to the channel.
- **Security**: Webhook URLs are bearer tokens — keep secret.

---

## 14. Container Orchestration (Compose-specific)

These are not read by the application but by `docker-compose.prod.yml` itself. They must be set in the shell environment (or `.env.production` loaded via `--env-file`).

| # | Name | Required | Default | Type |
|---|---|---|---|---|
| 14.1 | `DATABASE_PASSWORD` | 🔴 YES | (compose refuses to start) | string 🔐 |
| 14.2 | `JWT_SECRET_KEY` | 🔴 YES | (compose refuses to start) | string 🔐 |
| 14.3 | `API_URL` | 🟢 | `https://api.masteryengine.com` | URL |
| 14.4 | `GRAFANA_PASSWORD` | 🔴 YES | ⚠️ `admin` | string 🔐 |
| 14.5 | `COMPOSE_PROJECT_NAME` | 🟢 | (directory name) | string |

### 14.1–14.2 Required-by-compose

- The prod compose uses `${DATABASE_PASSWORD:?Set DATABASE_PASSWORD}` and `${JWT_SECRET_KEY:?...}` — the `:?` syntax means compose will **refuse to start** if these are unset. This is a deliberate guard against deploying with placeholder secrets.
- **Note**: `JWT_SECRET_KEY` is required by compose but is only used by the app if `JWT_ALGORITHM=HS256`. In RS256 mode it's unused but compose still demands it — set it to any non-empty string.

### 14.3 `API_URL`

- **Default**: `https://api.masteryengine.com`
- **Description**: Build arg for the frontend Docker image (`NEXT_PUBLIC_API_URL`). Determines the API URL baked into the JS bundle. **Must be set correctly before the first frontend build** — changing it requires a rebuild.

---

## 15. Complete `.env.production` Template

> Copy this into `.env.production`, fill in the placeholders, and never commit it.

```bash
# ============================================
# Mastery Engine — Production Environment
# Closed Beta configuration
# ============================================

# --- 1. Application Core ---
APP_ENV=production
APP_NAME=mastery-engine
APP_PORT=8000
APP_LOG_LEVEL=INFO
ENABLE_DOCS=false

# --- 2. Database ---
DATABASE_USER=mastery
DATABASE_PASSWORD=<openssl rand -base64 32>
DATABASE_NAME=mastery_engine
DATABASE_URL=postgresql+asyncpg://mastery:DATABASE_PASSWORD@postgres:5432/mastery_engine
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_ECHO=false
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=mastery_engine
POSTGRES_USER=mastery
POSTGRES_PASSWORD=<same as DATABASE_PASSWORD>

# --- 3. Redis ---
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<openssl rand -base64 32>
REDIS_DB=0

# --- 4. JWT (RS256) ---
JWT_ALGORITHM=RS256
JWT_ISSUER=https://app.masteryengine.com
JWT_AUDIENCE=mastery-engine-api
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
JWT_KEYS_DIR=/app/keys
JWT_CLOCK_SKEW_SECONDS=30
# Required by compose's :? guard; unused in RS256 mode:
JWT_SECRET_KEY=<openssl rand -base64 32>

# --- 5. Argon2id (OWASP 2024 defaults) ---
ARGON2_MEMORY_COST=19456
ARGON2_TIME_COST=2
ARGON2_PARALLELISM=1

# --- 6. Token TTLs ---
EMAIL_VERIFICATION_TOKEN_TTL_HOURS=24
PASSWORD_RESET_TOKEN_TTL_MINUTES=15
SESSION_IDLE_TIMEOUT_MINUTES=60
SESSION_ABSOLUTE_TIMEOUT_DAYS=30

# --- 7. CORS & Frontend ---
CORS_ORIGINS=https://app.masteryengine.com
NEXT_PUBLIC_API_URL=https://app.masteryengine.com
NEXT_PUBLIC_APP_NAME=Mastery Engine

# --- 8. SMTP ---
SMTP_HOST=smtp.postmarkapp.com
SMTP_PORT=587
SMTP_USERNAME=<postmark-server-token>
SMTP_PASSWORD=<postmark-server-token>
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@masteryengine.com
SMTP_FROM_NAME=Mastery Engine

# --- 9. AI (disabled for beta) ---
AI_ENABLED=false
# OLLAMA_HOST=http://ollama:11434
# OLLAMA_MODEL=qwen2.5:7b
# OPENAI_API_KEY=
# GEMINI_API_KEY=
# ANTHROPIC_API_KEY=

# --- 10. Closed Beta ---
CLOSED_BETA_ENABLED=true
MAX_BETA_USERS=20
BETA_INVITE_TOKEN_TTL_HOURS=168
BETA_FLAG_LEARNING_ENABLED=true
BETA_FLAG_CONTENT_AUTHORING_ENABLED=true
BETA_FLAG_AI_ENABLED=false
BETA_FLAG_NOTIFICATIONS_ENABLED=true
BETA_FLAG_ANALYTICS_ENABLED=true
BETA_FLAG_ADMIN_CONSOLE_ENABLED=true

# --- 11. Observability ---
SENTRY_DSN=https://<key>@o<org>.ingest.sentry.io/<project>
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
GRAFANA_PASSWORD=<openssl rand -base64 24>

# --- 12. Nginx ---
NGINX_PORT=80
NGINX_SSL_PORT=443

# --- 13. Backup & Recovery ---
BACKUP_DIR=/opt/mastery-engine/backups
RETENTION_DAYS=30
BACKUP_ENCRYPTION_KEY=<openssl rand -base64 32>
S3_BACKUP_BUCKET=mastery-engine-backups
SLACK_WEBHOOK=https://hooks.slack.com/services/...

# --- 14. Compose build args ---
API_URL=https://app.masteryengine.com
COMPOSE_PROJECT_NAME=masteryengine
```

---

## Appendix A: Secrets Generation Cheat Sheet

```bash
# Database password (32 chars)
openssl rand -base64 32

# Redis password (32 chars)
openssl rand -base64 32

# JWT secret (unused in RS256 but required by compose)
openssl rand -base64 32

# Backup encryption key (32 chars)
openssl rand -base64 32

# Grafana admin password (24 chars)
openssl rand -base64 24

# RS256 JWT keypair (4096-bit RSA)
openssl genrsa -out keys/jwt-private.pem 4096
openssl rsa -in keys/jwt-private.pem -pubout -out keys/jwt-public.pem
chmod 600 keys/jwt-private.pem

# Postgres self-signed cert (only if enabling Postgres SSL)
openssl req -new -x509 -days 3650 -nodes \
  -out infrastructure/postgres/ssl/postgres.pem \
  -keyout infrastructure/postgres/ssl/postgres-key.pem \
  -subj "/CN=postgres"
chmod 600 infrastructure/postgres/ssl/postgres-key.pem

# Beta invite token (manual, if scripting invite creation)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Appendix B: Variables Not In `Settings` (Gaps)

These variables are referenced in code or docs but are **NOT** in the `Settings` class. The application does not read them — they're either TODO items, compose-only, or hardcoded.

| Variable | Where referenced | Status | Action |
|---|---|---|---|
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME` | `email/service.py` (hardcoded `localhost:587`) | 🔴 Gap | Add to `Settings`, patch `ProductionSmtpClient` |
| `OLLAMA_HOST`, `OLLAMA_MODEL` | `docker-compose.prod.yml` | 🟠 Compose-only | App reads from `AIConfig` singleton (in-memory), not env. Patch AI config to read env on startup. |
| `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` | docs only | 🟠 Gap | Add to `Settings`, wire into AI router |
| `AI_ENABLED` | `docker-compose.prod.yml` | 🟠 Compose-only | App uses `BETA_FLAG_AI_ENABLED` instead |
| `OLLAMA_URL` | (mentioned in user task spec) | 🟢 Not implemented | Use `OLLAMA_HOST` instead |

## Appendix C: Development Defaults (Never Use In Production)

These values ship in `.env.example` and `docker-compose.yml` for developer convenience. **They must all be overridden in production.**

| Variable | Dev default | Risk if used in prod |
|---|---|---|
| `DATABASE_URL` | `...changeme_in_production@...` | Public password; DB pwned |
| `JWT_SECRET_KEY` | `changeme_in_production_use_a_long_random_string` | Token forgery |
| `JWT_ALGORITHM` | `HS256` (in `.env.example`) | Downgrade from RS256; symmetric key compromise = full auth bypass |
| `REDIS_PASSWORD` | (empty) | Unauthenticated Redis; data exfiltration |
| `GRAFANA_PASSWORD` | `admin` | Grafana pwned |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | Broken auth in prod (no HTTPS origin) |
| `ENABLE_DOCS` | `true` | API surface leak |
| `APP_ENV` | `development` | Stack traces exposed to clients |

---

**End of environment reference.** Next: read `production-launch.md` for the step-by-step launch procedure using these variables.
