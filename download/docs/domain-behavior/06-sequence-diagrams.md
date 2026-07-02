# 06 — Sequence Diagrams

> 30+ Mermaid sequence diagrams for critical flows.

---

## 1. User Registration

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant DB as Database
    participant E as Email Service
    participant O as Outbox

    U->>F: Enter email + password
    F->>B: POST /api/v1/auth/register
    B->>DB: INSERT user (pending_verification)
    B->>DB: INSERT user_credential (password)
    B->>O: WRITE UserRegistered + VerificationEmailQueued
    B-->>F: 201 Created
    F-->>U: "Check your email"
    O-->>E: VerificationEmailQueued (async)
    E-->>U: Verification email
```

---

## 2. Email Verification

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant DB as Database
    participant O as Outbox

    U->>F: Click verification link
    F->>B: POST /api/v1/auth/verify-email {token}
    B->>DB: SELECT user by token
    B->>DB: UPDATE user SET status='active', email_verified_at=now()
    B->>O: WRITE EmailVerified
    B-->>F: 200 OK
    F-->>U: "Email verified! You can enroll."
```

---

## 3. Login (Password)

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant DB as Database
    participant R as Redis
    participant O as Outbox

    U->>F: Enter email + password
    F->>B: POST /api/v1/auth/login
    B->>DB: SELECT user by email
    B->>DB: SELECT user_credential (password)
    B->>B: Verify argon2id hash
    B->>DB: INSERT session (refresh_token_hash)
    B->>O: WRITE UserLoggedIn
    B->>R: Cache user profile (5min)
    B-->>F: 200 {access_token, refresh_token (cookie)}
    F->>F: Store access_token in JS memory
    F-->>U: Redirect to /dashboard
```

---

## 4. Token Refresh

```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant DB as Database

    F->>B: API call (expired access_token)
    B-->>F: 401 Unauthorized
    F->>B: POST /api/v1/auth/refresh (cookie: refresh_token)
    B->>DB: SELECT session by refresh_token_hash
    alt Session valid
        B->>DB: UPDATE session (rotate refresh_token, last_seen_at)
        B-->>F: 200 {new access_token, new refresh_token (cookie)}
        F->>B: Retry original API call
        B-->>F: 200 OK
    else Rotation anomaly detected
        B->>DB: UPDATE sessions SET revoked_at=now() WHERE token_family_id=$1
        B-->>F: 401 (force re-login)
    end
```

---

## 5. Enroll in Subject

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant DB as Database
    participant O as Outbox

    U->>F: Click "Enroll in Python"
    F->>B: POST /api/v1/enrollments {subject_id}
    B->>DB: Check: user active, subject published, not already enrolled
    B->>DB: INSERT learner_enrollment (pending_onboarding)
    B->>O: WRITE LearnerEnrolled
    B-->>F: 201 Created
    F-->>U: Redirect to onboarding/diagnostic
```

---

## 6. Daily Learning Loop (full)

```mermaid
sequenceDiagram
    participant U as Learner
    participant F as Frontend
    participant B as Backend
    participant S as Scheduler
    participant QF as QuestionFactory
    participant A as Assessment
    participant M as Mastery
    participant DB as Database
    participant O as Outbox

    U->>F: Click "Start session"
    F->>B: POST /api/v1/sessions {intent: drill}
    B->>DB: INSERT study_session (active)
    B->>O: WRITE StudySessionStarted
    B->>S: GenerateAdaptiveQueue
    S->>DB: Load mastery_scores, reviews, weak_concepts
    S->>QF: Instantiate N questions (seeded)
    QF-->>S: Question instances
    S->>DB: INSERT practice_queue
    B->>O: WRITE AdaptiveQueueGenerated
    B-->>F: 200 {session_id, first_question}

    loop Answer loop
        U->>F: Submit answer
        F->>B: POST /api/v1/attempts {question_instance_id, answer}
        B->>A: ScoreAnswer (deterministic)
        A-->>B: scoring_outcome
        B->>DB: INSERT question_instance (answered) + attempt (append-only)
        B->>O: WRITE AnswerSubmitted + AttemptRecorded
        B-->>F: 200 {outcome, explanation}

        O-->>M: AttemptRecorded (async)
        M->>DB: Load attempt history for concept
        M->>M: Compute new mastery (deterministic)
        M->>DB: UPDATE mastery_score (optimistic concurrency)
        M->>O: WRITE MasteryUpdated + (maybe) ConceptStateChanged + (maybe) WeakConceptDetected
        M->>M: ScheduleReview
        M->>O: WRITE ReviewScheduled

        O-->>S: MasteryUpdated (async)
        S->>DB: Load updated mastery
        S->>QF: Instantiate next question
        S->>DB: UPDATE practice_queue

        B-->>F: (Next question via WebSocket or poll)
        F-->>U: Show next question
    end

    U->>F: Click "End session"
    F->>B: POST /api/v1/sessions/{id}/end
    B->>DB: UPDATE study_session (ended)
    B->>O: WRITE StudySessionEnded + SessionAnalyticsComputed
    B-->>F: 200 {session_summary}
    F-->>U: Show session results
```

