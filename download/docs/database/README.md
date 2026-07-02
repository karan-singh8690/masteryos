# Mastery Engine — PostgreSQL Database & Data Architecture

> **Status:** v1.0 — Authoritative source for the Mastery Engine database design.
> **Owner:** Staff Database Architect
> **Audience:** Backend engineers, data engineers, DBAs, analytics engineers.
> **Companion documents:**
> - Architecture Specification Document (Task 001) — `/mastery-engine-architecture-spec.md`
> - Ubiquitous Language & Domain Glossary (Task 002) — `/docs/domain/ubiquitous-language.md`
> - Architecture Decision Records (Task 003) — `/docs/adr/`

---

## What This Document Set Is

This is the complete data architecture for the Mastery Engine's PostgreSQL database. It is not a list of tables; it is the design rationale, the constraints, the trade-offs, and the evolution path for the system's most valuable long-term asset: the historical learning data that constitutes the company's competitive moat.

The database is designed to support millions of learners over the next decade. Every decision in these documents is evaluated against six criteria, in priority order:

1. **Correctness** — the schema enforces business invariants at the database level wherever feasible.
2. **Auditability** — every irreversible decision (content publish, mastery computation, privileged action) is traceable to a specific version, actor, and timestamp.
3. **Scalability** — the schema scales to billions of Attempts without redesign, via partitioning, indexing, and read replicas.
4. **Maintainability** — the schema is normalized (3NF/BCNF) with intentional, documented denormalizations.
5. **Historical reproducibility** — any historical Attempt can be replayed and any historical Mastery Score can be reconstructed, via triple versioning (ADR-0011).
6. **Analytical capability** — the schema supports both operational queries (the learning loop) and analytical queries (cohort retention, concept difficulty) without compromising either.

---

## Document Index

| File | Topic |
|---|---|
| `01-domain-model.md` | Every entity: purpose, owner, relationships, lifecycle, business rules, expected size, growth rate, access patterns. |
| `02-erd.md` | Complete Entity Relationship Diagram in Mermaid syntax. |
| `03-logical-schema.md` | For every entity: columns, PK, unique constraints, FKs, check constraints, nullability, defaults, business justification. |
| `04-physical-schema.md` | PostgreSQL implementation details: UUID strategy, timestamps, JSONB, ENUMs, composite keys, generated columns, sequences, extensions, schema separation, naming conventions. |
| `05-normalization.md` | Normalization analysis (1NF, 2NF, 3NF, BCNF) per table, with intentional denormalizations documented. |
| `06-indexing-strategy.md` | Per-table indexing: primary, secondary, composite, partial, GIN, BRIN, with justifications. |
| `07-partitioning-strategy.md` | Which tables require partitioning, partition keys, trade-offs. |
| `08-versioning-strategy.md` | Triple versioning (Content, Template, Algorithm) for historical reproducibility. |
| `09-data-retention.md` | Retention policy per data category, soft delete vs hard delete, GDPR compliance. |
| `10-migrations.md` | Migration philosophy: backward compatibility, rollback, feature flags, zero downtime, version numbering. |
| `11-seed-data.md` | Seed strategy: system roles, Python Subject, concept categories, difficulty levels, mastery levels, question types, default settings. |
| `12-performance.md` | Performance estimates at 100 / 10K / 100K / 1M users; table sizes; query hotspots; caching opportunities; read/write ratios. |
| `13-security.md` | Database security: least privilege, roles, encryption, secrets, PII isolation, audit, Row-Level Security, SQL injection protection. |
| `14-backup-recovery.md` | Backup frequency, point-in-time recovery, disaster recovery, replication, recovery testing, RTO/RPO. |
| `15-future-evolution.md` | How the schema evolves for ML, vector search, recommendation models, knowledge graph, enterprise customers, multiple subjects, i18n, offline learning, mobile sync, marketplace. |

---

## Conflict Reconciliations with the Brief

