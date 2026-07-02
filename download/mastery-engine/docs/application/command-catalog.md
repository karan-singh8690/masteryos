# Command Catalog

> Every command in the application layer with its handler and DTO.

---

## Command Pattern

Every write operation is a Command:
1. **Command DTO** (frozen dataclass) — the request.
2. **Command Handler** (class implementing `CommandHandler[C, R]`) — the orchestrator.
3. **Command Result** (`CommandResult[R]`) — success/failure + value + events.

---

## Identity Context

| Command | Handler | DTO |
|---|---|---|
| `RegisterUserCommand` | `RegisterUserHandler` | `UserDTO` |
| `VerifyEmailCommand` | `VerifyEmailHandler` | `UserDTO` |
| `AuthenticateUserCommand` | (future) | `AuthResultDTO` |
| `RequestPasswordResetCommand` | (future) | `None` |
| `ResetPasswordCommand` | (future) | `None` |
| `LogoutUserCommand` | (future) | `None` |
| `RequestAccountDeletionCommand` | `RequestAccountDeletionHandler` | `UserDTO` |
| `CancelAccountDeletionCommand` | `CancelAccountDeletionHandler` | `UserDTO` |
| `SuspendUserCommand` | `SuspendUserHandler` | `UserDTO` |
| `ReactivateUserCommand` | `ReactivateUserHandler` | `UserDTO` |
| `AnonymizeUserCommand` | `AnonymizeUserHandler` | `UserDTO` |

## Learning Context

| Command | Handler | DTO |
|---|---|---|
| `EnrollLearnerCommand` | `EnrollLearnerHandler` | `EnrollmentDTO` |
| `CompleteOnboardingCommand` | `CompleteOnboardingHandler` | `EnrollmentDTO` |
| `UnenrollCommand` | (future) | `EnrollmentDTO` |
| `SetLearningGoalCommand` | (future) | `LearningGoalDTO` |
| `StartStudySessionCommand` | `StartStudySessionHandler` | `StudySessionDTO` |
| `PauseStudySessionCommand` | `PauseStudySessionHandler` | `StudySessionDTO` |
| `ResumeStudySessionCommand` | `ResumeStudySessionHandler` | `StudySessionDTO` |
| `EndStudySessionCommand` | `EndStudySessionHandler` | `SessionAnalyticsDTO` |
| `DismissRecommendationCommand` | `DismissRecommendationHandler` | `None` |

## Assessment Context

| Command | Handler | DTO |
|---|---|---|
| `SubmitAttemptCommand` | `SubmitAttemptHandler` | `AttemptResultDTO` |

## Mastery Context

| Command | Handler | DTO |
|---|---|---|
| `UpdateMasteryCommand` | `UpdateMasteryHandler` | `list[MasteryScoreDTO]` |
| `PublishAlgorithmVersionCommand` | `PublishAlgorithmVersionHandler` | `None` |

## Content Context

| Command | Handler | DTO |
|---|---|---|
| `CreateSubjectCommand` | (future) | `SubjectDTO` |
| `CreateConceptCommand` | (future) | `ConceptDTO` |
| `PublishContentPackCommand` | (future) | `ContentVersionDTO` |
| `ArchiveContentCommand` | (future) | `None` |

## Billing Context

| Command | Handler | DTO |
|---|---|---|
| `SubscribeToPlanCommand` | (future) | `SubscriptionDTO` |
| `UpgradeSubscriptionCommand` | (future) | `SubscriptionDTO` |
| `CancelSubscriptionCommand` | (future) | `SubscriptionDTO` |

## Administration Context

| Command | Handler | DTO |
|---|---|---|
| `CreateFeatureFlagCommand` | (future) | `FeatureFlagDTO` |
| `CreateNotificationCommand` | (future) | `NotificationDTO` |
| `CreateOrganizationCommand` | (future) | `OrganizationDTO` |

---

## Handler Lifecycle

```
1. Receive command
2. Validate (application-level: shape, presence, constraints)
3. Begin Unit of Work
4. Load aggregates via repositories
5. Call domain behavior (entities, domain services)
6. Persist via repositories
7. Collect domain events from aggregates
8. Commit Unit of Work
9. Publish events via Event Publisher
10. Return CommandResult with DTO
```

On any exception: rollback Unit of Work; no events published; return failure result.
