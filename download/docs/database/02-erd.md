# 02 — Entity Relationship Diagram

> Complete ERD for the Mastery Engine database, in Mermaid syntax.
> Diagrams are split by bounded context (PostgreSQL schema) for readability; a high-level cross-context diagram follows.

---

## How to Read This Document

The ERD is split into:
1. **High-level cross-context diagram** — shows the relationships between the 10 bounded contexts.
2. **Per-context diagrams** — one per PostgreSQL schema, showing all entities and relationships within that context.
3. **Relationship legend** — explains the notation.

Mermaid syntax is used throughout. The diagrams render in GitHub, GitLab, and most Markdown viewers. For complex diagrams, the `erDiagram` syntax is used; for cross-context relationships, a flowchart is used for clarity.

---

## Relationship Legend

| Notation | Meaning |
|---|---|
| `||--||` | One-to-one |
| `||--o{` | One-to-zero-or-many |
| `||--\|{` | One-to-one-or-many |
| `}o--o{` | Many-to-many (via join table) |
| `||--o|` | One-to-zero-or-one |

In the cross-context flowchart:
- `A --> B` means "A references B" (A has a foreign key to B).
- Dotted lines indicate cross-schema references (permitted but governed by the single-writer rule).

---

## High-Level Cross-Context Diagram

This diagram shows how the 10 bounded contexts relate. Each box is a PostgreSQL schema; arrows indicate the direction of dependency (the source schema references the target).

```mermaid
flowchart TD
    identity[identity schema<br/>users, credentials, sessions]
    content[content schema<br/>subjects, concepts, templates, versions]
    learning[learning schema<br/>enrollments, sessions, goals]
    assessment[assessment schema<br/>attempts, answers, instances]
    mastery[mastery schema<br/>mastery_scores, reviews]
    scheduling[scheduling schema<br/>daily_queues, configs]
    analytics[analytics schema<br/>snapshots, statistics]
    billing[billing schema<br/>subscriptions, invoices]
    administration[administration schema<br/>audit_logs, feature_flags]
    infrastructure[infrastructure schema<br/>outbox_events, jobs]

    identity --> content
    identity --> learning
    identity --> billing
    identity --> administration
    content --> learning
    content --> assessment
    content --> mastery
    content --> analytics
    learning --> assessment
    learning --> scheduling
    learning --> analytics
    assessment --> mastery
    assessment --> analytics
    mastery --> scheduling
    mastery --> analytics
    learning -.-> administration
    assessment -.-> infrastructure
    mastery -.-> infrastructure
    content -.-> infrastructure
    administration -.-> infrastructure
```

**Key observations:**
- `identity` is the root; many contexts reference users.
- `content` is referenced by learning (enrollment), assessment (attempts), mastery (concept linkage), and analytics.
- `assessment` writes to `mastery` via domain events (the Mastery Engine consumes `AttemptRecorded`).
- `infrastructure` is written to by all contexts (outbox events) but is owned by no single context.
- Cross-schema references are governed by the single-writer rule: each table is written by exactly one context.

---

## Schema: `identity`

```mermaid
erDiagram
    users ||--|| user_profiles : has
    users ||--o{ user_credentials : has
    users ||--o{ sessions : has

    users {
        uuid id PK
        string email UK
        string email_verified_at
        string status
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    user_profiles {
        uuid id PK
        uuid user_id FK
        string display_name
        string timezone
        jsonb preferences
        string avatar_url
        timestamp created_at
        timestamp updated_at
    }

    user_credentials {
        uuid id PK
        uuid user_id FK
        string credential_type
        string password_hash
        string provider
        string provider_user_id
        timestamp created_at
        timestamp updated_at
    }

    sessions {
        uuid id PK
        uuid user_id FK
        string refresh_token_hash
        string device_fingerprint
        inet last_ip
        string user_agent
        timestamp expires_at
        timestamp revoked_at
        timestamp created_at
    }
```

**Relationships:**
- `users` 1:1 `user_profiles` (composition — profile does not exist without user).
- `users` 1:many `user_credentials` (aggregation — a user has 1+ credentials).
- `users` 1:many `sessions` (aggregation — sessions are created and revoked).

---

## Schema: `content`

