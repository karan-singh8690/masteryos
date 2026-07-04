# Deployment Diagrams — Mastery Engine Closed Beta

> **Audience:** All engineers and stakeholders needing a visual reference of the platform architecture.
> **Scope:** Architecture, data flow, deployment topology, request flow, security boundaries, failure modes.
> **Last updated:** 2026-07-03

---

## 1. High-Level Architecture (ASCII)

```
                              ┌─────────────────────────────────────────┐
                              │              INTERNET                    │
                              │  (20 invited beta users + 1-2 admins)   │
                              └────────────────┬────────────────────────┘
                                               │
                                               │ HTTPS (443)
                                               ▼
                              ┌─────────────────────────────────────────┐
                              │            NGINX (reverse proxy)         │
                              │  • TLS termination (Let's Encrypt)       │
                              │  • HSTS, CSP, X-Frame-Options, etc.      │
                              │  • Rate limiting (api: 60/min, auth:10)  │
                              │  • Gzip, HTTP/2, keepalive               │
                              │  • Routes:                                │
                              │    /api/*     → backend:8000              │
                              │    /ws        → backend:8000 (upgrade)   │
                              │    /          → frontend:3000            │
                              │    /metrics   → internal only            │
                              └──────┬───────────────────┬──────────────┘
                                     │                   │
                          /api/*, /ws│                   │ /
                                     ▼                   ▼
                ┌────────────────────────────┐  ┌─────────────────────┐
                │   BACKEND (FastAPI +       │  │  FRONTEND (Next.js  │
                │   uvicorn, Python 3.13)    │  │  15 + React 19)     │
                │   • Auth (Argon2id/RS256/  │  │  • Learner portal   │
                │     MFA/RBAC)              │  │  • Content author   │
                │   • REST API (/api/v1/*)   │  │  • Admin portal     │
                │   • WebSocket server (/ws) │  │  • Beta banner      │
                │   • Outbox dispatcher      │  │  • Feedback button  │
                │   • Prometheus /metrics    │  │  • Welcome wizard   │
                │   • Health endpoints       │  │  • Offline support  │
                └──┬───────┬────────────┬────┘  └─────────────────────┘
                   │       │            │
            SQL    │       │ Redis      │ HTTP (Ollama/OpenAI)
                   │       │            │
                   ▼       ▼            ▼
        ┌──────────────┐ ┌──────────┐ ┌─────────────────────┐
        │  POSTGRESQL  │ │  REDIS   │ │  AI PROVIDER (opt)  │
        │  16-alpine   │ │  7-alpine│ │  • Ollama (default) │
        │              │ │          │ │  • OpenAI           │
        │  10 schemas: │ │  • Cache │ │  • Gemini           │
        │  identity    │ │  • Rate  │ │  • Anthropic        │
        │  content     │ │    limit │ │                     │
        │  learning    │ │  • Sess. │ │  (Disabled by       │
        │  assessment  │ │  • Queue │ │   default for beta) │
        │  mastery     │ │  • Pub/  │ │                     │
        │  scheduling  │ │    Sub   │ │                     │
        │  analytics   │ │  • Locks │ │                     │
        │  billing     │ │          │ │                     │
        │  admin       │ │  512 MB  │ │                     │
        │  infra       │ │  maxmem  │ │                     │
        │              │ │  LRU     │ │                     │
        │  57 tables   │ │          │ │                     │
        └──────────────┘ └──────────┘ └─────────────────────┘

                ┌────────────────────────────┐
                │   WORKER (separate proc)   │
                │   • Outbox dispatcher      │
                │   • Scheduler processor    │
                │   • Notification processor │
                │   • Email sender           │
                │   • Retry engine           │
                │   • Dead letter handler    │
                └─────────┬──────────────────┘
                          │
                          ▼
                  (same Postgres + Redis)


                ┌──────────────────────────────────────────┐
                │       OBSERVABILITY STACK                │
                │                                          │
                │  ┌──────────────┐    ┌────────────────┐  │
                │  │ PROMETHEUS   │───▶│   GRAFANA      │  │
                │  │ (15s scrape) │    │   (dashboards) │  │
                │  └──────┬───────┘    └────────────────┘  │
                │         │                                │
                │         │ scrapes                        │
                │         ▼                                │
                │  backend:8000/metrics                    │
                │  backend:8000/api/v1/admin/bg/workers/   │
                │       metrics                            │
                │  frontend:3000/api/v1/health             │
                │                                          │
                │  ┌──────────────────────────────────────┐│
                │  │ SENTRY (SaaS, external)              ││
                │  │ • Error tracking                     ││
                │  │ • Performance monitoring             ││
                │  └──────────────────────────────────────┘│
                └──────────────────────────────────────────┘


                ┌──────────────────────────────────────────┐
                │       EXTERNAL SERVICES                  │
                │                                          │
                │  ┌──────────────┐  ┌──────────────────┐  │
                │  │ SMTP (e.g.   │  │ S3 (backups)     │  │
                │  │ Postmark,    │  │ STANDARD_IA      │  │
                │  │ SES, Resend) │  │                  │  │
                │  └──────────────┘  └──────────────────┘  │
                └──────────────────────────────────────────┘
```

---

