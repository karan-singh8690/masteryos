# 12 — Performance

> Performance estimates at 100 / 10K / 100K / 1M users; table sizes; query hotspots; caching opportunities; read/write ratios.

---

## Performance Principles

1. **The learning loop is the critical path** — the 200ms median latency target (ASD Section 5.2) governs all performance decisions.
2. **Measure before optimizing** — performance work is driven by profiling, not speculation.
3. **Cache before denormalizing** — Redis caching (ASD Section 13.2) is preferred over denormalization.
4. **Partition before sharding** — partitioning (ADR-0007, `07-partitioning-strategy.md`) is preferred over sharding.
5. **Read replicas before warehouse** — analytics queries route to a read replica before a separate warehouse is built.

---

## Scale Scenarios

### Scenario 1: 100 users (early beta)

| Metric | Estimate |
|---|---|
| Active learners | 100 |
| Attempts per day | 500 (5 per learner) |
| Total attempts | 50,000 (over 3 months) |
| Total mastery scores | 10,000 (100 learners × 100 concepts) |
| Database size | < 1 GB |
| Concurrent requests | < 10 |
| Query latency (p99) | < 50ms |

**Tables and sizes**:

| Table | Rows | Size |
|---|---|---|
| `users` | 100 | < 1 MB |
| `attempts` | 50,000 | ~5 MB |
| `mastery_scores` | 10,000 | ~1 MB |
| `outbox_events` | 500,000 | ~50 MB |
| Other | — | < 10 MB |

**Hot queries**:
- `SELECT * FROM mastery_scores WHERE learner_enrollment_id = $1` — < 5ms.
- `INSERT INTO attempts ...` — < 5ms.
- `SELECT * FROM reviews WHERE learner_enrollment_id = $1 AND due_at <= now()` — < 5ms.

**Infrastructure**: a single small PostgreSQL instance (e.g., 2 vCPU, 4 GB RAM) is sufficient. No read replica, no partitioning, no caching layer (in-process caching is enough).

---

### Scenario 2: 10,000 users (growth phase)

| Metric | Estimate |
|---|---|
| Active learners | 10,000 |
| Attempts per day | 50,000 (5 per learner) |
| Total attempts | 5 million (over 3 months) |
| Total mastery scores | 1 million (10K learners × 100 concepts) |
| Database size | ~10 GB |
| Concurrent requests | ~500 |
| Query latency (p99) | < 100ms |

**Tables and sizes**:

| Table | Rows | Size |
|---|---|---|
| `users` | 10,000 | < 10 MB |
| `attempts` | 5,000,000 | ~500 MB |
| `mastery_scores` | 1,000,000 | ~100 MB |
| `outbox_events` | 50,000,000 | ~5 GB |
| `learner_daily_snapshots` | 30,000,000 (1M × 30 days) | ~3 GB |
| Other | — | ~1 GB |

**Hot queries**:
- `SELECT * FROM mastery_scores WHERE learner_enrollment_id = $1` — < 10ms (indexed).
- `INSERT INTO attempts ...` — < 10ms.
- `SELECT * FROM attempts WHERE learner_enrollment_id = $1 ORDER BY created_at DESC LIMIT 20` — < 20ms (indexed).
- `SELECT * FROM reviews WHERE learner_enrollment_id = $1 AND due_at <= now()` — < 10ms (partial index).

**Infrastructure**:
- Single medium PostgreSQL instance (e.g., 8 vCPU, 32 GB RAM).
- PgBouncer for connection pooling.
- Redis for caching (mastery scores, queues, content).
- Partitioning on `attempts` and `outbox_events` becomes worthwhile at the upper end of this range (~50M rows).

**Caching opportunities**:
- `mastery_scores` per learner (Redis, 60s TTL).
- `content_versions` current version (Redis, 1h TTL).
- `scheduling_configs` per subject (Redis, 1h TTL).
- `daily_queues` per learner per day (Redis, 24h TTL).

---

### Scenario 3: 100,000 users (scale phase)

| Metric | Estimate |
|---|---|
| Active learners | 100,000 |
| Attempts per day | 500,000 (5 per learner) |
| Total attempts | 50 million (over 3 months) |
| Total mastery scores | 10 million (100K learners × 100 concepts) |
| Database size | ~100 GB |
| Concurrent requests | ~5,000 |
| Query latency (p99) | < 200ms |

**Tables and sizes**:

| Table | Rows | Size |
|---|---|---|
| `users` | 100,000 | ~100 MB |
| `attempts` | 50,000,000 | ~5 GB |
| `mastery_scores` | 10,000,000 | ~1 GB |
| `outbox_events` | 500,000,000 | ~50 GB |
| `learner_daily_snapshots` | 300,000,000 | ~30 GB |
| `audit_logs` | 50,000,000 | ~5 GB |
| Other | — | ~10 GB |

