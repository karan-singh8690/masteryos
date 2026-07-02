# ADR-0010 — Subject-agnostic Architecture

---

## Title

Implement Python (and all future Subjects) as content within a Subject-agnostic core engine, not as business logic.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine's first Subject is Python Technical Interview Preparation. The architecture specification (Task 001, Section 1.1) states that the system is designed so that additional Subjects (SQL, Java, Cybersecurity, Cloud, IELTS) can be onboarded without rewriting the core engine. This is not a casual aspiration; it is a foundational architectural commitment that shapes every decision about the domain model.

The temptation, when building for a single Subject, is to bake Subject-specific concepts into the core. "A Concept has a PythonDifficulty" or "A QuestionTemplate has a CodeExecutionType" would be natural choices for a Python-only system. But these choices create a core that is Python-shaped, and onboarding a second Subject (e.g., SQL, which has no code execution but has query execution) requires either forking the core or polluting it with Subject-specific conditionals. Either outcome destroys the architecture's longevity.

The Subject-agnostic principle is: the core domain (Concept, Learning Objective, Misconception, Question Template, Attempt, Mastery Score, Scheduler) is defined without reference to any specific Subject. A Subject is a content bundle — a populated Knowledge Graph, a set of Question Templates, a set of Misconceptions — not a code path. Adding a Subject is an authoring exercise, not an engineering one.

The architecture specification (Section 1.5) commits to this: "Concepts, Mastery Scores, Attempts, and Schedulers are defined without reference to Python; Python enters the system only as a populated subject graph and a set of question templates." This ADR formalizes the commitment and the rules that enforce it.

---

## Problem Statement

How should the Mastery Engine's core domain be designed to accommodate multiple Subjects (Python, SQL, Java, Cybersecurity, Cloud, IELTS) without code changes or forking, given that each Subject has different question types, different execution models, and different pedagogical conventions?

---

## Decision

We will implement a **Subject-agnostic core**. The core domain — Concept, Learning Objective, Misconception, Question Template, Question Instance, Attempt, Mastery Score, Review, Scheduler, Mastery Engine — is defined without reference to any specific Subject. A Subject is a content bundle: a populated Knowledge Graph, a set of Question Templates, a set of Misconceptions, and a Learning Path. Adding a Subject is an authoring exercise (populating the content bundle via the Content Pipeline, ADR-0009), not an engineering exercise.

**Subject-specific behavior is configured, not coded.** Where a Subject requires specific behavior (e.g., Python requires code execution; SQL requires query execution; IELTS requires free-response scoring), the behavior is implemented as a pluggable component (an Answer Evaluator, a Sandbox Runtime) that is configured per Subject, not as a conditional in the core. The core defines the interface (e.g., `AnswerEvaluator`); the Subject-specific implementation (e.g., `PythonCodeEvaluator`, `SQLQueryEvaluator`) is registered for that Subject.

**The Subject entity** (ASD Section 4.4) owns its content graph and its Subject-specific configuration. The Subject is the unit at which Subject-specific behavior is configured. The core engine reads the Subject's configuration and dispatches to the appropriate pluggable component.

---

## Alternatives Considered

### Alternative A: Python-specific core, refactored for each new Subject

- **Description:** Build a Python-specific core first; refactor when adding a second Subject.
- **Arguments in favor:**
  - Faster to launch (no abstraction cost).
  - Simpler code (no pluggable interfaces).
- **Arguments against:**
  - **Refactoring cost**: the refactoring to add a second Subject is a multi-quarter project that touches every core entity. The team will be under pressure to ship the second Subject, producing a rushed refactoring that introduces bugs.
  - **Abstraction debt**: Python-specific assumptions leak into the core (e.g., "a Question has a function signature"), and removing them later is harder than abstracting upfront.
  - **Forking risk**: under pressure, the team may fork the core for the second Subject rather than refactoring, producing two divergent cores that are expensive to maintain.
  - **The architecture's longevity claim is broken**: the ASD promises Subject-agnosticity; a Python-specific core breaks that promise.