## 2. Docker Compose Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│  HOST: /opt/mastery-engine/                                         │
│  Network: masteryengine_default (bridge, auto-created)              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  CONTAINER: nginx  (image: nginx:1.25-alpine)               │   │
│  │  Ports: 80→80, 443→443 (published)                          │   │
│  │  Volumes:                                                    │   │
│  │    • ./infrastructure/nginx/nginx.conf:/etc/nginx/nginx.conf │   │
│  │    • ./infrastructure/nginx/ssl:/etc/nginx/ssl:ro            │   │
│  │    • nginx_logs:/var/log/nginx                               │   │
│  │  Health: wget --spider http://localhost/health               │   │
│  │  Restart: always                                             │   │
│  │  Limits: 256M, 0.5 CPU                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              │                                      │
│  ┌──────────────────┐  ┌─────┴──────────┐  ┌──────────────────┐  │
│  │  CONTAINER:      │  │  CONTAINER:    │  │  CONTAINER:      │  │
│  │  backend         │  │  frontend      │  │  worker          │  │
│  │  (FastAPI)       │  │  (Next.js)     │  │  (background)    │  │
│  │                  │  │                │  │                  │  │
│  │  Port: 8000      │  │  Port: 3000    │  │  (no port)       │  │
│  │  (internal only) │  │  (internal)    │  │                  │  │
│  │                  │  │                │  │                  │  │
│  │  Volumes:        │  │  Volumes:      │  │  Volumes:        │  │
│  │   • ./keys:ro    │  │   (none)       │  │   • ./keys:ro    │  │
│  │   • backend_logs │  │                │  │   • worker_logs  │  │
│  │                  │  │                │  │                  │  │
│  │  Health:         │  │  Health:       │  │  Health:         │  │
│  │  python urllib   │  │  node http     │  │  python urllib   │  │
│  │  → /health/ready │  │  → /health     │  │  → /admin/bg/    │  │
│  │                  │  │                │  │    workers       │  │
│  │  Limits:         │  │  Limits:       │  │  Limits:         │  │
│  │   1G, 2 CPU      │  │   512M, 1 CPU  │  │   512M, 1 CPU    │  │
│  │                  │  │                │  │                  │  │
│  │  Replicas: 2     │  │  Replicas: 1   │  │  Replicas: 2     │  │
│  │  (Swarm-only)    │  │                │  │  (Swarm-only)    │  │
│  └────────┬─────────┘  └────────────────┘  └────────┬─────────┘  │
│           │                                         │            │
│           │           ┌──────────────┐              │            │
│           └──────────▶│  postgres    │◀─────────────┘            │
│                       │  16-alpine   │                            │
│                       │              │                            │
│                       │  Port: 5432  │                            │
│                       │  (internal)  │                            │
│                       │              │                            │
│                       │  Volume:     │                            │
│                       │   postgres_  │                            │
│                       │   data       │                            │
│                       │              │                            │
│                       │  Init:       │                            │
│                       │   01-schemas │                            │
│                       │   02-auth    │                            │
│                       │   03-bg      │                            │
│                       │   04-beta    │                            │
│                       │              │                            │
│                       │  Config:     │                            │
│                       │   postgresql │                            │
│                       │   .conf      │                            │
│                       │              │                            │
│                       │  Limits:     │                            │
│                       │   2G, 2 CPU  │                            │
│                       └──────┬───────┘                            │
│                              │                                    │
│           ┌──────────────────┴──────────────────┐                 │
│           │                                     │                 │
│           ▼                                     ▼                 │
│  ┌──────────────────┐                  ┌──────────────────┐      │
│  │  redis           │                  │  prometheus      │      │
│  │  7-alpine        │                  │                  │      │
│  │                  │                  │  Port: 9090      │      │
│  │  Port: 6379      │                  │  (internal)      │      │
│  │  (internal)      │                  │                  │      │
│  │                  │                  │  Volume:         │      │
│  │  Volume:         │                  │   prometheus_    │      │
│  │   redis_data     │                  │   data           │      │
│  │                  │                  │                  │      │
│  │  Config:         │                  │  Config:         │      │
│  │   redis.conf     │                  │   prometheus.yml │      │
│  │   (overridden    │                  │                  │      │
│  │    by command)   │                  │  Retention:      │      │
│  │                  │                  │   30d            │      │
│  │  Limits:         │                  │                  │      │
│  │   768M, 1 CPU    │                  │  Limits:         │      │
│  │   512M maxmem    │                  │   512M           │      │
│  └──────────────────┘                  └──────────────────┘      │
│                                                    │              │
│                                                    │              │
│                                       ┌────────────────────┐     │
│                                       │  grafana           │     │
│                                       │  (dashboards UI)   │     │
│                                       │                    │     │
│                                       │  Port: 3001        │     │
│                                       │  (published)       │     │
│                                       │                    │     │
│                                       │  Volume:           │     │
│                                       │   grafana_data     │     │
│                                       │                    │     │
│                                       │  Provisioning:     │     │
│                                       │   datasources/     │     │
│                                       │   dashboards/      │     │
│                                       │                    │     │
│                                       │  Limits:           │     │
│                                       │   256M             │     │
│                                       └────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘

Volumes (named, persistent):
  • postgres_data  → /var/lib/postgresql/data
  • redis_data     → /data
  • backend_logs   → /app/logs
  • worker_logs    → /app/logs
  • nginx_logs     → /var/log/nginx
  • prometheus_data → /prometheus
  • grafana_data   → /var/lib/grafana

Host mounts (config & secrets):
  • ./keys                            → /app/keys:ro (backend, worker)
  • ./infrastructure/nginx/nginx.conf → /etc/nginx/nginx.conf:ro (nginx)
  • ./infrastructure/nginx/ssl        → /etc/nginx/ssl:ro (nginx)
  • ./infrastructure/postgres/init    → /docker-entrypoint-initdb.d (postgres)
  • ./infrastructure/postgres/postgresql.conf → /etc/postgresql/postgresql.conf
  • ./infrastructure/redis/redis.conf → /usr/local/etc/redis/redis.conf (mounted but unused)
  • ./infrastructure/monitoring/prometheus/prometheus.yml → /etc/prometheus/prometheus.yml:ro
  • ./infrastructure/monitoring/grafana/provisioning → /etc/grafana/provisioning:ro
