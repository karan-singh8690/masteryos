# 06 — Indexing Strategy

> Per-table indexing: primary, secondary, composite, partial, GIN, BRIN, with justifications.
> Indexes are the primary performance optimization; denormalization (`05-normalization.md`) is the last resort.

---

## Indexing Principles

1. **Index for the dominant access pattern** — every table has 1–3 dominant queries; index for those first.
2. **Partial indexes over filtered queries** — if a query always filters `WHERE deleted_at IS NULL`, a partial index is smaller and faster.
3. **Composite indexes for multi-column filters** — order columns by selectivity (most selective first).
4. **BRIN for time-ordered, append-heavy tables** — `attempts`, `audit_logs`, `outbox_events` benefit from BRIN on `created_at` due to natural time-ordering.
5. **GIN for JSONB and trigram search** — JSONB columns that are queried, and text columns that are fuzzy-searched.
6. **Avoid over-indexing** — every index slows writes. Justify each index by a measured query.

---

## Index Naming Convention

- Primary key: `pk_<table>` (implicit with PRIMARY KEY constraint).
- Unique: `uq_<table>_<purpose>` (implicit with UNIQUE constraint).
- Secondary: `idx_<table>_<columns>`.
- Partial: `idx_<table>_<columns>_active` (where "active" denotes the partial condition).
- GIN: `gin_<table>_<column>`.
- BRIN: `brin_<table>_<column>`.

---

## Per-Table Indexing

### `identity.users`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_users` | btree (implicit) | `id` | PK lookup. |
| `uq_users_email` | btree (implicit) | `email` WHERE `deleted_at IS NULL` | Login by email; partial to allow re-registration after deletion. |

**Read patterns**: by `id` (every authenticated request); by `email` (login).
**Write patterns**: low (signup, profile updates).

---

### `identity.user_profiles`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_user_profiles` | btree (implicit) | `id` | PK. |
| `uq_user_profiles_user_id` | btree (implicit) | `user_id` | 1:1 with users. |

---

### `identity.user_credentials`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_user_credentials` | btree (implicit) | `id` | PK. |
| `idx_user_credentials_user_id` | btree | `user_id` | Login: fetch credentials by user. |
| `uq_user_credentials_oauth` | btree (implicit) | `(provider, provider_user_id)` WHERE `credential_type = 'oauth'` | OAuth callback lookup. |
| `uq_user_credentials_password` | btree (implicit) | `user_id` WHERE `credential_type = 'password'` | One password per user. |

---

### `identity.sessions`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_sessions` | btree (implicit) | `id` | PK. |
| `uq_sessions_refresh_token_hash` | btree (implicit) | `refresh_token_hash` | Token refresh lookup. |
| `idx_sessions_user_id_active` | btree | `user_id` WHERE `revoked_at IS NULL` | Active sessions list (partial: only non-revoked). |
| `idx_sessions_expires_at` | btree | `expires_at` | Cleanup job: find expired sessions. |

---

### `content.tenants`, `content.subjects`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_tenants` | btree (implicit) | `id` | PK. |
| `uq_tenants_code` | btree (implicit) | `code` | — |
| `pk_subjects` | btree (implicit) | `id` | PK. |
| `uq_subjects_code` | btree (implicit) | `code` | — |
| `uq_subjects_slug` | btree (implicit) | `slug` | URL lookup. |
| `idx_subjects_tenant_id` | btree | `tenant_id` | Tenant isolation queries. |

---

### `content.learning_paths`, `content.learning_path_items`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_learning_paths` | btree (implicit) | `id` | PK. |
| `uq_learning_paths_subject_name` | btree (implicit) | `(subject_id, name)` | — |
| `idx_learning_paths_subject_id` | btree | `subject_id` | Path selection by subject. |
| `pk_learning_path_items` | btree (implicit) | `id` | PK. |
| `uq_learning_path_items_path_position` | btree (implicit) | `(learning_path_id, position)` | — |
| `uq_learning_path_items_path_concept` | btree (implicit) | `(learning_path_id, concept_id)` | — |
| `idx_learning_path_items_concept_id` | btree | `concept_id` | "Which paths include this concept?" |

---

