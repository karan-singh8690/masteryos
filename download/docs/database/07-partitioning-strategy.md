# 07 — Partitioning Strategy

> Which tables require partitioning, partition keys, partition types, and trade-offs.
> Partitioning is the primary scalability mechanism for the database (ASD Section 13.3, ADR-0002).

---

## Partitioning Principles

1. **Partition append-heavy, time-ordered tables by time** — `attempts`, `outbox_events`, `audit_logs`, etc. benefit from monthly partitions with partition pruning.
2. **Do not partition small or slowly-growing tables** — the overhead outweighs the benefit.
3. **Do not partition tables queried primarily by non-time keys** — `mastery_scores` is queried by `learner_enrollment_id`, not by time; partitioning by time would not help.
4. **Co-locate related tables on the same partition key** — `attempts` and `answers` are partitioned by the same key (monthly by `created_at` / `submitted_at`) to enable co-located joins.
5. **Plan partitioning before the table reaches 100M rows** — partitioning an existing table is a multi-hour migration; designing for it from day one is cheap.

---

## Tables Requiring Partitioning

| Table | Partition Key | Type | Cadence | Trigger |
|---|---|---|---|---|
| `assessment.attempts` | `created_at` | RANGE | Monthly | Design from day one; activate when table reaches ~50M rows. |
| `assessment.question_instances` | `served_at` | RANGE | Monthly | Design from day one; activate with `attempts`. |
| `assessment.answers` | (co-located with `attempts` via `attempt_id`) | — | Monthly | Co-located partitioning; see below. |
| `infrastructure.outbox_events` | `created_at` | RANGE | Monthly | Design from day one; activate when table reaches ~50M rows. |
| `administration.audit_logs` | `created_at` | RANGE | Monthly | Design from day one; activate when table reaches ~50M rows. |
| `learning.learning_sessions` | `started_at` | RANGE | Monthly | Activate when table reaches ~50M rows. |
| `learning.recommendation_history` | `created_at` | RANGE | Monthly | Activate when table reaches ~50M rows. |
| `analytics.learner_daily_snapshots` | `snapshot_date` | RANGE | Monthly | Design from day one; activate when table reaches ~100M rows. |
| `administration.notifications` | `created_at` | RANGE | Monthly | Activate when table reaches ~50M rows. |
| `infrastructure.background_jobs` | `created_at` | RANGE | Monthly | Activate when table reaches ~50M rows. |

---

## Tables NOT Requiring Partitioning (at launch)

| Table | Why not | Future |
|---|---|---|
| `identity.users`, `user_profiles`, `user_credentials` | Small (~1M rows); low growth. | Consider hash partitioning by `id` at >100M users. |
| `identity.sessions` | Medium (~3M rows); high churn but short retention. | Consider partitioning by `expires_at` if retention extends. |
| `content.*` (all content tables) | Small (~5M rows total); low growth. | Never partitioned (content is small and stable). |
| `learning.learner_enrollments` | Medium (~2M rows); low growth per user. | Consider hash partitioning by `user_id` at >100M enrollments. |
| `learning.study_sessions` | Large (~500M rows) but queried by `learner_enrollment_id`, not time. | Consider hash partitioning by `learner_enrollment_id` at >5B rows. |
| `learning.recommendations`, `achievements`, `streaks` | Medium; queried by enrollment. | Consider hash partitioning at >5B rows. |
| `mastery.mastery_scores` | Very large (~2B rows) but queried by `learner_enrollment_id`. | **Hash partitioning by `learner_enrollment_id` at >5B rows** — see below. |
| `mastery.reviews` | Large (~2B rows); queried by `learner_enrollment_id`. | Consider hash partitioning at >5B rows. |
| `mastery.learner_misconceptions` | Large (~500M rows); queried by enrollment. | Consider hash partitioning at >5B rows. |
| `scheduling.daily_queues` | Small (~2M rows); high churn. | Never partitioned (purged daily). |
| `analytics.concept_statistics`, `template_statistics` | Small (~50M rows); nightly batch. | Consider partitioning by `snapshot_date` at >1B rows. |
| `billing.*` | Small (~6M rows). | Never partitioned. |
| `administration.feature_flags`, `system_settings`, `gdpr_requests`, `organizations` | Small. | Never partitioned. |
| `infrastructure.migration_history` | Tiny (~1000 rows). | Never partitioned. |

---

## Partitioning Design Details

### `assessment.attempts` — RANGE partitioning by `created_at`, monthly

