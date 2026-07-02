# ADR-0006 — Use Domain-Driven Design (DDD)

---

## Title

Adopt Domain-Driven Design as the modeling methodology for the Mastery Engine, with bounded contexts, ubiquitous language, and aggregates as first-class concepts.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine is a domain-complex system. Its business logic — the learning loop, the mastery model, the scheduling algorithm, the content pipeline — is the source of its competitive advantage, not its UI or its infrastructure. The system's complexity is in the domain: the relationships between Concepts, the dependencies between Objectives, the diagnosis of Misconceptions, the scheduling of Reviews. If the domain is modeled poorly, no amount of excellent infrastructure will save the product; if the domain is modeled well, the infrastructure can be replaced over time without losing the product's essence.

The team must choose a modeling methodology that: (1) makes the domain explicit and central; (2) provides vocabulary for communicating about the domain across engineering, product, design, and curriculum; (3) organizes the codebase so that the domain's structure is reflected in the code's structure; (4) scales as the system grows from one Subject (Python) to many (SQL, Java, Cybersecurity, Cloud, IELTS). Domain-Driven Design (DDD), as articulated by Eric Evans and refined by Vaughn Vernon, is the industry's most developed answer to these requirements.

The architecture specification (Task 001, Section 3) commits to DDD with nine bounded contexts (Identity, Learning, Assessment, Mastery, Content, Scheduling, Analytics, Billing, Administration). The Ubiquitous Language & Domain Glossary (Task 002) is the project's commitment to DDD's ubiquitous-language practice. This ADR formalizes the DDD commitment and the practices that follow from it.

---

## Problem Statement

What modeling methodology should the Mastery Engine adopt to ensure the domain is explicit, communicable, and reflected in the code's structure, and to scale gracefully as the system grows from one Subject to many?

---

## Decision

We will adopt **Domain-Driven Design** as the project's modeling methodology, with three practices as first-class commitments:

1. **Bounded Contexts** — the system is divided into nine bounded contexts (Identity, Learning, Assessment, Mastery, Content, Scheduling, Analytics, Billing, Administration). Each context owns a coherent slice of the domain, has its own ubiquitous language, owns its data, and communicates with other contexts via service interfaces (synchronous) and domain events (asynchronous). Cross-context repository access is forbidden.

2. **Ubiquitous Language** — each bounded context has a ubiquitous language (a shared vocabulary used by engineers, product, design, and curriculum) that is reflected in code, conversations, documentation, and UI labels. The project's glossary (Task 002) is the master record of the ubiquitous language; it is enforced by code review and naming standards.

3. **Aggregates** — domain objects are organized into Aggregates (consistency boundaries with a root Entity). Each Aggregate is persisted atomically via a Repository. Cross-Aggregate consistency is achieved via domain events, not via cross-Aggregate transactions. The single-writer principle is enforced: each Aggregate has exactly one owning context that may write to it.

---

## Alternatives Considered

### Alternative A: Database-first modeling (entity-relationship design driving the code)

- **Description:** Design the database schema first; generate or hand-write ORM models; put business logic in service classes that operate on the ORM models.
- **Arguments in favor:**
  - Familiar to most engineers; low learning curve.
  - Fast to start; the schema is the model.
  - Tooling is mature (ORM generators, schema migrations).
- **Arguments against:**
  - The database schema is not the domain model; it is a persistence concern. Conflating them couples the domain to the database and makes the domain hard to reason about independently.
  - Business logic migrates to ORM models (the "anemic domain model" anti-pattern) or to service classes that operate on bags of getters and setters, losing the domain's behavioral richness.
  - The model cannot be tested without a database.
  - As the system scales, the schema's normalization conflicts with the domain's aggregation, producing awkward joins and performance problems.
  - The vocabulary of the database (tables, columns) leaks into conversations, displacing the domain's vocabulary.
