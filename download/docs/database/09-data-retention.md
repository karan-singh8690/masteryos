# 09 — Data Retention

> Retention policy per data category, soft delete vs hard delete, GDPR compliance.
> Implements ASD Section 12.8 and ASD Section 17.4.

---

## Retention Principles

1. **Retain learning data indefinitely (anonymized)** — the Attempt corpus is the data moat; it is never deleted, only anonymized.
2. **Retain operational data per its useful life** — sessions, notifications, etc. have defined retention periods.
3. **Retain compliance data per legal requirements** — audit logs (7 years), invoices (7 years for tax).
4. **Soft delete for recoverability; hard delete for GDPR** — most tables use soft delete; PII is hard-deleted on GDPR erasure.
5. **Partition detachment for archival** — partitioned tables are archived by detaching old partitions, not by deleting rows.

---

## Retention Policy by Table

| Table | Retention | Soft/Hard Delete | Archival | GDPR Treatment |
|---|---|---|---|---|
| `identity.users` | Indefinite (anonymized after deletion) | Soft (`deleted_at`), then anonymize | None | PII purged on erasure; user_id retained for referential integrity. |
| `identity.user_profiles` | Indefinite (anonymized after deletion) | Soft, then anonymize | None | PII (display_name, etc.) purged on erasure. |
| `identity.user_credentials` | While account active + 90 days | Hard delete on credential unlink | None | Purged on erasure. |
| `identity.sessions` | 90 days post-expiry | Hard delete | None | Purged on erasure. |
| `content.*` (all content tables) | Indefinite (deprecated, not deleted) | Soft (`status = 'deprecated'`) | None | Not PII; no GDPR treatment. |
| `learning.learner_enrollments` | 90 days post-unenrollment, then anonymize | Soft, then anonymize | None | `user_id` retained (referential); enrollment metadata anonymized. |
| `learning.learning_goals` | 1 year post-completion/abandonment | Hard delete | None | Purged on erasure. |
| `learning.study_plans` | 1 year post-archive | Hard delete | None | Purged on erasure. |
| `learning.study_sessions` | Indefinite (anonymized) | Soft (none; retained) | None | `learner_enrollment_id` retained; PII (none) — sessions are not PII. |
| `learning.learning_sessions` | Indefinite (anonymized) | Soft | Partition archival after 2 years | Same as study_sessions. |
| `learning.practice_queues` | 24 hours post-session-end | Hard delete | None | Purged on erasure. |
| `learning.recommendations` | 1 year | Hard delete | None | Purged on erasure. |
| `learning.recommendation_history` | 1 year | Hard delete (partition detach) | Partition archival after 1 year | Purged on erasure. |
| `learning.achievements` | Indefinite (anonymized) | Soft | None | `learner_enrollment_id` retained; PII (none). |
| `learning.streaks` | 1 year post-last-update | Hard delete | None | Purged on erasure. |
| `assessment.question_instances` | Indefinite (anonymized) | Soft | Partition archival after 2 years | `learner_enrollment_id` retained; no PII in instance data. |
| `assessment.attempts` | **Indefinite (anonymized)** — the data moat | Append-only (no delete) | Partition archival after 2 years (cold storage) | `learner_enrollment_id` retained; no PII in attempt data. |
| `assessment.answers` | Indefinite (anonymized) | Append-only | Partition archival after 2 years | Code answers may contain PII (e.g., learner-typed strings); anonymized by replacing with `[anonymized]` on erasure. |
| `mastery.algorithm_versions` | Indefinite | Append-only | None | Not PII. |
| `mastery.mastery_scores` | Indefinite (anonymized) | Soft | None | `learner_enrollment_id` retained; scores are not PII. |
| `mastery.reviews` | Indefinite (anonymized) | Soft | None | Same as mastery_scores. |
| `mastery.learner_misconceptions` | Indefinite (anonymized) | Soft | None | Same as mastery_scores. |
| `scheduling.daily_queues` | 30 days | Hard delete | None | Purged on erasure. |
| `scheduling.scheduling_configs` | Indefinite (versioned) | Soft | None | Not PII. |
| `analytics.learner_daily_snapshots` | 5 years | Hard delete (partition detach) | Partition archival after 5 years | `learner_enrollment_id` retained; scores are not PII. |
| `analytics.concept_statistics` | Indefinite | Append-only | None | Not PII. |
| `analytics.template_statistics` | Indefinite | Append-only | None | Not PII. |
| `billing.billing_plans` | Indefinite (versioned) | Soft | None | Not PII. |
| `billing.subscriptions` | 7 years (tax compliance) | Soft | None | `user_id` retained; subscription metadata retained for tax. |
| `billing.invoices` | 7 years (tax compliance) | Append-only | None | `user_id` retained; invoice data retained for tax. |
| `administration.audit_logs` | 7 years | Append-only | Partition archival after 2 years | `actor_user_id` anonymized on erasure (set to NULL); action and target retained. |
| `administration.feature_flags` | Indefinite (retired, not deleted) | Soft | None | Not PII. |
| `administration.feature_flag_assignments` | 90 days post-retirement | Hard delete | None | Purged on erasure. |
| `administration.system_settings` | Indefinite (versioned) | Soft | None | Not PII. |
| `administration.gdpr_requests` | 7 years (compliance audit) | Append-only | None | `user_id` retained (the request itself is the audit trail); request metadata retained. |
| `administration.organizations` | Indefinite (dissolved, not deleted) | Soft | None | Organization name may be PII (business name); retained for billing audit. |
| `administration.organization_members` | 7 years post-leave | Soft | None | `user_id` retained for audit. |
| `administration.notifications` | 30 days post-delivery | Hard delete (partition detach) | None | Purged on erasure. |
| `infrastructure.outbox_events` | 90 days post-dispatch | Hard delete (partition detach) | Partition archival after 90 days | `actor_user_id` anonymized on erasure. |
| `infrastructure.background_jobs` | 30 days post-completion; 90 days for dead-lettered | Hard delete (partition detach) | None | Purged on erasure (payload may contain user_id). |
| `infrastructure.migration_history` | Indefinite | Append-only | None | Not PII. |

