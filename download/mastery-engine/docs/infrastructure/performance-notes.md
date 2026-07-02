# Performance Notes

> Query optimization, connection pooling, and caching strategies.

---

## Connection Pooling

- **Engine**: asyncpg via SQLAlchemy 2.x async.
- **Pool**: `AsyncAdaptedQueuePool` with `pool_pre_ping=True` (health check before checkout).
- **Pool size**: configurable (`DATABASE_POOL_SIZE`, default 10).
- **Max overflow**: configurable (`DATABASE_MAX_OVERFLOW`, default 20).
- **Pool recycle**: 3600s (1 hour) — prevents stale connections.
- **PgBouncer** (production): sits between the application and PostgreSQL for connection multiplexing.

## Statement Timeouts

- **Statement timeout**: 30s (prevents runaway queries).
- **Idle in transaction timeout**: 60s (prevents connection leaks from unclosed transactions).
- Configured via `connect_args["server_settings"]` in the engine.

## Slow Query Logging

Queries slower than 100ms are logged as warnings:

```python
@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    duration = time.time() - context._query_start_time
    if duration > 0.1:
        logger.warning("slow_query", duration_ms=round(duration * 1000, 2), statement=statement[:200])
```

## Indexing Strategy

Indexes match Task 004's specification:
- **Primary indexes**: UUID primary keys (B-tree).
- **Secondary indexes**: on frequently queried columns (e.g., `learner_enrollment_id`, `concept_id`).
- **Composite indexes**: for multi-column queries (e.g., `(learner_enrollment_id, created_at)`).
- **Partial indexes**: for filtered queries (e.g., `WHERE deleted_at IS NULL`, `WHERE status = 'pending'`).
- **GIN indexes**: on JSONB columns that are queried (e.g., `outbox_events.payload`).
- **BRIN indexes**: on time-ordered partitioned tables (e.g., `attempts.created_at`).

## Query Optimization

### Eager Loading
```python
# Avoid N+1 queries: use selectinload for relationships
stmt = select(UserModel).options(selectinload(UserModel.profile))
```

### Pagination
```python
# Cursor-based pagination (not OFFSET)
stmt = (
    select(AttemptModel)
    .where(AttemptModel.learner_enrollment_id == enrollment_id)
    .where(AttemptModel.created_at < cursor_value)
    .order_by(AttemptModel.created_at.desc())
    .limit(page_size)
)
```

### Batch Loading
```python
# Use IN for batch lookups
stmt = select(ConceptModel).where(ConceptModel.id.in_(concept_ids))
```

## Caching Strategy

### Cache Layers

| Layer | TTL | Invalidation |
|---|---|---|
| In-process LRU | Request-scoped | N/A (per-request) |
| Redis (object cache) | 60s–1h | On write (event-driven) |
| Redis (session cache) | Session-scoped | On regeneration |
| CDN | 1h–24h | On deploy |

### Cache Keys

- Mastery scores: `mastery:{enrollment_id}:{concept_id}` (60s TTL)
- Adaptive queue: `queue:{session_id}` (session-scoped)
- Content: `content:{subject_id}:{content_version_id}` (1h TTL)
- Scheduling config: `config:{subject_id}` (1h TTL)

### Cache Invalidation

Cache is invalidated by event subscribers:
- `MasteryUpdated` → invalidate `mastery:{enrollment_id}:*`
- `ContentPublished` → invalidate `content:{subject_id}:*`
- `SchedulingConfigUpdated` → invalidate `config:{subject_id}`

## Partitioning

High-volume tables are partitioned by time (monthly):
- `attempts` (partitioned by `created_at`)
- `outbox_events` (partitioned by `created_at`)
- `audit_logs` (partitioned by `created_at`)
- `learner_daily_snapshots` (partitioned by `snapshot_date`)

Partition pruning ensures time-range queries only scan relevant partitions.

## Read Replicas

Analytics queries route to a read replica:
- Per-user analytics: from the replica (eventually consistent, <1s lag).
- Aggregate analytics: from a derived analytics warehouse (nightly refresh).
- Write queries: always to the primary.

Replication lag is monitored; the application falls back to the primary if lag exceeds 1 second.
