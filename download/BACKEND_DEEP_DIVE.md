# MasteryOS — Complete Backend Deep-Dive Report

**Date:** 2026-07-05
**Backend:** `/home/z/my-project/backend/`
**Total:** 191 Python files · 51,150 lines of code · 114 API endpoints · 47 database tables

---

## 1. COMPLETE FILE INVENTORY

### Domain Layer (68 files, 14,966 lines)
The domain layer contains 8 bounded contexts with entities, value objects, domain events, and repository interfaces.

| Context | Files | Lines | Key Entities |
|---|---|---|---|
| identity | 7 | 2,108 | User, Profile, Credential, Session, AuthEvents |
| content | 12 | 4,431 | Subject, Concept, QuestionTemplate, TemplateVersion, ContentPack, ContentVersion, LearningObjective, Misconception, ConceptDependency |
| assessment | 8 | 1,120 | QuestionInstance, Attempt, Answer, QuestionFactory, TemplateEngine, VariableGenerator |
| learning | 8 | 998 | Enrollment, StudySession, Streak, Achievement, Recommendation, LearningGoal |
| mastery | 6 | 958 | MasteryScore, Review, AlgorithmVersion, MasteryCalculator |
| scheduling | 6 | 1,734 | DailyQueue, QueueGenerator, SchedulingConfig |
| administration | 7 | 2,396 | Notification, FeatureFlag, AuditLog, Organization |
| billing | 5 | 1,957 | Subscription, Invoice, BillingPlan |
| shared | 3 | 1,191 | Kernel (Entity, AggregateRoot, ValueObject, DomainEvent, Email), IDs, ValueObjects |

### Application Layer (12 files, 6,247 lines)

| File | Lines | What it does |
|---|---|---|
| identity/auth_service.py | 1,441 | ProductionAuthService: register, login, refresh, logout, MFA, password reset, email verification, session management |
| identity/auth_dto.py | 420 | Auth DTOs (RegisterRequest, LoginRequest, AuthResponse, etc.) |
| identity/handlers.py | 305 | Command handlers (RegisterUser, VerifyEmail, SuspendUser, etc.) |
| identity/dto.py | 179 | User DTOs |
| identity/mappers.py | 71 | Domain ↔ ORM mappers |
| learning/handlers.py | 303 | EnrollLearner, StartStudySession, SetLearningGoal handlers |
| learning/queries.py | 239 | Dashboard query, adaptive queue query |
| learning/dto.py | 183 | Learning DTOs |
| mastery/handlers.py | 267 | UpdateMastery, ScheduleReview handlers |
| assessment/handlers.py | 202 | SubmitAttempt, GetQuestion handlers |
| beta/service.py | 399 | BetaService: invite management, registration guard, feedback, analytics |
| beta_ops/service.py | 2,518 | BetaOpsService: 12-part closed beta operations platform |

### Infrastructure Layer (26 files, 9,638 lines)

| Module | Files | Lines | What it does |
|---|---|---|---|
| database/engine.py | 1 | 205 | Async engine, session factory, init_database (creates schemas + tables) |
| database/orm/ | 8 | 1,899 | 47 ORM models across 8 files |
| database/repositories/ | 2 | 1,579 | Auth repository (7 classes), Background repository (6 classes) |
| security/ | 6 | 1,456 | JWT (RS256), Password (Argon2id), MFA (TOTP), Session, Token, Authorization (RBAC) |
| cache/ | 1 | 509 | RedisCache with 13 cache policies + tag-based invalidation |
| events/outbox/ | 2 | 270 | Outbox dispatcher + event serializer |
| email/ | 2 | 1,043 | SMTP client + beta email templates |
| notifications/ | 1 | 292 | Notification service (in-app, email, SMS) |
| scheduler/ | 1 | 459 | Scheduler processor (8 default jobs) |
| performance/ | 1 | 376 | Compression + ETag + RequestTiming middleware |
| queue/ | 1 | 541 | Redis job queue with leasing + visibility timeout |

### Presentation Layer (16 files, 6,494 lines)

