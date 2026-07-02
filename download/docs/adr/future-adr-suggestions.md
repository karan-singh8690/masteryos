# Future ADR Suggestions

> **Purpose:** Anticipated decisions that the team expects to make as the system scales. These are not commitments; they are forward-looking topics that will likely warrant ADRs when the time comes.
> **Companion:** README.md (ADR process), individual ADRs (current decisions).

---

## How to Use This Document

This document lists 30 future ADR topics, grouped by theme. Each topic includes a brief rationale explaining why the decision is anticipated and a trigger condition indicating when the ADR should be written. When a trigger fires, the architecture review group proposes the ADR; until then, these topics are tracked but not acted upon.

The list is not exhaustive. New topics will emerge as the system evolves; this document is updated whenever a new anticipated decision is identified.

---

## Infrastructure and Operations (10 topics)

### F-001 — Redis Adoption for Caching and Rate Limiting

- **Rationale:** ASD Section 13.2 specifies layered caching (content, mastery, queue, HTTP) and ASD Section 12.3 specifies rate-limit counters in Redis. The initial implementation may use in-process caching and database-backed rate limiting, but as traffic grows, Redis becomes necessary for low-latency cache and global rate-limit consistency.
- **Trigger:** Cache hit rate falls below 80% with in-process caching, or rate-limit counters become a database bottleneck.
- **Expected ADR:** Redis as the cache and rate-limit store; key naming conventions; eviction policies; high-availability strategy.

### F-002 — Docker Containerization Strategy

- **Rationale:** ASD Section 1.5 specifies Docker for deployment. The containerization strategy (base images, multi-stage builds, image scanning, registry) needs formalization before production deployment.
- **Trigger:** Before the first production deployment (Phase 1 exit).
- **Expected ADR:** Base image choice, multi-stage build conventions, image scanning tooling, registry selection, image retention policy.

### F-003 — Kubernetes Migration

- **Rationale:** ASD Section 13.1 describes horizontal scaling behind a load balancer. Initially, this can be a simple container orchestration (Docker Compose, ECS, or a single Kubernetes cluster). As the system scales and the team's operational maturity grows, Kubernetes may become the deployment platform.
- **Trigger:** The team operates more than 5 distinct services or requires advanced orchestration (canary deployments, pod autoscaling, multi-region failover).
- **Expected ADR:** Kubernetes as the deployment platform; cluster topology; ingress; service mesh; GitOps workflow.

### F-004 — Search Engine Adoption (Elasticsearch / OpenSearch)

- **Rationale:** ASD Section 13.6 specifies that search initially uses PostgreSQL full-text search, with migration to a dedicated search engine when the catalog grows or latency exceeds 200ms at p99.
- **Trigger:** Content catalog exceeds 10,000 items, or search latency exceeds 200ms at p99.
- **Expected ADR:** Search engine selection (Elasticsearch, OpenSearch, or a managed equivalent); index schema; CDC pipeline from PostgreSQL; query patterns; multi-tenancy.

### F-005 — Analytics Warehouse (Columnar Database)

- **Rationale:** ASD Section 13.7 specifies a derived analytics store (BigQuery, Redshift, ClickHouse) for aggregate analytics, fed by CDC from PostgreSQL.
- **Trigger:** Aggregate analytics queries on the operational database exceed 1s at p99, or analytics load begins to affect the learning loop.
- **Expected ADR:** Warehouse selection; CDC pipeline tooling (Debezium, Fivetran); schema; query patterns; data retention; cost management.

### F-006 — CDN Strategy

- **Rationale:** ASD Section 9.11 specifies a performance budget with CDN for static assets. The CDN choice (Cloudflare, CloudFront, Fastly) and configuration (caching rules, origin shielding, edge functions) need formalization.
- **Trigger:** Before the first production deployment (Phase 1 exit), or when static asset latency becomes a user-experience issue in remote regions.
- **Expected ADR:** CDN selection; caching rules; origin configuration; edge function usage; cost management; cache invalidation strategy.

### F-007 — Backup Policy and Verification

