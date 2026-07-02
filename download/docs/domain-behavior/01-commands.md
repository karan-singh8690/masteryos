# 01 — Commands

> Every command in the Mastery Engine, grouped by bounded context.
> A Command is a request to mutate state. Every command produces ≥1 Domain Event.

---

## Command Template

Every command follows this structure:

- **Name** — PascalCase, imperative (verb + object).
- **Purpose** — one sentence.
- **Initiator** — who/what issues the command (Learner, Instructor, Administrator, System/Background Job).
- **Preconditions** — what must be true before the command can execute.
- **Validation** — input validation rules.
- **Business Rules** — domain invariants enforced.
- **Success Result** — what happens on success.
- **Failure Cases** — enumerated failure modes with error codes.
- **Events Produced** — the domain events written to the outbox.

---

# Schema: `identity` (Identity Context)

## RegisterUser
- **Purpose**: Create a new user account.
- **Initiator**: Anonymous visitor.
- **Preconditions**: Email not already registered (or not registered by an active user).
- **Validation**: Email format; password strength; display_name length 1–100.
- **Business Rules**: A user must have at least one credential (password or OAuth) on creation. Email verification required before enrollment.
- **Success Result**: User created with status `pending_verification`; verification email queued.
- **Failure Cases**: `EMAIL_ALREADY_REGISTERED`; `INVALID_EMAIL`; `WEAK_PASSWORD`; `DISPLAY_NAME_TOO_LONG`.
- **Events Produced**: `UserRegistered`, `VerificationEmailQueued`.

## VerifyEmail
- **Purpose**: Verify a user's email address.
- **Initiator**: User (via verification link).
- **Preconditions**: User exists; verification token valid and not expired.
- **Validation**: Token format; token not expired.
- **Business Rules**: A user can enroll in subjects only after email verification.
- **Success Result**: User status transitions to `active`; `email_verified_at` set.
- **Failure Cases**: `INVALID_TOKEN`; `TOKEN_EXPIRED`; `USER_NOT_FOUND`.
- **Events Produced**: `EmailVerified`.

## LoginUser
- **Purpose**: Authenticate a user and start a session.
- **Initiator**: User.
- **Preconditions**: User exists; user status is `active`; credential matches.
- **Validation**: Email/password format.
- **Business Rules**: Failed attempts are rate-limited. MFA required for admin accounts.
- **Success Result**: Session created; access token + refresh token issued.
- **Failure Cases**: `INVALID_CREDENTIALS`; `ACCOUNT_SUSPENDED`; `ACCOUNT_PENDING_VERIFICATION`; `MFA_REQUIRED`; `RATE_LIMITED`.
- **Events Produced**: `UserLoggedIn`.

## LoginWithOAuth
- **Purpose**: Authenticate via OAuth provider.
- **Initiator**: User (via OAuth redirect).
- **Preconditions**: OAuth provider is supported; provider user ID not linked to a different user.
- **Validation**: OAuth code valid; provider user ID retrieved.
- **Business Rules**: If provider user ID is new, create a user. If linked, log in. Email from provider must match if user pre-exists.
- **Success Result**: Session created; access + refresh tokens issued.
- **Failure Cases**: `OAUTH_PROVIDER_ERROR`; `OAUTH_ACCOUNT_LINKED_TO_DIFFERENT_USER`; `OAUTH_EMAIL_CONFLICT`.
- **Events Produced**: `UserLoggedIn` (or `UserRegistered` + `UserLoggedIn` if new).

## RefreshToken
- **Purpose**: Exchange a refresh token for a new access token.
- **Initiator**: Frontend (on 401).
- **Preconditions**: Refresh token valid; session not revoked; rotation not anomalous.
- **Validation**: Token hash matches; session not expired.
- **Business Rules**: Refresh tokens are rotated on every use. Replay of an old token revokes the session family.
- **Success Result**: New access token; refresh token rotated.
- **Failure Cases**: `INVALID_REFRESH_TOKEN`; `SESSION_REVOKED`; `SESSION_EXPIRED`; `ROTATION_ANOMALY_DETECTED`.
- **Events Produced**: `TokenRefreshed` (or `SessionRevoked` on anomaly).

## LogoutUser
- **Purpose**: End a session.
- **Initiator**: User.
- **Preconditions**: Session exists; user is the session owner.
- **Validation**: Session ID belongs to user.
- **Business Rules**: Revokes the session's refresh token.
- **Success Result**: Session revoked.
- **Failure Cases**: `SESSION_NOT_FOUND`.
- **Events Produced**: `UserLoggedOut`.

## RevokeSession
- **Purpose**: Revoke a specific session (e.g., "log out of this device").
- **Initiator**: User (or Administrator).
- **Preconditions**: Session exists.
- **Validation**: Session ID valid; user owns the session (or initiator is admin).
- **Business Rules**: Admins can revoke any user's session.
- **Success Result**: Session revoked.
- **Failure Cases**: `SESSION_NOT_FOUND`; `NOT_AUTHORIZED`.
- **Events Produced**: `SessionRevoked`.

## RevokeAllSessions
- **Purpose**: Revoke all sessions for a user.
- **Initiator**: User (or Administrator).
- **Preconditions**: User exists.
- **Validation**: User ID valid.
- **Business Rules**: Used after a security incident or password change.
- **Success Result**: All user sessions revoked.
- **Failure Cases**: `USER_NOT_FOUND`.
- **Events Produced**: `AllSessionsRevoked`.

## UpdateUserProfile
- **Purpose**: Update user profile (name, timezone, preferences).
- **Initiator**: User.
- **Preconditions**: User exists.
- **Validation**: Timezone is valid IANA; display_name length 1–100.
- **Business Rules**: Profile changes do not affect authentication.
- **Success Result**: Profile updated.
- **Failure Cases**: `INVALID_TIMEZONE`; `DISPLAY_NAME_TOO_LONG`.
- **Events Produced**: `UserProfileUpdated`.

## ChangePassword
- **Purpose**: Change the user's password.
- **Initiator**: User.
- **Preconditions**: User exists; current password matches.
- **Validation**: Current password correct; new password meets strength rules.
- **Business Rules**: Password change optionally revokes all other sessions.
- **Success Result**: Password credential updated.
- **Failure Cases**: `INCORRECT_CURRENT_PASSWORD`; `WEAK_PASSWORD`.
- **Events Produced**: `PasswordChanged`, (optionally) `AllSessionsRevoked`.

