# ADR-0014 — API-first Development

---

## Title

Adopt an API-first development workflow: design the API contract (OpenAPI) before implementing backend or frontend code; generate the frontend API client from the contract.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine has a React/Next.js frontend and a FastAPI backend, developed by a small team that will grow. The frontend and backend must agree on the API contract — the endpoints, request/response shapes, error codes, and authentication requirements. Without a single source of truth for the contract, the two sides drift: the backend changes an endpoint shape without updating the frontend, or the frontend calls an endpoint that doesn't exist, producing bugs that surface only at integration time.

The traditional approach — backend implements, frontend consumes, contract is implicit — produces these drift bugs and slows development. The team cannot afford this friction, especially as the team grows and the frontend and backend are worked on by different engineers simultaneously.

The architecture specification (Task 001, Section 8.2) commits to generating the frontend API client from the backend's OpenAPI spec, "so the frontend literally cannot call an endpoint the backend has not declared." This ADR formalizes the API-first workflow and the role of OpenAPI as the contract source of truth.

API-first means: the contract is designed and reviewed before implementation; the contract is the source of truth, not the implementation; the frontend and backend are both generated from the contract (the backend's structure is informed by the contract; the frontend's client is generated from it). Changes to the contract are deliberate, reviewed, and versioned.

---

## Problem Statement

How should the Mastery Engine manage the API contract between frontend and backend to prevent drift, enable parallel development, and maintain a single source of truth, given the FastAPI backend's OpenAPI generation capability and the Next.js frontend's TypeScript type requirements?

---

## Decision

We will adopt an **API-first development workflow** with OpenAPI as the contract source of truth.

- **Contract design before implementation**: an endpoint is designed (request DTO, response DTO, error codes, authentication) and reviewed before backend or frontend implementation begins. The design is captured in the backend's FastAPI route definitions and Pydantic models, which generate the OpenAPI spec.
- **OpenAPI as source of truth**: the OpenAPI spec, generated from the FastAPI code, is the contract. It is committed to the repository at build time. The frontend API client is generated from it. Manual edits to the generated client are forbidden.
- **Frontend client generation**: a code generator (e.g., openapi-typescript, orval, or a custom generator) produces a TypeScript client from the OpenAPI spec. The client is committed to the repository and regenerated whenever the spec changes. The frontend imports the generated client; it does not write manual fetch calls.
- **Parallel development**: once the contract is designed, the frontend builds against mock responses (derived from the spec) while the backend implements. Both sides converge on the same contract.
- **Contract versioning**: the API is versioned at the URL prefix (`/api/v1/...`). Breaking changes require a new major version; both versions run in parallel until the old one is deprecated. Non-breaking changes (additive fields, new endpoints) do not require a version bump.
- **Contract review**: changes to the contract (new endpoints, changed shapes) are reviewed by both frontend and backend engineers, ensuring the contract serves both sides.

---

## Alternatives Considered

### Alternative A: Backend-first (backend implements, frontend consumes)

- **Description:** The backend implements endpoints; the frontend reads the backend's code or tests against it to learn the contract.
- **Arguments in favor:**
  - Simpler process; no upfront contract design.
  - The backend is the source of truth (which it is, technically).
- **Arguments against:**
  - **Drift bugs**: the frontend calls an endpoint shape that the backend changed, producing runtime errors.
  - **No parallel development**: the frontend cannot start until the backend is implemented.
  - **No type safety**: the frontend's API calls are untyped (or manually typed), producing bugs that TypeScript cannot catch.
  - **Implicit contract**: the contract is implicit in the backend code, not documented; onboarding is harder.
- **Why rejected:** The drift bugs and the lack of parallel development are decisive. API-first eliminates both.

### Alternative B: Frontend-first (frontend defines the contract, backend implements to it)

- **Description:** The frontend team designs the API contract; the backend implements to it.
- **Arguments in favor:**
  - The contract serves the frontend's needs (which is the user's needs).
  - Parallel development is possible.
