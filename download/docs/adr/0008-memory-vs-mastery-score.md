# ADR-0008 — Separate Memory Score from Mastery Score

---

## Title

Maintain two distinct mastery estimates per Concept per Learner: a short-term Memory Score and a long-term Mastery Score, rather than a single composite.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine's job is to estimate, at any moment, a Learner's mastery of each Concept. This estimate drives two distinct decisions: short-term scheduling ("should we drill this Concept again today?") and long-term judgment ("is this Learner ready for their interview?"). These two decisions have different time horizons, different sensitivities to recent activity, and different tolerance for noise. A single estimate conflates them, producing scheduling that is too aggressive (drilling Concepts the Learner just learned) or too conservative (declaring interview readiness based on a single recent success).

The cognitive-science literature on spaced repetition distinguishes between short-term recall (memory, which decays sharply without reinforcement) and long-term retention (mastery, which is more durable and survives gaps). The Mastery Engine's mastery model should reflect this distinction, not flatten it. A Learner who learned a Concept an hour ago has high memory but unproven mastery; a Learner who learned a Concept six months ago and has not reviewed has low memory but potentially intact mastery; a Learner who has successfully reviewed a Concept across multiple spaced intervals has both high memory and high mastery.

The architecture specification (Task 001, Section 6.4) commits to this distinction. This ADR formalizes it and explains the practical consequences.

---

## Problem Statement

Should the Mastery Engine maintain one mastery estimate per Concept per Learner, or two (a short-term memory estimate and a long-term mastery estimate), and how should the two interact?

---

## Decision

We will maintain **two distinct estimates** per Concept per Learner:

1. **Memory Score** — the Engine's estimate of the probability that the Learner can correctly recall the Concept *right now*. Highly sensitive to recent Attempts; decays sharply with time. Drives short-term scheduling decisions (drill again today, schedule a review).

2. **Mastery Score** — the Engine's consolidated estimate of the Learner's *durable* understanding. Slower to rise (requires sustained correct performance across spaced reviews) and slower to fall (a single failure does not collapse it). Drives long-term decisions (graduation, interview readiness, learning path advancement).

The two scores are **combined, not averaged**. The Mastery Score anchors the estimate; the Memory Score modulates it for scheduling. A Learner with high Mastery but low Memory on a Concept is scheduled for a review; a Learner with low Mastery on the same Concept is scheduled for fresh instruction and drilling regardless of Memory.

The two scores share the same Attempt history as input but apply different functions to it. Both are versioned with the Algorithm Version (ADR-0011) and are reconstructible from the Attempt history.

---

## Alternatives Considered

### Alternative A: Single composite mastery score

- **Description:** One score per Concept per Learner, used for both short-term scheduling and long-term judgment.
- **Arguments in favor:**
  - Simpler model; one number to reason about.
  - Easier to communicate to Learners ("your mastery is 0.78").
  - Less storage and computation.
- **Arguments against:**
  - **Conflates time horizons**: a single score cannot distinguish "just learned, high memory, unproven mastery" from "learned long ago, low memory, intact mastery." The first case needs immediate reinforcement; the second needs a review; the third needs recognition of durable mastery. A single score treats them identically.
  - **Scheduling degradation**: without a separate memory signal, the Scheduler cannot detect that a Concept is fading in short-term recall while mastery is intact. It will either over-drill (treating low memory as low mastery) or under-review (treating intact mastery as no need for refresh).
  - **Long-term judgment degradation**: without a separate mastery signal, graduation and interview readiness are based on a noisy short-term estimate. A Learner who crammed yesterday appears ready; a Learner who studied steadily over months but did not study yesterday appears unready.
  - **Cognitive-science mismatch**: the single-score model does not match the well-established distinction between short-term recall and long-term retention.
- **Why rejected:** The conflation of time horizons produces worse scheduling and worse long-term judgment. The simplicity benefit is real but small; the cost is significant.

### Alternative B: Three or more scores (e.g., memory, mastery, confidence, fluency)

- **Description:** Maintain additional scores (e.g., a confidence interval, a fluency score based on response time, a transfer score based on cross-Concept performance).
- **Arguments in favor:**
  - Richer signal for scheduling and analytics.
  - More dimensions to personalize.
- **Arguments against:**
  - **Complexity**: each additional score adds modeling, validation, and communication burden.
  - **Diminishing returns**: the memory/mastery distinction captures the most important time-horizon effect; additional scores add marginal value.
  - **Cold-start**: each additional score needs data to calibrate; more scores mean more cold-start period.
  - **Communication**: Learners cannot reason about four scores; the dashboard becomes cluttered.
- **Why rejected:** The two-score model captures the essential distinction without the complexity of additional scores. Additional dimensions (confidence, fluency) are tracked as inputs to the two scores, not as separate scores. This decision can be revisited if analytics show that a third dimension would materially improve scheduling.

### Alternative C: Mastery Score plus a separate "due for review" boolean

- **Description:** One mastery score, plus a boolean indicating whether the Concept is due for review.
- **Arguments in favor:**
  - Simpler than two scores.
  - Captures the "needs refresh" signal.
- **Arguments against:**
  - The boolean is a coarse approximation of the memory score; it loses the graded signal (how urgently does the Concept need refresh?).
  - The boolean is derived from the mastery score and a review interval, which conflates the two concepts the architecture is trying to separate.
  - The boolean cannot drive graduated scheduling (e.g., "this Concept is fading fast, prioritize it over one fading slowly").