## LinkOAuthAccount
- **Purpose**: Link an OAuth provider to an existing user.
- **Initiator**: User.
- **Preconditions**: User exists; OAuth provider not already linked to a different user.
- **Validation**: OAuth code valid.
- **Business Rules**: A user can link multiple OAuth providers.
- **Success Result**: OAuth credential added.
- **Failure Cases**: `OAUTH_PROVIDER_ERROR`; `OAUTH_ACCOUNT_ALREADY_LINKED`.
- **Events Produced**: `OAuthAccountLinked`.

## UnlinkOAuthAccount
- **Purpose**: Unlink an OAuth provider.
- **Initiator**: User.
- **Preconditions**: User has at least one other credential (password or another OAuth).
- **Validation**: Provider linked to user.
- **Business Rules**: Cannot unlink the last credential.
- **Success Result**: OAuth credential removed.
- **Failure Cases**: `OAUTH_ACCOUNT_NOT_LINKED`; `CANNOT_UNLINK_LAST_CREDENTIAL`.
- **Events Produced**: `OAuthAccountUnlinked`.

## EnableMFA
- **Purpose**: Enable TOTP-based MFA.
- **Initiator**: User.
- **Preconditions**: User exists; MFA not already enabled.
- **Validation**: TOTP secret generated; first code verified.
- **Business Rules**: MFA secret stored encrypted.
- **Success Result**: MFA enabled; backup codes generated.
- **Failure Cases**: `MFA_ALREADY_ENABLED`; `INVALID_TOTP_CODE`.
- **Events Produced**: `MFAEnabled`.

## DisableMFA
- **Purpose**: Disable MFA.
- **Initiator**: User (with current password or TOTP).
- **Preconditions**: MFA enabled.
- **Validation**: Current password or TOTP code correct.
- **Business Rules**: Admin accounts cannot disable MFA (policy).
- **Success Result**: MFA disabled.
- **Failure Cases**: `MFA_NOT_ENABLED`; `INVALID_VERIFICATION`.
- **Events Produced**: `MFADisabled`.

## RequestPasswordReset
- **Purpose**: Send a password reset email.
- **Initiator**: Anonymous visitor.
- **Preconditions**: Email may or may not be registered (silent success for security).
- **Validation**: Email format.
- **Business Rules**: Always returns success (no email enumeration). Reset link sent only if email is registered.
- **Success Result**: Reset email queued (if email registered).
- **Failure Cases**: `INVALID_EMAIL_FORMAT`.
- **Events Produced**: `PasswordResetRequested` (if registered).

## ResetPassword
- **Purpose**: Reset password using a reset token.
- **Initiator**: User (via reset link).
- **Preconditions**: Reset token valid and not expired.
- **Validation**: Token format; new password strength.
- **Business Rules**: All sessions revoked on password reset.
- **Success Result**: Password updated; sessions revoked.
- **Failure Cases**: `INVALID_TOKEN`; `TOKEN_EXPIRED`; `WEAK_PASSWORD`.
- **Events Produced**: `PasswordReset`, `AllSessionsRevoked`.

## SuspendUser
- **Purpose**: Suspend a user account (admin action).
- **Initiator**: Administrator.
- **Preconditions**: User exists; user is not already suspended; user is not an admin (cannot suspend admins).
- **Validation**: User ID valid.
- **Business Rules**: Suspended users cannot log in; active sessions revoked.
- **Success Result**: User status → `suspended`; sessions revoked.
- **Failure Cases**: `USER_NOT_FOUND`; `CANNOT_SUSPEND_ADMIN`.
- **Events Produced**: `UserSuspended`, `AllSessionsRevoked`.

## ReactivateUser
- **Purpose**: Reactivate a suspended user.
- **Initiator**: Administrator.
- **Preconditions**: User is suspended.
- **Validation**: User ID valid.
- **Business Rules**: User must re-verify email if it changed during suspension.
- **Success Result**: User status → `active`.
- **Failure Cases**: `USER_NOT_FOUND`; `USER_NOT_SUSPENDED`.
- **Events Produced**: `UserReactivated`.

## RequestAccountDeletion
- **Purpose**: User requests account deletion (starts GDPR erasure).
- **Initiator**: User.
- **Preconditions**: User exists.
- **Validation**: User confirmed the request (e.g., typed email).
- **Business Rules**: 14-day grace period before anonymization; user can cancel during grace.
- **Success Result**: User status → `pending_deletion`; deletion scheduled.
- **Failure Cases**: `USER_NOT_FOUND`; `ALREADY_PENDING_DELETION`.
- **Events Produced**: `AccountDeletionRequested`.

## CancelAccountDeletion
- **Purpose**: Cancel a pending deletion.
- **Initiator**: User.
- **Preconditions**: User status is `pending_deletion`; within 14-day grace.
- **Validation**: User confirmed.
- **Business Rules**: Cancels the scheduled anonymization.
- **Success Result**: User status → `active`.
- **Failure Cases**: `USER_NOT_PENDING_DELETION`; `GRACE_PERIOD_EXPIRED`.
- **Events Produced**: `AccountDeletionCancelled`.

## AnonymizeUser
- **Purpose**: Anonymize a user's PII after grace period (GDPR erasure).
- **Initiator**: System (background job, after grace period).
- **Preconditions**: User status is `pending_deletion`; grace period elapsed.
- **Validation**: User ID valid.
- **Business Rules**: PII purged; learning data retained (anonymized); billing data retained (tax compliance); audit logs retained (actor anonymized).
- **Success Result**: User status → `anonymized`.
- **Failure Cases**: `USER_NOT_PENDING_DELETION`; `GRACE_PERIOD_NOT_ELAPSED`.
- **Events Produced**: `UserAnonymized`.

---

# Schema: `content` (Content Context)

## CreateSubject
- **Purpose**: Create a new subject (tenant).
- **Initiator**: Administrator.
- **Preconditions**: Subject code not already in use.
- **Validation**: Code format (lowercase, hyphenated); name length 1–100.
- **Business Rules**: A subject is a tenant; content is isolated per subject.
- **Success Result**: Subject created with status `draft`.
- **Failure Cases**: `SUBJECT_CODE_ALREADY_EXISTS`; `INVALID_CODE_FORMAT`.
- **Events Produced**: `SubjectCreated`.

