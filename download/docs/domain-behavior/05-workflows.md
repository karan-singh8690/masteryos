# 05 — Business Workflows

> End-to-end workflows that span multiple commands, events, and bounded contexts.
> Each workflow lists its steps, the commands and events involved, and the failure/recovery behavior.

---

## Workflow Template

For each workflow:

- **Trigger** — what starts the workflow.
- **Steps** — the ordered sequence of commands and events.
- **Failure Handling** — what happens on failure at each step.
- **End Condition** — what marks the workflow complete.

---

## 1. New Learner Onboarding

- **Trigger**: User completes `EnrollInSubject` for a subject.
- **Steps**:
  1. `EnrollInSubject` → `LearnerEnrolled` event.
  2. System presents diagnostic (a special study session with intent `diagnostic`).
  3. Learner answers diagnostic questions via `SubmitAnswer` (multiple times).
  4. Each `SubmitAnswer` → `AttemptRecorded` → `MasteryUpdated` (baseline mastery).
  5. After N diagnostic questions, `CompleteOnboarding` → `OnboardingCompleted`.
  6. System generates first daily queue (`GenerateDailyQueue` → `DailyQueueGenerated`).
  7. System generates welcome recommendation (`GenerateRecommendation`).
- **Failure Handling**: learner abandons diagnostic → enrollment stays `pending_onboarding`; can resume; after 7 days, reminder email.
- **End Condition**: `OnboardingCompleted` event; enrollment status `active`.

---

## 2. Daily Learning Loop

- **Trigger**: Learner opens the app (or starts a session).
- **Steps**:
  1. `GetDashboard` query → recommended next action.
  2. Learner clicks "Start session" → `StartStudySession` → `StudySessionStarted` + `AdaptiveQueueGenerated`.
  3. First question served (from adaptive queue).
  4. Learner answers → `SubmitAnswer` → `AttemptRecorded` → `MasteryUpdated` → `ConceptStateChanged` (maybe) → `ReviewScheduled` → `AdaptiveQueueGenerated` (regenerated).
  5. Next question served; loop repeats.
  6. Learner ends session → `EndStudySession` → `StudySessionEnded` + `SessionAnalyticsComputed`.
  7. Streak updated; achievements checked (e.g., "30-day streak").
- **Failure Handling**: see `10-error-handling.md` (late submissions, abandoned questions, mastery conflicts).
- **End Condition**: `StudySessionEnded`.

---

## 3. Adaptive Queue Generation

- **Trigger**: `StartStudySession` or post-attempt mastery update.
- **Steps**:
  1. `GenerateAdaptiveQueue` command.
  2. Scheduler loads mastery scores (`GetAllMasteryScores`), due reviews (`GetDueReviews`), weak concepts, learning goal, scheduling config.
  3. Scheduler computes priority per candidate concept.
  4. Scheduler filters by cooldown, prerequisite-readiness.
  5. Scheduler selects top N concepts; for each, selects a template; for each template, the Question Factory instantiates a question (seeded).
  6. Queue cached in Redis + `practice_queues` table (for reload recovery).
  7. `AdaptiveQueueGenerated` event.
- **Failure Handling**: scheduler unavailable → fallback to default (oldest due review); no eligible questions → session ends with "no content available."
- **End Condition**: queue returned to learner.

---

## 4. Question Answering (the Loop's core)

- **Trigger**: Learner submits an answer.
- **Steps**:
  1. `SubmitAnswer` command (validation: session active, question not answered).
  2. Assessment Domain Service scores the answer (deterministic).
  3. Attempt record written (append-only) with triple versioning; `AnswerSubmitted` + `AttemptRecorded` events to outbox (same transaction).
  4. Response returned to learner (scoring outcome + explanation).
  5. Asynchronously: Mastery context consumes `AttemptRecorded` → `UpdateMastery` → `MasteryUpdated` + maybe `ConceptStateChanged` + maybe `WeakConceptDetected`.
  6. Asynchronously: Scheduler consumes `MasteryUpdated` → `GenerateAdaptiveQueue` (regenerate).
  7. Asynchronously: Analytics consumes `AttemptRecorded` → updates statistics.
- **Failure Handling**: see `10-error-handling.md`.
- **End Condition**: attempt recorded; mastery updated (async); queue regenerated (async).

---

## 5. Mastery Recalculation (on attempt)

- **Trigger**: `AttemptRecorded` event consumed by Mastery context.
- **Steps**:
  1. Mastery Engine loads the learner's attempt history for the concept (via `template_concepts` join).
  2. Mastery Engine loads the current algorithm version's parameters.
  3. Mastery Engine computes new `memory_score`, `durable_mastery_score`, `mastery_score_combined` (deterministic function of attempt history + algorithm version).
  4. Optimistic concurrency: read `version`, compute, write with `WHERE version = $read_version`; on conflict, retry (re-read, recompute, re-write).
  5. Derive `concept_state` and `weakness_severity` from scores.
  6. `MasteryUpdated` event; if state changed, `ConceptStateChanged`; if weak, `WeakConceptDetected`.
  7. `ScheduleReview` command → `ReviewScheduled` event.