### `content.concepts`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_concepts` | btree (implicit) | `id` | PK. |
| `uq_concepts_subject_slug` | btree (implicit) | `(subject_id, slug)` | — |
| `idx_concepts_subject_id` | btree | `subject_id` | Knowledge graph traversal. |
| `gin_concepts_name_trgm` | GIN | `name gin_trgm_ops` | Fuzzy search by name (admin portal). |

---

### `content.concept_dependencies`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_concept_dependencies` | btree (implicit) | `id` | PK. |
| `uq_concept_dependencies_edge` | btree (implicit) | `(source_concept_id, target_concept_id, dependency_type)` | — |
| `idx_concept_dependencies_source` | btree | `source_concept_id` | "What does this concept depend on?" |
| `idx_concept_dependencies_target` | btree | `target_concept_id` | "What depends on this concept?" |

---

### `content.learning_objectives`, `content.misconceptions`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_learning_objectives` | btree (implicit) | `id` | PK. |
| `idx_learning_objectives_concept_id` | btree | `concept_id` | "Objectives for this concept." |
| `pk_misconceptions` | btree (implicit) | `id` | PK. |
| `idx_misconceptions_learning_objective_id` | btree | `learning_objective_id` | "Misconceptions for this objective." |

---

### `content.question_templates`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_question_templates` | btree (implicit) | `id` | PK. |
| `uq_question_templates_subject_code` | btree (implicit) | `(subject_id, code)` | — |
| `idx_question_templates_subject_id` | btree | `subject_id` | Template selection by subject. |
| `idx_question_templates_status` | btree | `status` WHERE `status = 'published'` | Published templates only (partial). |

---

### `content.template_versions`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_template_versions` | btree (implicit) | `id` | PK. |
| `uq_template_versions_template_version` | btree (implicit) | `(template_id, version_number)` | — |
| `idx_template_versions_template_id` | btree | `template_id` | Version history. |
| `idx_template_versions_content_version_id` | btree | `content_version_id` | "Templates in this content version." |

---

### `content.template_objectives`, `content.template_concepts`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_template_objectives` | btree (implicit) | `id` | PK. |
| `uq_template_objectives_pair` | btree (implicit) | `(template_version_id, learning_objective_id)` | — |
| `idx_template_objectives_objective_id` | btree | `learning_objective_id` | "Templates testing this objective" (coverage analysis). |
| `pk_template_concepts` | btree (implicit) | `id` | PK. |
| `uq_template_concepts_pair` | btree (implicit) | `(template_version_id, concept_id)` | — |
| `idx_template_concepts_concept_id` | btree | `concept_id` | "Templates for this concept" (scheduler selection). |

---

### `content.distractors`, `content.hints`, `content.explanations`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_distractors` | btree (implicit) | `id` | PK. |
| `uq_distractors_pair` | btree (implicit) | `(template_version_id, position)` | — |
| `idx_distractors_misconception_id` | btree | `misconception_id` WHERE `misconception_id IS NOT NULL` | "Distractors detecting this misconception" (analytics). |
| `pk_hints` | btree (implicit) | `id` | PK. |
| `uq_hints_pair` | btree (implicit) | `(template_version_id, tier)` | — |
| `pk_explanations` | btree (implicit) | `id` | PK. |
| `uq_explanations_pair` | btree (implicit) | `(template_version_id, outcome_key)` | — |

---

### `content.content_versions`, `content.content_packs`, `content.content_review_requests`, `content.content_approvals`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_content_versions` | btree (implicit) | `id` | PK. |
| `uq_content_versions_subject_version` | btree (implicit) | `(subject_id, version_number)` | — |
| `idx_content_versions_subject_id_active` | btree | `subject_id` WHERE `status = 'active'` | Current version lookup (partial). |
| `pk_content_packs` | btree (implicit) | `id` | PK. |
| `idx_content_packs_content_version_id` | btree | `content_version_id` | "Packs in this version." |
| `idx_content_packs_author_user_id` | btree | `author_user_id` | Author history. |
| `pk_content_review_requests` | btree (implicit) | `id` | PK. |
| `idx_content_review_requests_status` | btree | `status` WHERE `status IN ('peer_review', 'editorial_review', 'qa_pilot')` | Review queue (partial). |
| `idx_content_review_requests_author_user_id` | btree | `author_user_id` | Author's submissions. |
| `pk_content_approvals` | btree (implicit) | `id` | PK. |
| `idx_content_approvals_review_request_id` | btree | `content_review_request_id` | Review history. |
| `idx_content_approvals_reviewer_user_id` | btree | `reviewer_user_id` | Reviewer activity. |