- **Rationale:** ASD Section 17.5 specifies RTO of 4 hours and RPO of 15 minutes; ASD Section 17.10 specifies backup verification. The backup policy (frequency, retention, encryption, verification drills) needs formalization.
- **Trigger:** Before the first production deployment (Phase 1 exit).
- **Expected ADR:** Backup frequency and retention; encryption; verification drills (daily integrity, weekly full-restore, quarterly cross-region); restore procedures; documentation.

### F-008 — Disaster Recovery Plan

- **Rationale:** ASD Section 17.5 specifies a disaster recovery plan with RTO 4 hours, RPO 15 minutes, quarterly drills, and incident command structure.
- **Trigger:** Before the first production deployment (Phase 1 exit).
- **Expected ADR:** DR architecture (single-region with warm standby vs. multi-region active-passive); failover procedures; DNS and traffic management; data restoration; incident command; communication plan; drill schedule.

### F-009 — Encryption at Rest

- **Rationale:** ASD Section 12.7 specifies encryption at rest for the database, cache, and object storage, with field-level encryption for PII via envelope encryption with KMS-managed keys.
- **Trigger:** Before the first production deployment (Phase 1 exit), or when compliance requirements (GDPR, SOC 2) demand it.
- **Expected ADR:** Encryption strategy (database-level, field-level); KMS choice (AWS KMS, GCP KMS, HashiCorp Vault); key rotation; envelope encryption implementation; compliance mapping.

### F-010 — Secrets Management

- **Rationale:** ASD Section 12.6 specifies that secrets are stored in a secrets manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault) in production, fetched at startup.
- **Trigger:** Before the first production deployment (Phase 1 exit).
- **Expected ADR:** Secrets manager selection; secret hierarchy; access policies; rotation schedule; local development strategy (.env files); CI/CD integration.

---

## Architecture and Patterns (8 topics)

### F-011 — Feature Flag System

- **Rationale:** ASD Section 17.3 recommends a feature flag system as a Phase 1 requirement. The system (Redis-backed or a managed service like LaunchDarkly) and the flag lifecycle need formalization.
- **Trigger:** Before the first production deployment (Phase 1 exit), to enable safe rollout of the Mastery Engine v2 and Scheduler variants.
- **Expected ADR:** Feature flag system selection; flag lifecycle (created, active, retired); targeting rules; analytics; kill-switch patterns; A/B testing integration.

### F-012 — Background Job Framework

- **Rationale:** ASD Section 13.4 specifies background jobs for notifications, analytics projections, mastery recompute, content quality monitoring, and backups. The framework (Celery, RQ, Dramatiq, or a custom PostgreSQL-based queue) needs selection.
- **Trigger:** Before the first background job is implemented (Phase 1, for the outbox dispatcher).
- **Expected ADR:** Job framework selection; queue backends (PostgreSQL, Redis Streams); retry and dead-letter policies; worker scaling; observability; idempotency enforcement.

### F-013 — Observability Stack

- **Rationale:** ASD Section 17.1 recommends observability as a first-class concern: structured logging, metrics (Prometheus), distributed tracing (OpenTelemetry), error tracking (Sentry). The stack selection and instrumentation strategy need formalization.
- **Trigger:** Before the first production deployment (Phase 1 exit).
- **Expected ADR:** Logging stack (structured logging, log aggregation); metrics (Prometheus, Grafana); tracing (OpenTelemetry, Jaeger); error tracking (Sentry); PII scrubbing; correlation IDs; retention.

### F-014 — CI/CD Pipeline

- **Rationale:** ASD Section 14.7 specifies CI checks (lint, type, unit, integration, contract, e2e, build) and PR requirements. The CI/CD platform (GitHub Actions, GitLab CI, CircleCI) and pipeline structure need formalization.
- **Trigger:** Before the first production deployment (Phase 1 exit).
- **Expected ADR:** CI/CD platform; pipeline stages; environment promotion (dev, staging, production); deployment strategies (blue-green, canary); rollback procedures; secret management in CI.

### F-015 — Code Execution Sandbox

