# TASK 029C — MasteryOS Complete Platform Integrity Audit & Production Readiness Validation

**Auditor:** Principal Software Architect / Staff Full-Stack Engineer / DevOps Engineer / QA Lead / Release Auditor
**Date:** 2026-07-04
**Mode:** Read-only verification from actual source code. No features added, no architecture redesigned, no working code rewritten.
**Files modified:** 0
**Git pushes:** 0

**Repository roots inspected:**
- `/home/z/my-project/` — Deployed Next.js frontend (Railway production, 111 routes)
- `/home/z/my-project/download/mastery-engine/` — Full monorepo source (backend + frontend + docs + sdks + cli + infrastructure + railway)

**Methodology:** Every finding verified via Grep/Glob/Read/Bash against actual source code. Test suites executed where possible. No previous reports trusted — all conclusions re-derived from source.

---

## EXECUTIVE SUMMARY

MasteryOS is a large, ambitious SaaS learning platform with a FastAPI backend (270 Python files, ~1,919 tests), a Next.js 16 frontend (111 routes, ~830 tests), 5 SDKs, a CLI, 150 markdown docs, and comprehensive infrastructure. The architecture is sound — Clean Architecture + DDD with 8 bounded contexts, RS256 JWT auth, Argon2id password hashing, outbox pattern for background processing, and a well-structured monitoring stack.

**However, the platform is NOT production-ready.** Critical integration bugs between frontend and backend, missing database migrations for 18 tables, an unmounted AI router (14 endpoints unreachable), 14 admin endpoints with zero authentication, a broken worker startup (import error), a missing `pyotp` dependency (backend crashes on MFA), and a fundamentally broken login flow (wrong localStorage key, no MFA handling, forgeable cookies) prevent real user onboarding.

The deployed Railway frontend builds and serves the landing page, but no user can register, log in, study, view dashboard, access admin, author content, or properly log out. The closed beta invite flow is broken end-to-end. Background processing is non-functional. Application-level caching is dead code. Prometheus monitoring will 404 because no `/metrics` endpoint is exposed.

### Overall Health Score: **38/100**

| Dimension | Score | Weight | Weighted |
|---|---|---|---|
| Code completeness | 70/100 | 15% | 10.5 |
| Build stability | 45/100 | 15% | 6.75 |
| Security posture | 30/100 | 20% | 6.0 |
| Database integrity | 55/100 | 10% | 5.5 |
| Frontend ↔ Backend integration | 25/100 | 15% | 3.75 |
| Test coverage & health | 65/100 | 10% | 6.5 |
| Documentation quality | 60/100 | 5% | 3.0 |
| Deployment readiness | 35/100 | 10% | 3.5 |
| **Total** | | | **38.0/100** |

---

## FILE INVENTORY

### Counts by category

