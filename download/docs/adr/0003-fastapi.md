# ADR-0003 — Choose FastAPI for the Backend

---

## Title

Use FastAPI (Python) as the backend web framework for the Mastery Engine.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine backend serves an adaptive learning loop with a 200ms median latency target, hosts nine bounded contexts behind a clean-architecture layering, and must support the project's deterministic-first philosophy (no runtime AI for learning decisions). The backend framework is a foundational choice: it determines the language ecosystem, the typing discipline, the API contract mechanism, the testing patterns, and the operational characteristics of the system for years.

The project's stack (ASD Section 1.5) specifies Python as the backend language. This is driven by three factors: (1) Python's dominance in the educational and data-science ecosystems, which matters for a learning platform and for future ML work; (2) Python's strong typing via type hints and Pydantic, which satisfies the project's strong-typing requirement (ASD Section 14.1); (3) the team's existing Python expertise. Given Python as the language, the framework choice is among FastAPI, Django, and Flask, with Node.js frameworks (Express, NestJS) considered as a cross-language alternative.

The architecture specification (Task 001, Section 8) commits to a layered architecture: Controllers (thin, HTTP transport), Use Case Services (orchestration), Domain Services (pure business logic), and Repositories (persistence). The framework must support this layering without imposing its own opinions that conflict. The framework must also provide: async I/O for the learning loop's latency target, automatic OpenAPI generation for the API-first workflow (ADR-0014), request validation via Pydantic, and dependency injection for testability.

The Mastery Engine's runtime decision-making is deterministic (ASD Section 1.4); the framework's role is HTTP transport and orchestration, not business logic. This favors a framework that gets out of the way rather than one that imposes a worldview. The learning loop's latency target favors async I/O, since the loop's synchronous path touches multiple bounded contexts and any blocking I/O compounds.

---

## Problem Statement

What backend framework should the Mastery Engine use, given the requirements for async I/O, strong typing, automatic OpenAPI generation, Clean Architecture compatibility, dependency injection, and alignment with the project's Python-centric stack?

---

## Decision

We will use **FastAPI** as the backend web framework, running on Python 3.12+ with ASGI (Uvicorn or Hypercorn as the server). FastAPI is the HTTP transport layer; all business logic lives in Use Case Services and Domain Services that are framework-agnostic. FastAPI's `Depends` is used for dependency injection at the Controller boundary; below that, plain Python constructor injection is used.

We will use Pydantic v2 for all DTOs (Request, Response, Internal) and for configuration loading (Pydantic Settings). We will use FastAPI's automatic OpenAPI generation as the source of truth for the API contract (ADR-0014), with the frontend API client generated from the OpenAPI spec.

---

## Alternatives Considered

### Alternative A: Django (with Django REST Framework)

- **Description:** Django as the full-stack framework, with DRF for API endpoints.
- **Arguments in favor:**
  - Mature, batteries-included ORM, admin, auth, and migrations.
  - Large ecosystem and broad hire pool.
  - Strong conventions that accelerate greenfield development.
- **Arguments against:**
  - Synchronous by default; async support is improving but is not first-class. The learning loop's latency target is harder to meet with a sync framework that holds connections during I/O.
  - Django's ORM is opinionated and couples the domain model to the database schema; the project's Clean Architecture (ADR-0005) requires the domain to be ORM-agnostic, with SQLAlchemy or a custom mapper as the repository implementation.
  - Django's admin and auth are not needed (the project has its own Identity context and Admin Portal); pulling in Django for the framework while ignoring its batteries produces friction.
  - Django's settings and conventions impose a worldview that conflicts with the project's clean-architecture layering.
  - DRF's serializers overlap with Pydantic; using both produces confusion.
- **Why rejected:** The async limitation and the ORM coupling are decisive. The project's architecture requires a framework that gets out of the way; Django imposes too many of its own opinions. Django is an excellent choice for content-heavy, CRUD-oriented applications with sync I/O; it is not the best choice for a latency-critical, clean-architected, async-first system.

### Alternative B: Flask

- **Description:** Flask as a micro-framework, with extensions for ORM, auth, etc.
- **Arguments in favor:**
  - Minimal and unopinionated; gets out of the way.
  - Flexible; the team can structure the application as it sees fit.
  - Mature ecosystem of extensions.