```mermaid
erDiagram
    tenants ||--|| subjects : owns
    subjects ||--o{ learning_paths : has
    subjects ||--o{ concepts : has
    subjects ||--o{ question_templates : has
    subjects ||--o{ content_versions : has

    learning_paths ||--o{ learning_path_items : contains
    concepts ||--o{ learning_path_items : appears_in
    concepts ||--o{ concept_dependencies : source
    concepts ||--o{ concept_dependencies : target
    concepts ||--o{ learning_objectives : has
    learning_objectives ||--o{ misconceptions : violated_by

    question_templates ||--o{ template_versions : versioned_as
    template_versions ||--o{ template_objectives : tests
    learning_objectives ||--o{ template_objectives : tested_by
    template_versions ||--o{ template_concepts : exercises
    concepts ||--o{ template_concepts : exercised_by
    template_versions ||--o{ distractors : has
    misconceptions ||--o{ distractors : detected_by
    template_versions ||--o{ hints : has
    template_versions ||--o{ explanations : has
    misconceptions ||--o{ explanations : variant_for

    content_versions ||--o{ template_versions : contains
    content_versions ||--o{ content_packs : produced_by
    content_packs ||--o{ content_review_requests : reviewed_via
    content_review_requests ||--o{ content_approvals : has
    users ||--o{ content_packs : authors
    users ||--o{ content_approvals : approves

    tenants {
        uuid id PK
        string code UK
        string name
        timestamp created_at
    }

    subjects {
        uuid id PK
        uuid tenant_id FK
        string code UK
        string name
        string slug
        text description
        string status
        timestamp created_at
        timestamp published_at
    }

    learning_paths {
        uuid id PK
        uuid subject_id FK
        string name
        jsonb graduation_criteria
        string status
        timestamp created_at
    }

    learning_path_items {
        uuid id PK
        uuid learning_path_id FK
        uuid concept_id FK
        int position
        timestamp created_at
    }

    concepts {
        uuid id PK
        uuid subject_id FK
        string slug
        string name
        text description
        string difficulty
        string status
        timestamp created_at
        timestamp published_at
    }

    concept_dependencies {
        uuid id PK
        uuid source_concept_id FK
        uuid target_concept_id FK
        string dependency_type
        string weight
        timestamp created_at
    }

    learning_objectives {
        uuid id PK
        uuid concept_id FK
        string statement
        string status
        timestamp created_at
    }

    misconceptions {
        uuid id PK
        uuid learning_objective_id FK
        string name
        text description
        text remediation
        string status
        timestamp created_at
    }

    question_templates {
        uuid id PK
        uuid subject_id FK
        string code
        string question_type
        string status
        timestamp created_at
    }

    template_versions {
        uuid id PK
        uuid template_id FK
        uuid content_version_id FK
        int version_number
        jsonb parameter_schema
        jsonb prompt_template
        jsonb correct_answer_generator
        jsonb distractor_generator
        jsonb explanation_template
        string difficulty
        timestamp published_at
    }

    template_objectives {
        uuid id PK
        uuid template_version_id FK
        uuid learning_objective_id FK
        timestamp created_at
    }

    template_concepts {
        uuid id PK
        uuid template_version_id FK
        uuid concept_id FK
        timestamp created_at
    }

    distractors {
        uuid id PK
        uuid template_version_id FK
        uuid misconception_id FK
        int position
        jsonb generator
        timestamp created_at
    }

    hints {
        uuid id PK
        uuid template_version_id FK
        int tier
        text content
        timestamp created_at
    }

    explanations {
        uuid id PK
        uuid template_version_id FK
        uuid misconception_id FK
        string outcome_key
        text content
        timestamp created_at
    }

    content_versions {
        uuid id PK
        uuid subject_id FK
        uuid tenant_id FK
        int version_number
        string status
        timestamp published_at
    }

    content_packs {
        uuid id PK
        uuid content_version_id FK
        uuid author_user_id FK
        string name
        jsonb artifact_summary
        timestamp published_at
    }

    content_review_requests {
        uuid id PK
        uuid content_pack_id FK
        uuid author_user_id FK
        string status
        timestamp submitted_at
        timestamp completed_at
    }

    content_approvals {
        uuid id PK
        uuid content_review_request_id FK
        uuid reviewer_user_id FK
        string stage
        string decision
        text notes
        timestamp created_at
    }
```

