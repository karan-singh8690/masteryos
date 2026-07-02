# 11 — Seed Data

> Seed strategy: system roles, Python Subject, concept categories, difficulty levels, mastery levels, question types, default settings.
> Seed data is the baseline state of the database before any user or content is added.

---

## Seed Data Principles

1. **Idempotent** — seed scripts can be run multiple times without duplicating data.
2. **Versioned** — seed data is versioned with the application; changes are migrations.
3. **Environment-aware** — production seeds are minimal; development seeds include sample data for testing.
4. **Separate from migrations** — seeds populate lookup tables and defaults; migrations create schema. Seeds are re-runnable; migrations are not.

---

## Seed Categories

### 1. System Roles and Permissions

The platform defines four roles (per Task 002 and ADR-0013):

| Role Code | Name | Description |
|---|---|---|
| `learner` | Learner | A user enrolled in a subject; can study and view their own progress. |
| `instructor` | Instructor | A user who authors and reviews content; scoped per subject. |
| `administrator` | Administrator | A user with platform-wide privileges; can manage users, content, and configuration. |
| `mentor` (future) | Mentor | A user who guides other learners; future role. |

**Permissions** (granted to roles):

| Permission Code | Description | Granted To |
|---|---|---|
| `identity:user:read_self` | Read own user profile. | learner, instructor, administrator |
| `identity:user:update_self` | Update own user profile. | learner, instructor, administrator |
| `identity:session:manage_self` | Manage own sessions. | learner, instructor, administrator |
| `learning:enrollment:create` | Enroll in a subject. | learner, instructor, administrator |
| `learning:enrollment:read_self` | Read own enrollments. | learner, instructor, administrator |
| `learning:session:create` | Start a study session. | learner, instructor, administrator |
| `learning:attempt:submit` | Submit an attempt. | learner, instructor, administrator |
| `learning:progress:read_self` | Read own progress. | learner, instructor, administrator |
| `content:concept:read` | Read published concepts. | learner, instructor, administrator |
| `content:concept:create` | Author a concept. | instructor, administrator |
| `content:concept:edit` | Edit a concept (revision). | instructor, administrator |
| `content:template:author` | Author a question template. | instructor, administrator |
| `content:pack:submit_review` | Submit a content pack for review. | instructor, administrator |
| `content:pack:review_peer` | Peer-review a content pack. | instructor, administrator |
| `content:pack:review_editorial` | Editorial-review a content pack. | instructor (senior), administrator |
| `content:pack:publish` | Publish a content pack. | administrator |
| `admin:user:suspend` | Suspend a user. | administrator |
| `admin:user:delete` | Anonymize a user (GDPR). | administrator |
| `admin:feature_flag:manage` | Manage feature flags. | administrator |
| `admin:system_settings:manage` | Manage system settings. | administrator |
| `admin:audit_log:read` | Read audit logs. | administrator |
| `billing:subscription:manage_self` | Manage own subscription. | learner, instructor, administrator |
| `billing:subscription:refund` | Refund a subscription. | administrator |
| `billing:invoice:read_self` | Read own invoices. | learner, instructor, administrator |
| `billing:invoice:read_all` | Read any user's invoices. | administrator |

**Seed implementation**: roles and permissions are seeded into `administration.system_settings` (as a JSONB document) or into dedicated `roles` and `permissions` tables (if added in a future migration). At launch, they are application-defined constants (the `Role` enum in code), with `audit_logs` recording role grants.

---

### 2. Python Subject (the first tenant)

The Python Subject is the first tenant, seeded at launch:

```sql
INSERT INTO content.tenants (id, code, name, status)
VALUES ('00000000-0000-0000-0000-000000000001', 'python', 'Python', 'active')
ON CONFLICT (code) DO NOTHING;

INSERT INTO content.subjects (id, tenant_id, code, name, slug, description, status, published_at)
VALUES (
    '00000000-0000-0000-0000-000000000010',
    '00000000-0000-0000-0000-000000000001',
    'python',
    'Python Technical Interview Preparation',
    'python',
    'Master Python concepts for technical interviews.',
    'published',
    now()
)
ON CONFLICT (code) DO NOTHING;
```

The Python Subject's initial content (concepts, objectives, misconceptions, templates) is authored by Instructors via the Content Pipeline (ADR-0009), not seeded. The seed only creates the subject shell.

---

### 3. Concept Categories

Concept categories are a classification within a subject (e.g., "Data Structures," "Algorithms," "Concurrency"). They are seeded as `system_settings` or as a `concept_categories` lookup table (added in a future migration if needed).

**Python Subject categories** (seeded):

