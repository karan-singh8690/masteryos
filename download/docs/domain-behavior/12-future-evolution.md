# 12 — Future Evolution

> How the behavioral model evolves to support ML, collaborative learning, peer review, AI tutoring, offline mode, mobile sync, marketplace, enterprise organizations, real-time classrooms.

---

## Evolution Principles

1. **New behaviors are additive** — new commands, events, and state machines are added; existing ones are rarely removed.
2. **Event versioning handles schema evolution** — breaking changes produce new event versions (per `08-event-versioning.md`).
3. **Each evolution is a new ADR** — significant behavioral changes require an ADR documenting the rationale.
4. **Backward compatibility is preserved** — existing subscribers continue to work during migration.

---

## 1. Machine Learning (per ADR-0007)

### New Commands
- `TrainMLModel` — train a candidate ML model offline (background job).
- `StartShadowEvaluation` — run a candidate model in shadow mode.
- `EvaluateMLModel` — evaluate a candidate model against the documented protocol.
- `PromoteMLModel` — promote a candidate model to production (becomes a new Algorithm Version).

### New Events
- `MLModelTrained` — a candidate model finished training.
- `ShadowEvaluationStarted` — shadow mode begins.
- `ShadowEvaluationCompleted` — shadow mode ends; evaluation results available.
- `MLModelPromoted` — a candidate model is promoted (alias for `AlgorithmVersionPublished`).

### New State Machine: ML Model
- `draft` → `training` → `evaluated` → `shadow` → `promoted` (or `rejected`).
- Reuses the Algorithm Version state machine with ML-specific stages.

