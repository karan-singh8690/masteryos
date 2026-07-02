# ADR-0000 — Template

> **Purpose:** This is the template for all Architecture Decision Records in the Mastery Engine project. Copy this file to `NNNN-kebab-case-short-title.md`, fill in every section, and submit a pull request. See `README.md` for the ADR process.

---

## Title

[Short, descriptive title in Title Case. The title should state the decision, not the topic. "Use PostgreSQL as the primary database" is a good title; "Database selection" is not.]

---

## Status

[One of: Proposed | Accepted | Deprecated | Superseded | Rejected]

[If Superseded, add: "Superseded by ADR-NNNN on YYYY-MM-DD."]
[If Supersedes, add: "Supersedes ADR-NNNN."]

---

## Date

[YYYY-MM-DD — the date the ADR was Proposed. Do not update this date when the ADR transitions to Accepted; the proposal date is the historical anchor.]

---

## Context

[2–4 paragraphs describing the situation that gave rise to the decision. What is the system? What forces are at play? What constraints exist? What is the scale, the team, the timeline? The context section is what makes an ADR valuable years later — without it, the decision appears arbitrary. Write enough that a senior engineer joining the team in five years can understand the situation without asking anyone.]

[Include relevant references to the Architecture Specification Document and the Ubiquitous Language glossary where applicable. The context is where the ADR grounds itself in the project's existing architecture.]

---

## Problem Statement

[A single paragraph, framed as a question or a clear statement of the problem to be solved. The problem statement should be technology-neutral where possible — "How do we persist domain aggregates transactionally?" rather than "Which database do we use?" The technology-neutral framing forces genuine consideration of alternatives.]

---

## Decision

[1–3 paragraphs stating the decision clearly and unambiguously. "We will use X." "We will not use Y." The decision should be specific enough that an engineer reading it knows exactly what to do. If the decision has parameters (e.g., "we will use JWT with RS256, 15-minute access tokens, 30-day refresh tokens"), state them.]

[The decision section is the part that other ADRs and the ASD will reference. Make it quotable.]

---

## Alternatives Considered

[For each alternative, a subsection with: a one-line description, the arguments in favor, the arguments against, and the reason it was rejected. At least two genuine alternatives are required. "Genuine" means the alternative was seriously considered, not a strawman.]

### Alternative A: [Name]

- **Description:** [One line.]
- **Arguments in favor:** [Bullet list.]
- **Arguments against:** [Bullet list.]
- **Why rejected:** [One paragraph explaining the decisive factor.]

### Alternative B: [Name]

- **Description:** [One line.]
- **Arguments in favor:** [Bullet list.]
- **Arguments against:** [Bullet list.]
- **Why rejected:** [One paragraph explaining the decisive factor.]

[Add more alternatives as needed.]

---

## Pros

[What we gain by this decision. Bullet list. Be specific — "good performance" is weak; "sub-10ms p99 reads on hot paths with proper indexing" is strong. Pros should be things that would be lost if the decision were reversed.]

- [Pro 1]
- [Pro 2]
- [Pro 3]

---

## Cons

[What we lose or risk by this decision. Bullet list. Honest cons are the mark of a trustworthy ADR; an ADR with no cons has not been honestly considered. Cons should be things the team has decided to live with, not problems to be solved later.]

- [Con 1]
- [Con 2]
- [Con 3]

---

## Consequences

[What follows from this decision — the downstream effects, positive and negative. Consequences are not the same as pros and cons: pros and cons are direct; consequences are the second-order effects. "We chose PostgreSQL" is the decision; "the team must maintain SQL skills" is a consequence. Consequences often include required training, new infrastructure, operational burden, or constraints on future decisions.]

- [Consequence 1]
- [Consequence 2]
- [Consequence 3]

---

## Risks

[What could go wrong. Risks are conditional — "if X happens, then Y." For each risk, name the mitigation or the monitoring that will catch it. A risk without a mitigation is an open issue, not a documented risk.]

- **[Risk 1]:** [Description.] *Mitigation:* [What we do about it.]
- **[Risk 2]:** [Description.] *Mitigation:* [What we do about it.]

---

## Future Review Trigger

[The specific, measurable condition under which the team should revisit this decision. This is the most important section for the long-term health of the architecture. A decision that is never reviewed becomes a fossil; a decision with a clear review trigger stays alive.]

[Triggers should be measurable: "when the Attempts table exceeds 500M rows," "when p99 latency exceeds 500ms," "when the team exceeds 20 engineers," "when a second Subject is onboarded." Vague triggers like "when we scale" are not triggers; they are excuses to never review.]

**Review trigger:** [Specific, measurable condition.]

**Expected review action:** [What the team will do when the trigger fires — e.g., "evaluate extraction to a microservice," "evaluate migration to a columnar database," "evaluate adopting a managed service."]

---

## Related ADRs

[References to other ADRs that depend on, conflict with, or complement this one. Use the format `ADR-NNNN — Title`.]

- **Depends on:** [ADR-NNNN — Title] (this ADR assumes that decision)
- **Informs:** [ADR-NNNN — Title] (this ADR provides context for that one)
- **Conflicts with:** [ADR-NNNN — Title] (if applicable; explain how the conflict is resolved)

---

## Related Architecture Sections

[References to sections of the Architecture Specification Document (Task 001).]

- ASD Section X.Y — [Section name]

---

## Related Glossary Terms

[References to terms in the Ubiquitous Language & Domain Glossary (Task 002). List only the terms central to this decision.]

- [Term 1]
- [Term 2]

---

*End of ADR-0000 (Template).*
