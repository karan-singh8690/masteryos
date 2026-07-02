# Domain Model — Mastery Engine

> **Status:** v1.0 — Authoritative source for the domain layer implementation.
> **Owner:** Domain Modeling Lead
> **Companion documents:** Tasks 001–007 (Architecture, Glossary, ADRs, Database, Behavior, API, Repo Foundation)

---

## What This Is

This directory documents the **domain model** of the Mastery Engine — the pure Python, framework-independent layer that contains all business logic. The domain model is the foundation of the system; every other layer (application, infrastructure, presentation) depends on it, and it depends on nothing.

## Document Index

| File | Topic |
|---|---|
| `README.md` | This file — overview and navigation. |
| `aggregate-map.md` | Every aggregate root, its boundary, its child entities, and its invariants. |
| `entity-catalog.md` | Every entity in the domain model with its identity, lifecycle, and responsibilities. |
| `value-object-catalog.md` | Every value object with its validation rules and immutability guarantees. |
| `domain-event-catalog.md` | Every domain event with its trigger, payload, and consumers. |
| `repository-contracts.md` | Every abstract repository interface with its method contracts. |

## Architecture

The domain model follows **Domain-Driven Design** (ADR-0006) with **Clean Architecture** (ADR-0005):

```
app/domain/
├── shared/           # Shared kernel (base types, IDs, value objects, exceptions, enums)
├── identity/         # User authentication, sessions, credentials
├── content/          # Subjects, concepts, templates, content versioning
├── assessment/       # Attempts, answers, question instances
├── mastery/          # Mastery scores, reviews, algorithm versions, MasteryCalculator
├── learning/         # Enrollments, study sessions, recommendations, achievements, streaks
├── scheduling/       # Scheduling configs, daily queues
├── billing/          # Billing plans, subscriptions, invoices
└── administration/   # Audit logs, feature flags, notifications, organizations
```

## Purity Guarantee

The domain layer contains **no framework imports**:
- No SQLAlchemy, no Pydantic, no FastAPI
- No database queries, no HTTP handlers
- No Redis, no external service calls
- Only Python stdlib and intra-domain imports

This purity makes the domain:
1. **Fully testable** without a database or web server
2. **Stable** across infrastructure changes
3. **Reusable** across different deployment contexts

## Key Design Decisions

1. **AggregateRoot** collects domain events; the application layer publishes them after persistence (ADR-0012, outbox pattern).
2. **Attempt is append-only** — no methods modify state after creation (the data moat invariant, I1).
3. **MasteryScore uses optimistic concurrency** — the `version` field prevents lost updates (ASD Section 17.8).
4. **MasteryCalculator is a pure function** — same inputs always produce the same outputs (ADR-0007, invariant M1).
5. **Memory Score ≠ Mastery Score** — two distinct estimates, combined not averaged (ADR-0008).
6. **Triple versioning on every Attempt** — content_version_id, template_version_id, algorithm_version_id (ADR-0011).