---

## 7. Adaptive Queue Generation (detail)

```mermaid
sequenceDiagram
    participant B as Backend
    participant S as Scheduler
    participant DB as Database
    participant QF as QuestionFactory
    participant R as Redis

    B->>S: GenerateAdaptiveQueue(session_id)
    S->>R: Check cache (session-scoped)
    alt Cache hit
        R-->>S: Cached queue
    else Cache miss
        S->>DB: Load mastery_scores (all concepts for learner)
        S->>DB: Load due reviews (partial index)
        S->>DB: Load weak concepts (partial index)
        S->>DB: Load learning goal + scheduling config
        S->>S: Compute priority per candidate concept
        S->>S: Filter by cooldown, prerequisite-readiness
        S->>S: Select top N concepts
        loop Per concept
            S->>DB: Select template (by difficulty, misconception targeting)
            S->>QF: Instantiate(template_version, seed)
            QF-->>S: Question instance
        end
        S->>DB: INSERT practice_queue
        S->>R: Cache queue (session-scoped, 60s TTL)
    end
    S-->>B: Queue
```

---

## 8. Mastery Update (detail)

```mermaid
sequenceDiagram
    participant O as Outbox
    participant M as MasteryEngine
    participant DB as Database
    participant O2 as Outbox

    O-->>M: AttemptRecorded event
    M->>DB: Load attempt history (learner + concept)
    M->>DB: Load algorithm_version (active)
    M->>M: Compute memory_score, durable_mastery_score (pure function)
    M->>DB: SELECT mastery_score (with version for optimistic concurrency)
    alt Version matches
        M->>DB: UPDATE mastery_score (version+1)
        M->>DB: Derive concept_state, weakness_severity
        M->>O2: WRITE MasteryUpdated
        alt State changed
            M->>O2: WRITE ConceptStateChanged
        end
        alt Weak detected
            M->>O2: WRITE WeakConceptDetected
        end
        M->>M: ScheduleReview
        M->>O2: WRITE ReviewScheduled
    else Version mismatch (concurrent update)
        M->>M: Retry (re-read, recompute, re-write)
    end
```

---

## 9. Review Scheduling (detail)

```mermaid
sequenceDiagram
    participant M as MasteryEngine
    participant DB as Database
    participant O as Outbox

    M->>M: Compute new interval (expand on success, contract on failure)
    M->>DB: UPSERT review (learner_enrollment_id, concept_id)
    M->>O: WRITE ReviewScheduled
```

---

## 10. Content Publishing (full pipeline)

```mermaid
sequenceDiagram
    participant I as Instructor
    participant F as Admin Portal
    participant B as Backend
    participant DB as Database
    participant O as Outbox
    participant R as Reviewer
    participant Q as QA Pilot Cohort

    I->>F: Author content pack (concepts, templates)
    F->>B: SubmitContentPackForReview
    B->>DB: INSERT content_pack, content_review_request (peer_review)
    B->>O: WRITE ContentPackSubmittedForReview
    B-->>R: Notify (peer reviewer assigned)
    R->>F: Review; approve
    F->>B: ApproveContentPack (stage=peer)
    B->>DB: UPDATE review_request (editorial_review)
    B->>O: WRITE ContentPackApproved

    R->>F: Editorial review; approve
    F->>B: ApproveContentPack (stage=editorial)
    B->>DB: UPDATE review_request (qa_pilot)
    B->>O: WRITE ContentPackApproved

    B-->>Q: Serve sample questions to pilot cohort
    Q-->>B: Discrimination data
    R->>F: QA review; approve
    F->>B: ApproveContentPack (stage=qa)
    B->>B: PublishContentPack
    B->>DB: Content validation (acyclic, traceable, tagged)
    B->>DB: INSERT content_version (new)
    B->>DB: INSERT template_versions (new)
    B->>DB: UPDATE concepts.current_version_id
    B->>O: WRITE ContentPackPublished + ContentVersionCreated
    B-->>F: "Published!"
```

