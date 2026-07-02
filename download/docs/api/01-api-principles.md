# 01 — API Principles

> REST principles, resource-oriented design, naming, JSON conventions, HTTP status code philosophy.

---

## 1. REST Principles

The Mastery Engine API is **RESTful**: resource-oriented, stateless, cacheable where appropriate, and layered. We do not use RPC-style endpoints (`POST /submitAnswer`) or action-oriented URLs (`POST /attempts/submit`); instead, we use resource-oriented URLs (`POST /attempts` to create an attempt).

### Resource-Oriented Design

- Resources are nouns, not verbs: `/attempts`, `/study-sessions`, `/mastery-scores`.
- Operations are HTTP methods: `GET` (read), `POST` (create), `PATCH` (partial update), `PUT` (full update), `DELETE` (remove).
- Sub-resources express hierarchy: `/learners/{id}/enrollments`, `/subjects/{id}/concepts`.
- Custom actions (when no HTTP method fits) use a sub-resource verb: `POST /study-sessions/{id}/end`, `POST /attempts/{id}/submit`. These are sparingly used.

### Stateless Requests

Every request is self-contained: the server does not maintain session state between requests (the JWT carries identity). This enables horizontal scaling (any instance serves any request, per ASD Section 13.1).

### Cacheable

- `GET` responses include `ETag` and `Cache-Control` headers where caching is safe (e.g., content lookups).
- `POST`/`PUT`/`PATCH`/`DELETE` responses are not cached.
- Cache invalidation is via `ETag` mismatch or `Cache-Control: no-cache`.

---

## 2. Naming Conventions

### URL Paths

- **Kebab-case**, plural for collections, singular for individual resources:
  - `/api/v1/users` (collection)
  - `/api/v1/users/{user_id}` (individual)
- **Nested resources** express hierarchy:
  - `/api/v1/subjects/{subject_id}/concepts`
  - `/api/v1/learners/{learner_id}/mastery-scores`
- **Action endpoints** (when needed) use a verb sub-resource:
  - `POST /api/v1/study-sessions/{id}/end`
  - `POST /api/v1/auth/login`
- **Version prefix**: `/api/v1/...` (per `07-versioning.md`).

### JSON Field Names

- **snake_case** (matches Task 002's Naming Standards and Task 004's column names):
  - `learner_enrollment_id`, `mastery_score_combined`, `created_at`
- **Booleans** prefixed with `is_` or `has_`: `is_active`, `has_hint`
- **Timestamps** suffixed with `_at`: `created_at`, `served_at`
- **Dates** suffixed with `_date`: `queue_date`, `target_date`
- **Foreign keys** suffixed with `_id`: `user_id`, `concept_id`

### Query Parameters

- **snake_case**: `created_after`, `sort_by`, `page_size`
- **Boolean filters**: `is_active=true`, `include_archived=false`
- **Comma-separated lists**: `fields=id,name,slug`, `expand=concepts,objectives`

### Header Names

- Standard HTTP headers (`Authorization`, `Content-Type`, `Accept`).
- Custom headers prefixed with `X-`: `X-Idempotency-Key`, `X-Correlation-Id`, `X-Request-Id`.

---

## 3. JSON Conventions

### Request and Response Body

- `Content-Type: application/json` for all request and response bodies.
- UTF-8 encoding.
- No trailing commas.
- ISO 8601 timestamps with timezone: `2026-07-02T14:30:00Z`.
- Dates: `2026-07-02`.
- Durations: ISO 8601 durations (`P7D` for 7 days) or integer seconds, depending on context.
- UUIDs as strings: `"550e8400-e29b-41d4-a716-446655440000"`.
- Nulls are explicit: omitted fields are not null; null means "intentionally empty."
- Empty collections are `[]`, not omitted.

### Field Selection

Clients can request specific fields via the `fields` query parameter (per `06-pagination-filtering.md`):
```
GET /api/v1/concepts/{id}?fields=id,name,slug
```

### Expansion

Clients can expand related resources via the `expand` parameter:
```
GET /api/v1/concepts/{id}?expand=objectives,misconceptions,dependencies
```

### Envelope

Responses for single resources are the resource object directly:
```json
{
  "id": "...",
  "name": "..."
}
```

Responses for collections are paginated envelopes:
```json
{
  "data": [...],
  "pagination": {
    "cursor": "...",
    "next_cursor": "...",
    "has_more": true,
    "total_count": 1234
  }
}
```

---

## 4. HTTP Status Code Philosophy