### Impact on Existing Behavior
- `UpdateMastery` may use an ML model instead of the deterministic algorithm (transparent to callers; the algorithm version records which model was used).
- `GenerateAdaptiveQueue` may use ML-ranked candidates (transparent; the Scheduler's interface is unchanged).

---

## 2. Collaborative Learning

### New Commands
- `CreateStudyGroup` — create a group of learners.
- `InviteToStudyGroup` — invite a learner.
- `JoinStudyGroup` — accept invitation.
- `StartGroupSession` — start a collaborative session.
- `ShareProgress` — share progress with group.

### New Events
- `StudyGroupCreated`, `StudyGroupJoined`, `GroupSessionStarted`, `ProgressShared`.

### New State Machine: Study Group
- `active` → `dissolved`.

### Impact
- New bounded context (`collaboration`) or sub-context within `learning`.
- Queries: `GetStudyGroup`, `GetGroupProgress`.
- The learning loop is unchanged; collaborative features are additive.

---

## 3. Peer Review (Learners reviewing each other)

### New Commands
- `SubmitPeerReview` — a learner reviews another's answer.
- `EvaluatePeerReview` — system evaluates the review's quality.

### New Events
- `PeerReviewSubmitted`, `PeerReviewEvaluated`.

### Impact
- New question type: `peer_reviewed_free_response`.
- The assessment flow adds a peer-review stage between submission and final scoring.
- Idempotency: peer reviews are deduplicated by `(reviewer, reviewee, attempt)`.

---

## 4. AI Tutoring (assistive, not authoritative)

### Design Constraint
Per ADR-0009, AI is forbidden from runtime learning decisions. AI tutoring is permitted only as an optional, clearly-labeled assistive layer.

### New Commands
- `RequestAITutorExplanation` — learner requests an alternative explanation (clearly labeled "AI-generated, not reviewed").
- `RateAITutorExplanation` — learner rates the explanation (for quality monitoring).

### New Events
- `AITutorExplanationRequested`, `AITutorExplanationRated`.

### Impact
- AI tutoring is a read-only assistive layer; it does not affect mastery, scheduling, or content.
- The human-authored Explanation remains the source of truth.
- AI tutoring is feature-flagged; learners can disable it.

---

## 5. Offline Mode

### New Commands
- `SyncOfflineAttempts` — client uploads attempts made offline.
- `AcknowledgeSync` — client acknowledges successful sync.

### New Events
- `OfflineAttemptsSynced`, `SyncAcknowledged`.

### Impact
- `SubmitAnswer` is extended to accept offline timestamps; the attempt's `created_at` is the offline time.
- Conflict resolution: if the same question was answered online and offline, the server reconciles by timestamp (the earlier attempt wins; the later is recorded as a separate attempt).
- The learning loop is unchanged; offline is a client-side concern with a sync command.

---

## 6. Mobile Sync

### New Commands
- `RegisterDevice` — register a mobile device (for push notifications).
- `UnregisterDevice` — unregister.
- `SyncDeviceState` — sync device state (e.g., downloaded content for offline).

### New Events
- `DeviceRegistered`, `DeviceUnregistered`, `DeviceStateSynced`.

### Impact
- New `identity.devices` table (per Task 004 `15-future-evolution.md`).
- Push notifications use device tokens.
- The learning loop is unchanged; mobile sync is a client-side concern.

---

## 7. Marketplace (third-party content)

### New Commands
- `CreateContentListing` — author lists content for sale.
- `PurchaseContent` — learner purchases marketplace content.
- `PayoutRevenueShare` — system pays the author their share.

### New Events
- `ContentListingCreated`, `ContentPurchased`, `RevenueSharePaid`.

### Impact
- New bounded context (`marketplace`) or sub-context within `content` and `billing`.
- Marketplace content goes through the same Review Workflow as platform content.
- Entitlements: purchasing marketplace content grants access to that content (not a subscription).

---

## 8. Enterprise Organizations (B2B)

### New Commands
- `CreateOrganizationSSOConfig` — configure SAML/OIDC SSO.
- `SyncOrganizationMembers` — sync members from IdP.
- `GenerateOrganizationReport` — generate aggregate analytics for an org.

### New Events
- `OrganizationSSOConfigured`, `OrganizationMembersSynced`, `OrganizationReportGenerated`.

### Impact
- Extends the existing `administration.organizations` (per Task 004).
- SSO login flow: `LoginWithSAML` / `LoginWithOIDC` commands (alongside `LoginWithOAuth`).
- Org admins have scoped admin privileges (org-scoped, not platform-wide).

---

## 9. Real-Time Classrooms (future)

### New Commands
- `CreateClassroom` — create a live classroom session.
- `JoinClassroom` — learner joins.
- `BroadcastQuestion` — instructor broadcasts a question to all learners.
- `SubmitClassroomAnswer` — learner submits (real-time).
- `EndClassroom` — instructor ends.

### New Events
- `ClassroomCreated`, `LearnerJoinedClassroom`, `QuestionBroadcast`, `ClassroomAnswerSubmitted`, `ClassroomEnded`.

### Impact
- New bounded context (`classroom`).
- Real-time communication via WebSocket.
- Classroom answers are recorded as attempts (with `attempt_intent = 'classroom'`).
- The learning loop is unchanged; classroom is an additional interaction mode.

---

## 10. Internationalization (i18n)

### Impact on Behavior
- Commands and events are language-agnostic (payloads carry `locale` where relevant).
- Content queries return localized content based on `user_profiles.locale`.
- Notifications are templated per locale.

### New Commands
- `SetContentLocale` — author provides a translation (per Task 004 `15-future-evolution.md`).

### New Events
- `ContentLocaleAdded`.

---

## 11. Knowledge Graph Evolution

### New Commands
- `AddCrossSubjectDependency` — link concepts across subjects (per Task 004 `15-future-evolution.md`).
- `ComputeGraphAnalytics` — compute centrality, clusters.

### New Events
- `CrossSubjectDependencyAdded`, `GraphAnalyticsComputed`.

---

## 12. Vector Search / Embeddings

### New Commands
- `GenerateConceptEmbedding` — compute embedding for a concept (background).
- `GenerateLearnerEmbedding` — compute embedding for a learner (background).
- `SearchSimilarConcepts` — vector similarity search.

### New Events
- `ConceptEmbeddingGenerated`, `LearnerEmbeddingGenerated`.

### Impact
- New `pgvector` extension (per Task 004 `15-future-evolution.md`).
- Vector search is a query type; the learning loop is unchanged.

---

## Evolution Summary

| Evolution | New Commands | New Events | New Contexts | ADR Required |
|---|---|---|---|---|
| Machine Learning | 4 | 4 | none (extends mastery) | yes (ADR-0007 covers; new ADR for ML-specific) |
| Collaborative Learning | 5 | 4 | collaboration (new) | yes |
| Peer Review | 2 | 2 | none (extends assessment) | yes |
| AI Tutoring | 2 | 2 | none (assistive layer) | yes |
| Offline Mode | 2 | 2 | none (extends learning) | yes |
| Mobile Sync | 3 | 3 | none (extends identity) | yes |
| Marketplace | 3 | 3 | marketplace (new) | yes |
| Enterprise SSO | 3 | 3 | none (extends administration) | yes |
| Real-Time Classrooms | 5 | 5 | classroom (new) | yes |
| Internationalization | 1 | 1 | none (extends content) | yes |
| Knowledge Graph | 2 | 2 | none (extends content) | yes |
| Vector Search | 3 | 2 | none (extends analytics) | yes |

---

## Closing Note

The behavioral model is designed to evolve. Every evolution described here is additive (new commands, events, state machines); none requires rewriting existing behavior. The outbox pattern + idempotent subscribers + event versioning ensure that evolution does not break existing flows.

The role of this document is to anticipate the evolutions the team expects, so that when the time comes, the behavioral model is ready. Each evolution will be a new ADR, new commands, new events, and a new chapter in the system's behavior.

---

*End of Future Evolution.*