---

## 11. Authentication Flow (OAuth)

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant GP as Google OAuth
    participant DB as Database

    U->>F: Click "Login with Google"
    F->>GP: Redirect to Google consent
    GP-->>U: Consent screen
    U->>GP: Approve
    GP->>F: Redirect with code
    F->>B: POST /api/v1/auth/oauth/callback {code}
    B->>GP: Exchange code for tokens + user info
    GP-->>B: {access_token, user_info}
    B->>DB: SELECT user_credential by (provider=google, provider_user_id)
    alt Existing user
        B->>DB: INSERT session
        B-->>F: 200 {access_token, refresh_token}
    else New user
        B->>DB: INSERT user (active, email_verified)
        B->>DB: INSERT user_credential (oauth)
        B->>DB: INSERT session
        B->>O: WRITE UserRegistered + UserLoggedIn
        B-->>F: 200 {access_token, refresh_token}
    end
```

---

## 12. Recommendation Generation

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant DB as Database
    participant O as Outbox
    participant L as Learning Context
    participant N as Notification

    S->>DB: Load mastery_scores, weak concepts, learning goal
    S->>S: Compute recommendation (type, payload, score)
    S->>DB: Check dedup (no identical in 7 days)
    S->>DB: INSERT recommendation
    S->>O: WRITE RecommendationGenerated
    O-->>L: RecommendationGenerated (async)
    L->>DB: Mark recommendation presented
    O-->>N: (If milestone) QueueNotification
    N->>DB: INSERT notification
    N->>O: WRITE NotificationQueued
```

---

## 13. Algorithm Upgrade (rollout)

```mermaid
sequenceDiagram
    participant E as Engineer
    participant F as Admin Portal
    participant B as Backend
    participant DB as Database
    participant O as Outbox
    participant W as Background Worker

    E->>F: PublishAlgorithmVersion (after shadow eval + sign-off)
    F->>B: POST /api/v1/admin/algorithm-versions/{id}/publish
    B->>DB: UPDATE algorithm_versions SET is_active=false WHERE is_active=true
    B->>DB: UPDATE algorithm_versions SET is_active=true WHERE id={id}
    B->>O: WRITE AlgorithmVersionPublished
    B-->>F: 200 OK

    O-->>W: AlgorithmVersionPublished (async)
    W->>W: Start RecomputeMasteryForAlgorithmVersion
    W->>O: WRITE MasteryRecomputeStarted
    loop Batch (10,000 learners)
        W->>DB: SELECT batch of learners
        W->>DB: Recompute mastery_scores for batch
        W->>O: WRITE MasteryRecomputeProgressed
    end
    W->>O: WRITE MasteryRecomputeCompleted
```

---

## 14. Notification Flow

```mermaid
sequenceDiagram
    participant E as Event Subscriber
    participant B as Backend
    participant DB as Database
    participant O as Outbox
    participant W as Dispatch Worker
    participant P as Email/Push Provider

    E->>B: QueueNotification (from event)
    B->>DB: Check user preferences + dedup
    B->>DB: INSERT notification (queued)
    B->>O: WRITE NotificationQueued
    O-->>W: NotificationQueued (async)
    W->>DB: SELECT notification (queued)
    W->>P: Send (email/push/in-app)
    alt Success
        P-->>W: Delivered
        W->>DB: UPDATE notification (sent/delivered)
        W->>O: WRITE NotificationSent
    else Failure
        P-->>W: Error
        W->>DB: UPDATE notification (retry count++)
        W->>W: Schedule retry (backoff)
        alt Max retries reached
            W->>DB: UPDATE notification (failed)
            W->>O: WRITE NotificationFailed
        end
    end
```

---