**Relationships:**
- `tenants` 1:1 `subjects` (current architecture; reserved for future multi-subject tenants).
- `subjects` 1:many `learning_paths`, `concepts`, `question_templates`, `content_versions`.
- `learning_paths` many:many `concepts` (via `learning_path_items`).
- `concepts` many:many `concepts` (via `concept_dependencies` — self-referential).
- `concepts` 1:many `learning_objectives` 1:many `misconceptions` (composition).
- `question_templates` 1:many `template_versions` (versioning).
- `template_versions` many:many `learning_objectives` (via `template_objectives`).
- `template_versions` many:many `concepts` (via `template_concepts`).
- `template_versions` 1:many `distractors`, `hints`, `explanations`.
- `distractors` many:1 `misconceptions` (tagged).
- `explanations` many:1 `misconceptions` (variant keyed by misconception).
- `content_versions` 1:many `template_versions` (contains).
- `content_versions` 1:many `content_packs` (produced by).
- `content_packs` 1:many `content_review_requests` 1:many `content_approvals`.

---

## Schema: `learning`

```mermaid
erDiagram
    users ||--o{ learner_enrollments : enrolls_as
    subjects ||--o{ learner_enrollments : has
    learning_paths ||--o{ learner_enrollments : follows
    learner_enrollments ||--o{ learning_goals : has
    learner_enrollments ||--o{ study_plans : has
    learner_enrollments ||--o{ study_sessions : has
    learner_enrollments ||--o{ streaks : has
    learner_enrollments ||--o{ achievements : earns
    achievement_types ||--o{ achievements : awards
    study_sessions ||--o{ learning_sessions : part_of
    study_sessions ||--o{ practice_queues : has
    learner_enrollments ||--o{ recommendations : receives
    learner_enrollments ||--o{ recommendation_history : has
    recommendations ||--o{ recommendation_history : lifecycle

    learner_enrollments {
        uuid id PK
        uuid user_id FK
        uuid subject_id FK
        uuid learning_path_id FK
        string status
        timestamp enrolled_at
        timestamp onboarded_at
        timestamp last_active_at
        timestamp unenrolled_at
    }

    learning_goals {
        uuid id PK
        uuid learner_enrollment_id FK
        string goal_type
        date target_date
        jsonb parameters
        string status
        timestamp created_at
        timestamp completed_at
    }

    study_plans {
        uuid id PK
        uuid learner_enrollment_id FK
        uuid learning_path_id FK
        uuid learning_goal_id FK
        date projected_graduation_date
        jsonb weekly_schedule
        string status
        timestamp generated_at
    }

    study_sessions {
        uuid id PK
        uuid learner_enrollment_id FK
        uuid learning_session_id FK
        string intent
        int target_question_count
        timestamp started_at
        timestamp ended_at
        string status
    }

    learning_sessions {
        uuid id PK
        uuid learner_enrollment_id FK
        timestamp started_at
        timestamp ended_at
        int study_session_count
    }

    practice_queues {
        uuid id PK
        uuid study_session_id FK
        jsonb question_ids
        int current_position
        timestamp generated_at
    }

    recommendations {
        uuid id PK
        uuid learner_enrollment_id FK
        string recommendation_type
        jsonb payload
        string status
        timestamp created_at
        timestamp acted_at
    }

    recommendation_history {
        uuid id PK
        uuid recommendation_id FK
        string event_type
        jsonb event_data
        timestamp created_at
    }

    achievements {
        uuid id PK
        uuid learner_enrollment_id FK
        uuid achievement_type_id FK
        jsonb criteria_snapshot
        timestamp awarded_at
    }

    achievement_types {
        uuid id PK
        uuid subject_id FK
        string code UK
        string name
        string category
        jsonb criteria
        string status
    }

    streaks {
        uuid id PK
        uuid learner_enrollment_id FK
        int current_streak
        int longest_streak
        date last_study_date
        timestamp updated_at
    }
```

