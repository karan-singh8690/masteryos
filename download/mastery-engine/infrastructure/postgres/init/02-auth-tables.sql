-- Task 016: Production authentication tables.
-- Adds: verification_tokens, password_reset_tokens, refresh_tokens,
--       mfa_secrets, mfa_recovery_codes, security_incidents, auth_audit_logs
-- All in the identity schema.

-- ============================================================
-- Email Verification Tokens
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.verification_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL,
    token_type      TEXT NOT NULL DEFAULT 'email_verification'
                    CHECK (token_type IN ('email_verification', 'email_change')),
    expires_at      TIMESTAMPTZ NOT NULL,
    consumed_at     TIMESTAMPTZ,
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_verification_tokens_hash
    ON identity.verification_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_verification_tokens_user_active
    ON identity.verification_tokens(user_id)
    WHERE consumed_at IS NULL;

-- ============================================================
-- Password Reset Tokens
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.password_reset_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    consumed_at     TIMESTAMPTZ,
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_password_reset_tokens_hash
    ON identity.password_reset_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_active
    ON identity.password_reset_tokens(user_id)
    WHERE consumed_at IS NULL;

-- ============================================================
-- Refresh Tokens (with rotation tracking via token_family_id)
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.refresh_tokens (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    session_id              UUID NOT NULL REFERENCES identity.sessions(id) ON DELETE CASCADE,
    token_hash              TEXT NOT NULL,
    token_family_id         UUID NOT NULL,
    expires_at              TIMESTAMPTZ NOT NULL,
    consumed_at             TIMESTAMPTZ,
    revoked_at              TIMESTAMPTZ,
    revoke_reason           TEXT,
    rotated_to_token_hash   TEXT,
    ip_address              INET,
    user_agent              TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_refresh_tokens_revoke_reason
        CHECK ((revoked_at IS NULL) OR (revoke_reason IS NOT NULL))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_refresh_tokens_hash
    ON identity.refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_family
    ON identity.refresh_tokens(token_family_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_active
    ON identity.refresh_tokens(user_id)
    WHERE revoked_at IS NULL AND consumed_at IS NULL;

-- ============================================================
-- MFA Secrets (TOTP)
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.mfa_secrets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    secret_encrypted    BYTEA NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'active', 'revoked')),
    enabled_at          TIMESTAMPTZ,
    revoked_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mfa_secrets_user_active
    ON identity.mfa_secrets(user_id, status)
    WHERE status = 'active';

-- ============================================================
-- MFA Recovery Codes (one-time use)
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.mfa_recovery_codes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    code_hash       TEXT NOT NULL,
    consumed_at     TIMESTAMPTZ,
    consumed_ip     INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mfa_recovery_codes_hash
    ON identity.mfa_recovery_codes(code_hash);
CREATE INDEX IF NOT EXISTS idx_mfa_recovery_codes_user_active
    ON identity.mfa_recovery_codes(user_id)
    WHERE consumed_at IS NULL;

-- ============================================================
-- Security Incidents
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.security_incidents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES identity.users(id) ON DELETE SET NULL,
    incident_type   TEXT NOT NULL
                    CHECK (incident_type IN (
                        'refresh_token_reuse', 'login_brute_force', 'mfa_brute_force',
                        'suspicious_ip', 'account_takeover_attempt', 'password_spray',
                        'session_hijack_attempt', 'rate_limit_violation', 'other'
                    )),
    severity        TEXT NOT NULL DEFAULT 'warning'
                    CHECK (severity IN ('info', 'warning', 'critical')),
    description     TEXT NOT NULL,
    ip_address      INET,
    user_agent      TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    resolved_at     TIMESTAMPTZ,
    resolved_by     UUID,
    resolution_notes TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_security_incidents_user
    ON identity.security_incidents(user_id);
CREATE INDEX IF NOT EXISTS idx_security_incidents_type_created
    ON identity.security_incidents(incident_type, created_at);
CREATE INDEX IF NOT EXISTS idx_security_incidents_unresolved
    ON identity.security_incidents(resolved_at)
    WHERE resolved_at IS NULL;

-- ============================================================
-- Auth Audit Log (immutable append-only)
-- ============================================================
CREATE TABLE IF NOT EXISTS identity.auth_audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID,
    action          TEXT NOT NULL
                    CHECK (action IN (
                        'LOGIN_SUCCESS', 'LOGIN_FAILURE', 'LOGOUT', 'LOGOUT_ALL',
                        'PASSWORD_CHANGED', 'PASSWORD_CHANGE_FAILED', 'PASSWORD_RESET', 'PASSWORD_RESET_REQUESTED',
                        'EMAIL_VERIFIED', 'VERIFICATION_EMAIL_RESENT',
                        'MFA_ENABLED', 'MFA_DISABLED', 'MFA_SETUP_INITIATED', 'MFA_VERIFIED',
                        'MFA_RECOVERY_CODE_USED', 'MFA_RECOVERY_CODES_REGENERATED',
                        'REFRESH_ROTATED', 'REFRESH_REUSE_DETECTED',
                        'SESSION_REVOKED', 'SESSION_EXPIRED',
                        'SECURITY_INCIDENT', 'USER_REGISTERED', 'PROFILE_UPDATED'
                    )),
    success         BOOLEAN NOT NULL DEFAULT TRUE,
    ip_address      INET,
    user_agent      TEXT,
    session_id      UUID,
    correlation_id  TEXT,
    details         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_user_created
    ON identity.auth_audit_logs(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_action_created
    ON identity.auth_audit_logs(action, created_at);
CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_correlation
    ON identity.auth_audit_logs(correlation_id);

-- ============================================================
-- Add token_version column to users (for invalidating all tokens
-- on password change). Default = 1; bump on password change.
-- ============================================================
ALTER TABLE identity.users
    ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 1;

ALTER TABLE identity.users
    ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ;

-- ============================================================
-- Update sessions table to add token_family_id (if not present)
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'identity'
          AND table_name = 'sessions'
          AND column_name = 'token_family_id'
    ) THEN
        ALTER TABLE identity.sessions
            ADD COLUMN token_family_id UUID NOT NULL DEFAULT gen_random_uuid();
    END IF;
END $$;

-- Grant privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA identity TO mastery;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA identity TO mastery;

DO $$
BEGIN
    RAISE NOTICE 'Task 016: Production authentication tables created.';
END $$;
