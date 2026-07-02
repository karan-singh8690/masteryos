# ADR-0009 — Human-authored Curriculum is the Source of Truth

---

## Title

Treat human-authored curriculum as the canonical source of truth; permit AI assistance only within the authoring workflow, never as a runtime content generator or a publisher.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine's educational content — Concepts, Learning Objectives, Misconceptions, Question Templates, Explanations — is the substrate on which the learning loop operates. The quality, accuracy, and pedagogical soundness of this content directly determine the product's effectiveness. In 2026, large language models can draft plausible-looking educational content at near-zero cost, and the temptation to use them as the primary content source is strong: they promise to fill the content pipeline faster than human authors can.

However, the Mastery Engine's context makes this temptation dangerous. The platform's learners are preparing for technical interviews where wrong information has real consequences (a failed interview, a missed job). The platform's Misconception system (ASD Section 7.4) depends on accurate documentation of specific incorrect mental models; an LLM-generated Misconception that does not match how learners actually fail is worse than useless, because it misdirects remediation. The platform's Question Templates depend on correct-answer generators that produce the right answer for any valid parameters; an LLM that hallucinates a wrong "correct" answer produces silently incorrect scoring.

The architecture specification (Task 001, AI Usage Policy) states: "Human-authored content is the source of truth." The specification (Section 7.11) defines an AI Assistance Policy that permits AI within the authoring workflow (drafting, wording refinement, template skeletons) but forbids AI from publishing, editing published content, generating content at runtime, or making mastery/scheduling decisions. This ADR formalizes that policy and explains the rationale.

---

## Problem Statement

What role should AI (specifically LLMs) play in the Mastery Engine's content pipeline, given the requirements for content accuracy, pedagogical soundness, auditability, and the platform's data-moat thesis?

---

## Decision

**Human-authored curriculum is the canonical source of truth.** Every published content artifact (Concept, Learning Objective, Misconception, Question Template, Explanation) is authored, reviewed, and approved by a human Instructor (ASD Section 2.3) before it reaches learners. The Review Workflow (ASD Section 7.7) is the enforcement mechanism: no artifact publishes without peer review, editorial review, and QA/pilot.

**AI assistance is permitted within the authoring workflow**, under the following constraints:

- **Drafting**: AI may draft an initial version of an Explanation, an initial Distractor set, or an initial prompt wording. The Instructor reviews and edits before submitting for peer review.
- **Wording refinement**: AI may suggest rephrasings for clarity, tone, or brevity. The Instructor accepts or rejects each suggestion explicitly; accepted suggestions are recorded in the artifact's history.
- **Template skeleton generation**: AI may draft a Template skeleton (parameter schema, prompt structure, Distractor tags). The Instructor fills in the generators, validates correctness, and submits for review.

**AI is forbidden from**:

- Publishing artifacts (only human Instructors can publish).
- Editing published artifacts (edits require a Revision through the Review Workflow).
- Generating content at runtime (the learning loop serves only published, human-approved content).
- Making mastery or scheduling decisions (per ADR-0007).

**Provenance tracking**: every AI-assisted artifact carries a provenance flag in its history, recording which AI model assisted, on what date, and at which stage. This is a compliance and quality requirement.

---

## Alternatives Considered

### Alternative A: LLM-generated content as the primary source

- **Description:** Use an LLM to generate Concepts, Templates, and Explanations at scale; human review is light or absent.
- **Arguments in favor:**
  - Massive content production at near-zero cost.
  - Fast coverage of long-tail topics.
  - Always-available content (no waiting for human authors).
- **Arguments against:**
  - **Hallucination risk**: LLMs produce plausible-but-wrong content (a Misconception that does not match real learner errors; a correct-answer generator that fails on edge cases; an Explanation that subtly misrepresents the Concept). At the Mastery Engine's stakes, this is unacceptable.
  - **Pedagogical soundness**: LLMs do not understand how learners fail; they generate Misconceptions that look plausible but do not match the cognitive-science literature or observed learner data.
  - **Auditability**: LLM-generated content is not auditable in the way human-authored content is. When a learner reports a wrong answer, the team must be able to trace the content to a human author who can be asked "why did you write this?"
  - **Data moat dilution**: if the content is LLM-generated, competitors can replicate it; the moat shifts from content to the mastery model, but content quality is the substrate on which the mastery model operates.
  - **Trust**: serious learners will detect LLM-generated content (it has recognizable patterns) and lose trust in the platform.
  - **Regulatory risk**: future education regulations may require human-authored or human-reviewed content; LLM-generated content may not satisfy this.
