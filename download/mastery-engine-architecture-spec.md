# Mastery Engine — Architecture Specification Document (ASD)

> **Status:** v1.0 — Source of Truth for all implementation tasks
> **Owner:** Principal Architect
> **Audience:** Engineering team (backend, frontend, data, DevOps, instructional design)
> **Scope:** Full system architecture for the Mastery Engine SaaS platform
> **Subject-agnostic core; first tenant:** Python Technical Interview Preparation

---

## Document Conventions

- This document describes **architecture**, not implementation. No code, no SQL DDL, no UI mockups.
- Words **MUST / SHOULD / MAY** are used in their RFC 2119 sense.
- "The Engine" refers to the Mastery Engine as a whole.
- "The Loop" refers to the Adaptive Learning Loop defined in Section 5.
- "Tenant" refers to a subject hosted on the Engine (Python, SQL, Java, etc.).
- Section 17 (Appendix) collects architectural recommendations that the original brief did not request but that a Principal Architect is obligated to surface.

---

## Section 1 — Executive Summary

### 1.1 Product Purpose

Mastery Engine is a **Learning Operating System** that determines, at any moment, the single highest-value learning activity a user should perform next. It does not deliver static courses, it does not host passive video lectures, and it is not a chatbot. It is an adaptive engine that converts every interaction with a learner into a measurable update of their mastery state and uses that state to compute the next optimal action.

The first tenant is **Python Technical Interview Preparation**. The architecture, however, is designed so that additional tenants (SQL, Java, Cybersecurity, Cloud, IELTS, and others) can be onboarded without modifying the core engine. Tenancy is a data concept, not a code-fork concept.

### 1.2 Business Objective

The business objective is to build a defensible long-term position in the adaptive-learning market by accumulating proprietary data about how learners acquire and retain technical concepts. The product moat is not the curriculum, which can be replicated, nor the UI, which can be cloned. The moat is the **historical attempt corpus** combined with the **mastery model** that interprets it. Every architectural decision in this document is evaluated against whether it strengthens or weakens this moat.

A secondary objective is operational simplicity. The Engine competes against well-funded incumbents on focus, not on feature breadth. The architecture therefore favors a small number of durable subsystems over a large number of disposable features.

### 1.3 Learning Philosophy

The Engine is governed by a single educational premise: **learning is measurable through mastery, and mastery is built through deliberate practice distributed over time**. Concepts are atomic. Questions test concepts. Attempts update mastery. Mastery drives scheduling. Scheduling drives practice. Practice improves retention. Retention, not completion, is the success metric.

This philosophy rejects several popular alternatives. It rejects "course completion" as a success metric because completion does not imply retention. It rejects "time-on-platform" as a success metric because time does not imply mastery. It rejects "AI tutor chat" as the primary interaction because chat obscures the learner's actual state behind conversational fluency. The learner always sees a concrete next action — a question, a review, a diagnostic — never a vague suggestion.

### 1.4 Technical Philosophy

The Engine is **deterministic-first**. Scheduling, mastery computation, and queue selection are algorithms with auditable inputs and outputs. Artificial intelligence assists content authoring and explanation refinement but is forbidden from making runtime learning decisions. This choice has three justifications. First, deterministic systems are reproducible, which is essential for debugging, A/B testing, and regulatory defensibility. Second, deterministic systems are cheap to operate, which matters at scale. Third, deterministic systems build trust with serious learners who want to understand why a particular question was served.

The Engine is **normalized-first**. Data is stored in third-normal form in PostgreSQL. Denormalization, materialized views, and read replicas are introduced only when query latency or write throughput demands them. This choice sacrifices short-term development velocity for long-term data integrity and analytical flexibility — a trade the moat thesis makes mandatory.

The Engine is **modular-monolith-first**. The system ships as a single deployable backend with strong internal module boundaries, not as a distributed microservices mesh. Microservices are deferred until a specific, measured scaling or team-velocity requirement justifies the operational cost. This choice preserves deployment simplicity, transactional integrity across the Learning Loop, and developer onboarding speed during the critical first phases.

### 1.5 Why This Architecture Was Chosen

The architecture below combines a **subject-agnostic domain core** with a **subject-tenant configuration layer**. Concepts, Mastery Scores, Attempts, and Schedulers are defined without reference to Python; Python enters the system only as a populated subject graph and a set of question templates. This separation is the single most important architectural decision in the document because it determines whether the Engine can scale to multiple tenants without rewrite.

The chosen stack — **FastAPI + PostgreSQL + Next.js** — reflects the deterministic-first, normalized-first, modular-monolith-first philosophy. FastAPI provides async I/O, strong typing via Pydantic, and OpenAPI documentation for free, which accelerates the contract-driven workflow between frontend and backend. PostgreSQL provides ACID transactions, JSONB for semi-structured content, mature partitioning for the high-volume Attempts table, and a rich ecosystem for analytics. Next.js provides server-rendered pages for the dashboard, fast client transitions during a learning session, and a clear path to PWA for mobile without maintaining a separate React Native build. Docker provides reproducible deployments. Pytest and Playwright cover the test pyramid from property-based unit tests for mastery math to end-to-end learning-session smoke tests.

The rejected alternatives — Node/Express (weak typing, weaker async story for CPU-bound mastery math), Django (heavier framework, weaker async story), MongoDB (sacrifices relational integrity for the only data layer that needs it most), and microservices-from-day-one (operational overhead the team cannot afford) — were each evaluated and dismissed with documented rationale in Section 15.

---

## Section 2 — System Overview

The Engine is composed of eleven major subsystems. Each subsystem has a single, well-defined responsibility and communicates with other subsystems through documented interfaces. No subsystem reaches into another's data store.

### 2.1 Authentication Subsystem

The Authentication Subsystem verifies the identity of users and issues short-lived JWT access tokens and long-lived refresh tokens. It supports email/password, OAuth (Google, GitHub), and a recovery flow. It is responsible for credential storage (hashed with a modern adaptive hash), token issuance, token rotation, token revocation, and session listing. It is **not** responsible for authorization beyond asserting "this token belongs to this user"; fine-grained permission checks live in the subsystem that owns the resource being accessed.

### 2.2 User Management Subsystem

The User Management Subsystem owns the user profile, preferences, learning goals, timezone, and onboarding state. It is distinct from Authentication because identity (who you are) and profile (what you want) change for different reasons and at different rates. This subsystem also owns the user's relationship to tenants — for example, a user preparing for Python interviews and also studying SQL — and the per-tenant onboarding state for each.

### 2.3 Learning Engine

The Learning Engine is the orchestrator of the Loop. When a user starts a study session, the Learning Engine requests a queue from the Scheduler, dispatches the first question to the user, accepts the answer, records the Attempt via the Assessment context, asks the Mastery Engine to update mastery, asks the Scheduler to recompute, and returns the explanation plus the next question. It is the only subsystem that holds the Loop's state machine. It is **stateless between requests** — Loop state lives in the database, not in process memory — so any backend instance can serve any request in the middle of a session.

### 2.4 Scheduler

The Scheduler computes the adaptive practice queue. It takes as input the user's current mastery state across all concepts in the active tenant, the user's recent attempt history, the user's session goals (for example, "drill weak concepts" versus "diagnostic"), and the available question inventory. It returns an ordered list of question candidates ranked by expected educational value. The Scheduler is **deterministic**: given the same inputs it produces the same output. The scheduling algorithm is a weighted combination of spaced-repetition due-dates, weak-concept priority, prerequisite-readiness, and session-goal alignment. Section 6 describes its architecture; the precise formula is owned by the Mastery Engine subsystem and versioned in source control.

### 2.5 Mastery Engine

The Mastery Engine maintains the per-user, per-concept mastery state. It consumes Attempt events and produces updated Mastery Scores, updated review schedules, and weak-concept signals. It distinguishes between **memory score** (the decay-prone probability that a user can recall a concept now) and **mastery score** (the consolidated, less-decay-prone estimate of durable understanding). It is the only subsystem permitted to write Mastery Scores. It is the only subsystem permitted to compute review due-dates. Section 6 covers its full architecture.

### 2.6 Question Factory

The Question Factory converts Question Templates into concrete Questions ready to be served to a learner. A template encodes a parameterized problem — for example, "given list `L` and integer `k`, what is the time complexity of `L.count(k)`?" — and the Factory instantiates it with concrete values, generates the correct answer, generates distractors, and emits a fully-formed Question object. The Factory is **deterministic given a seed**, which means the same template with the same seed produces the same question. This property is essential for reproducibility, debugging, and analytics — every Attempt can be traced back to the exact template and seed that produced it.

### 2.7 Content Management

The Content Management Subsystem owns the authoring, review, versioning, and publishing lifecycle for all learning content: Subjects, Concepts, Concept Dependencies, Learning Objectives, Misconceptions, Question Templates, and Explanations. It enforces the human-authored source-of-truth principle: no learner-facing content is generated at runtime by AI. AI assistance is permitted only inside the authoring workflow, and every AI-touched artifact must pass human review before publishing. Section 7 describes the full pipeline.

### 2.8 Analytics

The Analytics Subsystem computes and serves aggregate and per-user metrics: mastery-over-time curves, retention curves, concept-difficulty distributions, engagement cohorts, and funnel metrics. It reads from the operational database for low-latency per-user queries and from a derived analytics store for expensive aggregates. It is **strictly read-only** against the operational database; no analytics query mutates learner state. This separation guarantees that analytics load cannot corrupt the Loop.

### 2.9 Payments

The Payments Subsystem owns subscriptions, invoicing, payment-method storage (via a PCI-compliant provider — Stripe by default), and entitlement resolution. Entitlements — "what features this user may access" — are computed from subscription state and exposed to other subsystems through a single read interface. The Learning Engine consults entitlements when constructing the queue (for example, free-tier users may be limited to N questions per day) but the Payments Subsystem itself never modifies learning state.

### 2.10 Notification System

The Notification Subsystem sends transactional and engagement messages: review reminders, streak nudges, weekly progress digests, and administrative alerts. It is **fully decoupled** from the Loop: notifications are queued on an internal event bus and dispatched by background workers. A notification failure never blocks a learning action. Notification preferences are user-controlled and GDPR-relevant; the system MUST honor opt-outs immediately.

### 2.11 Admin Portal

The Admin Portal is the internal interface for content authors, instructional designers, support staff, and engineers. It exposes Content Management workflows, user-support tooling (lookup, refund, password reset escalation), system health dashboards, and audit-log review. It is a separate Next.js route tree with a separate authentication and authorization policy. It MUST NOT share session state with the learner-facing application.

---

## Section 3 — Domain Driven Design

The Engine is decomposed into eight bounded contexts. Each context owns a coherent slice of the domain model, exposes a clear interface to other contexts, and persists its own data. Contexts communicate through **service interfaces** (synchronous, in-process for now) and **domain events** (asynchronous, via an internal event bus). Direct cross-context repository access is forbidden.

### 3.1 Bounded Contexts

| # | Context | Responsibility | Owned Aggregates |
|---|---|---|---|
| 1 | **Identity** | Authentication, sessions, tokens | User Credential, Session, RefreshToken |
| 2 | **Learning** | Orchestration of the Loop, study sessions, learning paths | StudySession, LearningPath, PracticeQueue |
| 3 | **Assessment** | Attempts, answers, scoring | Attempt, Answer, QuestionInstance |
| 4 | **Content** | Curriculum authoring, versioning, publishing | Subject, Concept, ConceptDependency, LearningObjective, Misconception, QuestionTemplate, Explanation |
| 5 | **Scheduling** | Adaptive queue computation, due-date calculation | Schedule, ReviewPlan |
| 6 | **Analytics** | Aggregate metrics, per-user dashboards | MetricSnapshot, Cohort, Funnel |
| 7 | **Billing** | Subscriptions, entitlements, invoices | Subscription, Entitlement, Invoice |
| 8 | **Administration** | Internal tooling, audit logs, support actions | SupportTicket, AuditLog, AdminAction |

The **Mastery state** is shared between Learning and Assessment but owned by neither. It forms its own implicit context — referred to in this document as the **Mastery Context** — and is accessed through the Mastery Engine subsystem. This is intentional: mastery is a first-class concept that crosses the Learning/Assessment boundary and must not be subordinated to either.

### 3.2 Context Communication Patterns

**Synchronous in-process calls** are used for read-heavy, low-latency, transactional operations inside the Loop. For example, when the Learning Engine needs the current mastery state to build a queue, it calls the Mastery Engine service directly. These calls are made through interfaces (Python protocols / abstract base classes), never through concrete classes, so they can be replaced with remote calls later without modifying callers.

**Asynchronous domain events** are used for cross-cutting side effects that do not need to block the user request. For example, when an Attempt is recorded, the Assessment context publishes an `AttemptRecorded` event. The Analytics context listens and updates its derived store. The Notification context listens and may send a milestone nudge. The Mastery context listens and updates the Mastery Score. Events are persisted in an outbox table within the same transaction as the originating write, then dispatched by a background worker — this guarantees that an event is never lost if the worker is briefly unavailable.

**Anti-corruption layers** are introduced at any boundary where a context consumes another context's data in a translated form. For example, the Analytics context does not read the Attempts table directly; it consumes a translated `AttemptFinalized` event containing only the fields Analytics needs. This prevents Analytics from becoming coupled to the Assessment schema.

### 3.3 Context Ownership Matrix

| Aggregate | Owner Context | Read By | Written By |
|---|---|---|---|
| User Profile | Identity | Learning, Analytics, Admin | Identity |
| StudySession | Learning | Analytics, User | Learning |
| Attempt | Assessment | Mastery, Analytics | Assessment |
| MasteryScore | Mastery | Learning, Scheduling, Analytics | Mastery |
| Concept | Content | Learning, Scheduling | Content |
| QuestionTemplate | Content | QuestionFactory | Content |
| Schedule | Scheduling | Learning | Scheduling |
| Subscription | Billing | Learning (entitlements) | Billing |