---

### `learning.learner_enrollments`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_learner_enrollments` | btree (implicit) | `id` | PK. |
| `uq_learner_enrollments_user_subject` | btree (implicit) | `(user_id, subject_id)` WHERE `status <> 'unenrolled'` | One active enrollment per user per subject. |
| `idx_learner_enrollments_user_id` | btree | `user_id` | "Subjects for this user." |
| `idx_learner_enrollments_subject_id` | btree | `subject_id` | Subject analytics. |
| `idx_learner_enrollments_last_active_at` | btree | `last_active_at` | Dormancy detection job. |

---

### `learning.learning_goals`, `learning.study_plans`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_learning_goals` | btree (implicit) | `id` | PK. |
| `idx_learning_goals_enrollment_active` | btree | `learner_enrollment_id` WHERE `status = 'active'` | Active goals (partial). |
| `uq_learning_goals_interview` | btree (implicit) | `learner_enrollment_id` WHERE `goal_type = 'interview_date' AND status = 'active'` | One active interview date. |
| `pk_study_plans` | btree (implicit) | `id` | PK. |
| `idx_study_plans_enrollment_active` | btree | `learner_enrollment_id` WHERE `status = 'active'` | Active plan (partial). |

---

### `learning.study_sessions`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_study_sessions` | btree (implicit) | `id` | PK. |
| `idx_study_sessions_enrollment_started_at` | btree | `(learner_enrollment_id, started_at DESC)` | Session history (most recent first). |
| `idx_study_sessions_enrollment_active` | btree | `learner_enrollment_id` WHERE `status IN ('active', 'paused')` | Active session lookup (partial). |
| `idx_study_sessions_learning_session_id` | btree | `learning_session_id` WHERE `learning_session_id IS NOT NULL` | Learning session grouping. |

---

### `learning.learning_sessions`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_learning_sessions` | btree (implicit) | `id` | PK. |
| `idx_learning_sessions_enrollment_started_at` | btree | `(learner_enrollment_id, started_at DESC)` | Engagement analytics. |
| `brin_learning_sessions_started_at` | BRIN | `started_at` | Time-range queries on partitioned table. |

---

### `learning.practice_queues`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_practice_queues` | btree (implicit) | `id` | PK. |
| `uq_practice_queues_session_type` | btree (implicit) | `(study_session_id, queue_type)` | — |

---

### `learning.recommendations`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_recommendations` | btree (implicit) | `id` | PK. |
| `idx_recommendations_enrollment_status_created` | btree | `(learner_enrollment_id, status, created_at DESC)` | Dashboard: recent recommendations by status. |
| `idx_recommendations_expires_at` | btree | `expires_at` WHERE `expires_at IS NOT NULL` | Expiry cleanup job. |

---

### `learning.recommendation_history`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_recommendation_history` | btree (implicit) | `id` | PK. |
| `idx_recommendation_history_recommendation_id` | btree | `recommendation_id` | Lifecycle lookup. |
| `brin_recommendation_history_created_at` | BRIN | `created_at` | Time-range analytics on partitioned table. |

---

### `learning.achievements`, `learning.achievement_types`, `learning.streaks`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_achievements` | btree (implicit) | `id` | PK. |
| `uq_achievements_enrollment_type` | btree (implicit) | `(learner_enrollment_id, achievement_type_id)` | — |
| `idx_achievements_enrollment_id` | btree | `learner_enrollment_id` | Profile: learner's achievements. |
| `pk_achievement_types` | btree (implicit) | `id` | PK. |
| `uq_achievement_types_code` | btree (implicit) | `code` | — |
| `idx_achievement_types_subject_id` | btree | `subject_id` WHERE `subject_id IS NOT NULL` | Catalog by subject. |
| `pk_streaks` | btree (implicit) | `id` | PK. |
| `uq_streaks_enrollment_id` | btree (implicit) | `learner_enrollment_id` | 1:1. |

---