- **Arguments against:**
  - Synchronous only; no native async support. This is a hard limitation for the latency target.
  - No built-in OpenAPI generation; requires a third-party extension (e.g., Flask-RESTX, apispec) that is less integrated than FastAPI's.
  - No built-in request validation via Pydantic; validation is bolted on.
  - No built-in dependency injection; the team would build it.
  - The "micro-framework" advantage is illusory for a production system: the team ends up assembling the equivalent of FastAPI from extensions, with less integration and more maintenance burden.
- **Why rejected:** The sync-only limitation is decisive. The lack of built-in OpenAPI and Pydantic integration means the team would rebuild what FastAPI provides for free. Flask is a fine choice for small services or for teams with specific reasons to avoid async; it is not the best choice for this project.

### Alternative C: Node.js with Express or NestJS

- **Description:** A Node.js backend using Express (minimal) or NestJS (opinionated, TypeScript-native).
- **Arguments in favor:**
  - TypeScript provides compile-time type safety across the entire stack; the frontend (Next.js, ADR-0004) and backend could share types.
  - Async-first (Node's event loop); excellent for I/O-bound workloads.
  - NestJS provides a clean-architecture-friendly module system.
  - Single language across the stack simplifies hiring and context-switching.
- **Arguments against:**
  - The project's stack (ASD Section 1.5) specifies Python for the backend, driven by the educational/data-science ecosystem and the team's expertise. Choosing Node.js would reverse that decision.
  - Python's dominance in future ML work (the Mastery Engine's ML integration, ASD Section 6.7) favors Python for the backend; a Node.js backend would require a separate Python service for ML, reintroducing the polyglot complexity this ADR's siblings avoid.
  - The Mastery Engine's domain logic (mastery computation, scheduling) is CPU-bound in places; Python's numerical ecosystem (NumPy, pandas) is more mature than Node's for the analytics and ML adjacency.
  - TypeScript's type system is stronger than Python's at the edges, but Pydantic + type hints is adequate for the project's needs.
- **Why rejected:** The stack decision (Python backend) is upstream of this ADR and is driven by the educational and ML ecosystem. Reversing it for a TypeScript backend would sacrifice the Python ecosystem's advantages for a marginal typing benefit. Node.js is a strong choice for I/O-bound backends; it is not the best choice for a system whose future includes Python-heavy ML and analytics.

---

## Pros

- **Async-native**: ASGI-based; the learning loop's I/O (database, cache, sandbox) is non-blocking, supporting the 200ms latency target.
- **Pydantic integration**: request validation, response serialization, and configuration loading all use Pydantic, eliminating the validation/serialization drift that plagues other frameworks.
- **Automatic OpenAPI generation**: the OpenAPI spec is generated from the route definitions and Pydantic models, making it the source of truth for the API contract (ADR-0014) with zero manual maintenance.
- **Dependency injection**: `Depends` provides a clean DI mechanism at the Controller boundary, supporting testability (fakes substitute real services).
- **Framework-agnostic domain**: FastAPI lives in the Controller layer; the domain layer is pure Python with no framework dependency, preserving Clean Architecture (ADR-0005).
- **Strong typing**: type hints throughout, with mypy/pyright enforcing type safety at CI time.
- **Python ecosystem**: access to the educational, data-science, and ML libraries that the project will need as it scales.
- **Performance**: FastAPI is among the fastest Python frameworks (on par with Node.js for many workloads) due to Starlette's ASGI foundation.
- **Active community and rapid evolution**: FastAPI is one of the fastest-growing Python frameworks; the project benefits from the ecosystem's momentum.

---

## Cons

- **Relative youth**: FastAPI is younger than Django or Flask; some edge cases (e.g., complex dependency lifecycles) are less explored. (Mitigated by the active community and the project's conservative use of FastAPI features.)
- **ORM-agnostic**: FastAPI does not include an ORM; the team must choose one (SQLAlchemy 2.0). This is a feature for Clean Architecture, but it is one more decision to make.
- **No admin interface**: Django's admin is genuinely useful for internal tooling; FastAPI has no equivalent. (Mitigated by the project's dedicated Admin Portal, ASD Section 2.11.)
- **Async ecosystem maturity**: some Python libraries (especially older ones) are sync-only, requiring `run_in_executor` or async alternatives. (Mitigated by choosing async-native libraries where possible: asyncpg, httpx, redis-py async.)
- **Python's GIL**: CPU-bound work (e.g., mastery recompute over large histories) is limited by the GIL within a single process. (Mitigated by scaling horizontally and by offloading CPU-bound work to background workers.)

