# ADR-0007 — Use Deterministic Scheduling before Machine Learning

---

## Title

Ship a deterministic scheduling and mastery algorithm first; admit ML only after earning the right through accumulated data and a documented evaluation protocol.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine's north-star question — "Given everything we know about this learner right now, what should they study next?" — is, in the abstract, a recommendation problem that ML could address. Modern ML recommender systems are powerful, and the temptation to use them from day one is strong: they promise personalization that hand-tuned heuristics cannot match, and they are the dominant approach in adjacent domains (content recommendation, ad targeting).

However, the Mastery Engine's context differs from those domains in three critical ways. First, the stakes are higher: a wrong recommendation in education is not a missed click; it is a wasted hour of the learner's time or a misjudged readiness for an interview. Second, the data is sparse at launch: ML recommenders need large interaction corpora to outperform heuristics, and a new platform has no such corpus. Third, reproducibility and auditability are essential: the Engine must be able to explain why a question was served, and must be able to recompute any historical mastery state on demand; ML models are opaque and version-drift in ways that deterministic algorithms are not.

The architecture specification (Task 001, Section 1.4) commits to a "deterministic-first" philosophy: scheduling, mastery computation, and queue selection are algorithms with auditable inputs and outputs; AI assists authoring but is forbidden from runtime learning decisions. The specification (Section 6.7) reserves a path for future ML integration via a model registry, shadow evaluation, and a promotion gate. This ADR formalizes the deterministic-first commitment and the conditions under which ML may be admitted.

The project's "AI Usage Policy" (ASD Section, AI Usage Policy) explicitly states: "Do not rely on AI for runtime decision making." This ADR is the architectural expression of that policy.

---

## Problem Statement

Should the Mastery Engine's scheduling and mastery algorithms be deterministic (hand-tuned heuristics) or ML-based (learned from data) at launch, and under what conditions should that decision be revisited?

---

## Decision

We will ship **deterministic algorithms** for the Mastery Engine (mastery computation, memory decay, review scheduling) and the Scheduler (queue ranking, priority computation) at launch. The algorithms are versioned (Algorithm Version, ADR-0011) and are pure functions of the Attempt history and the algorithm version, making mastery reproducible and auditable.

ML is not forbidden in principle; it is **deferred**. The architecture reserves integration points for future ML:
- A **feature extraction layer** persists structured feature vectors alongside every Mastery Score, enabling offline ML training without touching production.
- A **model registry** versions mastery models; the deterministic algorithm is "model v1."
- A **shadow evaluation** mode runs a candidate ML model in parallel with the production model, logging its outputs without using them, enabling offline evaluation against real traffic.
- A **promotion gate** requires a candidate model to pass a documented evaluation (reproducibility on historical Attempts, no regression on retention metrics, human sign-off) before it touches a learner.

ML may be promoted to production only after the data requirements (defined in Future Review Trigger) are met and the candidate model defeats the deterministic baseline on measured outcomes. The promotion is recorded as a new Algorithm Version and a new ADR.

---

## Alternatives Considered

### Alternative A: ML-based scheduling and mastery from day one

- **Description:** Use a learned model (e.g., a neural net or a gradient-boosted tree) for mastery computation and queue ranking from launch.
- **Arguments in favor:**
  - ML can in principle outperform heuristics on personalization.
  - Modern ML infrastructure (feature stores, model registries) makes this feasible.
  - The "cool factor" attracts hires and investors.
- **Arguments against:**
  - **Cold-start problem**: ML needs data; a new platform has none. The model would be untrained or trained on irrelevant data, producing worse recommendations than heuristics.
  - **Reproducibility**: ML models are stochastic and version-drift; recomputing a historical mastery state from a model that has since been retrained is impossible without snapshotting every model version's weights and inputs.
  - **Auditability**: when a learner asks "why was I served this question?", an ML model cannot give a satisfying answer; a deterministic algorithm can point to the inputs and the ranking.
  - **Cost**: ML infrastructure (training pipelines, feature stores, model servers) is expensive to build and operate, especially for a small team.
  - **Debugging**: when scheduling goes wrong (e.g., a learner is served the same Concept 10 times), debugging an ML model is far harder than debugging a deterministic algorithm.
  - **Trust**: serious learners want to understand the system's reasoning; ML opacity erodes trust.
  - **Regulatory risk**: future education regulations may require explainable recommendations; ML models may not satisfy this.
