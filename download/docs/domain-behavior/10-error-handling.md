# 10 — Error Handling

> Business failures and recovery strategies.

---

## Error Handling Principles

1. **Fail fast on invalid input** — validation rejects bad input before business logic.
2. **Fail gracefully on infrastructure issues** — the system degrades rather than crashes.
3. **Never lose data** — append-only tables (attempts, audit logs) are never modified; corrections are append-as-compensating.
4. **Recover automatically where possible** — retries with backoff; idempotent subscribers.
5. **Alert on unrecoverable failures** — dead-letter queues; on-call paging.

---

## Error Categories

### 1. Validation Errors (4xx)

Rejected at the API boundary before business logic.

| Error Code | Cause | Recovery |
|---|---|---|
| `INVALID_EMAIL` | Email format invalid. | Client corrects and retries. |
| `WEAK_PASSWORD` | Password below strength. | Client corrects. |
| `INVALID_TIMEZONE` | Not a valid IANA timezone. | Client corrects. |
| `INVALID_PARAMETER_SCHEMA` | Template parameter schema invalid JSON Schema. | Instructor corrects. |
| `ANSWER_TYPE_MISMATCH` | Answer type doesn't match question type. | Client corrects. |
| `INVALID_GOAL_TYPE` | Goal type not in enum. | Client corrects. |

**Handling**: return 422 with field-level errors; no state change; no event.

---

### 2. Precondition Errors (4xx)

Business rule violations.

| Error Code | Cause | Recovery |
|---|---|---|
| `EMAIL_ALREADY_REGISTERED` | Email in use by active user. | Client logs in or resets password. |
| `ALREADY_ENROLLED` | User already enrolled (active). | Client goes to dashboard. |
| `ACTIVE_SESSION_EXISTS` | Learner has an active session. | Client resumes or ends existing. |
| `QUESTION_ALREADY_ANSWERED` | Question instance already answered. | Client fetches next question. |
| `ALREADY_GRANTED` | Achievement already awarded. | Idempotent; no-op. |
| `ALREADY_SUBSCRIBED` | User has active subscription. | Client manages existing. |
| `EMAIL_NOT_VERIFIED` | User hasn't verified email. | Client verifies first. |
| `SUBJECT_NOT_PUBLISHED` | Subject is draft/deprecated. | Cannot enroll. |
| `MINIMUM_CONTENT_NOT_MET` | Subject lacks minimum content. | Authors add content. |
| `CANNOT_SUSPEND_ADMIN` | Admin accounts can't be suspended. | Revoke admin first. |
| `CANNOT_UNLINK_LAST_CREDENTIAL` | User needs ≥1 credential. | Add another credential first. |
| `CANNOT_REVOKE_OWN_ADMIN_ROLE` | Prevent self-lockout. | Have another admin revoke. |
| `CANNOT_REMOVE_LAST_ORG_ADMIN` | Org needs ≥1 admin. | Add another admin first. |

**Handling**: return 409 Conflict; no state change; no event.

---

### 3. Authorization Errors (4xx)

| Error Code | Cause | Recovery |
|---|---|---|
| `NOT_AUTHORIZED` | User lacks permission. | Client redirects to allowed page. |
| `REVIEWER_IS_AUTHOR` | Self-review forbidden. | Assign different reviewer. |

**Handling**: return 403; no state change; no event; audit-log the attempt.

---

### 4. State Transition Errors (4xx)

Invalid state machine transitions.

| Error Code | Cause | Recovery |
|---|---|---|
| `INVALID_STATE_TRANSITION` | E.g., publishing a `rejected` pack. | Client refreshes state; corrects. |
| `SESSION_NOT_ACTIVE` | Operating on a non-active session. | Client starts new session. |
| `SESSION_EXPIRED` | Session past 24h resumption window. | Client starts new session. |
| `ONBOARDING_ALREADY_COMPLETE` | Trying to complete onboarding twice. | Idempotent; no-op. |
| `USER_NOT_PENDING_DELETION` | Trying to cancel non-pending deletion. | No-op. |
| `GRACE_PERIOD_EXPIRED` | Trying to cancel deletion past grace. | Too late; account will be anonymized. |
| `MFA_ALREADY_ENABLED` / `MFA_NOT_ENABLED` | Wrong state for MFA command. | Client refreshes. |

**Handling**: return 409; no state change; no event.

---

### 5. Concurrency Errors (409)

| Error Code | Cause | Recovery |
|---|---|---|
| `OPTIMISTIC_CONCURRENCY_CONFLICT` | Two concurrent mastery updates. | Retry (re-read, recompute, re-write); max 3. |
| `ROTATION_ANOMALY_DETECTED` | Refresh token replay. | Revoke session family; force re-login. |

**Handling**: 
- `OPTIMISTIC_CONCURRENCY_CONFLICT`: automatic retry within the command handler (transparent to caller); if max retries exceeded, return 409.
- `ROTATION_ANOMALY_DETECTED`: return 401; force re-login; audit-log.

---

### 6. Infrastructure Errors (5xx)