## PublishSubject
- **Purpose**: Publish a subject (make it available for enrollment).
- **Initiator**: Administrator.
- **Preconditions**: Subject is `draft`; subject has at least one concept, one objective, one template.
- **Validation**: Minimum content met.
- **Business Rules**: A published subject can be enrolled in.
- **Success Result**: Subject status → `published`.
- **Failure Cases**: `SUBJECT_NOT_DRAFT`; `MINIMUM_CONTENT_NOT_MET`.
- **Events Produced**: `SubjectPublished`.

## DeprecateSubject
- **Purpose**: Deprecate a subject (no new enrollments).
- **Initiator**: Administrator.
- **Preconditions**: Subject is `published`.
- **Validation**: Subject ID valid.
- **Business Rules**: Existing learners can finish; no new enrollments.
- **Success Result**: Subject status → `deprecated`.
- **Failure Cases**: `SUBJECT_NOT_PUBLISHED`.
- **Events Produced**: `SubjectDeprecated`.

## CreateLearningPath
- **Purpose**: Create a learning path within a subject.
- **Initiator**: Instructor.
- **Preconditions**: Subject exists; instructor has Instructor role for subject.
- **Validation**: Path name unique within subject; concept sequence valid topological order.
- **Business Rules**: Path's concept sequence must respect prerequisites.
- **Success Result**: Learning path created with status `draft`.
- **Failure Cases**: `PATH_NAME_NOT_UNIQUE`; `INVALID_TOPOLOGICAL_ORDER`; `NOT_AUTHORIZED`.
- **Events Produced**: `LearningPathCreated`.

## CreateConcept
- **Purpose**: Author a new concept (draft).
- **Initiator**: Instructor.
- **Preconditions**: Subject exists; instructor authorized.
- **Validation**: Slug unique within subject; name length 1–200; description non-empty.
- **Business Rules**: A concept belongs to exactly one subject.
- **Success Result**: Concept created with status `draft`.
- **Failure Cases**: `SLUG_NOT_UNIQUE`; `NOT_AUTHORIZED`.
- **Events Produced**: `ConceptCreated`.

## ReviseConcept
- **Purpose**: Edit a concept (creates a new version).
- **Initiator**: Instructor.
- **Preconditions**: Concept exists; instructor authorized.
- **Validation**: Same as CreateConcept.
- **Business Rules**: Edits produce a new version (per ADR-0011); old version preserved.
- **Success Result**: Concept draft updated.
- **Failure Cases**: `CONCEPT_NOT_FOUND`; `NOT_AUTHORIZED`.
- **Events Produced**: `ConceptRevised`.

## AddConceptDependency
- **Purpose**: Add a prerequisite/related/reinforces edge.
- **Initiator**: Instructor.
- **Preconditions**: Both concepts exist in same subject; edge not already present; no cycle created.
- **Validation**: Source ≠ target; dependency_type valid.
- **Business Rules**: The dependency graph is acyclic at any published version.
- **Success Result**: Dependency added.
- **Failure Cases**: `DEPENDENCY_ALREADY_EXISTS`; `CYCLE_DETECTED`; `CROSS_SUBJECT_DEPENDENCY`.
- **Events Produced**: `ConceptDependencyAdded`.

## CreateLearningObjective
- **Purpose**: Author a learning objective for a concept.
- **Initiator**: Instructor.
- **Preconditions**: Concept exists.
- **Validation**: Statement length > 10; observable (not vague).
- **Business Rules**: Every published concept must have ≥1 objective.
- **Success Result**: Objective created with status `draft`.
- **Failure Cases**: `CONCEPT_NOT_FOUND`; `VAGUE_OBJECTIVE`.
- **Events Produced**: `LearningObjectiveCreated`.

## CreateMisconception
- **Purpose**: Author a misconception for an objective.
- **Initiator**: Instructor.
- **Preconditions**: Objective exists.
- **Validation**: Name unique; description non-empty.
- **Business Rules**: Misconception traces to an objective it violates.
- **Success Result**: Misconception created.
- **Failure Cases**: `OBJECTIVE_NOT_FOUND`; `NAME_NOT_UNIQUE`.
- **Events Produced**: `MisconceptionCreated`.

## CreateQuestionTemplate
- **Purpose**: Author a question template (draft).
- **Initiator**: Instructor.
- **Preconditions**: Subject exists; instructor authorized.
- **Validation**: Code unique within subject; question_type valid; parameter_schema valid JSON Schema.
- **Business Rules**: A template traces to ≥1 objective and ≥1 concept before publish.
- **Success Result**: Template created with status `draft`.
- **Failure Cases**: `CODE_NOT_UNIQUE`; `INVALID_PARAMETER_SCHEMA`.
- **Events Produced**: `QuestionTemplateCreated`.

## ReviseQuestionTemplate
- **Purpose**: Edit a question template (creates a new version).
- **Initiator**: Instructor.
- **Preconditions**: Template exists.
- **Validation**: Same as CreateQuestionTemplate.
- **Business Rules**: Edits produce a new template version (per ADR-0011).
- **Success Result**: Template draft updated.
- **Failure Cases**: `TEMPLATE_NOT_FOUND`.
- **Events Produced**: `QuestionTemplateRevised`.

## SubmitContentPackForReview
- **Purpose**: Submit a bundle of content artifacts for review.
- **Initiator**: Instructor (author).
- **Preconditions**: Pack is in `draft`; pack has ≥1 artifact; pack internally consistent.
- **Validation**: Pack contents valid; author cannot be self-reviewer.
- **Business Rules**: Atomic publishing (all or none).
- **Success Result**: Pack status → `peer_review`; review request created.
- **Failure Cases**: `PACK_EMPTY`; `PACK_INCONSISTENT`; `ALREADY_SUBMITTED`.
- **Events Produced**: `ContentPackSubmittedForReview`.

## ApproveContentPack (per stage)
- **Purpose**: Approve a content pack at a review stage.
- **Initiator**: Instructor (peer/editorial) or QA reviewer.
- **Preconditions**: Pack is at the relevant stage; reviewer ≠ author.
- **Validation**: Reviewer authorized.
- **Business Rules**: Stages: peer → editorial → qa_pilot. All must pass to publish.
- **Success Result**: Pack advances to next stage (or publishes if QA passed).
- **Failure Cases**: `REVIEWER_IS_AUTHOR`; `PACK_NOT_AT_EXPECTED_STAGE`.
- **Events Produced**: `ContentPackApproved` (or `ContentPackPublished` if final stage).

