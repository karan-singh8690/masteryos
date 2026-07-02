# 08 — Versioning Strategy

> Triple versioning (Content Version, Template Version, Algorithm Version) for historical reproducibility.
> Implements ADR-0011.

---

## Versioning Principles

The Mastery Engine's data moat (ASD Section 1.2) depends on the Attempt corpus being interpretable and replayable indefinitely. An Attempt recorded today must be meaningful five years from now, even if:
- The content has been revised (new Concepts, edited Templates).
- The Mastery Engine algorithm has been upgraded.

Triple versioning (ADR-0011) solves this by recording, on every Attempt, the three independent versions under which it was created and scored:

1. **Content Version** — the subject-wide content snapshot at the time of the Attempt.
2. **Template Version** — the specific Question Template snapshot that produced the Question Instance.
3. **Algorithm Version** — the Mastery Engine algorithm under which the resulting Mastery Score was computed.

These three versions are **independent**: a Content Version bump does not change the Algorithm Version, and a Template Version bump does not change the Content Version of other Templates.

---

## The Three Version Axes

### 1. Content Version

- **Granularity**: subject-wide snapshot.
- **Stored in**: `content.content_versions`.
- **Bumped**: atomically when one or more `content.content_packs` publish.
- **Referenced by**: `attempts.content_version_id`, `question_instances.content_version_id`, `template_versions.content_version_id`, `analytics.concept_statistics.content_version_id`.
- **Contents**: an immutable snapshot of the subject's entire content graph (concepts, dependencies, objectives, misconceptions, template versions) at publish time.

**Why subject-wide, not per-artifact**: a subject's content graph is interdependent (concepts reference objectives; templates reference objectives and concepts; dependencies form a graph). Versioning individual artifacts would require tracking consistency across artifact versions, which is complex and error-prone. A subject-wide snapshot guarantees consistency: if you know the content version, you know the entire graph state.

**What the snapshot contains**: the `content_versions` row itself contains metadata (version number, status, changelog). The actual content is in the regular content tables (`concepts`, `template_versions`, etc.), which carry their own versioning. A content version is effectively a "label" that says "at this moment, these were the current versions of all artifacts." The application reconstructs the snapshot by querying artifacts with `published_at <= content_version.published_at` and `deprecated_at IS NULL OR deprecated_at > content_version.published_at`.

**Alternative considered**: storing the full content graph as JSONB in `content_versions`. Rejected because it duplicates data and complicates queries. The "label" approach is lighter and sufficient.

---

### 2. Template Version

- **Granularity**: per Question Template.
- **Stored in**: `content.template_versions`.
- **Bumped**: on every edit to a Template (new version; old version preserved).
- **Referenced by**: `question_instances.template_version_id`, `attempts.template_version_id`, `template_objectives.template_version_id`, `template_concepts.template_version_id`, `distractors.template_version_id`, `hints.template_version_id`, `explanations.template_version_id`, `analytics.template_statistics.template_version_id`.
- **Contents**: the full Template specification (parameter schema, prompt template, correct-answer generator, distractor generator, explanation template, difficulty estimate, discrimination estimate) as immutable JSONB.

**Why per-Template, not subject-wide**: a Template edit (e.g., fixing a distractor generator bug) should not bump the Content Version of other Templates. Per-Template versioning allows independent evolution while the Content Version groups them into consistent snapshots.

**Relationship to Content Version**: a Content Version contains many Template Versions (one per published Template at that moment). A Template Version belongs to exactly one Content Version (`template_versions.content_version_id`).

---

### 3. Algorithm Version

- **Granularity**: the entire Mastery Engine algorithm.
- **Stored in**: `mastery.algorithm_versions`.
- **Bumped**: on every change to the Mastery Engine algorithm (scoring function, decay model, Review Interval logic).
- **Referenced by**: `mastery.mastery_scores.algorithm_version_id`, `mastery.reviews.algorithm_version_id`, `attempts.algorithm_version_id`.
- **Contents**: the algorithm parameters (decay rates, weights, thresholds) as immutable JSONB, plus a changelog.

