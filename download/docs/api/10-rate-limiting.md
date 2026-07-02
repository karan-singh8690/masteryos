# 10 — Rate Limiting

> Per-user, per-IP, per-tenant limits; burst; admin exemptions; Retry-After.

---

## 1. Rate Limiting Strategy

Rate limiting is enforced at the API gateway / middleware layer, keyed by:
- **User ID** (for authenticated requests).
- **IP address** (for unauthenticated requests).

Limits are per-endpoint and per-window, stored in Redis for low-latency increment and global consistency.

---

## 2. Limit Tiers

### Authentication Endpoints (unauthenticated, IP-keyed)

| Endpoint | Limit | Window | Rationale |
|---|---|---|---|
| `/auth/login` | 10 | per minute | Prevent credential stuffing. |
| `/auth/register` | 5 | per minute | Prevent account creation abuse. |
| `/auth/password-reset/request` | 3 | per minute | Prevent email enumeration. |
| `/auth/oauth/*` | 10 | per minute | Prevent OAuth abuse. |

### Authenticated Endpoints (user-keyed)

| Endpoint Category | Limit | Window | Rationale |
|---|---|---|---|
| Read endpoints (`GET`) | 1000 | per minute | Generous; cost control. |
| `POST /attempts` | 100 | per minute | Prevent abuse; realistic max ~1/sec. |
| `POST /study-sessions` | 10 | per minute | Realistic max. |
| `POST /question-instances/{id}/execute-code` | 30 | per minute | Sandbox cost control. |
| Other write endpoints | 60 | per minute | General write limit. |

### Admin Endpoints (user-keyed)

| Endpoint Category | Limit | Window |
|---|---|---|
| Admin reads | 100 | per minute |
| Admin writes | 30 | per minute |

---

## 3. Burst Handling

Rate limits use a **token bucket** algorithm: the bucket refills at the steady-state rate but can burst up to 2x the steady-state rate for short periods.

Example: `100/minute` allows a burst of 200 requests in the first second, then 100 per minute sustained.

---

## 4. Response When Rate Limited

```
HTTP/1.1 429 Too Many Requests
Retry-After: 30
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1719900930

{
  "code": "RATE_LIMITED",
  "message": "Rate limit exceeded. Retry after 30 seconds.",
  "correlation_id": "...",
  "retry_after": 30
}
```

### Headers

| Header | Description |
|---|---|
| `Retry-After` | Seconds to wait before retrying. |
| `X-RateLimit-Limit` | The limit (per window). |
| `X-RateLimit-Remaining` | Remaining requests in the current window. |
| `X-RateLimit-Reset` | Unix timestamp when the window resets. |

---

## 5. Admin Exemptions

Administrator accounts have higher limits (2x normal) for operational needs. Engineers can request temporary exemptions via the admin portal for testing or migration purposes.

---

## 6. Per-Tenant Limits (future)

For B2B organizations, per-tenant limits may be configured (e.g., an org with 1000 members gets a pooled limit). This is a future feature (Phase 5+).

---

## 7. Best Practices for Clients

1. **Respect `Retry-After`**: wait the indicated seconds before retrying.
2. **Exponential backoff with jitter**: for 429 responses, use exponential backoff to avoid thundering herd.
3. **Cache responses**: use `ETag` / `If-None-Match` to avoid re-fetching unchanged data.
4. **Batch where possible**: future batch endpoints will reduce request count.
5. **Monitor `X-RateLimit-Remaining`**: clients approaching the limit should throttle proactively.

---

*End of Rate Limiting.*
