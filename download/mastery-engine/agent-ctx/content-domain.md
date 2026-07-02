# Task: content-domain — Content bounded context (domain layer)

**Agent:** content-domain
**Started:** 2026-07-02
**Status:** ✅ Complete
**Scope:** `backend/app/domain/content/` (pure Python, no infrastructure)

## Objective

Implement the Content bounded context of the Mastery Engine domain layer:
four aggregate roots (`Subject`, `Concept`, `QuestionTemplate`,
`ContentPack`), three entities (`LearningObjective`, `Misconception`,
`ContentVersion`), two value objects (`ConceptDependency`,
`TemplateVersion`), 23 domain events, 20 context-specific exceptions,
and five abstract repository contracts.

## Files written

| Path | Purpose | Lines |
| --- | --- | --- |
| `backend/app/domain/content/exceptions.py` | `ContentError` base + 19 specific exception subclasses spanning Subject, Concept, LearningObjective, QuestionTemplate, ContentVersion, and ContentPack invariant violations. | 367 |
| `backend/app/domain/content/events.py` | 23 frozen-dataclass domain events inheriting from `DomainEvent`, all `kw_only=True` so required fields like `subject_id` can follow the inherited defaulted `event_id`/`occurred_at` fields. Covers all six aggregates/entities. | 468 |
| `backend/app/domain/content/concept_dependency.py` | `ConceptDependency` frozen-dataclass value object. Fields: source/target concept ids, dependency_type, weight. Invariant: source ≠ target (self-dep rejected in `__post_init__`). Convenience predicates (`is_prerequisite`, `is_strong`) and a `matches(target_concept_id, dependency_type)` helper for the natural-key lookup. | 116 |
| `backend/app/domain/content/subject.py` | `Subject` aggregate root. Factory `Subject.create(...)` creates subject in `DRAFT` with `minimum_content_ready=False`. Implements draft→published→deprecated state machine. `mark_minimum_content_ready()` is the application-layer gate; `publish()` raises `SubjectNotPublishable` if not ready. Field validation: code/slug/name/description lengths and non-emptiness. | 420 |
| `backend/app/domain/content/concept.py` | `Concept` aggregate root. Factory `Concept.create(...)`. Methods: `add_dependency` (with optional `target_subject_id` for cross-subject enforcement), `remove_dependency`, `revise` (draft only, returns changed-fields dict), `publish`, `deprecate`. Invariants: no self-dep, no duplicate `(target,type)` pair, optional same-subject check, no mutations on deprecated. Also adopts child `LearningObjective` and `Misconception` entities via `add_learning_objective` / `add_misconception` (records their creation events on the Concept's own event stream). | 754 |
| `backend/app/domain/content/learning_objective.py` | `LearningObjective` entity. Factory `LearningObjective.create(concept_id, statement)`. Invariant: statement must be > 10 chars (raises `LearningObjectiveStatementTooShort`). Strips whitespace. `pull_creation_event()` lets the parent Concept aggregate record the event on its own stream. | 165 |
| `backend/app/domain/content/misconception.py` | `Misconception` entity. Factory `Misconception.create(learning_objective_id, name, description, remediation)`. Field validation: non-empty name/description, string remediation (may be empty during drafting). Same `pull_creation_event()` pattern as LearningObjective. | 210 |
| `backend/app/domain/content/template_version.py` | `TemplateVersion` frozen-dataclass value object. 11 fields covering the six authoring payloads (parameter_schema, prompt_template, correct_answer_generator, distractor_generator, explanation_template) plus difficulty/discrimination estimates plus identity (id, template_id, content_version_id, version_number) plus published_at. `__post_init__` validates dict-typed fields. Truly immutable (frozen dataclass). | 197 |
| `backend/app/domain/content/question_template.py` | `QuestionTemplate` aggregate root. Factory `QuestionTemplate.create(subject_id, code, question_type)`. Methods: `add_version` (sequential `VersionNumber` enforcement), `publish(version_id)` (draft→published, designates current version; also rotates current version on an already-published template), `deprecate`. Stores appended-only `TemplateVersion` history. | 530 |
| `backend/app/domain/content/content_version.py` | `ContentVersion` entity (with its own repository — see ADR-0012 rationale in module docstring). Factory `ContentVersion.create(...)`. Methods: `publish` (typically orchestrated by ContentPack), `deprecate`. Restricts status to {draft, published, deprecated}. Mirrors AggregateRoot's event-collection surface so the entity can be persisted independently. | 354 |
| `backend/app/domain/content/content_pack.py` | `ContentPack` aggregate root. Factory `ContentPack.create(subject_id, author_id, name, description)`. Methods: `add_artifact`/`remove_artifact` (draft only), `submit_for_review` (draft→in_review), `approve(stage, reviewer_id)` (records stage approval; fresh cycle on re-submit), `request_changes(reviewer_id, notes)` (in_review→draft, clears approvals), `reject(reviewer_id, reason)` (in_review→rejected terminal), `publish(content_version_id)` (in_review→published terminal, requires all required stages approved). `DEFAULT_REQUIRED_STAGES` constant = {peer_review, editorial_review, qa_pilot}; overridable per pack. | 750 |
| `backend/app/domain/content/repository.py` | Five abstract `ABC` repositories — `SubjectRepository`, `ConceptRepository`, `QuestionTemplateRepository`, `ContentVersionRepository`, `ContentPackRepository` — all with `async` methods matching the Identity context pattern. Each repository exposes abstract `get_by_id`/`add`/`save` (or `add`-only upsert for ContentVersion) plus per-aggregate natural-key lookups (`get_by_slug`, `get_by_code`, `list_by_subject`, `list_by_status`, `get_active_by_subject`). Non-abstract `get_by_id_or_raise` convenience helpers raise `EntityNotFound`. | 501 |
| `backend/app/domain/content/__init__.py` | Re-exports the full public surface: 4 aggregates, 3 entities, 2 value objects, 1 constant (`DEFAULT_REQUIRED_STAGES`), 23 events, 20 exceptions, 5 repositories (58 `__all__` entries). | 178 |

**Total: 13 files, ~5,010 lines.**

## State machines enforced

```
Subject:    DRAFT ──publish()──► PUBLISHED ──deprecate()──► DEPRECATED
Concept:    DRAFT ──publish()──► PUBLISHED ──deprecate()──► DEPRECATED
QuestionTemplate:
            DRAFT ──publish(version_id)──► PUBLISHED ──deprecate()──► DEPRECATED
                       (also: PUBLISHED + publish(new_version_id) rotates current)
ContentVersion:
            DRAFT ──publish()──► PUBLISHED ──deprecate()──► DEPRECATED
ContentPack:
            DRAFT ──submit_for_review()──► IN_REVIEW
                   ◄──request_changes()──┐
                   │                      │
                   │   approve(stage) per required stage
                   │                      │
                   │                      ▼
                   │            (all stages approved)
                   │                      │
                   │              publish(content_version_id)
                   │                      │
                   │                      ▼
                   │                  PUBLISHED (terminal)
                   │
                   │   reject(reviewer_id, reason)
                   │                      │
                   │                      ▼
                   │                  REJECTED (terminal)
                   └── (after rework, author submits again)
```

Every transition checks current status and raises a context-specific
exception or `InvalidStateTransition` on mismatch. Every transition
calls `self._record_event(...)`.

## Invariants enforced

**Subject**:
- `publish()` requires `minimum_content_ready == True` (raises
  `SubjectNotPublishable`).
- `publish()` from PUBLISHED raises `SubjectAlreadyPublished`; from
  DEPRECATED raises `InvalidStateTransition`.
- `deprecate()` requires PUBLISHED; from DEPRECATED raises
  `SubjectAlreadyDeprecated`; from DRAFT raises `InvalidStateTransition`.
- Field validation: non-empty code/name/slug, length limits.

**Concept**:
- `add_dependency(target=c.id)` raises `ConceptSelfDependency`.
- `add_dependency` with duplicate `(target,type)` raises
  `ConceptDuplicateDependency`.
- `add_dependency(..., target_subject_id=other)` raises
  `ConceptDependencySubjectMismatch`. `target_subject_id` is optional —
  when omitted, the cross-subject check is deferred to the application
  service (which has access to a `ConceptRepository`).
- `add_dependency` / `remove_dependency` on a deprecated Concept raises
  `InvalidStateTransition`.
- `revise()` only allowed in DRAFT; raises `InvalidStateTransition` on
  published/deprecated.
- `remove_dependency` for a non-existent pair raises
  `ConceptDependencyNotFound`.
- On (re)construction from persistence, `_validate_dependencies()`
  re-checks source-id consistency and uniqueness — catches corrupt
  state from older code paths.

**ConceptDependency (value object)**:
- `source_concept_id == target_concept_id` raises `InvariantViolation`
  in `__post_init__`.

**LearningObjective**:
- `statement` ≤ 10 chars (after strip) raises
  `LearningObjectiveStatementTooShort`.
- Max 500 chars; whitespace stripped.

**Misconception**:
- Non-empty `name` and `description` (raises `InvariantViolation`).
- `remediation` must be a string (may be empty during drafting).

**TemplateVersion (value object, frozen)**:
- `parameter_schema`, `prompt_template`, `correct_answer_generator`,
  `explanation_template` must be dicts.
- `distractor_generator` must be a dict or `None`.
- `difficulty_estimate` must be a `DifficultyEstimate`.
- `discrimination_estimate` must be a `DiscriminationEstimate`.
- All fields immutable after construction (frozen dataclass).

**QuestionTemplate**:
- `add_version` enforces sequential `VersionNumber` (1, then 2, then
  3...).
- `add_version` rejects versions whose `template_id` doesn't match.
- `publish(version_id)` rejects unknown `version_id`.
- `publish(version_id)` on an already-published template where
  `version_id == current_version_id` raises
  `QuestionTemplateAlreadyPublished`.
- `deprecate()` requires PUBLISHED; from DEPRECATED raises
  `QuestionTemplateAlreadyDeprecated`.
- On (re)construction, `_validate_versions()` re-checks that every
  version's `template_id` matches, no duplicate ids/numbers, and
  `current_version_id` (if set) exists in the history.

**ContentVersion**:
- `changelog` must be a non-empty string.
- `version_number` must be a `VersionNumber` (>= 1).
- Status restricted to {DRAFT, PUBLISHED, DEPRECATED}.
- `deprecate()` requires PUBLISHED; from DEPRECATED raises
  `ContentVersionAlreadyDeprecated`.

**ContentPack**:
- `add_artifact` / `remove_artifact` only allowed in DRAFT.
- `submit_for_review` requires DRAFT; from IN_REVIEW raises
  `ContentPackAlreadySubmitted`; from terminal states raises
  `ContentPackAlreadyPublished` / `ContentPackAlreadyRejected`.
- `approve`, `request_changes`, `reject` all require IN_REVIEW.
  Terminal states short-circuit via `_assert_not_terminal()` to raise
  `ContentPackAlreadyPublished` / `ContentPackAlreadyRejected`; DRAFT
  raises `ContentPackNotInReview`.
- `approve(stage)` requires `stage ∈ required_stages`; duplicate stage
  approval raises `ContentPackStageAlreadyApproved`.
- `request_changes(reviewer_id, notes)` requires non-empty `notes`,
  returns pack to DRAFT, **clears all approved_stages** (fresh review
  cycle required).
- `reject(reviewer_id, reason)` requires non-empty `reason`; REJECTED
  is terminal.
- `publish(content_version_id)` requires `is_review_complete` (every
  `required_stage` approved); raises `ContentPackReviewIncomplete`
  listing the missing stages. PUBLISHED is terminal.
- Status restricted to {DRAFT, IN_REVIEW, PUBLISHED, REJECTED}.

## Validation

- All 13 files parse cleanly under Python 3.13 (`ast.parse` + `compile`).
- All imports resolve end-to-end
  (`from app.domain.content import *` exposes 58 symbols).
- Comprehensive smoke test (140 assertions across 8 sections) covers:
  Subject full lifecycle + min-content gate + idempotent
  `mark_minimum_content_ready` + all state-transition guards + field
  validation; ConceptDependency value equality + self-dep rejection +
  predicates; Concept full lifecycle + add/remove dependency with
  self/duplicate/subject-mismatch/not-found guards + revise (with
  no-op detection) + publish/deprecate guards + deprecated-mutation
  guard + revise-on-published guard; LearningObjective too-short
  rejection + event pull pattern; Misconception validation + event
  pull pattern; TemplateVersion construction + bad-schema rejection +
  frozen immutability; QuestionTemplate full lifecycle + version
  sequencing + publish rotation + deprecate guards; ContentVersion
  full lifecycle + empty-changelog rejection + deprecate guards;
  ContentPack full state machine including artifact management, all
  five terminal-state guards, stage-approval bookkeeping,
  review-incomplete publish rejection, request_changes clearing
  approvals, reject terminality; all five repositories refuse ABC
  instantiation; `get_by_id_or_raise` raises `EntityNotFound`.
  **140 passed, 0 failed.**
- Verified no infrastructure imports leak in (no `sqlalchemy`,
  `fastapi`, `pydantic`, `redis`, `asyncpg`, `alembic`, `uvicorn`,
  `structlog`, `httpx`, `passlib`, `jwt`, `orjson`, `starlette`).
  Only stdlib + `app.domain.shared` + intra-package imports.
- `ruff check --fix` applied (auto-fixed F401, I001, UP017). The
  remaining 69 warnings are all in categories the shared kernel and
  Identity context themselves trigger:
  - TC001/TC003 (typing-only imports) — pervasive in the kernel.
  - N818 (exception name suffix) — same as Identity's
    `EmailAlreadyRegistered`, etc.
  - A002 (`id` builtin shadowing) — required by the shared
    `Entity._identity_key = getattr(self, "id", None)` convention.
  - RUF002 (unicode dashes in docstrings) — same as Identity.
  - RUF022 (unsorted `__all__`) — Identity also groups entries with
    comments.
  - ERA001 (commented-out code) — false positives on decorative
    section dividers like `# Lifecycle: publish / deprecate`; same
    pattern as Identity's `# ----- Internal helpers -----`.
  - C901 (complex structure) — one occurrence on
    `ContentPack._validate_invariants`, which is a many-field
    validation method (same situation as Identity's
    `UserProfile._validate`).
  Style is consistent with the existing domain layer; the project
  does not strictly enforce these rules.

## Notes for downstream agents

- **Constructor visibility**: every aggregate root's `__init__` is
  public and intended for **reconstitution** from persistence
  (repositories use it to rebuild aggregates from stored state).
  New aggregates go through the `create()` classmethod factories,
  which emit the corresponding `*Created` event.
- **`ContentVersion` is an entity with its own repository**, not an
  aggregate root. This is a deliberate deviation from the strict
  "one-aggregate-per-repository" rule — putting it inside the Subject
  aggregate would make Subject a god-aggregate over every Concept and
  QuestionTemplate in the tenant. See the module docstring in
  `content_version.py` (references ADR-0012). To support this, the
  entity mirrors `AggregateRoot`'s `_record_event`/`collect_events`/
  `clear_events` surface so it can be persisted independently.
- **`ContentPack.publish(content_version_id)` does not also publish
  the bound `ContentVersion`**. The application service is responsible
  for calling `ContentVersion.publish()` in the same transaction —
  that step lives outside the ContentPack aggregate because
  `ContentVersion` is not part of the ContentPack aggregate boundary.
- **`Concept.add_dependency` signature extension**: the spec listed
  `add_dependency(target_concept_id, dependency_type, weight)`. The
  implementation extends this with an optional keyword-only
  `target_subject_id: SubjectId | None = None`. When provided, the
  aggregate verifies the target is in the same Subject (raising
  `ConceptDependencySubjectMismatch`); when omitted, the cross-subject
  check is deferred to the application service. This honours the
  spec's positional signature while enabling domain-level enforcement
  of the "same subject" invariant.
- **`QuestionTemplate.publish(version_id)` serves double duty**: it
  transitions a draft template to published **and** rotates the
  current version of an already-published template. The latter use
  case (rolling out a new version of an existing template) is the
  only way to change `current_version_id` after publication.
- **`ContentPack` review cycle semantics**: a fresh
  `submit_for_review()` call clears all previously-recorded stage
  approvals (a fresh review cycle starts). This means a pack that
  was peer-reviewed, then sent back via `request_changes`, must be
  peer-reviewed again after the author resubmits — there is no
  "approve-stands" carry-over. This is a deliberate safety choice:
  changes invalidate prior approvals.
- **`DEFAULT_REQUIRED_STAGES`** is exposed as a module-level constant
  for application services that need to reference the default set
  (e.g., to display the review pipeline in the UI). Per-pack override
  is available via the `required_stages` constructor argument for
  tenants with simpler workflows.
- **Event-pull pattern for child entities**: `LearningObjective` and
  `Misconception` use a `pull_creation_event()` method to hand their
  creation event to the parent `Concept` aggregate, which records it
  on its own event stream. This keeps the event stream per-aggregate-
  transaction consistent (one stream per save, not per entity).
- **Repository method `add` vs `save`**: `add` is for new aggregates
  (created via `*create()` factories); `save` is for aggregates loaded
  via `get_by_*` and then mutated. `ContentVersionRepository` has
  only `add` (upsert by id) — see the repository docstring for the
  rationale.
- **Async contract**: all repository methods are `async` to match the
  async SQLAlchemy pattern used in `backend/app/infrastructure/database.py`.
  The application layer awaits repository calls inside an async
  unit-of-work.
- **Concurrency contract**: implementations should enforce optimistic
  concurrency via a version column. Uniqueness of natural keys
  (`code`, `slug`) must be enforced by the persistence store via
  unique indexes — surfaced as `DuplicateEntity` at the application
  layer's discretion.