The brief's entity list was reconciled against the authoritative documents (Tasks 001–003) before design began. The reconciliations are documented here so future engineers understand the deviations.

### 1. "Questions" → `question_instances`

The brief lists "Questions" as an entity. Task 002 defines **Question Instance** as the concrete question (instantiated from a Question Template + seed) and explicitly distinguishes it from **Question Template**. The table is named `question_instances` per the glossary's Naming Standards.

### 2. "Tenants" vs "Subjects" vs "Organizations"

Task 002 distinguishes three concepts:
- **Subject** — the curriculum unit (Python, SQL, Java, etc.).
- **Tenant** — the content-isolation unit. In the current architecture, Tenant and Subject are 1:1; the term is reserved for future multi-Subject Tenants.
- **Organization** — the billing unit (future Phase 5+ per ASD Section 16.5).

All three are modeled. `tenants` and `subjects` are 1:1 today (with a `tenant_id` foreign key on `subjects`); `organizations` is modeled as a future-facing table with minimal columns, ready for Phase 5.

### 3. "Queues" → `practice_queues` (session-scoped only)

Task 002 defines AdaptiveQueue and DailyQueue as **runtime artifacts, not persisted long-term**. They are cached in Redis and regenerated on demand. A lightweight `practice_queues` table stores session-scoped queue snapshots for mid-session reload recovery, but it is not a long-term analytical store. Queue analytics are derived from `attempts` and `study_sessions`.

### 4. "Memory Scores" and "Mastery Scores" → single `mastery_scores` table

Task 002 and ADR-0008 define Memory Score as a **sub-component of** MasteryScore (a Value Object), not a separate top-level entity. They are modeled as columns within a single `mastery_scores` table (`memory_score`, `durable_mastery_score`, `mastery_score_combined`), per ADR-0008's "combined, not averaged" decision.

### 5. "Reviews" → `reviews` (scheduled review records)

Task 002 defines Review in three senses. The brief's "Reviews" maps to sense (b) — the scheduled review records produced by the Mastery Engine. The table `reviews` stores these. Sense (a) (Review Attempts) is a type of `attempts` (distinguished by `attempt_intent = 'review'`). Sense (c) (the ReviewWorkflow) is content authoring, modeled via `content_review_requests` and `content_approvals`.

### 6. Additional Entities Required by Authoritative Documents

The following entities are added beyond the brief's list because Tasks 001–003 require them:
- `user_credentials` — Task 002 Identity context; stores hashed passwords and OAuth links.
- `sessions` — Task 002; tracks authenticated sessions for revocation.
- `outbox_events` — ADR-0012; the outbox pattern for reliable domain event dispatch.
- `content_packs` — Task 002; the atomic publishing unit.
- `distractors` — Task 002; tagged incorrect answer choices (per Question Instance or Template Version).
- `learning_path_items` — join table for Learning Path → Concept ordering.
- `study_plans` — Task 002; the calendar-level projection of a Learning Path against a Learning Goal.
- `streaks` — Task 002; decorative engagement metric (never a mastery signal).
- `content_review_requests` and `content_approvals` — Task 002; the Review Workflow for content publishing.
- `concept_difficulty_estimates` and `template_difficulty_estimates` — authored priors refined from data.
- `feature_flag_assignments` — per-user feature flag overrides.

---

## Design Principles

The database design follows these principles, derived from Tasks 001–003:

