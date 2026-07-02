# ADR-0012 — Outbox Pattern + Domain Events

---

## Title

Use the Outbox Pattern with Domain Events for reliable, eventually-consistent, cross-context communication within the modular monolith.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine's bounded contexts (ASD Section 3.1) must communicate. When a Learner submits an Answer, the Assessment context writes the Attempt and must notify the Mastery context (to update the Mastery Score), the Analytics context (to update aggregates), and the Notification context (to send a milestone nudge if applicable). These notifications are side effects of the Attempt write; they should not block the Learner's request (the 200ms latency target), and they must not be lost if a downstream context is briefly unavailable.

The naive approach — the Assessment context directly calls the Mastery, Analytics, and Notification contexts within the request — has three problems. First, it couples the Assessment context to its consumers, violating the bounded-context independence that DDD (ADR-0006) requires. Second, it makes the request latency proportional to the slowest consumer, threatening the 200ms target. Third, it provides no durability: if a consumer is unavailable, the notification is lost unless the Assessment context implements its own retry, which duplicates infrastructure.

The industry-standard solution is the **Outbox Pattern**: the originating context writes the Attempt and an "outbox event" record in the same database transaction. A background worker (the Outbox Dispatcher) polls the outbox table, dispatches events to subscribers, and marks them as dispatched. The pattern provides durability (the event is committed with the originating write), decoupling (the originating context does not know its consumers), and asynchronous execution (the request is not blocked by consumers).

The architecture specification (Task 001, Section 3.2 and Section 11.4) commits to the outbox pattern with domain events. This ADR formalizes the commitment and the consequences.

---

## Problem Statement

How should the Mastery Engine's bounded contexts communicate side effects (Attempt recorded, Mastery updated, Content published) reliably, asynchronously, and without coupling, given the 200ms learning-loop latency target and the requirement that no event is lost?

---

## Decision

We will use the **Outbox Pattern with Domain Events** for all cross-context communication within the modular monolith.

- **Domain Events** are records of something that happened in a context (`AttemptRecorded`, `MasteryUpdated`, `ContentPublished`). They are named in past tense, are immutable once raised, and are versioned with the API.
- The originating context writes the domain change and the outbox event record **in the same database transaction**. If the transaction commits, the event is durable; if it rolls back, the event is not raised.
- An **Outbox Dispatcher** (background worker) polls the outbox table, dispatches events to subscribers, and marks them as dispatched. Dispatch is at-least-once; subscribers must be idempotent.
- **Subscribers** are event handlers in other contexts. They consume events asynchronously and update their own state. A subscriber failure does not block the originating context or other subscribers.
- The **Event Bus** is the in-process dispatch mechanism (currently in-process; may be backed by a message broker in the future if contexts are extracted to microservices, per ADR-0001).

Domain events are used for: analytics projection rebuilds, notification dispatch, mastery recompute triggers, cache invalidation, and any other side effect that does not need to block the originating request. Synchronous cross-context calls (e.g., the Learning context calling the Mastery context for the current Mastery Score to build a queue) are permitted for read-heavy, low-latency operations, but go through service interfaces, not through the outbox.

---

## Alternatives Considered

### Alternative A: Synchronous cross-context calls for all communication

- **Description:** Contexts call each other directly for both reads and side effects.
- **Arguments in favor:**
  - Simpler mental model.
  - No background workers or outbox table.
- **Arguments against:**
  - **Coupling**: the originating context knows its consumers, violating bounded-context independence.
  - **Latency**: the request is proportional to the slowest consumer, threatening the 200ms target.
  - **No durability**: if a consumer is unavailable, the side effect is lost unless the originating context retries, duplicating infrastructure.
  - **Failure propagation**: a consumer failure can fail the originating request, violating the principle that side effects should not block the main operation.
- **Why rejected:** The coupling, latency, and durability problems are decisive. Synchronous calls are acceptable for reads (where the originating context needs the result to proceed) but not for side effects.

### Alternative B: Direct database sharing (contexts read each other's tables)

- **Description:** Contexts read each other's database tables directly, without service interfaces or events.
- **Arguments in favor:**
  - Fastest implementation.
  - No event infrastructure.