| File | Lines | Endpoints | What it does |
|---|---|---|---|
| api/health.py | 148 | 3 | Health check (live, ready, live-alias) |
| api/v1/auth.py | 837 | 15 | Register, login, refresh, logout, MFA, password reset, email verify |
| api/v1/users.py | 295 | 3 | Get/update current user, security dashboard |
| api/v1/learning.py | 523 | 4 | Enroll, set goal, start session, adaptive queue |
| api/v1/questions.py | 850 | 3 | Get question, submit answer, dashboard |
| api/v1/content_admin.py | 528 | 11 | Subject/concept/template CRUD |
| api/v1/admin.py | 541 | 14 | Workers, outbox, dead letters, jobs, notifications (admin) |
| api/v1/beta.py | 484 | 9 | Beta status, feedback, invites CRUD |
| api/v1/beta_ops.py | 1,125 | 23 | Beta ops dashboard, funnel, learning, feedback, success, instructor, operations, releases, reports, experiments |
| api/v1/ai.py | 503 | 13 | AI status, config, explanations, coach, analytics, content, recommendations, reports, instructor, prompts, audit, metrics |
| api/v1/learner.py | 525 | 14 | Enrollments list/detail, study sessions, mastery, reviews, recommendations, achievements, notifications |
| api/v1/feature_flags.py | 120 | 2 | Feature flags (admin + public) |
| dependencies.py | 422 | — | DI providers (get_uow, get_jwt_service, get_current_user_id, RequireAdmin, etc.) |
| dependencies_email.py | 42 | — | Email service DI |
| middleware/correlation.py | 75 | — | Correlation ID middleware |
| middleware/security.py | 283 | — | CSRF, rate limiting, security headers middleware |

### Shared (4 files, 610 lines)

| File | Lines | What it does |
|---|---|---|
| config.py | 258 | Settings (60+ config fields) + Railway overrides |
| logging.py | 100 | Structured logging (structlog) |
| exceptions.py | 49 | Shared exceptions |
| railway_config.py | 203 | Railway deployment detection + env var overrides |

### AI Platform (8 files, 3,709 lines)

| File | Lines | What it does |
|---|---|---|
| __init__.py | 480 | AIConfig, AIProvider ABC, ProviderRegistry, exceptions |
| providers/__init__.py | 733 | 5 providers: Mock, Ollama, OpenAI, Gemini, Anthropic |
| gateway/__init__.py | 424 | AIGateway: routing, fallback, rate limiting, caching |
| coach/__init__.py | 787 | StudyCoach, PredictiveAnalytics, InstructorIntelligence, ContentIntelligence, RecommendationEnhancer, WeeklyReports, ModelVersionManager, ExperimentFramework, OfflineEvaluator |
| prompts/__init__.py | 471 | PromptRepository with 7 prompt types |
| explanations/__init__.py | 348 | ExplanationGenerator + HumanReviewWorkflow |
| safety/__init__.py | 275 | SafetyValidator (prompt injection, PII, toxicity, hallucination) |
| audit/__init__.py | 191 | AuditLogger for AI request/response tracking |

### Workers (7 files, 8,392 lines)

| File | Lines | What it does |
|---|---|---|
| worker_main.py | 178 | Worker entrypoint (registers 5 processors) |
| host.py | 443 | WorkerHost (graceful shutdown, heartbeat) |
| outbox_dispatcher.py | 684 | Outbox polling, batch dispatch, retry, dead lettering |
| processors.py | 310 | Notification, Email, Cleanup processors |
| retry_engine.py | 245 | Exponential backoff retry (1m, 5m, 15m, 1h, 6h, 24h) |
| metrics.py | 408 | BackgroundMetrics, MetricsCollector |
| subscriber_registry.py | 236 | Event subscriber registry (4 event types wired) |

### Scripts (2 files, 478 lines)

| File | Lines | What it does |
|---|---|---|
| railway/startup_backend.py | 247 | Railway backend startup (wait DB/Redis, create tables, verify schema, start uvicorn) |
| railway/startup_worker.py | 231 | Railway worker startup (wait DB/Redis, start WorkerHost) |

---

## 2. COMPLETE API ENDPOINT INVENTORY (114 endpoints)

