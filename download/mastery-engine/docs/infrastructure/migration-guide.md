# Migration Guide

> How Alembic migrations are structured and applied.

---

## Migration Philosophy

1. **Backward-compatible by default** — migrations don't break running applications.
2. **Zero-downtime** — no migration holds an exclusive lock for more than a few seconds.
3. **Expand-and-contract** — breaking changes follow: add new → dual-write → switch reads → drop old.
4. **Rollback-ready** — every migration has a tested `downgrade()`.
5. **Versioned** — monotonic version numbers recorded in `migration_history`.

## Alembic Configuration

- **Config**: `backend/alembic.ini`
- **Environment**: `backend/alembic/env.py` (async, uses application settings)
- **Versions**: `backend/alembic/versions/`
- **Database URL**: loaded from `DATABASE_URL` environment variable

## Migration Commands

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "create users table"

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

## Naming Conventions

- **Migration files**: `NNNN_description.py` (Alembic auto-generates the number).
- **Constraints**: `chk_<table>_<purpose>`, `uq_<table>_<purpose>`, `fk_<table>_<referenced>`, `idx_<table>_<columns>`.
- **Indexes**: `idx_<table>_<columns>`, `gin_<table>_<column>`, `brin_<table>_<column>`.

## Initial Migration

The initial migration creates:
- 10 PostgreSQL schemas (identity, content, learning, assessment, mastery, scheduling, analytics, billing, administration, infrastructure).
- Extensions (uuid-ossp, citext, pg_trgm, btree_gin).
- All tables with columns, constraints, indexes, and foreign keys per Task 004.

## Migration Patterns

### Additive (non-breaking)
```python
def upgrade():
    op.add_column('users', sa.Column('new_field', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('users', 'new_field')
```

### Add NOT NULL with default
```python
def upgrade():
    op.add_column('feature_flags', sa.Column('is_active', sa.Boolean(),
        nullable=False, server_default='true'))
```

### Create index concurrently
```python
def upgrade():
    op.execute("CREATE INDEX CONCURRENTLY idx_attempts_enrollment ON assessment.attempts (learner_enrollment_id)")

def downgrade():
    op.execute("DROP INDEX CONCURRENTLY idx_attempts_enrollment")
```

### Add CHECK constraint (NOT VALID)
```python
def upgrade():
    op.execute("ALTER TABLE assessment.attempts ADD CONSTRAINT chk_attempts_outcome CHECK (scoring_outcome IN (...)) NOT VALID")
    op.execute("ALTER TABLE assessment.attempts VALIDATE CONSTRAINT chk_attempts_outcome")
```

## Testing Migrations

1. **Staging**: apply against a full-size copy of production.
2. **Upgrade + downgrade + upgrade**: verify idempotency.
3. **Checksum verification**: migration file checksums match `migration_history`.

## Production Deployment

1. Migrations run as part of the deployment pipeline (before the application starts).
2. The application checks `migration_history` on startup and fails if migrations are pending.
3. Emergency migrations (rare) are applied directly by a DBA and back-filled into the repository within 24 hours.