The single-writer principle is enforced: every aggregate has exactly one context that may write to it. Other contexts read through service interfaces or projections.

---

## Section 4 — Core Domain Model

This section defines every major domain entity, its responsibility, and its key relationships. It is **not** a database schema; persistence concerns are deferred to a later task. Entities are grouped by their owning bounded context.

### 4.1 Identity Context

#### User
The User is the root identity of a learner. It holds immutable identity fields (id, email, created_at) and links to a User Profile and a set of User Credentials. The User entity itself does not hold learning state; that lives in the Mastery and Learning contexts. This separation allows identity to be migrated, merged, or anonymized without touching learning data.

#### UserCredential
Stores the hashed password and the OAuth provider linkage. Distinct from User so that credential rotation and identity merge do not ripple into profile or learning data. Only the Identity context may read or write this entity.

#### Session
Represents an authenticated session: the issued tokens, the device fingerprint, the IP, the user-agent, and the expiry. Sessions are revocable; revocation is the mechanism for "log out everywhere."

### 4.2 Learning Context

#### StudySession
A StudySession is a single sitting during which a learner practices. It has a start time, an end time, a goal (drill, diagnostic, review, mixed), a target concept set, and a sequence of Attempt references. The StudySession is the unit of analytics for engagement: streaks, total time, and questions-per-session are all computed from it. It is also the recovery unit — if a learner abandons a session, the next session can resume where the previous one stopped.

#### LearningPath
A LearningPath is an ordered, opinionated traversal of the Concept graph for a given Subject. It represents the Engine's recommendation of how to move from "no knowledge" to "interview-ready" within that subject. A user may follow the default LearningPath or a customized variant. The LearningPath is **not** the schedule — it is the goal; the Scheduler decides what to serve next within the goal.

#### PracticeQueue
A short-lived, ordered list of question candidates produced by the Scheduler for a specific StudySession. It is rebuilt on demand, not persisted long-term. It holds the next N questions the learner will see, allowing the frontend to pre-fetch and the Scheduler to amortize computation.

### 4.3 Assessment Context

#### Question
A concrete, instantiated question ready to be served to a learner. It has a reference to its Question Template, the seed used to instantiate it, the rendered prompt, the rendered choices or input contract, the correct answer, and the set of distractors. A Question instance is **immutable once served**; if a template is edited after a Question was served, the served Question is preserved verbatim for replay.

#### Attempt
An Attempt is the atomic unit of learning evidence. It records: which Question was presented, when, the learner's answer, the time-to-answer, whether hints were used, whether the answer was correct, partial-credit score if applicable, and the timestamp. The Attempt is **append-only** — once written, it is never modified. This immutability is the foundation of the moat: historical attempts cannot be retroactively edited, which makes every downstream mastery and analytics computation reproducible.

#### Answer
The learner's response to a Question. For multiple-choice this is a choice identifier; for code questions it is a code string plus an execution result; for free-response it is a text string. The Answer entity exists separately from the Attempt so that multiple Answer revisions (within a single attempt, for code questions with iterative execution) can be stored without duplicating Attempt metadata.

### 4.4 Content Context

#### Subject
A Subject is a top-level tenant: Python, SQL, Java, Cybersecurity, etc. A Subject owns its Concept graph, its Learning Objectives, its Misconceptions, and its Question Templates. The Engine is subject-agnostic; the Subject is the unit at which subject-specific behavior (if any) is configured. Subjects are versioned as a unit so that a major curriculum revision can be shipped without invalidating in-flight attempts.

#### Concept
A Concept is the atomic unit of knowledge. It is small enough to be mastered independently and large enough to be tested meaningfully. For Python: "list mutability," "dict lookup is O(1) average," "the GIL prevents true parallelism in CPU-bound threads." Each Concept belongs to exactly one Subject, has a stable identifier, a human-readable name, a description, and a difficulty estimate. Concepts are the vertices of the dependency graph.

#### ConceptDependency
A directed edge in the Concept graph. If concept A depends on concept B, the learner should generally master B before A. Dependencies are typed (prerequisite, related, reinforces) and weighted (strong, weak) because not all dependencies are equally load-bearing. The graph is **acyclic** at any published version; cycles are rejected at publish time. The dependency graph drives prerequisite-readiness scoring in the Scheduler.

#### LearningObjective
A Learning Objective is a verifiable statement of what a learner should be able to do with a Concept. Each Concept has one or more Learning Objectives. A Learning Objective is the bridge between curriculum design and assessment: every Question Template MUST trace to at least one Learning Objective, and every Misconception MUST trace to a Learning Objective it would violate. This traceability is what allows the Engine to diagnose why a learner is failing — not just that they are failing.

#### Misconception
A Misconception is a specific, documented incorrect mental model a learner may hold about a Concept. For Python list mutability, a common misconception is "reassigning an element creates a new list." Misconceptions are linked to Question Templates that are designed to detect them (via specific distractors that appeal to that misconception). When a learner selects such a distractor, the Engine updates mastery for the related Concept AND tags the learner as likely holding that Misconception, which the Scheduler uses to serve remediation. Misconceptions are the Engine's most important content artifact because they convert wrong answers from noise into signal.

#### QuestionTemplate
A Question Template is a parameterized specification for generating Questions. It references one or more Learning Objectives, declares the parameter schema, the prompt template, the correct-answer generator, the distractor generator, the explanation template, and the misconception mapping. Templates are versioned; an edit to a template produces a new version rather than mutating the old one, so historical Attempts remain interpretable. Templates are human-authored; AI may assist in drafting but not in publishing.

#### Explanation
An Explanation is the text, diagram, or interactive artifact shown to the learner after an Attempt. It is tied to a Question Template (or, more precisely, to a Template version), and may have variants keyed by the learner's specific mistake (correct answer, common-misconception A, common-misconception B, etc.). Explanations are part of the content graph and go through the same review-and-publish workflow.

### 4.5 Mastery Context

#### MasteryScore
A MasteryScore is the Engine's current belief about a learner's mastery of a single Concept. It is composed of two sub-scores — a memory score (short-term, decay-prone) and a mastery score (long-term, slower to decay) — plus a confidence interval, a last-updated timestamp, and a count of evidence points (attempts) underlying it. The MasteryScore is updated by the Mastery Engine after every Attempt and is the primary input to the Scheduler. It is **per-user, per-concept, per-tenant**.

#### Review
A Review is a scheduled future encounter with a Concept. It has a due timestamp, a priority, and a reference to the Concept and the Learning Objective it targets. Reviews are produced by the Mastery Engine's spaced-repetition logic and consumed by the Scheduler when constructing the Practice Queue.

### 4.6 Scheduling Context

#### Schedule
A Schedule is the per-user, per-tenant plan of what the learner should practice in the near term. It is the persistent projection of the Scheduler's most recent output: the current set of due Reviews, the current weak concepts, and the current goal. The Schedule is updated by the Scheduler and read by the Learning Engine when building a Practice Queue.

### 4.7 Cross-Context Aggregates

#### ContentVersion
A Content Version is an immutable snapshot of a Subject's content graph (Concepts, Dependencies, Objectives, Misconceptions, Templates) at a moment in time. Every Attempt references the Content Version under which it was served, so that future replays and analytics can interpret the Attempt even after the content has been revised. Content Versions are append-only.

#### AuditLog
An Append-only record of every privileged action: content publish, user-support action, admin configuration change, entitlement override. The AuditLog is owned by the Administration context but written to by every context that performs privileged operations. It is the compliance and forensic backbone of the system.

---

## Section 5 — Learning Loop

The Learning Loop is the Engine's heartbeat. Every other subsystem exists to serve it. This section describes the full lifecycle at architectural resolution — what each step's inputs, outputs, and side effects are. No formulas; the Mastery Engine's internal math is described in Section 6.

### 5.1 Loop Overview

```
User opens app
      ↓
Adaptive queue created
      ↓
Question served
      ↓
User answers
      ↓
Attempt recorded
      ↓
Mastery updated
      ↓
Scheduler recalculates
      ↓
Explanation displayed
      ↓
Queue regenerated
      ↓
(loop back to "Question served")
```

The loop runs at the cadence of the learner. A typical cycle lasts between 30 seconds and 5 minutes. The Engine MUST be able to sustain this cadence under load with sub-200ms backend response time at the median.

### 5.2 Step-by-Step Description

#### Step 1 — User Opens App
The frontend loads the active StudySession (if any) or requests the creation of a new one. The Learning Engine resolves the user's active tenant, active Learning Path, current Schedule, and current Mastery state. This step is **read-heavy**: it touches Identity, Learning, Scheduling, and Mastery in a single composed request. The composition happens in the Learning Engine service; no other subsystem is allowed to chain reads across these contexts.

#### Step 2 — Adaptive Queue Created
The Learning Engine asks the Scheduler to produce a Practice Queue. The Scheduler reads the user's Mastery Scores across the active Concept set, the user's due Reviews, the user's session goal, and the available Question Templates. It computes a ranked list of candidate concepts and, for each concept, asks the Question Factory to instantiate one or more Questions. The resulting queue is returned to the Learning Engine and cached for the duration of the session. The queue is **bounded in size** (typically 10–20 questions) so that it can be regenerated cheaply as mastery shifts.

#### Step 3 — Question Served
The Learning Engine returns the first Question from the Practice Queue to the frontend, along with the metadata the UI needs (concept, difficulty estimate, time budget, hint availability). The frontend renders the question. The backend records the "served" timestamp; this is the start of the time-to-answer measurement.

#### Step 4 — User Answers
The learner submits an answer. The frontend sends the answer to the Learning Engine. The Learning Engine does **not** evaluate correctness itself — it delegates to the Assessment context, which knows how to score the answer type (multiple-choice, code-execution, free-response). For code questions, the Assessment context runs the learner's code against a sandboxed execution environment and captures pass/fail plus any error output. The Assessment context returns a scoring result.

#### Step 5 — Attempt Recorded
The Assessment context writes an Attempt record. This write is **transactional with the answer evaluation**: the Attempt is only persisted if evaluation completed successfully. The Attempt is append-only; no field is ever updated after write. The Assessment context publishes an `AttemptRecorded` domain event to the event bus within the same transaction (via the outbox pattern). The event is consumed asynchronously by the Mastery, Analytics, and Notification contexts.

#### Step 6 — Mastery Updated
The Mastery Engine consumes the `AttemptRecorded` event and recomputes the Mastery Score for every Concept the Attempt's Question tests. The update uses the Attempt's outcome (correct, incorrect, partial), the time-to-answer, the hint usage, and the learner's prior Mastery Score for that Concept. The Mastery Engine writes the updated Mastery Score and emits a `MasteryUpdated` event. The Mastery Engine also recomputes the next Review due-date for the affected Concepts and writes the Review records.

#### Step 7 — Scheduler Recalculates
The Scheduler consumes the `MasteryUpdated` event (or, in the synchronous path, is called directly by the Learning Engine after the Mastery update commits) and rebuilds the Practice Queue for the active StudySession. The new queue reflects the updated Mastery Scores, the new Review schedule, and the still-active session goal.

#### Step 8 — Explanation Displayed
The Learning Engine returns the explanation for the served Question to the frontend. The explanation is keyed by the learner's specific outcome: a correct answer gets the "you got it right, here is the deeper why" variant; a wrong answer gets the variant tailored to the misconception that the selected distractor indicates. The explanation is part of the Question Template's published content; it is not generated at runtime.

#### Step 9 — Queue Regenerated
The Learning Engine returns the next Question from the (regenerated) Practice Queue. The frontend advances to the next question without a full page reload. The loop returns to Step 3.

### 5.3 Loop Invariants

The Loop MUST preserve the following invariants. Any implementation that violates any invariant is incorrect by definition.

- **I1 — Attempt Immutability.** An Attempt, once written, is never modified. Corrections (e.g., a scoring bug discovered later) are made by appending a compensating Attempt, not by editing the original.
- **I2 — Mastery Monotonicity with Respect to Evidence.** Mastery Scores are a pure function of the Attempt history and the Mastery Engine version. Given the same attempts and the same Mastery Engine version, the same Mastery Scores result. This makes mastery reproducible and auditable.
- **I3 — Queue Determinism.** Given the same Mastery state, the same Schedule, the same session goal, and the same Question Template availability, the Scheduler produces the same Practice Queue. Randomization, when desired, is driven by an explicit, logged seed.
- **I4 — Loop Atomicity per Step.** Each step either completes fully or rolls back. A failed Mastery update does not leave a half-written Attempt; a failed Scheduler recalculation does not corrupt the Practice Queue.
- **I5 — No Silent AI Decisions.** No AI model participates in any step of the Loop at runtime. The Loop is fully deterministic and fully auditable.

### 5.4 Loop Failure Modes

The Loop has three primary failure modes, each with a defined mitigation:

- **F1 — Mastery Update Failure.** If the Mastery Engine is unavailable, the Attempt is still recorded (Step 5 commits) but the Mastery update is queued for retry. The Loop continues with the prior Mastery state; the next Attempt is served with slightly stale scheduling. The system converges to correctness as the backlog drains.
- **F2 — Scheduler Failure.** If the Scheduler cannot produce a queue, the Learning Engine falls back to a deterministic default: serve the oldest due Review. This guarantees the learner always has a next action.
- **F3 — Frontend Disconnection.** If the learner closes the app mid-Attempt, the served Question is marked as "abandoned" after a configurable timeout. Abandoned Attempts are NOT scored — they do not update Mastery — but they ARE recorded for analytics. This prevents network flakiness from penalizing mastery.

---

## Section 6 — Mastery Engine

The Mastery Engine is the most architecturally sensitive subsystem in the platform. It is the only subsystem that translates Attempt evidence into the Engine's belief about a learner, and that belief drives every scheduling decision. Errors here compound silently: a small bias in mastery computation propagates into every queue, every review, and every analytics view, and is extremely hard to detect after the fact. The Mastery Engine is therefore designed for **auditability, reproducibility, and versioned evolution** rather than for raw performance.