**Why algorithm-wide, not per-concept or per-learner**: the algorithm is a single coherent function; versioning it per-concept or per-learner would fragment the model and make reconstruction impossible. Algorithm-wide versioning keeps the model coherent.

**Promotion gate** (per ADR-0007): a new Algorithm Version is promoted to production only after passing a documented evaluation (reproducibility on historical Attempts, no regression on retention metrics, human sign-off). The promotion is recorded as `is_active = true` on the new version and `is_active = false` on the old.

---

## How Triple Versioning Enables Reproducibility

### Replay an Attempt

Given an `attempts.id`, the Engine can reconstruct the exact Question Instance and re-score the Answer:

```sql
-- 1. Fetch the attempt
SELECT * FROM assessment.attempts WHERE id = $attempt_id;

-- 2. Fetch the question instance
SELECT * FROM assessment.question_instances WHERE id = $attempt.question_instance_id;

-- 3. Fetch the template version
SELECT * FROM content.template_versions WHERE id = $attempt.template_version_id;

-- 4. Fetch the content version (for context)
SELECT * FROM content.content_versions WHERE id = $attempt.content_version_id;

-- 5. Re-instantiate the question from the template version + seed
-- (Application re-runs the correct-answer generator and distractor generator
--  with the recorded parameter_seed and parameter_values.)

-- 6. Re-score the answer
-- (Application re-runs the Assessment Domain Service with the recorded answer
--  and the template version's scoring rubric.)
```

The re-scored outcome matches the recorded `scoring_outcome` exactly (assuming no bugs in the recording). This is the foundation of auditability and the basis for future ML retraining (ADR-0007).

### Reconstruct a Mastery Score

Given a `learner_enrollment_id` and a `concept_id`, the Engine can reconstruct the Mastery Score at any point in time:

```sql
-- 1. Fetch all attempts by this learner on this concept, up to the target time
SELECT a.*
FROM assessment.attempts a
JOIN content.template_versions tv ON a.template_version_id = tv.id
JOIN content.template_concepts tc ON tv.id = tc.template_version_id
WHERE a.learner_enrollment_id = $enrollment_id
  AND tc.concept_id = $concept_id
  AND a.created_at <= $target_time
ORDER BY a.created_at;

-- 2. Fetch the algorithm version active at the target time
SELECT * FROM mastery.algorithm_versions
WHERE promoted_at <= $target_time
ORDER BY version_number DESC
LIMIT 1;

-- 3. Re-run the Mastery Engine algorithm on the attempt history
-- (Application applies the algorithm's scoring function, decay model,
--  and review interval logic to the attempt sequence.)
```

The reconstructed Mastery Score matches the recorded `mastery_scores` row (assuming no bugs and that no recompute job has updated it since). This is invariant M1 (pure function) and M4 (event-sourced reconstruction) from ASD Section 6.8.

### Audit a Decision

When a learner asks "why was I served this question?" or "why is my mastery 0.78?", the Engine can answer concretely:

- "You were served this question because, under Content Version 3 and Algorithm Version 1, your Mastery Score for this concept was 0.45 (Weak), and the Scheduler's priority computation ranked it highest."
- "Your mastery is 0.78 because, under Algorithm Version 1, your 12 attempts on this concept (recorded under Content Versions 2 and 3, Template Versions 4 and 5) produced a Memory Score of 0.91 and a durable Mastery Score of 0.75, combined as 0.78."

This auditability is a competitive differentiator (serious learners value transparency) and a regulatory safeguard.

---

## Versioning Lifecycle

### Content Version Lifecycle

1. **Draft**: an Instructor authors content (Concepts, Objectives, Misconceptions, Templates) as a `content_pack` in draft state.
2. **Review**: the pack goes through the Review Workflow (peer, editorial, QA/pilot).
3. **Publish**: on approval, a new `content_versions` row is created atomically. All artifacts in the pack are linked to this content version. The previous content version's `status` remains `active` (multiple active versions can coexist during migration) until explicitly deprecated.
4. **Active**: the new content version is served to new learners and to existing learners who migrate.
5. **Deprecated**: when no longer needed (e.g., all learners have migrated), the content version is deprecated (`status = 'deprecated'`, `deprecated_at = now()`). It is not deleted; historical Attempts still reference it.
6. **Archived**: deprecated content versions are retained indefinitely (they are snapshots, not active data). Cold storage is optional for very old versions.