**Hot queries** (latency targets):
- Mastery score lookup: < 20ms (indexed; consider Redis cache).
- Attempt insert: < 20ms.
- Learner history (last 20 attempts): < 50ms (indexed, partitioned).
- Due reviews: < 20ms (partial index).
- Queue generation: < 100ms (multiple queries; cached results).

**Infrastructure**:
- Large PostgreSQL primary (e.g., 32 vCPU, 128 GB RAM, NVMe storage).
- **Read replica** for analytics queries (per ASD Section 13.3).
- Redis cluster for caching.
- **Partitioning active** on `attempts`, `outbox_events`, `audit_logs`, `learner_daily_snapshots`, `notifications` (per `07-partitioning-strategy.md`).
- Background workers on separate instances.

**Caching opportunities** (expanded):
- All Scenario 2 caches.
- `attempts` recent history per learner (Redis, 5min TTL).
- `concept_statistics` and `template_statistics` (Redis, 1h TTL; computed nightly).
- `learner_enrollments` per user (Redis, 5min TTL).

**Query hotspots**:
- The mastery recompute query (`SELECT * FROM attempts WHERE learner_enrollment_id = $1 AND concept_id = $2`) becomes a hotspot. **Mitigation**: denormalize `concept_id` onto `attempts` (with a GIN index on `concept_ids` array) to avoid the join through `template_versions` and `template_concepts`. This is a documented future optimization (see `06-indexing-strategy.md`).
- The Scheduler's queue generation query (multiple mastery scores + reviews + content) is the most complex. **Mitigation**: pre-compute the queue and cache in Redis; regenerate only on attempt completion.

**Read/write ratios**:
- `attempts`: 90% write, 10% read (append-heavy).
- `mastery_scores`: 50% read (scheduler), 50% write (mastery update).
- `reviews`: 90% read (scheduler), 10% write (recompute).
- `users`, `learner_enrollments`: 99% read, 1% write.
- `content.*`: 99.9% read, 0.1% write.
- `outbox_events`: 99% write, 1% read (dispatcher).

---

### Scenario 4: 1,000,000 users (maturity)

| Metric | Estimate |
|---|---|
| Active learners | 1,000,000 |
| Attempts per day | 5,000,000 (5 per learner) |
| Total attempts | 500 million (over 3 months); ~5 billion over a decade |
| Total mastery scores | 1 billion (1M learners × 1000 concepts) |
| Database size | ~1 TB |
| Concurrent requests | ~50,000 |
| Query latency (p99) | < 200ms (with caching and partitioning) |

**Tables and sizes**:

| Table | Rows | Size |
|---|---|---|
| `users` | 1,000,000 | ~1 GB |
| `attempts` | 500,000,000 (3 months); ~5B (decade) | ~50 GB (3 months); ~500 GB (decade, with archival) |
| `mastery_scores` | 1,000,000,000 | ~100 GB |
| `outbox_events` | 5,000,000,000 (3 months) | ~500 GB (with archival) |
| `learner_daily_snapshots` | 30,000,000,000 | ~3 TB (with archival) |
| `audit_logs` | 500,000,000 | ~50 GB |
| Other | — | ~50 GB |

