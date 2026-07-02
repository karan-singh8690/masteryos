# ADR Cross-Reference Matrix

> **Purpose:** The navigational map of the ADR repository. Consult this first when investigating an architectural question.
> **Companion:** README.md (ADR process), individual ADRs (decisions).

---

## ADR Index

| ADR | Title | Status | Date | Depends On | Informs |
|---|---|---|---|---|---|
| [ADR-0001](0001-modular-monolith.md) | Use a Modular Monolith Architecture | Accepted | 2026-07-02 | ADR-0005, ADR-0006, ADR-0012 | ADR-0014 |
| [ADR-0002](0002-postgresql.md) | Choose PostgreSQL as the Primary Database | Accepted | 2026-07-02 | ADR-0001, ADR-0005 | ADR-0011, ADR-0012 |
| [ADR-0003](0003-fastapi.md) | Choose FastAPI for the Backend | Accepted | 2026-07-02 | ADR-0002, ADR-0005 | ADR-0014 |
| [ADR-0004](0004-nextjs-typescript.md) | Choose Next.js with TypeScript | Accepted | 2026-07-02 | ADR-0014 | ADR-0015 |
| [ADR-0005](0005-clean-architecture.md) | Use Clean Architecture | Accepted | 2026-07-02 | ADR-0001, ADR-0006 | ADR-0003 |
| [ADR-0006](0006-domain-driven-design.md) | Use Domain-Driven Design | Accepted | 2026-07-02 | ADR-0005, ADR-0012 | ADR-0010, ADR-0011 |
| [ADR-0007](0007-deterministic-scheduling-before-ml.md) | Use Deterministic Scheduling before Machine Learning | Accepted | 2026-07-02 | ADR-0011, ADR-0006 | ADR-0009 |
| [ADR-0008](0008-memory-vs-mastery-score.md) | Separate Memory Score from Mastery Score | Accepted | 2026-07-02 | ADR-0007, ADR-0011 | ADR-0009 |
| [ADR-0009](0009-human-authored-curriculum.md) | Human-authored Curriculum is the Source of Truth | Accepted | 2026-07-02 | ADR-0007, ADR-0010 | ADR-0011 |
| [ADR-0010](0010-subject-agnostic-architecture.md) | Subject-agnostic Architecture | Accepted | 2026-07-02 | ADR-0006, ADR-0009 | ADR-0011 |
| [ADR-0011](0011-triple-versioning.md) | Triple Versioning | Accepted | 2026-07-02 | ADR-0009, ADR-0007 | ADR-0012 |
| [ADR-0012](0012-outbox-pattern-domain-events.md) | Outbox Pattern + Domain Events | Accepted | 2026-07-02 | ADR-0001, ADR-0006, ADR-0002 | ADR-0011 |
| [ADR-0013](0013-jwt-authentication.md) | JWT Authentication | Accepted | 2026-07-02 | ADR-0003, ADR-0002 | ADR-0014 |
| [ADR-0014](0014-api-first-development.md) | API-first Development | Accepted | 2026-07-02 | ADR-0003, ADR-0004 | ADR-0015 |
| [ADR-0015](0015-documentation-first-workflow.md) | Documentation-first Workflow | Accepted | 2026-07-02 | ADR-0001 through ADR-0014 | All future ADRs |

---

## Dependency Graph

The dependency graph shows which ADRs depend on which. An arrow from A to B means "A depends on B" (B must be Accepted before A is fully meaningful).

