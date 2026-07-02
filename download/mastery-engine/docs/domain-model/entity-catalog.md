# Entity Catalog

> Every entity in the Mastery Engine domain model with its identity, lifecycle, and responsibilities.

---

## What is an Entity?

An entity has identity (a unique ID) that persists across state changes. Two entities are equal if they have the same ID, even if their attributes differ. Entities are mutable within their invariant boundaries.

---

## Entities by Context

### Identity

| Entity | Identity | Aggregate Root | Lifecycle |
|---|---|---|---|
| User | UserId | User (root) | pending_verification → active → suspended → pending_deletion → anonymized |
| UserProfile | (embedded in User) | User | Created with User; updated independently |
| UserCredential | CredentialId | User | Created on link; deleted on unlink |

### Content

| Entity | Identity | Aggregate Root | Lifecycle |
|---|---|---|---|
| Subject | SubjectId | Subject (root) | draft → published → deprecated |
| Concept | ConceptId | Concept (root) | draft → in_review → published → deprecated |
| LearningObjective | LearningObjectiveId | Concept | draft → published → deprecated |
| Misconception | MisconceptionId | Concept | draft → published → deprecated |
| QuestionTemplate | QuestionTemplateId | QuestionTemplate (root) | draft → in_review → published → deprecated |
| TemplateVersion | TemplateVersionId | QuestionTemplate | Immutable after creation |
| ContentVersion | ContentVersionId | (standalone) | active → deprecated |
| ContentPack | ContentPackId | ContentPack (root) | draft → in_review → published/rejected |

### Assessment

| Entity | Identity | Aggregate Root | Lifecycle |
|---|---|---|---|
| QuestionInstance | QuestionInstanceId | QuestionInstance (root) | served → answered/abandoned |
| Attempt | AttemptId | Attempt (root) | Created once; **immutable** (append-only) |
| Answer | AnswerId | Attempt | Created with attempt; immutable after submission |

### Mastery

| Entity | Identity | Aggregate Root | Lifecycle |
|---|---|---|---|
| MasteryScore | MasteryScoreId | MasteryScore (root) | Initialized → updated (version increments) |
| Review | ReviewId | Review (root) | Scheduled → due → rescheduled |
| AlgorithmVersion | AlgorithmVersionId | AlgorithmVersion (root) | Created (inactive) → promoted (active) → superseded |

### Learning

| Entity | Identity | Aggregate Root | Lifecycle |
|---|---|---|---|
| LearnerEnrollment | LearnerEnrollmentId | LearnerEnrollment (root) | pending_onboarding → active → dormant → unenrolled |
| StudySession | StudySessionId | StudySession (root) | active → paused → ended/abandoned |
| LearningGoal | LearningGoalId | LearningGoal (root) | active → completed/abandoned |
| Recommendation | RecommendationId | Recommendation (root) | pending → presented → accepted/deferred/dismissed/expired |
| Achievement | AchievementId | Achievement (root) | Awarded once; **irreversible** |
| Streak | (keyed by enrollment) | Streak (root) | Updated on study; reset on gap |

### Scheduling

| Entity | Identity | Aggregate Root | Lifecycle |
|---|---|---|---|
| SchedulingConfig | SchedulingConfigId | (standalone entity) | Active → updated (versioned) → deactivated |
| DailyQueue | DailyQueueId | DailyQueue (root) | active → completed/expired |

### Billing

| Entity | Identity | Aggregate Root | Lifecycle |
|---|---|---|---|
| BillingPlan | BillingPlanId | (standalone entity) | Active → deprecated (versioned) |
| Subscription | SubscriptionId | Subscription (root) | active → past_due → canceled → expired |
| Invoice | InvoiceId | (standalone entity) | pending → paid/failed → refunded |

### Administration

| Entity | Identity | Aggregate Root | Lifecycle |
|---|---|---|---|
| AuditLog | AuditLogId | (standalone, append-only) | Created once; **immutable** |
| FeatureFlag | FeatureFlagId | FeatureFlag (root) | active → retired |
| Notification | NotificationId | Notification (root) | queued → sent → delivered → opened/dismissed; queued → failed |
| Organization | OrganizationId | Organization (root) | active → suspended → dissolved |
