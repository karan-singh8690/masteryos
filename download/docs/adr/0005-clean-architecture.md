# ADR-0005 — Use Clean Architecture

---

## Title

Adopt Clean Architecture as the layering model for the Mastery Engine backend, with strict dependency rules flowing inward.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine is a system whose business logic (the learning loop, the mastery model, the scheduling algorithm) is the source of its competitive advantage and whose infrastructure (FastAPI, PostgreSQL, Redis) is commodity. The team must be able to evolve infrastructure without touching business logic, to test business logic without infrastructure, and to reason about the system's behavior at the domain level without reading HTTP handlers or SQL. This requires a strict separation between the domain (what the system *is*) and the infrastructure (how the system *runs*).

The architecture specification (Task 001, Section 8 and Section 10) commits to a layered architecture: Controllers (API layer), Use Case Services (Application layer), Domain Services and Aggregates (Domain layer), and Repositories (Persistence layer). The dependency rule is that outer layers depend on inner layers, never the reverse: the domain depends on nothing infrastructure-specific; the application layer depends on the domain; the API and persistence layers depend on the application layer.

This is not a novel decision — Clean Architecture is well-established — but it is a consequential one, because it governs how every line of code is organized. The discipline of Clean Architecture is easy to articulate and hard to maintain: the temptation to let the domain depend on the ORM, or to put business logic in a Controller, is constant. This ADR formalizes the commitment and the rules that enforce it.

The alternative — a less rigid "layered architecture" without strict dependency rules — is the industry default and is what most teams drift toward without explicit discipline. The Mastery Engine rejects that default because the project's longevity (a decade or more) and the importance of the domain logic make the discipline worth the cost.

---

## Problem Statement

How should the Mastery Engine backend be layered to ensure that business logic is testable in isolation, that infrastructure can evolve without affecting the domain, and that the system's complexity remains manageable as it scales?

---

## Decision

We will adopt **Clean Architecture** with four layers and a strict inward-only dependency rule. The layers, from outermost to innermost:

1. **API Layer (Controllers)** — HTTP transport, request validation, response serialization. Depends on the Application Layer. Contains no business logic.
2. **Application Layer (Use Case Services)** — use-case orchestration, transaction boundaries, DTO composition. Depends on the Domain Layer. Contains no business rules, only orchestration.
3. **Domain Layer (Domain Services, Aggregates, Value Objects, Domain Events)** — pure business rules. Depends on nothing infrastructure-specific. Contains no I/O, no framework code, no ORM.
4. **Persistence Layer (Repositories)** — aggregate persistence, SQL. Depends on the Domain Layer (on Repository interfaces defined there). Implements those interfaces with infrastructure-specific code.

The dependency rule: **dependencies point inward only**. The Domain Layer depends on nothing outside itself. The Application Layer depends on the Domain. The API and Persistence Layers depend on the Application and Domain. No inner layer imports from an outer layer. This rule is enforced by linting (import boundaries) and by code review.

Repository interfaces are defined in the Domain Layer; their implementations live in the Persistence Layer. The DI container wires implementations to interfaces, so the Domain and Application Layers never know which implementation they are using. Tests substitute fakes by constructing services with fake repository implementations.

---

## Alternatives Considered

### Alternative A: Traditional layered architecture (without strict dependency rules)

- **Description:** A layered architecture (presentation, business, data) without the inward-only dependency rule; layers may depend on each other more freely.
- **Arguments in favor:**
  - Simpler to start with; no upfront design cost.
  - More flexible; engineers can reach across layers when convenient.
  - Common in industry; hires expect it.
- **Arguments against:**
  - The domain ends up depending on the ORM, the web framework, or both, because the convenience of reaching across layers is irresistible.
  - Business logic migrates to Controllers or to ORM models, where it is hard to test and hard to reason about.
  - Infrastructure changes (switching ORM, switching framework) become multi-quarter projects because the domain is coupled to them.
  - Testing business logic requires a database and a web server, slowing the test suite and making it fragile.
  - The system's complexity grows unmanageably over a decade as coupling accumulates.
- **Why rejected:** The long-term cost is decisive. The Mastery Engine is designed for a decade of maintenance; the discipline of Clean Architecture is the insurance that keeps the domain comprehensible over that horizon. The short-term convenience of traditional layering is not worth the long-term coupling.

### Alternative B: Hexagonal Architecture (Ports and Adapters)

- **Description:** Hexagonal Architecture, where the domain is surrounded by ports (interfaces) and adapters (implementations), with all I/O going through adapters.
- **Arguments in favor:**
  - Conceptually similar to Clean Architecture; emphasizes the isolation of the domain.
  - The "ports and adapters" vocabulary is intuitive for some teams.
- **Arguments against:**
  - Substantially the same as Clean Architecture in practice; the difference is vocabulary, not substance.
  - Clean Architecture's four-layer model is more concrete and prescriptive, which helps a small team avoid under- or over-layering.
  - The team's existing expertise is in Clean Architecture; adopting Hexagonal would impose a vocabulary change for no substantive benefit.
- **Why rejected:** The vocabulary and prescriptiveness of Clean Architecture are advantages for this team. Hexagonal is a fine alternative; the choice is close, and the deciding factor is team familiarity and the four-layer model's concreteness.

### Alternative C: Microkernel architecture

- **Description:** A microkernel (plug-in) architecture where the core system is minimal and features are added as plug-ins.
- **Arguments in favor:**
  - Excellent for extensibility; new features are plug-ins.
  - Used by some platforms (e.g., Eclipse, VS Code).
