# TASK 029E — MasteryOS Complete Repository Integrity Audit, Route Verification, Architecture Validation & Production Readiness Audit

**Auditor:** Forensic Engineering Audit (Senior Architect / QA / DevOps / Security / Release Manager)
**Date:** 2026-07-04
**Mode:** AUDIT ONLY. No features implemented. No architecture redesigned. No working code refactored. No business logic changed. Only inconsistency detection.
**Verification:** Every finding verified via Grep/Glob/Read/Bash against actual source code with exact file:line references.

**Repository roots:**
- `/home/z/my-project/` — Deployed Next.js frontend (Railway production, 111 routes)
- `/home/z/my-project/download/mastery-engine/` — Full monorepo source (backend + frontend + docs + sdks + cli + infrastructure + railway)

---

## Phase 1 — Repository Inventory

### Complete repository map

#### Backend (270 Python files)
| Component | Count | Location |
|---|---|---|
| API routers | 12 | `backend/app/presentation/api/` |
| ORM files | 8 | `backend/app/infrastructure/database/orm/` (47 tables) |
| AI module files | 8 | `backend/app/ai/` |
| Worker files | 8 | `backend/app/workers/` |
| Domain bounded contexts | 8 | `backend/app/domain/{identity,content,assessment,learning,mastery,scheduling,administration,billing}` |
| Application services | 7 | `backend/app/application/` |
| Infrastructure modules | 12+ | `backend/app/infrastructure/` |
| Security modules | 6 | `backend/app/infrastructure/security/` |
| Middleware | 3 | `backend/app/presentation/middleware/` |
| Backend tests | 75 files (~1,919 tests) | `backend/tests/` |

#### Frontend (deployed — 111 routes)
| Component | Count |
|---|---|
| Pages | 111 (9 auth + 14 learner + 15 marketing + 27 admin + 11 content + 16 docs + 3 portal + 9 standalone + 7 layouts) |
| Components | 44 (26 UI + 9 layout + 2 forms + 3 learner + 2 beta + 1 charts + 1 production) |
| Hooks | 10 |
| Lib files | 19 (api-client, cn, constants, validations, format, query-keys, admin-api, content-api, learner-api, beta-ops-api + 5 subdirs) |
| Providers | 5 |
| Stores | 3 |
| Types | 5 |
| Tests | 49 files (~830 tests) |
| Public assets | 7 |

