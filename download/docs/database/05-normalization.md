# 05 — Normalization

> Normalization analysis for every table: 1NF, 2NF, 3NF, BCNF, and intentional denormalizations.
> The schema is normalized to BCNF by default; denormalizations are explicit and justified.

---

## Normalization Principles

The Mastery Engine database is **normalized-first** (ASD Section 1.4, ADR-0002). Normalization provides:
- **Data integrity** — no redundant copies that can drift.
- **Analytical flexibility** — any query can be expressed without denormalization-induced limitations.
- **Schema evolution** — adding a column does not require updating redundant copies.

The cost of normalization (more joins, potentially slower queries) is accepted by default and mitigated by indexing (`06-indexing-strategy.md`), materialized views, and a derived analytics warehouse at scale (`12-performance.md`).

**Denormalizations are intentional, documented, and reversible.** Each denormalization in this document has a justification and a "how to normalize if needed" note.

---

## Normal Forms (quick reference)

- **1NF**: atomic values; no repeating groups. Every table in the schema is 1NF (no array columns that should be child tables; JSONB columns hold opaque payloads, not queryable sub-rows).
- **2NF**: 1NF + no partial dependencies on composite keys. The schema has no composite primary keys, so 2NF is trivially satisfied.
- **3NF**: 2NF + no transitive dependencies. Non-key columns depend only on the primary key, not on other non-key columns.
- **BCNF**: 3NF + every determinant is a candidate key. Stricter than 3NF; eliminates anomalies that 3NF misses.

---

## Per-Table Analysis

### `identity.users`
- **1NF**: ✓ (atomic columns).
- **2NF**: ✓ (single-column PK).
- **3NF**: ✓ (`email_verified_at` depends on `id`, not on `email` or `status`).
- **BCNF**: ✓.
- **Denormalizations**: none.

### `identity.user_profiles`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓ (`preferences` JSONB is opaque; no transitive dependencies).
- **BCNF**: ✓.
- **Denormalizations**: none.

### `identity.user_credentials`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓ (`password_hash` depends on `id`, not on `credential_type`).
- **BCNF**: ✓.
- **Denormalizations**: none.

### `identity.sessions`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `last_ip` and `user_agent` are denormalized from the request that last refreshed the session; they could be in a `session_events` table. Justification: session list display needs them without a join.

### `content.tenants`, `content.subjects`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `subjects.tenant_id` is technically redundant in the current 1:1 architecture (could be derived from `subject_id`). Justification: preserved for the future multi-subject tenant case (ADR-0010); the 1:1 is a current-state constraint, not a permanent one.

### `content.learning_paths`, `content.learning_path_items`
- **1NF**: ✓.
- **2NF**: ✓ (`learning_path_items` has a single-column PK; the composite unique is a constraint, not the PK).
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none. `learning_path_items` is a proper join table.

### `content.concepts`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓ (`difficulty` and `importance` are independent properties of the concept).
- **BCNF**: ✓.
- **Denormalizations**: `current_version_id` is denormalized from the latest `content_versions` row that published this concept. Justification: fast lookup of "current version" without scanning `content_versions`. Maintained by trigger on publish.

### `content.concept_dependencies`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `content.learning_objectives`, `content.misconceptions`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `content.question_templates`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `current_version_id` (same pattern as `concepts.current_version_id`).

### `content.template_versions`
- **1NF**: ✓ (the JSONB columns hold opaque specs, not queryable sub-rows).
- **2NF**: ✓.
- **3NF**: ✓ (`difficulty_estimate` and `discrimination_estimate` are independent).
- **BCNF**: ✓.
- **Denormalizations**: `content_version_id` is denormalized from the publish event that created this version. Justification: fast lookup of "which content version is this template version in" without scanning `content_versions`. Maintained by trigger on publish.

### `content.template_objectives`, `content.template_concepts`, `content.distractors`, `content.hints`, `content.explanations`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none. These are proper normalized child tables.

### `content.content_versions`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `tenant_id` is denormalized from `subjects.tenant_id`. Justification: avoids a join when filtering content versions by tenant. Maintained by trigger on subject create/update.

### `content.content_packs`, `content.content_review_requests`, `content.content_approvals`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `learning.learner_enrollments`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓ (`status` depends on `id`, not on `user_id` or `subject_id`).
- **BCNF**: ✓.
- **Denormalizations**: none.