## 15. Subscription Upgrade

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant S as Stripe
    participant DB as Database
    participant O as Outbox
    participant L as Learning Context

    U->>F: Click "Upgrade to Pro"
    F->>B: POST /api/v1/billing/upgrade {plan_id}
    B->>DB: SELECT subscription
    B->>S: Create prorated charge
    alt Payment success
        S-->>B: Payment confirmed
        B->>DB: UPDATE subscription (plan_id)
        B->>O: WRITE SubscriptionUpgraded
        B-->>F: 200 OK
        F-->>U: "Upgraded!"
        O-->>L: SubscriptionUpgraded (async)
        L->>L: Update entitlements (unlimited questions)
    else Payment failed
        S-->>B: Payment failed
        B-->>F: 402 PAYMENT_FAILED
        F-->>U: "Payment failed"
    end
```

---

## 16. Payment Webhook

```mermaid
sequenceDiagram
    participant S as Stripe
    participant B as Backend
    participant DB as Database
    participant O as Outbox

    S->>B: POST /api/v1/billing/webhooks {event}
    B->>B: Verify signature
    B->>DB: Check idempotency (webhook_id)
    alt Already processed
        B-->>S: 200 OK (idempotent)
    else New
        B->>DB: UPDATE invoice/subscription per event
        B->>O: WRITE PaymentProcessed + (conditionally) SubscriptionActivated/Canceled
        B-->>S: 200 OK
    end
```

---

## 17. GDPR Erasure

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant DB as Database
    participant O as Outbox
    participant W as Background Worker

    U->>F: Request account deletion
    F->>B: POST /api/v1/account/deletion
    B->>DB: UPDATE user SET status='pending_deletion'
    B->>O: WRITE AccountDeletionRequested
    B-->>F: 202 Accepted (14-day grace)

    Note over W: After 14 days...
    W->>DB: SELECT users pending_deletion past grace
    W->>DB: UPDATE user SET email=anonymized, status='anonymized'
    W->>DB: DELETE user_credentials, sessions
    W->>DB: UPDATE user_profiles SET display_name='[anonymized]'
    W->>DB: UPDATE audit_logs SET actor_user_id=NULL
    W->>DB: UPDATE answers SET submitted_answer='[anonymized]' WHERE free_response
    W->>DB: DELETE learning_goals, study_plans, recommendations, streaks, notifications
    W->>O: WRITE UserAnonymized + GDPRRequestProcessed
```

---

## 18. Background Job Processing

```mermaid
sequenceDiagram
    participant S as Event Subscriber
    participant B as Backend
    participant DB as Database
    participant W as Worker
    participant O as Outbox

    S->>B: EnqueueBackgroundJob (from event)
    B->>DB: Compute payload_hash; check dedup
    B->>DB: INSERT background_job (queued)
    W->>DB: SELECT job (queued, ordered by priority, available_at)
    W->>DB: UPDATE job (running)
    W->>W: Execute job
    alt Success
        W->>DB: UPDATE job (completed)
    else Failure
        W->>DB: UPDATE job (failed, attempt_count++)
        alt attempt_count < max
            W->>DB: UPDATE job (queued, available_at=now+backoff)
        else Max reached
            W->>DB: UPDATE job (dead_lettered)
            W->>O: WRITE BackgroundJobDeadLettered
        end
    end
```

---

## 19. Code Execution (Sandbox)

```mermaid
sequenceDiagram
    participant U as Learner
    participant F as Frontend
    participant B as Backend
    participant SB as Sandbox
    participant DB as Database
    participant O as Outbox

    U->>F: Write code; click "Run"
    F->>B: POST /api/v1/attempts/{id}/execute {code}
    B->>SB: Execute (isolated container, no network)
    SB->>SB: Run against test cases
    SB-->>B: {pass_count, fail_count, output}
    B->>DB: INSERT answer revision (pre-submission)
    B->>O: WRITE CodeExecuted
    B-->>F: 200 {results}
    F-->>U: Show pass/fail + output

    U->>F: Click "Submit"
    F->>B: POST /api/v1/attempts {final_code}
    B->>SB: Execute final
    SB-->>B: Final results
    B->>B: ScoreAttempt
    B->>DB: INSERT attempt
    B->>O: WRITE AttemptRecorded
    B-->>F: 200 {outcome, explanation}
```

---

## 20. Achievement Unlock