### 6.1 Inputs

The Mastery Engine consumes the following inputs:

- **Attempt events** — the primary evidence stream. Each event carries the Question identity, the Answer, the scoring outcome, the time-to-answer, the hint-usage flag, the misconception tag (if any), and the Content Version under which the Question was served.
- **Question Template metadata** — the Concept(s) the Question tests, the Learning Objective(s) it traces to, the difficulty estimate, and the discrimination weight (how strongly this question separates mastered from non-mastered learners).
- **Current Mastery state** — the prior Mastery Score for each affected Concept, including its confidence interval and evidence count.
- **Learner context** — the time of day, the session position (early vs. late in the session), and the learner's recent fatigue signal (declining accuracy over the last N attempts). These contextual factors modulate how heavily the new evidence is weighted.
- **Mastery Engine version** — the algorithm version under which the computation runs. This is recorded with every Mastery Score so historical computations remain reproducible.

### 6.2 Outputs

The Mastery Engine produces the following outputs:

- **Updated Mastery Score per affected Concept** — composed of the memory sub-score, the mastery sub-score, the confidence interval, the evidence count, and the timestamp.
- **Review record per affected Concept** — the next due-date for review, the review priority, and the review interval (which expands on success and contracts on failure).
- **Weak-Concept signal** — a boolean or graded flag indicating that a Concept has fallen below the mastery threshold and requires remediation. Consumed by the Scheduler.
- **MasteryUpdated domain event** — published to the event bus for downstream consumers (Scheduler, Analytics, Notification).
- **Diagnostic tag** (when applicable) — if the Attempt triggered a Misconception-tagged distractor, the Mastery Engine emits a diagnostic tag linking the learner to that Misconception. This tag is the basis for targeted remediation.

### 6.3 State Transitions

Each Concept's Mastery Score transitions through a finite set of states. Transitions are driven by accumulated evidence, not by single Attempts (a single wrong answer does not demote a Concept from Mastered to Novice).

| State | Definition | Transition In | Transition Out |
|---|---|---|---|
| **Unseen** | No Attempts yet | Initial state | First Attempt → Novice |
| **Novice** | Limited evidence; high uncertainty | First Attempt or repeated failure from Developing | Sustained correct Attempts → Developing |
| **Developing** | Moderate evidence; mixed outcomes | Correct streak from Novice or decay from Proficient | Continued correct streak → Proficient; sustained failure → Novice |
| **Proficient** | Strong evidence; reliable recall | Continued correct streak from Developing | Decay over time without review → Developing; sustained excellence → Mastered; sustained failure → Developing |
| **Mastered** | Strong evidence; durable recall; has survived multiple spaced reviews | Survival of multiple spaced reviews from Proficient | Decay without review → Proficient |
| **Decayed** | Was Mastered/Proficient; due for review and not yet attempted | Time-based decay | Successful Review → prior state; failed Review → Developing |

The state machine is **per-Concept**, not per-learner. A learner may be Mastered on Concept A and Novice on Concept B simultaneously. The Mastery Engine tracks each independently.

### 6.4 Memory Score vs. Mastery Score

The Engine distinguishes two orthogonal estimates because they decay at different rates and serve different purposes.

**Memory Score** is the Engine's estimate of the probability that the learner can correctly recall the Concept **right now**. It is highly sensitive to recent Attempts and decays sharply with time. It is the input to short-term scheduling decisions: "should we drill this Concept again today?" A learner who answered correctly an hour ago has a high memory score; the same learner, three weeks later without review, has a low memory score even if their underlying mastery is intact.

**Mastery Score** is the Engine's estimate of the learner's **durable** understanding — the probability that, given a brief refresher, the learner would perform reliably on the Concept. It is slower to rise (multiple successful spaced reviews are required) and slower to fall (a single failure does not collapse it). It is the input to long-term decisions: graduation from a Learning Path, eligibility for an advanced topic, the "interview-ready" badge.

The two scores are **combined, not averaged**. The Mastery Score anchors the estimate; the Memory Score modulates it for scheduling. A learner with high Mastery but low Memory on a Concept will be scheduled for a review; a learner with low Mastery on the same Concept will be scheduled for fresh instruction and drilling regardless of Memory.

### 6.5 Review Scheduling

Review scheduling is the Mastery Engine's mechanism for converting memory decay into actionable future work. The architecture is as follows:

- Every successful Attempt on a Concept extends the **review interval** for that Concept. The extension is proportional to the current interval (spaced-repetition behavior), bounded by a minimum and maximum interval, and modulated by the quality of the Attempt (fast correct answer extends more than slow correct answer).
- Every failed Attempt on a Concept contracts the review interval, with a floor that prevents the interval from collapsing to zero (which would otherwise cause review storms).
- A **Review record** is written whenever the review interval changes, recording the new due-date and the new interval. The Scheduler reads these records when building the Practice Queue.
- Reviews are **lattice-respecting**: if Concept A depends on Concept B, and B is due for review, the Scheduler MAY serve B before serving new material on A. This preserves the prerequisite-readiness invariant.
- Reviews are **batched for efficiency**: a single review question can refresh multiple related Concepts if the Question Template tests multiple Concepts. The Mastery Engine honors this by updating all tested Concepts from a single Attempt.

### 6.6 Weak-Concept Detection

A Concept is flagged as **weak** when its Mastery Score falls below a configurable threshold OR when its Memory Score falls below a different threshold while its Mastery Score is below the Proficient level. Weakness is graded (mild, moderate, severe) to allow the Scheduler to prioritize. The Mastery Engine emits the weak-concept signal as part of the `MasteryUpdated` event; the Scheduler uses it to bias the Practice Queue toward remediation.

Weak-concept detection also uses **Misconception clustering**: if a learner has selected the same Misconception-tagged distractor more than once across different Question Templates, the Mastery Engine elevates the weakness severity for that Concept-Misconception pair and emits a targeted remediation signal. This converts pattern-of-error from a passive observation into an active scheduling input.

### 6.7 Future ML Integration

The architecture is designed to admit ML-based enhancements later without rewriting the Mastery Engine. The integration points are:

- **Feature extraction layer** — every Mastery computation produces a structured feature vector (Attempt outcome, time-to-answer normalized by question difficulty, hint usage, prior mastery, concept-graph position, learner fatigue signal). This vector is persisted alongside the Mastery Score. An ML model trained later can consume these vectors offline without touching the production Mastery Engine.
- **Model registry** — a versioned registry of mastery models. The deterministic algorithm is "model v1" in this registry. A future ML model would be "model v2." The active model version is configurable per tenant and per cohort, enabling A/B testing.
- **Shadow evaluation** — a new model can run in shadow mode: it receives the same inputs as the production model, produces outputs, and the outputs are logged but not used. This allows offline evaluation against real production traffic before promotion.
- **Promotion gate** — a model is promoted from shadow to production only after passing a documented evaluation: reproducibility on historical attempts, no regression on retention metrics, and a human sign-off. The promotion is recorded as an audit event.

This architecture ensures that ML is **earned**, not assumed. The deterministic algorithm ships first, accumulates data, and any ML successor must defeat it on measured outcomes before it touches a learner.

### 6.8 Mastery Engine Invariants

- **M1 — Pure Function.** Given the same Attempt history, the same Content Version, the same learner context, and the same Mastery Engine version, the same Mastery Score results.
- **M2 — Versioned.** Every Mastery Score records the Mastery Engine version that produced it. A version change does not retroactively rewrite history; it produces new Scores going forward.
- **M3 — Single Writer.** Only the Mastery Engine writes Mastery Scores. No other subsystem, including Admin, may modify a Mastery Score directly.
- **M4 — Event-Sourced Reconstruction.** A learner's entire Mastery state is reconstructible from the Attempt history plus the Mastery Engine version log. This is the foundation of auditability and the prerequisite for any future ML retraining.

---

## Section 7 — Content Pipeline

Content is the Engine's fuel. The Content Pipeline is the workflow that converts an author's intent into a published, learner-facing artifact. It is governed by three principles: **human-authored source of truth**, **versioned immutability**, and **AI-assisted but not AI-authored**. This section describes the full pipeline.

### 7.1 Pipeline Stages

```
Authoring
    ↓
AI Assistance (optional, in-editor)
    ↓
Peer Review
    ↓
Editorial Review
    ↓
QA / Pilot
    ↓
Publishing
    ↓
Live Monitoring
    ↓
Revision Trigger
```

### 7.2 Concept Creation

A new Concept begins as a draft authored by a curriculum designer. The author specifies the Concept name, the description, the Subject it belongs to, the prerequisite Concepts (which establish Concept Dependency edges), and the Learning Objectives that the Concept satisfies. The author also specifies the **atomicity boundary**: what is in scope for this Concept and what belongs to adjacent Concepts. Atomicity is a curriculum-design judgment, not a technical one, but the pipeline enforces that no Concept may be published without at least one Learning Objective.

Concept drafts are stored in a draft store separate from the published content store. A draft Concept has no effect on the running Engine until it is published.

### 7.3 Learning Objectives

Each Learning Objective is a verifiable statement: "The learner can predict the time complexity of a dict lookup," "The learner can identify when a list mutation will alias another reference." Objectives are written in observable terms; vague objectives ("understand lists") are rejected at editorial review. Every Question Template MUST trace to at least one Objective; every Misconception MUST trace to an Objective it violates. This traceability is enforced at publish time and is non-negotiable.

### 7.4 Misconceptions

Misconceptions are documented as first-class content artifacts. Each Misconception has a name, a description of the incorrect mental model, a diagnosis of why learners fall into it, and a remediation strategy. Misconceptions are linked to the Question Templates that detect them: a Template that wants to detect Misconception M includes at least one distractor that appeals to M. When a learner selects that distractor, the Mastery Engine records the Misconception tag, and the Scheduler may serve a remediation Question targeting M.

Misconceptions are the Engine's most underappreciated content type. They are the difference between a system that knows a learner is wrong and a system that knows **why** the learner is wrong. Authors are required to document at least one Misconception per Learning Objective.

### 7.5 Question Templates

A Question Template is the parameterized specification of a class of Questions. The Template encodes:

- **Learning Objective linkage** — which Objectives this Template tests.
- **Concept linkage** — which Concepts this Template exercises.
- **Misconception linkage** — which Misconceptions the distractors are designed to elicit.
- **Parameter schema** — the typed parameters that vary across instantiations (e.g., list size, integer value, data structure choice).
- **Prompt template** — the parameterized text or code the learner sees.
- **Correct-answer generator** — a deterministic function that, given parameter values, produces the correct answer.
- **Distractor generator** — a deterministic function that, given parameter values, produces the distractors, each tagged with the Misconception it appeals to (or "none" for purely random distractors).
- **Explanation template** — the parameterized explanation, with variants keyed by the learner's selected distractor.
- **Difficulty estimate** — a coarse prior on how hard this Template is, used by the Scheduler before sufficient data accumulates.
- **Discrimination estimate** — a coarse prior on how well this Template separates mastered from non-mastered learners.
- **Seed contract** — the guarantee that the same parameter seed produces the same Question.

Templates are **versioned**. An edit to any of the above produces a new Template version, not a mutation. Historical Attempts reference the Template version under which they were served, so a Template edit never invalidates the interpretability of historical data.

### 7.6 Question Generation

The Question Factory instantiates Questions from Templates at serve time. The instantiation process:

1. The Scheduler selects a Template (based on Concept coverage, Misconception targeting, difficulty match).
2. The Scheduler passes a seed to the Question Factory.
3. The Question Factory invokes the Template's parameter generator with the seed to produce parameter values.
4. The Question Factory invokes the correct-answer generator and the distractor generator with the parameter values.
5. The Question Factory assembles a Question instance: the rendered prompt, the rendered choices or input contract, the correct answer, the distractors with their Misconception tags, and the Template version reference.
6. The Question is handed to the Learning Engine for serving.

The Factory is **deterministic given a seed**. This property is essential: every Attempt can be replayed by re-instantiating the Question from its Template version and seed, which is critical for debugging, for forensic analysis, and for ML retraining.

### 7.7 Review Workflow

Every artifact (Concept, Learning Objective, Misconception, Question Template, Explanation) passes through a multi-stage review before publishing:

- **Peer Review** — a second author reviews the artifact for accuracy, atomicity, and alignment with the Subject's curriculum design. Peer review is required for all artifacts.
- **Editorial Review** — a senior author reviews for stylistic consistency, tone, and pedagogical soundness. Editorial review is required for Templates and Explanations; recommended for Concepts.
- **QA / Pilot** — a sample of Questions generated from a new Template is served to a small pilot cohort (internal testers or opted-in learners). The QA stage measures the discrimination of the Template (does it separate mastered from non-mastered learners as expected?) and the clarity of the prompt (do pilot learners misread it in ways the author did not anticipate?). A Template that fails QA is sent back to the author.

Reviews are recorded as part of the content artifact's history. The reviewer, the review decision, and the review notes are persisted for audit.

### 7.8 Publishing Workflow

Publishing is the act of promoting a draft artifact to a live artifact. The publishing workflow:

- **Atomicity** — a publish operation is atomic. If a Concept is published together with its Learning Objectives, Misconceptions, and Templates, either all are published or none are.
- **Version stamping** — the publish operation assigns a new Content Version to the affected Subject. The Content Version is an immutable snapshot of the Subject's content graph at publish time.
- **Attempt reference** — every future Attempt served under the new Content Version references it. Historical Attempts continue to reference the Content Version under which they were served.
- **Rollback** — a published Content Version can be deprecated but not deleted. Deprecation prevents new Questions from being served under that Version, but historical Attempts remain interpretable. This is the content-side equivalent of Attempt immutability.

### 7.9 Versioning