### `learning.learning_goals`, `learning.study_plans`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `study_plans.learning_path_id` is denormalized from `learner_enrollments.learning_path_id`. Justification: the plan is tied to a specific path snapshot; if the learner switches paths, the old plan retains its path reference. This is intentional historical accuracy, not pure denormalization.

### `learning.study_sessions`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `question_count` is denormalized from `COUNT(attempts WHERE study_session_id = ...)`. Justification: fast dashboard reads without an aggregate. Maintained by trigger on attempt insert.

### `learning.learning_sessions`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `study_session_count` and `total_duration_seconds` are denormalized from `study_sessions`. Justification: fast engagement analytics without aggregation. Maintained by trigger on session end.

### `learning.practice_queues`
- **1NF**: ✓ (the JSONB arrays hold opaque ordered lists; `current_position` is atomic).
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `learning.recommendations`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `learning.recommendation_history`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `learning.achievements`, `learning.achievement_types`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `achievements.criteria_snapshot` is denormalized from `achievement_types.criteria` at award time. Justification: historical accuracy — if the criteria change later, the awarded achievement retains the criteria that were met. This is intentional, not pure denormalization.

### `learning.streaks`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓ (`longest_streak` is derived but stored for performance; it depends on `id`).
- **BCNF**: ✓.
- **Denormalizations**: `longest_streak` is denormalized from the history of `current_streak` values. Justification: fast display without scanning history. Maintained by trigger on `current_streak` update.

### `assessment.question_instances`
- **1NF**: ✓ (JSONB columns hold opaque instantiated data).
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**:
  - `content_version_id` is denormalized from `template_versions.content_version_id`. Justification: triple versioning requires the attempt to reference the content version directly; the question instance carries it for consistency. Maintained by trigger on instantiate.
  - `learner_enrollment_id` and `study_session_id` are denormalized from the serving context. Justification: fast queries by learner or session without joins.

### `assessment.attempts`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations** (all intentional for triple versioning and query speed):
  - `learner_enrollment_id` denormalized from `question_instances.learner_enrollment_id`. Justification: fast queries by learner (the dominant access pattern) without joining `question_instances`.
  - `study_session_id` denormalized from `question_instances.study_session_id`. Justification: fast queries by session.
  - `content_version_id`, `template_version_id` denormalized from `question_instances`. Justification: triple versioning requires the attempt to carry these directly.
  - `algorithm_version_id` is NOT denormalized from another table; it is the algorithm version under which the resulting mastery was computed, recorded at write time.
  - `misconception_id` denormalized from the selected distractor's tag. Justification: fast misconception analytics without joining through `distractors`.

### `assessment.answers`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `question_instance_id` is denormalized from `attempts.question_instance_id`. Justification: fast queries by question instance (e.g., revision analytics) without joining `attempts`.