### 2xx Success

| Code | Meaning | When |
|---|---|---|
| `200 OK` | Request succeeded; response body present. | All successful `GET`, `PATCH`, `PUT`. |
| `201 Created` | Resource created; `Location` header present. | Successful `POST` that creates a resource. |
| `202 Accepted` | Request accepted for async processing. | Long-running operations (e.g., GDPR export). |
| `204 No Content` | Request succeeded; no response body. | Successful `DELETE`; some `POST` actions. |

### 3xx Redirection

| Code | Meaning | When |
|---|---|---|
| `301 Moved Permanently` | Resource permanently moved. | Rare; deprecated URLs. |
| `304 Not Modified` | Cached response is still valid. | `GET` with `If-None-Match` matching `ETag`. |

### 4xx Client Errors

| Code | Meaning | When |
|---|---|---|
| `400 Bad Request` | Malformed request (invalid JSON, missing required field). | Validation errors before business logic. |
| `401 Unauthorized` | Missing or invalid authentication. | No/invalid JWT; expired access token. |
| `403 Forbidden` | Authenticated but not authorized. | User lacks permission for this resource. |
| `404 Not Found` | Resource does not exist. | Unknown ID. |
| `409 Conflict` | Request conflicts with current state. | Duplicate resource; state transition violation. |
| `410 Gone` | Resource permanently removed. | Deprecated endpoint. |
| `422 Unprocessable Entity` | Semantic validation failure. | Valid JSON but business rule violation. |
| `429 Too Many Requests` | Rate limit exceeded. | Rate limit hit; `Retry-After` header present. |

### 5xx Server Errors

| Code | Meaning | When |
|---|---|---|
| `500 Internal Server Error` | Unexpected server error. | Bugs; infrastructure failures. |
| `502 Bad Gateway` | Upstream service error. | Sandbox, OAuth provider down. |
| `503 Service Unavailable` | Service temporarily unavailable. | Database down; maintenance mode. |
| `504 Gateway Timeout` | Upstream timeout. | Sandbox execution timeout. |

### Status Code Selection Rules

- **Business rule violations return 422**, not 400. 400 is for malformed input (invalid JSON, missing required field); 422 is for semantically valid input that violates a business rule (e.g., enrolling in a deprecated subject).
- **401 vs 403**: 401 = "who are you?" (no/invalid auth); 403 = "I know who you are, but you can't do this."
- **404 vs 403**: when a user requests a resource they don't own, we return 404 (not 403) to avoid leaking existence. Authorization checks happen before existence checks only for resources the user could plausibly know about.

---

## 5. Idempotent Operations

- `GET`, `HEAD`, `OPTIONS` are inherently idempotent.
- `PUT`, `DELETE` are idempotent (repeating produces the same state).
- `POST` is not inherently idempotent; clients provide an `Idempotency-Key` header for write operations that may be retried (per `08-idempotency.md`).
- `PATCH` is not idempotent in general (depends on the patch format); we use JSON Patch (RFC 6902) which is idempotent for most operations.

---

## 6. Consistent Naming

- Resource names match Task 002's ubiquitous language (e.g., `study-sessions`, not `sessions` or `practice`).
- Field names match Task 004's column names (e.g., `mastery_score_combined`, not `score` or `mastery`).
- Error codes are SCREAMING_SNAKE_CASE (e.g., `EMAIL_ALREADY_REGISTERED`).
- Enum values are snake_case (e.g., `concept_state: "mastered"`).

---

## 7. HTTP Methods and Operations

| Method | Operation | Idempotent | Safe | Cacheable |
|---|---|---|---|---|
| `GET` | Read | Yes | Yes | Yes |
| `POST` | Create / Action | No (without key) | No | No |
| `PUT` | Full replace | Yes | No | No |
| `PATCH` | Partial update | No (generally) | No | No |
| `DELETE` | Remove | Yes | No | No |
| `HEAD` | Read headers | Yes | Yes | Yes |
| `OPTIONS` | CORS preflight | Yes | Yes | No |

---

## 8. Content Negotiation

- **Request**: clients send `Accept: application/json` (the only supported format).
- **Response**: server returns `Content-Type: application/json`.
- **Versioning**: via URI prefix (`/api/v1/`), not via `Accept` header (per `07-versioning.md`).
- **Future formats**: if we add other formats (e.g., Protocol Buffers for gRPC), they will be served at a different path or via content negotiation in a future API version.

---

*End of API Principles.*
