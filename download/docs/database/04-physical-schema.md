# 04 — Physical Schema

> PostgreSQL implementation details: UUID strategy, timestamps, JSONB usage, ENUMs, composite keys, generated columns, sequences, extensions, schema separation, naming conventions.

---

## 1. PostgreSQL Version

- **Minimum**: PostgreSQL 16.
- **Recommended**: PostgreSQL 16 or 17 (latest stable at deployment time).
- **Rationale**: PG 16+ has improved partitioning performance, better parallel query execution, and JSONB enhancements. PG 17 adds `MERGE ... RETURNING` and incremental backup improvements.
- **Upgrade cadence**: annual major version upgrade, tested against a full-size staging copy.

---

## 2. Schema Separation

The database uses PostgreSQL schemas (not databases) to separate bounded contexts. Each bounded context owns one schema.

```sql
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS content;
CREATE SCHEMA IF NOT EXISTS learning;
CREATE SCHEMA IF NOT EXISTS assessment;
CREATE SCHEMA IF NOT EXISTS mastery;
CREATE SCHEMA IF NOT EXISTS scheduling;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS administration;
CREATE SCHEMA IF NOT EXISTS infrastructure;
```

**Why schemas, not databases:**
- Cross-context queries (with single-writer discipline) are possible within one database.
- Transactional integrity (the outbox pattern, ADR-0012) requires a single database.
- Operational simplicity: one database to back up, monitor, upgrade.
- The single-writer rule (ASD Section 3.3) is enforced by application-layer repository discipline and by PostgreSQL roles (each context's application role has write privileges only to its own schema).

**Cross-schema references**: permitted (e.g., `learning.learner_enrollments.user_id` references `identity.users.id`), but governed by the single-writer rule: only the owning context writes to its tables.

---

## 3. UUID Strategy

- **Type**: `uuid` (PostgreSQL native).
- **Generation**: UUID v7 (time-ordered, sortable, globally unique).
- **Default**: `gen_random_uuid()` for backward compatibility (PG 13+). For UUID v7, a custom function or the `pg_uuidv7` extension (PG 17+ native support expected).
- **Why UUID v7**: time-ordered UUIDs are sortable (improving B-tree index locality for insert-heavy tables like `attempts`), while remaining globally unique (enabling future sharding without key collisions).
- **Why not `bigserial`**: integer sequences create contention on insert-heavy tables and prevent future sharding. UUIDs avoid both.
- **Storage**: 16 bytes per UUID (vs 8 bytes for `bigint`); the storage overhead is acceptable for the global-uniqueness and sharding benefits.

**Migration path to UUID v7**: if the application starts with `gen_random_uuid()` (UUID v4), a later migration to UUID v7 is non-breaking (existing UUIDs remain valid; new inserts use v7). The sort order of mixed v4/v7 UUIDs is not strictly chronological, but this is acceptable because all time-based queries use explicit `created_at` columns, not the UUID.

---

## 4. Timestamp Strategy

- **Type**: `timestamptz` (timestamp with time zone) for all timestamp columns.
- **Why `timestamptz`, not `timestamp`**: `timestamptz` stores the instant (UTC internally), display-converted to the session timezone. This avoids ambiguity when users are in different timezones.
- **Default**: `now()` for `created_at` and `updated_at`.
- **`updated_at` trigger**: a BEFORE UPDATE trigger sets `updated_at = now()` on every row update. This is defined once per table via a trigger function.

```sql
CREATE OR REPLACE FUNCTION infrastructure.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Per-table trigger:
CREATE TRIGGER users_set_updated_at
    BEFORE UPDATE ON identity.users
    FOR EACH ROW EXECUTE FUNCTION infrastructure.set_updated_at();
```

- **Date columns**: `date` for date-only columns (e.g., `queue_date`, `target_date`). Never `timestamptz` for date-only semantics.
- **Interval columns**: `interval` for durations (e.g., `review_interval` in `reviews`).

---

## 5. JSONB Usage

JSONB is used for semi-structured data where:
1. The shape varies per row (e.g., `parameters` in `learning_goals`).
2. The data is opaque to the database (e.g., `payload` in `outbox_events`).
3. The data is read whole (e.g., `entitlements` in `billing_plans`).

**JSONB columns in the schema:**

| Table | Column | Purpose |
|---|---|---|
| `user_profiles` | `preferences` | UI and notification preferences. |
| `learning_goals` | `parameters` | Goal-specific params (minutes per day, etc.). |
| `study_plans` | `weekly_schedule` | Projected weekly concept coverage. |
| `practice_queues` | `question_template_version_ids`, `question_seeds` | Ordered lists. |
| `recommendations` | `payload` | Type-specific payload. |
| `recommendation_history` | `event_data` | Event-specific data. |
| `achievements` | `criteria_snapshot` | Criteria at award time. |
| `achievement_types` | `criteria` | Machine-readable criteria. |
| `question_instances` | `parameter_values`, `rendered_prompt`, `rendered_choices`, `correct_answer`, `distractors_with_tags` | Instantiated question data. |
| `attempts` | `hint_tiers_used` | Which hint tiers, in order. |
| `answers` | `submitted_answer`, `execution_result`, `revision_history` | Learner response data. |
| `template_versions` | `parameter_schema`, `prompt_template`, `correct_answer_generator`, `distractor_generator`, `explanation_template` | Template specification. |
| `distractors` | `generator` | Distractor generation spec. |
| `content_packs` | `artifact_summary` | Counts of artifacts. |
| `audit_logs` | `metadata` | Action-specific details. |
| `feature_flags` | `targeting_rules`, `default_value` | Flag configuration. |
| `feature_flag_assignments` | `override_value` | Per-user override. |
| `system_settings` | `value` | Setting value (typed by `value_type`). |
| `gdpr_requests` | `request_metadata`, `completion_metadata` | Request details. |
| `outbox_events` | `payload` | Event payload. |
| `background_jobs` | `payload` | Job payload. |
| `scheduling_configs` | `priority_weights`, `difficulty_adjustment_bounds` | Scheduling parameters. |
| `daily_queues` | `question_template_version_ids`, `question_seeds`, `completed_items` | Queue contents. |
| `concept_statistics` | (none) | — |
| `template_statistics` | `distractor_distribution` | Distractor selection rates. |
| `billing_plans` | `entitlements` | Feature flags and limits. |
| `notifications` | `payload` | Notification content. |

**JSONB rules:**
1. **Never query into JSONB on the hot path** without a GIN index. If a field is queried frequently, promote it to a column.
2. **GIN index** on JSONB columns that are queried (e.g., `audit_logs.metadata`, `feature_flags.targeting_rules`).
3. **Schema validation**: JSONB columns have an application-layer schema (Pydantic); the database does not enforce JSON Schema (PostgreSQL's JSONB schema validation is limited). Application-layer validation is the gatekeeper.
4. **Versioning**: JSONB payloads that cross the API boundary (e.g., `outbox_events.payload`) carry a `payload_schema_version` column for evolution.

---

## 6. ENUM Strategy

The project uses **`text` columns with CHECK constraints** instead of PostgreSQL `ENUM` types.

**Why not PostgreSQL ENUM:**
- Adding a value to an ENUM requires `ALTER TYPE ... ADD VALUE`, which is non-transactional and can block.
- Removing a value from an ENUM is not supported without a table rewrite.
- ENUM types are not easily portable to other databases (relevant for analytics warehouse replication).
- CHECK constraints provide the same validation with full flexibility.

**Pattern:**

```sql
CREATE TABLE identity.users (
    -- ...
    status text NOT NULL DEFAULT 'pending_verification'
        CHECK (status IN (
            'pending_verification', 'active', 'suspended',
            'deactivated', 'pending_deletion', 'anonymized'
        )),
    -- ...
);
```

**Exception**: PostgreSQL ENUM is used for `attempt_intent` in `attempts` if the values are truly fixed and never expected to change. In practice, all enums in this schema use `text + CHECK`.

**Enum values used in the schema** (centralized here for reference):

| Column | Values |
|---|---|
| `users.status` | pending_verification, active, suspended, deactivated, pending_deletion, anonymized |
| `user_credentials.credential_type` | password, oauth |
| `sessions.revoke_reason` | logout, rotation_anomaly, admin, expired |
| `subjects.status` | draft, published, deprecated |
| `concepts.status` | draft, published, deprecated |
| `concepts.difficulty` | easy, medium, hard |
| `concepts.importance` | low, medium, high |
| `concept_dependencies.dependency_type` | prerequisite, related, reinforces |
| `concept_dependencies.weight` | weak, strong |
| `learning_objectives.status` | draft, published, deprecated |
| `misconceptions.status` | draft, published, deprecated |
| `question_templates.status` | draft, in_review, published, deprecated |
| `question_templates.question_type` | multiple_choice, code_execution, free_response |
| `distractors.tag` | none, misconception |
| `content_versions.status` | active, deprecated |
| `content_review_requests.status` | peer_review, editorial_review, qa_pilot, published, rejected, withdrawn |
| `content_approvals.stage` | peer, editorial, qa |
| `content_approvals.decision` | approve, request_changes, reject |
| `learner_enrollments.status` | pending_onboarding, active, dormant, unenrolled |
| `learning_goals.goal_type` | interview_date, daily_commitment, session_intent, mastery_target |
| `learning_goals.status` | active, completed, abandoned |
| `study_plans.feasibility_status` | feasible, at_risk, infeasible |
| `study_plans.status` | active, superseded, archived |
| `study_sessions.intent` | drill, diagnostic, review, mixed |
| `study_sessions.status` | active, paused, ended, abandoned |
| `practice_queues.queue_type` | adaptive, daily |
| `recommendations.status` | pending, presented, accepted, deferred, dismissed |
| `achievement_types.category` | milestone, graduation, streak, special |
| `achievement_types.status` | active, deprecated |
| `question_instances.status` | served, answered, abandoned |
| `attempts.scoring_outcome` | correct, incorrect, partial |
| `attempts.attempt_intent` | practice, review, diagnostic |
| `answers.answer_type` | multiple_choice, code, free_response |
| `mastery_scores.concept_state` | unseen, novice, developing, proficient, mastered, decayed |
| `mastery_scores.weakness_severity` | none, mild, moderate, severe |
| `reviews.priority` | low, medium, high |
| `reviews.last_review_outcome` | correct, incorrect, partial |
| `learner_misconceptions.severity` | mild, moderate, severe |
| `daily_queues.status` | active, completed, expired |
| `study_plans.status` | active, superseded, archived |
| `subscriptions.status` | active, past_due, canceled, expired |
| `invoices.status` | pending, paid, failed, refunded |
| `audit_logs.outcome` | success, failure |
| `gdpr_requests.request_type` | access, erasure, portability |
| `gdpr_requests.status` | pending, processing, completed, rejected |
| `organizations.status` | active, dissolved |
| `organization_members.role` | member, admin |
| `notifications.channel` | email, push, in_app |
| `notifications.status` | queued, sent, delivered, opened, dismissed, failed |
| `outbox_events.status` | pending, dispatched, dead_lettered |
| `background_jobs.status` | queued, running, completed, failed, dead_lettered |
| `system_settings.value_type` | integer, string, boolean, json |

---

## 7. Composite Keys

The schema uses **no composite primary keys**. All primary keys are single-column UUIDs.

**Composite unique constraints** are used extensively for natural keys:

| Table | Composite Unique | Purpose |
|---|---|---|
| `user_credentials` | `(provider, provider_user_id)` WHERE `credential_type = 'oauth'` | One OAuth link per provider per user. |
| `concept_dependencies` | `(source_concept_id, target_concept_id, dependency_type)` | No duplicate dependency edges. |
| `learning_path_items` | `(learning_path_id, position)`, `(learning_path_id, concept_id)` | No position conflicts, no duplicate concepts. |
| `template_objectives` | `(template_version_id, learning_objective_id)` | No duplicate objective links. |
| `template_concepts` | `(template_version_id, concept_id)` | No duplicate concept links. |
| `distractors` | `(template_version_id, position)` | No position conflicts. |
| `hints` | `(template_version_id, tier)` | One hint per tier. |
| `explanations` | `(template_version_id, outcome_key)` | One explanation per outcome. |
| `content_versions` | `(subject_id, version_number)` | Monotonic version per subject. |
| `template_versions` | `(template_id, version_number)` | Monotonic version per template. |
| `learner_enrollments` | `(user_id, subject_id)` WHERE `status <> 'unenrolled'` | One active enrollment per user per subject. |
| `mastery_scores` | `(learner_enrollment_id, concept_id)` | One score per learner per concept. |
| `reviews` | `(learner_enrollment_id, concept_id)` | One scheduled review per learner per concept. |
| `learner_misconceptions` | `(learner_enrollment_id, misconception_id)` | One record per learner per misconception. |
| `achievements` | `(learner_enrollment_id, achievement_type_id)` | Each achievement awarded once. |
| `daily_queues` | `(learner_enrollment_id, queue_date)` | One queue per learner per day. |
| `practice_queues` | `(study_session_id, queue_type)` | One adaptive + one daily per session. |
| `feature_flag_assignments` | `(feature_flag_id, user_id)` | One override per user per flag. |
| `organization_members` | `(organization_id, user_id)` WHERE `left_at IS NULL` | One active membership per user per org. |

---

## 8. Generated Columns

Generated columns are used for computed values that must be stored (for indexing or query speed).

| Table | Column | Generation | Purpose |
|---|---|---|---|
| `mastery_scores` | `mastery_score_combined` | `GENERATED ALWAYS AS (LEAST(1.000, GREATEST(0.000, (memory_score * 0.4 + durable_mastery_score * 0.6)))) STORED` | The combined mastery score per ADR-0008. The weights (0.4/0.6) are the algorithm's default; algorithm-specific weights are applied at write time, with this generated column as a documented default. |

**Note on the generated column and algorithm versioning:** The `mastery_score_combined` generated column uses a fixed formula (the Algorithm Version 1 default). When the algorithm changes (Algorithm Version 2+), the `mastery_score_combined` column will be updated by the application at write time (overriding the generated column by making it a regular column), and the formula will be versioned via `algorithm_versions.parameters`. The generated column is a Phase 1 convenience; it is not the source of truth for the algorithm.

---

## 9. Sequences

The schema uses **no explicit sequences**. All IDs are UUIDs generated by `gen_random_uuid()`.

**Exception**: `migration_history.version` uses a sequence-like integer, but it is managed by the migration tool (not a PostgreSQL sequence) to ensure cross-environment consistency.

---

## 10. Extensions

Required PostgreSQL extensions:

| Extension | Purpose | Schema |
|---|---|---|
| `pgcrypto` | `gen_random_uuid()` (built-in in PG 13+ but explicitly enabled). | `infrastructure` |
| `citext` | Case-insensitive text for `users.email`. | `infrastructure` |
| `pg_trgm` | Trigram indexes for fuzzy search (concept names, etc.). | `infrastructure` |
| `uuid-ossp` | UUID generation functions (if UUID v7 function is needed). | `infrastructure` |
| `pg_stat_statements` | Query performance monitoring. | `infrastructure` |
| `btree_gin` | Composite GIN+B-tree indexes (for complex queries on JSONB + columns). | `infrastructure` |
| `pgvector` | Vector similarity search (future, for ML embeddings — see `15-future-evolution.md`). | `infrastructure` |

**Installation:**

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA infrastructure;
CREATE EXTENSION IF NOT EXISTS citext SCHEMA infrastructure;
CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA infrastructure;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA infrastructure;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements SCHEMA infrastructure;
CREATE EXTENSION IF NOT EXISTS btree_gin SCHEMA infrastructure;
-- pgvector is installed when ML features are added (Phase 4+).
```

---

## 11. Naming Conventions

### Tables
- `snake_case`, plural: `users`, `attempts`, `mastery_scores`, `question_instances`.
- Join tables: singular+singular: `learning_path_items`, `template_objectives`, `concept_dependencies`.

### Columns
- `snake_case`: `created_at`, `user_id`, `mastery_score_combined`.
- Boolean columns: `is_` or `has_` prefix: `is_active`, `has_hint`, `mfa_enabled`.
- Timestamp columns: `_at` suffix: `created_at`, `published_at`, `last_reviewed_at`.
- Date columns: `_date` suffix: `queue_date`, `target_date`, `snapshot_date`.
- Foreign keys: `<singular_entity>_id`: `user_id`, `concept_id`, `learner_enrollment_id`.
- JSONB columns: descriptive nouns, never `data` or `info`: `parameters`, `payload`, `metadata`.

### Constraints
- Primary keys: `pk_<table>`.
- Unique constraints: `uq_<table>_<purpose>` (e.g., `uq_users_email`).
- Foreign keys: `fk_<table>_<referenced_table>` (e.g., `fk_attempts_learner_enrollments`).
- Check constraints: `chk_<table>_<purpose>` (e.g., `chk_users_status`).
- Indexes: `idx_<table>_<columns>` (e.g., `idx_attempts_learner_enrollment_id_created_at`).

### Schemas
- `snake_case`, singular: `identity`, `content`, `learning`, `assessment`, `mastery`, `scheduling`, `analytics`, `billing`, `administration`, `infrastructure`.

---

## 12. Append-Only Tables

The following tables are **append-only**: no UPDATE, no DELETE (except by the anonymization process for GDPR).

| Table | Enforcement |
|---|---|
| `attempts` | REVOKE UPDATE, DELETE from application role; BEFORE UPDATE/DELETE trigger raises exception. |
| `answers` (post-submission) | REVOKE UPDATE, DELETE; the `revision_history` JSONB captures pre-submission revisions. |
| `audit_logs` | REVOKE UPDATE, DELETE. |
| `outbox_events` (status = 'dispatched') | REVOKE UPDATE on dispatched rows; BEFORE UPDATE trigger raises if `status = 'dispatched'`. |
| `migration_history` | REVOKE UPDATE, DELETE. |
| `content_versions` | REVOKE UPDATE, DELETE (immutable snapshots). |
| `template_versions` | REVOKE UPDATE, DELETE (immutable snapshots). |
| `algorithm_versions` | REVOKE UPDATE, DELETE (immutable snapshots). |

**Trigger pattern for append-only enforcement:**

```sql
CREATE OR REPLACE FUNCTION infrastructure.prevent_modify_append_only()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Table % is append-only; UPDATE and DELETE are forbidden', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER attempts_prevent_update_delete
    BEFORE UPDATE OR DELETE ON assessment.attempts
    FOR EACH ROW EXECUTE FUNCTION infrastructure.prevent_modify_append_only();
```

**Exception for GDPR anonymization**: a dedicated `gdpr_anonymizer` role (used only by the anonymization job) has UPDATE privilege on `attempts` and `answers` for the specific purpose of PII stripping. This role is tightly controlled and audited.

---

## 13. Soft Delete Pattern

Most tables use soft delete via a `deleted_at` timestamp column.

**Pattern:**

```sql
ALTER TABLE identity.users ADD COLUMN deleted_at timestamptz NULL;

-- Queries filter:
SELECT * FROM identity.users WHERE deleted_at IS NULL AND id = $1;

-- Index:
CREATE INDEX idx_users_id_active ON identity.users (id) WHERE deleted_at IS NULL;
```

**Tables with soft delete:**
- `users` (anonymized after grace period)
- `subjects`, `concepts`, `learning_objectives`, `misconceptions`, `question_templates` (deprecated, not deleted)
- `learner_enrollments` (unenrolled, retained 90 days)
- `subscriptions` (canceled, retained for history)
- `organizations` (dissolved, retained for history)

**Tables without soft delete** (append-only or hard-delete):
- `attempts`, `answers`, `audit_logs`, `outbox_events`, `migration_history` (append-only)
- `sessions` (hard-deleted after expiry + 90 days)
- `practice_queues` (hard-deleted after session end + 24 hours)
- `daily_queues` (hard-deleted after 30 days)
- `notifications` (hard-deleted after 30 days, per retention policy)

---

## 14. Optimistic Concurrency Control

`mastery_scores` uses optimistic concurrency to prevent lost updates when two concurrent attempts update the same learner-concept score.

**Pattern:**

```sql
-- The application reads:
SELECT id, version, memory_score, durable_mastery_score, ...
FROM mastery.mastery_scores
WHERE learner_enrollment_id = $1 AND concept_id = $2;

-- The application computes the new score, then writes:
UPDATE mastery.mastery_scores
SET memory_score = $new_memory,
    durable_mastery_score = $new_durable,
    mastery_score_combined = $new_combined,  -- overrides generated column
    version = version + 1,
    last_updated_at = now()
WHERE id = $id AND version = $read_version;

-- If 0 rows affected, a concurrent update occurred; retry.
```

The `version` column is incremented on every update; the WHERE clause ensures the update only succeeds if the version hasn't changed since the read. Conflicts trigger a retry (re-read, recompute, re-write).

---

## 15. Connection Pooling

- **PgBouncer** (or equivalent) sits between the application and PostgreSQL.
- **Pool mode**: `transaction` (server connection returned to pool at end of transaction).
- **Pool size**: tuned per environment (e.g., 100 connections for production, 20 for staging).
- **Application connection count**: the application's async pool (asyncpg) connects to PgBouncer, not directly to PostgreSQL; PgBouncer multiplexes to a smaller PostgreSQL connection count.

---

## 16. Collation and Encoding

- **Encoding**: `UTF8`.
- **Collation**: `en_US.utf8` (default); `citext` for case-insensitive columns.
- **Locale**: `en_US.utf8` (overridable per-column if i18n demands).

---

## 17. Tablespaces

- **Default tablespace**: `pg_default`.
- **Separate tablespaces** for high-volume tables (`attempts`, `answers`, `outbox_events`, `learner_daily_snapshots`) if the storage layer benefits from separation (e.g., faster NVMe for hot tables, slower SATA for cold). This is environment-specific and not mandated by the schema.

---

## 18. Statistics and Query Planning

- **`ANALYZE`**: run automatically by autovacuum; run manually after large data loads.
- **`default_statistics_target`**: 100 (default); increased to 500 for high-cardinality columns in `attempts`, `mastery_scores`.
- **`work_mem`**: tuned per environment (e.g., 64MB for production) to avoid disk-based sorts and hashes.
- **`shared_buffers`**: 25% of available RAM (standard tuning).
- **`effective_cache_size`**: 75% of available RAM (standard tuning).

---

*End of Physical Schema.*