| Category Code | Name |
|---|---|
| `data_structures` | Data Structures |
| `algorithms` | Algorithms |
| `concurrency` | Concurrency |
| `memory_model` | Memory Model |
| `standard_library` | Standard Library |
| `oop` | Object-Oriented Programming |
| `functional` | Functional Programming |
| `async_io` | Async I/O |
| `metaprogramming` | Metaprogramming |
| `performance` | Performance |
| `testing` | Testing |
| `debugging` | Debugging |

**Note**: at launch, `concepts` does not have a `category_id` column (categories are metadata, not a structural dimension). If category-based filtering becomes important, a migration adds the column and a `concept_categories` table.

---

### 4. Difficulty Levels

Difficulty levels are enum values (not a separate table):

| Difficulty | Numeric | Description |
|---|---|---|
| `easy` | 0.25 | Most learners answer correctly on first attempt. |
| `medium` | 0.50 | Mixed outcomes; typical difficulty. |
| `hard` | 0.75 | Most learners struggle; requires solid understanding. |

These are seeded as `system_settings` documentation (the enum values are in the `concepts.difficulty` CHECK constraint).

---

### 5. Mastery Levels (Concept State)

Mastery levels (Concept State, per Task 002 and ADR-0008):

| State | Mastery Score Range | Memory Score Range | Description |
|---|---|---|---|
| `unseen` | 0.000 | 0.000 | No attempts yet. |
| `novice` | 0.001–0.400 | any | Limited evidence; high uncertainty. |
| `developing` | 0.401–0.699 | any | Moderate evidence; mixed outcomes. |
| `proficient` | 0.700–0.849 | any | Strong evidence; reliable recall. |
| `mastered` | 0.850–1.000 | any | Durable mastery; survived spaced reviews. |
| `decayed` | any | < 0.500 | Memory fading; due for review. |

These are seeded as `system_settings` (the thresholds are in `scheduling_configs.mastery_threshold_proficient` and `mastery_threshold_mastered`).

---

### 6. Question Types

Question types (per Task 002):

| Question Type | Description | Answer Type |
|---|---|---|
| `multiple_choice` | Multiple-choice question with tagged distractors. | `multiple_choice` |
| `code_execution` | Coding exercise; answer is executable code. | `code` |
| `free_response` | Free-response question; answer is text. | `free_response` |

Seeded as enum values in the `question_templates.question_type` CHECK constraint.

---

### 7. Default Settings

System-wide default settings (seeded into `administration.system_settings`):

| Key | Value Type | Value | Description |
|---|---|---|---|
| `default_daily_goal_minutes` | integer | 30 | Default daily study time goal. |
| `default_session_question_count` | integer | 15 | Default questions per study session. |
| `default_adaptive_queue_size` | integer | 15 | Default adaptive queue size. |
| `default_daily_queue_size` | integer | 20 | Default daily queue size. |
| `default_cooldown_minutes` | integer | 30 | Default per-concept cooldown. |
| `default_review_interval_min_days` | integer | 1 | Minimum review interval. |
| `default_review_interval_max_days` | integer | 180 | Maximum review interval. |
| `default_mastery_threshold_proficient` | number | 0.70 | Mastery threshold for Proficient. |
| `default_mastery_threshold_mastered` | number | 0.85 | Mastery threshold for Mastered. |
| `default_memory_threshold` | number | 0.50 | Memory threshold for review trigger. |
| `session_merge_window_minutes` | integer | 15 | Window for grouping study sessions into learning sessions. |
| `session_inactivity_timeout_hours` | integer | 24 | Inactivity timeout for study sessions. |
| `streak_reset_window_hours` | integer | 24 | Window for streak reset. |
| `notification_digest_frequency` | string | `weekly` | Default notification digest frequency. |
| `gdpr_erasure_grace_period_days` | integer | 14 | Grace period before GDPR erasure. |
| `audit_log_retention_years` | integer | 7 | Audit log retention period. |
| `session_retention_days` | integer | 90 | Session retention post-expiry. |
| `notification_retention_days` | integer | 30 | Notification retention post-delivery. |

---

### 8. Default Feature Flags

Default feature flags (seeded into `administration.feature_flags`):

| Key | Default Value | Description | Owner |
|---|---|---|---|
| `mastery_engine_v2` | `false` | Future Mastery Engine v2 (off by default). | Architecture |
| `scheduler_adaptive_queue` | `true` | Adaptive queue (on by default). | Architecture |
| `code_execution_questions` | `false` | Code execution questions (off until Phase 2 sandbox is ready). | Engineering |
| `gdpr_erasure_automation` | `true` | Automated GDPR erasure (on by default). | Administration |
| `analytics_dashboard_v2` | `false` | Future analytics dashboard v2. | Analytics |

---

### 9. Algorithm Version 1 (the deterministic algorithm)

The first Algorithm Version is seeded:

```sql
INSERT INTO mastery.algorithm_versions (id, version_number, name, description, parameters, changelog, is_active, promoted_at)
VALUES (
    '00000000-0000-0000-0000-000000000100',
    1,
    'Deterministic v1',
    'The initial deterministic Mastery Engine algorithm (per ADR-0007).',
    '{
        "memory_decay_rate_per_day": 0.05,
        "mastery_consolidation_rate": 0.10,
        "review_interval_expansion_factor": 2.5,
        "review_interval_contraction_factor": 0.3,
        "mastery_threshold_proficient": 0.70,
        "mastery_threshold_mastered": 0.85,
        "memory_threshold": 0.50,
        "weakness_severity_thresholds": {"mild": 0.40, "moderate": 0.30, "severe": 0.20},
        "hint_usage_mastery_penalty": 0.30,
        "time_to_answer_normalization_ms": 30000
    }'::jsonb,
    'Initial algorithm.',
    true,
    now()
)
ON CONFLICT (version_number) DO NOTHING;
```

---

### 10. Billing Plans

Default billing plans (seeded):

```sql
INSERT INTO billing.billing_plans (id, code, version_number, name, price_cents, currency, billing_period, entitlements, is_active)
VALUES
    ('00000000-0000-0000-0000-000000000200', 'free', 1, 'Free', 0, 'USD', 'monthly',
        '{"max_questions_per_day": 20, "advanced_analytics": false, "priority_support": false}'::jsonb, true),
    ('00000000-0000-0000-0000-000000000201', 'pro', 1, 'Pro', 1900, 'USD', 'monthly',
        '{"max_questions_per_day": null, "advanced_analytics": true, "priority_support": true}'::jsonb, true)
ON CONFLICT (code, version_number) DO NOTHING;
```

---

### 11. Achievement Types (platform-wide)

Default platform-wide achievement types (seeded):

```sql
INSERT INTO learning.achievement_types (id, subject_id, code, name, description, category, criteria, status)
VALUES
    ('00000000-0000-0000-0000-000000000300', NULL, 'first_concept_mastered', 'First Concept Mastered',
        'Awarded when the learner masters their first concept.', 'milestone',
        '{"type": "concept_state_change", "to_state": "mastered", "count": 1}'::jsonb, 'active'),
    ('00000000-0000-0000-0000-000000000301', NULL, 'ten_concepts_proficient', 'Ten Concepts Proficient',
        'Awarded when 10 concepts reach Proficient or above.', 'milestone',
        '{"type": "concept_count_at_state", "min_state": "proficient", "count": 10}'::jsonb, 'active'),
    ('00000000-0000-0000-0000-000000000302', NULL, 'seven_day_streak', 'Seven-Day Streak',
        'Awarded for studying 7 consecutive days.', 'streak',
        '{"type": "streak", "days": 7}'::jsonb, 'active'),
    ('00000000-0000-0000-0000-000000000303', NULL, 'thirty_day_streak', 'Thirty-Day Streak',
        'Awarded for studying 30 consecutive days.', 'streak',
        '{"type": "streak", "days": 30}'::jsonb, 'active')
ON CONFLICT (code) DO NOTHING;
```

Subject-specific achievement types (e.g., "Python Full Path Graduate") are created when the subject's learning paths are published, not seeded.

---

### 12. Notification Templates

Notification templates are seeded as `system_settings` or in a `notification_templates` table (if added in a future migration). At launch, they are application-defined constants.

**Default notification types**:

| Type | Channel | Trigger |
|---|---|---|
| `review_reminder` | email, in_app | Reviews due tomorrow. |
| `streak_nudge` | in_app | Streak at risk (no study today). |
| `weekly_progress_digest` | email | Weekly progress summary. |
| `milestone_achieved` | in_app | Achievement awarded. |
| `goal_at_risk` | email, in_app | Study plan projected to miss target date. |
| `interview_readiness_milestone` | email, in_app | Interview readiness crossed a threshold. |

---

## Seed Script Execution

Seed scripts are run:
1. **On initial database creation** — to establish the baseline.
2. **After major version upgrades** — to add new seed data (idempotently).
3. **In CI** — to set up a fresh database for integration tests.

**Idempotency**: every seed statement uses `ON CONFLICT DO NOTHING` (or equivalent) to avoid duplicates on re-run.

**Ordering**: seeds are ordered by dependency (tenants before subjects; algorithm versions before mastery scores; billing plans before subscriptions).

---

## Development Environment Seeds

In development and staging, additional seed data is added for testing:

- **Sample users**: 10 users with varied enrollment states.
- **Sample content**: 5 concepts with objectives, misconceptions, and templates per concept.
- **Sample attempts**: 100 attempts per sample user.
- **Sample mastery scores**: derived from sample attempts.
- **Sample study sessions**: 5 sessions per sample user.

Development seeds are clearly marked (`is_dev_seed = true` on a settings flag, or in a separate `dev_seeds` schema) and never run in production.

---

*End of Seed Data.*