---

## Soft Delete vs Hard Delete

### Soft Delete

Soft delete sets `deleted_at` (or `status = 'deprecated'`, etc.) without removing the row. The row remains queryable for audit and analytics; application queries filter `WHERE deleted_at IS NULL`.

**Used for**:
- `users`, `user_profiles` — recoverable for 14 days, then anonymized.
- `subjects`, `concepts`, `learning_objectives`, `misconceptions`, `question_templates` — deprecated, not deleted (historical Attempts reference them).
- `learner_enrollments` — unenrolled, retained 90 days for re-enrollment.
- `subscriptions` — canceled, retained 7 years for tax.
- `organizations` — dissolved, retained for audit.
- `feature_flags`, `system_settings` — retired/deprecated, not deleted.

**Why soft delete**: recoverability (user account recovery, content restoration), auditability (historical references), and referential integrity (Attempts reference deprecated Concepts).

### Hard Delete

Hard delete removes the row entirely (or detaches the partition). The row is no longer queryable.

**Used for**:
- `sessions`, `practice_queues`, `daily_queues`, `notifications` — short retention; no audit need.
- `learning_goals`, `study_plans`, `recommendations`, `recommendation_history`, `streaks` — medium retention; no audit need.
- `user_credentials` — on credential unlink.
- `feature_flag_assignments` — on flag retirement.
- Partitioned tables past retention (via partition detach).

**Why hard delete**: storage cost (these tables are high-volume but low-value historically), privacy (reduce PII surface).

### Append-Only (No Delete of Any Kind)

Append-only tables never UPDATE or DELETE (except GDPR anonymization). Corrections are made by appending compensating records.

**Used for**:
- `attempts`, `answers` (post-submission) — the data moat.
- `audit_logs` — compliance.
- `outbox_events` (dispatched) — audit trail.
- `migration_history` — schema audit.
- `content_versions`, `template_versions`, `algorithm_versions` — immutable snapshots.
- `concept_statistics`, `template_statistics` — nightly snapshots.
- `invoices` — tax compliance.
- `gdpr_requests` — compliance audit.

**Why append-only**: the data is the moat, the audit trail, or the compliance record. Modifying it would destroy its value.

---

## GDPR Compliance

### Right to Access (Article 15)

When a user submits an access request (`gdpr_requests.request_type = 'access'`):

1. The system compiles all data associated with the user across all tables.
2. The data is exported as a structured JSON or CSV file.
3. The export is delivered to the user via a secure download link (time-limited).
4. The request is marked `completed` with the export reference in `completion_metadata`.

**Data included in the export**:
- `users`, `user_profiles` — identity and profile.
- `user_credentials` — credential types and providers (not password hashes).
- `sessions` — active and recent sessions (IP, user agent, dates).
- `learner_enrollments`, `learning_goals`, `study_plans` — learning state.
- `study_sessions`, `learning_sessions` — engagement history.
- `attempts`, `answers` — full attempt history.
- `mastery_scores`, `reviews`, `learner_misconceptions` — mastery state.
- `recommendations`, `recommendation_history` — recommendations shown.
- `achievements`, `streaks` — recognitions.
- `subscriptions`, `invoices` — billing history.
- `audit_logs` — actions performed by or on the user.
- `notifications` — notifications sent.
- `gdpr_requests` — prior GDPR requests.

