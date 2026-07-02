# 10 — Migration Strategy

> Migration philosophy: backward compatibility, rollback, feature flags, zero downtime, data migration, version numbering.

---

## Migration Principles

1. **Backward compatibility** — every migration is backward-compatible with the previous version of the application. The application runs against the migrated schema without code changes (until a future deployment intentionally uses new schema features).
2. **Zero downtime** — migrations are applied without taking the application offline. This rules out any migration that holds an exclusive lock for more than a few seconds.
3. **Rollback-ready** — every migration has a documented rollback path. Rollback is tested in staging before production deployment.
4. **Feature-flagged** — schema changes that enable new features are deployed behind feature flags. The schema is migrated first; the feature is enabled later via flag.
5. **Expand-and-contract** — breaking changes follow the expand-and-contract pattern: add the new schema (expand), dual-write and backfill, switch reads, drop the old schema (contract).
6. **Versioned** — every migration has a monotonic version number, recorded in `migration_history`.
7. **Tested against production-size data** — migrations are tested against a full-size copy of the production database in staging.

---

## Migration Tooling

- **Tool**: a migration runner (e.g., Alembic for Python, Flyway, or a custom tool). The tool applies migrations in version order and records each in `migration_history`.
- **Format**: each migration is a Python or SQL file with `upgrade()` and `downgrade()` functions.
- **Checksum**: each migration file has a SHA-256 checksum, recorded in `migration_history.checksum`. A mismatch on re-run indicates the file was modified after application (forbidden).
- **Locking**: the migration runner acquires an advisory lock at the start of a migration to prevent concurrent migrations.

---

## Migration Patterns

### Pattern 1: Additive (non-breaking) migration

Adding a table, column (nullable or with default), index, or constraint that does not affect existing queries.

**Example**: add a `notes` column to `learner_enrollments`.

```python
def upgrade():
    op.add_column('learner_enrollments',
        sa.Column('notes', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('learner_enrollments', 'notes')
```

**Backward compatibility**: the old application ignores the new column; the new application uses it. No downtime.

