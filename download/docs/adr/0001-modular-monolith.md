# ADR-0001 — Use a Modular Monolith Architecture

---

## Title

Use a Modular Monolith architecture for the Mastery Engine backend, deferring microservices until a measured trigger justifies extraction.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine is a SaaS product designed to scale from a few hundred early users to millions of learners over the next decade. The backend must serve an adaptive learning loop with a 200ms median latency target, must support nine bounded contexts (Identity, Learning, Assessment, Mastery, Content, Scheduling, Analytics, Billing, Administration), and must be maintainable by a small founding team that will grow organically.

The team's instinct, shaped by industry discourse, was to begin with microservices. Microservices are the dominant architectural pattern in 2026 engineering culture, and the temptation to adopt them early is strong: they promise independent deployment, independent scaling, technology heterogeneity, and team boundaries that map to organizational structure. However, the cost of microservices — operational complexity, distributed-system debugging, network-failure modes, transactional integrity challenges, and the cognitive load of a service mesh — is paid from day one, while the benefits are only realized at scale and team size that the project will not reach for years.

The architecture specification (Task 001, Section 1.4) commits to a "modular-monolith-first" philosophy. This ADR formalizes that commitment and defines the objective criteria under which the team will revisit it. The decision is reversible — extraction of a bounded context to a microservice is a documented future path — but the cost of starting with microservices and consolidating later is far higher than the cost of starting with a monolith and extracting later. This asymmetry is the core of the decision.

The project's bounded contexts (ASD Section 3.1) have clear interfaces and communicate via domain events (ASD Section 3.2). This boundary discipline is what makes the modular monolith viable: the contexts are already designed for extraction, so the extraction is a deployment change, not a redesign.

---

## Problem Statement

What deployment topology should the Mastery Engine backend adopt at launch, given that the system must scale to millions of learners but is being built by a small team that cannot afford the operational overhead of premature distribution?

---

## Decision

We will deploy the Mastery Engine backend as a **modular monolith**: a single deployable FastAPI application with strong internal module boundaries matching the bounded contexts. Each context owns its data, exposes service interfaces to other contexts, and communicates cross-context via domain events through an in-process event bus backed by the outbox pattern. No context reaches into another's database tables.

Microservices are deferred. A bounded context may be extracted to a microservice only when a specific, measured trigger (defined in Future Review Trigger) fires. The architecture is designed to make extraction a deployment change rather than a redesign: domain services are pure functions, repositories are interface-bound, and domain events are the cross-context communication mechanism.

---

## Alternatives Considered

### Alternative A: Microservices from day one

- **Description:** Each bounded context is a separate service with its own database, deployed and scaled independently from launch.
- **Arguments in favor:**
  - Independent deployment allows contexts to evolve at different paces.
  - Independent scaling allows the Mastery Engine (CPU-bound) to scale separately from the API (I/O-bound).
  - Technology heterogeneity allows the right tool per service.
  - Team boundaries map cleanly to service boundaries.
  - Industry-standard pattern; hires expect it.
- **Arguments against:**
  - Operational complexity (service mesh, distributed tracing, cross-service debugging) is paid from day one.
  - Distributed transactions are required for the learning loop, which spans Assessment, Mastery, and Scheduling — sagas or two-phase commit add latency and failure modes.
  - Network failures become a first-class concern; the loop's 200ms target is harder to guarantee across services.
  - A small team cannot operate N services; the on-call burden is linear in service count.
  - Local development requires running N services; iteration speed drops.
  - The benefits (independent scaling, team boundaries) are not realized until the team and traffic are 10x larger.
- **Why rejected:** The cost is paid now; the benefit is realized later. The asymmetry is decisive. The same boundary discipline that microservices enforce can be achieved in a monolith with code-review and linting rules, at a fraction of the operational cost. When the team and traffic justify it, extraction is a documented path (ASD Section 13.5).

### Alternative B: Serverless functions (AWS Lambda, GCP Cloud Functions)

- **Description:** Each API endpoint is a serverless function; the backend is a collection of functions plus managed services.
- **Arguments in favor:**
  - No servers to operate; scaling is automatic.
  - Pay-per-use cost model is attractive for early-stage traffic.
  - Deployments are granular.
- **Arguments against:**
  - Cold starts violate the learning loop's 200ms latency target.
  - Long-running operations (mastery recompute jobs) are awkward in serverless.
  - Vendor lock-in is high; the project values deployment portability (Docker).
  - Stateful background workers (outbox dispatcher, notification sender) require separate infrastructure anyway.
  - The learning loop is a stateful workflow; serverless favors stateless request handling.
- **Why rejected:** The latency target and the stateful nature of the learning loop are incompatible with serverless defaults. The operational savings are real but do not outweigh the latency risk on the system's most critical path.

### Alternative C: Single deployable with no internal boundaries ("big ball of mud")

- **Description:** A monolith without enforced module boundaries; code is organized by convenience rather than by bounded context.
- **Arguments in favor:**
  - Maximum development speed in the short term (no boundaries to respect).
  - No upfront design cost.
- **Arguments against:**
  - The system becomes unmaintainable within 18 months as contexts bleed into each other.
  - Extraction to microservices becomes impossible because boundaries were never defined.
  - The learning loop's invariants (single-writer for MasteryScore, etc.) are unenforceable.
  - Onboarding new engineers is harder because the architecture is implicit.
