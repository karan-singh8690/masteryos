# 03 — Logical Schema

> For every entity: columns, primary key, unique constraints, foreign keys, check constraints, nullability, defaults, and business justification.
> SQL DDL is illustrative only; the authoritative physical implementation is in `04-physical-schema.md`.

---

## Conventions (apply to all tables)

- **Primary key**: `id uuid` (UUID v7, time-ordered), default `gen_random_uuid()`.
- **Timestamps**: `created_at timestamptz NOT NULL DEFAULT now()`; `updated_at timestamptz NOT NULL DEFAULT now()` (updated by a trigger on UPDATE).
- **Soft delete**: `deleted_at timestamptz NULL` where applicable; queries filter `WHERE deleted_at IS NULL` unless explicitly querying historical data.
- **Foreign keys**: `<singular_entity>_id uuid NOT NULL REFERENCES <schema>.<table>(id)`. Cascade rules per entity.
- **Check constraints**: named `chk_<table>_<purpose>` for documentation.
- **Naming**: tables are `snake_case` plural; columns are `snake_case`; enums stored as `text` with a CHECK constraint (not PostgreSQL ENUM types, for migration flexibility — see `04-physical-schema.md`).
- **JSONB columns**: used for semi-structured data (parameters, payloads, metadata); GIN-indexed where queried.

---

# Schema: `identity`

## `users`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | Primary key; immutable. |
| `email` | citext | NO | — | Login identifier; case-insensitive (citext extension). |
| `email_verified_at` | timestamptz | YES | NULL | NULL until email is verified; enrollment requires verification. |
| `status` | text | NO | `'pending_verification'` | Account status (enum-like). |
| `mfa_enabled` | boolean | NO | `false` | Whether MFA is enabled. |
| `mfa_secret_encrypted` | bytea | YES | NULL | Encrypted TOTP secret (NULL if MFA disabled). |
| `created_at` | timestamptz | NO | `now()` | — |
| `updated_at` | timestamptz | NO | `now()` | — |
| `deleted_at` | timestamptz | YES | NULL | Soft delete timestamp; NULL when active. |
| `anonymized_at` | timestamptz | YES | NULL | Set when PII is purged post-GDPR erasure. |

- **PK**: `id`
- **Unique**: `email` (where `deleted_at IS NULL` — partial unique index allows re-registration after deletion).
- **Check**: `status IN ('pending_verification', 'active', 'suspended', 'deactivated', 'pending_deletion', 'anonymized')`.
- **Check**: `(deleted_at IS NULL) OR (status = 'pending_deletion' OR status = 'anonymized')` — deletion implies a deletion-status.

**Why this table exists:** Root identity. See `01-domain-model.md`.

---

## `user_profiles`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `user_id` | uuid | NO | — | FK to users; composition. |
| `display_name` | text | NO | — | User-facing name. |
| `timezone` | text | NO | `'UTC'` | IANA timezone (e.g., 'Asia/Kolkata'). |
| `locale` | text | NO | `'en-US'` | BCP-47 locale for i18n. |
| `avatar_url` | text | YES | NULL | Optional avatar. |
| `preferences` | jsonb | NO | `'{}'` | UI and notification preferences. |
| `created_at` | timestamptz | NO | `now()` | — |
| `updated_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `user_id` (1:1 with users).
- **FK**: `user_id` REFERENCES `identity.users(id) ON DELETE CASCADE`.
- **Check**: `timezone ~ '^[A-Za-z_]+/[A-Za-z_]+$'` (loose IANA format check).

---

## `user_credentials`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `user_id` | uuid | NO | — | FK to users. |
| `credential_type` | text | NO | — | 'password' or 'oauth'. |
| `password_hash` | text | YES | NULL | argon2id hash; NULL for oauth credentials. |
| `provider` | text | YES | NULL | 'google', 'github'; NULL for password. |
| `provider_user_id` | text | YES | NULL | OAuth provider's user ID. |
| `created_at` | timestamptz | NO | `now()` | — |
| `updated_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(provider, provider_user_id)` WHERE `credential_type = 'oauth'` (partial index).
- **Unique**: `(user_id)` WHERE `credential_type = 'password'` (one password per user).
- **FK**: `user_id` REFERENCES `identity.users(id) ON DELETE CASCADE`.
- **Check**: `credential_type IN ('password', 'oauth')`.
- **Check**: `(credential_type = 'password' AND password_hash IS NOT NULL) OR (credential_type = 'oauth' AND provider IS NOT NULL AND provider_user_id IS NOT NULL)`.

---

## `sessions`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `user_id` | uuid | NO | — | FK to users. |
| `refresh_token_hash` | text | NO | — | Salted hash of refresh token. |
| `token_family_id` | uuid | NO | `gen_random_uuid()` | For rotation anomaly detection. |
| `device_fingerprint` | text | YES | NULL | Browser fingerprint. |
| `last_ip` | inet | YES | NULL | Last seen IP. |
| `user_agent` | text | YES | NULL | Last seen user agent. |
| `expires_at` | timestamptz | NO | — | Refresh token expiry. |
| `revoked_at` | timestamptz | YES | NULL | NULL when active; set on revoke. |
| `revoke_reason` | text | YES | NULL | 'logout', 'rotation_anomaly', 'admin', 'expired'. |
| `created_at` | timestamptz | NO | `now()` | — |
| `last_seen_at` | timestamptz | NO | `now()` | Updated on each refresh. |

- **PK**: `id`
- **Unique**: `refresh_token_hash`.
- **FK**: `user_id` REFERENCES `identity.users(id) ON DELETE CASCADE`.
- **Check**: `(revoked_at IS NULL) OR (revoke_reason IS NOT NULL)`.
- **Index**: `(user_id)` WHERE `revoked_at IS NULL` (active sessions lookup).

---

# Schema: `content`

## `tenants`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `code` | text | NO | — | Short code (e.g., 'python', 'sql'). |
| `name` | text | NO | — | Display name. |
| `status` | text | NO | `'active'` | 'active', 'deprecated'. |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `code`.

---

## `subjects`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `tenant_id` | uuid | NO | — | FK to tenants; 1:1 in current architecture. |
| `code` | text | NO | — | Short code. |
| `name` | text | NO | — | Display name. |
| `slug` | text | NO | — | URL slug. |
| `description` | text | YES | NULL | Longer description. |
| `status` | text | NO | `'draft'` | 'draft', 'published', 'deprecated'. |
| `default_learning_path_id` | uuid | YES | NULL | FK to learning_paths (set after publish). |
| `created_at` | timestamptz | NO | `now()` | — |
| `published_at` | timestamptz | YES | NULL | — |
| `deprecated_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **Unique**: `code`; `slug`.
- **FK**: `tenant_id` REFERENCES `content.tenants(id)`.
- **FK**: `default_learning_path_id` REFERENCES `content.learning_paths(id)` (deferred; set after first path publish).
- **Check**: `status IN ('draft', 'published', 'deprecated')`.

