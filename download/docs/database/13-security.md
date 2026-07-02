# 13 — Security

> Database security model: least privilege, roles, encryption, secrets, PII isolation, audit, Row-Level Security, SQL injection protection.
> Implements ASD Section 12.

---

## Security Principles

1. **Least privilege** — each database role has only the privileges it needs.
2. **Defense in depth** — security is layered (network, database, application).
3. **Encrypt everywhere** — at rest, in transit, and field-level for PII.
4. **Audit everything privileged** — every privileged action is logged.
5. **Assume breach** — the design limits blast radius if any layer is compromised.

---

## 1. Network Security

- **TLS 1.2+** for all database connections (application ↔ PostgreSQL, replica ↔ primary, CDC ↔ primary).
- **Private network** — the PostgreSQL instance is not publicly accessible; it resides in a private subnet, accessible only from the application's subnet.
- **Security groups / firewall rules** — only the application's IP range can connect to PostgreSQL on port 5432.
- **VPC peering** — for cross-region replication, VPC peering with restrictive security groups.

---

## 2. Database Roles (Least Privilege)

The database defines several roles, each with minimal privileges:

### `app_write` (application write role)
- **Privileges**: INSERT, UPDATE on tables in all schemas (per the single-writer rule, the application enforces which context writes which table; the database role has broad privileges, but the application layer restricts writes to the owning context).
- **No privileges**: DROP, ALTER, TRUNCATE, GRANT.
- **Append-only tables**: the role has INSERT but not UPDATE/DELETE on `attempts`, `audit_logs`, `outbox_events` (dispatched), `migration_history`, `content_versions`, `template_versions`, `algorithm_versions`. UPDATE/DELETE is revoked explicitly.

### `app_read` (application read role)
- **Privileges**: SELECT on all tables.
- **No privileges**: INSERT, UPDATE, DELETE, DROP, ALTER.
- **Used for**: read-only endpoints (dashboard, progress, admin portal reads).

### `analytics_read` (analytics reader)
- **Privileges**: SELECT on analytics tables, and SELECT on operational tables via materialized views (not direct access to `attempts`).
- **No privileges**: writes of any kind.
- **Used for**: the analytics read replica and the analytics warehouse CDC pipeline.

### `gdpr_anonymizer` (GDPR erasure role)
- **Privileges**: UPDATE on `users`, `user_profiles`, `learner_enrollments`, `audit_logs`, `outbox_events`, `answers`; DELETE on `user_credentials`, `sessions`, `learning_goals`, `study_plans`, `recommendations`, `recommendation_history`, `streaks`, `notifications`, `feature_flag_assignments`, `organization_members`, `practice_queues`.
- **No privileges**: INSERT, DROP, ALTER.
- **Used for**: only the GDPR anonymization background job. Tightly controlled; the job's credentials are stored in the secrets manager.
- **Audit**: every action by this role is logged in `audit_logs` with `action = 'gdpr.anonymize'`.

### `migration_runner` (schema migration role)
- **Privileges**: CREATE, ALTER, DROP on schemas and tables; INSERT on `migration_history`.
- **No privileges**: SELECT, UPDATE, DELETE on application data (the migration runner does not read or modify user data, except in data migration migrations which use `app_write`).
- **Used for**: only during deployment windows. Not available to the application at runtime.

### `dba` (database administrator)
- **Privileges**: all privileges.
- **Used for**: emergency operations, manual interventions.
- **Audit**: every action by this role is logged in `audit_logs`.

### `postgres` (superuser)
- **Privileges**: superuser.
- **Used for**: initial setup, major version upgrades. Never used by the application or routine operations.

---

## 3. Schema-Level Privileges

Each bounded context's application role has write privileges only to its own schema:

```sql
-- The application role has broad privileges, but the application enforces the single-writer rule.
-- For defense in depth, schema-level restrictions could be added:
GRANT USAGE ON SCHEMA identity TO app_write;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA identity TO app_write;
GRANT SELECT ON ALL TABLES IN SCHEMA identity TO app_read;
-- ... repeat for each schema ...
```

**Note**: at launch, the application uses a single `app_write` role with broad privileges, relying on the application layer (repository pattern, single-writer rule) to enforce context boundaries. At scale (Scenario 3+), per-context roles may be introduced for defense in depth.

---

## 4. Row-Level Security (RLS)

RLS is used to enforce data isolation where the application's authorization is insufficient or where defense in depth is warranted.

### RLS on `learner_enrollments`

A learner should only see their own enrollments:

```sql
ALTER TABLE learning.learner_enrollments ENABLE ROW LEVEL SECURITY;

CREATE POLICY learner_enrollments_isolation ON learning.learner_enrollments
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id')::uuid);
```