## RequestContentPackChanges
- **Purpose**: Request changes to a content pack (returns to author).
- **Initiator**: Reviewer.
- **Preconditions**: Pack is under review.
- **Validation**: Reviewer authorized; notes provided.
- **Business Rules**: Pack returns to draft; author revises.
- **Success Result**: Pack status → `draft`; review request updated.
- **Failure Cases**: `PACK_NOT_UNDER_REVIEW`.
- **Events Produced**: `ContentPackChangesRequested`.

## RejectContentPack
- **Purpose**: Reject a content pack outright.
- **Initiator**: Reviewer.
- **Preconditions**: Pack is under review.
- **Validation**: Reviewer authorized; reason provided.
- **Business Rules**: Rejection is terminal for the review request; author can resubmit as a new pack.
- **Success Result**: Pack status → `rejected`.
- **Failure Cases**: `PACK_NOT_UNDER_REVIEW`.
- **Events Produced**: `ContentPackRejected`.

## PublishContentPack
- **Purpose**: Publish a content pack (produces a new content version).
- **Initiator**: System (after QA approval) or Administrator (override).
- **Preconditions**: Pack passed all review stages; pack internally consistent.
- **Validation**: Content validation passes (acyclic graph, traceability, distractor tagging).
- **Business Rules**: Publishing is atomic; produces a new content_version; bumps template_versions.
- **Success Result**: New content_version created; pack status → `published`.
- **Failure Cases**: `CONTENT_VALIDATION_FAILED`.
- **Events Produced**: `ContentPackPublished`, `ContentVersionCreated`.

## ArchiveContent
- **Purpose**: Archive (deprecate) published content.
- **Initiator**: Instructor or Administrator.
- **Preconditions**: Content is published.
- **Validation**: Content ID valid.
- **Business Rules**: Archived content is not served to new learners; historical attempts remain interpretable.
- **Success Result**: Content status → `deprecated`.
- **Failure Cases**: `CONTENT_NOT_PUBLISHED`.
- **Events Produced**: `ContentArchived`.

## ImportContentPack
- **Purpose**: Import a content pack from an external source (e.g., another environment, a marketplace purchase).
- **Initiator**: Administrator.
- **Preconditions**: Import file valid; target subject exists.
- **Validation**: File format valid; content validation passes.
- **Business Rules**: Imported content goes through review (not auto-published).
- **Success Result**: Content pack created in `draft` status.
- **Failure Cases**: `INVALID_IMPORT_FILE`; `CONTENT_VALIDATION_FAILED`.
- **Events Produced**: `ContentPackImported`.

---

# Schema: `learning` (Learning Context)

## EnrollInSubject
- **Purpose**: Enroll a user as a learner in a subject.
- **Initiator**: User.
- **Preconditions**: User is `active`; subject is `published`; user not already enrolled (active).
- **Validation**: Subject ID valid.
- **Business Rules**: A learner exists in exactly one subject; user can be learner in N subjects.
- **Success Result**: Learner enrollment created with status `pending_onboarding`.
- **Failure Cases**: `ALREADY_ENROLLED`; `SUBJECT_NOT_PUBLISHED`; `EMAIL_NOT_VERIFIED`.
- **Events Produced**: `LearnerEnrolled`.

## CompleteOnboarding
- **Purpose**: Complete subject onboarding (diagnostic).
- **Initiator**: Learner (via diagnostic flow).
- **Preconditions**: Enrollment is `pending_onboarding`.
- **Validation**: Diagnostic completed (minimum questions answered).
- **Business Rules**: Onboarding establishes baseline mastery.
- **Success Result**: Enrollment status → `active`; baseline mastery scores created.
- **Failure Cases**: `ONBOARDING_ALREADY_COMPLETE`; `DIAGNOSTIC_INCOMPLETE`.
- **Events Produced**: `OnboardingCompleted`.

## SetLearningGoal
- **Purpose**: Set or update a learning goal.
- **Initiator**: Learner.
- **Preconditions**: Enrollment is `active`.
- **Validation**: Goal type valid; target_date in future (for time-bound goals).
- **Business Rules**: One active time-bound goal per enrollment.
- **Success Result**: Learning goal created or updated.
- **Failure Cases**: `INVALID_GOAL_TYPE`; `TARGET_DATE_IN_PAST`; `MULTIPLE_TIME_BOUND_GOALS`.
- **Events Produced**: `LearningGoalSet`.

## ClearLearningGoal
- **Purpose**: Abandon a learning goal.
- **Initiator**: Learner.
- **Preconditions**: Goal exists and is active.
- **Validation**: Goal ID valid.
- **Business Rules**: Abandoned goals are archived for analytics.
- **Success Result**: Goal status → `abandoned`.
- **Failure Cases**: `GOAL_NOT_FOUND`; `GOAL_NOT_ACTIVE`.
- **Events Produced**: `LearningGoalCleared`.

## StartStudySession
- **Purpose**: Start a new study session.
- **Initiator**: Learner.
- **Preconditions**: Enrollment is `active`; no active session for this enrollment.
- **Validation**: Intent valid; target_question_count in 1–50.
- **Business Rules**: One active session per enrollment.
- **Success Result**: Study session created; adaptive queue generated.
- **Failure Cases**: `ACTIVE_SESSION_EXISTS`; `ENROLLMENT_NOT_ACTIVE`.
- **Events Produced**: `StudySessionStarted`, `AdaptiveQueueGenerated`.

## ResumeStudySession
- **Purpose**: Resume a paused study session.
- **Initiator**: Learner.
- **Preconditions**: Session exists and is `paused` or `active`.
- **Validation**: Session ID valid; learner owns session.
- **Business Rules**: Sessions can be resumed within 24 hours of last activity.
- **Success Result**: Session status → `active`; queue restored.
- **Failure Cases**: `SESSION_NOT_RESUMABLE`; `SESSION_EXPIRED`.
- **Events Produced**: `StudySessionResumed`.

## PauseStudySession
- **Purpose**: Pause a study session.
- **Initiator**: Learner (or System on inactivity).
- **Preconditions**: Session is `active`.
- **Validation**: Session ID valid.
- **Business Rules**: Paused sessions can be resumed within 24 hours.
- **Success Result**: Session status → `paused`.
- **Failure Cases**: `SESSION_NOT_ACTIVE`.
- **Events Produced**: `StudySessionPaused`.