- **Why rejected:** The cold-start, reproducibility, and auditability problems are decisive at launch. ML may be admitted later, but only after the data and evaluation infrastructure exist to do it responsibly.

### Alternative B: Hybrid from day one (deterministic with ML refinement)

- **Description:** Use deterministic algorithms as the base, with an ML model adjusting weights or rankings from launch.
- **Arguments in favor:**
  - Combines the stability of deterministic with the personalization of ML.
  - The ML component starts simple (e.g., a learned weight on one factor) and grows.
- **Arguments against:**
  - The cold-start problem still applies to the ML component; the learned weights would be untrained.
  - The reproducibility problem still applies; the ML component introduces stochasticity.
  - The complexity of a hybrid system exceeds either pure approach; the team must maintain both the deterministic base and the ML refinement.
  - The benefit is marginal at launch (the ML component adds little when untrained) and the cost is real (maintaining two systems).
- **Why rejected:** The complexity is not justified at launch. The deterministic-first approach provides the same launch outcomes with less complexity. ML refinement can be added later via the shadow-evaluation and promotion-gate path.

### Alternative C: Third-party recommendation API (e.g., a managed ML service)

- **Description:** Use a third-party recommendation API for scheduling and mastery.
- **Arguments in favor:**
  - No ML infrastructure to build.
  - Fast to integrate.
- **Arguments against:**
  - The data moat thesis (ASD Section 1.2) depends on owning the mastery model; outsourcing it surrenders the moat.
  - Third-party APIs are paid per-call; at millions of learners, the cost is prohibitive.
  - The learning loop's latency target (200ms median) is harder to guarantee with an external API call.
  - Reproducibility and auditability are impossible with a third-party black box.
  - The AI Usage Policy (ASD) forbids dependence on paid APIs for runtime decisions.
- **Why rejected:** The data moat, cost, latency, and policy problems are all decisive. The Mastery Engine's mastery model is the product; it cannot be outsourced.

---

## Pros

- **Reproducibility**: given the Attempt history and the Algorithm Version, any historical mastery state can be reconstructed exactly. This is the foundation of auditability and the prerequisite for future ML retraining.
- **Auditability**: every scheduling decision can be traced to its inputs and the algorithm version. The Engine can answer "why this question?" with a concrete explanation.
- **Cold-start robustness**: deterministic heuristics work from day one, without data. They may not be optimal, but they are correct and explainable.
- **Low operational cost**: no training pipelines, no model servers, no feature stores. The algorithms run in-process with the API.
- **Debuggability**: when scheduling goes wrong, the inputs and the algorithm are inspectable; debugging is a deterministic process.
- **Trust**: serious learners can understand the system's reasoning, building trust.
- **ML integration path preserved**: the feature extraction layer, model registry, shadow evaluation, and promotion gate mean ML can be admitted later without rewriting the system.
- **Data accumulation**: the deterministic algorithm accumulates the Attempt corpus that future ML will need; the project does not delay data collection while deferring ML.

---

## Cons

- **Suboptimal personalization at launch**: deterministic heuristics are less personalized than a well-trained ML model would be. (Mitigated by the fact that no well-trained ML model exists at launch; the comparison is to an untrained model, which is worse.)
- **Manual tuning**: the algorithm's weights and thresholds require human tuning as data accumulates. (Mitigated by analytics that surface tuning opportunities; the algorithm is versioned, so tuning is a deliberate, reviewed change.)
- **ML deferral frustration**: the team may feel that ML is "the future" and that deferring it is backward. (Mitigated by the documented integration path; ML is deferred, not rejected.)
- **Algorithm design burden**: the team must design and validate the deterministic algorithm, which is non-trivial. (Mitigated by the Mastery Engine Algorithm Design task, which produces the algorithm as a separate design document.)

---

## Consequences