**Rollback**: drop the column (data in `notes` is lost on rollback; acceptable because it's nullable and new).

---

### Pattern 2: Add column with NOT NULL and default

Adding a NOT NULL column requires a default (PostgreSQL 11+ adds the column instantly if there's a constant default).

**Example**: add `is_active` to `feature_flags` with default `true`.

```python
def upgrade():
    op.add_column('feature_flags',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

def downgrade():
    op.drop_column('feature_flags', 'is_active')
```

**Backward compatibility**: the old application reads the column as `true` (the default); the new application uses it. No downtime.

**Rollback**: drop the column. Any data written to `is_active = false` is lost on rollback; mitigate by ensuring the rollback is a last resort.

---

### Pattern 3: Expand-and-contract (breaking change)

Renaming a column, changing a type, or removing a column. This requires multiple migrations over multiple deployments.

**Example**: rename `learner_enrollments.status` to `learner_enrollments.enrollment_status` (and change its values).

**Phase 1 (expand)**: add the new column.

```python
def upgrade():
    op.add_column('learner_enrollments',
        sa.Column('enrollment_status', sa.Text(), nullable=True))
    # Backfill: copy status to enrollment_status with value mapping
    op.execute("""
        UPDATE learner_enrollments
        SET enrollment_status = CASE status
            WHEN 'pending_onboarding' THEN 'pending'
            WHEN 'active' THEN 'active'
            WHEN 'dormant' THEN 'dormant'
            WHEN 'unenrolled' THEN 'un enrolled'
        END
    """)
```

**Phase 2 (dual-write)**: deploy application code that writes to both `status` and `enrollment_status`.

**Phase 3 (switch reads)**: deploy application code that reads from `enrollment_status` (falling back to `status` if null).

**Phase 4 (contract)**: after verifying all reads use `enrollment_status`, drop `status`.

```python
def upgrade():
    op.drop_column('learner_enrollments', 'status')
```

**Backward compatibility**: each phase is backward-compatible with the previous application version.

**Rollback**: each phase is reversible. Phase 4 (drop `status`) is the point of no return; ensure phase 3 has been live for sufficient time (e.g., 1 week) before phase 4.

---

### Pattern 4: Index creation without lock

Creating an index on a large table would block writes. Use `CREATE INDEX CONCURRENTLY` to avoid the lock.

**Example**: add an index on `attempts(learner_enrollment_id, created_at)`.

```python
def upgrade():
    op.execute("CREATE INDEX CONCURRENTLY idx_attempts_enrollment_created_at ON assessment.attempts (learner_enrollment_id, created_at DESC)")

def downgrade():
    op.execute("DROP INDEX CONCURRENTLY idx_attempts_enrollment_created_at")
```

**Note**: `CREATE INDEX CONCURRENTLY` cannot run inside a transaction. The migration runner must disable transaction wrapping for this migration.

**Backward compatibility**: the index is added while the application continues to run. No downtime.

---

### Pattern 5: Constraint addition without lock

Adding a NOT NULL or CHECK constraint to an existing column requires a full table scan, which can block writes. Use the `NOT VALID` pattern for CHECK constraints and the multi-step pattern for NOT NULL.

**Example**: add a CHECK constraint to `attempts.scoring_outcome`.

```python
def upgrade():
    # Add the constraint as NOT VALID (no scan; existing rows not checked)
    op.execute("ALTER TABLE assessment.attempts ADD CONSTRAINT chk_attempts_scoring_outcome CHECK (scoring_outcome IN ('correct', 'incorrect', 'partial')) NOT VALID")
    # Validate the constraint in a separate transaction (scans but doesn't lock)
    op.execute("ALTER TABLE assessment.attempts VALIDATE CONSTRAINT chk_attempts_scoring_outcome")
```

**Backward compatibility**: the constraint is enforced for new writes immediately; existing rows are validated asynchronously. No downtime.

---

### Pattern 6: Partitioning an existing table

Partitioning an existing table requires creating a new partitioned table, copying data, and renaming. This is a multi-hour migration for large tables.

**Example**: partition `attempts` by `created_at` (monthly).

**Phase 1**: create the new partitioned table.

```sql
CREATE TABLE assessment.attempts_new (
    LIKE assessment.attempts INCLUDING ALL
) PARTITION BY RANGE (created_at);
```

**Phase 2**: create partitions for existing data range.

```sql
CREATE TABLE assessment.attempts_new_2026_01 PARTITION OF assessment.attempts_new FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
-- ... for each month ...
```

**Phase 3**: copy data (in batches to avoid locking).

```sql
INSERT INTO assessment.attempts_new SELECT * FROM assessment.attempts WHERE created_at >= '2026-01-01' AND created_at < '2026-02-01';
-- ... for each month ...
```

**Phase 4**: sync delta (any rows written during the copy) via triggers or CDC.

**Phase 5**: rename in a single transaction.

```sql
BEGIN;
ALTER TABLE assessment.attempts RENAME TO attempts_old;
ALTER TABLE assessment.attempts_new RENAME TO attempts;
COMMIT;
```

**Phase 6**: drop the old table after verification.

```sql
DROP TABLE assessment.attempts_old;
```

**Backward compatibility**: the application continues to read and write `attempts` throughout (the rename is atomic). No downtime, but a brief increase in latency during the copy phase.

**Rollback**: rename back (the old table is retained until phase 6).

---

### Pattern 7: Data migration (backfill)

Migrating data within a table (e.g., computing a denormalized column).

**Example**: backfill `mastery_scores.last_attempt_at` from `attempts`.

```python
def upgrade():
    # Batch the backfill to avoid long transactions
    op.execute("""
        WITH batch AS (
            SELECT ms.id, MAX(a.created_at) AS last_attempt_at
            FROM mastery.mastery_scores ms
            JOIN assessment.attempts a ON a.learner_enrollment_id = ms.learner_enrollment_id
            JOIN content.template_versions tv ON a.template_version_id = tv.id
            JOIN content.template_concepts tc ON tv.id = tc.template_version_id
            WHERE tc.concept_id = ms.concept_id
              AND ms.last_attempt_at IS NULL
            GROUP BY ms.id
            LIMIT 10000
        )
        UPDATE mastery.mastery_scores
        SET last_attempt_at = batch.last_attempt_at
        FROM batch
        WHERE mastery_scores.id = batch.id
    """)
    # Repeat until no rows updated
```

The migration is run in batches of 10,000 rows, committed per batch, to avoid long transactions. A separate job continues the backfill if the migration leaves rows unprocessed.

---

## Version Numbering

- **Format**: monotonic integer (1, 2, 3, ...).
- **Stored in**: `infrastructure.migration_history.version`.
- **No branching**: migrations are linear; no parallel migration branches. If two PRs add migrations simultaneously, they are renumbered on merge.
- **No skipping**: the migration runner applies all migrations in order; it does not skip versions.
- **No modification**: a migration that has been applied to any environment (including local dev) is immutable. Changes require a new migration.

---

## Backward Compatibility Rules

A migration is backward-compatible with the previous application version if:

1. **No column is removed** (until the contract phase of expand-and-contract).
2. **No column type is changed incompatibly** (use expand-and-contract for type changes).
3. **No constraint is added that would reject existing writes** (use `NOT VALID` for CHECK constraints; ensure NOT NULL columns have a default).
4. **No index is dropped that the application relies on** (the application's queries should not depend on specific indexes; the query planner chooses).
5. **No enum value is removed** (text + CHECK pattern allows adding values; removing values requires expand-and-contract).

If a migration violates any of these, it must be split into multiple migrations across multiple deployments.

---

## Rollback Strategy

Every migration has a `downgrade()` function. However, rollback is a last resort because:

1. **Data loss**: dropping a column or table loses data written after the migration.
2. **Cascading migrations**: rolling back migration N requires rolling back migrations N+1, N+2, ... first.
3. **State divergence**: if the application has been running with the new schema, its data may not be valid under the old schema.

**Rollback policy**:
- **Within the deployment window** (first 30 minutes after deployment): rollback is automatic if health checks fail.
- **After the deployment window**: rollback is manual, requires architecture review group approval, and is tested in staging first.
- **For data-loss rollbacks** (dropping a column): rollback is not attempted; instead, a forward-fix migration is written.

**Rollback testing**: every migration's `downgrade()` is tested in staging as part of the migration review. The test applies `upgrade()` then `downgrade()` then `upgrade()` again, verifying idempotency.

---

## Feature Flags and Migrations

Schema migrations and feature deployments are decoupled via feature flags:

1. **Migrate the schema** (additive) — the new schema is in place but unused.
2. **Deploy the application** (with feature flag off) — the application has the new code but does not use the new schema.
3. **Enable the feature flag** (gradually) — the application uses the new schema for a subset of users.
4. **Monitor** — if issues arise, disable the feature flag (no migration rollback needed).
5. **Fully enable** — the feature flag is enabled for all users.
6. **Retire the feature flag** (future) — the flag is removed.

This decoupling means schema migrations are low-risk (they are additive and unused) and feature rollouts are reversible (via the flag, not via migration rollback).

---

## Zero-Downtime Rules

To achieve zero downtime, migrations must:

1. **Not hold exclusive locks** for more than a few seconds. Use `CREATE INDEX CONCURRENTLY`, `NOT VALID` constraints, and batch operations.
2. **Not require application downtime**. The application continues to run against the schema throughout the migration.
3. **Be idempotent** where possible (re-running is safe).
4. **Be batchable** for large data migrations (avoid single long transactions).
5. **Be testable** against production-size data in staging.

**Migrations that violate these rules** (e.g., partitioning a 5B-row table) are scheduled during low-traffic windows (Sunday 2–4 AM) and may involve a brief read-only mode (the application serves cached data while the migration runs).

---

## Migration Review Process

Every migration PR is reviewed by:

1. **A senior engineer** — for correctness and style.
2. **A DBA or database-aware engineer** — for performance and lock implications.
3. **The architecture review group** (for migrations that change the data model materially) — for architectural conformance.

The review checklist:
- [ ] Migration is backward-compatible (or follows expand-and-contract).
- [ ] Migration has a tested `downgrade()`.
- [ ] Migration uses `CONCURRENTLY` for index creation on large tables.
- [ ] Migration uses `NOT VALID` for CHECK constraints on large tables.
- [ ] Migration is batched for large data backfills.
- [ ] Migration has been tested against production-size data in staging.
- [ ] Migration is documented (what it does, why, rollback plan).

---

## Migration History and Audit

`infrastructure.migration_history` records every applied migration:
- `version`, `filename`, `checksum`, `applied_by_user_id`, `applied_at`.

The table is append-only (no UPDATE or DELETE). The migration runner checks this table on startup and applies pending migrations in version order.

**Audit**: the migration history is part of the database audit trail. Any schema change is traceable to a migration, a version, an applier, and a timestamp.

---

## Emergency Migrations

In rare cases (e.g., a critical bug fix), an emergency migration may bypass the normal review process:

1. The migration is applied directly to production by a DBA.
2. The migration is back-filled into the migration repository within 24 hours.
3. The migration is reviewed retroactively by the architecture review group.

Emergency migrations are rare and documented in `audit_logs` (action = 'migration.emergency_apply').

---

*End of Migration Strategy.*