Versioning applies at three levels:

- **Artifact version** — every Concept, Objective, Misconception, Template, and Explanation has a version. An edit produces a new version; the old version is preserved.
- **Subject version (Content Version)** — a snapshot of the entire content graph for a Subject at a moment in time. Bumped atomically on every publish.
- **Mastery Engine version** — the algorithm version under which Mastery Scores are computed. Bumped on every algorithm change.

All three versions are recorded on every Attempt. This triple-versioning is what makes the Engine fully auditable: any Attempt can be replayed against the exact content, template, and algorithm under which it was originally scored.

### 7.10 Quality Assurance

QA is not a single stage but a continuous activity. The Content Pipeline includes:

- **Discrimination monitoring** — every published Template's discrimination is continuously computed from live Attempt data. A Template whose discrimination falls below threshold is flagged for review.
- **Distractor analysis** — for each Misconception-tagged distractor, the engine tracks the rate at which it is selected by learners who eventually master the Concept vs. those who do not. A distractor that fails to discriminate is flagged.
- **Explanation effectiveness** — after viewing an explanation, the learner's probability of answering a related Question correctly on the next encounter is measured. Explanations that do not improve this probability are flagged for revision.
- **Curriculum coverage** — the pipeline enforces that every Learning Objective is tested by at least N Templates, every Concept by at least M, and every Misconception by at least one Template with a tagged distractor. Gaps are surfaced as content work items.

### 7.11 AI Assistance Policy

AI is permitted inside the authoring workflow under the following constraints:

- **Drafting** — AI may draft an initial version of an explanation, an initial distractor set, or an initial prompt wording. The author reviews and edits before submitting for peer review.
- **Wording refinement** — AI may suggest rephrasings for clarity, tone, or brevity. The author accepts or rejects each suggestion explicitly; accepted suggestions are recorded in the artifact's history.
- **Template generation** — AI may draft a Template skeleton (parameter schema, prompt structure, distractor tags). The author fills in the generators, validates correctness, and submits for review.
- **Forbidden uses** — AI may not publish artifacts. AI may not edit published artifacts. AI may not generate content at runtime. AI may not make mastery or scheduling decisions.

Every AI-assisted artifact carries a provenance flag in its history, recording which AI model assisted, on what date, and at which stage. This is a compliance and quality requirement, not a stylistic preference.

---

## Section 8 — API Architecture

This section defines the **service boundaries** of the API surface without enumerating endpoints. Endpoints will be specified in a later API contract task; this section constrains how those endpoints are organized.

### 8.1 Layered Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Next.js)                                          │
│  - Server Components for read-heavy screens                  │
│  - Client Components for interactive learning session        │
│  - API client generated from OpenAPI                         │
└─────────────────────────────────────────────────────────────┘
                          │  HTTPS / JSON
┌─────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Controllers (API layer)                               │  │
│  │  - HTTP transport, auth, request validation            │  │
│  │  - No business logic                                   │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Use Case Services (Application layer)                 │  │
│  │  - Orchestrate domain services                         │  │
│  │  - Transaction boundaries                              │  │
│  │  - DTO composition                                     │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Domain Services (Domain layer)                        │  │
│  │  - Pure business rules                                 │  │
│  │  - No I/O, no transport awareness                      │  │
│  │  - Subject-agnostic core                               │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Repositories (Persistence layer)                      │  │
│  │  - Aggregate persistence                               │  │
│  │  - Query encapsulation                                 │  │
│  │  - Single-writer enforcement                           │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │  SQL / Redis
┌─────────────────────────────────────────────────────────────┐
│  Infrastructure                                              │
│  - PostgreSQL (primary)                                      │
│  - Redis (cache, rate-limit counters, queue backend)         │
│  - Object storage (explanations, diagrams)                   │
│  - Sandbox runtime (code execution)                          │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────────┐
│  External Services                                           │
│  - OAuth providers (Google, GitHub)                          │
│  - Payment provider (Stripe)                                 │
│  - Email/SMS providers                                       │
│  - AI providers (authoring-time only, never runtime)         │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Frontend Boundary

The frontend communicates with the backend exclusively through the documented API surface. No frontend code makes direct database calls, no frontend code imports backend domain modules, and no frontend code is permitted to construct business rules that the backend also implements. The frontend's job is to render state and capture user intent; the backend's job is to interpret intent and update state. This separation is enforced by generating the frontend API client from the backend's OpenAPI spec, so the frontend literally cannot call an endpoint the backend has not declared.

### 8.3 Backend Layers

The backend is organized in four layers, each with a single responsibility. Dependencies flow inward: outer layers depend on inner layers, never the reverse.

**Controllers** (API layer) handle HTTP transport. They parse requests, validate input shape (using Pydantic schemas), invoke a Use Case Service, and serialize the response. Controllers contain no business logic. If a controller has an `if` statement that is not about input validation or HTTP status selection, it is in the wrong layer.