---

## `learning_paths`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `subject_id` | uuid | NO | — | FK to subjects. |
| `name` | text | NO | — | Display name. |
| `description` | text | YES | NULL | — |
| `graduation_criteria` | jsonb | NO | — | Concepts that must reach Mastered. |
| `estimated_duration_hours` | integer | YES | NULL | Author estimate. |
| `status` | text | NO | `'draft'` | — |
| `created_at` | timestamptz | NO | `now()` | — |
| `published_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **Unique**: `(subject_id, name)`.
- **FK**: `subject_id` REFERENCES `content.subjects(id) ON DELETE RESTRICT`.

---

## `learning_path_items`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learning_path_id` | uuid | NO | — | FK. |
| `concept_id` | uuid | NO | — | FK. |
| `position` | integer | NO | — | 1-indexed order in path. |
| `is_optional` | boolean | NO | `false` | Optional concepts in the path. |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(learning_path_id, position)`; `(learning_path_id, concept_id)`.
- **FK**: `learning_path_id` REFERENCES `content.learning_paths(id) ON DELETE CASCADE`.
- **FK**: `concept_id` REFERENCES `content.concepts(id) ON DELETE RESTRICT`.
- **Check**: `position > 0`.

---

## `concepts`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `subject_id` | uuid | NO | — | FK. |
| `slug` | text | NO | — | URL slug within subject. |
| `name` | text | NO | — | Display name. |
| `description` | text | NO | — | Author description. |
| `difficulty` | text | NO | `'medium'` | 'easy', 'medium', 'hard'. |
| `importance` | text | NO | `'medium'` | 'low', 'medium', 'high'. |
| `status` | text | NO | `'draft'` | 'draft', 'published', 'deprecated'. |
| `current_version_id` | uuid | YES | NULL | FK to a concept_versions table (or embedded; see versioning strategy). |
| `created_at` | timestamptz | NO | `now()` | — |
| `published_at` | timestamptz | YES | NULL | — |
| `deprecated_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **Unique**: `(subject_id, slug)`.
- **FK**: `subject_id` REFERENCES `content.subjects(id) ON DELETE RESTRICT`.
- **Check**: `difficulty IN ('easy', 'medium', 'hard')`.
- **Check**: `importance IN ('low', 'medium', 'high')`.
- **Check**: `status IN ('draft', 'published', 'deprecated')`.

**Note on concept versioning:** Concepts are versioned via `content_versions` (the subject-wide snapshot). Individual concept edits produce a new content version; we do not maintain a separate `concept_versions` table. The `current_version_id` is the content version in which this concept was last published. See `08-versioning-strategy.md`.

---

## `concept_dependencies`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `source_concept_id` | uuid | NO | — | The concept that depends. |
| `target_concept_id` | uuid | NO | — | The prerequisite concept. |
| `dependency_type` | text | NO | — | 'prerequisite', 'related', 'reinforces'. |
| `weight` | text | NO | `'strong'` | 'weak', 'strong'. |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(source_concept_id, target_concept_id, dependency_type)`.
- **FK**: `source_concept_id` REFERENCES `content.concepts(id) ON DELETE CASCADE`.
- **FK**: `target_concept_id` REFERENCES `content.concepts(id) ON DELETE CASCADE`.
- **Check**: `source_concept_id <> target_concept_id` (no self-dependency).
- **Check**: `dependency_type IN ('prerequisite', 'related', 'reinforces')`.
- **Check**: `weight IN ('weak', 'strong')`.

---

## `learning_objectives`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `concept_id` | uuid | NO | — | FK. |
| `statement` | text | NO | — | Verifiable skill statement. |
| `status` | text | NO | `'draft'` | — |
| `created_at` | timestamptz | NO | `now()` | — |
| `published_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **FK**: `concept_id` REFERENCES `content.concepts(id) ON DELETE CASCADE`.
- **Check**: `length(statement) > 10` (reject trivially short objectives).
- **Check**: `status IN ('draft', 'published', 'deprecated')`.

---

## `misconceptions`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learning_objective_id` | uuid | NO | — | FK. |
| `name` | text | NO | — | Short name. |
| `description` | text | NO | — | Description of the incorrect mental model. |
| `remediation` | text | YES | NULL | Remediation strategy. |
| `status` | text | NO | `'draft'` | — |
| `created_at` | timestamptz | NO | `now()` | — |
| `published_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **FK**: `learning_objective_id` REFERENCES `content.learning_objectives(id) ON DELETE CASCADE`.
- **Check**: `status IN ('draft', 'published', 'deprecated')`.

---

## `question_templates`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `subject_id` | uuid | NO | — | FK. |
| `code` | text | NO | — | Author-facing code (e.g., 'py_dict_lookup_complexity_mcq'). |
| `question_type` | text | NO | — | 'multiple_choice', 'code_execution', 'free_response'. |
| `status` | text | NO | `'draft'` | — |
| `current_version_id` | uuid | YES | NULL | FK to template_versions (the current published version). |
| `created_at` | timestamptz | NO | `now()` | — |
| `published_at` | timestamptz | YES | NULL | — |
| `deprecated_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **Unique**: `(subject_id, code)`.
- **FK**: `subject_id` REFERENCES `content.subjects(id) ON DELETE RESTRICT`.
- **FK**: `current_version_id` REFERENCES `content.template_versions(id)`.
- **Check**: `question_type IN ('multiple_choice', 'code_execution', 'free_response')`.
- **Check**: `status IN ('draft', 'in_review', 'published', 'deprecated')`.

---

## `template_versions`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `template_id` | uuid | NO | — | FK to question_templates. |
| `content_version_id` | uuid | NO | — | FK to content_versions. |
| `version_number` | integer | NO | — | Monotonic per template. |
| `parameter_schema` | jsonb | NO | — | JSON Schema for parameters. |
| `prompt_template` | jsonb | NO | — | Parameterized prompt (text or code). |
| `correct_answer_generator` | jsonb | NO | — | Function spec (deterministic). |
| `distractor_generator` | jsonb | YES | NULL | For multiple_choice only. |
| `explanation_template` | jsonb | NO | — | Variant-keyed explanations. |
| `difficulty_estimate` | text | NO | `'medium'` | 'easy', 'medium', 'hard'. |
| `discrimination_estimate` | numeric(3,2) | NO | `'0.50'` | Prior 0.00–1.00. |
| `published_at` | timestamptz | NO | `now()` | — |
| `deprecated_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **Unique**: `(template_id, version_number)`.
- **FK**: `template_id` REFERENCES `content.question_templates(id) ON DELETE RESTRICT`.
- **FK**: `content_version_id` REFERENCES `content.content_versions(id) ON DELETE RESTRICT`.
- **Check**: `difficulty_estimate IN ('easy', 'medium', 'hard')`.
- **Check**: `discrimination_estimate BETWEEN 0.00 AND 1.00`.

---

## `template_objectives`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `template_version_id` | uuid | NO | — | FK. |
| `learning_objective_id` | uuid | NO | — | FK. |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(template_version_id, learning_objective_id)`.
- **FK**: `template_version_id` REFERENCES `content.template_versions(id) ON DELETE CASCADE`.
- **FK**: `learning_objective_id` REFERENCES `content.learning_objectives(id) ON DELETE RESTRICT`.

