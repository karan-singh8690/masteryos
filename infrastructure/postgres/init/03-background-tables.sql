-- Task 017: Background processing tables.
-- Adds: dead_letter_events, notifications, notification_preferences,
--       scheduled_jobs, worker_heartbeats, email_delivery_log, outbox_leases

-- ============================================================
-- Dead Letter Events (events that exhausted retries)
-- ============================================================
CREATE TABLE IF NOT EXISTS infrastructure.dead_letter_events (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_event_id       UUID NOT NULL,
    event_type              VARCHAR(100) NOT NULL,
    aggregate_id            UUID NOT NULL,
    aggregate_type          VARCHAR(50) NOT NULL,
    actor_user_id           UUID,
    payload                 JSONB NOT NULL,
    originating_schema      VARCHAR(50) NOT NULL,
    error_message           TEXT NOT NULL,
    error_type              VARCHAR(200) NOT NULL,
    stack_trace             TEXT,
    retry_count             INTEGER NOT NULL DEFAULT 0,
    retry_history           JSONB NOT NULL DEFAULT '[]'::jsonb,
    subscriber_handler      VARCHAR(255),
    final_worker_id         VARCHAR(100),
    severity                VARCHAR(20) NOT NULL DEFAULT 'error'
                            CHECK (severity IN ('warning', 'error', 'critical')),
    resolved_at             TIMESTAMPTZ,
    resolved_by             UUID,
    resolution_notes        TEXT,
    replayed_as_event_id    UUID,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dead_letters_event_type
    ON infrastructure.dead_letter_events(event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_dead_letters_aggregate
    ON infrastructure.dead_letter_events(aggregate_id);
CREATE INDEX IF NOT EXISTS idx_dead_letters_unresolved
    ON infrastructure.dead_letter_events(resolved_at)
    WHERE resolved_at IS NULL;

-- ============================================================
-- Notifications
-- ============================================================
CREATE TABLE IF NOT EXISTS administration.notifications (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL,
    notification_type       VARCHAR(128) NOT NULL,
    channel                 VARCHAR(20) NOT NULL DEFAULT 'in_app'
                            CHECK (channel IN ('in_app', 'email', 'push', 'sms')),
    priority                VARCHAR(20) NOT NULL DEFAULT 'normal'
                            CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    status                  VARCHAR(20) NOT NULL DEFAULT 'queued'
                            CHECK (status IN ('queued', 'sent', 'delivered', 'opened', 'dismissed', 'failed')),
    title                   TEXT NOT NULL,
    body                    TEXT NOT NULL,
    payload                 JSONB NOT NULL DEFAULT '{}'::jsonb,
    locale                  VARCHAR(10) NOT NULL DEFAULT 'en-US',
    dedup_key               VARCHAR(255),
    scheduled_at            TIMESTAMPTZ NOT NULL,
    expires_at              TIMESTAMPTZ,
    sent_at                 TIMESTAMPTZ,
    delivered_at            TIMESTAMPTZ,
    opened_at               TIMESTAMPTZ,
    dismissed_at            TIMESTAMPTZ,
    failed_at               TIMESTAMPTZ,
    failure_reason          TEXT,
    related_aggregate_id    UUID,
    related_aggregate_type  VARCHAR(50),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_status
    ON administration.notifications(user_id, status);
CREATE INDEX IF NOT EXISTS idx_notifications_status_scheduled
    ON administration.notifications(status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
    ON administration.notifications(user_id)
    WHERE status IN ('queued', 'sent', 'delivered');
CREATE UNIQUE INDEX IF NOT EXISTS idx_notifications_dedup
    ON administration.notifications(user_id, notification_type, dedup_key)
    WHERE dedup_key IS NOT NULL;

-- ============================================================
-- Notification Preferences
-- ============================================================
CREATE TABLE IF NOT EXISTS administration.notification_preferences (
    id                                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                                 UUID NOT NULL UNIQUE,
    email_enabled                           BOOLEAN NOT NULL DEFAULT TRUE,
    in_app_enabled                          BOOLEAN NOT NULL DEFAULT TRUE,
    push_enabled                            BOOLEAN NOT NULL DEFAULT FALSE,
    sms_enabled                             BOOLEAN NOT NULL DEFAULT FALSE,
    security_notifications_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    achievement_notifications_enabled       BOOLEAN NOT NULL DEFAULT TRUE,
    marketing_notifications_enabled         BOOLEAN NOT NULL DEFAULT FALSE,
    reminder_notifications_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    digest_frequency                        VARCHAR(20) NOT NULL DEFAULT 'immediate'
                                            CHECK (digest_frequency IN ('immediate', 'hourly', 'daily', 'weekly', 'never')),
    quiet_hours_start                       VARCHAR(5),
    quiet_hours_end                         VARCHAR(5),
    timezone                                VARCHAR(50) NOT NULL DEFAULT 'UTC',
    created_at                              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- Scheduled Jobs (recurring)
-- ============================================================
CREATE TABLE IF NOT EXISTS infrastructure.scheduled_jobs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    VARCHAR(100) NOT NULL UNIQUE,
    description             TEXT,
    handler_name            VARCHAR(255) NOT NULL,
    schedule_type           VARCHAR(20) NOT NULL
                            CHECK (schedule_type IN ('cron', 'interval', 'one_time')),
    schedule_expr           VARCHAR(100) NOT NULL,
    status                  VARCHAR(20) NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'paused', 'disabled')),
    next_run_at             TIMESTAMPTZ NOT NULL,
    last_run_at             TIMESTAMPTZ,
    last_run_status         VARCHAR(20),
    last_run_error          TEXT,
    last_run_duration_ms    INTEGER,
    locked_by               VARCHAR(100),
    locked_at               TIMESTAMPTZ,
    lock_expires_at         TIMESTAMPTZ,
    run_count               INTEGER NOT NULL DEFAULT 0,
    failure_count           INTEGER NOT NULL DEFAULT 0,
    consecutive_failures    INTEGER NOT NULL DEFAULT 0,
    max_runtime_seconds     INTEGER NOT NULL DEFAULT 300,
    retry_count             INTEGER NOT NULL DEFAULT 3,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_next_run
    ON infrastructure.scheduled_jobs(next_run_at)
    WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_locked
    ON infrastructure.scheduled_jobs(locked_by)
    WHERE locked_by IS NOT NULL;

-- ============================================================
-- Worker Heartbeats
-- ============================================================
CREATE TABLE IF NOT EXISTS infrastructure.worker_heartbeats (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id               VARCHAR(100) NOT NULL UNIQUE,
    worker_type             VARCHAR(50) NOT NULL,
    hostname                VARCHAR(255),
    process_id              INTEGER,
    status                  VARCHAR(20) NOT NULL DEFAULT 'starting',
    last_seen_at            TIMESTAMPTZ NOT NULL,
    started_at              TIMESTAMPTZ NOT NULL,
    jobs_processed          INTEGER NOT NULL DEFAULT 0,
    jobs_failed             INTEGER NOT NULL DEFAULT 0,
    current_job             VARCHAR(255),
    shutdown_requested      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_worker_heartbeats_status
    ON infrastructure.worker_heartbeats(status);
CREATE INDEX IF NOT EXISTS idx_worker_heartbeats_last_seen
    ON infrastructure.worker_heartbeats(last_seen_at);

-- ============================================================
-- Email Delivery Log
-- ============================================================
CREATE TABLE IF NOT EXISTS infrastructure.email_delivery_log (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id         UUID,
    user_id                 UUID,
    to_address              TEXT NOT NULL,
    from_address            TEXT NOT NULL,
    subject                 TEXT NOT NULL,
    template_name           VARCHAR(100) NOT NULL,
    status                  VARCHAR(20) NOT NULL DEFAULT 'queued'
                            CHECK (status IN ('queued', 'sent', 'delivered', 'bounced', 'failed', 'deferred')),
    message_id              TEXT,
    smtp_response           TEXT,
    error_message           TEXT,
    bounce_type             VARCHAR(50),
    bounce_reason           TEXT,
    attempt_count           INTEGER NOT NULL DEFAULT 0,
    next_retry_at           TIMESTAMPTZ,
    sent_at                 TIMESTAMPTZ,
    delivered_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_email_delivery_user
    ON infrastructure.email_delivery_log(user_id);
CREATE INDEX IF NOT EXISTS idx_email_delivery_status
    ON infrastructure.email_delivery_log(status, created_at);
CREATE INDEX IF NOT EXISTS idx_email_delivery_message_id
    ON infrastructure.email_delivery_log(message_id);

-- ============================================================
-- Outbox Leases (visibility timeout)
-- ============================================================
CREATE TABLE IF NOT EXISTS infrastructure.outbox_leases (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outbox_event_id         UUID NOT NULL UNIQUE,
    worker_id               VARCHAR(100) NOT NULL,
    acquired_at             TIMESTAMPTZ NOT NULL,
    expires_at              TIMESTAMPTZ NOT NULL,
    released_at             TIMESTAMPTZ,
    release_reason          VARCHAR(50),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_outbox_leases_expires
    ON infrastructure.outbox_leases(expires_at)
    WHERE released_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_outbox_leases_worker
    ON infrastructure.outbox_leases(worker_id);

-- ============================================================
-- Extend outbox_events with lease + retry tracking columns
-- (added via ALTER for backward compat)
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'infrastructure'
          AND table_name = 'outbox_events'
          AND column_name = 'leased_until'
    ) THEN
        ALTER TABLE infrastructure.outbox_events
            ADD COLUMN leased_until TIMESTAMPTZ;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'infrastructure'
          AND table_name = 'outbox_events'
          AND column_name = 'leased_by'
    ) THEN
        ALTER TABLE infrastructure.outbox_events
            ADD COLUMN leased_by VARCHAR(100);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'infrastructure'
          AND table_name = 'outbox_events'
          AND column_name = 'next_retry_at'
    ) THEN
        ALTER TABLE infrastructure.outbox_events
            ADD COLUMN next_retry_at TIMESTAMPTZ;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'infrastructure'
          AND table_name = 'outbox_events'
          AND column_name = 'retry_history'
    ) THEN
        ALTER TABLE infrastructure.outbox_events
            ADD COLUMN retry_history JSONB NOT NULL DEFAULT '[]'::jsonb;
    END IF;
END $$;

-- Grant privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA infrastructure TO mastery;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA administration TO mastery;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA infrastructure TO mastery;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA administration TO mastery;

DO $$
BEGIN
    RAISE NOTICE 'Task 017: Background processing tables created.';
END $$;