### Health (3 endpoints — all public)
| Method | Path | Auth |
|---|---|---|
| GET | /api/v1/health | Public |
| GET | /api/v1/health/ready | Public |
| GET | /api/v1/health/live | Public |

### Auth (15 endpoints)
| Method | Path | Auth |
|---|---|---|
| POST | /api/v1/auth/register | Public |
| POST | /api/v1/auth/login | Public |
| POST | /api/v1/auth/refresh | Public |
| POST | /api/v1/auth/logout | Auth |
| POST | /api/v1/auth/logout-all | Auth |
| POST | /api/v1/auth/verify-email | Public |
| POST | /api/v1/auth/resend-verification | Public |
| POST | /api/v1/auth/forgot-password | Public |
| POST | /api/v1/auth/reset-password | Public |
| POST | /api/v1/auth/change-password | Auth |
| POST | /api/v1/auth/mfa/setup | Auth |
| POST | /api/v1/auth/mfa/verify | Auth |
| POST | /api/v1/auth/mfa/enable | Auth |
| POST | /api/v1/auth/mfa/disable | Auth |
| POST | /api/v1/auth/mfa/recovery | Auth |

### Users (3 endpoints)
| Method | Path | Auth |
|---|---|---|
| GET | /api/v1/users/me | Auth |
| PATCH | /api/v1/users/me | Auth |
| GET | /api/v1/users/me/security | Auth |

### Learning (4 endpoints)
| Method | Path | Auth |
|---|---|---|
| POST | /api/v1/enrollments | Auth |
| POST | /api/v1/enrollments/{id}/learning-goals | Auth |
| POST | /api/v1/study-sessions | Auth |
| GET | /api/v1/study-sessions/{id}/adaptive-queue | Auth |

### Questions (3 endpoints)
| Method | Path | Auth |
|---|---|---|
| GET | /api/v1/questions/{id} | Auth |
| POST | /api/v1/questions/{id}/submit | Auth |
| GET | /api/v1/questions/dashboard | Auth |

### Content Admin (11 endpoints — RBAC: instructor/editor/admin)
| Method | Path | Auth |
|---|---|---|
| POST | /api/v1/admin/subjects | Auth+RBAC |
| POST | /api/v1/admin/subjects/{id}/publish | Auth+RBAC |
| GET | /api/v1/admin/subjects | Auth+RBAC |
| POST | /api/v1/admin/subjects/{id}/concepts | Auth+RBAC |
| POST | /api/v1/admin/concepts/{id}/objectives | Auth+RBAC |
| POST | /api/v1/admin/concepts/{id}/misconceptions | Auth+RBAC |
| POST | /api/v1/admin/subjects/{id}/question-templates | Auth+RBAC |
| POST | /api/v1/admin/question-templates/{id}/publish | Auth+RBAC |
| GET | /api/v1/admin/subjects/{id}/concepts | Auth+RBAC |
| GET | /api/v1/admin/subjects/{id}/question-templates | Auth+RBAC |
| GET | /api/v1/admin/question-templates/{id} | Auth+RBAC |

### Admin/Background (14 endpoints — RBAC: admin)
| Method | Path | Auth |
|---|---|---|
| GET | /api/v1/admin/bg/workers | Admin |
| GET | /api/v1/admin/bg/workers/metrics | Admin |
| GET | /api/v1/admin/bg/outbox | Admin |
| GET | /api/v1/admin/bg/outbox/stats | Admin |
| GET | /api/v1/admin/bg/outbox/{id} | Admin |
| POST | /api/v1/admin/bg/outbox/{id}/replay | Admin |
| GET | /api/v1/admin/bg/dead-letters | Admin |
| POST | /api/v1/admin/bg/dead-letters/{id}/retry | Admin |
| POST | /api/v1/admin/bg/dead-letters/{id}/resolve | Admin |
| GET | /api/v1/admin/bg/notifications | Admin |
| GET | /api/v1/admin/bg/jobs | Admin |
| POST | /api/v1/admin/bg/jobs/run | Admin |
| POST | /api/v1/admin/bg/jobs/{id}/pause | Admin |
| POST | /api/v1/admin/bg/jobs/{id}/resume | Admin |

