# ADR-0011 — Triple Versioning

---

## Title

Version every Attempt along three independent axes: Content Version (Subject-wide content snapshot), Template Version (per-Question-Template snapshot), and Algorithm Version (Mastery Engine algorithm snapshot).

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine's data moat (ASD Section 1.2) depends on the Attempt corpus being interpretable and replayable indefinitely. An Attempt recorded today must be meaningful five years from now, even if the content has been revised, the question templates have been edited, and the mastery algorithm has been upgraded. Without versioning, historical Attempts become opaque: "which version of the question was this?" and "which algorithm scored this?" become unanswerable, and the moat erodes.

The system has three independent evolution axes:
1. **Content** evolves as Instructors revise Concepts, add Misconceptions, and edit Question Templates. A Concept description today may differ from a year ago.
2. **Templates** evolve as Instructors fix bugs in correct-answer generators, add Distractors, or refine prompts. A Question Instance served today must be reproducible from its Template, even if the Template is later edited.
3. **The Mastery Algorithm** evolves as the team tunes the deterministic model (and, in the future, promotes ML models per ADR-0007). A Mastery Score computed today must be reconstructible from the Attempt history under the algorithm that produced it.

These three axes are independent: a Content Version bump does not change the Algorithm Version, and a Template Version bump does not change the Content Version of other Templates. Versioning them together (a single "system version") would couple unrelated evolutions and force simultaneous upgrades. Versioning them separately allows each to evolve at its own pace.

The architecture specification (Task 001, Section 7.9) commits to triple versioning. This ADR formalizes the commitment and the auditability and reproducibility properties it enables.

---

## Problem Statement

How should the Mastery Engine version its content, question templates, and mastery algorithm to ensure that every historical Attempt remains interpretable and every historical Mastery Score remains reconstructible, even as each axis evolves independently over the system's decade-long lifespan?

---

## Decision

We will version every Attempt along three independent axes:

1. **Content Version** — an immutable snapshot of a Subject's entire content graph (Concepts, Concept Dependencies, Learning Objectives, Misconceptions, Question Templates, Explanations) at a moment in time. Bumped atomically on every publish of one or more Content Packs. Referenced by every Attempt served under it.

2. **Template Version** — an immutable snapshot of a single Question Template. Bumped on every edit to the Template. Referenced by every Question Instance instantiated from it. The finest-grained versioning in the system.

3. **Algorithm Version** — an immutable snapshot of the Mastery Engine's algorithm (the scoring function, the decay model, the Review Interval logic). Bumped on every change to the algorithm. Referenced by every Mastery Score computed under it.

Every Attempt record carries all three versions: `content_version_id`, `template_version_id`, `algorithm_version_id`. Every Mastery Score record carries the `algorithm_version_id` under which it was computed. This triple-versioning makes every Attempt fully replayable (reconstruct the Question Instance from the Template Version + seed + Content Version) and every Mastery Score fully reconstructible (recompute from the Attempt history under the recorded Algorithm Version).

---

## Alternatives Considered

### Alternative A: Single "system version" for everything

- **Description:** One version number for the entire system; bumping any component bumps the system version.
- **Arguments in favor:**
  - Simpler model; one number to track.
  - No coordination problem between versions.
- **Arguments against:**
  - **Coupled evolution**: a typo fix in one Template would bump the system version, requiring all Attempts to reference the new version even though only one Template changed. The version graph becomes enormous and meaningless.
  - **No independent evolution**: the team cannot upgrade the algorithm without bumping content versions, forcing simultaneous content re-validation.
  - **Storage overhead**: every system version is a full snapshot; the storage cost is prohibitive.
- **Why rejected:** The coupling is unworkable. The three axes evolve at different rates (content weekly, templates monthly, algorithm yearly); coupling them produces a versioning nightmare.

### Alternative B: Version only Content and Algorithm (no Template Version)

- **Description:** Version Content (Subject-wide) and Algorithm, but not individual Templates. A Template is identified by its Content Version.
- **Arguments in favor:**
  - Simpler than triple versioning.
  - Fewer version records to store.
- **Arguments against:**
  - **Question Instance non-replayability**: a Question Instance is instantiated from a Template + seed. Without Template Versioning, editing a Template's correct-answer generator makes old Question Instances non-reproducible (the same Template + seed now produces a different question). This breaks the replayability invariant.
  - **Coarse-grained content versioning**: a Content Version is Subject-wide; without Template Versioning, every Template edit requires a Content Version bump, producing enormous Content Version churn.
- **Why rejected:** Template Versioning is necessary for Question Instance replayability, which is a core requirement (ASD Section 7.6). Without it, the Attempt corpus is not fully interpretable.

### Alternative C: Event sourcing (version everything as an event log)

- **Description:** Model all changes as events in a log; reconstruct any historical state by replaying events.
- **Arguments in favor:**
  - Maximum auditability and replayability.
  - Natural fit for the outbox pattern (ADR-0012).
- **Arguments against:**
  - **Complexity**: event sourcing adds significant complexity (event schema versioning, projection management, snapshotting) that the project does not need.
  - **Query overhead**: reconstructing historical state requires replaying events, which is slow for ad-hoc queries.
  - **The triple-versioning model achieves sufficient auditability**: by snapshotting Content, Templates, and Algorithm at publish time, the system can replay any Attempt without full event sourcing.
- **Why rejected:** Event sourcing is a strong pattern but overkill for this project. Triple versioning with snapshots achieves the auditability and replayability goals with less complexity. Event sourcing may be revisited for specific contexts (e.g., Billing) in the future.

---

## Pros

