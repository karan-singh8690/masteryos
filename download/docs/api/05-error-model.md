# 05 — Error Model

> Standard error object, error codes, correlation IDs.

---

## Standard Error Object

Every error response uses the same shape:

```json
{
  "code": "EMAIL_ALREADY_REGISTERED",
  "message": "An account with this email already exists.",
  "details": {
    "field": "email",
    "value": "alex@example.com"
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-07-02T14:30:00Z",
  "doc_url": "https://docs.masteryengine.com/api/errors/EMAIL_ALREADY_REGISTERED",
  "retry_after": null
}
```

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `code` | string | yes | SCREAMING_SNAKE_CASE error code. Stable; part of the API contract. |
| `message` | string | yes | Human-readable message. May change between versions; do not parse. |
| `details` | object | no | Field-level validation errors or additional context. |
| `correlation_id` | UUID | yes | For support and log tracing. Include in support requests. |
| `timestamp` | ISO 8601 | no | When the error occurred. |
| `doc_url` | URI | no | Link to error documentation. |
| `retry_after` | integer | no | Seconds to wait before retrying (rate limits, 503). |

---

## Error Code Categories

### Authentication Errors (401)

| Code | HTTP | Meaning |
|---|---|---|
| `UNAUTHORIZED` | 401 | Missing or invalid access token. |
| `TOKEN_EXPIRED` | 401 | Access token expired; refresh required. |
| `MFA_REQUIRED` | 401 | MFA code required for this operation. |
| `INVALID_CREDENTIALS` | 401 | Wrong email/password/MFA code. |

### Authorization Errors (403)

| Code | HTTP | Meaning |
|---|---|---|
| `FORBIDDEN` | 403 | Authenticated but not authorized. |
| `EMAIL_NOT_VERIFIED` | 403 | Email verification required. |
| `SUBSCRIPTION_REQUIRED` | 403 | Paid subscription required. |

### Resource Errors (404, 410)

| Code | HTTP | Meaning |
|---|---|---|
| `NOT_FOUND` | 404 | Resource does not exist. |
| `GONE` | 410 | Resource permanently removed (deprecated). |

### Conflict Errors (409)

| Code | HTTP | Meaning |
|---|---|---|
| `EMAIL_ALREADY_REGISTERED` | 409 | Email in use. |
| `ALREADY_ENROLLED` | 409 | Already enrolled. |
| `ACTIVE_SESSION_EXISTS` | 409 | Active session exists. |
| `QUESTION_ALREADY_ANSWERED` | 409 | Question already answered. |
| `ALREADY_GRANTED` | 409 | Achievement already awarded. |
| `ALREADY_SUBSCRIBED` | 409 | Active subscription exists. |
| `DUPLICATE_RECOMMENDATION` | 409 | Duplicate within cooldown window. |
| `OPTIMISTIC_CONCURRENCY_CONFLICT` | 409 | Concurrent modification; retry. |
| `ROTATION_ANOMALY_DETECTED` | 409 | Refresh token replay; session revoked. |
| `INVALID_STATE_TRANSITION` | 409 | Invalid state machine transition. |
| `CYCLE_DETECTED` | 409 | Concept dependency cycle. |
| `REVIEWER_IS_AUTHOR` | 409 | Self-review forbidden. |

### Validation Errors (422)

| Code | HTTP | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Semantic validation failure (see `details` for fields). |
| `INVALID_EMAIL` | 422 | Email format invalid. |
| `WEAK_PASSWORD` | 422 | Password below strength. |
| `INVALID_TIMEZONE` | 422 | Not a valid IANA timezone. |
| `INVALID_PARAMETER_SCHEMA` | 422 | Template parameter schema invalid. |
| `ANSWER_TYPE_MISMATCH` | 422 | Answer type doesn't match question type. |
| `INVALID_GOAL_TYPE` | 422 | Goal type not in enum. |
| `VAGUE_OBJECTIVE` | 422 | Objective not observable. |
| `CONTENT_VALIDATION_FAILED` | 422 | Content pack validation failed. |
| `MINIMUM_CONTENT_NOT_MET` | 422 | Subject lacks minimum content. |
| `TARGET_DATE_IN_PAST` | 422 | Target date must be future. |
| `MULTIPLE_TIME_BOUND_GOALS` | 422 | Only one active time-bound goal allowed. |

