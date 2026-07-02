# Mastery Engine — Domain Behavior: Commands, Events, Queries, State Machines

> **Status:** v1.0 — Authoritative source for the Mastery Engine's behavioral model.
> **Owner:** Principal Domain Architect
> **Audience:** Backend engineers, frontend engineers, data engineers, QA, AI agents.
> **Companion documents:**
> - Architecture Specification (Task 001) — `/mastery-engine-architecture-spec.md`
> - Ubiquitous Language (Task 002) — `/docs/domain/ubiquitous-language.md`
> - ADR Repository (Task 003) — `/docs/adr/`
> - PostgreSQL Database Architecture (Task 004) — `/docs/database/`

---

## What This Document Set Is

This is the complete **behavioral model** of the Mastery Engine. Where Task 004 defined the *data* architecture (what is stored), this document set defines the *behavior* architecture (what the system *does*). Every meaningful change in the system is represented as a **Command** (a request to mutate state) or a **Domain Event** (a record of something that happened). Every read is represented as a **Query**. Every aggregate's lifecycle is represented as a **State Machine**.

The behavioral model is governed by four rules (from the brief's acceptance criteria):

1. **Every mutation originates from a Command.** No state changes happen except via a command handler. This makes all mutations auditable and testable.
2. **Every Command produces one or more Domain Events.** A command that produces no event either did nothing or is a query mislabeled as a command. Events are the durable record of what the command did.
3. **Every Query is read-only.** Queries never mutate state. They may read from caches or read models, but they never write.
4. **Every aggregate has a documented lifecycle.** The state machine for each aggregate defines its valid states, transitions, and recovery from invalid states.

---

## Conflict Reconciliation with the Brief

The brief targets "100+ commands" and "150+ events." After analysis against the authoritative documents (Tasks 001–004, which define ~9 bounded contexts and ~57 database tables), the natural count of *distinct, coarse-grained, non-duplicative* commands is ~70 and events is ~90. Meeting the literal targets would require either:

- **Splitting coarse commands into finer variants** (e.g., `UpdateConceptDescription` vs `UpdateConceptName` vs `UpdateConceptDifficulty`), which violates the DDD principle of coarse-grained commands and contradicts Task 002's ubiquitous language (which treats "revise a Concept" as one operation).
- **Inventing commands/events for hypothetical features** not in the roadmap (Tasks 001/003), which would inflate the document without adding value.

This document set provides **full coverage** of all meaningful business behavior (~70 commands, ~90 events) without artificial inflation. If finer granularity is later required, a follow-up pass can split commands; the current granularity matches the ubiquitous language and the architecture specification.

---

## Document Index

| File | Topic |
|---|---|
| `01-commands.md` | Every command in the system, grouped by bounded context. |
| `02-domain-events.md` | Every domain event, grouped by bounded context. |
| `03-queries.md` | Every query (read operation), with consistency, latency, caching, authorization. |
| `04-state-machines.md` | State machines for all 18 aggregates, with Mermaid diagrams. |
| `05-workflows.md` | End-to-end business workflows (onboarding, daily learning, content publish, etc.). |
| `06-sequence-diagrams.md` | 30+ Mermaid sequence diagrams for critical flows. |
| `07-event-catalog.md` | Complete event catalog: producer, consumers, ordering, criticality, retention, replay. |
| `08-event-versioning.md` | Event schema evolution, backward compatibility, replay, deprecation, migration. |
| `09-eventual-consistency.md` | Where the system is strongly vs eventually consistent; synchronous vs asynchronous; outbox integration. |
| `10-error-handling.md` | Business failures and recovery strategies. |
| `11-idempotency.md` | Idempotency strategy for commands, events, retries, message processing. |
| `12-future-evolution.md` | How the behavioral model evolves for ML, collaborative learning, AI tutoring, offline mode, marketplace, etc. |

---

## Behavioral Architecture Overview

### Command Flow

```
Client (Browser/App) → API Controller → Command Handler (Application Service)
                                              │
                                              ▼
                                      Domain Service (pure)
                                              │
                                              ▼
                                      Repository (persist)
                                              │
                                              ▼
                                      Outbox (write event in same txn)
                                              │
                                              ▼
                                      Response DTO to Client
```

A Command is issued by a client (or a background job), validated by the API layer, handled by an Application Service (the command handler), which calls Domain Services to perform business logic, persists changes via Repositories, and writes Domain Events to the Outbox in the same transaction. The response is returned to the client. The Outbox Dispatcher asynchronously delivers events to subscribers.

### Event Flow

```
Outbox Table → Outbox Dispatcher → Event Bus → Subscriber Handlers
                                                      │
                                          ┌───────────┼───────────┐
                                          ▼           ▼           ▼
                                     Mastery      Analytics    Notification
                                     Handler      Handler      Handler
                                          │           │           │
                                          ▼           ▼           ▼
                                     Update       Update       Queue
                                     Mastery      Read Model   Notification
                                     Score        Projection
```

Domain Events are written to the Outbox in the same transaction as the originating command's data changes. The Outbox Dispatcher polls the Outbox (or uses PostgreSQL LISTEN/NOTIFY) and delivers events to the Event Bus. The Event Bus routes events to subscriber handlers in other bounded contexts. Subscribers update their own state asynchronously.

### Query Flow

```
Client → API Controller → Query Handler → Read Model / Cache / Repository
                                              │
                                              ▼
                                      Response DTO to Client
```

A Query is issued by a client, validated by the API layer, handled by a Query Handler that reads from a Read Model (precomputed projection), a cache (Redis), or directly from the database (via Repository). Queries never mutate state.

### State Machine Enforcement

Each aggregate's state machine is enforced by:
1. **Database CHECK constraints** — e.g., `status IN ('draft', 'published', 'deprecated')`.
2. **Domain Service invariants** — the Domain Service rejects invalid transitions.
3. **Command handlers** — the command handler checks preconditions before issuing the command.

---

## Conformance to Authoritative Documents

| Source | Conformance |
|---|---|
| ASD Section 3 (DDD) | Commands and events are scoped to bounded contexts; cross-context communication is via events (not direct calls). |
| ASD Section 5 (Learning Loop) | The Loop is modeled as a workflow (SubmitAnswer command → AttemptRecorded event → MasteryUpdated event → QueueRegenerated event). |
| ASD Section 8 (API Architecture) | Commands and Queries map to API endpoints (Commands → POST/PUT/DELETE; Queries → GET). |
| ASD Section 10 (Backend Architecture) | Command handlers are Application Services; event subscribers are background workers. |
| Task 002 (Ubiquitous Language) | Command and event names use the glossary's terms (e.g., `SubmitAnswer`, not `SaveResponse`; `AttemptRecorded`, not `AnswerSaved`). |
| ADR-0006 (DDD) | Aggregates are consistency boundaries; state machines define aggregate lifecycles. |
| ADR-0007 (Deterministic Scheduling) | Mastery and scheduling commands are deterministic; no runtime AI. |
| ADR-0011 (Triple Versioning) | Events carry version references (content_version_id, template_version_id, algorithm_version_id). |
| ADR-0012 (Outbox Pattern) | Events are written to the Outbox in the same transaction as the originating write. |
| Task 004 (Database) | Commands and events map to the 57 tables defined in Task 004. |

---

## How to Use This Document Set

- **Implementing a feature**: find the relevant workflow in `05-workflows.md`; follow the commands and events; consult `04-state-machines.md` for aggregate lifecycles.
- **Understanding a flow**: find the sequence diagram in `06-sequence-diagrams.md`.
- **Adding a new command**: follow the template in `01-commands.md`; ensure it produces ≥1 event; add the event to `02-domain-events.md` and `07-event-catalog.md`.
- **Debugging an event flow**: consult `07-event-catalog.md` for producer/consumers; consult `09-eventual-consistency.md` for consistency expectations.
- **Handling a failure**: consult `10-error-handling.md` for the failure type and recovery strategy.
- **Ensuring idempotency**: consult `11-idempotency.md` for the command/event idempotency requirements.

---

*End of Domain Behavior README.*