- **Why rejected:** The short-term speed is illusory; the long-term cost is fatal. This alternative is explicitly forbidden by the engineering standards (ASD Section 14.2).

---

## Pros

- **Lowest operational complexity** for the team size: one deployment, one monitoring dashboard, one log stream.
- **Transactional integrity** across the learning loop: Attempt recording, Mastery update, and Queue regeneration can share a transaction when needed, avoiding distributed transactions.
- **Local development simplicity**: one process to run, one database to migrate, fast iteration.
- **Boundary discipline preserved**: the bounded contexts (ASD Section 3.1) provide the same architectural clarity that microservices would, without the network.
- **Extraction path preserved**: because domain services are pure, repositories are interface-bound, and cross-context communication is via events, extracting a context to a microservice is a deployment change, not a redesign.
- **Single codebase** simplifies testing, CI, and versioning.
- **Lower cloud cost** at low traffic (one process vs N processes with idle overhead).

---

## Cons

- **No independent scaling**: if the Mastery Engine becomes CPU-bound, the whole application must scale, even if only one context needs it.
- **No independent deployment**: a change to one context requires redeploying the whole application.
- **Single runtime failure domain**: a crash in one context crashes the whole application.
- **Team scaling friction**: as the team grows, merge conflicts increase and ownership boundaries become organizational rather than technical.
- **Technology homogeneity**: all contexts must use Python and FastAPI; there is no per-context language choice.

---

## Consequences

- The team must maintain discipline around bounded context boundaries through code review and linting, since the compiler will not enforce them.
- The outbox pattern (ADR-0012) is mandatory from day one to preserve the extraction path; cross-context communication is always via events, never via direct repository access.
- Each bounded context's data must be owned by that context alone (single-writer principle, ASD Section 3.3); shared tables are forbidden.
- The deployment pipeline produces one container image; the team must build observability (ASD Section 17.1) that works within a single process.
- When a context is extracted (future), the event bus must be upgraded to a real message broker; the outbox pattern makes this a configuration change rather than a code change.
- The team must resist the temptation to skip boundaries "just this once"; one violation erodes the discipline that makes the architecture viable.

---

## Risks

- **Boundary erosion**: engineers take shortcuts, contexts bleed, and the monolith becomes a big ball of mud. *Mitigation:* linting rules that forbid cross-context repository imports; code review by the architecture review group for cross-context changes; periodic architecture audits.
- **Single point of failure**: a crash takes down the entire backend. *Mitigation:* run multiple instances behind a load balancer; health checks and auto-restart; the stateless property (ASD Section 13.1) means any instance can serve any request.
- **Scaling ceiling**: a single context's load forces the whole application to scale, wasting resources. *Mitigation:* monitor per-context CPU and latency; trigger extraction (Future Review Trigger) before the ceiling is hit.
- **Extraction surprise**: when extraction finally happens, hidden coupling is discovered that makes it harder than expected. *Mitigation:* the outbox pattern and interface-bound repositories make coupling explicit; periodic "extraction drills" (run a context in a separate process against the same database) surface hidden coupling early.

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Per-context scaling pressure**: the Mastery Engine or the Sandbox (when added) consumes more than 40% of the application's CPU at peak, while other contexts consume less than 20% — indicating that one context's load is forcing over-provisioning of the whole.
2. **Team size**: the engineering team exceeds 12 engineers working on the backend simultaneously, producing merge conflicts and ownership ambiguity that organizational process cannot resolve.
3. **Independent deployment demand**: a context (e.g., Content) needs to deploy multiple times per day while the rest of the application needs weekly stability — indicating that deployment coupling is hindering velocity.
4. **Latency regression**: the learning loop's p99 latency exceeds 500ms and profiling attributes it to in-process cross-context calls that would benefit from independent scaling.
5. **Incident isolation**: a recurring incident in one context (e.g., the Sandbox) takes down the whole application more than twice in a quarter, indicating that fault isolation would improve availability.

**Expected review action:** When any trigger fires, the architecture review group evaluates extraction of the triggering context to a microservice. The evaluation produces a new ADR proposing the extraction, with a migration plan, a rollback plan, and a measured justification. The first extraction candidate, by design, is the Sandbox (Phase 2, per ASD Section 16.2), because it has different security and scaling properties from the rest of the API.

---

## Related ADRs

- **Depends on:** ADR-0005 (Clean Architecture) — the modular monolith's boundary discipline is enforced by Clean Architecture's layer rules.
- **Depends on:** ADR-0006 (Domain-Driven Design) — the bounded contexts define the module boundaries.
- **Depends on:** ADR-0012 (Outbox Pattern + Domain Events) — cross-context communication must be event-based to preserve the extraction path.
- **Informs:** ADR-0014 (API-first development) — the API is the only external interface; internal context boundaries are not exposed.

---

## Related Architecture Sections

- ASD Section 1.4 — Technical Philosophy (modular-monolith-first).
- ASD Section 2 — System Overview (subsystem responsibilities within the monolith).
- ASD Section 3 — Domain Driven Design (bounded contexts).
- ASD Section 13.1 — Horizontal Scaling (stateless property).
- ASD Section 13.5 — Future Microservices (extraction triggers).

---

## Related Glossary Terms

- Bounded Context
- Domain Event
- Outbox
- Application Service
- Domain Service

---

*End of ADR-0001.*