The application sets `app.current_user_id` at the start of each request:

```sql
SET LOCAL app.current_user_id = '<user-uuid>';
```

**Note**: RLS is a defense-in-depth measure; the application's authorization layer (per ASD Section 12.2) is the primary enforcement. RLS catches application bugs that would otherwise leak data.

### RLS on `mastery_scores`, `reviews`, `learner_misconceptions`

These tables are queried by `learner_enrollment_id`, which links to `learner_enrollments.user_id`. RLS policies join through `learner_enrollments` to check ownership:

```sql
ALTER TABLE mastery.mastery_scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY mastery_scores_isolation ON mastery.mastery_scores
    FOR SELECT
    USING (
        learner_enrollment_id IN (
            SELECT id FROM learning.learner_enrollments
            WHERE user_id = current_setting('app.current_user_id')::uuid
        )
    );
```

### RLS on `attempts`, `answers`

Same pattern: RLS checks ownership via `learner_enrollments`.

### RLS bypass

The `dba` and `analytics_read` roles bypass RLS (via `BYPASSRLS` attribute) for administrative and analytics access.

---

## 5. Encryption

### Encryption in Transit

- TLS 1.2+ for all connections (application ↔ database, replica ↔ primary, CDC ↔ database).
- Certificate-based authentication for replica and CDC connections.
- HSTS for the application (enforces HTTPS for API clients).

### Encryption at Rest

- **Database volume encryption**: the PostgreSQL data directory resides on an encrypted volume (AWS EBS encryption, GCP disk encryption, or LUKS for self-hosted).
- **Backup encryption**: backups are encrypted with separate keys (per ASD Section 12.7).
- **WAL encryption**: WAL files are on the encrypted volume; additional WAL encryption is available via PostgreSQL's `ssl_*` or third-party tools (not native in PostgreSQL 16; native WAL encryption is expected in a future version).

### Field-Level Encryption (PII)

PII columns are encrypted at the application layer using envelope encryption with KMS-managed keys:

| Column | Encryption |
|---|---|
| `users.email` | Encrypted at application layer (envelope encryption with KMS); stored as ciphertext. **Note**: this conflicts with the citext unique index. Resolution: store `email_hash` (SHA-256 of the email) for uniqueness checks, and `email_encrypted` for retrieval. The application decrypts on read. |
| `user_profiles.display_name` | Encrypted at application layer. |
| `user_profiles.avatar_url` | Not encrypted (public URL). |
| `user_credentials.password_hash` | Already a hash (argon2id); no additional encryption. |
| `user_credentials.mfa_secret_encrypted` | Encrypted (envelope encryption). |
| `sessions.device_fingerprint` | Encrypted at application layer. |
| `audit_logs.metadata` | May contain PII; encrypted selectively (specific fields within the JSONB). |
| `gdpr_requests.request_metadata` | May contain PII; encrypted selectively. |

**Envelope encryption pattern**:
1. A Data Encryption Key (DEK) is generated per row (or per column).
2. The DEK encrypts the PII value.
3. The DEK is encrypted with the KMS Key Encryption Key (KEK).
4. The encrypted DEK and the encrypted value are stored together.

**Key rotation**: the KEK is rotated quarterly. Rotation re-encrypts DEKs (not the underlying data), which is fast.

---

## 6. Secrets Management

- **Database credentials**: stored in the secrets manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault); fetched at application startup.
- **KMS keys**: managed by the cloud KMS; key policies restrict access to the application role.
- **Replication credentials**: stored in the secrets manager; rotated quarterly.
- **Local development**: `.env` file (gitignored); never contains production secrets.
- **CI/CD**: secrets injected via the CI provider's secret store; never logged.

**Secret rotation**:
- Database passwords: annually, or on personnel turnover.
- KMS keys: quarterly.
- JWT signing keys: quarterly (per ASD Section 12.6).
- OAuth client secrets: when the provider rotates them.

---

## 7. PII Isolation

PII is isolated to the `identity` schema (`users`, `user_profiles`, `user_credentials`) and select columns in other schemas (`sessions.device_fingerprint`, `audit_logs.metadata`, `gdpr_requests.request_metadata`).

**PII inventory** (maintained as a living document):