### Precondition Errors (422)

| Code | HTTP | Meaning |
|---|---|---|
| `SESSION_NOT_ACTIVE` | 422 | Session not active. |
| `SESSION_EXPIRED` | 422 | Session past 24h. |
| `ONBOARDING_ALREADY_COMPLETE` | 422 | Onboarding already done. |
| `USER_NOT_PENDING_DELETION` | 422 | No pending deletion. |
| `GRACE_PERIOD_EXPIRED` | 422 | Deletion grace period elapsed. |
| `MFA_ALREADY_ENABLED` | 422 | MFA already on. |
| `MFA_NOT_ENABLED` | 422 | MFA not on. |
| `CANNOT_SUSPEND_ADMIN` | 422 | Cannot suspend admin. |
| `CANNOT_UNLINK_LAST_CREDENTIAL` | 422 | Need ≥1 credential. |
| `CANNOT_REVOKE_OWN_ADMIN_ROLE` | 422 | Prevent self-lockout. |
| `CANNOT_REMOVE_LAST_ORG_ADMIN` | 422 | Org needs ≥1 admin. |

### Rate Limiting (429)

| Code | HTTP | Meaning |
|---|---|---|
| `RATE_LIMITED` | 429 | Rate limit exceeded; see `Retry-After` header. |

### Payment Errors (402)

| Code | HTTP | Meaning |
|---|---|---|
| `PAYMENT_FAILED` | 402 | Stripe charge declined. |
| `PAYMENT_METHOD_REQUIRED` | 402 | No payment method on file. |

### Server Errors (5xx)

| Code | HTTP | Meaning |
|---|---|---|
| `INTERNAL_ERROR` | 500 | Unexpected server error. |
| `DATABASE_UNAVAILABLE` | 503 | Database unreachable. |
| `REDIS_UNAVAILABLE` | 503 | Cache unreachable; degraded. |
| `SANDBOX_UNAVAILABLE` | 503 | Code execution sandbox down. |
| `OAUTH_PROVIDER_ERROR` | 502 | OAuth provider (Google/GitHub) error. |
| `EMAIL_SERVICE_UNAVAILABLE` | 502 | Email provider down. |
| `GATEWAY_TIMEOUT` | 504 | Upstream timeout. |

---

## Validation Error Details

For `VALIDATION_ERROR` (422), the `details` field contains field-level errors:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed.",
  "details": {
    "errors": [
      { "field": "email", "code": "INVALID_EMAIL", "message": "Invalid email format." },
      { "field": "password", "code": "TOO_SHORT", "message": "Password must be at least 12 characters." }
    ]
  },
  "correlation_id": "..."
}
```

---

## Correlation ID

Every request is assigned a `correlation_id` (UUID), returned in:
- The `X-Correlation-Id` response header (always).
- The `correlation_id` field of error responses.

Clients can pass `X-Correlation-Id` in the request header to trace a request across services; the server uses the client-provided ID if present, otherwise generates one.

Support requests should include the `correlation_id` for fast log tracing.

---

## Retry Hints

For errors where retry is appropriate, the error includes guidance:
- `429 RATE_LIMITED`: `Retry-After` header (seconds).
- `503 SERVICE_UNAVAILABLE`: `Retry-After` header.
- `409 OPTIMISTIC_CONCURRENCY_CONFLICT`: client should re-read and retry (automatic for most clients).
- `5xx`: exponential backoff with jitter.

For errors where retry is not appropriate (4xx validation, authorization), no retry hint is provided; the client must fix the request.

---

*End of Error Model.*