**Relationships:**
- `users` 1:many `learner_enrollments` (a user can be a learner in multiple subjects).
- `subjects` 1:many `learner_enrollments`.
- `learning_paths` 1:many `learner_enrollments` (current path).
- `learner_enrollments` 1:many `learning_goals`, `study_plans`, `study_sessions`, `streaks`, `achievements`, `recommendations`.
- `study_sessions` many:1 `learning_sessions` (a learning session groups consecutive study sessions).
- `study_sessions` 1:1 `practice_queues` (current queue snapshot).
- `achievements` many:1 `achievement_types`.
- `recommendations` 1:many `recommendation_history` (lifecycle events).

---

## Schema: `assessment`

```mermaid
erDiagram
    learner_enrollments ||--o{ question_instances : served_to
    template_versions ||--o{ question_instances : instantiated_from
    content_versions ||--o{ question_instances : served_under
    study_sessions ||--o{ question_instances : served_in
    question_instances ||--o| attempts : answered_by
    learner_enrollments ||--o{ attempts : makes
    study_sessions ||--o{ attempts : contains
    content_versions ||--o{ attempts : references
    template_versions ||--o{ attempts : references
    algorithm_versions ||--o{ attempts : scored_under
    attempts ||--|| answers : has

    question_instances {
        uuid id PK
        uuid template_version_id FK
        uuid content_version_id FK
        uuid learner_enrollment_id FK
        uuid study_session_id FK
        bigint parameter_seed
        jsonb rendered_prompt
        jsonb rendered_choices
        jsonb correct_answer
        jsonb distractors_with_tags
        timestamp served_at
        timestamp answered_at
        string status
    }

    attempts {
        uuid id PK
        uuid question_instance_id FK
        uuid learner_enrollment_id FK
        uuid study_session_id FK
        uuid content_version_id FK
        uuid template_version_id FK
        uuid algorithm_version_id FK
        string scoring_outcome
        numeric partial_credit
        int time_to_answer_ms
        boolean hint_used
        jsonb hint_tiers_used
        uuid misconception_id FK
        timestamp created_at
    }

    answers {
        uuid id PK
        uuid attempt_id FK
        uuid question_instance_id FK
        string answer_type
        jsonb submitted_answer
        jsonb execution_result
        int revision_count
        timestamp submitted_at
    }
```

**Relationships:**
- `learner_enrollments` 1:many `question_instances` (served to).
- `template_versions` 1:many `question_instances` (instantiated from).
- `content_versions` 1:many `question_instances` (served under).
- `study_sessions` 1:many `question_instances` (served in).
- `question_instances` 1:0-or-1 `attempts` (an instance may be abandoned without an attempt).
- `learner_enrollments` 1:many `attempts`.
- `study_sessions` 1:many `attempts`.
- `attempts` many:1 `content_versions`, `template_versions`, `algorithm_versions` (triple versioning).
- `attempts` 1:1 `answers` (composition — an attempt has exactly one submitted answer).

**Critical: triple versioning** — every `attempts` row references `content_version_id`, `template_version_id`, and `algorithm_version_id`. This is the foundation of historical reproducibility (ADR-0011).

---

## Schema: `mastery`

```mermaid
erDiagram
    learner_enrollments ||--o{ mastery_scores : has
    concepts ||--o{ mastery_scores : measured_for
    algorithm_versions ||--o{ mastery_scores : computed_under
    learner_enrollments ||--o{ reviews : has
    concepts ||--o{ reviews : scheduled_for
    algorithm_versions ||--o{ reviews : computed_under
    attempts ||--o{ reviews : scheduled_by
    learner_enrollments ||--o{ learner_misconceptions : exhibits
    misconceptions ||--o{ learner_misconceptions : detected_in

    mastery_scores {
        uuid id PK
        uuid learner_enrollment_id FK
        uuid concept_id FK
        uuid algorithm_version_id FK
        numeric memory_score
        numeric durable_mastery_score
        numeric mastery_score_combined
        numeric confidence_interval
        int evidence_count
        string concept_state
        int version
        timestamp last_updated_at
        timestamp created_at
    }

    reviews {
        uuid id PK
        uuid learner_enrollment_id FK
        uuid concept_id FK
        uuid algorithm_version_id FK
        uuid scheduled_by_attempt_id FK
        timestamp due_at
        string priority
        interval review_interval
        timestamp last_reviewed_at
        timestamp created_at
        timestamp updated_at
    }

    learner_misconceptions {
        uuid id PK
        uuid learner_enrollment_id FK
        uuid misconception_id FK
        int detection_count
        string severity
        timestamp first_detected_at
        timestamp last_detected_at
        timestamp cleared_at
    }

    algorithm_versions {
        uuid id PK
        int version_number UK
        string name
        jsonb parameters
        text changelog
        boolean is_active
        timestamp promoted_at
    }
```