| Table | Column | PII Type | Encryption |
|---|---|---|---|
| `users` | `email` | Email | Field-level (envelope) |
| `user_profiles` | `display_name` | Name | Field-level (envelope) |
| `user_profiles` | `avatar_url` | (URL, may identify) | None (public URL) |
| `user_credentials` | `password_hash` | (hash, not PII) | Already a hash |
| `user_credentials` | `mfa_secret_encrypted` | MFA secret | Field-level (envelope) |
| `sessions` | `device_fingerprint` | Device identifier | Field-level (envelope) |
| `sessions` | `last_ip` | IP address | None (retained 90 days) |
| `sessions` | `user_agent` | User agent | None (may contain PII) |
| `audit_logs` | `actor_ip` | IP address | None (retained 7 years) |
| `audit_logs` | `metadata` | May contain PII | Selective field-level |
| `answers` | `submitted_answer` (free_response) | May contain PII | None (anonymized on erasure) |
| `gdpr_requests` | `request_metadata` | May contain PII | Selective field-level |
| `billing.invoices` | (provider_invoice_id) | (reference, not PII) | None |

**PII access logging**: every read of a PII column is logged in `audit_logs` if the read is by an administrator (learner reads of their own PII are not logged, to avoid log bloat).

---

## 8. Audit

Every privileged action is logged in `administration.audit_logs` (append-only, partitioned by month, retained 7 years).

**Audited actions**:
- Content publish, deprecate, version rollback.
- User support actions (password reset, entitlement override, refund).
- Admin configuration changes (feature flags, system settings, rate limits).
- Authentication events (login, logout, failed login, MFA enable/disable).
- GDPR requests (submission, processing, completion).
- Schema migrations (apply, rollback).
- Role grants and revocations.
- Data exports (GDPR access requests).

**Audit log fields**: `actor_user_id`, `action`, `target_type`, `target_id`, `metadata` (JSONB), `actor_ip`, `user_agent`, `correlation_id`, `outcome`, `failure_reason`, `created_at`.

**Audit log access**: only `administrator` role can read audit logs (via the Admin Portal). The `audit_log:read` permission governs access.

---

## 9. SQL Injection Protection

- **Parameterized queries everywhere**: the application uses parameterized queries (via asyncpg or SQLAlchemy) for all database access. No string concatenation of SQL.
- **ORM usage**: SQLAlchemy's ORM provides additional protection (queries are constructed programmatically).
- **Input validation**: Pydantic validates all input at the API boundary (per ASD Section 12.5); invalid input is rejected before reaching the database.
- **No dynamic SQL**: the application does not construct SQL from user input. Where dynamic queries are needed (e.g., analytics), the dynamic parts are column names or whitelisted values, never user-supplied strings.
- **Least privilege**: even if SQL injection occurs, the `app_write` role's limited privileges constrain the damage (no DROP, no ALTER).
- **RLS**: even if SQL injection bypasses the application's authorization, RLS prevents cross-user data access.

---

## 10. Append-Only Enforcement

Append-only tables (`attempts`, `audit_logs`, `outbox_events` dispatched, `migration_history`, version tables) are protected by:

1. **REVOKE UPDATE, DELETE** from `app_write`.
2. **BEFORE UPDATE/DELETE trigger** that raises an exception (defense in depth).
3. **The `gdpr_anonymizer` role** is the only role with UPDATE on `attempts` and `answers`, and only for anonymization ( tightly controlled and audited).

---

## 11. Connection Security

- **TLS**: all connections use TLS 1.2+.
- **Certificate validation**: the application validates the PostgreSQL server certificate.
- **Client certificates**: the replica and CDC connections use client certificates for mutual TLS.
- **Connection limits**: each role has a connection limit (e.g., `app_write` 100, `app_read` 200, `analytics_read` 50).
- **Idle timeout**: idle connections are closed after 10 minutes (configurable via `tcp_keepalives_idle`).

---

## 12. Backup Security

- **Backup encryption**: backups are encrypted with separate keys (not the same as the production data encryption keys).
- **Backup access**: only the `dba` role can restore backups; restore operations are audited.
- **Backup retention**: per `14-backup-recovery.md`.
- **Backup testing**: quarterly restore drills verify backup integrity (per ASD Section 17.10).

---

## 13. Vulnerability Management

- **PostgreSQL version**: tracked; security patches applied within 7 days of release.
- **Extension versions**: tracked; updated with PostgreSQL upgrades.
- **Dependency scanning**: the application's Python and TypeScript dependencies are scanned (Snyk, Dependabot) for vulnerabilities.
- **Penetration testing**: annual penetration testing includes the database (per `future-adr-suggestions.md` F-023).

---

## 14. Incident Response

- **Database breach suspected**: the incident response runbook includes database-specific steps (rotate credentials, revoke suspicious sessions, restore from backup if data corruption).
- **Audit log review**: the audit log is the primary forensic source; the incident response team reviews relevant entries.
- **Communication**: per GDPR (ASD Section 12.8), a breach affecting PII requires 72-hour notification to authorities and affected users.

---

*End of Security.*