```

---

## 3. Request Flow — User Logs In & Starts a Study Session

```
USER BROWSER                          NGINX                         BACKEND
─────────────                         ─────                         ───────
                   1. POST /api/v1/auth/login
                   (email, password)
                  ─────────────────▶  ─────────────────────────▶
                                                              2. Validate email format
                                                              3. Lookup user by email
                                                              4. Verify password (Argon2id, ~100ms)
                                                              5. Check MFA required?
                                                              6. Generate access token (RS256, 15min)
                                                              7. Generate refresh token (family rotation)
                                                              8. Store tokens in DB
                                                              9. Audit log: LOGIN_SUCCESS
                                                            ◀─────────────────────────
                  10. 200 OK {access_token, refresh_token, user}
                  ◀──────────────────  ◀─────────────────────────
                  
                   11. Set cookies:
                       mastery-authenticated=true
                       mastery-role=user
                       mastery-token=<access_token>
                  
                   12. GET /dashboard (with cookies)
                  ─────────────────▶  ─────────────────────────▶
                                                              (frontend SSR, returns HTML)
                                                            ◀─────────────────────────
                  13. 200 OK (HTML)
                  ◀──────────────────
                  
                   14. JS loads, calls:
                       GET /api/v1/learning/dashboard
                       Authorization: Bearer <token>
                  ─────────────────▶  ─────────────────────────▶
                                                              15. Verify JWT (RS256 pub key)
                                                              16. Check session valid
                                                              17. Fetch dashboard data:
                                                                  - active sessions
                                                                  - mastery summary
                                                                  - recommendations
                                                                  - streak
                                                              18. Cache result in Redis (5min TTL)
                                                            ◀─────────────────────────
                  19. 200 OK (JSON)
                  ◀──────────────────
                  
                   20. User clicks "Start Session"
                       POST /api/v1/learning/sessions
                  ─────────────────▶  ─────────────────────────▶
                                                              21. Create study_session aggregate
                                                              22. Pick questions via recommender
                                                              23. Persist to learning.study_sessions
                                                              24. Publish event: SessionStarted
                                                              25. Write to outbox_events
                                                              26. Return session with questions
                                                            ◀─────────────────────────
                  27. 201 Created (session + questions)
                  ◀──────────────────

                                                            (async)
                                                              28. Worker picks up SessionStarted
                                                              29. Dispatch to subscribers:
                                                                  - NotificationSubscriber → in-app
                                                                  - EmailSubscriber (if enabled)
                                                              30. Update outbox: consumed_at