**Why monthly**: daily partitions produce too many partitions (365/year); yearly partitions are too coarse for pruning (a query for last month's data scans a full year). Monthly is the sweet spot.

**Partition naming**: `attempts_YYYY_MM` (e.g., `attempts_2026_07`).

**Partition creation**: a scheduled job creates the next month's partition 7 days in advance, ensuring no insert fails due to a missing partition.

```sql
-- Example: create the July 2026 partition
CREATE TABLE assessment.attempts_2026_07
    PARTITION OF assessment.attempts
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
```

**Default partition**: a default partition catches out-of-range dates (should be empty; alerts if not).

```sql
CREATE TABLE assessment.attempts_default
    PARTITION OF assessment.attempts DEFAULT;
```

**Partition pruning**: queries with `WHERE created_at >= '2026-07-01' AND created_at < '2026-08-01'` prune to a single partition.

**Archival**: partitions older than the retention period (see `09-data-retention.md`) are detached and moved to cold storage:

```sql
ALTER TABLE assessment.attempts DETACH PARTITION assessment.attempts_2024_01;
-- Then move the detached table to cold storage (tablespace or external storage).
```

**Trade-offs**:
- **Pro**: partition pruning makes time-range queries fast.
- **Pro**: archival is a metadata operation (detach), not a delete.
- **Con**: cross-partition queries (e.g., "all attempts by this learner") scan all partitions for the learner's active period. Mitigated by the index `(learner_enrollment_id, created_at DESC)` on each partition.
- **Con**: unique constraints must include the partition key. The PK `id` alone cannot be unique across partitions; we use a global unique index (PG 16+ supports this) or accept that `id` uniqueness is enforced per-partition (acceptable because UUIDs are globally unique).

---

### `assessment.question_instances` — RANGE partitioning by `served_at`, monthly

Co-located with `attempts` on the same monthly cadence. A query joining `attempts` and `question_instances` on the same month prunes both to the same partition.

---

### `assessment.answers` — co-located partitioning

`answers` is 1:1 with `attempts` and is queried together with `attempts`. Two options:

**Option A (recommended)**: partition `answers` by `submitted_at` (monthly), co-located with `attempts` partitions. Joins on `(attempt_id)` within the same month are co-located.

**Option B**: store `answers` in the same partition as `attempts` by making `answers` a child table of `attempts` (not standard PostgreSQL; requires application-level handling). Rejected for complexity.

We choose Option A. The `attempt_id` foreign key cannot be enforced across partitions in PostgreSQL < 16, but PG 16+ supports cross-partition foreign keys. For earlier versions, the application enforces the relationship.

---

### `infrastructure.outbox_events` — RANGE partitioning by `created_at`, monthly

Same pattern as `attempts`. The dispatcher queries `WHERE status = 'pending' AND created_at < now()` which prunes to recent partitions.

---

### `administration.audit_logs` — RANGE partitioning by `created_at`, monthly

Same pattern. Audit logs are retained for 7 years (per `09-data-retention.md`); old partitions are detached and moved to cold storage annually.

---

### `learning.learning_sessions` — RANGE partitioning by `started_at`, monthly

Same pattern. Engagement analytics queries prune to the relevant months.

---

### `learning.recommendation_history` — RANGE partitioning by `created_at`, monthly

Same pattern. Retention is 1 year (per `09-data-retention.md`); old partitions are detached and archived.

---

### `analytics.learner_daily_snapshots` — RANGE partitioning by `snapshot_date`, monthly

Same pattern. Retention analytics queries prune to the relevant months. This is the largest table by row count (~50B at maturity); partitioning is mandatory.

---

### `administration.notifications` — RANGE partitioning by `created_at`, monthly

Same pattern. Retention is 30 days (per `09-data-retention.md`); old partitions are detached and dropped (no archival needed for short retention).

---

### `infrastructure.background_jobs` — RANGE partitioning by `created_at`, monthly

Same pattern. Completed/failed jobs are purged after 30 days; dead-lettered jobs are retained for 90 days.

---

## Hash Partitioning for `mastery.mastery_scores` (future)

`mastery_scores` is queried by `learner_enrollment_id`, not by time. At >5B rows, a single table becomes a write bottleneck (index maintenance) and a read bottleneck (the index `(learner_enrollment_id, concept_id)` becomes deep).

**Hash partitioning by `learner_enrollment_id`** (e.g., 16 or 64 partitions) distributes writes and reads across partitions. A query `WHERE learner_enrollment_id = $1` prunes to a single partition.

**Trade-offs**:
- **Pro**: write parallelism across partitions.
- **Pro**: read pruning by `learner_enrollment_id`.
- **Con**: cross-learner queries (e.g., "average mastery for this concept across all learners") scan all partitions. Mitigated by `analytics.concept_statistics` (precomputed aggregates).
- **Con**: partition count is fixed at creation; changing it requires a rewrite. Choose 16 or 64 partitions to allow 16x or 64x scaling.

**Trigger**: when `mastery_scores` exceeds 5B rows (estimated at ~5M learners × 1000 concepts × 1 subject, or ~2.5M learners × 2 subjects).

**Migration**: a multi-day backfill via `INSERT INTO ... SELECT ...` from the old table to the new partitioned table, with a cutover via renaming. Documented in a future ADR.

---

## Partitioning Trade-offs Summary

| Trade-off | Resolution |
|---|---|
| Unique constraints must include partition key | Use UUIDs (globally unique without DB enforcement) or accept per-partition uniqueness. |
| Cross-partition queries are slower | Mitigated by per-partition indexes and partition pruning. |
| Partition creation must be automated | Scheduled job creates next month's partition 7 days in advance. |
| Archival requires detach + move | Operational procedure documented; automated for short-retention tables. |
| Foreign keys across partitions | PG 16+ supports cross-partition FKs; for earlier versions, application enforces. |
| Hash partition count is fixed | Choose 16 or 64 partitions; document the rewrite path if more are needed. |

---

## Partition Management Automation

A scheduled job (background worker) runs daily to:

1. **Create next month's partition** for all partitioned tables (7 days in advance).
2. **Alert if the default partition is non-empty** (indicates a missing future partition).
3. **Detach and archive old partitions** per the retention schedule (see `09-data-retention.md`).
4. **Run `ANALYZE` on newly created partitions** to update statistics.

The job is idempotent: creating an existing partition is a no-op; detaching a non-existent partition is skipped.

---

*End of Partitioning Strategy.*
