# ADR-0015 — Documentation-first Workflow

---

## Title

Complete architecture, glossary, ADRs, API contracts, and database design before feature implementation; maintain documentation as a first-class artifact throughout the project's life.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine is designed to be maintained for a decade or more. Over that horizon, the founding team will turn over, memories will fade, and the rationale behind decisions will be lost unless it is written down. The project has already produced three foundational documents — the Architecture Specification Document (Task 001), the Ubiquitous Language & Domain Glossary (Task 002), and this ADR repository (Task 003) — before any feature implementation. This is not an accident; it is a deliberate workflow choice.

The temptation, especially under investor or market pressure, is to "just start coding" and document later. This temptation is strong because documentation feels like non-progress while code feels like progress. The reality is the opposite: undocumented code produces rework, drift, and onboarding friction that cost far more than the documentation would have. The project's documentation-first workflow is the discipline that prevents this.

The architecture specification (Task 001, Section 14.5) commits to documentation standards: docstrings, module-level documentation, ADRs, OpenAPI, READMEs, and runbooks. This ADR formalizes the broader workflow: documentation is completed before implementation, not after; documentation is maintained as the system evolves; documentation is reviewed with the same rigor as code.

---

## Problem Statement

What workflow should the Mastery Engine adopt to ensure that documentation is a first-class artifact, completed before implementation and maintained throughout the system's life, given the project's decade-long lifespan and the cost of undocumented decisions?

---

## Decision

We will adopt a **documentation-first workflow** with the following commitments:

1. **Architecture before implementation**: the Architecture Specification Document is the source of truth for the system's architecture. Feature implementation conforms to it; changes to it require a new ADR. The ASD is completed (as it now is) before feature implementation begins.

2. **Ubiquitous language before code**: the Ubiquitous Language & Domain Glossary is the source of truth for terminology. Code, schema, UI, and documentation use the glossary's terms. The glossary is completed (as it now is) before feature implementation begins. New terms require a glossary change request.

3. **ADRs before irreversible decisions**: every irreversible architectural decision is captured in an ADR before the decision is implemented. The ADR is reviewed and Accepted before the implementation PR is merged. The ADR repository (this directory) is the permanent architectural memory.

4. **API contracts before endpoint implementation**: the API contract (OpenAPI spec, generated from FastAPI) is designed and reviewed before backend or frontend implementation of an endpoint (per ADR-0014). The contract is the source of truth; the implementation conforms to it.

5. **Database design before schema implementation**: the database schema is designed (tables, indexes, partitioning, relationships) before migration code is written. The schema design is reviewed by the architecture review group. (This will be formalized in a future Database Design document, produced before Phase 1 implementation.)

6. **Documentation maintained as the system evolves**: documentation is not a one-time artifact. When the system changes, the documentation changes with it, in the same PR. A PR that changes behavior without updating documentation is incomplete and is not merged.

7. **Documentation reviewed with code**: documentation is reviewed in code review with the same rigor as code. A PR with misleading or missing documentation is rejected.

8. **Documentation as onboarding**: new engineers are onboarded via the documentation (ASD, glossary, ADRs, API contract, runbooks). The documentation's quality is measured by how quickly a new engineer can become productive without asking the founders.

---

## Alternatives Considered

### Alternative A: Code-first, document-later

- **Description:** Implement features first; document later when there is time.
- **Arguments in favor:**
  - Faster perceived progress (code ships sooner).
  - No upfront documentation cost.
- **Arguments against:**
  - **Documentation never happens**: "later" never comes; the team is always under pressure to ship the next feature.
  - **Drift**: undocumented decisions are forgotten; the implementation drifts from the intent; rework accumulates.
  - **Onboarding failure**: new engineers cannot understand the system without asking the founders, who become a bottleneck.
  - **Decision re-litigation**: without ADRs, the team re-decides the same issues every six months.
  - **The project's decade-long lifespan makes this approach fatal**: a system maintained for a decade without documentation becomes unmaintainable.
- **Why rejected:** The long-term cost is decisive. The documentation-first workflow is the insurance that keeps the system maintainable over its lifespan.

### Alternative B: Documentation alongside code (agile documentation)

- **Description:** Write documentation in parallel with code, in the same PRs.
- **Arguments in favor:**
  - Documentation is always current (it ships with the code).
  - No upfront documentation phase.
- **Arguments against:**
  - **No big-picture design**: without upfront architecture and glossary, the team codes without a shared understanding, producing inconsistency.
  - **ADRs become after-the-fact rationalizations**: if the ADR is written after the decision, it documents what was done rather than why it was chosen, losing the alternatives-considered analysis.
  - **The founding documents (ASD, glossary) cannot be written alongside code**: they must exist before code, because they shape the code.
- **Why rejected:** The founding documents must be upfront; they cannot be written alongside code. For ongoing changes, documentation-alongside-code is the correct approach (commitment 6 above), but it is not a substitute for the upfront founding documents.

### Alternative C: External documentation team

- **Description:** A separate documentation team writes and maintains documentation; engineers focus on code.
- **Arguments in favor:**
  - Engineers are not distracted by documentation.
  - Documentation is written by specialists.