---

## Consequences

- The team maintains FastAPI expertise; framework upgrades are tracked (FastAPI moves fast; minor versions may have breaking changes).
- SQLAlchemy 2.0 (or equivalent) is the ORM, used only in the repository layer; the domain layer has no ORM dependency.
- Pydantic v2 is the validation and serialization library everywhere; the team maintains Pydantic expertise (v2's API differs significantly from v1).
- The OpenAPI spec is generated at build time and committed to the repository; the frontend API client is generated from it (ADR-0014).
- ASGI server (Uvicorn or Hypercorn) is the production server; gunicorn with Uvicorn workers is a common production deployment.
- Background workers run the same FastAPI application's domain services but do not use the HTTP layer; they use the same DI container and the same repository implementations.
- The team must be disciplined about keeping business logic out of Controllers; FastAPI makes it easy to put logic in route handlers, and the team resists this via code review.

---

## Risks

- **Framework churn**: FastAPI evolves rapidly; breaking changes in minor versions could disrupt upgrades. *Mitigation:* pin FastAPI version; test upgrades in staging before production; follow the FastAPI changelog.
- **Pydantic v2 migration risk**: Pydantic v2's performance is much better than v1, but the API is different; libraries depending on v1 may need updates. *Mitigation:* use Pydantic v2 from the start; avoid libraries that depend on v1.
- **Async/sync impedance**: calling sync libraries from async code blocks the event loop; the team must identify and wrap or replace sync libraries. *Mitigation:* prefer async-native libraries (asyncpg, httpx, redis-py async); use `run_in_executor` for unavoidable sync calls; monitor event loop lag.
- **GIL ceiling**: CPU-bound mastery recompute could block the event loop if run in-process. *Mitigation:* CPU-bound work runs in background workers (separate processes), not in the API process; the API process is I/O-only.
- **Talent risk**: FastAPI expertise is growing but is less common than Django or Flask. *Mitigation:* FastAPI is easy to learn for Python engineers; the project's clean architecture means most of the codebase is plain Python, not FastAPI-specific.

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Latency regression**: the learning loop's p99 latency exceeds 500ms and profiling attributes it to FastAPI or ASGI overhead (unlikely but possible if the framework fails to scale).
2. **Framework abandonment**: FastAPI's maintenance slows significantly (no releases for 12+ months) or the project is forked/discontinued, threatening long-term support.
3. **ML integration friction**: the future ML Mastery Engine (ASD Section 6.7) requires a runtime that FastAPI cannot support (e.g., a model server with different latency characteristics), justifying a split backend.
4. **Type-safety ceiling**: the project's type-safety requirements exceed what Python + Pydantic can provide, and a TypeScript backend becomes attractive for end-to-end type safety.

**Expected review action:** When any trigger fires, the architecture review group evaluates alternatives (a different Python framework, a split backend with a Node.js or Go service for specific contexts, a full backend language migration). The evaluation produces a new ADR. A full backend language migration is the most expensive decision in the project's history and would require overwhelming justification; the team favors targeted splits (e.g., a Go service for the Sandbox) over wholesale migration.

---

## Related ADRs

- **Depends on:** ADR-0002 (PostgreSQL) — FastAPI's async story is best with asyncpg against PostgreSQL.
- **Depends on:** ADR-0005 (Clean Architecture) — FastAPI is confined to the Controller layer; the domain is framework-agnostic.
- **Informs:** ADR-0014 (API-first development) — FastAPI's OpenAPI generation is the source of truth for the API contract.
- **Related:** ADR-0004 (Next.js with TypeScript) — the frontend consumes FastAPI's OpenAPI spec.

---

## Related Architecture Sections

- ASD Section 1.5 — Why This Architecture Was Chosen (FastAPI rationale).
- ASD Section 8 — API Architecture (layered overview with FastAPI as the backend).
- ASD Section 10 — Backend Architecture (layer responsibilities).
- ASD Section 10.6 — Dependency Injection (FastAPI's `Depends` at the Controller boundary).

---

## Related Glossary Terms

- Controller
- Application Service
- Domain Service
- DTO
- Repository
- Dependency Injection

---

*End of ADR-0003.*
