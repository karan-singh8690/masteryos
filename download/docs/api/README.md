# Mastery Engine — OpenAPI 3.1 API Contract

> **Status:** v1.0 — Authoritative API contract for the Mastery Engine.
> **Owner:** Principal API Architect
> **Audience:** Backend engineers, frontend engineers, SDK authors, QA, partner integrators.
> **Companion documents:**
> - Architecture Specification (Task 001)
> - Ubiquitous Language (Task 002)
> - ADR Repository (Task 003)
> - PostgreSQL Database Architecture (Task 004)
> - Domain Behavior (Task 005)

---

## What This Document Set Is

This is the **complete API contract** for the Mastery Engine. The contract is the single source of truth for the API surface: every endpoint, every schema, every error code, every authentication requirement. Backend engineers implement to it; frontend engineers build against it; SDK authors generate from it; QA tests against it; mock servers are generated from it.

The API is a **contract, not an implementation**. This document set does not contain FastAPI code, business logic, or controllers — only the specification. The authoritative OpenAPI 3.1 YAML is `03-openapi-spec.yaml`; the markdown documents provide context, principles, and guidelines that the YAML alone cannot express.

---

## Conflict Reconciliations with the Brief

Three reconciliations were made against Task 002's ubiquitous language (documented in the relevant files):

1. **Milestones** — modeled as a query filter on the Achievements resource (`GET /achievements?category=milestone`), not as a separate resource. A Milestone is a type of Achievement (per Task 002).
2. **Billing** — decomposed into Subscriptions and Invoices (both in the brief's list). No separate "Billing" resource to avoid duplication.
3. **Tenants** — exposed only via admin endpoints, not learner-facing. Learners interact with Subjects; Tenants are a content-isolation unit (per Task 002).

---

## Document Index

| File | Topic |
|---|---|
| `01-api-principles.md` | REST principles, resource-oriented design, naming, JSON conventions, HTTP status codes. |
| `02-resource-model.md` | Every API resource: purpose, ownership, relationships, operations, authorization. |
| `03-openapi-spec.yaml` | The complete OpenAPI 3.1 specification (the authoritative contract). |
| `04-authentication.md` | JWT flow, refresh tokens, OAuth, MFA, session management. |
| `05-error-model.md` | Standard error object, error codes, correlation IDs. |
| `06-pagination-filtering.md` | Cursor pagination, sorting, filtering, field selection, expansion. |
| `07-versioning.md` | URI versioning, deprecation, sunset, backward compatibility. |
| `08-idempotency.md` | Idempotency-Key header, replay, duplicate handling. |
| `09-webhooks.md` | Webhook contracts, signing, verification, retry. |
| `10-rate-limiting.md` | Per-user, per-IP, per-tenant limits; burst; Retry-After. |
| `11-security.md` | OWASP API security, authorization, mass assignment, CORS, CSRF. |
| `12-examples.md` | Complete example requests/responses for major workflows. |
| `13-sdk-guidelines.md` | SDK generation conventions for TypeScript, Python, Kotlin, Swift. |
| `14-testing.md` | Contract testing, schema validation, mock servers, consumer-driven contracts. |
| `15-future-evolution.md` | GraphQL, gRPC, streaming, SSE, real-time, offline sync, AI clients. |

---

## API at a Glance

- **Version**: v1 (URI-prefixed `/api/v1/...`).
- **Format**: JSON over HTTPS.
- **Auth**: JWT (access token in `Authorization: Bearer` header; refresh token in HttpOnly cookie).
- **Pagination**: cursor-based (`cursor`, `limit`).
- **Idempotency**: `Idempotency-Key` header for write operations.
- **Errors**: standardized error object with `code`, `message`, `details`, `correlation_id`.
- **Rate limiting**: per-user and per-IP; `429` with `Retry-After`.
- **Webhooks**: HMAC-signed; for partner integrations and internal event-driven consumers.

---

## Conformance to Authoritative Documents

| Source | Conformance |
|---|---|
| Task 002 (Ubiquitous Language) | Resource and field names use the glossary's terms (e.g., `study_sessions`, `mastery_scores`, `question_instances`). |
| Task 004 (Database) | Schemas align with the 57 tables; fields match columns. |
| Task 005 (Domain Behavior) | Every Command maps to a POST/PUT/DELETE/PATCH endpoint; every Query maps to a GET endpoint. |
| ADR-0013 (JWT Auth) | Auth flow, token lifecycle, refresh rotation. |
| ADR-0014 (API-first) | OpenAPI is the source of truth; frontend client is generated from it. |

---

## How to Use This Document Set

- **Implementing the backend**: start with `03-openapi-spec.yaml`; implement each endpoint per its schema; consult `04-authentication.md` and `05-error-model.md` for cross-cutting concerns.
- **Building the frontend**: generate the API client from `03-openapi-spec.yaml` (per `13-sdk-guidelines.md`); consult `12-examples.md` for workflow examples.
- **Testing**: consult `14-testing.md` for contract testing strategy; use the spec to generate mock servers.
- **Integrating via webhooks**: consult `09-webhooks.md` for webhook contracts and signing.
- **Evolving the API**: consult `07-versioning.md` for versioning and deprecation; consult `15-future-evolution.md` for future API paradigms.

---

*End of API Contract README.*
