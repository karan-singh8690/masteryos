# Architecture Decision Records (ADR)

> **Status:** Living document — the permanent architectural memory of the Mastery Engine project.
> **Owner:** Principal Architect
> **Audience:** All engineers, present and future.
> **Companion documents:** Architecture Specification Document (Task 001), Ubiquitous Language & Domain Glossary (Task 002).

---

## What is an ADR?

An **Architecture Decision Record** (ADR) is a short, immutable document that captures one architectural decision: the context in which it was made, the alternatives considered, the decision itself, and the consequences of living with it. ADRs are the institutional memory of an engineering organization. They exist so that the answer to "why did we choose this?" is never "I don't know, someone decided it before I joined."

The Mastery Engine project adopts ADRs because the system is designed to be maintained for a decade or more. Over that horizon, the founding team will turn over, memories will fade, and the rationale behind irreversible decisions will be lost unless it is written down. An ADR is the cheapest form of insurance against that loss: a few hours of writing saves years of confusion and prevents the team from re-litigating decisions every six months.

An ADR is **not** a design document. A design document describes how a system will be built; an ADR records why a particular approach was chosen. An ADR is **not** a ticket. A ticket tracks work; an ADR records a decision. An ADR is **not** a RFC. An RFC is a proposal seeking feedback; an ADR is the record of a decision that has been made. The Mastery Engine uses all three artifacts for different purposes, and conflating them produces noise.

The relationship between this ADR repository and the Architecture Specification Document (Task 001) is worth being explicit about. The ASD describes the **current state** of the architecture — what the system is. ADRs describe the **decision history** — how the system came to be and why each irreversible choice was made. The ASD references ADRs; ADRs reference the ASD. When the ASD is updated to reflect a new decision, a new ADR is created first, and the ASD update references it.

---

## When to Create a New ADR

A new ADR should be created whenever a decision is **irreversible or expensive to reverse**. The test is not "is this decision important?" — that is too subjective. The test is "would reversing this decision require rewriting more than one bounded context, migrating data, or breaking the API contract?" If the answer is yes, the decision warrants an ADR.

Concrete triggers that require an ADR:

- Choosing or changing a primary database, message broker, or cache.
- Choosing or changing the backend framework, frontend framework, or language.
- Adopting or removing a bounded context.
- Changing the authentication mechanism, authorization model, or secrets management approach.
- Changing the deployment topology (monolith to microservices, single-region to multi-region).
- Adopting a new architectural pattern (event sourcing, CQRS, saga) or removing one.
- Changing the API versioning strategy, the API contract, or the OpenAPI generation approach.
- Changing the testing strategy at the architectural level (property-based, contract, load).
- Decisions about data ownership, data residency, or data retention that affect multiple contexts.
- Decisions about the learning loop, the mastery model, or the scheduling algorithm.
- Any decision referenced as a Future Review Trigger in an existing ADR that has now been activated.

Decisions that do **not** require an ADR:

- Choosing a library within an already-chosen ecosystem (e.g., which Pydantic version).
- Internal class design within a single bounded context.
- Bug fixes, refactors, and performance optimizations that do not change the architecture.
- Feature additions that fit within the existing architecture.
- Operational choices (e.g., which CI provider) that are easily reversible.

When in doubt, write the ADR. The cost of an unnecessary ADR is a few hours of writing; the cost of a missing ADR is years of confusion.

---

## ADR Lifecycle

Every ADR moves through a defined lifecycle. The lifecycle is enforced by the ADR process; an ADR that skips a state is invalid.

### Lifecycle States

```
Proposed ──accept──▶ Accepted ──supersede──▶ Superseded
    │                    │
    │                  deprecate
    │                    │
    │                    ▼
    │               Deprecated
    │
    reject
    │
    ▼
Rejected
```

**Proposed** — The ADR has been drafted and submitted for review. It is not yet binding. Engineers may reference it to understand the proposal, but no implementation should proceed on the assumption that it will be accepted. A Proposed ADR that lingers without review for more than two weeks is either promoted to Accepted or demoted to Rejected; the architecture review group is responsible for not letting proposals stall.

**Accepted** — The ADR has been reviewed and approved. The decision is binding. All implementation must conform to it. The ASD is updated to reference the ADR. An Accepted ADR is **immutable**: its content does not change after acceptance. Corrections are made by superseding the ADR with a new one.

**Deprecated** — The ADR is no longer recommended, but no replacement has been chosen. This is an unusual state, used when a decision is recognized as wrong but the team has not yet decided what to do instead. A Deprecated ADR carries a deprecation notice explaining why it was deprecated and what the team plans to do. Implementation should not follow a Deprecated ADR.

**Superseded** — The ADR has been replaced by a newer ADR. The newer ADR's number is recorded in the superseded ADR's status line. The superseded ADR remains in the repository for historical reference; it is never deleted. Supersession is the only mechanism for changing a binding architectural decision.

