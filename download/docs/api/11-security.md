# 11 — Security

> OWASP API security alignment, authorization, mass assignment prevention, object-level authorization, input validation, sensitive field handling, audit logging, CORS, CSRF.

---

## 1. OWASP API Security Top 10 Alignment

The API aligns with the OWASP API Security Top 10 (2023):

| Risk | Mitigation |
|---|---|
| API1: Broken Object Level Authorization | Object-level authorization on every endpoint (see below). |
| API2: Broken Authentication | JWT with short-lived access tokens; refresh token rotation; MFA; OAuth. |
| API3: Broken Object Property Level Authorization | Mass assignment prevention; field-level authorization; explicit allowlists. |
| API4: Resource Exhaustion | Rate limiting (per `10-rate-limiting.md`); pagination max 100. |
| API5: Broken Function Level Authorization | Role-based authorization at controller + use case layers. |
| API6: Unlimited Access to Sensitive Data Flows | Sensitive fields (PII) encrypted; field selection restricted for sensitive endpoints. |
| API7: SSRF | No user-supplied URLs are fetched by the server (except OAuth callbacks, which are validated). |
| API8: Security Misconfiguration | HTTPS enforced; HSTS; security headers; no default credentials. |
| API9: Inventory Management Issues | All endpoints documented in OpenAPI; no undocumented endpoints in production. |
| API10: Unsafe API Consumption | Outbound calls (OAuth, Stripe) use TLS; response validation. |

---

## 2. Authorization

### Role-Based Access Control (RBAC)

Roles (per Task 002): `learner`, `instructor`, `administrator`, `mentor` (future).

Each endpoint declares its required role(s) in the OpenAPI spec (via `x-required-role` extension). The controller enforces the role check.

### Object-Level Authorization

Every endpoint that accesses a specific resource (e.g., `GET /enrollments/{id}`) checks that the requesting user owns or is authorized to access that resource.

- **Own data**: learners can only access their own enrollments, attempts, mastery scores, etc.
- **Subject-scoped**: instructors can only author/review content for subjects where they have the Instructor role.
- **Platform-wide**: administrators can access all resources.

Authorization is enforced at two layers (per ASD Section 12.2):
1. **Controller**: role check (`require_role("instructor")`).
2. **Use case**: resource ownership check (`enrollment.user_id == current_user.id`).

---

## 3. Mass Assignment Prevention

Request bodies are bound to explicit DTOs (Pydantic models), not to domain aggregates directly. Only fields explicitly declared in the DTO are accepted; extra fields are rejected.

**Example**: `UpdateProfileRequest` allows `display_name`, `timezone`, `locale`, `avatar_url`, `preferences`. A client sending `{ "is_admin": true }` gets `422 VALIDATION_ERROR` (the `is_admin` field is not in the DTO).

---

## 4. Input Validation

- **Pydantic validation** at the API boundary: type, length, range, format.
- **Domain validation** in the use case layer: business rules (e.g., "cannot enroll in a deprecated subject").
- **Reject unknown fields**: the request body must match the DTO exactly; extra fields are rejected (not silently ignored).
- **SQL injection prevention**: parameterized queries everywhere; no string concatenation of SQL.

---

## 5. Sensitive Field Handling

### PII Encryption

PII fields (email, display_name, MFA secret) are encrypted at rest (per Task 004 `13-security.md`).

### Field Selection Restrictions

The `fields` parameter cannot select sensitive fields on other users' resources. A learner cannot `GET /admin/users?fields=email` (admin-only endpoint).

### Response Filtering

Responses are filtered by role: admin responses include more fields than learner responses (e.g., admin sees `email_verified_at`; learner sees only their own).

---

## 6. Audit Logging

Every privileged action is recorded in `audit_logs` (per Task 005):
- Content publish, deprecate, archive.
- User suspend, reactivate, anonymize.
- Role grant, revoke.
- Feature flag, system setting changes.
- GDPR request processing.
- Schema migrations.
- Payment refunds.

Audit log entries include: actor, action, target, metadata, IP, user agent, correlation ID, outcome.

---

## 7. CORS

### Allowed Origins

- **Production**: `https://app.masteryengine.com`, `https://admin.masteryengine.com`.
- **Staging**: `https://staging-app.masteryengine.com`.
- **Local development**: `http://localhost:3000`.

### Headers

```
Access-Control-Allow-Origin: <allowed origin>
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type, Idempotency-Key, X-Correlation-Id
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 600
```

`Allow-Credentials: true` is required for the refresh token cookie.

### Preflight

`OPTIONS` requests are handled by the CORS middleware; they do not reach the application logic.

---

## 8. CSRF Strategy

### Risk

The refresh token is in a cookie; CSRF could trigger a refresh, minting a new access token for the attacker. However, the attacker cannot read the access token (it's in JavaScript memory, and CORS prevents cross-origin reads).

### Mitigation

- **SameSite=Lax** on the refresh token cookie: prevents cross-site POST (the most common CSRF vector).
- **Refresh endpoint requires a custom header** (`X-Requested-With` or similar) that cannot be set by a cross-origin form submission.
- **Access token in JavaScript memory**: not in a cookie, so CSRF cannot steal it.

### What's Not at Risk

- `GET` requests are idempotent (no state change).
- `POST/PUT/PATCH/DELETE` use `Authorization: Bearer` (not cookies) for the access token; CSRF cannot set the `Authorization` header cross-origin.

---

## 9. Security Headers

| Header | Value | Purpose |
|---|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | HSTS; force HTTPS. |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing. |
| `X-Frame-Options` | `DENY` | Prevent clickjacking. |
| `Content-Security-Policy` | `default-src 'none'` (API; no content) | Prevent XSS (API returns JSON only). |
| `Cache-Control` | `no-store` for authenticated responses | Prevent caching of sensitive data. |
| `X-Correlation-Id` | UUID | Request tracing. |

---

## 10. SQL Injection Prevention

- **Parameterized queries** everywhere (asyncpg, SQLAlchemy).
- **No dynamic SQL** from user input.
- **ORM usage**: SQLAlchemy's query builder prevents injection.
- **Input validation** at the API boundary rejects malformed input before it reaches the database.

---

## 11. Secrets Management

- **No secrets in code or config files**: secrets are in the secrets manager (per ASD Section 12.6).
- **JWT signing keys**: KMS-managed; rotated quarterly.
- **OAuth client secrets**: in the secrets manager.
- **Database credentials**: in the secrets manager; fetched at startup.
- **Stripe API keys**: in the secrets manager.

---

*End of Security.*