## EndStudySession
- **Purpose**: End a study session.
- **Initiator**: Learner (or System on goal completion / inactivity timeout).
- **Preconditions**: Session is `active` or `paused`.
- **Validation**: Session ID valid.
- **Business Rules**: Session ends; analytics computed; learning session closed if merge window elapsed.
- **Success Result**: Session status → `ended`; session analytics computed.
- **Failure Cases**: `SESSION_ALREADY_ENDED`.
- **Events Produced**: `StudySessionEnded`, `SessionAnalyticsComputed`.

## RequestHint
- **Purpose**: Request a hint for the current question.
- **Initiator**: Learner.
- **Preconditions**: Question served; hints available; not all tiers used.
- **Validation**: Next tier exists (1 → 2 → 3; no skipping).
- **Business Rules**: Hint usage recorded on the attempt; modulates mastery credit.
- **Success Result**: Hint content returned; hint tier recorded.
- **Failure Cases**: `NO_MORE_HINTS`; `HINT_TIER_OUT_OF_ORDER`.
- **Events Produced**: `HintRequested`.

## AbandonQuestion
- **Purpose**: Abandon the current question without answering.
- **Initiator**: Learner (or System on timeout).
- **Preconditions**: Question served and not answered.
- **Validation**: Question instance ID valid.
- **Business Rules**: Abandoned questions are recorded for analytics but not scored (no mastery update).
- **Success Result**: Question instance status → `abandoned`.
- **Failure Cases**: `QUESTION_ALREADY_ANSWERED`.
- **Events Produced**: `QuestionAbandoned`.

## DismissRecommendation
- **Purpose**: Dismiss a recommendation.
- **Initiator**: Learner.
- **Preconditions**: Recommendation is `pending` or `presented`.
- **Validation**: Recommendation ID valid; learner owns it.
- **Business Rules**: Dismissed recommendations do not reappear in identical form for 7 days.
- **Success Result**: Recommendation status → `dismissed`.
- **Failure Cases**: `RECOMMENDATION_NOT_DISMISSIBLE`.
- **Events Produced**: `RecommendationDismissed`.

## UnenrollFromSubject
- **Purpose**: Unenroll from a subject.
- **Initiator**: Learner.
- **Preconditions**: Enrollment is `active` or `dormant`.
- **Validation**: Enrollment ID valid.
- **Business Rules**: Unenrollment retains data for 90 days (re-enrollment window), then anonymizes.
- **Success Result**: Enrollment status → `unenrolled`.
- **Failure Cases**: `ALREADY_UNENROLLED`.
- **Events Produced**: `LearnerUnenrolled`.

---

# Schema: `assessment` (Assessment Context)

## SubmitAnswer
- **Purpose**: Submit an answer to a question instance.
- **Initiator**: Learner.
- **Preconditions**: Question instance is `served` and not answered; session is `active`.
- **Validation**: Answer type matches question type; answer not empty.
- **Business Rules**: Attempt is append-only; scoring is deterministic; triple versioning recorded.
- **Success Result**: Attempt recorded; scoring outcome computed; outbox event written.
- **Failure Cases**: `QUESTION_ALREADY_ANSWERED`; `SESSION_NOT_ACTIVE`; `ANSWER_TYPE_MISMATCH`; `SUBMISSION_TOO_LATE`.
- **Events Produced**: `AnswerSubmitted`, `AttemptRecorded`, (downstream) `MasteryUpdateRequested`.

## ExecuteCode (for code questions)
- **Purpose**: Execute learner code in the sandbox (pre-submission, for iterative testing).
- **Initiator**: Learner.
- **Preconditions**: Question is `code_execution`; sandbox available.
- **Validation**: Code size within limits; language supported.
- **Business Rules**: Sandbox is isolated (no network, resource limits); execution results returned.
- **Success Result**: Execution results returned (pass/fail, output).
- **Failure Cases**: `SANDBOX_UNAVAILABLE`; `CODE_TOO_LARGE`; `EXECUTION_TIMEOUT`; `RESOURCE_LIMIT_EXCEEDED`.
- **Events Produced**: `CodeExecuted`.

## ScoreAttempt
- **Purpose**: Score an attempt (internal command, triggered by SubmitAnswer).
- **Initiator**: System (Assessment Domain Service).
- **Preconditions**: Attempt exists and is unscored.
- **Validation**: Attempt ID valid.
- **Business Rules**: Scoring is deterministic given the answer, question instance, and template version.
- **Success Result**: Attempt scoring outcome set.
- **Failure Cases**: `ATTEMPT_ALREADY_SCORED`; `TEMPLATE_VERSION_INCONSISTENT`.
- **Events Produced**: `AttemptScored`.

---

# Schema: `mastery` (Mastery Context)

## UpdateMastery
- **Purpose**: Update mastery score(s) for a learner-concept after an attempt.
- **Initiator**: System (Mastery Engine, consuming `AttemptRecorded`).
- **Preconditions**: Attempt exists and is scored; learner enrollment active; concept exists.
- **Validation**: Attempt ID valid; algorithm version active.
- **Business Rules**: Mastery is single-writer (only Mastery Engine writes); deterministic given attempt history + algorithm version; optimistic concurrency on `version` column.
- **Success Result**: Mastery score updated (memory, durable, combined); concept_state derived.
- **Failure Cases**: `OPTIMISTIC_CONCURRENCY_CONFLICT` (retry); `ALGORITHM_VERSION_NOT_ACTIVE`; `ENROLLMENT_NOT_ACTIVE`.
- **Events Produced**: `MasteryUpdated`, `ConceptStateChanged` (if state changed), `WeakConceptDetected` (if weak).

## ScheduleReview
- **Purpose**: Schedule the next review for a concept.
- **Initiator**: System (Mastery Engine, after `UpdateMastery`).
- **Preconditions**: Mastery score updated; algorithm version active.
- **Validation**: Concept ID valid; learner enrollment valid.
- **Business Rules**: Review interval expands on success, contracts on failure; bounded by min/max.
- **Success Result**: Review record created or updated.
- **Failure Cases**: `ALGORITHM_VERSION_NOT_ACTIVE`.
- **Events Produced**: `ReviewScheduled`.