```

---

## 4. Authentication & Token Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       AUTHENTICATION PIPELINE                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  REGISTRATION                                                              │
│  ─────────────                                                              │
│  Browser → POST /api/v1/auth/register {email, password, invite_token?}    │
│                                                                            │
│   ┌─ If CLOSED_BETA_ENABLED=true ─┐                                        │
│   │  Validate invite_token:        │                                       │
│   │   • exists in beta_invites     │                                       │
│   │   • used_at IS NULL            │                                       │
│   │   • expires_at > now()         │                                       │
│   │   • email matches invite       │                                       │
│   │  Check user_count < MAX_BETA   │                                       │
│   └────────────────────────────────┘                                       │
│                                                                            │
│  1. Hash password (Argon2id: 19MB, 2 iter, 1 lane)                        │
│  2. Insert into identity.users                                            │
│  3. Mark invite as used (used_at = now())                                 │
│  4. Create session (token_family_id)                                      │
│  5. Issue access + refresh tokens (RS256)                                 │
│  6. Publish UserRegistered event → welcome email queued                   │
│  7. Audit log: USER_REGISTERED                                            │
│                                                                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  LOGIN                                                                      │
│  ─────                                                                      │
│  Browser → POST /api/v1/auth/login {email, password}                       │
│                                                                            │
│  1. Lookup user by email                                                   │
│  2. Verify password (Argon2id)                                             │
│  3. Check MFA enabled?                                                     │
│     │                                                                      │
│     ├─ NO MFA → issue tokens, return 200                                  │
│     │                                                                      │
│     └─ MFA → return 200 {mfa_required: true, mfa_token}                   │
│              Browser → POST /api/v1/auth/mfa/verify {mfa_token, code}     │
│              Verify TOTP code (pyotp)                                      │
│              Issue tokens, return 200                                      │
│                                                                            │
│  4. Audit log: LOGIN_SUCCESS or LOGIN_FAILED                              │
│                                                                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  TOKEN ROTATION                                                            │
│  ────────────                                                              │
│  access_token (15min) ──▶ EXPIRED                                         │
│                          │                                                 │
│                          ▼                                                 │
│  Browser → POST /api/v1/auth/refresh {refresh_token}                      │
│                          │                                                 │
│                          ▼                                                 │
│  1. Verify refresh_token signature (RS256)                                │
│  2. Lookup by token_hash in identity.refresh_tokens                       │
│  3. Check: revoked_at IS NULL, consumed_at IS NULL                        │
│  4. REUSE DETECTION:                                                       │
│     If token was already consumed (consumed_at != NULL):                  │
│       │                                                                    │
│       ├─ REVOKE entire token_family                                        │
│       ├─ Log: REFRESH_REUSE_DETECTED (security incident)                  │
│       └─ Return 401 — user must re-login                                  │
│                                                                            │
│  5. Mark old refresh token: consumed_at = now()                           │
│  6. Issue new access + refresh tokens (same family)                       │
│  7. Update rotated_to_token_hash on old token                             │
│  8. Return new tokens                                                      │
│                                                                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  AUTHENTICATED REQUEST                                                     │
│  ──────────────────────                                                    │
│  Browser → GET /api/v1/learning/dashboard                                 │
│             Authorization: Bearer <access_token>                          │
│                                                                            │
│  Middleware stack (outer → inner):                                         │
│   1. CORS                                                                  │
│   2. SecurityHeaders                                                       │
│   3. RateLimit (Redis sliding window)                                     │
│   4. CSRF (for non-GET, check X-CSRF-Token)                               │
│   5. Correlation (assign X-Request-ID)                                    │
│                                                                            │
│  Dependency injection:                                                     │
│   get_current_user_id(token) →                                             │
│     1. Decode JWT (RS256 pub key, verify iss, aud, exp, iat)             │
│     2. Check token_version matches user.token_version                    │
│     3. Lookup session in identity.sessions                                │
│     4. Check session not revoked, not expired (idle + absolute)          │
│     5. Return user_id                                                     │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Database Schema Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL — 10 SCHEMAS, 57+ TABLES                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────┐  ┌──────────────────────────────┐ │
│  │  identity                       │  │  content                     │ │
│  │  ─────────                      │  │  ───────                     │ │
│  │  • users                        │  │  • subjects                  │ │
│  │  • sessions                     │  │  • concepts                  │ │
│  │  • verification_tokens          │  │  • concept_dependencies      │ │
│  │  • password_reset_tokens        │  │  • learning_objectives       │ │
│  │  • refresh_tokens               │  │  • question_templates        │ │
│  │  • mfa_secrets                  │  │  • template_versions         │ │
│  │  • mfa_recovery_codes           │  │  • content_versions          │ │
│  │  • security_incidents           │  │  • content_packs             │ │
│  │  • auth_audit_logs              │  │  • misconceptions            │ │
│  │  • beta_invites                 │  │                              │ │
│  │  • beta_feedback                │  │                              │ │
│  └─────────────────────────────────┘  └──────────────────────────────┘ │
│                                                                         │
│  ┌─────────────────────────────────┐  ┌──────────────────────────────┐ │
│  │  learning                       │  │  assessment                  │ │
│  │  ─────────                      │  │  ───────────                 │ │
│  │  • enrollments                  │  │  • attempts                  │ │
│  │  • study_sessions               │  │  • answers                   │ │
│  │  • learning_goals               │  │  • attempt_results           │ │
│  │  • achievements                 │  │                              │ │
│  │  • streaks                      │  │                              │ │
│  └─────────────────────────────────┘  └──────────────────────────────┘ │
│                                                                         │
│  ┌─────────────────────────────────┐  ┌──────────────────────────────┐ │
│  │  mastery                        │  │  scheduling                  │ │
│  │  ───────                        │  │  ──────────                  │ │
│  │  • mastery_scores               │  │  • review_schedules          │ │
│  │  • mastery_history              │  │  • scheduled_reviews         │ │
│  │  • algorithm_versions           │  │                              │ │
│  │  • reviews                      │  │                              │ │
│  └─────────────────────────────────┘  └──────────────────────────────┘ │
│                                                                         │
│  ┌─────────────────────────────────┐  ┌──────────────────────────────┐ │
│  │  analytics                      │  │  billing                     │ │
│  │  ─────────                      │  │  ───────                     │ │
│  │  • events                       │  │  • subscriptions             │ │
│  │  • beta_events                  │  │  • invoices                  │ │
│  │  • user_activity                │  │  • payments                  │ │
│  └─────────────────────────────────┘  └──────────────────────────────┘ │
│                                                                         │
│  ┌─────────────────────────────────┐  ┌──────────────────────────────┐ │
│  │  administration                 │  │  infrastructure              │ │
│  │  ──────────────                 │  │  ──────────────              │ │
│  │  • notifications                │  │  • outbox_events             │ │
│  │  • notification_preferences     │  │  • outbox_leases             │ │
│  │                                 │  │  • scheduled_jobs            │ │
│  │                                 │  │  • worker_heartbeats         │ │
│  │                                 │  │  • email_delivery_log        │ │
│  │                                 │  │  • dead_letter_events        │ │
│  └─────────────────────────────────┘  └──────────────────────────────┘ │
│                                                                         │
│  Extensions: uuid-ossp, citext, pg_trgm, btree_gin                       │
│  Tuning: shared_buffers=1GB, work_mem=16MB, max_connections=200         │
│  SSL: enabled (certs at /etc/ssl/certs/postgres.pem)                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Background Processing Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  WORKER PROCESS — INTERNAL ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  Worker Host (single process, async event loop)             │       │
│  │  app/workers/host.py                                        │       │
│  │                                                             │       │
│  │  ┌─────────────────────┐  ┌─────────────────────────┐      │       │
│  │  │  Outbox Dispatcher  │  │  Scheduler Processor    │      │       │
│  │  │  ─────────────────  │  │  ──────────────────     │      │       │
│  │  │  Loop (every 1s):   │  │  Loop (every 30s):      │      │       │
│  │  │  1. SELECT pending  │  │  1. SELECT due jobs     │      │       │
│  │  │     from outbox     │  │  2. Acquire lock        │      │       │
│  │  │  2. Acquire lease   │  │     (locked_by,         │      │       │
│  │  │     (outbox_leases) │  │      lock_expires_at)   │      │       │
│  │  │  3. Deserialize     │  │  3. Execute job         │      │       │
│  │  │     event           │  │  4. Update next_run_at  │      │       │
│  │  │  4. Dispatch to all │  │  5. Update heartbeat    │      │       │
│  │  │     subscribers     │  │                         │      │       │
│  │  │  5. On success:     │  │                         │      │       │
│  │  │     consumed_at=now │  │                         │      │       │
│  │  │  6. On failure:     │  │                         │      │       │
│  │  │     next_retry_at   │  │                         │      │       │
│  │  │     retry_history   │  │                         │      │       │
│  │  │     += {attempt}    │  │                         │      │       │
│  │  │  7. After N retries │  │                         │      │       │
│  │  │     → dead_letter   │  │                         │      │       │
│  │  └─────────────────────┘  └─────────────────────────┘      │       │
│  │                                                             │       │
│  │  ┌─────────────────────┐  ┌─────────────────────────┐      │       │
│  │  │  Notification       │  │  Email Sender           │      │       │
│  │  │  Processor          │  │  ────────────           │      │       │
│  │  │  ────────────       │  │  Loop (every 10s):      │      │       │
│  │  │  Subscribes to:     │  │  1. SELECT queued       │      │       │
│  │  │   • SessionStarted  │  │     emails from         │      │       │
│  │  │   • MasteryUpdated  │  │     email_delivery_log  │      │       │
│  │  │   • AchievementUnl  │  │  2. Send via SMTP       │      │       │
│  │  │   • StreakUpdated   │  │  3. Update status       │      │       │
│  │  │  Creates            │  │     (sent/failed/bounce)│      │       │
│  │  │   administration.   │  │  4. On bounce: log      │      │       │
│  │  │   notifications     │  │     bounce_type         │      │       │
│  │  │  Routes via prefs   │  │  5. On failure:         │      │       │
│  │  │   (in_app/email)    │  │     schedule retry      │      │       │
│  │  └─────────────────────┘  └─────────────────────────┘      │       │
│  │                                                             │       │
│  │  ┌─────────────────────────────────────────────────┐       │       │
│  │  │  Retry Engine                                    │       │       │
│  │  │  ────────────                                    │       │       │
│  │  │  Exponential backoff:                            │       │       │
│  │  │   attempt 1: retry in 1 min                      │       │       │
│  │  │   attempt 2: retry in 5 min                      │       │       │
│  │  │   attempt 3: retry in 15 min                     │       │       │
│  │  │   attempt 4: retry in 1 hour                     │       │       │
│  │  │   attempt 5: → dead_letter_events                │       │       │
│  │  │                                                  │       │       │
│  │  │  Jitter: ±20% to avoid thundering herd           │       │       │
│  │  └─────────────────────────────────────────────────┘       │       │
│  │                                                             │       │
│  │  ┌─────────────────────────────────────────────────┐       │       │
│  │  │  Subscriber Registry                             │       │       │
│  │  │  ─────────────────                               │       │       │
│  │  │  Maps event_type → list of subscriber callables  │       │       │
│  │  │  Each subscriber is idempotent (uses event_id    │       │       │
│  │  │  as dedup key)                                   │       │       │
│  │  └─────────────────────────────────────────────────┘       │       │
│  │                                                             │       │
│  │  ┌─────────────────────────────────────────────────┐       │       │
│  │  │  Heartbeat (every 15s)                           │       │       │
│  │  │  UPDATE infrastructure.worker_heartbeats         │       │       │
│  │  │  SET last_seen_at = now(),                       │       │       │
│  │  │      jobs_processed = N,                         │       │       │
│  │  │      jobs_failed = M,                            │       │       │
│  │  │      current_job = '...'                         │       │       │
│  │  └─────────────────────────────────────────────────┘       │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Closed Beta Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CLOSED BETA — END-TO-END FLOW                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ADMIN                          PLATFORM                     USER       │
│  ─────                          ────────                     ────       │
│                                                                         │
│  1. POST /admin/beta/invites ─▶ 2. Create invite in        │           │
│     {email: "jane@x.com"}        identity.beta_invites     │           │
│                                  (token=secrets.urlsafe(32),│           │
│                                   expires_at=now()+7d)      │           │
│                                  3. Email beta_invitation ─▶│(email)    │
│                                  4. Return token to admin   │           │
│  5. Send invite URL manually ───────────────────────────▶ 6. Click URL │
│                                                              │          │
│                                                              ▼          │
│  7. Register form pre-fills email ◀────────────────────── 8. Submit   │
│     POST /api/v1/auth/register                              with token │
│     {email, password, invite_token}                                    │
│                              │                                         │
│                              ▼                                         │
│  9. Validate invite:                                                   │
│     • exists? • unused? • not expired? • email matches?               │
│  10. Check user_count < 20                                            │
│  11. Hash password (Argon2id)                                          │
│  12. Insert into identity.users                                        │
│  13. Mark invite used_at=now()                                         │
│  14. Create session + tokens                                           │
│  15. Publish UserRegistered event                                      │
│  16. Email beta_welcome ◀───────────────────────────────── 17. Inbox  │
│                              │                                         │
│                              ▼                                         │
│  18. Welcome wizard shows (4 steps) ◀──────────── 19. User logs in    │
│      • Profile (display name, timezone)                                │
│      • Learning goal (5/10/15/20)                                      │
│      • Subject pick                                                    │
│      • Tutorial                                                        │
│  20. Beta banner shows on all pages                                    │
│  21. Feedback button (floating) shows on all pages                     │
│                              │                                         │
│                              ▼                                         │
│                              22. User studies, submits feedback        │
│                              POST /api/v1/beta/feedback                │
│                              {rating, category, comment,               │
│                               browser, platform, route,                │
│                               correlation_id}                         │
│                              │                                         │
│                              ▼                                         │
│  23. Triage feedback ◀────── 24. Stored in identity.beta_feedback      │
│      GET /api/v1/beta/feedback                                         │
│      • Reproduce bug                                                   │
│      • Categorize                                                      │
│      • Update status: open→acknowledged→resolved→closed                │
│      • Email user with resolution                                     │
│                              │                                         │
│                              ▼                                         │
│  25. Review analytics                                                 │
│      GET /api/v1/beta/analytics                                       │
│      • DAU, sessions, completion rate                                 │
│      • Feedback themes                                                │
│      • Drop-off points                                                │
│                                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Security Boundaries

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       SECURITY ZONES & BOUNDARIES                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ZONE 1: PUBLIC INTERNET (untrusted)                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • 20 invited beta users' browsers                              │   │
│  │  • Anyone attempting unauthenticated access                     │   │
│  └──────────────────────────┬──────────────────────────────────────┘   │
│                             │                                           │
│  BOUNDARY: Firewall (UFW) — only 22, 80, 443 exposed                   │
│                             │                                           │
│  ▼                                       │                               │
│  ZONE 2: DMZ (Nginx)                     │                               │
│  ┌───────────────────────────────────────┘                               │
│  │  • TLS termination                                                  │
│  │  • Rate limiting (per-IP)                                           │
│  │  • Security headers (HSTS, CSP, X-Frame-Options)                    │
│  │  • Request size limit (50 MB)                                       │
│  │  • No business logic                                                │
│  └──────────────────────────┬                                          │
│                             │                                          │
│  BOUNDARY: Docker network (internal only)                              │
│                             │                                          │
│  ▼                                       │                              │
│  ZONE 3: APPLICATION (Backend, Frontend, Worker)                       │
│  ┌───────────────────────────────────────┘                              │
│  │  • JWT verification (RS256 pub key)                                │
│  │  • Argon2id password hashing                                       │
│  │  • MFA (TOTP)                                                      │
│  │  • RBAC role checks (admin endpoints)                              │
│  │  • CSRF token validation                                           │
│  │  • SQL injection prevention (SQLAlchemy parameterized queries)     │
│  │  • XSS prevention (React escapes by default)                       │
│  │  • Audit logging (every auth event)                                │
│  │  • Rate limiting (per-user, Redis-backed)                          │
│  └─────┬──────────────────────┬──────────────────────┬───────────────┘
│        │                      │                      │
│        ▼                      ▼                      ▼
│  BOUNDARY: Docker network    BOUNDARY: Docker       BOUNDARY: Network
│  (DB only on internal)       network (internal)     egress (HTTPS only)
│        │                      │                      │
│  ▼                            ▼                      ▼
│  ZONE 4: DATA                ZONE 4: DATA           ZONE 5: EXTERNAL
│  ┌──────────────────┐        ┌──────────────────┐   ┌────────────────┐
│  │  PostgreSQL      │        │  Redis           │   │  • SMTP        │
│  │  (no public      │        │  (no public      │   │  • Sentry      │
│  │   port)          │        │   port)          │   │  • S3          │
│  │                  │        │                  │   │  • AI provider │
│  │  • Encrypted     │        │  • Auth required │   │    (optional)  │
│  │    connections   │        │    (requirepass) │   │                │
│  │    (SSL)         │        │                  │   │                │
│  │  • Role-based    │        │  • LRU eviction  │   │                │
│  │    access        │        │                  │   │                │
│  │    (mastery user │        │  • 512MB maxmem  │   │                │
│  │     has DML only)│        │                  │   │                │
│  │                  │        │                  │   │                │
│  │  • Audit tables  │        │                  │   │                │
│  │    (immutable)   │        │                  │   │                │
│  │                  │        │                  │   │                │
│  │  • Encrypted     │        │                  │   │                │
│  │    MFA secrets   │        │                  │   │                │
│  │    (BYTEA)       │        │                  │   │                │
│  └──────────────────┘        └──────────────────┘   └────────────────┘
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

SECRET LOCATIONS:
  • /opt/mastery-engine/.env.production  (chmod 600, deployer:deployer)
  • /opt/mastery-engine/keys/jwt-private.pem (chmod 600)
  • /opt/mastery-engine/infrastructure/nginx/ssl/privkey.pem (chmod 600)
  • External secrets store (Vault, AWS SM, sops+age)
  • NOT in the docker image
  • NOT in git
  • NOT in logs (redacted by structlog config)
```

