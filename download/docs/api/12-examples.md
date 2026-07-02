# 12 — Examples

> Complete example requests and responses for major workflows.

---

## 1. Registration

### Request

```
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "alex@example.com",
  "password": "SecurePass123!",
  "display_name": "Alex Chen",
  "timezone": "Asia/Kolkata",
  "locale": "en-US"
}
```

### Response (201 Created)

```
HTTP/1.1 201 Created
Location: /api/v1/users/me
Content-Type: application/json

{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "alex@example.com",
    "status": "pending_verification",
    "mfa_enabled": false,
    "email_verified_at": null,
    "created_at": "2026-07-02T14:30:00Z"
  }
}
```

---

## 2. Login

### Request

```
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "alex@example.com",
  "password": "SecurePass123!"
}
```

### Response (200 OK)

```
HTTP/1.1 200 OK
Set-Cookie: refresh_token=abc123...; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth; Max-Age=2592000
Content-Type: application/json

{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "alex@example.com",
    "status": "active",
    "mfa_enabled": false,
    "email_verified_at": "2026-07-02T14:35:00Z",
    "created_at": "2026-07-02T14:30:00Z"
  }
}
```

---

## 3. Enroll in Subject

### Request

```
POST /api/v1/enrollments
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
Idempotency-Key: 6ba7b810-9dad-11d1-80b4-00c04fd430c8
Content-Type: application/json

{
  "subject_id": "00000000-0000-0000-0000-000000000010"
}
```

### Response (201 Created)

```json
{
  "id": "7ba7b810-9dad-11d1-80b4-00c04fd430c9",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "subject_id": "00000000-0000-0000-0000-000000000010",
  "learning_path_id": null,
  "status": "pending_onboarding",
  "enrolled_at": "2026-07-02T14:40:00Z",
  "onboarded_at": null,
  "last_active_at": "2026-07-02T14:40:00Z"
}
```

---

## 4. Start Study Session

### Request

```
POST /api/v1/study-sessions
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
Idempotency-Key: 6ba7b811-9dad-11d1-80b4-00c04fd430c8
Content-Type: application/json

{
  "enrollment_id": "7ba7b810-9dad-11d1-80b4-00c04fd430c9",
  "intent": "drill",
  "target_question_count": 15
}
```

### Response (201 Created)

```json
{
  "id": "8ba7b810-9dad-11d1-80b4-00c04fd430ca",
  "learner_enrollment_id": "7ba7b810-9dad-11d1-80b4-00c04fd430c9",
  "intent": "drill",
  "status": "active",
  "started_at": "2026-07-02T14:45:00Z",
  "ended_at": null,
  "question_count": 0,
  "queue": {
    "study_session_id": "8ba7b810-9dad-11d1-80b4-00c04fd430ca",
    "current_position": 0,
    "questions": [
      {
        "id": "9ba7b810-9dad-11d1-80b4-00c04fd430cb",
        "template_version_id": "aba7b810-9dad-11d1-80b4-00c04fd430cc",
        "rendered_prompt": {
          "type": "multiple_choice",
          "prompt": "What is the average-case time complexity of a dict lookup in Python?",
          "choices": ["O(1)", "O(log n)", "O(n)", "O(n log n)"]
        },
        "rendered_choices": null,
        "served_at": "2026-07-02T14:45:00Z",
        "status": "served"
      }
    ]
  }
}
```

---

## 5. Submit Answer

### Request

```
POST /api/v1/attempts
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
Idempotency-Key: 6ba7b812-9dad-11d1-80b4-00c04fd430c8
Content-Type: application/json

{
  "question_instance_id": "9ba7b810-9dad-11d1-80b4-00c04fd430cb",
  "answer": {
    "answer_type": "multiple_choice",
    "submitted_answer": { "choice": "O(1)" }
  }
}
```

### Response (201 Created)

```json
{
  "attempt_id": "bba7b810-9dad-11d1-80b4-00c04fd430cd",
  "scoring_outcome": "correct",
  "partial_credit": null,
  "explanation": {
    "content": "Correct! Average-case dict lookup is O(1) because Python dicts use a hash table. Worst-case is O(n) when there are hash collisions, but this is rare with a good hash function.",
    "outcome_key": "correct"
  },
  "next_question": {
    "id": "cba7b810-9dad-11d1-80b4-00c04fd430ce",
    "template_version_id": "dba7b810-9dad-11d1-80b4-00c04fd430cf",
    "rendered_prompt": {
      "type": "multiple_choice",
      "prompt": "What happens when you reassign an element of a list in Python?",
      "choices": ["A new list is created", "The original list is modified in place", "An error is raised", "The element is removed"]
    },
    "served_at": "2026-07-02T14:45:05Z",
    "status": "served"
  },
  "updated_mastery": {
    "id": "eba7b810-9dad-11d1-80b4-00c04fd430d0",
    "learner_enrollment_id": "7ba7b810-9dad-11d1-80b4-00c04fd430c9",
    "concept_id": "fba7b810-9dad-11d1-80b4-00c04fd430d1",
    "memory_score": 0.92,
    "durable_mastery_score": 0.45,
    "mastery_score_combined": 0.62,
    "confidence_interval": 0.15,
    "evidence_count": 1,
    "concept_state": "novice",
    "weakness_severity": "none",
    "last_attempt_at": "2026-07-02T14:45:05Z",
    "last_updated_at": "2026-07-02T14:45:05Z"
  }
}
```

