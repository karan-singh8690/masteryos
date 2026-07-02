# 11 — Idempotency

> Idempotency strategy for commands, events, retries, message processing, duplicate prevention, replay.

---

## Idempotency Principles

1. **Commands are idempotent where possible** — retrying a command with the same idempotency key produces the same result.
2. **Events are idempotent at subscribers** — re-processing an event produces the same state.
3. **Retries are safe** — network retries don't cause duplicate side effects.
4. **Replay is safe** — re-processing historical events reconstructs the same state.

---

## Command Idempotency

### Idempotency Key Pattern

Most commands accept an optional `idempotency_key` (client-generated UUID). The server stores the key + result for 24 hours. A retry with the same key returns the cached result; no duplicate state change.

```python
def submit_answer(command, idempotency_key):
    cached = redis.get(f"idempotency:{idempotency_key}")
    if cached:
        return cached
    result = handle_submit_answer(command)
    redis.setex(f"idempotency:{idempotency_key}", 86400, result)
    return result
```

### Commands with Idempotency Keys

| Command | Idempotency Key | Dedup Window |
|---|---|---|
| `SubmitAnswer` | client-generated UUID | 24h |
| `ProcessPaymentWebhook` | webhook ID (from provider) | indefinite |
| `EnrollInSubject` | `(user_id, subject_id)` | active enrollment check |
| `StartStudySession` | `(learner_enrollment_id, started_at_window)` | 1min |
| `GrantAchievement` | `(learner_enrollment_id, achievement_type_id)` | unique constraint |
| `GenerateRecommendation` | `(learner_enrollment_id, type, payload_hash)` | 7 days |
| `QueueNotification` | `(user_id, type, payload_hash)` | dedup window |

### Commands that are Naturally Idempotent

Some commands are idempotent without an explicit key (the state check enforces it):

| Command | Natural Idempotency |
|---|---|
| `VerifyEmail` | Already-verified user is a no-op. |
| `RefreshToken` | Already-rotated token is rejected (rotation anomaly). |
| `LogoutUser` | Already-revoked session is a no-op. |
| `UpdateMastery` | Deterministic function of attempt history; re-applying the same attempt produces the same score. |
| `ScheduleReview` | Upsert by `(learner_enrollment_id, concept_id)`. |
| `CompleteOnboarding` | Already-completed is a no-op. |
| `AnonymizeUser` | Already-anonymized is a no-op. |

---

## Event Idempotency (at subscribers)

Subscribers must be idempotent: re-processing the same event produces the same state.

### Idempotency Strategies

1. **Deduplication by event ID**: subscriber stores processed event IDs; checks before processing.
   ```
   if redis.sismember("processed_events", event_id):
       return  # already processed
   process(event)
   redis.sadd("processed_events", event_id)
   ```

2. **State-based idempotency**: the subscriber's effect is a function of the event's data; re-applying produces the same state.
   - Example: `UpdateMastery` subscriber recomputes mastery from attempt history; re-processing `AttemptRecorded` doesn't change mastery (the attempt is already in history).

3. **Unique constraint idempotency**: the database enforces uniqueness.
   - Example: `GrantAchievement` has a unique constraint on `(learner_enrollment_id, achievement_type_id)`; duplicate insert fails.

### Subscriber Idempotency Requirements

| Subscriber | Strategy | Why |
|---|---|---|
| Mastery Engine (`AttemptRecorded`) | State-based (recompute from history) | Re-applying attempt doesn't change mastery. |
| Scheduler (`MasteryUpdated`) | State-based (regenerate from current mastery) | Re-applying mastery update doesn't change queue. |
| Learning (`ConceptStateChanged` → achievements) | Unique constraint | Achievement already granted → insert fails. |
| Analytics (`AttemptRecorded`) | Deduplication by event ID | Avoid double-counting in statistics. |
| Notification (`*` → queue notification) | Dedup window | No duplicate notifications within window. |
| Streak updater (`StudySessionEnded`) | State-based (check last_study_date) | Already-counted session → no change. |

---

## Retry Idempotency

### Command retries (client → server)

Client retries (e.g., network timeout) use the `idempotency_key`. The server returns the cached result for a duplicate key.

### Event retries (dispatcher → subscriber)

The dispatcher retries event delivery on subscriber failure. Subscribers must be idempotent (see above). Retries use the same event ID; the subscriber deduplicates.

### Background job retries

Background jobs are idempotent (the job's effect is the same on retry). The job tracks progress (e.g., `processed_learners`) and resumes from the last checkpoint.

---

## Duplicate Prevention

### Duplicate attempts

- **Cause**: network retry; double-click.
- **Prevention**: `SubmitAnswer` idempotency key; server caches result for 24h.

### Duplicate notifications

- **Cause**: event delivered twice; subscriber processes both.
- **Prevention**: `QueueNotification` dedup by `(user_id, type, payload_hash)` within a window (e.g., 1h).

### Duplicate achievements

- **Cause**: event delivered twice; subscriber tries to grant twice.
- **Prevention**: unique constraint on `(learner_enrollment_id, achievement_type_id)`; second insert fails.

### Duplicate payments

- **Cause**: Stripe webhook retry.
- **Prevention**: `ProcessPaymentWebhook` dedup by webhook ID; duplicate returns 200 OK without reprocessing.

---

## Replay Behavior

Replay (re-processing historical events) is safe because:

1. **Subscribers are idempotent** (see above).
2. **Events carry full context** (no implicit state dependence).
3. **Ordering is preserved** (per-aggregate ordering ensures deterministic reconstruction).

### Replay Use Cases

- **New subscriber backfill**: a new subscriber (e.g., a new analytics projection) processes all historical events to build its state.
- **Subscriber recovery**: a subscriber that lost state (e.g., database restore) re-processes recent events to rebuild.
- **Bug fix**: a subscriber with a bug is fixed; historical events are replayed to apply the corrected logic.

### Replay Limitations

- **External side effects**: replay of events like `NotificationSent` does not re-send emails (the side effect already happened). Replay is for state reconstruction.
- **Time-sensitive logic**: if a subscriber's logic depends on "now" (e.g., `due_at = now()`), replay produces different timestamps. Subscribers must use the event's timestamp, not the processing timestamp.

---

## Idempotency Key Generation

- **Client-generated UUID** (for command idempotency keys): the client generates a UUID per logical operation; retries use the same UUID.
- **Event ID** (for event idempotency): the outbox assigns a UUID to each event; the dispatcher delivers the same UUID on retry.
- **Content hash** (for dedup): `payload_hash` (SHA-256) for notifications, recommendations, background jobs.

---

## Idempotency and the Outbox

The outbox pattern ensures at-least-once delivery. Combined with idempotent subscribers, this provides effectively-once semantics:

- At-least-once delivery: an event may be delivered multiple times (dispatcher retry, subscriber restart).
- Idempotent subscriber: re-processing produces the same state.
- Effectively-once: the final state is as if the event was processed exactly once.

---

*End of Idempotency.*
