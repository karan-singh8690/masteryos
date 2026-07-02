# 01 — Domain Model

> Every entity in the Mastery Engine database, with purpose, owner, relationships, lifecycle, business rules, expected size, growth rate, and access patterns.
> Entities are grouped by owning bounded context (PostgreSQL schema).

---

## How to Read This Document

Each entity follows the same template:

- **Purpose** — why this entity exists; the business problem it solves.
- **Owner** — the bounded context (PostgreSQL schema) that owns the entity; only this context may write to it.
- **Relationships** — cardinality with other entities.
- **Lifecycle** — create, update, archive, delete behavior.
- **Business Rules** — invariants the database or application enforces.
- **Expected Size** — estimated row count at maturity (1M learners).
- **Growth Rate** — how fast the table grows.
- **Access Patterns** — the dominant read/write patterns the table must support.

A "Why this table exists" section precedes each entity, satisfying the brief's additional requirement.

---

# Schema: `identity`

The Identity context owns user identity, credentials, sessions, and authentication.

---

## users

**Why this table exists:** The `users` table is the root identity of every person on the platform. Without it, there is no concept of "who is learning." It is the anchor for all per-user data: credentials, sessions, attempts, mastery scores, subscriptions. It is intentionally minimal (identity only); profile data lives in `user_profiles` and learning data lives in other schemas, so that identity changes (e.g., account merge) do not ripple through learning data.

- **Purpose:** Store the root identity of every user: a unique, immutable identifier and a verified email. Carries no learning state.
- **Owner:** `identity`
- **Relationships:**
  - 1:1 with `user_profiles`
  - 1:many with `user_credentials` (password, OAuth providers)
  - 1:many with `sessions`
  - 1:many with `learners` (one user can be a learner in multiple subjects)
  - 1:many with `attempts` (via `learners`)
  - 1:many with `audit_logs` (as actor)
- **Lifecycle:**
  - Created at signup (email/password or OAuth).
  - Updated rarely (email verification status, account status).
  - Soft-deleted (`deleted_at` set) on deletion request; anonymized after 14-day grace period.
  - Never hard-deleted while attempts reference it (referential integrity).
- **Business Rules:**
  - Email is unique and verified before any subject enrollment.
  - `id` is immutable and never reused.
  - An account cannot be hard-deleted while it has non-anonymized attempts.
  - Status transitions: `pending_verification` → `active` → `suspended` | `deactivated` | `pending_deletion` → `anonymized`.
- **Expected Size:** ~1M rows at maturity (1M learners + instructors + admins).
- **Growth Rate:** Linear with signups; ~1,000–10,000/day at scale.
- **Access Patterns:**
  - Read by `id` (every authenticated request).
  - Read by `email` (login).
  - Write on signup, email verification, status change.
  - High read, low write.

---

## user_profiles

**Why this table exists:** Separates user-editable attributes (name, timezone, preferences) from identity (`users`) and credentials (`user_credentials`). This separation lets profile edits happen without touching authentication, and lets identity changes (e.g., account merge) preserve the profile. The profile carries no security-sensitive data.

- **Purpose:** Store user-facing attributes: name, timezone, preferences, avatar URL.
- **Owner:** `identity`
- **Relationships:**
  - 1:1 with `users`
- **Lifecycle:**
  - Created at signup with defaults.
  - Updated by the user in Settings.
  - Anonymized on account deletion (PII purged).
- **Business Rules:**
  - One profile per user.
  - Timezone must be a valid IANA timezone.
  - No security-sensitive data (no passwords, no tokens).
- **Expected Size:** ~1M rows (1:1 with users).
- **Growth Rate:** Linear with users.
- **Access Patterns:**
  - Read by `user_id` (dashboard, settings).
  - Write on profile edits.
  - High read, low write.

---

## user_credentials

**Why this table exists:** Stores authentication credentials (hashed passwords, OAuth provider links) separately from `users` so that credential rotation, OAuth linking/unlinking, and identity merge do not affect the user root or profile. Only the Identity context reads this table; no other context touches credentials.

- **Purpose:** Store hashed passwords and OAuth provider links for authentication.
- **Owner:** `identity`
- **Relationships:**
  - Many:1 with `users`
- **Lifecycle:**
  - Created at signup (password or OAuth) or when a user links a new OAuth provider.
  - Updated on password change.
  - Deleted when a user unlinks an OAuth provider (password credential is never deleted while the account is active).
- **Business Rules:**
  - Passwords stored as salted adaptive hash (argon2id); never plaintext.
  - A user must have at least one credential (password or OAuth) while active.
  - OAuth credentials store the provider's user ID, not an access token.
  - Password credential is unique per user (one password per user).
- **Expected Size:** ~1.5M rows (most users have 1 credential; some have password + 1 OAuth).
- **Growth Rate:** Linear with users.
- **Access Patterns:**
  - Read by `user_id` + `credential_type` (login).
  - Read by `provider` + `provider_user_id` (OAuth callback).
  - Write on credential changes.
  - High read (every login), low write.

---

## sessions

**Why this table exists:** Tracks authenticated sessions for revocation ("log out everywhere"), device fingerprinting, and security audit. Without it, the platform could not revoke a stolen session or show the user their active sessions. JWT access tokens are stateless, but refresh tokens require server-side state for rotation and revocation.

- **Purpose:** Store active session metadata: refresh token hash, device, IP, user-agent, expiry.
- **Owner:** `identity`
- **Relationships:**
  - Many:1 with `users`
- **Lifecycle:**
  - Created at login.
  - Updated on refresh token rotation.
  - Revoked on logout, on "revoke all sessions," or on expiry.
  - Hard-deleted after 90 days post-expiry (retention per `09-data-retention.md`).
- **Business Rules:**
  - Refresh tokens stored as salted hash (never plaintext).
  - Refresh token rotation produces a "token family"; replay of an old token revokes the family.
  - A user can have multiple active sessions (multi-device).
  - Sessions expire (default 30 days sliding).
- **Expected Size:** ~3M rows (3 active sessions per user average).
- **Growth Rate:** Linear with logins; high churn (sessions expire).
- **Access Patterns:**
  - Read by `refresh_token_hash` (token refresh).
  - Read by `user_id` (session list).
  - Write on login, refresh, revoke.
  - High read, high write (every request refreshes).

---

# Schema: `content`

The Content context owns the curriculum: subjects, concepts, dependencies, objectives, misconceptions, templates, explanations, and versioning.

---

## tenants

**Why this table exists:** The `tenants` table enforces content isolation. In the current architecture, each Subject is a Tenant (1:1); the table is reserved for future multi-Subject Tenants (e.g., a "backend interview" tenant containing Python + SQL + System Design). Modeling it separately from `subjects` preserves the future path without complicating the current 1:1 case.

- **Purpose:** Content-isolation boundary; each tenant's content is isolated from others.
- **Owner:** `content`
- **Relationships:**
  - 1:1 with `subjects` (current architecture).
  - 1:many with `content_versions`.
  - 1:many with `concepts`, `question_templates`, etc. (via subject).
- **Lifecycle:**
  - Created when a new subject is published.
  - Updated rarely (metadata).
  - Deprecated (not deleted) when a subject is retired.
- **Business Rules:**
  - Content is isolated per tenant; cross-tenant queries are explicit.
  - A learner's mastery state is per-tenant.
  - Tenancy is a data concept (ADR-0010), not a code fork.
- **Expected Size:** ~10–50 rows (one per subject + future multi-subject tenants).
- **Growth Rate:** Near-zero (new subjects are rare).
- **Access Patterns:**
  - Read by `id` (every content query filters by tenant).
  - Write on tenant creation.
  - Very high read, near-zero write.

---

## subjects

**Why this table exists:** A Subject is the top-level curriculum unit (Python, SQL, Java, etc.). It owns its concept graph, learning paths, and question templates. Modeling it separately from `tenants` (which is 1:1 today) preserves the future multi-subject tenant path and gives the curriculum a clear unit of organization.

- **Purpose:** Top-level curriculum unit; owns a knowledge graph, learning paths, and question templates.
- **Owner:** `content`
- **Relationships:**
  - 1:1 with `tenants` (current).
  - 1:many with `learning_paths`.
  - 1:many with `concepts`.
  - 1:many with `question_templates`.
  - 1:many with `content_versions`.
  - 1:many with `learner_enrollments` (via `learning` schema).
- **Lifecycle:**
  - Created as a draft by an administrator.
  - Populated by instructors (concepts, templates).
  - Published when initial curriculum reaches minimum viable size.
  - Versioned on every content publish.
  - Deprecated when retired; learners can finish in-flight sessions but no new enrollments.
- **Business Rules:**
  - A subject's knowledge graph is acyclic at any published version.
  - A subject cannot be deleted while it has enrolled learners.
  - Every published concept, objective, misconception, and template belongs to exactly one subject.
- **Expected Size:** ~10–50 rows (Python, SQL, Java, Cybersecurity, Cloud, IELTS, etc.).
- **Growth Rate:** Near-zero (new subjects are rare, ~1–2/year).
- **Access Patterns:**
  - Read by `id` (every content query filters by subject).
  - Read by `slug` (URLs).
  - Write on subject creation/publish.
  - Very high read, near-zero write.

---

## learning_paths

