# Domain Event Catalog

> Every domain event in the Mastery Engine domain model with its trigger, payload, and consumers.

---

## What is a Domain Event?

A domain event is an immutable record of something that happened in the domain. Events are named in past tense, carry all information needed for subscribers, and are collected by aggregate roots for the application layer to publish via the outbox pattern (ADR-0012).

---

## Events by Context

### Identity (10 events)

| Event | Trigger | Key Payload |
|---|---|---|
| `UserRegistered` | `User.register()` | user_id, email |
| `EmailVerified` | `User.verify_email()` | user_id |
| `UserSuspended` | `User.suspend()` | user_id, reason |
| `UserReactivated` | `User.reactivate()` | user_id |
| `AccountDeletionRequested` | `User.request_deletion()` | user_id, scheduled_anonymization_at |
| `AccountDeletionCancelled` | `User.cancel_deletion()` | user_id |
| `UserAnonymized` | `User.anonymize()` | user_id |
| `MFAEnabled` | `User.enable_mfa()` | user_id |
| `MFADisabled` | `User.disable_mfa()` | user_id |
| `UserProfileUpdated` | `User.update_profile()` | user_id, changed_fields |

### Content (23 events)

| Event | Trigger |
|---|---|
| `SubjectCreated` | `Subject.create()` |
| `SubjectPublished` | `Subject.publish()` |
| `SubjectDeprecated` | `Subject.deprecate()` |
| `LearningPathCreated` | Path creation |
| `ConceptCreated` | `Concept.create()` |
| `ConceptRevised` | `Concept.revise()` |
| `ConceptDependencyAdded` | `Concept.add_dependency()` |
| `ConceptPublished` | `Concept.publish()` |
| `ConceptDeprecated` | `Concept.deprecate()` |
| `LearningObjectiveCreated` | `LearningObjective.create()` |
| `MisconceptionCreated` | `Misconception.create()` |
| `QuestionTemplateCreated` | `QuestionTemplate.create()` |
| `QuestionTemplateRevised` | Template revision |
| `QuestionTemplatePublished` | `QuestionTemplate.publish()` |
| `QuestionTemplateDeprecated` | `QuestionTemplate.deprecate()` |
| `ContentPackSubmittedForReview` | `ContentPack.submit_for_review()` |
| `ContentPackApproved` | `ContentPack.approve()` |
| `ContentPackChangesRequested` | `ContentPack.request_changes()` |
| `ContentPackRejected` | `ContentPack.reject()` |
| `ContentPackPublished` | `ContentPack.publish()` |
| `ContentVersionCreated` | Version creation |
| `ContentVersionDeprecated` | `ContentVersion.deprecate()` |
| `ContentPackImported` | Import |

### Assessment (4 events)

| Event | Trigger | Key Payload |
|---|---|---|
| `QuestionInstanceServed` | `QuestionInstance.serve()` | instance_id, enrollment_id, template_version_id |
| `QuestionInstanceAnswered` | `QuestionInstance.mark_answered()` | instance_id, attempt_id, scoring_outcome |
| `QuestionInstanceAbandoned` | `QuestionInstance.abandon()` | instance_id |
| `AttemptRecorded` | `Attempt.record()` | attempt_id, enrollment_id, concept_ids, scoring_outcome, triple versioning IDs |

### Mastery (6 events)

| Event | Trigger | Key Payload |
|---|---|---|
| `MasteryUpdated` | `MasteryScore.apply_update()` | mastery_score_id, enrollment_id, concept_id, scores, algorithm_version_id |
| `ConceptStateChanged` | `MasteryScore.apply_update()` (state change) | enrollment_id, concept_id, old_state, new_state |
| `WeakConceptDetected` | `MasteryScore.apply_update()` (weakness) | enrollment_id, concept_id, severity |
| `ReviewScheduled` | `Review.schedule()` / `Review.reschedule()` | review_id, enrollment_id, concept_id, due_at, priority, interval_days |
| `AlgorithmVersionPublished` | `AlgorithmVersion.promote()` | algorithm_version_id, version_number, previous_version_number |
| `LearnerMisconceptionCleared` | Misconception clearing | learner_misconception_id |

