# Aggregate Map

> Every aggregate root in the Mastery Engine domain model, its boundary, child entities, and invariants.

---

## What is an Aggregate?

An aggregate is a cluster of domain objects treated as a single consistency boundary. The **aggregate root** is the only entry point; external code cannot directly access child entities. Persistence is atomic at the aggregate level.

---

## Aggregate Roots by Context

### Identity Context

#### User Aggregate
- **Root:** `User`
- **Children:** `UserProfile`, `UserCredential` (list)
- **Repository:** `UserRepository`
- **Invariants:**
  - Email must be verified before status can go active.
  - Cannot suspend an admin account.
  - Cannot anonymize unless status is `pending_deletion` and grace period elapsed.
  - MFA cannot be disabled for admin accounts.
  - At least one credential must exist while the account is active.

### Content Context

#### Subject Aggregate
- **Root:** `Subject`
- **Children:** none (references concepts by ID)
- **Repository:** `SubjectRepository`
- **Invariants:**
  - Status transitions: draft → published → deprecated (one-way).

#### Concept Aggregate
- **Root:** `Concept`
- **Children:** `LearningObjective` (list), `Misconception` (list), `ConceptDependency` (list)
- **Repository:** `ConceptRepository`
- **Invariants:**
  - No self-dependency.
  - No duplicate dependency edges.
  - Dependencies must be within the same subject.

#### QuestionTemplate Aggregate
- **Root:** `QuestionTemplate`
- **Children:** `TemplateVersion` (history, immutable)
- **Repository:** `QuestionTemplateRepository`
- **Invariants:**
  - Template versions are immutable after creation.
  - `current_version_id` points to the latest published version.

#### ContentPack Aggregate
- **Root:** `ContentPack`
- **Children:** none (references artifacts by ID)
- **Repository:** `ContentPackRepository`
- **Invariants:**
  - Review workflow: draft → in_review → published (or rejected).
  - Publishing is atomic (all artifacts or none).
  - Author cannot be the peer reviewer.

### Assessment Context

#### QuestionInstance Aggregate
- **Root:** `QuestionInstance`
- **Children:** none
- **Repository:** `QuestionInstanceRepository`
- **Invariants:**
  - Cannot answer an already-answered instance.
  - Cannot abandon an answered instance.
  - Immutable once served (prompt, choices, correct answer never change).

#### Attempt Aggregate
- **Root:** `Attempt`
- **Children:** `Answer` (1:1, optional)
- **Repository:** `AttemptRepository`
- **Invariants:**
  - **Append-only** — no methods modify state after creation (the data moat).
  - `partial_credit` is set only when `scoring_outcome` is PARTIAL.
  - `time_to_answer` must be non-negative.
  - Triple versioning: content_version_id, template_version_id, algorithm_version_id are set at creation.

### Mastery Context

#### MasteryScore Aggregate
- **Root:** `MasteryScore`
- **Children:** none
- **Repository:** `MasteryScoreRepository`
- **Invariants:**
  - Only the Mastery Engine writes MasteryScores (single-writer, M3).
  - All score values are bounded [0.0, 1.0].
  - Optimistic concurrency: `version` increments on each update.
  - `concept_state` and `weakness_severity` are derived from scores.

#### Review Aggregate
- **Root:** `Review`
- **Children:** none
- **Repository:** `ReviewRepository`
- **Invariants:**
  - One review per (learner_enrollment_id, concept_id).
  - `review_interval` is bounded by ReviewInterval.MIN_DAYS and MAX_DAYS.

#### AlgorithmVersion Aggregate
- **Root:** `AlgorithmVersion`
- **Children:** none
- **Repository:** `AlgorithmVersionRepository`
- **Invariants:**
  - Immutable after creation (parameters never change).
  - Only one version can be active at a time.
  - Once promoted, cannot be demoted (a new version supersedes it).

### Learning Context

#### LearnerEnrollment Aggregate
- **Root:** `LearnerEnrollment`
- **Children:** none
- **Repository:** `EnrollmentRepository`
- **Invariants:**
  - Status: pending_onboarding → active → (dormant ↔ active) → unenrolled → anonymized.

#### StudySession Aggregate
- **Root:** `StudySession`
- **Children:** none
- **Repository:** `StudySessionRepository`
- **Invariants:**
  - Cannot add attempts to a completed session (ENDED/ABANDONED).
  - Cannot resume a session past the 24h resumption window.
  - One active session per enrollment.

#### LearningGoal Aggregate
- **Root:** `LearningGoal`
- **Children:** none
- **Repository:** `LearningGoalRepository`
- **Invariants:**
  - `target_date` must be in the future for time-bound goals.
  - At most one active time-bound goal per enrollment.

#### Recommendation Aggregate
- **Root:** `Recommendation`
- **Children:** none
- **Repository:** `RecommendationRepository`
- **Invariants:**
  - Terminal states (ACCEPTED, DISMISSED, EXPIRED) cannot transition.
  - Score must be 0.0–1.0.

#### Achievement Aggregate
- **Root:** `Achievement`
- **Children:** none
- **Repository:** `AchievementRepository`
- **Invariants:**
  - Irreversible (once awarded, always awarded).
  - One per (enrollment, achievement_type).

#### Streak Aggregate
- **Root:** `Streak`
- **Children:** none
- **Repository:** `StreakRepository`
- **Invariants:**
  - `current_streak` ≤ `longest_streak`.
  - Streak increments only once per calendar day.
  - Streaks are decorative; they do not affect scheduling or mastery.

### Scheduling Context

#### DailyQueue Aggregate
- **Root:** `DailyQueue`
- **Children:** none
- **Repository:** `DailyQueueRepository`
- **Invariants:**
  - Bounded size (10–30 questions).
  - Expires at end of local day.

### Billing Context

#### Subscription Aggregate
- **Root:** `Subscription`
- **Children:** none
- **Repository:** `SubscriptionRepository`
- **Invariants:**
  - State machine: ACTIVE → (PAST_DUE → ACTIVE or CANCELED) → EXPIRED.
  - One active subscription per user.

### Administration Context

#### FeatureFlag Aggregate
- **Root:** `FeatureFlag`
- **Children:** none
- **Repository:** `FeatureFlagRepository`
- **Invariants:**
  - `key` is unique and matches `^[a-z][a-z0-9_.\-]*$`.
  - Retired flags cannot be updated.

#### Notification Aggregate
- **Root:** `Notification`
- **Children:** none
- **Repository:** `NotificationRepository`
- **Invariants:**
  - State machine: QUEUED → SENT → DELIVERED → (OPENED | DISMISSED); QUEUED → FAILED.
  - Terminal states cannot transition.

#### Organization Aggregate
- **Root:** `Organization`
- **Children:** none
- **Repository:** `OrganizationRepository`
- **Invariants:**
  - State machine: ACTIVE → (SUSPENDED ↔ ACTIVE) → DISSOLVED (terminal).
