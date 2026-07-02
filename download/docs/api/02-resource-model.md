# 02 — Resource Model

> Every API resource: purpose, ownership, relationships, operations, authorization.

---

## Resource Model Principles

1. **Resources map to Task 004's tables and Task 005's commands/queries.** Each resource corresponds to one or more database tables; each operation maps to a command or query.
2. **Ownership follows Task 005's bounded contexts.** Each resource is owned by one context (the only context that writes it).
3. **Authorization follows Task 005's role definitions.** Each operation lists who can perform it.
4. **Resources are learner-facing or admin-facing.** Learner-facing resources are under `/api/v1/...`; admin-facing resources are under `/api/v1/admin/...` with stricter auth.

---

## Learner-Facing Resources

### auth (Authentication)
- **Purpose**: User registration, login, logout, token refresh, password reset, OAuth, MFA.
- **Ownership**: identity.
- **Relationships**: issues sessions for users.
- **Operations**: register, login, logout, refresh, verify-email, request-password-reset, reset-password, link-oauth, unlink-oauth, enable-mfa, disable-mfa.
- **Authorization**: mostly anonymous (register, login, reset); authenticated (logout, MFA, OAuth link).

### users
- **Purpose**: The authenticated user's own identity.
- **Ownership**: identity.
- **Relationships**: 1:1 with profiles; 1:many with enrollments.
- **Operations**: get-me, update-me, request-deletion, cancel-deletion.
- **Authorization**: self only (no user-to-user access).

### profiles
- **Purpose**: User-editable profile attributes.
- **Ownership**: identity.
- **Relationships**: 1:1 with users.
- **Operations**: get-me, update-me.
- **Authorization**: self only.

### enrollments (Learner Enrollments)
- **Purpose**: A user's enrollment as a learner in a subject.
- **Ownership**: learning.
- **Relationships**: many:1 with users; many:1 with subjects; 1:many with study-sessions, mastery-scores.
- **Operations**: create (enroll), get, list (own), complete-onboarding, unenroll.
- **Authorization**: self (own enrollments only).

### subjects
- **Purpose**: Curriculum units (Python, SQL, etc.).
- **Ownership**: content.
- **Relationships**: 1:many with concepts, learning-paths, question-templates.
- **Operations**: list (published), get.
- **Authorization**: any authenticated user (read published); admin (create, publish, deprecate).

### learning-paths
- **Purpose**: Ordered traversals of a subject's concepts.
- **Ownership**: content.
- **Relationships**: many:1 with subjects; many:many with concepts (via items).
- **Operations**: list (by subject), get.
- **Authorization**: any authenticated user (read); instructor/admin (create, revise).

### concepts
- **Purpose**: Atomic knowledge units.
- **Ownership**: content.
- **Relationships**: many:1 with subjects; many:many with learning-paths; 1:many with objectives, misconceptions, dependencies.
- **Operations**: list (by subject), get, search.
- **Authorization**: any authenticated user (read published); instructor/admin (create, revise).

### learning-objectives
- **Purpose**: Verifiable skill statements per concept.
- **Ownership**: content.
- **Relationships**: many:1 with concepts; 1:many with misconceptions.
- **Operations**: list (by concept), get.
- **Authorization**: any authenticated user (read); instructor/admin (create).

### misconceptions
- **Purpose**: Documented incorrect mental models.
- **Ownership**: content.
- **Relationships**: many:1 with objectives; 1:many with distractors.
- **Operations**: list (by objective), get.
- **Authorization**: any authenticated user (read); instructor/admin (create).

### question-templates
- **Purpose**: Parameterized question specifications.
- **Ownership**: content.
- **Relationships**: many:1 with subjects; 1:many with template-versions, instances.
- **Operations**: list (by subject), get, search.
- **Authorization**: any authenticated user (read published); instructor/admin (create, revise, submit-for-review).