---

## 9. Failure Modes & Cascading Effects

```
                       FAILURE CASCADE DIAGRAM

  Postgres down
       │
       ├─▶ Backend /health/ready → 503 (DB check fails)
       │       │
       │       └─▶ Nginx marks backend unhealthy
       │              │
       │              └─▶ Users see 502 (no upstream)
       │
       ├─▶ Worker cannot process outbox → backlog grows
       │       │
       │       └─▶ Notifications not sent
       │       └─▶ Emails not sent
       │       └─▶ Audit events not persisted (lost)
       │
       └─▶ Scheduler cannot lock jobs → jobs delayed
              │
              └─▶ Stale recommendations
              └─▶ No streak updates

  Redis down
       │
       ├─▶ Backend /health/ready → 503 (Redis check fails)
       │
       ├─▶ Rate limiting fails open (or closed, depending on config)
       │       │
       │       └─▶ If fail-open: DDoS possible
       │       └─▶ If fail-closed: all requests 429
       │
       ├─▶ Cache misses → every request hits DB
       │       │
       │       └─▶ DB connections exhausted
       │              │
       │              └─▶ Cascade to Postgres failure mode
       │
       ├─▶ Session storage unavailable
       │       │
       │       └─▶ Users cannot log in
       │       └─▶ Existing sessions may fail
       │
       └─▶ Pub/Sub broken
              │
              └─▶ WebSocket events not delivered
              └─▶ Real-time updates stop

  Worker down (single instance)
       │
       ├─▶ Outbox grows unboundedly
       │       │
       │       └─▶ Disk fills up (outbox_events table)
       │
       ├─▶ Emails not sent (password reset, beta invites)
       │       │
       │       └─▶ Users locked out (can't reset password)
       │
       ├─▶ Notifications not delivered
       │
       └─▶ Scheduler misses job windows
              │
              └─▶ Streak calculations stale
              └─▶ Review reminders not sent

  Nginx down
       │
       └─▶ Platform completely unreachable
              │
              └─▶ No failover (single Nginx instance for beta)
              └─▶ Users see connection refused

  Disk full
       │
       ├─▶ Postgres cannot write WAL → crashes
       │       │
       │       └─▶ Cascade to Postgres failure mode
       │
       ├─▶ Redis cannot persist (BGSAVE fails)
       │
       ├─▶ Docker cannot write logs → containers may crash
       │
       └─▶ Backups cannot be written → backup fails

  Network partition (server loses internet)
       │
       ├─▶ Cannot send email (SMTP unreachable)
       ├─▶ Cannot upload backups to S3
       ├─▶ Cannot send events to Sentry
       ├─▶ Cannot reach AI providers (if enabled)
       │
       └─▶ Platform still works locally (users can study)
              (until a cascade triggers)

  TLS cert expired
       │
       ├─▶ Browsers show "Not secure" warning
       │       │
       │       └─▶ Users may abandon (trust lost)
       │
       └─▶ Mobile apps with cert pinning fail entirely
```