```mermaid
sequenceDiagram
    participant M as Mastery Context
    participant O as Outbox
    participant L as Learning Context (subscriber)
    participant DB as Database
    participant N as Notification

    M->>O: WRITE ConceptStateChanged (to=mastered)
    O-->>L: ConceptStateChanged (async)
    L->>DB: Check achievement criteria (first concept mastered?)
    alt Criteria met + not already granted
        L->>DB: INSERT achievement
        L->>O: WRITE AchievementGranted
        O-->>N: AchievementGranted (async)
        N->>DB: INSERT notification ("Achievement unlocked!")
        N->>O: WRITE NotificationQueued
    else Already granted (idempotent)
        L->>L: Skip
    end
```

---

## 21. Feature Flag Evaluation

```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant R as Redis
    participant DB as Database

    F->>B: API call (with user context)
    B->>R: GET feature flag {key}
    alt Cache hit
        R-->>B: Flag config
    else Cache miss
        B->>DB: SELECT feature_flag
        B->>R: SET (1min TTL)
    end
    B->>DB: SELECT feature_flag_assignment (user override)
    B->>B: Evaluate (targeting rules + override)
    B-->>F: Response (with flag-gated behavior)
```

---

## 22. Session Pause/Resume

```mermaid
sequenceDiagram
    participant U as Learner
    participant F as Frontend
    participant B as Backend
    participant DB as Database
    participant R as Redis

    U->>F: Click "Pause"
    F->>B: POST /api/v1/sessions/{id}/pause
    B->>DB: UPDATE study_session (paused)
    B->>R: Cache queue state (24h TTL)
    B-->>F: 200 OK

    Note over U: Later (within 24h)...
    U->>F: Click "Resume"
    F->>B: POST /api/v1/sessions/{id}/resume
    B->>DB: SELECT study_session (paused, not expired)
    B->>R: GET cached queue
    B->>DB: UPDATE study_session (active)
    B-->>F: 200 {current_question}
    F-->>U: Resume at paused question
```

---

## 23. Outbox Dispatch

```mermaid
sequenceDiagram
    participant DB as Database
    participant D as Outbox Dispatcher
    participant EB as Event Bus
    participant S1 as Subscriber 1 (Mastery)
    participant S2 as Subscriber 2 (Analytics)
    participant S3 as Subscriber 3 (Notification)

    D->>DB: SELECT outbox_events WHERE status='pending' (batch)
    DB-->>D: Events
    loop Per event
        D->>EB: Dispatch event
        par Parallel delivery
            EB->>S1: Event
            EB->>S2: Event
            EB->>S3: Event
        end
        S1-->>EB: ACK
        S2-->>EB: ACK
        S3-->>EB: ACK (or NACK → retry)
        D->>DB: UPDATE outbox_events SET status='dispatched'
    end
```

---

## 24. PITR (Point-in-Time Recovery)

```mermaid
sequenceDiagram
    participant DBA as DBA
    participant FS as Object Storage
    participant R as Recovery Instance
    participant P as Primary (corrupted)

    DBA->>FS: Fetch most recent full backup (before target)
    DBA->>R: Restore full backup
    DBA->>R: Configure recovery_target_time
    R->>FS: Replay WAL segments (up to target)
    R->>R: Promote
    DBA->>R: Verify data (deleted rows present)
    DBA->>R: pg_dump affected tables
    DBA->>P: Import recovered data
    DBA->>P: Verify production
```

---

## 25. DR Failover

```mermaid
sequenceDiagram
    participant M as Monitoring
    participant O as On-Call
    participant DR as DR Standby
    participant DNS as DNS/LB
    participant A as Application
    participant U as Users

    M->>O: Alert: primary unavailable
    O->>O: Declare incident
    O->>DR: pg_ctl promote
    DR->>DR: Promote to primary
    O->>DNS: Update to point to DR region
    DNS-->>U: Route to DR
    A->>DR: Reconnect
    A->>A: Health checks pass
    A-->>U: Service restored
```

---

## 26. Nightly Analytics Snapshot

```mermaid
sequenceDiagram
    participant S as Scheduler (cron)
    participant W as Worker
    participant DB as Database
    participant O as Outbox

    S->>W: Trigger ComputeNightlySnapshots
    W->>DB: SELECT active learner_enrollments
    loop Per learner (batch)
        W->>DB: SELECT mastery_scores
        W->>DB: INSERT learner_daily_snapshots
    end
    W->>DB: INSERT concept_statistics, template_statistics
    W->>O: WRITE NightlySnapshotsComputed + ConceptStatisticsRecomputed + TemplateStatisticsRecomputed
```