- **Arguments against:**
  - **Backend constraints ignored**: the frontend may design a contract that is expensive or awkward for the backend to implement (e.g., requiring a complex join that the backend's bounded contexts do not support).
  - **No single source of truth**: the contract lives in the frontend's design, not in the backend's code; drift is possible.
  - **Backend expertise underused**: the backend team knows the domain model and the persistence constraints; their input is needed in contract design.
- **Why rejected:** API-first (collaborative contract design with OpenAPI as source of truth) captures the frontend-first benefit (parallel development, user-serving contract) without the backend-constraint problem.

### Alternative C: GraphQL instead of REST + OpenAPI

- **Description:** Use GraphQL for the API, with the schema as the contract.
- **Arguments in favor:**
  - Flexible queries (the frontend fetches exactly what it needs).
  - Single endpoint (simpler routing).
  - Strong typing (GraphQL schema is typed).
- **Arguments against:**
  - **Operational complexity**: GraphQL servers are more complex to operate than REST; caching is harder (POST-based queries); rate limiting is more complex.
  - **Backend complexity**: the backend must resolve GraphQL queries, which can produce N+1 query problems without careful design (DataLoader, etc.).
  - **The project's stack (ASD Section 1.5) specifies REST**; GraphQL would reverse that.
  - **The learning loop's latency target** is easier to guarantee with REST endpoints (each with a clear latency budget) than with GraphQL queries (which can be arbitrarily complex).
  - **FastAPI's OpenAPI generation is a significant advantage** that GraphQL would not provide.
- **Why rejected:** The operational and backend complexity, combined with the stack decision (REST) and FastAPI's OpenAPI advantage, are decisive. GraphQL is a strong choice for APIs with diverse clients and flexible query needs; the Mastery Engine's API is for a single frontend and has well-defined query patterns, making REST the better fit.

### Alternative D: Manual contract (hand-written OpenAPI spec, no generation)

- **Description:** Write the OpenAPI spec by hand; generate backend stubs and frontend clients from it.
- **Arguments in favor:**
  - The spec is the source of truth, independent of backend or frontend.
  - Both sides generate from the spec.
- **Arguments against:**
  - **Spec drift from implementation**: the hand-written spec can diverge from the backend implementation (the backend's actual behavior differs from the spec), producing bugs.
  - **Maintenance burden**: the spec must be updated manually for every change, which is error-prone.
  - **FastAPI's generation capability is unused**: FastAPI generates a correct OpenAPI spec from the code for free; hand-writing duplicates this effort.
- **Why rejected:** The spec-drift risk and the duplication of FastAPI's generation capability are decisive. Generating the spec from the backend code (with contract design happening in the code via route definitions and Pydantic models) is more reliable and less effort.

---

## Pros

- **Single source of truth**: the OpenAPI spec, generated from the backend, is the contract. No drift between backend and frontend.
- **Type safety end-to-end**: the frontend's TypeScript types are generated from the spec, matching the backend's Pydantic models. TypeScript catches contract violations at compile time.
- **Parallel development**: once the contract is designed, frontend and backend develop in parallel against the same spec.
- **Fast iteration**: contract changes regenerate the frontend client automatically; no manual client updates.
- **Onboarding**: the OpenAPI spec is self-documenting; new engineers learn the API by reading the spec or the generated docs.
- **Contract review discipline**: changes to the contract are reviewed by both frontend and backend, producing a contract that serves both sides.
- **Versioning clarity**: the API is versioned at the URL prefix; breaking changes are deliberate and managed.
- **Testing**: contract tests (ASD Section 14.4) verify that the backend's responses match the spec, catching implementation drift.

---

## Cons

- **Contract design overhead**: designing the contract before implementation adds an upfront step. (This is a feature, not a bug — the upfront design catches issues before they are expensive to fix.)
- **Code generation complexity**: the frontend client generator must be configured and maintained. (Mitigated by the maturity of generators like openapi-typescript and orval.)
- **Generation friction**: regenerating the client is an extra step in the workflow. (Mitigated by automating regeneration in CI and pre-commit hooks.)
- **FastAPI spec limitations**: FastAPI's OpenAPI generation is excellent but has some limitations (e.g., complex generic types may not generate cleanly). (Mitigated by keeping DTOs simple and by manual OpenAPI annotations where needed.)

---

## Consequences

- Every API endpoint is designed (request DTO, response DTO, error codes, authentication) before implementation, in collaboration between frontend and backend.
- The OpenAPI spec is generated from the FastAPI code at build time and committed to the repository.
- The frontend API client is generated from the spec and committed to the repository; manual edits are forbidden.
- The frontend imports the generated client; manual fetch calls are forbidden.
- Contract changes are reviewed by both frontend and backend engineers.
- The API is versioned at the URL prefix (`/api/v1/...`); breaking changes require a new major version.
- Contract tests verify that the backend's responses match the spec.
- The OpenAPI spec is published as API documentation (auto-generated docs UI, e.g., Swagger UI or ReDoc).
- The glossary (Task 002) defines DTO, Request DTO, Response DTO, and related terms; the Naming Standards govern endpoint and DTO naming.

---

## Risks

- **Spec generation bugs**: FastAPI's OpenAPI generation produces an incorrect spec (e.g., a complex type is not represented correctly), causing the generated client to be wrong. *Mitigation:* contract tests verify the spec matches the implementation; complex types are avoided or manually annotated.
- **Client generation bugs**: the frontend client generator produces incorrect TypeScript (e.g., a type is wrong), causing frontend bugs. *Mitigation:* the generator is tested; generated code is reviewed on first generation and on generator upgrades.
- **Contract review bottleneck**: contract reviews slow development if the review group is not responsive. *Mitigation:* contract reviews are prioritized; the review group has a documented SLA.
- **Spec drift between versions**: the v1 and v2 specs diverge, producing maintenance burden. *Mitigation:* v1 is deprecated on a documented schedule; v2 is the focus; v1 receives only critical fixes.
- **Over-engineering the contract**: the contract design step becomes heavyweight, slowing feature delivery. *Mitigation:* contract design is lightweight (a route definition and DTOs); the step is not a formal document but a code review.

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Contract complexity**: the API grows to hundreds of endpoints, making the OpenAPI spec unwieldy and the generated client large, justifying splitting the API into multiple specs (e.g., per bounded context).
2. **GraphQL demand**: a future feature (e.g., a customizable dashboard that fetches diverse data) makes GraphQL's flexible queries significantly more efficient than REST.
3. **Multi-client demand**: a future mobile app or partner integration requires a different API shape, justifying a separate contract.
4. **Generation tooling obsolescence**: the OpenAPI generation or client generation tooling is no longer maintained, requiring a change.

**Expected review action:** When any trigger fires, the architecture review group evaluates the contract strategy change. Splitting the API into multiple specs is a moderate change; switching to GraphQL is a significant change requiring a new ADR and a migration plan.

---

## Related ADRs

- **Depends on:** ADR-0003 (FastAPI) — FastAPI's OpenAPI generation is the source of truth.
- **Depends on:** ADR-0004 (Next.js with TypeScript) — the frontend consumes the generated TypeScript client.
- **Informs:** ADR-0015 (Documentation-first workflow) — the API contract is designed before implementation, as part of the documentation-first philosophy.

---

## Related Architecture Sections

- ASD Section 8.2 — Frontend Boundary (frontend communicates through the documented API surface).
- ASD Section 8.4 — DTOs and Validation (Pydantic-everywhere).
- ASD Section 8.8 — API Versioning.
- ASD Section 14.4 — Testing Philosophy (contract tests).

---

## Related Glossary Terms

- DTO
- Request DTO (referenced in glossary)
- Response DTO (referenced in glossary)
- Controller
- Command
- Query
- REST Resources (referenced in Naming Standards)

---

*End of ADR-0014.*