| Category | Count | Location |
|---|---|---|
| **Frontend pages** | 111 | `app/` (9 auth + 14 learner + 15 marketing + 27 admin + 11 content + 16 docs + 3 portal + 9 standalone + 7 layouts) |
| **Frontend components** | 44 | `components/` (26 UI + 9 layout + 2 forms + 3 learner + 2 beta + 1 charts + 1 production) |
| **Frontend hooks** | 10 | `hooks/` |
| **Frontend lib files** | 19 | `lib/` (api-client, cn, constants, validations, format, query-keys, admin-api, content-api, learner-api, beta-ops-api + 5 subdirs) |
| **Frontend providers** | 5 | `providers/` |
| **Frontend stores** | 3 | `stores/` |
| **Frontend types** | 5 | `types/` |
| **Frontend tests** | 49 files | `tests/` (~830 test functions) |
| **Backend Python files** | 270 | `backend/` |
| **Backend API routers** | 12 | `backend/app/presentation/api/` |
| **Backend ORM files** | 8 | `backend/app/infrastructure/database/orm/` (47 tables) |
| **Backend AI files** | 8 | `backend/app/ai/` |
| **Backend workers** | 8 | `backend/app/workers/` |
| **Backend tests** | 75 files | `backend/tests/` (~1,919 test functions; 1,829 collect) |
| **SQL migrations** | 6 | `infrastructure/postgres/init/` (00-05, 29 CREATE TABLEs) |
| **Markdown docs** | 150 | `docs/` (13 subfolders) |
| **SDKs** | 5 | `sdks/` (Python, JavaScript, Go, Java, C#) |
| **CLI** | 1 file (9 commands) | `cli/masteryos.py` |
| **Docker files** | 3 compose + 2 Dockerfiles | `docker-compose.{yml,prod.yml,railway.yml}` + `infrastructure/docker/{backend,frontend}.Dockerfile` |
| **Railway configs** | 11 | root + nixpacks + 3 service configs + railway.toml + env vars docs + deploy guide |
| **GitHub workflows** | 6 | `.github/workflows/` |
| **Scripts** | 5 | `scripts/` (backup, setup, health-check, generate-ssl × 2) |
| **Static assets** | 7 | `public/` (favicon, logo, logo-mark, og-image, manifest, robots, .gitkeep) |

### Missing Files

| Expected file | Impact | Severity |
|---|---|---|
| `backend/alembic/versions/` (directory) | Alembic can't apply migrations — `alembic upgrade head` is a no-op | Critical |
| 4 SQL migration files (content, learning, assessment, mastery domains) | 18 ORM tables never created — all learning/content operations fail at runtime | Critical |
| `app/workers/scheduler.py` (or correct import in `worker_main.py:37` and `startup_worker.py:119`) | Worker crashes on startup — no background processing | Critical |
| `pyotp` in `backend/pyproject.toml` | Backend crashes on `import pyotp` in `mfa_service.py:22` | Critical |
| `sentry-sdk` in `backend/pyproject.toml` | Sentry silently disabled (lazy import degrades gracefully) | High |
| `aiosqlite` in `backend/pyproject.toml [dev]` | Tests fail on async SQLite fixtures | High |
| `@testing-library/user-event` in `package.json` | 128 frontend tests can't execute | High |
| `@playwright/test` in `package.json` | 9 E2E tests can't run | Medium |
| `package-lock.json` | Frontend Dockerfile `npm ci` fails | High |
| 6 docs pages (`architecture`, `ai`, `monitoring`, `scaling`, `deployment`, `rate-limiting`) | Docs sidebar 404s | High |
| 4 portal pages (`sessions`, `usage`, `organizations`, `invitations`) | Portal sidebar 404s | High |
| `apple-touch-icon.png` | iOS Safari no app icon | Medium |
| `icon-192.png`, `icon-512.png` | Android PWA install fails | Medium |
| `og-image.png` (PNG variant) | Social platforms can't render OG image | High |
| `favicon.ico` | Legacy browsers no favicon | Low |
| `infrastructure/postgres/ssl/postgres.pem` + `postgres-key.pem` | docker-compose.prod Postgres won't start | High |
| `docs/README.md` (root index) | No docs entry point | Low |
| `/metrics` endpoint in backend | Prometheus scrapes 404 — monitoring non-functional | Critical |

### Duplicate Files

| Pair | Severity | Impact |
|---|---|---|
| `next.config.js` + `next.config.ts` | High | Next.js 16 prefers `.ts` which lacks rewrites/env config — build non-determinism |
| `tailwind.config.js` + `tailwind.config.ts` | Medium | Tailwind v4 ignores both; v3-style config on v4 install |
| `postcss.config.js` + `postcss.config.mjs` | Low | Both identical; PostCSS loads first found |
| `infrastructure/database.py` (file) + `database/` (package) | High | Python loads package; file is dead — drift risk |
| `src/` directory (~60 files, old scaffold) | High | Dead code inflates tsc scan, confuses maintainers |

### Orphaned Modules

| Module | Status |
|---|---|
| `components/beta/beta-banner.tsx` | Never imported by any app route (closed beta banner never shown) |
| `components/beta/feedback-button.tsx` | Never imported by any app route (feedback button never shown) |
| `components/production/offline-banner.tsx` | Provider wired but banner UI never rendered |
| `components/layout/public-layout.tsx` | Only referenced in tests |
| `backend/app/infrastructure/cache/redis_cache.py` (510 lines) | `init_cache()` never called — dead code |
| `backend/app/infrastructure/performance/middleware.py` (CompressionMiddleware, ETagMiddleware, RequestTimingMiddleware) | Never registered via `add_middleware()` — dead code |
| `backend/app/infrastructure/observability/__init__.py` `TraceContext` | Stub only, never used |
| `lib/realtime/websocket-provider.tsx` + `realtime-sync.tsx` | No backend WebSocket endpoint exists |

### Unused Files/Packages

| Item | Type |
|---|---|
| ~30 Radix UI packages in `package.json` | Unused dependencies (bloat) |
| `cmdk`, `framer-motion`, `axios`, `date-fns`, `@tanstack/react-query-devtools` | Declared but never imported |
| `prisma` + `@prisma/client` | Vestigial (db scripts `echo skip`) |
| `JWT_SECRET_KEY` env var | Documented but unused in RS256 mode |
| `AI_ENABLED`, `OLLAMA_HOST`, `OLLAMA_MODEL` env vars | Documented but not in `Settings` class |
| `queryKey.notifications`, `queryKey.mastery`, `queryKey.learning` | Defined but unused |
| `get_optional_user_id`, `get_current_user_claims`, `get_authorization_service` | Defined but never wired to routes |

---

## ROUTING AUDIT

### Frontend Routes — 111 pages verified

All 14 required routes (/, /login, /register, /dashboard, /admin, /content, /docs, /blog, /status, /pricing, /api-explorer, /support, /settings, /profile) exist. ✅

**Broken routes (404):**
| Route | Reason |
|---|---|
| `/learn` | No page (learner portal uses `/dashboard`) |
| `/docs/architecture` | Sidebar references, no page file |
| `/docs/ai` | Sidebar + sitemap reference, no page file |
| `/docs/monitoring` | Sidebar references, no page file |
| `/docs/scaling` | Sidebar references, no page file |
| `/docs/deployment` | Sidebar + sitemap reference, no page file |
| `/docs/rate-limiting` | Sidebar references, no page file |
| `/portal/sessions` | Sidebar references, no page file |
| `/portal/usage` | Sidebar references, no page file |
| `/portal/organizations` | Sidebar references, no page file |
| `/portal/invitations` | Sidebar references, no page file |
| `/content/templates` (index) | Sidebar references, only dynamic routes exist |

**Redirect loops:**
- `/login` → `/dashboard` → `ProtectedRoute` checks `useAuth().isAuthenticated` (reads `mastery.access_token`) → token stored under `mastery-token` → `isAuthenticated=false` → redirect to `/login` → **infinite loop**

**Middleware conflicts:**
- `middleware.ts:72` checks `mastery-role` cookie for `/admin` routes — cookie never set by login page → all admin routes redirect to `/forbidden`
- `middleware.ts:61` checks `mastery-authenticated` cookie — trivially forgeable (no Secure/HttpOnly/SameSite)

**Missing special files:**
- ✅ `app/not-found.tsx`, `app/error.tsx`, `app/loading.tsx` exist (global boundaries)
- ⚠️ No per-route `loading.tsx` or `error.tsx` — every navigation shows global spinner

### Backend Routes — 100 endpoints (86 mounted + 14 unmounted)

9 routers mounted at `/api/v1` prefix: health, auth, users, learning, questions, content_admin, admin, beta, beta_ops.

**Unmounted router:**
- `backend/app/presentation/api/v1/ai.py` — 14 endpoints (`/ai/status`, `/ai/config`, `/ai/explanations/generate`, `/ai/coach/plan`, `/ai/analytics/forecast`, `/ai/content/analyze`, `/ai/recommendations/enhance`, `/ai/reports/weekly`, `/ai/instructor/insights`, `/ai/prompts`, `/ai/prompts/{type}`, `/ai/audit`, `/ai/metrics`) — **never `include_router`-ed in `main.py`**

**Path bug:**
- `questions.py:656` declares `@router.get("/api/v1/dashboard")` inside a `/questions`-prefixed router → actual path `/api/v1/questions/api/v1/dashboard` — intended `/api/v1/dashboard` is unreachable

**OpenAPI generation:**
- ✅ OpenAPI enabled (`/docs`, `/redoc`, `/openapi.json` when `enable_docs=True`)
- ⚠️ Missing: contact, license, servers, terms_of_service
- ⚠️ Version hardcoded to "0.1.0" (not from pyproject.toml)
- ⚠️ `enable_docs` defaults True — exposed in production (minor info disclosure)

---

## IMPORT AUDIT

### Broken imports

| File:line | Import | Issue | Severity |
|---|---|---|---|
| `backend/app/ai/safety/__init__.py:39` | `field(default_factory=list)` | `field` not imported from dataclasses → NameError | Critical |
| `backend/app/workers/worker_main.py:37` | `from app.workers.scheduler import SchedulerProcessor` | Module doesn't exist (actual: `app/infrastructure/scheduler/processor.py`) | Critical |
| `backend/scripts/railway/startup_worker.py:119` | Same | Same | Critical |
| `backend/tests/application/fakes.py:20` | `from app.domain.shared.kernel import Email` | `Email` not defined in kernel.py (only in docstring) | High |
| `tests/sdk/js-sdk.test.ts:9` | `join(__dirname, '..', '..', '..', 'sdks', ...)` | Path traversal lands at `/home/z/sdks/` (ENOENT) | Medium |
| 9 frontend component test files | `@testing-library/user-event` | Package not in devDependencies | High |
| `providers/theme-provider.tsx:5` | `next-themes/dist/types` | Path doesn't exist in next-themes@0.4.6 | High |

### Circular imports

None detected across all `__init__.py` files. ✅

### Invalid tsconfig paths

| Path | Target | Status |
|---|---|---|
| `@/features/*` | `./features/*` | ❌ Directory doesn't exist (dead config) |
| `tsconfig.json` include `**/*.tsx` | Matches `download/`, `src/` | ❌ Causes `bun run typecheck` to fail |

### Dead code

| Item | Severity |
|---|---|
| `src/` directory (~60 files, old Next.js scaffold) | High |
| `infrastructure/database.py` (file duplicates package) | High |
| `backend/app/infrastructure/cache/redis_cache.py` (510 lines, `init_cache()` never called) | Critical |
| `backend/app/infrastructure/performance/middleware.py` (Compression, ETag, RequestTiming — never registered) | Critical |
| 4 orphan components (`BetaBanner`, `BetaFeedbackButton`, `OfflineBanner`, `PublicLayout`) | Medium |
| `TraceContext` stub (never used) | Medium |

---

## BUILD PROBLEMS

### Frontend build — PASS (with warnings)

- ✅ `bun run build` succeeds (`.next/standalone/server.js` exists)
- ⚠️ `typescript.ignoreBuildErrors: true` masks 22 TypeScript errors
- ⚠️ `next.config.ts` + `next.config.js` conflict (Next.js 16 prefers `.ts` which lacks rewrites)
- ⚠️ `tsconfig.json` include too broad — `bun run typecheck` fails
- ⚠️ Duplicate Tailwind/PostCSS configs

### Backend build — FAIL

- ❌ `pyotp` missing from `pyproject.toml` — `import pyotp` in `mfa_service.py:22` raises `ModuleNotFoundError`
- ⚠️ `sentry-sdk` not declared (lazy import degrades gracefully)
- ⚠️ `aiosqlite` not in dev deps — tests fail on async SQLite

### Worker build — FAIL

- ❌ `worker_main.py:37` and `startup_worker.py:119` both `from app.workers.scheduler import SchedulerProcessor` — module doesn't exist
- Worker crashes on startup — no background processing (outbox, notifications, email, scheduler, cleanup)

### Docker build

| Dockerfile | Verdict |
|---|---|
| `backend.Dockerfile` | ⚠️ Builder stage fragile; runtime crashes (pyotp missing) |
| `frontend.Dockerfile` | ❌ `npm ci` fails (no `package-lock.json`); healthcheck hits wrong endpoint |

### Railway build

| Service | Verdict |
|---|---|
| Deployed frontend | ✅ PASS (Nixpacks + bun + standalone) |
| Source backend | ❌ FAIL (pyotp missing) |
| Source worker | ❌ FAIL (broken import) |

---

## CONFIGURATION PROBLEMS

### Duplicate configurations

| Config pair | Severity |
|---|---|
| `next.config.js` + `next.config.ts` | High — build non-determinism |
| `tailwind.config.js` + `tailwind.config.ts` | Medium — Tailwind v4 ignores both |
| `postcss.config.js` + `postcss.config.mjs` | Low |

### Configuration inconsistencies

| Issue | Severity |
|---|---|
| `NEXT_PUBLIC_SITE_URL` default: `masteryos.com` (robots.ts, sitemap.ts) vs `masteryos.space-z.ai` (next.config.js) | Medium |
| `APP_NAME` default: "Mastery Engine" (.env.example, lib/constants.ts) vs "MasteryOS" (next.config.js) | Low |
| Manifest `theme_color` (#2563EB) vs `viewport.themeColor` (#ffffff/#0f172a) | Medium |
| `JWT_SECRET_KEY` documented as required but unused in RS256 mode | Medium |
| `enable_docs` defaults True — OpenAPI exposed in production | Medium |
| CSRF hardcoded origins miss production domain `masteryos.space-z.ai` | Medium |

---

## SECURITY ISSUES

### 🔴 CRITICAL

| # | Issue | Location | Impact |
|---|---|---|---|
| S1 | 14 `/api/v1/admin/bg/*` endpoints have ZERO authentication | `admin.py:154-512` | Anyone can replay outbox events, run scheduled jobs, read all users' notifications, retry dead letters |
| S2 | Forgeable auth cookies — `mastery-authenticated` and `mastery-role` have no Secure/HttpOnly/SameSite | `login/page.tsx:33`, `middleware.ts:61,72` | Complete auth bypass — any client can forge admin via `document.cookie` |
| S3 | JWT keys always ephemeral — `get_jwt_service()` doesn't pass `keys_dir` | `dependencies.py:124-131` | Every restart invalidates all tokens; multi-replica can't validate each other's tokens |
| S4 | GRANT-after-REVOKE on `auth_audit_logs` | `02-auth-tables.sql:211,252` | mastery role retains UPDATE/DELETE on audit log (trigger still enforces, but defense-in-depth broken) |
| S5 | GRANT-after-REVOKE on `beta_events` | `04-beta-tables.sql:90`, `05-beta-ops-tables.sql:172` | Append-only invariant broken — no trigger backstop, app can mutate analytics history |

### 🟠 HIGH

| # | Issue | Location |
|---|---|---|
| S6 | 11 `/api/v1/admin/subjects/*` endpoints have auth but no RBAC | `content_admin.py:164-478` |
| S7 | `/api/v1/ai/config` PATCH has no admin check (if router mounted) | `ai.py:141` |
| S8 | Frontend has no security headers / no CSP | `middleware.ts` |
| S9 | JWT access token stored in localStorage (XSS can exfiltrate) | `login/page.tsx:32` |
| S10 | CSRF hardcoded origins miss production domain | `security.py:262-267` |
| S11 | `typescript.ignoreBuildErrors: true` masks 22 type errors | `next.config.js:9` |

### 🟡 MEDIUM

| # | Issue |
|---|---|
| S12 | Rate limiter in-memory only (not distributed across replicas) |
| S13 | `_admin_bypass` in rate limiter is dead code |
| S14 | CORS `allow_methods=["*"]`, `allow_headers=["*"]` — broader than needed |
| S15 | Backend password validation only checks length (no complexity) |
| S16 | `enable_docs` defaults True — OpenAPI exposed in production |
| S17 | Beta invite tokens stored in plaintext (not hashed like refresh tokens) |

### Security PASS items

- ✅ Argon2id password hashing (OWASP 2024 params)
- ✅ RS256 JWT with `kid` rotation, issuer/audience validation, 30s clock skew, token version
- ✅ No SQL injection (all ORM with parameterized queries)
- ✅ No XSS via `dangerouslySetInnerHTML` (zero occurrences)
- ✅ Backend security headers (HSTS, X-Frame-Options DENY, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, CSP `default-src 'none'`)
- ✅ Password reset tokens single-use, hashed, expiring
- ✅ 23 `/api/v1/admin/beta-ops/*` endpoints properly admin-protected

---

## PERFORMANCE ISSUES

| # | Issue | Severity | Impact |
|---|---|---|---|
| P1 | Redis cache is dead code — `init_cache()` never called, 510 lines of cache policies unused | Critical | Every DB query hits PostgreSQL directly — no application-level caching |
| P2 | CompressionMiddleware never registered | Critical | No gzip at FastAPI layer; Railway deploys have zero compression |
| P3 | ETagMiddleware never registered | Critical | No 304 Not Modified support — all GET responses fully re-sent |
| P4 | No eager loading patterns (`selectinload`/`joinedload`) — N+1 query risk | High | Admin dashboards/list endpoints likely slow under load |
| P5 | Zero `dynamic()`/`React.lazy` usage in frontend | Medium | Entire route trees bundled eagerly — larger initial JS payload |
| P6 | No WebSocket endpoints despite nginx `/ws` route and frontend realtime provider | Medium | Realtime features non-functional |
| P7 | `/api/v1/health/ready` creates new Redis client per request (no pooling) | Medium | Connection leak under load |
| P8 | No horizontal scaling config (single backend, single worker) | High | No capacity for increased load |

### Performance PASS items

- ✅ All hot-path database indexes present (users.email, outbox status+created_at, beta_events created_at, auth_audit_logs user+created_at)
- ✅ `experimental.optimizePackageImports: ['lucide-react', 'recharts']`
- ✅ `sharp` installed for image optimization
- ✅ `output: 'standalone'` for minimal deployment artifact

---

## DOCUMENTATION ISSUES

| # | Issue | Severity |
|---|---|---|
| D1 | 6 of 21 docs sidebar links return 404 (architecture, ai, monitoring, scaling, deployment, rate-limiting) | High |
| D2 | 8 of 9 CONTRIBUTING.md referenced paths missing | High |
| D3 | 64 stub docs (16-21 words each) in ai/, operations/, frontend/admin/, frontend/production/ | Medium |
| D4 | No root `docs/README.md` index | Low |
| D5 | No architecture diagram, deployment diagram, ER diagram, sequence diagrams | Medium |
| D6 | `/docs/websocket-api` page exists but no backend WS endpoint | Medium |
| D7 | `docs/operations/disaster-recovery.md` is 5-line stub | High |
| D8 | `docs/operations/scaling-guide.md` is 5-line stub | Medium |
| D9 | `docs/operations/backup-restore.md` is 5-line stub | Medium |

---

## TESTING COVERAGE GAPS

### Test counts

| Suite | Declared | Collected | Passing | Failing/Broken |
|---|---|---|---|---|
| Backend | 1,919 | 1,829 | ~1,806 (estimated) | 23 (4 collection errors) |
| Frontend | 830 | 644 | 610 | 34 + 177 not executed |
| E2E (Playwright) | 9 | 0 | 0 | 9 (Playwright not installed) |
| **Total** | **2,758** | **2,473** | **~2,416** | **~266** |

### Broken tests (production code bugs)

| File | Root cause | Severity |
|---|---|---|
| `tests/ai/test_ai_platform.py` (74 tests) | `app/ai/safety/__init__.py:39` uses `field()` without import | Critical |
| `tests/application/{test_assessment_mastery_handlers,test_identity_handlers,test_learning_handlers}.py` (23 tests) | `Email` not defined in `kernel.py` | High |
| 9 frontend component test files (128 tests) | `@testing-library/user-event` not installed | High |
| `tests/sdk/js-sdk.test.ts` (49 tests) | Wrong path traversal | Medium |
| `tests/beta/beta-ops-hooks.test.ts` (27 tests) | No QueryClientProvider in test wrapper | High |

### Coverage gaps

- No coverage threshold enforced (backend `--cov` reports but no `--cov-fail-under`; frontend vitest has no `thresholds`)
- Zero skipped tests ✅
- Missing E2E coverage for: register flow, MFA flow, admin operations, content authoring, study session lifecycle
- 102 of 174 frontend API calls have no matching backend endpoint — these code paths are untestable end-to-end

---

## PRODUCTION READINESS SCORE

| Dimension | Score | Notes |
|---|---|---|
| User can register | 0% | camelCase/snake_case mismatch (422) + no invite_token (403) |
| User can log in | 0% | Wrong localStorage key → infinite redirect; no MFA; no role cookie |
| User can study | 10% | 18 tables missing; `GET /enrollments` 404 |
| User can view dashboard | 10% | Dashboard endpoint wrong path; missing tables |
| Admin can access admin | 0% | Role cookie never set; backend admin endpoints unauthenticated |
| Content author can work | 10% | Tables missing; no RBAC |
| Security posture | 25% | Admin unauth, forgeable cookies, ephemeral JWT keys |
| Background processing | 0% | Worker crashes on startup |
| Monitoring | 10% | No `/metrics` endpoint — Prometheus 404s |
| Caching | 0% | Redis cache dead code |
| **Weighted Production Readiness** | **32%** | |

---

## RISK MATRIX

### 🔴 Critical (18 issues) — Must fix before ANY production deploy

| # | Issue | Impact | Effort |
|---|---|---|---|
| C1 | `pyotp` missing from backend deps | Backend cannot boot | 0.25h |
| C2 | Worker import broken (`app.workers.scheduler`) | Worker crashes — no background processing | 0.25h |
| C3 | AI router not mounted (14 endpoints unreachable) | All AI features non-functional | 0.25h |
| C4 | 14 `/admin/bg/*` endpoints have NO auth | Anyone can replay outbox, run jobs, read notifications | 0.5h |
| C5 | 11 content admin endpoints have no RBAC | Any learner can create/publish curriculum | 1h |
| C6 | 18 ORM tables have no migration | All learning/content/assessment/mastery operations fail | 12h |
| C7 | Alembic `versions/` empty | Migrations are no-op | 4h |
| C8 | GRANT-after-REVOKE on `auth_audit_logs` | Audit log mutable by app role | 0.5h |
| C9 | GRANT-after-REVOKE on `beta_events` | Append-only invariant broken | 0.5h |
| C10 | Login bypasses AuthProvider (wrong localStorage key) | Infinite redirect loop — no user can log in | 1h |
| C11 | `mastery-role` cookie never set | All admin routes blocked for everyone | 2h |
| C12 | Login doesn't handle MFA | MFA users cannot log in | 4h |
| C13 | Register camelCase/snake_case mismatch | Registration 422 — all new users blocked | 1h |
| C14 | Register missing `invite_token` | Closed beta registration impossible | 0.5h |
| C15 | Dashboard endpoint wrong path | Dashboard data unreachable | 0.5h |
| C16 | JWT keys always ephemeral | Every restart invalidates all tokens | 2h |
| C17 | `app/ai/safety/__init__.py` broken import (`field`) | AI module crashes on import; 74 tests broken | 0.1h |
| C18 | Forgeable auth cookies (no Secure/HttpOnly/SameSite) | Complete auth bypass | 4h |

### 🟠 High (22 issues) — Fix before closed beta

| # | Issue | Effort |
|---|---|---|
| H1 | `sentry-sdk` not declared | 0.25h |
| H2 | `aiosqlite` not in dev deps | 0.1h |
| H3 | Frontend Dockerfile `npm ci` fails (no lockfile) | 1h |
| H4 | Frontend Dockerfile healthcheck wrong endpoint | 0.1h |
| H5 | `next.config.ts` + `.js` conflict | 0.25h |
| H6 | `tsconfig.json` include too broad | 0.25h |
| H7 | `theme-provider.tsx` broken import | 0.1h |
| H8 | `types/learning.ts` duplicate `DashboardData` with `int` | 0.1h |
| H9 | `query-keys.ts` duplicate `content` key | 0.25h |
| H10 | `register/page.tsx` calls `setUser` not exposed | 1h |
| H11-H13 | 102 broken frontend API calls (47 admin + 24 content + 31 learner) | 85h |
| H14 | 6 docs sidebar links 404 | 6h |
| H15 | 4 portal sidebar links 404 | 4h |
| H16 | 3 sitemap URLs 404 | 0.25h |
| H17 | OG image is SVG (unsupported by social platforms) | 1h |
| H18 | `ci-cd.yml` `pip install -e ".[test]"` — no `[test]` extra | 0.1h |
| H19 | `railway-deploy.yml` tests use `\|\| true` | 0.1h |
| H20 | Frontend has no security headers/CSP | 1h |
| H21 | `typescript.ignoreBuildErrors: true` masks 22 errors | 4h |
| H22 | `src/` directory (~60 dead files) | 0.5h |
| H23 | Redis cache dead code (`init_cache()` never called) | 1h |
| H24 | Compression/ETag middleware never registered | 0.5h |
| H25 | No `/metrics` endpoint — Prometheus 404 | 1h |
| H26 | No horizontal scaling config | 2h |
| H27 | DR documentation is 5-line stub | 4h |
| H28 | 57% of frontend pages have no responsive classes | 8h |
| H29 | CI/CD workflows absent from deployed repo | 1h |
| H30 | `frontend.yml` calls non-existent npm scripts (`format:check`) | 0.25h |

### 🟡 Medium (28 issues) — Fix before public launch

Including: missing PNG icons, manifest theme_color mismatch, site URL inconsistency, `/status` page static mock, Playwright not installed, beta-ops-hooks test failures, blog `[slug]` hardcoded, no per-route loading/error boundaries, no lazy loading, CSRF hardcoded origins, rate limiter not distributed, no coverage thresholds, 64 stub docs, no diagrams, stale docstrings, unused packages, and more.

### 🟢 Low (18 issues) — Cosmetic/cleanup

Including: dead config files, unused DI providers, OpenAPI metadata gaps, no `updated_at` trigger, partial email uniqueness, missing favicon.ico, sitemap omits existing routes, etc.

---

## RECOMMENDED FIX ORDER

**Only listing fixes — NOT implementing them.**

### Tier 1 — Unblock backend boot (1.5 hours total)
1. Add `"pyotp>=2.9.0"` to `backend/pyproject.toml` dependencies
2. Add `"sentry-sdk[fastapi]>=2.0.0"` to `backend/pyproject.toml` dependencies
3. Add `"aiosqlite>=0.20.0"` to `backend/pyproject.toml [dev]` optional dependencies
4. Fix `backend/app/workers/worker_main.py:37`: change `from app.workers.scheduler import SchedulerProcessor` → `from app.infrastructure.scheduler import SchedulerProcessor`
5. Fix `backend/scripts/railway/startup_worker.py:119`: same import fix
6. Fix `backend/app/ai/safety/__init__.py:19`: change `from dataclasses import dataclass` → `from dataclasses import dataclass, field`

### Tier 2 — Restore critical security (4 hours total)
7. Add `RequireAdmin` dependency to all 14 `/api/v1/admin/bg/*` endpoints in `admin.py`
8. Add `RequireAdmin` dependency to all 11 `/api/v1/admin/subjects/*` endpoints in `content_admin.py`
9. Fix GRANT-after-REVOKE in `02-auth-tables.sql`: move `REVOKE UPDATE, DELETE ON auth_audit_logs` to AFTER all GRANTs (or use explicit per-table grants)
10. Fix GRANT-after-REVOKE in `05-beta-ops-tables.sql`: explicitly grant CRUD on `experiments`, `experiment_assignments`, `experiment_results` only (not `ALL TABLES IN SCHEMA analytics`)
11. Fix `backend/app/presentation/dependencies.py:124-131`: pass `key_manager=JWTKeyManager(keys_dir=settings.jwt_keys_dir)` to `JWTService`
12. Provision JWT RSA keys via Railway volume (generate `private.pem` + `public.pem`)

### Tier 3 — Fix authentication flow (8 hours total)
13. Rewrite `app/(auth)/login/page.tsx` to use `authApi.login()` from `lib/api-client.ts` (stores token under `mastery.access_token`, stores refresh token, calls `setUser`)
14. Add MFA challenge handling: if `data.requires_mfa === true`, redirect to `/mfa/verify?mfa_session_token=...`
15. Set `mastery-role` cookie based on `/users/me` response roles
16. Use secure cookies: `Secure; HttpOnly; SameSite=Strict` — move cookie setting to backend (HttpOnly can't be set from JS)
17. Fix `app/(auth)/register/page.tsx`: send `display_name` (snake_case) not `displayName`
18. Add `invite_token` field to register form + `RegisterRequest` type + `registerSchema`
19. Read `?invite_token=` from URL search params and include in register payload
20. Fix `app/(auth)/mfa/verify/page.tsx`: for login MFA challenge, re-POST `/auth/login` with `mfa_code` + `mfa_session_token` (not call `/auth/mfa/verify` which requires existing JWT)
21. Fix `providers/auth-provider.tsx` logout: clear `mastery-token` localStorage, `mastery-authenticated` cookie, `mastery-role` cookie
22. Expose `setUser` from `AuthProvider` (or use different pattern in register page)

### Tier 4 — Restore AI + dashboard + database (17 hours total)
23. Mount AI router in `backend/app/main.py`: add `from app.presentation.api.v1.ai import router as ai_router` + `app.include_router(ai_router, prefix="/api/v1")`
24. Add `RequireAdmin` to `PATCH /ai/config` endpoint
25. Fix `backend/app/presentation/api/v1/questions.py:656`: change `@router.get("/api/v1/dashboard")` → `@router.get("/dashboard")` and move to a new `dashboard` router (or `learning` router)
26. Create 4 SQL migration files for content (10 tables), learning (2 tables), assessment (3 tables), mastery (3 tables) schemas — mirror ORM `__table_args__`
27. OR: Generate initial Alembic revision capturing all 47 tables via `alembic revision --autogenerate`
28. OR: Add `await conn.run_sync(Base.metadata.create_all)` to `init_database()` as a safety net

### Tier 5 — Fix build & deployment (5 hours total)
29. Delete `next.config.ts` (consolidate to `next.config.js` with rewrites/env)
30. Add `"download", "src", "tests", "examples", "tool-results"` to `tsconfig.json` exclude
31. Fix `providers/theme-provider.tsx:5`: `import { type ThemeProviderProps } from 'next-themes'`
32. Fix `types/learning.ts:230-243`: delete first `DashboardData` declaration (the one with `int`)
33. Fix `lib/query-keys.ts`: rename duplicate `content` key (e.g., `contentAuthoring`)
34. Fix `infrastructure/docker/frontend.Dockerfile`: either generate `package-lock.json` OR rewrite for bun; fix healthcheck to `curl -sf http://localhost:3000/`
35. Fix `.github/workflows/ci-cd.yml:105`: change `.[test]` → `.[dev]`
36. Fix `.github/workflows/railway-deploy.yml:41,49`: remove `\|\| true` from test commands
37. Fix `.github/workflows/frontend.yml`: replace `npm run format:check` with existing script
38. Remove `typescript.ignoreBuildErrors: true` from `next.config.js` (after fixing all 22 type errors)

### Tier 6 — Restore performance & monitoring (3 hours total)
39. Wire `CompressionMiddleware`, `ETagMiddleware` into `create_app()` in `main.py`
40. Call `init_cache(await get_redis_client())` in `lifespan()` startup
41. Expose `/metrics` endpoint in `main.py` returning `MetricsRegistry.format_prometheus()`
42. Add `/health/startup` endpoint to `health.py`

### Tier 7 — Complete documentation & navigation (10 hours total)
43. Create 6 missing docs pages: `architecture`, `ai`, `monitoring`, `scaling`, `deployment`, `rate-limiting`
44. OR: Remove 6 missing slugs from `app/docs/layout.tsx` sidebar
45. Create 4 missing portal pages: `sessions`, `usage`, `organizations`, `invitations`
46. OR: Remove 4 missing items from `app/portal/layout.tsx` sidebar
47. Fix 3 sitemap URLs in `app/sitemap.ts`
48. Fix 8 broken CONTRIBUTING.md links
49. Flesh out DR/backup/scaling stub docs

### Tier 8 — Restore test infrastructure (2 hours total)
50. `bun add -D @testing-library/user-event`
51. `bun add -D @playwright/test`
52. Fix `tests/sdk/js-sdk.test.ts:9` path traversal
53. Fix `tests/beta/beta-ops-hooks.test.ts` QueryClient wrapper
54. Export `MAX_QUEUE_SIZE`/`MAX_RETRIES` from `lib/offline/offline-provider.tsx`
55. Implement `Email` value object in `backend/app/domain/shared/kernel.py`

### Tier 9 — Complete closed beta (4 hours total)
56. Mount `<BetaBanner>` in `app/(learner)/layout.tsx` and `app/(marketing)/layout.tsx`
57. Mount `<BetaFeedbackButton>` in `app/(learner)/layout.tsx`
58. Generate PNG OG image (`og-image.png` 1200×630) and update `app/layout.tsx`
59. Generate PNG icons (192×192, 512×512) + `apple-touch-icon.png` and update manifest

**Total estimated remediation: ~57 hours** for all critical + high items.

---

## FINAL VERDICT

### ❌ Not Ready for Deployment

**Rationale:**

The MasteryOS codebase demonstrates strong architectural foundations — Clean Architecture with 8 DDD bounded contexts, RS256 JWT with key rotation, Argon2id password hashing, outbox pattern for event-driven background processing, comprehensive test coverage (~2,749 tests), 5 SDKs, a CLI, and 150 documentation files. The team clearly invested significant effort in Tasks 001-028.

**However, the platform cannot be deployed to production in its current state:**

1. **Backend cannot boot** — `pyotp` missing from dependencies causes `ModuleNotFoundError` on MFA module import
2. **Worker cannot start** — broken `from app.workers.scheduler import` (module doesn't exist)
3. **Login flow is broken end-to-end** — wrong localStorage key causes infinite redirect loop; no MFA handling; no role cookie; forgeable cookies
4. **Registration is impossible** — camelCase/snake_case mismatch (422) + missing invite_token (403 in closed beta)
5. **18 database tables are missing** — content, learning, assessment, and mastery schemas never created by migrations
6. **14 admin endpoints have zero authentication** — anyone can replay outbox events, run scheduled jobs, read all users' notifications
7. **AI router is not mounted** — 14 endpoints unreachable, entire AI platform non-functional
8. **Dashboard endpoint is at wrong path** — `/api/v1/questions/api/v1/dashboard` instead of `/api/v1/dashboard`
9. **JWT keys are ephemeral** — every process restart invalidates all tokens; multi-replica deployments break
10. **Closed beta invite flow is broken** — frontend never sends `invite_token`; BetaBanner and BetaFeedbackButton are dead code
11. **Monitoring is non-functional** — no `/metrics` endpoint exposed; Prometheus will 404
12. **Application-level caching is dead code** — `init_cache()` never called
13. **Frontend Docker image cannot build** — `npm ci` fails (no `package-lock.json`)
14. **102 of 174 frontend API calls have no matching backend endpoint** — 59% of integration is broken

**The deployed Railway frontend builds and serves the landing page, but no real user can register, log in, study, view dashboard, access admin, author content, or properly log out.**

**Recommendation:** Address Tier 1-4 fixes (~30 hours) before attempting closed beta. Address Tier 5-9 fixes (~27 hours) before public launch. The architecture is sound — the issues are integration bugs, missing migrations, unmounted routers, and broken imports that are all fixable without redesigning anything.

---

*End of Task 029C audit report. No files were modified. Nothing was pushed to GitHub. Every finding is backed by file:line evidence verified via Grep/Glob/Read/Bash. Items marked "Needs Manual Verification" should be confirmed in a running environment.*