**Rejected** — The ADR was proposed and explicitly rejected. The rejection reason is recorded in the ADR. A Rejected ADR remains in the repository so that future engineers understand the decision was considered and turned down, preventing re-proposal of the same idea without new context.

### Transitions

- **Proposed → Accepted**: the architecture review group approves.
- **Proposed → Rejected**: the architecture review group rejects, with reason.
- **Accepted → Superseded**: a new ADR is Accepted that replaces this one.
- **Accepted → Deprecated**: the team recognizes the decision is wrong but has no replacement yet.
- **Deprecated → Superseded**: a replacement ADR is Accepted.
- **Superseded → (no further transitions)**: a Superseded ADR is frozen.
- **Rejected → (no further transitions)**: a Rejected ADR is frozen. If the idea is revived later, a new ADR is created that references the rejected one.

No ADR is ever deleted. The repository is append-only in the sense that ADRs accumulate; even Rejected and Superseded ADRs remain, because the history of what was considered and rejected is as valuable as the history of what was accepted.

---

## ADR Numbering Convention

ADRs are numbered sequentially starting at 0001. The number is assigned when the ADR is first Proposed and never changes, even if the ADR is later Rejected or Superseded. Numbers are not reused.

The four-digit zero-padded format (`0001`, `0002`, ... `9999`) is used for sort order in file listings and to make references unambiguous (`ADR-0007` is clearer than `ADR-7`). The project will not reach 9999 ADRs; if it does, the format extends to five digits without disruption.

The template file is `0000-template.md`. The number 0000 is reserved for the template and is never used for a real ADR.

Filenames follow the convention `NNNN-kebab-case-short-title.md`. Examples: `0001-modular-monolith.md`, `0007-deterministic-scheduling-before-ml.md`. The short title is descriptive but not the full ADR title (which appears inside the document). Filenames are lowercase kebab-case; the ADR title inside the document is Title Case.

When an ADR supersedes another, the superseding ADR gets the next available number; it does not reuse the superseded ADR's number. For example, if ADR-0002 is superseded, the superseding ADR might be ADR-0042 (the next available number at the time), and ADR-0002's status line reads "Superseded by ADR-0042."

---

## ADR Status Values — Quick Reference

| Status | Meaning | Implementation follows it? | Mutable? |
|---|---|---|---|
| **Proposed** | Drafted, under review | No | Yes (the draft may evolve during review) |
| **Accepted** | Approved, binding | Yes | No (immutable; supersede to change) |
| **Deprecated** | No longer recommended; no replacement yet | No | No (frozen at deprecation) |
| **Superseded** | Replaced by a newer ADR | No (follow the superseding ADR) | No (frozen) |
| **Rejected** | Considered and turned down | No | No (frozen) |

---

## How to Write an ADR

Use the template at `0000-template.md`. Copy it to `NNNN-kebab-case-short-title.md`, fill in every section, and submit a pull request. The architecture review group reviews the PR; approval transitions the ADR from Proposed to Accepted.

Every section of the template is mandatory. If a section does not apply, write "Not applicable" and explain why — do not omit the section. The discipline of filling in every section forces the author to consider every angle, which is the point of the exercise.

The most important section is **Alternatives Considered**. An ADR without alternatives is not a decision; it is a rationalization. If only one option was considered, the decision was not really a decision, and an ADR is unnecessary. Document at least two genuine alternatives, explain why each was rejected, and name the trade-off that made the chosen option win.

The second most important section is **Future Review Trigger**. This is the condition under which the team should revisit the decision. Every irreversible decision has a review trigger; an ADR without one suggests the author has not thought about when the decision might become wrong. The trigger should be specific and measurable, not vague ("when we scale" is not a trigger; "when the Attempts table exceeds 500M rows" is).

---

## ADR Index

The full ADR index, including dependencies, superseding relationships, and cross-references to the ASD and glossary, is maintained in `cross-reference-matrix.md`. The matrix is the navigational map of the repository; consult it first when investigating an architectural question.

Future ADR topics, with brief rationales for why each is anticipated, are listed in `future-adr-suggestions.md`. These are not commitments; they are anticipated decisions that the team expects to make as the system scales.

---

## Process Ownership

The ADR process is owned by the **Principal Architect**. The architecture review group — composed of the Principal Architect, the Engineering Lead, and a rotating senior engineer — reviews all Proposed ADRs and transitions them to Accepted or Rejected. Any engineer may propose an ADR; the architecture review group's role is to ensure consistency with existing ADRs and the ASD, not to gatekeep ideas.

ADRs are version-controlled in the same repository as the code. A change to an ADR is a pull request like any other, with the same review requirements plus the architecture review group's approval. The ADR repository's history is itself an audit trail of architectural thinking.

---

## References

- Michael Nygard's original ADR article: <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>
- ThoughtWorks Technology Radar: ADRs as a "Trial" technique adopted by the industry.
- Architecture Specification Document (Task 001) — `/mastery-engine-architecture-spec.md`.
- Ubiquitous Language & Domain Glossary (Task 002) — `/docs/domain/ubiquitous-language.md`.

---

*End of ADR README.*