---

## 10. Deployment Sequence (Step-by-Step)

```
STEP 1: Provision host
  └─▶ Install Docker, clone repo, create .env.production

STEP 2: Generate secrets
  ├─▶ openssl genrsa → keys/jwt-private.pem
  ├─▶ openssl rsa → keys/jwt-public.pem
  ├─▶ certbot certonly → infrastructure/nginx/ssl/*.pem
  └─▶ Generate DATABASE_PASSWORD, REDIS_PASSWORD, etc.

STEP 3: Start infrastructure
  └─▶ docker compose up -d postgres redis
       ├─▶ Postgres runs init scripts 01-04 (some may fail on FK to identity.users)
       └─▶ Redis starts with password + maxmemory

STEP 4: Start backend (creates base tables via Base.metadata.create_all)
  └─▶ docker compose up -d backend
       ├─▶ lifespan hook calls init_database()
       ├─▶ Creates identity.users, identity.sessions, infrastructure.outbox_events
       └─▶ Re-run any failed init scripts (02, 03, 04)

STEP 5: Start worker
  └─▶ docker compose up -d worker
       ├─▶ Registers heartbeat
       ├─▶ Outbox dispatcher starts polling
       ├─▶ Scheduler starts picking up due jobs
       └─▶ Email sender starts polling queue

STEP 6: Start frontend
  └─▶ docker compose up -d --build frontend
       ├─▶ Builds Next.js with NEXT_PUBLIC_API_URL baked in
       └─▶ Serves on port 3000

STEP 7: Start Nginx
  └─▶ docker compose up -d nginx
       ├─▶ Loads TLS certs
       ├─▶ Routes /api/* → backend, / → frontend
       └─▶ Security headers applied

STEP 8: Start monitoring
  └─▶ docker compose up -d prometheus grafana
       ├─▶ Prometheus scrapes backend, workers, frontend
       └─▶ Grafana loads production dashboard

STEP 9: Bootstrap admin user
  ├─▶ Temporarily disable CLOSED_BETA_ENABLED
  ├─▶ POST /api/v1/auth/register (admin email)
  ├─▶ SQL: UPDATE identity.users SET role='administrator'
  └─▶ Re-enable CLOSED_BETA_ENABLED, restart backend + worker

STEP 10: Create invites
  └─▶ Loop: POST /api/v1/admin/beta/invites (×5 canary, then ×15)

STEP 11: Verify
  └─▶ Run smoke tests (deployment-checklist.md §10)

STEP 12: Launch
  ├─▶ Send canary invites (5 users)
  ├─▶ Wait 4 hours
  ├─▶ If green: send remaining 15 invites
  └─▶ On-call rotation starts
```