---

## `template_concepts`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `template_version_id` | uuid | NO | — | FK. |
| `concept_id` | uuid | NO | — | FK. |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(template_version_id, concept_id)`.
- **FK**: `template_version_id` REFERENCES `content.template_versions(id) ON DELETE CASCADE`.
- **FK**: `concept_id` REFERENCES `content.concepts(id) ON DELETE RESTRICT`.

---

## `distractors`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `template_version_id` | uuid | NO | — | FK. |
| `misconception_id` | uuid | YES | NULL | FK; NULL for 'none' tag. |
| `position` | integer | NO | — | Choice position (1-indexed). |
| `generator` | jsonb | NO | — | Function spec to generate the distractor. |
| `tag` | text | NO | `'none'` | 'none' or 'misconception'. |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(template_version_id, position)`.
- **FK**: `template_version_id` REFERENCES `content.template_versions(id) ON DELETE CASCADE`.
- **FK**: `misconception_id` REFERENCES `content.misconceptions(id) ON DELETE SET NULL`.
- **Check**: `position > 0`.
- **Check**: `(tag = 'misconception' AND misconception_id IS NOT NULL) OR (tag = 'none' AND misconception_id IS NULL)`.

---

## `hints`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `template_version_id` | uuid | NO | — | FK. |
| `tier` | integer | NO | — | 1, 2, or 3. |
| `content` | text | NO | — | Hint content (non-answer-revealing). |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(template_version_id, tier)`.
- **FK**: `template_version_id` REFERENCES `content.template_versions(id) ON DELETE CASCADE`.
- **Check**: `tier IN (1, 2, 3)`.

---

## `explanations`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `template_version_id` | uuid | NO | — | FK. |
| `outcome_key` | text | NO | — | 'correct' or a misconception ID string. |
| `misconception_id` | uuid | YES | NULL | FK; NULL for 'correct' variant. |
| `content` | text | NO | — | Explanation content. |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(template_version_id, outcome_key)`.
- **FK**: `template_version_id` REFERENCES `content.template_versions(id) ON DELETE CASCADE`.
- **FK**: `misconception_id` REFERENCES `content.misconceptions(id) ON DELETE RESTRICT`.
- **Check**: `(outcome_key = 'correct' AND misconception_id IS NULL) OR (outcome_key <> 'correct' AND misconception_id IS NOT NULL)`.

---

## `content_versions`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `subject_id` | uuid | NO | — | FK. |
| `tenant_id` | uuid | NO | — | FK. |
| `version_number` | integer | NO | — | Monotonic per subject. |
| `status` | text | NO | `'active'` | 'active', 'deprecated'. |
| `changelog` | text | YES | NULL | Author summary of changes. |
| `published_at` | timestamptz | NO | `now()` | — |
| `deprecated_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **Unique**: `(subject_id, version_number)`.
- **FK**: `subject_id` REFERENCES `content.subjects(id) ON DELETE RESTRICT`.
- **FK**: `tenant_id` REFERENCES `content.tenants(id) ON DELETE RESTRICT`.
- **Check**: `status IN ('active', 'deprecated')`.

---

## `content_packs`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `content_version_id` | uuid | NO | — | FK; the version this pack produced. |
| `author_user_id` | uuid | NO | — | FK to users. |
| `name` | text | NO | — | Pack name. |
| `description` | text | YES | NULL | — |
| `artifact_summary` | jsonb | NO | — | Counts of concepts, templates, etc. |
| `published_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **FK**: `content_version_id` REFERENCES `content.content_versions(id) ON DELETE RESTRICT`.
- **FK**: `author_user_id` REFERENCES `identity.users(id) ON DELETE RESTRICT`.

---

## `content_review_requests`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `content_pack_id` | uuid | NO | — | FK. |
| `author_user_id` | uuid | NO | — | FK. |
| `status` | text | NO | `'peer_review'` | 'peer_review', 'editorial_review', 'qa_pilot', 'published', 'rejected', 'withdrawn'. |
| `submitted_at` | timestamptz | NO | `now()` | — |
| `completed_at` | timestamptz | YES | NULL | — |
| `rejection_reason` | text | YES | NULL | — |

- **PK**: `id`
- **FK**: `content_pack_id` REFERENCES `content.content_packs(id) ON DELETE CASCADE`.
- **FK**: `author_user_id` REFERENCES `identity.users(id) ON DELETE RESTRICT`.
- **Check**: `status IN ('peer_review', 'editorial_review', 'qa_pilot', 'published', 'rejected', 'withdrawn')`.

---

## `content_approvals`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `content_review_request_id` | uuid | NO | — | FK. |
| `reviewer_user_id` | uuid | NO | — | FK. |
| `stage` | text | NO | — | 'peer', 'editorial', 'qa'. |
| `decision` | text | NO | — | 'approve', 'request_changes', 'reject'. |
| `notes` | text | YES | NULL | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **FK**: `content_review_request_id` REFERENCES `content.content_review_requests(id) ON DELETE CASCADE`.
- **FK**: `reviewer_user_id` REFERENCES `identity.users(id) ON DELETE RESTRICT`.
- **Check**: `stage IN ('peer', 'editorial', 'qa')`.
- **Check**: `decision IN ('approve', 'request_changes', 'reject')`.
- **Check**: `reviewer_user_id <> (SELECT author_user_id FROM content_review_requests WHERE id = content_review_request_id)` (no self-review; enforced via trigger).

---

# Schema: `learning`

## `learner_enrollments`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `user_id` | uuid | NO | — | FK. |
| `subject_id` | uuid | NO | — | FK. |
| `learning_path_id` | uuid | YES | NULL | FK; current path. |
| `status` | text | NO | `'pending_onboarding'` | 'pending_onboarding', 'active', 'dormant', 'unenrolled'. |
| `enrolled_at` | timestamptz | NO | `now()` | — |
| `onboarded_at` | timestamptz | YES | NULL | — |
| `last_active_at` | timestamptz | YES | NULL | Updated on each session. |
| `unenrolled_at` | timestamptz | YES | NULL | — |
| `anonymized_at` | timestamptz | YES | NULL | Set when PII is purged post-unenrollment. |

- **PK**: `id`
- **Unique**: `(user_id, subject_id)` WHERE `status <> 'unenrolled'` (partial; allows re-enrollment).
- **FK**: `user_id` REFERENCES `identity.users(id) ON DELETE RESTRICT`.
- **FK**: `subject_id` REFERENCES `content.subjects(id) ON DELETE RESTRICT`.
- **FK**: `learning_path_id` REFERENCES `content.learning_paths(id) ON DELETE SET NULL`.
- **Check**: `status IN ('pending_onboarding', 'active', 'dormant', 'unenrolled')`.