- **Why rejected:** The hallucination, pedagogical, auditability, and trust problems are decisive. The cost savings of LLM-generated content are real but do not outweigh the quality risk at the platform's stakes.

### Alternative B: LLM-generated content with heavy human review

- **Description:** Use an LLM to generate content, but require thorough human review before publishing.
- **Arguments in favor:**
  - Faster than pure human authoring.
  - Human review catches errors.
- **Arguments against:**
  - **Review fatigue**: human reviewers of LLM-generated content suffer from "alert fatigue" — they skim rather than scrutinize, missing subtle errors. The review quality degrades when the reviewer knows the content is LLM-generated.
  - **Asymmetry of effort**: reviewing LLM content for subtle errors is harder than writing it from scratch, because the reviewer must verify every claim rather than recognize their own intent.
  - **Pedagogical drift**: LLM-generated content tends toward generic explanations that lack the specificity that drives learning. Reviewers may not catch this because the content is "fine" but not excellent.
  - **The Review Workflow's QA/pilot stage**: the QA stage measures discrimination and clarity on a pilot cohort, but pilot cohorts are small and may not catch errors that surface at scale.
- **Why rejected:** The review quality problem is decisive. The Review Workflow is designed for human-authored content; LLM-generated content stresses it in ways it was not designed for. The AI-assistance-permitted approach (the Decision) captures the productivity benefits of LLMs (drafting, wording) without the review-quality risk.

### Alternative C: Runtime LLM-generated Explanations

- **Description:** Use an LLM to generate Explanations at runtime, personalized to the Learner's specific mistake.
- **Arguments in favor:**
  - Highly personalized explanations.
  - No need to author Explanation variants in advance.
- **Arguments against:**
  - **Hallucination risk at runtime**: a runtime-generated Explanation that is wrong is served to a learner immediately, with no review. The damage is done before anyone catches it.
  - **Reproducibility**: runtime LLM Explanations are stochastic; the same Learner mistake may produce different Explanations on different attempts, breaking the reproducibility invariant.
  - **Latency**: runtime LLM calls add latency (seconds, not milliseconds) to the learning loop, violating the 200ms target.
  - **Cost**: runtime LLM calls are paid per-call; at millions of learners, the cost is prohibitive.
  - **The AI Usage Policy** (ASD) forbids runtime AI for content generation.
- **Why rejected:** The hallucination, reproducibility, latency, cost, and policy problems are all decisive. Runtime LLM Explanations are explicitly forbidden.

---

## Pros

- **Content accuracy**: human-authored content is reviewed by multiple Instructors, catching errors before they reach learners.
- **Pedagogical soundness**: human Instructors understand how learners fail; Misconceptions are documented from real learner data, not LLM guesses.
- **Auditability**: every published artifact has a chain of named human Approvers (ASD Section 7.7); any quality issue is traceable.
- **Trust**: learners know the content is human-authored and reviewed; this is a competitive differentiator in an era of AI-generated content.
- **Data moat preservation**: the content is a proprietary asset; LLM-generated content would be replicable by competitors.
- **AI productivity captured**: the AI-assistance-permitted approach captures the productivity benefits of LLMs (drafting, wording refinement) without the quality risk.
- **Provenance**: AI-assisted artifacts carry provenance flags, enabling future quality analysis (did AI-assisted artifacts perform differently from non-assisted ones?).

---

## Cons