**Hot queries** (latency targets):
- Mastery score lookup: < 20ms (Redis cache; DB fallback < 50ms).
- Attempt insert: < 20ms (partitioned; insert goes to the current month's partition).
- Learner history: < 100ms (partitioned; prunes to recent partitions).
- Due reviews: < 20ms (partial index; per-learner).
- Queue generation: < 100ms (cached; regenerated on attempt).
- Analytics queries (cohort retention, concept difficulty): < 2s (read replica; or analytics warehouse).

**Infrastructure**:
- **Multiple PostgreSQL primaries** via read replicas for reads; the primary handles writes.
- **Read replica** dedicated to analytics.
- **Redis cluster** for caching (multi-node for availability).
- **Partitioning active** on all high-volume tables.
- **Hash partitioning** on `mastery_scores` and `reviews` by `learner_enrollment_id` (16 or 64 partitions) — see `07-partitioning-strategy.md`.
- **Analytics warehouse** (BigQuery, Redshift, ClickHouse) fed by CDC for aggregate analytics.
- **Background workers** on a dedicated node pool.
- **Sandbox runtime** on a separate node pool (for code-execution questions).

**Caching opportunities** (mature):
- All Scenario 3 caches.
- Multi-level caching: in-process LRU → Redis → database.
- CDN for static assets and public API responses.
- Pre-computed daily aggregates for dashboard.

**Query hotspots**:
- The mastery recompute query is critical. **Denormalization**: `attempts.concept_ids` (array of concept IDs tested by this attempt's template) with a GIN index enables `WHERE learner_enrollment_id = $1 AND $2 = ANY(concept_ids)` without joins. This is mandatory at 1M users.
- The Scheduler's queue generation is cached aggressively; the cache is invalidated on attempt completion.
- Analytics queries on `attempts` (e.g., "success rate for this template over the last month") are routed to the read replica or the analytics warehouse.

**Read/write ratios** (similar to Scenario 3, but more pronounced):
- `attempts`: 95% write, 5% read (the write path dominates; reads go to the warehouse).
- `mastery_scores`: 70% read (scheduler), 30% write.
- `outbox_events`: 99% write, 1% read.

---

## Query Hotspots and Mitigations

### Hotspot 1: Learning loop submit-answer path

**Query**: insert attempt, update mastery score, regenerate queue.
**Latency budget**: 200ms median.
**Mitigations**:
- Attempt insert: partitioned; goes to current month's partition; < 20ms.
- Mastery update: single-row update by `(learner_enrollment_id, concept_id)`; < 20ms.
- Queue regeneration: cached; the cache key includes the learner's mastery state hash; cache hit on most requests.
- Outbox event insert: same transaction as attempt insert; no additional latency.

### Hotspot 2: Scheduler queue generation

**Query**: fetch mastery scores, due reviews, weak concepts, available templates; rank; instantiate.
**Latency budget**: 100ms median.
**Mitigations**:
- Mastery scores: Redis cache (60s TTL).
- Due reviews: partial index; < 20ms.
- Weak concepts: partial index; < 20ms.
- Available templates: Redis cache (1h TTL).
- Ranking: in-memory computation.
- Instantiation: in-memory Question Factory.
- Queue cached in Redis (session-scoped).

### Hotspot 3: Mastery recompute (on algorithm version change)

**Query**: for each learner, for each concept, recompute mastery from attempt history.
**Latency budget**: background job; no user-facing latency, but must complete within a maintenance window.
**Mitigations**:
- Batched by learner (10,000 learners per batch).
- Parallelized across background workers.
- Idempotent and resumable.
- Estimated duration at 1M learners: 7 days (with 10 parallel workers).
- The old mastery scores remain (referenced by historical attempts); new scores are written under the new algorithm version.

### Hotspot 4: Analytics queries (cohort retention, concept difficulty)

**Query**: aggregate over attempts and mastery scores.
**Latency budget**: < 2s for admin portal; < 30s for ad-hoc analytics.
**Mitigations**:
- Per-user analytics: from `learner_daily_snapshots` (precomputed nightly).
- Aggregate analytics: from `concept_statistics` and `template_statistics` (precomputed nightly).
- Ad-hoc analytics: routed to the read replica or the analytics warehouse.
- At 1M users, the analytics warehouse is mandatory for ad-hoc queries.

---

## Caching Layers

| Layer | Purpose | TTL | Invalidation |
|---|---|---|---|
| In-process LRU | Hot objects (current user, current subject) | Request-scoped | N/A (per-request) |
| Redis (object cache) | Mastery scores, queues, content | 60s–1h | On write (event-driven) |
| Redis (session cache) | Practice queues, daily queues | Session-scoped | On regeneration |
| CDN | Static assets, public API responses | 1h–24h | On deploy |
| Materialized views | Nightly aggregates | 24h | Nightly refresh |
| Analytics warehouse | Aggregate analytics | 24h | CDC pipeline |

---

## Connection Pooling

- **PgBouncer** in transaction mode.
- **Pool size**: 100–500 connections (tuned per environment).
- **Application connection count**: the async pool (asyncpg) connects to PgBouncer, not directly to PostgreSQL.
- **Read replica**: a separate PgBouncer pool for read-only connections (analytics, dashboards).

---

## Read/Write Splitting

At Scenario 3+ (100K users), read queries are routed to a read replica:
- **Write queries** (and read-after-write queries within a transaction): primary.
- **Read queries** (dashboard, progress, analytics): replica.
- **Consistency mode** (per ASD Section 17.9): each endpoint declares its consistency mode (strong, read-your-writes, eventually consistent).

**Replication lag monitoring**: alerts if lag exceeds 1 second; the application falls back to the primary for read-your-writes queries when lag is high.

---

## Performance Monitoring

- **`pg_stat_statements`**: tracks query counts and latency; reviewed weekly.
- **Slow query log**: queries > 100ms are logged; reviewed daily.
- **`pg_stat_user_tables`**: tracks table access patterns; identifies unused indexes.
- **`pg_stat_user_indexes`**: tracks index usage; identifies unused indexes.
- **Application-level metrics**: Prometheus metrics for query latency, cache hit rate, connection pool usage.
- **Load testing**: nightly load tests against staging (per ASD Section 14.4).

---

*End of Performance.*