---

## 6. View Mastery

### Request

```
GET /api/v1/enrollments/7ba7b810-9dad-11d1-80b4-00c04fd430c9/mastery-scores?weak_only=true
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

### Response (200 OK)

```json
[
  {
    "id": "eba7b810-9dad-11d1-80b4-00c04fd430d0",
    "learner_enrollment_id": "7ba7b810-9dad-11d1-80b4-00c04fd430c9",
    "concept_id": "fba7b810-9dad-11d1-80b4-00c04fd430d1",
    "memory_score": 0.30,
    "durable_mastery_score": 0.25,
    "mastery_score_combined": 0.27,
    "confidence_interval": 0.20,
    "evidence_count": 2,
    "concept_state": "novice",
    "weakness_severity": "moderate",
    "last_attempt_at": "2026-07-01T10:00:00Z",
    "last_updated_at": "2026-07-01T10:00:00Z"
  }
]
```

---

## 7. End Session (Review)

### Request

```
POST /api/v1/study-sessions/8ba7b810-9dad-11d1-80b4-00c04fd430ca/end
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
Idempotency-Key: 6ba7b813-9dad-11d1-80b4-00c04fd430c8
```

### Response (200 OK)

```json
{
  "study_session_id": "8ba7b810-9dad-11d1-80b4-00c04fd430ca",
  "question_count": 15,
  "success_rate": 0.80,
  "mastery_delta": 0.08,
  "duration_seconds": 1200,
  "concepts_covered": [
    "fba7b810-9dad-11d1-80b4-00c04fd430d1",
    "fca7b810-9dad-11d1-80b4-00c04fd430d2"
  ]
}
```

---

## 8. Content Publication (Admin)

### Submit Content Pack

```
POST /api/v1/admin/content-packs
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
Idempotency-Key: 6ba7b814-9dad-11d1-80b4-00c04fd430c8
Content-Type: application/json

{
  "subject_id": "00000000-0000-0000-0000-000000000010",
  "name": "Python Data Structures Pack v2",
  "description": "Revised list and dict concepts with new misconceptions.",
  "artifact_ids": {
    "concepts": ["con-1", "con-2"],
    "learning_objectives": ["obj-1", "obj-2", "obj-3"],
    "misconceptions": ["mis-1", "mis-2"],
    "question_templates": ["tpl-1", "tpl-2", "tpl-3"]
  }
}
```

### Response (201 Created)

```json
{
  "id": "pack-1",
  "status": "peer_review",
  "submitted_at": "2026-07-02T15:00:00Z"
}
```

### Approve (QA stage, final)

```
POST /api/v1/admin/content-packs/pack-1/approve
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
Content-Type: application/json

{
  "stage": "qa",
  "decision": "approve",
  "notes": "Discrimination looks good; pilot showed clear separation."
}
```

### Response (200 OK)

```json
{
  "id": "pack-1",
  "status": "published",
  "content_version_id": "cv-3",
  "published_at": "2026-07-02T16:00:00Z"
}
```

---

## 9. Admin Operation (Suspend User)

### Request

```
POST /api/v1/admin/users/550e8400-e29b-41d4-a716-446655440000/suspend
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
Idempotency-Key: 6ba7b815-9dad-11d1-80b4-00c04fd430c8
Content-Type: application/json

{
  "reason": "Rate limit abuse after multiple warnings."
}
```

### Response (200 OK)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "alex@example.com",
  "status": "suspended",
  "mfa_enabled": false,
  "email_verified_at": "2026-07-02T14:35:00Z",
  "created_at": "2026-07-02T14:30:00Z"
}
```

---

## 10. Error Response Example

### Request (duplicate email)

```
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "alex@example.com",
  "password": "SecurePass123!",
  "display_name": "Alex Chen"
}
```

### Response (409 Conflict)

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
  "doc_url": "https://docs.masteryengine.com/api/errors/EMAIL_ALREADY_REGISTERED"
}
```

---

*End of Examples.*
