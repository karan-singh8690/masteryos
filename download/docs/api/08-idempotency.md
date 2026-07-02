# 08 — Idempotency

> Idempotency-Key header, replay behavior, duplicate handling, expiration, conflict responses.

---

## 1. Idempotency-Key Header

Write operations (POST, PUT, PATCH, DELETE that mutate state) support the `Idempotency-Key` header:

```
POST /attempts
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{ "question_instance_id": "...", "answer": {...} }
```

The client generates a UUID per logical operation. Retries (network timeout, 5xx) use the same key. The server caches the result for 24 hours; a retry with the same key returns the cached result without re-executing the operation.

---

## 2. Which Endpoints Support Idempotency

| Endpoint | Method | Idempotency |
|---|---|---|
| `/auth/register` | POST | Required |
| `/auth/login` | POST | Not required (naturally idempotent: same credentials → same result) |
| `/enrollments` | POST | Required |
| `/study-sessions` | POST | Required |
| `/attempts` | POST | Required (critical: prevents duplicate attempts) |
| `/billing/subscriptions` | POST | Required |
| `/billing/subscriptions/me/upgrade` | POST | Required |
| `/admin/*` (create/submit) | POST | Required |
| `/billing/webhooks/stripe` | POST | Not required (idempotent via webhook ID) |
| `GET`, `DELETE` | — | Inherently idempotent |

---

## 3. Replay Behavior

When a client retries with the same `Idempotency-Key`:

1. **Server checks cache**: looks up the key in Redis (or database).
2. **Cache hit**: returns the cached response (same status code, body, headers).
3. **Cache miss**: executes the operation, caches the result (24h TTL), returns the response.

### Concurrent Requests with Same Key

If two requests with the same key arrive concurrently:
- The first request executes and caches the result.
- The second request waits (or returns `409 Idempotency-Key-In-Use`).
- This prevents duplicate execution.

---

## 4. Duplicate Handling

### Duplicate Attempt Prevention

Without idempotency, a network retry could create two attempts for the same answer. With idempotency:

1. Client submits answer (key K).
2. Server records attempt; caches result under K.
3. Network timeout; client retries with key K.
4. Server finds cached result; returns it without recording a new attempt.

### Duplicate Payment Prevention

Stripe webhooks are retried by Stripe. The webhook endpoint is idempotent via the webhook ID (not the `Idempotency-Key` header): a duplicate webhook returns `200 OK` without reprocessing.

### Duplicate Achievement Prevention

Achievements have a unique constraint on `(learner_enrollment_id, achievement_type_id)`. A duplicate grant attempt fails with `409 ALREADY_GRANTED` (idempotent outcome).

---

## 5. Expiration

- **Idempotency cache TTL**: 24 hours.
- **After expiration**: a retry with the same key is treated as a new request (may fail if the operation is no longer valid, e.g., the session has ended).
- **Recommendation**: clients generate a new UUID for each logical operation, not for each retry.

---

## 6. Conflict Responses

### `409 Idempotency-Key-In-Use`

If two concurrent requests use the same key and the server cannot determine which is the "real" request:

```json
{
  "code": "IDEMPOTENCY_KEY_IN_USE",
  "message": "An operation with this idempotency key is already in progress.",
  "correlation_id": "..."
}
```

The client should wait and retry (the first request's result will be cached).

### `422 Idempotency-Key-Mismatch`

If a client reuses a key with a different request body:

```json
{
  "code": "IDEMPOTENCY_KEY_MISMATCH",
  "message": "This idempotency key was used with a different request body.",
  "correlation_id": "..."
}
```

The server detects this by hashing the request body and comparing to the cached hash. This prevents accidental key reuse for different operations.

---

## 7. Best Practices for Clients

1. **Generate a UUID per logical operation** (not per retry).
2. **Store the key** with the operation context (so retries can reuse it).
3. **Handle `409 IDEMPOTENCY_KEY_IN_USE`** by waiting and retrying.
4. **Don't reuse keys** for different operations (the server will reject mismatched bodies).
5. **For long-running operations**, use `202 Accepted` with a job ID; poll for completion (idempotency applies to the acceptance, not the completion).

---

*End of Idempotency.*