### Template Version Lifecycle

1. **Draft**: an Instructor edits a Template (creating a new draft version).
2. **Review**: the draft goes through the Review Workflow as part of a content pack.
3. **Publish**: on pack publish, the new `template_versions` row is created and linked to the content version. The `question_templates.current_version_id` is updated to point to the new version.
4. **Active**: the new template version is served to new Question Instances.
5. **Deprecated**: when no longer needed, the template version is deprecated. Historical Attempts and Question Instances still reference it.
6. **Archived**: retained indefinitely.

### Algorithm Version Lifecycle

1. **Draft**: an engineer develops a new algorithm (offline, against historical data).
2. **Shadow evaluation**: the new algorithm runs in shadow mode (per ADR-0007), receiving the same inputs as the production algorithm and logging its outputs without using them.
3. **Evaluation**: the algorithm is evaluated against the documented protocol (reproducibility, no regression on retention metrics).
4. **Promotion**: on passing the evaluation and human sign-off, a new `algorithm_versions` row is created with `is_active = true`. The previous version's `is_active` is set to `false`. The promotion is recorded in `audit_logs`.
5. **Recompute**: a background job recomputes all `mastery_scores` and `reviews` under the new algorithm version. The job is idempotent and resumable; it tracks progress per learner. During the recompute, the old scores remain (they are still referenced by historical Attempts).
6. **Active**: the new algorithm version is used for all new Mastery Score computations.
7. **Superseded**: when a newer version is promoted, this version's `is_active` is set to `false`. It is not deleted; historical Mastery Scores still reference it.

---

## Versioning and the Single-Writer Rule

Each version table is written by exactly one context:
- `content_versions`, `template_versions`: written by `content` only.
- `algorithm_versions`: written by `mastery` only (via the promotion process).

No other context may modify version tables. This enforces the immutability invariant.

---

## Versioning and Partitioning

Version tables are small and stable; they are **not partitioned**. The high-volume tables (`attempts`, `mastery_scores`) reference versions via foreign keys, which is efficient because the version tables are small (fit in memory).

---

## Versioning and Schema Evolution

Version table schemas evolve slowly. When a version table's schema changes (e.g., adding a column to `algorithm_versions.parameters`), the change is backward-compatible (new column is nullable or has a default). Old version rows remain valid; new version rows use the new schema.

For breaking changes to version table schemas (rare), a new version table is created (e.g., `algorithm_versions_v2`) and the application reads from both, migrating old rows lazily. This is a last resort, documented in an ADR.

---

## Versioning and the Outbox

Domain events that carry version information (e.g., `AttemptRecorded` includes `content_version_id`, `template_version_id`, `algorithm_version_id`) enable cross-context consistency. A consumer that needs to replay an event can reconstruct the version context from the event payload.

Event payloads are versioned via `outbox_events.payload_schema_version` (per `04-physical-schema.md`). A breaking change to an event payload produces a new `payload_schema_version`; consumers handle both versions during migration.

---

## Summary

| Version Axis | Table | Granularity | Bumped When | Referenced By |
|---|---|---|---|---|
| Content Version | `content.content_versions` | Subject-wide | Content Pack publishes | `attempts`, `question_instances`, `template_versions`, `analytics.concept_statistics` |
| Template Version | `content.template_versions` | Per Template | Template edits | `attempts`, `question_instances`, `template_objectives`, `template_concepts`, `distractors`, `hints`, `explanations`, `analytics.template_statistics` |
| Algorithm Version | `mastery.algorithm_versions` | Algorithm-wide | Algorithm changes | `mastery.mastery_scores`, `mastery.reviews`, `attempts` |

Triple versioning is the foundation of the data moat. Every Attempt is replayable; every Mastery Score is reconstructible; every decision is auditable. This is what makes the historical learning data valuable indefinitely.

---

*End of Versioning Strategy.*