1. **Normalized-first** (ASD Section 1.4, ADR-0002) — 3NF/BCNF by default; denormalization only when measured query latency demands it, and only with an ADR.
2. **Single-writer per aggregate** (ASD Section 3.3, ADR-0006) — each table is written by exactly one bounded context; cross-context writes are forbidden.
3. **Append-only for evidence** (ASD Section 5.3, ADR-0011) — `attempts`, `audit_logs`, `outbox_events` are append-only; corrections are made by appending compensating records, not by editing.
4. **Triple versioning** (ADR-0011) — every Attempt references `content_version_id`, `template_version_id`, `algorithm_version_id`.
5. **Soft delete for recoverability, hard delete for GDPR** (ASD Section 12.8) — most entities use soft delete (`deleted_at`); PII is hard-deleted on GDPR erasure request, with anonymized aggregates retained.
6. **UUIDs for public identifiers** (this design) — all primary keys are UUID v7 (time-ordered, sortable, globally unique), avoiding integer-sequence contention and enabling future sharding.
7. **Timestamps with timezone** (this design) — all timestamp columns are `timestamptz`; the application converts to the user's timezone for display.
8. **JSONB for semi-structured content** (ADR-0002) — Explanation variants, parameter schemas, and audit metadata use JSONB, with GIN indexes where queried.
9. **PostgreSQL-native features** (ADR-0002) — declarative partitioning, full-text search (tsvector), row-level security, logical replication, generated columns.
10. **Schema separation by bounded context** (this design) — each bounded context owns a PostgreSQL schema (`identity`, `learning`, `assessment`, `mastery`, `content`, `scheduling`, `analytics`, `billing`, `administration`); cross-schema queries are permitted but cross-schema writes follow the single-writer rule.

---

## Conformance to Authoritative Documents

| Source | Conformance |
|---|---|
| ASD Section 1.4 (normalized-first) | All tables are 3NF/BCNF; denormalizations are documented in `05-normalization.md`. |
| ASD Section 3.1 (bounded contexts) | PostgreSQL schemas map 1:1 to bounded contexts. |
| ASD Section 3.3 (single-writer) | Each table is owned by one schema; cross-schema writes are forbidden. |
| ASD Section 5.3 (Loop invariants) | `attempts` is append-only; `mastery_scores` is single-writer (mastery schema only). |
| ASD Section 7.9 (triple versioning) | `content_versions`, `template_versions`, `algorithm_versions` tables; every `attempts` row references all three. |
| ASD Section 12.1 (JWT auth) | `user_credentials`, `sessions` tables; refresh token hashing. |
| ASD Section 12.4 (audit logging) | `audit_logs` table, append-only, partitioned by time. |
| ASD Section 12.8 (GDPR) | PII columns flagged; `gdpr_requests` table; anonymization procedures in `09-data-retention.md`. |
| ASD Section 13.3 (partitioning) | `attempts`, `audit_logs`, `outbox_events`, `learning_sessions`, `recommendation_history` partitioned by time. |
| ADR-0002 (PostgreSQL) | All tables in PostgreSQL; no polyglot persistence at launch. |
| ADR-0008 (Memory vs Mastery) | `mastery_scores` table has `memory_score`, `durable_mastery_score`, `mastery_score_combined` columns. |
| ADR-0011 (Triple Versioning) | Three version tables; every Attempt references all three. |
| ADR-0012 (Outbox Pattern) | `outbox_events` table, written in the same transaction as the originating write. |
| Task 002 (Naming Standards) | Tables are `snake_case` plural; columns are `snake_case`; FKs are `<singular>_id`; timestamps end in `_at`. |

---

## How to Use This Document Set

- **Implementing the schema**: start with `04-physical-schema.md` (conventions), then `03-logical-schema.md` (per-table columns), then `06-indexing-strategy.md` (indexes), then `07-partitioning-strategy.md` (partitioning).
- **Understanding why a table exists**: see `01-domain-model.md` for purpose, owner, and business rules.
- **Understanding relationships**: see `02-erd.md` for the ERD.
- **Migrating the schema**: see `10-migrations.md` for the migration philosophy.
- **Evaluating a query plan**: see `06-indexing-strategy.md` and `12-performance.md`.
- **Planning for scale**: see `07-partitioning-strategy.md` and `12-performance.md`.
- **Planning for the future**: see `15-future-evolution.md`.

---

*End of Database Architecture README.*