- **Arguments against:**
  - **Single-writer violation**: if multiple contexts write to the same table, data integrity is at risk.
  - **Schema coupling**: a schema change in one context breaks all contexts that read its tables.
  - **No bounded-context independence**: contexts are tightly coupled at the data level.
  - **Forbidden by the ASD** (Section 3.1): "Direct cross-context repository access is forbidden."
- **Why rejected:** The schema coupling and single-writer violation are decisive. Direct database sharing is explicitly forbidden by the architecture.

### Alternative C: External message broker (Kafka, RabbitMQ) from day one

- **Description:** Use a message broker for all cross-context communication from launch.
- **Arguments in favor:**
  - Industry-standard for event-driven systems.
  - Built-in durability, retry, and dead-letter queues.
  - Scales to microservices without change.
- **Arguments against:**
  - **Operational overhead**: a message broker is another system to operate, monitor, and upgrade. The team cannot afford this at the current size.
  - **Latency**: broker round-trips add latency (milliseconds, not microseconds) that the in-process outbox avoids.
  - **Complexity**: broker configuration, topic management, and consumer-group management add complexity that the modular monolith does not need.
  - **The outbox pattern provides a migration path**: when a context is extracted to a microservice (ADR-0001), the outbox dispatcher can be upgraded to publish to a broker instead of dispatching in-process, without changing the originating context.
- **Why rejected:** The operational overhead and complexity are not justified at launch. The outbox pattern provides the same durability and decoupling benefits in-process, with a clear migration path to a broker when needed.

### Alternative D: Change Data Capture (CDC) from the database

- **Description:** Use CDC (e.g., Debezium) to capture row changes from PostgreSQL and propagate them as events.
- **Arguments in favor:**
  - No application code changes; events are derived from the database.
  - Captures all changes, including those from background jobs.
- **Arguments against:**
  - **CDC captures data changes, not domain events**: a row change in the Attempts table is not the same as the domain event `AttemptRecorded`. The domain event carries semantic meaning that the row change does not.
  - **Coupling to schema**: CDC events mirror the database schema, coupling consumers to the schema rather than to the domain event contract.
  - **Operational complexity**: CDC tooling (Debezium, Kafka Connect) is non-trivial to operate.
  - **The outbox pattern is more domain-appropriate**: domain events are raised by the application, carrying domain meaning, and are decoupled from the schema.
- **Why rejected:** CDC is a strong pattern for analytics replication (feeding the derived analytics store, ASD Section 13.7) but not for domain event dispatch. The outbox pattern is more domain-appropriate for cross-context communication.

---

## Pros

- **Durability**: events are committed with the originating write; no event is lost if the dispatcher is briefly unavailable.
- **Decoupling**: the originating context does not know its consumers; consumers subscribe without the originator's knowledge.
- **Asynchronous**: the originating request is not blocked by consumers; the 200ms latency target is preserved.
- **Bounded-context independence**: contexts communicate through events, not through shared tables or direct calls.
- **Idempotency requirement encourages good design**: subscribers must be idempotent (at-least-once delivery), which produces more robust consumers.
- **Migration path to microservices**: when a context is extracted (ADR-0001), the outbox dispatcher publishes to a broker instead of dispatching in-process, without changing the originating context.
- **Audit trail**: outbox events are persisted, providing an audit trail of all cross-context communication.
- **Replayability**: outbox events can be replayed (e.g., to backfill a new consumer or to recover from a consumer failure).

---

## Cons