**Relationships:**
- `learner_enrollments` 1:many `mastery_scores` (one score per concept per learner).
- `concepts` 1:many `mastery_scores`.
- `algorithm_versions` 1:many `mastery_scores` (the version under which computed).
- `learner_enrollments` 1:many `reviews` (one scheduled review per concept per learner).
- `concepts` 1:many `reviews`.
- `algorithm_versions` 1:many `reviews`.
- `attempts` 1:many `reviews` (the attempt that scheduled this review).
- `learner_enrollments` 1:many `learner_misconceptions`.
- `misconceptions` 1:many `learner_misconceptions`.

**Critical: ADR-0008** — `mastery_scores` holds both `memory_score` and `durable_mastery_score` as columns, with `mastery_score_combined` as a generated column. This is the "combined, not averaged" decision.

**Critical: ADR-0011** — `mastery_scores.algorithm_version_id` records the version under which the score was computed, enabling reconstruction.

---

## Schema: `scheduling`

```mermaid
erDiagram
    learner_enrollments ||--o{ daily_queues : has
    subjects ||--o{ scheduling_configs : configured_by

    daily_queues {
        uuid id PK
        uuid learner_enrollment_id FK
        date queue_date
        jsonb question_template_version_ids
        jsonb completed_items
        string status
        timestamp generated_at
        timestamp completed_at
    }

    scheduling_configs {
        uuid id PK
        uuid subject_id FK
        int default_queue_size
        int cooldown_minutes
        jsonb priority_weights
        jsonb difficulty_adjustment_bounds
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
```

**Relationships:**
- `learner_enrollments` 1:many `daily_queues` (one per day per learner).
- `subjects` 1:many `scheduling_configs` (one active config per subject).

---

## Schema: `analytics`

```mermaid
erDiagram
    learner_enrollments ||--o{ learner_daily_snapshots : has
    concepts ||--o{ learner_daily_snapshots : for
    concepts ||--o{ concept_statistics : has
    content_versions ||--o{ concept_statistics : under
    template_versions ||--o{ template_statistics : has

    learner_daily_snapshots {
        uuid id PK
        uuid learner_enrollment_id FK
        uuid concept_id FK
        date snapshot_date
        numeric memory_score
        numeric durable_mastery_score
        numeric mastery_score_combined
        string concept_state
        int evidence_count
        timestamp created_at
    }

    concept_statistics {
        uuid id PK
        uuid concept_id FK
        uuid content_version_id FK
        date snapshot_date
        numeric avg_mastery_score
        numeric success_rate
        interval median_time_to_mastery
        numeric retention_30d
        int learner_count
        timestamp created_at
    }

    template_statistics {
        uuid id PK
        uuid template_version_id FK
        date snapshot_date
        numeric success_rate
        numeric discrimination
        jsonb distractor_distribution
        interval avg_time_to_answer
        numeric hint_usage_rate
        int attempt_count
        timestamp created_at
    }
```

**Relationships:**
- `learner_enrollments` 1:many `learner_daily_snapshots` (one per concept per day).
- `concepts` 1:many `learner_daily_snapshots`, `concept_statistics`.
- `content_versions` 1:many `concept_statistics` (stats are per content version).
- `template_versions` 1:many `template_statistics`.

---

## Schema: `billing`

```mermaid
erDiagram
    users ||--o{ subscriptions : has
    billing_plans ||--o{ subscriptions : subscribed_to
    subscriptions ||--o{ invoices : generates
    users ||--o{ invoices : billed

    billing_plans {
        uuid id PK
        string code
        int version_number
        string name
        int price_cents
        string currency
        string billing_period
        jsonb entitlements
        boolean is_active
        timestamp created_at
    }

    subscriptions {
        uuid id PK
        uuid user_id FK
        uuid billing_plan_id FK
        string status
        date current_period_start
        date current_period_end
        date canceled_at
        string payment_provider
        string provider_subscription_id
        timestamp created_at
        timestamp updated_at
    }

    invoices {
        uuid id PK
        uuid subscription_id FK
        uuid user_id FK
        int amount_cents
        string currency
        string status
        string provider_invoice_id
        date issued_at
        date paid_at
        timestamp created_at
    }
```