- **Content production velocity**: human authoring is slower than LLM generation; the content pipeline is a bottleneck. (Mitigated by AI assistance in drafting, by parallel authoring, and by the future contributor program.)
- **Cost**: human authors are paid; LLM generation is cheap. (Mitigated by the platform's subscription model, which funds content authoring.)
- **Scalability**: scaling content production to multiple Subjects requires scaling the author pool, which is an organizational challenge. (Mitigated by the contributor program and by AI assistance.)
- **AI assistance discipline**: the team must maintain the discipline that AI assists but does not publish; violations erode the policy. (Mitigated by the Review Workflow, which requires human approval at every stage.)

---

## Consequences

- Every published artifact has a chain of human Approvers recorded in its history (ASD Section 7.7).
- The Review Workflow (peer review, editorial review, QA/pilot) is mandatory for all content; no artifact publishes without it.
- AI-assisted artifacts carry provenance flags (which model, when, which stage) in their history.
- The content pipeline is a human-driven process; AI is a tool within it, not a participant in the publishing decision.
- The glossary (Task 002) defines "Instructor" as the human role that authors and reviews content; the AI is not an Instructor.
- Runtime content generation by AI is forbidden and enforced by code review (no LLM calls in the learning loop's runtime path).
- The content pipeline's analytics (Quality Metrics, ASD Section 7.10) measure the quality of human-authored content; AI-assisted artifacts are compared to non-assisted ones to validate the assistance policy.

---

## Risks

- **Authoring bottleneck**: the content pipeline cannot keep up with demand, slowing Subject expansion. *Mitigation:* AI assistance accelerates drafting; the contributor program expands the author pool; analytics prioritize high-yield Concepts.
- **AI policy erosion**: under deadline pressure, Instructors let AI-generated content publish without thorough review. *Mitigation:* the Review Workflow is non-negotiable; the QA/pilot stage catches content that does not discriminate; periodic audits verify that AI-assisted artifacts meet the same quality bar as non-assisted ones.
- **Provenance gaps**: AI-assisted artifacts are not flagged, losing the provenance record. *Mitigation:* the authoring tool requires explicit provenance declaration; linting checks for missing provenance flags.
- **Reviewer fatigue**: reviewers of AI-assisted content skim rather than scrutinize. *Mitigation:* the Review Workflow's QA/pilot stage is an objective check (discrimination, clarity) that does not depend on reviewer attention; reviewers are trained to scrutinize AI-assisted drafts as carefully as human drafts.
- **Quality divergence**: AI-assisted artifacts perform worse than non-assisted ones, indicating that AI assistance is degrading quality. *Mitigation:* analytics compare the two; if divergence is detected, the AI assistance policy is revisited via a new ADR.

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **AI model capability leap**: a new LLM (e.g., a future generation) demonstrates dramatically lower hallucination rates on educational content, justifying a re-evaluation of the AI-as-primary-source alternative.
2. **Quality divergence**: analytics show that AI-assisted artifacts perform significantly worse (lower discrimination, lower retention) than non-assisted ones, indicating that AI assistance is degrading quality and the policy should be tightened.
3. **Authoring bottleneck**: the content pipeline cannot keep up with Subject expansion demand, and the contributor program has not closed the gap, justifying expanded AI assistance (e.g., AI-generated drafts with mandatory heavy review).
4. **Regulatory change**: education regulations require human-authored or human-reviewed content, confirming the current policy, OR regulations explicitly permit AI-generated content with specific safeguards, opening the door to a policy revision.

**Expected review action:** When any trigger fires, the architecture review group and the curriculum lead evaluate the policy change. Any expansion of AI's role requires a new ADR with a documented evaluation of the quality risk and a mitigation plan. The human-authored-source-of-truth principle is the default; deviations require overwhelming justification.

---

## Related ADRs

- **Depends on:** ADR-0007 (Deterministic Scheduling before ML) — the human-authored principle extends the "human is source of truth" philosophy from algorithms to content.
- **Depends on:** ADR-0010 (Subject-agnostic architecture) — the content pipeline is the mechanism by which new Subjects are added; its integrity determines the architecture's scalability.
- **Informs:** ADR-0011 (Triple Versioning) — content versioning is the audit mechanism for the human-authored policy.

---

## Related Architecture Sections

- ASD Section 1.4 — Technical Philosophy (AI Usage Policy).
- ASD Section 7 — Content Pipeline (authoring, review, publishing, versioning).
- ASD Section 7.11 — AI Assistance Policy (permitted and forbidden uses).
- ASD Section 2.3 — Instructor role (the human author/reviewer).

---

## Related Glossary Terms

- Instructor
- Content Pack
- Content Version
- Review Workflow
- Content Approval
- Published Content
- Draft Content
- Misconception
- Question Template
- Explanation

---

*End of ADR-0009.*