---

## `learning_goals`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `goal_type` | text | NO | — | 'interview_date', 'daily_commitment', 'session_intent', 'mastery_target'. |
| `target_date` | date | YES | NULL | For time-bound goals. |
| `parameters` | jsonb | NO | `'{}'` | Goal-specific params (e.g., minutes per day). |
| `status` | text | NO | `'active'` | 'active', 'completed', 'abandoned'. |
| `created_at` | timestamptz | NO | `now()` | — |
| `completed_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE CASCADE`.
- **Check**: `goal_type IN ('interview_date', 'daily_commitment', 'session_intent', 'mastery_target')`.
- **Check**: `status IN ('active', 'completed', 'abandoned')`.
- **Partial unique**: `(learner_enrollment_id)` WHERE `goal_type = 'interview_date' AND status = 'active'` (one active interview date per enrollment).

---

## `study_plans`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `learning_path_id` | uuid | NO | — | FK. |
| `learning_goal_id` | uuid | NO | — | FK. |
| `projected_graduation_date` | date | YES | NULL | NULL if infeasible. |
| `weekly_schedule` | jsonb | NO | `'{}'` | Projected weekly concept coverage. |
| `feasibility_status` | text | NO | `'feasible'` | 'feasible', 'at_risk', 'infeasible'. |
| `status` | text | NO | `'active'` | 'active', 'superseded', 'archived'. |
| `generated_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE CASCADE`.
- **FK**: `learning_path_id` REFERENCES `content.learning_paths(id) ON DELETE RESTRICT`.
- **FK**: `learning_goal_id` REFERENCES `learning.learning_goals(id) ON DELETE CASCADE`.
- **Check**: `feasibility_status IN ('feasible', 'at_risk', 'infeasible')`.
- **Partial unique**: `(learner_enrollment_id)` WHERE `status = 'active'`.

---

## `study_sessions`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `learning_session_id` | uuid | YES | NULL | FK; set when the learning session is determined. |
| `intent` | text | NO | `'mixed'` | 'drill', 'diagnostic', 'review', 'mixed'. |
| `target_question_count` | integer | YES | NULL | — |
| `started_at` | timestamptz | NO | `now()` | — |
| `ended_at` | timestamptz | YES | NULL | NULL while active. |
| `status` | text | NO | `'active'` | 'active', 'paused', 'ended', 'abandoned'. |
| `question_count` | integer | NO | `0` | Denormalized count for fast dashboard reads. |

- **PK**: `id`
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE CASCADE`.
- **FK**: `learning_session_id` REFERENCES `learning.learning_sessions(id) ON DELETE SET NULL`.
- **Check**: `intent IN ('drill', 'diagnostic', 'review', 'mixed')`.
- **Check**: `status IN ('active', 'paused', 'ended', 'abandoned')`.
- **Check**: `(ended_at IS NULL) = (status IN ('active', 'paused'))`.
- **Check**: `question_count >= 0`.
- **Partial unique**: `(learner_enrollment_id)` WHERE `status IN ('active', 'paused')` (one active session per enrollment).

---

## `learning_sessions`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `started_at` | timestamptz | NO | `now()` | — |
| `ended_at` | timestamptz | YES | NULL | NULL while open. |
| `study_session_count` | integer | NO | `0` | Denormalized. |
| `total_duration_seconds` | integer | NO | `0` | Denormalized. |

- **PK**: `id`
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE CASCADE`.
- **Check**: `(ended_at IS NULL) = (study_session_count > 0 AND ended_at IS NULL)` (open session has no end).
- **Partitioning**: By `started_at` (monthly).

---

## `practice_queues`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `study_session_id` | uuid | NO | — | FK. |
| `queue_type` | text | NO | `'adaptive'` | 'adaptive', 'daily'. |
| `question_template_version_ids` | jsonb | NO | `'[]'` | Ordered list of template version IDs. |
| `question_seeds` | jsonb | NO | `'[]'` | Seeds for instantiation. |
| `current_position` | integer | NO | `0` | Index of the next question. |
| `generated_at` | timestamptz | NO | `now()` | — |
| `expires_at` | timestamptz | NO | `now() + interval '24 hours'` | Purged after expiry. |

- **PK**: `id`
- **Unique**: `(study_session_id, queue_type)` (one adaptive + one daily per session).
- **FK**: `study_session_id` REFERENCES `learning.study_sessions(id) ON DELETE CASCADE`.
- **Check**: `queue_type IN ('adaptive', 'daily')`.
- **Check**: `current_position >= 0`.

---

## `recommendations`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `recommendation_type` | text | NO | — | 'review_due', 'weak_concept_remediation', 'path_progression', etc. |
| `payload` | jsonb | NO | — | Type-specific payload (concept IDs, dates, etc.). |
| `recommendation_score` | numeric(3,2) | NO | — | 0.00–1.00 confidence. |
| `status` | text | NO | `'pending'` | 'pending', 'presented', 'accepted', 'deferred', 'dismissed'. |
| `created_at` | timestamptz | NO | `now()` | — |
| `presented_at` | timestamptz | YES | NULL | — |
| `acted_at` | timestamptz | YES | NULL | — |
| `expires_at` | timestamptz | YES | NULL | When the recommendation is no longer relevant. |

- **PK**: `id`
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE CASCADE`.
- **Check**: `recommendation_score BETWEEN 0.00 AND 1.00`.
- **Check**: `status IN ('pending', 'presented', 'accepted', 'deferred', 'dismissed')`.
- **Index**: `(learner_enrollment_id, status, created_at)`.

---

## `recommendation_history`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `recommendation_id` | uuid | NO | — | FK. |
| `event_type` | text | NO | — | 'created', 'presented', 'accepted', 'deferred', 'dismissed', 'expired'. |
| `event_data` | jsonb | NO | `'{}'` | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **FK**: `recommendation_id` REFERENCES `learning.recommendations(id) ON DELETE CASCADE`.
- **Check**: `event_type IN ('created', 'presented', 'accepted', 'deferred', 'dismissed', 'expired')`.
- **Partitioning**: By `created_at` (monthly).

---

## `achievements`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `achievement_type_id` | uuid | NO | — | FK. |
| `criteria_snapshot` | jsonb | NO | — | The criteria at award time. |
| `awarded_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(learner_enrollment_id, achievement_type_id)` (each achievement awarded once per enrollment).
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE CASCADE`.
- **FK**: `achievement_type_id` REFERENCES `learning.achievement_types(id) ON DELETE RESTRICT`.

---