**Relationships:**
- `users` 1:many `subscriptions` (historical; one active at a time).
- `billing_plans` 1:many `subscriptions`.
- `subscriptions` 1:many `invoices`.
- `users` 1:many `invoices` (denormalized for query convenience).

---

## Schema: `administration`

```mermaid
erDiagram
    users ||--o{ audit_logs : performs
    users ||--o{ feature_flag_assignments : has
    feature_flags ||--o{ feature_flag_assignments : has
    users ||--o{ gdpr_requests : submits
    users ||--o{ organizations : member_of
    users ||--o{ notifications : receives

    audit_logs {
        uuid id PK
        uuid actor_user_id FK
        string action
        string target_type
        uuid target_id
        jsonb metadata
        inet actor_ip
        string user_agent
        string outcome
        timestamp created_at
    }

    feature_flags {
        uuid id PK
        string key UK
        string description
        jsonb targeting_rules
        boolean is_active
        string owner
        timestamp created_at
        timestamp retired_at
    }

    feature_flag_assignments {
        uuid id PK
        uuid feature_flag_id FK
        uuid user_id FK
        jsonb override_value
        timestamp created_at
    }

    system_settings {
        uuid id PK
        string key UK
        string value_type
        jsonb value
        text description
        timestamp updated_at
        uuid updated_by_user_id FK
    }

    gdpr_requests {
        uuid id PK
        uuid user_id FK
        string request_type
        string status
        jsonb request_metadata
        jsonb completion_metadata
        timestamp requested_at
        timestamp completed_at
    }

    organizations {
        uuid id PK
        string name
        string status
        uuid billing_subscription_id FK
        timestamp created_at
        timestamp dissolved_at
    }

    organization_members {
        uuid id PK
        uuid organization_id FK
        uuid user_id FK
        string role
        timestamp joined_at
        timestamp left_at
    }

    notifications {
        uuid id PK
        uuid user_id FK
        string notification_type
        string channel
        jsonb payload
        string status
        timestamp scheduled_at
        timestamp sent_at
        timestamp delivered_at
        timestamp opened_at
        timestamp dismissed_at
        timestamp created_at
    }
```

**Relationships:**
- `users` 1:many `audit_logs` (actor).
- `feature_flags` 1:many `feature_flag_assignments` (per-user overrides).
- `users` 1:many `feature_flag_assignments`.
- `users` 1:many `gdpr_requests`.
- `organizations` 1:many `organization_members` (join table; users are members of organizations).
- `users` 1:many `organization_members`.
- `users` 1:many `notifications`.

**Note:** `system_settings.updated_by_user_id` is a self-reference to `users` for audit.

---

## Schema: `infrastructure`

```mermaid
erDiagram
    users ||--o{ outbox_events : triggers

    outbox_events {
        uuid id PK
        string event_type
        uuid aggregate_id
        string aggregate_type
        uuid actor_user_id FK
        jsonb payload
        string payload_schema_version
        timestamp created_at
        timestamp dispatched_at
        int dispatch_attempt_count
        string status
    }

    background_jobs {
        uuid id PK
        string job_type
        jsonb payload
        string payload_hash
        string status
        int priority
        int attempt_count
        timestamp available_at
        timestamp started_at
        timestamp completed_at
        timestamp failed_at
        text last_error
        timestamp created_at
    }

    migration_history {
        uuid id PK
        int version UK
        string filename
        string checksum
        uuid applied_by_user_id
        timestamp applied_at
    }
```

**Relationships:**
- `users` 1:many `outbox_events` (actor; nullable for system events).
- `background_jobs` and `migration_history` have no FK relationships (they reference aggregates via JSONB payload).

---

## Cross-Context Relationship Summary

The most important cross-context relationships (and the ones engineers must understand):

