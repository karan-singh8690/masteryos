-- Task 026: Closed Beta Operations Platform tables.
--
-- Adds:
--   identity.beta_feedback_votes      — votes on feedback items (Part 4)
--   identity.beta_feedback_tags       — tags + roadmap linkage (Part 4)
--   administration.release_notes      — versioned release notes (Part 8)
--   administration.release_stages     — canary/stable/rollback tracking (Part 8)
--   analytics.experiment_assignments  — persisted A/B assignments (Part 10)
--   analytics.experiment_results      — aggregated experiment outcomes (Part 10)
--
-- All statements are idempotent (CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS).
-- All grants follow the existing convention: SELECT, INSERT, UPDATE, DELETE to `mastery`.

-- ============================================================
-- Part 4: Feedback Platform — votes + roadmap linkage
-- ============================================================

CREATE TABLE IF NOT EXISTS identity.beta_feedback_votes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_id     UUID NOT NULL REFERENCES identity.beta_feedback(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL,
    vote            SMALLINT NOT NULL DEFAULT 1 CHECK (vote IN (-1, 1)),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One vote per user per feedback item.
CREATE UNIQUE INDEX IF NOT EXISTS idx_beta_feedback_votes_unique
    ON identity.beta_feedback_votes(feedback_id, user_id);

CREATE INDEX IF NOT EXISTS idx_beta_feedback_votes_feedback
    ON identity.beta_feedback_votes(feedback_id);

CREATE INDEX IF NOT EXISTS idx_beta_feedback_votes_user
    ON identity.beta_feedback_votes(user_id);

-- Feedback priority + roadmap linkage (added as a separate table so the
-- existing beta_feedback table is not altered — backward compatible).
CREATE TABLE IF NOT EXISTS identity.beta_feedback_meta (
    feedback_id     UUID PRIMARY KEY REFERENCES identity.beta_feedback(id) ON DELETE CASCADE,
    priority        TEXT NOT NULL DEFAULT 'normal'
                    CHECK (priority IN ('low', 'normal', 'high', 'urgent', 'blocker')),
    roadmap_status  TEXT NOT NULL DEFAULT 'untriaged'
                    CHECK (roadmap_status IN ('untriaged', 'planned', 'in_progress', 'shipped', 'wont_fix', 'duplicate')),
    roadmap_link    TEXT,
    duplicate_of    UUID REFERENCES identity.beta_feedback(id) ON DELETE SET NULL,
    tags            JSONB NOT NULL DEFAULT '[]'::jsonb,
    assigned_to     UUID,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      UUID
);

CREATE INDEX IF NOT EXISTS idx_beta_feedback_meta_priority
    ON identity.beta_feedback_meta(priority);

CREATE INDEX IF NOT EXISTS idx_beta_feedback_meta_roadmap
    ON identity.beta_feedback_meta(roadmap_status);

-- ============================================================
-- Part 8: Release Management
-- ============================================================

CREATE TABLE IF NOT EXISTS administration.release_notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version         TEXT NOT NULL UNIQUE,
    release_type    TEXT NOT NULL DEFAULT 'patch'
                    CHECK (release_type IN ('major', 'minor', 'patch', 'hotfix', 'beta')),
    title           TEXT NOT NULL,
    summary         TEXT,
    body            TEXT NOT NULL,
    features        JSONB NOT NULL DEFAULT '[]'::jsonb,
    bug_fixes       JSONB NOT NULL DEFAULT '[]'::jsonb,
    breaking_changes JSONB NOT NULL DEFAULT '[]'::jsonb,
    known_issues    JSONB NOT NULL DEFAULT '[]'::jsonb,
    feature_freeze  BOOLEAN NOT NULL DEFAULT FALSE,
    published_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      UUID
);

CREATE INDEX IF NOT EXISTS idx_release_notes_published
    ON administration.release_notes(published_at DESC)
    WHERE published_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_release_notes_type
    ON administration.release_notes(release_type);

CREATE TABLE IF NOT EXISTS administration.release_stages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    release_note_id     UUID NOT NULL REFERENCES administration.release_notes(id) ON DELETE CASCADE,
    stage               TEXT NOT NULL
                        CHECK (stage IN ('planned', 'building', 'canary', 'staged', 'live', 'rolled_back', 'abandoned')),
    rollout_percentage  INTEGER NOT NULL DEFAULT 0 CHECK (rollout_percentage BETWEEN 0 AND 100),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,
    notes               TEXT,
    triggered_by        UUID
);

CREATE INDEX IF NOT EXISTS idx_release_stages_release
    ON administration.release_stages(release_note_id);

CREATE INDEX IF NOT EXISTS idx_release_stages_stage
    ON administration.release_stages(stage);

-- ============================================================
-- Part 10: Experiment Platform (persistent A/B testing)
-- ============================================================

CREATE TABLE IF NOT EXISTS analytics.experiments (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT,
    experiment_type     TEXT NOT NULL DEFAULT 'ab'
                        CHECK (experiment_type IN ('ab', 'feature_rollout', 'recommendation', 'queue', 'explanation', 'ai_vs_rule')),
    variant_a           TEXT NOT NULL,
    variant_b           TEXT NOT NULL,
    rollout_percentage  INTEGER NOT NULL DEFAULT 50 CHECK (rollout_percentage BETWEEN 0 AND 100),
    status              TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'running', 'completed', 'stopped')),
    target_metric       TEXT,
    min_sample_size     INTEGER NOT NULL DEFAULT 100,
    started_at          TIMESTAMPTZ,
    ended_at            TIMESTAMPTZ,
    winner              TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_experiments_status
    ON analytics.experiments(status);

CREATE TABLE IF NOT EXISTS analytics.experiment_assignments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id   TEXT NOT NULL REFERENCES analytics.experiments(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL,
    variant         TEXT NOT NULL,
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One assignment per user per experiment (sticky bucketing).
CREATE UNIQUE INDEX IF NOT EXISTS idx_experiment_assignments_unique
    ON analytics.experiment_assignments(experiment_id, user_id);

CREATE INDEX IF NOT EXISTS idx_experiment_assignments_exp
    ON analytics.experiment_assignments(experiment_id);

CREATE INDEX IF NOT EXISTS idx_experiment_assignments_user
    ON analytics.experiment_assignments(user_id);

CREATE TABLE IF NOT EXISTS analytics.experiment_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id       TEXT NOT NULL REFERENCES analytics.experiments(id) ON DELETE CASCADE,
    variant             TEXT NOT NULL,
    sample_size         INTEGER NOT NULL DEFAULT 0,
    metric_value        DOUBLE PRECISION,
    metric_std_error    DOUBLE PRECISION,
    conversion_count    INTEGER NOT NULL DEFAULT 0,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_experiment_results_exp
    ON analytics.experiment_results(experiment_id, variant);

-- ============================================================
-- Grants
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA identity TO mastery;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA administration TO mastery;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO mastery;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA identity TO mastery;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA administration TO mastery;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO mastery;

DO $$
BEGIN
    RAISE NOTICE 'Task 026: Closed Beta Operations Platform tables created.';
END $$;