## `achievement_types`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `subject_id` | uuid | YES | NULL | FK; NULL for platform-wide achievements. |
| `code` | text | NO | — | e.g., 'first_concept_mastered'. |
| `name` | text | NO | — | Display name. |
| `description` | text | NO | — | — |
| `category` | text | NO | — | 'milestone', 'graduation', 'streak', 'special'. |
| `criteria` | jsonb | NO | — | Machine-readable criteria. |
| `icon_url` | text | YES | NULL | Badge icon. |
| `status` | text | NO | `'active'` | 'active', 'deprecated'. |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `code`.
- **FK**: `subject_id` REFERENCES `content.subjects(id) ON DELETE RESTRICT`.
- **Check**: `category IN ('milestone', 'graduation', 'streak', 'special')`.

---

## `streaks`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `current_streak` | integer | NO | `0` | Days. |
| `longest_streak` | integer | NO | `0` | Days. |
| `last_study_date` | date | YES | NULL | — |
| `updated_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `learner_enrollment_id` (1:1).
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE CASCADE`.
- **Check**: `current_streak >= 0`.
- **Check**: `longest_streak >= current_streak`.

---

# Schema: `assessment`

## `question_instances`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `template_version_id` | uuid | NO | — | FK. |
| `content_version_id` | uuid | NO | — | FK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `study_session_id` | uuid | NO | — | FK. |
| `parameter_seed` | bigint | NO | — | Seed for deterministic instantiation. |
| `parameter_values` | jsonb | NO | — | Concrete parameter values. |
| `rendered_prompt` | jsonb | NO | — | The prompt shown to the learner. |
| `rendered_choices` | jsonb | YES | NULL | For multiple_choice. |
| `correct_answer` | jsonb | NO | — | The correct answer. |
| `distractors_with_tags` | jsonb | YES | NULL | Rendered distractors with misconception tags. |
| `served_at` | timestamptz | NO | `now()` | — |
| `answered_at` | timestamptz | YES | NULL | NULL until answered. |
| `status` | text | NO | `'served'` | 'served', 'answered', 'abandoned'. |
| `abandoned_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **FK**: `template_version_id` REFERENCES `content.template_versions(id) ON DELETE RESTRICT`.
- **FK**: `content_version_id` REFERENCES `content.content_versions(id) ON DELETE RESTRICT`.
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE RESTRICT`.
- **FK**: `study_session_id` REFERENCES `learning.study_sessions(id) ON DELETE RESTRICT`.
- **Check**: `status IN ('served', 'answered', 'abandoned')`.
- **Check**: `(answered_at IS NOT NULL) = (status = 'answered')`.
- **Partitioning**: By `served_at` (monthly), co-located with `attempts`.

---

## `attempts`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `question_instance_id` | uuid | NO | — | FK. |
| `learner_enrollment_id` | uuid | NO | — | FK (denormalized for query speed). |
| `study_session_id` | uuid | NO | — | FK (denormalized). |
| `content_version_id` | uuid | NO | — | FK (triple versioning). |
| `template_version_id` | uuid | NO | — | FK (triple versioning). |
| `algorithm_version_id` | uuid | NO | — | FK (triple versioning — the version under which mastery was computed). |
| `scoring_outcome` | text | NO | — | 'correct', 'incorrect', 'partial'. |
| `partial_credit` | numeric(4,3) | YES | NULL | 0.000–1.000 for partial. |
| `time_to_answer_ms` | integer | NO | — | — |
| `hint_used` | boolean | NO | `false` | — |
| `hint_tiers_used` | jsonb | NO | `'[]'` | Which hint tiers, in order. |
| `misconception_id` | uuid | YES | NULL | FK; set when a tagged distractor was selected. |
| `attempt_intent` | text | NO | `'practice'` | 'practice', 'review', 'diagnostic'. |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **FK**: `question_instance_id` REFERENCES `assessment.question_instances(id) ON DELETE RESTRICT`.
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE RESTRICT`.
- **FK**: `study_session_id` REFERENCES `learning.study_sessions(id) ON DELETE RESTRICT`.
- **FK**: `content_version_id` REFERENCES `content.content_versions(id) ON DELETE RESTRICT`.
- **FK**: `template_version_id` REFERENCES `content.template_versions(id) ON DELETE RESTRICT`.
- **FK**: `algorithm_version_id` REFERENCES `mastery.algorithm_versions(id) ON DELETE RESTRICT`.
- **FK**: `misconception_id` REFERENCES `content.misconceptions(id) ON DELETE RESTRICT`.
- **Check**: `scoring_outcome IN ('correct', 'incorrect', 'partial')`.
- **Check**: `(scoring_outcome = 'partial' AND partial_credit IS NOT NULL) OR (scoring_outcome <> 'partial' AND partial_credit IS NULL)`.
- **Check**: `partial_credit BETWEEN 0.000 AND 1.000` (when not null).
- **Check**: `time_to_answer_ms >= 0`.
- **Check**: `attempt_intent IN ('practice', 'review', 'diagnostic')`.
- **Append-only enforcement**: No UPDATE or DELETE; enforced via REVOKE and a trigger. See `13-security.md`.
- **Partitioning**: By `created_at` (monthly).

---

## `answers`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `attempt_id` | uuid | NO | — | FK. |
| `question_instance_id` | uuid | NO | — | FK (denormalized). |
| `answer_type` | text | NO | — | 'multiple_choice', 'code', 'free_response'. |
| `submitted_answer` | jsonb | NO | — | The learner's submitted answer. |
| `execution_result` | jsonb | YES | NULL | For code answers: pass/fail, test output. |
| `revision_count` | integer | NO | `0` | Pre-submission revisions. |
| `revision_history` | jsonb | NO | `'[]'` | Pre-submission revisions (for analytics). |
| `submitted_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `attempt_id` (1:1 with attempts).
- **FK**: `attempt_id` REFERENCES `assessment.attempts(id) ON DELETE RESTRICT`.
- **FK**: `question_instance_id` REFERENCES `assessment.question_instances(id) ON DELETE RESTRICT`.
- **Check**: `answer_type IN ('multiple_choice', 'code', 'free_response')`.
- **Check**: `revision_count >= 0`.
- **Partitioning**: Co-located with `attempts` (same partition key, same monthly partition).

---

# Schema: `mastery`

## `algorithm_versions`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `version_number` | integer | NO | — | Monotonic. |
| `name` | text | NO | — | Display name (e.g., 'Deterministic v1'). |
| `description` | text | YES | NULL | — |
| `parameters` | jsonb | NO | — | Algorithm parameters (decay rates, weights, thresholds). |
| `changelog` | text | YES | NULL | What changed from the previous version. |
| `is_active` | boolean | NO | `false` | Only one version is active at a time. |
| `promoted_at` | timestamptz | YES | NULL | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `version_number`.
- **Partial unique**: `is_active = true` (only one active version) — enforced via a partial unique index on `(is_active) WHERE is_active = true`.
- **Check**: `(is_active = true AND promoted_at IS NOT NULL) OR (is_active = false AND promoted_at IS NULL)`.

---