**Why this table exists:** A Learning Path is an ordered, opinionated traversal of a subject's knowledge graph. Without it, the Scheduler would optimize for short-term mastery gains without giving the learner a sense of progression. The path provides the spine; the Scheduler provides the day-to-day movement.

- **Purpose:** Ordered traversal of concepts within a subject, representing the recommended path to graduation.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `subjects`.
  - 1:many with `learning_path_items` (join table to concepts).
  - 1:many with `study_plans` (per-learner instances).
  - 1:many with `learner_enrollments` (a learner enrolls in a path).
- **Lifecycle:**
  - Authored by instructors as an ordered list of concept references.
  - Published as part of a content version.
  - Customized per learner (the learner's path instance may skip tested-out concepts).
  - Versioned; learners on an old version continue until they migrate.
- **Business Rules:**
  - A path's concept sequence must be a valid topological traversal of the knowledge graph (prerequisites before dependents).
  - A learner has at most one active path per subject at a time.
  - Graduation criteria are explicit (a set of concepts that must reach Mastered).
- **Expected Size:** ~100–500 rows (5–10 paths per subject × 10–50 subjects).
- **Growth Rate:** Low (new paths are rare; ~10/year).
- **Access Patterns:**
  - Read by `subject_id` (path selection).
  - Read by `id` (learner dashboard).
  - Write on authoring/publish.
  - High read, very low write.

---

## learning_path_items

**Why this table exists:** Join table that captures the ordering of concepts within a learning path. Without it, the path-concept relationship would be a many-to-many bag with no order; with it, the path is an ordered sequence that the Scheduler can traverse.

- **Purpose:** Ordered many-to-many between learning paths and concepts.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `learning_paths`.
  - Many:1 with `concepts`.
- **Lifecycle:**
  - Created/updated/deleted with the learning path.
  - Versioned with the content version.
- **Business Rules:**
  - `(learning_path_id, position)` is unique (no two concepts at the same position).
  - `(learning_path_id, concept_id)` is unique (no duplicate concepts in a path).
  - Position is 1-indexed and gapless.
- **Expected Size:** ~50,000 rows (500 paths × 100 concepts average).
- **Growth Rate:** Low (grows with new paths/concepts).
- **Access Patterns:**
  - Read by `learning_path_id` ordered by `position` (path traversal).
  - Write on path authoring.
  - High read, very low write.

---

## concepts

**Why this table exists:** A Concept is the atomic unit of knowledge. Without atomic concepts, mastery cannot be measured precisely (the Engine would have to score vague clusters). Concepts are the vertices of the knowledge graph; mastery is measured per concept.

- **Purpose:** Atomic knowledge unit; vertex in the knowledge graph.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `subjects`.
  - 1:many with `concept_dependencies` (as source or target).
  - 1:many with `learning_objectives`.
  - 1:many with `misconceptions`.
  - 1:many with `question_templates` (via template-concept links).
  - 1:many with `mastery_scores` (per learner).
  - Many:many with `learning_paths` (via `learning_path_items`).
- **Lifecycle:**
  - Authored as a draft by an instructor.
  - Reviewed in the Review Workflow.
  - Published as part of a content version.
  - Versioned on edit (old versions preserved).
  - Deprecated (not deleted) when superseded.
- **Business Rules:**
  - A concept belongs to exactly one subject.
  - A concept cannot be deleted while any attempt references it (deprecate instead).
  - A concept must have at least one learning objective before publishing.
  - `slug` is unique within a subject.
- **Expected Size:** ~5,000–20,000 rows (500–1000 concepts per subject × 10–20 subjects at maturity).
- **Growth Rate:** Low–medium (new concepts added as curriculum expands; ~100/month).
- **Access Patterns:**
  - Read by `id` (content rendering, mastery display).
  - Read by `subject_id` (knowledge graph traversal).
  - Read by `slug` + `subject_id` (URLs).
  - Write on authoring/publish.
  - Very high read, low write.

---

## concept_dependencies

**Why this table exists:** Edges in the knowledge graph. Without explicit dependencies, the Scheduler cannot respect prerequisite-readiness, and the Learning Path cannot be topologically ordered. The graph is acyclic at any published version.

- **Purpose:** Directed edge between concepts (prerequisite, related, reinforces).
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `concepts` (source).
  - Many:1 with `concepts` (target/prerequisite).
- **Lifecycle:**
  - Authored with the concept.
  - Validated at publish time (cycles rejected).
  - Versioned with the content version.
  - Deprecated (not deleted) when removed; old edges preserved for historical attempt interpretability.
- **Business Rules:**
  - The dependency graph is acyclic at any published version (enforced at publish via topological sort).
  - A dependency cannot be self-referential.
  - Dependency type and weight are mandatory.
  - `(source_concept_id, target_concept_id, dependency_type)` is unique.
- **Expected Size:** ~15,000–60,000 rows (3× the concept count, average 3 dependencies per concept).
- **Growth Rate:** Low (grows with concepts).
- **Access Patterns:**
  - Read by `source_concept_id` (what does this concept depend on?).
  - Read by `target_concept_id` (what depends on this concept?).
  - Write on authoring/publish.
  - High read (scheduler queries), very low write.

---

## learning_objectives

**Why this table exists:** A Learning Objective is a verifiable statement of what a learner should be able to do with a concept. Without objectives, mastery is a vague "understanding level"; with them, mastery is "the probability the learner can satisfy this concept's objectives." Objectives bridge curriculum design and assessment.

- **Purpose:** Verifiable skill statement linked to a concept; the bridge between curriculum and assessment.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `concepts`.
  - 1:many with `question_templates` (via template-objective links).
  - 1:many with `misconceptions` (a misconception violates an objective).
- **Lifecycle:**
  - Authored by an instructor for a concept.
  - Reviewed; vague objectives rejected at editorial review.
  - Published with the concept.
  - Versioned with the concept.
- **Business Rules:**
  - Every published concept has at least one learning objective.
  - Every published question template traces to at least one objective.
  - Every published misconception traces to an objective it violates.
  - Objectives are written in observable terms; vague objectives ("understand X") are rejected.
- **Expected Size:** ~15,000–60,000 rows (3 objectives per concept average).
- **Growth Rate:** Low (grows with concepts).
- **Access Patterns:**
  - Read by `concept_id` (content rendering).
  - Read by `id` (template authoring).
  - Write on authoring/publish.
  - High read, very low write.

---

## misconceptions

**Why this table exists:** A Misconception is a documented incorrect mental model. Without misconceptions, the Engine can only know that a learner was wrong; with them, the Engine knows why (via tagged distractors), enabling targeted remediation. Misconceptions are the Engine's most important content artifact after concepts.

- **Purpose:** Documented incorrect mental model; linked to distractors for diagnosis.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `learning_objectives` (a misconception violates an objective).
  - 1:many with `distractors` (tagged in templates).
  - 1:many with `learner_misconceptions` (per-learner misconception state).
- **Lifecycle:**
  - Authored by an instructor for a concept's objective.
  - Linked to question templates via tagged distractors.
  - Published with the concept.
  - Monitored post-publish; if never observed in learner errors, flagged for review.
- **Business Rules:**
  - Every published concept has at least one misconception per learning objective.
  - Every published misconception traces to an objective it violates.
  - A misconception must have at least one tagged distractor (else undetectable).
- **Expected Size:** ~30,000–120,000 rows (2 misconceptions per objective average).
- **Growth Rate:** Low (grows with objectives).
- **Access Patterns:**
  - Read by `learning_objective_id` (content rendering).
  - Read by `id` (distractor tagging, learner diagnosis).
  - Write on authoring/publish.
  - High read, very low write.

---

## question_templates

**Why this table exists:** A Question Template is the parameterized specification for generating question instances. Without templates, the Engine would need finite authored questions; with templates, one specification produces infinite practice material, and every attempt is replayable from the template + seed.

- **Purpose:** Parameterized specification for question generation; the unit of content authoring for assessment.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `subjects`.
  - Many:many with `learning_objectives` (via `template_objectives`).
  - Many:many with `concepts` (via `template_concepts`).
  - 1:many with `template_versions`.
  - 1:many with `distractors`.
  - 1:many with `hints`.
  - 1:many with `explanations`.
  - 1:many with `question_instances` (when served).
- **Lifecycle:**
  - Authored as a draft by an instructor.
  - Reviewed in the Review Workflow (peer, editorial, QA/pilot).
  - Published as part of a content version.
  - Versioned on edit (old versions preserved).
  - Deprecated (not deleted) when superseded.
- **Business Rules:**
  - A template must trace to at least one learning objective.
  - A template is deterministic given its version, parameter values, and seed.
  - The correct-answer generator must produce the correct answer for any valid parameter values.
  - Distractors must be tagged with a misconception or "none."
- **Expected Size:** ~50,000–200,000 rows (5–10 templates per concept).
- **Growth Rate:** Medium (new templates added continuously; ~500/month).
- **Access Patterns:**
  - Read by `id` (instantiation, analytics).
  - Read by `subject_id` + filters (scheduler selection).
  - Read by `concept_id` (via template_concepts).
  - Write on authoring/publish.
  - Very high read, low write.

---

## template_versions

**Why this table exists:** Snapshots of a question template at a moment in time. Without versioning, editing a template's correct-answer generator would make old attempts non-replayable. Template Version is the finest-grained versioning in the system (ADR-0011).

- **Purpose:** Immutable snapshot of a question template; the unit of historical reproducibility for attempts.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `question_templates`.
  - Many:1 with `content_versions` (a content version contains many template versions).
  - 1:many with `question_instances`.
  - 1:many with `attempts` (via question_instances).
- **Lifecycle:**
  - Created on first publish of a template.
  - Bumped on every edit (new version).
  - Immutable once created.
  - Never deleted while any attempt references it.
- **Business Rules:**
  - A template version is immutable.
  - A template version is preserved indefinitely while any attempt references it.
  - `(template_id, version_number)` is unique.
  - The template version's `parameter_schema`, `prompt_template`, `correct_answer_generator`, `distractor_generator`, and `explanation_template` are stored as immutable JSONB.
- **Expected Size:** ~150,000–600,000 rows (3 versions per template average).
- **Growth Rate:** Medium (grows with template edits).
- **Access Patterns:**
  - Read by `id` (attempt replay).
  - Read by `template_id` ordered by `version_number` (version history).
  - Write on publish.
  - High read, low write.

---

## template_objectives

**Why this table exists:** Join table capturing which learning objectives a question template tests. Without it, the template-objective relationship would be implicit (in JSONB), making it hard to query "which templates test this objective?" (needed for curriculum coverage analysis).

- **Purpose:** Many-to-many between question templates (via versions) and learning objectives.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `template_versions`.
  - Many:1 with `learning_objectives`.
- **Lifecycle:**
  - Created/updated with the template version.
  - Versioned with the content version.
- **Business Rules:**
  - Every published template version has at least one objective link.
  - `(template_version_id, learning_objective_id)` is unique.
- **Expected Size:** ~300,000–1,200,000 rows (2 objectives per template average).
- **Growth Rate:** Medium (grows with templates).
- **Access Patterns:**
  - Read by `template_version_id` (instantiation, scoring).
  - Read by `learning_objective_id` (coverage analysis).
  - Write on publish.
  - High read, very low write.

---

## template_concepts

**Why this table exists:** Join table capturing which concepts a question template exercises. Distinct from `template_objectives` because a template may test an objective that spans multiple concepts, or exercise a concept via multiple objectives. Both joins are needed for scheduler selection and analytics.

- **Purpose:** Many-to-many between question templates (via versions) and concepts.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `template_versions`.
  - Many:1 with `concepts`.
- **Lifecycle:**
  - Created/updated with the template version.
  - Versioned with the content version.
- **Business Rules:**
  - Every published template version has at least one concept link.
  - `(template_version_id, concept_id)` is unique.
- **Expected Size:** ~300,000–1,200,000 rows (2 concepts per template average).
- **Growth Rate:** Medium (grows with templates).
- **Access Patterns:**
  - Read by `template_version_id` (mastery update).
  - Read by `concept_id` (scheduler selection).
  - Write on publish.
  - Very high read (scheduler), very low write.

---

## distractors

**Why this table exists:** Stores the distractor generator specification per template version, with misconception tags. Without explicit distractor records, the diagnostic signal (which misconception does this distractor appeal to?) would be buried in JSONB, making it hard to query "which distractors detect misconception X?" and to compute distractor analytics.

- **Purpose:** Incorrect answer choices for multiple-choice templates, tagged with the misconception they appeal to.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `template_versions`.
  - Many:1 with `misconceptions` (or null for "none" tag).
- **Lifecycle:**
  - Created/updated with the template version.
  - Versioned with the content version.
- **Business Rules:**
  - Every distractor in a multiple-choice template version is incorrect (validated at publish).
  - Every distractor is tagged with a misconception or "none."
  - `(template_version_id, position)` is unique.
- **Expected Size:** ~600,000–2,400,000 rows (4 distractors per template average).
- **Growth Rate:** Medium (grows with templates).
- **Access Patterns:**
  - Read by `template_version_id` (instantiation).
  - Read by `misconception_id` (analytics: which distractors detect this misconception?).
  - Write on publish.
  - High read, very low write.

---

## hints

**Why this table exists:** Stores tiered hints per template version. Without a dedicated table, hints would be JSONB in the template version, making it hard to query hint usage analytics. The table also enforces the tier ordering invariant.

- **Purpose:** Tiered hints for a template version (Hint 1 gentle, Hint 2 specific, Hint 3 near-complete).
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `template_versions`.
- **Lifecycle:**
  - Created/updated with the template version.
  - Versioned with the content version.
- **Business Rules:**
  - Hints never reveal the correct answer directly (enforced at editorial review).
  - Tiers are ordered 1, 2, 3; the Engine does not skip tiers.
  - `(template_version_id, tier)` is unique.
  - Tier 1 is mandatory; tiers 2 and 3 are optional.
- **Expected Size:** ~300,000–1,200,000 rows (2 hints per template average).
- **Growth Rate:** Medium (grows with templates).
- **Access Patterns:**
  - Read by `template_version_id` ordered by `tier` (serving).
  - Write on publish.
  - High read, very low write.

---

## explanations

**Why this table exists:** Stores explanation variants per template version, keyed by outcome (correct, specific misconception). Without a dedicated table, explanations would be JSONB, making it hard to query "which explanation variant was shown to this learner?" for analytics. The table also enforces the "every template has a correct-variant explanation" invariant.

- **Purpose:** Explanation variants for a template version, keyed by learner outcome.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `template_versions`.
  - Many:1 with `misconceptions` (for misconception-keyed variants; null for "correct" variant).
- **Lifecycle:**
  - Created/updated with the template version.
  - Versioned with the content version.
- **Business Rules:**
  - Every published template version has at least one explanation (the "correct" variant).
  - An explanation never contradicts the template's correct answer.
  - `(template_version_id, outcome_key)` is unique, where `outcome_key` is 'correct' or a misconception ID.
- **Expected Size:** ~300,000–1,200,000 rows (2 variants per template average).
- **Growth Rate:** Medium (grows with templates).
- **Access Patterns:**
  - Read by `template_version_id` + `outcome_key` (post-attempt display).
  - Write on publish.
  - Very high read (every attempt), very low write.

---

## content_versions

**Why this table exists:** Immutable snapshots of a subject's entire content graph at publish time. Without content versions, editing a concept would make old attempts uninterpretable (which concept version produced this?). Content Version is one axis of triple versioning (ADR-0011).

- **Purpose:** Subject-wide content snapshot; the unit of atomic publishing and historical reproducibility.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `subjects`.
  - Many:1 with `tenants`.
  - 1:many with `template_versions` (contained in this content version).
  - 1:many with `attempts` (served under this content version).
  - 1:many with `content_packs` (the packs published in this version).
- **Lifecycle:**
  - Created atomically when one or more content packs publish.
  - Immutable once created.
  - Deprecated (prevents new serves) but never deleted.
- **Business Rules:**
  - A content version is immutable.
  - Internally consistent (acyclic knowledge graph, all objectives traced, all misconceptions linked).
  - `(subject_id, version_number)` is unique.
  - Preserved indefinitely while any attempt references it.
- **Expected Size:** ~500–2,000 rows (20–50 versions per subject over a decade).
- **Growth Rate:** Low (new versions on each publish; ~1/month per subject).
- **Access Patterns:**
  - Read by `subject_id` ordered by `version_number` (current version lookup).
  - Read by `id` (attempt replay).
  - Write on publish.
  - High read, very low write.

---

## content_packs

**Why this table exists:** Atomic publishing unit. Without content packs, an instructor might publish a new concept without its templates, leaving the curriculum inconsistent. Content packs enforce atomic publishing (all artifacts or none).

- **Purpose:** Bundle of related content artifacts authored and published together atomically.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `content_versions` (the version produced by publishing this pack).
  - Many:1 with `users` (author).
  - 1:many with `content_review_requests`.
- **Lifecycle:**
  - Authored as a bundle.
  - Reviewed as a unit.
  - Published atomically (produces a new content version).
  - Immutable once published.
- **Business Rules:**
  - A pack's artifacts must be internally consistent.
  - Publishing is atomic: all artifacts or none.
  - A pack cannot span subjects.
- **Expected Size:** ~5,000–20,000 rows (100–400 packs per subject over a decade).
- **Growth Rate:** Low–medium (~50/month).
- **Access Patterns:**
  - Read by `content_version_id` (version composition).
  - Read by `author_user_id` (author history).
  - Write on publish.
  - Medium read, low write.

---

## content_review_requests

**Why this table exists:** Tracks the Review Workflow state for each content pack. Without it, the review process would be ad hoc and unaccountable. The table enforces the "no self-review" rule and records the review stage transitions.

- **Purpose:** Review Workflow state for a content pack (peer → editorial → QA/pilot → published).
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `content_packs`.
  - Many:1 with `users` (author).
  - 1:many with `content_approvals`.
- **Lifecycle:**
  - Created when an author submits a pack for review.
  - Transitions: peer_review → editorial_review → qa_pilot → published (or rejected/withdrawn).
  - Terminal states: published, rejected, withdrawn.
- **Business Rules:**
  - The author cannot be the peer reviewer.
  - All review decisions are recorded.
  - A pack cannot publish without passing all stages.
- **Expected Size:** ~5,000–20,000 rows (1:1 with content packs).
- **Growth Rate:** Low–medium (grows with packs).
- **Access Patterns:**
  - Read by `status` (review queue).
  - Read by `author_user_id` (author's submissions).
  - Write on stage transitions.
  - Medium read, low write.

---

## content_approvals

**Why this table exists:** Records each approval decision in the Review Workflow, with reviewer, timestamp, and stage. Without it, accountability for content quality would be opaque. Every published artifact has a chain of named approvers.

- **Purpose:** Individual approval decisions within the Review Workflow.
- **Owner:** `content`
- **Relationships:**
  - Many:1 with `content_review_requests`.
  - Many:1 with `users` (reviewer).
- **Lifecycle:**
  - Created when a reviewer approves/rejects.
  - Immutable once created.
- **Business Rules:**
  - An approval is immutable.
  - The approver cannot be the author (for peer review).
  - Records the stage, decision, and notes.
- **Expected Size:** ~15,000–60,000 rows (3 approvals per pack average).
- **Growth Rate:** Low–medium (grows with packs).
- **Access Patterns:**
  - Read by `content_review_request_id` (review history).
  - Read by `reviewer_user_id` (reviewer activity).
  - Write on approval.
  - Low read, low write.

---

# Schema: `learning`

The Learning context owns learner enrollment, study sessions, learning sessions, learning goals, study plans, queues, recommendations, and achievements.

---

## learner_enrollments

**Why this table exists:** Models the Learner role (Task 002): a User enrolled in a Subject. Without it, the system would conflate User (identity) with Learner (learning role), preventing multi-subject enrollment with isolated progress.

- **Purpose:** Enroll a user as a learner in a subject, with isolated mastery state.
- **Owner:** `learning`
- **Relationships:**
  - Many:1 with `users`.
  - Many:1 with `subjects`.
  - Many:1 with `learning_paths` (active path).
  - 1:many with `study_sessions`.
  - 1:many with `mastery_scores` (via attempts).
  - 1:many with `learning_goals`.
  - 1:many with `study_plans`.
- **Lifecycle:**
  - Created when a user enrolls in a subject.
  - Activated after onboarding (diagnostic completion).
  - Dormant after 30 days of inactivity; reactivated on next session.
  - Unenrolled at user request; state retained 90 days for re-enrollment, then anonymized.
- **Business Rules:**
  - A learner exists in exactly one subject.
  - A user may be a learner in N subjects, each with independent state.
  - `(user_id, subject_id)` is unique.
  - A learner's mastery state is reconstructible from attempts + algorithm version.
- **Expected Size:** ~2M rows (2 subject enrollments per user average).
- **Growth Rate:** Linear with enrollments; ~5,000/day at scale.
- **Access Patterns:**
  - Read by `user_id` + `subject_id` (every authenticated learning request).
  - Read by `subject_id` (subject analytics).
  - Write on enrollment, onboarding, dormancy transitions.
  - Very high read, low write.

---

## learning_goals

**Why this table exists:** Stores learner-declared targets (interview date, daily commitment, session intent) that influence scheduling. Without it, the Scheduler would treat all learners identically, ignoring urgency and intent.

- **Purpose:** Learner-declared goals that modulate scheduling.
- **Owner:** `learning`
- **Relationships:**
  - Many:1 with `learner_enrollments`.
- **Lifecycle:**
  - Set by the learner during onboarding or in settings.
  - Updated as circumstances change.
  - Archived when completed or abandoned.
  - Defaulted to subject-level default if none set.
- **Business Rules:**
  - A goal cannot require the Scheduler to violate prerequisite-readiness.
  - A time-bound goal must produce a feasible schedule or warn the learner.
  - A learner has at most one active time-bound goal per subject.
- **Expected Size:** ~2M rows (1:1 with enrollments, plus archived).
- **Growth Rate:** Linear with enrollments.
- **Access Patterns:**
  - Read by `learner_enrollment_id` (scheduler, dashboard).
  - Write on goal changes.
  - High read, low write.

---

## study_plans

**Why this table exists:** Calendar-level projection of a learning path against a learning goal. Without it, the Engine could not answer "when will I be ready?" The plan is a projection, not a contract; it updates as mastery and pace vary.

- **Purpose:** Projected schedule from current mastery, learning path, and learning goal.
- **Owner:** `learning`
- **Relationships:**
  - Many:1 with `learner_enrollments`.
  - Many:1 with `learning_paths`.
  - Many:1 with `learning_goals`.
- **Lifecycle:**
  - Generated when a learner sets a time-bound goal.
  - Regenerated nightly and after every study session.
  - Superseded when the goal changes.
  - Archived when the goal completes.
- **Business Rules:**
  - A plan is always recomputable from current mastery, path, and goal.
  - An infeasible goal surfaces a warning, not a silent adjustment.
  - A learner has at most one active plan per subject.
- **Expected Size:** ~1M rows (active + recent archived).
- **Growth Rate:** Linear with enrollments; high churn (regenerated nightly).
- **Access Patterns:**
  - Read by `learner_enrollment_id` (dashboard).
  - Write on regeneration.
  - High read, high write (nightly regeneration).

---

## study_sessions

**Why this table exists:** A Study Session is a single sitting during which a learner practices. Without it, engagement analytics (streaks, time-on-platform) would be computed from individual attempts, which is gameable. The session is the unit of engagement.

- **Purpose:** Single practice sitting; the unit of engagement analytics.
- **Owner:** `learning`
- **Relationships:**
  - Many:1 with `learner_enrollments`.
  - 1:many with `attempts`.
  - Many:1 with `learning_sessions` (parent episode).
- **Lifecycle:**
  - Started by the learner (or resumed).
  - Active while attempts are submitted.
  - Paused (resumable for 24 hours).
  - Ended by learner, by session goal, or by 24-hour inactivity timeout.
  - Archived after end; attempt history retained indefinitely.
- **Business Rules:**
  - A learner has at most one active session per subject at a time.
  - An attempt belongs to exactly one session.
  - A session cannot outlive the learner's enrollment.
- **Expected Size:** ~50M–500M rows (500 sessions per learner over a decade).
- **Growth Rate:** High (~500,000/day at 1M learners).
- **Access Patterns:**
  - Read by `id` (session resume).
  - Read by `learner_enrollment_id` ordered by `started_at` (history).
  - Write on start, pause, end.
  - High read, high write.

---

## learning_sessions

**Why this table exists:** Groups consecutive study sessions into a logical learning episode (per Task 002). Without it, engagement metrics would over-count learners who take breaks. The merge window (default 15 minutes) defines the grouping.

- **Purpose:** Logical learning episode; groups study sessions within a merge window.
- **Owner:** `learning`
- **Relationships:**
  - Many:1 with `learner_enrollments`.
  - 1:many with `study_sessions`.
- **Lifecycle:**
  - Opened when a study session starts and no learning session is active.
  - Extended when a new study session starts within the merge window.
  - Closed when no new study session starts within the merge window.
  - Archived for analytics.
- **Business Rules:**
  - Two study sessions more than the merge window apart belong to different learning sessions.
  - A learning session cannot span subjects.
  - The merge window is configurable per subject but never zero.
- **Expected Size:** ~30M–300M rows (slightly fewer than study sessions).
- **Growth Rate:** High.
- **Access Patterns:**
  - Read by `learner_enrollment_id` + date range (engagement analytics).
  - Write on session start/extend/close.
  - Medium read, high write.
- **Partitioning:** By `started_at` (monthly) — see `07-partitioning-strategy.md`.

---

## practice_queues

**Why this table exists:** Stores session-scoped queue snapshots for mid-session reload recovery. Per Task 002, queues are runtime artifacts cached in Redis; this table is a fallback for recovery, not a long-term store. Without it, a reload mid-session would lose the queue and force regeneration (acceptable but degrading UX).

- **Purpose:** Session-scoped snapshot of the adaptive queue for reload recovery.
- **Owner:** `learning`
- **Relationships:**
  - Many:1 with `study_sessions`.
- **Lifecycle:**
  - Created at session start.
  - Updated on queue regeneration.
  - Deleted when the session ends (not retained long-term).
- **Business Rules:**
  - A queue is bounded in size (10–20 questions).
  - A queue is regenerated, not persisted across sessions.
  - Deleted on session end (retention: 24 hours post-session for recovery, then purged).
- **Expected Size:** ~100K–1M rows (active sessions only).
- **Growth Rate:** High churn (created/deleted per session).
- **Access Patterns:**
  - Read by `study_session_id` (reload recovery).
  - Write on regeneration.
  - High read, high write, high churn.

---

## recommendations

**Why this table exists:** Stores recommendations produced by the Scheduler or analytics jobs. Without it, recommendations would be transient, with no analytics on effectiveness. The table also enforces the "dismissed recommendations do not reappear for 7 days" invariant.

- **Purpose:** Advisory suggestions presented to the learner outside the active practice loop.
- **Owner:** `learning` (produced by `scheduling`).
- **Relationships:**
  - Many:1 with `learner_enrollments`.
  - Many:1 with `recommendation_types` (lookup).
- **Lifecycle:**
  - Generated by the Scheduler or background jobs.
  - Presented on dashboard or in notifications.
  - Accepted, deferred, or dismissed by the learner.
  - Archived for analytics regardless of disposition.
- **Business Rules:**
  - Non-binding; the Engine never auto-acts on a recommendation.
  - Dismissible in one click.
  - A dismissed recommendation does not reappear in identical form for at least 7 days.
- **Expected Size:** ~50M–500M rows (50 recommendations per learner over a decade).
- **Growth Rate:** High.
- **Access Patterns:**
  - Read by `learner_enrollment_id` + `status` (dashboard).
  - Write on generation, acceptance, dismissal.
  - High read, high write.
- **Partitioning:** By `created_at` (monthly) — see `07-partitioning-strategy.md`.

---

## recommendation_history

**Why this table exists:** Append-only history of recommendation lifecycle events (generated, presented, accepted, deferred, dismissed). Without it, recommendation analytics would be limited to current state, not trajectory. The table is the basis for recommendation effectiveness analysis.

- **Purpose:** Append-only event log for recommendation lifecycle.
- **Owner:** `learning`
- **Relationships:**
  - Many:1 with `recommendations`.
- **Lifecycle:**
  - Appended on each lifecycle event.
  - Immutable.
  - Retained per `09-data-retention.md`.
- **Business Rules:**
  - Append-only; no edits, no deletes (except anonymization).
  - Ordered by `created_at` within a recommendation.
- **Expected Size:** ~200M–2B rows (4 events per recommendation average).
- **Growth Rate:** Very high.
- **Access Patterns:**
  - Read by `recommendation_id` (lifecycle).
  - Read by `learner_enrollment_id` + date range (analytics).
  - Write on events.
  - Low read (analytics), very high write.
- **Partitioning:** By `created_at` (monthly) — see `07-partitioning-strategy.md`.

---

## achievements

**Why this table exists:** Records engine-recognized accomplishments (milestones, graduations, streaks). Without it, recognitions would be transient. The table is the source of truth for badges and progress markers.

- **Purpose:** Engine-recognized learner accomplishments.
- **Owner:** `learning`
- **Relationships:**
  - Many:1 with `learner_enrollments`.
  - Many:1 with `achievement_types` (lookup).
- **Lifecycle:**
  - Awarded automatically when criteria are met.
  - Irreversible (once awarded, always awarded).
  - Archived with the learner.
- **Business Rules:**
  - Awarded automatically (no manual award).
  - Irreversible.
  - Documented criteria per achievement type.
- **Expected Size:** ~20M–200M rows (20 achievements per learner average).
- **Growth Rate:** High.
- **Access Patterns:**
  - Read by `learner_enrollment_id` (profile, dashboard).
  - Write on award.
  - High read, medium write.

---

## achievement_types

**Why this table exists:** Lookup table for the catalog of achievements (milestones, graduations, streaks). Without it, achievement definitions would be hardcoded. The table makes the catalog data-driven and editable by administrators.

- **Purpose:** Catalog of achievement definitions.
- **Owner:** `learning` (managed by `administration`).
- **Relationships:**
  - 1:many with `achievements`.
  - Many:1 with `subjects` (some achievements are per-subject).
- **Lifecycle:**
  - Defined by the platform.
  - Updated rarely (criteria refinement).
  - Deprecated (not deleted) when retired.
- **Business Rules:**
  - `code` is unique (e.g., `first_concept_mastered`, `python_full_path_graduate`).
  - Criteria are documented in JSONB.
- **Expected Size:** ~100–500 rows (10–50 achievement types per subject).
- **Growth Rate:** Low.
- **Access Patterns:**
  - Read by `subject_id` (achievement catalog).
  - Read by `code` (award logic).
  - Very high read, near-zero write.

---

## streaks

**Why this table exists:** Stores streak state (current streak, longest streak, last study date). Per Task 002, streaks are decorative engagement metrics, never mastery signals. The table is intentionally separate from mastery to reinforce this distinction.

- **Purpose:** Decorative engagement metric (current/longest streak); never a mastery signal.
- **Owner:** `learning`
- **Relationships:**
  - Many:1 with `learner_enrollments`.
- **Lifecycle:**
  - Updated on each study session.
  - Reset on inactivity (>24 hours gap, configurable per subject).
  - Archived with the learner.
- **Business Rules:**
  - Streaks are decorative; they do not affect scheduling or mastery.
  - Streak reset rules are configurable per subject.
  - Streaks are per-learner, per-subject.
- **Expected Size:** ~2M rows (1:1 with enrollments).
- **Growth Rate:** Linear with enrollments.
- **Access Patterns:**
  - Read by `learner_enrollment_id` (dashboard).
  - Write on session end.
  - High read, low write.

---

# Schema: `assessment`

The Assessment context owns attempts, answers, and question instances.

---

## question_instances

**Why this table exists:** A Question Instance is a concrete, instantiated question served to a learner. Without it, the Engine would score templates (parameterized specs) rather than concrete questions. The instance is the unit of assessment; it is immutable once served and replayable from template version + seed.

- **Purpose:** Concrete question served to a learner; the unit of assessment.
- **Owner:** `assessment`
- **Relationships:**
  - Many:1 with `template_versions`.
  - Many:1 with `content_versions`.
  - 1:1 with `attempts` (when answered; an instance may be abandoned).
  - Many:1 with `study_sessions`.
  - Many:1 with `learner_enrollments`.
- **Lifecycle:**
  - Instantiated by the Question Factory from a template version + seed.
  - Served to a learner (served_at starts the time-to-answer clock).
  - Answered via an attempt, or abandoned after timeout.
  - Immutable after serving.
- **Business Rules:**
  - Deterministic given template version + seed + content version.
  - Immutable once served.
  - References exactly one template version.
  - `parameter_seed` is logged for replay.
- **Expected Size:** ~500M–5B rows (every attempt has an instance; ~500 attempts per learner).
- **Growth Rate:** Very high (~5M/day at 1M learners).
- **Access Patterns:**
  - Read by `id` (attempt replay).
  - Read by `learner_enrollment_id` + date (history).
  - Write on serve, on answer.
  - High read (analytics), very high write.
- **Partitioning:** By `served_at` (monthly) — see `07-partitioning-strategy.md`. Closely coupled with `attempts` partitioning.

---

## attempts

**Why this table exists:** An Attempt is the atomic unit of learning evidence. It is the project's data moat: append-only, immutable, replayable. Every mastery score, every analytics aggregate, every future ML model is derived from attempts. The table is the most important table in the database.

- **Purpose:** Atomic learning evidence; the irreducible unit of the data moat.
- **Owner:** `assessment`
- **Relationships:**
  - Many:1 with `question_instances`.
  - Many:1 with `learner_enrollments`.
  - Many:1 with `study_sessions`.
  - Many:1 with `content_versions` (triple versioning).
  - Many:1 with `template_versions` (triple versioning).
  - Many:1 with `algorithm_versions` (triple versioning — the version under which the resulting mastery was computed).
  - 1:1 with `answers`.
- **Lifecycle:**
  - Created when a learner submits an answer.
  - Scored within the same transaction.
  - Published as `AttemptRecorded` domain event (via outbox).
  - Immutable after write; corrections by appending compensating attempts.
- **Business Rules:**
  - Append-only; no field is ever modified after write.
  - References exactly one question instance, one learner enrollment, one study session.
  - References content version, template version, algorithm version (triple versioning).
  - Scoring is deterministic given instance + answer + template version.
- **Expected Size:** ~500M–5B rows (~500 attempts per learner × 1M learners).
- **Growth Rate:** Very high (~5M/day at 1M learners).
- **Access Patterns:**
  - Read by `learner_enrollment_id` + `concept_id` (mastery recompute).
  - Read by `learner_enrollment_id` + date range (history, analytics).
  - Read by `template_version_id` (question statistics).
  - Read by `content_version_id` (content analytics).
  - Write on submission.
  - Very high read (analytics), very high write.
- **Partitioning:** By `created_at` (monthly) — see `07-partitioning-strategy.md`. The highest-volume table; partitioning is mandatory at scale.

---

## answers

**Why this table exists:** Stores the learner's response separately from the attempt metadata. Without it, code-execution answers with iterative revisions would require duplicating attempt metadata per revision. The separation enables revision analytics.

- **Purpose:** Learner's response to a question instance, with pre-submission revisions.
- **Owner:** `assessment`
- **Relationships:**
  - Many:1 with `attempts`.
  - Many:1 with `question_instances`.
- **Lifecycle:**
  - Drafted by the learner.
  - Revised zero or more times before submission (for code questions).
  - Submitted as part of an attempt.
  - Immutable after submission.
- **Business Rules:**
  - An answer belongs to exactly one attempt.
  - Immutable after the attempt is submitted.
  - Answer type matches the question instance's input contract.
- **Expected Size:** ~600M–6B rows (1.2 answers per attempt average, including revisions).
- **Growth Rate:** Very high (grows with attempts).
- **Access Patterns:**
  - Read by `attempt_id` (attempt review).
  - Write on submission, on revisions (pre-submission).
  - High read, very high write.
- **Partitioning:** By `attempt_id`'s partition (co-located with attempts) — see `07-partitioning-strategy.md`.

---

# Schema: `mastery`

The Mastery context owns mastery scores, reviews, algorithm versions, and learner misconception state. Per ADR-0008, Memory Score and Mastery Score are columns in a single `mastery_scores` table.

---

## algorithm_versions

**Why this table exists:** Snapshots of the Mastery Engine algorithm. Without algorithm versions, an algorithm change would silently rewrite every learner's mastery score, breaking reproducibility. Algorithm Version is one axis of triple versioning (ADR-0011).

- **Purpose:** Immutable snapshot of the Mastery Engine algorithm; the unit of mastery reproducibility.
- **Owner:** `mastery`
- **Relationships:**
  - 1:many with `mastery_scores`.
  - 1:many with `reviews`.
  - 1:many with `attempts` (recorded for triple versioning).
- **Lifecycle:**
  - Created when a new algorithm is promoted to production (after passing the evaluation protocol per ADR-0007).
  - Immutable once created.
  - Superseded by a new version; old scores remain under the old version until a recompute job runs.
- **Business Rules:**
  - Immutable once created.
  - Preserved indefinitely while any mastery score references it.
  - A change to the algorithm requires a new version (no in-place edits).
  - `(version_number)` is unique.
- **Expected Size:** ~10–50 rows (algorithm changes are rare; ~2/year).
- **Growth Rate:** Near-zero.
- **Access Patterns:**
  - Read by `id` (mastery score reconstruction).
  - Read by `is_active = true` (current version lookup).
  - Write on promotion (rare).
  - Very high read, near-zero write.

---

## mastery_scores

**Why this table exists:** The Engine's authoritative estimate of a learner's mastery of each concept. Per ADR-0008, this table holds both the Memory Score (short-term) and the durable Mastery Score (long-term) as columns, plus a combined score, confidence interval, and evidence count. This is the single most queried table in the learning loop (the Scheduler reads it for every queue generation).

- **Purpose:** Per-learner, per-concept mastery estimate (Memory + Mastery + confidence).
- **Owner:** `mastery` (single-writer; no other context writes this table).
- **Relationships:**
  - Many:1 with `learner_enrollments`.
  - Many:1 with `concepts`.
  - Many:1 with `algorithm_versions`.
- **Lifecycle:**
  - Initialized at the learner's first attempt on a concept.
  - Updated by the Mastery Engine after every attempt on the concept.
  - Slow-moving; a single attempt does not collapse or inflate it.
  - Reconstructible from attempt history + algorithm version.
- **Business Rules:**
  - Only the Mastery Engine writes this table (M3 invariant, ASD Section 6.8).
  - Bounded (0.0–1.0) for all score columns.
  - Records the algorithm version that produced it (M2 invariant).
  - `(learner_enrollment_id, concept_id)` is unique.
  - `mastery_score_combined` is a generated column from `memory_score` and `durable_mastery_score` (per ADR-0008's "combined, not averaged" — the exact formula is in the algorithm spec).
  - Optimistic concurrency: `version` column for compare-and-swap updates (per ASD Section 17.8).
- **Expected Size:** ~2B–20B rows (1000 concepts mastered per learner × 1M learners × 2 subjects). At 1M learners, ~2B rows; this is the second-largest table after attempts.
- **Growth Rate:** High (~10M new rows/day at 1M learners, as learners encounter new concepts).
- **Access Patterns:**
  - Read by `learner_enrollment_id` (scheduler: all concepts for a learner).
  - Read by `learner_enrollment_id` + `concept_id` (single concept).
  - Read by `concept_id` (concept statistics: average mastery).
  - Write on attempt completion (mastery update).
  - Very high read (scheduler), high write.
- **Indexing:** Primary on `id`; unique on `(learner_enrollment_id, concept_id)`; secondary on `concept_id`; partial on `(learner_enrollment_id) WHERE durable_mastery_score < 0.5` (weak concepts) — see `06-indexing-strategy.md`.
- **Partitioning:** Not partitioned by time (queried by learner, not by date). Considered for hash partitioning by `learner_enrollment_id` at >5B rows — see `07-partitioning-strategy.md`.

---

## reviews

**Why this table exists:** Scheduled future encounters with concepts (Review records, per Task 002 sense (b)). Without it, the Engine would have no concrete "when" for spaced repetition. The table is the input to the Review Queue.

- **Purpose:** Scheduled future review of a concept; the spaced-repetition schedule.
- **Owner:** `mastery`
- **Relationships:**
  - Many:1 with `learner_enrollments`.
  - Many:1 with `concepts`.
  - Many:1 with `algorithm_versions`.
  - Many:1 with `attempts` (the attempt that scheduled this review).
- **Lifecycle:**
  - Computed by the Mastery Engine after every attempt on a concept.
  - Updated on every review attempt (extending or contracting the interval).
  - Consumed by the Scheduler when due.
  - Recomputed continuously as mastery and memory decay.
- **Business Rules:**
  - A review's due date is deterministic given attempt history + algorithm version.
  - Per-learner, per-concept.
  - Priority is graded (low, medium, high) based on decay severity and goals.
  - `(learner_enrollment_id, concept_id)` is unique (one scheduled review per concept per learner).
- **Expected Size:** ~2B rows (1:1 with mastery_scores; one scheduled review per concept per learner).
- **Growth Rate:** High (grows with mastery_scores).
- **Access Patterns:**
  - Read by `learner_enrollment_id` + `due_at <= now()` (due reviews).
  - Read by `learner_enrollment_id` (review queue).
  - Write on attempt completion.
  - Very high read (scheduler), high write.
- **Indexing:** Primary on `id`; unique on `(learner_enrollment_id, concept_id)`; partial index on `(learner_enrollment_id, due_at) WHERE due_at <= now()` (due reviews) — see `06-indexing-strategy.md`.

---

## learner_misconceptions

**Why this table exists:** Records which misconceptions a learner has exhibited (via tagged distractor selections). Without it, the Scheduler could not bias the queue toward remediation for specific misconceptions. The table enables misconception clustering (multiple selections of the same misconception across templates elevates severity).

- **Purpose:** Per-learner, per-misconception state (detection count, severity, last detected).
- **Owner:** `mastery`
- **Relationships:**
  - Many:1 with `learner_enrollments`.
  - Many:1 with `misconceptions`.
- **Lifecycle:**
  - Created when a learner first selects a misconception-tagged distractor.
  - Updated on each subsequent selection (detection count, severity, last detected).
  - Cleared when the learner demonstrates mastery of the related objective (configurable).
- **Business Rules:**
  - `(learner_enrollment_id, misconception_id)` is unique.
  - Severity is graded (mild, moderate, severe) based on detection count and recency.
  - Cleared only by demonstrated mastery, not by time passage.
- **Expected Size:** ~500M rows (250 misconceptions per learner average, those who have exhibited them).
- **Growth Rate:** High.
- **Access Patterns:**
  - Read by `learner_enrollment_id` (scheduler: remediation biasing).
  - Read by `misconception_id` (analytics: misconception frequency).
  - Write on distractor selection.
  - High read, high write.

---

# Schema: `scheduling`

The Scheduling context owns daily queues (snapshots), queue generation metadata, and scheduling configuration. Per Task 002, queues are runtime artifacts; this schema stores minimal persistent state.

---

## daily_queues

**Why this table exists:** Stores the daily queue snapshot for the current day, per learner. Without it, the daily queue would be regenerated on every access (acceptable but wasteful). The table is a cache with a 24-hour TTL; it is not a long-term store.

- **Purpose:** Day-scoped queue snapshot; the bridge between study plan and adaptive queue.
- **Owner:** `scheduling`
- **Relationships:**
  - Many:1 with `learner_enrollments`.
- **Lifecycle:**
  - Generated at the start of the learner's local day.
  - Updated as items are completed.
  - Refreshed if completed early (bonus queue).
  - Expired at end of local day.
- **Business Rules:**
  - Bounded in size (10–30 questions).
  - Cannot include a concept whose prerequisites are not minimally mastered (unless diagnostic).
  - Expires at end of local day.
  - `(learner_enrollment_id, queue_date)` is unique.
- **Expected Size:** ~2M rows (1:1 with enrollments; churns daily).
- **Growth Rate:** High churn (regenerated daily).
- **Access Patterns:**
  - Read by `learner_enrollment_id` + `queue_date` (session start).
  - Write on generation, on item completion.
  - High read, high write, high churn.

---

## scheduling_configs

**Why this table exists:** Per-subject scheduling configuration (cooldown duration, queue sizes, priority weights, difficulty adjustment bounds). Without it, scheduling parameters would be hardcoded or scattered. The table makes scheduling data-driven and tunable without redeployment.

- **Purpose:** Per-subject scheduling parameters.
- **Owner:** `scheduling`
- **Relationships:**
  - Many:1 with `subjects`.
- **Lifecycle:**
  - Defined per subject.
  - Updated by administrators (with ADR for significant changes).
  - Versioned (current version referenced by scheduler).
- **Business Rules:**
  - One active config per subject.
  - Parameter bounds enforced (e.g., cooldown >= 5 minutes, queue size 10–30).
  - Changes are audited.
- **Expected Size:** ~50 rows (1:1 with subjects, plus historical versions).
- **Growth Rate:** Near-zero.
- **Access Patterns:**
  - Read by `subject_id` + `is_active = true` (scheduler).
  - Write on config changes (rare).
  - Very high read, near-zero write.

---

# Schema: `analytics`

The Analytics context owns precomputed aggregates and analytics projections. Per ASD Section 13.7, the operational database handles per-user analytics; a derived columnar store handles aggregate analytics at scale. This schema holds the per-user projections and the nightly aggregate snapshots.

---

## learner_daily_snapshots

**Why this table exists:** Nightly snapshot of per-learner, per-concept mastery state. Without it, retention analytics would require querying the attempts table (expensive at scale). The snapshot is the basis for mastery-over-time charts and retention curves.

- **Purpose:** Nightly per-learner mastery snapshot for retention analytics.
- **Owner:** `analytics`
- **Relationships:**
  - Many:1 with `learner_enrollments`.
  - Many:1 with `concepts`.
- **Lifecycle:**
  - Created nightly by a background job.
  - Immutable once created.
  - Retained per `09-data-retention.md` (anonymized after account deletion).
- **Business Rules:**
  - One snapshot per learner per concept per day.
  - `(learner_enrollment_id, concept_id, snapshot_date)` is unique.
  - Immutable.
- **Expected Size:** ~50B rows at 1M learners (2B mastery_scores × 30-day retention × rolled up). In practice, snapshots are taken only for active learners, reducing this significantly.
- **Growth Rate:** Very high (~30M rows/day at 1M learners).
- **Access Patterns:**
  - Read by `learner_enrollment_id` + `concept_id` + date range (retention curves).
  - Read by `concept_id` + `snapshot_date` (concept retention analytics).
  - Write nightly (batch).
  - Medium read (analytics), high batch write.
- **Partitioning:** By `snapshot_date` (monthly) — see `07-partitioning-strategy.md`.

---

## concept_statistics

**Why this table exists:** Nightly aggregate statistics per concept (average mastery, success rate, time-to-mastery distribution, retention). Without it, instructors would query the attempts table (expensive). The table is the basis for curriculum quality monitoring.

- **Purpose:** Nightly per-concept aggregate statistics.
- **Owner:** `analytics`
- **Relationships:**
  - Many:1 with `concepts`.
  - Many:1 with `content_versions`.
- **Lifecycle:**
  - Computed nightly.
  - Immutable once created (a new row per night).
  - Retained indefinitely.
- **Business Rules:**
  - `(concept_id, content_version_id, snapshot_date)` is unique.
  - Computed from real attempt data.
- **Expected Size:** ~5M rows (20K concepts × 365 days × 5 years).
- **Growth Rate:** Medium (~20K rows/day).
- **Access Patterns:**
  - Read by `concept_id` (admin portal: concept quality).
  - Read by `content_version_id` (version comparison).
  - Write nightly (batch).
  - Medium read, low batch write.

---

## template_statistics

**Why this table exists:** Nightly aggregate statistics per template version (success rate, distractor distribution, discrimination, time-to-answer). Without it, template quality monitoring would query attempts (expensive). The table drives template revision decisions.

- **Purpose:** Nightly per-template-version aggregate statistics.
- **Owner:** `analytics`
- **Relationships:**
  - Many:1 with `template_versions`.
- **Lifecycle:**
  - Computed nightly.
  - Immutable once created.
  - Retained indefinitely.
- **Business Rules:**
  - `(template_version_id, snapshot_date)` is unique.
  - Computed from real attempt data.
- **Expected Size:** ~50M rows (200K template versions × 365 days × 5 years, filtered to active templates).
- **Growth Rate:** Medium (~50K rows/day).
- **Access Patterns:**
  - Read by `template_version_id` (admin portal: template quality).
  - Write nightly (batch).
  - Medium read, low batch write.

---

# Schema: `billing`

The Billing context owns subscriptions, billing plans, invoices, and entitlements. This schema is minimal at launch (Phase 3 per ASD Section 16.3); the tables are modeled now to preserve the future path.

---

## billing_plans

**Why this table exists:** Catalog of billing plans (Free, Pro, Interview Plus). Without it, plans would be hardcoded. The table makes plans data-driven, versioned, and deprecable.

- **Purpose:** Catalog of subscription offerings.
- **Owner:** `billing`
- **Relationships:**
  - 1:many with `subscriptions`.
- **Lifecycle:**
  - Defined by the platform.
  - Versioned (price changes produce new versions; existing subscriptions grandfathered).
  - Deprecated (no new subscriptions; existing continue).
- **Business Rules:**
  - `code` is unique (e.g., `free`, `pro`, `interview_plus`).
  - Entitlements stored as JSONB.
  - Versioned; `(code, version_number)` is unique.
- **Expected Size:** ~50 rows (10 plans × 5 versions over a decade).
- **Growth Rate:** Near-zero.
- **Access Patterns:**
  - Read by `code` + `is_active = true` (signup).
  - Very high read, near-zero write.

---

## subscriptions

**Why this table exists:** A user's active billing relationship. Without it, entitlements could not be computed. The table integrates with an external payment provider (Stripe).

- **Purpose:** User's billing relationship (active plan, renewal, payment method).
- **Owner:** `billing`
- **Relationships:**
  - Many:1 with `users`.
  - Many:1 with `billing_plans`.
  - 1:many with `invoices`.
- **Lifecycle:**
  - Started when a user subscribes.
  - Renewed on renewal date.
  - Upgraded/downgraded.
  - Canceled by user or system (non-payment).
  - Expired at end of billing period after cancellation.
- **Business Rules:**
  - A user has at most one active subscription.
  - State changes logged in audit_logs.
  - Entitlements computed from subscription state.
- **Expected Size:** ~1M rows (1:1 with users, plus historical).
- **Growth Rate:** Linear with users.
- **Access Patterns:**
  - Read by `user_id` + `status = 'active'` (entitlement check).
  - Write on subscribe, renew, cancel.
  - High read, low write.

---

## invoices

**Why this table exists:** Records of billing events (charges, refunds). Required for accounting and tax compliance.

- **Purpose:** Billing event records (charges, refunds, adjustments).
- **Owner:** `billing`
- **Relationships:**
  - Many:1 with `subscriptions`.
  - Many:1 with `users`.
- **Lifecycle:**
  - Created on each billing event.
  - Immutable once created.
  - Retained per `09-data-retention.md` (7 years for tax compliance).
- **Business Rules:**
  - Immutable.
  - References the external payment provider's invoice ID.
- **Expected Size:** ~5M rows (5 invoices per user average over a decade).
- **Growth Rate:** Linear with users.
- **Access Patterns:**
  - Read by `user_id` (billing history).
  - Read by `subscription_id`.
  - Write on billing events.
  - Low read, low write.

---

# Schema: `administration`

The Administration context owns audit logs, feature flags, system settings, GDPR requests, and organizations (future).

---

## audit_logs

**Why this table exists:** Append-only record of every privileged action. Without it, accountability and forensics would be impossible. The table is the compliance and forensic backbone.

- **Purpose:** Append-only record of privileged actions.
- **Owner:** `administration`
- **Relationships:**
  - Many:1 with `users` (actor; nullable for system actions).
- **Lifecycle:**
  - Written within the same transaction as the privileged action.
  - Append-only; no edits, no deletes.
  - Retained per `09-data-retention.md` (7 years).
  - Exported daily to cold storage.
- **Business Rules:**
  - Append-only.
  - Transactional with the privileged action.
  - Records actor, action, target, metadata, outcome.
- **Expected Size:** ~500M–5B rows (every privileged action over a decade).
- **Growth Rate:** High (~500K/day at scale).
- **Access Patterns:**
  - Read by `target_type` + `target_id` (forensics: who did what to this?).
  - Read by `actor_user_id` + date range (user activity).
  - Read by `action` + date range (action audit).
  - Write on privileged actions.
  - Medium read, high write.
- **Partitioning:** By `created_at` (monthly) — see `07-partitioning-strategy.md`.

---

## feature_flags

**Why this table exists:** Runtime feature toggles for gradual rollouts, A/B testing, kill switches (per ASD Section 17.3 and ADR-0014-era infrastructure). Without it, every feature would be live on deployment.

- **Purpose:** Runtime feature configuration.
- **Owner:** `administration`
- **Relationships:**
  - 1:many with `feature_flag_assignments` (per-user overrides).
- **Lifecycle:**
  - Created by an engineer for a new feature.
  - Configured with targeting rules (percentage, cohort, specific users).
  - Toggled without redeployment.
  - Retired when the feature is fully released or removed.
- **Business Rules:**
  - `key` is unique (e.g., `mastery_engine_v2`).
  - Targeting rules stored as JSONB.
  - Has a documented owner and retirement plan.
- **Expected Size:** ~500 rows (50 active flags × 10 versions).
- **Growth Rate:** Low.
- **Access Patterns:**
  - Read by `key` + `is_active = true` (every request evaluates flags).
  - Write on toggle (rare).
  - Very high read, near-zero write.

---

## feature_flag_assignments

**Why this table exists:** Per-user feature flag overrides (for specific user targeting). Without it, per-user targeting would require scanning all users on every flag evaluation.

- **Purpose:** Per-user feature flag override assignments.
- **Owner:** `administration`
- **Relationships:**
  - Many:1 with `feature_flags`.
  - Many:1 with `users`.
- **Lifecycle:**
  - Created when a user is assigned to a flag override.
  - Updated on reassignment.
  - Deleted when the flag retires.
- **Business Rules:**
  - `(feature_flag_id, user_id)` is unique.
  - Override value stored as JSONB.
- **Expected Size:** ~1M rows (only users with explicit overrides).
- **Growth Rate:** Low.
- **Access Patterns:**
  - Read by `user_id` (flag evaluation).
  - Write on assignment.
  - High read, low write.

---

## system_settings

**Why this table exists:** Platform-wide configuration (e.g., default daily goal, default cooldown, support email). Without it, settings would be environment variables, requiring redeployment to change.

- **Purpose:** Platform-wide configuration key-value store.
- **Owner:** `administration`
- **Relationships:** None (singleton-style key-value).
- **Lifecycle:**
  - Defined by administrators.
  - Updated rarely.
  - Versioned (audit trail of changes).
- **Business Rules:**
  - `key` is unique.
  - Value stored as JSONB (typed by `value_type`).
  - Changes audited.
- **Expected Size:** ~100 rows.
- **Growth Rate:** Near-zero.
- **Access Patterns:**
  - Read by `key` (every request that needs a setting).
  - Write on changes (rare).
  - High read, near-zero write.

---

## gdpr_requests

**Why this table exists:** Tracks GDPR data subject requests (access, erasure, portability). Without it, GDPR compliance would be ad hoc. The table is the audit trail for regulatory compliance.

- **Purpose:** GDPR data subject request tracking (access, erasure, portability).
- **Owner:** `administration`
- **Relationships:**
  - Many:1 with `users`.
- **Lifecycle:**
  - Created when a user submits a request.
  - Processed within 30 days (legal requirement).
  - Completed with a reference to the export/erasure artifact.
  - Retained for audit (the request itself is logged).
- **Business Rules:**
  - Requests processed within 30 days.
  - Erasure requests anonymize PII but retain anonymized aggregates (documented in privacy policy).
  - Request state transitions are audited.
- **Expected Size:** ~10K–100K rows (a small fraction of users exercise GDPR rights).
- **Growth Rate:** Low.
- **Access Patterns:**
  - Read by `user_id` (user's request history).
  - Read by `status` (admin queue).
  - Write on request submission, processing.
  - Low read, low write.

---

## organizations

**Why this table exists:** B2B billing entity (future Phase 5+ per ASD Section 16.5). Modeled now with minimal columns to preserve the future path. Without it, B2B monetization would require a schema migration later.

- **Purpose:** B2B organization for bulk billing and admin delegation.
- **Owner:** `administration` (with `billing` for billing).
- **Relationships:**
  - 1:many with `users` (members).
  - 1:1 with `subscriptions` (organization subscription).
- **Lifecycle:**
  - Created by an administrator or self-service B2B signup (future).
  - Populated with member users.
  - Dissolved by request; member users revert to individual subscriptions.
- **Business Rules:**
  - At least one organization administrator.
  - Members are users (not learners; learner is per-subject).
  - Dissolution preserves member learning data.
- **Expected Size:** ~1,000–10,000 rows at B2B maturity.
- **Growth Rate:** Low (B2B is a future phase).
- **Access Patterns:**
  - Read by `id` (admin portal).
  - Read by `member_user_id` (user's organization).
  - Write on creation, member changes.
  - Low read, low write.

---

## notifications

**Why this table exists:** Stores notification records (review reminders, streak nudges, weekly digests). Without it, notifications would be fire-and-forget, with no analytics on delivery or effectiveness. The table also enforces deduplication and user preferences.

- **Purpose:** Notification records (sent, delivered, opened, dismissed).
- **Owner:** `administration` (with `learning` producing some).
- **Relationships:**
  - Many:1 with `users`.
- **Lifecycle:**
  - Created by the notification system.
  - Sent via the channel (email, push, in-app).
  - Delivered, opened, or dismissed by the user.
  - Retained per `09-data-retention.md` (30 days for delivery records).
- **Business Rules:**
  - Respects user preferences (channel, frequency).
  - Deduplicated (no duplicate notifications within a configurable window).
  - Records delivery status for analytics.
- **Expected Size:** ~500M rows (500 notifications per user over a decade).
- **Growth Rate:** High.
- **Access Patterns:**
  - Read by `user_id` + `status` (notification center).
  - Write on creation, delivery, dismissal.
  - High read, high write.
- **Partitioning:** By `created_at` (monthly) — see `07-partitioning-strategy.md`.

---

# Schema: `infrastructure` (cross-cutting)

The `infrastructure` schema holds cross-cutting tables that don't belong to a single bounded context: the outbox, jobs, and migration history.

---

## outbox_events

**Why this table exists:** The outbox pattern (ADR-0012) requires a table to store domain events in the same transaction as the originating write. Without it, events could be lost if the dispatcher is unavailable. The table is the durability mechanism for cross-context communication.

- **Purpose:** Transactional outbox for domain event dispatch.
- **Owner:** `infrastructure` (written by all contexts; read by the dispatcher).
- **Relationships:**
  - Many:1 with `users` (nullable; some events are system-generated).
- **Lifecycle:**
  - Written in the same transaction as the originating domain write.
  - Dispatched by the Outbox Dispatcher to subscribers.
  - Marked as dispatched (or dead-lettered on repeated failure).
  - Retained per `09-data-retention.md` (90 days for audit, then archived).
- **Business Rules:**
  - Append-only.
  - Transactional with the originating write.
  - At-least-once delivery; subscribers must be idempotent.
  - `event_type` is the domain event name (e.g., `AttemptRecorded`).
  - `payload` is JSONB (versioned with the API).
- **Expected Size:** ~5B rows (10 events per attempt × 500M attempts).
- **Growth Rate:** Very high (~50M/day at 1M learners).
- **Access Patterns:**
  - Read by `dispatched_at IS NULL` ordered by `created_at` (dispatcher poll).
  - Read by `aggregate_id` (event replay for a specific aggregate).
  - Write on domain events.
  - High read (dispatcher), very high write.
- **Partitioning:** By `created_at` (monthly) — see `07-partitioning-strategy.md`.

---

## background_jobs

**Why this table exists:** Tracks background job state (notification dispatch, analytics projection rebuilds, mastery recompute, backups). Without it, jobs would be fire-and-forget, with no retry or dead-letter management. The table is the durable job queue.

- **Purpose:** Background job tracking (queued, running, completed, failed, dead-lettered).
- **Owner:** `infrastructure`
- **Relationships:** None (jobs reference aggregates via JSONB payload).
- **Lifecycle:**
  - Created when a job is enqueued.
  - Picked up by a worker (running).
  - Completed or failed.
  - Retried with exponential backoff.
  - Dead-lettered after configurable failure count.
- **Business Rules:**
  - Jobs are idempotent (at-least-once delivery).
  - `(job_type, payload_hash)` is unique (deduplication).
  - Dead-lettered jobs require manual investigation.
- **Expected Size:** ~1B rows (jobs for notifications, analytics, recompute).
- **Growth Rate:** High.
- **Access Patterns:**
  - Read by `status = 'queued'` ordered by `priority` + `created_at` (worker poll).
  - Write on enqueue, on status transitions.
  - High read, high write.
- **Partitioning:** By `created_at` (monthly) — see `07-partitioning-strategy.md`.

---

## migration_history

**Why this table exists:** Tracks schema migrations applied to the database. Without it, migrations could be applied twice or skipped. The table is the source of truth for schema version.

- **Purpose:** Schema migration tracking.
- **Owner:** `infrastructure`
- **Relationships:** None.
- **Lifecycle:**
  - Created when a migration is applied.
  - Immutable once created.
  - Never deleted.
- **Business Rules:**
  - `version` is unique.
  - Immutable.
  - Records the migration filename, checksum, applied_at, and applied_by.
- **Expected Size:** ~1,000 rows (100 migrations/year × 10 years).
- **Growth Rate:** Low.
- **Access Patterns:**
  - Read by `version` (migration check on startup).
  - Read all ordered by `version` (current schema version).
  - Write on migration.
  - Low read, low write.

---

## Summary of Tables by Schema

| Schema | Tables | Total Rows at 1M Learners (est.) |
|---|---|---|
| `identity` | users, user_profiles, user_credentials, sessions | ~6M |
| `content` | tenants, subjects, learning_paths, learning_path_items, concepts, concept_dependencies, learning_objectives, misconceptions, question_templates, template_versions, template_objectives, template_concepts, distractors, hints, explanations, content_versions, content_packs, content_review_requests, content_approvals | ~3M |
| `learning` | learner_enrollments, learning_goals, study_plans, study_sessions, learning_sessions, practice_queues, recommendations, recommendation_history, achievements, achievement_types, streaks | ~600M |
| `assessment` | question_instances, attempts, answers | ~6B (the data moat) |
| `mastery` | algorithm_versions, mastery_scores, reviews, learner_misconceptions | ~5B |
| `scheduling` | daily_queues, scheduling_configs | ~2M |
| `analytics` | learner_daily_snapshots, concept_statistics, template_statistics | ~50B (snapshots; partitioned) |
| `billing` | billing_plans, subscriptions, invoices | ~6M |
| `administration` | audit_logs, feature_flags, feature_flag_assignments, system_settings, gdpr_requests, organizations, notifications | ~500M |
| `infrastructure` | outbox_events, background_jobs, migration_history | ~6B |
| **Total** | **~50 tables** | **~70B rows** (dominated by attempts, mastery_scores, snapshots, outbox, analytics) |

The database is designed to handle this scale via partitioning (attempts, outbox, snapshots, audit, notifications by time; mastery_scores and reviews by hash if needed), indexing (see `06-indexing-strategy.md`), read replicas (analytics traffic), and a derived columnar store (aggregate analytics at scale).

---

*End of Domain Model.*