- **Why rejected:** The domain complexity of the Mastery Engine demands a richer model than the database schema provides. Database-first modeling is adequate for CRUD applications; it is inadequate for a system whose domain is the product.

### Alternative B: Service-oriented architecture without DDD

- **Description:** Organize the system into services by technical concern (auth service, content service, analytics service) without the explicit domain-modeling discipline of DDD.
- **Arguments in favor:**
  - Simpler to start with; services are organized by what they do.
  - Avoids the upfront cost of domain modeling.
- **Arguments against:**
  - Without bounded contexts, service boundaries are arbitrary and tend to drift toward technical concerns rather than domain concerns.
  - Without ubiquitous language, conversations about the domain become ambiguous (different teams use different words for the same concept).
  - Without aggregates, consistency boundaries are unclear, and services end up with either too-tight coupling or too-loose consistency.
  - The system's complexity becomes unmanageable as it grows, because the domain's structure is not reflected in the code's structure.
- **Why rejected:** The lack of discipline produces a system that is hard to reason about and hard to evolve. DDD's upfront cost is paid back over the system's lifetime in clarity and maintainability.

### Alternative C: Event-Driven Architecture (EDA) as the primary methodology

- **Description:** Model the system as a stream of events; services react to events and produce new events; the event log is the source of truth (event sourcing).
- **Arguments in favor:**
  - Excellent for auditability and replayability.
  - Loose coupling between services.
  - Natural fit for analytics.
- **Arguments against:**
  - Event sourcing adds significant complexity (versioning, schema evolution, projection management) that the project does not need at launch.
  - The learning loop's synchronous path (Attempt → Mastery → Queue) benefits from transactional integrity that event sourcing makes harder.
  - The team's expertise is in DDD with event-augmented (not event-sourced) architecture; the outbox pattern (ADR-0012) provides the auditability benefits without the full event-sourcing complexity.
- **Why rejected:** Event sourcing is a strong pattern for systems with strict audit or replay requirements; the Mastery Engine achieves sufficient auditability via the outbox pattern and the append-only Attempt table, without the full complexity of event sourcing. Event sourcing may be revisited for specific contexts (e.g., Billing) in the future.

---

## Pros

- **Domain centrality**: the domain is the center of the system; infrastructure is peripheral. The system's behavior is comprehensible by reading the domain.
- **Ubiquitous language**: engineers, product, design, and curriculum use the same vocabulary, eliminating the ambiguity that plagues most projects. The glossary (Task 002) is the master record.
- **Bounded contexts**: the system is divided into coherent slices that can evolve independently, with clear interfaces between them. This is the foundation of the modular monolith (ADR-0001) and the extraction path to microservices.
- **Aggregates**: consistency boundaries are explicit; transactional integrity is achievable; the single-writer principle prevents data corruption.
- **Scalability of the model**: as new Subjects are added (ADR-0010), the existing bounded contexts accommodate them without restructuring; the Subject-agnostic core (Content, Mastery, Scheduling) is reusable.
- **Testability**: Aggregates and Domain Services are pure; unit tests are fast and comprehensive.
- **Onboarding**: new engineers learn the system by learning the bounded contexts and the ubiquitous language; the model is the map.

---

## Cons

- **Upfront cost**: domain modeling is slow; the team must invest time in understanding the domain before coding. This is a feature, not a bug, but it is a cost.
- **Learning curve**: DDD is not universally known; engineers unfamiliar with it need onboarding to bounded contexts, aggregates, and ubiquitous language.
- **Discipline required**: the practices (ubiquitous language, aggregate boundaries, single-writer) are easy to violate under deadline pressure, and violations compound.
- **Risk of over-modeling**: DDD can lead to over-engineering for simple subdomains (e.g., Billing, which may be a CRUD context). (Mitigated by distinguishing core, supporting, and generic subdomains; only core subdomains get full DDD treatment.)

---

## Consequences

