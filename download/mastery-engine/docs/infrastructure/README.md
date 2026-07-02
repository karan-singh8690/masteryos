# Infrastructure Layer — Mastery Engine

> **Status:** v1.0 — Infrastructure layer connecting the Application Layer to PostgreSQL and external systems.
> **Depends on:** Domain Layer (Task 008), Application Layer (Task 009)

---

## What This Is

The Infrastructure Layer implements the interfaces defined by the Domain and Application layers. It connects the pure domain model to PostgreSQL (via SQLAlchemy 2.x async), Redis, and external services.

**Key principle:** Infrastructure hides SQLAlchemy completely. The Application Layer never sees an ORM model; it only sees domain entities returned by repositories.

## Architecture

```
Application Layer
       ↓ (interfaces)
Infrastructure Layer
       ├── database/          SQLAlchemy engine, ORM models, repositories, mappers, UoW
       ├── events/outbox/      Transactional outbox dispatcher + serializer
       ├── cache/              Redis + local cache abstractions
       ├── clock/              Injectable clock (system + fixed for tests)
       ├── ids/                UUID v7 generation
       └── config/             Infrastructure configuration
```

## Document Index

| File | Topic |
|---|---|
| `README.md` | This file. |
| `repository-implementation.md` | How repositories implement domain interfaces with SQLAlchemy. |
| `mapping-strategy.md` | How mappers convert between domain entities and ORM models. |
| `unit-of-work.md` | How AsyncUnitOfWork manages transactions and event publishing. |
| `outbox-pattern.md` | How the transactional outbox ensures reliable event delivery. |
| `migration-guide.md` | How Alembic migrations are structured and applied. |
| `performance-notes.md` | Query optimization, connection pooling, and caching strategies. |

## Key Abstractions

### Database Engine (`database/engine.py`)
- Async SQLAlchemy 2.x with asyncpg.
- Connection pooling (pool_size + max_overflow configurable).
- Statement timeout (30s) and idle transaction timeout (60s).
- Slow query logging (>100ms).
- Connection recycling (1 hour).

### ORM Models (`database/orm/`)
- SQLAlchemy declarative models for every table in Task 004.
- UUID primary keys, timestamptz, JSONB, CHECK constraints.
- Append-only enforcement for attempts, audit_logs, outbox_events.
- Composite indexes matching Task 004's indexing strategy.

### Domain Mappers (`database/mappers/`)
- Bidirectional: domain entity ⇄ ORM model.
- The ONLY place where ORM and domain interact.
- No ORM leakage into the domain or application layers.

### Repository Implementations (`database/repositories/`)
- Implement the domain's abstract repository interfaces.
- Return domain entities (via mappers); never expose ORM models.
- Support optimistic concurrency (MasteryScore's version field).
- Support pagination, filtering, and eager loading.

### AsyncUnitOfWork (`database/unit_of_work/`)
- Manages a single AsyncSession as the transaction boundary.
- All repositories share the same session.
- `commit()` persists changes; `rollback()` discards them.
- Events are written to the outbox in the same transaction.

### Outbox Dispatcher (`events/outbox/`)
- Polls the outbox table for pending events.
- Delivers events to registered subscribers (in-process).
- At-least-once delivery; subscribers must be idempotent.
- Dead-letters events after max retries.

### Clock (`clock/`)
- `SystemClock` — production (uses `datetime.now(timezone.utc)`).
- `FixedClock` — testing (returns a fixed time; can advance).

### ID Generation (`ids/`)
- `UuidV7Generator` — production (time-ordered, sortable).
- `UuidV4Generator` — development (random).
- `DeterministicIdGenerator` — testing (sequential, predictable).

### Cache (`cache/`)
- `RedisCache` — production (Redis-backed).
- `LocalCache` — testing (in-memory).

## Purity Guarantee

The infrastructure layer:
- ✅ Implements domain and application interfaces
- ✅ Uses SQLAlchemy 2.x async
- ✅ Uses Redis for caching
- ❌ Does NOT contain business rules
- ❌ Does NOT contain FastAPI routes
- ❌ Does NOT expose ORM models to the application layer