- The Mastery Engine and the Scheduler are implemented as deterministic Domain Services (pure functions).
- Every Mastery Score records the Algorithm Version under which it was computed (ADR-0011).
- A feature extraction layer persists structured feature vectors alongside every Mastery Score, enabling future offline ML training.
- A model registry is built (Phase 4, per ASD Section 16.4) to version mastery models; the deterministic algorithm is "model v1."
- Shadow evaluation infrastructure is built (Phase 4) to run candidate ML models in parallel with production.
- A promotion gate (reproducibility, no regression, human sign-off) governs ML model promotion.
- The Attempt corpus accumulates from day one, building the data asset that future ML will require.
- Algorithm changes are versioned (new Algorithm Version) and require an ADR; they are never in-place edits.

---

## Risks

- **Heuristic tuning stagnation**: the deterministic algorithm is not tuned as data accumulates, leaving it suboptimal. *Mitigation:* analytics surface tuning opportunities; the architecture review group schedules periodic algorithm reviews.
- **ML pressure**: external pressure (investors, hires, competitors) pushes the team to adopt ML before the data and evaluation infrastructure are ready. *Mitigation:* the promotion gate is non-negotiable; ML is admitted only when it defeats the deterministic baseline on measured outcomes.
- **Shadow evaluation cost**: running a candidate model in shadow mode doubles the mastery computation cost. *Mitigation:* shadow evaluation runs on a sample of traffic, not all; the cost is bounded.
- **Feature extraction drift**: the feature vectors persisted alongside Mastery Scores change over time, complicating offline ML training. *Mitigation:* feature vectors are versioned with the Algorithm Version; offline training uses the feature vectors that were current at the Attempt time.
- **Algorithm bug propagation**: a bug in the deterministic algorithm propagates to every Mastery Score computed under that Algorithm Version. *Mitigation:* property-based tests (ASD Section 14.4) catch algorithm bugs; the Algorithm Version system allows bug fixes via a new version, with recomputation of affected Mastery Scores.

---

## Future Review Trigger

**Review trigger:** All of the following conditions must be met before ML is admitted for the Mastery Engine or the Scheduler:

1. **Data volume**: the platform has accumulated at least 10 million Attempts across at least 10,000 learners, providing sufficient training data.
2. **Baseline stability**: the deterministic algorithm has been stable (no major changes) for at least 6 months, providing a stable baseline for comparison.
3. **Feature infrastructure**: the feature extraction layer and the model registry are built and tested.
4. **Shadow evaluation infrastructure**: the shadow evaluation mode is operational, with offline evaluation tooling.
5. **Evaluation protocol**: a documented evaluation protocol exists, specifying the metrics (retention, mastery gain, scheduling diversity), the significance threshold, and the human sign-off process.
6. **Candidate model**: a candidate ML model has been trained offline and shows promise on historical data.
7. **No regression on shadow**: the candidate model, run in shadow mode for at least 30 days, shows no regression on retention metrics and no anomalies in scheduling diversity.
8. **Human sign-off**: the architecture review group and the curriculum lead sign off that the candidate model's recommendations are pedagogically sound.

**Expected review action:** When all conditions are met, the architecture review group produces a new ADR proposing the promotion of the candidate model to production as a new Algorithm Version. The ADR includes the evaluation results, the promotion plan, the rollback plan, and the monitoring plan. If the candidate model is promoted, the deterministic algorithm remains as a fallback (a kill switch via feature flag, ADR-0014-era infrastructure) in case the ML model regresses in production.

---

## Related ADRs

- **Depends on:** ADR-0011 (Triple Versioning) — the Algorithm Version is one of the three versioning dimensions.
- **Depends on:** ADR-0006 (Domain-Driven Design) — the Mastery Engine is a Domain Service, pure and deterministic.
- **Informs:** ADR-0009 (Human-authored curriculum) — the deterministic-first philosophy extends the "human is source of truth" principle from content to algorithms.

---

## Related Architecture Sections

- ASD Section 1.4 — Technical Philosophy (deterministic-first).
- ASD Section 6 — Mastery Engine (inputs, outputs, state transitions, future ML integration).
- ASD Section 6.7 — Future ML Integration (feature extraction, model registry, shadow evaluation, promotion gate).
- ASD Section 6.8 — Mastery Engine Invariants (pure function, versioned, single writer, event-sourced reconstruction).

---

## Related Glossary Terms

- Mastery Score
- Memory Score
- Mastery Engine
- Scheduler
- Algorithm Version
- Concept State
- Review Interval

---

*End of ADR-0007.*