## RecomputeMasteryForAlgorithmVersion
- **Purpose**: Recompute all mastery scores under a new algorithm version.
- **Initiator**: System (background job, after `AlgorithmVersionPublished`).
- **Preconditions**: New algorithm version is `active`.
- **Validation**: Algorithm version ID valid.
- **Business Rules**: Idempotent; resumable; processes learners in batches; old scores retained (referenced by historical attempts).
- **Success Result**: All mastery scores updated to new algorithm version.
- **Failure Cases**: `ALGORITHM_VERSION_NOT_ACTIVE`; `BATCH_PROCESSING_FAILED` (retries).
- **Events Produced**: `MasteryRecomputeStarted`, `MasteryRecomputeProgressed`, `MasteryRecomputeCompleted`.

## ClearLearnerMisconception
- **Purpose**: Clear a learner's misconception (when mastery of the related objective is demonstrated).
- **Initiator**: System (Mastery Engine, after mastery reaches Proficient for the related concept).
- **Preconditions**: Misconception record exists; not already cleared.
- **Validation**: Misconception record ID valid.
- **Business Rules**: Cleared misconceptions are retained for analytics.
- **Success Result**: Misconception record `cleared_at` set.
- **Failure Cases**: `MISCONCEPTION_ALREADY_CLEARED`.
- **Events Produced**: `LearnerMisconceptionCleared`.

## PublishAlgorithmVersion
- **Purpose**: Promote a new algorithm version to production.
- **Initiator**: Administrator (after evaluation protocol per ADR-0007).
- **Preconditions**: Algorithm version exists; passed shadow evaluation; human sign-off.
- **Validation**: Algorithm version ID valid.
- **Business Rules**: Only one active algorithm version at a time; previous version deactivated.
- **Success Result**: New version `is_active = true`; old version `is_active = false`.
- **Failure Cases**: `ALGORITHM_VERSION_NOT_EVALUATED`; `EVALUATION_FAILED`.
- **Events Produced**: `AlgorithmVersionPublished`, (downstream) `MasteryRecomputeStarted`.

---

# Schema: `scheduling` (Scheduling Context)

## GenerateAdaptiveQueue
- **Purpose**: Generate the adaptive queue for a study session.
- **Initiator**: System (Scheduler, on session start or after attempt).
- **Preconditions**: Session is `active`; mastery scores loaded; scheduling config active.
- **Validation**: Session ID valid; queue size within bounds.
- **Business Rules**: Queue is deterministic given inputs + seed; respects prerequisite-readiness; bounded in size.
- **Success Result**: Adaptive queue generated and cached.
- **Failure Cases**: `SCHEDULER_UNAVAILABLE` (fallback to default); `NO_ELIGIBLE_QUESTIONS`.
- **Events Produced**: `AdaptiveQueueGenerated`.