**Timeframe**: 30 days from request (legal requirement).

### Right to Erasure (Article 17)

When a user submits an erasure request (`gdpr_requests.request_type = 'erasure'`):

1. The user's account enters a 14-day grace period (`users.status = 'pending_deletion'`). During this period, the user can cancel the erasure.
2. After 14 days, the anonymization process runs:
   - `users.email` is replaced with `anonymized_<uuid>@anonymized.invalid`.
   - `users.email_verified_at` is set to NULL.
   - `users.status` is set to `'anonymized'`.
   - `users.anonymized_at` is set to `now()`.
   - `user_profiles` PII columns (`display_name`, `avatar_url`) are replaced with `[anonymized]`.
   - `user_credentials` rows are hard-deleted.
   - `sessions` rows are hard-deleted.
   - `learning_goals`, `study_plans`, `recommendations`, `recommendation_history`, `streaks`, `notifications`, `feature_flag_assignments` are hard-deleted.
   - `learner_enrollments.user_id` is retained (for referential integrity with `attempts`); `learner_enrollments.status` is set to `'anonymized'`.
   - `attempts`, `answers`, `mastery_scores`, `reviews`, `learner_misconceptions`, `achievements`, `study_sessions`, `learning_sessions`, `question_instances` retain `learner_enrollment_id` (via the enrollment's `user_id` link, which is now anonymized); no PII is in these tables.
   - `answers.submitted_answer` for code/free-response questions may contain learner-typed PII; these are replaced with `[anonymized]` if the answer_type is `free_response` (code answers are retained because they are not PII and are needed for analytics).
   - `audit_logs.actor_user_id` is set to NULL (the action is retained; the actor is anonymized).
   - `outbox_events.actor_user_id` is set to NULL.
   - `subscriptions`, `invoices` — `user_id` is retained (tax compliance requires 7 years of billing records); the subscription is canceled if active.
   - `organization_members` rows are hard-deleted.
   - `gdpr_requests` — the erasure request itself is retained (it is the audit trail); `user_id` is retained.

3. The request is marked `completed` with anonymization details in `completion_metadata`.

**What is retained after erasure**:
- Anonymized `users` row (for referential integrity).
- `attempts`, `mastery_scores`, etc. (no PII; the data moat is preserved).
- `subscriptions`, `invoices` (tax compliance).
- `audit_logs`, `gdpr_requests` (compliance audit; actor anonymized).
- `content_versions`, `template_versions`, `algorithm_versions` (not PII).

**Timeframe**: 30 days from request (legal requirement); the 14-day grace period is internal policy.

### Right to Portability (Article 20)

When a user submits a portability request (`gdpr_requests.request_type = 'portability'`):

1. The system compiles the user's data in a machine-readable format (JSON, structured per the GDPR data portability guidelines).
2. The export includes only data the user provided or that was generated by their activity (not inferred data like mastery scores, which are derived).
3. The export is delivered via a secure download link.

**Timeframe**: 30 days from request.

### Consent Management

Consent records are stored in `audit_logs` (action = 'consent.grant' or 'consent.withdraw'). Withdrawal of consent triggers immediate cessation of the relevant processing (e.g., marketing emails stop).

---

## Anonymization Process

The anonymization process is a background job triggered by `gdpr_requests` with `request_type = 'erasure'` and `status = 'pending'` past the 14-day grace period.

**Implementation**:

```sql
-- Anonymize the user
UPDATE identity.users
SET email = 'anonymized_' || id::text || '@anonymized.invalid',
    email_verified_at = NULL,
    status = 'anonymized',
    anonymized_at = now()
WHERE id = $user_id AND status = 'pending_deletion';

-- Anonymize the profile
UPDATE identity.user_profiles
SET display_name = '[anonymized]',
    avatar_url = NULL,
    preferences = '{}'
WHERE user_id = $user_id;

-- Hard-delete credentials and sessions
DELETE FROM identity.user_credentials WHERE user_id = $user_id;
DELETE FROM identity.sessions WHERE user_id = $user_id;

-- Hard-delete transitive data
DELETE FROM learning.learning_goals WHERE learner_enrollment_id IN (SELECT id FROM learning.learner_enrollments WHERE user_id = $user_id);
DELETE FROM learning.study_plans WHERE learner_enrollment_id IN (SELECT id FROM learning.learner_enrollments WHERE user_id = $user_id);
DELETE FROM learning.recommendations WHERE learner_enrollment_id IN (SELECT id FROM learning.learner_enrollments WHERE user_id = $user_id);
DELETE FROM learning.recommendation_history WHERE recommendation_id IN (SELECT id FROM learning.recommendations WHERE learner_enrollment_id IN (SELECT id FROM learning.learner_enrollments WHERE user_id = $user_id));
DELETE FROM learning.streaks WHERE learner_enrollment_id IN (SELECT id FROM learning.learner_enrollments WHERE user_id = $user_id);
DELETE FROM learning.practice_queues WHERE study_session_id IN (SELECT id FROM learning.study_sessions WHERE learner_enrollment_id IN (SELECT id FROM learning.learner_enrollments WHERE user_id = $user_id));
DELETE FROM administration.feature_flag_assignments WHERE user_id = $user_id;
DELETE FROM administration.organization_members WHERE user_id = $user_id;

-- Anonymize free-response answers (code answers retained)
UPDATE assessment.answers
SET submitted_answer = '[anonymized]'::jsonb,
    revision_history = '[]'::jsonb
WHERE attempt_id IN (SELECT id FROM assessment.attempts WHERE learner_enrollment_id IN (SELECT id FROM learning.learner_enrollments WHERE user_id = $user_id))
  AND answer_type = 'free_response';

-- Anonymize audit logs and outbox events
UPDATE administration.audit_logs SET actor_user_id = NULL WHERE actor_user_id = $user_id;
UPDATE infrastructure.outbox_events SET actor_user_id = NULL WHERE actor_user_id = $user_id;

-- Mark enrollments as anonymized
UPDATE learning.learner_enrollments
SET status = 'anonymized',
    anonymized_at = now()
WHERE user_id = $user_id;

-- Cancel active subscriptions
UPDATE billing.subscriptions
SET status = 'canceled',
    canceled_at = now()
WHERE user_id = $user_id AND status = 'active';
```

The job runs in a single transaction per user (or per batch, if anonymizing multiple users). It is idempotent: re-running on an already-anonymized user is a no-op.

**Notifications**: notifications for the anonymized user are purged (they are short-retention anyway).

---

## Deleted Users

A "deleted user" is an anonymized user. The `users` row remains (for referential integrity with `attempts`, etc.), but all PII is purged and the account is non-functional.

**Re-registration**: the anonymized email (`anonymized_<uuid>@anonymized.invalid`) is unique, so the original email can be re-used for a new account. The new account has no link to the anonymized one (the data moat is anonymized, not transferred).

---

## Retention Enforcement

Retention is enforced by scheduled background jobs:

| Job | Frequency | Action |
|---|---|---|
| Session cleanup | Daily | Hard-delete sessions where `expires_at < now() - interval '90 days'`. |
| Practice queue cleanup | Hourly | Hard-delete practice queues where `expires_at < now()`. |
| Daily queue cleanup | Daily | Hard-delete daily queues where `queue_date < current_date - 30`. |
| Notification cleanup | Daily | Detach notifications partitions older than 30 days. |
| Recommendation cleanup | Daily | Hard-delete recommendations where `created_at < now() - interval '1 year'`. |
| Recommendation history archival | Monthly | Detach recommendation_history partitions older than 1 year; move to cold storage. |
| Streak cleanup | Daily | Hard-delete streaks where `last_study_date < current_date - 365`. |
| Outbox archival | Monthly | Detach outbox_events partitions older than 90 days; move to cold storage. |
| Audit log archival | Monthly | Detach audit_logs partitions older than 2 years; move to cold storage. Retain 7 years total. |
| Learning session archival | Monthly | Detach learning_sessions partitions older than 2 years; move to cold storage. |
| Question instance archival | Monthly | Detach question_instances partitions older than 2 years; move to cold storage. |
| Attempt archival | Monthly | Detach attempts partitions older than 2 years; move to cold storage. (Attempts are retained indefinitely in cold storage; the data moat is never deleted.) |
| Answer archival | Monthly | Detach answers partitions older than 2 years; move to cold storage. |
| Snapshot retention | Monthly | Detach learner_daily_snapshots partitions older than 5 years; move to cold storage or delete. |
| GDPR request processing | Hourly | Process `gdpr_requests` where `status = 'pending'` and grace period elapsed. |

**Job implementation**: each job is a `background_jobs` entry with a corresponding worker. Jobs are idempotent and resumable. Failures are retried with exponential backoff; persistent failures are dead-lettered.

---

## Compliance Documentation

The retention policy is documented in the platform's privacy policy and terms of service. Users are informed of:
- What data is collected.
- How long it is retained.
- How to exercise GDPR rights.
- What is retained after erasure (anonymized aggregates).

The `gdpr_requests` table is the audit trail for compliance; it is retained for 7 years.

---

*End of Data Retention.*