## `mastery_scores`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `concept_id` | uuid | NO | — | FK. |
| `algorithm_version_id` | uuid | NO | — | FK (the version under which computed). |
| `memory_score` | numeric(4,3) | NO | `0.000` | Short-term recall; 0.000–1.000. |
| `durable_mastery_score` | numeric(4,3) | NO | `0.000` | Long-term mastery; 0.000–1.000. |
| `mastery_score_combined` | numeric(4,3) | NO | — | Generated column (per ADR-0008). |
| `confidence_interval` | numeric(4,3) | NO | `'1.000'` | ± around mastery_score_combined. |
| `evidence_count` | integer | NO | `0` | Number of attempts underlying this score. |
| `concept_state` | text | NO | `'unseen'` | 'unseen', 'novice', 'developing', 'proficient', 'mastered', 'decayed'. |
| `weakness_severity` | text | NO | `'none'` | 'none', 'mild', 'moderate', 'severe'. |
| `version` | integer | NO | `1` | Optimistic concurrency control. |
| `last_attempt_at` | timestamptz | YES | NULL | Denormalized for fast "last studied" queries. |
| `last_updated_at` | timestamptz | NO | `now()` | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(learner_enrollment_id, concept_id)`.
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE CASCADE`.
- **FK**: `concept_id` REFERENCES `content.concepts(id) ON DELETE RESTRICT`.
- **FK**: `algorithm_version_id` REFERENCES `mastery.algorithm_versions(id) ON DELETE RESTRICT`.
- **Check**: `memory_score BETWEEN 0.000 AND 1.000`.
- **Check**: `durable_mastery_score BETWEEN 0.000 AND 1.000`.
- **Check**: `mastery_score_combined BETWEEN 0.000 AND 1.000`.
- **Check**: `confidence_interval BETWEEN 0.000 AND 1.000`.
- **Check**: `evidence_count >= 0`.
- **Check**: `concept_state IN ('unseen', 'novice', 'developing', 'proficient', 'mastered', 'decayed')`.
- **Check**: `weakness_severity IN ('none', 'mild', 'moderate', 'severe')`.
- **Check**: `version > 0`.
- **Generated column**: `mastery_score_combined` is computed from `memory_score` and `durable_mastery_score` via the algorithm's formula (stored in `algorithm_versions.parameters`). Implementation note: PostgreSQL generated columns cannot reference other tables, so the formula is a simple function of the two columns; the exact formula is part of the algorithm spec and applied at write time, with a generated column for redundancy/checking. See `04-physical-schema.md`.

---

## `reviews`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `concept_id` | uuid | NO | — | FK. |
| `algorithm_version_id` | uuid | NO | — | FK. |
| `scheduled_by_attempt_id` | uuid | YES | NULL | FK; the attempt that scheduled this review. |
| `due_at` | timestamptz | NO | — | When the review is due. |
| `priority` | text | NO | `'medium'` | 'low', 'medium', 'high'. |
| `review_interval` | interval | NO | — | Current interval (e.g., '7 days'). |
| `last_reviewed_at` | timestamptz | YES | NULL | — |
| `last_review_outcome` | text | YES | NULL | 'correct', 'incorrect', 'partial'. |
| `created_at` | timestamptz | NO | `now()` | — |
| `updated_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(learner_enrollment_id, concept_id)`.
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE CASCADE`.
- **FK**: `concept_id` REFERENCES `content.concepts(id) ON DELETE RESTRICT`.
- **FK**: `algorithm_version_id` REFERENCES `mastery.algorithm_versions(id) ON DELETE RESTRICT`.
- **FK**: `scheduled_by_attempt_id` REFERENCES `assessment.attempts(id) ON DELETE SET NULL`.
- **Check**: `priority IN ('low', 'medium', 'high')`.
- **Check**: `last_review_outcome IN ('correct', 'incorrect', 'partial')` (when not null).

---

## `learner_misconceptions`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `misconception_id` | uuid | NO | — | FK. |
| `detection_count` | integer | NO | `1` | — |
| `severity` | text | NO | `'mild'` | 'mild', 'moderate', 'severe'. |
| `first_detected_at` | timestamptz | NO | `now()` | — |
| `last_detected_at` | timestamptz | NO | `now()` | — |
| `cleared_at` | timestamptz | YES | NULL | Set when the learner demonstrates mastery. |
| `created_at` | timestamptz | NO | `now()` | — |
| `updated_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(learner_enrollment_id, misconception_id)`.
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE CASCADE`.
- **FK**: `misconception_id` REFERENCES `content.misconceptions(id) ON DELETE CASCADE`.
- **Check**: `detection_count >= 1`.
- **Check**: `severity IN ('mild', 'moderate', 'severe')`.

---

# Schema: `scheduling`

## `daily_queues`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `queue_date` | date | NO | — | The learner's local date. |
| `question_template_version_ids` | jsonb | NO | `'[]'` | Ordered list. |
| `question_seeds` | jsonb | NO | `'[]'` | Seeds for instantiation. |
| `completed_items` | jsonb | NO | `'[]'` | IDs of completed question instances. |
| `status` | text | NO | `'active'` | 'active', 'completed', 'expired'. |
| `generated_at` | timestamptz | NO | `now()` | — |
| `completed_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **Unique**: `(learner_enrollment_id, queue_date)`.
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE CASCADE`.
- **Check**: `status IN ('active', 'completed', 'expired')`.

---

## `scheduling_configs`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `subject_id` | uuid | NO | — | FK. |
| `version` | integer | NO | `1` | Config version. |
| `default_queue_size` | integer | NO | `15` | — |
| `cooldown_minutes` | integer | NO | `30` | Per-concept cooldown. |
| `priority_weights` | jsonb | NO | — | Weights for urgency, importance, weakness, etc. |
| `difficulty_adjustment_bounds` | jsonb | NO | — | e.g., {"min": -0.20, "max": 0.20}. |
| `mastery_threshold_proficient` | numeric(3,2) | NO | `'0.70'` | — |
| `mastery_threshold_mastered` | numeric(3,2) | NO | `'0.85'` | — |
| `memory_threshold` | numeric(3,2) | NO | `'0.50'` | — |
| `is_active` | boolean | NO | `true` | — |
| `created_at` | timestamptz | NO | `now()` | — |
| `updated_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Partial unique**: `(subject_id)` WHERE `is_active = true` (one active config per subject).
- **FK**: `subject_id` REFERENCES `content.subjects(id) ON DELETE RESTRICT`.
- **Check**: `default_queue_size BETWEEN 5 AND 50`.
- **Check**: `cooldown_minutes BETWEEN 5 AND 240`.
- **Check**: `mastery_threshold_proficient BETWEEN 0.00 AND 1.00`.
- **Check**: `mastery_threshold_mastered > mastery_threshold_proficient`.
- **Check**: `memory_threshold BETWEEN 0.00 AND 1.00`.

---

# Schema: `analytics`

## `learner_daily_snapshots`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `learner_enrollment_id` | uuid | NO | — | FK. |
| `concept_id` | uuid | NO | — | FK. |
| `snapshot_date` | date | NO | — | — |
| `memory_score` | numeric(4,3) | NO | — | — |
| `durable_mastery_score` | numeric(4,3) | NO | — | — |
| `mastery_score_combined` | numeric(4,3) | NO | — | — |
| `concept_state` | text | NO | — | — |
| `evidence_count` | integer | NO | — | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(learner_enrollment_id, concept_id, snapshot_date)`.
- **FK**: `learner_enrollment_id` REFERENCES `learning.learner_enrollments(id) ON DELETE RESTRICT` (anonymization handled by application).
- **FK**: `concept_id` REFERENCES `content.concepts(id) ON DELETE RESTRICT`.
- **Check**: scores BETWEEN 0.000 AND 1.000.
- **Partitioning**: By `snapshot_date` (monthly).