```
ADR-0005 (Clean Architecture) ◀── ADR-0001 (Modular Monolith)
ADR-0006 (DDD) ◀── ADR-0001 (Modular Monolith)
ADR-0012 (Outbox) ◀── ADR-0001 (Modular Monolith)

ADR-0001 (Modular Monolith) ◀── ADR-0002 (PostgreSQL)
ADR-0005 (Clean Architecture) ◀── ADR-0002 (PostgreSQL)

ADR-0002 (PostgreSQL) ◀── ADR-0003 (FastAPI)
ADR-0005 (Clean Architecture) ◀── ADR-0003 (FastAPI)

ADR-0014 (API-first) ◀── ADR-0004 (Next.js)

ADR-0001 (Modular Monolith) ◀── ADR-0005 (Clean Architecture)
ADR-0006 (DDD) ◀── ADR-0005 (Clean Architecture)

ADR-0005 (Clean Architecture) ◀── ADR-0006 (DDD)
ADR-0012 (Outbox) ◀── ADR-0006 (DDD)

ADR-0011 (Triple Versioning) ◀── ADR-0007 (Deterministic Scheduling)
ADR-0006 (DDD) ◀── ADR-0007 (Deterministic Scheduling)

ADR-0007 (Deterministic Scheduling) ◀── ADR-0008 (Memory vs Mastery)
ADR-0011 (Triple Versioning) ◀── ADR-0008 (Memory vs Mastery)

ADR-0007 (Deterministic Scheduling) ◀── ADR-0009 (Human-authored)
ADR-0010 (Subject-agnostic) ◀── ADR-0009 (Human-authored)

ADR-0006 (DDD) ◀── ADR-0010 (Subject-agnostic)
ADR-0009 (Human-authored) ◀── ADR-0010 (Subject-agnostic)

ADR-0009 (Human-authored) ◀── ADR-0011 (Triple Versioning)
ADR-0007 (Deterministic Scheduling) ◀── ADR-0011 (Triple Versioning)

ADR-0001 (Modular Monolith) ◀── ADR-0012 (Outbox)
ADR-0006 (DDD) ◀── ADR-0012 (Outbox)
ADR-0002 (PostgreSQL) ◀── ADR-0012 (Outbox)

ADR-0003 (FastAPI) ◀── ADR-0013 (JWT)
ADR-0002 (PostgreSQL) ◀── ADR-0013 (JWT)

ADR-0003 (FastAPI) ◀── ADR-0014 (API-first)
ADR-0004 (Next.js) ◀── ADR-0014 (API-first)

ADR-0001 through ADR-0014 ◀── ADR-0015 (Documentation-first)
```

### Foundational Layer

The foundational ADRs (those that other ADRs depend on but that depend on few others) are:

- **ADR-0001 (Modular Monolith)** — the deployment topology decision.
- **ADR-0005 (Clean Architecture)** — the layering decision.
- **ADR-0006 (DDD)** — the modeling methodology decision.
- **ADR-0002 (PostgreSQL)** — the database decision.
- **ADR-0009 (Human-authored curriculum)** — the content philosophy decision.

These five are the load-bearing decisions; changing any of them would trigger a cascade of supersessions.

---

## Superseding Relationships

As of 2026-07-02, no ADRs have been superseded. The repository is at version 1.0. Supersession will occur when a Future Review Trigger fires for an ADR and a new ADR is Accepted that replaces it.

When a supersession occurs, this matrix will be updated to show:

| Superseded ADR | Superseded By | Superseded On | Reason |
|---|---|---|---|
| (none yet) | | | |

---

## Cross-Reference to Architecture Specification Document (ASD)

| ADR | ASD Section | Topic |
|---|---|---|
| ADR-0001 | Section 1.4, Section 2, Section 13.1, Section 13.5 | Modular monolith philosophy, subsystems, horizontal scaling, future microservices |
| ADR-0002 | Section 1.4, Section 4, Section 13.3, Section 13.7, Section 17.5 | Normalized-first philosophy, domain model, database optimization, analytics at scale, disaster recovery |
| ADR-0003 | Section 1.5, Section 8, Section 10 | Why FastAPI, API architecture, backend architecture |
| ADR-0004 | Section 1.5, Section 9 | Why Next.js, frontend architecture |
| ADR-0005 | Section 8, Section 10, Section 14.1 | Layered overview, backend layers, coding standards |
| ADR-0006 | Section 3, Section 4, Section 14.2 | DDD, bounded contexts, domain model, folder organization |
| ADR-0007 | Section 1.4, Section 6, Section 6.7, Section 6.8 | Deterministic-first philosophy, mastery engine, future ML, invariants |
| ADR-0008 | Section 6.4, Section 6.6, Section 6.3 | Memory vs mastery, weak concept detection, state transitions |
| ADR-0009 | Section 1.4 (AI Usage Policy), Section 7, Section 7.11 | AI policy, content pipeline, AI assistance policy |
| ADR-0010 | Section 1.1, Section 1.5, Section 4.4, Section 7 | Product purpose, subject-agnostic core, subject entity, content pipeline |
| ADR-0011 | Section 7.9, Section 4.7, Section 6.7, Section 6.8 | Versioning, cross-context aggregates, ML integration, invariants |
| ADR-0012 | Section 3.2, Section 11.4, Section 10.11, Section 13.4 | Context communication, background job flow, background workers, background jobs |
| ADR-0013 | Section 12.1, Section 12.2, Section 9.3, Section 12.6 | Authentication, authorization, frontend auth flow, secrets management |
| ADR-0014 | Section 8.2, Section 8.4, Section 8.8, Section 14.4 | Frontend boundary, DTOs, API versioning, testing philosophy |
| ADR-0015 | Section 14.5, Section 14.7, Section 14.8 | Documentation standards, PR requirements, code review culture |