---

## 27. Content Cache Invalidation

```mermaid
sequenceDiagram
    participant B as Backend (Content)
    participant O as Outbox
    participant S as Scheduling Context
    participant R as Redis

    B->>O: WRITE ContentPackPublished + ContentVersionCreated
    O-->>S: ContentPackPublished (async)
    S->>R: Invalidate content cache (subject_id)
    S->>R: Invalidate mastery cache (learners on this subject)
    S->>R: Invalidate queue cache (active sessions)
```

---

## 28. Streak Update

```mermaid
sequenceDiagram
    participant B as Backend (Learning)
    participant O as Outbox
    participant L as Learning Context (subscriber)
    participant DB as Database

    B->>O: WRITE StudySessionEnded
    O-->>L: StudySessionEnded (async)
    L->>DB: SELECT streak
    alt Last study date = today
        L->>L: No change (already counted)
    else Last study date = yesterday
        L->>DB: UPDATE streak (current_streak++, longest_streak if exceeded)
    else Gap > 1 day
        L->>DB: UPDATE streak (current_streak=1)
    end
    L->>DB: UPDATE streak (last_study_date=today)
```

---

## 29. Diagnostic Onboarding

```mermaid
sequenceDiagram
    participant U as Learner
    participant F as Frontend
    participant B as Backend
    participant S as Scheduler
    participant DB as Database
    participant O as Outbox

    U->>F: Start diagnostic
    F->>B: POST /api/v1/sessions {intent: diagnostic}
    B->>S: GenerateAdaptiveQueue (stratified sample across concepts)
    S-->>B: Diagnostic questions
    B-->>F: First question

    loop N diagnostic questions
        U->>F: Answer
        F->>B: SubmitAnswer
        B->>DB: INSERT attempt (intent=diagnostic)
        B->>O: WRITE AttemptRecorded
        O-->>Mastery: (async) UpdateMastery (baseline)
    end

    F->>B: POST /api/v1/onboarding/complete
    B->>DB: UPDATE learner_enrollment (active)
    B->>O: WRITE OnboardingCompleted
    B-->>F: 200 OK
    F-->>U: "Onboarding complete! Here's your dashboard."
```

---

## 30. Concurrent Mastery Update (optimistic concurrency)

```mermaid
sequenceDiagram
    participant W1 as Worker 1
    participant W2 as Worker 2
    participant DB as Database
    participant O as Outbox

    Note: Two attempts on the same concept arrive concurrently
    W1->>DB: SELECT mastery_score (version=5)
    W2->>DB: SELECT mastery_score (version=5)
    W1->>W1: Compute (includes attempt A)
    W2->>W2: Compute (includes attempt B)
    W1->>DB: UPDATE WHERE version=5 → success (version=6)
    W2->>DB: UPDATE WHERE version=5 → 0 rows affected (conflict)
    W2->>DB: SELECT mastery_score (version=6)
    W2->>W2: Recompute (includes attempt A + attempt B)
    W2->>DB: UPDATE WHERE version=6 → success (version=7)
    W2->>O: WRITE MasteryUpdated
```

---

## 31. Organization Member Addition

```mermaid
sequenceDiagram
    participant A as Org Admin
    participant F as Admin Portal
    participant B as Backend
    participant DB as Database
    participant O as Outbox

    A->>F: Add member (email)
    F->>B: POST /api/v1/organizations/{id}/members {user_id, role}
    B->>DB: Check: user exists, not already member
    B->>DB: INSERT organization_member
    B->>O: WRITE OrganizationMemberAdded
    B-->>F: 201 Created
    F-->>A: "Member added"
```

---

## 32. Migration Application

```mermaid
sequenceDiagram
    participant E as Engineer
    participant MR as Migration Runner
    participant DB as Database
    participant O as Outbox

    E->>MR: Apply migrations
    MR->>DB: Acquire advisory lock
    MR->>DB: SELECT migration_history (last version)
    loop Per pending migration
        MR->>DB: BEGIN
        MR->>DB: Apply migration (DDL)
        MR->>DB: INSERT migration_history
        MR->>DB: COMMIT
    end
    MR->>DB: Release advisory lock
    MR->>O: WRITE MigrationApplied (per migration)
```

---

*End of Sequence Diagrams.*