- **Why rejected:** The refactoring cost and the forking risk are decisive. The abstraction cost of Subject-agnosticity upfront is modest (defining interfaces instead of concrete classes); the cost of refactoring later is large. The upfront investment is justified.

### Alternative B: Subject-specific microservices per Subject

- **Description:** Each Subject is a separate service with its own codebase, sharing only the database schema.
- **Arguments in favor:**
  - Maximum per-Subject flexibility.
  - No abstraction needed; each Subject's service is custom.
- **Arguments against:**
  - **Operational explosion**: N Subjects means N services to operate, monitor, and upgrade.
  - **Code duplication**: the mastery model, the scheduler, the learning loop are duplicated across N services, producing drift and inconsistency.
  - **Cross-Subject features**: a Learner studying both Python and SQL cannot get a unified view of their progress without a separate aggregation service.
  - **The Mastery Engine's competitive advantage is the core algorithm**: duplicating it across N services means N versions of the algorithm, with no guarantee they are consistent.
- **Why rejected:** The operational cost and the algorithm-duplication risk are decisive. Subject-agnosticity is the project's core architectural commitment; this alternative abandons it.

### Alternative C: Subject-agnostic core with Subject-specific code paths (conditionals)

- **Description:** A single core codebase with `if subject == "python"` conditionals at key decision points.
- **Arguments in favor:**
  - Single codebase (no service explosion).
  - Subject-specific behavior is explicit.
- **Arguments against:**
  - **Conditional explosion**: as Subjects are added, conditionals multiply, producing code that is hard to read and hard to test.
  - **Coupling**: each Subject's behavior is coupled to every other Subject's behavior through the shared conditionals; a change for one Subject risks breaking another.
  - **Open-closed principle violation**: the core is open to modification (adding conditionals) rather than open to extension (adding pluggable components).
- **Why rejected:** The conditional-explosion and coupling problems are decisive. The pluggable-component approach (the Decision) achieves the same per-Subject flexibility without the conditionals.

---

## Pros

- **Subject onboarding without code changes**: adding SQL, Java, or Cybersecurity is an authoring exercise (populating the content bundle and registering pluggable components), not an engineering exercise.
- **Core algorithm consistency**: the Mastery Engine and the Scheduler are shared across all Subjects; a Learner's experience is consistent; algorithm improvements benefit all Subjects.
- **Cross-Subject features**: a Learner studying multiple Subjects gets a unified view (one Mastery Engine, one Scheduler, one Progress page) without aggregation.
- **Testability**: the core is tested without Subject-specific fixtures; Subject-specific components are tested in isolation.
- **Longevity**: the architecture's promise of a decade-long lifespan depends on Subject-agnosticity; this decision honors that promise.
- **Competitive advantage**: the core algorithm is the product's moat; centralizing it (rather than duplicating per Subject) preserves the moat.

---

## Cons

- **Abstraction cost**: the core uses interfaces (e.g., `AnswerEvaluator`) instead of concrete classes; engineers must understand the interface and the registered implementation.
- **Configuration complexity**: Subject-specific behavior is configured (registered pluggable components) rather than coded; the configuration must be documented and tested.
- **Cold-start for new Subjects**: a new Subject requires not just content authoring but also implementation of pluggable components (e.g., a new `AnswerEvaluator` for SQL query execution). This is less work than refactoring the core, but it is work.
- **Interface design discipline**: the core's interfaces must be designed carefully to accommodate future Subjects without breaking existing ones. (Mitigated by interface versioning and by the ADR process for interface changes.)

---

## Consequences

