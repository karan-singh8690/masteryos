# ADR-0002 — Choose PostgreSQL as the Primary Database

---

## Title

Use PostgreSQL as the primary relational database for all bounded contexts in the Mastery Engine.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine's data is its long-term competitive moat. The system accumulates an append-only Attempt corpus that grows to billions of rows over the decade, a normalized content graph (Concepts, Dependencies, Objectives, Misconceptions, Templates) that evolves through versioned snapshots, and per-Learner mastery state that must be reproducible from the Attempt history. The database choice is among the most irreversible decisions in the project: migrating away from a primary database after years of accumulated data is a multi-quarter, high-risk effort that few teams survive without downtime or data loss.

The architecture specification (Task 001, Section 1.4) commits to a "normalized-first" data philosophy: data is stored in third-normal form, with denormalization introduced only when query latency or write throughput demands it. This philosophy favors a relational database with strong transactional guarantees, mature query planning, and a rich ecosystem for analytics. The Mastery Engine's bounded contexts (ASD Section 3.1) each own their data with single-writer enforcement (ASD Section 3.3), which requires a database that supports row-level consistency and transactional integrity across multiple writes.

The learning loop (ASD Section 5) is the latency-critical path: an Attempt write, a Mastery update, and a Queue regeneration must complete within 200ms at the median. The database must support this latency under load, with proper indexing and connection pooling. The Attempts table is the highest-volume table and will require partitioning at scale (ASD Section 13.3); the database must support declarative partitioning with partition pruning for analytics queries.

The project also requires JSONB for semi-structured content (Explanation variants, parameter schemas), full-text search for the content catalog (initially, before a dedicated search engine is adopted per ASD Section 13.6), and point-in-time recovery for disaster recovery (ASD Section 17.5). All of these are table stakes for the database choice.

---

## Problem Statement

What database should serve as the primary, transactional, source-of-truth store for all bounded contexts in the Mastery Engine, given the requirements for transactional integrity, normalized data, append-only history, partitioning at scale, and a 200ms learning-loop latency target?

---

## Decision

We will use **PostgreSQL** (currently version 16+, with annual major-version upgrades) as the primary database for all bounded contexts. Each context owns its tables; cross-context data access is via service interfaces, not via shared tables. PostgreSQL is the only OLTP database in the system; analytics at scale will use a derived columnar store (ASD Section 13.7), fed by change-data-capture from PostgreSQL.

We will use PostgreSQL's native features aggressively: JSONB for semi-structured content, declarative partitioning for the Attempts table (triggered at ~100M rows), full-text search for the initial content catalog, row-level security where appropriate for multi-tenant isolation, and logical replication for the read replica and the analytics CDC pipeline.

---

## Alternatives Considered

### Alternative A: MySQL

- **Description:** MySQL (or its fork, MariaDB) as the primary database.
- **Arguments in favor:**
  - Mature, widely deployed, well-understood by hires.
  - Historically perceived as faster for read-heavy workloads (though PostgreSQL has closed this gap).
  - Simpler operational model in some deployments.