### `assessment.question_instances`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_question_instances` | btree (implicit) | `id` | PK. |
| `idx_question_instances_template_version_id` | btree | `template_version_id` | Template analytics. |
| `idx_question_instances_enrollment_served_at` | btree | `(learner_enrollment_id, served_at DESC)` | Learner history. |
| `idx_question_instances_study_session_id` | btree | `study_session_id` | Session contents. |
| `idx_question_instances_status` | btree | `status` WHERE `status = 'served'` | Abandoned instance cleanup (partial). |
| `brin_question_instances_served_at` | BRIN | `served_at` | Time-range queries on partitioned table. |

---

### `assessment.attempts` (the most critical table)

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_attempts` | btree (implicit) | `id` | PK. |
| `idx_attempts_enrollment_created_at` | btree | `(learner_enrollment_id, created_at DESC)` | Learner history; mastery recompute. |
| `idx_attempts_enrollment_concept` | btree | `(learner_enrollment_id, concept_id)` (via join to `template_concepts`; or denormalize `concept_id` if needed) | Mastery recompute for a concept. **Note**: this requires a join through `question_instances` → `template_versions` → `template_concepts`. For performance at scale, consider denormalizing `concept_id` onto `attempts`. See `12-performance.md`. |
| `idx_attempts_template_version_id` | btree | `template_version_id` | Template statistics. |
| `idx_attempts_content_version_id` | btree | `content_version_id` | Content analytics. |
| `idx_attempts_algorithm_version_id` | btree | `algorithm_version_id` | Algorithm version analytics. |
| `idx_attempts_study_session_id` | btree | `study_session_id` | Session contents. |
| `idx_attempts_misconception_id` | btree | `misconception_id` WHERE `misconception_id IS NOT NULL` | Misconception analytics (partial). |
| `brin_attempts_created_at` | BRIN | `created_at` | Time-range queries on partitioned table. |

**Critical note on `idx_attempts_enrollment_concept`**: the dominant mastery-recompute query is "all attempts by this learner on this concept." Because `attempts` does not directly carry `concept_id` (it's linked via `question_instances` → `template_versions` → `template_concepts`), this query requires joins. At scale, **denormalize `concept_ids` (an array) onto `attempts`** with a GIN index. This is a documented future optimization (see `12-performance.md`); at launch, the join approach is sufficient.

---

### `assessment.answers`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_answers` | btree (implicit) | `id` | PK. |
| `uq_answers_attempt_id` | btree (implicit) | `attempt_id` | 1:1 with attempts. |
| `idx_answers_question_instance_id` | btree | `question_instance_id` | Instance analytics. |

---

### `mastery.algorithm_versions`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_algorithm_versions` | btree (implicit) | `id` | PK. |
| `uq_algorithm_versions_version_number` | btree (implicit) | `version_number` | — |
| `uq_algorithm_versions_active` | btree (implicit) | `is_active` WHERE `is_active = true` | Only one active version (partial unique). |

---