| Error Code | Cause | Recovery |
|---|---|---|
| `DATABASE_UNAVAILABLE` | PostgreSQL unreachable. | Retry with backoff; circuit breaker; failover to replica (reads only). |
| `REDIS_UNAVAILABLE` | Cache unreachable. | Fall through to database; degraded latency. |
| `SANDBOX_UNAVAILABLE` | Code execution sandbox down. | Return error; learner retries; degrade to non-code questions. |
| `OAUTH_PROVIDER_ERROR` | Google/GitHub OAuth down. | Return error; suggest password login. |
| `PAYMENT_FAILED` | Stripe charge declined. | Return 402; user updates payment method. |
| `EMAIL_SERVICE_UNAVAILABLE` | Email provider down. | Queue notification; retry. |

**Handling**: return 503 (Service Unavailable) with `Retry-After`; retry with exponential backoff; circuit breaker prevents cascading failures.

---

### 7. Outbox Failures

| Failure | Cause | Recovery |
|---|---|---|
| Outbox dispatcher down | Process crash / restart. | Events accumulate; dispatcher resumes; no loss. |
| Subscriber unavailable | Subscriber context down. | Events stay `pending`; retried with backoff; dead-letter after 5 attempts (standard) or 10 (critical). |
| Subscriber processing failure | Bug in subscriber handler. | Retry with backoff; dead-letter; alert; manual investigation. |
| Dead-letter queue growth | Repeated subscriber failures. | Alert on-call; investigate root cause; re-queue after fix. |

**Handling**:
- Standard events: 5 retries with exponential backoff (1s, 2s, 4s, 8s, 16s); dead-letter.
- Critical events: 10 retries with longer backoff; dead-letter; immediate alert.
- Dead-lettered events: stored in outbox with `status = 'dead_lettered'`; visible in admin portal; manual re-queue or discard.

---

### 8. Specific Business Failures

#### Duplicate Attempts
- **Cause**: network retry; learner double-clicks submit.
- **Handling**: `SubmitAnswer` is idempotent via `idempotency_key` (client-generated). A retry with the same key returns the original result; no duplicate attempt is recorded.
- **Recovery**: client retries with same key; server returns cached result.

#### Late Submissions
- **Cause**: learner submits after session ended or question timed out.
- **Handling**: return 409 `SESSION_NOT_ACTIVE` or `QUESTION_ALREADY_ANSWERED`. The attempt is not recorded.
- **Recovery**: client starts a new session.

#### Deleted Content
- **Cause**: content archived while a learner has it in their queue.
- **Handling**: the scheduler filters out archived content; the question is skipped; the next question is served.
- **Recovery**: transparent to the learner.

#### Expired Sessions
- **Cause**: learner returns after 24h; session is `abandoned`.
- **Handling**: return 409 `SESSION_EXPIRED`; client starts a new session.
- **Recovery**: the abandoned session's analytics are recorded (no scoring).

#### Algorithm Mismatch
- **Cause**: an attempt references an `algorithm_version_id` that is no longer active.
- **Handling**: this is expected (triple versioning); the Mastery Engine uses the recorded version for historical reconstruction and the active version for new computations. No error.
- **Recovery**: none needed (by design).

#### Version Conflicts (mastery)
- **Cause**: two concurrent `UpdateMastery` commands on the same learner-concept.
- **Handling**: optimistic concurrency; the second write fails; retry with re-read.
- **Recovery**: automatic retry (max 3); if still failing, log and skip (the next attempt will update mastery correctly).

#### Notification Failures
- **Cause**: email/push provider down; invalid address; user blocked.
- **Handling**: retry with backoff (max 5); dead-letter; alert on repeated failures.
- **Recovery**: dead-lettered notifications are visible in admin portal; manual retry or discard.

#### Mastery Recompute Failures
- **Cause**: background job fails mid-batch (database error, OOM).
- **Handling**: the job is idempotent and resumable; it tracks progress per learner; on restart, it resumes from the last checkpoint.
- **Recovery**: automatic (job scheduler restarts); if persistent, manual intervention.

#### Payment Webhook Duplicate
- **Cause**: Stripe retries webhooks; same event delivered twice.
- **Handling**: `ProcessPaymentWebhook` is idempotent via webhook ID dedup. A duplicate returns 200 OK without reprocessing.
- **Recovery**: none needed (idempotent).

#### Content Validation Failure (at publish)
- **Cause**: content pack has a cycle, missing objective, untagged distractor.
- **Handling**: `PublishContentPack` fails; pack stays `in_review`; `ContentValidationFailed` error with details.
- **Recovery**: author fixes the issue; resubmits.

---

## Recovery Strategies Summary

| Failure Type | Strategy |
|---|---|
| Validation / precondition / authorization / state | Return 4xx; no state change; client corrects. |
| Concurrency | Automatic retry (optimistic); force re-login (rotation anomaly). |
| Infrastructure | Retry with backoff; circuit breaker; failover; degrade gracefully. |
| Outbox / subscriber | Retry; dead-letter; alert; manual investigation. |
| Duplicate (client retry) | Idempotency key; return cached result. |
| Background job failure | Idempotent resumable retry; dead-letter after max. |

---

## Alerting

- **Dead-letter queue depth > threshold**: page on-call.
- **Outbox dispatch lag > 60s**: page on-call.
- **Subscriber failure rate > 5%**: page on-call.
- **Critical event dead-lettered**: immediate page.
- **Background job dead-lettered**: page on-call.
- **Database / Redis / Sandbox unavailable**: immediate page.

---

*End of Error Handling.*