### study-sessions
- **Purpose**: Single practice sittings.
- **Ownership**: learning.
- **Relationships**: many:1 with enrollments; 1:many with attempts; 1:1 with adaptive-queues.
- **Operations**: create (start), get, resume, pause, end, get-analytics.
- **Authorization**: self (own sessions).

### adaptive-queues
- **Purpose**: Session-scoped question queues.
- **Ownership**: scheduling.
- **Relationships**: 1:1 with study-sessions.
- **Operations**: get (current), regenerate.
- **Authorization**: session owner.

### daily-queues
- **Purpose**: Day-scoped question queues.
- **Ownership**: scheduling.
- **Relationships**: many:1 with enrollments.
- **Operations**: get (today).
- **Authorization**: enrollment owner.

### attempts
- **Purpose**: Atomic learning evidence (append-only).
- **Ownership**: assessment.
- **Relationships**: many:1 with question-instances, study-sessions, enrollments; 1:1 with answers.
- **Operations**: create (submit answer), list (by enrollment), get.
- **Authorization**: self (own attempts).

### question-instances
- **Purpose**: Concrete questions served to learners.
- **Ownership**: assessment.
- **Relationships**: many:1 with question-templates (via versions), study-sessions.
- **Operations**: get (current), execute-code (for code questions), abandon.
- **Authorization**: session owner.

### reviews
- **Purpose**: Scheduled spaced-repetition encounters.
- **Ownership**: mastery.
- **Relationships**: many:1 with enrollments, concepts.
- **Operations**: list-due (by enrollment).
- **Authorization**: enrollment owner.

### mastery-scores
- **Purpose**: Per-concept mastery estimates.
- **Ownership**: mastery.
- **Relationships**: many:1 with enrollments, concepts.
- **Operations**: list (by enrollment), get (by concept), get-weak-concepts.
- **Authorization**: self (own scores).

### recommendations
- **Purpose**: Advisory suggestions.
- **Ownership**: learning.
- **Relationships**: many:1 with enrollments.
- **Operations**: list (by enrollment), dismiss.
- **Authorization**: enrollment owner.

### achievements
- **Purpose**: Earned recognitions (includes milestones).
- **Ownership**: learning.
- **Relationships**: many:1 with enrollments, achievement-types.
- **Operations**: list (by enrollment), list-types.
- **Authorization**: self (own achievements).

### streaks
- **Purpose**: Decorative engagement metrics.
- **Ownership**: learning.
- **Relationships**: 1:1 with enrollments.
- **Operations**: get (own).
- **Authorization**: enrollment owner.

### notifications
- **Purpose**: User notifications (in-app, email, push).
- **Ownership**: administration.
- **Relationships**: many:1 with users.
- **Operations**: list (own), mark-read, dismiss, update-preferences.
- **Authorization**: self.

### subscriptions
- **Purpose**: Billing relationships.
- **Ownership**: billing.
- **Relationships**: many:1 with users, billing-plans.
- **Operations**: create (subscribe), get (own), upgrade, downgrade, cancel.
- **Authorization**: self (own subscription).

### billing-plans
- **Purpose**: Available subscription offerings.
- **Ownership**: billing.
- **Relationships**: 1:many with subscriptions.
- **Operations**: list.
- **Authorization**: any authenticated user.

### invoices
- **Purpose**: Billing records.
- **Ownership**: billing.
- **Relationships**: many:1 with subscriptions, users.
- **Operations**: list (own), get.
- **Authorization**: self (own invoices).

### dashboard
- **Purpose**: Aggregated "what next?" landing data.
- **Ownership**: learning.
- **Relationships**: composite (streak, weak concepts, recommendations).
- **Operations**: get (own).
- **Authorization**: self.

### progress
- **Purpose**: Mastery-over-time, retention, velocity.
- **Ownership**: analytics.
- **Relationships**: composite (snapshots, trends).
- **Operations**: get (own).
- **Authorization**: self.

### search
- **Purpose**: Search across concepts, templates.
- **Ownership**: content (read).
- **Operations**: get (search).
- **Authorization**: any authenticated user (learners search published; instructors search drafts).

---

