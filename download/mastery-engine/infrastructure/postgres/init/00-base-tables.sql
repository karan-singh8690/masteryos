-- Task 025-deploy: Base tables required by the application before any
-- feature-specific init scripts run.
--
-- This file is loaded alphabetically BEFORE 01-create-schemas.sql, but
-- 01-create-schemas.sql is idempotent and grants USAGE on schemas, so the
-- schemas will exist by the time the 02/03/04 scripts run.
--
-- The tables created here are the minimal set referenced by FKs in
-- 02-auth-tables.sql, 03-background-tables.sql, and 04-beta-tables.sql,
-- as well as by the application's `Base.metadata.create_all()` call.
--
-- Without this file, the chicken-and-egg ordering is:
--   1. Docker starts postgres with an empty volume.
--   2. Docker runs 01-create-schemas.sql (creates 10 schemas).
--   3. Docker runs 02-auth-tables.sql → FAILS because identity.users doesn't exist.
--   4. App starts, Base.metadata.create_all() creates identity.users.
--   5. Manual re-run of 02/03/04 is required.
--
-- With this file:
--   1. Docker starts postgres.
--   2. 00-base-tables.sql runs first (creates schemas inline if missing,
--      then creates users, sessions, user_profiles, user_credentials,
--      outbox_events).
--   3. 01-create-schemas.sql runs (idempotent — schemas already exist).
--   4. 02/03/04 run cleanly because their FK targets exist.
--   5. App starts; Base.metadata.create_all() is idempotent (CREATE TABLE
--      IF NOT EXISTS) and skips already-existing tables.
--
-- All statements are idempotent (CREATE TABLE IF NOT EXISTS, CREATE INDEX
-- IF NOT EXISTS, ALTER TABLE ... ADD COLUMN IF NOT EXISTS) so this file is
-- safe to re-run.

-- ============================================================
-- Schemas (created here too in case 00 runs before 01)
-- ============================================================
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS infrastructure;

-- ============================================================
-- identity.users
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.users (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                       TEXT NOT NULL,
    email_verified_at           TIMESTAMPTZ,
    status                      TEXT NOT NULL DEFAULT 'pending_verification'
                                CHECK (status IN ('pending_verification', 'active', 'suspended', 'deactivated', 'pending_deletion', 'anonymized')),
    role                        TEXT NOT NULL DEFAULT 'learner'
                                CHECK (role IN ('learner', 'instructor', 'content_editor', 'organization_admin', 'administrator', 'system_admin')),
    mfa_enabled                 BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret_encrypted        BYTEA,
    anonymized_at               TIMESTAMPTZ,
    deleted_at                  TIMESTAMPTZ,
    token_version               INTEGER NOT NULL DEFAULT 1,
    password_changed_at         TIMESTAMPTZ,
    last_login_at               TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Unique email among non-deleted users
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_active
    ON identity.users(email)
    WHERE deleted_at IS NULL;

-- ============================================================
-- identity.user_profiles
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.user_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    display_name    TEXT NOT NULL,
    timezone        TEXT NOT NULL DEFAULT 'UTC',
    locale          TEXT NOT NULL DEFAULT 'en-US',
    avatar_url      TEXT,
    preferences     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user
    ON identity.user_profiles(user_id);

-- ============================================================
-- identity.user_credentials
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.user_credentials (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    credential_type     TEXT NOT NULL
                        CHECK (credential_type IN ('password', 'oauth')),
    password_hash       TEXT,
    provider            TEXT,
    provider_user_id    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (
        (credential_type = 'password' AND password_hash IS NOT NULL)
        OR
        (credential_type = 'oauth' AND provider IS NOT NULL AND provider_user_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_credentials_oauth
    ON identity.user_credentials(provider, provider_user_id)
    WHERE credential_type = 'oauth';

CREATE INDEX IF NOT EXISTS idx_user_credentials_user
    ON identity.user_credentials(user_id);

-- ============================================================
-- identity.sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.sessions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    refresh_token_hash      TEXT NOT NULL,
    token_family_id         UUID NOT NULL DEFAULT gen_random_uuid(),
    device_fingerprint      TEXT,
    last_ip                 INET,
    user_agent              TEXT,
    expires_at              TIMESTAMPTZ NOT NULL,
    revoked_at              TIMESTAMPTZ,
    revoke_reason           TEXT,
    last_seen_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((revoked_at IS NULL) OR (revoke_reason IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_active
    ON identity.sessions(user_id)
    WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_sessions_token_family
    ON identity.sessions(token_family_id);

-- ============================================================
-- infrastructure.outbox_events
-- ============================================================
CREATE TABLE IF NOT EXISTS infrastructure.outbox_events (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type                  TEXT NOT NULL,
    aggregate_id                UUID NOT NULL,
    aggregate_type              TEXT NOT NULL,
    actor_user_id               UUID,
    payload                     JSONB NOT NULL,
    payload_schema_version      TEXT NOT NULL DEFAULT '1',
    originating_schema          TEXT NOT NULL,
    status                      TEXT NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'dispatched', 'dead_lettered')),
    dispatch_attempt_count      INTEGER NOT NULL DEFAULT 0,
    last_dispatch_error         TEXT,
    dispatched_at               TIMESTAMPTZ,
    -- Task 017: visibility timeout + retry tracking
    leased_until                TIMESTAMPTZ,
    leased_by                   VARCHAR(100),
    next_retry_at               TIMESTAMPTZ,
    retry_history               JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_outbox_pending
    ON infrastructure.outbox_events(status, created_at)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_outbox_aggregate
    ON infrastructure.outbox_events(aggregate_id);

CREATE INDEX IF NOT EXISTS idx_outbox_event_type
    ON infrastructure.outbox_events(event_type, created_at);

-- ============================================================
-- Grants (also in 01-create-schemas.sql but harmless to repeat)
-- ============================================================
GRANT USAGE ON SCHEMA identity TO mastery;
GRANT USAGE ON SCHEMA infrastructure TO mastery;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA identity TO mastery;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA infrastructure TO mastery;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA identity TO mastery;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA infrastructure TO mastery;

DO $$
BEGIN
    RAISE NOTICE 'Task 025-deploy: Base tables (users, user_profiles, user_credentials, sessions, outbox_events) created.';
END $$;