- **Arguments against:**
  - The Mastery Engine is not a platform for third-party extensibility; it is a single product. The plug-in model adds complexity without benefit.
  - The domain logic (mastery, scheduling) is not naturally decomposable into plug-ins; it is a coherent whole.
  - The plug-in model introduces versioning and compatibility complexity that the project does not need.
- **Why rejected:** The architecture does not match the problem. Microkernel is for extensible platforms; the Mastery Engine is a product.

---

## Pros

- **Testability**: the Domain Layer is pure Python with no I/O; unit tests run in milliseconds without a database or web server. The Application Layer is tested with fake repositories. Only the Persistence Layer's tests need a real database.
- **Infrastructure independence**: the ORM (SQLAlchemy), the web framework (FastAPI), and the cache (Redis) can be swapped by changing the outer layers; the domain is unaffected.
- **Domain focus**: business logic lives in one place (the Domain Layer), not scattered across Controllers, ORM models, and service classes. The system's behavior is comprehensible by reading the domain.
- **Parallel development**: the API contract (ADR-0014) is designed first; the frontend builds against mocks while the backend implements the Application and Domain Layers; the Persistence Layer is added when the schema is finalized.
- **Clear ownership**: each layer has a single responsibility; code review focuses on whether code is in the right layer.
- **Future-proofing**: when a bounded context is extracted to a microservice (ADR-0001), the Domain and Application Layers move unchanged; only the API and Persistence Layers are re-wired.

---

## Cons

- **Boilerplate**: each use case has a Controller, an Application Service, Domain Service calls, and Repository calls. The boilerplate is real and adds lines of code.
- **Indirection**: a request flows through Controller → Application Service → Domain Service → Repository → database. Following the flow requires jumping between files.
- **Discipline required**: the rules are easy to violate (putting logic in a Controller, letting the domain import the ORM) and violations compound if not caught in review.
- **Over-engineering for simple CRUD**: for genuinely simple CRUD endpoints, the four layers are overkill. (Mitigated by allowing simple CRUD endpoints to skip the Domain Service layer when there is no business logic.)
- **Learning curve**: engineers unfamiliar with Clean Architecture need onboarding to the layering rules and the dependency direction.

---

## Consequences

- Every bounded context has four layers (API, Application, Domain, Persistence), organized as folders (ASD Section 10.1).
- Repository interfaces live in the Domain Layer; implementations live in the Persistence Layer.
- Domain Services are pure (no I/O); all I/O is in Application Services and Repositories.
- Controllers are thin (validate, call one Application Service method, serialize response).
- The DI container wires implementations to interfaces; tests substitute fakes.
- Linting rules forbid cross-layer imports (e.g., Domain Layer cannot import from Infrastructure).
- Code review checks layer placement: "is this code in the right layer?" is a standard review question.
- The architecture is documented in the ASD (Section 8, Section 10) and onboarding materials; new engineers learn the rules in their first week.

---

## Risks

- **Layer erosion**: engineers put logic in the wrong layer, and the discipline degrades over time. *Mitigation:* linting rules that forbid cross-layer imports; code review by the architecture review group; periodic architecture audits.
- **Over-application**: engineers apply the four layers to trivially simple code, adding boilerplate without benefit. *Mitigation:* the rules allow skipping the Domain Service layer when there is no business logic; code review flags unnecessary layers.
- **Indirection fatigue**: engineers find the indirection tedious and propose flattening. *Mitigation:* the architecture review group holds the line; the long-term benefits (testability, infrastructure independence) are documented and referenced.
- **Test discipline gap**: if tests do not actually substitute fakes (and instead use real databases), the testability benefit is lost. *Mitigation:* the test pyramid (ASD Section 14.4) specifies that unit tests use fakes; CI verifies that Domain Layer tests do not touch the database.

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Boilerplate overhead**: the team reports that the layering is slowing feature delivery by more than 20% (measured by cycle time), and the slowdown is attributed to layer boilerplate rather than to genuine complexity.
2. **Layer erosion beyond recovery**: a periodic architecture audit finds that more than 10% of code violates the dependency rules, indicating that the discipline is not sustainable.
3. **Extraction forces re-evaluation**: when a bounded context is extracted to a microservice (ADR-0001), the four-layer model may need adjustment for the extracted context (e.g., the API layer becomes a remote interface rather than a local one).

**Expected review action:** When any trigger fires, the architecture review group evaluates whether to relax the rules (allow more flexibility in specific contexts), to reinforce them (add tooling, training), or to adopt a different model for specific contexts. Clean Architecture is the default; deviations are per-context and documented in their own ADRs.

---

## Related ADRs

- **Depends on:** ADR-0001 (Modular Monolith) — the monolith's boundary discipline is enforced by Clean Architecture's layer rules.
- **Depends on:** ADR-0006 (Domain-Driven Design) — the Domain Layer's content (Aggregates, Value Objects, Domain Services) is shaped by DDD.
- **Informs:** ADR-0003 (FastAPI) — FastAPI is confined to the API Layer; the domain is framework-agnostic.

---

## Related Architecture Sections

- ASD Section 8 — API Architecture (layered overview).
- ASD Section 10 — Backend Architecture (layer responsibilities).
- ASD Section 10.1 — Layers (folder structure).
- ASD Section 14.1 — Coding Standards (SOLID, layer discipline).

---

## Related Glossary Terms

- Aggregate
- Entity
- Value Object
- Repository
- Application Service
- Domain Service
- Infrastructure Service
- Controller
- DTO

---

*End of ADR-0005.*