---

## `concept_statistics`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `concept_id` | uuid | NO | — | FK. |
| `content_version_id` | uuid | NO | — | FK. |
| `snapshot_date` | date | NO | — | — |
| `avg_mastery_score` | numeric(4,3) | YES | NULL | — |
| `success_rate` | numeric(4,3) | YES | NULL | — |
| `median_time_to_mastery_days` | numeric(6,2) | YES | NULL | — |
| `retention_30d` | numeric(4,3) | YES | NULL | — |
| `learner_count` | integer | NO | `0` | — |
| `attempt_count` | integer | NO | `0` | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(concept_id, content_version_id, snapshot_date)`.
- **FK**: `concept_id` REFERENCES `content.concepts(id) ON DELETE RESTRICT`.
- **FK**: `content_version_id` REFERENCES `content.content_versions(id) ON DELETE RESTRICT`.

---

## `template_statistics`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `template_version_id` | uuid | NO | — | FK. |
| `snapshot_date` | date | NO | — | — |
| `success_rate` | numeric(4,3) | YES | NULL | — |
| `discrimination` | numeric(3,2) | YES | NULL | — |
| `distractor_distribution` | jsonb | YES | NULL | — |
| `avg_time_to_answer_ms` | integer | YES | NULL | — |
| `hint_usage_rate` | numeric(4,3) | YES | NULL | — |
| `attempt_count` | integer | NO | `0` | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(template_version_id, snapshot_date)`.
- **FK**: `template_version_id` REFERENCES `content.template_versions(id) ON DELETE RESTRICT`.

---

# Schema: `billing`

## `billing_plans`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `code` | text | NO | — | 'free', 'pro', 'interview_plus'. |
| `version_number` | integer | NO | `1` | — |
| `name` | text | NO | — | — |
| `price_cents` | integer | NO | `0` | — |
| `currency` | text | NO | `'USD'` | ISO 4217. |
| `billing_period` | text | NO | `'monthly'` | 'monthly', 'annual'. |
| `entitlements` | jsonb | NO | — | Feature flags and limits. |
| `is_active` | boolean | NO | `true` | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(code, version_number)`.
- **Check**: `price_cents >= 0`.
- **Check**: `billing_period IN ('monthly', 'annual')`.

---

## `subscriptions`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `user_id` | uuid | NO | — | FK. |
| `billing_plan_id` | uuid | NO | — | FK. |
| `status` | text | NO | `'active'` | 'active', 'past_due', 'canceled', 'expired'. |
| `current_period_start` | date | NO | — | — |
| `current_period_end` | date | NO | — | — |
| `canceled_at` | date | YES | NULL | — |
| `payment_provider` | text | NO | `'stripe'` | — |
| `provider_subscription_id` | text | YES | NULL | — |
| `created_at` | timestamptz | NO | `now()` | — |
| `updated_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **FK**: `user_id` REFERENCES `identity.users(id) ON DELETE RESTRICT`.
- **FK**: `billing_plan_id` REFERENCES `billing.billing_plans(id) ON DELETE RESTRICT`.
- **Check**: `status IN ('active', 'past_due', 'canceled', 'expired')`.
- **Partial unique**: `(user_id)` WHERE `status = 'active'` (one active subscription per user).

---

## `invoices`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `subscription_id` | uuid | NO | — | FK. |
| `user_id` | uuid | NO | — | FK (denormalized). |
| `amount_cents` | integer | NO | — | — |
| `currency` | text | NO | `'USD'` | — |
| `status` | text | NO | — | 'pending', 'paid', 'failed', 'refunded'. |
| `provider_invoice_id` | text | YES | NULL | — |
| `issued_at` | date | NO | — | — |
| `paid_at` | date | YES | NULL | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **FK**: `subscription_id` REFERENCES `billing.subscriptions(id) ON DELETE RESTRICT`.
- **FK**: `user_id` REFERENCES `identity.users(id) ON DELETE RESTRICT`.
- **Check**: `status IN ('pending', 'paid', 'failed', 'refunded')`.
- **Check**: `amount_cents >= 0`.

---

# Schema: `administration`

## `audit_logs`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `actor_user_id` | uuid | YES | NULL | FK; NULL for system actions. |
| `action` | text | NO | — | 'content.publish', 'user.suspend', etc. |
| `target_type` | text | NO | — | 'user', 'concept', 'subscription', etc. |
| `target_id` | uuid | YES | NULL | NULL for system-wide actions. |
| `metadata` | jsonb | NO | `'{}'` | Action-specific details. |
| `actor_ip` | inet | YES | NULL | — |
| `user_agent` | text | YES | NULL | — |
| `correlation_id` | uuid | YES | NULL | For tracing. |
| `outcome` | text | NO | `'success'` | 'success', 'failure'. |
| `failure_reason` | text | YES | NULL | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **FK**: `actor_user_id` REFERENCES `identity.users(id) ON DELETE SET NULL`.
- **Check**: `outcome IN ('success', 'failure')`.
- **Check**: `(outcome = 'failure') = (failure_reason IS NOT NULL)`.
- **Append-only**: No UPDATE or DELETE; enforced via REVOKE and trigger.
- **Partitioning**: By `created_at` (monthly).

---

## `feature_flags`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `key` | text | NO | — | 'mastery_engine_v2', etc. |
| `description` | text | NO | — | — |
| `targeting_rules` | jsonb | NO | — | Percentage, cohort, user list. |
| `default_value` | jsonb | NO | `'false'` | — |
| `is_active` | boolean | NO | `true` | — |
| `owner` | text | NO | — | Team or individual responsible. |
| `retirement_plan` | text | YES | NULL | When and how the flag will retire. |
| `created_at` | timestamptz | NO | `now()` | — |
| `retired_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **Unique**: `key`.

---

## `feature_flag_assignments`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `feature_flag_id` | uuid | NO | — | FK. |
| `user_id` | uuid | NO | — | FK. |
| `override_value` | jsonb | NO | — | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(feature_flag_id, user_id)`.
- **FK**: `feature_flag_id` REFERENCES `administration.feature_flags(id) ON DELETE CASCADE`.
- **FK**: `user_id` REFERENCES `identity.users(id) ON DELETE CASCADE`.