- The codebase is organized by bounded context, with each context having its own domain, application, infrastructure, and API layers (ADR-0005).
- The ubiquitous language (Task 002) is enforced in code (class names, method names, variable names), in documentation, and in UI labels.
- Each Aggregate has one owning context and one Repository; cross-context writes are forbidden.
- Domain events (ADR-0012) are the cross-context communication mechanism; the outbox pattern ensures durability.
- The Mastery context is treated as a first-class bounded context (not a sub-context of Learning or Assessment), because mastery state crosses the Learning/Assessment boundary and must not be subordinated to either (ASD Section 3.1).
- Core subdomains (Learning, Assessment, Mastery, Content, Scheduling) receive full DDD treatment; supporting subdomains (Analytics, Administration) receive lighter treatment; generic subdomains (Identity, Billing) may use off-the-shelf solutions where appropriate.
- The glossary is maintained as a living document; new terms require a glossary change request adjudicated by the Domain Modeling Lead.

---

## Risks

- **Ubiquitous language drift**: teams use different words for the same concept, eroding the language. *Mitigation:* the glossary is the source of truth; code review flags terminology violations; linting checks for forbidden terms (Task 002, Forbidden Terminology).
- **Aggregate boundary errors**: aggregates are too large (causing contention) or too small (causing excessive cross-aggregate coordination). *Mitigation:* aggregate boundaries are reviewed by the architecture review group; refactoring aggregates is permitted via a new ADR.
- **Over-modeling**: supporting subdomains receive full DDD treatment unnecessarily, adding overhead. *Mitigation:* the architecture review group distinguishes core, supporting, and generic subdomains; only core subdomains get full treatment.
- **Context boundary erosion**: contexts reach into each other's data, breaking the single-writer principle. *Mitigation:* linting rules forbid cross-context repository imports; code review by the architecture review group.
- **DDD expertise gap**: engineers unfamiliar with DDD produce models that look like DDD but lack its discipline. *Mitigation:* onboarding training; pairing with DDD-experienced engineers; the architecture review group coaches.

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Context boundary friction**: cross-context communication becomes a significant source of latency or complexity, indicating that context boundaries may need re-drawing.
2. **Aggregate contention**: an Aggregate's write contention becomes a bottleneck (measured by lock wait times or transaction retries), indicating that the Aggregate is too large and should be split.
3. **Ubiquitous language breakdown**: a periodic glossary audit finds widespread terminology violations, indicating that the language needs reinforcement or revision.
4. **New Subject onboarding friction**: adding a second Subject (e.g., SQL) reveals that the Subject-agnostic core is not as agnostic as assumed, indicating that the bounded context boundaries need adjustment.

**Expected review action:** When any trigger fires, the architecture review group evaluates the boundary or language change. Aggregate refactoring is permitted via a new ADR; context boundary changes are more disruptive and require strong justification. The ubiquitous language is updated via glossary change requests.

---

## Related ADRs

- **Depends on:** ADR-0005 (Clean Architecture) — DDD's aggregates and domain services live in Clean Architecture's Domain Layer.
- **Depends on:** ADR-0012 (Outbox Pattern + Domain Events) — DDD's cross-context communication is via domain events.
- **Informs:** ADR-0010 (Subject-agnostic architecture) — DDD's bounded contexts make the Subject-agnostic core possible.
- **Informs:** ADR-0011 (Triple Versioning) — DDD's aggregates carry the version metadata.

---

## Related Architecture Sections

- ASD Section 3 — Domain Driven Design (bounded contexts, communication patterns, ownership matrix).
- ASD Section 4 — Core Domain Model (entities per bounded context).
- ASD Section 14.2 — Folder Organization (one folder per bounded context).

---

## Related Glossary Terms

- Bounded Context
- Ubiquitous Language
- Aggregate
- Entity
- Value Object
- Domain Event
- Repository
- Domain Service

---

*End of ADR-0006.*
