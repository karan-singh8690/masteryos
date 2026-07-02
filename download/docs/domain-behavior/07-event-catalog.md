# 07 — Event Catalog

> Complete event catalog, grouped by bounded context.
> Shows producer, consumers, ordering, criticality, retention, and replay support for every event.

---

## Catalog Legend

- **Ordering**: per-aggregate (events for the same aggregate are ordered); global (all events ordered); none.
- **Criticality**: critical (system function depends on it); standard (best-effort).
- **Retention**: how long the event is retained in the outbox; archival policy.
- **Replay**: whether the event can be replayed (re-processed by subscribers).

---

## Identity Events

| Event | Producer | Consumers | Ordering | Criticality | Retention | Replay |
|---|---|---|---|---|---|---|
| `UserRegistered` | identity | analytics, administration | per user | standard | 90 days | yes |
| `EmailVerified` | identity | analytics, administration | per user | standard | 90 days | yes |
| `UserLoggedIn` | identity | analytics, administration | per user | standard | 90 days | yes |
| `UserLoggedOut` | identity | analytics, administration | per session | standard | 90 days | yes |
| `TokenRefreshed` | identity | administration | per session | standard | 30 days | no |
| `SessionRevoked` | identity | administration | per session | standard | 90 days | yes |
| `AllSessionsRevoked` | identity | administration | per user | standard | 90 days | yes |
| `UserProfileUpdated` | identity | analytics, administration | per user | standard | 90 days | no |
| `PasswordChanged` | identity | administration | per user | standard | 90 days | no |
| `PasswordReset` | identity | administration | per user | standard | 90 days | no |
| `PasswordResetRequested` | identity | administration | per email | standard | 30 days | no |
| `OAuthAccountLinked` | identity | administration | per user | standard | 90 days | no |
| `OAuthAccountUnlinked` | identity | administration | per user | standard | 90 days | no |
| `MFAEnabled` | identity | administration | per user | standard | 90 days | no |
| `MFADisabled` | identity | administration | per user | standard | 90 days | no |
| `VerificationEmailQueued` | identity | administration (dispatch) | per user | standard | 30 days | yes |
| `UserSuspended` | identity | analytics, administration | per user | standard | 90 days | yes |
| `UserReactivated` | identity | analytics, administration | per user | standard | 90 days | yes |
| `AccountDeletionRequested` | identity | administration, analytics | per user | critical | 7 years | yes |
| `UserAnonymized` | identity | analytics, administration, billing | per user | critical | 7 years | yes |

---

## Content Events

| Event | Producer | Consumers | Ordering | Criticality | Retention | Replay |
|---|---|---|---|---|---|---|
| `SubjectCreated` | content | analytics, administration | per subject | standard | indefinite | yes |
| `SubjectPublished` | content | analytics, administration | per subject | standard | indefinite | yes |
| `SubjectDeprecated` | content | analytics, administration, learning | per subject | standard | indefinite | yes |
| `LearningPathCreated` | content | analytics | per path | standard | indefinite | yes |
| `ConceptCreated` | content | analytics | per concept | standard | indefinite | yes |
| `ConceptRevised` | content | analytics | per concept | standard | indefinite | yes |
| `ConceptDependencyAdded` | content | analytics | per source concept | standard | indefinite | yes |
| `LearningObjectiveCreated` | content | analytics | per concept | standard | indefinite | yes |
| `MisconceptionCreated` | content | analytics | per objective | standard | indefinite | yes |
| `QuestionTemplateCreated` | content | analytics | per template | standard | indefinite | yes |
| `QuestionTemplateRevised` | content | analytics | per template | standard | indefinite | yes |
| `ContentPackSubmittedForReview` | content | administration | per pack | standard | indefinite | yes |
| `ContentPackApproved` | content | administration | per pack (stage order) | standard | indefinite | yes |
| `ContentPackChangesRequested` | content | administration | per pack | standard | indefinite | yes |
| `ContentPackRejected` | content | administration | per pack | standard | indefinite | yes |
| `ContentPackPublished` | content | analytics, scheduling, learning | per subject | critical | indefinite | yes |
| `ContentVersionCreated` | content | analytics, scheduling | per subject (monotonic) | critical | indefinite | yes |
| `ContentArchived` | content | scheduling, learning | per content | standard | indefinite | yes |
| `ContentPackImported` | content | administration | per pack | standard | indefinite | yes |