### Beta (9 endpoints)
| Method | Path | Auth |
|---|---|---|
| GET | /api/v1/beta/status | Public |
| POST | /api/v1/beta/feedback | Auth |
| GET | /api/v1/beta/feedback | Admin |
| POST | /api/v1/beta/track | Auth |
| GET | /api/v1/beta/analytics | Admin |
| POST | /api/v1/admin/beta/invites | Admin |
| GET | /api/v1/admin/beta/invites | Admin |
| DELETE | /api/v1/admin/beta/invites/{id} | Admin |
| POST | /api/v1/admin/beta/invites/resend | Admin |

### Beta Ops (23 endpoints — all admin)
Dashboard, funnel, retention, learning, feedback (list/vote/meta/mark-duplicate), success, instructor, operations, releases (list/create/update/stage), reports (get/generate), experiments (list/get/create/update/assign/results)

### AI (13 endpoints)
| Method | Path | Auth |
|---|---|---|
| GET | /api/v1/ai/status | Public |
| PATCH | /api/v1/ai/config | Auth |
| POST | /api/v1/ai/explanations/generate | Auth |
| POST | /api/v1/ai/coach/plan | Auth |
| POST | /api/v1/ai/analytics/forecast | Auth |
| POST | /api/v1/ai/content/analyze | Auth |
| POST | /api/v1/ai/recommendations/enhance | Auth |
| POST | /api/v1/ai/reports/weekly | Auth |
| POST | /api/v1/ai/instructor/insights | Auth |
| GET | /api/v1/ai/prompts | Auth |
| GET | /api/v1/ai/prompts/{type} | Auth |
| GET | /api/v1/ai/audit | Auth |
| GET | /api/v1/ai/metrics | Auth |

### Learner (14 endpoints — all auth)
Enrollments (list/detail), study sessions (get/end), mastery scores (list/weak), reviews (due), recommendations, achievements, notifications (list/open/dismiss/mark-all/unread-count)

### Feature Flags (2 endpoints)
| Method | Path | Auth |
|---|---|---|
| GET | /api/v1/admin/feature-flags | Admin |
| GET | /api/v1/feature-flags | Auth |

### Other
| Method | Path | Auth |
|---|---|---|
| GET | / | Public |
| GET | /metrics | Public |

---

## 3. COMPLETE DATABASE MODEL INVENTORY (47 tables)

| Schema | Tables | ORM File |
|---|---|---|
| identity | 15 | identity.py (4) + auth.py (7) + beta.py (3) + beta_ops.py (2) |
| content | 10 | content.py |
| learning | 2 | core.py |
| assessment | 3 | core.py |
| mastery | 3 | core.py |
| administration | 4 | background.py (3) + beta_ops.py (1) |
| analytics | 4 | beta.py (1) + beta_ops.py (3) |
| infrastructure | 6 | core.py (1) + background.py (6) |
| scheduling | 0 | (domain exists, no tables) |
| billing | 0 | (domain exists, no tables) |
| **Total** | **47** | |

---

## 4. BACKEND ISSUES — What Needs Fixing

### 🔴 Critical (blocks core functionality)

| # | Issue | File:Line | Fix |
|---|---|---|---|
| 1 | Admin endpoints show [Public] in audit but have router-level RBAC | admin.py:57-64 | ✅ Already fixed (router-level dependencies) |
| 2 | Alembic versions/ directory missing | backend/alembic/ | Create initial migration OR keep using create_all |
| 3 | Only 2 repository files (auth.py, background.py) — 8 domain contexts have repository INTERFACES but no implementations | database/repositories/ | Implement repositories for content, learning, mastery, assessment, scheduling, billing, administration, notifications |
| 4 | JWT keys are ephemeral (no keys provisioned on Railway) | dependencies.py:133 | Generate RSA keys + mount on Railway volume |
| 5 | Worker not deployed on Railway | — | Deploy worker service |

### 🟠 High (significant gaps)