- **Arguments against:**
  - **Knowledge transfer bottleneck**: the documentation team must interview engineers to write documentation, which is slower and less accurate than engineers writing it directly.
  - **Drift**: the documentation team is not in the code; their documentation drifts from the implementation.
  - **Cost**: a separate documentation team is expensive; the project's size does not justify it.
  - **Engineer ownership**: engineers who write documentation own the system's understanding; outsourcing this produces engineers who do not understand their own system.
- **Why rejected:** Documentation is an engineering responsibility, not a separate team's. The documentation-first workflow commits engineers to writing and maintaining documentation as part of their work.

---

## Pros

- **Foundational clarity**: the ASD, glossary, and ADRs provide a shared understanding before code is written, producing consistency.
- **Decision permanence**: ADRs capture decisions and their rationale, preventing re-litigation.
- **Onboarding speed**: new engineers become productive via documentation, without founder bottleneck.
- **Drift prevention**: documentation maintained with code keeps the system's understanding current.
- **Long-term maintainability**: a decade-long lifespan requires documentation; the workflow ensures it exists.
- **Review rigor**: documentation reviewed with code catches misunderstandings early.
- **Knowledge distribution**: documentation distributes knowledge across the team, reducing bus factor.

---

## Cons

- **Upfront cost**: the founding documents (ASD, glossary, ADRs) are a significant upfront investment. (This is a feature; the investment pays back over the system's life.)
- **Ongoing discipline**: maintaining documentation with every PR is discipline that engineers must be held to. (Mitigated by code review and by the cultural norm that "undocumented code is incomplete code.")
- **Documentation overhead**: some documentation (e.g., a one-line endpoint) feels like overhead. (Mitigated by right-sizing the documentation to the change; not every change needs an ADR.)
- **Risk of over-documentation**: the team over-documents trivial changes, producing noise. (Mitigated by the ADR trigger criteria in the README; not every decision needs an ADR.)

---

## Consequences

- The ASD, glossary, and ADR repository are completed before Phase 1 feature implementation (they now are).
- A Database Design document is produced before schema implementation (a future task).
- API contracts are designed before endpoint implementation (per ADR-0014).
- Every PR that changes behavior includes documentation updates; PRs without documentation updates are rejected.
- ADRs are written before irreversible decisions are implemented; the ADR is Accepted before the implementation PR is merged.
- The glossary is maintained as a living document; new terms require a glossary change request.
- Code review includes documentation review; reviewers check that documentation is accurate and complete.
- New engineers are onboarded via the documentation; onboarding effectiveness is measured (time-to-first-PR, time-to-independent-contribution).
- The documentation's quality is a tracked metric; periodic audits verify accuracy.

---

## Risks

- **Documentation staleness**: documentation drifts from the implementation if PRs do not update it. *Mitigation:* code review rejects PRs with stale documentation; periodic audits verify accuracy; documentation is treated as code (versioned, reviewed, tested where possible).
- **Documentation overhead fatigue**: engineers feel the documentation burden is too high and push back. *Mitigation:* right-size documentation to the change; not every change needs an ADR; the ADR trigger criteria in the README are clear.
- **Over-documentation**: the team over-documents trivial changes, producing noise that obscures important documentation. *Mitigation:* the ADR trigger criteria; documentation right-sizing; the architecture review group coaches.
- **Founder bottleneck on documentation**: the founders write all the documentation, becoming a bottleneck. *Mitigation:* documentation is an engineering responsibility; all engineers write and review documentation; the founders' role is review, not authorship, of most documentation.
- **Documentation as theater**: documentation is written to satisfy the process but is not maintained, becoming useless. *Mitigation:* documentation is reviewed with code; stale documentation is a bug; the cultural norm is "documentation is part of the work."

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Documentation drift**: a periodic audit finds that more than 10% of documentation is stale (does not match the implementation), indicating that the workflow is not being followed.
2. **Onboarding failure**: new engineers report that the documentation is not sufficient for them to become productive, indicating that the documentation is incomplete or inaccurate.
3. **Documentation overhead**: the team reports that documentation is slowing feature delivery by more than 20% (measured by cycle time), indicating that the workflow is too heavyweight.
4. **ADRs not being written**: irreversible decisions are being made without ADRs, indicating that the ADR process is not being followed.
5. **Glossary drift**: engineers use terms not in the glossary, or use glossary terms incorrectly, indicating that the glossary needs reinforcement or revision.

**Expected review action:** When any trigger fires, the architecture review group evaluates the workflow. Drift and onboarding failure trigger reinforcement (training, audits, process tightening). Overhead triggers right-sizing (relaxing the workflow for trivial changes). ADR and glossary drift trigger process reinforcement. The documentation-first principle is the default; deviations require strong justification.

---

## Related ADRs

- **Depends on:** ADR-0001 through ADR-0014 — all prior ADRs are products of the documentation-first workflow.
- **Informs:** All future ADRs — the documentation-first workflow governs how future decisions are captured.

---

## Related Architecture Sections

- ASD Section 14.5 — Documentation Standards (docstrings, ADRs, OpenAPI, READMEs, runbooks).
- ASD Section 14.7 — Pull Request Requirements (documentation updates required).
- ASD Section 14.8 — Code Review Culture (documentation review).

---

## Related Glossary Terms

- Ubiquitous Language
- Architecture Decision Record
- Bounded Context
- Aggregate
- DTO
- Audit Log

---

*End of ADR-0015.*