---

## Learning Events

| Event | Producer | Consumers | Ordering | Criticality | Retention | Replay |
|---|---|---|---|---|---|---|
| `LearnerEnrolled` | learning | analytics, administration | per user | standard | indefinite | yes |
| `OnboardingCompleted` | learning | analytics, scheduling | per enrollment | standard | indefinite | yes |
| `LearningGoalSet` | learning | scheduling, analytics | per enrollment | standard | indefinite | yes |
| `LearningGoalCleared` | learning | scheduling | per goal | standard | indefinite | yes |
| `StudySessionStarted` | learning | analytics, scheduling | per enrollment | standard | 1 year | yes |
| `StudySessionResumed` | learning | analytics | per session | standard | 1 year | no |
| `StudySessionPaused` | learning | analytics | per session | standard | 1 year | no |
| `StudySessionEnded` | learning | analytics, administration | per session | standard | 1 year | yes |
| `SessionAnalyticsComputed` | learning | analytics | per session | standard | 1 year | no |
| `HintRequested` | learning | analytics | per question (tier order) | standard | 1 year | no |
| `QuestionAbandoned` | learning | analytics | per question | standard | 1 year | no |
| `RecommendationGenerated` | scheduling | learning, analytics | per enrollment | standard | 1 year | yes |
| `RecommendationDismissed` | learning | analytics | per recommendation | standard | 1 year | no |
| `LearnerUnenrolled` | learning | analytics, administration | per enrollment | standard | indefinite | yes |

---

## Assessment Events

| Event | Producer | Consumers | Ordering | Criticality | Retention | Replay |
|---|---|---|---|---|---|---|
| `AnswerSubmitted` | assessment | analytics | per attempt | standard | indefinite | yes |
| `AttemptRecorded` | assessment | mastery, analytics, administration | per learner (chronological) | critical | indefinite | yes |
| `AttemptScored` | assessment | analytics | per attempt | standard | indefinite | no |
| `CodeExecuted` | assessment | analytics | per question | standard | 30 days | no |

---

## Mastery Events

| Event | Producer | Consumers | Ordering | Criticality | Retention | Replay |
|---|---|---|---|---|---|---|
| `MasteryUpdated` | mastery | scheduling, analytics, learning | per learner-concept (chronological) | critical | indefinite | yes |
| `ConceptStateChanged` | mastery | learning (achievements), analytics | per learner-concept | critical | indefinite | yes |
| `WeakConceptDetected` | mastery | scheduling, learning | per learner-concept | standard | indefinite | yes |
| `ReviewScheduled` | mastery | scheduling | per learner-concept | standard | indefinite | yes |
| `LearnerMisconceptionCleared` | mastery | analytics | per learner-misconception | standard | indefinite | yes |
| `AlgorithmVersionPublished` | mastery | mastery (recompute), administration, analytics | global (monotonic) | critical | indefinite | yes |
| `MasteryRecomputeStarted` | mastery | administration | per algorithm version | standard | 1 year | no |
| `MasteryRecomputeProgressed` | mastery | administration | per algorithm version (monotonic) | standard | 1 year | no |
| `MasteryRecomputeCompleted` | mastery | administration | per algorithm version | standard | 1 year | no |

---

## Scheduling Events

| Event | Producer | Consumers | Ordering | Criticality | Retention | Replay |
|---|---|---|---|---|---|---|
| `AdaptiveQueueGenerated` | scheduling | analytics | per session | standard | 30 days | no |
| `DailyQueueGenerated` | scheduling | analytics | per enrollment per date | standard | 30 days | no |
| `SchedulingConfigUpdated` | scheduling | administration | per subject | standard | indefinite | yes |

---

## Analytics Events

| Event | Producer | Consumers | Ordering | Criticality | Retention | Replay |
|---|---|---|---|---|---|---|
| `NightlySnapshotsComputed` | analytics | administration | per date | standard | 1 year | no |
| `ConceptStatisticsRecomputed` | analytics | administration | per concept per date | standard | 1 year | no |
| `TemplateStatisticsRecomputed` | analytics | administration | per template per date | standard | 1 year | no |

