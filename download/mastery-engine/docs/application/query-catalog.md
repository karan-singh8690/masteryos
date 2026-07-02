# Query Catalog

> Every query in the application layer with its handler and response DTO.

---

## Query Pattern

Every read operation is a Query:
1. **Query** (frozen dataclass) — the request parameters.
2. **Query Handler** (class implementing `QueryHandler[Q, R]`) — the reader.
3. **Response DTO** — the read model returned.

Query handlers NEVER modify state. They read from repositories via the Unit of Work, build DTOs, and return them.

---

## Implemented Queries

### Learning Context

| Query | Handler | Response |
|---|---|---|
| `GetDashboardQuery` | `GetDashboardHandler` | `DashboardDTO` |
| `GetMasteryScoresQuery` | `GetMasteryScoresHandler` | `list[MasteryScoreDTO]` |
| `GetAttemptHistoryQuery` | `GetAttemptHistoryHandler` | `list[AttemptDTO]` |
| `GetRecommendationsQuery` | `GetRecommendationsHandler` | `list[RecommendationDTO]` |
| `GetStudySessionQuery` | `GetStudySessionHandler` | `StudySessionDTO` |

### Identity Context (future)

| Query | Handler | Response |
|---|---|---|
| `GetUserQuery` | (future) | `UserWithProfileDTO` |
| `GetUserSessionsQuery` | (future) | `list[SessionDTO]` |
| `SearchUsersQuery` | (future) | `list[UserSummaryDTO]` |

### Content Context (future)

| Query | Handler | Response |
|---|---|---|
| `GetSubjectQuery` | (future) | `SubjectDTO` |
| `GetConceptQuery` | (future) | `ConceptDTO` |
| `SearchConceptsQuery` | (future) | `list[ConceptSummaryDTO]` |

### Mastery Context (future)

| Query | Handler | Response |
|---|---|---|
| `GetMasteryScoreQuery` | (future) | `MasteryScoreDTO` |
| `GetDueReviewsQuery` | (future) | `list[ReviewDTO]` |
| `GetAlgorithmVersionQuery` | (future) | `AlgorithmVersionDTO` |

### Billing Context (future)

| Query | Handler | Response |
|---|---|---|
| `GetSubscriptionQuery` | (future) | `SubscriptionDTO` |
| `GetInvoicesQuery` | (future) | `list[InvoiceDTO]` |
| `GetBillingPlansQuery` | (future) | `list[BillingPlanDTO]` |

### Administration Context (future)

| Query | Handler | Response |
|---|---|---|
| `GetNotificationsQuery` | (future) | `list[NotificationDTO]` |
| `GetAuditLogsQuery` | (future) | `list[AuditLogDTO]` |
| `GetFeatureFlagsQuery` | (future) | `list[FeatureFlagDTO]` |

---

## Query Handler Lifecycle

```
1. Receive query
2. Begin Unit of Work (read-only context)
3. Read from repositories
4. Apply authorization checks
5. Build DTOs (never expose domain entities)
6. Return response
```

No commit needed (read-only). No events collected. No state modified.