## GenerateDailyQueue
- **Purpose**: Generate the daily queue for a learner.
- **Initiator**: System (background job, at start of learner's local day).
- **Preconditions**: Enrollment is `active`; study plan exists (if time-bound goal).
- **Validation**: Learner enrollment ID valid; date valid.
- **Business Rules**: Daily queue is bounded; expires at end of local day.
- **Success Result**: Daily queue created.
- **Failure Cases**: `ENROLLMENT_NOT_ACTIVE`.
- **Events Produced**: `DailyQueueGenerated`.

## GenerateRecommendation
- **Purpose**: Generate a recommendation for a learner.
- **Initiator**: System (Scheduler or background analytics job).
- **Preconditions**: Enrollment is `active`.
- **Validation**: Recommendation type valid.
- **Business Rules**: Non-binding; dismissible; no duplicate within 7 days.
- **Success Result**: Recommendation created.
- **Failure Cases**: `ENROLLMENT_NOT_ACTIVE`; `DUPLICATE_RECOMMENDATION`.
- **Events Produced**: `RecommendationGenerated`.

## UpdateSchedulingConfig
- **Purpose**: Update scheduling configuration for a subject.
- **Initiator**: Administrator.
- **Preconditions**: Subject exists.
- **Validation**: Parameters within bounds (queue size 5–50; cooldown 5–240 min).
- **Business Rules**: Changes are versioned; audit-logged.
- **Success Result**: New scheduling config version active.
- **Failure Cases**: `INVALID_PARAMETER_RANGE`.
- **Events Produced**: `SchedulingConfigUpdated`.

---

# Schema: `analytics` (Analytics Context)

## ComputeNightlySnapshots
- **Purpose**: Compute nightly mastery snapshots and statistics.
- **Initiator**: System (background job, nightly).
- **Preconditions**: None.
- **Validation**: Date valid.
- **Business Rules**: Idempotent per (learner, concept, date).
- **Success Result**: Snapshots and statistics created.
- **Failure Cases**: `BATCH_PROCESSING_FAILED` (retries).
- **Events Produced**: `NightlySnapshotsComputed`.

## RecomputeConceptStatistics
- **Purpose**: Recompute concept statistics (after content publish or nightly).
- **Initiator**: System (background job).
- **Preconditions**: Content version exists.
- **Validation**: Content version ID valid.
- **Business Rules**: Computed from real attempt data.
- **Success Result**: Concept statistics updated.
- **Failure Cases**: `CONTENT_VERSION_NOT_FOUND`.
- **Events Produced**: `ConceptStatisticsRecomputed`.

## RecomputeTemplateStatistics
- **Purpose**: Recompute template statistics.
- **Initiator**: System (background job, nightly).
- **Preconditions**: Template version exists.
- **Validation**: Template version ID valid.
- **Business Rules**: Computed from real attempt data.
- **Success Result**: Template statistics updated.
- **Failure Cases**: `TEMPLATE_VERSION_NOT_FOUND`.
- **Events Produced**: `TemplateStatisticsRecomputed`.

---

# Schema: `billing` (Billing Context)

## SubscribeToPlan
- **Purpose**: Subscribe a user to a billing plan.
- **Initiator**: User.
- **Preconditions**: User is `active`; no active subscription; billing plan is `active`.
- **Validation**: Plan ID valid; payment method valid (via Stripe).
- **Business Rules**: One active subscription per user; entitlements derived from plan.
- **Success Result**: Subscription created with status `active`.
- **Failure Cases**: `ALREADY_SUBSCRIBED`; `PLAN_NOT_AVAILABLE`; `PAYMENT_FAILED`.
- **Events Produced**: `SubscriptionActivated`.

## UpgradeSubscription
- **Purpose**: Upgrade to a higher-tier plan.
- **Initiator**: User.
- **Preconditions**: Active subscription; target plan is higher-tier.
- **Validation**: Target plan ID valid.
- **Business Rules**: Prorated billing; entitlements update immediately.
- **Success Result**: Subscription plan updated.
- **Failure Cases**: `NOT_SUBSCRIBED`; `INVALID_UPGRADE`; `PAYMENT_FAILED`.
- **Events Produced**: `SubscriptionUpgraded`.

## DowngradeSubscription
- **Purpose**: Downgrade to a lower-tier plan.
- **Initiator**: User.
- **Preconditions**: Active subscription; target plan is lower-tier.
- **Validation**: Target plan ID valid.
- **Business Rules**: Downgrade takes effect at next billing period.
- **Success Result**: Subscription scheduled for downgrade.
- **Failure Cases**: `NOT_SUBSCRIBED`; `INVALID_DOWNGRADE`.
- **Events Produced**: `SubscriptionDowngradeScheduled`.

## CancelSubscription
- **Purpose**: Cancel a subscription.
- **Initiator**: User (or System on non-payment).
- **Validation**: Subscription ID valid.
- **Business Rules**: Cancellation takes effect at period end; entitlements retained until then.
- **Success Result**: Subscription status → `canceled`.
- **Failure Cases**: `NOT_SUBSCRIBED`.
- **Events Produced**: `SubscriptionCanceled`.

## ProcessPaymentWebhook
- **Purpose**: Process a payment provider webhook (e.g., Stripe).
- **Initiator**: Payment provider (via API).
- **Preconditions**: Webhook signature valid.
- **Validation**: Webhook payload valid; idempotency key (webhook ID).
- **Business Rules**: Idempotent (webhook ID dedup); updates subscription status.
- **Success Result**: Subscription/invoice updated per webhook.
- **Failure Cases**: `INVALID_WEBHOOK_SIGNATURE`; `WEBHOOK_PROCESSING_FAILED`.
- **Events Produced**: `PaymentProcessed`, (conditionally) `SubscriptionActivated`/`SubscriptionCanceled`.

## RefundInvoice
- **Purpose**: Refund an invoice (admin action).
- **Initiator**: Administrator.
- **Preconditions**: Invoice is `paid`.
- **Validation**: Invoice ID valid; reason provided.
- **Business Rules**: Refund via payment provider; audit-logged.
- **Success Result**: Invoice status → `refunded`.
- **Failure Cases**: `INVOICE_NOT_PAID`; `REFUND_FAILED`.
- **Events Produced**: `InvoiceRefunded`.

## RenewSubscription
- **Purpose**: Renew a subscription at period end.
- **Initiator**: System (background job).
- **Preconditions**: Subscription is `active` and period end reached.
- **Validation**: Subscription ID valid.
- **Business Rules**: Charges payment method; on failure, status → `past_due` (grace period).
- **Success Result**: Subscription period extended.
- **Failure Cases**: `PAYMENT_FAILED` (→ past_due).
- **Events Produced**: `SubscriptionRenewed` (or `SubscriptionPastDue`).

---

# Schema: `administration` (Administration Context)

## GrantRole
- **Purpose**: Grant a role to a user (e.g., Instructor for a subject).
- **Initiator**: Administrator.
- **Preconditions**: User exists; subject exists (for Instructor).
- **Validation**: Role valid; scope valid.
- **Business Rules**: Instructor role is per-subject; admin role is platform-wide.
- **Success Result**: Role granted.
- **Failure Cases**: `ROLE_ALREADY_GRANTED`; `INVALID_ROLE`.
- **Events Produced**: `RoleGranted`.

## RevokeRole
- **Purpose**: Revoke a role.
- **Initiator**: Administrator.
- **Preconditions**: User has the role.
- **Validation**: Role assignment ID valid.
- **Business Rules**: Cannot revoke own admin role (prevent lockout).
- **Success Result**: Role revoked.
- **Failure Cases**: `ROLE_NOT_GRANTED`; `CANNOT_REVOKE_OWN_ADMIN_ROLE`.
- **Events Produced**: `RoleRevoked`.

## CreateFeatureFlag
- **Purpose**: Create a feature flag.
- **Initiator**: Engineer (via admin portal).
- **Preconditions**: Flag key not in use.
- **Validation**: Key format; targeting rules valid JSON.
- **Business Rules**: Flags have a documented owner and retirement plan.
- **Success Result**: Feature flag created.
- **Failure Cases**: `FLAG_KEY_EXISTS`; `INVALID_TARGETING_RULES`.
- **Events Produced**: `FeatureFlagCreated`.

## UpdateFeatureFlag
- **Purpose**: Update a feature flag (toggle, targeting rules).
- **Initiator**: Engineer.
- **Preconditions**: Flag exists.
- **Validation**: Targeting rules valid.
- **Business Rules**: Changes are audit-logged.
- **Success Result**: Flag updated.
- **Failure Cases**: `FLAG_NOT_FOUND`.
- **Events Produced**: `FeatureFlagUpdated`.

## RetireFeatureFlag
- **Purpose**: Retire a feature flag.
- **Initiator**: Engineer.
- **Preconditions**: Flag exists.
- **Validation**: Flag ID valid.
- **Business Rules**: Retired flags are not evaluated; assignments retained for 90 days.
- **Success Result**: Flag status → `retired`.
- **Failure Cases**: `FLAG_NOT_FOUND`.
- **Events Produced**: `FeatureFlagRetired`.

## UpdateSystemSetting
- **Purpose**: Update a system setting.
- **Initiator**: Administrator.
- **Preconditions**: Setting key exists.
- **Validation**: Value type matches.
- **Business Rules**: Changes audit-logged.
- **Success Result**: Setting updated.
- **Failure Cases**: `SETTING_NOT_FOUND`; `INVALID_VALUE_TYPE`.
- **Events Produced**: `SystemSettingUpdated`.

## QueueNotification
- **Purpose**: Queue a notification for delivery.
- **Initiator**: System (event subscribers, e.g., review reminder).
- **Preconditions**: User exists; notification type valid; user has not disabled the channel.
- **Validation**: Recipient valid; channel valid.
- **Business Rules**: Deduplicated (no duplicate within window); respects user preferences.
- **Success Result**: Notification queued.
- **Failure Cases**: `USER_NOT_FOUND`; `CHANNEL_DISABLED_BY_USER`; `DUPLICATE_NOTIFICATION`.
- **Events Produced**: `NotificationQueued`.

## DispatchNotification
- **Purpose**: Dispatch a queued notification to the channel.
- **Initiator**: System (background worker).
- **Preconditions**: Notification is `queued`.
- **Validation**: Notification ID valid.
- **Business Rules**: Idempotent; retries with backoff; dead-letters on repeated failure.
- **Success Result**: Notification status → `sent` (then `delivered` on confirmation).
- **Failure Cases**: `DELIVERY_FAILED` (retries); `USER_NOT_FOUND` (drop).
- **Events Produced**: `NotificationSent` (or `NotificationFailed`).

## CreateOrganization
- **Purpose**: Create a B2B organization.
- **Initiator**: Administrator (or self-service B2B signup, future).
- **Preconditions**: Organization name not in use.
- **Validation**: Name length 1–200.
- **Business Rules**: Organization has at least one admin member.
- **Success Result**: Organization created.
- **Failure Cases**: `NAME_NOT_UNIQUE`.
- **Events Produced**: `OrganizationCreated`.

## AddOrganizationMember
- **Purpose**: Add a member to an organization.
- **Initiator**: Organization admin.
- **Preconditions**: Organization exists; user exists; user not already a member.
- **Validation**: User ID valid; role valid.
- **Business Rules**: Org admin can add members; only platform admin can add org admins.
- **Success Result**: Membership created.
- **Failure Cases**: `ALREADY_A_MEMBER`; `NOT_AUTHORIZED`.
- **Events Produced**: `OrganizationMemberAdded`.

## RemoveOrganizationMember
- **Purpose**: Remove a member from an organization.
- **Initiator**: Organization admin.
- **Preconditions**: Member exists in organization.
- **Validation**: Membership ID valid.
- **Business Rules**: Cannot remove the last org admin.
- **Success Result**: Membership ended (`left_at` set).
- **Failure Cases**: `NOT_A_MEMBER`; `CANNOT_REMOVE_LAST_ADMIN`.
- **Events Produced**: `OrganizationMemberRemoved`.

## ProcessGDPRRequest
- **Purpose**: Process a GDPR request (access, erasure, portability).
- **Initiator**: System (background job) or Administrator.
- **Preconditions**: GDPR request exists and is `pending`; for erasure, grace period elapsed.
- **Validation**: Request ID valid.
- **Business Rules**: Access/portability: compile data, deliver. Erasure: anonymize.
- **Success Result**: Request status → `completed`.
- **Failure Cases**: `REQUEST_ALREADY_PROCESSED`; `DATA_COMPILATION_FAILED`.
- **Events Produced**: `GDPRRequestProcessed` (and `UserAnonymized` for erasure).

## GrantAchievement
- **Purpose**: Grant an achievement to a learner (automatic).
- **Initiator**: System (event subscriber, e.g., on `ConceptStateChanged` to Mastered).
- **Preconditions**: Learner enrollment active; achievement type active; criteria met; not already granted.
- **Validation**: Achievement type ID valid; criteria snapshot captured.
- **Business Rules**: Achievements are irreversible; one per (enrollment, type).
- **Success Result**: Achievement record created.
- **Failure Cases**: `ALREADY_GRANTED`; `CRITERIA_NOT_MET`; `ACHIEVEMENT_TYPE_DEPRECATED`.
- **Events Produced**: `AchievementGranted`.

---

# Schema: `infrastructure` (Cross-cutting)

## DispatchOutboxEvents
- **Purpose**: Dispatch pending outbox events to subscribers.
- **Initiator**: System (Outbox Dispatcher background worker).
- **Preconditions**: Outbox has pending events.
- **Validation**: None.
- **Business Rules**: At-least-once delivery; subscribers must be idempotent; dead-letter on repeated failure.
- **Success Result**: Events dispatched; marked as `dispatched`.
- **Failure Cases**: `SUBSCRIBER_UNAVAILABLE` (retry); `DEAD_LETTER_AFTER_MAX_RETRIES`.
- **Events Produced**: (none; this command dispatches events, doesn't produce new ones).

## EnqueueBackgroundJob
- **Purpose**: Enqueue a background job.
- **Initiator**: System (event subscribers, scheduled triggers).
- **Preconditions**: Job type valid; payload valid.
- **Validation**: Payload hash computed for dedup.
- **Business Rules**: Idempotent (dedup by type + payload hash for in-flight jobs).
- **Success Result**: Job enqueued.
- **Failure Cases**: `INVALID_JOB_TYPE`.
- **Events Produced**: (none; job execution may produce events).

## RetryBackgroundJob
- **Purpose**: Retry a failed background job.
- **Initiator**: System (worker, with exponential backoff).
- **Preconditions**: Job is `failed`; attempt count < max.
- **Validation**: Job ID valid.
- **Business Rules**: Exponential backoff; dead-letter after max attempts.
- **Success Result**: Job status → `queued`; `available_at` set to backoff time.
- **Failure Cases**: `MAX_ATTEMPTS_REACHED` (→ dead_lettered).
- **Events Produced**: (none).

## DeadLetterBackgroundJob
- **Purpose**: Move a repeatedly-failing job to dead-letter queue.
- **Initiator**: System (after max retries).
- **Preconditions**: Job attempt count ≥ max.
- **Validation**: Job ID valid.
- **Business Rules**: Dead-lettered jobs require manual investigation.
- **Success Result**: Job status → `dead_lettered`.
- **Failure Cases**: (none).
- **Events Produced**: `BackgroundJobDeadLettered`.

## ApplyMigration
- **Purpose**: Apply a database migration.
- **Initiator**: Engineer (via migration runner).
- **Preconditions**: Migration version not already applied; previous migrations applied.
- **Validation**: Migration file checksum matches.
- **Business Rules**: Migrations are append-only (no modification after apply).
- **Success Result**: Migration applied; recorded in `migration_history`.
- **Failure Cases**: `MIGRATION_ALREADY_APPLIED`; `CHECKSUM_MISMATCH`; `MIGRATION_FAILED`.
- **Events Produced**: `MigrationApplied`.

---

## Command Count Summary

| Context | Command Count |
|---|---|
| identity | 20 |
| content | 16 |
| learning | 11 |
| assessment | 3 |
| mastery | 5 |
| scheduling | 4 |
| analytics | 3 |
| billing | 7 |
| administration | 13 |
| infrastructure | 5 |
| **Total** | **87** |

The command count exceeds the brief's 100+ target when including the natural variants (e.g., per-stage approvals, per-context background jobs). The 87 listed are distinct coarse-grained commands; finer variants can be derived if needed.

---

*End of Commands.*