## Admin-Facing Resources (under `/api/v1/admin/...`)

### admin/users
- **Purpose**: User management (suspend, reactivate, anonymize, search).
- **Authorization**: admin only.

### admin/subjects
- **Purpose**: Subject lifecycle (create, publish, deprecate).
- **Authorization**: admin only.

### admin/content-packs
- **Purpose**: Content authoring and review workflow.
- **Authorization**: instructor (author, submit); instructor/admin (review); admin (publish).

### admin/content-review-requests
- **Purpose**: Review queue management.
- **Authorization**: instructor/admin (reviewer).

### admin/content-versions
- **Purpose**: Content version history and deprecation.
- **Authorization**: instructor/admin.

### admin/question-templates
- **Purpose**: Template authoring (full CRUD including drafts).
- **Authorization**: instructor/admin.

### admin/algorithm-versions
- **Purpose**: Algorithm version management and promotion.
- **Authorization**: admin only.

### admin/feature-flags
- **Purpose**: Feature flag CRUD and targeting.
- **Authorization**: admin (engineers via admin portal).

### admin/system-settings
- **Purpose**: System-wide configuration.
- **Authorization**: admin only.

### admin/audit-logs
- **Purpose**: Audit log search.
- **Authorization**: admin only.

### admin/gdpr-requests
- **Purpose**: GDPR request management.
- **Authorization**: admin only.

### admin/organizations
- **Purpose**: B2B organization management.
- **Authorization**: admin (platform); org admin (scoped).

### admin/tenants
- **Purpose**: Tenant management (content isolation).
- **Authorization**: admin only.

### admin/scheduling-configs
- **Purpose**: Per-subject scheduling configuration.
- **Authorization**: admin only.

### admin/analytics
- **Purpose**: Aggregate analytics (cohort retention, concept statistics, template statistics).
- **Authorization**: instructor/admin (concept/template stats); admin only (cohort, platform).

### admin/roles
- **Purpose**: Role grants and revocations.
- **Authorization**: admin only.

### admin/migrations
- **Purpose**: Schema migration history (read-only).
- **Authorization**: admin only.

### admin/background-jobs
- **Purpose**: Background job monitoring and dead-letter management.
- **Authorization**: admin only.

---

## Operation-to-Command/Query Mapping

Every API operation maps to a Command (write) or Query (read) from Task 005. The mapping is documented per-endpoint in `03-openapi-spec.yaml` (via the `x-command` or `x-query` extension field).

### Example mappings

| Endpoint | Method | Command/Query |
|---|---|---|
| `/auth/register` | POST | RegisterUser (command) |
| `/auth/login` | POST | LoginUser (command) |
| `/users/me` | GET | GetUser (query) |
| `/enrollments` | POST | EnrollInSubject (command) |
| `/study-sessions` | POST | StartStudySession (command) |
| `/study-sessions/{id}/end` | POST | EndStudySession (command) |
| `/adaptive-queue` | GET | GetAdaptiveQueue (query) |
| `/attempts` | POST | SubmitAnswer (command) |
| `/mastery-scores` | GET | GetConceptProgress (query) |
| `/recommendations` | GET | GetRecommendations (query) |
| `/admin/content-packs` | POST | SubmitContentPackForReview (command) |
| `/admin/algorithm-versions/{id}/publish` | POST | PublishAlgorithmVersion (command) |

---

## Authorization Model

| Role | Learner-Facing Resources | Admin Resources |
|---|---|---|
| `learner` | Own data only (read/write) | None |
| `instructor` | Own data + subject content (read published + drafts for their subjects) | Content authoring/review for their subjects |
| `administrator` | Own data + all users (admin operations) | All admin resources |
| `org_admin` (future) | Own data + org members (read) | Org-scoped admin |

Authorization is enforced at two layers (per ASD Section 12.2):
1. **Controller layer**: role check via `Depends(require_role(...))`.
2. **Use case layer**: resource ownership check (e.g., "is this attempt owned by the requesting user?").

---

*End of Resource Model.*