---

## `system_settings`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `key` | text | NO | — | 'default_daily_goal_minutes', etc. |
| `value_type` | text | NO | — | 'integer', 'string', 'boolean', 'json'. |
| `value` | jsonb | NO | — | — |
| `description` | text | YES | NULL | — |
| `updated_at` | timestamptz | NO | `now()` | — |
| `updated_by_user_id` | uuid | YES | NULL | FK. |

- **PK**: `id`
- **Unique**: `key`.
- **FK**: `updated_by_user_id` REFERENCES `identity.users(id) ON DELETE SET NULL`.
- **Check**: `value_type IN ('integer', 'string', 'boolean', 'json')`.

---

## `gdpr_requests`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `user_id` | uuid | NO | — | FK. |
| `request_type` | text | NO | — | 'access', 'erasure', 'portability'. |
| `status` | text | NO | `'pending'` | 'pending', 'processing', 'completed', 'rejected'. |
| `request_metadata` | jsonb | NO | `'{}'` | — |
| `completion_metadata` | jsonb | YES | NULL | Export URL, anonymization details. |
| `requested_at` | timestamptz | NO | `now()` | — |
| `completed_at` | timestamptz | YES | NULL | — |
| `due_at` | date | NO | `(now() + interval '30 days')::date` | GDPR 30-day requirement. |

- **PK**: `id`
- **FK**: `user_id` REFERENCES `identity.users(id) ON DELETE RESTRICT`.
- **Check**: `request_type IN ('access', 'erasure', 'portability')`.
- **Check**: `status IN ('pending', 'processing', 'completed', 'rejected')`.

---

## `organizations`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `name` | text | NO | — | — |
| `status` | text | NO | `'active'` | 'active', 'dissolved'. |
| `billing_subscription_id` | uuid | YES | NULL | FK to subscriptions. |
| `created_at` | timestamptz | NO | `now()` | — |
| `dissolved_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **FK**: `billing_subscription_id` REFERENCES `billing.subscriptions(id) ON DELETE RESTRICT`.
- **Check**: `status IN ('active', 'dissolved')`.

---

## `organization_members`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `organization_id` | uuid | NO | — | FK. |
| `user_id` | uuid | NO | — | FK. |
| `role` | text | NO | `'member'` | 'member', 'admin'. |
| `joined_at` | timestamptz | NO | `now()` | — |
| `left_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **Unique**: `(organization_id, user_id)` WHERE `left_at IS NULL`.
- **FK**: `organization_id` REFERENCES `administration.organizations(id) ON DELETE CASCADE`.
- **FK**: `user_id` REFERENCES `identity.users(id) ON DELETE CASCADE`.
- **Check**: `role IN ('member', 'admin')`.

---

## `notifications`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `user_id` | uuid | NO | — | FK. |
| `notification_type` | text | NO | — | 'review_reminder', 'streak_nudge', etc. |
| `channel` | text | NO | — | 'email', 'push', 'in_app'. |
| `payload` | jsonb | NO | — | — |
| `status` | text | NO | `'queued'` | 'queued', 'sent', 'delivered', 'opened', 'dismissed', 'failed'. |
| `scheduled_at` | timestamptz | NO | — | — |
| `sent_at` | timestamptz | YES | NULL | — |
| `delivered_at` | timestamptz | YES | NULL | — |
| `opened_at` | timestamptz | YES | NULL | — |
| `dismissed_at` | timestamptz | YES | NULL | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **FK**: `user_id` REFERENCES `identity.users(id) ON DELETE CASCADE`.
- **Check**: `channel IN ('email', 'push', 'in_app')`.
- **Check**: `status IN ('queued', 'sent', 'delivered', 'opened', 'dismissed', 'failed')`.
- **Partitioning**: By `created_at` (monthly).

---

# Schema: `infrastructure`

## `outbox_events`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `event_type` | text | NO | — | 'AttemptRecorded', 'MasteryUpdated', etc. |
| `aggregate_id` | uuid | NO | — | The aggregate's ID. |
| `aggregate_type` | text | NO | — | 'Attempt', 'MasteryScore', etc. |
| `actor_user_id` | uuid | YES | NULL | FK; NULL for system events. |
| `payload` | jsonb | NO | — | The event payload. |
| `payload_schema_version` | text | NO | `'1'` | For event schema evolution. |
| `originating_schema` | text | NO | — | Which bounded context raised it. |
| `status` | text | NO | `'pending'` | 'pending', 'dispatched', 'dead_lettered'. |
| `dispatch_attempt_count` | integer | NO | `0` | — |
| `last_dispatch_error` | text | YES | NULL | — |
| `created_at` | timestamptz | NO | `now()` | — |
| `dispatched_at` | timestamptz | YES | NULL | — |

- **PK**: `id`
- **FK**: `actor_user_id` REFERENCES `identity.users(id) ON DELETE SET NULL`.
- **Check**: `status IN ('pending', 'dispatched', 'dead_lettered')`.
- **Append-only for `status = 'dispatched'`**: dispatched events are immutable.
- **Partitioning**: By `created_at` (monthly).

---

## `background_jobs`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `job_type` | text | NO | — | 'notification_dispatch', 'analytics_rebuild', etc. |
| `payload` | jsonb | NO | — | — |
| `payload_hash` | text | NO | — | SHA-256 of payload for dedup. |
| `status` | text | NO | `'queued'` | 'queued', 'running', 'completed', 'failed', 'dead_lettered'. |
| `priority` | integer | NO | `5` | 1 (high) to 10 (low). |
| `attempt_count` | integer | NO | `0` | — |
| `max_attempts` | integer | NO | `5` | — |
| `available_at` | timestamptz | NO | `now()` | For backoff scheduling. |
| `started_at` | timestamptz | YES | NULL | — |
| `completed_at` | timestamptz | YES | NULL | — |
| `failed_at` | timestamptz | YES | NULL | — |
| `last_error` | text | YES | NULL | — |
| `created_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `(job_type, payload_hash)` WHERE `status IN ('queued', 'running')` (dedup of in-flight jobs).
- **Check**: `status IN ('queued', 'running', 'completed', 'failed', 'dead_lettered')`.
- **Check**: `priority BETWEEN 1 AND 10`.
- **Check**: `attempt_count >= 0`.
- **Partitioning**: By `created_at` (monthly).

---

## `migration_history`

| Column | Type | Nullable | Default | Justification |
|---|---|---|---|---|
| `id` | uuid | NO | `gen_random_uuid()` | PK. |
| `version` | integer | NO | — | Monotonic migration version. |
| `filename` | text | NO | — | — |
| `checksum` | text | NO | — | SHA-256 of the migration file. |
| `applied_by_user_id` | uuid | YES | NULL | — |
| `applied_at` | timestamptz | NO | `now()` | — |

- **PK**: `id`
- **Unique**: `version`.
- **Append-only**: No UPDATE or DELETE.

---

*End of Logical Schema.*
