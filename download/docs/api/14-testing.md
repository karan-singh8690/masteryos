# 14 — Testing

> Contract testing, schema validation, mock server generation, consumer-driven contracts, backward compatibility tests.

---

## 1. Contract Testing

The OpenAPI spec is the contract. Contract tests verify that the backend implementation matches the spec.

### Tools

- **Schemathesis**: property-based testing of the API against the OpenAPI spec (Python).
- **Dredd**: API contract testing against the spec.
- **Postman / Newman**: API testing with spec-generated collections.

### What's Tested

- Every endpoint returns the documented status codes.
- Request validation matches the spec (invalid requests are rejected).
- Response schemas match the spec (field names, types, nullability).
- Error responses match the error model.

### CI Integration

Contract tests run on every PR; a failing contract test blocks the merge.

---

## 2. Schema Validation

### Request Validation

The backend (FastAPI + Pydantic) validates requests against the spec at runtime. A request that doesn't match the spec is rejected with `422 VALIDATION_ERROR`.

### Response Validation

The backend validates responses against the spec in testing (not in production, for performance). A response that doesn't match the spec fails the test.

### Tools

- **Pydantic** (backend): runtime request validation.
- **openapi-core** (Python): response validation in tests.
- **@anatine/zod-openapi** (TypeScript): spec validation in frontend tests.

---

## 3. Mock Server Generation

A mock server is generated from the OpenAPI spec for frontend development and testing.

### Tools

- **Prism**: mock server from OpenAPI spec; validates requests; returns example responses.
- **MSW (Mock Service Worker)**: frontend mocking; integrates with the generated TypeScript client.

### Usage

- Frontend engineers build against the mock server before the backend is implemented (per ADR-0014).
- Integration tests use the mock server for deterministic testing.
- The mock server returns the examples from the spec (per `12-examples.md`).

---

## 4. Consumer-Driven Contracts

In the future (when there are multiple API consumers — frontend, mobile, partners), consumer-driven contract testing ensures the API doesn't break consumers.

### Tools

- **Pact**: consumer-driven contract testing.

### Process

1. Each consumer (frontend, mobile, partner SDK) writes a Pact test specifying the interactions it expects.
2. The consumer tests produce a contract (Pact file).
3. The backend verifies against the consumer contracts (Pact verification).
4. A backend change that breaks a consumer contract fails the verification.

### Current Status

Consumer-driven contracts are a future addition (when there are multiple consumers); for now, the OpenAPI spec + contract tests suffice.

---

## 5. Backward Compatibility Tests

### Schema Backward Compatibility

Every change to the OpenAPI spec is checked for backward compatibility:
- Adding fields: compatible.
- Removing fields: breaking (requires version bump).
- Changing types: breaking.

### Tools

- **oasdiff**: OpenAPI diff tool; detects breaking changes.
- **openapi-diff**: similar.

### CI Integration

On every PR that changes the spec, `oasdiff` runs; a breaking change fails the PR unless the version is bumped.

---

## 6. Test Pyramid

### Unit Tests (Backend)

- Domain services: pure-function tests (fast).
- Use case services: tests with fake repositories.

### Integration Tests (Backend)

- Repository tests against a real PostgreSQL (Docker container).
- API tests against a real FastAPI instance + test database.

### Contract Tests

- Backend ↔ spec (per above).

### End-to-End Tests

- Playwright tests covering critical user journeys (signup, study session, content publish).
- Run against a full deployment in CI.

### Load Tests

- The learning loop (`POST /attempts`) is load-tested to verify the 200ms median latency target.
- Nightly against staging.

---

## 7. Test Data

- **Fixtures**: deterministic test data (users, subjects, concepts) loaded before tests.
- **Factories**: test data factories for creating entities on demand.
- **Cleanup**: tests clean up after themselves (or use a fresh database per test run).

---

## 8. Test Environments

- **Local**: Docker Compose with PostgreSQL, Redis, the API, and the frontend.
- **CI**: ephemeral containers per test run.
- **Staging**: full deployment; used for E2E and load tests.

---

*End of Testing.*