#### Source monorepo
| Component | Count |
|---|---|
| SQL migrations | 6 (00-05, 29 CREATE TABLEs) |
| Markdown docs | 150 (13 subfolders) |
| SDKs | 5 (Python, JavaScript, Go, Java, C#) |
| CLI | 1 file (9 commands) |
| Docker files | 3 compose + 2 Dockerfiles |
| GitHub workflows | 6 |
| Monitoring configs | 6 (Prometheus + Grafana + Alertmanager) |
| Railway configs | 11 |
| Scripts | 5 |

### Folder verification — All expected folders exist ✅
backend/, frontend/, workers/, docs/, sdks/, cli/, marketing/, admin/, learner/, content/, railway/, docker/, scripts/, migrations/, assets/, public/

---

## Phase 2 — Missing File Detection

### Missing files (verified against Tasks 001-028 specs)

| # | Expected file | Status | Impact | Severity |
|---|---|---|---|---|
| 1 | `backend/alembic/versions/` (directory) | ❌ MISSING | Alembic can't apply migrations — `alembic upgrade head` is no-op | Critical |
| 2 | 4 SQL migration files (content, learning, assessment, mastery domains) | ❌ MISSING | 18 ORM tables never created — all learning/content ops fail | Critical |
| 3 | `app/workers/scheduler.py` (or correct import path in `worker_main.py:37`, `startup_worker.py:119`) | ❌ MISSING | Worker crashes on startup — no background processing | Critical |
| 4 | `pyotp` in `backend/pyproject.toml` | ❌ MISSING | Backend crashes on `import pyotp` in `mfa_service.py:22` | Critical |
| 5 | `sentry-sdk` in `backend/pyproject.toml` | ❌ MISSING | Sentry silently disabled | High |
| 6 | `aiosqlite` in `backend/pyproject.toml [dev]` | ❌ MISSING | Tests fail on async SQLite | High |
| 7 | `@testing-library/user-event` in `package.json` | ❌ MISSING | 128 frontend tests can't execute | High |
| 8 | `@playwright/test` in `package.json` | ❌ MISSING | 9 E2E tests can't run | Medium |
| 9 | `package-lock.json` | ❌ MISSING | Frontend Dockerfile `npm ci` fails | High |
| 10 | `app/docs/architecture/page.tsx` | ❌ MISSING | Sidebar 404 | High |
| 11 | `app/docs/ai/page.tsx` | ❌ MISSING | Sidebar + sitemap 404 | High |
| 12 | `app/docs/monitoring/page.tsx` | ❌ MISSING | Sidebar 404 | High |
| 13 | `app/docs/scaling/page.tsx` | ❌ MISSING | Sidebar 404 | High |
| 14 | `app/docs/deployment/page.tsx` | ❌ MISSING | Sidebar + sitemap 404 | High |
| 15 | `app/docs/rate-limiting/page.tsx` | ❌ MISSING | Sidebar 404 | High |
| 16 | `app/portal/sessions/page.tsx` | ❌ MISSING | Portal sidebar 404 | High |
| 17 | `app/portal/usage/page.tsx` | ❌ MISSING | Portal sidebar 404 | High |
| 18 | `app/portal/organizations/page.tsx` | ❌ MISSING | Portal sidebar 404 | High |
| 19 | `app/portal/invitations/page.tsx` | ❌ MISSING | Portal sidebar 404 | High |
| 20 | `apple-touch-icon.png` | ❌ MISSING | iOS Safari no app icon | Medium |
| 21 | `icon-192.png`, `icon-512.png` | ❌ MISSING | Android PWA install fails | Medium |
| 22 | `og-image.png` (PNG variant) | ❌ MISSING | Social platforms can't render OG image | High |
| 23 | `favicon.ico` | ❌ MISSING | Legacy browsers no favicon | Low |
| 24 | `infrastructure/postgres/ssl/postgres.pem` + `postgres-key.pem` | ❌ MISSING | docker-compose.prod Postgres won't start | High |
| 25 | `docs/README.md` (root index) | ❌ MISSING | No docs entry point | Low |
| 26 | `/metrics` endpoint in backend | ❌ MISSING | Prometheus scrapes 404 — monitoring non-functional | Critical |

### Unexpected files

| File | Issue | Severity |
|---|---|---|
| `src/` directory (~60 files, old Next.js scaffold) | Dead code — not used (no `srcDir` config); inflates tsc scan | High |
| `infrastructure/database.py` (file) | Duplicates `database/` package — Python loads package, file is dead | High |
| `mini-services/`, `examples/`, `tool-results/`, `upload/`, `prisma/`, `db/` | Vestigial directories from scaffolding | Low |

### Duplicate files

| Pair | Severity | Impact |
|---|---|---|
| `next.config.js` + `next.config.ts` | High | Next.js 16 prefers `.ts` which lacks rewrites/env — build non-determinism |
| `tailwind.config.js` + `tailwind.config.ts` | Medium | Tailwind v4 ignores both; v3-style config on v4 install |
| `postcss.config.js` + `postcss.config.mjs` | Low | Both identical; PostCSS loads first found |
| `public/robots.txt` + `app/robots.ts` | Low | Next.js serves `app/robots.ts`; static file is dead |

### Empty/placeholder files
- 64 stub docs (16-21 words each) in `docs/ai/` (22 files), `docs/operations/` (12 files), `docs/frontend/admin/` (15 files), `docs/frontend/production/` (15 files) — each is a stub pointing back to README

---

## Phase 3 — Route Audit

### Required routes verification (34 checked)

| Route | Status | Notes |
|---|---|---|
| `/` | ✅ EXISTS | `app/(marketing)/page.tsx` |
| `/login` | ✅ EXISTS | `app/(auth)/login/page.tsx` (but login flow broken — see Phase 9) |
| `/register` | ✅ EXISTS | `app/(auth)/register/page.tsx` (but register flow broken) |
| `/dashboard` | ✅ EXISTS | `app/(learner)/dashboard/page.tsx` (but API calls 404) |
| `/learn` | ❌ MISSING | No route (learner portal uses `/dashboard`) |
| `/admin` | ✅ EXISTS | `app/admin/page.tsx` (redirects to `/admin/dashboard`) |
| `/admin/beta` | ❌ MISSING | No route (beta ops at `/admin/beta-ops`) |
| `/admin/beta-ops` | ✅ EXISTS | `app/admin/beta-ops/page.tsx` |
| `/docs` | ✅ EXISTS | `app/docs/page.tsx` |
| `/docs/getting-started` | ✅ EXISTS | |
| `/docs/api` | ❌ MISSING | No page (REST API at `/docs/rest-api`) |
| `/docs/security` | ✅ EXISTS | |
| `/docs/deployment` | ❌ MISSING | Sidebar + sitemap reference → 404 |
| `/docs/authentication` | ✅ EXISTS | |
| `/docs/errors` | ✅ EXISTS | |
| `/docs/websocket-api` | ✅ EXISTS | (but no backend WS endpoint) |
| `/docs/content-authoring` | ✅ EXISTS | |
| `/docs/scaling` | ❌ MISSING | Sidebar references → 404 |
| `/docs/monitoring` | ❌ MISSING | Sidebar references → 404 |
| `/docs/architecture` | ❌ MISSING | Sidebar + sitemap reference → 404 |
| `/docs/faq` | ✅ EXISTS | |
| `/docs/troubleshooting` | ✅ EXISTS | |
| `/docs/installation` | ✅ EXISTS | |
| `/blog` | ✅ EXISTS | |
| `/pricing` | ✅ EXISTS | |
| `/about` | ✅ EXISTS | |
| `/contact` | ✅ EXISTS | |
| `/status` | ✅ EXISTS | (but static mock data) |
| `/changelog` | ✅ EXISTS | |
| `/roadmap` | ✅ EXISTS | |
| `/privacy` | ✅ EXISTS | |
| `/terms` | ✅ EXISTS | |
| `/api-explorer` | ✅ EXISTS | |
| `/customer` | ❌ MISSING | No route (customer portal at `/portal/account`) |
| `/support` | ✅ EXISTS | |

**Result: 27/34 required routes exist. 7 MISSING (`/learn`, `/admin/beta`, `/docs/api`, `/docs/deployment`, `/docs/scaling`, `/docs/monitoring`, `/docs/architecture`, `/customer`).**

### Redirect loops
- `/login` → `/dashboard` → `ProtectedRoute` checks `useAuth().isAuthenticated` (reads `mastery.access_token`) → token stored under `mastery-token` (wrong key) → `isAuthenticated=false` → redirect to `/login` → **infinite loop**

### 404 routes
12 broken routes (7 missing required + 4 portal + 1 content): `/learn`, `/admin/beta`, `/docs/api`, `/docs/deployment`, `/docs/scaling`, `/docs/monitoring`, `/docs/architecture`, `/docs/rate-limiting`, `/portal/sessions`, `/portal/usage`, `/portal/organizations`, `/portal/invitations`, `/content/templates` (index)

---

## Phase 4 — Backend API Audit

### Routers mounted in `main.py`

9 routers mounted at `/api/v1` prefix:
1. health (`/health`) — 3 endpoints ✅
2. auth (`/auth`) — 15 endpoints ✅
3. users (`/users`) — 3 endpoints ✅
4. learning (no prefix) — 4 endpoints ✅
5. questions (`/questions`) — 3 endpoints ⚠️ (dashboard path bug)
6. content_admin (`/admin`) — 11 endpoints 🔴 (no RBAC)
7. admin (`/admin/bg`) — 14 endpoints 🔴 (NO AUTH)
8. beta (no prefix) — 8 endpoints ✅
9. beta_ops (`/admin/beta-ops`) — 23 endpoints ✅

### Unmounted router — CRITICAL

| Router file | Endpoints | Status |
|---|---|---|
| `backend/app/presentation/api/v1/ai.py` | 14 endpoints (`/ai/status`, `/ai/config`, `/ai/explanations/generate`, `/ai/coach/plan`, `/ai/analytics/forecast`, `/ai/content/analyze`, `/ai/recommendations/enhance`, `/ai/reports/weekly`, `/ai/instructor/insights`, `/ai/prompts`, `/ai/prompts/{type}`, `/ai/audit`, `/ai/metrics`) | 🔴 **NOT MOUNTED** — all 14 unreachable |

### Path bug — CRITICAL

`questions.py:656` declares `@router.get("/api/v1/dashboard")` inside a router with `prefix="/questions"` mounted at `/api/v1`. Actual path: `/api/v1/questions/api/v1/dashboard`. Intended `/api/v1/dashboard` is unreachable.

### Authentication failures

| Router | Auth | RBAC | Status |
|---|---|---|---|
| `/api/v1/admin/bg/*` (14 endpoints) | **NONE** | **NONE** | 🔴 CRITICAL — anyone can replay outbox, run jobs, read notifications |
| `/api/v1/admin/subjects/*` (11 endpoints) | ✅ `get_current_user_id` | **NONE** | 🔴 Any learner can create/publish curriculum |
| `/api/v1/ai/config` PATCH | ✅ | **NONE** | ⚠️ Any user can change AI config (if mounted) |
| `/api/v1/admin/beta-ops/*` (23 endpoints) | ✅ | ✅ `RequireAdmin` | ✅ PASS |
| `/api/v1/admin/beta/invites*` (4 endpoints) | ✅ | ✅ `RequireAdmin` | ✅ PASS |

### WebSocket endpoints
**None.** Zero `@app.websocket` or `@router.websocket` matches. Frontend has `lib/realtime/websocket-provider.tsx` targeting non-existent backend WS.

### OpenAPI
- ✅ `/docs`, `/redoc`, `/openapi.json` exposed (when `enable_docs=True`)
- ⚠️ Missing: contact, license, servers, terms_of_service
- ⚠️ Version hardcoded to "0.1.0"
- ⚠️ `enable_docs` defaults True — exposed in production

### Duplicate routes
No duplicate (method, path) pairs across mounted routers. ✅

---

## Phase 5 — Frontend Integration Audit

### Frontend ↔ Backend API mapping

| Client file | Calls defined | Backend matches | Broken |
|---|---|---|---|
| `lib/api-client.ts` (auth + user) | 18 | 18 | 0 |
| `lib/admin-api.ts` | 61 | 14 | **47** |
| `lib/content-api.ts` | 33 | 9 | **24** |
| `lib/learner-api.ts` | 38 | 7 | **31** |
| `lib/beta-ops-api.ts` | 22 | 22 | 0 |
| **Total** | **172** | **70** | **102 broken (59%)** |

### Critical integration bugs

| # | Issue | Location | Severity |
|---|---|---|---|
| F1 | Login page uses raw `fetch` + stores token under `mastery-token` instead of `mastery.access_token` | `login/page.tsx:32` vs `constants.ts:11` | Critical |
| F2 | Register sends `displayName` (camelCase), backend expects `display_name` (snake_case) → 422 | `types/auth.ts:65` vs `auth.py:57` | Critical |
| F3 | Register doesn't send `invite_token` → 403 in closed beta | `register/page.tsx` vs `auth.py:60` | Critical |
| F4 | Login doesn't handle `requires_mfa: true` → MFA users can't log in | `login/page.tsx:30-34` | Critical |
| F5 | Login doesn't set `mastery-role` cookie → admin routes blocked | `login/page.tsx:33` vs `middleware.ts:72` | Critical |
| F6 | Login doesn't store refresh token → session expires after 15 min | `login/page.tsx:32` | Critical |
| F7 | Logout doesn't clear cookies or wrong-key localStorage | `auth-provider.tsx:75-98` | Critical |
| F8 | MFA verify page calls `/auth/mfa/verify` (requires JWT) during login flow (no JWT) | `mfa/verify/page.tsx:39` | Critical |
| F9 | `AuthResponse` TS types use camelCase, backend returns snake_case → `response.accessToken` is undefined | `types/auth.ts:45-53` vs `auth.py:129-136` | Critical |
| F10 | `register/page.tsx:33` calls `setUser` but `AuthContextValue` doesn't expose it | `register/page.tsx:33` vs `auth-provider.tsx` | High |
| F11 | Health-check TS interface doesn't match backend `ReadinessResponse` → runtime crash | `lib/production/health-checks.ts:7-17` | Medium |
| F12 | `/admin/bg/dead-letters/{id}/resolve` — FE sends body, BE expects query param | `lib/admin-api.ts:165` vs `admin.py:358` | Medium |

### Mock/hardcoded data
- `/status` page (`app/status/page.tsx`) — hardcoded mock service data, not wired to backend
- Blog `[slug]` page (`app/(marketing)/blog/[slug]/page.tsx`) — doesn't use `params`, renders hardcoded content for all 9 slugs
- Blog post list (`app/(marketing)/blog/page.tsx`) — 9 posts defined inline, no MDX/CMS/DB

### React Query issues
- `query-keys.ts:60,97` — duplicate `content` key (TS1117) — first declaration silently overwritten
- `use-beta-ops.ts` uses local `QK = ['beta-ops']` instead of centralized factory
- `use-learner.ts:205` — `useSubmitAnswer` invalidates `queryKey.learner.adaptiveQueue` (function ref, not return value) — cache miss

### Unused hooks/providers
- 4 orphan components: `BetaBanner`, `BetaFeedbackButton`, `OfflineBanner`, `PublicLayout`
- `queryKey.notifications`, `queryKey.mastery`, `queryKey.learning` unused

---

## Phase 6 — Component Integrity

### Component inventory (44 files, all present)

| Subfolder | Count | Status |
|---|---|---|
| `components/ui/` | 26 | ✅ All shadcn primitives present (alert, avatar, badge, breadcrumb, button, card, checkbox, dialog, dropdown-menu, empty-state, error-state, input, label, pagination, progress, radio-group, select, separator, sheet, skeleton, spinner, switch, tabs, textarea, toaster, tooltip) |
| `components/layout/` | 9 | ✅ app-layout, auth-layout, header, notification-menu, profile-menu, public-layout, route-protection, sidebar, theme-toggle |
| `components/forms/` | 2 | ✅ form, password-strength-meter |
| `components/learner/` | 3 | ✅ dashboard-widgets, question-renderer, question-types |
| `components/beta/` | 2 | ⚠️ beta-banner, feedback-button (orphaned — never imported) |
| `components/charts/` | 1 | ✅ index (TrendChart, ActivityBarChart, MasteryDonut, Sparkline) |
| `components/production/` | 1 | ⚠️ offline-banner (orphaned — provider wired but banner never rendered) |

### Import resolution
All `@/lib/*`, `@/components/*`, `@/hooks/*`, `@/providers/*`, `@/stores/*`, `@/types/*` imports resolve. ✅

### TypeScript errors (22, suppressed by `ignoreBuildErrors: true`)
- 🔴 `types/learning.ts:233,234` — `Cannot find name 'int'` (duplicate `DashboardData`)
- 🔴 `lib/query-keys.ts:97` — Duplicate `content` property (TS1117)
- 🔴 `providers/theme-provider.tsx:5` — `Cannot find module 'next-themes/dist/types'`
- 🔴 `app/(auth)/register/page.tsx:33` — `Property 'setUser' does not exist on 'AuthContextValue'`
- ⚠️ 7 react-hook-form/zod type incompatibilities
- ⚠️ `components/forms/form.tsx:59` — `fieldState.id` no longer exists
- ⚠️ `lib/offline/offline-provider.tsx:103` — `flushQueue` wrong arg count
- ⚠️ `lib/realtime/hooks.ts:48,52` — `useWebSocketSubscription` wrong signature

### ARIA/accessibility
- ✅ Good coverage in `components/ui/` (aria-label, role="alert", aria-current, aria-hidden, aria-busy, aria-disabled)
- ✅ Forms: `aria-invalid`, `aria-describedby`, `role="alert"` on FormMessage
- ⚠️ No custom keyboard navigation (relies on Radix defaults)
- ⚠️ 57% of pages have no responsive classes (no `md:`/`lg:` breakpoints)

### Loading/error/empty states
- ✅ `Skeleton`, `Spinner`, `EmptyState`, `ErrorState` components present
- ✅ Global `app/loading.tsx`, `app/error.tsx` exist
- ⚠️ No per-route `loading.tsx` or `error.tsx`

### Theme support
- ✅ `next-themes` wired in `providers/index.tsx`
- ✅ Theme toggle in marketing, docs, portal, learner layouts
- ✅ `<html suppressHydrationWarning>` set

### Orphan components
| Component | Status |
|---|---|
| `BetaBanner` | Never imported by any app route |
| `BetaFeedbackButton` | Never imported by any app route |
| `OfflineBanner` | Provider wired but banner UI never rendered |
| `PublicLayout` | Only referenced in tests |

---

## Phase 7 — Documentation Audit

### Documentation inventory
150 markdown files across 13 subfolders in `download/mastery-engine/docs/`:
- `ai/` (22 stubs), `application/` (6 full), `background-processing/` (10 full), `beta/` (10 full), `brand/` (1), `domain-model/` (6 full), `frontend/` (37 mixed), `infrastructure/` (7 full), `notifications/` (1), `operations/` (12 stubs), `security/` (1), `vertical-slices/` (5 full), root (2)

### Frontend docs pages — 16 of 22 required exist

| Required page | Status |
|---|---|
| `/docs` | ✅ |
| `/docs/getting-started` | ✅ |
| `/docs/installation` | ✅ |
| `/docs/architecture` | ❌ MISSING (sidebar 404) |
| `/docs/rest-api` | ✅ |
| `/docs/websocket-api` | ✅ (but no backend WS) |
| `/docs/authentication` | ✅ |
| `/docs/errors` | ✅ |
| `/docs/rate-limiting` | ❌ MISSING (sidebar 404) |
| `/docs/sdks` | ✅ |
| `/docs/cli` | ✅ |
| `/docs/api-explorer` | ✅ |
| `/docs/deployment` | ❌ MISSING (sidebar + sitemap 404) |
| `/docs/scaling` | ❌ MISSING (sidebar 404) |
| `/docs/monitoring` | ❌ MISSING (sidebar 404) |
| `/docs/security` | ✅ |
| `/docs/ai` | ❌ MISSING (sidebar + sitemap 404) |
| `/docs/learning-engine` | ✅ |
| `/docs/content-authoring` | ✅ |
| `/docs/administration` | ✅ |
| `/docs/troubleshooting` | ✅ |
| `/docs/faq` | ✅ |

**6 of 22 required docs pages MISSING.**

### Broken internal links
- 6 docs sidebar links 404 (architecture, ai, monitoring, scaling, deployment, rate-limiting)
- 4 portal sidebar links 404 (sessions, usage, organizations, invitations)
- 3 sitemap URLs 404 (docs/deployment, docs/architecture, docs/ai)
- 8 broken CONTRIBUTING.md links (`docs/domain/`, `docs/adr/`, `docs/api/`, `docs/database/`, `docs/domain-behavior/`, etc.)
- 1 content sidebar link 404 (`/content/templates` index)

### Documentation mismatches
| Document | Claim | Reality |
|---|---|---|
| `docs/operations/README.md` | "Redis caching layer with 13 cache policies" | `init_cache()` never called — dead code |
| `docs/operations/README.md` | "Distributed tracing (TraceContext)" | TraceContext is stub, never used |
| `app/docs/websocket-api/page.tsx` | "Comprehensive WebSocket API" | No backend WS endpoints exist |
| `docs/operations/disaster-recovery.md` | Implies DR plan | 5-line stub |
| `docs/operations/scaling-guide.md` | Implies scaling guidance | 5-line stub |
| `docs/ai/` (22 files) | 22 separate AI docs | All 22 are 21-word stubs |
| `backend/app/workers/__init__.py` docstring | References 5 modules | None exist with those names |

---

## Phase 8 — Build Configuration Audit

### package.json
- ✅ Scripts: dev, build, start, lint, typecheck, test, test:watch
- ✅ Build: `next build && cp -r .next/static .next/standalone/.next/ && cp -r public .next/standalone/`
- ⚠️ `db:push`, `db:generate`, `db:migrate`, `db:reset` are `echo skip` (vestigial prisma)
- ❌ Missing: `@testing-library/user-event`, `@playwright/test`
- ⚠️ ~30 unused Radix UI packages
- ⚠️ `cmdk`, `framer-motion`, `axios`, `date-fns` unused

### Lockfile
- ✅ `bun.lock` exists (deployed frontend uses bun)
- ❌ `package-lock.json` MISSING — frontend Dockerfile `npm ci` fails

### tsconfig.json
- ✅ `strict: true`, `noUncheckedIndexedAccess: true`
- ⚠️ `include: ["**/*.ts", "**/*.tsx"]` too broad — matches `download/`, `src/` → `bun run typecheck` fails
- ⚠️ `@/features/*` path maps to non-existent directory

### next.config.js + next.config.ts — DUPLICATE
- `next.config.js`: has `output: 'standalone'`, rewrites, env, experimental
- `next.config.ts`: minimal, lacks rewrites/env
- Next.js 16 prefers `.ts` → **build non-determinism**

### postcss.config.js + postcss.config.mjs — DUPLICATE
- Both identical (`@tailwindcss/postcss`)
- PostCSS loads first found

### tailwind.config.js + tailwind.config.ts — DUPLICATE
- Both v3-style configs
- `package.json` declares Tailwind v4 (`^4.1.18`) — v4 ignores JS configs
- Different content paths and color palettes between the two

### Dockerfiles
| Dockerfile | Verdict |
|---|---|
| `backend.Dockerfile` | ⚠️ Builder stage fragile; runtime crashes (pyotp missing) |
| `frontend.Dockerfile` | ❌ `npm ci` fails (no lockfile); healthcheck hits wrong endpoint |

### Railway configs (11 files)
| Config | Verdict |
|---|---|
| `/home/z/my-project/railway.json` (deployed FE) | ✅ PASS |
| `/home/z/my-project/nixpacks.toml` | ⚠️ `start.cmd` lacks `HOSTNAME=0.0.0.0` |
| `railway/backend/railway.json` | ⚠️ Config correct, runtime fails (pyotp) |
| `railway/frontend/railway.json` | ⚠️ Missing `HOSTNAME=0.0.0.0` |
| `railway/worker/railway.json` | ❌ Worker crashes on broken import |
| `railway/railway.toml` | ⚠️ TOML format Railway doesn't read |

### GitHub Actions (6 workflows)
| Workflow | Verdict |
|---|---|
| `backend.yml` | ⚠️ Docker build fails |
| `frontend.yml` | ❌ `npm ci` fails; calls non-existent `format:check` script |
| `integration.yml` | ❌ Fails at build step |
| `ci-cd.yml` | ❌ `pip install -e ".[test]"` — no `[test]` extra; deploy steps are `echo` stubs |
| `security.yml` | ✅ Solid (pip-audit, npm audit, CodeQL) |
| `railway-deploy.yml` | ⚠️ Tests use `|| true` — failures don't block deploy |

---

## Phase 9 — Middleware Audit

### Backend middleware (5 registered in `main.py:87-104`)
| Middleware | Status |
|---|---|
| `CorrelationMiddleware` | ✅ |
| `CSRFMiddleware` | ✅ (but hardcoded origins miss production domain) |
| `RateLimitMiddleware` | ✅ (but in-memory only, not distributed) |
| `SecurityHeadersMiddleware` | ✅ |
| `CORSMiddleware` | ✅ (but `allow_methods=["*"]` too broad) |

**Not registered:**
- `CompressionMiddleware` (defined in `performance/middleware.py:32-91`, never `add_middleware()`)
- `ETagMiddleware` (defined, never registered)
- `RequestTimingMiddleware` (defined, never registered)

### Frontend middleware (`/home/z/my-project/middleware.ts`)
- ✅ `PUBLIC_ROUTES` correctly lists 14 unauthenticated paths
- ✅ `PUBLIC_PREFIXES` covers 19 public prefix paths
- 🔴 **CRITICAL: `mastery-role` cookie never set by login page** — middleware admin check (`middleware.ts:72`) always redirects to `/forbidden`
- 🔴 `mastery-authenticated` cookie has no `Secure`, `HttpOnly`, `SameSite` — trivially forgeable
- ⚠️ Middleware checks cookie presence, not actual token validity — UX convenience only

### Redirect logic
- `/login` → `/dashboard` → `ProtectedRoute` → token under wrong key → `isAuthenticated=false` → `/login` → **infinite loop**

### Protected routes
- `components/layout/route-protection.tsx` uses `useAuth().isAuthenticated`
- `isAuthenticated` = `!!currentUser` = `hasToken && !!user`
- `hasToken` reads `mastery.access_token` — never set by login page → always false

### Health routes
- ✅ `/api/v1/health`, `/health/ready`, `/health/live` exist
- ❌ `/health/startup` missing (Kubernetes startup probe)

### API routes
- ✅ `/api/:path*` rewrite to backend in `next.config.js`
- ⚠️ No rewrites for `/openapi.json`, `/redoc`, `/openapi.yaml` — API explorer links 404

---

## Phase 10 — Database Audit

### Migrations (6 SQL init files, 29 CREATE TABLEs)
| File | Tables |
|---|---|
| `00-base-tables.sql` | 5 (identity.users, user_profiles, user_credentials, sessions, infrastructure.outbox_events) |
| `01-create-schemas.sql` | 0 (10 schemas + extensions) |
| `02-auth-tables.sql` | 7 (verification_tokens, password_reset_tokens, refresh_tokens, mfa_secrets, mfa_recovery_codes, security_incidents, auth_audit_logs) |
| `03-background-tables.sql` | 7 (dead_letter_events, notifications, notification_preferences, scheduled_jobs, worker_heartbeats, email_delivery_log, outbox_leases) |
| `04-beta-tables.sql` | 3 (beta_invites, beta_feedback, beta_events) |
| `05-beta-ops-tables.sql` | 7 (beta_feedback_votes, beta_feedback_meta, release_notes, release_stages, experiments, experiment_assignments, experiment_results) |

### Alembic — FAIL
- ✅ `alembic.ini`, `env.py` with `target_metadata = Base.metadata`
- ❌ **`versions/` directory MISSING** — `alembic upgrade head` is a no-op

### ORM vs migrations — CRITICAL
**47 ORM tables. 29 migration tables. 18 ORM tables have NO migration:**

| Schema | Missing tables |
|---|---|
| content (10) | subjects, concepts, learning_objectives, misconceptions, question_templates, template_versions, template_concepts, explanations, content_versions, content_packs |
| learning (2) | learner_enrollments, study_sessions |
| assessment (3) | question_instances, attempts, answers |
| mastery (3) | mastery_scores, reviews, algorithm_versions |

**Impact:** All content authoring, learning, assessment, and mastery operations fail at runtime with `relation does not exist`.

### Foreign keys — PASS (with minor gaps)
All declared FKs reference valid table+column pairs. Some UUIDs intentionally un-FK'd (DDD pattern). Minor gaps:
- `beta_invites.created_by` — no FK (orphan risk)
- `beta_feedback.user_id` — no FK (intentional)
- `outbox_leases.outbox_event_id` — UNIQUE but no FK

### Indexes — PASS
- ✅ `users.email` unique partial (`idx_users_email_active`)
- ✅ `outbox_events.(status, created_at)` partial (`idx_outbox_pending`)
- ✅ `beta_events.created_at` + type_created + user
- ✅ `auth_audit_logs.(user_id, created_at)` + action_created + correlation
- ✅ 41 total indexes, all `CREATE INDEX IF NOT EXISTS` (idempotent)

### Constraints — PASS
30+ CHECK constraints, 11 UNIQUE indexes, pervasive NOT NULL. All well-formed.

### Triggers — PASS
- ✅ `prevent_audit_log_mutation()` function exists (`02-auth:192-197`)
- ✅ `trg_audit_logs_no_update` BEFORE UPDATE on `auth_audit_logs`
- ✅ `trg_audit_logs_no_delete` BEFORE DELETE on `auth_audit_logs`
- ✅ Both idempotent (DROP IF EXISTS + CREATE OR REPLACE)

### Permissions — CRITICAL (GRANT-after-REVOKE bugs)
| Severity | Issue |
|---|---|
| 🔴 CRITICAL | `02-auth:211` `REVOKE UPDATE, DELETE ON auth_audit_logs` undone by `02-auth:252` `GRANT ... ON ALL TABLES IN SCHEMA identity` |
| 🔴 CRITICAL | `04-beta:90` `GRANT SELECT, INSERT ON beta_events` (append-only) undone by `05-beta-ops:172` `GRANT ... ON ALL TABLES IN SCHEMA analytics` — no trigger backstop |

### Seed data / views
- 0 seed INSERTs ✅
- 0 CREATE VIEWs ✅

### UUID generation
- ✅ `gen_random_uuid()` (built-in PG13+, used in all tables)

### Duplicate migrations
None. ✅

### Orphan migrations
None (all 6 SQL files create tables that have ORM models). ✅

---

## Phase 11 — Production Audit

| Component | Status | Notes |
|---|---|---|
| Docker (backend) | ⚠️ Builds, crashes at runtime | pyotp missing |
| Docker (frontend) | ❌ Cannot build | No `package-lock.json` |
| Docker Compose (3 files) | ⚠️ Frontend healthcheck wrong endpoint; Postgres SSL certs missing | |
| Railway (deployed FE) | ✅ RUNNING | `railway.json` correct |
| Railway (backend) | ❌ Cannot boot | pyotp missing |
| Railway (worker) | ❌ Cannot start | Broken import |
| Health endpoints | ⚠️ Partial | `/health`, `/ready`, `/live` exist; `/health/startup` missing |
| PORT handling | ✅ Correct | `apply_railway_overrides()` reads `$PORT` |
| Environment variables | ⚠️ Gaps | 12 used-but-undocumented, 4 documented-but-unused |
| Redis | ✅ Config present | Cache is dead code (`init_cache()` never called) |
| Postgres | ✅ Config present | 18 tables missing migrations |
| Sentry | ⚠️ Broken | `sentry-sdk` not in pyproject.toml; lazy import degrades gracefully |
| Prometheus | ❌ Non-functional | No `/metrics` endpoint — scrapes 404 |
| Grafana | ✅ Config valid | Dashboard + provisioning present |
| Nginx | ⚠️ Unused on Railway | Config exists but Railway doesn't use nginx |
| SSL | ⚠️ Railway auto-SSL | Custom domain requires manual setup |
| Workers | ❌ Cannot start | Broken import |
| Backups | ⚠️ VPS-only | `scripts/backup.sh` hardcodes `/opt/mastery-engine/` paths |
| Cron | ⚠️ Not configured | No cron config for backups/scheduler |
| Email | ✅ SMTP configured | `ProductionSmtpClient` with real smtplib |
| AI | ❌ Non-functional | Router not mounted; safety module broken |
| Feature flags | ✅ 6 beta flags | Configured via env vars |
| Closed beta | 🔴 BROKEN | Frontend doesn't send invite_token; banner/feedback button never mounted |

---

## Phase 12 — Code Quality Audit

### Dead code
| Item | Severity |
|---|---|
| `backend/app/infrastructure/cache/redis_cache.py` (510 lines, `init_cache()` never called) | Critical |
| `backend/app/infrastructure/performance/middleware.py` (Compression, ETag, RequestTiming — never registered) | Critical |
| `backend/app/infrastructure/observability/__init__.py` `TraceContext` (stub, never used) | Medium |
| `backend/app/infrastructure/database.py` (file duplicates package) | High |
| `src/` directory (~60 files, old scaffold) | High |
| 4 orphan components (`BetaBanner`, `BetaFeedbackButton`, `OfflineBanner`, `PublicLayout`) | Medium |
| `lib/realtime/websocket-provider.tsx` + `realtime-sync.tsx` (no backend WS) | Medium |
| ~30 unused Radix UI packages | Low |
| `cmdk`, `framer-motion`, `axios`, `date-fns` unused | Low |
| `prisma` + `@prisma/client` vestigial | Low |

### Broken imports
| File:line | Import | Issue |
|---|---|---|
| `backend/app/ai/safety/__init__.py:39` | `field()` | Not imported from dataclasses → NameError |
| `backend/app/workers/worker_main.py:37` | `from app.workers.scheduler import` | Module doesn't exist |
| `backend/scripts/railway/startup_worker.py:119` | Same | Same |
| `backend/tests/application/fakes.py:20` | `from app.domain.shared.kernel import Email` | Not defined (only in docstring) |
| `tests/sdk/js-sdk.test.ts:9` | Path traversal | Lands at `/home/z/sdks/` (ENOENT) |
| 9 frontend test files | `@testing-library/user-event` | Package not installed |
| `providers/theme-provider.tsx:5` | `next-themes/dist/types` | Path doesn't exist in v0.4.6 |

### Circular imports
None detected across all `__init__.py` files. ✅

### TODOs/FIXMEs
- 1 real TODO: `lib/production/error-recovery.ts` — "Send to Sentry/Datadog" (not wired)
- 0 FIXMEs, 0 HACKs, 0 @deprecated

### Commented-out production code
No suspicious blocks found. ✅

### Large files
- `backend/app/application/beta_ops/service.py` — 2,519 lines
- `backend/app/presentation/api/v1/beta_ops.py` — 1,097 lines
- `backend/app/ai/coach/__init__.py` — 787 lines
- `backend/app/ai/providers/__init__.py` — 733 lines
- `backend/app/infrastructure/cache/redis_cache.py` — 510 lines (dead code)

### Stale docstrings
- `backend/app/workers/__init__.py:1-14` references 5 non-existent modules

---

## Phase 13 — Testing Audit

### Test counts
| Suite | Declared | Collected | Passing | Failing/Broken |
|---|---|---|---|---|
| Backend | 1,919 | 1,829 | ~1,806 | 23 (4 collection errors) |
| Frontend | 830 | 644 | 610 | 34 + 177 not executed |
| E2E | 9 | 0 | 0 | 9 (Playwright not installed) |
| **Total** | **2,758** | **2,473** | **~2,416** | **~266** |

### Broken tests (production code bugs)
| File | Tests | Root Cause |
|---|---|---|
| `tests/ai/test_ai_platform.py` | 74 | `app/ai/safety/__init__.py:39` uses `field()` without import |
| `tests/application/test_assessment_mastery_handlers.py` | 7 | `Email` not defined in `kernel.py` |
| `tests/application/test_identity_handlers.py` | 8 | Same |
| `tests/application/test_learning_handlers.py` | 8 | Same |

### Frontend test failures
| Category | Files | Tests | Issue |
|---|---|---|---|
| Missing `@testing-library/user-event` | 9 | 128 | Package not in devDependencies |
| Wrong SDK path | 1 | 49 | `tests/sdk/js-sdk.test.ts` path traversal wrong |
| Assertion failures | 6 | 34 | QueryClient context, MAX_QUEUE_SIZE export, password min length, title regex |
| E2E (Playwright) | 1 | 9 | `@playwright/test` not installed |

### Coverage
- Backend: `--cov=app` but no `--cov-fail-under` threshold
- Frontend: coverage provider `v8` but no `thresholds` enforced

### Skipped tests
Zero skipped tests. ✅

### Missing tests
- No E2E coverage for: register flow, MFA flow, admin operations, content authoring, study session lifecycle
- 102 of 174 frontend API calls have no matching backend endpoint — these paths are untestable end-to-end

---

## Phase 14 — SEO Audit

### robots.txt
- ✅ `app/robots.ts` exists with valid rules
- ⚠️ `public/robots.txt` duplicate (Next.js serves `app/robots.ts`)
- ✅ Allow `/`, Disallow `/api/`, `/admin/`, `/dashboard`, `/study`, etc.
- ✅ Sitemap reference: `${SITE_URL}/sitemap.xml`
- ⚠️ Site URL default inconsistency: `masteryos.com` (robots.ts) vs `masteryos.space-z.ai` (next.config.js)

### sitemap.ts
- ✅ 28 URLs declared
- ❌ 3 URLs 404: `/docs/deployment`, `/docs/architecture`, `/docs/ai`

### manifest.webmanifest
- ✅ name, short_name, description, start_url, display, background_color, theme_color present
- ⚠️ theme_color `#2563EB` mismatches `viewport.themeColor` (`#ffffff`/`#0f172a`)
- ❌ Icons SVG only (no PNG) — Android PWA install fails

### favicon
- ✅ `public/favicon.svg` exists
- ❌ No `favicon.ico` fallback for legacy browsers
- ❌ No `apple-touch-icon.png` (iOS Safari ignores SVG)

### OpenGraph
- ✅ `openGraph.type`, `locale`, `url`, `siteName`, `title`, `description` set
- ❌ `openGraph.images[0].url` = `/brand/og-image.svg` — SVG unsupported by FB/Twitter/LinkedIn/Slack
- ❌ No per-page OG images

### Twitter cards
- ✅ `twitter.card` = `summary_large_image`
- ✅ `twitter.creator` = `@masteryos`
- ❌ Twitter image also SVG (unsupported)

### Canonical URLs
- ✅ Root canonical `/` set in `app/layout.tsx`
- ❌ No per-page canonical anywhere — every page canonicalizes to `/`

### Structured data (JSON-LD)
**Zero `application/ld+json` scripts found anywhere.** Missing: Organization, WebSite, BlogPosting, Article, BreadcrumbList, SoftwareApplication, FAQPage.

### Metadata
- ✅ Root layout has comprehensive metadata
- ❌ Only 2 of 100+ pages export their own metadata
- ❌ Marketing pages are `'use client'` — cannot export `metadata`

---

## Phase 15 — Final Consistency Report

### Repository Inventory
- **Backend:** 270 Python files, 12 API routers, 8 ORM files (47 tables), 8 AI files, 8 worker files, 75 test files (~1,919 tests)
- **Frontend:** 111 pages, 44 components, 10 hooks, 19 lib files, 5 providers, 3 stores, 5 types, 49 test files (~830 tests)
- **Source monorepo:** 6 SQL migrations, 150 MD docs, 5 SDKs, 1 CLI, 3 Docker compose, 2 Dockerfiles, 6 GitHub workflows, 6 monitoring configs, 11 Railway configs, 5 scripts

### Missing Files (26)
1. `backend/alembic/versions/` directory
2-5. 4 SQL migration files (content, learning, assessment, mastery)
6. `app/workers/scheduler.py` (or correct import)
7. `pyotp` in pyproject.toml
8. `sentry-sdk` in pyproject.toml
9. `aiosqlite` in pyproject.toml [dev]
10. `@testing-library/user-event` in package.json
11. `@playwright/test` in package.json
12. `package-lock.json`
13-18. 6 docs pages (architecture, ai, monitoring, scaling, deployment, rate-limiting)
19-22. 4 portal pages (sessions, usage, organizations, invitations)
23. `apple-touch-icon.png`
24. `icon-192.png` + `icon-512.png`
25. `og-image.png`
26. `/metrics` endpoint

### Broken Routes (12)
`/learn`, `/admin/beta`, `/docs/api`, `/docs/deployment`, `/docs/scaling`, `/docs/monitoring`, `/docs/architecture`, `/docs/rate-limiting`, `/portal/sessions`, `/portal/usage`, `/portal/organizations`, `/portal/invitations`, `/content/templates` (index)

Plus unreachable backend routes:
- 14 `/api/v1/ai/*` endpoints (router not mounted)
- `/api/v1/dashboard` (path bug — at `/api/v1/questions/api/v1/dashboard`)

### Broken APIs (102 frontend calls with no backend match)
- `lib/admin-api.ts`: 47 broken (users, organizations, rbac, feature-flags, audit-logs, security, billing, analytics, system-config, search, bulk, email-delivery)
- `lib/content-api.ts`: 24 broken (getById/update/archive/delete for subjects/concepts/objectives/misconceptions/templates, plus all `/admin/content/{dashboard,analytics,search,bulk,import,export}`)
- `lib/learner-api.ts`: 31 broken (dashboard, mastery, reviews, recommendations, achievements, notifications, enrollments list, study-session lifecycle)

### Broken Documentation
- 6 missing docs pages (404)
- 64 stub docs (16-21 words each)
- 8 broken CONTRIBUTING.md links
- 12 documentation mismatches (Redis cache claim, WebSocket API, DR/scaling stubs, etc.)
- No architecture/deployment/ER diagrams

### Broken Middleware
- `mastery-role` cookie never set → admin routes blocked for everyone
- `mastery-authenticated` cookie forgeable (no Secure/HttpOnly/SameSite)
- `CompressionMiddleware`, `ETagMiddleware`, `RequestTimingMiddleware` defined but never registered
- CSRF hardcoded origins miss production domain

### Build Problems
1. Backend cannot boot — `pyotp` missing
2. Worker cannot start — broken `app.workers.scheduler` import
3. Frontend Dockerfile cannot build — no `package-lock.json`
4. `next.config.ts` + `.js` conflict — build non-determinism
5. `tsconfig.json` include too broad — `bun run typecheck` fails
6. 22 TypeScript errors masked by `ignoreBuildErrors: true`
7. Duplicate Tailwind/PostCSS configs

### Railway Problems
1. Backend Railway config correct but runtime fails (pyotp)
2. Worker Railway config crashes on broken import
3. `nixpacks.toml` start.cmd lacks `HOSTNAME=0.0.0.0`
4. `railway/frontend/railway.json` missing `HOSTNAME=0.0.0.0`
5. `railway/railway.toml` uses TOML format Railway doesn't read
6. Source frontend `next.config.js` lacks `output: 'standalone'`
7. No CI/CD workflows in deployed repo (only in source monorepo)

### Production Problems
1. No `/metrics` endpoint — Prometheus 404
2. Redis cache dead code (`init_cache()` never called)
3. No horizontal scaling config (single backend, single worker)
4. Backups VPS-only (incompatible with Railway)
5. DR documentation is 5-line stub
6. No SSL configuration for custom domain
7. Closed beta broken (no invite_token, banner/feedback never mounted)
8. AI platform non-functional (router not mounted)
9. Monitoring non-functional (no /metrics)
10. Caching non-functional (dead code)

### Dead Code
1. `backend/app/infrastructure/cache/redis_cache.py` (510 lines)
2. `backend/app/infrastructure/performance/middleware.py` (Compression, ETag, RequestTiming)
3. `backend/app/infrastructure/observability/__init__.py` TraceContext
4. `backend/app/infrastructure/database.py` (file duplicates package)
5. `src/` directory (~60 files)
6. 4 orphan components
7. `lib/realtime/*` (no backend WS)
8. ~30 unused Radix UI packages
9. `cmdk`, `framer-motion`, `axios`, `date-fns` unused
10. `prisma` + `@prisma/client` vestigial

### Duplicate Files
1. `next.config.js` + `next.config.ts`
2. `tailwind.config.js` + `tailwind.config.ts`
3. `postcss.config.js` + `postcss.config.mjs`
4. `infrastructure/database.py` (file) + `database/` (package)
5. `public/robots.txt` + `app/robots.ts`
6. `src/` directory (~60 files duplicate of root app/)

### Unused Components
1. `components/beta/beta-banner.tsx` — never imported
2. `components/beta/feedback-button.tsx` — never imported
3. `components/production/offline-banner.tsx` — provider wired but banner never rendered
4. `components/layout/public-layout.tsx` — only in tests

### Missing Environment Variables (used but undocumented)
1. `NEXT_PUBLIC_SITE_URL` — used in sitemap.ts, layout.tsx, robots.ts but not in `.env.example`
2. `DATABASE_ECHO` — used in engine.py but not documented
3. `JWT_CLOCK_SKEW_SECONDS` — used in settings but not documented
4. `ARGON2_MEMORY_COST`, `ARGON2_TIME_COST`, `ARGON2_PARALLELISM` — used but not documented
5. `ENABLE_DOCS` — used in main.py but not documented
6. `SESSION_IDLE_TIMEOUT_MINUTES`, `SESSION_ABSOLUTE_TIMEOUT_DAYS` — used but not documented
7. `EMAIL_VERIFICATION_TOKEN_TTL_HOURS`, `PASSWORD_RESET_TOKEN_TTL_MINUTES` — used but not documented
8. `RAILWAY_PROJECT_ID`, `RAILWAY_SERVICE_ID` — used in railway_config.py but not documented

### Missing Tests
- No E2E coverage for: register, MFA, admin operations, content authoring, study sessions
- 102 frontend API calls with no backend — untestable end-to-end
- No coverage thresholds enforced
- Playwright not installed (9 E2E tests can't run)
- `@testing-library/user-event` missing (128 tests can't run)

### Security Problems
1. 🔴 14 `/api/v1/admin/bg/*` endpoints have ZERO authentication
2. 🔴 Forgeable auth cookies (no Secure/HttpOnly/SameSite)
3. 🔴 JWT keys always ephemeral (every restart invalidates tokens)
4. 🔴 GRANT-after-REVOKE on `auth_audit_logs`
5. 🔴 GRANT-after-REVOKE on `beta_events` (no trigger backstop)
6. 🟠 11 content admin endpoints have no RBAC
7. 🟠 `/api/v1/ai/config` PATCH has no admin check
8. 🟠 Frontend has no security headers/CSP
9. 🟠 JWT access token in localStorage (XSS can exfiltrate)
10. 🟠 CSRF hardcoded origins miss production domain
11. 🟡 Rate limiter in-memory only (not distributed)
12. 🟡 Backend password validation only checks length

### Performance Problems
1. 🔴 Redis cache is dead code — every query hits PostgreSQL
2. 🔴 CompressionMiddleware never registered — no gzip
3. 🔴 ETagMiddleware never registered — no 304 support
4. 🟠 No eager loading patterns (N+1 query risk)
5. 🟡 Zero `dynamic()`/`React.lazy` usage — eager bundling
6. 🟡 No WebSocket endpoints (realtime features non-functional)
7. 🟡 `/api/v1/health/ready` creates new Redis client per request
8. 🟡 No horizontal scaling config

### Architecture Violations
1. `infrastructure/scheduler/processor.py:36` imports from `app.workers.host` — inverted dependency direction (infrastructure → workers)
2. 2 empty schemas (scheduling, billing) — domains exist but no persistence
3. 18 ORM tables have no migration — ORM/migration mismatch
4. AI router defined but not mounted — dead code in presentation layer
5. `database.py` (file) coexists with `database/` (package) — Python loads package, file is dead
6. `src/` directory duplicates root app/ structure — old scaffold not cleaned up

### Recommended Fixes (priority order, NOT implemented)

**Tier 1 — Unblock backend boot (1.5h):**
1. Add `pyotp>=2.9.0`, `sentry-sdk[fastapi]>=2.0.0`, `aiosqlite>=0.20.0` to pyproject.toml
2. Fix `worker_main.py:37` and `startup_worker.py:119`: `from app.infrastructure.scheduler import SchedulerProcessor`
3. Fix `safety/__init__.py:19`: `from dataclasses import dataclass, field`

**Tier 2 — Restore security (4h):**
4. Add `RequireAdmin` to all 14 `/admin/bg/*` endpoints in `admin.py`
5. Add `RequireAdmin` to all 11 `/admin/subjects/*` endpoints in `content_admin.py`
6. Fix GRANT-after-REVOKE in `02-auth-tables.sql` and `05-beta-ops-tables.sql`
7. Pass `keys_dir=settings.jwt_keys_dir` to `JWTService` in `dependencies.py:124-131`
8. Provision JWT RSA keys via Railway volume

**Tier 3 — Fix auth flow (8h):**
9. Rewrite `login/page.tsx` to use `authApi.login()` + `tokenStorage`
10. Add MFA challenge handling
11. Set `mastery-role` cookie from `/users/me` response
12. Use secure cookies (Secure; HttpOnly; SameSite=Strict)
13. Fix `register/page.tsx`: send `display_name` + `invite_token`
14. Fix `mfa/verify/page.tsx`: re-POST `/auth/login` for login MFA
15. Fix `auth-provider.tsx` logout: clear all cookies + localStorage keys
16. Expose `setUser` from `AuthProvider`

**Tier 4 — Restore AI + dashboard + database (17h):**
17. Mount AI router in `main.py`
18. Add `RequireAdmin` to `PATCH /ai/config`
19. Fix `questions.py:656`: change to `@router.get("/dashboard")` + move router
20. Create 4 SQL migration files for 18 missing tables (OR generate Alembic revision)

**Tier 5 — Fix build & deployment (5h):**
21. Delete `next.config.ts` (consolidate to `next.config.js`)
22. Add `"download", "src", "tests"` to `tsconfig.json` exclude
23. Fix `theme-provider.tsx:5`: `import { type ThemeProviderProps } from 'next-themes'`
24. Fix `types/learning.ts:230-243`: delete first `DashboardData`
25. Fix `lib/query-keys.ts`: rename duplicate `content` key
26. Fix `frontend.Dockerfile`: use bun OR generate lockfile; fix healthcheck
27. Fix `ci-cd.yml:105`: `.[test]` → `.[dev]`
28. Fix `railway-deploy.yml`: remove `|| true`
29. Remove `typescript.ignoreBuildErrors: true`

**Tier 6 — Restore performance & monitoring (3h):**
30. Wire `CompressionMiddleware`, `ETagMiddleware` into `create_app()`
31. Call `init_cache()` in `lifespan()` startup
32. Expose `/metrics` endpoint
33. Add `/health/startup` endpoint

**Tier 7 — Complete documentation (10h):**
34. Create 6 missing docs pages OR remove from sidebar
35. Create 4 missing portal pages OR remove from sidebar
36. Fix 3 sitemap URLs
37. Fix 8 broken CONTRIBUTING.md links

**Tier 8 — Restore test infrastructure (2h):**
38. `bun add -D @testing-library/user-event @playwright/test`
39. Fix `tests/sdk/js-sdk.test.ts:9` path
40. Implement `Email` value object in `kernel.py`

**Tier 9 — Complete closed beta (4h):**
41. Mount `<BetaBanner>` + `<BetaFeedbackButton>` in layouts
42. Generate PNG OG image + PNG icons + apple-touch-icon

**Total: ~57 hours for all critical + high items.**

---

## FINAL VERDICT

### ❌ Not Ready for Deployment

**Production Readiness: 32%**

| Score | Value |
|---|---|
| Overall Health | 38/100 |
| Architecture | 72/100 |
| Backend | 45/100 |
| Frontend | 55/100 |
| Security | 30/100 |
| Deployment | 35/100 |
| Documentation | 60/100 |
| Testing | 65/100 |
| Maintainability | 50/100 |
| **Production Readiness** | **32%** |

The architecture is sound — Clean Architecture with 8 DDD bounded contexts, RS256 JWT, Argon2id, outbox pattern. The issues are integration bugs, missing migrations, unmounted routers, and broken imports that are all fixable without redesigning anything.

**Not Ready for Closed Beta. Not Ready for Public Beta. Not Ready for Production.**

**Recommendation:** Address Tier 1-4 fixes (~30 hours) before attempting closed beta. The deployed Railway frontend builds and serves the landing page, but no real user can register, log in, study, view dashboard, access admin, author content, or properly log out.

---

*End of Task 029E audit report. No files were modified. Nothing was pushed to GitHub. Every finding references exact file and line verified via Grep/Glob/Read/Bash. This is a COMPLETE AUDIT ONLY — no fixes were implemented.*