### Learning (15 events)

| Event | Trigger |
|---|---|
| `LearnerEnrolled` | `LearnerEnrollment.enroll()` |
| `OnboardingCompleted` | `LearnerEnrollment.complete_onboarding()` |
| `LearnerUnenrolled` | `LearnerEnrollment.unenroll()` |
| `StudySessionStarted` | `StudySession.start()` |
| `StudySessionPaused` | `StudySession.pause()` |
| `StudySessionResumed` | `StudySession.resume()` |
| `StudySessionEnded` | `StudySession.end()` |
| `StudySessionAbandoned` | `StudySession.abandon()` |
| `LearningGoalSet` | `LearningGoal.set()` |
| `LearningGoalCleared` | `LearningGoal.abandon()` |
| `RecommendationGenerated` | `Recommendation.generate()` |
| `RecommendationDismissed` | `Recommendation.dismiss()` |
| `AchievementGranted` | `Achievement.grant()` |
| `StreakUpdated` | `Streak.record_study()` |
| `StreakReset` | `Streak` gap detected |

### Scheduling (6 events)

| Event | Trigger |
|---|---|
| `DailyQueueGenerated` | `DailyQueue.generate()` |
| `DailyQueueCompleted` | `DailyQueue.mark_completed()` |
| `DailyQueueExpired` | `DailyQueue.expire()` |
| `SchedulingConfigCreated` | `SchedulingConfig.create()` |
| `SchedulingConfigUpdated` | `SchedulingConfig.update_parameters()` |
| `SchedulingConfigDeactivated` | `SchedulingConfig.deactivate()` |

### Billing (14 events)

| Event | Trigger |
|---|---|
| `SubscriptionActivated` | `Subscription.subscribe()` |
| `SubscriptionUpgraded` | `Subscription.upgrade()` |
| `SubscriptionDowngradeScheduled` | `Subscription.downgrade()` |
| `SubscriptionCanceled` | `Subscription.cancel()` |
| `SubscriptionRenewed` | `Subscription.renew()` |
| `SubscriptionPastDue` | `Subscription.mark_past_due()` |
| `SubscriptionExpired` | `Subscription.expire()` |
| `InvoiceIssued` | `Invoice.issue()` |
| `InvoicePaid` | `Invoice.mark_paid()` |
| `InvoiceFailed` | `Invoice.mark_failed()` |
| `InvoiceRefunded` | `Invoice.refund()` |
| `BillingPlanCreated` | `BillingPlan.create()` |
| `BillingPlanDeprecated` | `BillingPlan.deprecate()` |
| `PaymentProcessed` | Payment webhook |

### Administration (8+ events)

| Event | Trigger |
|---|---|
| `NotificationQueued` | `Notification.queue()` |
| `NotificationSent` | `Notification.mark_sent()` |
| `NotificationDelivered` | `Notification.mark_delivered()` |
| `NotificationFailed` | `Notification.mark_failed()` |
| `FeatureFlagCreated` | `FeatureFlag.create()` |
| `FeatureFlagUpdated` | `FeatureFlag.update()` |
| `FeatureFlagRetired` | `FeatureFlag.retire()` |
| `OrganizationCreated` | `Organization.create()` |
| `OrganizationSuspended` | `Organization.suspend()` |

---

## Event Base Class

All events inherit from `DomainEvent` (frozen dataclass):
- `event_id: UUID` — unique, auto-generated.
- `occurred_at: datetime` — auto-generated, UTC.
- `event_type: str` — the class name (property).

---

## Event Collection Pattern

Aggregate roots collect events via `self._record_event(event)`. The application layer retrieves them via `aggregate.collect_events()` after successful persistence and publishes them via the outbox pattern.