---

## 11. Network Ports Reference

| Port | Service | Exposed? | Purpose |
|---|---|---|---|
| 22 | sshd | ✅ public | SSH admin access |
| 80 | nginx | ✅ public | HTTP (redirects to 443) |
| 443 | nginx | ✅ public | HTTPS (main entry) |
| 3000 | frontend | ❌ internal | Next.js dev/prod server |
| 3001 | grafana | ⚠️ should be private | Grafana UI |
| 5432 | postgres | ❌ internal | PostgreSQL |
| 6379 | redis | ❌ internal | Redis |
| 8000 | backend | ❌ internal | FastAPI / uvicorn |
| 9090 | prometheus | ⚠️ should be private | Prometheus UI |
| 9113 | nginx-exporter | ❌ internal | Nginx metrics |
| 9121 | redis-exporter | ❌ internal | Redis metrics |
| 9187 | postgres-exporter | ❌ internal | Postgres metrics |

**Firewall (UFW) recommendation:**
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp        # SSH
sudo ufw allow 80/tcp        # HTTP
sudo ufw allow 443/tcp       # HTTPS
# Optionally, allow Grafana/Prometheus only from VPN:
sudo ufw allow from 10.0.0.0/8 to any port 3001
sudo ufw allow from 10.0.0.0/8 to any port 9090
sudo ufw enable
```

---

## 12. Volume & Backup Topology

```
┌──────────────────────────────────────────────────────────────────────┐
│                     VOLUMES & BACKUP TOPOLOGY                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  HOST FILESYSTEM                  DOCKER VOLUMES                     │
│  ───────────────                  ──────────────                     │
│                                                                      │
│  /opt/mastery-engine/              postgres_data ─┐                  │
│  ├── .env.production               (Postgres data)│                  │
│  ├── docker-compose.prod.yml                        │                 │
│  ├── infrastructure/               redis_data ─────┤                 │
│  │   ├── nginx/                    (Redis RDB)     │                 │
│  │   │   ├── nginx.conf                              │                │
│  │   │   └── ssl/                                   │                │
│  │   │       ├── fullchain.pem     backend_logs ───┤                 │
│  │   │       └── privkey.pem       (uvicorn logs)  │                 │
│  │   ├── postgres/                                   │                │
│  │   │   ├── init/                 worker_logs ────┤                 │
│  │   │   │   ├── 01-schemas.sql    (worker logs)   │                 │
│  │   │   │   ├── 02-auth.sql                        │                │
│  │   │   │   ├── 03-bg.sql         nginx_logs ─────┤                 │
│  │   │   │   └── 04-beta.sql       (access/error)  │                 │
│  │   │   └── postgresql.conf                        │                │
│  │   ├── redis/                                     │                │
│  │   │   └── redis.conf            prometheus_data─┤                │
│  │   └── monitoring/               (15d metrics)   │                │
│  │       ├── prometheus/                            │                │
│  │       │   ├── prometheus.yml    grafana_data ───┘                │
│  │       │   └── alerts.yml         (dashboards, users)             │
│  │       └── grafana/                                              │
│  │           └── dashboards/                                       │
│  ├── keys/                                                          │
│  │   ├── jwt-private.pem                                            │
│  │   └── jwt-public.pem                                             │
│  ├── scripts/                                                       │
│  │   ├── backup.sh                                                  │
│  │   ├── health-check.sh                                            │
│  │   └── setup.sh                                                   │
│  ├── backend/                                                       │
│  ├── frontend/                                                      │
│  └── backups/  ◀── daily backup tar.gz.enc                          │
│      ├── mastery_engine_2026-07-01.tar.gz.enc                       │
│      ├── mastery_engine_2026-07-02.tar.gz.enc                       │
│      └── ... (30-day retention)                                     │
│                                                                      │
│                              │                                       │
│                              │ daily cron (02:00 UTC)                │
│                              ▼                                       │
│                  ┌─────────────────────────┐                        │
│                  │  backup.sh              │                        │
│                  │  1. pg_dump (custom,    │                        │
│                  │     compress=9)         │                        │
│                  │  2. Redis BGSAVE        │                        │
│                  │  3. tar .env, compose,  │                        │
│                  │     nginx config        │                        │
│                  │  4. openssl encrypt     │                        │
│                  │     (AES-256-CBC,       │                        │
│                  │      PBKDF2)            │                        │
│                  │  5. aws s3 cp           │                        │
│                  │     (STANDARD_IA)       │                        │
│                  │  6. cleanup >30d        │                        │
│                  └──────────┬──────────────┘                        │
│                             │                                       │
│                             ▼                                       │
│                  ┌─────────────────────────┐                        │
│                  │  AWS S3                 │                        │
│                  │  s3://mastery-engine-   │                        │
│                  │  backups/               │                        │
│                  │  ├── 2026-07-01.enc     │                        │
│                  │  ├── 2026-07-02.enc     │                        │
│                  │  └── ...                │                        │
│                  └─────────────────────────┘                        │
│                                                                      │
│  Slack notification on success/failure (SLACK_WEBHOOK)               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 13. CI/CD Pipeline (Reference)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CI/CD PIPELINE (GitHub Actions)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PUSH TO main / PR opened                                           │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────┐                                                    │
│  │ 1. lint     │  ruff (backend) + eslint (frontend)                │
│  │    (5 min)  │  Fail on any error                                 │
│  └──────┬──────┘                                                    │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────┐  ┌─────────────────┐  ┌────────────────────────┐  │
│  │ 2. backend  │  │ 3. frontend     │  │ 4. security scan       │  │
│  │    tests    │  │    tests        │  │    (Trivy, gitleaks,   │  │
│  │    (10 min) │  │    (8 min)      │  │     pip-audit,         │  │
│  │             │  │                 │  │     npm audit)         │  │
│  │  pytest     │  │  vitest         │  │    (5 min)             │  │
│  │  + mypy     │  │  + playwright   │  │                        │  │
│  └──────┬──────┘  └────────┬────────┘  └───────────┬────────────┘  │
│         │                  │                       │               │
│         └──────────┬───────┴───────────────────────┘               │
│                    │                                               │
│                    ▼                                               │
│         ┌─────────────┐                                            │
│         │ 5. build    │  docker build (with layer caching)         │
│         │    (8 min)  │  Tag with git SHA                          │
│         └──────┬──────┘                                            │
│                │                                                   │
│                ▼                                                   │
│         ┌─────────────┐                                            │
│         │ 6. staging  │  Deploy to staging instance                │
│         │    deploy   │  Run smoke tests                           │
│         │    (5 min)  │  Tag image as "staging-verified"           │
│         └──────┬──────┘                                            │
│                │                                                   │
│       (manual approval gate)                                       │
│                │                                                   │
│                ▼                                                   │
│         ┌─────────────┐                                            │
│         │ 7. prod     │  Blue-green deploy:                        │
│         │    deploy   │   - Deploy to green                        │
│         │    (10 min) │   - Health check                           │
│         │             │   - Switch Nginx upstream                  │
│         │             │   - Tear down blue                         │
│         └─────────────┘                                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

**End of deployment diagrams.** Next: read `post-launch-monitoring.md` for the long-term monitoring strategy, alert rules, and dashboard usage.