- **Eventual consistency**: consumers see events after a delay (the dispatcher's poll interval plus processing time). The system is eventually consistent, not immediately consistent.
- **Complexity**: the outbox table, the dispatcher, and the subscriber handlers are additional infrastructure.
- **Idempotency burden**: subscribers must be idempotent, which requires careful design (e.g., deduplication by event id).
- **Ordering**: events from the same originator are ordered (the dispatcher preserves order within a context), but events from different originators are not globally ordered. Subscribers that need ordering must handle it.
- **Dead-letter management**: events that fail repeatedly must be dead-lettered and investigated, requiring monitoring and on-call process.

---

## Consequences

- Every bounded context that raises domain events has an outbox table in its schema.
- Every Application Service that performs a write also writes an outbox event in the same transaction.
- An Outbox Dispatcher background worker polls the outbox table (or uses PostgreSQL LISTEN/NOTIFY for lower latency) and dispatches events to subscribers.
- Subscribers are event handlers in other contexts, registered with the Event Bus.
- Subscribers are idempotent (deduplicate by event id; design for at-least-once delivery).
- Events are versioned with the API; schema changes are backward-compatible or accompanied by a new event version.
- The Event Bus is in-process currently; the interface is designed so that a message broker can replace it without changing originators or subscribers.
- Dead-letter queues are monitored; dead-lettered events are investigated and re-processed or discarded with rationale.
- The outbox table is partitioned by time (or archived) to prevent unbounded growth.

---

## Risks

- **Eventual consistency surprises**: a user sees stale data because a consumer has not yet processed the event. *Mitigation:* explicit consistency-mode declaration per endpoint (ASD Section 17.9); UI affordances that signal potential staleness; subscriber lag monitoring.
- **Subscriber failure**: a subscriber fails to process an event, leaving its state inconsistent with the originator. *Mitigation:* retry with exponential backoff; dead-letter after configurable failure count; monitoring and alerting on dead-letter queue depth.
- **Outbox table growth**: the outbox table grows unbounded if events are not archived. *Mitigation:* dispatched events are archived or partitioned; retention policy documented.
- **Event schema evolution**: an event schema changes, breaking existing subscribers. *Mitigation:* events are versioned; backward-compatible changes are preferred; breaking changes produce a new event version with parallel publishing during migration.
- **Dispatcher downtime**: the dispatcher is unavailable, and events accumulate in the outbox. *Mitigation:* the dispatcher is stateless and restartable; multiple dispatcher instances can run in parallel (with locking to avoid duplicate dispatch); backlog monitoring alerts when the outbox grows.
- **Idempotency bugs**: a subscriber is not idempotent, and a redelivered event produces duplicate side effects (e.g., two notifications). *Mitigation:* subscriber code review enforces idempotency; integration tests verify idempotency under redelivery.

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Cross-context extraction**: a bounded context is extracted to a microservice (per ADR-0001), requiring the Event Bus to be backed by a message broker instead of in-process dispatch.
2. **Event volume**: the outbox table's write rate or the dispatcher's dispatch rate exceeds sustainable throughput, indicating that the in-process model is insufficient.
3. **Subscriber lag**: subscriber lag (time between event raise and event processing) consistently exceeds 5 seconds, indicating that the dispatcher or subscribers cannot keep up.
4. **Cross-service events**: a future feature requires events to be consumed by an external system (e.g., a data warehouse, a partner integration), justifying a message broker with external connectivity.
5. **Event schema complexity**: event schemas become so complex that versioning and backward compatibility are unsustainable, indicating that a schema registry or a different eventing model is needed.

**Expected review action:** When any trigger fires, the architecture review group evaluates the migration to a message broker (Kafka, RabbitMQ, or a managed equivalent). The migration is a significant decision requiring a new ADR, a migration plan (the outbox dispatcher publishes to the broker instead of dispatching in-process), and a rollback plan. The outbox pattern itself is unchanged; only the dispatch mechanism changes.

---

## Related ADRs

- **Depends on:** ADR-0001 (Modular Monolith) — the outbox pattern preserves the extraction path to microservices.
- **Depends on:** ADR-0006 (Domain-Driven Design) — domain events are the DDD mechanism for cross-context communication.
- **Depends on:** ADR-0002 (PostgreSQL) — the outbox is a PostgreSQL table, written in the same transaction as the originating write.
- **Informs:** ADR-0011 (Triple Versioning) — domain events carry version references for cross-context consistency.

---

## Related Architecture Sections

- ASD Section 3.2 — Context Communication Patterns (synchronous vs. asynchronous).
- ASD Section 11.4 — Background Job Flow (outbox dispatcher and worker pool).
- ASD Section 10.11 — Background Workers (idempotency, separate processes).
- ASD Section 13.4 — Background Jobs (job types including outbox dispatch).

---

## Related Glossary Terms

- Domain Event
- Outbox
- Event Bus
- Bounded Context
- Application Service
- Background Worker

---

*End of ADR-0012.*