### `mastery.algorithm_versions`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `mastery.mastery_scores`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓ (`concept_state` and `weakness_severity` are derived from the score columns but are stored for query speed; they depend on `id`).
- **BCNF**: ✓.
- **Denormalizations** (intentional, all for query performance):
  - `concept_state` is denormalized from the score columns (derived via the algorithm's thresholds). Justification: fast filtering by state (e.g., "all weak concepts") without recomputing. Maintained by trigger on score update.
  - `weakness_severity` is denormalized from `memory_score`, `durable_mastery_score`, and `concept_state`. Justification: fast weak-concept queries. Maintained by trigger on score update.
  - `mastery_score_combined` is a generated column (per ADR-0008) — technically denormalized from `memory_score` and `durable_mastery_score`.
  - `last_attempt_at` is denormalized from the latest `attempts.created_at` for this learner-concept. Justification: fast "last studied" queries without joining `attempts`. Maintained by trigger on attempt insert.
  - `algorithm_version_id` is NOT denormalized; it records the version under which the score was computed.

### `mastery.reviews`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `mastery.learner_misconceptions`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `severity` is denormalized from `detection_count` and `last_detected_at`. Justification: fast filtering by severity. Maintained by trigger on detection.

### `scheduling.daily_queues`, `scheduling.scheduling_configs`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `analytics.learner_daily_snapshots`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: this entire table is a denormalization (a snapshot of `mastery_scores` over time). Justification: retention analytics over time without querying the append-only `attempts` table. This is an intentional, documented denormalization at the analytics layer.

### `analytics.concept_statistics`, `analytics.template_statistics`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: these tables are aggregations (denormalized from `attempts` and `mastery_scores`). Justification: precomputed aggregates for admin portal performance. Intentional analytics-layer denormalization.

### `billing.billing_plans`, `billing.subscriptions`, `billing.invoices`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `invoices.user_id` is denormalized from `subscriptions.user_id`. Justification: fast billing history queries by user without joining `subscriptions`.

### `administration.audit_logs`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `actor_ip`, `user_agent`, `correlation_id` are denormalized from the request context. Justification: audit logs must be self-contained (no joins to request logs, which may be purged).

### `administration.feature_flags`, `administration.feature_flag_assignments`, `administration.system_settings`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `administration.gdpr_requests`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `administration.organizations`, `administration.organization_members`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `administration.notifications`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

### `infrastructure.outbox_events`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `actor_user_id` is denormalized from the originating context's request. Justification: outbox events must be self-contained for audit and replay.

### `infrastructure.background_jobs`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: `payload_hash` is denormalized (computed) from `payload`. Justification: dedup index on a hash is faster than on the full JSONB.

### `infrastructure.migration_history`
- **1NF**: ✓.
- **2NF**: ✓.
- **3NF**: ✓.
- **BCNF**: ✓.
- **Denormalizations**: none.

---

## Summary of Intentional Denormalizations

| Table | Denormalized Column | Source | Justification | Maintenance |
|---|---|---|---|---|
| `sessions` | `last_ip`, `user_agent` | Request context | Session list display | Trigger on refresh |
| `subjects` | `tenant_id` | (1:1 with tenant) | Future multi-subject tenant | Trigger on create |
| `concepts` | `current_version_id` | Latest `content_versions` | Fast "current version" lookup | Trigger on publish |
| `question_templates` | `current_version_id` | Latest `template_versions` | Fast "current version" lookup | Trigger on publish |
| `template_versions` | `content_version_id` | Publish event | Fast "which content version" lookup | Trigger on publish |
| `content_versions` | `tenant_id` | `subjects.tenant_id` | Avoid join | Trigger on create |
| `study_plans` | `learning_path_id` | `learner_enrollments.learning_path_id` | Historical accuracy | Application |
| `study_sessions` | `question_count` | `COUNT(attempts)` | Fast dashboard reads | Trigger on attempt insert |
| `learning_sessions` | `study_session_count`, `total_duration_seconds` | `study_sessions` | Fast engagement analytics | Trigger on session end |
| `achievements` | `criteria_snapshot` | `achievement_types.criteria` | Historical accuracy | Application at award time |
| `streaks` | `longest_streak` | History of `current_streak` | Fast display | Trigger on update |
| `question_instances` | `content_version_id`, `learner_enrollment_id`, `study_session_id` | `template_versions`, serving context | Triple versioning, fast queries | Trigger on instantiate |
| `attempts` | `learner_enrollment_id`, `study_session_id`, `content_version_id`, `template_version_id`, `misconception_id` | `question_instances`, `distractors` | Triple versioning, fast queries | Trigger on insert |
| `answers` | `question_instance_id` | `attempts.question_instance_id` | Fast queries by instance | Application at insert |
| `mastery_scores` | `concept_state`, `weakness_severity`, `mastery_score_combined`, `last_attempt_at` | Score columns, algorithm thresholds, latest attempt | Fast filtering, fast "last studied" | Triggers on score update and attempt insert |
| `learner_misconceptions` | `severity` | `detection_count`, `last_detected_at` | Fast filtering by severity | Trigger on detection |
| `invoices` | `user_id` | `subscriptions.user_id` | Fast billing history | Application at insert |
| `audit_logs` | `actor_ip`, `user_agent`, `correlation_id` | Request context | Self-contained audit | Application at insert |
| `outbox_events` | `actor_user_id` | Request context | Self-contained event | Application at insert |
| `background_jobs` | `payload_hash` | `payload` (computed) | Fast dedup index | Application at insert |

---

## When to Denormalize Further

Denormalization is a response to measured query latency, not a preemptive optimization. The rule:

1. **Measure** — identify a query whose p99 latency exceeds the budget (200ms for the learning loop, 2s for analytics).
2. **Optimize indexes first** — most latency issues are solved by adding the right index (`06-indexing-strategy.md`).
3. **Optimize the query second** — rewrite the query to be more selective.
4. **Denormalize last** — only if indexes and query optimization are insufficient, add a denormalized column with a trigger to maintain it.
5. **Document the denormalization** — add it to this table with justification and maintenance strategy.
6. **ADR for significant denormalizations** — if the denormalization changes the data model materially, write an ADR.

---

*End of Normalization.*