- **Full Attempt replayability**: given an Attempt's three version references and its seed, the Engine can reconstruct the exact Question Instance, score the Answer, and recompute the Mastery Score — exactly as it was at Attempt time.
- **Full Mastery Score reconstructibility**: given a Learner's Attempt history and the Algorithm Version log, the Engine can reconstruct any historical Mastery Score exactly.
- **Independent evolution**: Content, Templates, and Algorithm evolve at their own paces without forcing simultaneous upgrades.
- **Auditability**: every decision (which content, which template, which algorithm) is traceable to a specific version. The Engine can answer "why was this Mastery Score 0.78?" with a concrete reference.
- **ML retraining foundation**: the Attempt corpus with triple versioning is the dataset for future ML training (ADR-0007); the versioning ensures the dataset is consistent and interpretable.
- **Rollback safety**: a Content Version or Algorithm Version can be deprecated (preventing new serves) without affecting historical Attempts, because the old versions are preserved.
- **Bug isolation**: a bug in a specific Algorithm Version can be identified (all Mastery Scores under that version are suspect) and corrected via a new version, without affecting other versions.

---

## Cons

- **Storage overhead**: three version references per Attempt, plus the version snapshots themselves. (Mitigated by the fact that version references are integers/UUIDs; the snapshots are stored once and referenced many times.)
- **Complexity**: engineers must understand three versioning axes and their independence. (Mitigated by documentation and by the glossary's clear definitions.)
- **Recompute cost**: when a new Algorithm Version ships, a background job recomputes all Mastery Scores under the new version. This is a multi-day job at scale. (Mitigated by the outbox pattern and background workers; the recompute is idempotent and resumable.)
- **Version drift visibility**: Learners may be confused if their Mastery Score changes after an Algorithm Version upgrade. (Mitigated by communicating the upgrade in advance and by surfacing the version in the UI.)

---

## Consequences

- Every Attempt record carries `content_version_id`, `template_version_id`, `algorithm_version_id`.
- Every Mastery Score record carries `algorithm_version_id`.
- Content Versions are created atomically on Content Pack publish (ADR-0009).
- Template Versions are bumped on every Template edit; old versions are preserved indefinitely.
- Algorithm Versions are bumped on every algorithm change; promotion is gated by the evaluation protocol (ADR-0007).
- A recompute job (background worker) backfills Mastery Scores when a new Algorithm Version ships; the job is idempotent and resumable.
- The Admin Portal exposes the version history for audit.
- The glossary (Task 002) defines Content Version, Template Version, Algorithm Version, and Version (the umbrella term), with the Synonym Table distinguishing them.
- The Naming Standards ensure version fields are consistently named (`*_version_id`).

---

## Risks

- **Version reference loss**: an Attempt's version references are lost (e.g., a migration bug), breaking replayability. *Mitigation:* version references are NOT NULL with foreign keys; migrations are tested against full-size staging copies; backups protect against data loss.
- **Snapshot inconsistency**: a Content Version snapshot is internally inconsistent (e.g., a Concept references a Learning Objective not in the snapshot). *Mitigation:* Content Validation (ASD Section 7.10) runs at publish time; inconsistent snapshots are rejected.
- **Recompute job failure**: the Algorithm Version recompute job fails partway, leaving some Mastery Scores on the old version and some on the new. *Mitigation:* the job is idempotent and resumable; it tracks progress per Learner; it can be re-run from the last checkpoint.
- **Version proliferation**: Template Versions proliferate (every typo fix bumps a version), producing version-graph bloat. *Mitigation:* versions are lightweight (immutable references); the storage cost is modest; old versions are preserved but not actively served.
- **Learner-visible version confusion**: Learners see their Mastery Score change after an Algorithm Version upgrade and lose trust. *Mitigation:* communicate upgrades in advance; surface the version in the UI with an explanation; ensure upgrades are improvements (the promotion gate, ADR-0007).

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Version reference storage overhead**: the version references per Attempt consume more than 5% of the Attempt record's storage, indicating that the versioning model is too heavyweight.
2. **Recompute job duration**: the Algorithm Version recompute job takes more than 7 days at scale, indicating that the recompute strategy needs optimization (e.g., incremental recompute, parallel recompute).
3. **Version graph complexity**: the version graph (which Content Version contains which Template Versions) becomes too complex to query efficiently, indicating that a different versioning model (e.g., event sourcing) may be needed.
4. **Cross-version consistency demand**: a feature requires consistency across versions (e.g., comparing Mastery Scores across Algorithm Versions), justifying a new versioning dimension or a projection.

**Expected review action:** When any trigger fires, the architecture review group evaluates the versioning model. Changes to the triple-versioning model are significant and require a new ADR. The triple-versioning model is the default; deviations require strong justification.

---

## Related ADRs

- **Depends on:** ADR-0009 (Human-authored curriculum) — Content Versions and Template Versions are produced by the Content Pipeline.
- **Depends on:** ADR-0007 (Deterministic Scheduling before ML) — Algorithm Versions are the versioning dimension for the deterministic algorithm and for future ML models.
- **Informs:** ADR-0012 (Outbox Pattern + Domain Events) — version references are included in domain events for cross-context consistency.

---

## Related Architecture Sections

- ASD Section 7.9 — Versioning (triple versioning).
- ASD Section 4.7 — Cross-Context Aggregates (Content Version as an aggregate).
- ASD Section 6.7 — Future ML Integration (Algorithm Version as the model registry's version).
- ASD Section 6.8 — Mastery Engine Invariants (M2: versioned; M4: event-sourced reconstruction).

---

## Related Glossary Terms

- Version
- Content Version
- Template Version
- Algorithm Version
- Attempt
- Mastery Score
- Question Instance

---

*End of ADR-0011.*