---

## Cross-Reference to Ubiquitous Language & Domain Glossary

| ADR | Key Glossary Terms |
|---|---|
| ADR-0001 | Bounded Context, Domain Event, Outbox, Application Service, Domain Service |
| ADR-0002 | Aggregate, Repository, Write Model, Read Model, Content Version, Attempt History |
| ADR-0003 | Controller, Application Service, Domain Service, DTO, Repository, Dependency Injection |
| ADR-0004 | User Profile, Dashboard, Learning Session, Study Session, Admin Portal, Read Model |
| ADR-0005 | Aggregate, Entity, Value Object, Repository, Application Service, Domain Service, Infrastructure Service, Controller, DTO |
| ADR-0006 | Bounded Context, Ubiquitous Language, Aggregate, Entity, Value Object, Domain Event, Repository, Domain Service |
| ADR-0007 | Mastery Score, Memory Score, Mastery Engine, Scheduler, Algorithm Version, Concept State, Review Interval |
| ADR-0008 | Memory Score, Mastery Score, Concept State, Weak Concept, Strong Concept, Mastery Threshold, Memory Threshold, Knowledge Decay |
| ADR-0009 | Instructor, Content Pack, Content Version, Review Workflow, Content Approval, Published Content, Draft Content, Misconception, Question Template, Explanation |
| ADR-0010 | Subject, Tenant, Concept, Question Template, Content Version, Knowledge Graph, Learning Path |
| ADR-0011 | Version, Content Version, Template Version, Algorithm Version, Attempt, Mastery Score, Question Instance |
| ADR-0012 | Domain Event, Outbox, Event Bus, Bounded Context, Application Service, Background Worker |
| ADR-0013 | Authentication, Authorization, User, User Profile, UserCredential, Session, Role, Permission |
| ADR-0014 | DTO, Request DTO, Response DTO, Controller, Command, Query, REST Resources |
| ADR-0015 | Ubiquitous Language, Architecture Decision Record, Bounded Context, Aggregate, DTO, Audit Log |

---

## Thematic Grouping

The 15 ADRs group into five thematic clusters:

### Cluster 1: Deployment and Infrastructure (ADR-0001, ADR-0002)

The "what runs where" decisions: modular monolith topology, PostgreSQL database. These are the load-bearing infrastructure choices.

### Cluster 2: Technology Stack (ADR-0003, ADR-0004)

The "what tools" decisions: FastAPI backend, Next.js frontend. These are the framework choices that determine the team's day-to-day work.

### Cluster 3: Architectural Patterns (ADR-0005, ADR-0006, ADR-0012)

The "how we organize code" decisions: Clean Architecture, DDD, Outbox Pattern. These are the methodology choices that govern code structure.

### Cluster 4: Domain and Pedagogy (ADR-0007, ADR-0008, ADR-0009, ADR-0010, ADR-0011)

The "what the system does" decisions: deterministic scheduling, memory vs mastery, human-authored curriculum, subject-agnostic architecture, triple versioning. These are the product-shaping choices that determine the system's educational effectiveness.

### Cluster 5: Workflow and Process (ADR-0013, ADR-0014, ADR-0015)

The "how we work" decisions: JWT authentication, API-first development, documentation-first workflow. These are the process choices that govern how the team operates.

---

## ADRs by Bounded Context

Each ADR primarily affects certain bounded contexts (ASD Section 3.1):

| Bounded Context | Primary ADRs |
|---|---|
| Identity | ADR-0013 (JWT Authentication) |
| Learning | ADR-0006 (DDD), ADR-0010 (Subject-agnostic), ADR-0012 (Outbox) |
| Assessment | ADR-0006 (DDD), ADR-0011 (Triple Versioning), ADR-0012 (Outbox) |
| Mastery | ADR-0007 (Deterministic Scheduling), ADR-0008 (Memory vs Mastery), ADR-0011 (Triple Versioning) |
| Content | ADR-0009 (Human-authored), ADR-0010 (Subject-agnostic), ADR-0011 (Triple Versioning) |
| Scheduling | ADR-0007 (Deterministic Scheduling), ADR-0008 (Memory vs Mastery) |
| Analytics | ADR-0002 (PostgreSQL), ADR-0011 (Triple Versioning), ADR-0012 (Outbox) |
| Billing | ADR-0013 (JWT Authentication, for subscription management) |
| Administration | ADR-0013 (JWT Authentication, for admin portal), ADR-0015 (Documentation-first, for audit) |

---

*End of Cross-Reference Matrix.*