### `mastery.mastery_scores` (critical for the learning loop)

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_mastery_scores` | btree (implicit) | `id` | PK. |
| `uq_mastery_scores_enrollment_concept` | btree (implicit) | `(learner_enrollment_id, concept_id)` | One score per learner per concept. |
| `idx_mastery_scores_concept_id` | btree | `concept_id` | Concept statistics. |
| `idx_mastery_scores_enrollment_weak` | btree | `learner_enrollment_id` WHERE `durable_mastery_score < 0.5` | Weak concepts for a learner (partial; the Scheduler's primary query). |
| `idx_mastery_scores_algorithm_version_id` | btree | `algorithm_version_id` | Recompute job: find scores under an old version. |

---

### `mastery.reviews`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_reviews` | btree (implicit) | `id` | PK. |
| `uq_reviews_enrollment_concept` | btree (implicit) | `(learner_enrollment_id, concept_id)` | One review per learner per concept. |
| `idx_reviews_enrollment_due` | btree | `(learner_enrollment_id, due_at)` WHERE `due_at <= now()` | Due reviews for a learner (partial; the Scheduler's primary query). |
| `idx_reviews_concept_id` | btree | `concept_id` | Concept review analytics. |

---

### `mastery.learner_misconceptions`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_learner_misconceptions` | btree (implicit) | `id` | PK. |
| `uq_learner_misconceptions_pair` | btree (implicit) | `(learner_enrollment_id, misconception_id)` | — |
| `idx_learner_misconceptions_misconception_id` | btree | `misconception_id` | Misconception frequency analytics. |
| `idx_learner_misconceptions_enrollment_active` | btree | `learner_enrollment_id` WHERE `cleared_at IS NULL` | Active misconceptions for a learner (partial). |

---

### `scheduling.daily_queues`, `scheduling.scheduling_configs`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_daily_queues` | btree (implicit) | `id` | PK. |
| `uq_daily_queues_enrollment_date` | btree (implicit) | `(learner_enrollment_id, queue_date)` | — |
| `idx_daily_queues_status` | btree | `status` WHERE `status = 'active'` | Active queues (partial). |
| `pk_scheduling_configs` | btree (implicit) | `id` | PK. |
| `uq_scheduling_configs_subject_active` | btree (implicit) | `subject_id` WHERE `is_active = true` | One active config per subject. |

---

### `analytics.learner_daily_snapshots`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_learner_daily_snapshots` | btree (implicit) | `id` | PK. |
| `uq_learner_daily_snapshots_triplet` | btree (implicit) | `(learner_enrollment_id, concept_id, snapshot_date)` | — |
| `idx_learner_daily_snapshots_concept_date` | btree | `(concept_id, snapshot_date)` | Concept retention analytics. |
| `brin_learner_daily_snapshots_snapshot_date` | BRIN | `snapshot_date` | Time-range queries on partitioned table. |

---

### `analytics.concept_statistics`, `analytics.template_statistics`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_concept_statistics` | btree (implicit) | `id` | PK. |
| `uq_concept_statistics_triplet` | btree (implicit) | `(concept_id, content_version_id, snapshot_date)` | — |
| `idx_concept_statistics_concept_id` | btree | `concept_id` | Concept quality over time. |
| `pk_template_statistics` | btree (implicit) | `id` | PK. |
| `uq_template_statistics_pair` | btree (implicit) | `(template_version_id, snapshot_date)` | — |
| `idx_template_statistics_template_version_id` | btree | `template_version_id` | Template quality over time. |

---

### `billing.billing_plans`, `billing.subscriptions`, `billing.invoices`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_billing_plans` | btree (implicit) | `id` | PK. |
| `uq_billing_plans_code_version` | btree (implicit) | `(code, version_number)` | — |
| `idx_billing_plans_code_active` | btree | `code` WHERE `is_active = true` | Active plan lookup. |
| `pk_subscriptions` | btree (implicit) | `id` | PK. |
| `idx_subscriptions_user_id_active` | btree | `user_id` WHERE `status = 'active'` | Entitlement check (partial). |
| `idx_subscriptions_status` | btree | `status` | Subscription analytics. |
| `pk_invoices` | btree (implicit) | `id` | PK. |
| `idx_invoices_user_id_issued_at` | btree | `(user_id, issued_at DESC)` | Billing history. |
| `idx_invoices_subscription_id` | btree | `subscription_id` | Subscription invoices. |

---

### `administration.audit_logs`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_audit_logs` | btree (implicit) | `id` | PK. |
| `idx_audit_logs_target` | btree | `(target_type, target_id)` | Forensics: "who did what to this?" |
| `idx_audit_logs_actor_user_id_created_at` | btree | `(actor_user_id, created_at DESC)` | User activity. |
| `idx_audit_logs_action_created_at` | btree | `(action, created_at DESC)` | Action audit. |
| `gin_audit_logs_metadata` | GIN | `metadata` | Query by metadata fields. |
| `brin_audit_logs_created_at` | BRIN | `created_at` | Time-range queries on partitioned table. |

---

### `administration.feature_flags`, `administration.feature_flag_assignments`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_feature_flags` | btree (implicit) | `id` | PK. |
| `uq_feature_flags_key` | btree (implicit) | `key` | — |
| `idx_feature_flags_active` | btree | `is_active` WHERE `is_active = true` | Active flags (partial). |
| `pk_feature_flag_assignments` | btree (implicit) | `id` | PK. |
| `uq_feature_flag_assignments_pair` | btree (implicit) | `(feature_flag_id, user_id)` | — |
| `idx_feature_flag_assignments_user_id` | btree | `user_id` | Flag evaluation by user. |

---

### `administration.system_settings`, `administration.gdpr_requests`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_system_settings` | btree (implicit) | `id` | PK. |
| `uq_system_settings_key` | btree (implicit) | `key` | — |
| `pk_gdpr_requests` | btree (implicit) | `id` | PK. |
| `idx_gdpr_requests_user_id` | btree | `user_id` | User's request history. |
| `idx_gdpr_requests_status` | btree | `status` WHERE `status IN ('pending', 'processing')` | Admin queue (partial). |
| `idx_gdpr_requests_due_at` | btree | `due_at` | Overdue request alerting. |

---

### `administration.organizations`, `administration.organization_members`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_organizations` | btree (implicit) | `id` | PK. |
| `pk_organization_members` | btree (implicit) | `id` | PK. |
| `uq_organization_members_active` | btree (implicit) | `(organization_id, user_id)` WHERE `left_at IS NULL` | Active membership. |
| `idx_organization_members_user_id` | btree | `user_id` WHERE `left_at IS NULL` | User's organization. |

---

### `administration.notifications`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_notifications` | btree (implicit) | `id` | PK. |
| `idx_notifications_user_id_status_created_at` | btree | `(user_id, status, created_at DESC)` | Notification center. |
| `idx_notifications_status_scheduled_at` | btree | `(status, scheduled_at)` WHERE `status = 'queued'` | Dispatcher: find due notifications (partial). |
| `brin_notifications_created_at` | BRIN | `created_at` | Time-range queries on partitioned table. |

---

### `infrastructure.outbox_events`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_outbox_events` | btree (implicit) | `id` | PK. |
| `idx_outbox_events_status_created_at` | btree | `(status, created_at)` WHERE `status = 'pending'` | Dispatcher poll (partial). |
| `idx_outbox_events_aggregate_id` | btree | `aggregate_id` | Event replay for an aggregate. |
| `idx_outbox_events_event_type_created_at` | btree | `(event_type, created_at DESC)` | Event type analytics. |
| `gin_outbox_events_payload` | GIN | `payload` | Query by payload fields (analytics). |
| `brin_outbox_events_created_at` | BRIN | `created_at` | Time-range queries on partitioned table. |

---

### `infrastructure.background_jobs`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_background_jobs` | btree (implicit) | `id` | PK. |
| `idx_background_jobs_status_priority_available_at` | btree | `(status, priority, available_at)` WHERE `status = 'queued'` | Worker poll: find due jobs by priority (partial). |
| `uq_background_jobs_dedup` | btree (implicit) | `(job_type, payload_hash)` WHERE `status IN ('queued', 'running')` | Dedup of in-flight jobs. |
| `idx_background_jobs_status_failed_at` | btree | `status` WHERE `status = 'dead_lettered'` | Dead-letter queue (partial). |

---

### `infrastructure.migration_history`

| Index | Type | Columns | Justification |
|---|---|---|---|
| `pk_migration_history` | btree (implicit) | `id` | PK. |
| `uq_migration_history_version` | btree (implicit) | `version` | — |

---

## Index Maintenance

- **Autovacuum**: configured aggressively on high-write tables (`attempts`, `outbox_events`, `mastery_scores`) to keep index statistics fresh.
- **Manual REINDEX**: scheduled monthly during low-traffic windows for high-write tables, to reclaim index bloat.
- **Index monitoring**: `pg_stat_user_indexes` tracks index usage; unused indexes are candidates for removal.
- **Index-only scans**: covered indexes (including all columns a query needs) enable index-only scans; used for hot queries (e.g., `idx_mastery_scores_enrollment_weak` could include `durable_mastery_score` for the Scheduler's weak-concept query).

---

## Index Summary by Type

| Type | Count | Primary Use |
|---|---|---|
| btree (PK) | ~50 | Primary key lookups. |
| btree (unique) | ~30 | Natural key enforcement. |
| btree (secondary) | ~60 | Dominant access patterns. |
| btree (partial) | ~20 | Filtered queries (active, non-deleted, etc.). |
| GIN | 4 | JSONB query, trigram search. |
| BRIN | 6 | Time-range on partitioned append-heavy tables. |

**Total**: ~170 indexes across ~50 tables. The write overhead is acceptable because most tables are low-write; the high-write tables (`attempts`, `outbox_events`) have a focused index set optimized for their dominant patterns.

---

*End of Indexing Strategy.*
