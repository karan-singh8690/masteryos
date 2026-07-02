# 09 — Eventual Consistency

> Where the system is strongly consistent, eventually consistent, synchronous, or asynchronous — and why.

---

## Consistency Model

The Mastery Engine uses a **hybrid consistency model**: strong consistency within a bounded context (transactional), eventual consistency across contexts (via events). This is the standard DDD + outbox pattern trade-off (ADR-0006, ADR-0012).

---

## Strongly Consistent (within a transaction)

These operations are atomic within a single database transaction:

| Operation | Scope | Why strong |
|---|---|---|
| `SubmitAnswer` → write Attempt + write Outbox event | assessment | The attempt and its event must be written together (outbox pattern). |
| `UpdateMastery` → write MasteryScore + write Outbox event | mastery | The score and its event must be written together. |
| `PublishContentPack` → write ContentVersion + TemplateVersions + Outbox events | content | Atomic publishing (all or none). |
| `SubscribeToPlan` → write Subscription + write Outbox event | billing | Atomic. |
| `GrantRole` → write role + write Outbox event | administration | Atomic. |
| `AnonymizeUser` → update user + delete credentials + Outbox event | identity | Atomic (GDPR compliance). |
| Session state transitions (start/pause/end) | learning | Atomic. |

**Guarantee**: if the transaction commits, all writes are durable; if it rolls back, none are. The outbox event is committed with the data change, so it is never lost.

---

## Eventually Consistent (across contexts, via events)

These operations propagate asynchronously via the outbox + event bus:

| Trigger (event) | Consumer (eventual) | What's eventually consistent | Lag target |
|---|---|---|---|
| `AttemptRecorded` | Mastery (updates MasteryScore) | Mastery score reflects the latest attempt | < 1s |
| `MasteryUpdated` | Scheduling (regenerates queue) | Queue reflects updated mastery | < 1s |
| `MasteryUpdated` | Analytics (snapshot) | Analytics reflect updated mastery | nightly |
| `MasteryUpdated` | Learning (progress page) | Progress page reflects updated mastery | < 5s (cache TTL) |
| `ConceptStateChanged` | Learning (achievements) | Achievements reflect state change | < 1s |
| `ContentPackPublished` | Scheduling (cache invalidation) | Scheduler uses new content | < 1s |
| `StudySessionEnded` | Administration (streak update) | Streak reflects session | < 1s |
| `SubscriptionActivated` | Learning (entitlements) | Entitlements reflect subscription | < 1s |
| `UserAnonymized` | Analytics, Billing | Anonymized data propagates | < 1s |
| `AlgorithmVersionPublished` | Mastery (recompute) | All scores under new algorithm | days (batch) |

**Guarantee**: the event is delivered at-least-once; subscribers are idempotent; the final state is consistent. The lag is the dispatch + processing time.

---

## Synchronous (request-response)

These operations are synchronous (the caller waits for the result):

| Operation | Why synchronous |
|---|---|
| `GetDashboard`, `GetConceptProgress`, all Queries | Read-only; caller needs the result. |
| `SubmitAnswer` (the write) | The learner waits for scoring outcome + explanation. |
| `StartStudySession` | The learner waits for the first question. |
| `LoginUser`, `RefreshToken` | The user waits for tokens. |
| `EnrollInSubject` | The user waits for confirmation. |
| `SubscribeToPlan` | The user waits for payment confirmation. |
| All command writes (the initial write) | The caller waits for "accepted." |

**Note**: the synchronous part is the initial write + outbox write. The downstream effects (mastery update, queue regeneration, notifications) are asynchronous.

---

## Asynchronous (fire-and-forget via events)

These operations are asynchronous (the caller does not wait):

| Operation | Trigger | Async consumer |
|---|---|---|
| Mastery score update | `AttemptRecorded` | Mastery Engine |
| Queue regeneration | `MasteryUpdated` | Scheduler |
| Achievement award | `ConceptStateChanged` | Learning |
| Notification dispatch | Various events | Notification worker |
| Analytics snapshot | `MasteryUpdated` (nightly batch) | Analytics worker |
| Streak update | `StudySessionEnded` | Learning subscriber |
| Cache invalidation | `ContentPublished` | Scheduling subscriber |
| Mastery recompute | `AlgorithmVersionPublished` | Mastery worker (batch) |
| GDPR anonymization | `AccountDeletionRequested` (after grace) | Administration worker |