- **Rationale:** ASD Section 12.9 specifies a sandbox for code-execution questions (essential for Python interview prep). The sandbox implementation (gVisor, Firecracker, nsjail, or a managed service) and isolation strategy need formalization.
- **Trigger:** Phase 2, when CodingExercise questions are implemented.
- **Expected ADR:** Sandbox technology selection; isolation strategy; resource limits (CPU, memory, time, network); image hardening; separate node pool; cost management; security review process.

### F-016 — Multi-Region Deployment

- **Rationale:** ASD Section 13.9 specifies that multi-region deployment is triggered by latency or regulatory requirements. The architecture (active-passive with remote read replicas, or active-active) needs formalization when triggered.
- **Trigger:** A user base concentrated in a region far from the primary, or a regulatory requirement (e.g., EU data residency) that single-region cannot meet.
- **Expected ADR:** Multi-region architecture (active-passive vs. active-active); database replication; traffic routing (geo-DNS, anycast); failover procedures; data residency compliance; cost.

### F-017 — Microservices Extraction (first context)

- **Rationale:** ADR-0001 defines triggers for extracting a bounded context to a microservice. The first extraction (likely the Sandbox or the Mastery Engine) needs a formal ADR.
- **Trigger:** Any trigger in ADR-0001's Future Review Trigger fires.
- **Expected ADR:** Which context to extract; the message broker for cross-service events (Kafka, RabbitMQ); the deployment topology; the migration plan; the rollback plan; observability for the extracted service.

### F-018 — Event Sourcing for Specific Contexts

- **Rationale:** ADR-0006 (DDD) mentions that event sourcing may be revisited for specific contexts (e.g., Billing) where strict audit or replay is required.
- **Trigger:** A context's audit or replay requirements exceed what the outbox pattern provides.
- **Expected ADR:** Which context adopts event sourcing; event schema versioning; projection management; snapshotting; migration from the current model; coexistence with non-event-sourced contexts.

---

## Security and Compliance (5 topics)

### F-019 — Rate Limiting Strategy

- **Rationale:** ASD Section 12.3 specifies rate limiting per endpoint and per window. The strategy (token bucket, sliding window, fixed window) and the storage (Redis) need formalization.
- **Trigger:** Before the first production deployment (Phase 1 exit), to protect authentication endpoints.
- **Expected ADR:** Rate-limit algorithm; per-endpoint limits; storage (Redis); response (429 with Retry-After); escalation (temporary account lock); monitoring.

### F-020 — Audit Log Retention and Export

- **Rationale:** ASD Section 12.4 specifies audit log retention of at least 2 years and daily export to cold storage. The retention policy, export mechanism, and SIEM integration need formalization.
- **Trigger:** Before the first production deployment (Phase 1 exit), for compliance.
- **Expected ADR:** Retention period per audit log category; export mechanism (S3, GCS); cold storage tier; SIEM integration (Splunk, Datadog); access controls; legal hold procedures.

### F-021 — GDPR and Data Subject Rights

- **Rationale:** ASD Section 12.8 specifies GDPR compliance including right to access and right to erasure. The implementation (data export, anonymization, consent management) needs formalization.
- **Trigger:** Before the first production deployment (Phase 1 exit), especially if EU users are expected.
- **Expected ADR:** Data export format and delivery; anonymization strategy (Attempt retention with PII stripping); consent management; data residency; breach notification procedures; DPO responsibilities.

### F-022 — Web Application Firewall (WAF) and DDoS Protection

- **Rationale:** The production deployment needs protection against common web attacks (SQL injection, XSS, CSRF) and DDoS. The WAF and DDoS mitigation strategy need selection.
- **Trigger:** Before the first production deployment (Phase 1 exit).
- **Expected ADR:** WAF selection (Cloudflare, AWS WAF, Cloud Armor); rule sets; DDoS protection; bot mitigation; false-positive handling; monitoring.

### F-023 — Penetration Testing and Security Review Cadence

- **Rationale:** The system needs periodic security review (penetration testing, code review, dependency scanning) to maintain security posture over time.
- **Trigger:** Annually, or before major releases, or after significant architecture changes.
- **Expected ADR:** Penetration testing frequency and scope; code review security checklist; dependency scanning (Snyk, Dependabot); vulnerability disclosure program; remediation SLAs.