- **Failure Handling**: optimistic conflict → retry (max 3); algorithm version not active → use active version; enrollment not active → skip (log warning).
- **End Condition**: mastery score updated; review scheduled.

---

## 6. Review Scheduling

- **Trigger**: `MasteryUpdated` event (consumed by Mastery context's `ScheduleReview` command).
- **Steps**:
  1. Compute new review interval (expand on success, contract on failure; bounded).
  2. Compute new `due_at` = now + interval.
  3. Upsert review record (`(learner_enrollment_id, concept_id)` unique).
  4. `ReviewScheduled` event.
  5. Scheduler includes due reviews in next queue generation.
- **Failure Handling**: algorithm version not active → use active version.
- **End Condition**: review record updated.

---

## 7. Content Publication

- **Trigger**: Instructor submits a content pack for review.
- **Steps**:
  1. `SubmitContentPackForReview` → `ContentPackSubmittedForReview` (status → `peer_review`).
  2. Peer reviewer assigned; reviews; `ApproveContentPack` (stage = peer) → status → `editorial_review`.
  3. Editorial reviewer; `ApproveContentPack` (stage = editorial) → status → `qa_pilot`.
  4. QA pilot: pack's questions served to a pilot cohort; discrimination measured.
  5. QA reviewer; `ApproveContentPack` (stage = qa) → `PublishContentPack`.
  6. `PublishContentPack`: content validation (acyclic graph, traceability, distractor tagging); create new `content_version`; bump `template_versions`; update `concepts.current_version_id`.
  7. `ContentPackPublished` + `ContentVersionCreated` events.
  8. Scheduling context invalidates content cache; analytics context tracks new version.
- **Failure Handling**: any stage rejection → `RequestContentPackChanges` (returns to author) or `RejectContentPack`; validation failure → publish aborted, pack stays `in_review`.
- **End Condition**: `ContentVersionCreated`; pack status `published`.

---

## 8. Algorithm Rollout

- **Trigger**: Engineering completes a new algorithm version; evaluation protocol passed.
- **Steps**:
  1. Engineer runs shadow evaluation (new model runs in parallel; outputs logged).
  2. Evaluation: reproducibility on historical attempts; no regression on retention metrics.
  3. Human sign-off (architecture review group + curriculum lead).
  4. `PublishAlgorithmVersion` command → new version `is_active = true`; old version `is_active = false`.
  5. `AlgorithmVersionPublished` event.
  6. Mastery context starts `RecomputeMasteryForAlgorithmVersion` background job.
  7. Job processes learners in batches (10,000 per batch); emits `MasteryRecomputeProgressed` per batch.
  8. On completion: `MasteryRecomputeCompleted`.
  9. Scheduler uses new algorithm version for new mastery computations.
- **Failure Handling**: recompute job failure → retry batches (idempotent); critical regression → kill switch (feature flag reverts to old version).
- **End Condition**: `MasteryRecomputeCompleted`; all mastery scores under new version.

---

## 9. Subscription Upgrade

- **Trigger**: User clicks "Upgrade to Pro."
- **Steps**:
  1. `UpgradeSubscription` command (validation: user subscribed; target plan higher-tier).
  2. Billing context calls Stripe (prorated charge).
  3. On success: subscription `billing_plan_id` updated; `SubscriptionUpgraded` event.
  4. Learning context consumes event → updates entitlements (e.g., unlimited questions).
  5. User sees upgraded features immediately.
- **Failure Handling**: payment failed → `PAYMENT_FAILED`; subscription unchanged; user notified.
- **End Condition**: `SubscriptionUpgraded`; entitlements active.

---

## 10. Organization Creation (B2B)

- **Trigger**: Administrator creates an organization (or self-service B2B signup, future).
- **Steps**:
  1. `CreateOrganization` → `OrganizationCreated`.
  2. Administrator adds members: `AddOrganizationMember` (per user) → `OrganizationMemberAdded`.
  3. Organization subscribes to a plan (org-level `SubscribeToPlan`).
  4. Members inherit organization entitlements.
  5. Org admin can assign Instructor roles within the org's subjects (future).
- **Failure Handling**: user already a member of another org → `ALREADY_A_MEMBER` (must leave first).
- **End Condition**: organization active; members added; subscription active.

---

## 11. Subject Creation

- **Trigger**: Administrator decides to add a new subject (e.g., SQL).
- **Steps**:
  1. `CreateSubject` → `SubjectCreated` (status `draft`).
  2. Instructors author concepts, objectives, misconceptions, templates (each `Create*` command).
  3. Instructors create learning paths (`CreateLearningPath`).
  4. Instructors bundle artifacts into content packs; submit for review; publish (`PublishContentPack`).
  5. After minimum content met: `PublishSubject` → `SubjectPublished`.
  6. Subject available for enrollment.
- **Failure Handling**: minimum content not met → `MINIMUM_CONTENT_NOT_MET`.
- **End Condition**: `SubjectPublished`; learners can enroll.

---

## 12. Achievement Unlock

- **Trigger**: Event subscriber detects criteria met (e.g., `ConceptStateChanged` to `mastered` for the first time).
- **Steps**:
  1. Event subscriber (learning context) evaluates achievement criteria.
  2. If criteria met and not already granted: `GrantAchievement` command.
  3. `AchievementGranted` event.
  4. Notification context queues "Achievement unlocked!" notification.
  5. Learner sees badge on dashboard.
- **Failure Handling**: already granted → `ALREADY_GRANTED` (idempotent; subscriber dedupes).
- **End Condition**: `AchievementGranted`.

---

## 13. GDPR Deletion

- **Trigger**: User submits `RequestAccountDeletion`.
- **Steps**:
  1. `RequestAccountDeletion` → `AccountDeletionRequested` (status `pending_deletion`).
  2. 14-day grace period (user can cancel via `CancelAccountDeletion`).
  3. After grace: `AnonymizeUser` background job runs.
  4. PII purged (email, display_name, credentials, sessions); learning data retained (anonymized); billing retained (tax); audit logs retained (actor anonymized).
  5. `UserAnonymized` event.
  6. Billing context cancels active subscription; analytics context anonymizes learner data.
- **Failure Handling**: anonymization job failure → retry; partial anonymization → idempotent re-run.
- **End Condition**: `UserAnonymized`; `GDPRRequestProcessed`.

---

## 14. Backup Restore (Disaster Recovery)

- **Trigger**: Primary database failure (regional) or data corruption.
- **Steps**:
  1. Detect failure (health checks).
  2. Declare incident; initiate DR failover.
  3. (Regional failure) Promote DR standby: `pg_ctl promote` on DR instance.
  4. (Data corruption) PITR: restore most recent full backup; replay WAL to target timestamp.
  5. Reconfigure application (DNS / load balancer) to point to recovered instance.
  6. Verify application health.
  7. Communicate to users (per GDPR if PII affected).
- **Failure Handling**: PITR failure → fall back to most recent full backup (lose data since backup); DR standby promotion failure → manual intervention.
- **End Condition**: Application serving from recovered instance; incident closed.

---

## 15. Disaster Recovery Failover

- **Trigger**: Primary region failure.
- **Steps**:
  1. Automated health checks detect primary unavailability (> 1 min).
  2. On-call declares incident; initiates DR failover.
  3. Promote DR standby (cross-region replica) to primary.
  4. Update DNS / load balancer to route traffic to DR region.
  5. Application reconnects; verifies health.
  6. Users redirected; service restored.
  7. Post-incident: plan failback (re-establish replication to original region) or remain in DR.
- **Failure Handling**: DR standby promotion failure → manual intervention; data loss = replication lag (target < 15s).
- **End Condition**: Service restored from DR region; RTO 4h, RPO 15min (per `14-backup-recovery.md`).

---

## 16. Notification Dispatch

- **Trigger**: Event subscriber queues a notification (e.g., `ReviewScheduled` → review reminder for tomorrow).
- **Steps**:
  1. Event subscriber calls `QueueNotification` (respects user preferences, dedup).
  2. `NotificationQueued` event; notification status `queued`.
  3. Dispatch worker picks up queued notifications (`DispatchNotification` command).
  4. Worker sends via channel (email/Push/in-app).
  5. On success: `NotificationSent` → `delivered` (on channel confirmation).
  6. On failure: retry with backoff; after max retries, `NotificationFailed` → dead-letter.
  7. User opens/dismisses → status updated.
- **Failure Handling**: delivery failure → retry (max 5); user not found → drop; channel disabled by user → drop.
- **End Condition**: `delivered`, `opened`, `dismissed`, or `failed`.

---

## 17. Code Execution (Sandbox)

- **Trigger**: Learner submits code for a `code_execution` question (pre-submission testing or final submission).
- **Steps**:
  1. `ExecuteCode` command (validation: code size, language).
  2. Assessment context sends code to sandbox runtime (isolated container, no network, resource limits).
  3. Sandbox executes code against test cases; returns pass/fail + output.
  4. `CodeExecuted` event (for analytics).
  5. Results returned to learner.
  6. (If final submission) `SubmitAnswer` proceeds with execution results as the answer.
- **Failure Handling**: sandbox unavailable → `SANDBOX_UNAVAILABLE` (retry); timeout → `EXECUTION_TIMEOUT`; resource limit → `RESOURCE_LIMIT_EXCEEDED`.
- **End Condition**: execution results returned.

---

*End of Workflows.*
