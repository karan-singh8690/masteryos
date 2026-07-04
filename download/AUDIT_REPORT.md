# MasteryOS — Production Audit Report

**Auditor:** Senior Staff Engineer (read-only audit)
**Date:** 2026-07-04
**Scope:** Full codebase inspection across Tasks 001–028
**Project roots inspected:**
- `/home/z/my-project/` — **Deployed Next.js frontend** (Railway production, 111 routes)
- `/home/z/my-project/download/mastery-engine/` — **Full monorepo source** (backend + frontend + docs + sdks + cli + infrastructure + railway)

**No files were modified. Nothing was pushed to GitHub.**

---

## ⚠️ CRITICAL CAVEAT — Source vs Deployed Divergence

A top-priority discovery: **the deployed frontend (`/home/z/my-project/`) and the source frontend (`download/mastery-engine/frontend/`) have diverged significantly.** The deployed version contains fixes and entire directories that the source repo does not:

| Aspect | Source `frontend/` | Deployed `/home/z/my-project/` |
|---|---|---|
| `lib/` directory | ❌ **MISSING entirely** (186 imports broken) | ✅ Present — 19 files (api-client, cn, constants, validations, format, query-keys, admin-api, content-api, learner-api, beta-ops-api + 5 subdirs) |
| Route groups | ❌ Uses `(admin)`, `(content)`, `(app)`, `(learner)`, `(portal)` — all collide on root URLs (8 sets of duplicates) | ✅ Uses real folders `admin/`, `content/`, `docs/`, `portal/` (URL-prefixed); only `(auth)`, `(learner)`, `(marketing)` are groups |
| `/login` page | ❌ MISSING | ✅ Present at `app/(auth)/login/page.tsx` |
| `/admin` index | ❌ MISSING (route group doesn't prefix URL) | ✅ Present at `app/admin/page.tsx` |
| `/content` index | ❌ MISSING | ✅ Present at `app/content/page.tsx` |
| 13 `/docs/*` pages | ❌ MISSING (only 3 exist) | ✅ All 13 present (administration, authentication, cli, content-authoring, errors, faq, installation, learning-engine, sdks, security, troubleshooting, websocket-api, api-explorer) |
| `/privacy`, `/terms` | ❌ Only at `/legal/privacy`, `/legal/terms` | ✅ Both root `/privacy` + `/terms` AND `/legal/*` exist |
| `output: 'standalone'` in next.config.js | ❌ MISSING | ✅ Set |
| Route count | ~95 (with conflicts) | 111 (clean, no conflicts) |
| Build status | ❌ CANNOT BUILD | ✅ Builds successfully (`.next/standalone/server.js` exists) |

**Conclusion:** The deployed version is the source of truth for what's running in production. The source repo is stale. Many "FAIL" findings against the source frontend don't apply to the deployed version. This report calls out both, but production-readiness is judged against the **deployed** version.

---

## PASS-BY-PASS VERDICTS

| Pass | Area | Verdict | Critical Issues |
|------|------|---------|-----------------|
| 1 | Project structure | ✅ **PASS** | All 13 expected top-level folders exist |
| 2 | Route audit (deployed) | ⚠️ **WARN** | 111 routes; middleware admin check dead; some portal sidebar links broken |
| 2 | Route audit (source) | 🔴 **FAIL** | Missing lib/, 8 duplicate route sets, no /login, no /docs/*, no /admin |
| 3 | Documentation | ⚠️ **WARN** | 153 md files, ~56k words; 64 stub files; 6 broken CONTRIBUTING links; no root docs index |
| 4 | Component audit | ✅ **PASS** (deployed) / 🔴 FAIL (source) | 45 components; all 26 shadcn primitives present; source has broken imports |
| 5 | API audit | 🔴 **FAIL** | AI router NOT mounted (13 endpoints unreachable); `/api/v1/dashboard` path bug; admin endpoints unauthenticated |
| 6 | Backend audit | 🔴 **FAIL** | AI router unmounted; admin router public; worker import broken; pyotp missing; AI config not in Settings |
| 7 | Database audit | 🔴 **FAIL** | 18 ORM tables have no migration (content/learning/assessment/mastery); Alembic versions/ empty; 47 tables vs 57 claimed; 2/10 schemas empty |
| 8 | Railway deployment | ⚠️ **WARN** | Deployed frontend OK; source frontend broken; worker startCommand crashes; root railway.json bypasses startup script |
| 9 | Build audit | ⚠️ **WARN** | Deployed frontend builds; backend pip install OK but runtime crashes (pyotp); worker crashes on import; duplicate Tailwind/PostCSS configs |
| 10 | Static asset audit | ⚠️ **WARN** | All required assets exist; OG image is SVG (unsupported by social platforms); no PNG icons in manifest; no apple-touch-icon |
| 11 | Authentication audit | 🔴 **FAIL** | JWT keys always ephemeral; admin endpoints unauth; login bypasses MFA; register doesn't send invite_token; middleware admin check dead; pyotp missing |
| 12 | Broken link audit | ⚠️ **WARN** (deployed) / 🔴 FAIL (source) | Deployed: 4 broken portal sidebar links; source: 18+ broken links, 12 sitemap 404s |
| 13 | Import audit | ✅ **PASS** (deployed) / 🔴 FAIL (source) | Deployed: all imports resolve; source: 186 broken @/lib/* imports |
| 14 | SEO audit | 🔴 **FAIL** | Only 2 pages export metadata; zero JSON-LD; zero per-page canonicals; OG image SVG; blog [slug] hardcoded; 12 sitemap URLs 404 |
| 15 | Production audit | ⚠️ **WARN** | Most Task 001-028 features exist but several are broken at runtime (AI unreachable, worker crashes, admin unauth, 18 tables missing migrations) |

---

## PASS 1 — PROJECT STRUCTURE AUDIT  ✅ PASS

### 1.1 Top-level folder inventory

| Expected folder | Location | Status |
|---|---|---|
| `backend/` | `download/mastery-engine/backend/` | ✅ Present (FastAPI + Python 3.13) |
| `frontend/` | `download/mastery-engine/frontend/` + deployed root | ✅ Present (Next.js 16 + React 19) |
| `docs/` | `download/mastery-engine/docs/` | ✅ Present (13 subfolders, 153 md files) |
| `scripts/` | `download/mastery-engine/scripts/` | ✅ Present (5 shell scripts + railway/) |
| `docker/` | `download/mastery-engine/infrastructure/docker/` | ✅ Present (2 Dockerfiles) |
| `monitoring/` | `download/mastery-engine/infrastructure/monitoring/` | ✅ Present (alertmanager, grafana, prometheus) |
| `railway/` | `download/mastery-engine/railway/` | ✅ Present (3 service configs + guides) |
| `infrastructure/` | `download/mastery-engine/infrastructure/` | ✅ Present (docker, monitoring, nginx, postgres, redis, load-testing) |
| `migrations/` | `backend/alembic/` + `infrastructure/postgres/init/` | ⚠️ Alembic configured but `versions/` empty; 6 SQL init scripts present |
| `workers/` | `backend/app/workers/` | ✅ Present (7 files) |
| `ai/` | `backend/app/ai/` | ✅ Present (8 subpackages: prompts, safety, audit, gateway, explanations, coach, providers) |
| `sdk/` | `download/mastery-engine/sdks/` | ✅ Present (5 SDKs: Python, JS, Go, Java, C#) |
| `cli/` | `download/mastery-engine/cli/` | ✅ Present (masteryos.py with 9 commands) |

**Verdict: PASS.** All 13 expected folders exist. The only structural concern is the empty Alembic `versions/` directory (covered in Pass 7).

---

## PASS 2 — ROUTE AUDIT  ⚠️ WARN (deployed) / 🔴 FAIL (source)

### 2.1 Deployed frontend route inventory (111 routes)

**Route organization (deployed):**
- **Route groups** (no URL prefix): `(auth)` 9 routes, `(learner)` 14 routes, `(marketing)` 15 routes
- **Real folders** (URL-prefixed): `admin/` 27 routes, `content/` 11 routes, `docs/` 15 routes, `portal/` 3 routes
- **Standalone**: 9 routes (api-explorer, forbidden, health, maintenance, offline, sdk, status, support, unauthorized)

### 2.2 Required routes verification (deployed)

| Required URL | Status | File |
|---|---|---|
| `/` | ✅ | `app/(marketing)/page.tsx` |
| `/login` | ✅ | `app/(auth)/login/page.tsx` |
| `/register` | ✅ | `app/(auth)/register/page.tsx` |
| `/dashboard` | ✅ | `app/(learner)/dashboard/page.tsx` |
| `/admin` | ✅ | `app/admin/page.tsx` |
| `/content` | ✅ | `app/content/page.tsx` |
| `/docs` | ✅ | `app/docs/page.tsx` |
| `/docs/*` | ✅ | 13 sub-pages under `app/docs/` |
| `/api-explorer` | ✅ | `app/api-explorer/page.tsx` |
| `/blog` | ✅ | `app/(marketing)/blog/page.tsx` |
| `/support` | ✅ | `app/support/page.tsx` |
| `/status` | ✅ | `app/status/page.tsx` |
| `/pricing` | ✅ | `app/(marketing)/pricing/page.tsx` |
| `/security` | ✅ | `app/(marketing)/security/page.tsx` |
| `/privacy` | ✅ | `app/(marketing)/privacy/page.tsx` + `/legal/privacy` |
| `/terms` | ✅ | `app/(marketing)/terms/page.tsx` + `/legal/terms` |
| `/roadmap` | ✅ | `app/(marketing)/roadmap/page.tsx` |
| `/changelog` | ✅ | `app/(marketing)/changelog/page.tsx` |
| `/customer` | ❌ MISSING | No `/customer` route (customer portal is at `/portal/account`) |
| `/account` | ✅ | `app/portal/account/page.tsx` |
| `/api-keys` | ✅ | `app/portal/api-keys/page.tsx` |
| `/billing` | ✅ | `app/portal/billing/page.tsx` |

### 2.3 Source frontend route audit (FAIL)

The source frontend at `download/mastery-engine/frontend/` has severe structural issues:
- **Missing `lib/` directory** — 186 imports across 124 files reference `@/lib/*` modules that don't exist
- **8 sets of duplicate routes** from route group misuse (`/`, `/dashboard`, `/security`, `/notifications`, `/billing`, `/search`, `/analytics`, `/subjects`, `/subjects/[subjectId]`)
- **`/login` page missing** — middleware redirects to `/login` which 404s
- **`/admin` index missing** — `(admin)` route group doesn't prefix URL
- **`/content` index missing** — same reason
- **13 `/docs/*` pages missing** — only 3 exist
- **`/privacy` and `/terms` missing** — only at `/legal/privacy` and `/legal/terms`
- **`next.config.js` lacks `output: 'standalone'`** — Railway build would fail

### 2.4 Middleware audit (deployed)

**File:** `/home/z/my-project/middleware.ts`

- ✅ `PUBLIC_ROUTES` correctly lists 14 unauthenticated paths
- ✅ `PUBLIC_PREFIXES` covers 19 public prefix paths
- ❌ **CRITICAL: `mastery-role` cookie is never set by the login page** — middleware admin check (`if (role !== 'administrator' && role !== 'system_admin')`) always redirects to `/forbidden`. **All admin routes are inaccessible to everyone, including legitimate admins.**
- ⚠️ `mastery-authenticated` cookie has no `Secure`, `HttpOnly`, or `SameSite` attributes — forgeable via XSS
- ⚠️ Middleware checks cookie presence, not actual token validity — UX convenience only, not real authz

### 2.5 `next.config.js` audit (deployed)

- ✅ `output: 'standalone'` is set (line 5)
- ✅ `reactStrictMode: false`, `poweredByHeader: false`
- ⚠️ `typescript.ignoreBuildErrors: true` — masks TypeScript errors at build time
- ✅ `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_NAME`, `NEXT_PUBLIC_SITE_URL` exposed
- ✅ Rewrites: `/api/:path*` → `${NEXT_PUBLIC_API_URL}/api/:path*`
- ⚠️ No rewrites for `/openapi.json`, `/redoc`, `/openapi.yaml` — API explorer links to these will 404

### 2.6 Root layout audit (deployed)

- ✅ `<html lang="en">` with `suppressHydrationWarning`
- ✅ Fonts: Inter + JetBrains Mono via `next/font/google`
- ✅ Comprehensive metadata: title template, description, openGraph, twitter, manifest, icons, robots, canonical, viewport
- ✅ `metadataBase` set from `NEXT_PUBLIC_SITE_URL`
- ✅ Providers wrapper from `@/providers`

### 2.7 Duplicate config files (deployed)

| Config | Status |
|---|---|
| `next.config.js` + `next.config.ts` | ⚠️ Both exist — Next.js loads `.ts` first; `.ts` lacks rewrites/env config |
| `tailwind.config.js` + `tailwind.config.ts` | ⚠️ Both exist — v3 syntax on Tailwind v4 install |
| `postcss.config.js` + `postcss.config.mjs` | ⚠️ Both exist — `.mjs` loaded first |
| `tsconfig.json` | ✅ Single file |

---

## PASS 3 — DOCUMENTATION AUDIT  ⚠️ WARN

### 3.1 Documentation inventory

**Total:** 153 markdown files · **~55,876 words** combined across 13 subfolders.

| Subfolder | Files | Words | Notes |
|---|---|---|---|
| `ai/` | 23 | ~1,100 | README + 22 stubs (21 words each) |
| `application/` | 6 | 2,278 | Full content |
| `background-processing/` | 10 | 6,260 | Full content |
| `beta/` | 10 | 16,254 | Full content, no README |
| `brand/` | 1 | 1,017 | Brand guidelines only, no README |
| `domain-model/` | 6 | 4,283 | Full content |
| `frontend/` | 40 | mixed | README + 10 full + 27 stubs |
| `infrastructure/` | 7 | 2,902 | Full content |
| `notifications/` | 1 | 250 | README only |
| `operations/` | 13 | ~900 | README + 12 stubs (19 words each) |
| `security/` | 1 | 1,121 | Comprehensive README |
| `vertical-slices/` | 5 | 7,471 | Full content, no README |
| Root | 2 | 980 | CONTRIBUTING + DEVELOPMENT |

### 3.2 Issues

- **No root `docs/README.md` index** — users entering `/docs/` filesystem have no entry point
- **4 of 13 subfolders lack a README** (`beta/`, `brand/`, `notifications/` has only README, `vertical-slices/`)
- **64 stub docs (16-21 words each)** in `ai/`, `frontend/admin/`, `frontend/production/`, `operations/` — each links back to its README, but the README links *to* the stub as if it were real content
- **6 broken CONTRIBUTING.md links**: `docs/mastery-engine-architecture-spec.md`, `docs/domain/ubiquitous-language.md`, `docs/adr/`, `docs/api/`, `docs/database/`, `docs/domain-behavior/`

---

## PASS 4 — COMPONENT AUDIT  ✅ PASS (deployed) / 🔴 FAIL (source)

### 4.1 Component inventory (45 files, deployed)

| Subfolder | Count | Status |
|---|---|---|
| `components/ui/` | 26 | ✅ All shadcn primitives present (alert, avatar, badge, breadcrumb, button, card, checkbox, dialog, dropdown-menu, empty-state, error-state, input, label, pagination, progress, radio-group, select, separator, sheet, skeleton, spinner, switch, tabs, textarea, toaster, tooltip) |
| `components/layout/` | 8 | ✅ app-layout, auth-layout, header, notification-menu, profile-menu, public-layout, route-protection, sidebar, theme-toggle |
| `components/forms/` | 2 | ✅ form, password-strength-meter |
| `components/learner/` | 3 | ✅ dashboard-widgets, question-renderer, question-types |
| `components/beta/` | 2 | ✅ beta-banner, feedback-button |
| `components/charts/` | 1 | ✅ index (TrendChart, ActivityBarChart, MasteryDonut, Sparkline) |
| `components/production/` | 1 | ✅ offline-banner |

### 4.2 Import resolution (deployed)

- ✅ All `@/lib/*` imports resolve (lib/ has 19 files)
- ✅ All `@/components/*` imports resolve
- ✅ All `@/hooks/*` imports resolve (10 hook files)
- ✅ All `@/providers/*` imports resolve (5 provider files)
- ✅ All `@/stores/*` imports resolve (3 store files)
- ✅ All `@/types/*` imports resolve (5 type files)
- ✅ No circular imports detected
- ✅ All 27 external packages used are in package.json

### 4.3 Source frontend issues (FAIL)

- ❌ All 26 UI primitives import `@/lib/cn` which doesn't exist
- ❌ All layout components import `@/lib/constants` (ROUTES) which doesn't exist
- ❌ auth-provider imports `@/lib/api-client` which doesn't exist
- ❌ production-providers imports 4 missing `@/lib/realtime/*`, `@/lib/offline/*`, `@/lib/production/*` modules
- ❌ `types/learning.ts` has TypeScript errors: `int` (not a TS type) on lines 233-234, duplicate `DashboardData` interface on lines 252-265

---

## PASS 5 — API AUDIT  🔴 FAIL

### 5.1 Frontend API client (deployed)

**File:** `/home/z/my-project/lib/api-client.ts` (well-structured, 350+ lines)

- ✅ Axios instance with base URL + JSON content type
- ✅ Request interceptor: Authorization header + correlation ID + idempotency key
- ✅ Response interceptor: error normalization
- ✅ 401 interceptor: automatic token refresh + retry
- ✅ Token storage abstraction (SSR-safe)
- ✅ Pagination helpers
- ✅ File upload support

### 5.2 API endpoint coverage

**authApi methods (lib/api-client.ts):**
- `register`, `login`, `refresh`, `logout`, `logoutAll`
- `verifyEmail`, `resendVerification`, `forgotPassword`, `resetPassword`, `changePassword`
- `mfaSetup`, `mfaVerify`, `mfaEnable`, `mfaDisable`, `mfaRecovery`

**userApi methods:** `getMe`, `updateMe`, `getSecurityInfo`

**Specialized API clients:**
- `lib/admin-api.ts` — admin endpoints
- `lib/content-api.ts` — content management endpoints
- `lib/learner-api.ts` — learner endpoints
- `lib/beta-ops-api.ts` — beta operations endpoints

### 5.3 Backend endpoint inventory

**9 routers mounted in `main.py`** at `/api/v1` prefix:

| Router | Prefix | Endpoints | Auth |
|---|---|---|---|
| health | `/health` | 3 (live, ready, live-alias) | None |
| auth | `/auth` | 15 (register, login, refresh, logout, logout-all, verify-email, resend-verification, forgot-password, reset-password, change-password, mfa-setup, mfa-verify, mfa-enable, mfa-disable, mfa-recovery) | Mixed |
| users | `/users` | 3 (me, update-me, security) | `get_current_user_id` |
| learning | (no prefix) | 4 (enrollments, learning-goals, study-sessions, adaptive-queue) | `get_current_user_id` |
| questions | `/questions` | 3 (get, submit, dashboard) | `get_current_user_id` |
| content_admin | `/admin` | 11 (subjects, concepts, objectives, misconceptions, templates CRUD) | `get_current_user_id` ⚠️ **NO RBAC** |
| admin | `/admin/bg` | 14 (workers, outbox, dead-letters, notifications, jobs) | ❌ **NONE — fully public** |
| beta | (no prefix) | 8 (status, feedback, track, analytics, invites CRUD) | Mixed (admin endpoints protected) |
| beta_ops | `/admin/beta-ops` | 23 (dashboard, funnel, learning, feedback, success, instructor, operations, releases, reports, experiments) | 22 admin-only, 1 open-to-authenticated |

### 5.4 API audit failures

| Severity | Issue | Impact |
|---|---|---|
| 🔴 CRITICAL | **AI router NOT mounted** — `app/presentation/api/v1/ai.py` defines 13 endpoints (`/ai/status`, `/ai/config`, `/ai/explanations/generate`, `/ai/coach/plan`, `/ai/analytics/forecast`, `/ai/content/analyze`, `/ai/recommendations/enhance`, `/ai/reports/weekly`, `/ai/instructor/insights`, `/ai/prompts`, `/ai/prompts/{type}`, `/ai/audit`, `/ai/metrics`) but `main.py` never calls `app.include_router(ai_router)`. **All 13 AI endpoints unreachable.** | Task 023-024 AI platform is non-functional in production |
| 🔴 CRITICAL | **`/api/v1/admin/bg/*` has NO authentication** — 14 endpoints for worker management, outbox replay, dead-letter retry, notification listing, and scheduled job execution are completely public | Anyone can list workers, replay outbox events, retry dead letters, run arbitrary scheduled jobs, pause/resume jobs |
| 🔴 CRITICAL | **`/api/v1/admin/subjects/*`, `/admin/concepts/*`, `/admin/question-templates/*` have NO RBAC** — only `get_current_user_id` required | Any authenticated learner can create/publish subjects, concepts, question templates |
| ⚠️ HIGH | **`/api/v1/questions/api/v1/dashboard` path bug** — `@router.get("/api/v1/dashboard")` inside `/questions`-prefixed router → actual path is `/api/v1/questions/api/v1/dashboard`. Intended `/api/v1/dashboard` is unreachable. All 5 SDKs call `/api/v1/dashboard` and will 404. | Dashboard data unreachable from SDKs |
| ⚠️ HIGH | **`PATCH /ai/config` lacks admin check** — docstring says "admin only" but only requires `get_current_user_id` | Any learner can change AI configuration (if AI router were mounted) |
| ⚠️ MEDIUM | Missing `/health/startup` endpoint (Kubernetes startup probe) | Orchestrators using startup probe won't have a dedicated endpoint |
| ⚠️ MEDIUM | No WebSocket endpoints exist (grep returned zero matches) despite `BusinessMetrics.set_websocket_connections()` gauge being defined | Realtime features (`lib/realtime/websocket-provider.tsx`) have no backend counterpart |

### 5.5 React Query hooks

- ✅ `hooks/use-admin.ts` — admin hooks with proper query keys
- ✅ `hooks/use-content.ts` — content hooks
- ✅ `hooks/use-learner.ts` — learner hooks
- ✅ `hooks/use-beta-ops.ts` — beta ops hooks (22 hooks)
- ✅ `hooks/use-copy-to-clipboard.ts`, `use-debounce.ts`, `use-interval.ts`, `use-local-storage.ts`, `use-media-query.ts`, `use-previous.ts` — utility hooks
- ✅ `lib/query-keys.ts` — centralized query key factory

---

## PASS 6 — BACKEND AUDIT  🔴 FAIL

### 6.1 Routers mounted — WARN (see Pass 5.3-5.4)

9 routers mounted, 1 critical router (AI) NOT mounted.

### 6.2 Dependencies — PASS

All 20+ provider functions in `dependencies.py` and `dependencies_email.py` resolve correctly:
- `get_uow()`, `get_db_session()`, `get_event_publisher()`
- `get_password_service()`, `get_jwt_service()`, `get_mfa_service()`, `get_session_service()`, `get_token_service()`
- `get_auth_service()` (lazy import to avoid cycle)
- `get_current_user_id()`, `get_optional_user_id()`, `get_current_user_claims()`, `get_current_auth_context()`, `get_auth_context`
- `get_authorization_service()`, `require_permission(p)`, `require_role(r)`, `require_any_role(*r)`
- `get_request_ip()`, `get_request_user_agent()`, `get_idempotency_key()`, `create_access_token()`
- `get_email_service()`

### 6.3 Middleware — PASS

5 middleware registered (all files exist):
- `CorrelationMiddleware` — correlation ID propagation
- `CSRFMiddleware` — CSRF protection
- `RateLimitMiddleware` — rate limiting
- `SecurityHeadersMiddleware` — security headers
- `CORSMiddleware` — CORS

### 6.4 Authentication — PASS (with caveats)

| Component | Implementation | Status |
|---|---|---|
| JWT | RS256 (asymmetric), `kid` rotation, rejects HS256, 15m access / 30d refresh, issuer+audience validation, 30s clock skew | ✅ Correct |
| Session | Refresh-token rotation, family-based reuse detection, idle+absolute timeouts, revoke single/all/family | ✅ Correct |
| Password | Argon2id via passlib (OWASP params: memory_cost=19456, time_cost=2, parallelism=1), SHA256 detection + forced rehash | ✅ Correct |
| MFA | TOTP via `pyotp`, ±1 window, 10 recovery codes (16 chars, one-time, constant-time compare) | ⚠️ `pyotp` NOT in pyproject.toml — **ImportError on module load** |
| Authorization | 6 roles, 29 permissions, object-level `require_owner_or_admin` | ✅ Correct (but not enforced on admin.py and content_admin.py routers — see Pass 5.4) |
| Token | SHA-256 hashed, single-use, expiring (24h verify, 15min reset) | ✅ Correct |

### 6.5 Health endpoints — WARN

- ✅ `GET /api/v1/health` (liveness)
- ✅ `GET /api/v1/health/ready` (readiness — DB + Redis probes)
- ✅ `GET /api/v1/health/live` (liveness alias)
- ❌ Missing `/health/startup` (Kubernetes startup probe)

### 6.6 WebSocket routes — FAIL (none exist)

Grep across `backend/` for `@app.websocket`, `WebSocketRoute`, `@router.websocket` returned **zero matches**. The `BusinessMetrics.set_websocket_connections()` gauge exists but is never fed. Frontend has `lib/realtime/websocket-provider.tsx` and `lib/realtime/realtime-sync.tsx` with no backend counterpart.

### 6.7 AI routes & providers — FAIL (router not mounted)

**AI router** (`app/presentation/api/v1/ai.py`) defines 13 endpoints but is **never mounted** in `main.py`. All 13 endpoints unreachable.

**AI providers** (all implemented in `app/ai/providers/__init__.py`, 733 lines):
- `MockProvider` (testing)
- `OllamaProvider` (local LLM via httpx, default `qwen2.5:7b`)
- `OpenAIProvider` (cloud)
- `GeminiProvider` (Google)
- `AnthropicProvider` (Claude)

AI infrastructure packages all exist:
- `app/ai/__init__.py` (480 lines) — `AIConfig`, `AIProvider`, `ProviderRegistry`
- `app/ai/gateway/__init__.py` (425 lines) — `AIGateway` with rate limiter, safety, audit, caching
- `app/ai/safety/__init__.py` (275 lines) — `SafetyValidator`, prompt-injection patterns
- `app/ai/audit/__init__.py` (191 lines) — `AuditLogger`, `AuditEntry`
- `app/ai/prompts/__init__.py` (471 lines) — `PromptRepository`, `PromptType` enum
- `app/ai/explanations/__init__.py` (348 lines) — `ExplanationGenerator`
- `app/ai/coach/__init__.py` (787 lines) — `StudyCoach`, `PredictiveAnalytics`, `ContentIntelligence`

### 6.8 Beta endpoints — PASS

- `beta.py`: 8 endpoints, admin endpoints protected with `RequireAdmin`
- `beta_ops.py`: 23 endpoints, 22 admin-only, 1 open-to-authenticated (vote — by design)

### 6.9 Background workers — FAIL

Files exist (`worker_main.py`, `outbox_dispatcher.py`, `processors.py`, `retry_engine.py`, `host.py`, `metrics.py`, `subscriber_registry.py`) but:

- ❌ **`worker_main.py:37`** imports `from app.workers.scheduler import SchedulerProcessor` — module doesn't exist. `SchedulerProcessor` is in `app/infrastructure/scheduler/processor.py`.
- ❌ **`scripts/railway/startup_worker.py:119`** has the same broken import.
- **Worker will crash-loop on startup.** Railway will retry 10 times then give up.

### 6.10 Configuration — WARN

`Settings` class has all required fields for: app, database, redis, SMTP, JWT, Argon2, token TTLs, session, CORS, feature flags, closed beta, beta flags, sentry.

**Missing from Settings:**
- AI configuration (`ai_enabled`, `ollama_host`, `ollama_model`, `ai_timeout`, `temperature`, etc.) — lives in separate `AIConfig` in `app/ai/__init__.py`, NOT env-driven
- `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` env vars — documented but never read by code

**Unused fields:**
- `jwt_algorithm` (JWTService hardcodes RS256)
- `jwt_access_token_expire_minutes` (JWTService uses constant)
- `jwt_refresh_token_expire_days` (JWTService uses constant)

### 6.11 Circular imports — PASS

No circular imports detected across 59 `__init__.py` files. Notable defensive pattern: `dependencies.py:get_auth_service` uses lazy import for `ProductionAuthService`.

### 6.12 Test count — PASS

- 62 test files under `backend/tests/`
- ~1,919 test functions (`def test_` occurrences minus fixtures)

---

## PASS 7 — DATABASE AUDIT  🔴 FAIL

### 7.1 Migrations — WARN

6 SQL init files under `infrastructure/postgres/init/`:

| File | Tables created |
|---|---|
| `00-base-tables.sql` | 5 (identity.users, user_profiles, user_credentials, sessions, infrastructure.outbox_events) |
| `01-create-schemas.sql` | 0 (creates 10 schemas + extensions) |
| `02-auth-tables.sql` | 7 (verification_tokens, password_reset_tokens, refresh_tokens, mfa_secrets, mfa_recovery_codes, security_incidents, auth_audit_logs) |
| `03-background-tables.sql` | 7 (dead_letter_events, notifications, notification_preferences, scheduled_jobs, worker_heartbeats, email_delivery_log, outbox_leases) |
| `04-beta-tables.sql` | 3 (beta_invites, beta_feedback, beta_events) |
| `05-beta-ops-tables.sql` | 7 (beta_feedback_votes, beta_feedback_meta, release_notes, release_stages, experiments, experiment_assignments, experiment_results) |

**Total: 29 CREATE TABLE statements in migrations.**

### 7.2 Alembic history — FAIL

| Check | Status |
|---|---|
| `backend/alembic.ini` exists | ✅ |
| `backend/alembic/env.py` exists | ✅ |
| `target_metadata = Base.metadata` wired | ✅ |
| All 8 ORM modules imported in env.py | ✅ |
| Async engine support | ✅ |
| **At least one revision in `backend/alembic/versions/`** | ❌ **directory does not exist** |

**Alembic is NOT usable for `alembic upgrade head`.** The command silently succeeds (no-op). `startup_backend.py` falls back to running raw SQL init scripts.

### 7.3 ORM models — PASS

All 8 ORM files exist with 47 total models:
- `base.py` (foundational)
- `identity.py` (4 models)
- `auth.py` (7 models)
- `core.py` (9 models — enrollment, study_session, question_instance, attempt, answer, mastery_score, review, algorithm_version, outbox_event)
- `content.py` (10 models)
- `background.py` (7 models)
- `beta.py` (3 models)
- `beta_ops.py` (7 models)

### 7.4 Table inventory — FAIL (count mismatch)

| Schema | Tables | Claimed |
|---|---|---|
| identity | 15 | ✅ |
| content | 10 | ✅ |
| infrastructure | 6 | ✅ |
| administration | 4 | ✅ |
| analytics | 4 | ✅ |
| mastery | 3 | ✅ |
| assessment | 3 | ✅ |
| learning | 2 | ✅ |
| scheduling | **0** | ❌ Claimed |
| billing | **0** | ❌ Claimed |
| **TOTAL** | **47** | ❌ **Worklog claimed 57** |

### 7.5 Missing tables — FAIL

**18 ORM tables have NO migration CREATE TABLE:**

All 18 tables in `content`, `learning`, `assessment`, and `mastery` schemas:
- content: subjects, concepts, learning_objectives, misconceptions, question_templates, template_versions, template_concepts, explanations, content_versions, content_packs (10)
- learning: learner_enrollments, study_sessions (2)
- assessment: question_instances, attempts, answers (3)
- mastery: mastery_scores, reviews, algorithm_versions (3)

**Production impact:** Queries against `content.subjects`, `learning.study_sessions`, `assessment.attempts`, `mastery.mastery_scores` will fail with `relation does not exist` because the tables are never created. The `verify_schema` check in `startup_backend.py` only checks 4 tables (identity.users, identity.sessions, infrastructure.outbox_events, infrastructure.worker_heartbeats) and won't catch this.

**Tests pass** because `tests/*/conftest.py` calls `Base.metadata.create_all()` on in-memory SQLite.

### 7.6 Foreign keys — PASS

All declared FKs reference valid table+column pairs. Many UUIDs intentionally un-FK'd (cross-aggregate references by ID only — DDD pattern).

### 7.7 Indexes — WARN

- ✅ `users.email` unique partial index (allows re-registration after soft delete)
- ✅ `outbox_events.(status, created_at)` partial index — but doesn't cover lease/retry filters
- ✅ `beta_events.created_at` + type_created + user indexes
- ✅ `auth_audit_logs.(user_id, created_at)` + action_created + correlation indexes
- ✅ Many unique constraints on natural keys (subject code/slug, template version, etc.)
- ⚠️ `sessions.refresh_token_hash` has no index (if any code queries sessions by hash, seq-scan)

### 7.8 Schemas — WARN

All 10 schemas CREATED in `01-create-schemas.sql` but only 8 have tables. `scheduling` and `billing` are empty (DDD domain exists but no persistence).

### 7.9 Outbox pattern — WARN

Table exists with expected columns, but column names differ from spec:
- `dispatch_attempt_count` (not `retry_count`)
- `next_retry_at` (not `next_attempt_at`)
- `dispatched_at` (not `processed_at`)

Additional useful columns: `actor_user_id`, `payload_schema_version`, `last_dispatch_error`, `leased_until`, `leased_by`, `retry_history` (JSONB).

Index doesn't fully cover dispatcher query (lease-expiry + retry-due predicates not covered).

### 7.10 Triggers / functions — PASS

- ✅ `identity.prevent_audit_log_mutation()` trigger function exists
- ✅ `trg_audit_logs_no_update` BEFORE UPDATE trigger on `auth_audit_logs`
- ✅ `trg_audit_logs_no_delete` BEFORE DELETE trigger on `auth_audit_logs`
- ✅ Both triggers drop-if-exists before creation (idempotent)
- ✅ Function is `CREATE OR REPLACE`

### 7.11 Permissions — WARN (GRANT-after-REVOKE bug)

**Critical permission issue in `02-auth-tables.sql`:**

1. Line 211: `REVOKE UPDATE, DELETE ON identity.auth_audit_logs FROM mastery;`
2. Line 252 (41 lines later): `GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA identity TO mastery;`

PostgreSQL `GRANT` is additive — line 252 re-grants UPDATE/DELETE, **silently undoing the REVOKE**. The trigger still enforces immutability at the DB level, but defense-in-depth at the GRANT level is broken.

**Same pattern affects `analytics.beta_events`** (append-only by design):
- `04-beta-tables.sql:90`: `GRANT SELECT, INSERT ON analytics.beta_events` (append-only)
- `05-beta-ops-tables.sql:172`: `GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics` — re-grants UPDATE/DELETE

**No trigger backstop on `beta_events`** — the app role CAN actually UPDATE/DELETE rows, breaking the append-only audit trail.

---

## PASS 8 — RAILWAY DEPLOYMENT AUDIT  ⚠️ WARN

### 8.1 Active deployed Railway config (`/home/z/my-project/railway.json`)

| Key | Value | Verdict |
|---|---|---|
| `build.builder` | `NIXPACKS` | ✅ |
| `build.buildCommand` | `bun run build` | ✅ |
| `deploy.startCommand` | `HOSTNAME=0.0.0.0 node .next/standalone/server.js` | ✅ Binds 0.0.0.0, uses standalone |
| `deploy.healthcheckPath` | `/` | ⚠️ Liveness-only (returns 200 even if backend/DB down) |
| `deploy.healthcheckTimeout` | `180` | ✅ |
| `deploy.restartPolicyType` | `ON_FAILURE` | ✅ |
| `deploy.restartPolicyMaxRetries` | `5` | ✅ |

⚠️ **This deployment is frontend-only.** No backend service, no worker service, no Postgres/Redis plugins referenced. Railway runs only the Next.js app.

### 8.2 Source repo Railway configs

| File | Issue |
|---|---|
| `railway.json` (root) | `startCommand` bypasses `startup_backend.py` — no migrations, no DB-wait |
| `railway/railway.toml` | Frontend `startCommand: "npm start"` — incompatible with standalone |
| `railway/backend/railway.json` | ✅ Correct (uses `startup_backend.py`) |
| `railway/frontend/railway.json` | ❌ `startCommand: "node .next/standalone/server.js"` but source `next.config.js` lacks `output: 'standalone'` |
| `railway/worker/railway.json` | ❌ `startCommand` runs `startup_worker.py` which crashes on broken import |

### 8.3 Dockerfiles

**`infrastructure/docker/backend.Dockerfile`** ✅ PASS
- Multi-stage (builder, builder-dev, runtime)
- Python 3.13-slim
- curl + wget + ca-certificates installed
- Healthcheck: `curl -sf http://localhost:8000/api/v1/health`
- Non-root user `mastery`
- ⚠️ CMD bypasses `startup_backend.py` (no migrations)

**`infrastructure/docker/frontend.Dockerfile`** ⚠️ WARN
- Multi-stage (deps, builder, runtime)
- Node 20-alpine
- Copies `.next/standalone` — but source `next.config.js` lacks `output: 'standalone'`
- Healthcheck: `curl -sf http://localhost:3000/api/v1/health` — couples frontend liveness to backend reachability
- Non-root user `nextjs:nodejs`

### 8.4 Environment variables

**Coverage:** Most variables documented in `.env.example` and `RAILWAY_ENV_VARS.md` are consumed by code.

**Issues:**
- ❌ `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` — documented but **NEVER read by code**
- ⚠️ `AI_ENABLED`, `OLLAMA_HOST`, `OLLAMA_MODEL` — documented but not in `Settings` class
- ⚠️ `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS` — declared in Settings but never read (JWTService uses constants)
- ⚠️ `JWT_SECRET_KEY` — documented as "required" but unused in RS256 mode
- ⚠️ `NEXT_PUBLIC_SITE_URL` — used in code but not in `.env.example`

### 8.5 Health checks

| Service | Path | Exists? | Verdict |
|---|---|---|---|
| Backend | `/api/v1/health` | ✅ | OK |
| Frontend (deployed) | `/` | ✅ | OK (liveness only) |
| Frontend (Dockerfile) | `/api/v1/health` | ⚠️ | Depends on backend rewrite |
| Worker | none | — | OK (no HTTP) |

### 8.6 Next.js standalone

| File | `output: 'standalone'`? | Verdict |
|---|---|---|
| `/home/z/my-project/next.config.js` | ✅ YES | OK — deployed |
| `/home/z/my-project/next.config.ts` | ✅ YES | ⚠️ Loaded first by Next.js; lacks rewrites/env config |
| `download/mastery-engine/frontend/next.config.js` | ❌ **NO** | FAIL — Railway build would fail |

---

## PASS 9 — BUILD AUDIT  ⚠️ WARN

### 9.1 Frontend build (deployed)

- ✅ `package.json` scripts: `dev`, `build`, `start`, `lint`, `typecheck`, `test`
- ✅ `build` script: `"next build && cp -r .next/static .next/standalone/.next/ && cp -r public .next/standalone/"` — correctly handles standalone
- ✅ Build artifact verified: `/home/z/my-project/.next/standalone/server.js` exists
- ✅ All dependencies resolve
- ⚠️ `typescript.ignoreBuildErrors: true` — masks TS errors
- ⚠️ Duplicate Tailwind configs (v3 syntax on v4 install)
- ⚠️ Duplicate PostCSS configs
- ⚠️ Dead `src/` directory (old scaffold)
- **Build prediction: SUCCEEDS** (verified by existing artifact)

### 9.2 Backend build

- ✅ `pyproject.toml`: Python ≥ 3.13
- ✅ All declared dependencies resolve
- ❌ **`pyotp` missing from dependencies** — imported in `mfa_service.py:22`. **ImportError on MFA module load.**
- ⚠️ `cryptography` imported directly but only pulled in transitively via `pyjwt[crypto]`
- ✅ `ruff.toml`, `mypy.ini`, `alembic.ini` exist
- ❌ Alembic `versions/` directory missing
- **Build prediction: `pip install` SUCCEEDS, runtime CRASHES on MFA import**
- **Worker startup: CRASHES** on broken `app.workers.scheduler` import

### 9.3 Docker build

- Backend Dockerfile: ✅ Builds successfully
- Frontend Dockerfile (against source): ❌ Fails (no standalone output)
- Frontend Dockerfile (against deployed): ✅ Should work

### 9.4 Railway (Nixpacks) build

- Deployed root: ✅ Sound pipeline (`bun install` → `bun run build` → `node .next/standalone/server.js`)
- Source backend: ✅ Sound (`pip install -e .` → `startup_backend.py`)
- Source frontend: ❌ Fails (no standalone)
- Source worker: ❌ Crashes on import

---

## PASS 10 — STATIC ASSET AUDIT  ⚠️ WARN

### 10.1 Public asset inventory

| Path | Status |
|---|---|
| `public/favicon.svg` | ✅ (no `.ico` fallback for legacy browsers) |
| `public/manifest.webmanifest` | ✅ |
| `public/robots.txt` | ⚠️ Duplicate of `app/robots.ts` (Next.js serves `app/robots.ts`; static file is dead) |
| `public/brand/logo.svg` | ✅ |
| `public/brand/logo-mark.svg` | ✅ |
| `public/brand/og-image.svg` | ⚠️ SVG format — unsupported by Facebook/Twitter/LinkedIn/Slack/Discord OG scrapers |

### 10.2 Required-asset checklist

| Requirement | Status |
|---|---|
| favicon.ico or favicon.svg | ✅ favicon.svg (no .ico fallback) |
| logo.svg under public/brand/ | ✅ |
| logo-mark.svg under public/brand/ | ✅ |
| og-image (png/jpg) | ❌ SVG only — will not render on social platforms |
| manifest.webmanifest | ✅ Referenced in root layout |
| robots.txt | ✅ Both static + app/robots.ts (duplicate) |
| app/robots.ts | ✅ |
| app/sitemap.ts | ✅ |
| Apple-touch-icon (PNG) | ❌ Not provided (uses SVG — iOS Safari ignores) |
| PNG icons in manifest (192×192, 512×512) | ❌ SVG only — Android Chrome requires PNG |
| Fonts | ✅ Inter + JetBrains Mono via next/font/google |

### 10.3 Manifest issues

- ❌ No PNG icons — Android Chrome and most PWA installers require PNG
- ⚠️ `theme_color` is `#2563EB` but `viewport.themeColor` is `#ffffff`/`#0f172a` — mismatch

---

## PASS 11 — AUTHENTICATION AUDIT  🔴 FAIL

### 11.1 Login page (deployed) — WARN

- ✅ Route exists at `app/(auth)/login/page.tsx`
- ✅ Submits to `/api/v1/auth/login`
- ❌ **Does NOT handle `requires_mfa: true` response** — backend returns `requires_mfa=True` + `mfa_session_token` when MFA enabled; login page treats any non-error response as success. **Users with MFA cannot log in.**
- ❌ **Does NOT store refresh token** — only `localStorage.setItem('mastery-token', data.access_token)`. Refresh-token-based session extension broken.
- ❌ **Does NOT set `mastery-role` cookie** — middleware admin check is dead
- ❌ Cookie security: `document.cookie = 'mastery-authenticated=true; path=/'` — no `Secure`, no `HttpOnly`, no `SameSite`. Forgeable via XSS.
- ⚠️ Uses raw `fetch` instead of typed `authApi.login()` (register page uses authApi)

### 11.2 Register page (deployed) — WARN

- ✅ Route exists, uses typed `authApi.register()`
- ✅ Password strength validation (`strongPasswordSchema`)
- ✅ PasswordStrengthMeter component
- ✅ Terms acceptance checkbox
- ❌ **Does NOT send `invite_token`** — `RegisterRequest` type and `registerSchema` don't include `inviteToken`. **Closed beta registration impossible from frontend.**
- ✅ Error handling for `EMAIL_ALREADY_REGISTERED`, field errors, generic errors

### 11.3 JWT — WARN

- ✅ RS256 (asymmetric), `kid` rotation, rejects HS256
- ✅ Access token (15 min) + Refresh token (opaque, 30 days) distinction
- ✅ Token rotation on refresh with family-based reuse detection
- ✅ Issuer + audience validation, 30s clock skew
- ✅ Token version support (invalidation on password change)
- ❌ **CRITICAL: `get_jwt_service()` doesn't pass `keys_dir=settings.jwt_keys_dir` to `JWTKeyManager`** — keys are always ephemeral. Every process restart invalidates all tokens. Multi-replica deployments break (each replica has different keys).
- ❌ `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` env vars documented but never read — no logic to materialize them into `/app/keys/*.pem` files

### 11.4 Refresh token — PASS

- ✅ `POST /api/v1/auth/refresh` endpoint exists
- ✅ Accepts `RefreshRequest { refresh_token }`
- ✅ Rotation: old token marked consumed, new token issued in same family
- ✅ Reuse detection: revokes entire family + records `SECURITY_INCIDENT` (severity=critical)
- ✅ Frontend `api-client.ts` has automatic 401 → refresh → retry interceptor

### 11.5 MFA — WARN

- ✅ Backend: 5 endpoints (setup, verify, enable, disable, recovery)
- ✅ TOTP per RFC 6238 (pyotp, 6 digits, 30s, ±1 window)
- ✅ Recovery codes: 10 codes, 16 chars, one-time, constant-time compare
- ✅ Frontend pages: `/mfa/setup`, `/mfa/verify`, `/recovery-codes`
- ❌ **`pyotp` NOT in pyproject.toml** — backend crashes on import
- ⚠️ MFA setup page renders QR as placeholder `<div>QR Code (Render in production)</div>` — not scannable
- ⚠️ MFA verify page uses `context='sensitive_action'` not `'login'`
- ❌ Login page doesn't trigger MFA flow

### 11.6 RBAC — FAIL

**6 roles defined:** learner, instructor, content_editor, organization_admin, administrator, system_admin

**29 permissions defined** across identity, learning, content, admin, billing, organization domains.

**RBAC enforcement FAILURES:**

| Router | Protection | Verdict |
|---|---|---|
| `beta.py` admin endpoints | ✅ `RequireAdmin` | OK |
| `beta_ops.py` (22/23 endpoints) | ✅ `RequireAdmin` | OK |
| `admin.py` (`/admin/bg/*`, 14 endpoints) | ❌ **NONE** | **CRITICAL FAIL** |
| `content_admin.py` (`/admin/subjects/*` etc., 11 endpoints) | ⚠️ `get_current_user_id` only | **FAIL** |
| `ai.py` (`/ai/config`, `/ai/audit`, `/ai/metrics`) | ⚠️ `get_current_user_id` only | **FAIL** |
| `users.py` | ✅ `get_current_user_id` + `require_permission` | OK |

### 11.7 Beta invites — WARN

- ✅ `/auth/register` validates invite_token when `CLOSED_BETA_ENABLED=true`
- ✅ Admin invite CRUD endpoints (create, list, delete, resend) — all admin-protected
- ✅ Invite tokens are opaque (`secrets.token_urlsafe(32)`)
- ✅ Single-use (`used_at` set on first use)
- ⚠️ Tokens stored in plaintext (not hashed like refresh tokens) — DB leak = all unused invites compromised
- ❌ Frontend register page doesn't send `invite_token` — closed beta registration impossible from UI

### 11.8 Session management — WARN

- ✅ Logout endpoints (current + all)
- ✅ Session-expired page
- ✅ `api-client.ts` redirects to `/session-expired` when refresh fails
- ⚠️ Middleware checks `mastery-authenticated` cookie presence, not token validity — UX convenience only
- ⚠️ Cookie has no `Secure`/`HttpOnly`/`SameSite` — forgeable
- ⚠️ In-memory `SessionService` class is dead code (real impl uses DB-backed `RefreshTokenRepository`)

### 11.9 Password security — PASS

- ✅ Argon2id with OWASP 2024 params (memory_cost=19456, time_cost=2, parallelism=1)
- ✅ SHA256 format detection + forced rehash
- ✅ `verify_and_upgrade()` rehashes on next login
- ✅ Password reset flow (forgot-password, reset-password — single-use, 15-min TTL, revokes all sessions)
- ✅ Email verification flow (verify-email, resend-verification — single-use, 24h TTL)
- ✅ Frontend password strength validation (≥12 chars + upper + lower + digit + special)
- ⚠️ Backend only checks length (≥12), no complexity — frontend complexity bypassable via direct API call

---

## PASS 12 — BROKEN LINK AUDIT  ⚠️ WARN (deployed)

### 12.1 Deployed frontend broken links

| Source | Target | Reason |
|---|---|---|
| Portal sidebar | `/portal/sessions` | No page file |
| Portal sidebar | `/portal/usage` | No page file |
| Portal sidebar | `/portal/organizations` | No page file |
| Portal sidebar | `/portal/invitations` | No page file |
| API explorer | `/openapi.json` | No rewrite in next.config.js |
| API explorer | `/redoc` | No rewrite |
| API explorer | `/openapi.yaml` | No rewrite |

### 12.2 Source frontend broken links (FAIL)

- 18+ broken internal links (all `/admin/*` and `/content/*` links 404 because route groups don't prefix URLs)
- 12 sitemap URLs return 404 (all `/docs/*` except 3)
- 17 of 19 docs sidebar links broken
- `/login`, `/privacy`, `/terms` linked but missing

---

## PASS 13 — IMPORT AUDIT  ✅ PASS (deployed) / 🔴 FAIL (source)

### 13.1 Deployed frontend — PASS

- ✅ All `@/lib/*` imports resolve (19 files in lib/)
- ✅ All `@/components/*` imports resolve (45 files)
- ✅ All `@/hooks/*` imports resolve (10 files)
- ✅ All `@/providers/*` imports resolve (5 files)
- ✅ All `@/stores/*` imports resolve (3 files)
- ✅ All `@/types/*` imports resolve (5 files)
- ✅ No circular imports
- ✅ All 27 external packages in package.json
- ⚠️ Duplicate config files: `next.config.js` + `.ts`, `tailwind.config.js` + `.ts`, `postcss.config.js` + `.mjs`

### 13.2 Source frontend — FAIL

- ❌ 186 imports across 124 files reference non-existent `@/lib/*` modules
- ❌ 18 distinct `@/lib/*` modules missing (cn, constants, api-client, validations, format, query-keys, admin-api, content-api, learner-api, beta-ops-api, offline/*, production/*, realtime/*, uploads/*, optimistic/*)
- ❌ `types/learning.ts` has TypeScript errors (`int` not a TS type, duplicate interface)

### 13.3 Backend imports — FAIL

- ❌ `app/workers/worker_main.py:37` — `from app.workers.scheduler import SchedulerProcessor` (module doesn't exist)
- ❌ `scripts/railway/startup_worker.py:119` — same broken import
- ❌ `pyotp` imported but not in pyproject.toml

---

## PASS 14 — SEO AUDIT  🔴 FAIL

### 14.1 Metadata coverage

| Page type | metadata export? | Unique title? | Unique description? | OG? | Twitter? | Canonical? |
|---|---|---|---|---|---|---|
| Root layout | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ `/` |
| `(app)/layout.tsx` | ✅ (title only) | ⚠️ | ❌ inherits | ❌ | ❌ | ❌ |
| All marketing pages | ❌ | inherits | inherits | inherits | inherits | ❌ |
| All admin pages | ❌ | inherits | inherits | inherits | inherits | ❌ |
| All learner pages | ❌ | inherits | inherits | inherits | inherits | ❌ |
| All docs pages | ❌ | inherits | inherits | inherits | inherits | ❌ |
| Blog [slug] | ❌ | ❌ hardcoded | ❌ | ❌ | ❌ | ❌ |

**Only 2 of 100+ pages export metadata.** Every marketing page is `'use client'` so cannot export `metadata` — would need server components or `generateMetadata` wrappers.

### 14.2 Structured data (JSON-LD)

**Zero `application/ld+json` scripts found anywhere.** Missing: `Organization`, `WebSite`, `BlogPosting`, `Article`, `BreadcrumbList`, `Product`/`SoftwareApplication`, `FAQPage`.

### 14.3 Canonical URLs

- Root canonical `/` set in `app/layout.tsx`
- **No per-page canonical anywhere** — every page canonicalizes to `/`, treated as duplicate by search engines

### 14.4 OpenGraph images

- Single OG image: `/brand/og-image.svg` (1200×630)
- ⚠️ SVG unsupported by Facebook, Twitter, LinkedIn, Slack, Discord
- ❌ No per-page OG images

### 14.5 Blog [slug] page

- ❌ Does not accept `params` — `BlogPostPage()` with no props
- ❌ No `generateMetadata({ params })`
- ❌ No `generateStaticParams`
- ❌ Renders hardcoded content for "Building an Adaptive Learning Engine" regardless of slug
- ❌ Blog post list hardcoded (9 posts inline) — no MDX/CMS/DB
- ❌ Blog cards on `/blog` not wrapped in `<Link>` — not clickable

### 14.6 Sitemap URL existence

30 URLs declared in `app/sitemap.ts`. **All 30 exist in deployed version** (the 13 `/docs/*` URLs that 404 in source all exist in deployed).

⚠️ However, `robots.ts` disallows `/security` — blocks crawling of public marketing security page (should be indexed).

### 14.7 robots.ts issues

- ⚠️ Disallows `/security` (public marketing page — should be indexed)
- ⚠️ `public/robots.txt` duplicates `app/robots.ts` with differences (missing `/portal` disallow)
- ⚠️ Conflated rules: `/profile`, `/settings`, `/notifications` match authenticated routes but too broad

---

## PASS 15 — PRODUCTION AUDIT (Task 001-028 feature verification)  ⚠️ WARN

| Task | Description | Status | Notes |
|---|---|---|---|
| 001 | Architecture design, ADR | ✅ PASS | `docs/vertical-slices/` has 5 ADR-like docs; architecture is Clean Architecture + DDD |
| 002 | Database (57 tables/10 schemas claimed) | 🔴 FAIL | Actual: 47 tables / 8 schemas with tables; 18 ORM tables have no migration; 2 schemas (scheduling, billing) empty |
| 003 | Domain layer | ✅ PASS | 7 bounded contexts (identity, content, assessment, learning, mastery, scheduling, administration, billing) under `backend/app/domain/` |
| 004 | Application layer | ✅ PASS | Application services + handlers + DTOs under `backend/app/application/` |
| 005 | Infrastructure layer | ✅ PASS | Database, cache, security, events, notifications, queue, scheduler under `backend/app/infrastructure/` |
| 006 | Presentation layer | ✅ PASS | API v1 routers, middleware, dependencies under `backend/app/presentation/` |
| 007 | Vertical slices | ✅ PASS | 5 vertical slice docs; onboarding, learning loop, content system, content integration, production auth |
| 008 | Content domain | ✅ PASS | 10 ORM models in `content.py`; domain entities exist |
| 009 | Learning domain | ✅ PASS | Domain entities + application handlers exist |
| 010 | Assessment domain | ✅ PASS | Question template engine, variable generator, attempt tracking |
| 011 | Mastery domain | ✅ PASS | Mastery calculator, algorithm versioning, review scheduling |
| 012 | Scheduling domain | ⚠️ WARN | Domain exists but no persistence (0 tables in scheduling schema) |
| 013 | Administration domain | ✅ PASS | 4 tables, feature flags, notifications, audit log |
| 014 | Billing domain | ⚠️ WARN | Domain exists but no persistence (0 tables in billing schema) |
| 015 | Production auth (Argon2id, RS256, MFA, RBAC) | 🔴 FAIL | Crypto correct but: `pyotp` missing from deps; JWT keys always ephemeral; admin router unauthenticated; login bypasses MFA; register doesn't send invite_token |
| 016 | Auth flows (register, login, refresh, reset, verify, MFA, RBAC) | 🔴 FAIL | Backend endpoints exist; frontend wiring broken (no MFA handling, no invite_token, no role cookie) |
| 017 | Background processing (outbox, notifications, email, scheduler) | 🔴 FAIL | Code exists but worker startup crashes on broken import |
| 018 | Frontend foundation | ✅ PASS | Next.js 16 + React 19 + Tailwind + shadcn/ui + React Query + Zustand |
| 019 | Learner portal | ✅ PASS | 14 routes under (learner) + learner components |
| 020 | Content authoring | ✅ PASS | 11 routes under content/ + content hooks |
| 021 | Admin portal | ✅ PASS | 27 routes under admin/ + admin hooks |
| 022 | End-to-end integration | ⚠️ WARN | Integration tests exist but several flows broken at runtime |
| 023 | AI platform | 🔴 FAIL | All AI infrastructure exists (providers, gateway, safety, audit, prompts, coach) but **AI router NOT mounted** — 13 endpoints unreachable |
| 024 | Platform hardening (Redis cache, CI/CD, DR) | ✅ PASS | Redis cache, monitoring stack, backup scripts, health checks all present |
| 025 | Closed Beta system | ⚠️ WARN | Backend complete; frontend register page doesn't send invite_token |
| 025-deploy | Deployment fixes (16 fixes) | ⚠️ WARN | Most fixes applied; GRANT-after-REVOKE bug persists; pyotp missing; worker import broken |
| 026 | Beta Ops platform (10 parts) | ✅ PASS | 23 API endpoints, 10 admin pages, 326 tests — all present |
| 027 | Brand, marketing, docs, SDKs, CLI, status, roadmap, changelog, blog, customer portal, support, SEO, assets | ⚠️ WARN | All 15 parts delivered in deployed version; SEO has major gaps (no per-page metadata, no JSON-LD, SVG OG image, hardcoded blog) |
| 028 | Railway native deployment | ✅ PASS | Deployed frontend running on Railway; `railway.json` correct; standalone build working |

**Feature completeness: ~85%** (most features exist but several are broken at runtime)

---

## CONSOLIDATED ISSUE LISTS

### 🔴 CRITICAL ISSUES (Production Blockers)

| # | Issue | Location | Impact |
|---|---|---|---|
| C1 | **AI router NOT mounted** — 13 endpoints unreachable | `backend/app/main.py` | Task 023-024 AI platform non-functional |
| C2 | **`/api/v1/admin/bg/*` endpoints completely unauthenticated** — 14 endpoints public | `backend/app/presentation/api/v1/admin.py` | Anyone can list workers, replay outbox, retry dead letters, run jobs |
| C3 | **Worker startup crashes** — `from app.workers.scheduler import SchedulerProcessor` (module doesn't exist) | `backend/app/workers/worker_main.py:37`, `backend/scripts/railway/startup_worker.py:119` | Background worker service crash-loops; outbox never dispatched; notifications/emails never sent |
| C4 | **`pyotp` missing from pyproject.toml** — ImportError on MFA module load | `backend/pyproject.toml` | Backend crashes on first MFA-related request (or at import if eager) |
| C5 | **18 ORM tables have no migration** — content, learning, assessment, mastery schemas never created | `infrastructure/postgres/init/` (missing 4 SQL files) | Production queries against subjects, concepts, attempts, mastery_scores fail with "relation does not exist" |
| C6 | **JWT keys always ephemeral** — `get_jwt_service()` doesn't pass `keys_dir` | `backend/app/presentation/dependencies.py:124-131` | Every process restart invalidates all tokens; multi-replica deployments break |
| C7 | **`/api/v1/admin/subjects/*`, `/admin/concepts/*`, `/admin/question-templates/*` have no RBAC** | `backend/app/presentation/api/v1/content_admin.py` | Any authenticated learner can create/publish curriculum |
| C8 | **Login page bypasses MFA** — doesn't handle `requires_mfa: true` | `/home/z/my-project/app/(auth)/login/page.tsx` | Users with MFA enabled cannot log in |
| C9 | **Register page doesn't send `invite_token`** | `/home/z/my-project/app/(auth)/register/page.tsx` | Closed beta registration impossible from frontend |
| C10 | **Middleware admin check is dead code** — `mastery-role` cookie never set | `/home/z/my-project/middleware.ts` + login page | All admin routes redirect to `/forbidden` for everyone, including admins |
| C11 | **Source frontend cannot build** — missing `lib/` directory, 8 duplicate route sets, no `/login`, no `output: 'standalone'` | `download/mastery-engine/frontend/` | Source repo is non-functional; deployed version has diverged |
| C12 | **`/api/v1/questions/api/v1/dashboard` path bug** — intended `/api/v1/dashboard` unreachable | `backend/app/presentation/api/v1/questions.py:657` | All 5 SDKs call `/api/v1/dashboard` and will 404 |

### 🟠 HIGH ISSUES

| # | Issue | Location |
|---|---|---|
| H1 | Alembic `versions/` directory missing — `alembic upgrade head` is no-op | `backend/alembic/versions/` |
| H2 | GRANT-after-REVOKE bug — `auth_audit_logs` immutability broken at GRANT level (trigger still works) | `infrastructure/postgres/init/02-auth-tables.sql:211,252` |
| H3 | `analytics.beta_events` is actually mutable — re-granted UPDATE/DELETE, no trigger backstop | `infrastructure/postgres/init/05-beta-ops-tables.sql:172` |
| H4 | `PATCH /ai/config` lacks admin check (if AI router were mounted) | `backend/app/presentation/api/v1/ai.py:141` |
| H5 | 4 broken portal sidebar links (`/portal/sessions`, `/portal/usage`, `/portal/organizations`, `/portal/invitations`) | `app/portal/layout.tsx` |
| H6 | Zero marketing pages export metadata — SEO failure | All marketing pages are `'use client'` |
| H7 | Zero JSON-LD structured data anywhere in codebase | Frontend-wide |
| H8 | Zero per-page canonical URLs — every page canonicalizes to `/` | Frontend-wide |
| H9 | OG image is SVG — unsupported by all major social platforms | `public/brand/og-image.svg` |
| H10 | Blog `[slug]` page is hardcoded — doesn't read params, renders same content for all 9 slugs | `app/(marketing)/blog/[slug]/page.tsx` |
| H11 | AI configuration not in `Settings` class — not env-driven | `backend/app/shared/config.py` vs `app/ai/__init__.py:410` |
| H12 | `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` env vars documented but never read by code | Documentation vs code |
| H13 | Beta invite tokens stored in plaintext (not hashed like refresh tokens) | `backend/app/infrastructure/database/orm/beta.py` |
| H14 | Backend password validation only checks length — no complexity | `backend/app/application/identity/auth_service.py` |
| H15 | `mastery-authenticated` cookie has no `Secure`/`HttpOnly`/`SameSite` — forgeable via XSS | `/home/z/my-project/app/(auth)/login/page.tsx` |
| H16 | Source root `railway.json` startCommand bypasses `startup_backend.py` — no migrations, no DB-wait | `download/mastery-engine/railway.json` |
| H17 | Source frontend `next.config.js` lacks `output: 'standalone'` — Railway build fails | `download/mastery-engine/frontend/next.config.js` |
| H18 | Frontend Dockerfile healthcheck hits `/api/v1/health` — couples frontend liveness to backend | `infrastructure/docker/frontend.Dockerfile` |
| H19 | No WebSocket endpoints exist despite frontend having websocket-provider | `backend/app/` (zero matches) |
| H20 | 64 stub docs (16-21 words each) in ai/, frontend/admin/, frontend/production/, operations/ | `docs/` |

### 🟡 MEDIUM ISSUES

| # | Issue |
|---|---|
| M1 | Missing `/health/startup` endpoint (Kubernetes startup probe) |
| M2 | Outbox dispatcher index doesn't cover lease-expiry + retry-due predicates |
| M3 | 2 of 10 schemas empty (scheduling, billing) — created but no tables |
| M4 | Worklog claims 57 tables, actual is 47 |
| M5 | Duplicate config files: `next.config.js`+`.ts`, `tailwind.config.js`+`.ts`, `postcss.config.js`+`.mjs` |
| M6 | `typescript.ignoreBuildErrors: true` masks TS errors |
| M7 | Dead `src/` directory (old scaffold) |
| M8 | Dead `app/infrastructure/database.py` file coexists with `database/` package |
| M9 | In-memory `SessionService` class is dead code (real impl uses DB-backed repo) |
| M10 | `robots.ts` disallows `/security` (public marketing page should be indexed) |
| M11 | `public/robots.txt` duplicates `app/robots.ts` with differences |
| M12 | Manifest `theme_color` (`#2563EB`) mismatches `viewport.themeColor` (`#ffffff`/`#0f172a`) |
| M13 | No PNG icons in manifest — Android Chrome requires PNG |
| M14 | No apple-touch-icon (iOS Safari ignores SVG) |
| M15 | No favicon.ico fallback for legacy browsers |
| M16 | 6 broken CONTRIBUTING.md links (`docs/mastery-engine-architecture-spec.md`, `docs/domain/ubiquitous-language.md`, `docs/adr/`, `docs/api/`, `docs/database/`, `docs/domain-behavior/`) |
| M17 | No root `docs/README.md` index |
| M18 | 4 of 13 docs subfolders lack README (`beta/`, `brand/`, `notifications/` has only README, `vertical-slices/`) |
| M19 | `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS` settings unused |
| M20 | `JWT_SECRET_KEY` documented as required but unused in RS256 |
| M21 | MFA setup page renders QR as placeholder `<div>` — not scannable |
| M22 | API explorer links to `/openapi.json`, `/redoc`, `/openapi.yaml` — no rewrites |
| M23 | Login page uses raw `fetch` instead of typed `authApi.login()` |
| M24 | Blog cards on `/blog` not wrapped in `<Link>` — not clickable |
| M25 | `PublishIcon` from lucide-react may not exist (2 content pages import it) |

### 🟢 LOW ISSUES

| # | Issue |
|---|---|
| L1 | `workers/__init__.py` docstring references non-existent `scheduler` and `metrics_collector` modules |
| L2 | `dependencies.py:381` has top-level import after `__all__` (style only) |
| L3 | `infrastructure/scheduler/processor.py` imports from `app.workers.host` — architecturally inverted dependency direction |
| L4 | Tailwind config scans `./features/**` and `./lib/**` — features/ doesn't exist |
| L5 | `app/(admin)/layout.tsx` imports `type LucideIcon as LucideIcon2` — unused alias |
| L6 | `app/health/page.tsx` uses Tailwind classes instead of theme tokens (cosmetic) |
| L7 | Domain mismatch in `brand-guidelines.md` — claims `docs.masteryos.com` subdomain (doesn't exist) |
| L8 | `POSTGRES_HOST`/`PORT`/`DB`/`USER`/`PASSWORD` env vars documented but unused (only `DATABASE_URL` read) |
| L9 | `NEXT_PUBLIC_WS_URL` documented but unused in deployed code |

---

## MISSING FILES

| File | Expected location | Impact |
|---|---|---|
| `frontend/lib/` (entire directory) | `download/mastery-engine/frontend/lib/` | Source frontend cannot build (186 imports broken) |
| `app/(auth)/login/page.tsx` | `download/mastery-engine/frontend/app/(auth)/login/` | Source frontend auth flow broken |
| 13 `/docs/*` page.tsx files | `download/mastery-engine/frontend/app/docs/` | Source docs portal incomplete |
| `backend/alembic/versions/` (directory) | `backend/alembic/versions/` | Alembic cannot apply migrations |
| 4 SQL migration files (content, learning, assessment, mastery) | `infrastructure/postgres/init/` | 18 ORM tables never created in production |
| `app/workers/scheduler.py` | `backend/app/workers/` | Worker startup crashes (or fix import to `app.infrastructure.scheduler`) |
| `pyotp` in pyproject.toml | `backend/pyproject.toml` | MFA module crashes on import |
| `apple-touch-icon.png` | `frontend/public/` | iOS Safari no app icon |
| PNG manifest icons (192×192, 512×512) | `frontend/public/` | Android Chrome PWA install fails |
| `og-image.png` | `frontend/public/brand/` | Social platforms can't render OG image |
| `docs/README.md` (root index) | `docs/` | No docs entry point |
| 4 portal pages (sessions, usage, organizations, invitations) | `app/portal/` | Sidebar links 404 |
| `/customer` route | `app/` | Customer portal expectation unmet (customer portal is at `/portal/account`) |

---

## BROKEN ROUTES

| Route | Affected | Reason |
|---|---|---|
| `/api/v1/ai/*` (13 endpoints) | All AI features | Router not mounted in main.py |
| `/api/v1/dashboard` | All SDKs | Path bug (`/questions/api/v1/dashboard`) |
| `/api/v1/admin/bg/*` (14 endpoints) | Security | No authentication (functional but dangerous) |
| `/portal/sessions`, `/portal/usage`, `/portal/organizations`, `/portal/invitations` | Customer portal | No page files |
| `/openapi.json`, `/redoc`, `/openapi.yaml` | API explorer | No rewrites in next.config.js |
| `/docs/*` (13 URLs in source) | Source docs portal | Pages don't exist in source frontend |
| `/login` (in source) | Source auth flow | Page doesn't exist in source frontend |
| `/admin/*`, `/content/*` (in source) | Source admin/content nav | Route groups don't prefix URLs in source |

---

## BROKEN APIs

| API | Issue |
|---|---|
| All 13 `/api/v1/ai/*` endpoints | Router not mounted — unreachable |
| `/api/v1/dashboard` (intended) | Path bug makes it `/api/v1/questions/api/v1/dashboard` |
| `/api/v1/admin/bg/*` (14 endpoints) | Functional but completely unauthenticated — security crisis |
| `/api/v1/admin/subjects/*`, `/admin/concepts/*`, `/admin/question-templates/*` | Functional but no RBAC — any learner can admin content |
| `/api/v1/auth/mfa/*` (5 endpoints) | Will crash — `pyotp` not installed |
| All worker-processed operations (outbox dispatch, notifications, emails, scheduled jobs) | Worker crashes on startup — no background processing occurs |
| All `/api/v1/learning/*` queries against `learning.study_sessions`, etc. | Will fail in production — tables never created by migrations |
| All `/api/v1/admin/subjects/*` queries against `content.subjects`, etc. | Will fail in production — tables never created by migrations |

---

## DELETED COMPONENTS

No components were found deleted from the deployed version. However, the **source repo is missing** the following that exist in deployed:
- Entire `frontend/lib/` directory (19 files)
- `app/(auth)/login/page.tsx`
- 13 `app/docs/*/page.tsx` files
- `app/(marketing)/privacy/page.tsx`, `app/(marketing)/terms/page.tsx`
- `app/admin/page.tsx`, `app/content/page.tsx` (index pages)
- Real folder structure (`admin/`, `content/`, `docs/`, `portal/` instead of route groups)
- `output: 'standalone'` in next.config.js

This suggests the deployed version was built from a different (newer) branch that was never merged back to the source repo.

---

## DELETED PAGES

No pages are deleted from the deployed version. Source repo is missing several pages that exist in deployed (listed above).

---

## DEPLOYMENT BLOCKERS

### Must fix before any production deploy with backend:

1. **C1** — Mount AI router in `main.py`
2. **C2** — Add `RequireAdmin` to all `/api/v1/admin/bg/*` endpoints
3. **C3** — Fix worker import: `from app.infrastructure.scheduler.processor import SchedulerProcessor`
4. **C4** — Add `pyotp>=2.9.0` to `backend/pyproject.toml`
5. **C5** — Create 4 SQL migration files for content/learning/assessment/mastery schemas (18 tables)
6. **C6** — Pass `key_manager=JWTKeyManager(keys_dir=settings.jwt_keys_dir)` in `get_jwt_service()` + materialize `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY` env vars into `/app/keys/*.pem` files
7. **C7** — Add `require_any_role(ROLE_INSTRUCTOR, ROLE_CONTENT_EDITOR, ROLE_ADMINISTRATOR)` to content_admin.py write endpoints
8. **C8** — Update login page to handle `requires_mfa: true` response
9. **C9** — Update register page to read `invite_token` from URL and include in API call
10. **C10** — Set `mastery-role` cookie on login (or move admin authz to server-side check)
11. **C12** — Fix `/api/v1/questions/api/v1/dashboard` path bug

### Must fix before source repo is functional:

12. **C11** — Restore `frontend/lib/` directory, fix duplicate routes, add `/login`, add `output: 'standalone'`

### Current deployed frontend-only state:

The currently deployed Railway app (frontend-only) **does not have these blockers** because:
- No backend is deployed (so C1-C7, C12 don't apply)
- The frontend builds and runs (so C11 doesn't apply)
- C8, C9, C10 affect the deployed frontend but are functional bugs, not deployment blockers

**The deployed frontend will run, but:**
- Users cannot log in if MFA is enabled (C8)
- Users cannot register in closed beta (C9)
- Admins cannot access admin pages (C10)
- No backend API is available (all `/api/v1/*` calls will fail unless a separate backend is deployed)

---

## REGRESSION SUMMARY

| Area | Claimed (worklog) | Actual | Regression? |
|---|---|---|---|
| Backend test count | 1,185 → 1,928 | ~1,919 test functions | ✅ Matches |
| Frontend routes | 111 | 111 | ✅ Matches (deployed) |
| Database tables | 57 | 47 | ❌ 10 tables missing |
| Database schemas with tables | 10 | 8 | ❌ 2 empty |
| Alembic migrations | Wired | versions/ empty | ❌ Not usable |
| AI endpoints | 13 | 13 defined but 0 mounted | ❌ Unreachable |
| Worker | Functional | Crashes on import | ❌ Broken |
| Admin endpoints | Protected | 14 public, 11 no RBAC | ❌ Security regression |
| JWT keys | From env/files | Always ephemeral | ❌ Multi-replica broken |
| MFA | Functional | `pyotp` missing | ❌ Crashes on import |
| Closed beta registration | Functional | Frontend doesn't send invite_token | ❌ Broken |
| Admin login | Functional | Middleware dead code | ❌ Admins can't access |
| Frontend build (source) | Functional | Missing lib/, duplicate routes | ❌ Source broken |
| Frontend build (deployed) | Functional | Builds successfully | ✅ OK |
| Documentation | 153 files | 153 files | ✅ Matches |
| SDKs | 5 | 5 (Python, JS, Go, Java, C#) | ✅ Matches |
| CLI | 9 commands | 9 commands | ✅ Matches |
| SEO | Comprehensive | Major gaps | ❌ Regression |

**Regression count: 11 regressions out of 18 claimed areas (61% regression rate in claimed-vs-actual)**

---

## FEATURE COMPLETENESS PERCENTAGE

| Category | Completeness |
|---|---|
| Project structure | 100% |
| Backend domain/application/infrastructure layers | 95% (scheduling + billing domains have no persistence) |
| Backend API surface | 85% (AI router unmounted, dashboard path bug, admin unauth) |
| Backend security | 60% (admin unauth, content_admin no RBAC, JWT keys ephemeral, pyotp missing) |
| Backend background processing | 40% (worker crashes on startup) |
| Database migrations | 60% (29/47 tables have migrations; Alembic empty) |
| Frontend (deployed) | 90% (login MFA bypass, register no invite_token, admin middleware dead) |
| Frontend (source) | 30% (missing lib/, duplicate routes, missing pages) |
| Documentation | 75% (64 stubs, 6 broken links, no root index) |
| SDKs | 100% (5 SDKs complete) |
| CLI | 100% (9 commands) |
| SEO | 30% (no per-page metadata, no JSON-LD, SVG OG, hardcoded blog) |
| Static assets | 75% (no PNG icons, SVG OG, no apple-touch-icon) |
| Railway deployment (deployed) | 90% (frontend-only, no backend service) |
| Railway deployment (source) | 50% (worker crashes, frontend no standalone, root bypasses startup) |
| Testing | 90% (~1,919 backend tests, frontend tests exist) |

**Overall feature completeness: ~78%**

---

## OVERALL PRODUCTION READINESS SCORE

| Dimension | Score | Weight | Weighted |
|---|---|---|---|
| Functionality (does it work?) | 60/100 | 30% | 18.0 |
| Security (is it safe?) | 40/100 | 25% | 10.0 |
| Reliability (will it stay up?) | 50/100 | 20% | 10.0 |
| Maintainability (can we fix it?) | 70/100 | 15% | 10.5 |
| Deployability (can we ship it?) | 65/100 | 10% | 6.5 |
| **Overall** | | | **55/100** |

### Production Readiness Verdict: **NOT READY FOR PRODUCTION**

The deployed frontend-only Railway app runs, but:
- It has no backend (all API calls fail unless a separate backend is deployed)
- Login is broken for MFA users
- Registration is broken for closed beta
- Admin access is broken for everyone

The full source repo has **12 critical issues** that must be resolved before backend-inclusive production deployment:
- 4 security crises (unauthenticated admin, no RBAC, ephemeral JWT keys, missing pyotp)
- 3 functionality crises (AI router unmounted, worker crashes, 18 tables missing migrations)
- 3 frontend wiring crises (login MFA bypass, register no invite_token, middleware dead)
- 1 path bug (dashboard unreachable from SDKs)
- 1 source/deployed divergence (source frontend non-functional)

**Recommendation:** Do NOT deploy backend-inclusive production until all 12 critical issues are resolved. The currently deployed frontend-only app is a marketing shell — it cannot serve authenticated users.

---

## APPENDIX A — Complete Backend Endpoint Inventory

### Mounted and reachable (84 endpoints)

**Root:** `GET /`

**Health (3):** `GET /api/v1/health`, `/api/v1/health/ready`, `/api/v1/health/live`

**Auth (15):** register, login, refresh, logout, logout-all, verify-email, resend-verification, forgot-password, reset-password, change-password, mfa-setup, mfa-verify, mfa-enable, mfa-disable, mfa-recovery

**Users (3):** me, update-me, security

**Learning (4):** enrollments, learning-goals, study-sessions, adaptive-queue

**Questions (3):** get, submit, dashboard (path-bugged)

**Content Admin (11):** subjects CRUD, concepts, objectives, misconceptions, templates CRUD — ⚠️ no RBAC

**Background Admin (14):** workers, outbox, dead-letters, notifications, jobs — ❌ no auth

**Beta (8):** status, feedback, track, analytics, invites CRUD — ✅ admin-protected

**Beta Ops (23):** dashboard, funnel, retention, learning, feedback, success, instructor, operations, releases, reports, experiments — ✅ 22 admin-protected, 1 open

### Defined but NOT mounted (13 endpoints — AI router)

`/ai/status`, `/ai/config` (PATCH), `/ai/explanations/generate`, `/ai/coach/plan`, `/ai/analytics/forecast`, `/ai/content/analyze`, `/ai/recommendations/enhance`, `/ai/reports/weekly`, `/ai/instructor/insights`, `/ai/prompts`, `/ai/prompts/{type}`, `/ai/audit`, `/ai/metrics`

### WebSocket endpoints: 0

---

## APPENDIX B — Complete Route Inventory (Deployed Frontend)

**111 routes total:**

- **(auth) group (9):** forgot-password, login, mfa/setup, mfa/verify, recovery-codes, register, reset-password, session-expired, verify-email
- **(learner) group (14):** achievements, dashboard, mastery, mastery/[conceptId], notifications, profile, recommendations, reviews, search, settings, settings/security, study/[sessionId], study/[sessionId]/summary, study/start, subjects, subjects/[subjectId], welcome
- **(marketing) group (15):** about, blog, blog/[slug], blog/category/[category], careers, changelog, contact, features, legal/privacy, legal/terms, page (root), pricing, privacy, roadmap, security, terms
- **admin/ folder (27):** analytics, audit, beta-ops (10 sub-routes), billing, dashboard, dead-letters, email, feature-flags, notifications, organizations, outbox, page (index), rbac, scheduler, search, security, system-config, users, users/[userId], workers
- **content/ folder (11):** analytics, dashboard, import-export, page (index), search, subjects, subjects/[subjectId], subjects/create, templates/[templateId], templates/[templateId]/preview, templates/[templateId]/versions, templates/create
- **docs/ folder (15):** administration, api-explorer, authentication, cli, content-authoring, errors, faq, getting-started, installation, learning-engine, page (index), rest-api, sdks, security, troubleshooting, websocket-api
- **portal/ folder (3):** account, api-keys, billing
- **standalone (9):** api-explorer, forbidden, health, maintenance, offline, sdk, status, support, unauthorized

---

## APPENDIX C — Test Inventory

- **Backend:** 62 test files, ~1,919 test functions
  - `tests/auth/` — 11 files (~200 tests)
  - `tests/domain/` — 13 files (~370 tests)
  - `tests/workers/` — 9 files (~170 tests)
  - `tests/beta_ops/` — 7 files (~270 tests)
  - `tests/public_platform/` — 2 files (~283 tests)
  - `tests/ai/` — 1 file (74 tests)
  - `tests/railway/` — 1 file (126 tests)
  - `tests/security/` — 1 file (62 tests)
  - `tests/deployment/` — 1 file (63 tests)
- **Frontend (deployed):** test files under `tests/` (charts, hooks, learner, content, admin, beta, components, forms, integration, sdk, realtime)

---

*End of audit report. No files were modified. Nothing was pushed to GitHub.*
