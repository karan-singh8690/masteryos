-- Task 025: Closed Beta tables.
-- Adds: beta_invites, beta_feedback, beta_analytics_events

-- ============================================================
-- Beta Invites
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.beta_invites (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL,
    invite_token    TEXT NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    used_at         TIMESTAMPTZ,
    created_by      UUID NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_beta_invites_email CHECK (email ~* '^[^@]+@[^@]+\.[^@]+$')
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_beta_invites_token
    ON identity.beta_invites(invite_token);
CREATE INDEX IF NOT EXISTS idx_beta_invites_email
    ON identity.beta_invites(email);
CREATE INDEX IF NOT EXISTS idx_beta_invites_unused
    ON identity.beta_invites(used_at)
    WHERE used_at IS NULL;

-- ============================================================
-- Beta Feedback
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.beta_feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    rating          INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    category        TEXT NOT NULL CHECK (category IN (
        'bug', 'feature_request', 'ui_ux', 'content', 'performance', 'other'
    )),
    comment         TEXT NOT NULL,
    screenshot_url  TEXT,
    -- Auto-captured context
    correlation_id  TEXT,
    browser         TEXT,
    platform        TEXT,
    route           TEXT,
    user_agent      TEXT,
    -- Metadata
    status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'resolved', 'closed')),
    resolved_at     TIMESTAMPTZ,
    resolved_by     UUID,
    resolution_notes TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_beta_feedback_user
    ON identity.beta_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_status
    ON identity.beta_feedback(status);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_category
    ON identity.beta_feedback(category);

-- ============================================================
-- Beta Analytics Events
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics.beta_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID,
    event_type      TEXT NOT NULL,
    event_data      JSONB NOT NULL DEFAULT '{}'::jsonb,
    session_id      TEXT,
    correlation_id  TEXT,
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_beta_events_type_created
    ON analytics.beta_events(event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_beta_events_user
    ON analytics.beta_events(user_id);
CREATE INDEX IF NOT EXISTS idx_beta_events_created
    ON analytics.beta_events(created_at);

-- Grant privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON identity.beta_invites TO mastery;
GRANT SELECT, INSERT, UPDATE, DELETE ON identity.beta_feedback TO mastery;
-- Task 025-deploy fix #16: beta_events is append-only by design (per
-- docs/beta/closed-beta.md architectural decision #5). Revoke UPDATE
-- and DELETE so the DB enforces the invariant, not just convention.
GRANT SELECT, INSERT ON analytics.beta_events TO mastery;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA identity TO mastery;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO mastery;

DO $$
BEGIN
    RAISE NOTICE 'Task 025: Closed Beta tables created. (Task 025-deploy: beta_events is append-only.)';
END $$;