| Source | Target | Cardinality | Purpose |
|---|---|---|---|
| `learning.learner_enrollments` | `identity.users` | many:1 | A learner is a user enrolled in a subject. |
| `learning.learner_enrollments` | `content.subjects` | many:1 | A learner is enrolled in a subject. |
| `learning.learner_enrollments` | `content.learning_paths` | many:1 | A learner follows a path. |
| `assessment.question_instances` | `content.template_versions` | many:1 | An instance is instantiated from a template version. |
| `assessment.question_instances` | `content.content_versions` | many:1 | An instance is served under a content version. |
| `assessment.attempts` | `content.content_versions` | many:1 | Triple versioning: content version. |
| `assessment.attempts` | `content.template_versions` | many:1 | Triple versioning: template version. |
| `assessment.attempts` | `mastery.algorithm_versions` | many:1 | Triple versioning: algorithm version. |
| `assessment.attempts` | `learning.study_sessions` | many:1 | An attempt belongs to a session. |
| `mastery.mastery_scores` | `learning.learner_enrollments` | many:1 | A score is per-learner. |
| `mastery.mastery_scores` | `content.concepts` | many:1 | A score is per-concept. |
| `mastery.mastery_scores` | `mastery.algorithm_versions` | many:1 | A score records its algorithm version. |
| `mastery.reviews` | `assessment.attempts` | many:1 | A review is scheduled by an attempt. |
| `analytics.learner_daily_snapshots` | `learning.learner_enrollments` | many:1 | A snapshot is per-learner. |
| `analytics.concept_statistics` | `content.content_versions` | many:1 | Stats are per content version. |
| `administration.audit_logs` | `identity.users` | many:1 | An audit log records the actor. |
| `infrastructure.outbox_events` | `identity.users` | many:1 | An event records the triggering actor. |

---

## Inheritance and Composition Notes

The Mastery Engine schema uses **no table inheritance** (PostgreSQL's `INHERITS` is avoided due to its limitations with foreign keys and partitioning). Inheritance-style relationships are modeled via:

- **Single-table inheritance with discriminator**: e.g., `user_credentials.credential_type` ('password' | 'oauth') discriminates the credential subtype within one table.
- **Class-table inheritance with shared PK**: not used (the complexity is not justified for the current entity set).

**Composition** (child cannot exist without parent) is enforced via:
- `user_profiles.user_id` NOT NULL with ON DELETE CASCADE.
- `learning_path_items.learning_path_id` NOT NULL with ON DELETE CASCADE.
- `template_objectives`, `template_concepts`, `distractors`, `hints`, `explanations` all have `template_version_id` NOT NULL with ON DELETE CASCADE.
- `attempts.answer_id` (or `answers.attempt_id` — see logical schema) enforces composition.

**Aggregation** (child can exist without parent but is owned by it) is modeled via:
- `user_credentials.user_id` NOT NULL but ON DELETE RESTRICT (a credential cannot outlive its user, but deletion is governed by application logic, not cascade).
- `sessions.user_id` NOT NULL with ON DELETE CASCADE.
- `learner_enrollments.user_id` NOT NULL with ON DELETE RESTRICT (unenrollment is a soft process).

---

## Dependency Notes

The dependency direction (which table must exist before another) follows the schema creation order:

1. `identity` (users, user_profiles, user_credentials, sessions) — no dependencies.
2. `content` (tenants, subjects, ..., content_versions) — depends on identity (for author/reviewer).
3. `learning` (learner_enrollments, ..., achievements) — depends on identity, content.
4. `assessment` (question_instances, attempts, answers) — depends on content, learning, mastery.
5. `mastery` (algorithm_versions, mastery_scores, reviews, learner_misconceptions) — depends on learning, content, assessment.
6. `scheduling` (daily_queues, scheduling_configs) — depends on learning, content.
7. `analytics` (snapshots, statistics) — depends on learning, content, mastery.
8. `billing` (billing_plans, subscriptions, invoices) — depends on identity.
9. `administration` (audit_logs, ..., organizations, notifications) — depends on identity.
10. `infrastructure` (outbox_events, background_jobs, migration_history) — depends on identity (for actor).

Migration scripts create schemas and tables in this order to satisfy foreign key dependencies.

---

*End of ERD.*