---

## Billing Events

| Event | Producer | Consumers | Ordering | Criticality | Retention | Replay |
|---|---|---|---|---|---|---|
| `SubscriptionActivated` | billing | learning, administration | per user | standard | 7 years | yes |
| `SubscriptionUpgraded` | billing | learning, administration | per subscription | standard | 7 years | yes |
| `SubscriptionDowngradeScheduled` | billing | learning, administration | per subscription | standard | 7 years | yes |
| `SubscriptionCanceled` | billing | learning, administration | per subscription | standard | 7 years | yes |
| `SubscriptionRenewed` | billing | administration | per subscription | standard | 7 years | yes |
| `SubscriptionPastDue` | billing | learning, administration | per subscription | standard | 7 years | yes |
| `PaymentProcessed` | billing | administration | per invoice | standard | 7 years | yes |
| `InvoiceRefunded` | billing | administration | per invoice | standard | 7 years | yes |

---

## Administration Events

| Event | Producer | Consumers | Ordering | Criticality | Retention | Replay |
|---|---|---|---|---|---|---|
| `RoleGranted` | administration | administration, analytics | per user | standard | 7 years | yes |
| `RoleRevoked` | administration | administration | per user | standard | 7 years | yes |
| `FeatureFlagCreated` | administration | administration | per flag | standard | indefinite | yes |
| `FeatureFlagUpdated` | administration | administration, application | per flag | standard | indefinite | yes |
| `FeatureFlagRetired` | administration | administration, application | per flag | standard | indefinite | yes |
| `SystemSettingUpdated` | administration | administration, application | per key | standard | indefinite | yes |
| `NotificationQueued` | administration | administration (dispatch) | per user (chronological) | standard | 30 days | yes |
| `NotificationSent` | administration | analytics | per notification | standard | 30 days | no |
| `NotificationFailed` | administration | administration (alerting) | per notification | standard | 30 days | no |
| `OrganizationCreated` | administration | billing, analytics | per org | standard | indefinite | yes |
| `OrganizationMemberAdded` | administration | analytics, administration | per org | standard | indefinite | yes |
| `OrganizationMemberRemoved` | administration | analytics, administration | per org | standard | indefinite | yes |
| `GDPRRequestProcessed` | administration | administration | per request | critical | 7 years | yes |
| `AchievementGranted` | learning | administration (notification), analytics | per enrollment | standard | indefinite | yes |
| `BackgroundJobDeadLettered` | infrastructure | administration (alerting) | per job | standard | 90 days | no |
| `MigrationApplied` | infrastructure | administration | global (monotonic) | critical | indefinite | yes |

---

## Critical Events (require guaranteed delivery)

The following events are **critical**: subscribers must process them, and delivery failures require manual intervention.

- `AttemptRecorded` — mastery depends on it.
- `MasteryUpdated` — scheduling depends on it.
- `ConceptStateChanged` — achievements depend on it.
- `ContentPackPublished` / `ContentVersionCreated` — cache invalidation depends on it.
- `AlgorithmVersionPublished` — triggers recompute.
- `AccountDeletionRequested` / `UserAnonymized` — GDPR compliance.
- `GDPRRequestProcessed` — GDPR compliance.
- `MigrationApplied` — schema audit.

Critical events use a separate outbox dispatch queue with higher priority and more aggressive retry (max 10 attempts vs 5 for standard).

---

## Replay Support

Events marked "replay: yes" can be re-processed by subscribers (e.g., to backfill a new subscriber or recover from a subscriber failure). Replay is safe because:

1. **Subscribers are idempotent** (see `11-idempotency.md`).
2. **Events carry enough context** (payload includes all needed fields; no implicit state).
3. **Ordering is preserved** (per-aggregate ordering ensures replay produces the same final state).

Replay is initiated by an administrator via the admin portal: select an event type and date range, and the dispatcher re-publishes the events. Subscribers process them as if they were new.

Events marked "replay: no" are transient (e.g., `TokenRefreshed`, `HintRequested`) and reprocessing them has no meaningful effect (idempotent but pointless).

---

*End of Event Catalog.*