- The core domain (Concept, Learning Objective, Misconception, Question Template, Question Instance, Attempt, Mastery Score, Review, Scheduler, Mastery Engine) is defined without Subject-specific fields or methods.
- Subject-specific behavior is implemented as pluggable components behind interfaces: `AnswerEvaluator`, `SandboxRuntime`, `ExplanationRenderer`. Each Subject registers its implementations.
- The Subject entity (ASD Section 4.4) owns its content graph and its Subject-specific configuration (registered components).
- Adding a Subject is a documented process: author the content bundle (Concepts, Objectives, Misconceptions, Templates) via the Content Pipeline (ADR-0009); implement and register any Subject-specific pluggable components; configure the Subject; publish.
- The Python Subject's code-execution feature is implemented as a `PythonCodeEvaluator` and a `PythonSandboxRuntime`, registered for the Python Subject — not as conditionals in the core.
- Future Subjects (SQL, Java, Cybersecurity) follow the same pattern: author content; implement pluggable components if needed; register; publish.
- The glossary (Task 002) defines Subject, Tenant, and the Subject-agnostic core terms; the Naming Standards ensure no Subject-specific names leak into the core.
- Code review enforces Subject-agnosticity: a PR that adds a Subject-specific field to a core entity is rejected; the PR must instead add a pluggable component or a Subject-specific configuration.

---

## Risks

- **Interface design errors**: a core interface (e.g., `AnswerEvaluator`) is designed for Python and does not accommodate a future Subject (e.g., IELTS free-response scoring). *Mitigation:* interfaces are designed conservatively (minimal, generic); interface changes are versioned and governed by ADRs; the cold-start for new Subjects includes interface review.
- **Subject-specific configuration drift**: Subject-specific configuration becomes inconsistent across Subjects (e.g., Python registers an `AnswerEvaluator` but SQL does not, producing a runtime error). *Mitigation:* configuration is validated at Subject publish time; missing required components are rejected.
- **Pluggable component quality divergence**: a Subject's pluggable component (e.g., the `PythonSandboxRuntime`) is lower quality than the core, degrading the Subject's experience. *Mitigation:* pluggable components are subject to the same testing and review standards as the core; Quality Metrics (ASD Section 7.10) measure per-Subject quality.
- **Core pollution under pressure**: under deadline pressure, engineers add Subject-specific conditionals to the core rather than implementing pluggable components. *Mitigation:* code review enforces Subject-agnosticity; the architecture review group audits for conditionals.
- **Subject onboarding underestimated**: the team underestimates the work to onboard a second Subject (content authoring is significant; pluggable components may be needed), producing schedule slippage. *Mitigation:* the Subject onboarding process is documented; the first new Subject onboarding produces a checklist that future onboardings follow.

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Interface inadequacy**: a new Subject cannot be onboarded without modifying a core interface, indicating that the interface is too Python-specific and must be generalized (via a new ADR).
2. **Core pollution**: a periodic audit finds Subject-specific conditionals in the core, indicating that the Subject-agnostic discipline is eroding.
3. **Pluggable component duplication**: multiple Subjects implement near-identical pluggable components (e.g., Python and Java both need code execution), indicating that the abstraction level is wrong and a higher-level shared component is needed.
4. **Subject-specific feature demand**: a Subject requires a feature that the Subject-agnostic core cannot accommodate (e.g., a Subject with collaborative learning), justifying a core extension via a new ADR.

**Expected review action:** When any trigger fires, the architecture review group evaluates the interface change, the core cleanup, the shared-component extraction, or the core extension. Any change to the core's Subject-agnosticity is a significant decision requiring a new ADR. The Subject-agnostic principle is the default; deviations require overwhelming justification.

---

## Related ADRs

- **Depends on:** ADR-0006 (Domain-Driven Design) — the bounded contexts (especially Content, Mastery, Scheduling) are the Subject-agnostic core.
- **Depends on:** ADR-0009 (Human-authored curriculum) — Subject onboarding is an authoring exercise, governed by the Content Pipeline.
- **Informs:** ADR-0011 (Triple Versioning) — Content Versions are per-Subject; the core is versioned independently.

---

## Related Architecture Sections

- ASD Section 1.1 — Product Purpose (Subject-agnostic core, first tenant Python).
- ASD Section 1.5 — Why This Architecture Was Chosen (Subject-agnostic core with Subject-tenant configuration).
- ASD Section 4.4 — Content Context (Subject entity).
- ASD Section 7 — Content Pipeline (Subject onboarding via the pipeline).

---

## Related Glossary Terms

- Subject
- Tenant
- Concept
- Question Template
- Content Version
- Knowledge Graph
- Learning Path

---

*End of ADR-0010.*
