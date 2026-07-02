# 15 — Future Evolution

> How the API evolves to support GraphQL, gRPC, streaming, SSE, real-time collaboration, offline sync, AI-assisted clients, mobile-first optimizations.

---

## 1. GraphQL (Future)

### When

If the frontend's data needs become highly variable (e.g., a customizable dashboard that fetches diverse data shapes), GraphQL's flexible queries may be more efficient than fixed REST endpoints.

### How

- GraphQL served at `/api/v1/graphql` (or `/graphql`).
- The GraphQL schema is generated from the same domain model as the REST API.
- Authentication reuses the JWT.
- REST and GraphQL coexist; clients choose.

### Impact

- New GraphQL schema; REST endpoints unchanged.
- The OpenAPI spec covers REST; a separate GraphQL schema covers GraphQL.
- The underlying domain services and repositories are shared.

---

## 2. gRPC (Future)

### When

If internal service-to-service communication (after microservice extraction) needs high performance, gRPC may replace HTTP/JSON for internal APIs.

### How

- gRPC served at a separate port (e.g., 9090).
- Protocol Buffers schemas define the gRPC contract.
- External clients continue to use REST/JSON; internal services use gRPC.

### Impact

- New Protocol Buffers schemas; REST endpoints unchanged.
- The OpenAPI spec covers the external API; .proto files cover the internal API.
- Code generation from .proto for internal clients.

---

## 3. Streaming (Future)

### When

If the learning loop benefits from streaming (e.g., streaming partial code execution results as they arrive), a streaming endpoint may be added.

### How

- **Server-Sent Events (SSE)**: for one-way streaming (server → client), e.g., real-time mastery updates.
- **WebSocket**: for two-way streaming, e.g., collaborative learning.
- **HTTP/2 streaming**: for large response payloads.

### Impact

- New streaming endpoints (e.g., `GET /enrollments/{id}/mastery-scores/stream` for SSE).
- The OpenAPI spec supports SSE via callbacks; WebSocket is documented separately.

---

## 4. Server-Sent Events (SSE)

### Use Cases

- Real-time mastery score updates (learner sees mastery change immediately after an attempt, without polling).
- Real-time recommendation updates.
- Live dashboard refresh.

### Example

```
GET /api/v1/enrollments/{id}/mastery-scores/stream
Authorization: Bearer eyJ...
Accept: text/event-stream

event: mastery_updated
data: {"concept_id": "...", "mastery_score_combined": 0.85, ...}

event: mastery_updated
data: {"concept_id": "...", "mastery_score_combined": 0.72, ...}
```

### Impact

- New SSE endpoints; REST endpoints unchanged.
- The frontend uses `EventSource` (or a polyfill) to consume.

---

## 5. Real-Time Collaboration (Future)

### When

If collaborative learning (study groups, shared sessions) is added, real-time two-way communication is needed.

### How

- WebSocket for real-time state synchronization.
- The REST API handles non-real-time operations; WebSocket handles real-time.

### Impact

- New WebSocket endpoints (e.g., `/ws/study-groups/{id}`).
- The OpenAPI spec does not cover WebSocket (documented separately).
- New commands and events (per Task 005 `12-future-evolution.md`).

---

## 6. Offline Sync (Future)

### When

If the PWA or native app supports offline learning, the API must support sync.

### How

- New endpoints: `POST /sync/offline-attempts` (batch upload offline attempts), `GET /sync/state` (fetch current state for offline cache).
- The client stores attempts locally; syncs when online.
- Conflict resolution: server reconciles by timestamp (per Task 005 `12-future-evolution.md`).

### Impact

- New sync endpoints; existing endpoints unchanged.
- Idempotency is critical (offline attempts may be uploaded multiple times).

---

## 7. AI-Assisted Clients (Future)

### When

If AI agents (e.g., a learner's AI tutor, or an instructor's AI authoring assistant) consume the API, the API may need agent-specific endpoints.

### How

- AI agents authenticate with scoped tokens (e.g., a learner's agent acts on their behalf).
- New endpoints: `POST /ai-tutor/explain` (request an alternative explanation), `POST /ai-author/draft` (draft a content pack).
- Rate limits are tighter for AI agents (to control cost).

### Impact

- New AI-specific endpoints; existing endpoints unchanged.
- Per ADR-0009, AI is assistive, not authoritative; AI endpoints are clearly labeled.

---

## 8. Mobile-First Optimizations (Future)

### When

If mobile usage dominates, the API may add mobile-specific optimizations.

### How

- **Field selection by default**: mobile clients get smaller payloads by default.
- **Batching**: `POST /batch` endpoint for multiple operations in one request.
- **Compression**: Brotli compression for responses.
- **HTTP/2 or HTTP/3**: multiplexing for multiple requests.

### Impact

- New batch endpoint; existing endpoints unchanged.
- Field selection (per `06-pagination-filtering.md`) is already supported.

---

## 9. API Version 2 (Future)

### When

If enough breaking changes accumulate, v2 is shipped alongside v1.

### How

- `/api/v2/...` runs in parallel with `/api/v1/...`.
- v1 is deprecated with a sunset date (per `07-versioning.md`).
- v2 incorporates lessons learned from v1 (e.g., simplified error model, GraphQL integration).

### Impact

- New OpenAPI spec for v2; v1 spec is frozen.
- The frontend migrates per the deprecation schedule.

---

## 10. Marketplace API (Future)

### When

If the marketplace is added (per Task 005 `12-future-evolution.md`), partner-specific endpoints are added.

### How

- `/api/v1/marketplace/listings`, `/api/v1/marketplace/purchases`.
- Partner authentication (separate from learner auth).
- Revenue share endpoints for authors.

### Impact

- New marketplace endpoints; existing endpoints unchanged.

---

## Closing Note

The API is designed to evolve. The REST/JSON foundation is stable and will serve the platform for years. Future paradigms (GraphQL, gRPC, streaming) are additive — they coexist with REST, not replace it. The OpenAPI spec is the contract that keeps the evolution orderly.

---

*End of Future Evolution.*