| # | Issue | Fix |
|---|---|---|
| 6 | 13 admin API endpoints missing (/admin/users, /admin/rbac, /admin/organizations, /admin/audit-logs, /admin/billing, /admin/email, /admin/security, /admin/analytics, /admin/system-config, /admin/search, /admin/bulk, /admin/bg/operations, /admin/bg/email-delivery) | Implement endpoints |
| 7 | 102 frontend API calls have no matching backend endpoint | Implement missing endpoints OR remove frontend calls |
| 8 | SMTP_HOST typo: smtp.gamil.com → smtp.gmail.com | Fix env var on Railway |
| 9 | No Alembic migration history | Generate initial revision |
| 10 | Application layer missing 10+ command handlers (GenerateAdaptiveQueue, ScheduleReview, GenerateRecommendation, UnlockAchievement, PublishContent, CreateQuestionTemplate, CreateOrganization, EnableFeatureFlag, CreateSubscription, CancelSubscription, CreateNotification) | Implement handlers |
| 11 | No domain mappers (database/mappers/ is empty) | Implement bidirectional Domain ↔ ORM mappers |
| 12 | Application services use direct service calls instead of Command/Query pattern | Refactor to Command handlers |
| 13 | Scheduling + billing schemas have 0 tables | Implement ORM models + migrations |

### 🟡 Medium

| # | Issue | Fix |
|---|---|---|
| 14 | AI config not in Settings class (env vars AI_ENABLED, OLLAMA_HOST, OLLAMA_MODEL unused) | Add to Settings |
| 15 | Redis cache initialized but no routes use cache-aside pattern | Apply cache to dashboard, mastery, questions |
| 16 | Rate limiter is in-memory (not Redis-distributed) | Implement Redis-backed rate limiter |
| 17 | No WebSocket endpoints | Implement /ws for real-time notifications |
| 18 | Only 4 event subscribers wired (out of 17 claimed) | Wire remaining 13 event subscribers |
| 19 | 4 of 9 scheduler jobs missing (review_reminders, queue_generation, monthly_reports, backup_verification) | Implement missing jobs |
| 20 | OAuth (Google/GitHub) not implemented | Implement OAuth service + endpoints |
| 21 | No cookie-based auth (HttpOnly) — using localStorage | Implement HttpOnly cookie auth |
| 22 | No /health/startup endpoint | Add Kubernetes startup probe |

---

## 5. RECOMMENDED IMPROVEMENTS (Top 20, ordered by priority)

| # | What | Why | Effort | Impact |
|---|---|---|---|---|
| 1 | Implement 13 missing admin endpoints | Admin pages show empty data | 20h | High |
| 2 | Implement repositories for 6 domain contexts | Only 2 of 8 contexts have repos | 16h | High |
| 3 | Fix SMTP_HOST typo on Railway | Email sending broken | 0.1h | High |
| 4 | Provision JWT RSA keys on Railway | Tokens invalidated on restart | 1h | Critical |
| 5 | Deploy worker on Railway | No background processing | 1h | Critical |
| 6 | Generate Alembic initial migration | No migration history | 4h | Medium |
| 7 | Implement 10 missing command handlers | Application layer incomplete | 16h | Medium |
| 8 | Add AI config to Settings class | AI env vars unused | 1h | Medium |
| 9 | Apply Redis cache to hot routes | Performance | 4h | Medium |
| 10 | Implement Redis-backed rate limiter | Multi-replica safety | 4h | Medium |
| 11 | Wire remaining 13 event subscribers | Event-driven features broken | 8h | Medium |
| 12 | Implement 4 missing scheduler jobs | Background jobs incomplete | 4h | Low |
| 13 | Implement WebSocket /ws endpoint | Real-time features broken | 8h | Medium |
| 14 | Implement OAuth (Google/GitHub) | Social login missing | 8h | Low |
| 15 | Implement cookie-based auth | Security improvement | 8h | Medium |
| 16 | Implement domain mappers | Clean Architecture compliance | 8h | Low |
| 17 | Add scheduling + billing tables | 2 schemas empty | 4h | Low |
| 18 | Refactor to Command/Query pattern | Architecture consistency | 16h | Low |
| 19 | Add /health/startup endpoint | K8s readiness | 0.5h | Low |
| 20 | Add password complexity validation | Security hardening | 1h | Low |

**Total estimated effort: ~130 hours for all improvements.**
