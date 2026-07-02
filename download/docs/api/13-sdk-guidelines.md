# 13 — SDK Guidelines

> Conventions for future SDK generation: TypeScript, Python, Kotlin, Swift.

---

## 1. SDK Generation Strategy

SDKs are **generated** from the OpenAPI spec (`03-openapi-spec.yaml`), not hand-written. This ensures the SDK always matches the API contract. Generation tools:

- **TypeScript**: `openapi-typescript` (types) + `orval` (client) or `openapi-fetch`.
- **Python**: `openapi-python-client` or `datamodel-code-generator` (Pydantic models).
- **Kotlin**: `openapi-generator` (Kotlin client).
- **Swift**: `openapi-generator` (Swift client).

---

## 2. Naming Conventions

The OpenAPI spec uses `snake_case` for fields (matching Task 002 and Task 004). SDKs preserve this convention:

- **TypeScript**: `snake_case` for fields (consistent with the spec). This is unusual for JS/TS (which prefers `camelCase`), but consistency with the API and the backend outweighs local convention. A future option is to configure the generator to convert to `camelCase` for the TS client.
- **Python**: `snake_case` (natural fit).
- **Kotlin**: `snake_case` for fields (matching the spec); class names are `PascalCase`.
- **Swift**: `snake_case` for fields (matching the spec); type names are `PascalCase`.

---

## 3. Error Handling

SDKs expose the standard error object (per `05-error-model.md`) as a typed exception:

### TypeScript

```typescript
try {
  const result = await client.submitAnswer({ ... });
} catch (error) {
  if (error instanceof ApiError) {
    console.log(error.code); // "QUESTION_ALREADY_ANSWERED"
    console.log(error.correlationId);
    console.log(error.details);
  }
}
```

### Python

```python
from mastery_engine import ApiError

try:
    result = client.submit_answer(...)
except ApiError as e:
    print(e.code)  # "QUESTION_ALREADY_ANSWERED"
    print(e.correlation_id)
```

---

## 4. Retries

SDKs retry on:
- Network timeouts.
- `5xx` errors (exponential backoff with jitter).
- `429 RATE_LIMITED` (honor `Retry-After`).

SDKs do **not** retry on:
- `4xx` errors (client must fix the request).

### Retry Configuration

```typescript
const client = new MasteryEngineClient({
  maxRetries: 3,
  retryDelay: (attempt) => Math.pow(2, attempt) * 1000 + Math.random() * 500,
});
```

---

## 5. Pagination

SDKs provide a pagination iterator:

### TypeScript

```typescript
for await (const attempt of client.listAttempts({ enrollment_id: '...' })) {
  console.log(attempt);
}
```

### Python

```python
for attempt in client.list_attempts(enrollment_id='...'):
    print(attempt)
```

The SDK handles cursor management internally; the developer iterates as if it were a normal collection.

---

## 6. Idempotency

SDKs auto-generate `Idempotency-Key` for write operations:

```typescript
const result = await client.submitAnswer(
  { question_instance_id: '...', answer: { ... } },
  { idempotencyKey: crypto.randomUUID() }
);
```

The SDK stores the key with the operation context; retries (via the SDK's retry logic) reuse the key.

---

## 7. Authentication

SDKs handle token refresh automatically:

```typescript
const client = new MasteryEngineClient({
  accessToken: localStorage.getItem('access_token'),
  onTokenRefresh: async () => {
    const response = await fetch('/api/v1/auth/refresh', { method: 'POST', credentials: 'include' });
    const { access_token } = await response.json();
    localStorage.setItem('access_token', access_token);
    return access_token;
  },
});
```

On `401`, the SDK calls `onTokenRefresh`; on success, it retries the original request; on failure, it throws `AuthenticationError`.

---

## 8. Type Safety

Generated SDKs provide full type safety:

```typescript
const attempt: AttemptResult = await client.submitAnswer({ ... });
// TypeScript knows the shape of AttemptResult
```

Schema changes (additive) produce new optional fields; breaking changes produce a new SDK major version.

---

## 9. Versioning

SDK versions align with API versions:
- `mastery-engine-ts@1.x.y` → API v1.
- `mastery-engine-ts@2.x.y` → API v2.

The SDK's major version bumps when the API's major version bumps.

---

## 10. Distribution

- **TypeScript**: npm package `@masteryengine/api-client`.
- **Python**: PyPI package `mastery-engine`.
- **Kotlin**: Maven Central.
- **Swift**: Swift Package Manager.

---

*End of SDK Guidelines.*