**Use Case Services** (Application layer) orchestrate domain services to fulfill a use case. They define transaction boundaries, compose multiple domain services when a use case spans contexts, and assemble DTOs for the response. For example, the `StartStudySession` use case calls the Identity service (verify user), the Learning service (resolve active session), the Scheduling service (build initial queue), and the Content service (fetch first Question's rendering data), then composes the result into a DTO. Use Case Services are the unit of transactional integrity.

**Domain Services** (Domain layer) implement pure business rules. The Mastery Engine, the Scheduler, and the Question Factory live here. Domain Services have no I/O awareness — they accept inputs, return outputs, and never touch the database or the network directly. This purity is what makes them testable in isolation and what allows them to be replaced (e.g., the deterministic Mastery Engine replaced by an ML model) without rippling changes.

**Repositories** (Persistence layer) persist and retrieve aggregates. Each aggregate has exactly one Repository, and each Repository is the single writer for its aggregate. Repositories encapsulate all SQL; no other layer is permitted to issue SQL. This restriction is enforced by code review and by linting rules that forbid SQL strings outside the repository package.

### 8.4 DTOs and Validation

Data Transfer Objects are the wire representation of data crossing layer boundaries. There are three categories:

- **Request DTOs** — the shape of data the frontend sends. Validated by Pydantic at the Controller boundary; invalid requests are rejected with 422 before any Use Case logic runs.
- **Response DTOs** — the shape of data the frontend receives. Constructed by Use Case Services; never the raw domain model. This decoupling allows the domain model to evolve without breaking the API contract.
- **Internal DTOs** — the shape of data passed between Use Case Services and Domain Services. These are typed but not serialized; they exist for type safety and clarity.

Validation is **Pydantic-everywhere**. Request DTOs use Pydantic for shape validation; Domain Services use Pydantic or `dataclass` for invariants; Repositories use Pydantic for row-to-aggregate mapping. This consistency eliminates the entire class of bugs where input validation at the boundary disagrees with internal invariants.

### 8.5 Exception Handling

Exceptions are handled at three layers:

- **Domain exceptions** — raised by Domain Services when a business rule is violated (e.g., `ConceptCycleError` when a new dependency would create a cycle). These are caught by Use Case Services and translated to HTTP-level responses.
- **Use case exceptions** — raised by Use Case Services when an orchestration-level invariant is violated (e.g., `ConcurrentSessionError` when a user tries to start two sessions). Caught by Controllers and translated to 4xx responses with structured error bodies.
- **Infrastructure exceptions** — raised by Repositories or external clients (e.g., database connection lost, OAuth provider down). Caught by a global middleware that logs the error, masks internal details, and returns a 5xx response with a correlation ID.

Every error response carries a correlation ID and a stable error code. The error code is part of the API contract; the frontend may branch on it. The correlation ID is for support and forensics.

### 8.6 Dependency Injection

The backend uses FastAPI's `Depends` for dependency injection at the Controller boundary and a lightweight DI container (or manual constructor injection) for wiring Use Case Services and Domain Services. The DI graph is **explicit and testable**: every service declares its dependencies as constructor parameters, and tests substitute fakes by constructing the service with different dependencies. No service uses module-level singletons or hidden global state. This discipline is what makes the Loop testable end-to-end with deterministic fakes for the Mastery Engine, Scheduler, and Question Factory.

### 8.7 Cross-Cutting Concerns

Cross-cutting concerns (authentication, authorization, rate limiting, audit logging, request tracing) are implemented as middleware and decorators, not as inline logic in Controllers or Services. A Controller method that needs authentication declares it via a `Depends(current_user)` parameter; the auth middleware resolves the JWT, fetches the user, and injects it. A Controller method that needs rate limiting declares it via a decorator; the rate-limit middleware enforces the limit. This keeps business logic free of cross-cutting noise.

### 8.8 API Versioning

The API is versioned at the URL prefix (`/api/v1/...`). Breaking changes require a new major version; both versions run in parallel until the old one is deprecated. Non-breaking changes (additive fields, new endpoints) do not require a version bump. Deprecation follows a published schedule: a deprecated version is supported for at least 6 months after its successor ships, with a sunset date communicated through the API response headers.

---

## Section 9 — Frontend Architecture

The frontend is built with Next.js (App Router) and TypeScript, styled with Tailwind CSS. Its design obeys one rule above all others: **every screen answers one question**. The dashboard answers "what should I study next?". The learning session answers "what is my answer to this question?". The progress page answers "how am I doing over time?". Settings, admin, and supporting pages are scoped to their own single questions. Complexity is pushed to the backend; the frontend is responsible for clarity, not for business rules.

### 9.1 Routing

Routing follows Next.js App Router conventions with a route tree that mirrors the user's mental model of the product.

```
/                            → redirect to /dashboard or /auth/login
/auth/login                  → email/password + OAuth
/auth/register               → signup
/auth/recover                → password recovery
/auth/oauth/callback         → OAuth redirect target
/dashboard                   → "what next?" landing
/session/[id]                → active learning session
/session/[id]/results        → end-of-session summary
/progress                    → mastery-over-time, weak concepts
/progress/[subject]          → per-subject breakdown
/paths                       → learning path selection
/paths/[subject]/[pathId]    → path detail
/settings                    → profile, preferences, notifications
/settings/billing            → subscription, invoices
/admin                       → admin portal root (separate auth gate)
/admin/content               → content management
/admin/users                 → user support
/admin/analytics             → system analytics
/admin/audit                 → audit log
```

The `/admin` subtree is **code-split and lazily loaded** so that admin bundle weight never reaches learner-facing users. Admin routes use a separate middleware that requires an admin-role claim; learner JWTs cannot reach admin controllers regardless of frontend routing.

### 9.2 Layouts

Next.js layouts are used to factor shared chrome. There are three layout roots:

- **Public layout** — `/auth/*`. Minimal chrome: logo, no nav. Used for login, register, recover.
- **App layout** — `/dashboard`, `/session/*`, `/progress/*`, `/paths/*`, `/settings/*`. Full chrome: top nav (logo, subject switcher, streak indicator, user menu), no left rail by default. The learning session is the only route that hides the top nav, to minimize distraction during practice.
- **Admin layout** — `/admin/*`. Separate chrome: admin sidebar, admin top bar, admin user menu. Visually distinct from the app layout to prevent admin-from-app confusion.

Layouts are server components by default. Client-side interactivity is confined to specific components within a layout, not to the layout itself.

### 9.3 Authentication Flow

The authentication flow is:

1. **Unauthenticated user** visits any `/app` route. Middleware redirects to `/auth/login`.
2. **Login** — user enters credentials or clicks OAuth. Frontend posts to the login endpoint; backend returns access token (short-lived, in-memory) and refresh token (long-lived, in an HttpOnly secure cookie).
3. **Access token storage** — the access token lives in JavaScript memory only, never in localStorage or a cookie. This limits the blast radius of XSS to the current session.
4. **Refresh flow** — when an API call returns 401, the frontend attempts a single refresh using the HttpOnly cookie. If refresh succeeds, the original call is retried. If refresh fails, the user is redirected to `/auth/login`.
5. **Logout** — frontend calls logout endpoint (revokes refresh token), clears in-memory access token, redirects to `/auth/login`.
6. **Session list** — `/settings/security` shows active sessions; user can revoke any session.

### 9.4 Dashboard

The dashboard is the single most important screen. Its job is to answer "what should I study next?" in under three seconds of cognitive load. The dashboard consists of:

- **Primary action card** — a single large card with the recommended next action ("Continue Python session," "Review 5 due concepts," "Start diagnostic"). One click starts the action.
- **Streak and recent activity** — a compact strip showing current streak, last study date, and this week's total time.
- **Weak concept preview** — the top 3 weak concepts with a one-click "drill these" action.
- **Subject switcher** — for multi-tenant users, a compact switcher between enrolled subjects.

Nothing else. The dashboard refuses to grow into a feature showcase. Anything that does not serve "what next?" is moved to `/progress` or `/settings`.

### 9.5 Learning Session

The learning session is the Loop's frontend projection. It is a **single full-viewport client component** that manages local UI state (current question, answer draft, time elapsed) and synchronizes with the backend through the Loop API. Key design decisions:

- **Pre-fetch** — when a question is displayed, the next question's data is pre-fetched so that advancing is instant.
- **Optimistic UI for answer submission** — the learner's answer is shown as "submitted" immediately; the backend's evaluation arrives asynchronously. This decouples perceived latency from backend processing time.
- **Keyboard-first** — every interaction has a keyboard shortcut: number keys for multiple-choice, `Cmd/Ctrl+Enter` for submission, `H` for hint, `E` for explanation. The mouse is optional.
- **No nav during session** — the top nav is hidden; the only exits are "End session" (with confirmation) and completing the session goal.
- **State recovery** — if the user reloads mid-session, the session resumes from the last unanswered question. State lives on the backend, not in the URL.

### 9.6 Progress

The progress page shows mastery-over-time, weak concepts, retention curves, and per-subject breakdown. It is **read-only** — no learning actions happen here. The page is server-rendered for the initial load and client-hydrated for interactive filtering. Charts are rendered with a lightweight charting library (no animation libraries; progress data is for review, not entertainment).

### 9.7 Settings

Settings is divided into: profile (name, email, timezone), preferences (default subject, daily goal, notification timing), security (password, sessions, MFA), and billing (subscription, invoices, payment methods). Each subsection is a single form; no settings page mixes concerns.

### 9.8 Admin

Admin is described in Section 2.11. From a frontend architecture perspective, admin is a separate route tree with a separate layout, separate auth middleware, and a separate bundle. Admin components are not imported by app components, and vice versa.

### 9.9 Component Hierarchy

Components are organized in three tiers:

- **Primitive components** — buttons, inputs, cards, modals, tooltips. Subject-agnostic, layout-agnostic. Live in `/components/ui`.
- **Composite components** — combinations of primitives that form a recognizable unit (question card, mastery gauge, progress chart, session header). Live in `/components/<feature>`.
- **Route components** — page-level components that compose composites into a screen. Live in the App Router `page.tsx` files.

The hierarchy is strict: primitives never import composites, composites never import route components. This discipline keeps the dependency graph a DAG and prevents the "spaghetti imports" anti-pattern.

### 9.10 State Management

State management is split by purpose:

- **Server state** — managed by a data-fetching library (React Query / SWR or Next.js native fetch extensions). Cached, revalidated, invalidated by mutation. The source of truth is the backend.
- **URL state** — filters, pagination, current subject, current tab. Lives in the URL so it is shareable, bookmarkable, and survives reloads.
- **Local UI state** — answer drafts, modal open/closed, current tab within a single page. Lives in `useState` / `useReducer`. Never in a global store.
- **Global app state** — current user, current tenant. Lives in a small client-side context (or React Context), hydrated from the session endpoint on app load.

No Redux, no MobX, no global stores beyond the small session context. The system is too small to justify a global state library, and the discipline of pushing state to the server or the URL keeps the frontend simple.

### 9.11 Performance Budget

The frontend has a documented performance budget:

- **LCP under 2.0s** on the dashboard at the 75th percentile on a mid-tier mobile network.
- **TBT under 200ms** on the dashboard.
- **Bundle size** — the learner-facing bundle (excluding admin) must stay under 250KB gzipped. Admin is allowed a separate budget.
- **No render-blocking third-party scripts** on learner-facing routes. Analytics scripts are loaded with `async` and never block first paint.

Performance is a feature. The dashboard that loads slowly is a dashboard that learners abandon. The performance budget is enforced in CI by Lighthouse checks against the staging deployment.

---

## Section 10 — Backend Architecture

The backend is a single FastAPI application organized in Clean Architecture layers. This section describes the layers, their contents, and the conventions that govern them. Layer responsibilities are summarized in Section 8; this section describes the engineering expectations within each layer.

### 10.1 Layers

```
backend/
├── api/                  # Controllers (HTTP transport)
│   ├── v1/
│   │   ├── routes/       # Route definitions, thin
│   │   └── dependencies.py
│   └── middleware/       # Auth, rate-limit, error, logging
├── application/          # Use Case Services
│   ├── identity/
│   ├── learning/
│   ├── assessment/
│   ├── content/
│   ├── scheduling/
│   ├── analytics/
│   ├── billing/
│   └── administration/
├── domain/               # Domain Services + Aggregates + Events
│   ├── identity/
│   ├── learning/
│   ├── assessment/
│   ├── mastery/          # The Mastery Engine lives here
│   ├── content/
│   ├── scheduling/
│   ├── analytics/
│   ├── billing/
│   └── shared/           # Shared kernel: events, types, base classes
├── infrastructure/       # Repositories, external clients, persistence
│   ├── persistence/
│   │   ├── models/       # ORM models (SQLAlchemy or similar)
│   │   ├── repositories/ # Repository implementations
│   │   └── mappers/      # ORM ↔ Domain aggregate mappers
│   ├── cache/            # Redis client
│   ├── events/           # Event bus implementation (outbox + dispatcher)
│   ├── external/         # OAuth, Stripe, email, etc.
│   └── sandbox/          # Code execution sandbox
├── config/               # Configuration loading, env parsing
├── main.py               # App factory, wiring, lifespan
└── tests/                # Mirror the structure above
```

This layout is **non-negotiable**. New code is placed in the layer that matches its responsibility; cross-layer shortcuts are rejected at code review.

### 10.2 Controllers

Controllers are thin. A controller method:

1. Receives the validated Request DTO (Pydantic validation has already run).
2. Resolves dependencies (current user, current tenant, services) via `Depends`.
3. Calls exactly one Use Case Service method.
4. Receives a Response DTO.
5. Returns the DTO (FastAPI serializes it).

A controller method that contains a loop, a database call, a service-to-service call, or a conditional beyond HTTP-status selection is wrong. Controllers exist to translate HTTP into Use Case calls and Use Case results into HTTP.

### 10.3 Use Case Services

Use Case Services are the orchestration layer. Each use case is a class with a single public method (e.g., `StartStudySession.execute(input)`). The class declares its dependencies as constructor parameters; the DI container wires them. The `execute` method:

1. Loads required aggregates via Repositories.
2. Authorizes the operation (the use case is the last line of defense; even if the controller authorized the request, the use case re-checks that the user may perform this operation on these aggregates).
3. Calls Domain Services to perform business logic.
4. Persists changes via Repositories within a transaction.
5. Publishes domain events via the event bus (through the outbox, in the same transaction).
6. Returns a Response DTO.

Use Case Services are **idempotent where possible**. For example, `SubmitAnswer` is idempotent on the request id: a retry with the same request id returns the same result without recording a duplicate Attempt.

### 10.4 Domain Services

Domain Services contain pure business logic. The Mastery Engine, the Scheduler, and the Question Factory are Domain Services. They:

- Accept typed inputs (domain aggregates, value objects, primitives).
- Return typed outputs (new aggregate states, decisions, events).
- Perform no I/O. They do not call Repositories, they do not call external services, they do not publish events. The Use Case Service does that.
- Are deterministic given inputs (the Mastery Engine's determinism is mandatory; the Scheduler's determinism is mandatory given an explicit seed).

This purity is what allows the Mastery Engine to be tested exhaustively without a database, what allows it to be replayed against historical Attempts, and what allows it to be replaced by an ML model later without modifying callers.

### 10.5 Domain Models (Aggregates and Value Objects)

The domain model is expressed as aggregates and value objects, not as ORM models. Aggregates are consistency boundaries: a save of an aggregate is atomic. Value objects are immutable and compared by value. The domain model lives in `/domain/<context>/` and has no dependency on the ORM, the web framework, or any infrastructure.

This separation is what allows the domain model to evolve independently of the database schema. A schema change touches the ORM model and the mapper; the domain model is unaffected. A domain model change touches the domain model and the mapper; the ORM model may or may not change.

### 10.6 Repositories

Repositories persist and retrieve aggregates. Each aggregate has exactly one Repository interface (defined in `/domain/<context>/`) and one implementation (defined in `/infrastructure/persistence/repositories/`). The interface is what Domain Services and Use Case Services depend on; the implementation is what the DI container wires.

A Repository:

- Accepts and returns domain aggregates, never ORM models.
- Encapsulates all SQL for its aggregate.
- Enforces the single-writer principle: no other Repository writes the same table.
- Is the unit of transactional integrity for its aggregate.

Repositories do not call each other. A use case that needs to load two aggregates loads them through two separate Repository calls and composes them in the Use Case Service.

### 10.7 DTOs

DTOs are Pydantic models. There are three categories (Request, Response, Internal — see Section 8.4). DTOs live alongside the Use Case Service that produces or consumes them. Naming convention: `StartSessionRequest`, `StartSessionResponse`. DTOs are versioned with the API; a v2 of an endpoint may use a v2 DTO.

### 10.8 Validation

Validation is layered:

- **Shape validation** at the Controller boundary by Pydantic Request DTOs. Rejects malformed input with 422.
- **Invariant validation** inside Domain Services and aggregates. A `Concept` aggregate may reject a name that is empty or too long. These raise domain exceptions, caught by Use Case Services.
- **Authorization validation** inside Use Case Services. The use case verifies that the current user may perform the operation on the target aggregate. Raises an authorization exception, caught and translated to 403.

Validation is never duplicated across layers without reason. If a DTO rejects empty strings and the aggregate also rejects empty strings, that is intentional defense in depth. If the DTO enforces a business rule (e.g., "passwords must contain a digit"), that is wrong — the rule belongs in the domain.

### 10.9 Exception Handling

Exceptions follow Section 8.5. The concrete pattern:

- Domain Services raise `DomainError` subclasses.
- Use Case Services catch `DomainError` and either translate to `UseCaseError` (for 4xx responses) or re-raise (for 5xx, when the error is unexpected).
- A global middleware catches `UseCaseError` and returns a structured 4xx response with error code and message.
- A global middleware catches all other exceptions, logs them with a correlation ID, and returns a 500 with the correlation ID only.

The error response body is structured: `{ "error": { "code": "CONCEPT_CYCLE", "message": "...", "correlation_id": "..." } }`. The error code is part of the API contract.

### 10.10 Dependency Injection

Dependency injection is **constructor-based**. Every service class declares its dependencies as typed constructor parameters. The DI container (or manual wiring in `main.py`) constructs services with their dependencies. Tests substitute fakes by constructing the service directly with fake dependencies.

FastAPI's `Depends` is used at the Controller boundary to inject Use Case Services and the current user. Below the Controller, everything is plain Python constructor injection. This keeps the domain layer framework-free and testable.

### 10.11 Background Workers

Background workers consume the event bus and execute asynchronous side effects: dispatching notifications, updating analytics projections, sending webhook events to external systems. Workers are **idempotent** — they may receive the same event twice (at-least-once delivery) and must produce the same result. Workers are **separate processes** from the API, deployed together but scaled independently. A worker failure never blocks an API request.

### 10.12 Configuration

Configuration is loaded from environment variables at startup, parsed by Pydantic Settings (or equivalent), and injected via DI. No service reads environment variables directly at runtime. Configuration is **typed** and **fail-fast**: an invalid configuration prevents the application from starting, rather than failing silently later.

---

## Section 11 — Data Flow

This section describes how data moves through the Engine for the most important flows. Diagrams are ASCII for portability; the production engineering wiki will maintain Mermaid equivalents.

### 11.1 Authentication Flow

```
Browser                Next.js              FastAPI              PostgreSQL
   │                      │                     │                     │
   │──POST /auth/login───▶│                     │                     │
   │                      │──POST /api/v1/auth──▶│                     │
   │                      │                     │──verify credential─▶│
   │                      │                     │◀─user + hash────────│
   │                      │                     │                     │
   │                      │                     │  issue JWT access   │
   │                      │                     │  + refresh token    │
   │                      │◀─access + refresh───│                     │
   │                      │  (refresh in        │                     │
   │                      │   HttpOnly cookie)  │                     │
   │◀─200 + redirect──────│                     │                     │
   │  (access token in    │                     │                     │
   │   JS memory)         │                     │                     │
```

### 11.2 Learning Loop Data Flow

```
Browser          Next.js           FastAPI (Learning     Mastery      Scheduler    Question
                                    Use Case Service)     Engine                    Factory
   │                │                     │                   │             │            │
   │──GET /session──▶│                     │                   │             │            │
   │                │──GET /api/v1/       │                   │             │            │
   │                │   sessions/active──▶│                   │             │            │
   │                │                     │──load user,       │             │            │
   │                │                     │  active session,  │             │            │
   │                │                     │  schedule─────────▶─────────────│            │
   │                │                     │                   │             │            │
   │                │                     │                   │  compute   │            │
   │                │                     │                   │  queue ────▶│ instantiate│
   │                │                     │                   │             │  questions │
   │                │                     │◀──queue + first ──│◀────────────│◀───────────│
   │                │                     │   question        │             │            │
   │                │◀──session dto───────│                   │             │            │
   │◀─render────────│                     │                   │             │            │
   │                │                     │                   │             │            │
   │──submit answer─▶│                     │                   │             │            │
   │                │──POST /api/v1/      │                   │             │            │
   │                │   attempts──────────▶│                   │             │            │
   │                │                     │──score answer     │             │            │
   │                │                     │  (Assessment       │             │            │
   │                │                     │   Domain Service) │             │            │
   │                │                     │──write Attempt ──▶│             │            │
   │                │                     │  + outbox event   │             │            │
   │                │                     │                   │──consume   │            │
   │                │                     │                   │  AttemptRecorded         │
   │                │                     │                   │──recompute │            │
   │                │                     │                   │  MasteryScore            │
   │                │                     │                   │──write Score            │
   │                │                     │                   │  + Review   │            │
   │                │                     │                   │──publish                │
   │                │                     │                   │  MasteryUpdated ────────▶│
   │                │                     │                   │             │──recompute │
   │                │                     │                   │             │  queue     │
   │                │                     │◀──next question───│◀────────────│            │
   │                │◀──response +        │                   │             │            │
   │                │   explanation───────│                   │             │            │
   │◀─render next───│                     │                   │             │            │
```

Key observations:

- The **synchronous path** (Steps 4–7 of Section 5) is: score → write Attempt → recompute Mastery → recompute Queue → return next question. This entire path is the latency-critical surface of the Engine and must complete in under 200ms at the median.
- The **asynchronous path** (analytics, notifications) is decoupled via the event bus and does not affect response latency.
- The Mastery Engine update MAY be performed synchronously (within the request) or asynchronously (via event consumption) depending on the configured consistency mode. The default is synchronous for the active concept and asynchronous for downstream analytics. This tradeoff is documented in Section 13.

### 11.3 Content Publishing Flow

```
Author          Admin UI         Content         Publishing        Event Bus       Analytics
                                 Use Case        Worker
   │                │             │                │                 │                │
   │──edit draft───▶│             │                │                 │                │
   │                │──save──────▶│                │                 │                │
   │──submit review▶│             │                │                 │                │
   │                │──request───▶│                │                 │                │
   │                │  peer       │                │                 │                │
   │                │  review     │                │                 │                │
   │◀─review feedback             │                │                 │                │
   │──revise───────▶│             │                │                 │                │
   │──approve──────▶│             │                │                 │                │
   │                │──publish───▶│                │                 │                │
   │                │             │──create new    │                 │                │
   │                │             │  ContentVersion│                 │                │
   │                │             │  atomically    │                 │                │
   │                │             │──write outbox──│                 │                │
   │                │             │  event         │                 │                │
   │                │             │                │──consume───────▶│                │
   │                │             │                │  ContentPublished│               │
   │                │             │                │                 │──invalidate───▶│
   │                │             │                │                 │  caches        │
   │                │             │                │                 │──rebuild      │
   │                │             │                │                 │  projections  │
```

### 11.4 Background Job Flow

```
API Request     Outbox Table     Event Dispatcher     Worker Pool     External Service
   │                │                    │                   │                │
   │──write row +   │                    │                   │                │
   │  outbox event  │                    │                   │                │
   │  (txn)────────▶│                    │                   │                │
   │                │                    │                   │                │
   │◀─response──────│                    │                   │                │
   │                │                    │                   │                │
   │                │◀─poll / LISTEN─────│                   │                │
   │                │──deliver event─────▶                   │                │
   │                │                    │──enqueue job──────▶                │
   │                │                    │                   │──process job──▶│
   │                │                    │                   │◀─result───────│
   │                │                    │                   │──ack job       │
```

Background jobs are persisted (in a jobs table or a Redis stream), retried with exponential backoff, and dead-lettered after a configurable failure count. The dead-letter queue is monitored and drained by an on-call rotation.

### 11.5 Analytics Read Flow

```
Browser           Next.js (Server      FastAPI              Read Replica /         Materialized
                  Component)            Analytics API        Operational DB         Views
   │                  │                     │                      │                  │
   │──GET /progress───▶                     │                      │                  │
   │                  │──GET /api/v1/       │                      │                  │
   │                  │   analytics/        │                      │                  │
   │                  │   me/progress──────▶│                      │                  │
   │                  │                     │──read materialized──▶│                  │
   │                  │                     │  view (per-user,     │                  │
   │                  │                     │   low-latency)       │                  │
   │                  │                     │◀─rows────────────────│                  │
   │                  │◀─progress dto───────│                      │                  │
   │◀─render──────────│                     │                      │                  │
```

Per-user analytics reads hit materialized views on the operational database (or a read replica). Aggregate analytics reads hit a derived analytics store refreshed by background jobs. This separation prevents aggregate queries from competing with the Loop for database resources.

---

## Section 12 — Security

Security is designed in layers, with each layer defending against a different threat. No single layer is assumed sufficient; the Engine is secure only if all layers hold.

### 12.1 Authentication

Authentication is JWT-based with the following properties:

- **Access tokens** are short-lived (15 minutes), signed with an asymmetric algorithm (RS256 or EdDSA), and contain only the user id, tenant, and role claims. They are never stored in cookies or localStorage; they live in JavaScript memory only.
- **Refresh tokens** are long-lived (30 days, sliding), random opaque strings stored in an HttpOnly, Secure, SameSite=Lax cookie. They are stored as a salted hash in the database so that a database leak does not immediately compromise active sessions. They are rotated on every use; a stolen-and-replayed refresh token is detected and revokes the entire session family.
- **OAuth** is supported for Google and GitHub. OAuth links to a User via the UserCredential entity. A user may have both a password and OAuth linked; either may authenticate the same User.
- **MFA** is supported via TOTP. MFA is required for admin accounts and optional for learner accounts.
- **Recovery** is via emailed magic link, single-use, short expiry (15 minutes). The link is delivered to the verified email only; no SMS recovery.

### 12.2 Authorization

Authorization is **role-based** at the coarse grain and **resource-based** at the fine grain. Roles are: `learner`, `author`, `editor`, `admin`. Resources are: a User's own data, a Subject's content, the system itself. A request is authorized if (a) the user's role permits the operation class AND (b) the user owns or has been granted access to the specific resource.

Authorization is enforced at **two layers**: at the Controller (via a `Depends(require_role("author"))` decorator) and inside the Use Case Service (which re-checks resource ownership). The double check is defense in depth; either layer alone is insufficient.

### 12.3 Rate Limiting

Rate limiting is enforced at the API gateway / middleware layer, keyed by user id (for authenticated requests) and by IP (for unauthenticated requests). Limits are per-endpoint and per-window:

- **Authentication endpoints** (login, register, recover) — strict limits to prevent credential stuffing.
- **Submit Answer** — moderate limit to prevent abuse without affecting real learners.
- **Read endpoints** — generous limits, primarily for cost control.
- **Admin endpoints** — strict limits per admin user.

Rate-limit counters live in Redis for low-latency increment and global consistency. A rate-limited response is 429 with a `Retry-After` header. Repeated rate-limit violations trigger an alert and may temporarily lock the account.

### 12.4 Audit Logging

Every privileged action is recorded in the AuditLog:

- Content publishing, deprecation, version rollback.
- User support actions (password reset, entitlement override, refund).
- Admin configuration changes (rate-limit adjustments, feature flags).
- Authentication events (login, logout, failed login, MFA enable/disable).
- Data export and deletion (GDPR-relevant).

Each audit entry records: timestamp, actor (user id, role), action, target (resource type and id), request metadata (IP, user-agent, correlation id), and outcome (success or failure with reason). The AuditLog is append-only, retained for at least 2 years, and exported daily to cold storage for long-term retention.

### 12.5 Input Validation

All input is validated at the Controller boundary by Pydantic Request DTOs. Validation covers:

- **Type correctness** — strings are strings, integers are integers, dates are dates.
- **Length and range** — strings have max lengths, integers have ranges, dates are bounded.
- **Format** — emails, URLs, UUIDs, and other structured strings are validated by format.
- **Whitelisting** — enumerated fields accept only documented values.
- **Rejection of unexpected fields** — the request body must match the DTO exactly; extra fields are rejected (not silently ignored).

Validation is the first line of defense against injection. After validation, the Use Case Service treats input as trusted within its declared contract. Defense in depth (parameterized queries, ORM escaping, output encoding on the frontend) handles the residual risk.

### 12.6 Secrets Management

Secrets (database passwords, OAuth client secrets, JWT signing keys, third-party API keys) are:

- **Never committed to source control.** A pre-commit hook scans for high-entropy strings.
- **Loaded from environment variables** in all environments. Local development uses a `.env` file that is gitignored and never shared.
- **Stored in a secrets manager** (AWS Secrets Manager, GCP Secret Manager, or HashiCorp Vault) in production. The application fetches secrets at startup; they do not live on disk.
- **Rotated on a schedule.** JWT signing keys are rotated quarterly; database passwords annually; OAuth secrets when the provider rotates them.
- **Accessed with least privilege.** Each service has access only to the secrets it needs; an Admin service can read all secrets, a Learner-facing service can read only its own.

### 12.7 Transport and Storage Security

- **HTTPS everywhere.** HTTP requests are redirected to HTTPS; HSTS is enforced.
- **TLS 1.2 minimum** on all connections, including database and Redis.
- **Encryption at rest** for the database, the cache, and object storage. Encryption keys are managed by the cloud KMS.
- **Field-level encryption** for PII (email, name) at rest, using envelope encryption with KMS-managed keys. This limits the blast radius of a database read compromise.
- **Backup encryption** — all backups are encrypted with separate keys.

### 12.8 GDPR Considerations

The Engine is designed for GDPR compliance:

- **Lawful basis** — consent for marketing emails, contract for service delivery, legitimate interest for security logging.
- **Data minimization** — the Engine collects only data needed for the learning loop and security. No tracking pixels, no third-party analytics that export PII.
- **Right to access** — `/settings/privacy` exposes a "Download my data" action that produces a complete export of the user's data within 30 days.
- **Right to erasure** — `/settings/privacy` exposes a "Delete my account" action. Deletion is irreversible after a 14-day grace period. Deletion anonymizes the user's Attempts (retains the aggregate for analytics) and removes PII. The retention of anonymized attempt data is documented in the privacy policy.
- **Consent management** — consent records are timestamped and versioned. Withdrawal of consent triggers immediate cessation of the relevant processing.
- **Data residency** — the Engine deploys to a single region (EU or US) per tenant configuration, with no cross-region replication of PII.
- **Breach notification** — incident response runbook includes GDPR-mandated 72-hour notification to authorities and affected users.

### 12.9 Code Execution Sandbox

Code-execution Questions (essential for Python interview prep) require the Engine to execute learner-submitted code. This is the single highest-risk surface in the system. The sandbox:

- Runs in an isolated container with no network access.
- Has a strict CPU and memory limit.
- Has a strict execution time limit.
- Runs as a non-root user with minimal filesystem permissions.
- Is destroyed after each execution (no reuse between learners).
- Is deployed on a separate node pool from the API and database, so a sandbox compromise cannot reach learner data.

The sandbox is the one place where the Engine accepts the cost of strong isolation in exchange for security. The cost is justified because the alternative — executing learner code on shared infrastructure — is unacceptable.

---

## Section 13 — Scalability

The Engine is designed to scale from a few hundred early users to millions of learners over the next decade. This section describes the scaling strategy at each layer and the triggers that justify moving from the simple path to the more complex one.

### 13.1 Horizontal Scaling

The backend is **stateless**. No request relies on in-process state; all state lives in PostgreSQL or Redis. This allows the API to scale horizontally by adding instances behind a load balancer. The same property applies to background workers — they scale horizontally by adding consumer processes.

The stateless invariant is enforced by code review: any code that stores request-relevant state in a module-level variable, a thread-local, or an in-process cache is rejected. Caching that benefits from being local to a process (e.g., a small LRU for hot content) is permitted but must be treated as a hint, not as a source of truth — the system must remain correct if the cache is empty.

The database does not scale horizontally in the same way. PostgreSQL scales vertically (bigger instance) up to a point, then through read replicas, then through partitioning (Section 13.3). Sharding is a last resort, deferred until partitioning is exhausted, because sharding complicates every query that touches the shard key.

### 13.2 Caching

Caching is layered, with explicit invalidation rules:

- **Content cache (Redis)** — Concepts, Templates, Explanations, and Content Versions are cached by their immutable identifier. Cache invalidation is trivial because content is versioned: a new version produces a new cache key; old keys age out naturally. TTL is generous (hours); invalidation on publish is explicit.
- **Mastery cache (Redis)** — a short-lived (60-second) cache of a user's Mastery Scores for the active Subject. Invalidated on any Attempt. This cache is purely an optimization; the Mastery Engine is the source of truth.
- **Queue cache (Redis)** — the Practice Queue for an active StudySession is cached for the duration of the session. Invalidated when the queue is regenerated.
- **HTTP cache (CDN)** — static assets and any public, anonymous-eligible pages are cached at the CDN. Authenticated responses are never cached at the CDN.

Caching discipline: every cache entry has a documented invalidation trigger. A cache without an invalidation rule is a bug waiting to happen. The team rejects PRs that introduce caches without invalidation.

### 13.3 Database Optimization

The database is the long-term scaling bottleneck. The strategy:

- **Indexing** — every query path has a documented index. Index choice is reviewed at PR time. The Attempts table is the highest-volume table and has indexes on (user_id, created_at), (concept_id, created_at), and (content_version_id) for analytics.
- **Partitioning** — the Attempts table is partitioned by time (monthly partitions) once it crosses ~100M rows. Partition pruning makes historical analytics queries cheap. Old partitions can be moved to colder storage without affecting the hot path.
- **Read replicas** — a read replica serves analytics queries and any read endpoint that does not require strict consistency. Writes go to the primary. Replication lag is monitored; the system falls back to the primary if lag exceeds a threshold.
- **Connection pooling** — PgBouncer (or equivalent) sits between the API and the database, pooling connections so that API process count does not translate directly to database connection count.
- **Query budgets** — every endpoint has a documented query budget. Slow queries (over 100ms) are logged; queries over 1s trigger an alert. The query budget is enforced by monitoring, not by code, but violations are tracked and resolved.

### 13.4 Background Jobs

Background jobs handle anything that does not need to be in the request path:

- **Notification dispatch** — email, push, in-app.
- **Analytics projection rebuilds** — materialized view refreshes.
- **Mastery recalculation on algorithm version change** — when a new Mastery Engine version ships, all users' Mastery Scores are recomputed in the background over a period of days.
- **Content quality monitoring** — nightly jobs that compute discrimination, distractor analysis, and explanation effectiveness metrics.
- **Backup and export** — daily database backups, daily audit log export, on-demand user data export.

Jobs are persisted (PostgreSQL-based queue for transactional correctness, Redis Streams for high-throughput cases), retried with exponential backoff, and dead-lettered after configurable failure counts. Workers scale horizontally; the queue depth is the scaling signal.

### 13.5 Future Microservices

The Engine is a modular monolith today. Microservices are deferred until a specific, measured requirement justifies the operational cost. The triggers that would justify extraction:

- **The Mastery Engine** is extracted if its computation cost dominates API latency and benefits from independent scaling. The pure-function property (Section 6.8) makes this extraction straightforward.
- **The Question Factory + sandbox** is extracted early because the sandbox has different security and scaling properties from the rest of the API. This extraction is likely in Phase 2.
- **Analytics** is extracted if the analytics query load begins to affect the operational database despite read replicas. Extraction moves analytics to its own database derived from the operational one via change-data-capture.
- **Billing** is extracted if the team needs to integrate multiple payment providers or handle complex invoicing that warrants independent deployment.

Each extraction is a deliberate decision, documented in an Architecture Decision Record, with the migration plan and the rollback plan.

### 13.6 Search

Search is initially served by PostgreSQL full-text search over Concepts, Templates, and Learning Objectives. This is sufficient for the content catalog at the scale of a single Subject.

When the catalog grows to tens of thousands of items across multiple Subjects, or when search latency exceeds 200ms at the 99th percentile, the search workload moves to a dedicated search engine (Elasticsearch, OpenSearch, or a managed equivalent). The migration is a read-side concern only; the write side continues to write to PostgreSQL, and a CDC pipeline updates the search index.

Search for learner-facing content (Concepts, Objectives) is separated from search for admin content (drafts, review state) because they have different access patterns and access controls.

### 13.7 Analytics at Scale

Per-user analytics (mastery-over-time, retention curves, weak concepts) are computed on-the-fly from the Attempts table, with materialized views for the most common shapes. This scales well because per-user queries touch a single user's rows.

Aggregate analytics (cohort retention, concept difficulty distributions, funnel metrics) are expensive at scale. The strategy:

- **Materialized views** for the most common aggregates, refreshed nightly.
- **A derived analytics store** (a columnar database — BigQuery, Redshift, or ClickHouse) for ad-hoc and exploratory analytics, populated by a CDC pipeline from the operational database.
- **No analytics queries on the operational primary.** This rule is enforced by routing analytics traffic to a dedicated replica or to the derived store.

The derived analytics store is the long-term home for the Engine's data moat. It is the surface against which future ML training is conducted.

### 13.8 AI Integration at Scale

The Engine's AI policy (no runtime AI for learning decisions) is preserved at scale. AI integration at scale means:

- **Authoring assistance** scales horizontally — multiple author sessions can use AI assistance concurrently. The cost is bounded by the authoring rate, not the learner rate.
- **ML training** runs offline against the derived analytics store. Training jobs are batch; they do not affect production.
- **ML inference** (when a future ML Mastery Engine ships) runs in shadow mode initially, with its own infrastructure. Promotion to production is gated by the documented evaluation (Section 6.7).
- **No runtime LLM calls** in the Loop. This is a permanent invariant, not a Phase 1 limitation. The cost, latency, and reproducibility characteristics of runtime LLM calls are incompatible with the Loop's requirements.

### 13.9 Geographic Distribution

Initially, the Engine is deployed in a single region. Multi-region deployment is triggered by:

- A user base that is geographically concentrated in a region far from the primary, producing unacceptable latency.
- A regulatory requirement (e.g., EU data residency) that cannot be met by single-region deployment.

Multi-region deployment is non-trivial because of the database. The strategy is **active-passive with read replicas in remote regions** for reads, with writes always going to the primary region. A full active-active multi-region deployment is deferred until the regulatory or latency requirements force it, and is treated as a major architectural change requiring its own design document.

---

## Section 14 — Engineering Standards

Engineering standards are the substrate on which the architecture rests. A good architecture with poor standards produces a poor system. This section documents the non-negotiable standards for the Engine.

### 14.1 Coding Standards

- **SOLID** — every class has a single responsibility; dependencies target abstractions; no premature generalization but no duplication either.
- **Strong typing** — Python type hints are mandatory in all backend code; TypeScript strict mode is mandatory in all frontend code. CI fails on type errors.
- **Small files** — no file exceeds 400 lines. Files exceeding 300 lines are flagged for review. A file that grows beyond 400 lines is split.
- **Small functions** — no function exceeds 50 lines. Functions exceeding 30 lines are flagged. Complex functions are decomposed.
- **Pure where possible** — Domain Services are pure. Use Case Services are pure except for orchestrated I/O. Side effects live at the edges (Repositories, external clients).
- **No magic** — no `**kwargs` in domain code, no `eval`, no `exec`, no metaclass tricks without justification. Readability beats cleverness.
- **Defensive at boundaries, trusting inside** — input is validated at the Controller; inside the Use Case Service and Domain Service, types are trusted.

### 14.2 Folder Organization

The folder structure is dictated by Clean Architecture (Section 10.1). Within each layer:

- One folder per bounded context.
- One file per aggregate (domain layer) or per use case (application layer).
- One file per Repository (infrastructure layer).
- Tests mirror the source structure.

Cross-context imports are forbidden at the domain layer. The only cross-context communication permitted is through service interfaces (application layer) or domain events.

### 14.3 Naming Conventions

- **Files** — `snake_case.py` for Python, `PascalCase.tsx` for React components, `camelCase.ts` for non-component TypeScript.
- **Classes** — `PascalCase`. Use cases are named `VerbObject` (e.g., `StartStudySession`).
- **Functions** — `snake_case` for Python, `camelCase` for TypeScript.
- **Constants** — `UPPER_SNAKE_CASE`.
- **Database tables** — `snake_case`, plural (e.g., `attempts`, `mastery_scores`).
- **Database columns** — `snake_case`.
- **Domain events** — `VerbNounPastTense` (e.g., `AttemptRecorded`, `MasteryUpdated`, `ContentPublished`).
- **DTOs** — `VerbObjectRequest` / `VerbObjectResponse`.

Naming is enforced by linting (ruff for Python, ESLint for TypeScript) and by code review.

### 14.4 Testing Philosophy

The test pyramid:

- **Unit tests** — the bulk of the suite. Domain Services have near-100% coverage because they are pure functions. Use Case Services are tested with fake Repositories and fake Domain Services.
- **Property-based tests** — the Mastery Engine and the Scheduler are tested with property-based tests (Hypothesis). Properties like "mastery is monotonic in evidence," "scheduler is deterministic given a seed," and "review interval is bounded" are checked across thousands of generated inputs.
- **Integration tests** — Repository implementations are tested against a real PostgreSQL instance (in a Docker container) to catch ORM and SQL errors.
- **Contract tests** — the frontend's API client is generated from the backend's OpenAPI spec, and a contract test verifies that the frontend's expectations match the backend's responses.
- **End-to-end tests** — Playwright tests cover the critical user journeys: signup, study session, progress review, content publish. E2E tests run against a full deployment in CI.
- **Load tests** — the Loop's submit-answer path is load-tested to verify the 200ms median latency target. Load tests run nightly against staging.

Coverage targets: 90% for domain, 80% for application, 70% for infrastructure, 60% for API. Coverage is a hint, not a gate; the gate is the test suite passing, not a coverage number.

### 14.5 Documentation Standards

- **Docstrings** — every public class and function has a docstring. The docstring describes what the function does, not how. The "how" should be obvious from the code.
- **Module-level documentation** — every module has a docstring describing its responsibility and its place in the architecture.
- **Architecture Decision Records (ADRs)** — every architectural decision that is non-obvious or that closes off alternatives is recorded as an ADR in `/docs/adr/`. ADRs are numbered, dated, and immutable once merged; supersession is by a new ADR.
- **OpenAPI** — the backend's OpenAPI spec is the source of truth for the API. The spec is generated from code annotations; no separate hand-maintained spec.
- **README** — every repository has a README that explains how to run the system locally, how to run tests, and where to find the architecture documentation.
- **Runbooks** — every operational procedure (deployment, rollback, incident response, on-call escalation) has a runbook in `/docs/runbooks/`.

### 14.6 Git Workflow

- **Trunk-based development** — short-lived branches merge into `main`. Long-lived feature branches are discouraged.
- **Branch naming** — `<type>/<short-description>` (e.g., `feature/mastery-engine-v2`, `fix/attempts-duplicate`).
- **Commit messages** — Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`). The body explains why, not what.
- **Small commits** — commits are small, focused, and reviewable. A PR with one commit is fine; a PR with 50 commits is suspicious.
- **Squash-and-merge** — PRs are squashed on merge to keep `main` history linear and reviewable.

### 14.7 Pull Request Requirements

A PR is mergeable when:

- It passes all CI checks (lint, type, unit, integration, contract, e2e, build).
- It has been reviewed by at least one engineer who did not author it.
- It includes tests for new behavior.
- It includes documentation updates where the public surface changed.
- It includes an ADR if it changes a documented architectural decision.
- It is linked to a ticket (no orphan PRs).
- The PR description explains what changed, why, and how to test it.

PRs that touch the Mastery Engine, the Scheduler, or the Question Factory require review by a senior engineer with domain expertise, because errors in these components compound silently.

### 14.8 Code Review Culture

Code review is a learning conversation, not a gatekeeping exercise. Reviewers are expected to:

- Suggest improvements with reasoning, not just directives.
- Distinguish between "must fix" (correctness, security, architectural violation) and "consider" (style, alternative approaches).
- Approve PRs that meet the bar, even if the reviewer would have written the code differently.
- Use suggestions and comments, not blocking requests, for non-blocking feedback.

Reviewers who block PRs on stylistic preferences are corrected. Authors who push back on legitimate architectural concerns are corrected. Both directions matter.

---

## Section 15 — Risks

This section identifies the risks that could derail the Engine and the mitigation strategy for each. Risks are categorized by type. The categorization is intentional — technical risks are mitigated differently from educational risks, and conflating them produces poor mitigations.

### 15.1 Technical Risks

**T1 — Mastery Algorithm Correctness.** The Mastery Engine is the highest-leverage and highest-risk component. A subtle bias in mastery computation (e.g., systematically underestimating mastery for learners who use hints) propagates into every scheduling decision and is extremely hard to detect.

*Mitigation:* property-based tests, event-sourced reconstruction (M4), shadow evaluation of any algorithm change, and a documented evaluation protocol before promotion. Algorithm changes require an ADR and senior review.

**T2 — Schema Migration Pain.** A normalized schema with extensive historical data is painful to migrate. As the schema evolves, migrations become riskier.

*Mitigation:* expand-and-contract migrations (add the new schema, dual-write, backfill, switch reads, drop the old schema). No breaking migration is deployed without a rollback plan. Migrations are tested against a full-size copy of the production database in staging.

**T3 — Loop Latency Regression.** The Loop's 200ms median target is easy to violate as features accumulate. A slow Repository, an over-eager event subscriber, or a missing index can push the Loop over the budget.

*Mitigation:* latency monitoring on every Loop request in production, alerting on p50/p95/p99 thresholds, query budgets, and a fast-by-default culture that resists feature creep in the Loop path.

**T4 — Sandbox Compromise.** The code-execution sandbox is the most attractive attack surface. A sandbox escape could allow an attacker to run arbitrary code on Engine infrastructure.

*Mitigation:* defense in depth — isolated containers, no network, separate node pool, non-root execution, time and resource limits, destroyed-after-use, regular security review of the sandbox image, and bug-bounty coverage of the sandbox specifically.

**T5 — Eventual Consistency Surprises.** The outbox pattern and async workers introduce eventual consistency. A user might see stale mastery on a slow connection or receive a delayed notification.

*Mitigation:* explicit consistency contracts on every endpoint (synchronous vs. asynchronous); UI affordances that signal when data may be stale; worker lag monitoring with alerts.

### 15.2 Educational Risks

**E1 — Concept Graph Design Errors.** A poorly designed concept graph (wrong dependencies, missing prerequisites, over-atomic or under-atomic concepts) makes the Scheduler's prerequisite-readiness scoring meaningless.

*Mitigation:* the Content Pipeline (Section 7) requires editorial review of the concept graph; QA / Pilot stage measures whether learners who skip prerequisites actually fail at higher rates; the graph is revisable per Content Version.

**E2 — Gamification Creep.** Streaks, badges, and leaderboards can drive engagement but can also distract from mastery. A learner who drills easy questions to maintain a streak is not learning.

*Mitigation:* engagement metrics are tracked but never optimized at the expense of retention metrics. The Mastery Engine ignores streak state; the Scheduler does not serve easier questions to maintain a streak. Gamification is decorative, never load-bearing.

**E3 — Misconception Coverage Gaps.** If authors under-document Misconceptions, the Engine's ability to diagnose "why" a learner is wrong degrades to "that" a learner is wrong.

*Mitigation:* the Content Pipeline requires at least one Misconception per Learning Objective; the QA stage flags Concepts whose Misconceptions do not appear in learner errors (suggesting the documented Misconceptions are wrong or incomplete).

**E4 — Curriculum Staleness.** Technical interviews evolve; Python's interview canon shifts (asyncio, type hints, data classes). A curriculum that does not keep up loses relevance.

*Mitigation:* quarterly curriculum review owned by an editorial lead; analytics on "this Concept is rarely tested in the wild" signals; community feedback channel.

### 15.3 Business Risks

**B1 — Content Velocity.** The Engine needs substantial content to be useful. A single author produces content at a bounded rate; scaling content production is a business problem, not a technical one.

*Mitigation:* the Content Pipeline is designed for parallel authoring; AI assistance accelerates drafting without bypassing review; the long-term plan includes a contributor program for vetted external authors.

**B2 — Retention.** A learning product's value is realized over months; most learners drop off in the first two weeks. Retention is the primary business metric.

*Mitigation:* the Loop itself is the primary retention mechanism — every session should produce a visible mastery gain. Onboarding produces an early win (a "you mastered your first concept" moment) within the first session. Notification system nudges lapsed learners without spamming.

**B3 — Monetization Pressure.** Subscription revenue is the model, but free-tier limits must not cripple the Loop. A free-tier user who cannot complete a study session will not convert.

*Mitigation:* free-tier limits are on volume (questions per day), not on quality (which questions, which explanations). The free tier is a complete product; the paid tier is more of the same.

**B4 — Competitive Incumbents.** Established players (LeetCode, HackerRank for Python interview prep) have brand recognition and large content libraries.

*Mitigation:* the moat is mastery measurement, not content volume. The Engine's value is "we tell you what to study next" — a value incumbents do not provide. Marketing leans into this differentiation.

### 15.4 Scaling Risks

**S1 — Attempts Table Growth.** At millions of learners each producing thousands of Attempts, the Attempts table reaches billions of rows. Queries against it slow; migrations against it become risky.

*Mitigation:* time-based partitioning (Section 13.3) is the primary defense; archival of old partitions to cold storage; analytics queries routed to a derived store. The partitioning strategy is designed before the table reaches 100M rows, not after.

**S2 — Queue Computation Cost.** The Scheduler recomputes the Practice Queue on every Attempt. As the active concept set grows and the question inventory grows, queue computation could become expensive.

*Mitigation:* the queue is bounded in size (10–20 questions); the Scheduler uses an index-backed ranking rather than a full sort; the queue is regenerated incrementally when possible (replace only the consumed question, not the entire queue).

**S3 — Multi-Tenant Content Conflict.** As more Subjects are added, content authors for different Subjects may make conflicting assumptions about the Engine's behavior.

*Mitigation:* the Subject-agnostic core is enforced by the Domain Service purity invariant. Subject-specific behavior is configured at the Subject level, not coded into the Domain Services. A new Subject is onboarded by populating content, not by modifying the Engine.

**S4 — Team Scaling.** A small founding team can maintain discipline informally; a growing team requires explicit standards. The architecture that scales to millions of users must also scale to dozens of engineers.

*Mitigation:* this document and its accompanying ADRs are the onboarding material. The folder structure, layer boundaries, and review requirements are enforced by CI and by code review culture, not by individual heroics.

### 15.5 Mitigation Strategy Summary

Across all categories, the mitigation strategy follows three principles:

1. **Make the right thing easy and the wrong thing hard.** The folder structure, the DI patterns, and the linting rules make the architecture the path of least resistance.
2. **Measure, then act.** Every risk has a measurable signal (latency, retention, discrimination, queue depth). Mitigations are triggered by signals, not by calendar.
3. **Document the decisions.** ADRs, runbooks, and this ASD are the institutional memory. A team that does not document its decisions re-litigates them every six months.

---

## Section 16 — Roadmap

The roadmap is divided into four phases. Each phase has explicit goals, deliverables, exit criteria, dependencies, and a complexity estimate. The phases are sequential by default; parallelism within a phase is encouraged where dependencies allow.

### 16.1 Phase 1 — Core Loop MVP

**Goals:** Ship a working learning loop for a single Subject (Python interview prep) to a closed beta. Prove that the Engine can answer "what should I study next?" with a measurable improvement over linear curriculum traversal.

**Deliverables:**
- Identity context: signup, login, JWT issuance, refresh flow.
- User profile: minimal (email, name, timezone, active Subject).
- Content context: Concept, Concept Dependency, Learning Objective, Misconception, Question Template, Explanation — authored for an initial Python concept set (~50 concepts).
- Mastery Engine v1: deterministic algorithm, memory + mastery scores, review scheduling, weak-concept detection.
- Scheduler v1: weighted ranking by due-date, weakness, prerequisite-readiness, session goal.
- Question Factory v1: deterministic instantiation from templates, multiple-choice and short-answer question types.
- Learning Loop: start session, serve question, record attempt, update mastery, regenerate queue, display explanation, serve next question.
- Frontend: login, dashboard, learning session, basic progress page.
- Admin: minimal content authoring UI for the initial concept set.
- Deployment: Docker Compose for local dev; single-instance production deployment.

**Exit Criteria:**
- A closed-beta learner can complete a 20-question study session end-to-end.
- The Loop's median backend latency is under 200ms.
- Mastery Scores update correctly and reproducibly from Attempt history (M1, M4 invariants hold).
- The Scheduler's output is deterministic given a seed (I3 invariant holds).
- Property-based tests for the Mastery Engine and Scheduler pass.

**Dependencies:** None (this is the foundation).

**Estimated Complexity:** High. The Mastery Engine and Scheduler are the hardest components and they are both in Phase 1. There is no shortcut; they must be right.

### 16.2 Phase 2 — Content Pipeline + Code Execution + Admin Portal

**Goals:** Build the content authoring pipeline that allows the team to scale content production. Add code-execution questions (essential for Python interview prep). Build the admin portal that supports the full content lifecycle.

**Deliverables:**
- Content Pipeline: draft authoring, peer review, editorial review, QA / pilot, publishing, versioning.
- Question Factory v2: code-execution question type, sandbox integration.
- Sandbox: isolated containerized runtime, CPU/memory/time limits, separate node pool.
- Admin Portal: content management UI, user support tools, audit log viewer.
- Content Versioning: immutable snapshots, attempt references to Content Version.
- Background workers: outbox dispatcher, notification dispatch, analytics projection rebuilds.
- Caching: content cache, mastery cache, queue cache, with documented invalidation.
- Monitoring: latency, error rate, queue depth, sandbox health.

**Exit Criteria:**
- A new Concept can be authored, reviewed, piloted, and published end-to-end without engineering intervention.
- Code-execution questions run in the sandbox with no network access and no path to learner data.
- Content Version is recorded on every Attempt; historical Attempts remain interpretable after a content revision.
- The team has shipped at least 200 Concepts and 1000 Question Templates.

**Dependencies:** Phase 1 complete. The Content Pipeline requires the Content context from Phase 1; the Question Factory v2 requires the v1 Factory.

**Estimated Complexity:** Medium-High. The sandbox is the most complex piece; the Content Pipeline is mostly workflow and state machine work.

### 16.3 Phase 3 — Analytics, Notifications, Payments, Multi-Subject Scaffolding

**Goals:** Build the supporting subsystems that turn the Engine into a product: analytics for learners and the team, notifications for engagement, payments for monetization, and the multi-Subject scaffolding that allows the second Subject to be onboarded.

**Deliverables:**
- Analytics: per-user progress page (mastery-over-time, weak concepts, retention curves), admin analytics dashboard (cohort retention, concept difficulty, funnel metrics), materialized views for common aggregates.
- Notifications: review reminders, streak nudges, weekly progress digest. User-controlled preferences. Event-bus-driven dispatch.
- Payments: subscription tiers, Stripe integration, entitlement resolution, billing UI.
- Multi-Subject scaffolding: Subject entity, per-Subject content isolation, per-Subject onboarding, Subject switcher in UI.
- Background jobs: nightly quality monitoring (discrimination, distractor analysis, explanation effectiveness), nightly materialized view refreshes.
- Read replica: analytics traffic routed to a read replica.
- Performance hardening: query budgets enforced, slow-query alerts, CDN for static assets.

**Exit Criteria:**
- A learner can subscribe, pay, and access paid-tier features.
- A learner enrolled in two Subjects can switch between them and see independent progress.
- Analytics dashboards load in under 2s at the 95th percentile.
- The second Subject (likely SQL or a second programming language) can be onboarded without code changes to the Engine core.

**Dependencies:** Phase 2 complete. Analytics requires the Attempt history accumulated in Phases 1–2. Multi-Subject scaffolding requires the Subject-agnostic core from Phase 1.

**Estimated Complexity:** Medium. The components are individually well-understood; the complexity is in integration and in not compromising the Loop.

### 16.4 Phase 4 — Scale, Search, Recommendations, ML Hooks

**Goals:** Scale the Engine to support orders of magnitude more learners and content. Add the capabilities that justify the long-term moat: search at scale, refined recommendations, and the ML integration hooks that allow the deterministic algorithms to be challenged and replaced where data justifies it.

**Deliverables:**
- Attempts table partitioning by time; archival of old partitions.
- Derived analytics store (columnar database) populated by CDC.
- Dedicated search engine (Elasticsearch or equivalent) for content catalog.
- Mastery Engine model registry: deterministic algorithm as v1, shadow evaluation framework for v2 candidates.
- Scheduler enhancements: refined ranking, A/B testing framework for scheduling variants.
- Notification system enhancements: behavioral triggers, delivery time optimization.
- PWA support for mobile learners (no separate React Native build).
- Multi-region deployment readiness (active-passive with remote read replicas).
- Load testing infrastructure; documented capacity planning.

**Exit Criteria:**
- The Engine sustains 10x Phase 3 traffic at the same latency targets.
- The Mastery Engine model registry supports shadow evaluation of a candidate model against live traffic, with documented evaluation results.
- A second Subject is fully live with paying subscribers.
- The team has run at least one A/B test on the Scheduler and shipped the winning variant.

**Dependencies:** Phase 3 complete. ML hooks require the data accumulated through Phases 1–3. Multi-region requires the operational maturity to run a multi-region deployment safely.

**Estimated Complexity:** High. Scaling always is. The ML hooks are intentionally low-risk (shadow mode only) but the surrounding infrastructure (model registry, evaluation protocol, A/B framework) is non-trivial.

### 16.5 Post-Phase-4 (Out of Scope for this ASD)

Items deliberately deferred beyond Phase 4:
- Active-active multi-region deployment.
- Native mobile applications (PWA is the path until a native app is forced by market pressure).
- B2B / enterprise tier with SSO and tenant isolation.
- Marketplace for third-party content authors.
- Real-time collaborative features (study groups, shared sessions).

Each of these is a major architectural change and warrants its own design document when triggered.

---

## Section 17 — Appendix: Architectural Recommendations Beyond the Brief

A Principal Architect is obligated to surface weaknesses in the vision, not just to execute on it. This section documents the recommendations that the original brief did not request but that the architecture should adopt. These are not optional; they are the difference between a system that scales and a system that fractures.

### 17.1 Add Observability as a First-Class Concern

The brief mentions testing but not observability. A production system without observability is operated blind. The architecture should adopt:

- **Structured logging** with correlation IDs, mandatory in every log line.
- **Metrics** (Prometheus or equivalent) for every endpoint, every background job, every Loop step.
- **Distributed tracing** (OpenTelemetry) across the API, workers, and the database.
- **Error tracking** (Sentry or equivalent) with PII scrubbing.

Observability is not a Phase 4 addition; it is a Phase 1 requirement. The Loop's latency budget cannot be enforced without it.

### 17.2 Add an Architecture Decision Record Process

The brief asks for production-quality architecture but does not specify how architectural decisions are recorded. The ASD captures the current state; ADRs capture the decision history. Without ADRs, the team re-litigates decisions every six months. ADRs are referenced throughout Section 14 and should be a Phase 1 deliverable.

### 17.3 Add a Feature Flag System

The architecture assumes features are either shipped or not. In practice, features need to be rolled out gradually, gated by user cohort, or killed quickly if they regress. A feature flag system (even a simple one backed by Redis) should be in Phase 1. It is the mechanism for safely deploying the Mastery Engine v2, the Scheduler variants, and any A/B test.

### 17.4 Add a Data Retention Policy

The brief emphasizes the historical attempt corpus as the moat but does not specify how long data is retained. Indefinite retention creates legal and storage risk. The architecture should adopt an explicit retention policy:

- **Attempts** — retained indefinitely in anonymized form; PII stripped after 24 months.
- **Audit logs** — retained for 7 years (compliance best practice).
- **Session data** — retained for 90 days, then aggregated.
- **Notification delivery records** — retained for 30 days.

The retention policy is documented in the privacy policy and enforced by background jobs.

### 17.5 Add a Disaster Recovery Plan

The brief does not mention disaster recovery. The architecture should adopt:

- **Recovery Time Objective (RTO)** of 4 hours for the full system.
- **Recovery Point Objective (RPO)** of 15 minutes (achieved by point-in-time recovery from WAL archiving).
- **Quarterly disaster recovery drills** that restore the system from backup into a fresh environment.
- **Documented incident command** structure for major outages.

A disaster recovery plan that has never been drilled is a fiction. The first drill will fail; subsequent drills converge to a working plan.

### 17.6 Add a Privacy-by-Design Review Process

GDPR compliance (Section 12.8) is a baseline, not a destination. The architecture should adopt a privacy-by-design review for any feature that touches user data: a brief written assessment of what data is collected, why, who can access it, how long it is retained, and what the user's rights are. This review is part of the PR template for data-touching features.

### 17.7 Add a Cost Monitoring Discipline

Cloud cost is the silent scaler. A system that scales to millions of learners also scales to millions of dollars. The architecture should adopt:

- **Per-feature cost tagging** in the cloud provider.
- **Monthly cost review** with anomaly investigation.
- **A cost ceiling** per environment that triggers alerts when exceeded.
- **A sandbox cost budget** — the sandbox is the most likely component to surprise the team on cost.

### 17.8 Acknowledge the Concurrency Risk in the Loop

The Loop's submit-answer path performs a read-modify-write on the Mastery Score. Two concurrent submissions on the same Concept (rare but possible during retry storms) could produce a lost update. The architecture should adopt **optimistic concurrency control** on the Mastery Score: the score is read with a version number, the update is written conditional on the version, and a conflict triggers a re-read and re-compute. This is a small addition to the Mastery Engine that prevents a subtle class of bugs.

### 17.9 Recommend Explicit Consistency Modes for Each Endpoint

The architecture describes synchronous and asynchronous paths but does not require each endpoint to declare its consistency mode. Every endpoint should declare one of: **strong** (reads from primary, returns latest committed), **read-your-writes** (reads from primary if the user recently wrote, else from replica), **eventually consistent** (reads from replica, may be stale). The declaration is part of the endpoint's documentation and is enforced by the framework.

### 17.10 Recommend a Backup Verification Process

Backups that have never been restored are a fiction. The architecture should adopt:

- **Daily backup integrity checks** (a restore into a sandbox environment, a smoke test, a teardown).
- **Weekly full-restore drills** into a staging environment.
- **Quarterly cross-region restore drills** (if multi-region).

A backup that fails to restore is worse than no backup, because it produces false confidence.

---

## Document Control

| Field | Value |
|---|---|
| Document Title | Mastery Engine — Architecture Specification Document |
| Version | 1.0 |
| Status | Source of Truth |
| Owner | Principal Architect |
| Approvers | Engineering Lead, Product Lead, Curriculum Lead |
| Supersedes | None |
| Superseded By | None (future versions will reference this one) |
| Last Updated | 2026-07-02 |

### Change Log

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-07-02 | Principal Architect | Initial architecture specification, covering Sections 1–17. |

---

*End of Architecture Specification Document.*