- **Why rejected:** The boolean is too coarse. The graded memory score is needed for graduated scheduling and for honest communication to the Learner about the state of their recall.

---

## Pros

- **Time-horizon separation**: short-term scheduling uses the Memory Score; long-term judgment uses the Mastery Score. Each decision uses the right signal.
- **Cognitive-science alignment**: the two-score model matches the established distinction between short-term recall and long-term retention.
- **Graduated scheduling**: the Memory Score's graded value drives graduated review prioritization (a Concept at 0.30 is more urgent than one at 0.55).
- **Honest long-term judgment**: graduation and interview readiness are based on the durable Mastery Score, not the noisy Memory Score.
- **Decay visibility**: the two-score model makes memory decay visible and actionable, driving the spaced-repetition loop.
- **Learner communication**: the dashboard can show both ("you mastered this Concept, but your memory is fading — review to refresh"), which is more informative than a single number.

---

## Cons

- **Complexity**: two scores to compute, store, and communicate.
- **Learner confusion**: Learners may not understand the distinction without clear communication. (Mitigated by UI design that explains the two scores; the distinction is intuitive once explained.)
- **Calibration**: the two scores' functions must be calibrated separately; the decay rate for Memory and the consolidation rate for Mastery are different parameters. (Mitigated by the Algorithm Version system, which versions the parameters together.)
- **Storage**: two scores per Concept per Learner, versus one. (Negligible cost at the project's scale.)

---

## Consequences

- The MasteryScore Value Object (ASD Section 4.5) contains two sub-scores: MemoryScore and durable-mastery sub-score, plus a confidence interval, an evidence count, and a last-updated timestamp.
- The Mastery Engine (ASD Section 6) computes both scores from the Attempt history; the functions are versioned with the Algorithm Version.
- The Scheduler (ASD Section 2.4) consumes both scores: the Memory Score drives short-term review scheduling; the Mastery Score drives long-term decisions (graduation, interview readiness).
- The dashboard and progress page display both scores, with clear explanations of the distinction.
- The glossary (Task 002) defines both terms and the Synonym Table explicitly distinguishes them (Memory Score ≠ Mastery Score).
- Concept State (Unseen, Novice, Developing, Proficient, Mastered, Decayed) is derived from both scores: a Concept is Decayed when Mastery is intact but Memory has fallen below threshold.
- The Weak Concept detection (ASD Section 6.6) uses both scores: a Concept is Weak when Mastery is below threshold OR when Memory is below threshold while Mastery is below Proficient.

---

## Risks

- **Score conflation in communication**: engineers, product, or Learners conflate the two scores, eroding the distinction. *Mitigation:* the glossary and the Synonym Table explicitly distinguish them; code review flags conflation; UI copy is reviewed for clarity.
- **Calibration drift**: the decay rate for Memory and the consolidation rate for Mastery drift apart, producing inconsistent scores. *Mitigation:* the Algorithm Version system versions both together; recalibration is a deliberate, reviewed change.
- **Learner confusion**: Learners do not understand the distinction, leading to misinterpretation of their progress. *Mitigation:* UI design explains the distinction; the dashboard's primary display emphasizes Mastery Score (the long-term signal), with Memory Score as a secondary "needs refresh" indicator.
- **Over-reliance on Memory Score for long-term decisions**: if graduation or interview readiness accidentally uses Memory Score instead of Mastery Score, the decisions become noisy. *Mitigation:* code review enforces that long-term decisions use Mastery Score; the architecture review group audits this.

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Score correlation**: the Memory Score and the Mastery Score become highly correlated (correlation > 0.9) across the Learner population, indicating that the distinction is not adding value and the model could be simplified.
2. **Scheduling degradation**: analytics show that scheduling decisions based on the two-score model are not outperforming a single-score baseline on retention metrics, indicating that the distinction is not producing better outcomes.
3. **Learner confusion**: user research shows widespread Learner confusion about the two scores, indicating that the communication cost exceeds the value.
4. **Additional dimension needed**: analytics show that a third dimension (e.g., fluency, transfer) would materially improve scheduling, justifying the complexity of additional scores.

**Expected review action:** When any trigger fires, the architecture review group evaluates whether to merge the two scores, to add a third, or to revise the communication. Any change to the score model is a new Algorithm Version (ADR-0011) and a new ADR.

---

## Related ADRs

- **Depends on:** ADR-0007 (Deterministic Scheduling before ML) — the two-score model is part of the deterministic algorithm.
- **Depends on:** ADR-0011 (Triple Versioning) — both scores are versioned with the Algorithm Version.
- **Informs:** ADR-0009 (Human-authored curriculum) — the Misconception system depends on the Mastery Score's stability for accurate diagnosis.

---

## Related Architecture Sections

- ASD Section 6.4 — Memory Score vs. Mastery Score.
- ASD Section 6.6 — Weak Concept Detection (uses both scores).
- ASD Section 6.3 — State Transitions (Concept State derived from both scores).

---

## Related Glossary Terms

- Memory Score
- Mastery Score
- Concept State
- Weak Concept
- Strong Concept
- Mastery Threshold
- Memory Threshold
- Knowledge Decay

---

*End of ADR-0008.*