---

## Data and Analytics (4 topics)

### F-024 — Data Retention Policy

- **Rationale:** ASD Section 17.4 recommends an explicit data retention policy: Attempts (indefinite, anonymized after 24 months), audit logs (7 years), session data (90 days), notification records (30 days).
- **Trigger:** Before the first production deployment (Phase 1 exit), for compliance and cost management.
- **Expected ADR:** Retention period per data category; anonymization strategy; archival mechanism; deletion procedures; legal hold; compliance mapping.

### F-025 — Cost Monitoring and Management

- **Rationale:** ASD Section 17.7 recommends cost monitoring: per-feature cost tagging, monthly cost review, cost ceilings, sandbox cost budget.
- **Trigger:** Before the first production deployment (Phase 1 exit), to establish cost discipline early.
- **Expected ADR:** Cloud cost tagging strategy; cost allocation per bounded context; monthly review process; cost ceiling alerts; sandbox cost budget; anomaly detection.

### F-026 — ML Model Registry and Training Pipeline

- **Rationale:** ADR-0007 specifies a model registry and shadow evaluation for future ML integration. The registry (MLflow, Vertex AI, SageMaker) and training pipeline need formalization when ML is admitted.
- **Trigger:** The Future Review Trigger in ADR-0007 fires (10M+ Attempts, 10K+ learners, stable baseline).
- **Expected ADR:** Model registry selection; training pipeline; feature store; shadow evaluation infrastructure; promotion gate automation; monitoring.

### F-027 — A/B Testing Framework

- **Rationale:** ASD Section 13.8 and ADR-0007 mention A/B testing for Scheduler variants and ML models. The framework (in-house, Statsig, Optimizely) needs selection.
- **Trigger:** When the first A/B test is needed (likely Phase 4, for Scheduler variants or ML shadow evaluation).
- **Expected ADR:** A/B testing framework; experiment lifecycle; statistical significance; metric selection; cohort assignment; ethical considerations.

---

## Product and Pedagogy (3 topics)

### F-028 — Notification System Architecture

- **Rationale:** ASD Section 2.10 specifies a notification system (review reminders, streak nudges, weekly digests). The architecture (channels, templates, preferences, delivery) needs formalization.
- **Trigger:** Phase 3, when notifications are implemented.
- **Expected ADR:** Notification channels (email, push, in-app); template engine; user preferences; delivery scheduling; deduplication; analytics; GDPR compliance.

### F-029 — Payment Provider Integration

- **Rationale:** ASD Section 2.9 specifies a payments subsystem with a PCI-compliant provider (Stripe by default). The integration architecture needs formalization.
- **Trigger:** Phase 3, when subscriptions are implemented.
- **Expected ADR:** Payment provider selection; integration architecture; webhook handling; idempotency; refund procedures; PCI compliance scope; revenue recognition.

### F-030 — Mobile Strategy (PWA vs. Native)

- **Rationale:** ASD Section 9.11 and ADR-0004 specify PWA as the mobile strategy, deferring native apps. The decision to build a native app needs formalization when triggered.
- **Trigger:** PWA users exceed 30% of traffic and mobile churn is significantly worse than desktop, per ADR-0004's Future Review Trigger.
- **Expected ADR:** Native app decision (React Native, Expo, or native iOS/Android); feature parity; offline support; push notifications; release cadence; team structure.

---

## Summary

| Theme | Count | ADR Topics |
|---|---|---|
| Infrastructure and Operations | 10 | F-001 to F-010 |
| Architecture and Patterns | 8 | F-011 to F-018 |
| Security and Compliance | 5 | F-019 to F-023 |
| Data and Analytics | 4 | F-024 to F-027 |
| Product and Pedagogy | 3 | F-028 to F-030 |
| **Total** | **30** | |

These 30 topics are anticipated; the actual ADRs written will depend on which triggers fire and what new topics emerge. The list is reviewed quarterly by the architecture review group and updated as the system evolves.

---

*End of Future ADR Suggestions.*