**Guarantee**: the caller receives a response before the async effects complete. The UI may show a loading state or update via WebSocket/polling when the async effect completes.

---

## Outbox Integration

The outbox pattern (ADR-0012) is the bridge between synchronous and asynchronous:

1. **Synchronous**: the command handler writes the data change + the outbox event in one transaction. The caller waits for this transaction to commit.
2. **Asynchronous**: the outbox dispatcher polls the outbox and delivers events to subscribers. Subscribers process events asynchronously.

**Why this matters**:
- The data change and the event are atomic (no lost events).
- The caller doesn't wait for subscribers (low latency).
- Subscribers can process at their own pace (decoupled).

**Failure modes**:
- Outbox dispatcher down → events accumulate in outbox; delivered when dispatcher resumes.
- Subscriber down → events accumulate in outbox (dispatched but not processed); subscriber catches up when it resumes.
- Subscriber processing failure → retry with backoff; dead-letter after max attempts.

See `10-error-handling.md` for failure recovery.

---

## Consistency by Query (per `03-queries.md`)

| Consistency | Queries | Read from |
|---|---|---|
| **Strong** | GetUser, GetSubject, GetConcept, GetAttemptHistory, GetSubscription, GetAuditLogs | Primary |
| **Read-your-writes** | GetDashboard, GetAdaptiveQueue, GetConceptProgress, GetWeakConcepts, GetMasteryScore, GetDueReviews | Primary (or replica with < 1s lag check) |
| **Eventually consistent** | SearchUsers (admin), GetRetentionAnalytics, GetConceptStatistics, GetCohortAnalytics, GetLearnerDailySnapshots | Read replica or analytics warehouse |

**Read-your-writes implementation**: the query handler checks the replica lag; if lag < 1s, read from replica; if lag > 1s (or the user wrote recently), read from primary. This ensures the learner sees their own recent writes immediately.

---

## Why Hybrid (not all strong, not all eventual)

**All strong (single distributed transaction)**:
- Pro: simplest mental model.
- Con: distributed transactions are slow and fragile; the learning loop's 200ms target is unachievable.
- Con: tight coupling between contexts.

**All eventual (no transactions)**:
- Pro: maximum decoupling.
- Con: the learning loop's core (attempt + mastery) would be inconsistent; a learner could see an outdated mastery score immediately after answering.
- Con: data integrity is at risk (e.g., attempt without event).

**Hybrid (chosen)**:
- Strong within a context (transactional integrity).
- Eventual across contexts (decoupled, fast).
- The learner's experience is "fast write, slightly delayed effects" — acceptable because the delays are < 1s for critical paths.

---

## Consistency Trade-offs Accepted

1. **Mastery score delay**: after `SubmitAnswer`, the mastery score updates within ~1s (async). The learner sees the explanation immediately (synchronous); the mastery score updates on the next dashboard load (or via WebSocket push).

2. **Queue regeneration delay**: after `MasteryUpdated`, the queue regenerates within ~1s (async). The next question may use the old queue for ~1s; acceptable.

3. **Analytics delay**: nightly snapshots mean analytics are up to 24h stale. Acceptable for aggregate analytics; per-user analytics are real-time (from primary).

4. **Recommendation delay**: recommendations are generated asynchronously; the learner may not see a new recommendation for ~5s. Acceptable (recommendations are advisory).

5. **Notification delay**: notifications are dispatched asynchronously; a notification may take seconds to minutes to deliver. Acceptable (notifications are not time-critical).

---

## Critical Consistency Requirements (non-negotiable)

1. **Attempt + Outbox event atomicity**: the attempt and its `AttemptRecorded` event are written in one transaction. No attempt without an event; no event without an attempt.
2. **Mastery score single-writer**: only the Mastery Engine writes `mastery_scores`. No other context writes directly.
3. **Triple versioning on every attempt**: `content_version_id`, `template_version_id`, `algorithm_version_id` are recorded atomically with the attempt.
4. **GDPR erasure completeness**: `AnonymizeUser` is atomic; all PII is purged or none. No partial anonymization.
5. **Audit log atomicity**: privileged actions and their audit log entries are written in one transaction.

---

*End of Eventual Consistency.*