- **Arguments against:**
  - Weaker JSON support than PostgreSQL's JSONB (MySQL's JSON is text-stored; JSONB is binary with indexing).
  - Weaker full-text search (PostgreSQL's tsvector is more flexible).
  - Historically weaker transactional semantics in some storage engines (InnoDB is solid, but the ecosystem has fragmentation).
  - Declarative partitioning is less mature than PostgreSQL's.
  - The data moat thesis favors the richer query and analytics ecosystem of PostgreSQL.
- **Why rejected:** The JSONB and partitioning advantages are decisive for the Mastery Engine's content graph and the Attempts table's scale. The gap in analytics-friendly features (window functions, CTEs, materialized views) is significant for a system whose data is the moat. MySQL is a fine choice for many applications; it is not the best choice for this one.

### Alternative B: SQLite

- **Description:** SQLite as the primary database (file-based, embedded).
- **Arguments in favor:**
  - Zero operational overhead; no server to run.
  - Fast for single-process, low-concurrency workloads.
  - Excellent for local development and testing.
- **Arguments against:**
  - Single-writer concurrency model; the Mastery Engine has concurrent writes from many Learners.
  - No built-in replication; read replicas require external tooling.
  - No partitioning; the Attempts table would hit scaling ceilings quickly.
  - Not designed for the scale the Mastery Engine targets (millions of learners).
  - No network access; the database must run on the same host as the application, preventing horizontal scaling.
- **Why rejected:** SQLite is fundamentally unsuited to a multi-user SaaS workload at the Mastery Engine's target scale. It is, however, an excellent choice for local development and for the test suite (in-memory SQLite for unit tests, where its simplicity is an advantage). We adopt SQLite for testing only; production uses PostgreSQL.

### Alternative C: MongoDB

- **Description:** MongoDB (a document-oriented NoSQL database) as the primary database.
- **Arguments in favor:**
  - Schema flexibility; content artifacts (Concepts, Templates) have variable shapes.
  - Horizontal scaling via sharding is built-in.
  - JSON-native; maps well to API responses.
- **Arguments against:**
  - Sacrifices relational integrity for the only data layer that needs it most. The Concept Dependency graph, the Attempt-to-QuestionTemplate-to-Concept traceability, and the Mastery Score-to-Attempt provenance are all relational; MongoDB would require application-level joins or denormalization that risks inconsistency.
  - Transactions were added late and are less mature than PostgreSQL's; the learning loop's transactional integrity (Attempt + outbox event in one transaction) is harder to guarantee.
  - Analytics on normalized data require aggregation pipelines that are less expressive than SQL.
  - The data moat thesis depends on the Attempt corpus being analyzable in arbitrary ways; a relational schema supports this; a document schema constrains it.
  - The Mastery Engine's data is not naturally document-shaped; it is relational (Concepts relate to Objectives relate to Templates relate to Attempts relate to MasteryScores).
- **Why rejected:** The relational integrity requirements are decisive. The Mastery Engine's data is relational at its core; using a document database would require constant application-level enforcement of integrity that the database should provide. The flexibility MongoDB offers is not needed (the schema is well-defined) and the integrity it sacrifices is essential.

### Alternative D: A polyglot persistence approach (different databases per context)

- **Description:** Each bounded context chooses its own database (e.g., PostgreSQL for Identity, MongoDB for Content, Redis for Scheduling, a time-series DB for Analytics).
- **Arguments in favor:**
  - Maximum per-context optimization.
  - Each context uses the best tool for its data shape.
- **Arguments against:**
  - Operational complexity explodes (multiple databases to operate, back up, monitor, upgrade).
  - Cross-context consistency (e.g., Attempt in Assessment + Mastery update in Mastery) cannot use a single transaction; distributed transactions or sagas are required.
  - The team cannot afford the operational burden at the current size.
  - The benefits are marginal: PostgreSQL handles all the data shapes adequately, even if not optimally.
- **Why rejected:** The operational cost is disproportionate to the benefit at the project's current and mid-term scale. Polyglot persistence is a pattern for organizations with dedicated platform teams; the Mastery Engine will use PostgreSQL for everything and revisit per-context specialization only when a context's data shape genuinely demands it (Future Review Trigger).

---

## Pros

- **Transactional integrity**: ACID transactions guarantee the learning loop's consistency (Attempt + outbox event in one transaction).
- **Relational integrity**: foreign keys, constraints, and triggers enforce the data moat's correctness at the database level.
- **JSONB for semi-structured content**: Explanation variants, parameter schemas, and audit metadata use JSONB without sacrificing queryability.
- **Declarative partitioning**: the Attempts table can be partitioned by time without application changes, enabling scale to billions of rows.
- **Full-text search**: tsvector and tsquery provide adequate content search for the initial catalog, deferring the need for a dedicated search engine.
- **Mature analytics ecosystem**: SQL window functions, CTEs, materialized views, and rich index types (B-tree, GIN, GiST) support analytics queries that a NoSQL database cannot express.
- **Read replicas and logical replication**: analytics traffic routes to a replica; the CDC pipeline feeds the derived analytics store.
- **Point-in-time recovery**: WAL archiving enables the 15-minute RPO required by the disaster recovery plan (ASD Section 17.5).
- **Broad hire pool**: PostgreSQL is widely known; onboarding is fast.
- **Strong open-source governance**: not controlled by a single cloud provider; portable across AWS, GCP, Azure, and self-hosted.

---

## Cons

- **Single write-primary**: PostgreSQL does not natively support multi-master replication; writes go to one primary, which is a scaling ceiling and a failure domain. (Mitigated by read replicas for reads and by failover tooling for the primary.)
- **Vertical scaling bias**: scaling up means a bigger instance, which is more expensive than horizontal scaling; the Attempts table's write throughput will eventually require partitioning and possibly sharding.
- **Operational burden**: PostgreSQL requires vacuum tuning, connection pooling (PgBouncer), and version upgrades; this is real work, not zero-maintenance.
- **No built-in change-data-capture**: the CDC pipeline for analytics requires external tooling (Debezium, pglogical, or a custom logical replication consumer).
- **Connection count limits**: PostgreSQL's per-connection process model requires connection pooling to scale; this is an operational discipline, not a default.

---

## Consequences

- The team must maintain PostgreSQL operational expertise (vacuum, replication, upgrades, backup/restore).
- PgBouncer (or equivalent) is mandatory from day one to pool connections between the API and the database.
- The Attempts table is designed for partitioning from the start (partition key, indexes) so that the partitioning trigger at ~100M rows is a metadata change, not a schema redesign.
- A read replica is provisioned when analytics load begins to affect the primary (Phase 3, per ASD Section 16.3).
- A CDC pipeline (Debezium or equivalent) is built in Phase 4 to feed the derived analytics store.
- Backup and restore procedures are documented and drilled quarterly (ASD Section 17.5, 17.10).
- Major PostgreSQL version upgrades are planned annually, tested against a full-size staging copy, and executed with a documented rollback plan.

---

## Risks

- **Write throughput ceiling**: the single primary may not sustain the Attempts table's write rate at millions of learners. *Mitigation:* partitioning reduces write pressure on hot indexes; if partitioning is insufficient, the Attempts table is the first candidate for sharding (a future ADR).
- **Vacuum bloat**: high-write tables (Attempts) can suffer vacuum bloat if autovacuum is not tuned. *Mitigation:* aggressive autovacuum settings on the Attempts table; monitoring of bloat; periodic manual vacuums during low-traffic windows.
- **Replication lag**: the read replica may lag behind the primary, causing stale reads on analytics endpoints. *Mitigation:* consistency-mode declaration per endpoint (ASD Section 17.9); fallback to primary when lag exceeds threshold.
- **Upgrade risk**: major version upgrades can break queries or extensions. *Mitigation:* upgrades tested against a full-size staging copy; extensions pinned to compatible versions; rollback plan documented.
- **Vendor lock-in for managed PostgreSQL**: using a managed service (RDS, Cloud SQL) introduces some lock-in. *Mitigation:* avoid proprietary extensions; keep the schema portable; the migration path between managed providers is well-trodden.

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Write throughput ceiling**: the Attempts table's write rate exceeds 50% of the primary's sustainable throughput (measured by replication lag under load and by commit latency), indicating that partitioning alone is insufficient and sharding must be considered.
2. **Specialized data shape**: a bounded context's data shape genuinely diverges from relational (e.g., a future feature requiring a time-series database, a graph database for advanced KnowledgeGraph analytics, or a vector database for ML embeddings), justifying polyglot persistence for that context.
3. **Cost ceiling**: PostgreSQL's vertical scaling cost exceeds the cost of operating a horizontally-scaled alternative (e.g., a sharded NewSQL database like CockroachDB or TiDB) by more than 2x at the same performance.
4. **Multi-region write demand**: a regulatory or latency requirement forces multi-region writes, which PostgreSQL's single-primary model cannot satisfy without multi-master replication (which PostgreSQL does not natively support).

**Expected review action:** When any trigger fires, the architecture review group evaluates the alternatives (sharding, polyglot persistence for the triggering context, migration to a distributed SQL database, or multi-region architecture). The evaluation produces a new ADR proposing the change, with a migration plan that preserves the Attempt corpus's integrity (the moat).

---

## Related ADRs

- **Depends on:** ADR-0001 (Modular Monolith) — the monolith's transactional integrity relies on a single database.
- **Depends on:** ADR-0005 (Clean Architecture) — repositories abstract PostgreSQL, allowing the schema to evolve without affecting the domain.
- **Informs:** ADR-0011 (Triple Versioning) — the versioning model is implemented via PostgreSQL tables and foreign keys.
- **Informs:** ADR-0012 (Outbox Pattern) — the outbox is a PostgreSQL table, written in the same transaction as the originating write.

---

## Related Architecture Sections

- ASD Section 1.4 — Technical Philosophy (normalized-first).
- ASD Section 4 — Core Domain Model (entities that PostgreSQL persists).
- ASD Section 13.3 — Database Optimization (indexing, partitioning, read replicas, connection pooling).
- ASD Section 13.7 — Analytics at Scale (derived analytics store fed by CDC).
- ASD Section 17.5 — Disaster Recovery Plan (RPO via WAL archiving).

---

## Related Glossary Terms

- Aggregate
- Repository
- Write Model
- Read Model
- Content Version
- Attempt History

---

*End of ADR-0002.*
