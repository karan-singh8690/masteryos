# Mastery Engine — Ubiquitous Language & Domain Glossary

> **Status:** v1.0 — Authoritative source of truth for all project vocabulary
> **Owner:** Domain Modeling Lead
> **Audience:** Engineering, Product, Design, Curriculum, Analytics, Documentation, AI agents
> **Scope:** All terminology used across the Mastery Engine project
> **Companion document:** Architecture Specification Document (Task 001)

---

## How to Use This Document

This document is the **single source of truth** for the project's vocabulary. Every database table, Python class, TypeScript interface, REST resource, event name, UI label, error message, help article, and curriculum artifact **must** use the terms defined here, in the form defined here. If a term is not in this document, it is not part of the project's language. If a term is here but is used in a different sense, the usage is wrong, not the definition.

When two terms seem to mean the same thing, consult the **Synonym Table** at the end. When a word is not listed but feels like it should be, consult the **Forbidden Terminology** section — it may have been deliberately excluded. When in doubt, do not invent a new term; open a glossary change request and let the domain modeling lead adjudicate.

The glossary is organized by bounded context. A term appears exactly once, in its owning context. Terms from other contexts that reference it must use its official name. Cross-references are denoted by the official term in **bold** on first mention within an entry.

---

## Document Conventions

- Each term follows the same 11-section template.
- "Owning context" identifies the single bounded context responsible for the term. Other contexts may read it; only the owner may write it.
- "Invariants" are business rules that the system enforces, not suggestions. A violation is a bug.
- "Non-Examples" exist to disambiguate terms that are commonly confused in industry usage but mean different things in this project.
- Where the brief's term list contains pairs that overlap (e.g., **Study Session** and **Learning Session**), the glossary treats them as distinct concepts and the **Synonym Table** documents the distinction explicitly. This is deliberate: the project gains precision by separating concerns that the industry usually conflates.
- Words marked `FORBIDDEN` in the **Forbidden Terminology** section must never appear in code, schema, UI, documentation, or analytics. Each has an approved replacement.

---

# Part I — Learning Domain

The Learning Domain owns the core educational vocabulary: who is learning, what they are learning, how learning is organized, how it is practiced, how it is measured, and how progress is recognized. This is the largest and most pedagogically sensitive part of the glossary.

---

### User

#### Name
**User**

#### Definition
A **User** is any authenticated identity that can sign in to the Mastery Engine. A User is the root entity of identity: it owns credentials, holds a profile, and may be linked to one or more subject enrollments. The User itself carries no learning state — learning state lives on the **Learner** role the User adopts within a **Subject**.

A single User may participate in multiple Subjects (for example, Python interview prep and SQL fundamentals), each with independent progress. The User is the unit of authentication, billing, and account administration; it is not the unit of learning measurement.

#### Business Purpose
The User exists to separate identity (who you are) from learning (what you know). This separation lets the platform support credential rotation, account merging, anonymization for GDPR, and multi-subject enrollment without rippling changes through learning data.

#### Lifecycle
- **Created** at signup, via email/password or OAuth.
- **Updated** when profile fields change (name, timezone, preferences).
- **Suspended** by administration for abuse or non-payment.
- **Anonymized** on deletion request after a 14-day grace period; learning history is retained in anonymized form, PII is purged.
- **Never hard-deleted** while the account has Attempts; the audit trail requires the User id to remain referenceable.

#### Owner
Identity

#### Relationships
- Has one **User Profile**.
- Has one or more **UserCredential** records (password, OAuth).
- Adopts the **Learner** role in each enrolled **Subject**.
- May hold the **Instructor** or **Administrator** role.
- Owns **Attempt**s, **StudySession**s, and **MasteryScore**s.

#### Invariants
- A User has exactly one email, verified before any Subject enrollment.
- A User cannot be hard-deleted while linked to Attempts.
- A User id is immutable and never reused.

#### Examples
1. A job-seeker signs up with `alex@example.com` and enrolls in the Python Subject.
2. A User signs up via GitHub OAuth and links a password later.
3. An administrator suspends a User who is abusing the rate limit.

#### Non-Examples
- A **Learner** is not a User — it is the role a User plays within a Subject.
- A **Tenant** is not a User — it is an organizational container.
- An anonymous visitor browsing the marketing site is not a User until signup completes.

#### Future Extensions
- Account merge flow (two Users consolidated into one after email verification).
- Household accounts (multiple Users sharing a billing plan but with separate learning state).
- Delegated access (a parent User viewing a minor's progress).

---

### Learner

#### Name
**Learner**

#### Definition
A **Learner** is the role a **User** adopts when enrolled in a **Subject**. The Learner is the unit of learning measurement: every **Attempt**, **MasteryScore**, and **Review** belongs to a Learner, not to the User in the abstract. A User becomes a Learner the moment they enroll in their first Subject; they may be a Learner in multiple Subjects simultaneously, with independent progress in each.

The Learner role is the bridge between identity and pedagogy. It carries per-Subject onboarding state (diagnostic completion, baseline mastery), per-Subject preferences (daily goal, session length), and per-Subject mastery state.

#### Business Purpose
Separating Learner from User allows the same person to study multiple Subjects with isolated progress, mastery, and recommendations. It also allows a future B2B tier where one User belongs to an Organization but is a Learner in Subjects owned by that Organization.

#### Lifecycle
- **Created** when a User enrolls in a Subject (explicitly or via diagnostic).
- **Activated** after the Subject's onboarding flow completes.
- **Dormant** after 30 days of inactivity; reactivated on next session.
- **Unenrolled** at User request; Learner state is retained for 90 days for re-enrollment, then anonymized.

#### Owner
Learning

#### Relationships
- Belongs to exactly one **User**.
- Belongs to exactly one **Subject**.
- Owns **Attempt**s, **StudySession**s, **MasteryScore**s, **Review**s within the Subject.
- Follows a **LearningPath** within the Subject.
- Holds **LearningGoal**s.

#### Invariants
- A Learner exists in exactly one Subject.
- A User may be a Learner in N Subjects, each with independent state.
- A Learner's mastery state is reconstructible from its Attempt history plus the **Mastery Engine** version log.

#### Examples
1. A User enrolls in Python — they are now a Learner in the Python Subject.
2. The same User enrolls in SQL — they are now a Learner in two Subjects, with independent progress.
3. A Learner in Python has MasteryScores for `list-mutability` and `dict-lookup` but no scores for SQL concepts.

#### Non-Examples
- A **User** is the identity, not the learning role.
- An **Instructor** is not a Learner — Instructors author content but do not have mastery state in the learner sense (unless they also enroll).
- A free trial visitor is not a Learner until they enroll in a Subject.

#### Future Extensions
- Learner profiles importable across Subjects (a Learner's mastery in Python lists carries forward to a future "Python data structures" Subject).
- Learner transfer between Organizations.

---

### Instructor

#### Name
**Instructor**

#### Definition
An **Instructor** is a **User** role authorized to author and review content within one or more **Subject**s. Instructors create **Concept**s, **LearningObjective**s, **Misconception**s, and **QuestionTemplate**s, and they participate in the **ReviewWorkflow** that publishes content. An Instructor is not a teacher in the traditional sense — the platform has no live teaching; Instructors are curriculum authors and reviewers.

The Instructor role is scoped per Subject. A User may be an Instructor in Python and a Learner in SQL. Instructorship does not grant administrative privileges beyond the content workflow.

#### Business Purpose
The Instructor role exists to enforce the human-authored source-of-truth principle from Task 001. Only Instructors may publish content; AI may assist drafting but cannot publish. The role also scopes accountability: every published artifact has a named Instructor who approved it.

#### Lifecycle
- **Granted** by an Administrator to a User, scoped to a Subject.
- **Revoked** by an Administrator; the Instructor's published content remains, attributed to them.
- **Suspended** pending review if quality metrics fall below threshold.

#### Owner
Content (with Administration managing the role assignment)

#### Relationships
- Is a role of a **User**.
- Scoped to one or more **Subject**s.
- Authors **Concept**s, **LearningObjective**s, **Misconception**s, **QuestionTemplate**s.
- Participates in the **ReviewWorkflow** as peer or editorial reviewer.

#### Invariants
- An Instructor cannot publish their own draft without peer review by a different Instructor.
- An Instructor's role is per-Subject; one Subject's Instructorship does not transfer.
- Every published artifact records the Instructor who approved it.

#### Examples
1. A senior Python engineer is granted Instructor in the Python Subject and authors the `dict-lookup-complexity` Concept.
2. An Instructor peer-reviews a colleague's QuestionTemplate and requests revisions.
3. An Instructor's published Templates are flagged by quality metrics; an Administrator suspends their publishing rights pending review.

#### Non-Examples
- An **Administrator** is not an Instructor — Administrators manage the platform, not the curriculum.
- A live teacher in a classroom sense — the platform has no such role.
- An AI drafting assistant — it is a tool Instructors use, not a role.

#### Future Extensions
- External contributor program (Instructors from outside the core team, with sandboxed publishing).
- Instructor analytics (which Instructors' content drives the best learning outcomes).
- Co-instructorship (multiple Instructors sharing authorship on a Concept).

---

### Administrator

#### Name
**Administrator**

#### Definition
An **Administrator** is a **User** role with platform-wide privileges: managing **Instructor** assignments, suspending **User**s, processing refunds, viewing the **AuditLog**, configuring feature flags, and operating the Admin Portal. Administrators do not author content directly — they manage the people and the platform that produce content.

Administrator actions are always recorded in the **AuditLog**. Every privileged action has a named Administrator behind it; the system has no anonymous administrative access.

#### Business Purpose
The Administrator role exists to separate platform operations from content authoring and from learning. This separation prevents a single compromised account from corrupting both content and learning data, and it provides a clean audit trail for compliance.

#### Lifecycle
- **Granted** by an existing Administrator, with MFA required.
- **Revoked** by another Administrator; revocation is itself audited.
- **Emergency** Administrator accounts exist for incident response, sealed and monitored.

#### Owner
Administration

#### Relationships
- Is a role of a **User**.
- Manages **Instructor** role assignments.
- Operates the Admin Portal.
- Writes to the **AuditLog**.
- May override **Subscription** entitlements in exceptional cases (also audited).

#### Invariants
- Administrator actions require MFA.
- Every Administrator action is recorded in the AuditLog within the same transaction.
- An Administrator cannot grant Administrator to themselves.
- Administrators cannot directly modify a **MasteryScore** — mastery is owned by the **Mastery Engine** alone.

#### Examples
1. An Administrator suspends a User who is credential-stuffing the login endpoint.
2. An Administrator grants Instructor role to a new hire in the SQL Subject.
3. An Administrator reviews the AuditLog after a content-rollback incident.

#### Non-Examples
- An **Instructor** — Instructors manage content, not the platform.
- A **Learner** with admin-like permissions — the platform has no such hybrid role.
- A customer support agent without Administrator role — they have read-only support tools, not Administrator powers.

#### Future Extensions
- Role细分 (read-only Administrator, billing Administrator, content Administrator).
- Just-in-time Administrator elevation (temporary grant with auto-expiry).
- Break-glass procedures for incident response.

---

### Subject

#### Name
**Subject**

#### Definition
A **Subject** is the top-level tenant of learning content: Python, SQL, Java, Cybersecurity, Cloud, IELTS, and so on. A Subject owns its **KnowledgeGraph** (the full set of **Concept**s and **ConceptDependency** edges), its **LearningPath**s, its **QuestionTemplate** inventory, and its published **ContentVersion**s. The Mastery Engine core is Subject-agnostic; the Subject is the unit at which Subject-specific content is configured.

A Subject is more than a category — it is a bounded content universe with its own version history, its own quality metrics, and its own onboarding flow. A Learner enrolled in a Subject has mastery state only within that Subject.

#### Business Purpose
The Subject exists to make the engine multi-tenant without code forks. Adding a new Subject is a content-authoring exercise, not an engineering one. This preserves the architecture's longevity and lets the platform expand beyond Python without rewriting the core.

#### Lifecycle
- **Created** as a draft by an Administrator, with an initial scope statement.
- **Populated** by Instructors authoring Concepts, Objectives, Templates.
- **Published** when the initial curriculum reaches a minimum viable size (defined per Subject).
- **Versioned** on every content publish; each version is an immutable snapshot.
- **Deprecated** when the Subject is retired; Learners can finish in-flight sessions but no new enrollments are accepted.

#### Owner
Content

#### Relationships
- Owns a **KnowledgeGraph** of **Concept**s and **ConceptDependency**s.
- Owns one or more **LearningPath**s.
- Owns a set of **QuestionTemplate**s.
- Has many **Learner**s (via enrollment).
- Has many **ContentVersion**s.

#### Invariants
- A Subject's KnowledgeGraph is acyclic at any published version.
- A Subject cannot be deleted while it has enrolled Learners.
- Every published Concept, Objective, Misconception, and Template belongs to exactly one Subject.

#### Examples
1. "Python Technical Interview Preparation" — the first Subject on the platform.
2. "SQL Fundamentals" — a planned second Subject.
3. "Cybersecurity Essentials" — a future Subject, currently a draft with no published content.

#### Non-Examples
- A **LearningPath** — a path is an ordered traversal within a Subject, not the Subject itself.
- A **ContentPack** — a pack is a versioned bundle, not the tenant.
- A **Topic** (forbidden term) — the project uses Concept and Subject, not Topic.

#### Future Extensions
- Cross-Subject prerequisites (a SQL Subject that requires Python mastery).
- Subject bundles (a "backend interview" bundle spanning Python, SQL, and System Design).
- User-generated Subjects (marketplace model, Phase 5+).

---

### Learning Path

#### Name
**Learning Path**

#### Definition
A **Learning Path** is an ordered, opinionated traversal of the **KnowledgeGraph** for a **Subject**. It represents the Engine's recommendation for how to move from "no knowledge" to the Subject's graduation criteria. A Subject may have multiple Learning Paths (for example, "Python for beginners," "Python for experienced developers," "Python crash course for tomorrow's interview").

A Learning Path is the goal, not the schedule. The **Scheduler** decides what to serve next within the path, balancing the path's ordering against the Learner's current mastery, due reviews, and weak concepts.

#### Business Purpose
The Learning Path exists to give Learners a coherent narrative through the otherwise flat KnowledgeGraph. Without it, the Scheduler would optimize for short-term mastery gains but might leave the Learner without a sense of progression. The path provides the spine; the Scheduler provides the day-to-day movement.

#### Lifecycle
- **Authored** by Instructors as an ordered list of Concept references with optional branching.
- **Published** as part of a **ContentVersion**.
- **Customized** per Learner (the Learner's path instance may skip concepts they have tested out of).
- **Versioned**; Learners on an old version continue on it until they explicitly migrate.

#### Owner
Learning

#### Relationships
- Belongs to a **Subject**.
- References a sequence of **Concept**s.
- Has many **Learner** instances following it.
- May have prerequisite **LearningPath**s (a "Python advanced" path may require "Python fundamentals").

#### Invariants
- A Learning Path's Concept sequence must be a valid topological traversal of the KnowledgeGraph (prerequisites before dependents).
- A Learner has at most one active Learning Path per Subject at a time.
- A Learning Path's graduation criteria are explicit and measurable (a set of Concepts that must reach Mastered).

#### Examples
1. "Python Interview Prep — Full Path" traverses 80 Concepts over an estimated 60 hours.
2. "Python Interview Prep — Crash Course" traverses 25 high-yield Concepts over 10 hours.
3. A Learner tests out of the first 20 Concepts of the Full Path; their customized instance starts at Concept 21.

#### Non-Examples
- A **StudyPlan** — a plan is a Learner-specific schedule, not a curriculum ordering.
- A **DailyQueue** — the queue is a per-session artifact, not a long-term path.
- The **KnowledgeGraph** — the graph is the unordered structure; the path is an ordering.

#### Future Extensions
- Adaptive paths that branch based on diagnostic performance.
- Learner-created custom paths.
- Path comparison analytics (which paths produce better outcomes for which Learner profiles).

---

### Learning Goal

#### Name
**Learning Goal**

#### Definition
A **Learning Goal** is a Learner-declared target that influences scheduling. Goals include target dates ("interview on 2026-09-15"), target mastery levels ("reach Proficient on all Python data structures"), time commitments ("30 minutes per day"), and session intents ("drill weak concepts tonight"). Goals are inputs to the **Scheduler**; they modulate queue priority but do not override mastery-based scheduling fundamentals.

Goals are distinct from **Milestone**s (engine-recognized progress markers) and from **LearningPath** graduation criteria (curriculum-defined completion). A Goal is what the Learner wants; a Milestone is what the Engine recognizes; graduation is what the curriculum requires.

#### Business Purpose
The Learning Goal exists to let the Learner express urgency and intent without forcing the Engine to abandon mastery-based scheduling. A Learner with an interview in two weeks receives a different queue than one studying for fun, but both still get spaced-repetition reviews and prerequisite-respecting sequencing.

#### Lifecycle
- **Set** by the Learner during onboarding or anytime in settings.
- **Updated** as circumstances change; the Scheduler reacts within the next queue generation.
- **Archived** when completed or explicitly abandoned.
- **Defaulted** to a Subject-level default if the Learner sets none.

#### Owner
Learning

#### Relationships
- Belongs to a **Learner**.
- Influences the **Scheduler**'s queue generation.
- May align with one or more **Milestone**s.
- May target a **LearningPath**'s graduation.

#### Invariants
- A Goal cannot require the Scheduler to violate prerequisite-readiness.
- A Goal with a target date must produce a feasible schedule or warn the Learner (the Engine does not silently over-promise).
- A Learner has at most one active time-bound Goal per Subject at a time.

#### Examples
1. "I have an interview on September 15 — prioritize high-yield Concepts."
2. "I want to study 30 minutes per day, 5 days per week."
3. "Tonight's session: drill my three weakest Concepts for 20 minutes."

#### Non-Examples
- A **Milestone** — milestones are engine-recognized, not learner-declared.
- A **LearningPath**'s graduation criteria — those are curriculum-defined.
- A daily **StudySession** goal (e.g., "20 questions today") — that is a session-level intent, captured as a session parameter, not a Learning Goal.

#### Future Extensions
- Goal templates ("interview in 1 month," "interview in 1 week") with auto-generated schedules.
- Goal-sharing with mentors or accountability partners.
- Goal-attainment analytics (which goal profiles produce the best outcomes).

---

### Study Plan

#### Name
**Study Plan**

#### Definition
A **Study Plan** is a Learner-specific, time-bounded schedule produced by the **Scheduler** that projects the **LearningPath** against the **LearningGoal** and the Learner's current mastery. It is the Engine's answer to "if I keep studying at this pace, when will I reach my goal?" A Study Plan is a projection, not a contract — it updates as mastery updates, as the Learner's pace varies, and as the Learning Goal changes.

A Study Plan is distinct from a **DailyQueue** (the immediate list of questions for the current session) and from a **LearningPath** (the curriculum ordering). The plan sits between them: it is the calendar-level projection of the path against the goal.

#### Business Purpose
The Study Plan exists to give Learners a credible answer to the scheduling question without overcommitting the Engine. The Engine does not promise the Learner will be ready by a date; it promises to show the Learner, given current pace, when readiness would arrive — and to flag when the goal is at risk.

#### Lifecycle
- **Generated** when a Learner sets a time-bound LearningGoal.
- **Regenerated** nightly and after every StudySession, reflecting updated mastery and pace.
- **Superseded** when the LearningGoal changes.
- **Archived** when the goal is completed or abandoned.

#### Owner
Scheduling

#### Relationships
- Belongs to a **Learner**.
- References a **LearningPath**.
- References a **LearningGoal**.
- Drives the **DailyQueue** at session start.

#### Invariants
- A Study Plan is always recomputable from the Learner's current mastery, the active LearningPath, and the active LearningGoal.
- A Study Plan with an infeasible goal must surface a warning, not silently adjust the goal.
- A Learner has at most one active Study Plan per Subject.

#### Examples
1. A Learner with a September 15 interview goal sees a Study Plan projecting readiness on September 12, with 3 days of buffer.
2. A Learner who skips three days sees their Study Plan slip; the Engine surfaces a "goal at risk" warning.
3. A Learner without a time-bound goal has no Study Plan — the Scheduler operates session-by-session.

#### Non-Examples
- A **DailyQueue** — the queue is for the current session; the plan is for the calendar.
- A **LearningPath** — the path is the curriculum; the plan is the schedule.
- A **LearningGoal** — the goal is the intent; the plan is the projection.

#### Future Extensions
- Plan scenarios ("what if I study 45 minutes instead of 30?").
- Plan export to calendar apps.
- Plan sharing with mentors.

---

### Study Session

#### Name
**Study Session**

#### Definition
A **Study Session** is a single sitting during which a **Learner** practices within a **Subject**. It has a start time, an end time, a session intent (drill, diagnostic, review, mixed), a target Concept set, and a sequence of **Attempt** references. The Study Session is the unit of engagement analytics: streaks, total time, and questions-per-session are computed from it.

A Study Session is **frontend-managed** in the sense that the Learner starts and ends it explicitly. It is **backend-managed** in the sense that all state lives on the backend — a reload resumes the session, a crash recovers it.

#### Business Purpose
The Study Session exists to give the Engine a clean unit of engagement measurement and to give the Learner a clean unit of focus. Streaks and time-on-platform are computed from sessions, not from individual Attempts, which prevents gaming (a Learner cannot maintain a streak by submitting one Attempt per day in 30 seconds).

#### Lifecycle
- **Started** by the Learner (or resumed if an unfinished session exists).
- **Active** while Attempts are being submitted.
- **Paused** if the Learner steps away (the session remains resumable for 24 hours).
- **Ended** by the Learner, by reaching the session goal, or by a 24-hour inactivity timeout.
- **Archived** after end; the Attempt history is retained indefinitely.

#### Owner
Learning

#### Relationships
- Belongs to a **Learner**.
- Contains a sequence of **Attempt**s.
- Uses a **DailyQueue** (or **AdaptiveQueue**) generated by the **Scheduler**.
- Has a session intent that aligns with a **LearningGoal** or defaults to "mixed."

#### Invariants
- A Learner has at most one active Study Session per Subject at a time.
- An Attempt belongs to exactly one Study Session.
- A Study Session cannot outlive the Learner's enrollment.

#### Examples
1. A Learner starts a 20-minute drilling session on weak Concepts; the Engine serves 15 Attempts; the Learner ends the session.
2. A Learner starts a diagnostic session to establish baseline mastery; the Engine serves a stratified sample across the KnowledgeGraph.
3. A Learner pauses mid-session, returns the next morning, and resumes from the unanswered question.

#### Non-Examples
- A **LearningSession** — see that term; the two are deliberately distinguished in this project.
- A single Attempt — an Attempt is one interaction; a session is a sequence.
- A **PracticeSession** — see that term; practice is a session intent, not a distinct session type.

#### Future Extensions
- Group study sessions (multi-Learner, future Phase 5+).
- Session replay for review.
- Session templates (saved session configurations).

---

### Learning Session

#### Name
**Learning Session**

#### Definition
A **Learning Session** is a logical abstraction that groups one or more consecutive **StudySession**s into a single learning episode from the Learner's perspective. Where a Study Session is a single sitting, a Learning Session is the Learner's perceived unit of learning — it may span a brief break, a device switch, or an intentional pause-and-resume within the same study episode.

The distinction matters for analytics: engagement metrics that count Study Sessions over-count learners who take breaks; metrics that count Learning Sessions under-count learners who study in discrete sittings. The project tracks both and uses each where appropriate.

#### Business Purpose
The Learning Session exists to give analytics a learner-aligned unit of measurement. A Learner who studies 45 minutes, takes a 5-minute break, and studies another 30 minutes had **two Study Sessions but one Learning Session**. Treating these as one episode gives a more honest picture of engagement and a more stable input to retention analytics.

#### Lifecycle
- **Opened** when a Study Session starts and no Learning Session is active.
- **Extended** when a new Study Session starts within the merge window (default 15 minutes).
- **Closed** when no new Study Session starts within the merge window.
- **Archived** for analytics; not directly visible to the Learner.

#### Owner
Learning (with Analytics reading)

#### Relationships
- Contains one or more **StudySession**s.
- Belongs to a **Learner**.
- Aggregates the **Attempt**s of its constituent Study Sessions for analytics.

#### Invariants
- Two Study Sessions more than the merge window apart belong to different Learning Sessions.
- A Learning Session cannot span Subjects (each Subject has its own sessions).
- The merge window is configurable per Subject but is never zero (which would collapse Learning Session into Study Session).

#### Examples
1. A Learner studies 25 minutes, takes a 5-minute break, studies 20 more — one Learning Session of 45 minutes net, two Study Sessions.
2. A Learner studies Tuesday evening and Wednesday morning — two Learning Sessions.
3. A Learner's session is interrupted by a phone call; they resume after 10 minutes — same Learning Session (within merge window).

#### Non-Examples
- A **StudySession** — a study session is one sitting; a learning session is one episode.
- A **PracticeSession** — practice is an intent, not an episode unit.
- A calendar "study block" — that is external to the platform.

#### Future Extensions
- Learner-visible Learning Session summaries ("You studied 45 minutes today across 2 sessions").
- Cross-Subject Learning Sessions (a multi-Subject study evening).
- Adaptive merge windows based on session content.

---

### Learning Recommendation

#### Name
**Learning Recommendation**

#### Definition
A **Learning Recommendation** is a structured suggestion the Engine produces for a **Learner** outside the active practice loop. Recommendations include "review these 5 Concepts before your interview," "your weak Concepts suggest reviewing this prerequisite," "you are ready to advance to the next Learning Path stage." Recommendations are advisory — the Learner may accept, defer, or dismiss them.

Recommendations are distinct from the **DailyQueue**, which is the imperative list of questions for the current session. A recommendation is a suggestion; a queue is an instruction.

#### Business Purpose
The Learning Recommendation exists to extend the Engine's "what next?" capability beyond the active session. Without it, the Learner gets guidance only while practicing; with it, the Learner gets guidance on what to practice, when to practice, and what to study in adjacent Subjects.

#### Lifecycle
- **Generated** by the **Scheduler** or background analytics jobs.
- **Presented** on the dashboard or in notifications.
- **Accepted** (the Learner acts on it), **Deferred** (the Learner snoozes), or **Dismissed** (the Learner rejects).
- **Archived** for analytics regardless of disposition.

#### Owner
Learning (with Scheduling producing)

#### Relationships
- Produced for a **Learner**.
- May reference a set of **Concept**s, a **LearningPath** stage, or a **Review** schedule.
- May align with a **LearningGoal**.

#### Invariants
- A Recommendation is non-binding; the Engine never auto-acts on it without Learner consent.
- A Recommendation must be dismissible in one click.
- A dismissed Recommendation does not reappear in identical form for at least 7 days.

#### Examples
1. "Review these 5 due Concepts before September 15" — presented on the dashboard.
2. "Your weak Concepts suggest revisiting list mutability" — presented as a prerequisite drill.
3. "You are ready to advance to the Advanced Python path" — presented as a path progression.

#### Non-Examples
- The **DailyQueue** — the queue is imperative ("answer these now"); the recommendation is advisory.
- A **Milestone** notification — milestones recognize past progress; recommendations suggest future action.
- A marketing nudge ("upgrade to pro!") — that is a billing message, not a learning recommendation.

#### Future Extensions
- Recommendation personalization based on Learner cohorts.
- Recommendation effectiveness analytics (which recommendations drive the best outcomes).
- Mentor-shared recommendations.

---

### Daily Queue

#### Name
**Daily Queue**

#### Definition
A **Daily Queue** is a **Learner**-scoped, day-bounded list of **QuestionInstance**s that the **Scheduler** recommends the Learner complete on a given day. It is generated once per day (typically at the start of the Learner's local day) and is consumed across one or more **StudySession**s. The Daily Queue is the bridge between the long-term **StudyPlan** and the immediate **AdaptiveQueue**: it is what the Learner should do today; the AdaptiveQueue is what the Learner should do right now.

The Daily Queue is **advisory** — the Learner may exceed it, fall short, or skip it. The Engine does not penalize shortfall, but it does use daily queue completion as an input to engagement analytics.

#### Business Purpose
The Daily Queue exists to give the Learner a concrete, finite daily target. Without it, the Engine would present an endless stream of questions, which research and experience show reduces engagement. A bounded daily target gives the Learner a sense of "I'm done for today," which is itself a retention mechanism.

#### Lifecycle
- **Generated** at the start of the Learner's local day, based on the StudyPlan, due Reviews, and weak Concepts.
- **Consumed** across one or more StudySessions; the Engine tracks which items have been completed.
- **Refreshed** if the Learner completes it early and chooses to continue (the Engine generates a "bonus" queue).
- **Expired** at the end of the local day; uncompleted items are re-evaluated for the next day's queue.

#### Owner
Scheduling

#### Relationships
- Belongs to a **Learner** and a date.
- Contains **QuestionInstance** references.
- Informs the **AdaptiveQueue** at session start.
- Derived from the **StudyPlan** and the **Scheduler**'s ranking.

#### Invariants
- A Daily Queue is bounded in size (typically 10–30 questions, scaled by the Learner's daily goal).
- A Daily Queue cannot include a Concept whose prerequisites are not yet minimally mastered (unless the Learner explicitly requests a diagnostic).
- A Daily Queue expires at the end of the local day; it is not carried forward as-is.

#### Examples
1. On Monday morning the Engine generates a 15-question Daily Queue covering 3 due Reviews and 12 new Concepts.
2. A Learner completes all 15 by noon and asks for more; the Engine generates a 5-question bonus queue from weak Concepts.
3. A Learner completes only 8 of 15; the uncompleted 7 are re-evaluated for Tuesday's queue (some may be re-included, some deferred).

#### Non-Examples
- The **AdaptiveQueue** — the adaptive queue is for the current session; the daily queue is for the day.
- The **ReviewQueue** — the review queue is the set of due Reviews; the daily queue is a broader daily target that includes reviews and new material.
- A calendar reminder — that is external to the platform.

#### Future Extensions
- Daily Queue previews the night before.
- Daily Queue difficulty adjustment based on prior-day performance.
- Daily Queue sharing for study groups.

---

### Adaptive Queue

#### Name
**Adaptive Queue**

#### Definition
An **Adaptive Queue** is a **StudySession**-scoped, short-lived, ordered list of **QuestionInstance**s that the **Scheduler** produces for the current session. It is regenerated as the Learner answers — each **Attempt** updates mastery, which updates the queue. The Adaptive Queue is the imperative form of "what should I do right now?" within a session.

The Adaptive Queue is the runtime artifact of the learning loop. It is bounded in size (typically 10–20 questions) so that regeneration is cheap and so that the Learner is not committed to a long pre-computed sequence that mastery updates would invalidate.

#### Business Purpose
The Adaptive Queue exists to make the learning loop adaptive at the session level. Without it, the Engine would serve a fixed sequence; with it, the Engine reacts to every Attempt, drilling weak Concepts and skipping Concepts the Learner has just demonstrated mastery of.

#### Lifecycle
- **Generated** at StudySession start (or on resumption).
- **Updated** after each Attempt (the head item is consumed; the queue may be partially or fully regenerated).
- **Expired** when the StudySession ends.
- **Never persisted** beyond the session; it is a runtime artifact.

#### Owner
Scheduling

#### Relationships
- Belongs to a **StudySession**.
- Contains **QuestionInstance** references.
- Generated by the **Scheduler**; instantiated by the QuestionFactory.
- Influenced by the **DailyQueue** (the session typically draws from it).

#### Invariants
- The Adaptive Queue is deterministic given the same mastery state, the same session intent, and the same explicit seed (the **Scheduler**'s I3 invariant).
- The Adaptive Queue is bounded in size; it is never infinite.
- A regeneration preserves any items the Learner has already seen (no duplicate serves within a session).

#### Examples
1. A Learner starts a drilling session; the Adaptive Queue opens with 5 weak-Concept questions.
2. After answering 3 correctly, the queue regenerates to drop those Concepts and add the next 3 weak Concepts.
3. A Learner answers a Review incorrectly; the queue inserts a related remediation question before proceeding.

#### Non-Examples
- The **DailyQueue** — the daily queue is day-scoped; the adaptive queue is session-scoped.
- The **ReviewQueue** — the review queue is the set of due Reviews; the adaptive queue includes reviews plus new material.
- A static question list — that would be a non-adaptive quiz, which the project does not produce.

#### Future Extensions
- Multi-objective queue optimization (balance coverage, weakness, recency, difficulty in a learned ranking).
- Queue explainability (the Engine surfaces why each question was selected).
- Queue A/B testing infrastructure.

---

### Review Queue

#### Name
**Review Queue**

#### Definition
A **Review Queue** is a **Learner**-scoped, time-bounded list of **Concept**s (not questions) that are due for spaced-repetition review at a given moment. It is the set of Concepts whose **Review** records have a due date at or before now. The Review Queue is an input to the **AdaptiveQueue** and the **DailyQueue**; it is not itself a sequence of questions.

The Review Queue is the Engine's mechanism for converting memory decay into actionable work. Concepts enter the Review Queue when their review interval elapses; they leave when a Review Attempt is recorded.

#### Business Purpose
The Review Queue exists to make spaced repetition explicit and auditable. The Engine does not silently decide "this Concept is due"; it produces a Review Queue that the Learner can see and that drives scheduling. This visibility is what differentiates the Engine from black-box spaced-repetition systems.

#### Lifecycle
- **Populated** continuously as Review records become due.
- **Consumed** as the Learner completes Review Attempts (Concepts leave the queue on successful review, or are re-queued on failure).
- **Visible** to the Learner on the dashboard ("5 Concepts due for review").
- **Capped** to prevent review storms (the Engine never lets the Review Queue exceed a configurable size; overdue reviews are triaged by priority).

#### Owner
Scheduling (with the **Mastery Engine** producing Review records)

#### Relationships
- Belongs to a **Learner**.
- Contains **Concept** references (not questions).
- Drives the **DailyQueue** and **AdaptiveQueue**.
- Updated by **Review** records from the Mastery Engine.

#### Invariants
- A Concept is in the Review Queue if and only if its Review record's due date is at or before now.
- A Concept leaves the Review Queue only when a Review Attempt is recorded (not on time passage alone).
- The Review Queue is bounded; over-due reviews are triaged by priority, not dumped.

#### Examples
1. On Monday morning, the Review Queue contains 5 Concepts last reviewed a week ago.
2. A Learner reviews 3 of them; the queue drops to 2.
3. A Learner returns from a 2-week break; the Review Queue has grown to 18 Concepts; the Engine triages to the top 8 highest-priority and defers the rest.

#### Non-Examples
- The **DailyQueue** — the daily queue includes new material, not just reviews.
- The **AdaptiveQueue** — the adaptive queue is a sequence of questions; the review queue is a set of Concepts.
- A "to-do list" — that is a generic productivity concept; the Review Queue is a specific spaced-repetition artifact.

#### Future Extensions
- Review Queue prioritization strategies (priority by decay severity, by upcoming goal, by prerequisite criticality).
- Review Queue batch compression (a single question that reviews multiple Concepts).
- Review Queue forecasts ("you will have 12 reviews due Friday").

---

### Question Queue

#### Name
**Question Queue**

#### Definition
A **Question Queue** is a generic term for any ordered list of **QuestionInstance**s produced by the **Scheduler**. It is the umbrella concept covering the **AdaptiveQueue** (session-scoped), the **DailyQueue** (day-scoped), and any future queue variant. When the project needs to refer to "a list of questions the Engine produces" without specifying which kind, it uses Question Queue.

The Question Queue is not a separate artifact — it is the abstract type of which the Adaptive and Daily queues are concrete instances. Engineers use the term in interfaces and base classes; product and design use the specific names.

#### Business Purpose
The Question Queue exists to give engineering a single abstraction over the various queue types, so that infrastructure (caching, regeneration, metrics) can be built once and reused. Product and design always use the specific names in user-facing language.

#### Lifecycle
- Inherited from the specific queue type (AdaptiveQueue or DailyQueue).

#### Owner
Scheduling

#### Relationships
- Umbrella for **AdaptiveQueue** and **DailyQueue**.
- Contains **QuestionInstance** references.

#### Invariants
- Every concrete Question Queue is bounded in size.
- Every concrete Question Queue is regenerable from its inputs.
- Every concrete Question Queue records the seed used in generation.

#### Examples
1. An engineer writes a generic `QuestionQueue` interface that both `AdaptiveQueue` and `DailyQueue` implement.
2. A metric tracks "average Question Queue regeneration time" across both types.
3. A cache layer caches any Question Queue by its deterministic cache key.

#### Non-Examples
- The **ReviewQueue** — the review queue contains Concepts, not questions, and is therefore not a Question Queue.
- A static question set — that is content, not a queue.
- A Learner's question history — that is the Attempt stream, not a queue.

#### Future Extensions
- New queue variants (e.g., a "diagnostic queue" for placement tests, a "challenge queue" for advanced Learners).
- Queue composition rules (a daily queue composed of review questions + new questions + challenge questions).

---

### Concept

#### Name
**Concept**

#### Definition
A **Concept** is the atomic unit of knowledge in the platform. It is small enough to be mastered independently and large enough to be tested meaningfully. A Concept belongs to exactly one **Subject**, has a stable identifier, a human-readable name, a description, and a difficulty estimate. Concepts are the vertices of the **KnowledgeGraph**.

Atomicity is the defining property of a Concept. "List mutability in Python" is a Concept; "Python data structures" is not (it is a cluster of Concepts). The Engine measures mastery at the Concept level; it does not measure "mastery of Python" as a single number — that is a derived aggregate.

#### Business Purpose
The Concept exists to make mastery measurable. Without atomic units, the Engine could not produce a meaningful MasteryScore — it would have to score vague clusters, which would not drive precise scheduling. Atomic Concepts also make the **KnowledgeGraph** useful: dependencies between Concepts are precise, and prerequisite-readiness scoring is meaningful.

#### Lifecycle
- **Authored** as a draft by an **Instructor**.
- **Reviewed** in the **ReviewWorkflow**.
- **Published** as part of a **ContentVersion**.
- **Versioned** on edit; old versions preserved for historical Attempt interpretability.
- **Deprecated** when superseded; never deleted while any Attempt references it.

#### Owner
Content

#### Relationships
- Belongs to a **Subject**.
- Has one or more **LearningObjective**s.
- Has zero or more **ConceptDependency** edges (prerequisites and dependents).
- Has zero or more **Misconception**s.
- Has zero or more **QuestionTemplate**s that test it.
- Has one **MasteryScore** per **Learner** who has encountered it.

#### Invariants
- A Concept belongs to exactly one Subject.
- A Concept cannot be deleted while any Attempt references it (deprecate instead).
- A Concept must have at least one LearningObjective before publishing.

#### Examples
1. `python.list.mutability` — "Lists in Python are mutable; reassigning an element modifies the original list."
2. `python.dict.lookup_complexity` — "Average-case dict lookup is O(1); worst-case is O(n)."
3. `python.gil.bound_threads` — "The GIL prevents true parallelism for CPU-bound threads."

#### Non-Examples
- A **LearningObjective** — an objective is a verifiable statement about a Concept; the Concept is the knowledge unit itself.
- A **SubConcept** — see that term; the project does not generally use SubConcepts, but the term is defined for the rare case where it is needed.
- A "topic" (forbidden) — the project uses Concept, not Topic.

#### Future Extensions
- Concept difficulty learned from Attempt data (replacing the author's prior estimate).
- Concept cross-references (related Concepts that are not prerequisites).
- Concept retirement workflow (deprecated Concepts that learners should no longer study).

---

### Sub Concept

#### Name
**Sub Concept**

#### Definition
A **Sub Concept** is a refinement of a **Concept** used when a Concept is complex enough to warrant internal decomposition for pedagogical clarity, but not enough to justify splitting into multiple independent Concepts. A Sub Concept does not have its own **MasteryScore** — mastery is measured at the Concept level. Sub Concepts exist to structure explanations and **WorkedExample**s, not to multiply the mastery measurement surface.

The project uses Sub Concepts sparingly. The default is to split a complex Concept into multiple Concepts connected by **ConceptDependency** edges. Sub Concepts are reserved for cases where splitting would fragment the mastery signal unhelpfully.

#### Business Purpose
The Sub Concept exists to give authors a middle ground between "one Concept with everything" and "many Concepts with thin mastery signals." It is a content-organization tool, not a measurement tool.

#### Lifecycle
- **Authored** within a parent Concept by an Instructor.
- **Versioned** with the parent Concept.
- **Deprecated** with the parent Concept.

#### Owner
Content

#### Relationships
- Belongs to exactly one parent **Concept**.
- May be referenced by **Explanation**s and **WorkedExample**s.
- Does NOT have its own MasteryScore.

#### Invariants
- A Sub Concept has exactly one parent Concept.
- A Sub Concept has no independent mastery measurement.
- A Sub Concept cannot outlive its parent.

#### Examples
1. The Concept `python.gil.bound_threads` has Sub Concepts "GIL and I/O-bound threads," "GIL and CPU-bound threads," and "GIL release points" — used to structure the explanation.
2. The Concept `sql.join.types` has Sub Concepts "inner join," "left join," "full outer join" — used to organize worked examples.
3. The Concept `python.list.slicing` has a Sub Concept "negative indexing" — used to introduce one subtopic before another.

#### Non-Examples
- A **Concept** — a Concept has its own MasteryScore; a Sub Concept does not.
- A **LearningObjective** — an objective is a verifiable statement; a Sub Concept is a knowledge refinement.
- A "subsection" of a course module (forbidden framing) — the project does not have modules.

#### Future Extensions
- Sub Concept promotion to Concept (when measurement at the sub-level becomes valuable).
- Sub Concept analytics (which subtopics within a Concept cause the most failure).

---

### Concept Dependency

#### Name
**Concept Dependency**

#### Definition
A **Concept Dependency** is a directed edge in the **KnowledgeGraph** from one **Concept** to another, indicating that mastery of the source depends on mastery of the target. Dependencies are typed (prerequisite, related, reinforces) and weighted (strong, weak). The dependency graph is acyclic at any published version.

Dependencies drive the **Scheduler**'s prerequisite-readiness scoring: a Learner cannot be served a Concept whose prerequisites are not yet minimally mastered. They also drive **Misconception** remediation: if a Learner fails a Concept, the Engine may recommend reviewing its prerequisites.

#### Business Purpose
The Concept Dependency exists to make the curriculum's pedagogical structure explicit and machine-readable. Without it, the Scheduler would optimize for short-term mastery gains without respecting the natural learning order, which research and practice show produces fragile mastery.

#### Lifecycle
- **Authored** by an **Instructor** when creating or editing a Concept.
- **Validated** at publish time (cycles are rejected).
- **Versioned** with the **ContentVersion**.
- **Deprecated** when the dependency is removed in a new version; the old edge is preserved for historical Attempt interpretability.

#### Owner
Content

#### Relationships
- Connects two **Concept**s within a **Subject**.
- Read by the **Scheduler** for prerequisite-readiness scoring.
- Read by the **Mastery Engine** for remediation recommendations.

#### Invariants
- The dependency graph is acyclic at any published version (enforced at publish time).
- A dependency cannot be self-referential.
- Dependency type and weight are mandatory; no untyped edges.

#### Examples
1. `python.list.comprehension` depends on `python.list.mutability` (prerequisite, strong).
2. `python.dict.lookup_complexity` reinforces `python.hash.basics` (reinforces, weak).
3. `python.asyncio.gather` depends on `python.asyncio.coroutines` (prerequisite, strong) and `python.asyncio.event_loop` (prerequisite, strong).

#### Non-Examples
- A **Prerequisite** — prerequisite is one type of Concept Dependency, not a synonym.
- A "related topic" link on a wiki — that is untyped and non-binding; Concept Dependencies are typed, weighted, and pedagogically load-bearing.
- A course-module ordering — the project does not have modules.

#### Future Extensions
- Dependency weight learned from Learner data (which prerequisites actually predict success).
- Conditional dependencies (Concept A requires B only for Learners who studied path X).
- Dependency visualization for Learners.

---

### Learning Objective

#### Name
**Learning Objective**

#### Definition
A **Learning Objective** is a verifiable statement of what a **Learner** should be able to do with a **Concept**. It is written in observable terms: "predict the time complexity of a dict lookup," "identify when a list mutation will alias another reference." Every **QuestionTemplate** traces to at least one Learning Objective; every **Misconception** traces to an Objective it would violate.

Learning Objectives are the bridge between curriculum design and assessment. They are what makes the Engine's mastery measurement meaningful — a MasteryScore is "the probability the Learner can satisfy this Concept's Objectives," not a vague "understanding level."

#### Business Purpose
The Learning Objective exists to make mastery measurable and to enforce assessment-coverage discipline. Without Objectives, a Concept would be a vague blob; with them, every Question has a verifiable purpose, and gaps in assessment coverage are detectable.

#### Lifecycle
- **Authored** by an **Instructor** for a **Concept**.
- **Reviewed** in the **ReviewWorkflow**; vague objectives ("understand lists") are rejected.
- **Published** with the Concept.
- **Versioned** with the Concept.

#### Owner
Content

#### Relationships
- Belongs to a **Concept** (one Concept has one or more Objectives).
- Tested by one or more **QuestionTemplate**s.
- Violated by one or more **Misconception**s.

#### Invariants
- Every published Concept has at least one Learning Objective.
- Every published QuestionTemplate traces to at least one Learning Objective.
- Every published Misconception traces to an Objective it violates.
- An Objective is written in observable terms; vague objectives are rejected at editorial review.

#### Examples
1. For `python.dict.lookup_complexity`: "Predict the average-case and worst-case time complexity of a dict lookup."
2. For `python.list.mutability`: "Identify whether a code snippet mutates the original list or creates a new one."
3. For `python.gil.bound_threads`: "Predict whether a multi-threaded Python program will see speedup on a multi-core machine for a given workload."

#### Non-Examples
- A **Concept** — the Concept is the knowledge unit; the Objective is the verifiable skill statement about it.
- A **QuestionTemplate** — the template tests the Objective; it is not the Objective.
- A "learning outcome" in a syllabus — that is the same idea in a different vocabulary; the project uses Learning Objective.

#### Future Extensions
- Objective difficulty learned from data.
- Objective-level mastery (finer-grained than Concept-level).
- Objective mapping across Subjects (a Python Objective that maps to a SQL Objective for transfer learning).

---

### Prerequisite

#### Name
**Prerequisite**

#### Definition
A **Prerequisite** is a specific type of **ConceptDependency** where the source Concept cannot be meaningfully studied without prior mastery of the target Concept. It is the strongest form of dependency. The **Scheduler** enforces prerequisites: a Learner is not served a Concept whose prerequisites are not yet minimally mastered, unless the Learner explicitly requests a diagnostic.

"Prerequisite" is both a relationship (the edge in the graph) and a role (the target Concept is "a prerequisite of" the source). The project uses the term in both senses; context disambiguates.

#### Business Purpose
The Prerequisite exists to enforce pedagogical order without forcing the Learner to follow a rigid linear path. The Engine can serve Concepts in any order that respects prerequisites, giving the Scheduler flexibility while preserving learning integrity.

#### Lifecycle
Inherited from **ConceptDependency**.

#### Owner
Content

#### Relationships
- A type of **ConceptDependency**.
- The target Concept plays the Prerequisite role for the source Concept.
- Read by the **Scheduler** for prerequisite-readiness scoring.

#### Invariants
- A Prerequisite is the strongest dependency type; violating it blocks scheduling.
- A Concept cannot be a Prerequisite of itself.
- Prerequisite transitivity is honored: if A requires B and B requires C, A effectively requires C.

#### Examples
1. `python.list.comprehension` has Prerequisite `python.list.mutability`.
2. `python.asyncio.gather` has Prerequisites `python.asyncio.coroutines` and `python.asyncio.event_loop`.
3. A Learner who has not mastered `python.dict.basics` cannot be served `python.dict.lookup_complexity` (it is a Prerequisite).

#### Non-Examples
- A "related" Concept Dependency — related is weaker; it suggests, not requires.
- A "reinforces" Concept Dependency — reinforces is bidirectional soft support; prerequisite is unidirectional hard requirement.
- A course-module prerequisite (forbidden framing).

#### Future Extensions
- Prerequisite waivers (a Learner tests out of a Prerequisite via a placement test).
- Conditional Prerequisites (path-dependent).
- Prerequisite strength learned from data.

---

### Knowledge Graph

#### Name
**Knowledge Graph**

#### Definition
A **Knowledge Graph** is the complete set of **Concept**s and **ConceptDependency** edges within a **Subject**. It is the structural map of the Subject's curriculum. The Knowledge Graph is acyclic at any published version; it is the input that makes the **LearningPath**'s topological ordering possible.

The Knowledge Graph is a content artifact, versioned with the **Subject**. It is not a runtime data structure — it is the published structure against which the **Scheduler** and **Mastery Engine** operate.

#### Business Purpose
The Knowledge Graph exists to make the curriculum machine-readable. Without it, the Engine could not respect prerequisites, could not identify weak clusters, and could not produce meaningful **LearningPath**s. The graph is the substrate of all adaptive scheduling.

#### Lifecycle
- **Grown** as Instructors author new Concepts and Dependencies.
- **Versioned** as part of each **ContentVersion**.
- **Validated** for acyclicity at every publish.
- **Deprecatable** as a whole (when a Subject is retired) but not deletable while Learners are enrolled.

#### Owner
Content

#### Relationships
- Belongs to a **Subject**.
- Contains **Concept**s (vertices) and **ConceptDependency**s (edges).
- Traversed by **LearningPath**s.
- Read by the **Scheduler** and **Mastery Engine**.

#### Invariants
- The graph is acyclic at every published version.
- Every Concept in the graph belongs to the same Subject.
- The graph is connected (or has a documented reason for being disconnected).

#### Examples
1. The Python Subject's Knowledge Graph contains 80 Concepts and 120 ConceptDependency edges at v1.0.
2. A new Concept `python.match.statement` is added; the graph grows to 81 Concepts and 122 edges.
3. A cycle is detected when an Instructor tries to publish; the publish is rejected with a cycle error.

#### Non-Examples
- A **LearningPath** — the path is an ordering; the graph is the structure.
- A "topic tree" (forbidden) — the project uses a graph, not a tree.
- A mind map — that is a visualization; the Knowledge Graph is the data.

#### Future Extensions
- Graph analytics (cluster detection, centrality, bridge Concepts).
- Graph visualization for Learners ("here's where you are in the map").
- Cross-Subject graph links (a Python graph that references a SQL graph for data-engineering Learners).

---

### Misconception

#### Name
**Misconception**

#### Definition
A **Misconception** is a specific, documented incorrect mental model a **Learner** may hold about a **Concept**. Each Misconception has a name, a description of the incorrect model, a diagnosis of why Learners fall into it, and a remediation strategy. Misconceptions are linked to **QuestionTemplate**s via tagged **Distractor**s: when a Learner selects a Misconception-tagged Distractor, the Mastery Engine records the Misconception against the Learner, enabling targeted remediation.

Misconceptions are the Engine's most important content artifact after Concepts themselves. They convert wrong answers from noise into signal — the Engine learns not just that the Learner was wrong, but why.

#### Business Purpose
The Misconception exists to make the Engine's "what next?" answer diagnostic, not just corrective. Without Misconceptions, the Engine could only say "you got this wrong, here's the right answer"; with them, the Engine can say "you got this wrong because you hold Misconception X; here's the targeted remediation."

#### Lifecycle
- **Authored** by an **Instructor** for a **Concept**'s **LearningObjective**.
- **Linked** to one or more **QuestionTemplate**s via tagged Distractors.
- **Published** with the Concept.
- **Monitored** post-publish; if a Misconception never appears in Learner errors, it may be inaccurate and is flagged for review.

#### Owner
Content

#### Relationships
- Belongs to a **Concept** (via a **LearningObjective**).
- Linked to **QuestionTemplate**s via tagged **Distractor**s.
- Recorded against a **Learner** when the Learner selects a tagged Distractor.
- Drives targeted remediation in the **Scheduler**.

#### Invariants
- Every published Concept has at least one Misconception per Learning Objective.
- Every published Misconception traces to a Learning Objective it violates.
- A Misconception must have at least one Distractor that elicits it (else it is undetectable).

#### Examples
1. For `python.list.mutability`: "Reassigning an element creates a new list." (Wrong: it modifies in place.)
2. For `python.dict.lookup_complexity`: "Dict lookup is O(n) because it scans keys." (Wrong: average O(1) via hashing.)
3. For `python.gil.bound_threads`: "Adding threads always speeds up CPU-bound Python." (Wrong: GIL prevents it.)

#### Non-Examples
- A **Distractor** — the Distractor is the wrong answer; the Misconception is the mental model the Distractor appeals to.
- A common mistake — that is informal; a Misconception is documented and linked.
- A "bug" in Learner understanding — the project uses Misconception, not bug.

#### Future Extensions
- Misconception clustering across Concepts (Learners who hold Misconception X often also hold Misconception Y).
- Misconception severity learned from data.
- Misconception remediation effectiveness analytics.

---

### Hint

#### Name
**Hint**

#### Definition
A **Hint** is a non-answer-revealing nudge shown to a **Learner** who is stuck on a **QuestionInstance**. Hints are tiered (Hint 1 is gentle, Hint 2 is more specific, Hint 3 is near-complete), and each tier is part of the **QuestionTemplate**'s published content. Hint usage is recorded on the **Attempt** and modulates the **MasteryScore** update (a correct answer with hints counts less than a correct answer without).

Hints are optional — the Learner may submit an answer without using any hint. They are also limited per question (typically 3 tiers) to prevent the hint system from becoming an answer-reveal system.

#### Business Purpose
The Hint exists to keep the Learner in the learning loop when they are stuck, without removing the cognitive work that produces mastery. Without hints, a stuck Learner either guesses randomly (low learning value) or gives up (lost engagement). Hints provide a productive middle path.

#### Lifecycle
- **Authored** by an **Instructor** as part of a **QuestionTemplate**.
- **Tiered** (Hint 1, Hint 2, Hint 3), each more specific than the last.
- **Versioned** with the Template.
- **Recorded** on the Attempt when used (which tiers, in what order).

#### Owner
Content (authored) with Assessment (recorded)

#### Relationships
- Belongs to a **QuestionTemplate**.
- Recorded on an **Attempt** when used.
- Modulates the **MasteryScore** update for that Attempt.

#### Invariants
- A Hint never reveals the correct answer directly.
- Hint tiers are ordered; the Engine does not skip tiers (a Learner cannot request Hint 3 without seeing Hint 1 and 2).
- Hint usage reduces the mastery credit for a correct answer; it never increases it.

#### Examples
1. Hint 1 for a list-mutability question: "Think about whether the operation modifies in place."
2. Hint 2: "Consider whether `=` on an index creates a new object."
3. Hint 3: "Lists are mutable; `lst[0] = x` modifies `lst` in place."

#### Non-Examples
- An **Explanation** — the explanation is shown after the Attempt; the hint is shown during.
- A **WorkedExample** — a worked example is a content artifact for study; a hint is an in-question nudge.
- A "solution" — solutions reveal the answer; hints do not.

#### Future Extensions
- Adaptive hint thresholds (offer hints automatically after N seconds of inactivity).
- Hint effectiveness analytics (which hints actually help Learners answer correctly).
- Hint authoring AI assistance (drafting tiered hints for Instructor review).

---

### Explanation

#### Name
**Explanation**

#### Definition
An **Explanation** is the content artifact shown to a **Learner** after an **Attempt**, regardless of whether the Attempt was correct. It explains the right answer, why the right answer is right, why common wrong answers are wrong, and what the Learner should take away. Explanations are tied to a **QuestionTemplate** (more precisely, to a Template version) and may have variants keyed by the Learner's specific outcome (correct, Misconception A, Misconception B).

Explanations are part of the content graph and go through the same **ReviewWorkflow** as other content. They are not generated at runtime.

#### Business Purpose
The Explanation exists to close the learning loop on each Attempt. Without it, the Learner knows whether they were right or wrong but not why; the Attempt produces scoring signal but not learning. The Explanation converts every Attempt into a learning opportunity, not just a measurement.

#### Lifecycle
- **Authored** by an **Instructor** as part of a **QuestionTemplate**.
- **Variant-authored** for common Misconceptions (the variant for Misconception A explains why A is wrong).
- **Reviewed** and **Published** with the Template.
- **Versioned** with the Template.

#### Owner
Content

#### Relationships
- Belongs to a **QuestionTemplate** (or a Template version).
- Has variants keyed by outcome (correct, specific Misconceptions).
- May reference **WorkedExample**s for deeper study.

#### Invariants
- Every published QuestionTemplate has at least one Explanation (the "correct" variant).
- An Explanation never contradicts the Template's correct answer.
- Explanations are deterministic given the Template version and the outcome key.

#### Examples
1. The "correct" variant: "Right! List mutation modifies in place; here's the deeper why."
2. The "Misconception A" variant: "You chose 'creates a new list' — that's a common error. Here's why mutation modifies in place."
3. The "Misconception B" variant: "You chose 'raises an error' — that's incorrect. Here's why mutation is allowed."

#### Non-Examples
- A **Hint** — the hint is during; the explanation is after.
- A **WorkedExample** — a worked example is a study artifact; the explanation is an Attempt-closing artifact.
- A "solution" in the LeetCode sense — those are end-of-problem reveals; Explanations are pedagogical and outcome-aware.

#### Future Extensions
- Explanation effectiveness analytics (does viewing the Explanation improve the next Attempt on the same Concept?).
- Explanation personalization (variant selected by Learner's prior Misconception history).
- Multi-modal Explanations (text + diagram + interactive).

---

### Example

#### Name
**Example**

#### Definition
An **Example** is a concrete instance of a **Concept** in use, shown to a **Learner** as a study artifact. Examples are part of the content graph and may appear within **Explanation**s, on Concept pages, or in **WorkedExample**s. An Example is not a question — it does not test; it illustrates.

Examples are distinct from **WorkedExample**s (which are step-by-step problem solutions) and from **QuestionInstance**s (which are test events). An Example is a static illustration; a Worked Example is a process narrative.

#### Business Purpose
The Example exists to give the Learner a concrete referent for an abstract Concept. Many Learners understand abstractions best through instances; Examples provide those instances without forcing the Learner to encounter them only via questions.

#### Lifecycle
- **Authored** by an **Instructor** for a **Concept**.
- **Versioned** with the Concept.
- **Referenced** from **Explanation**s and Concept pages.

#### Owner
Content

#### Relationships
- Belongs to a **Concept**.
- May be referenced by **Explanation**s and **WorkedExample**s.

#### Invariants
- An Example is correct (it does not illustrate a Misconception unless explicitly framed as a counter-example).
- An Example is deterministic given its version.

#### Examples
1. For `python.list.mutability`: "After `lst = [1, 2, 3]; lst[0] = 9`, `lst` is `[9, 2, 3]`."
2. For `python.dict.lookup_complexity`: "Looking up `d['name']` in a 10M-entry dict takes ~100ns on average."
3. For `python.gil.bound_threads`: "Two threads summing a list of 10M ints take ~the same time as one thread."

#### Non-Examples
- A **WorkedExample** — a worked example walks through solving a problem; an Example shows a Concept in use.
- A **QuestionInstance** — a question tests; an example illustrates.
- A counter-example — that is a special case; the project uses "counter-example" explicitly when the illustration is of what not to do.

#### Future Extensions
- Example difficulty tagging.
- Example generation from templates (for variation).
- Example recommendation based on Learner's prior confusion patterns.

---

### Worked Example

#### Name
**Worked Example**

#### Definition
A **Worked Example** is a step-by-step narrative showing how to solve a representative problem using a **Concept**. It is a study artifact, not a test. Worked Examples are longer and more structured than **Example**s (which are single illustrations) and are used to teach problem-solving process, not just Concept application.

Worked Examples are part of the content graph, authored by **Instructor**s, versioned with the **ContentVersion**. They may be referenced from **Explanation**s or studied independently from a Concept page.

#### Business Purpose
The Worked Example exists to teach process, not just result. Many Learners can apply a Concept to a simple instance but cannot reason through a multi-step problem; Worked Examples bridge that gap by externalizing the expert's reasoning.

#### Lifecycle
- **Authored** by an **Instructor** for a **Concept** or a small cluster of Concepts.
- **Reviewed** in the **ReviewWorkflow**.
- **Published** with the **ContentVersion**.
- **Versioned** with the Concept(s).

#### Owner
Content

#### Relationships
- Belongs to one or more **Concept**s.
- May reference **Example**s and **Explanation**s.
- May be linked from a **QuestionTemplate** as a "study this if you got it wrong" reference.

#### Invariants
- A Worked Example is correct (the steps produce the stated answer).
- A Worked Example is deterministic given its version.
- A Worked Example's reasoning is explicit (not just "the answer is X").

#### Examples
1. For `python.list.mutability`: a 6-step walkthrough of tracing through code that mutates a list across function calls.
2. For `python.dict.lookup_complexity`: a walkthrough of analyzing hash collisions and explaining when lookup degrades to O(n).
3. For `python.gil.bound_threads`: a walkthrough of profiling a CPU-bound multi-threaded program and explaining why it does not speed up.

#### Non-Examples
- An **Example** — an example is a single illustration; a Worked Example is a process narrative.
- A **QuestionInstance** — a question tests; a Worked Example teaches.
- A tutorial video — that is a different medium; the project may host videos but they are not Worked Examples.

#### Future Extensions
- Interactive Worked Examples (the Learner steps through, predicting each step).
- Worked Example branching (different paths for different Learner backgrounds).
- Worked Example analytics (which steps cause the most confusion).

---

### Assessment

#### Name
**Assessment**

#### Definition
An **Assessment** is the act of evaluating a **Learner**'s response to a **QuestionInstance**. It is the bounded context that owns **Attempt**s, **Answer**s, and the scoring logic that converts an Answer into an outcome (correct, incorrect, partial). The Assessment context does not own mastery — that is the **Mastery Engine**'s domain; Assessment provides the evidence that Mastery consumes.

"Assessment" is also the noun for a specific assessment event — the scoring of one Attempt. Context disambiguates: "the Assessment context" (the bounded context) vs. "an Assessment event" (one scoring).

#### Business Purpose
The Assessment exists to separate the act of measuring from the act of modeling mastery. This separation lets the Engine swap scoring logic (e.g., add code-execution scoring) without touching the Mastery Engine, and swap mastery algorithms without touching scoring.

#### Lifecycle
- **Triggered** when a Learner submits an Answer to a QuestionInstance.
- **Executed** by the Assessment Domain Service (pure function: Answer + Question → Outcome).
- **Persisted** as an **Attempt** by the Assessment Repository.
- **Published** as an `AttemptRecorded` domain event for the Mastery Engine to consume.

#### Owner
Assessment

#### Relationships
- Owns **Attempt**s and **Answer**s.
- Consumes **QuestionInstance**s (produced by the QuestionFactory).
- Publishes `AttemptRecorded` events consumed by the **Mastery Engine** and **Analytics**.
- Does not own **MasteryScore**s.

#### Invariants
- An Assessment is deterministic given the QuestionInstance, the Answer, and the QuestionTemplate version.
- An Assessment produces exactly one outcome per Attempt.
- Assessment never modifies mastery directly.

#### Examples
1. A Learner submits "O(1)" to a dict-lookup question; Assessment scores it correct.
2. A Learner submits code that raises an exception; Assessment scores it incorrect and records the error.
3. A Learner submits a partial answer; Assessment scores it partial-credit per the Template's rubric.

#### Non-Examples
- A **MasteryScore** — mastery is the model; assessment is the measurement.
- A **QuestionInstance** — the question is the stimulus; the assessment is the scoring of the response.
- A "test" or "exam" — those are content bundles; the project uses Assessment for the scoring act.

#### Future Extensions
- Multi-modal Assessment (code + free-response + multiple-choice in one question).
- Peer Assessment (Learners scoring each other, for future study-group features).
- Automated Assessment quality review (does the scoring match expert judgment?).

---

### Question Template

#### Name
**Question Template**

#### Definition
A **Question Template** is a parameterized specification for generating **QuestionInstance**s. It references one or more **LearningObjective**s, declares the parameter schema, the prompt template, the correct-answer generator, the **Distractor** generator, the **Explanation** template, and the **Misconception** mapping. Templates are versioned; an edit produces a new version, preserving historical Attempts' interpretability.

The Question Template is the unit of content authoring for assessment. The Engine never serves a Template directly; it always instantiates a QuestionInstance via the QuestionFactory.

#### Business Purpose
The Question Template exists to make assessment scalable and reproducible. One Template produces many concrete questions, each testing the same Objectives with different parameters. This gives the Engine infinite practice material from finite authoring effort, and it makes every Attempt replayable from the Template + seed.

#### Lifecycle
- **Authored** by an **Instructor** as a draft.
- **Reviewed** in the **ReviewWorkflow** (peer, editorial, QA/pilot).
- **Published** as part of a **ContentVersion**.
- **Versioned** on edit; old versions preserved.
- **Deprecated** when superseded; never deleted while any Attempt references it.

#### Owner
Content

#### Relationships
- Belongs to a **Subject**.
- References one or more **LearningObjective**s.
- References one or more **Concept**s.
- Has one or more **Distractor** generators (for multiple-choice).
- Has one **Explanation** template with variants.
- Has one or more **Hint** tiers.
- Has a **Difficulty** estimate and a discrimination estimate.
- Instantiated into **QuestionInstance**s by the QuestionFactory.

#### Invariants
- A Template must trace to at least one Learning Objective.
- A Template is deterministic given its version, parameter values, and seed.
- A Template's correct-answer generator must produce the correct answer for any valid parameter values.
- A Template's Distractors must be tagged with the Misconception they appeal to (or "none" for random distractors).

#### Examples
1. A Template for `python.dict.lookup_complexity`: parameters are dict size and key; prompt asks for time complexity; correct answer is "O(1)"; distractors include "O(n)" (Misconception: scanning).
2. A Template for `python.list.mutability`: parameters are an operation; prompt asks whether it mutates; correct answer varies; distractors appeal to specific Misconceptions.
3. A Template for code execution: parameters are a function signature and a test case; prompt asks the Learner to implement the function; correct answer is the test passing.

#### Non-Examples
- A **QuestionInstance** — the instance is the concrete question; the Template is the specification.
- A "question bank" entry — that is a static question; the Template is parameterized.
- An **InterviewQuestion** — see that term; an InterviewQuestion is a curated real-world question, often wrapped in a Template.

#### Future Extensions
- Template composition (a Template that combines multiple Concepts).
- Template inheritance (a Template extends another).
- AI-assisted Template drafting (with mandatory Instructor review).

---

### Question Instance

#### Name
**Question Instance**

#### Definition
A **Question Instance** is a concrete, instantiated question ready to be served to a **Learner**. It is produced by the QuestionFactory from a **QuestionTemplate**, a parameter seed, and a **ContentVersion**. It has the rendered prompt, the rendered choices or input contract, the correct answer, the **Distractor**s with their **Misconception** tags, and the Template version reference.

A Question Instance is **immutable once served** — if a Template is edited after a Question was served, the served Question is preserved verbatim for replay. Every **Attempt** references the Question Instance (via Template version + seed) so the exact question can be reconstructed.

#### Business Purpose
The Question Instance exists to be the unit of assessment. The Engine scores Instances; it does not score Templates. Separating Instance from Template lets the Engine serve many concrete questions from one Template, and lets analytics reason about specific serves (e.g., "this Distractor was selected 23% of the time").

#### Lifecycle
- **Instantiated** by the QuestionFactory from a Template + seed.
- **Served** to a Learner (the served timestamp starts the time-to-answer clock).
- **Answered** via an **Attempt** (or marked abandoned after timeout).
- **Immutable** after serving; never edited.

#### Owner
Assessment (with Content owning the Template that produces it)

#### Relationships
- Produced from a **QuestionTemplate** version + seed.
- Belongs to a **ContentVersion**.
- References its **Distractor**s with Misconception tags.
- The subject of an **Attempt** when served.

#### Invariants
- A Question Instance is deterministic given its Template version, seed, and Content Version.
- A Question Instance is immutable once served.
- A Question Instance references exactly one Template version.

#### Examples
1. The dict-lookup Template with seed 12345 produces a Question Instance with a 1M-entry dict and key "user_id"; the correct answer is "O(1)."
2. The list-mutability Template with seed 67890 produces a Question Instance asking about `lst.append(x)`; the correct answer is "mutates in place."
3. A code-execution Template with seed 24680 produces a Question Instance asking the Learner to implement `two_sum`.

#### Non-Examples
- A **QuestionTemplate** — the Template is the specification; the Instance is the concrete question.
- An **Attempt** — the Attempt is the Learner's response; the Question Instance is what they respond to.
- A "question" in a static quiz — that is content; the project's Questions are Template-instantiated.

#### Future Extensions
- Question Instance provenance tracking (which seed, which generation context).
- Instance-level analytics (which specific Instances discriminate best).
- Instance reuse rules (avoid serving the same Instance to the same Learner twice within N days).

---

### Question Difficulty

#### Name
**Question Difficulty**

#### Definition
A **Question Difficulty** is a coarse estimate of how hard a **QuestionTemplate** is, used by the **Scheduler** as a prior before sufficient Attempt data accumulates, and by the **Mastery Engine** to modulate how strongly an Attempt updates the **MasteryScore**. Difficulty is authored as a prior (e.g., easy, medium, hard) and refined over time from observed Attempt outcomes.

Difficulty is a property of the Template, not of a specific Question Instance — all Instances of a Template share the same Difficulty prior, though observed difficulty may vary per Instance as data accumulates.

#### Business Purpose
The Question Difficulty exists to give the Scheduler and Mastery Engine a starting estimate before data arrives. Without it, the first few Attempts on a new Template would be treated identically to Attempts on a well-known Template, producing noisy mastery updates. Difficulty stabilizes the cold-start period.

#### Lifecycle
- **Authored** by an **Instructor** as a prior (easy / medium / hard, with optional numeric 0–1).
- **Refined** by nightly jobs that compute observed difficulty from Attempt outcomes.
- **Surfaced** for review if observed difficulty diverges significantly from the prior.
- **Versioned** with the Template.

#### Owner
Content (with Analytics refining)

#### Relationships
- A property of a **QuestionTemplate**.
- Read by the **Scheduler** for cold-start ranking.
- Read by the **Mastery Engine** for Attempt weighting.

#### Invariants
- Difficulty is bounded (easy/medium/hard, or 0–1 numeric).
- Difficulty is per-Template, not per-Instance.
- Observed difficulty overrides the prior after sufficient data (configurable threshold).

#### Examples
1. The dict-lookup Template is authored as "easy"; observed data confirms 85% correct on first Attempt.
2. The GIL-bound-threads Template is authored as "hard"; observed data confirms 35% correct.
3. A Template authored as "medium" shows 20% correct in observed data; it is flagged for review (the prior was wrong).

#### Non-Examples
- **MasteryScore** — mastery is the Learner's state; difficulty is the Template's property.
- A Learner's "skill level" — that is mastery, not difficulty.
- Time-to-answer — that is a signal that informs difficulty but is not difficulty itself.

#### Future Extensions
- Continuous difficulty (0–1) replacing the coarse prior.
- Per-Learner difficulty (a question that is easy for one cohort may be hard for another).
- Difficulty drift detection over time.

---

### Answer

#### Name
**Answer**

#### Definition
An **Answer** is a **Learner**'s response to a **QuestionInstance**. For multiple-choice it is a choice identifier; for code questions it is a code string plus an execution result; for free-response it is a text string. The Answer exists separately from the **Attempt** so that multiple Answer revisions (within a single Attempt, for code questions with iterative execution) can be stored without duplicating Attempt metadata.

An Answer is the Learner's input; the **Assessment** context scores it to produce an outcome. The Answer is immutable once the Attempt is submitted, but pre-submission revisions are retained for analytics on the Learner's problem-solving process.

#### Business Purpose
The Answer exists to separate the Learner's input from the scoring of that input. This separation lets the Engine support multi-step answers (code with iterative execution) and lets analytics study the Learner's revision patterns.

#### Lifecycle
- **Drafted** by the Learner in the UI.
- **Revised** zero or more times before submission (for code questions with execution).
- **Submitted** as part of an **Attempt**.
- **Scored** by the Assessment Domain Service.
- **Immutable** after submission.

#### Owner
Assessment

#### Relationships
- Belongs to an **Attempt**.
- References the **QuestionInstance** it answers.
- Scored by the Assessment Domain Service.

#### Invariants
- An Answer belongs to exactly one Attempt.
- An Answer is immutable after the Attempt is submitted.
- An Answer's type matches the QuestionInstance's input contract.

#### Examples
1. A multiple-choice Answer: choice "B" (O(1)).
2. A code Answer: `def two_sum(nums, target): ...` with execution result "all tests passed."
3. A free-response Answer: "The list is mutated in place because lists are mutable."

#### Non-Examples
- An **Attempt** — the Attempt is the full event (Answer + scoring + metadata); the Answer is the input portion.
- A **CorrectAnswer** — see that term; the correct answer is the Template's expected response; the Answer is the Learner's response.
- A "submission" in a quiz — that is informal; the project uses Answer.

#### Future Extensions
- Multi-modal Answers (code + explanation in one Answer).
- Answer revision analytics (how many revisions predict mastery?).
- Answer hint correlation (which hints lead to which Answer patterns?).

---

### Correct Answer

#### Name
**Correct Answer**

#### Definition
A **Correct Answer** is the expected response to a **QuestionInstance**, produced by the **QuestionTemplate**'s correct-answer generator. It is part of the Template, not part of the **Attempt**. The Assessment Domain Service compares the Learner's **Answer** to the Correct Answer (or, for code questions, runs the Learner's code against test cases derived from the Correct Answer) to score the Attempt.

The Correct Answer is deterministic given the Template version and the parameter seed. It is never shown to the Learner before the Attempt is submitted.

#### Business Purpose
The Correct Answer exists to make scoring deterministic and replayable. Without it, the Engine could not score consistently across Attempts on the same Template; with it, every Attempt is scored against the same standard.

#### Lifecycle
- **Generated** by the QuestionFactory at QuestionInstance instantiation.
- **Stored** as part of the QuestionInstance (never shown to the Learner pre-submission).
- **Used** by the Assessment Domain Service to score the Attempt.
- **Revealed** to the Learner only after the Attempt is submitted, alongside the **Explanation**.

#### Owner
Content (via the Template) with Assessment consuming

#### Relationships
- A property of a **QuestionInstance**.
- Produced by the **QuestionTemplate**'s correct-answer generator.
- Compared to the Learner's **Answer** by the Assessment Domain Service.

#### Invariants
- The Correct Answer is deterministic given the Template version and seed.
- The Correct Answer is never exposed to the Learner before Attempt submission.
- The Correct Answer is consistent with the Template's **Explanation** (the Explanation must justify the Correct Answer).

#### Examples
1. For a dict-lookup question with a 1M-entry dict: Correct Answer is "O(1)."
2. For a list-mutability question on `lst.append(x)`: Correct Answer is "mutates in place."
3. For a code question on `two_sum`: Correct Answer is the test cases that the Learner's code must pass.

#### Non-Examples
- The Learner's **Answer** — that is the Learner's response; the Correct Answer is the expected response.
- An **Explanation** — the explanation justifies the Correct Answer; it is not the Correct Answer.
- A "solution" — that is informal; the project uses Correct Answer.

#### Future Extensions
- Multiple Correct Answers (for questions with multiple valid approaches).
- Partial Correct Answers (for questions with partial-credit rubrics).
- Correct Answer generation AI assistance (drafted, Instructor-validated).

---

### Distractor

#### Name
**Distractor**

#### Definition
A **Distractor** is an incorrect answer choice in a multiple-choice **QuestionInstance**. Each Distractor is generated by the **QuestionTemplate**'s distractor generator and is tagged with the **Misconception** it appeals to (or "none" for purely random distractors). When a Learner selects a Misconception-tagged Distractor, the **Mastery Engine** records the Misconception against the Learner, enabling targeted remediation.

Distractors are not "filler" — they are diagnostic instruments. A well-authored Distractor appeals to a specific, documented Misconception and thereby converts a wrong answer into a precise signal about the Learner's mental model.

#### Business Purpose
The Distractor exists to make wrong answers informative. Without tagged Distractors, the Engine learns only "the Learner was wrong"; with them, the Engine learns "the Learner holds Misconception X," which drives targeted remediation and accelerates mastery.

#### Lifecycle
- **Generated** by the QuestionFactory from the Template's distractor generator at QuestionInstance instantiation.
- **Tagged** with a Misconception (or "none") as part of the Template.
- **Selected** by the Learner (or not) during the Attempt.
- **Analyzed** post-publish by quality monitoring (Distractors that fail to discriminate are flagged).

#### Owner
Content (via the Template) with Assessment recording selection

#### Relationships
- Part of a **QuestionInstance**.
- Tagged with a **Misconception** (or "none").
- Selected by the Learner in an **Attempt** (when chosen).
- Analyzed by quality monitoring jobs.

#### Invariants
- Every Distractor in a multiple-choice QuestionInstance is incorrect.
- Every Distractor is tagged with a Misconception or "none."
- A Distractor that is correct (a bug) is rejected at QuestionFactory validation.

#### Examples
1. For a dict-lookup question: Distractor "O(n)" tagged with Misconception "scanning-keys."
2. For a list-mutability question: Distractor "creates a new list" tagged with Misconception "reassignment-creates-new."
3. For a GIL question: Distractor "speeds up linearly with cores" tagged with Misconception "gil-allows-parallelism."

#### Non-Examples
- The **CorrectAnswer** — that is the right choice; Distractors are wrong choices.
- A **Misconception** — the Misconception is the mental model; the Distractor is the answer choice that appeals to it.
- A random wrong answer — the project's Distractors are tagged, not random (except for the "none" tag).

#### Future Extensions
- Adaptive Distractor selection (choose Distractors most likely to elicit the Learner's suspected Misconceptions).
- Distractor effectiveness analytics (which Distractors discriminate best).
- Distractor pool sharing across Templates.

---

### Interview Question

#### Name
**Interview Question**

#### Definition
An **Interview Question** is a curated, real-world-style question that mirrors what a **Learner** is likely to encounter in a technical interview. Interview Questions are typically wrapped in one or more **QuestionTemplate**s for parameterization and reuse. They are tagged with metadata (company, role, difficulty, observed frequency) to give the Learner context.

An Interview Question is a content curation artifact, not a separate technical type. Technically, it is realized as a Template (or a set of Templates); the "Interview Question" label is a curation and presentation concern.

#### Business Purpose
The Interview Question exists to give the Learner authentic practice. The Engine's MasteryScore is built from any Attempt, but Learners also want to know "can I handle the actual questions I'll see?" Interview Questions provide that authenticity check.

#### Lifecycle
- **Curated** by an **Instructor** from real interview reports, public question banks, or company-public problem sets.
- **Wrapped** in one or more **QuestionTemplate**s.
- **Tagged** with metadata (company, role, observed frequency, difficulty).
- **Published** and **Versioned** as part of the **ContentVersion**.

#### Owner
Content

#### Relationships
- Realized as one or more **QuestionTemplate**s.
- Tagged with metadata (company, role, frequency).
- May be linked from a **LearningPath** as a "milestone practice" item.

#### Invariants
- An Interview Question must trace to at least one **Concept** and **LearningObjective**.
- An Interview Question's metadata must be truthful (no fabricated company attributions).
- An Interview Question's source must be documented (where the question came from).

#### Examples
1. "Implement a least-recently-used cache" — a classic interview question, wrapped in a Template, tagged "Google, Meta, medium frequency."
2. "Reverse a linked list" — wrapped in a Template, tagged "common across companies."
3. "Explain the GIL and how to work around it" — a free-response Template, tagged "senior Python roles."

#### Non-Examples
- A **QuestionTemplate** — the Template is the technical artifact; the Interview Question is the curation artifact (often realized as a Template).
- A **CodingExercise** — see that term; a CodingExercise is a code-execution question; an Interview Question may or may not involve coding.
- A "LeetCode problem" — that is a specific platform's content; the project's Interview Questions may be inspired by but are independently authored.

#### Future Extensions
- Company-specific question sets (a "Google prep" bundle).
- Interview Question freshness tracking (which questions are still being asked?).
- Learner-reported Interview Questions (community-submitted, Instructor-curated).

---

### Coding Exercise

#### Name
**Coding Exercise**

#### Definition
A **Coding Exercise** is a **QuestionTemplate** variant where the **Answer** is executable code, scored by running the Learner's code against test cases in a sandboxed environment. Coding Exercises are essential for Python interview prep (and for several other future Subjects). They are technically Templates with a code-execution input contract; the "Coding Exercise" label denotes the input type.

The sandbox runtime is part of the infrastructure, not the Template. The Template specifies the function signature, the test cases, and the scoring rubric; the sandbox executes the Learner's code and returns pass/fail plus error output.

#### Business Purpose
The Coding Exercise exists to assess the kind of skill that multiple-choice cannot — the ability to write correct, runnable code under constraints. For Python interview prep, this is the primary assessment type; for other Subjects (e.g., Cybersecurity), it may be less central.

#### Lifecycle
- **Authored** by an **Instructor** as a **QuestionTemplate** with a code-execution input contract.
- **Specified** with a function signature, test cases, and a scoring rubric.
- **Published** and **Versioned** as part of the **ContentVersion**.
- **Served** as a **QuestionInstance** with the sandbox as the execution environment.

#### Owner
Content (authored) with Assessment (executed via the sandbox)

#### Relationships
- A type of **QuestionTemplate**.
- **Answer** is executable code.
- Scored by the Assessment Domain Service via the sandbox.
- May be linked from an **InterviewQuestion** curation.

#### Invariants
- The sandbox executes the Learner's code with no network access and bounded resources.
- Test cases are deterministic and versioned with the Template.
- The scoring rubric is explicit (pass/fail, or partial credit per test case).

#### Examples
1. Implement `two_sum(nums, target)` — test cases include the canonical case, edge cases, and a performance case.
2. Implement an LRU cache class with `get` and `put` methods — test cases include sequential operations and capacity evictions.
3. Implement a function that detects a cycle in a linked list — test cases include no-cycle, single-node cycle, and large-list cycle.

#### Non-Examples
- A multiple-choice **QuestionTemplate** — that has a different input contract.
- A free-response **QuestionTemplate** — that has a text Answer, not executable code.
- A "challenge" or "kata" — those are external platform concepts; the project uses Coding Exercise.

#### Future Extensions
- Multi-file Coding Exercises (a project with multiple modules).
- Coding Exercises with hidden test cases (only revealed post-Attempt).
- Pair-programming Coding Exercises (future study-group feature).

---

### Practice Session

#### Name
**Practice Session**

#### Definition
A **Practice Session** is a **StudySession** whose intent is "practice" — drilling Concepts the Learner has already encountered, as opposed to "diagnostic" (establishing baseline) or "review" (spaced-repetition refresh). Practice Sessions are not a separate technical type; they are StudySessions with a specific intent parameter that influences the **Scheduler**'s queue generation.

The distinction matters for analytics: practice outcomes are weighted differently from diagnostic outcomes in the **MasteryScore** update, because practice reflects current mastery while diagnostic reflects baseline mastery.

#### Business Purpose
The Practice Session exists to give the Learner a clear intent for their study time and to give the Engine a clear signal about how to weight the resulting Attempts. Without intent, the Engine would treat all Attempts identically, conflating baseline measurement with consolidation practice.

#### Lifecycle
Inherited from **StudySession**, with the intent parameter set to "practice."

#### Owner
Learning

#### Relationships
- A type of **StudySession**.
- Uses an **AdaptiveQueue** generated with the "practice" intent.
- Produces **Attempt**s that are weighted as "practice" in the **MasteryScore** update.

#### Invariants
- A Practice Session's queue prioritizes Concepts the Learner has already encountered (not new Concepts).
- A Practice Session's Attempts are tagged with intent "practice" for analytics and mastery weighting.

#### Examples
1. A Learner who learned list mutability yesterday starts a Practice Session to consolidate; the queue serves 10 list-mutability questions.
2. A Learner drills their weak Concepts in a Practice Session; the queue prioritizes those.
3. A Learner mixes practice with review; the Engine interleaves due reviews and practice items.

#### Non-Examples
- A **StudySession** with intent "diagnostic" — that establishes baseline, not practice.
- A **StudySession** with intent "review" — that refreshes due Concepts, not newly-learned ones.
- A free-form "playing around" — that is not a session; the Engine requires intent.

#### Future Extensions
- Practice Session templates (saved configurations for repeat practice).
- Practice Session difficulty targeting (always slightly above current mastery, for stretch).
- Practice Session streak rewards (recognition for consistent practice).

---

### Attempt

#### Name
**Attempt**

#### Definition
An **Attempt** is the atomic unit of learning evidence. It records: which **QuestionInstance** was presented, when, the Learner's **Answer**, the time-to-answer, whether **Hint**s were used, the scoring outcome (correct, incorrect, partial), and the timestamp. The Attempt is **append-only** — once written, it is never modified. This immutability is the foundation of the project's data moat.

Every **MasteryScore** is a pure function of the Learner's Attempt history plus the **Mastery Engine** version. This makes mastery reproducible, auditable, and retrainable for future ML models.

#### Business Purpose
The Attempt exists to be the irreducible unit of learning evidence. Without it, the Engine could not measure mastery, could not schedule adaptively, and could not build the data moat. The Attempt's append-only property is what makes the moat durable — historical evidence cannot be retroactively edited.

#### Lifecycle
- **Created** when a Learner submits an **Answer** to a **QuestionInstance**.
- **Scored** by the Assessment Domain Service within the same transaction.
- **Published** as an `AttemptRecorded` domain event (via the outbox, in the same transaction).
- **Immutable** after write; corrections are made by appending a compensating Attempt, not by editing.

#### Owner
Assessment

#### Relationships
- Belongs to a **Learner** and a **StudySession**.
- References a **QuestionInstance** (and through it, a **QuestionTemplate** version and **ContentVersion**).
- Contains an **Answer** and a scoring outcome.
- Consumed by the **Mastery Engine** to update **MasteryScore**s.
- Consumed by **Analytics** for aggregation.

#### Invariants
- An Attempt is append-only; no field is ever modified after write.
- An Attempt references exactly one QuestionInstance, one Learner, and one StudySession.
- An Attempt's scoring is deterministic given the QuestionInstance, the Answer, and the Template version.
- Corrections to scoring bugs are made by appending a compensating Attempt, not by editing the original.

#### Examples
1. A Learner answers "O(1)" correctly in 8 seconds without hints; the Attempt records outcome "correct," time 8s, hints 0.
2. A Learner answers "O(n)" (Misconception-tagged Distractor) in 25 seconds with 1 hint; the Attempt records outcome "incorrect," Misconception "scanning-keys," time 25s, hints 1.
3. A Learner submits buggy code that fails 2 of 5 tests; the Attempt records outcome "partial," with the test results attached.

#### Non-Examples
- A **Review** — see that term; a Review is a specific type of Attempt whose purpose is spaced-repetition refresh, not first-time practice.
- A **StudySession** — a session is a sequence; an Attempt is one interaction.
- A "submission" in a quiz — that is informal; the project uses Attempt.

#### Future Extensions
- Attempt provenance (which queue, which seed, which A/B variant).
- Attempt-level ML features (for future model training).
- Attempt streaming for real-time analytics.

---

### Review

#### Name
**Review**

#### Definition
A **Review** is a specific type of **Attempt** whose purpose is spaced-repetition refresh of a **Concept** the Learner has previously encountered. Reviews are scheduled by the **Mastery Engine** based on the **ReviewInterval**; the **Scheduler** serves them when their due date arrives. A Review's outcome updates the MasteryScore and the next ReviewInterval (extending on success, contracting on failure).

"Review" is used in three senses in the project, distinguished by context: (1) a **Review Attempt** — an Attempt whose purpose is refresh; (2) a **Review record** — the scheduled future encounter with a Concept, produced by the Mastery Engine; (3) the **ReviewWorkflow** — the content authoring review process. This glossary entry covers senses (1) and (2); the ReviewWorkflow is a separate term.

#### Business Purpose
The Review exists to convert memory decay into actionable, scheduled work. Without it, the Engine would have no mechanism to refresh fading mastery; Learners would forget Concepts they once knew. Reviews are the Engine's retention mechanism.

#### Lifecycle
- **Scheduled** by the Mastery Engine when a Concept's ReviewInterval elapses (the Review record).
- **Served** by the Scheduler when the Review record's due date arrives (producing a Review Attempt).
- **Scored** like any Attempt.
- **Re-scheduled** by the Mastery Engine based on the outcome (extending or contracting the ReviewInterval).

#### Owner
Mastery (scheduling) with Assessment (execution)

#### Relationships
- A type of **Attempt** (when executed).
- Scheduled by the **Mastery Engine** as a Review record.
- Belongs to a **Concept** and a **Learner**.
- Has a **ReviewInterval** that updates based on outcome.

#### Invariants
- A Review Attempt is always for a Concept the Learner has previously encountered (not a first-time Concept).
- A Review's outcome updates the ReviewInterval (success extends, failure contracts).
- A Review record's due date is deterministic given the prior Attempt history and the Mastery Engine version.

#### Examples
1. A Learner mastered list mutability a week ago; the Mastery Engine schedules a Review for today; the Scheduler serves a list-mutability question; the Learner answers correctly; the ReviewInterval extends to 2 weeks.
2. A Learner's Review of dict-lookup is due; they answer incorrectly (Misconception); the ReviewInterval contracts to 1 day; the Mastery Engine flags the Concept as weak.
3. A Learner returns from a 2-week break; 8 Reviews are due; the Engine triages and serves the top 5 today, deferring the rest.

#### Non-Examples
- A first-time **Attempt** — that is not a Review; the Concept is new.
- A **PracticeSession** Attempt — that is consolidation, not spaced-repetition refresh.
- The **ReviewWorkflow** — that is content authoring review, a separate concept.

#### Future Extensions
- Review batching (one question that refreshes multiple Concepts).
- Review priority learning (which due Reviews are most urgent?).
- Review forecasting ("you will have 12 reviews due Friday").

---

### Revision

#### Name
**Revision**

#### Definition
A **Revision** is a content-edit event on a published artifact (**Concept**, **LearningObjective**, **Misconception**, **QuestionTemplate**, **Explanation**). A Revision produces a new version of the artifact, preserving the old version for historical **Attempt** interpretability. Revisions go through the **ReviewWorkflow** like new content.

A Revision is a content-lifecycle event, not a learning event. It is distinct from a **Review** (a spaced-repetition Attempt) and from a Learner's **Answer** revision (pre-submission editing within an Attempt).

#### Business Purpose
The Revision exists to let content evolve without invalidating historical data. Without versioned Revisions, editing a Template would make old Attempts uninterpretable (which Template produced this Question?); with them, every Attempt references a specific version that is preserved forever.

#### Lifecycle
- **Proposed** by an **Instructor** as an edit to a published artifact.
- **Reviewed** in the **ReviewWorkflow**.
- **Published** as a new version of the artifact.
- **Old version preserved**; never deleted.
- **Deprecated** versions are marked but retained.

#### Owner
Content

#### Relationships
- A lifecycle event on a content artifact (**Concept**, **Template**, etc.).
- Produces a new **ContentVersion** for the Subject.
- Preserves the old version for historical Attempt interpretability.

#### Invariants
- A Revision never mutates an existing version; it always produces a new one.
- A Revision's old version is preserved indefinitely while any Attempt references it.
- A Revision goes through the same ReviewWorkflow as new content.

#### Examples
1. An Instructor revises a dict-lookup Template to add a new Misconception-tagged Distractor; a new Template version is published; old Attempts still reference the old version.
2. An Instructor revises a Concept description for clarity; a new Concept version is published; historical Attempts are still interpretable against the old version.
3. An Instructor revises an Explanation variant to fix a typo; a new Template version is published.

#### Non-Examples
- A **Review** — that is a spaced-repetition Attempt, not a content edit.
- An **Answer** revision — that is pre-submission editing within an Attempt.
- A "patch" or "fix" — those are informal; the project uses Revision.

#### Future Extensions
- Revision impact analytics (which Revisions improved learning outcomes?).
- Revision rollback (publishing a previous version as a new version).
- Revision AI assistance (drafting edits for Instructor review).

---

### Memory Score

#### Name
**Memory Score**

#### Definition
A **Memory Score** is the **Mastery Engine**'s estimate of the probability that a **Learner** can correctly recall a **Concept** **right now**. It is highly sensitive to recent **Attempt**s and decays sharply with time. It is the input to short-term scheduling decisions: "should we drill this Concept again today?" The Memory Score is one component of the **MasteryScore**; it is not the same as MasteryScore.

A Learner who answered correctly an hour ago has a high Memory Score; the same Learner, three weeks later without review, has a low Memory Score even if their underlying mastery is intact. The Memory Score is what makes the Engine's spaced-repetition scheduling work.

#### Business Purpose
The Memory Score exists to give the **Scheduler** a short-term recall signal distinct from long-term mastery. Without it, the Engine would treat "just learned" and "learned long ago" identically, missing the urgent need to refresh decaying memories.

#### Lifecycle
- **Initialized** at the Learner's first Attempt on the Concept.
- **Updated** by the Mastery Engine after every Attempt on the Concept.
- **Decayed** over time by the Mastery Engine's decay function.
- **Refreshed** by successful Review Attempts.

#### Owner
Mastery

#### Relationships
- A component of a **MasteryScore** for a **Concept** and **Learner**.
- Decays over time per the Mastery Engine's decay function.
- Refreshed by **Attempt**s and **Review**s.

#### Invariants
- The Memory Score is bounded (0–1 or 0–100, configurable).
- The Memory Score decays monotonically between Attempts (a successful Attempt raises it; time lowers it).
- The Memory Score is reconstructible from the Attempt history plus the Mastery Engine version.

#### Examples
1. A Learner answers a dict-lookup question correctly at 10am; Memory Score at 11am is 0.95.
2. The same Learner does not study for 3 weeks; Memory Score decays to 0.40.
3. The Learner completes a Review; Memory Score refreshes to 0.92; the ReviewInterval extends.

#### Non-Examples
- **MasteryScore** — see that term; MasteryScore is the long-term estimate; Memory Score is the short-term estimate.
- A "skill level" — that is mastery, not memory.
- Time-to-answer — that is a signal that informs Memory Score but is not Memory Score itself.

#### Future Extensions
- Per-Learner decay rate (some Learners forget faster than others).
- Per-Concept decay rate (some Concepts are more forgettable).
- Memory Score forecasting ("this Concept will be at 0.3 by Friday without review").

---

### Mastery Score

#### Name
**Mastery Score**

#### Definition
A **Mastery Score** is the **Mastery Engine**'s consolidated estimate of a **Learner**'s durable understanding of a **Concept**. It combines the **MemoryScore** (short-term recall) with longer-term evidence (sustained correct performance across spaced reviews) into a slower-moving, more stable estimate. It is the input to long-term decisions: graduation from a **LearningPath**, eligibility for advanced topics, the "interview-ready" badge.

The Mastery Score is composed of two sub-scores (Memory and durable-mastery), a confidence interval, an evidence count, and a last-updated timestamp. It is updated only by the **Mastery Engine**; no other subsystem may write it.

#### Business Purpose
The Mastery Score exists to be the Engine's authoritative answer to "how well does this Learner know this Concept?" Without it, the Engine would have only the noisy Memory Score, which fluctuates daily; with it, the Engine has a stable signal for long-term decisions.

#### Lifecycle
- **Initialized** at the Learner's first Attempt on the Concept.
- **Updated** by the Mastery Engine after every Attempt on the Concept.
- **Slow-moving**; a single Attempt does not collapse or inflate it.
- **Reconstructible** from the Attempt history plus the Mastery Engine version.

#### Owner
Mastery

#### Relationships
- Belongs to a **Learner** and a **Concept**.
- Composed of a **MemoryScore** and a durable-mastery sub-score.
- Drives the **Scheduler**'s queue ranking.
- Drives **LearningPath** graduation decisions.
- Drives **InterviewReadiness** computation.

#### Invariants
- The Mastery Score is bounded (0–1 or 0–100).
- The Mastery Score is a pure function of the Attempt history and the Mastery Engine version (M1 invariant from Task 001).
- Only the Mastery Engine writes Mastery Scores (M3 invariant).
- The Mastery Score records the Mastery Engine version that produced it (M2 invariant).

#### Examples
1. A Learner has answered 12 dict-lookup questions correctly across 3 spaced reviews over 2 months; Mastery Score is 0.88, Memory Score is 0.91.
2. A Learner answered correctly once yesterday; Mastery Score is 0.45 (insufficient evidence for durable mastery), Memory Score is 0.90.
3. A Learner has not studied a Concept for 6 months; Mastery Score is 0.60 (decayed but stable), Memory Score is 0.20 (decayed sharply).

#### Non-Examples
- **MemoryScore** — Memory Score is short-term; Mastery Score is long-term.
- A "grade" — that is a course concept; the project uses Mastery Score.
- A **SuccessRate** — that is an aggregate metric; Mastery Score is a per-Concept estimate.

#### Future Extensions
- Mastery Score confidence intervals surfaced to the Learner ("we're 90% sure your mastery is between 0.75 and 0.85").
- Mastery Score decomposition (showing the Memory and durable components).
- Mastery Score ML model (a future v2 of the Mastery Engine, gated by the promotion protocol).

---

### Retention

#### Name
**Retention**

#### Definition
**Retention** is the Engine's measure of how well a **Learner** maintains **MasteryScore** over time without active practice. It is the primary success metric of the platform: not "how much did the Learner study?" but "how much does the Learner still know weeks later?" Retention is computed from **MasteryScore** trajectories and **Review** outcomes across a time window.

Retention is reported at multiple levels: per-Concept (does this Learner retain this Concept?), per-Learner (does this Learner retain their portfolio?), per-Subject (does this Subject's curriculum produce durable mastery?), and per-platform (does the Engine's methodology work?).

#### Business Purpose
Retention exists to keep the Engine honest. A platform that drives high engagement but low retention is a failing platform — Learners feel they are learning but forget everything. Retention is the metric that catches this failure mode early.

#### Lifecycle
- **Computed** continuously by Analytics jobs from MasteryScore trajectories.
- **Aggregated** at multiple levels (Concept, Learner, Subject, platform).
- **Reported** on dashboards (Learner, Instructor, Administrator).
- **Tracked** over time as the primary success metric.

#### Owner
Analytics

#### Relationships
- Computed from **MasteryScore** trajectories and **Review** outcomes.
- Aggregated across **Concept**s, **Learner**s, and **Subject**s.
- The primary input to product decisions about curriculum and scheduling.

#### Invariants
- Retention is computed from MasteryScore trajectories, not from engagement metrics.
- Retention is reported with a time window (e.g., "30-day retention" = mastery retained 30 days after last study).
- Retention is never optimized at the expense of MasteryScore validity.

#### Examples
1. A Learner's 30-day retention on `python.list.mutability` is 0.85 (they retain 85% of mastery 30 days after last study).
2. The Python Subject's 90-day retention across all Learners is 0.72 — a target the team monitors.
3. A specific Concept shows 30-day retention of 0.40 across all Learners; it is flagged for curriculum review (the Concept is not sticking).

#### Non-Examples
- **MasteryScore** — mastery is the point-in-time estimate; retention is the over-time measure.
- **SuccessRate** — that is per-Attempt; retention is over-time.
- Engagement (time-on-platform) — that is the opposite of retention; the Engine tracks both but optimizes for retention.

#### Future Extensions
- Retention prediction (forecasting future retention from early data).
- Retention-based curriculum optimization (which Concepts produce the best retention?).
- Retention benchmarks (comparing the Engine's retention to industry baselines).

---

### Knowledge Decay

#### Name
**Knowledge Decay**

#### Definition
**Knowledge Decay** is the **Mastery Engine**'s model of how **MemoryScore** declines over time without active practice. It is a function (not a formula in this document — the algorithm is owned by the Mastery Engine) that takes the time since the last Attempt and the prior MemoryScore and produces the current decayed MemoryScore. Decay is the input that drives **Review** scheduling.

Decay is not a single global constant — it is parameterized per **Concept** (some Concepts decay faster) and per **Learner** (some Learners forget faster). The parameters are initialized to defaults and refined over time from data.

#### Business Purpose
Knowledge Decay exists to make spaced repetition adaptive. Without a decay model, the Engine would schedule Reviews at fixed intervals; with one, the Engine schedules Reviews when they are actually needed, neither too early (wasting the Learner's time) nor too late (the memory has faded too far).

#### Lifecycle
- **Initialized** with default parameters per Concept and per Learner.
- **Refined** by Analytics jobs from observed Review outcomes.
- **Versioned** with the Mastery Engine.
- **Surfaced** for review if parameters diverge significantly from defaults.

#### Owner
Mastery

#### Relationships
- A function within the **Mastery Engine**.
- Drives **MemoryScore** decline over time.
- Drives **Review** scheduling via the **ReviewInterval**.

#### Invariants
- Decay is monotonic between Attempts (MemoryScore only declines, never rises, without an Attempt).
- Decay is bounded (MemoryScore never falls below 0).
- Decay parameters are versioned with the Mastery Engine.

#### Examples
1. A Concept with default decay parameters: MemoryScore 0.95 → 0.70 over 7 days without review.
2. A "forgettable" Concept (e.g., a syntax detail): MemoryScore 0.95 → 0.50 over 7 days.
3. A "sticky" Concept (e.g., a foundational idea): MemoryScore 0.95 → 0.85 over 7 days.

#### Non-Examples
- **ReviewInterval** — the interval is when to review; decay is why.
- **MemoryScore** — that is the point-in-time value; decay is the function that changes it.
- "Forgetting curve" — that is the academic term; the project uses Knowledge Decay.

#### Future Extensions
- Per-Learner decay personalization.
- Per-Concept decay learned from data.
- Decay model versioning and A/B testing.

---

### Weak Concept

#### Name
**Weak Concept**

#### Definition
A **Weak Concept** is a **Concept** whose **MasteryScore** for a given **Learner** has fallen below a configurable threshold, OR whose **MemoryScore** has fallen below a different threshold while the MasteryScore is below Proficient. Weakness is graded (mild, moderate, severe) to allow the **Scheduler** to prioritize. The Mastery Engine emits a weak-Concept signal as part of the `MasteryUpdated` event; the Scheduler uses it to bias the queue toward remediation.

Weak-Concept detection also uses **Misconception** clustering: if a Learner has selected the same Misconception-tagged **Distractor** more than once across different **QuestionTemplate**s, the Mastery Engine elevates the weakness severity for that Concept-Misconception pair.

#### Business Purpose
The Weak Concept exists to give the **Scheduler** a precise target for remediation. Without it, the Engine would drill broadly; with it, the Engine drills specifically, accelerating mastery recovery.

#### Lifecycle
- **Detected** by the Mastery Engine after each Attempt, when the MasteryScore or MemoryScore crosses a threshold.
- **Graded** (mild, moderate, severe) based on how far below threshold and how sustained the weakness is.
- **Surfaced** to the **Scheduler** for queue biasing.
- **Cleared** when the MasteryScore recovers above the threshold.

#### Owner
Mastery (detected) with Scheduling (acted upon)

#### Relationships
- A property of a **Concept** for a specific **Learner**.
- Drives **Scheduler** queue biasing.
- May trigger **LearningRecommendation**s.

#### Invariants
- A Weak Concept is per-Learner, per-Concept.
- Weakness is graded, not binary.
- Weakness clears only when the MasteryScore recovers, not on time passage alone.

#### Examples
1. A Learner's MasteryScore on `python.gil.bound_threads` is 0.35 (below 0.50 threshold); it is a moderate Weak Concept.
2. A Learner selects the same Misconception-tagged Distractor on 3 different Templates for `python.dict.lookup_complexity`; weakness is elevated to severe.
3. A Learner completes a remediation Practice Session; MasteryScore recovers to 0.65; the Concept is no longer Weak.

#### Non-Examples
- A **StrongConcept** — that is the opposite state.
- A failed **Attempt** — that is one event; a Weak Concept is a sustained state.
- A "hard Concept" — that is a property of the Concept (difficulty), not of the Learner-Concept pair.

#### Future Extensions
- Weak Concept forecasting (which Concepts are at risk of becoming weak?).
- Weak Concept remediation effectiveness analytics.
- Cohort-level Weak Concept analysis (which Concepts are weak across many Learners?).

---

### Strong Concept

#### Name
**Strong Concept**

#### Definition
A **Strong Concept** is a **Concept** whose **MasteryScore** for a given **Learner** is at the Proficient or Mastered level AND whose **MemoryScore** is also above threshold. Strength is the opposite of Weakness; it indicates the Concept does not need immediate attention from the **Scheduler**.

Strong Concepts are not surfaced to the Learner as actionable — there is nothing to do. They are surfaced on the Progress page as recognition and used by the Scheduler to skip redundant drilling.

#### Business Purpose
The Strong Concept exists to give the **Scheduler** permission to skip Concepts and to give the Learner recognition. Without it, the Engine might over-drill Concepts the Learner already knows, wasting time; with it, the Engine focuses on Weak and developing Concepts.

#### Lifecycle
- **Detected** by the Mastery Engine when MasteryScore and MemoryScore are both above threshold.
- **Maintained** as long as scores remain above threshold.
- **Cleared** if either score falls below threshold (becoming a Weak Concept or developing Concept).

#### Owner
Mastery (detected) with Scheduling (acted upon)

#### Relationships
- A property of a **Concept** for a specific **Learner**.
- Drives **Scheduler** queue skipping.
- Surfaced on the Progress page.

#### Invariants
- A Strong Concept requires both MasteryScore and MemoryScore above threshold.
- A Strong Concept is per-Learner, per-Concept.
- A Strong Concept can become Weak; the transition is driven by score changes.

#### Examples
1. A Learner's MasteryScore on `python.list.mutability` is 0.92, MemoryScore 0.95; it is Strong.
2. A Learner's MasteryScore on `python.dict.basics` is 0.88 (Proficient), MemoryScore 0.90; it is Strong.
3. A Learner's Strong Concept `python.list.mutability` drops to MemoryScore 0.40 after a 3-week break; it is no longer Strong (it may be Weak or developing).

#### Non-Examples
- A **WeakConcept** — that is the opposite state.
- A "mastered Concept" — that is a **ConceptState** (Mastered); Strong is a broader category including Proficient and Mastered.
- An "easy Concept" — that is a property of the Concept, not the Learner-Concept pair.

#### Future Extensions
- Strong Concept longevity analytics (which Concepts stay Strong longest?).
- Strong Concept clustering (a Learner strong on a cluster of Concepts may be ready to advance).
- Strong Concept recognition (badges, milestones).

---

### Concept State

#### Name
**Concept State**

#### Definition
A **Concept State** is a finite-state classification of a **Learner**'s relationship with a **Concept**, derived from the **MasteryScore** and the evidence history. The states are: **Unseen, Novice, Developing, Proficient, Mastered, Decayed**. Transitions are driven by accumulated evidence, not by single Attempts. The state machine is per-Concept, per-Learner.

Concept State is the human-readable projection of the MasteryScore; it is what the Learner sees on their Progress page and what the **Scheduler** uses for high-level queue decisions.

#### Business Purpose
The Concept State exists to give Learners and the Engine a shared, stable vocabulary for mastery progression. The raw MasteryScore is too noisy for human consumption; the Concept State abstracts it into a recognizable progression.

#### Lifecycle
- **Unseen** at first encounter (no Attempts).
- **Novice** after the first Attempt (limited evidence, high uncertainty).
- **Developing** with sustained correct Attempts.
- **Proficient** with continued correct performance.
- **Mastered** after surviving multiple spaced Reviews.
- **Decayed** when a previously Proficient/Mastered Concept's MemoryScore has fallen and the Concept is due for Review.
- Transitions are reversible (Decayed → Proficient on successful Review; Proficient → Developing on sustained failure).

#### Owner
Mastery

#### Relationships
- A property of a **Concept** for a specific **Learner**.
- Derived from the **MasteryScore** and evidence history.
- Drives **Scheduler** queue decisions at a high level.
- Surfaced on the Progress page.

#### Invariants
- The state machine is finite and enumerated.
- Transitions are driven by accumulated evidence, not by single Attempts.
- A Concept's state is per-Learner (the same Concept may be Mastered for one Learner and Novice for another).

#### Examples
1. A Learner's first Attempt on `python.list.mutability` is correct; state transitions Unseen → Novice.
2. After 5 correct Attempts across 2 weeks, state transitions Novice → Developing.
3. After surviving 3 spaced Reviews over 2 months, state transitions Developing → Proficient → Mastered.

#### Non-Examples
- **MasteryScore** — that is the numeric estimate; Concept State is the categorical projection.
- **WeakConcept** / **StrongConcept** — those are threshold-based flags; Concept State is the full progression.
- A "grade level" — that is a course concept; the project uses Concept State.

#### Future Extensions
- Concept State visualization on the KnowledgeGraph.
- Concept State transition analytics (which transitions are most common? which are blocked?).
- Concept State as a prerequisite (a Learner cannot attempt Concept B until Concept A is at least Developing).

---

### Graduation

#### Name
**Graduation**

#### Definition
**Graduation** is the engine-recognized completion of a **LearningPath** by a **Learner**. It occurs when all the Path's graduation criteria (a specified set of **Concept**s that must reach the Mastered **ConceptState**) are met. Graduation is a state transition, not a single event — it is the moment the last criterion is satisfied, recorded as a domain event.

Graduation is distinct from **InterviewReadiness** (a broader estimate) and from a **Milestone** (an intermediate progress marker). Graduation is the path's terminal recognition; Interview Readiness is the Engine's assessment that the Learner is ready for the real thing.

#### Business Purpose
Graduation exists to give the Learner a clear, measurable completion target. Without it, the Learner would study indefinitely without a sense of "I'm done"; with it, the Learner has a finish line that the Engine can credibly assess.

#### Lifecycle
- **Defined** by the **LearningPath**'s graduation criteria (a set of Concepts that must reach Mastered).
- **Tracked** continuously as the Learner's ConceptStates update.
- **Triggered** when the last criterion is met.
- **Recorded** as a `Graduated` domain event.
- **Recognized** on the Progress page and via a **Badge**.

#### Owner
Learning

#### Relationships
- A property of a **Learner**'s progress on a **LearningPath**.
- Driven by **ConceptState** transitions to Mastered.
- Triggers **Badge** award and **LearningRecommendation** for next Path.
- Distinct from **InterviewReadiness**.

#### Invariants
- Graduation requires all graduation criteria to be met (no partial graduation).
- Graduation is per-Learner, per-LearningPath.
- Graduation is irreversible (a Learner who later forgets does not "un-graduate"; their MasteryScores simply decay, which may affect Interview Readiness).

#### Examples
1. A Learner's last required Concept for the Python Full Path reaches Mastered; Graduation is triggered; a Badge is awarded.
2. A Learner completes the Python Crash Course Path; Graduation triggers a recommendation for the Full Path.
3. A Learner's MasteryScores decay after Graduation; they remain Graduated but their Interview Readiness drops.

#### Non-Examples
- **InterviewReadiness** — that is a broader estimate; Graduation is path-specific.
- A **Milestone** — that is an intermediate marker; Graduation is terminal.
- A "certificate of completion" — that is an external artifact; the project uses Graduation.

#### Future Extensions
- Graduation refresh requirements (a Graduated Learner must maintain certain MasteryScores to keep the recognition).
- Graduation analytics (which Paths produce the best long-term retention?).
- Graduation sharing (a shareable credential, possibly via Open Badges).

---

### Interview Readiness

#### Name
**Interview Readiness**

#### Definition
**Interview Readiness** is the Engine's consolidated estimate that a **Learner** is prepared for a real Python technical interview. It is computed from the Learner's **MasteryScore** distribution across the **Subject**'s high-yield Concepts, their **Retention** trajectory, their performance on **InterviewQuestion**s, and their **ConceptState** distribution. It is a 0–1 score with a confidence interval, surfaced on the dashboard.

Interview Readiness is distinct from **Graduation** (path completion) and from any individual **MasteryScore**. It is the Engine's answer to "am I ready?" — the question every interview-prep Learner is actually asking.

#### Business Purpose
Interview Readiness exists to give the Learner a credible, composite answer to the question that brought them to the platform. Without it, the Learner would have to interpret dozens of MasteryScores and ConceptStates; with it, the Learner gets one number with a clear interpretation.

#### Lifecycle
- **Initialized** at the Learner's first Attempt (typically low, with wide confidence interval).
- **Updated** continuously as MasteryScores and Retention update.
- **Refined** as the Learner attempts InterviewQuestions (their performance on real-world-style questions weighs heavily).
- **Surfaced** on the dashboard with the confidence interval and a breakdown.

#### Owner
Learning (with Analytics computing)

#### Relationships
- Computed from **MasteryScore** distribution, **Retention**, **InterviewQuestion** performance, and **ConceptState** distribution.
- Drives **LearningRecommendation**s ("you are 0.65 — focus on weak Concepts to reach 0.80").
- Distinct from **Graduation** (path-specific) — Interview Readiness is broader.

#### Invariants
- Interview Readiness is bounded (0–1).
- Interview Readiness includes a confidence interval (the Engine is honest about its uncertainty).
- Interview Readiness is per-Learner, per-Subject.

#### Examples
1. A Learner's Interview Readiness is 0.72 (±0.08); the dashboard shows "Ready for most mid-level interviews; focus on weak Concepts to reach senior readiness."
2. A Learner's Interview Readiness is 0.45 (±0.15); the dashboard shows "Not yet ready; prioritize the LearningPath."
3. A Learner's Interview Readiness rises to 0.88 after a month of focused study; the dashboard shows "Ready for senior interviews."

#### Non-Examples
- **Graduation** — that is path completion; Interview Readiness is broader.
- An average of **MasteryScore**s — that is too simplistic; Interview Readiness weights high-yield Concepts and Retention.
- A "test score" — that is a course concept; the project uses Interview Readiness.

#### Future Extensions
- Company-specific Interview Readiness (a "Google readiness" estimate based on Google-tagged InterviewQuestions).
- Interview Readiness forecasting ("at your current pace, you will reach 0.80 in 6 weeks").
- Interview Readiness validation (correlation with actual interview outcomes, via opt-in Learner reporting).

---

### Progress

#### Name
**Progress**

#### Definition
**Progress** is the umbrella term for the Learner's forward movement through the curriculum, measured by **ConceptState** transitions, **MasteryScore** improvements, **Milestone** achievements, and **LearningPath** advancement. It is not a single metric but a category of metrics, all shown on the Progress page.

"Progress" is also the name of the frontend page (`/progress`) that surfaces these metrics. Context disambiguates: "the Learner's Progress" (the metrics) vs. "the Progress page" (the UI).

#### Business Purpose
Progress exists to give the Learner a visible sense of forward movement, which is the primary retention driver. Without visible Progress, the Learner would feel they are treading water; with it, the Learner sees concrete evidence of improvement, even on days when individual Attempts feel difficult.

#### Lifecycle
- **Tracked** continuously as MasteryScores and ConceptStates update.
- **Aggregated** at multiple levels (per-Concept, per-Subject, per-LearningPath).
- **Surfaced** on the Progress page and in weekly digest notifications.

#### Owner
Analytics (with Learning surfacing)

#### Relationships
- Computed from **MasteryScore** trajectories, **ConceptState** transitions, **Milestone** achievements, and **LearningPath** advancement.
- Surfaced on the Progress page and in notifications.

#### Invariants
- Progress is computed from mastery metrics, not from engagement metrics.
- Progress is reported with a time window (e.g., "this week," "this month," "all time").
- Progress is per-Learner, per-Subject.

#### Examples
1. A Learner's weekly Progress: 3 Concepts advanced from Developing to Proficient, 12 correct Attempts, 1 Milestone achieved.
2. A Learner's all-time Progress: 45 of 80 Concepts at Proficient or above, 2 Milestones achieved, 60% through the LearningPath.
3. A Learner's Progress page shows a mastery-over-time chart, a ConceptState distribution, and recent Milestones.

#### Non-Examples
- **MasteryScore** — that is a per-Concept estimate; Progress is the aggregate trajectory.
- Engagement metrics (time-on-platform, Attempts-per-day) — those are inputs but not Progress itself.
- A "grade" or "level" — those are course concepts; the project uses Progress.

#### Future Extensions
- Progress forecasting ("at your current pace, you will graduate in 6 weeks").
- Progress comparison (anonymous cohort comparison: "you are in the top 20% of Learners who started in September").
- Progress sharing (with mentors or accountability partners).

---

### Milestone

#### Name
**Milestone**

#### Definition
A **Milestone** is an engine-recognized intermediate progress marker on the way to **Graduation**. Examples: "first Concept Mastered," "10 Concepts at Proficient," "completed the first spaced-Review cycle," "Interview Readiness crossed 0.50." Milestones are defined by the platform (not the Learner) and are awarded automatically when criteria are met.

Milestones are distinct from **Badge**s (which are visual recognitions, often but not always tied to Milestones) and from **Achievement**s (which are a broader category including Milestones, Badges, and other recognitions).

#### Business Purpose
The Milestone exists to give the Learner intermediate recognition on a long journey. Without Milestones, the Learner would study for weeks without recognition; with them, the Learner gets frequent small wins that sustain motivation.

#### Lifecycle
- **Defined** by the platform per **Subject** (a catalog of Milestones).
- **Awarded** automatically when criteria are met.
- **Recorded** as a `MilestoneAchieved` domain event.
- **Surfaced** on the Progress page and in notifications.

#### Owner
Learning (with Analytics detecting)

#### Relationships
- A type of **Achievement**.
- May trigger a **Badge** award.
- Distinct from **Graduation** (terminal) — Milestones are intermediate.

#### Invariants
- Milestones are platform-defined, not Learner-defined.
- Milestones are awarded automatically when criteria are met (no manual award).
- Milestones are irreversible (once achieved, always achieved).

#### Examples
1. "First Concept Mastered" — awarded when the Learner's first Concept reaches Mastered.
2. "10 Concepts at Proficient" — awarded when 10 Concepts reach Proficient or above.
3. "Interview Readiness 0.50" — awarded when the Learner's Interview Readiness first crosses 0.50.

#### Non-Examples
- A **Badge** — that is the visual recognition; the Milestone is the underlying achievement.
- **Graduation** — that is terminal; Milestones are intermediate.
- A **LearningGoal** — that is Learner-declared; Milestones are engine-recognized.

#### Future Extensions
- Custom Milestones (Learner-defined, in addition to platform-defined).
- Milestone analytics (which Milestones drive the best retention?).
- Milestone sharing (social recognition).

---

### Badge

#### Name
**Badge**

#### Definition
A **Badge** is a visual recognition awarded to a **Learner** for achieving a **Milestone**, completing a **LearningPath** (Graduation), or other notable events. Badges are the visible artifact of an underlying **Achievement**; they appear on the Learner's profile and may be shareable.

Badges are decorative — they do not affect scheduling, mastery, or entitlement. The Engine's gamification is intentionally light; Badges provide recognition without incentivizing the wrong behaviors (e.g., drilling easy Concepts to farm Badges).

#### Business Purpose
The Badge exists to give the Learner visible recognition without distorting the learning loop. Without Badges, the Learner's only recognition would be MasteryScore numbers; with them, the Learner has shareable, celebratory artifacts.

#### Lifecycle
- **Defined** by the platform (a catalog of Badges).
- **Awarded** automatically when the linked Achievement's criteria are met.
- **Displayed** on the Learner's profile.
- **Shareable** via a public URL (optional, Learner-controlled).

#### Owner
Learning

#### Relationships
- A visual recognition of an **Achievement** (typically a **Milestone** or **Graduation**).
- Displayed on the Learner's profile.
- Does not affect **Scheduler**, **MasteryScore**, or entitlements.

#### Invariants
- Badges are decorative; they do not affect scheduling or mastery.
- Badges are awarded only for documented Achievements (no manual award).
- Badges are irreversible (once awarded, always awarded).

#### Examples
1. "First Concept Mastered" Badge — awarded when the first Concept reaches Mastered.
2. "Python Full Path Graduate" Badge — awarded on Graduation from the Python Full Path.
3. "30-Day Streak" Badge — awarded for 30 consecutive days of study.

#### Non-Examples
- A **Milestone** — the Milestone is the underlying achievement; the Badge is the visual recognition.
- An **Achievement** — that is the broader category; the Badge is one form of recognition.
- A "trophy" or "medal" — those are informal; the project uses Badge.

#### Future Extensions
- Open Badges standard compliance (portable credentials).
- Badge tiers (bronze, silver, gold for escalating criteria).
- Badge marketplace (Badges that unlock premium content).

---

### Achievement

#### Name
**Achievement**

#### Definition
An **Achievement** is the umbrella term for any engine-recognized Learner accomplishment: **Milestone**s, **Graduation**s, **Badge**s, streaks, and any future recognition category. It is the abstract type of which Milestones, Badges, and Graduations are concrete instances.

"Achievement" is used when the project needs to refer to "any recognition" without specifying the kind. Product and design typically use the specific names; engineering uses Achievement in interfaces and base classes.

#### Business Purpose
The Achievement exists to give engineering a single abstraction over the various recognition types, so that infrastructure (awarding, displaying, sharing) can be built once and reused.

#### Lifecycle
Inherited from the specific type (Milestone, Badge, Graduation).

#### Owner
Learning

#### Relationships
- Umbrella for **Milestone**, **Badge**, **Graduation**, and other recognition types.
- Awarded automatically when criteria are met.
- Surfaced on the Learner's profile.

#### Invariants
- Every Achievement is documented (criteria, recognition).
- Every Achievement is awarded automatically (no manual award).
- Every Achievement is irreversible.

#### Examples
1. A Milestone is an Achievement.
2. A Graduation is an Achievement.
3. A 30-day streak is an Achievement.

#### Non-Examples
- A **MasteryScore** — that is a measurement, not a recognition.
- A **LearningGoal** — that is Learner-declared, not engine-recognized.
- A "reward" in a gamification sense — the project's Achievements are recognitions, not incentives.

#### Future Extensions
- Achievement composition (an Achievement that requires other Achievements).
- Achievement analytics (which Achievements drive the best retention?).
- Achievement export (to a portfolio or credential wallet).

---

# Part II — Content Domain

The Content Domain owns the vocabulary of curriculum authoring, versioning, publishing, and quality. These terms govern how Instructors produce the artifacts that the Learning Domain consumes.

---

### Content Pack

#### Name
**Content Pack**

#### Definition
A **Content Pack** is a versioned bundle of related content artifacts (**Concept**s, **LearningObjective**s, **Misconception**s, **QuestionTemplate**s, **Explanation**s) authored together as a unit. A Content Pack is the unit of atomic publishing: either all its artifacts publish together or none do. Content Packs prevent the inconsistency that would arise from publishing individual artifacts that depend on each other.

Content Packs are distinct from **SubjectPack**s (which are larger, Subject-level bundles) and from **ContentVersion**s (which are Subject-wide snapshots). A Content Pack is a publishable unit within a Subject; a Content Version is the result of publishing one or more Content Packs.

#### Business Purpose
The Content Pack exists to make publishing safe. Without atomic bundles, an Instructor might publish a new Concept without its Templates, leaving the curriculum in an inconsistent state; with Content Packs, the Engine guarantees that a publish is internally consistent.

#### Lifecycle
- **Authored** by an **Instructor** as a bundle of related artifacts.
- **Reviewed** in the **ReviewWorkflow** as a unit.
- **Published** atomically (all artifacts or none).
- **Versioned** as a unit within the Subject's **ContentVersion** history.

#### Owner
Content

#### Relationships
- Contains **Concept**s, **LearningObjective**s, **Misconception**s, **QuestionTemplate**s, **Explanation**s.
- Published as a unit, producing a new **ContentVersion** for the **Subject**.
- Authored and reviewed by **Instructor**s.

#### Invariants
- A Content Pack's artifacts must be internally consistent (Concepts reference Objectives; Templates reference Objectives and Misconceptions).
- Publishing is atomic: all artifacts publish or none.
- A Content Pack cannot span Subjects.

#### Examples
1. A Content Pack for `python.asyncio.basics` includes the Concept, 3 Learning Objectives, 2 Misconceptions, 5 QuestionTemplates, and their Explanations.
2. A Content Pack for `sql.join.types` includes the Concept, 4 Objectives, 3 Misconceptions, and 8 Templates.
3. A Content Pack fails review because one Template is missing a Misconception tag; the entire Pack is held until fixed.

#### Non-Examples
- A **SubjectPack** — that is a Subject-level bundle; a Content Pack is a smaller publishable unit within a Subject.
- A **ContentVersion** — that is the Subject-wide snapshot; a Content Pack is one input to a Content Version.
- A "module" (forbidden) — the project does not use modules.

#### Future Extensions
- Content Pack dependencies (a Pack that requires another Pack to be published first).
- Content Pack analytics (which Packs produce the best learning outcomes?).
- Content Pack templates (starter structures for common Pack shapes).

---

### Subject Pack

#### Name
**Subject Pack**

#### Definition
A **Subject Pack** is the complete content bundle for a **Subject** at a given **ContentVersion**. It is the union of all published **ContentPack**s and represents the entire curriculum state of the Subject at a moment in time. A Subject Pack is what a new **Learner** enrolls against; it is what an existing Learner's **Attempt**s reference.

The Subject Pack is the largest content bundle in the project. It is the unit of Subject-wide versioning and the unit of Subject-wide rollback (a deprecated Subject Pack prevents new serves but preserves historical interpretability).

#### Business Purpose
The Subject Pack exists to give the Engine a stable, versioned curriculum state. Without it, individual artifact versions would float freely, making it impossible to reason about "what the curriculum was at time T"; with Subject Packs, the Engine has a clear answer.

#### Lifecycle
- **Assembled** automatically when one or more **ContentPack**s publish.
- **Versioned** as a **ContentVersion** for the Subject.
- **Deployed** to Learners incrementally (new enrollments get the new Pack; existing Learners may migrate or stay).
- **Deprecatable** as a whole when a Subject is retired.

#### Owner
Content

#### Relationships
- The complete content bundle for a **Subject** at a **ContentVersion**.
- Composed of all published **ContentPack**s.
- Referenced by **Attempt**s (via ContentVersion).
- Enrolled against by new **Learner**s.

#### Invariants
- A Subject Pack is immutable once published.
- A Subject Pack's artifacts are internally consistent (cycles in the **KnowledgeGraph** are rejected).
- A Subject Pack is the largest atomic unit; it cannot span Subjects.

#### Examples
1. Python Subject Pack v1.0 contains 80 Concepts, 200 Objectives, 150 Misconceptions, and 1000 Templates.
2. Python Subject Pack v1.1 adds 5 new Concepts and revises 12 Templates; existing Learners may migrate.
3. SQL Subject Pack v1.0 is the first release of the SQL Subject.

#### Non-Examples
- A **ContentPack** — that is a smaller publishable unit; a Subject Pack is the Subject-wide bundle.
- A **ContentVersion** — that is the version label; the Subject Pack is the content at that version.
- A "course" (forbidden) — the project does not use courses.

#### Future Extensions
- Subject Pack diffs (what changed between v1.0 and v1.1).
- Subject Pack migration tooling (helping Learners migrate to a new Pack).
- Subject Pack analytics (which Packs produce the best outcomes?).

---

### Version

#### Name
**Version**

#### Definition
A **Version** is the umbrella term for any versioned artifact in the project. The project versions at three levels: **ContentVersion** (Subject-wide), **TemplateVersion** (per-Template), and **AlgorithmVersion** (Mastery Engine). "Version" without qualification refers to the appropriate level based on context.

Versioning is the project's mechanism for evolving without invalidating history. Every **Attempt** references the Versions under which it was served, so the Attempt remains interpretable even after the underlying artifacts evolve.

#### Business Purpose
The Version exists to make the project's history reproducible. Without Versioning, edits would silently rewrite history; with it, every change produces a new Version, and old Versions are preserved.

#### Lifecycle
- **Created** when an artifact is first published.
- **Bumped** on every edit (producing a new Version).
- **Preserved** indefinitely while any **Attempt** references it.
- **Deprecatable** but never deletable.

#### Owner
Cross-cutting (each context owns its own Versioning)

#### Relationships
- Umbrella for **ContentVersion**, **TemplateVersion**, **AlgorithmVersion**.
- Referenced by **Attempt**s.

#### Invariants
- Versions are immutable once published.
- Versions are monotonic (v2 always follows v1).
- Versions are preserved while referenced.

#### Examples
1. ContentVersion 3 for the Python Subject.
2. TemplateVersion 5 for the dict-lookup Template.
3. AlgorithmVersion 2 for the Mastery Engine.

#### Non-Examples
- A "draft" — that is pre-Version; a Version is published.
- A git commit hash — that is a source-control artifact, not a content Version.
- A "release" — that is a deployment concept; the project uses Version.

#### Future Extensions
- Version provenance (which edit produced which Version).
- Version rollback (publishing a previous Version as a new Version).
- Version diffs (what changed between two Versions).

---

### Content Version

#### Name
**Content Version**

#### Definition
A **Content Version** is an immutable snapshot of a **Subject**'s entire content graph (**Concept**s, **ConceptDependency**s, **LearningObjective**s, **Misconception**s, **QuestionTemplate**s, **Explanation**s) at a moment in time. It is bumped atomically on every publish of one or more **ContentPack**s. Every **Attempt** references the Content Version under which it was served.

The Content Version is the project's mechanism for letting curriculum evolve without invalidating historical Attempt interpretability. An Attempt served under Content Version 3 remains interpretable even after Content Version 4 ships.

#### Business Purpose
The Content Version exists to make the curriculum's evolution safe. Without it, editing a Concept would make old Attempts uninterpretable (which Concept version produced this Attempt?); with it, every Attempt references a specific, preserved snapshot.

#### Lifecycle
- **Created** atomically when one or more **ContentPack**s publish.
- **Immutable** once created.
- **Referenced** by every **Attempt** served under it.
- **Deprecatable** (prevents new serves) but never deletable.

#### Owner
Content

#### Relationships
- A snapshot of a **Subject**'s content graph.
- Composed of all published **ContentPack**s at the moment of creation.
- Referenced by **Attempt**s.
- Contains **TemplateVersion**s for all its Templates.

#### Invariants
- A Content Version is immutable once created.
- A Content Version is internally consistent (acyclic **KnowledgeGraph**, all Objectives traced, all Misconceptions linked).
- A Content Version is preserved indefinitely while any **Attempt** references it.

#### Examples
1. Python Content Version 3 ships on 2026-09-01 with 5 new Concepts and 12 revised Templates.
2. An Attempt served on 2026-08-15 references Content Version 2; it remains interpretable after Version 3 ships.
3. Content Version 2 is deprecated on 2026-10-01; no new serves use it, but historical Attempts still reference it.

#### Non-Examples
- A **TemplateVersion** — that is per-Template; a Content Version is Subject-wide.
- An **AlgorithmVersion** — that is for the Mastery Engine, not the content.
- A "release" — that is a deployment concept; the project uses Content Version.

#### Future Extensions
- Content Version migration tooling (helping Learners migrate).
- Content Version analytics (which Versions produce the best outcomes?).
- Content Version rollback (publishing a previous Version as a new Version).

---

### Template Version

#### Name
**Template Version**

#### Definition
A **Template Version** is an immutable snapshot of a single **QuestionTemplate** at a moment in time. It is bumped on every edit to the Template. Every **QuestionInstance** references the Template Version under which it was instantiated, so the exact question can be replayed.

Template Versioning is the finest-grained versioning in the project. It is what makes individual **Attempt**s replayable: given the Template Version, the parameter seed, and the **ContentVersion**, the Engine can reconstruct the exact Question Instance.

#### Business Purpose
The Template Version exists to make individual questions replayable. Without it, editing a Template would make old Attempts uninterpretable (which Template produced this Question?); with it, every Attempt references a specific, preserved Template Version.

#### Lifecycle
- **Created** when a Template is first published.
- **Bumped** on every edit (producing a new Template Version).
- **Immutable** once created.
- **Referenced** by every **QuestionInstance** instantiated from it.

#### Owner
Content

#### Relationships
- A snapshot of a single **QuestionTemplate**.
- Contained within a **ContentVersion**.
- Referenced by **QuestionInstance**s and **Attempt**s.

#### Invariants
- A Template Version is immutable once created.
- A Template Version is preserved indefinitely while any **Attempt** references it.
- A Template Version is deterministic: the same Template Version + seed produces the same QuestionInstance.

#### Examples
1. The dict-lookup Template is at Version 5 after 4 edits.
2. An Attempt served on 2026-08-15 references dict-lookup Template Version 4; it remains replayable after Version 5 ships.
3. An edit to a Template's Distractor generator produces Template Version 6.

#### Non-Examples
- A **ContentVersion** — that is Subject-wide; a Template Version is per-Template.
- A **Revision** — that is the edit event; a Template Version is the resulting snapshot.
- A "draft" — that is pre-Version; a Template Version is published.

#### Future Extensions
- Template Version diffs (what changed between v4 and v5).
- Template Version A/B testing (serving different Versions to different cohorts).
- Template Version rollback (publishing a previous Version as a new Version).

---

### Algorithm Version

#### Name
**Algorithm Version**

#### Definition
An **Algorithm Version** is an immutable snapshot of the **Mastery Engine**'s algorithm at a moment in time. It is bumped on every change to the mastery computation (the scoring function, the decay model, the **ReviewInterval** logic). Every **MasteryScore** references the Algorithm Version under which it was computed.

Algorithm Versioning is what makes the Mastery Engine reproducible and auditable. Given a Learner's **Attempt** history and the Algorithm Version log, the Engine can reconstruct any historical MasteryScore exactly.

#### Business Purpose
The Algorithm Version exists to let the Mastery Engine evolve without invalidating history. Without it, an algorithm change would silently rewrite every Learner's MasteryScore; with it, old Scores remain interpretable, and new Scores are computed under the new Version going forward.

#### Lifecycle
- **Created** when a new Mastery Engine algorithm is promoted to production (after passing the evaluation protocol).
- **Immutable** once created.
- **Referenced** by every **MasteryScore** computed under it.
- **Superseded** by a new Algorithm Version; old Scores remain under the old Version until a recompute job runs.

#### Owner
Mastery

#### Relationships
- A snapshot of the **Mastery Engine** algorithm.
- Referenced by **MasteryScore**s.
- Promotion gated by the evaluation protocol (shadow mode, no regression, human sign-off).

#### Invariants
- An Algorithm Version is immutable once created.
- An Algorithm Version is preserved indefinitely while any **MasteryScore** references it.
- A change to the Mastery Engine algorithm requires a new Algorithm Version (no in-place edits).

#### Examples
1. Algorithm Version 1 is the deterministic algorithm shipped in Phase 1.
2. Algorithm Version 2 is a refined decay model, promoted after shadow evaluation shows no regression.
3. A recompute job backfills all Learners' MasteryScores from Version 1 to Version 2 over a week.

#### Non-Examples
- A **ContentVersion** — that is for content; an Algorithm Version is for the Mastery Engine.
- A **TemplateVersion** — that is for a single Template; an Algorithm Version is for the entire Mastery Engine.
- A "model" in an ML sense — an Algorithm Version may be deterministic or ML-based; the term covers both.

#### Future Extensions
- Algorithm Version A/B testing (different Versions for different cohorts).
- Algorithm Version rollback (reverting to a previous Version after a regression).
- Algorithm Version analytics (which Versions produce the best retention?).

---

### Published Content

#### Name
**Published Content**

#### Definition
**Published Content** is any content artifact (**Concept**, **LearningObjective**, **Misconception**, **QuestionTemplate**, **Explanation**) that has passed the **ReviewWorkflow** and is live — eligible to be served to **Learner**s. Published Content is immutable within its **Version**; edits produce a new Version rather than mutating the published one.

Published Content is the state, not the artifact. A Concept is "published" (state) when it has passed review and is live; the Concept itself is the artifact.

#### Business Purpose
The Published Content state exists to give the Engine a clear distinction between what is live and what is not. Without it, the Engine might serve draft content; with it, only reviewed, approved content reaches Learners.

#### Lifecycle
- **Transitioned to** when a **ContentPack** passes the **ReviewWorkflow** and publishes.
- **Immutable** within its Version.
- **Deprecatable** (transitioned to **ArchivedContent**) but not deletable while referenced.

#### Owner
Content

#### Relationships
- The live state of content artifacts.
- Produced by the **ReviewWorkflow**.
- Eligible to be served to **Learner**s.
- Versioned via **ContentVersion**s and **TemplateVersion**s.

#### Invariants
- Published Content has passed the **ReviewWorkflow**.
- Published Content is immutable within its Version.
- Published Content is eligible to be served; Draft Content is not.

#### Examples
1. The `python.list.mutability` Concept at Version 3 is Published Content.
2. A dict-lookup Template at Version 5 is Published Content; Version 4 is also Published but deprecated.
3. A new Concept is drafted but not yet reviewed; it is Draft Content, not Published.

#### Non-Examples
- **DraftContent** — that is the pre-review state.
- **ArchivedContent** — that is the deprecated state.
- A "live" course module (forbidden) — the project uses Published Content.

#### Future Extensions
- Published Content health metrics (discrimination, clarity, effectiveness).
- Published Content lifecycle automation (auto-deprecate low-quality content).
- Published Content A/B testing (different Versions for different cohorts).

---

### Draft Content

#### Name
**Draft Content**

#### Definition
**Draft Content** is any content artifact that is being authored or reviewed but has not yet passed the **ReviewWorkflow**. Draft Content is not eligible to be served to **Learner**s. It lives in a separate draft store, isolated from Published Content.

Draft Content may be edited freely; it is not Versioned until it publishes. Multiple Instructors may collaborate on a draft, with ownership and change tracking.

#### Business Purpose
The Draft Content state exists to give Instructors a safe space to author without affecting Learners. Without it, edits would be live immediately, risking inconsistent or wrong content reaching Learners; with it, content is reviewed before it ships.

#### Lifecycle
- **Created** by an **Instructor** starting a new artifact.
- **Edited** freely; no Versioning until publish.
- **Submitted** to the **ReviewWorkflow**.
- **Transitioned to** Published Content on approval, or back to Draft on rejection.

#### Owner
Content

#### Relationships
- The pre-review state of content artifacts.
- Edited by **Instructor**s.
- Submitted to the **ReviewWorkflow**.
- Not eligible to be served to **Learner**s.

#### Invariants
- Draft Content is not served to Learners.
- Draft Content is not Versioned (Versioning happens at publish).
- Draft Content may have multiple editors, with ownership tracked.

#### Examples
1. An Instructor drafts a new Concept `python.match.statement`; it is Draft Content until reviewed.
2. An Instructor revises a Template's Distractor generator; the revision is Draft Content until published.
3. A peer reviewer requests changes; the artifact returns to Draft Content for revision.

#### Non-Examples
- **PublishedContent** — that is the post-review state.
- **ArchivedContent** — that is the deprecated state.
- A "scratch" or "sandbox" — those are informal; the project uses Draft Content.

#### Future Extensions
- Draft Content collaboration (real-time multi-editor).
- Draft Content templates (starter structures).
- Draft Content AI assistance (drafting, wording refinement).

---

### Archived Content

#### Name
**Archived Content**

#### Definition
**Archived Content** is content that has been published and later deprecated. It is no longer eligible to be served to new **Learner**s, but it is preserved indefinitely because historical **Attempt**s reference it. Archived Content is immutable.

Archiving is the project's mechanism for retiring content without deleting it. Deletion would invalidate historical Attempt interpretability; archiving preserves it.

#### Business Purpose
The Archived Content state exists to let the curriculum evolve without losing history. Without it, the Engine would face a choice between keeping obsolete content live (confusing Learners) or deleting it (invalidating history); with archiving, the Engine retires content while preserving history.

#### Lifecycle
- **Transitioned to** from **PublishedContent** when an **Instructor** or **Administrator** deprecates it.
- **Immutable**; no further edits.
- **Preserved** indefinitely while any **Attempt** references it.
- **Not eligible** for new serves.

#### Owner
Content

#### Relationships
- The deprecated state of content artifacts.
- Referenced by historical **Attempt**s.
- Not eligible for new serves.
- May be restored to Published Content in a new Version (rare).

#### Invariants
- Archived Content is immutable.
- Archived Content is preserved while referenced.
- Archived Content is not eligible for new serves.

#### Examples
1. A Concept `python.print.statement` is archived because it is too basic for the current curriculum; historical Attempts still reference it.
2. A Template is archived after a better Template replaces it; the old Template's Attempts remain interpretable.
3. A Misconception is archived because data shows it never appears in Learner errors; it may be inaccurate.

#### Non-Examples
- **PublishedContent** — that is the live state.
- **DraftContent** — that is the pre-review state.
- "Deleted" content — the project does not delete; it archives.

#### Future Extensions
- Archived Content analytics (which archived content was most useful historically?).
- Archived Content restoration workflows.
- Archived Content migration tooling (helping Learners migrate away from archived content).

---

### Review Workflow

#### Name
**Review Workflow**

#### Definition
The **Review Workflow** is the multi-stage process that **DraftContent** passes through before becoming **PublishedContent**. The stages are: **Peer Review** (a second **Instructor** reviews for accuracy and atomicity), **Editorial Review** (a senior Instructor reviews for style and pedagogy), and **QA / Pilot** (a sample of generated questions is served to a pilot cohort to measure discrimination and clarity). A draft that fails any stage returns for revision.

The Review Workflow is the project's enforcement mechanism for the human-authored source-of-truth principle. AI may assist drafting but cannot publish; only Instructors who have passed the Review Workflow can publish.

#### Business Purpose
The Review Workflow exists to ensure content quality before it reaches Learners. Without it, content would ship with errors, unclear prompts, or low discrimination; with it, content is vetted by multiple Instructors and tested on a pilot cohort.

#### Lifecycle
- **Triggered** when an **Instructor** submits **DraftContent** for review.
- **Stages**: Peer Review → Editorial Review → QA / Pilot.
- **Outcomes**: Approve (advance to next stage), Request Changes (return to Draft), Reject (return to Draft with major issues).
- **Terminal**: Publish (all stages passed) or Withdrawn (Instructor withdraws).

#### Owner
Content

#### Relationships
- Governs the transition from **DraftContent** to **PublishedContent**.
- Involves multiple **Instructor**s (author, peer reviewer, editorial reviewer).
- May involve a pilot cohort of **Learner**s for QA.
- Records all decisions in the content artifact's history.

#### Invariants
- Every **ContentPack** must pass all stages before publishing.
- The author cannot be their own peer reviewer.
- All review decisions are recorded in the artifact's history.

#### Examples
1. An Instructor submits a new Concept; a peer reviewer requests clarification on the description; the author revises; the peer reviewer approves; editorial review approves; QA pilot shows good discrimination; the Concept publishes.
2. A Template's QA pilot shows low discrimination (the question does not separate mastered from non-mastered Learners); it returns to the author for revision.
3. An editorial reviewer rejects a Misconception as inaccurate; the author withdraws the draft.

#### Non-Examples
- A **Revision** — that is the edit event; the Review Workflow governs the publishing of Revisions.
- A "code review" — that is for source code; the Review Workflow is for content.
- A "pull request" — that is a source-control artifact; the Review Workflow is a content-lifecycle process.

#### Future Extensions
- Review Workflow automation (auto-routing to appropriate reviewers).
- Review Workflow analytics (which reviewers are most effective?).
- Review Workflow SLAs (time-to-review targets).

---

### Content Approval

#### Name
**Content Approval**

#### Definition
**Content Approval** is the decision event within the **ReviewWorkflow** where a reviewer (peer, editorial, or QA) approves a draft, advancing it to the next stage or to **PublishedContent**. Each Approval is recorded in the content artifact's history with the reviewer, the timestamp, and the decision.

Content Approval is the unit of accountability: every published artifact has a chain of named Approvers, and any quality issue can be traced back to who approved what.

#### Business Purpose
The Content Approval exists to make content quality accountable. Without it, content would ship without clear responsibility; with it, every published artifact has a documented chain of approval.

#### Lifecycle
- **Recorded** when a reviewer approves a draft in the **ReviewWorkflow**.
- **Immutable** once recorded.
- **Part of the artifact's history** forever.

#### Owner
Content

#### Relationships
- A decision event within the **ReviewWorkflow**.
- Recorded by an **Instructor** (the reviewer).
- Part of the content artifact's history.

#### Invariants
- An Approval is immutable once recorded.
- The approver cannot be the author (for peer review).
- An Approval records the reviewer, the timestamp, and the stage.

#### Examples
1. Peer reviewer Alice approves the Concept draft; the Approval is recorded; the draft advances to editorial review.
2. Editorial reviewer Bob approves the Template; the Approval is recorded; the draft advances to QA.
3. QA reviewer Carol approves the Template after pilot; the Approval is recorded; the draft publishes.

#### Non-Examples
- A **ReviewWorkflow** — that is the process; an Approval is one event within it.
- A "thumbs up" or "LGTM" — those are informal; the project uses Content Approval.
- An automated check — those are validations; an Approval is a human decision.

#### Future Extensions
- Approval delegation (a reviewer delegates to another).
- Approval analytics (which reviewers' approvals correlate with best outcomes?).
- Approval SLAs (time-to-approve targets).

---

### Content Validation

#### Name
**Content Validation**

#### Definition
**Content Validation** is the automated checking that **DraftContent** undergoes before it can enter the **ReviewWorkflow**, and that **PublishedContent** undergoes continuously. Validation checks include: **Concept** atomicity (does it have at least one **LearningObjective**?), **KnowledgeGraph** acyclicity, **QuestionTemplate** determinism (does the correct-answer generator produce the right answer for any valid parameters?), **Distractor** tagging (is every Distractor tagged with a **Misconception** or "none"?), and traceability (does every Template trace to at least one Objective?).

Validation is automated and objective; the **ReviewWorkflow** is human and subjective. Both are required for publishing.

#### Business Purpose
The Content Validation exists to catch objective errors before they reach human reviewers, freeing reviewers to focus on subjective quality. Without it, reviewers would waste time on missing tags and cyclic graphs; with it, they focus on pedagogy and clarity.

#### Lifecycle
- **Run** automatically when an **Instructor** submits **DraftContent** to the **ReviewWorkflow**.
- **Re-run** continuously on **PublishedContent** (e.g., when a new **ContentVersion** ships, validation confirms consistency).
- **Outcome**: Pass (advance to ReviewWorkflow) or Fail (return to Draft with errors).

#### Owner
Content

#### Relationships
- Pre-conditions for the **ReviewWorkflow**.
- Run on **DraftContent** (pre-review) and **PublishedContent** (post-publish).
- Enforces structural invariants (acyclicity, traceability, tagging).

#### Invariants
- Validation is automated; no human judgment.
- Validation must pass before the ReviewWorkflow can start.
- Validation rules are versioned with the **ContentVersion**.

#### Examples
1. A new Concept is submitted; validation checks that it has at least one LearningObjective; it passes; the ReviewWorkflow begins.
2. A Template is submitted; validation runs its correct-answer generator on 100 random parameter sets and confirms all produce the documented correct answer; it passes.
3. A new ConceptDependency is added; validation detects a cycle; the submission fails with a cycle error.

#### Non-Examples
- The **ReviewWorkflow** — that is human review; Validation is automated.
- **QualityMetrics** — those are post-publish measurements; Validation is pre-publish checks.
- A "lint" or "static analysis" — those are source-code concepts; the project uses Content Validation.

#### Future Extensions
- Validation rule extensibility (custom rules per Subject).
- Validation analytics (which rules catch the most errors?).
- Validation AI assistance (suggesting fixes for validation failures).

---

### Quality Metrics

#### Name
**Quality Metrics**

#### Definition
**Quality Metrics** are the post-publish measurements that assess the quality of **PublishedContent**. They include: **Discrimination** (does the content separate mastered from non-mastered Learners?), **Distractor Analysis** (do Misconception-tagged Distractors actually attract Learners who hold those Misconceptions?), **Explanation Effectiveness** (does viewing the Explanation improve the next Attempt on the same Concept?), and **Curriculum Coverage** (is every **LearningObjective** tested by at least N Templates?).

Quality Metrics are computed continuously by Analytics jobs. Content that falls below threshold is flagged for **Revision**.

#### Business Purpose
The Quality Metrics exist to give the team a feedback loop on content quality. Without them, the team would ship content and hope it works; with them, the team measures what works and revises what doesn't.

#### Lifecycle
- **Computed** continuously by Analytics jobs from **Attempt** data.
- **Aggregated** per **QuestionTemplate**, per **Concept**, per **Subject**.
- **Surfaced** on the Admin Portal for Instructor review.
- **Trigger** Revisions when metrics fall below threshold.

#### Owner
Analytics (computed) with Content (acted upon)

#### Relationships
- Computed from **Attempt** data.
- Per **QuestionTemplate**, **Concept**, **Subject**.
- Drive **Revision**s and **ArchivedContent** decisions.

#### Invariants
- Quality Metrics are computed from real Attempt data, not from author judgment.
- Quality Metrics are versioned with the **ContentVersion** (metrics for v3 are separate from v4).
- Quality Metrics below threshold trigger a flag, not an automatic archive.

#### Examples
1. A Template's discrimination is 0.15 (below 0.30 threshold); it is flagged for review.
2. A Distractor tagged with Misconception X is selected by only 2% of Learners who hold X; the Distractor is flagged as ineffective.
3. An Explanation's effectiveness (improvement on next Attempt) is 0.05 (low); the Explanation is flagged for revision.

#### Non-Examples
- **ContentValidation** — that is pre-publish; Quality Metrics are post-publish.
- A "review" — that is human; Quality Metrics are automated.
- A "rating" — that is subjective; Quality Metrics are computed.

#### Future Extensions
- Quality Metrics predictive models (forecasting quality before enough data accumulates).
- Quality Metrics alerts (real-time flagging of quality drops).
- Quality Metrics benchmarking (comparing quality across Subjects).

---

# Part III — Scheduling Domain

The Scheduling Domain owns the vocabulary of "what should the Learner do next?" — the **Scheduler**, the queues it produces, the intervals it works with, and the priorities it assigns.

---

### Scheduler

#### Name
**Scheduler**

#### Definition
The **Scheduler** is the subsystem that computes the **AdaptiveQueue** and the **DailyQueue** for a **Learner**. It takes as input the Learner's current **MasteryScore**s, due **Review**s, **WeakConcept**s, active **LearningGoal**s, and the available **QuestionTemplate** inventory, and produces an ordered list of **QuestionInstance** candidates ranked by expected educational value.

The Scheduler is **deterministic**: given the same inputs and the same explicit seed, it produces the same output. This determinism is invariant S1 (Section 5.3 of Task 001) and is non-negotiable.

#### Business Purpose
The Scheduler exists to answer the project's north-star question: "Given everything we know about this Learner right now, what should they study next?" It is the component that converts mastery state into actionable practice.

#### Lifecycle
- **Stateless** between requests; all state lives in the database.
- **Invoked** at StudySession start, after each Attempt, and at DailyQueue generation.
- **Output** is the AdaptiveQueue or DailyQueue, cached for the session or day.
- **Versioned** as an algorithm (separate from the Mastery Engine's AlgorithmVersion).

#### Owner
Scheduling

#### Relationships
- Consumes **MasteryScore**s, **Review** records, **WeakConcept** signals, **LearningGoal**s, **LearningPath**s.
- Produces **AdaptiveQueue**s and **DailyQueue**s.
- Calls the QuestionFactory to instantiate **QuestionInstance**s.
- Influenced by **Cooldown**s, **Priority**, **Urgency**, **Importance**.

#### Invariants
- Deterministic given inputs and seed (S1).
- Bounded output size (10–20 questions for AdaptiveQueue; 10–30 for DailyQueue).
- Respects **Prerequisite**-readiness (does not serve a Concept whose prerequisites are not minimally mastered).

#### Examples
1. At StudySession start, the Scheduler produces an AdaptiveQueue of 15 questions prioritizing 5 due Reviews and 10 Weak Concepts.
2. After an Attempt, the Scheduler regenerates the queue, dropping the consumed Concept and adding the next priority.
3. At midnight local time, the Scheduler produces a DailyQueue of 20 questions for the next day.

#### Non-Examples
- The **MasteryEngine** — that updates mastery; the Scheduler consumes mastery.
- The **QuestionFactory** — that instantiates questions; the Scheduler selects which to instantiate.
- A "recommender system" in the ML sense — the Scheduler is deterministic; ML is deferred to future versions.

#### Future Extensions
- Multi-objective scheduling (balance coverage, weakness, recency, difficulty).
- A/B testing infrastructure for Scheduler variants.
- Scheduler explainability (surface why each question was selected).

---

### Scheduling Engine

#### Name
**Scheduling Engine**

#### Definition
The **Scheduling Engine** is the umbrella term for the **Scheduler** plus its supporting infrastructure (the **QueueGeneration** logic, the **Cooldown** manager, the **Priority** calculator). It is the abstract subsystem; the Scheduler is the concrete component that produces queues.

"Scheduling Engine" and "Scheduler" are near-synonyms in casual usage; the project uses Scheduler for the concrete component and Scheduling Engine for the abstract subsystem. Engineers writing code use Scheduler; architects writing about the subsystem use Scheduling Engine.

#### Business Purpose
The Scheduling Engine exists as a concept to give the team a name for the broader subsystem that includes more than just queue production. It is useful in architectural discussion; in code, Scheduler is the term.

#### Lifecycle
Inherited from the **Scheduler**.

#### Owner
Scheduling

#### Relationships
- Umbrella for the **Scheduler** and its supporting components.
- Produces **QuestionQueue**s.

#### Invariants
- Inherited from the **Scheduler**.

#### Examples
1. "The Scheduling Engine includes the Scheduler, the Cooldown manager, and the Priority calculator."
2. An architect writes: "The Scheduling Engine will be extracted as a microservice in Phase 4 if latency demands."
3. "The Scheduler is the user-facing part of the Scheduling Engine."

#### Non-Examples
- The **MasteryEngine** — that is a separate subsystem.
- A "recommendation engine" — that is an ML concept; the Scheduling Engine is deterministic.

#### Future Extensions
- Scheduling Engine extraction as a microservice.
- Scheduling Engine plugin architecture (pluggable ranking strategies).

---

### Next Review

#### Name
**Next Review**

#### Definition
A **Next Review** is the scheduled future encounter with a **Concept**, produced by the **MasteryEngine** as a **Review** record. It has a due timestamp, a priority, and a reference to the Concept. The **Scheduler** consumes Next Reviews when building the **ReviewQueue** and the **AdaptiveQueue**.

"Next Review" is the forward-looking aspect of a Review record — when it will next be due. The Review record itself is the persistent artifact; the Next Review is its scheduling projection.

#### Business Purpose
The Next Review exists to make spaced repetition actionable. Without it, the Engine would have no concrete "when" for review; with it, the Engine has a precise due date that drives scheduling.

#### Lifecycle
- **Computed** by the MasteryEngine after every Attempt on a Concept.
- **Updated** on every Review Attempt (extending or contracting the interval).
- **Consumed** by the Scheduler when due.
- **Recomputed** continuously as MasteryScores and MemoryScores decay.

#### Owner
Mastery (produced) with Scheduling (consumed)

#### Relationships
- A property of a **Review** record.
- Produced by the **MasteryEngine**.
- Consumed by the **Scheduler** when due.

#### Invariants
- A Next Review's due date is deterministic given the Attempt history and the AlgorithmVersion.
- A Next Review is per-Learner, per-Concept.
- A Next Review's priority is graded (low, medium, high) based on decay severity and upcoming goals.

#### Examples
1. After a successful Review today, the Next Review is scheduled for 7 days later.
2. After a failed Review, the Next Review is scheduled for 1 day later (contracted interval).
3. A Learner returns from a 2-week break; 8 Next Reviews are overdue; the Scheduler triages by priority.

#### Non-Examples
- A **Review** Attempt — that is the execution; the Next Review is the schedule.
- A **ReviewInterval** — that is the duration; the Next Review is the timestamp.
- A calendar reminder — that is external; the project uses Next Review.

#### Future Extensions
- Next Review forecasting ("you will have 12 Next Reviews due Friday").
- Next Review priority learning (which overdue Reviews are most urgent?).
- Next Review batching (one question that satisfies multiple Next Reviews).

---

### Review Interval

#### Name
**Review Interval**

#### Definition
A **Review Interval** is the duration between the current **Attempt** on a **Concept** and the **NextReview**. It expands on successful Attempts (spaced repetition) and contracts on failed Attempts, with a floor that prevents collapse to zero. The interval is bounded by a minimum and maximum, and is modulated by the quality of the Attempt (fast correct extends more than slow correct).

The Review Interval is the mechanism by which the **MasteryEngine** converts memory decay into actionable scheduling. It is the input to the **NextReview** computation.

#### Business Purpose
The Review Interval exists to make spaced repetition adaptive. Without it, reviews would be at fixed intervals; with it, reviews are scheduled when actually needed, optimizing Learner time.

#### Lifecycle
- **Initialized** at the Learner's first Attempt on a Concept (typically 1 day).
- **Expanded** on successful Review Attempts (proportional to current interval, modulated by quality).
- **Contracted** on failed Review Attempts (with a floor).
- **Bounded** by a minimum (e.g., 1 day) and a maximum (e.g., 180 days).

#### Owner
Mastery

#### Relationships
- A property of a **Concept** for a specific **Learner**.
- Drives the **NextReview** computation.
- Updated by the **MasteryEngine** after every Attempt.

#### Invariants
- The Review Interval is bounded (minimum and maximum).
- The Review Interval never collapses to zero (floor prevents review storms).
- The Review Interval is deterministic given the Attempt history and the AlgorithmVersion.

#### Examples
1. A Learner answers correctly on day 1; interval expands to 3 days; Next Review is day 4.
2. A Learner answers correctly on day 4; interval expands to 9 days; Next Review is day 13.
3. A Learner answers incorrectly on day 13; interval contracts to 2 days; Next Review is day 15.

#### Non-Examples
- **NextReview** — that is the timestamp; the Review Interval is the duration.
- **Cooldown** — that is a per-Concept serve-frequency limit; the Review Interval is a review-scheduling duration.
- A "deadline" — that is a target; the Review Interval is a computed duration.

#### Future Extensions
- Per-Learner interval personalization (some Learners need shorter intervals).
- Per-Concept interval personalization (some Concepts are more forgettable).
- Interval A/B testing (different expansion factors for different cohorts).

---

### Spaced Repetition

#### Name
**Spaced Repetition**

#### Definition
**Spaced Repetition** is the pedagogical principle that **Review**s are most effective when scheduled at increasing intervals, timed to occur just before the **Learner** would otherwise forget. The **MasteryEngine** implements Spaced Repetition via the **ReviewInterval** and **NextReview** mechanisms.

Spaced Repetition is a principle, not a component. The project's implementation of it is the MasteryEngine's review-scheduling logic; the principle itself is the justification for that logic.

#### Business Purpose
Spaced Repetition exists as a documented principle to justify the Engine's review-scheduling design. Without it, the team might question why reviews are scheduled at expanding intervals; with it, the design has a clear pedagogical foundation.

#### Lifecycle
N/A (a principle, not an entity).

#### Owner
Mastery (the principle is implemented by the MasteryEngine)

#### Relationships
- Implemented by the **MasteryEngine** via **ReviewInterval** and **NextReview**.
- Consumes **MemoryScore** decay as input.
- Produces **Review** records as output.

#### Invariants
- The implementation of Spaced Repetition is deterministic (given the same Attempt history, the same Review schedule results).
- Spaced Repetition intervals expand on success and contract on failure.
- Spaced Repetition is never bypassed (the Engine does not allow "cram mode" that disables it).

#### Examples
1. A Learner masters a Concept; the MasteryEngine schedules Reviews at 1 day, 3 days, 9 days, 27 days — expanding intervals.
2. A Learner fails a Review; the interval contracts from 9 days to 2 days.
3. A Learner's Spaced Repetition schedule is visible on the Progress page as an upcoming review calendar.

#### Non-Examples
- **ReviewInterval** — that is the duration; Spaced Repetition is the principle.
- **NextReview** — that is the timestamp; Spaced Repetition is the principle.
- "Cramming" — that is the opposite of Spaced Repetition; the project does not support cram mode.

#### Future Extensions
- Spaced Repetition algorithm variants (SM-2, FSRS, custom) as future AlgorithmVersions.
- Spaced Repetition personalization (per-Learner, per-Concept).
- Spaced Repetition effectiveness analytics.

---

### Priority

#### Name
**Priority**

#### Definition
**Priority** is the **Scheduler**'s ranking signal for ordering **QuestionInstance** candidates in a queue. Priority is computed from multiple factors: **Urgency** (time-bound goals), **Importance** (curriculum criticality), **WeakConcept** severity, **Review** overdueness, and **Prerequisite**-readiness. Priority is a numeric score; the queue is ordered by descending priority.

Priority is per-candidate, per-queue-generation. It is recomputed on every queue regeneration; it is not persisted across sessions.

#### Business Purpose
The Priority exists to give the Scheduler a single ranking signal that balances multiple competing factors. Without it, the Scheduler would need to choose one factor (e.g., urgency) and ignore others; with it, the Scheduler balances all factors in a documented weighting.

#### Lifecycle
- **Computed** by the Scheduler for each candidate during queue generation.
- **Recomputed** on every queue regeneration.
- **Not persisted**; it is a runtime value.

#### Owner
Scheduling

#### Relationships
- Computed by the **Scheduler**.
- Combines **Urgency**, **Importance**, **WeakConcept** severity, **Review** overdueness, **Prerequisite**-readiness.
- Drives **QuestionQueue** ordering.

#### Invariants
- Priority is per-candidate, per-queue-generation.
- Priority is deterministic given inputs and seed.
- Priority weights are versioned with the Scheduler.

#### Examples
1. A due Review with high decay severity has Priority 0.85; a new Concept has Priority 0.40; the queue serves the Review first.
2. A Concept on a time-bound LearningGoal has elevated Urgency, raising its Priority.
3. A Weak Concept with severe weakness has elevated Priority for remediation.

#### Non-Examples
- **Urgency** — that is one factor of Priority; Priority is the composite.
- **Importance** — that is another factor; Priority is the composite.
- A "to-do list priority" — that is a generic concept; the project's Priority is scheduling-specific.

#### Future Extensions
- Priority weight learning (which weightings produce the best outcomes?).
- Priority explainability (surface which factors contributed to a candidate's Priority).
- Priority A/B testing.

---

### Recommendation

#### Name
**Recommendation**

#### Definition
A **Recommendation** is a structured suggestion produced by the **Scheduler** or background analytics jobs, advising a **Learner** on what to study, when to study, or what to study next outside the active practice loop. Recommendations are advisory — the Learner may accept, defer, or dismiss them.

"Recommendation" in the Scheduling Domain refers to the scheduling-specific suggestions (e.g., "review these 5 Concepts before your interview"). The broader category including non-scheduling suggestions is **LearningRecommendation** (defined in the Learning Domain).

#### Business Purpose
The Recommendation exists to extend the Engine's "what next?" capability beyond the active session. Without it, the Learner gets guidance only while practicing; with it, the Learner gets guidance on what and when to practice.

#### Lifecycle
- **Generated** by the Scheduler or background jobs.
- **Presented** on the dashboard or in notifications.
- **Accepted**, **Deferred**, or **Dismissed** by the Learner.
- **Archived** for analytics regardless of disposition.

#### Owner
Scheduling (produced) with Learning (presented)

#### Relationships
- A type of **LearningRecommendation**.
- Produced by the **Scheduler** or analytics jobs.
- May reference a set of **Concept**s, a **Review** schedule, or a **LearningPath** stage.

#### Invariants
- A Recommendation is non-binding; the Engine never auto-acts on it.
- A Recommendation is dismissible in one click.
- A dismissed Recommendation does not reappear in identical form for at least 7 days.

#### Examples
1. "Review these 5 due Concepts before September 15" — a scheduling Recommendation.
2. "Your Weak Concepts suggest revisiting list mutability" — a remediation Recommendation.
3. "You are ready to advance to the next LearningPath stage" — a progression Recommendation.

#### Non-Examples
- The **AdaptiveQueue** — that is imperative; a Recommendation is advisory.
- A **Milestone** notification — that recognizes past progress; a Recommendation suggests future action.
- A marketing nudge — that is billing, not scheduling.

#### Future Extensions
- Recommendation personalization based on Learner cohorts.
- Recommendation effectiveness analytics.
- Mentor-shared Recommendations.

---

### Recommendation Score

#### Name
**Recommendation Score**

#### Definition
A **Recommendation Score** is the numeric confidence the Engine assigns to a **Recommendation**, indicating how strongly it believes the Learner should act on it. The score is computed from the same factors as **Priority** but weighted differently (Recommendations weigh long-term outcomes more; Priority weighs immediate queue ordering). The score is surfaced to the Learner as "highly recommended" / "recommended" / "consider."

The Recommendation Score is distinct from **Priority** (which orders queue candidates) and from **MasteryScore** (which measures the Learner). It is the Engine's confidence in a suggestion.

#### Business Purpose
The Recommendation Score exists to give the Learner a sense of how strongly the Engine endorses a suggestion. Without it, all Recommendations would feel equally weighted; with it, the Learner can prioritize high-confidence suggestions.

#### Lifecycle
- **Computed** when a Recommendation is generated.
- **Surfaced** with the Recommendation as a tier (high / medium / low).
- **Not persisted** beyond the Recommendation's lifecycle.

#### Owner
Scheduling (with Analytics)

#### Relationships
- A property of a **Recommendation**.
- Computed from **MasteryScore**, **WeakConcept** severity, **LearningGoal** alignment, and historical outcome data.
- Surfaced as a tier to the Learner.

#### Invariants
- The Recommendation Score is bounded (0–1).
- The Recommendation Score is deterministic given inputs.
- The Recommendation Score is not the same as Priority (different weighting).

#### Examples
1. "Review these 5 due Concepts before September 15" — Recommendation Score 0.92 (highly recommended).
2. "Your Weak Concepts suggest revisiting list mutability" — Recommendation Score 0.71 (recommended).
3. "You are ready to advance to the next LearningPath stage" — Recommendation Score 0.58 (consider).

#### Non-Examples
- **Priority** — that orders queue candidates; Recommendation Score rates suggestions.
- **MasteryScore** — that measures the Learner; Recommendation Score rates a suggestion.
- A "confidence interval" — that measures uncertainty; Recommendation Score measures endorsement strength.

#### Future Extensions
- Recommendation Score calibration (do high-score Recommendations actually produce better outcomes?).
- Recommendation Score personalization (per-Learner calibration).
- Recommendation Score explainability (surface which factors contributed).

---

### Urgency

#### Name
**Urgency**

#### Definition
**Urgency** is a component of **Priority** that reflects time-bound **LearningGoal**s. A Concept due for a Learner with an interview in 2 weeks has higher Urgency than the same Concept for a Learner studying for fun. Urgency is computed from the LearningGoal's target date and the Concept's relevance to that goal.

Urgency is one factor of Priority; it is not Priority itself. The Scheduler combines Urgency with Importance, Weakness, and other factors.

#### Business Purpose
The Urgency exists to let the Scheduler respect Learner-declared time constraints without abandoning mastery-based scheduling. Without it, all Learners would get the same queue; with it, time-pressured Learners get a queue biased toward high-yield Concepts.

#### Lifecycle
- **Computed** by the Scheduler for each candidate during queue generation.
- **Updated** when the LearningGoal changes.
- **Zero** for Learners without a time-bound goal.

#### Owner
Scheduling

#### Relationships
- A component of **Priority**.
- Computed from the **LearningGoal**'s target date and the Concept's relevance.
- Zero for Learners without a time-bound goal.

#### Invariants
- Urgency is bounded (0–1).
- Urgency is zero for Learners without a time-bound goal.
- Urgency cannot override Prerequisite-readiness (a Concept cannot be served if prerequisites are unmet, regardless of Urgency).

#### Examples
1. A Learner with an interview in 2 weeks has high Urgency for high-yield Concepts.
2. A Learner with an interview in 6 months has moderate Urgency.
3. A Learner studying for fun has zero Urgency.

#### Non-Examples
- **Priority** — that is the composite; Urgency is one factor.
- **Importance** — that is curriculum criticality; Urgency is time-bound.
- A "deadline" — that is a target; Urgency is a scheduling signal.

#### Future Extensions
- Urgency personalization (some Learners perform better under pressure; others worse).
- Urgency decay (Urgency rises as the goal approaches).
- Urgency analytics (does Urgency-weighted scheduling improve goal attainment?).

---

### Importance

#### Name
**Importance**

#### Definition
**Importance** is a component of **Priority** that reflects a **Concept**'s curriculum criticality. A Concept that is a prerequisite for many others, or that is frequently tested in interviews, has higher Importance than a peripheral Concept. Importance is authored by **Instructor**s as part of the Concept and refined over time from data.

Importance is one factor of Priority; it is not Priority itself. The Scheduler combines Importance with Urgency, Weakness, and other factors.

#### Business Purpose
The Importance exists to let the Scheduler prioritize Concepts that matter most for the Learner's goal. Without it, all Concepts would be treated equally; with it, high-yield Concepts are served before peripheral ones.

#### Lifecycle
- **Authored** by an **Instructor** as part of the Concept (a coarse prior: low / medium / high).
- **Refined** by Analytics jobs from observed interview frequency and downstream dependency count.
- **Versioned** with the Concept.

#### Owner
Content (authored) with Scheduling (consumed)

#### Relationships
- A property of a **Concept**.
- A component of **Priority**.
- Refined from interview frequency and downstream dependency count.

#### Invariants
- Importance is bounded (low / medium / high, or 0–1 numeric).
- Importance is per-Concept, not per-Learner.
- Importance is versioned with the Concept.

#### Examples
1. `python.list.mutability` has high Importance (prerequisite for many Concepts, frequently tested).
2. `python.print.statement` has low Importance (rarely tested, few dependents).
3. `python.gil.bound_threads` has medium Importance (tested for senior roles, moderate dependents).

#### Non-Examples
- **Urgency** — that is time-bound; Importance is curriculum-intrinsic.
- **Priority** — that is the composite; Importance is one factor.
- **Difficulty** — that is how hard the Concept is; Importance is how critical.

#### Future Extensions
- Importance learned from data (which Concepts actually predict interview success?).
- Importance per-role (a Concept important for backend roles may not be for data roles).
- Importance drift detection over time.

---

### Difficulty Adjustment

#### Name
**Difficulty Adjustment**

#### Definition
**Difficulty Adjustment** is the **Scheduler**'s mechanism for modulating question **Difficulty** based on the **Learner**'s current state. A Learner on a winning streak may receive slightly harder questions (to stretch them); a Learner on a losing streak may receive slightly easier ones (to rebuild confidence and avoid frustration). Difficulty Adjustment is bounded — it never serves a question far above or below the Learner's current mastery.

Difficulty Adjustment is distinct from **QuestionDifficulty** (the authored prior) and from **MasteryScore** (the Learner's state). It is the adjustment applied to the prior based on the Learner's recent performance.

#### Business Purpose
The Difficulty Adjustment exists to keep the Learner in the zone of proximal development — challenged but not overwhelmed. Without it, the Scheduler would serve questions at fixed difficulty; with it, the Scheduler adapts to the Learner's recent performance.

#### Lifecycle
- **Computed** by the Scheduler during queue generation.
- **Based on** the Learner's recent Attempt outcomes (last N Attempts).
- **Bounded** — the adjustment is capped (e.g., ±20% of the authored Difficulty).

#### Owner
Scheduling

#### Relationships
- A mechanism within the **Scheduler**.
- Modulates **QuestionDifficulty** based on recent Attempt outcomes.
- Bounded to prevent extreme adjustments.

#### Invariants
- Difficulty Adjustment is bounded (capped at a configurable percentage).
- Difficulty Adjustment cannot override Prerequisite-readiness.
- Difficulty Adjustment is deterministic given inputs.

#### Examples
1. A Learner on a 5-correct streak receives questions at +15% Difficulty.
2. A Learner on a 3-incorrect streak receives questions at -15% Difficulty.
3. A Learner with mixed recent outcomes receives questions at the authored Difficulty (no adjustment).

#### Non-Examples
- **QuestionDifficulty** — that is the authored prior; Difficulty Adjustment is the modulation.
- **MasteryScore** — that is the Learner's state; Difficulty Adjustment is a scheduling mechanism.
- "Adaptive difficulty" in a game sense — the project's Difficulty Adjustment is bounded and pedagogically motivated.

#### Future Extensions
- Difficulty Adjustment personalization (some Learners thrive on stretch; others on consolidation).
- Difficulty Adjustment analytics (does adjustment improve outcomes?).
- Difficulty Adjustment A/B testing.

---

### Mastery Threshold

#### Name
**Mastery Threshold**

#### Definition
A **Mastery Threshold** is the **MasteryScore** level above which a **Concept** is considered sufficiently mastered for a given purpose. The project defines multiple thresholds: the **Proficient** threshold (ConceptState transition), the **Mastered** threshold (graduation criteria), and the **InterviewReadiness** threshold (composite). Thresholds are configurable per **Subject** and versioned with the **AlgorithmVersion**.

Mastery Thresholds are the boundaries that drive state transitions and decisions; the MasteryScore is the value that crosses them.

#### Business Purpose
The Mastery Threshold exists to give the Engine concrete, measurable criteria for state transitions and decisions. Without it, "mastered" would be a vague judgment; with it, "mastered" is a documented threshold that the Engine can assess objectively.

#### Lifecycle
- **Defined** per **Subject** by the curriculum lead.
- **Versioned** with the **AlgorithmVersion** (a threshold change requires a new AlgorithmVersion).
- **Surfaced** to the Learner as the target for each ConceptState.

#### Owner
Mastery (with Content defining per-Subject)

#### Relationships
- A configuration value per **Subject** and **AlgorithmVersion**.
- Drives **ConceptState** transitions.
- Drives **Graduation** criteria.
- Drives **InterviewReadiness** computation.

#### Invariants
- Mastery Thresholds are bounded (0–1).
- Mastery Thresholds are versioned with the AlgorithmVersion.
- Mastery Thresholds cannot be changed without a new AlgorithmVersion (no in-place edits).

#### Examples
1. The Proficient threshold for the Python Subject is 0.70; a Concept with MasteryScore 0.72 transitions to Proficient.
2. The Mastered threshold is 0.85; a Concept with MasteryScore 0.88 transitions to Mastered.
3. The InterviewReadiness threshold is 0.75; a Learner with composite 0.78 is "interview-ready."

#### Non-Examples
- **MasteryScore** — that is the value; the threshold is the boundary.
- **MemoryThreshold** — that is for MemoryScore; Mastery Threshold is for MasteryScore.
- A "passing grade" — that is a course concept; the project uses Mastery Threshold.

#### Future Extensions
- Per-Learner threshold personalization (some Learners need higher mastery for confidence).
- Per-Concept thresholds (some Concepts warrant higher mastery).
- Threshold analytics (which thresholds produce the best retention?).

---

### Memory Threshold

#### Name
**Memory Threshold**

#### Definition
A **Memory Threshold** is the **MemoryScore** level below which a **Concept** is considered to need immediate refresh. The project defines the threshold (e.g., 0.50) below which a Concept is flagged for priority review. The Memory Threshold is distinct from the **MasteryThreshold** (which is about durable mastery); the Memory Threshold is about short-term recall.

A Concept may have a high MasteryScore but a low MemoryScore (e.g., mastered long ago but not recently refreshed); the Memory Threshold catches this case and triggers a Review.

#### Business Purpose
The Memory Threshold exists to catch Concepts that are mastered but fading in short-term recall. Without it, the Engine would miss the urgent need to refresh; with it, the Engine schedules Reviews before the memory decays too far.

#### Lifecycle
- **Defined** per **Subject** by the curriculum lead.
- **Versioned** with the **AlgorithmVersion**.
- **Surfaced** to the Scheduler as a trigger for priority Reviews.

#### Owner
Mastery

#### Relationships
- A configuration value per **Subject** and **AlgorithmVersion**.
- Drives **WeakConcept** detection (when MemoryScore is below threshold and MasteryScore is below Proficient).
- Drives priority **Review** scheduling.

#### Invariants
- Memory Threshold is bounded (0–1).
- Memory Threshold is versioned with the AlgorithmVersion.
- Memory Threshold is lower than the Mastery Threshold for Proficient (a Concept can be Proficient in mastery but below memory threshold).

#### Examples
1. A Concept with MasteryScore 0.75 (Proficient) and MemoryScore 0.40 (below 0.50 threshold) is flagged for priority Review.
2. A Concept with MasteryScore 0.90 (Mastered) and MemoryScore 0.45 (below threshold) is flagged for Review but not Weak (mastery is intact).
3. A Concept with MasteryScore 0.45 (below Proficient) and MemoryScore 0.30 (below threshold) is Weak.

#### Non-Examples
- **MasteryThreshold** — that is for MasteryScore; Memory Threshold is for MemoryScore.
- **MasteryScore** / **MemoryScore** — those are the values; thresholds are the boundaries.
- A "decay threshold" — that is informal; the project uses Memory Threshold.

#### Future Extensions
- Per-Learner Memory Threshold personalization.
- Per-Concept Memory Threshold (some Concepts fade faster).
- Memory Threshold analytics.

---

### Cooldown

#### Name
**Cooldown**

#### Definition
A **Cooldown** is a per-Concept, per-**Learner** time window during which the **Scheduler** will not serve the same **Concept** again, regardless of priority. Cooldowns prevent the Engine from drilling the same Concept repeatedly in a session, which would be both frustrating and pedagogically suboptimal. Cooldowns are distinct from **ReviewInterval**s (which schedule future Reviews); Cooldowns are session-level serve-frequency limits.

Cooldowns are typically short (e.g., 30 minutes within a session, 4 hours across sessions) and are lifted automatically when they expire.

#### Business Purpose
The Cooldown exists to enforce variety in practice. Without it, the Scheduler might serve the same Weak Concept repeatedly; with it, the Learner gets a balanced session that covers multiple Concepts.

#### Lifecycle
- **Started** when a Concept is served in an Attempt.
- **Active** for the configured duration (e.g., 30 minutes).
- **Expired** automatically when the duration elapses.
- **Reset** if the Concept is served again (a new Cooldown starts).

#### Owner
Scheduling

#### Relationships
- A per-Concept, per-Learner runtime state in the **Scheduler**.
- Prevents re-serving a Concept within the Cooldown window.
- Distinct from **ReviewInterval** (which schedules future Reviews).

#### Invariants
- Cooldown is bounded (typically minutes to hours, not days).
- Cooldown does not override due **Review**s (a due Review can be served despite Cooldown, but with reduced priority).
- Cooldown is per-Concept, per-Learner, not global.

#### Examples
1. A Learner answers a list-mutability question; the Concept enters a 30-minute Cooldown; the Scheduler will not serve list-mutability again for 30 minutes.
2. A due Review for dict-lookup is served despite Cooldown (Reviews override Cooldowns with reduced priority).
3. A Learner ends a session; the Cooldowns expire; the next session can serve the same Concepts.

#### Non-Examples
- **ReviewInterval** — that schedules future Reviews; Cooldown prevents immediate re-serves.
- **Priority** — that orders candidates; Cooldown excludes candidates.
- A "rate limit" — that is for API abuse; Cooldown is for pedagogical variety.

#### Future Extensions
- Per-Learner Cooldown personalization (some Learners benefit from more repetition).
- Per-Concept Cooldown (some Concepts benefit from immediate re-drilling).
- Cooldown analytics (does Cooldown improve outcomes?).

---

### Queue Generation

#### Name
**Queue Generation**

#### Definition
**Queue Generation** is the act of the **Scheduler** producing a **QuestionQueue** (Adaptive or Daily). It is the process, not the output. Queue Generation takes the Learner's current state and the available inventory, computes **Priority** for each candidate, applies **Cooldown**s and **Prerequisite**-readiness filters, and produces the ordered queue.

Queue Generation is the most latency-sensitive operation in the Engine. The Loop's 200ms median target depends on Queue Generation completing quickly.

#### Business Purpose
The Queue Generation exists as a named process to give the team a unit of optimization. Without it, "the Scheduler produces a queue" would be a vague statement; with it, the team can measure, optimize, and A/B test the generation process.

#### Lifecycle
- **Triggered** at StudySession start, after each Attempt, and at DailyQueue generation.
- **Latency-sensitive** — must complete in under 100ms at the median for the Loop to meet its 200ms target.
- **Cached** — the output is cached for the session or day.

#### Owner
Scheduling

#### Relationships
- The process performed by the **Scheduler**.
- Produces **AdaptiveQueue**s and **DailyQueue**s.
- Consumes **MasteryScore**s, **Review** records, **WeakConcept** signals, **LearningGoal**s.
- Applies **Cooldown**s and **Prerequisite**-readiness filters.

#### Invariants
- Queue Generation is deterministic given inputs and seed.
- Queue Generation is bounded in output size.
- Queue Generation completes in under 100ms at the median (latency budget).

#### Examples
1. At StudySession start, Queue Generation produces a 15-question AdaptiveQueue in 80ms.
2. After an Attempt, Queue Generation regenerates the queue in 60ms (incremental update).
3. At midnight, Queue Generation produces a 20-question DailyQueue for the next day in 120ms (more candidates evaluated).

#### Non-Examples
- The **Scheduler** — that is the component; Queue Generation is the process.
- The **AdaptiveQueue** / **DailyQueue** — those are the outputs; Queue Generation is the process.
- A "query" — that is a database operation; Queue Generation is a domain process.

#### Future Extensions
- Incremental Queue Generation (regenerate only the consumed slot, not the whole queue).
- Queue Generation caching (cache partial results for common states).
- Queue Generation A/B testing (different generation strategies for different cohorts).

---

# Part IV — Analytics Domain

The Analytics Domain owns the vocabulary of measurement: how the Engine computes aggregates, surfaces trends, and turns raw **Attempt** data into actionable insight. Analytics is read-only against operational data; it never mutates learning state.

---

### Attempt History

#### Name
**Attempt History**

#### Definition
An **Attempt History** is the complete, ordered sequence of **Attempt**s for a **Learner** (optionally filtered by **Subject** or **Concept**). It is the raw evidence stream from which every **MasteryScore**, **Retention** curve, and **LearningVelocity** is computed. The Attempt History is append-only and immutable; it is the project's data moat.

#### Business Purpose
The Attempt History exists to be the source of truth for all learning measurement. Without it, the Engine could not recompute mastery, could not audit decisions, and could not train future ML models. Its immutability is what makes the moat durable.

#### Lifecycle
- **Appended** to on every Attempt.
- **Immutable**; no edits, no deletes (anonymization is the only modification, and only on account deletion).
- **Retained** indefinitely (in anonymized form after account deletion).

#### Owner
Analytics (read) with Assessment (write)

#### Relationships
- Composed of **Attempt**s.
- The source for **MasteryScore** reconstruction, **Retention** computation, **LearningVelocity**, and all other analytics.
- Filterable by **Subject**, **Concept**, time window.

#### Invariants
- Append-only; no edits.
- Immutable; no deletes (except anonymization on account deletion).
- Ordered by timestamp.

#### Examples
1. A Learner's Attempt History in Python: 450 Attempts across 80 Concepts over 6 months.
2. A Learner's Attempt History for `python.list.mutability`: 12 Attempts over 4 months.
3. An analytics job recomputes a Learner's MasteryScores from their Attempt History after an AlgorithmVersion change.

#### Non-Examples
- A **MasteryScore** — that is derived; Attempt History is the source.
- A "log" — that is a system concept; the project uses Attempt History.
- A "transcript" — that is a course concept; the project uses Attempt History.

#### Future Extensions
- Attempt History streaming for real-time analytics.
- Attempt History export for Learner data portability.
- Attempt History ML feature extraction.

---

### Learning History

#### Name
**Learning History**

#### Definition
**Learning History** is the umbrella term for the broader record of a **Learner**'s engagement: not just **Attempt**s but also **StudySession**s, **Review**s completed, **Milestone**s achieved, **LearningPath** progress, and time-on-platform. It is the human-readable counterpart to the machine-readable **AttemptHistory**.

Learning History is what the Learner sees on their Progress page; Attempt History is what the Engine uses for computation.

#### Business Purpose
The Learning History exists to give the Learner a coherent narrative of their journey. Without it, the Learner would see only MasteryScores; with it, the Learner sees the full arc of their engagement.

#### Lifecycle
- **Aggregated** continuously from Attempt History, StudySessions, Milestones, and other events.
- **Surfaced** on the Progress page.
- **Retained** with the same policy as Attempt History.

#### Owner
Analytics

#### Relationships
- Aggregated from **AttemptHistory**, **StudySession**s, **Milestone**s, **LearningPath** progress.
- Surfaced on the Progress page.
- The human-readable counterpart to **AttemptHistory**.

#### Invariants
- Learning History is derived; it is not the source (Attempt History is).
- Learning History is filtered by time window (e.g., "this week," "all time").
- Learning History is per-Learner, per-Subject.

#### Examples
1. A Learner's Learning History shows: 6 months on platform, 450 Attempts, 12 StudySessions, 3 Milestones, 60% through the LearningPath.
2. A weekly digest shows: 5 StudySessions, 45 Attempts, 1 Milestone, 3 Concepts advanced.
3. A Learner's all-time Learning History shows the full arc from diagnostic to Graduation.

#### Non-Examples
- **AttemptHistory** — that is the raw Attempt stream; Learning History is the aggregate.
- A "transcript" — that is a course concept; the project uses Learning History.
- A "report card" — that is a course concept; the project uses Learning History.

#### Future Extensions
- Learning History export (portfolio).
- Learning History sharing (with mentors).
- Learning History narratives (AI-summarized arcs).

---

### Session Analytics

#### Name
**Session Analytics**

#### Definition
**Session Analytics** are the per-**StudySession** metrics computed after a session ends: number of **Attempt**s, **SuccessRate**, average time-to-answer, **HintUsage**, **Concept**s covered, **MasteryScore** delta. They are surfaced to the Learner at session end and retained for trend analysis.

#### Business Purpose
The Session Analytics exist to give the Learner immediate feedback on a session and to give the Engine per-session signal for trend analysis. Without them, the Learner would end a session without a summary; with them, the Learner sees concrete outcomes.

#### Lifecycle
- **Computed** at StudySession end.
- **Surfaced** on the session-results page.
- **Retained** for trend analysis.

#### Owner
Analytics

#### Relationships
- Computed from the **Attempt**s in a **StudySession**.
- Includes **SuccessRate**, **AverageResponseTime**, **HintUsage**, **MasteryScore** delta.
- Surfaced at session end.

#### Invariants
- Session Analytics are derived from Attempts; they are not stored separately as source.
- Session Analytics include the MasteryScore delta (before vs. after the session).
- Session Analytics are per-StudySession.

#### Examples
1. A 20-question session: 16 correct (80% SuccessRate), avg 22s per Attempt, 2 Hints used, MasteryScore +0.08.
2. A 10-question review session: 9 correct (90%), avg 15s, 0 Hints, MasteryScore +0.03.
3. A diagnostic session: 25 questions, 12 correct (48%), avg 35s, 0 Hints, baseline MasteryScores established.

#### Non-Examples
- **AttemptHistory** — that is per-Attempt; Session Analytics is per-Session.
- A "score" — that is a single number; Session Analytics is a bundle.
- A "report" — that is a generic concept; the project uses Session Analytics.

#### Future Extensions
- Session Analytics trends (is this session better than the last 5?).
- Session Analytics benchmarking (anonymous cohort comparison).
- Session Analytics export.

---

### Retention Analytics

#### Name
**Retention Analytics**

#### Definition
**Retention Analytics** are the aggregate measurements of how well **Learner**s maintain **MasteryScore**s over time. They include 30-day, 90-day, and 180-day retention curves, per-**Concept** retention, per-**Subject** retention, and cohort retention. Retention Analytics are the Engine's primary success metric — more important than engagement.

#### Business Purpose
The Retention Analytics exist to keep the Engine honest about its educational effectiveness. A platform with high engagement but low retention is failing; Retention Analytics catches this early.

#### Lifecycle
- **Computed** continuously by Analytics jobs.
- **Aggregated** at multiple levels (Concept, Subject, cohort, platform).
- **Surfaced** on the Admin Portal and in weekly digests.

#### Owner
Analytics

#### Relationships
- Computed from **MasteryScore** trajectories over time.
- Includes 30/90/180-day retention curves.
- The primary success metric for the platform.

#### Invariants
- Retention Analytics are computed from MasteryScore trajectories, not from engagement.
- Retention Analytics are reported with a time window.
- Retention Analytics are never optimized at the expense of MasteryScore validity.

#### Examples
1. The Python Subject's 30-day retention is 0.78 (Learners retain 78% of mastery 30 days after last study).
2. The `python.list.mutability` Concept has 30-day retention of 0.85 across all Learners.
3. A cohort that started in September shows 90-day retention of 0.65.

#### Non-Examples
- **Retention** (the metric) — that is the concept; Retention Analytics is the measurement bundle.
- Engagement metrics — those are the opposite of retention; the project tracks both but prioritizes retention.
- A "completion rate" — that is a course concept; the project uses Retention Analytics.

#### Future Extensions
- Retention prediction (forecasting future retention from early data).
- Retention benchmarking (against industry baselines).
- Retention-based curriculum optimization.

---

### Learning Velocity

#### Name
**Learning Velocity**

#### Definition
**Learning Velocity** is a metric representing how quickly a **Learner** is advancing through the curriculum, measured in **Concept**s reaching **Proficient** per week (or per month). It is distinct from engagement (time-on-platform) and from **MasteryScore** (point-in-time mastery); Velocity is the rate of mastery acquisition.

Velocity is used by the **Scheduler** to project **StudyPlan** feasibility and by Analytics to identify Learners who are stalled or accelerating.

#### Business Purpose
The Learning Velocity exists to give the Engine a rate metric for projection and early-warning. Without it, the Engine could not answer "will I be ready by my interview?"; with it, the Engine projects readiness from the current rate.

#### Lifecycle
- **Computed** continuously from **ConceptState** transitions.
- **Aggregated** as a rolling average (e.g., 4-week Velocity).
- **Surfaced** on the Progress page and in **StudyPlan** projections.

#### Owner
Analytics

#### Relationships
- Computed from **ConceptState** transitions (Concepts reaching Proficient per week).
- Drives **StudyPlan** feasibility projections.
- Surfaced on the Progress page.

#### Invariants
- Velocity is a rate (Concepts per unit time), not a level.
- Velocity is rolling (e.g., 4-week average), not instantaneous.
- Velocity is per-Learner, per-Subject.

#### Examples
1. A Learner's 4-week Velocity is 3 Concepts/week (advancing steadily).
2. A Learner's Velocity drops to 0.5 Concepts/week; the Engine flags a stall warning.
3. A Learner's Velocity rises to 5 Concepts/week after a strategy change; the Engine projects earlier Graduation.

#### Non-Examples
- **MasteryScore** — that is a level; Velocity is a rate.
- Engagement (time-on-platform) — that is input; Velocity is outcome.
- A "pace" — that is informal; the project uses Learning Velocity.

#### Future Extensions
- Velocity personalization (what is a healthy Velocity for this Learner?).
- Velocity prediction (forecasting future Velocity from current data).
- Velocity benchmarking (anonymous cohort comparison).

---

### Confidence Trend

#### Name
**Confidence Trend**

#### Definition
A **Confidence Trend** is the trajectory of the **MasteryScore**'s confidence interval for a **Concept** over time. A narrowing confidence interval means the Engine is becoming more certain about the Learner's mastery; a widening one means uncertainty is increasing (usually due to sparse recent data). Confidence Trends are surfaced on the Progress page as a secondary signal.

#### Business Purpose
The Confidence Trend exists to give the Learner a sense of how certain the Engine is about their mastery. Without it, the Learner would see only a number; with it, the Learner sees whether the Engine is confident or still learning about them.

#### Lifecycle
- **Computed** continuously as the MasteryScore's confidence interval.
- **Tracked** over time as a trend.
- **Surfaced** on the Progress page.

#### Owner
Analytics (with Mastery producing)

#### Relationships
- Derived from the **MasteryScore**'s confidence interval.
- Tracked over time as a trend.
- Surfaced on the Progress page.

#### Invariants
- Confidence Trend is derived; it is not stored separately.
- Confidence Trend is per-Learner, per-Concept.
- Confidence Trend narrows with more evidence and widens with sparse data.

#### Examples
1. A Learner's MasteryScore for `python.list.mutability` has a confidence interval of ±0.05 after 12 Attempts; the trend shows narrowing from ±0.20.
2. A Learner's MasteryScore for `python.gil.bound_threads` has a confidence interval of ±0.15 after 3 Attempts; the trend is still wide.
3. A Learner returns from a break; their confidence intervals widen as recent data becomes sparse.

#### Non-Examples
- **MasteryScore** — that is the value; Confidence Trend is the uncertainty trajectory.
- **MasteryTrend** — that is the value trajectory; Confidence Trend is the uncertainty trajectory.
- A "margin of error" — that is a static value; Confidence Trend is a trajectory.

#### Future Extensions
- Confidence Trend alerts (notify when confidence drops below threshold).
- Confidence Trend personalization (per-Learner certainty calibration).
- Confidence Trend analytics (which Concepts have persistently low confidence?).

---

### Mastery Trend

#### Name
**Mastery Trend**

#### Definition
A **Mastery Trend** is the trajectory of the **MasteryScore** for a **Concept** over time. It shows whether the Learner's mastery is rising, stable, or declining. Mastery Trends are surfaced on the Progress page as the primary mastery visualization.

#### Business Purpose
The Mastery Trend exists to give the Learner a visual sense of progress. Without it, the Learner would see only current MasteryScores; with it, the Learner sees the direction of travel, which is more motivating than the absolute level.

#### Lifecycle
- **Computed** continuously from the MasteryScore history.
- **Tracked** over time as a trend.
- **Surfaced** on the Progress page.

#### Owner
Analytics

#### Relationships
- Derived from **MasteryScore** history.
- Tracked over time as a trend.
- Surfaced on the Progress page.

#### Invariants
- Mastery Trend is derived; it is not stored separately.
- Mastery Trend is per-Learner, per-Concept.
- Mastery Trend reflects the MasteryScore trajectory, not the MemoryScore trajectory.

#### Examples
1. A Learner's Mastery Trend for `python.list.mutability` shows a rise from 0.40 to 0.85 over 6 weeks.
2. A Learner's Mastery Trend for `python.gil.bound_threads` shows a decline from 0.70 to 0.55 after a 3-week break.
3. A Learner's Mastery Trend for `python.dict.lookup_complexity` is stable at 0.85 for 2 months.

#### Non-Examples
- **MasteryScore** — that is the point-in-time value; Mastery Trend is the trajectory.
- **ConfidenceTrend** — that is the uncertainty trajectory; Mastery Trend is the value trajectory.
- A "grade trend" — that is a course concept; the project uses Mastery Trend.

#### Future Extensions
- Mastery Trend forecasting.
- Mastery Trend benchmarking (anonymous cohort comparison).
- Mastery Trend anomaly detection (flagging unexpected drops).

---

### Concept Statistics

#### Name
**Concept Statistics**

#### Definition
**Concept Statistics** are aggregate metrics about a **Concept** across all **Learner**s: average **MasteryScore**, **SuccessRate**, **TimeToMastery** distribution, **Retention** curve, **Misconception** frequency. They are surfaced on the Admin Portal for **Instructor**s to assess curriculum quality.

#### Business Purpose
The Concept Statistics exist to give the team insight into how a Concept is performing across the Learner population. Without them, the team would author Concepts blindly; with them, the team identifies Concepts that are too hard, too easy, or producing specific Misconceptions.

#### Lifecycle
- **Computed** continuously by Analytics jobs.
- **Aggregated** per **Concept** across all Learners.
- **Surfaced** on the Admin Portal.

#### Owner
Analytics

#### Relationships
- Aggregated per **Concept** across all **Learner**s.
- Includes average **MasteryScore**, **SuccessRate**, **TimeToMastery**, **Retention**.
- Drives **Revision** decisions.

#### Invariants
- Concept Statistics are aggregated; they do not expose individual Learner data.
- Concept Statistics are versioned with the **ContentVersion**.
- Concept Statistics are computed from real Attempt data.

#### Examples
1. `python.list.mutability`: average MasteryScore 0.78, SuccessRate 82%, TimeToMastery 2.5 weeks, 30-day Retention 0.85.
2. `python.gil.bound_threads`: average MasteryScore 0.55, SuccessRate 48%, TimeToMastery 4.2 weeks, 30-day Retention 0.60.
3. `python.asyncio.gather`: average MasteryScore 0.45, SuccessRate 35%; flagged for curriculum review.

#### Non-Examples
- **QuestionStatistics** — those are per-Template; Concept Statistics are per-Concept.
- A Learner's MasteryScore — that is per-Learner; Concept Statistics are aggregated.
- A "concept rating" — that is subjective; the project uses Concept Statistics.

#### Future Extensions
- Concept Statistics benchmarking (across Subjects).
- Concept Statistics anomaly detection.
- Concept Statistics predictive models.

---

### Question Statistics

#### Name
**Question Statistics**

#### Definition
**Question Statistics** are aggregate metrics about a **QuestionTemplate** across all **Learner**s: **SuccessRate**, **Distractor** selection distribution, discrimination, average time-to-answer, **HintUsage** rate. They are surfaced on the Admin Portal for **Instructor**s to assess Template quality.

#### Business Purpose
The Question Statistics exist to give the team insight into how a Template is performing. Without them, the team would author Templates blindly; with them, the team identifies Templates with low discrimination, ineffective Distractors, or unclear prompts.

#### Lifecycle
- **Computed** continuously by Analytics jobs.
- **Aggregated** per **QuestionTemplate** across all Learners.
- **Surfaced** on the Admin Portal.

#### Owner
Analytics

#### Relationships
- Aggregated per **QuestionTemplate** across all **Learner**s.
- Includes **SuccessRate**, **Distractor** distribution, discrimination, time-to-answer.
- Drives **Revision** and **ArchivedContent** decisions.

#### Invariants
- Question Statistics are aggregated; they do not expose individual Learner data.
- Question Statistics are versioned with the **TemplateVersion**.
- Question Statistics are computed from real Attempt data.

#### Examples
1. A dict-lookup Template: SuccessRate 78%, Distractor "O(n)" selected 18%, discrimination 0.65, avg time 12s.
2. A list-mutability Template: SuccessRate 65%, Distractor "creates new list" selected 28%, discrimination 0.72, avg time 18s.
3. A Template with discrimination 0.15 (low); flagged for Revision.

#### Non-Examples
- **ConceptStatistics** — those are per-Concept; Question Statistics are per-Template.
- A Learner's Attempt — that is per-Learner; Question Statistics are aggregated.
- A "question rating" — that is subjective; the project uses Question Statistics.

#### Future Extensions
- Question Statistics benchmarking (across Templates).
- Question Statistics anomaly detection.
- Question Statistics predictive models.

---

### Success Rate

#### Name
**Success Rate**

#### Definition
**Success Rate** is the percentage of **Attempt**s on a **QuestionTemplate** (or **Concept**, or **Learner**) that were scored correct. It is a basic aggregate metric, used as one input among many; it is not a mastery measure on its own.

Success Rate is easily gamed (a Learner could have 100% Success Rate by attempting only easy Concepts), so the Engine never uses it as the primary mastery signal. It is a diagnostic, not a verdict.

#### Business Purpose
The Success Rate exists as a basic diagnostic metric for Templates, Concepts, and Learners. Without it, the team would lack a quick aggregate; with it, the team has a first-pass signal that complements the MasteryScore.

#### Lifecycle
- **Computed** continuously by Analytics jobs.
- **Aggregated** per **QuestionTemplate**, **Concept**, **Learner**.
- **Surfaced** as a diagnostic, not a primary metric.

#### Owner
Analytics

#### Relationships
- Computed from **Attempt** outcomes.
- Aggregated per Template, Concept, Learner.
- A diagnostic input, not a primary mastery signal.

#### Invariants
- Success Rate is a percentage (0–100%).
- Success Rate is not weighted by difficulty or hint usage (those are separate metrics).
- Success Rate is never used as the sole mastery signal.

#### Examples
1. A Template's Success Rate is 78% across 500 Attempts.
2. A Concept's Success Rate is 82% across all Templates testing it.
3. A Learner's Success Rate is 71% across all Attempts in the Python Subject.

#### Non-Examples
- **MasteryScore** — that is the model-based estimate; Success Rate is the raw percentage.
- **FailureRate** — that is the complement (1 - Success Rate); the project uses both.
- A "grade" — that is a course concept; the project uses Success Rate as one metric among many.

#### Future Extensions
- Weighted Success Rate (weighted by difficulty).
- Time-decayed Success Rate (recent Attempts weighted more).
- Success Rate benchmarking.

---

### Failure Rate

#### Name
**Failure Rate**

#### Definition
**Failure Rate** is the complement of **SuccessRate**: the percentage of **Attempt**s that were scored incorrect (or partial). It is presented alongside Success Rate for completeness; the two sum to 100% (ignoring partial credit, which is reported separately).

#### Business Purpose
The Failure Rate exists as the complement to Success Rate, useful for identifying Concepts or Templates where Learners struggle. The Engine uses it as a diagnostic, not a primary metric.

#### Lifecycle
- **Computed** continuously by Analytics jobs.
- **Aggregated** per **QuestionTemplate**, **Concept**, **Learner**.
- **Surfaced** as a diagnostic alongside Success Rate.

#### Owner
Analytics

#### Relationships
- The complement of **SuccessRate**.
- Computed from **Attempt** outcomes.
- A diagnostic input.

#### Invariants
- Failure Rate + Success Rate + Partial Rate = 100%.
- Failure Rate is not weighted.
- Failure Rate is never used as the sole mastery signal.

#### Examples
1. A Template's Failure Rate is 22% (Success Rate 78%).
2. A Concept's Failure Rate is 18% (Success Rate 82%).
3. A Learner's Failure Rate is 29% (Success Rate 71%).

#### Non-Examples
- **SuccessRate** — that is the complement; the project uses both.
- A "drop rate" — that is a course concept; the project uses Failure Rate.
- **WeakConcept** — that is a Learner-Concept state; Failure Rate is an aggregate.

#### Future Extensions
- Failure Rate decomposition (by Misconception).
- Failure Rate trends over time.
- Failure Rate benchmarking.

---

### Time to Mastery

#### Name
**Time to Mastery**

#### Definition
**Time to Mastery** is the duration from a **Learner**'s first **Attempt** on a **Concept** to the moment the **MasteryScore** first reaches the **Mastered** threshold. It is a per-Learner, per-Concept metric, aggregated into distributions for analytics.

Time to Mastery is distinct from **TimeToMastery** for a Concept (which is the aggregate distribution) and from **AverageResponseTime** (which is per-Attempt).

#### Business Purpose
The Time to Mastery exists to give the team a measure of how long mastery takes. Without it, the team could not identify Concepts that take unusually long (suggesting curriculum issues); with it, the team targets Revisions where they matter.

#### Lifecycle
- **Computed** when a Concept first reaches Mastered for a Learner.
- **Aggregated** into distributions per **Concept** and per **Subject**.
- **Surfaced** on the Admin Portal.

#### Owner
Analytics

#### Relationships
- Computed from **Attempt** history and **MasteryScore** trajectory.
- Per-Learner, per-Concept; aggregated into distributions.
- Drives curriculum Review for Concepts with long Time to Mastery.

#### Invariants
- Time to Mastery is a duration (e.g., 2.5 weeks).
- Time to Mastery is computed only for Concepts that reach Mastered.
- Time to Mastery is per-Learner; the aggregate is a distribution.

#### Examples
1. A Learner's Time to Mastery for `python.list.mutability` is 2.5 weeks (12 Attempts).
2. The `python.gil.bound_threads` Concept has a median Time to Mastery of 4.2 weeks across all Learners.
3. A Concept with median Time to Mastery of 8 weeks is flagged for curriculum review (too long).

#### Non-Examples
- **AverageResponseTime** — that is per-Attempt; Time to Mastery is per-Concept-acquisition.
- A "completion time" — that is a course concept; the project uses Time to Mastery.
- **LearningVelocity** — that is a rate; Time to Mastery is a duration.

#### Future Extensions
- Time to Mastery prediction (forecasting from early Attempts).
- Time to Mastery personalization (per-Learner baselines).
- Time to Mastery benchmarking.

---

### Average Response Time

#### Name
**Average Response Time**

#### Definition
**Average Response Time** is the mean time-to-answer across **Attempt**s on a **QuestionTemplate**, **Concept**, or for a **Learner**. It is a diagnostic metric; fast response with high Success Rate suggests strong mastery, while fast response with low Success Rate suggests guessing.

#### Business Purpose
The Average Response Time exists to give the Engine a signal about Learner fluency and about Template clarity. Without it, the Engine would have only correctness; with it, the Engine distinguishes confident mastery from hesitant correctness.

#### Lifecycle
- **Computed** continuously by Analytics jobs.
- **Aggregated** per Template, Concept, Learner.
- **Used** by the **MasteryEngine** as one input (fast correct weights more than slow correct).

#### Owner
Analytics

#### Relationships
- Computed from **Attempt** time-to-answer.
- Aggregated per Template, Concept, Learner.
- An input to the **MasteryEngine**'s Attempt weighting.

#### Invariants
- Average Response Time is a duration (e.g., 12 seconds).
- Average Response Time is per-Attempt; the aggregate is a mean.
- Average Response Time is normalized by Template difficulty for cross-Template comparison.

#### Examples
1. A Template's Average Response Time is 12 seconds (fast, suggests fluency).
2. A Concept's Average Response Time is 25 seconds (slower, suggests more deliberation).
3. A Learner's Average Response Time is 18 seconds across all Attempts.

#### Non-Examples
- **TimeToMastery** — that is per-Concept-acquisition; Average Response Time is per-Attempt.
- A "speed metric" — that is informal; the project uses Average Response Time.
- Time-on-platform — that is engagement; Average Response Time is per-Attempt fluency.

#### Future Extensions
- Response Time distribution (not just the mean).
- Response Time personalization (per-Learner baselines).
- Response Time anomaly detection (flagging unusually slow Attempts).

---

### Confidence Score

#### Name
**Confidence Score**

#### Definition
A **Confidence Score** is the Engine's certainty about a **MasteryScore**, expressed as a confidence interval (e.g., 0.78 ± 0.06). It is distinct from the MasteryScore itself (the value) and from the **ConfidenceTrend** (the trajectory). A narrow Confidence Score means high certainty; a wide one means low certainty.

The Confidence Score is computed from the evidence count (number of Attempts) and the consistency of outcomes. It widens with sparse data and narrows with consistent evidence.

#### Business Purpose
The Confidence Score exists to keep the Engine honest about its uncertainty. Without it, the Engine would present MasteryScores as certain; with it, the Engine communicates that early MasteryScores are uncertain and later ones are more reliable.

#### Lifecycle
- **Computed** with every MasteryScore update.
- **Widens** with sparse data; **narrows** with consistent evidence.
- **Surfaced** on the Progress page as a secondary signal.

#### Owner
Mastery (produced) with Analytics (surfaced)

#### Relationships
- A property of a **MasteryScore**.
- Computed from evidence count and consistency.
- Surfaced as a confidence interval.

#### Invariants
- Confidence Score is a range (e.g., ±0.06).
- Confidence Score is per-MasteryScore.
- Confidence Score never exceeds the MasteryScore's bounds (e.g., a 0.50 MasteryScore cannot have a ±0.60 Confidence Score).

#### Examples
1. A MasteryScore of 0.78 with 12 Attempts has a Confidence Score of ±0.06.
2. A MasteryScore of 0.65 with 2 Attempts has a Confidence Score of ±0.20 (wide; uncertain).
3. A MasteryScore of 0.85 with 30 Attempts has a Confidence Score of ±0.03 (narrow; certain).

#### Non-Examples
- **MasteryScore** — that is the value; Confidence Score is the uncertainty.
- **ConfidenceTrend** — that is the trajectory; Confidence Score is the point-in-time value.
- A "margin of error" — that is a statistical concept; the project uses Confidence Score.

#### Future Extensions
- Confidence Score personalization (per-Learner calibration).
- Confidence Score alerts (notify when uncertainty is too high for a decision).
- Confidence Score analytics (which Concepts have persistently low confidence?).

---

### Hint Usage

#### Name
**Hint Usage**

#### Definition
**Hint Usage** is the rate at which **Learner**s use **Hint**s on a **QuestionTemplate**, **Concept**, or in a **StudySession**. It is a diagnostic metric; high Hint Usage with high Success Rate suggests the Template is hint-dependent, while high Hint Usage with low Success Rate suggests the Concept is too hard.

Hint Usage is recorded per **Attempt** (which tiers, in what order) and aggregated for analytics.

#### Business Purpose
The Hint Usage exists to give the team a signal about Template difficulty and Concept clarity. Without it, the team would lack data on whether Hints are helping; with it, the team identifies Templates where Hints are overused (suggesting the prompt is unclear) or underused (suggesting the Hints are ineffective).

#### Lifecycle
- **Recorded** per **Attempt** (which Hint tiers, in what order).
- **Aggregated** per Template, Concept, Learner.
- **Used** by the **MasteryEngine** to modulate MasteryScore updates (Hint-aided correct counts less).

#### Owner
Analytics (with Assessment recording)

#### Relationships
- Recorded per **Attempt**.
- Aggregated per Template, Concept, Learner.
- An input to the **MasteryEngine**'s Attempt weighting.

#### Invariants
- Hint Usage is a rate (0–100% of Attempts using at least one Hint).
- Hint Usage records which tiers were used, not just a boolean.
- Hint Usage reduces the mastery credit for a correct answer.

#### Examples
1. A Template's Hint Usage is 35% (35% of Attempts used at least one Hint).
2. A Concept's Hint Usage is 50% across all Templates testing it; flagged for review (Concept may be too hard).
3. A Learner's Hint Usage is 15% (uses Hints sparingly).

#### Non-Examples
- **Hint** — that is the content artifact; Hint Usage is the metric.
- A "help rate" — that is informal; the project uses Hint Usage.
- Time-to-answer — that is a different signal; Hint Usage is about Hint consumption.

#### Future Extensions
- Hint Usage personalization (per-Learner hint thresholds).
- Hint Usage analytics (which Hints actually help?).
- Hint Usage adaptive thresholds (offer Hints automatically after N seconds).

---

# Part V — Identity Domain

The Identity Domain owns the vocabulary of who users are and what they may do. These terms govern authentication, authorization, billing, and organizational structure.

---

### User Profile

#### Name
**User Profile**

#### Definition
A **User Profile** is the set of user-facing attributes for a **User**: name, email, timezone, preferences, avatar. It is distinct from the **User** (the identity root) and from **UserCredential** (the authentication data). The Profile is what the User edits in Settings; the User is what the system authenticates.

The Profile carries no security-sensitive data; it is the user-facing projection of the User.

#### Business Purpose
The User Profile exists to separate user-editable attributes from identity and credentials. Without it, profile edits would ripple into authentication; with it, profile changes are isolated.

#### Lifecycle
- **Created** at signup with default values.
- **Updated** by the User in Settings.
- **Anonymized** on account deletion (PII purged).

#### Owner
Identity

#### Relationships
- Belongs to a **User**.
- Distinct from **UserCredential**.
- Read by Learning, Analytics, Administration (for support).

#### Invariants
- A User has exactly one Profile.
- A Profile carries no security-sensitive data.
- Profile updates do not affect authentication.

#### Examples
1. A User sets their name to "Alex Chen" and timezone to "Asia/Kolkata" in Settings.
2. A User updates their email; verification is required before the change takes effect.
3. A User deletes their account; their Profile is anonymized.

#### Non-Examples
- The **User** — that is the identity root; the Profile is the attributes.
- **UserCredential** — that is authentication data; the Profile is user-facing.
- A "profile" in a social-network sense — the project's Profile is functional, not social.

#### Future Extensions
- Profile customization (themes, layouts).
- Profile sharing (with mentors).
- Profile import (from other platforms).

---

### Authentication

#### Name
**Authentication**

#### Definition
**Authentication** is the process of verifying a **User**'s identity. The project uses JWT-based authentication: short-lived access tokens, long-lived refresh tokens (HttpOnly cookies), OAuth (Google, GitHub), and optional MFA (TOTP). Authentication is the responsibility of the Identity bounded context.

Authentication is distinct from **Authorization** (which decides what an authenticated User may do).

#### Business Purpose
The Authentication exists to establish identity securely. Without it, any request could claim any identity; with it, identity is cryptographically verified.

#### Lifecycle
- **Triggered** at login, at token refresh, at OAuth callback.
- **Verified** on every authenticated request (JWT signature, expiry, revocation list).
- **Logged** in the AuditLog for security events.

#### Owner
Identity

#### Relationships
- A process owned by the Identity context.
- Issues JWTs and refresh tokens.
- Distinct from **Authorization**.

#### Invariants
- Access tokens are short-lived (15 minutes).
- Refresh tokens are rotated on every use.
- Authentication events are logged in the AuditLog.

#### Examples
1. A User logs in with email/password; the Engine issues an access token and a refresh token.
2. A User's access token expires; the frontend uses the refresh token to get a new one.
3. A User enables MFA; subsequent logins require a TOTP code.

#### Non-Examples
- **Authorization** — that decides permissions; Authentication verifies identity.
- A "session" — that is the result of Authentication; Authentication is the process.
- A "login" — that is one trigger; Authentication is the broader process.

#### Future Extensions
- Passwordless authentication (magic link, passkeys).
- Biometric authentication (mobile).
- Federated identity (SAML for enterprise).

---

### Authorization

#### Name
**Authorization**

#### Definition
**Authorization** is the process of deciding what an authenticated **User** may do. The project uses role-based access control (RBAC) at the coarse grain (Learner, Instructor, Administrator) and resource-based access control at the fine grain (a User may only edit their own Profile). Authorization is enforced at two layers: the Controller (role check) and the Use Case Service (resource ownership check).

Authorization is distinct from **Authentication** (which verifies identity).

#### Business Purpose
The Authorization exists to enforce least privilege. Without it, any authenticated User could do anything; with it, Users can do only what their role and resource ownership permit.

#### Lifecycle
- **Enforced** on every request that touches a protected resource.
- **Checked** at the Controller (role) and at the Use Case Service (ownership).
- **Logged** in the AuditLog for privileged actions.

#### Owner
Identity (with each context enforcing its own resource checks)

#### Relationships
- A process enforced across all contexts.
- Uses **Role**s and **Permission**s.
- Distinct from **Authentication**.

#### Invariants
- Authorization is enforced at two layers (Controller + Use Case).
- Privileged actions are logged in the AuditLog.
- Authorization failures return 403, not 401 (which is Authentication failure).

#### Examples
1. A Learner requests their own MasteryScores; Authorization permits (resource owner).
2. A Learner requests another Learner's MasteryScores; Authorization denies (not resource owner).
3. An Instructor requests content authoring tools; Authorization permits (Instructor role).

#### Non-Examples
- **Authentication** — that verifies identity; Authorization decides permissions.
- A "permission" — that is one input; Authorization is the process.
- A "login" — that is Authentication; Authorization happens after.

#### Future Extensions
- Attribute-based access control (ABAC) for finer-grained policies.
- Policy as code (declarative authorization rules).
- Just-in-time elevation (temporary role grants).

---

### Role

#### Name
**Role**

#### Definition
A **Role** is a named set of **Permission**s granted to a **User**. The project defines four roles: **Learner** (study within enrolled Subjects), **Instructor** (author and review content), **Administrator** (manage the platform), and a future **Mentor** role (guide other Learners). A User may hold multiple roles simultaneously (e.g., Instructor in Python and Learner in SQL).

Roles are scoped: Instructor is per-Subject; Administrator is platform-wide; Learner is per-Subject (via enrollment).

#### Business Purpose
The Role exists to group Permissions into manageable units. Without it, every User would need individual Permission grants; with it, role assignment conveys a bundle of Permissions.

#### Lifecycle
- **Granted** by an Administrator (for Instructor, Administrator) or by enrollment (for Learner).
- **Revoked** by an Administrator or by unenrollment.
- **Scoped** per-Subject for Instructor and Learner; platform-wide for Administrator.

#### Owner
Identity

#### Relationships
- A named set of **Permission**s.
- Granted to a **User**.
- Scoped per-Subject (Instructor, Learner) or platform-wide (Administrator).

#### Invariants
- A User may hold multiple Roles simultaneously.
- Instructor and Learner roles are per-Subject; Administrator is platform-wide.
- Role grants are logged in the AuditLog.

#### Examples
1. A User is enrolled in Python; they have the Learner role in Python.
2. An Administrator grants the Instructor role to a User for the SQL Subject.
3. A User holds Learner (Python), Learner (SQL), and Instructor (Python) simultaneously.

#### Non-Examples
- A **Permission** — that is one capability; a Role is a bundle.
- A "user type" — that is informal; the project uses Role.
- A "tier" (free/pro) — that is a **Subscription** concept, not a Role.

#### Future Extensions
- Custom roles (organization-defined).
- Role inheritance (a Mentor role that includes Learner permissions).
- Role analytics (which roles drive which behaviors?).

---

### Permission

#### Name
**Permission**

#### Definition
A **Permission** is a single capability granted to a **Role**: "create Concept," "publish ContentPack," "view Admin Portal," "refund Subscription." Permissions are the atomic unit of **Authorization**; Roles bundle Permissions for manageability.

Permissions are not granted to Users directly; they are granted to Roles, and Users inherit Permissions through their Roles.

#### Business Purpose
The Permission exists to be the atomic unit of access control. Without it, Roles would be opaque bundles; with it, the team can audit and adjust capabilities precisely.

#### Lifecycle
- **Defined** by the platform (a catalog of Permissions).
- **Granted** to **Role**s (not to Users directly).
- **Inherited** by Users through their Roles.
- **Versioned** with the platform (new Permissions may be added; existing ones are stable).

#### Owner
Identity

#### Relationships
- An atomic capability.
- Granted to **Role**s.
- Inherited by **User**s through Roles.
- Enforced by **Authorization**.

#### Invariants
- Permissions are granted to Roles, not to Users directly.
- Permissions are platform-defined; Users cannot create custom Permissions.
- Permission checks are enforced at two layers (Controller + Use Case).

#### Examples
1. `content:concept:create` — granted to the Instructor role.
2. `admin:user:suspend` — granted to the Administrator role.
3. `billing:subscription:refund` — granted to the Administrator role.

#### Non-Examples
- A **Role** — that is a bundle; a Permission is one capability.
- A "capability" in the sense of a feature flag — that is a **FeatureFlag**; a Permission is an access control unit.
- A "right" — that is informal; the project uses Permission.

#### Future Extensions
- Permission analytics (which Permissions are most used?).
- Permission delegation (a User temporarily grants a Permission to another).
- Permission groups (sub-bundles within Roles).

---

### Subscription

#### Name
**Subscription**

#### Definition
A **Subscription** is a **User**'s billing relationship with the platform: the active **BillingPlan**, the renewal date, the payment method, and the entitlement state. Subscriptions are managed by the Billing bounded context and integrate with an external payment provider (Stripe by default).

A Subscription determines what the User may access (free tier vs. paid tier). Entitlements are computed from the Subscription state and exposed to other contexts through a read interface.

#### Business Purpose
The Subscription exists to monetize the platform. Without it, all features would be free or all would be paid; with it, the platform offers a free tier for acquisition and a paid tier for revenue.

#### Lifecycle
- **Started** when a User subscribes to a BillingPlan.
- **Renewed** on the renewal date (monthly or annual).
- **Upgraded** / **Downgraded** between BillingPlans.
- **Canceled** by the User or by the system (non-payment).
- **Expired** at the end of the billing period after cancellation.

#### Owner
Billing

#### Relationships
- Belongs to a **User**.
- References a **BillingPlan**.
- Determines entitlements (what the User may access).
- Integrates with an external payment provider.

#### Invariants
- A User has at most one active Subscription at a time.
- Subscription state changes are logged in the AuditLog.
- Entitlements are computed from Subscription state, not stored separately.

#### Examples
1. A User subscribes to the Pro plan; their Subscription is active; they have Pro entitlements.
2. A User downgrades from Pro to Free; their Subscription changes; entitlements update at the next renewal.
3. A User's payment fails; their Subscription enters a grace period; entitlements are retained for 7 days before suspension.

#### Non-Examples
- A **BillingPlan** — that is the offering; a Subscription is the User's instance of a plan.
- A **Role** — that is access control; a Subscription is billing.
- An "entitlement" — that is derived from a Subscription; the Subscription is the source.

#### Future Extensions
- Family / team Subscriptions (multiple Users on one plan).
- Lifetime deals (one-time payment for permanent access).
- Subscription analytics (which plans retain best?).

---

### Billing Plan

#### Name
**Billing Plan**

#### Definition
A **Billing Plan** is a named offering with a price, a billing period (monthly/annual), and an entitlement set. The project defines plans like "Free" (limited daily questions), "Pro" (unlimited questions, advanced analytics), and "Interview Plus" (Pro + mock interviews, future). BillingPlans are platform-defined; Users subscribe to them via a **Subscription**.

BillingPlans are distinct from **Role**s (access control) and from **Entitlement**s (what the plan grants).

#### Business Purpose
The Billing Plan exists to give the platform a clear monetization structure. Without it, billing would be ad-hoc; with it, plans are versioned, priced, and entitle clearly.

#### Lifecycle
- **Defined** by the platform (a catalog of BillingPlans).
- **Priced** per billing period (monthly, annual).
- **Versioned** (price changes produce new plan versions; existing Subscriptions may be grandfathered).
- **Deprecated** (no new Subscriptions; existing ones continue).

#### Owner
Billing

#### Relationships
- A named offering with price and entitlements.
- Subscribed to by **User**s via **Subscription**s.
- Distinct from **Role**s and **Permission**s.

#### Invariants
- BillingPlans are platform-defined; Users cannot create custom plans.
- BillingPlan changes are versioned; existing Subscriptions are grandfathered unless explicitly migrated.
- Entitlements are derived from the BillingPlan, not stored per-User.

#### Examples
1. "Free" — $0/month, 20 questions per day, basic analytics.
2. "Pro" — $19/month, unlimited questions, advanced analytics, priority support.
3. "Interview Plus" — $49/month, Pro + mock interviews (future).

#### Non-Examples
- A **Subscription** — that is the User's instance; the BillingPlan is the offering.
- A **Role** — that is access control; the BillingPlan is billing.
- A "tier" — that is informal; the project uses BillingPlan.

#### Future Extensions
- Regional pricing.
- Promotional plans (discounted for a period).
- Plan analytics (which plans drive the best retention?).

---

### Organization

#### Name
**Organization**

#### Definition
An **Organization** is a B2B entity that groups multiple **User**s under a single billing and administrative umbrella. An Organization may purchase bulk **Subscription**s, assign **Instructor** roles, and view aggregate analytics for its members. Organizations are a future feature (Phase 5+); the architecture reserves the term.

Organizations are distinct from **Tenant**s (which are content-isolation units) and from **Workspace**s (which are collaboration units within an Organization).

#### Business Purpose
The Organization exists to support B2B monetization. Without it, the platform cannot serve companies buying for their employees; with it, bulk billing and admin delegation are possible.

#### Lifecycle
- **Created** by an Administrator or via self-service B2B signup (future).
- **Populated** with member Users.
- **Billed** via a single Organization Subscription.
- **Managed** by Organization Administrators (a scoped Administrator role).
- **Dissolved** by request; member Users revert to individual Subscriptions.

#### Owner
Billing (with Administration for management)

#### Relationships
- Groups multiple **User**s.
- Has a single Organization Subscription.
- Has Organization Administrators (scoped role).
- Distinct from **Tenant** and **Workspace**.

#### Invariants
- An Organization has at least one Organization Administrator.
- An Organization's members are Users (not Learners; Learner is per-Subject).
- Organization dissolution preserves member Users' learning data.

#### Examples
1. A company buys 50 Pro Subscriptions for its engineering team; an Organization is created with 50 members.
2. An Organization Administrator assigns Instructor roles to senior engineers.
3. An Organization views aggregate analytics for its members (anonymized individual data).

#### Non-Examples
- A **Tenant** — that is a content-isolation unit; an Organization is a billing unit.
- A **Workspace** — that is a collaboration unit within an Organization.
- A "team" — that is informal; the project uses Organization.

#### Future Extensions
- SSO integration (SAML, OIDC) for Organizations.
- Organization-level content customization (private Concepts).
- Organization analytics dashboards.

---

### Tenant

#### Name
**Tenant**

#### Definition
A **Tenant** is a content-isolation unit: a **Subject** plus its **Learner**s, **Instructor**s, and content. The project's first Tenant is the Python Subject; future Tenants include SQL, Java, etc. The Mastery Engine core is Tenant-agnostic; Tenancy is a data concept, not a code-fork concept.

Tenant is distinct from **Organization** (billing) and **Workspace** (collaboration). In the current architecture, Tenant and Subject are near-synonyms; the term Tenant is reserved for future multi-Subject-per-Tenant scenarios.

#### Business Purpose
The Tenant exists to give the Engine a content-isolation boundary. Without it, content from different Subjects would mix; with it, each Subject is a clean universe.

#### Lifecycle
- **Created** when a new Subject is published.
- **Populated** with Concepts, Templates, Learners, Instructors.
- **Versioned** via ContentVersions.
- **Deprecated** when the Subject is retired.

#### Owner
Content (with Learning for enrollment)

#### Relationships
- A content-isolation unit containing a **Subject** and its constituents.
- Distinct from **Organization** (billing) and **Workspace** (collaboration).
- Near-synonym with Subject in the current architecture.

#### Invariants
- A Tenant's content is isolated from other Tenants.
- A Learner's mastery state is per-Tenant.
- Tenancy is a data concept, not a code-fork concept.

#### Examples
1. The Python Subject is the first Tenant.
2. The SQL Subject will be the second Tenant.
3. A Learner enrolled in Python and SQL has mastery state in two Tenants, isolated.

#### Non-Examples
- An **Organization** — that is a billing unit; a Tenant is a content unit.
- A **Workspace** — that is a collaboration unit within an Organization.
- A "database tenant" — that is an infrastructure concept; the project's Tenant is domain-level.

#### Future Extensions
- Multi-Subject Tenants (a "backend interview" Tenant containing Python, SQL, System Design).
- Tenant-specific configuration (per-Tenant Scheduler weights).
- Tenant migration (moving Learners between Tenants).

---

### Workspace

#### Name
**Workspace**

#### Definition
A **Workspace** is a collaboration unit within an **Organization**: a subset of the Organization's members who share a learning context (e.g., a "backend interview prep" workspace, a "SQL fundamentals" workspace). Workspaces are a future feature (Phase 5+); the architecture reserves the term.

Workspaces are distinct from **Organization**s (billing) and **Tenant**s (content isolation). A Workspace operates within a single Organization and may span multiple Tenants.

#### Business Purpose
The Workspace exists to support team-based learning within Organizations. Without it, Organizations would be monolithic; with it, sub-teams can have focused learning contexts.

#### Lifecycle
- **Created** by an Organization Administrator.
- **Populated** with a subset of the Organization's members.
- **Scoped** to one or more Tenants (Subjects).
- **Dissolved** by the Organization Administrator; member learning data is preserved.

#### Owner
Administration (future)

#### Relationships
- A collaboration unit within an **Organization**.
- Contains a subset of Organization members.
- May span multiple **Tenant**s.
- Distinct from Organization and Tenant.

#### Invariants
- A Workspace belongs to exactly one Organization.
- A Workspace's members are a subset of the Organization's members.
- Workspace dissolution preserves member learning data.

#### Examples
1. A company's "backend interview prep" Workspace with 10 engineers, spanning Python and SQL Tenants.
2. A company's "data science fundamentals" Workspace with 5 analysts, spanning SQL and Python Tenants.
3. A Workspace is dissolved; the 10 engineers retain their individual learning data.

#### Non-Examples
- An **Organization** — that is the billing unit; a Workspace is a sub-unit.
- A **Tenant** — that is a content unit; a Workspace is a collaboration unit.
- A "team" — that is informal; the project uses Workspace.

#### Future Extensions
- Workspace analytics (which Workspaces drive the best outcomes?).
- Workspace leaderboards (gamification within teams).
- Workspace mentorship (Mentor role within a Workspace).

---

# Part VI — Engineering Domain

The Engineering Domain owns the vocabulary of software architecture: the building blocks (Aggregate, Entity, Value Object), the patterns (Repository, Service, Event Bus), and the artifacts (DTO, ADR, Feature Flag) that engineers use to construct the system. These terms are shared across all bounded contexts.

---

### Aggregate

#### Name
**Aggregate**

#### Definition
An **Aggregate** is a cluster of domain objects treated as a single unit for data consistency. Each Aggregate has a root **Entity** (the Aggregate Root) and a boundary that defines what is inside vs. outside. Persistence is atomic at the Aggregate level: a save of an Aggregate is all-or-nothing. The project's Aggregates include **User**, **Concept**, **Attempt**, **MasteryScore**, **StudySession**.

Aggregates are the unit of transactional integrity. Cross-Aggregate consistency is achieved via **DomainEvent**s, not via cross-Aggregate transactions.

#### Business Purpose
The Aggregate exists to define consistency boundaries. Without it, the team would face "everything in one transaction" (slow, fragile) or "no consistency" (incorrect); with Aggregates, the team has clean, bounded consistency units.

#### Lifecycle
- **Defined** during domain modeling (one per consistency boundary).
- **Persisted** atomically via a **Repository**.
- **Updated** via methods on the Aggregate Root (not by direct field mutation).
- **Versioned** for optimistic concurrency control.

#### Owner
Cross-cutting (each context defines its own Aggregates)

#### Relationships
- A cluster of domain objects with a root **Entity**.
- Persisted via a **Repository**.
- Communicates with other Aggregates via **DomainEvent**s.
- The unit of transactional integrity.

#### Invariants
- An Aggregate is persisted atomically.
- Cross-Aggregate consistency is via events, not transactions.
- Aggregate updates go through the root's methods.

#### Examples
1. The **User** Aggregate includes the User root and its UserCredential.
2. The **Attempt** Aggregate is a single immutable record (no children).
3. The **Concept** Aggregate includes the Concept root and its LearningObjectives.

#### Non-Examples
- An **Entity** — that is a domain object with identity; an Aggregate is a consistency boundary.
- A **ValueObject** — that is an immutable, compared-by-value object; an Aggregate is a consistency unit.
- A "table" — that is a database concept; an Aggregate is a domain concept.

#### Future Extensions
- Aggregate splitting (when an Aggregate grows too large).
- Aggregate merging (when two Aggregates need stronger consistency).
- Aggregate analytics (which Aggregates have the most contention?).

---

### Entity

#### Name
**Entity**

#### Definition
An **Entity** is a domain object with a distinct identity that persists over time, even as its attributes change. Entities are distinguished by their identity (typically a UUID), not by their attribute values. The project's Entities include **User**, **Concept**, **Attempt**, **StudySession**.

Entities are contrasted with **ValueObject**s, which have no identity and are compared by value. An Entity may be an **Aggregate** Root or a child within an Aggregate.

#### Business Purpose
The Entity exists to model domain objects with identity. Without it, the team would conflate identity-bearing objects (Users, Concepts) with value objects (MasteryScores, timestamps); with Entities, the team models identity correctly.

#### Lifecycle
- **Created** with a unique identity (typically a UUID).
- **Updated** via methods (for Entities that are mutable).
- **Persisted** within an Aggregate.
- **Compared** by identity, not by attribute values.

#### Owner
Cross-cutting

#### Relationships
- A domain object with identity.
- May be an **Aggregate** Root or a child.
- Distinct from **ValueObject**.
- Persisted via a **Repository** (if an Aggregate Root).

#### Invariants
- An Entity has a unique identity that persists over time.
- Entities are compared by identity, not by attribute values.
- An Entity's identity is immutable (a new identity is a new Entity).

#### Examples
1. A **User** is an Entity (identity = user_id; attributes change over time).
2. A **Concept** is an Entity (identity = concept_id; attributes change via Revisions).
3. An **Attempt** is an Entity (identity = attempt_id; but it is immutable after creation).

#### Non-Examples
- A **ValueObject** — that is compared by value; an Entity is compared by identity.
- An **Aggregate** — that is a consistency boundary; an Entity is a domain object.
- A "row" — that is a database concept; an Entity is a domain concept.

#### Future Extensions
- Entity identity strategies (UUID, snowflake, natural keys).
- Entity lifecycle modeling (created, active, archived).
- Entity analytics (which Entities have the most relationships?).

---

### Value Object

#### Name
**Value Object**

#### Definition
A **Value Object** is an immutable domain object compared by value, not by identity. Two Value Objects with the same attributes are interchangeable. The project's Value Objects include **MasteryScore** (a numeric value with a confidence interval), **TimeWindow** (a start and end), **QuestionSeed** (a parameter seed).

Value Objects are contrasted with **Entity**s, which have identity. Value Objects are typically children within an **Aggregate**.

#### Business Purpose
The Value Object exists to model domain concepts that are defined by their value, not by identity. Without it, the team would impose identity on concepts that don't have it (e.g., "which MasteryScore is this?" — the question is meaningless; MasteryScores are interchangeable if equal); with Value Objects, the team models correctly.

#### Lifecycle
- **Created** with all attributes (no setters).
- **Immutable**; "changes" produce a new Value Object.
- **Compared** by attribute values.
- **Persisted** as part of an Aggregate (typically as embedded values).

#### Owner
Cross-cutting

#### Relationships
- An immutable, compared-by-value domain object.
- Distinct from **Entity**.
- Typically a child within an **Aggregate**.

#### Invariants
- A Value Object is immutable.
- Value Objects are compared by attribute values.
- Value Objects have no identity.

#### Examples
1. A **MasteryScore** is a Value Object (value = 0.78 ± 0.06; two scores with the same value are interchangeable).
2. A **TimeWindow** is a Value Object (start, end; two windows with the same bounds are interchangeable).
3. A **QuestionSeed** is a Value Object (an integer; two seeds with the same value produce the same Question).

#### Non-Examples
- An **Entity** — that has identity; a Value Object does not.
- An **Aggregate** — that is a consistency boundary; a Value Object is a domain object.
- A "struct" — that is a language concept; a Value Object is a domain concept.

#### Future Extensions
- Value Object validation (invariants enforced at construction).
- Value Object factories (canonical construction).
- Value Object analytics (which Value Objects are most used?).

---

### Repository

#### Name
**Repository**

#### Definition
A **Repository** is the persistence abstraction for an **Aggregate**: it provides methods to load and save the Aggregate, hiding the database details. Each Aggregate has exactly one Repository interface (in the domain layer) and one implementation (in the infrastructure layer). Repositories enforce the single-writer principle: no other component writes the same Aggregate.

Repositories are the boundary between the domain layer (pure, no I/O) and the infrastructure layer (database, external services). Domain Services and Use Case Services depend on Repository interfaces, not implementations.

#### Business Purpose
The Repository exists to decouple the domain from the database. Without it, domain code would contain SQL; with it, domain code is pure and testable, and database changes are isolated.

#### Lifecycle
- **Defined** as an interface in the domain layer.
- **Implemented** in the infrastructure layer.
- **Wired** by the DI container.
- **Substituted** with fakes in tests.

#### Owner
Cross-cutting (each context defines its own Repositories)

#### Relationships
- The persistence abstraction for an **Aggregate**.
- One interface per Aggregate, in the domain layer.
- One implementation per Aggregate, in the infrastructure layer.
- Depended on by Domain Services and Use Case Services.

#### Invariants
- One Repository per Aggregate.
- Repositories enforce single-writer (no other component writes the same table).
- Repositories accept and return Aggregates, not ORM models.

#### Examples
1. The `AttemptRepository` interface (domain) and its SQLAlchemy implementation (infrastructure).
2. The `MasteryScoreRepository` interface and implementation.
3. A test substitutes a `FakeAttemptRepository` to test the MasteryEngine without a database.

#### Non-Examples
- A **Service** — that contains business logic; a Repository persists.
- A "DAO" (Data Access Object) — that is a thinner abstraction; a Repository is domain-oriented.
- A "table gateway" — that is a database pattern; a Repository is a domain pattern.

#### Future Extensions
- Repository caching (transparent caching of loaded Aggregates).
- Repository batching (loading multiple Aggregates in one query).
- Repository analytics (which Repositories have the most load?).

---

### Service

#### Name
**Service**

#### Definition
A **Service** is a stateless domain component that performs business logic that does not naturally belong to an **Entity** or **ValueObject**. Services are categorized as **DomainService**s (pure business rules), **ApplicationService**s (use-case orchestration), and **InfrastructureService**s (external integrations). The project's Services include the MasteryEngine, the Scheduler, the QuestionFactory (all Domain Services).

Services are stateless; state lives in Aggregates, accessed via Repositories.

#### Business Purpose
The Service exists to house business logic that doesn't fit on an Entity. Without it, Entities would bloat with cross-cutting logic; with Services, Entities stay focused on their own state.

#### Lifecycle
- **Defined** as a class with business methods.
- **Wired** by the DI container with its dependencies.
- **Invoked** by Use Case Services (for Domain Services) or Controllers (for Application Services).
- **Stateless**; no instance variables persist between calls.

#### Owner
Cross-cutting

#### Relationships
- A stateless domain component.
- Categorized as **DomainService**, **ApplicationService**, **InfrastructureService**.
- Depended on by other Services and Controllers.
- Uses Repositories for persistence.

#### Invariants
- Services are stateless.
- Services depend on abstractions (Repository interfaces, other Service interfaces).
- Domain Services perform no I/O.

#### Examples
1. The **MasteryEngine** is a Domain Service (pure function: Attempt + prior Mastery → new Mastery).
2. The `StartStudySession` use case is an Application Service (orchestrates Identity, Learning, Scheduling).
3. The `StripeClient` is an Infrastructure Service (wraps the Stripe API).

#### Non-Examples
- An **Entity** — that has identity and state; a Service is stateless.
- A **Repository** — that persists; a Service performs business logic.
- A "function" — that is a language concept; a Service is a domain concept.

#### Future Extensions
- Service composition (Services calling Services, with documented dependency graphs).
- Service analytics (which Services are on the critical path?).
- Service extraction (promoting a Service to a microservice).

---

### Domain Event

#### Name
**Domain Event**

#### Definition
A **Domain Event** is a record of something that happened in the domain: `AttemptRecorded`, `MasteryUpdated`, `ContentPublished`, `UserEnrolled`. Events are published by the context that caused them and consumed by other contexts asynchronously. The project uses the outbox pattern: events are written to an outbox table in the same transaction as the originating write, then dispatched by a background worker.

Events are the primary mechanism for cross-context communication. They enable loose coupling: the publishing context does not know who consumes its events.

#### Business Purpose
The Domain Event exists to decouple contexts. Without it, contexts would call each other directly, creating tight coupling; with events, contexts communicate asynchronously and can evolve independently.

#### Lifecycle
- **Raised** by a Use Case Service after a state change.
- **Written** to the outbox in the same transaction.
- **Dispatched** by a background worker to subscribers.
- **Consumed** by other contexts' event handlers.
- **Persisted** for audit and replay.

#### Owner
Cross-cutting (each context raises its own events)

#### Relationships
- A record of a domain occurrence.
- Published via the **Outbox**.
- Consumed by other contexts via the **EventBus**.
- Named in past tense (`AttemptRecorded`, not `RecordAttempt`).

#### Invariants
- Events are immutable once raised.
- Events are published transactionally with the originating write (outbox pattern).
- Event names are in past tense.

#### Examples
1. `AttemptRecorded` — raised by Assessment after an Attempt is written; consumed by Mastery and Analytics.
2. `MasteryUpdated` — raised by Mastery after a MasteryScore update; consumed by Scheduling and Notification.
3. `ContentPublished` — raised by Content after a ContentPack publishes; consumed by Analytics and the cache invalidator.

#### Non-Examples
- A **Command** — that is a request to do something; a Domain Event is a record of something done.
- A "log entry" — that is for operations; a Domain Event is for domain communication.
- A "message" — that is a generic concept; the project uses Domain Event.

#### Future Extensions
- Event schemas versioned with the API.
- Event replay (re-processing historical events after a consumer change).
- Event analytics (which events drive the most consumer load?).

---

### Application Service

#### Name
**Application Service**

#### Definition
An **Application Service** is a **Service** that orchestrates a use case: it loads Aggregates via Repositories, calls Domain Services, persists changes, and publishes Domain Events. Application Services define transaction boundaries and assemble DTOs for the response. They are the layer that the Controller calls.

Application Services are distinct from **DomainService**s (pure business rules) and **InfrastructureService**s (external integrations).

#### Business Purpose
The Application Service exists to orchestrate use cases. Without it, Controllers would contain business logic; with Application Services, Controllers stay thin and business logic is testable.

#### Lifecycle
- **Defined** as a class with one public method per use case (e.g., `StartStudySession.execute(input)`).
- **Wired** by the DI container with its dependencies.
- **Invoked** by Controllers.
- **Defines** transaction boundaries.

#### Owner
Cross-cutting (each context defines its own Application Services)

#### Relationships
- A **Service** that orchestrates use cases.
- Calls **DomainService**s and **Repository**s.
- Publishes **DomainEvent**s.
- Invoked by Controllers.

#### Invariants
- Application Services define transaction boundaries.
- Application Services are the only layer that composes multiple Repositories in one transaction.
- Application Services return DTOs, not domain objects.

#### Examples
1. `StartStudySession` — loads User, resolves active session, calls Scheduler, returns session DTO.
2. `SubmitAnswer` — scores the Answer, writes the Attempt, publishes `AttemptRecorded`.
3. `PublishContentPack` — validates, writes the new ContentVersion, publishes `ContentPublished`.

#### Non-Examples
- A **DomainService** — that is pure; an Application Service orchestrates.
- A **Controller** — that handles HTTP; an Application Service handles the use case.
- A "use case" — that is the concept; an Application Service is the implementation.

#### Future Extensions
- Application Service composition (orchestrating other Application Services).
- Application Service analytics (which use cases are most used?).
- Application Service idempotency (retries with the same request id return the same result).

---

### Infrastructure Service

#### Name
**Infrastructure Service**

#### Definition
An **Infrastructure Service** is a **Service** that wraps an external system: the Stripe API, an email provider, an OAuth provider, the sandbox runtime. Infrastructure Services implement interfaces defined in the domain or application layer, allowing the domain to remain pure while still calling external systems.

Infrastructure Services are the outermost layer; they depend on external systems, while nothing depends on them directly (only on their interfaces).

#### Business Purpose
The Infrastructure Service exists to isolate external integrations. Without it, external API calls would be scattered through the domain; with Infrastructure Services, integrations are isolated and substitutable.

#### Lifecycle
- **Defined** as an implementation of a domain or application interface.
- **Wired** by the DI container.
- **Substituted** with fakes in tests.

#### Owner
Cross-cutting (each context defines its own Infrastructure Services)

#### Relationships
- A **Service** that wraps an external system.
- Implements an interface defined in the domain or application layer.
- Depended on by Application Services (via interface).

#### Invariants
- Infrastructure Services implement domain-defined interfaces.
- Infrastructure Services are the only layer that touches external systems.
- Infrastructure Services are substitutable with fakes in tests.

#### Examples
1. `StripeClient` implements `PaymentGateway` (domain interface) and wraps the Stripe API.
2. `SmtpEmailSender` implements `EmailSender` and wraps an SMTP server.
3. `SandboxRunner` implements `CodeExecutor` and wraps the sandbox runtime.

#### Non-Examples
- A **DomainService** — that is pure; an Infrastructure Service touches external systems.
- An **ApplicationService** — that orchestrates; an Infrastructure Service wraps.
- A "client" — that is a thin wrapper; an Infrastructure Service implements a domain interface.

#### Future Extensions
- Infrastructure Service resilience (circuit breakers, retries).
- Infrastructure Service observability (per-integration metrics).
- Infrastructure Service substitution (swapping Stripe for another provider).

---

### DTO

#### Name
**DTO**

#### Definition
A **DTO** (Data Transfer Object) is the wire representation of data crossing a layer boundary. The project has three categories: **Request DTO** (frontend → backend, validated by Pydantic at the Controller), **Response DTO** (backend → frontend, constructed by Application Services), and **Internal DTO** (between Application Services and Domain Services, typed but not serialized). DTOs are Pydantic models.

DTOs are distinct from domain objects (Aggregates, Value Objects): the domain model may evolve without breaking the API contract, because DTOs are translated at the boundary.

#### Business Purpose
The DTO exists to decouple the wire format from the domain model. Without it, API changes would require domain changes; with DTOs, the two evolve independently.

#### Lifecycle
- **Defined** as a Pydantic model alongside the Application Service that uses it.
- **Validated** at the Controller boundary (for Request DTOs).
- **Constructed** by Application Services (for Response DTOs).
- **Serialized** to JSON by FastAPI.

#### Owner
Cross-cutting

#### Relationships
- The wire representation of data.
- Three categories: Request, Response, Internal.
- Pydantic models.
- Distinct from domain objects.

#### Invariants
- DTOs are Pydantic models.
- DTOs are validated at the Controller boundary (Request DTOs).
- DTOs never expose the raw domain model.

#### Examples
1. `StartSessionRequest` (Request DTO) — `{ subject_id: str, intent: str }`.
2. `StartSessionResponse` (Response DTO) — `{ session_id: str, first_question: QuestionDTO }`.
3. `MasteryUpdateInput` (Internal DTO) — passed from Application Service to MasteryEngine.

#### Non-Examples
- A domain **Aggregate** — that is the persisted model; a DTO is the wire model.
- A **ValueObject** — that is a domain concept; a DTO is a wire concept.
- A "struct" — that is a language concept; a DTO is an architectural concept.

#### Future Extensions
- DTO versioning (v1, v2 for the same endpoint).
- DTO generation from OpenAPI (single source of truth).
- DTO analytics (which DTOs are most used?).

---

### Command

#### Name
**Command**

#### Definition
A **Command** is a request to perform an action: `StartStudySession`, `SubmitAnswer`, `PublishContentPack`. Commands are imperative (verb + object) and may succeed or fail. They are the write-side counterpart to **Query**s. In the project, Commands are typically implemented as Application Service methods.

Commands are distinct from **DomainEvent**s (which record what happened; Commands request what should happen).

#### Business Purpose
The Command exists to model write-side operations explicitly. Without it, writes and reads would be conflated; with Commands, the team can reason about, audit, and secure writes separately.

#### Lifecycle
- **Issued** by a Controller (after authentication and authorization).
- **Handled** by an Application Service.
- **Succeeds** (returns a Response DTO) or **fails** (raises an exception).
- **Logged** for audit (especially privileged Commands).

#### Owner
Cross-cutting

#### Relationships
- A write-side request.
- Handled by **ApplicationService**s.
- Distinct from **Query** (read-side) and **DomainEvent** (record of past).

#### Invariants
- Commands are imperative (verb + object).
- Commands may succeed or fail.
- Commands are idempotent where possible (retries with the same request id return the same result).

#### Examples
1. `StartStudySession` (Command) — handled by the StartStudySession Application Service.
2. `SubmitAnswer` (Command) — handled by the SubmitAnswer Application Service.
3. `PublishContentPack` (Command) — handled by the PublishContentPack Application Service.

#### Non-Examples
- A **Query** — that is read-side; a Command is write-side.
- A **DomainEvent** — that records the past; a Command requests the future.
- An "endpoint" — that is HTTP; a Command is a domain concept.

#### Future Extensions
- Command buses (decoupling Controllers from Application Services).
- Command validation pipelines (cross-cutting validation).
- Command analytics (which Commands are most used?).

---

### Query

#### Name
**Query**

#### Definition
A **Query** is a request to read data: `GetMasteryScore`, `ListAttempts`, `GetProgressPage`. Queries are read-side operations; they do not mutate state. They are the read-side counterpart to **Command**s. In the project, Queries are typically implemented as Application Service methods or as direct reads from a **ReadModel**.

Queries are distinct from Commands (write-side) and from **ReadModel**s (the precomputed read-optimized projections that Queries may read from).

#### Business Purpose
The Query exists to model read-side operations explicitly. Without it, reads and writes would be conflated; with Queries, the team can optimize reads independently (e.g., via ReadModels).

#### Lifecycle
- **Issued** by a Controller (after authentication and authorization).
- **Handled** by an Application Service or a Query handler.
- **Returns** a Response DTO without mutating state.
- **Cacheable** (Queries may be cached for performance).

#### Owner
Cross-cutting

#### Relationships
- A read-side request.
- Handled by **ApplicationService**s or Query handlers.
- May read from a **ReadModel**.
- Distinct from **Command** (write-side).

#### Invariants
- Queries do not mutate state.
- Queries are cacheable.
- Queries return Response DTOs.

#### Examples
1. `GetMasteryScore` (Query) — returns the Learner's MasteryScores.
2. `ListAttempts` (Query) — returns a paginated list of Attempts.
3. `GetProgressPage` (Query) — returns the aggregated progress data.

#### Non-Examples
- A **Command** — that is write-side; a Query is read-side.
- A **ReadModel** — that is the projection; a Query is the request.
- A "GET request" — that is HTTP; a Query is a domain concept.

#### Future Extensions
- Query caching strategies (per-User, per-Subject).
- Query batching (multiple Queries in one request).
- Query analytics (which Queries are slowest?).

---

### Read Model

#### Name
**Read Model**

#### Definition
A **Read Model** is a precomputed, read-optimized projection of domain data, optimized for a specific query pattern. The project's Read Models include the Progress page's aggregated mastery-over-time view, the Admin Portal's cohort retention view, and the Dashboard's "what next?" summary. Read Models are updated by background jobs that consume **DomainEvent**s.

Read Models are distinct from the **WriteModel** (the normalized domain Aggregates); they are denormalized for read performance.

#### Business Purpose
The Read Model exists to serve read-heavy queries without burdening the write-optimized database. Without it, complex reads would compete with the learning loop for database resources; with Read Models, reads are fast and isolated.

#### Lifecycle
- **Defined** for a specific query pattern.
- **Populated** by background jobs that consume DomainEvents.
- **Refreshed** on a schedule or on event.
- **Read** by Query handlers.

#### Owner
Cross-cutting (Analytics typically owns Read Models)

#### Relationships
- A read-optimized projection.
- Updated by consuming **DomainEvent**s.
- Read by **Query** handlers.
- Distinct from the **WriteModel**.

#### Invariants
- Read Models are derived; they are not the source of truth.
- Read Models are eventually consistent with the WriteModel.
- Read Models may be rebuilt from the event log.

#### Examples
1. The Progress page's mastery-over-time Read Model, refreshed nightly.
2. The Admin Portal's cohort retention Read Model, refreshed weekly.
3. The Dashboard's "what next?" summary Read Model, refreshed on every event.

#### Non-Examples
- The **WriteModel** — that is the source of truth; a Read Model is a projection.
- A **Query** — that is the request; a Read Model is the data.
- A "materialized view" — that is a database concept; a Read Model is a domain concept (though it may be implemented as a materialized view).

#### Future Extensions
- Read Model versioning (v1, v2 for the same query pattern).
- Read Model caching (in Redis for low-latency reads).
- Read Model analytics (which Read Models are most queried?).

---

### Write Model

#### Name
**Write Model**

#### Definition
The **Write Model** is the normalized, source-of-truth representation of domain data: the **Aggregate**s in PostgreSQL. It is optimized for write consistency and integrity, not for read performance. Reads that need performance use **ReadModel**s.

The Write Model is the canonical data; Read Models are derived projections. If all Read Models were lost, they could be rebuilt from the Write Model and the event log.

#### Business Purpose
The Write Model exists to be the source of truth. Without it, the project would have multiple "truths" (one per Read Model); with a clear Write Model, the source is unambiguous.

#### Lifecycle
- **Updated** by Application Services via Repositories.
- **Transactional**; updates are atomic per Aggregate.
- **Source** for Read Model rebuilds.

#### Owner
Cross-cutting (each context owns its own Write Model Aggregates)

#### Relationships
- The source-of-truth representation.
- Composed of **Aggregate**s.
- The source for **ReadModel** rebuilds.
- Distinct from Read Models.

#### Invariants
- The Write Model is the source of truth.
- Write Model updates are transactional per Aggregate.
- Read Models are derived from the Write Model.

#### Examples
1. The **Attempt** table is part of the Write Model; an Attempt Read Model might denormalize it for analytics.
2. The **MasteryScore** table is part of the Write Model; a Read Model might aggregate it for the Progress page.
3. The **User** table is part of the Write Model; a Read Model might denormalize it for the Admin Portal.

#### Non-Examples
- A **ReadModel** — that is a projection; the Write Model is the source.
- A "database" — that is infrastructure; the Write Model is a domain concept.
- A "primary" in replication — that is a database concept; the Write Model is architectural.

#### Future Extensions
- Write Model sharding (for horizontal scaling).
- Write Model partitioning (e.g., Attempts by time).
- Write Model analytics (which Aggregates have the most write contention?).

---

### Bounded Context

#### Name
**Bounded Context**

#### Definition
A **Bounded Context** is a logical boundary within which a domain model is consistent. Each Bounded Context owns a coherent slice of the domain, exposes a clear interface to other contexts, and persists its own data. The project's Bounded Contexts are: Identity, Learning, Assessment, Mastery, Content, Scheduling, Analytics, Billing, Administration.

Bounded Contexts communicate via **Service** interfaces (synchronous, in-process) and **DomainEvent**s (asynchronous, via the EventBus). Direct cross-context repository access is forbidden.

#### Business Purpose
The Bounded Context exists to manage complexity by dividing the domain into consistent units. Without it, the domain model would be one tangled whole; with Bounded Contexts, each context has a clear model and clear boundaries.

#### Lifecycle
- **Defined** during domain modeling.
- **Owned** by a team (or a sub-team).
- **Communicates** with other contexts via interfaces and events.
- **Evolvable** independently (within its interface contract).

#### Owner
Cross-cutting

#### Relationships
- A logical boundary with a consistent domain model.
- Communicates via **Service** interfaces and **DomainEvent**s.
- Owns its own data (no cross-context repository access).
- Contains **Aggregate**s, **Service**s, **Repository**s.

#### Invariants
- A Bounded Context's internal model is consistent.
- Cross-context communication is via interfaces or events, not direct repository access.
- Each Aggregate has exactly one owning Bounded Context (single-writer).

#### Examples
1. The Identity Bounded Context owns User, UserCredential, Session.
2. The Mastery Bounded Context owns MasteryScore, Review records.
3. The Assessment Bounded Context owns Attempt, Answer, QuestionInstance.

#### Non-Examples
- A "module" — that is a code-organization concept; a Bounded Context is a domain concept.
- A "microservice" — that is a deployment concept; a Bounded Context is a domain concept (it may become a microservice later).
- A "package" — that is a language concept; a Bounded Context is architectural.

#### Future Extensions
- Bounded Context extraction (promoting a context to a microservice).
- Bounded Context interfaces (formal contracts).
- Bounded Context analytics (which contexts have the most cross-context communication?).

---

### Ubiquitous Language

#### Name
**Ubiquitous Language**

#### Definition
**Ubiquitous Language** is the shared vocabulary used by all team members (engineers, product, design, curriculum, analytics) to describe the domain. It is the language of this glossary. The term comes from Domain-Driven Design: a "ubiquitous" language is one that is used everywhere — in code, in conversations, in documentation, in UI labels.

The Ubiquitous Language is the project's commitment to precision. When a term is in this glossary, it is the only correct term for its concept; synonyms and informal alternatives are forbidden.

#### Business Purpose
The Ubiquitous Language exists to eliminate ambiguity. Without it, team members would use different words for the same concept (or the same word for different concepts), producing confusion; with a Ubiquitous Language, communication is precise.

#### Lifecycle
- **Defined** in this glossary.
- **Evolved** via glossary change requests (adjudicated by the Domain Modeling Lead).
- **Enforced** in code (naming), in documentation (terminology), in UI (labels).

#### Owner
Cross-cutting (Domain Modeling Lead maintains)

#### Relationships
- The shared vocabulary across the project.
- Defined in this glossary.
- Enforced in all artifacts (code, docs, UI).

#### Invariants
- Every term has one definition.
- Every concept has one name.
- Forbidden terms (Section: Forbidden Terminology) never appear.

#### Examples
1. The team says "Attempt" (not "submission" or "answer event") in every conversation.
2. The database table is `attempts` (not `submissions`).
3. The UI label is "Submit Answer" (not "Submit Attempt" — the user-facing term for the action may differ from the domain term, but the underlying concept is Attempt).

#### Non-Examples
- A "glossary" — that is the document; the Ubiquitous Language is the living vocabulary.
- "Domain language" — that is a synonym; the project uses Ubiquitous Language (the DDD term).
- "Jargon" — that is informal; the project uses Ubiquitous Language.

#### Future Extensions
- Ubiquitous Language linters (automated terminology checks in code and docs).
- Ubiquitous Language training (onboarding for new team members).
- Ubiquitous Language analytics (which terms are most used? which are confused?).

---

### Architecture Decision Record

#### Name
**Architecture Decision Record**

#### Definition
An **Architecture Decision Record** (ADR) is a short document capturing one architectural decision: the context, the options considered, the decision, and the consequences. ADRs are numbered, dated, and immutable once merged; supersession is by a new ADR that references the old one. ADRs live in `/docs/adr/`.

ADRs are the project's institutional memory. Without them, the team re-litigates decisions every six months; with ADRs, the rationale is preserved.

#### Business Purpose
The ADR exists to capture architectural rationale. Without it, decisions would be opaque ("why did we choose X?"); with ADRs, the context, options, and trade-offs are documented.

#### Lifecycle
- **Proposed** by an engineer as a draft ADR.
- **Reviewed** by the architecture review group.
- **Merged** (immutable) or **Rejected** (with rationale).
- **Superseded** by a new ADR that references the old one (the old ADR remains for history).

#### Owner
Cross-cutting (architecture review group maintains)

#### Relationships
- A document capturing one architectural decision.
- Numbered, dated, immutable once merged.
- Referenced by code, docs, and other ADRs.

#### Invariants
- ADRs are immutable once merged.
- ADRs are numbered and dated.
- Supersession is by a new ADR, not by editing the old one.

#### Examples
1. ADR-001: "Use FastAPI for the backend." — context, options (FastAPI, Django, Flask), decision (FastAPI), consequences.
2. ADR-002: "Use PostgreSQL for the primary database." — context, options, decision, consequences.
3. ADR-005 supersedes ADR-003: "Switch from JWT to opaque tokens" (a hypothetical future change).

#### Non-Examples
- A "design doc" — that is broader; an ADR is one decision.
- A "RFC" — that is a proposal process; an ADR is the record of a decision.
- A "ticket" — that is for work tracking; an ADR is for architectural memory.

#### Future Extensions
- ADR templates (standardized structure).
- ADR tooling (auto-generation, search, cross-referencing).
- ADR analytics (which ADRs are most referenced?).

---

### Event Bus

#### Name
**Event Bus**

#### Definition
The **Event Bus** is the infrastructure component that dispatches **DomainEvent**s from publishers to subscribers. In the current architecture, the Event Bus is in-process: events are written to an **Outbox** table in the same transaction as the originating write, then dispatched by a background worker to in-process subscribers. Future versions may use a message broker (Kafka, RabbitMQ) for cross-service events.

The Event Bus is the mechanism; the Outbox is the persistence pattern that ensures events are not lost.

#### Business Purpose
The Event Bus exists to decouple publishers from subscribers. Without it, publishers would call subscribers directly; with the Event Bus, publishers raise events and subscribers consume them asynchronously.

#### Lifecycle
- **Initialized** at application startup.
- **Receives** events from the Outbox dispatcher.
- **Routes** events to subscribers.
- **Retries** failed deliveries with exponential backoff.
- **Dead-letters** events that fail repeatedly.

#### Owner
Cross-cutting (infrastructure)

#### Relationships
- Dispatches **DomainEvent**s.
- Fed by the **Outbox**.
- Routes to subscriber handlers (in other Bounded Contexts).
- May be backed by a message broker in future versions.

#### Invariants
- The Event Bus delivers events at-least-once (subscribers must be idempotent).
- The Event Bus does not lose events (the Outbox ensures durability).
- The Event Bus does not block publishers (dispatch is asynchronous).

#### Examples
1. Assessment writes an Attempt + an `AttemptRecorded` event to the Outbox in one transaction; the Event Bus dispatches the event to Mastery and Analytics subscribers.
2. A Mastery subscriber fails to process an event; the Event Bus retries with exponential backoff.
3. An event fails repeatedly; the Event Bus dead-letters it for manual investigation.

#### Non-Examples
- The **Outbox** — that is the persistence pattern; the Event Bus is the dispatch mechanism.
- A "message queue" — that is a broader concept; the project uses Event Bus for domain events.
- A "webhook" — that is for external delivery; the Event Bus is for internal dispatch.

#### Future Extensions
- Event Bus backed by Kafka or RabbitMQ (for cross-service events).
- Event Bus schemas (versioned event contracts).
- Event Bus analytics (which events have the most lag?).

---

### Outbox

#### Name
**Outbox**

#### Definition
The **Outbox** is a database table that stores **DomainEvent**s in the same transaction as the originating write. A background worker (the Outbox Dispatcher) polls the Outbox, dispatches events to the **EventBus**, and marks them as dispatched. The Outbox ensures that events are not lost even if the worker is briefly unavailable.

The Outbox is the persistence pattern; the Event Bus is the dispatch mechanism. Together, they provide reliable event delivery.

#### Business Purpose
The Outbox exists to ensure event durability. Without it, an event published after a write could be lost if the worker crashed; with the Outbox, the event is persisted with the write and dispatched later.

#### Lifecycle
- **Written** in the same transaction as the originating write.
- **Polled** by the Outbox Dispatcher.
- **Dispatched** to the EventBus.
- **Marked** as dispatched (or dead-lettered on repeated failure).

#### Owner
Cross-cutting (infrastructure)

#### Relationships
- A database table storing **DomainEvent**s.
- Fed by Application Services (within their transactions).
- Consumed by the Outbox Dispatcher, which feeds the **EventBus**.

#### Invariants
- Outbox writes are in the same transaction as the originating write.
- Outbox events are dispatched at-least-once.
- Outbox events are retained for audit (configurable retention).

#### Examples
1. An Application Service writes an Attempt and an `AttemptRecorded` Outbox row in one transaction; the Dispatcher dispatches the event to the EventBus.
2. The Dispatcher crashes; on restart, it resumes from the last dispatched event (no events lost).
3. An event fails repeatedly; the Dispatcher dead-letters it for manual investigation.

#### Non-Examples
- The **EventBus** — that dispatches; the Outbox persists.
- A "queue" — that is a broader concept; the Outbox is specifically the transactional event store.
- A "log" — that is for operations; the Outbox is for domain events.

#### Future Extensions
- Outbox compaction (archiving old dispatched events).
- Outbox partitioning (by time or by context).
- Outbox analytics (which events have the most dispatch lag?).

---

### Audit Log

#### Name
**Audit Log**

#### Definition
The **Audit Log** is an append-only record of every privileged action: content publishing, user support actions, admin configuration changes, authentication events, data export and deletion. Each entry records the timestamp, actor (User id, Role), action, target (resource type and id), request metadata (IP, user-agent, correlation id), and outcome (success or failure with reason).

The Audit Log is the project's compliance and forensic backbone. It is retained for at least 2 years and exported daily to cold storage.

#### Business Purpose
The Audit Log exists to provide accountability and forensic capability. Without it, privileged actions would be opaque; with it, every action has a named actor and a timestamp.

#### Lifecycle
- **Written** within the same transaction as the privileged action.
- **Append-only**; no edits, no deletes.
- **Retained** for at least 2 years.
- **Exported** daily to cold storage.

#### Owner
Administration

#### Relationships
- An append-only record of privileged actions.
- Written by all contexts that perform privileged operations.
- Read by Administrators for forensics and compliance.

#### Invariants
- The Audit Log is append-only.
- Audit Log writes are transactional with the privileged action.
- The Audit Log is retained for at least 2 years.

#### Examples
1. An Administrator suspends a User; an Audit Log entry records the action, actor, target, timestamp, and reason.
2. An Instructor publishes a ContentPack; an Audit Log entry records the action, actor, target ContentVersion.
3. A User exports their data (GDPR); an Audit Log entry records the action and the export's delivery.

#### Non-Examples
- A **DomainEvent** — that is for domain communication; the Audit Log is for accountability.
- A "log" — that is for operations; the Audit Log is for privileged actions.
- A "history" — that is a generic concept; the project uses Audit Log.

#### Future Extensions
- Audit Log analytics (which privileged actions are most common?).
- Audit Log alerting (flagging suspicious patterns).
- Audit Log export to SIEM systems.

---

### Feature Flag

#### Name
**Feature Flag**

#### Definition
A **Feature Flag** is a runtime configuration that enables or disables a feature, or selects between variants, without redeployment. Feature Flags are used for gradual rollouts, A/B testing, and emergency kill switches. They are stored in a feature flag service (or a simple Redis-backed store) and evaluated at runtime.

Feature Flags are the mechanism for safely deploying the Mastery Engine v2, the Scheduler variants, and any A/B test. They are a Phase 1 requirement (recommended in Task 001, Section 17.3).

#### Business Purpose
The Feature Flag exists to decouple deployment from release. Without it, every feature would be live on deployment; with Feature Flags, the team can deploy often and release gradually.

#### Lifecycle
- **Created** by an engineer for a new feature.
- **Configured** with targeting rules (percentage, cohort, specific Users).
- **Evaluated** at runtime by application code.
- **Toggled** without redeployment.
- **Retired** when the feature is fully released or removed.

#### Owner
Cross-cutting (infrastructure)

#### Relationships
- A runtime configuration.
- Stored in a feature flag service.
- Evaluated by application code.
- Used for gradual rollouts, A/B testing, kill switches.

#### Invariants
- Feature Flags are evaluated at runtime (no redeployment to toggle).
- Feature Flags have a documented owner and retirement plan.
- Feature Flags are logged (which User saw which variant) for analytics.

#### Examples
1. A `mastery_engine_v2` Feature Flag is enabled for 5% of Learners; the team monitors retention before expanding.
2. A `scheduler_adaptive_queue` Feature Flag is the kill switch for the new Scheduler; it can be disabled instantly if a regression is detected.
3. An `interview_questions_v2` Feature Flag A/B tests two question formats.

#### Non-Examples
- A **Permission** — that is access control; a Feature Flag is feature gating.
- A **Role** — that is a bundle of Permissions; a Feature Flag is a runtime toggle.
- A "config" — that is a broader concept; a Feature Flag is specifically a runtime feature toggle.

#### Future Extensions
- Feature Flag analytics (which flags drive the best outcomes?).
- Feature Flag automation (auto-rollout based on metrics).
- Feature Flag inheritance (Organization-level flags).

---

# Glossary Rules

This closing section codifies the relationships between terms, the terms that are forbidden, and the naming standards that govern all artifacts in the project.

---

## Synonym Table

The following pairs are commonly confused in industry usage but mean different things in this project. The table is the authoritative disambiguation.

| Term A | Term B | Distinction |
|---|---|---|
| **Review** | **Attempt** | A Review is a specific type of Attempt whose purpose is spaced-repetition refresh. All Reviews are Attempts; not all Attempts are Reviews. A first-time Attempt is not a Review; a refresh Attempt is. |
| **Study Session** | **Learning Session** | A Study Session is a single sitting. A Learning Session is a logical episode that may span multiple Study Sessions within a merge window (default 15 minutes). Two Study Sessions 5 minutes apart are one Learning Session. |
| **Memory Score** | **Mastery Score** | Memory Score is the short-term recall probability (decays fast). Mastery Score is the long-term durable understanding (decays slow). Memory Score is one component of Mastery Score. |
| **Concept** | **Learning Objective** | A Concept is the atomic unit of knowledge. A Learning Objective is a verifiable statement of what a Learner should be able to do with a Concept. One Concept has one or more Learning Objectives. |
| **Question Template** | **Question Instance** | A Question Template is the parameterized specification. A Question Instance is the concrete question produced by instantiating a Template with a seed. One Template produces many Instances. |
| **Subject** | **Tenant** | In the current architecture, near-synonyms (each Subject is a Tenant). Tenant is the content-isolation unit; Subject is the curriculum unit. The terms may diverge in future multi-Subject Tenants. |
| **Organization** | **Workspace** | An Organization is a billing unit (a company). A Workspace is a collaboration unit within an Organization (a sub-team). One Organization has many Workspaces. |
| **Role** | **Permission** | A Role is a named bundle of Permissions. A Permission is one atomic capability. Roles are granted to Users; Permissions are granted to Roles. |
| **Subscription** | **Billing Plan** | A Subscription is a User's active billing relationship. A Billing Plan is the offering (Free, Pro). One Billing Plan has many Subscriptions. |
| **Content Pack** | **Content Version** | A Content Pack is a publishable bundle of artifacts. A Content Version is the Subject-wide snapshot produced by publishing one or more Content Packs. |
| **Content Version** | **Template Version** | A Content Version is Subject-wide. A Template Version is per-Template. A Content Version contains many Template Versions. |
| **Algorithm Version** | **Content Version** | An Algorithm Version is a snapshot of the Mastery Engine algorithm. A Content Version is a snapshot of the content. Both are referenced by Attempts. |
| **Scheduler** | **Scheduling Engine** | The Scheduler is the concrete component that produces queues. The Scheduling Engine is the abstract subsystem including the Scheduler and supporting components. Engineers use Scheduler; architects use Scheduling Engine. |
| **Daily Queue** | **Adaptive Queue** | A Daily Queue is day-scoped (what to do today). An Adaptive Queue is session-scoped (what to do right now). The Adaptive Queue typically draws from the Daily Queue. |
| **Review Queue** | **Adaptive Queue** | A Review Queue contains due Concepts (not questions). An Adaptive Queue contains Questions (including review questions plus new material). |
| **Attempt History** | **Learning History** | Attempt History is the raw Attempt stream (machine-readable). Learning History is the aggregate including Study Sessions, Milestones, etc. (human-readable). |
| **Retention** | **Mastery Score** | Retention is the over-time measure (how much mastery is retained). Mastery Score is the point-in-time value. Retention is computed from Mastery Score trajectories. |
| **Mastery Threshold** | **Memory Threshold** | Mastery Threshold is the Mastery Score boundary for state transitions. Memory Threshold is the Memory Score boundary for refresh triggers. They are different thresholds for different scores. |
| **Review Interval** | **Cooldown** | A Review Interval is the duration until the next scheduled Review. A Cooldown is the session-level serve-frequency limit (prevents re-serving the same Concept immediately). |
| **Prerequisite** | **Concept Dependency** | A Prerequisite is one type of Concept Dependency (the strongest type, blocking). Concept Dependency is the umbrella (prerequisite, related, reinforces). |
| **Milestone** | **Badge** | A Milestone is the underlying achievement. A Badge is the visual recognition. A Milestone may trigger a Badge; not all Badges correspond to Milestones. |
| **Graduation** | **Interview Readiness** | Graduation is path-specific completion (a set of Concepts reached Mastered). Interview Readiness is the broader composite estimate. A Learner may Graduate but not be Interview-Ready, or vice versa. |
| **Command** | **Domain Event** | A Command is a request to do something (future-oriented). A Domain Event is a record of something done (past-oriented). Commands trigger Events. |
| **Command** | **Query** | A Command is write-side (mutates state). A Query is read-side (no mutation). CQRS separation. |
| **Aggregate** | **Entity** | An Aggregate is a consistency boundary with a root Entity. An Entity is a domain object with identity. An Aggregate Root is an Entity; not all Entities are Aggregate Roots. |
| **Entity** | **Value Object** | An Entity has identity (compared by id). A Value Object has no identity (compared by value). A User is an Entity; a MasteryScore is a Value Object. |
| **Repository** | **Service** | A Repository persists Aggregates. A Service performs business logic. Repositories are for persistence; Services are for behavior. |
| **Application Service** | **Domain Service** | An Application Service orchestrates use cases (calls Repositories, defines transactions). A Domain Service contains pure business rules (no I/O). |
| **Read Model** | **Write Model** | A Read Model is a read-optimized projection. The Write Model is the source-of-truth Aggregates. Read Models are derived from the Write Model. |
| **DTO** | **Aggregate** | A DTO is the wire representation. An Aggregate is the persisted domain model. DTOs are translated at the boundary. |
| **Priority** | **Urgency** | Priority is the composite ranking signal. Urgency is one factor of Priority (the time-bound component). |
| **Priority** | **Importance** | Priority is the composite. Importance is one factor (the curriculum-criticality component). |
| **Hint** | **Explanation** | A Hint is shown during the Attempt (non-answer-revealing nudge). An Explanation is shown after the Attempt (full pedagogical closure). |
| **Example** | **Worked Example** | An Example is a single illustration. A Worked Example is a step-by-step process narrative. |
| **Coding Exercise** | **Interview Question** | A Coding Exercise is a Template variant with executable code Answers. An Interview Question is a curation artifact (may or may not involve coding). |
| **Concept State** | **Mastery Score** | Concept State is the categorical projection (Unseen, Novice, etc.). Mastery Score is the numeric value. Concept State is derived from Mastery Score. |
| **Weak Concept** | **Strong Concept** | A Weak Concept is below threshold (needs remediation). A Strong Concept is above threshold (does not need attention). They are opposite states. |
| **Authentication** | **Authorization** | Authentication verifies identity (who you are). Authorization decides permissions (what you may do). |
| **User** | **Learner** | A User is the identity root. A Learner is the role a User adopts within a Subject. One User may be a Learner in many Subjects. |
| **Instructor** | **Administrator** | An Instructor authors and reviews content. An Administrator manages the platform. Instructors do not have admin powers; Administrators do not author content. |

---

## Forbidden Terminology

The following words are **forbidden** in all project artifacts (code, schema, UI, documentation, analytics). Each has an approved replacement. Forbidden terms are forbidden because they introduce ambiguity, conflict with the Ubiquitous Language, or carry unwanted connotations.

| Forbidden Term | Approved Replacement | Reason |
|---|---|---|
| **Lesson** | **Concept** or **LearningPath** | "Lesson" implies a course structure the project does not have. Use Concept for the atomic unit; LearningPath for the ordering. |
| **Module** | **ContentPack** or **Subject** | "Module" implies a course module. Use ContentPack for the publishable unit; Subject for the tenant. |
| **Chapter** | **LearningPath stage** or **Concept cluster** | "Chapter" implies a book structure. Use LearningPath stage for the path's segments. |
| **Topic** | **Concept** or **Subject** | "Topic" is ambiguous (could mean Concept or Subject). Use the specific term. |
| **Score** (as a noun for mastery) | **MasteryScore** or **MemoryScore** | "Score" is ambiguous (could mean Success Rate, Mastery Score, or Memory Score). Use the specific term. |
| **AI** (as a runtime decision-maker) | **MasteryEngine** or **Scheduler** | The project forbids runtime AI for learning decisions. Use the deterministic component name. (AI may be mentioned in the authoring-assistance context.) |
| **Knowledge** (as a measurable) | **Mastery** or **MasteryScore** | "Knowledge" is unmeasurable; "mastery" is the project's measurable. Use Mastery. |
| **Progress** (as a single metric) | **MasteryTrend** or **LearningVelocity** | "Progress" is a category, not a metric. Use the specific metric. (The Progress *page* is fine; "the Learner's Progress" as a category is fine; "a Progress score" is forbidden.) |
| **Course** | **Subject** or **LearningPath** | "Course" implies a static course structure. Use Subject for the tenant; LearningPath for the ordering. |
| **Curriculum** (as a countable) | **Subject** or **ContentVersion** | "Curriculum" is fine as a mass noun ("the curriculum"); forbidden as a countable ("a curriculum"). Use Subject for the unit. |
| **Grade** | **MasteryScore** or **ConceptState** | "Grade" implies a course grade. Use MasteryScore for the numeric; ConceptState for the categorical. |
| **Level** (as a Learner attribute) | **ConceptState** or **InterviewReadiness** | "Level" implies a game level. Use ConceptState for per-Concept; InterviewReadiness for composite. |
| **XP** / **Experience Points** | **MasteryScore** or **Milestone** | "XP" implies gamification. Use MasteryScore for the measurement; Milestone for the recognition. |
| **Streak** (as a mastery metric) | (none — streaks are decorative) | Streaks are decorative engagement metrics, never mastery metrics. They may be displayed but never used to evaluate learning. |
| **Smart** (as in "smart scheduler") | **Adaptive** or **Deterministic** | "Smart" is vague. Use Adaptive for the behavior; Deterministic for the property. |
| **Adaptive** (without qualification) | **AdaptiveQueue** or **DifficultyAdjustment** | "Adaptive" alone is ambiguous. Use the specific mechanism. |
| **Personalized** (as a marketing term) | (specific mechanism name) | "Personalized" is marketing fluff. Name the specific mechanism (per-Learner decay, per-Learner thresholds, etc.). |
| **Quiz** | **StudySession** or **Assessment** | "Quiz" implies a static quiz. Use StudySession for the session; Assessment for the scoring act. |
| **Test** (as a content artifact) | **Diagnostic** or **StudySession** (intent: diagnostic) | "Test" implies a course test. Use Diagnostic for the baseline-establishing session. |
| **Exam** | (none — the project has no exams) | The project does not have exams. Mastery is continuous, not exam-based. |
| **Certificate** | **Graduation** or **Badge** | "Certificate" implies a course certificate. Use Graduation for the completion; Badge for the visual recognition. |
| **Teacher** | **Instructor** | "Teacher" implies a classroom role. Use Instructor for the content author/reviewer. |
| **Student** | **Learner** | "Student" implies a classroom role. Use Learner for the User role within a Subject. |
| **Class** | **Cohort** or **Workspace** | "Class" implies a course class. Use Cohort for analytics grouping; Workspace for collaboration. |
| **Cohort** (as a billing unit) | **Organization** | "Cohort" is for analytics grouping; Organization is for billing. Do not conflate. |
| **Recommendation** (without qualification) | **LearningRecommendation** or **Recommendation** (Scheduling) | "Recommendation" alone is ambiguous. Use the specific type. |
| **Queue** (without qualification) | **AdaptiveQueue** or **DailyQueue** or **ReviewQueue** | "Queue" alone is ambiguous. Use the specific type. |
| **Hint** (as a noun for the Explanation) | **Explanation** | "Hint" is during the Attempt; "Explanation" is after. Do not conflate. |
| **Solution** (as a noun for the CorrectAnswer) | **CorrectAnswer** | "Solution" is informal. Use CorrectAnswer. |
| **Correct** (as a noun) | **CorrectAnswer** | "Correct" is an adjective; use the noun form CorrectAnswer. |
| **Wrong** (as a noun) | **Distractor** or **incorrect Answer** | "Wrong" is informal. Use Distractor for the choice; "incorrect Answer" for the Learner's response. |
| **Forget** / **Forgotten** | **Decayed** (ConceptState) | "Forget" implies a binary state; decay is gradual. Use Decayed. |
| **Remember** / **Remembered** | **Retained** or **Strong** (Concept) | "Remember" is informal. Use Retained for the over-time measure; Strong for the per-Concept state. |

---

## Naming Standards

Naming standards ensure that the Ubiquitous Language is reflected consistently across all artifacts. These standards are enforced by linting, code review, and CI checks.

### Database Tables

- **Convention**: `snake_case`, plural.
- **Examples**: `users`, `attempts`, `mastery_scores`, `question_templates`, `content_versions`.
- **Join tables**: `snake_case`, singular+singular (e.g., `concept_dependency`, `user_subject`).
- **Boolean columns**: `is_` or `has_` prefix (e.g., `is_published`, `has_hint`).
- **Timestamp columns**: `_at` suffix (e.g., `created_at`, `published_at`, `last_reviewed_at`).
- **Foreign keys**: `<singular_entity>_id` (e.g., `user_id`, `concept_id`, `subject_id`).

### Python Classes

- **Convention**: `PascalCase`.
- **Examples**: `User`, `Attempt`, `MasteryScore`, `QuestionTemplate`, `ContentVersion`.
- **Use Case Services**: `VerbObject` (e.g., `StartStudySession`, `SubmitAnswer`, `PublishContentPack`).
- **Domain Services**: `NounEngine` or `NounCalculator` (e.g., `MasteryEngine`, `Scheduler`, `QuestionFactory`).
- **Repositories**: `<Aggregate>Repository` (e.g., `AttemptRepository`, `MasteryScoreRepository`).
- **Interfaces**: same name as the concrete class (Python convention; the interface is implicit). Alternatively, prefix with `I` is forbidden (not Pythonic).
- **Exceptions**: `<Problem>Error` (e.g., `ConceptCycleError`, `ConcurrentSessionError`).
- **Enums**: `PascalCase` for the enum, `UPPER_SNAKE_CASE` for values (e.g., `ConceptState.MASTERED`, `SessionIntent.DRILL`).

### TypeScript Interfaces

- **Convention**: `PascalCase`, no `I` prefix.
- **Examples**: `User`, `Attempt`, `MasteryScore`, `QuestionTemplate`.
- **DTOs**: `VerbObjectRequest` / `VerbObjectResponse` (e.g., `StartSessionRequest`, `StartSessionResponse`).
- **Component props**: `ComponentNameProps` (e.g., `QuestionCardProps`, `MasteryGaugeProps`).
- **Enums**: `PascalCase` for the enum, `PascalCase` for values (e.g., `ConceptState.Mastered`, `SessionIntent.Drill` — TypeScript convention differs from Python).

### REST Resources

- **Convention**: `kebab-case`, plural for collections, singular for individual resources.
- **Examples**: `/api/v1/users`, `/api/v1/users/{id}`, `/api/v1/attempts`, `/api/v1/attempts/{id}`.
- **Nested resources**: `/api/v1/subjects/{id}/concepts`, `/api/v1/learners/{id}/mastery-scores`.
- **Actions (non-CRUD)**: `/api/v1/attempts/{id}/submit`, `/api/v1/sessions/{id}/end` (verb as a sub-resource).
- **Versioning**: `/api/v1/...`, `/api/v2/...` for breaking changes.

### Events

- **Convention**: `VerbNounPastTense` (PascalCase).
- **Examples**: `AttemptRecorded`, `MasteryUpdated`, `ContentPublished`, `UserEnrolled`, `Graduated`, `MilestoneAchieved`.
- **Past tense is mandatory**: events record what happened, not what should happen.
- **Versioning**: `AttemptRecordedV1`, `AttemptRecordedV2` for breaking schema changes.

### Queues

- **Convention**: `kebab-case`, descriptive of scope and purpose.
- **Examples**: `adaptive-queue`, `daily-queue`, `review-queue`.
- **Cache keys**: `kebab-case` with colons for hierarchy (e.g., `mastery-score:user-id:concept-id`, `queue:session-id`).
- **Background job queues**: `kebab-case`, descriptive of the job (e.g., `notification-dispatch`, `analytics-projection-rebuild`).

### Enums

- **Python**: `PascalCase` enum class, `UPPER_SNAKE_CASE` values (e.g., `ConceptState.MASTERED`).
- **TypeScript**: `PascalCase` enum, `PascalCase` values (e.g., `ConceptState.Mastered`).
- **Database**: stored as `snake_case` strings (e.g., `mastered`, `developing`); mapped to enums in code.
- **Examples**: `ConceptState` (UNSEEN, NOVICE, DEVELOPING, PROFICIENT, MASTERED, DECAYED), `SessionIntent` (DRILL, DIAGNOSTIC, REVIEW, MIXED), `ContentState` (DRAFT, PUBLISHED, ARCHIVED).

### Files

- **Python**: `snake_case.py` (e.g., `mastery_engine.py`, `attempt_repository.py`).
- **TypeScript (non-component)**: `camelCase.ts` or `kebab-case.ts` (project choice: `kebab-case.ts` for consistency with Next.js conventions; e.g., `api-client.ts`, `mastery-engine.ts`).
- **TypeScript (components)**: `PascalCase.tsx` (e.g., `QuestionCard.tsx`, `MasteryGauge.tsx`).
- **Tests**: `<name>.test.ts` or `test_<name>.py` (e.g., `mastery_engine.test.ts`, `test_mastery_engine.py`).
- **Configuration**: `kebab-case` (e.g., `docker-compose.yml`, `pyproject.toml`).

### Folders

- **Convention**: `kebab-case` for all folders (Python included, for cross-language consistency).
- **Examples**: `domain/`, `application/`, `infrastructure/`, `mastery-engine/`, `question-factory/`.
- **Bounded Context folders**: the context name in `kebab-case` (e.g., `identity/`, `learning/`, `assessment/`, `mastery/`, `content/`, `scheduling/`, `analytics/`, `billing/`, `administration/`).
- **Test folders**: mirror the source structure, with `__tests__/` (TypeScript) or `tests/` (Python) at each level.

### Markdown Documents

- **Convention**: `kebab-case.md`.
- **Examples**: `ubiquitous-language.md`, `architecture-spec.md`, `api-contract.md`, `adr-001-fastapi.md`.
- **ADR numbering**: `adr-NNN-<short-description>.md` (e.g., `adr-001-fastapi.md`, `adr-002-postgresql.md`).
- **Location**: `/docs/` for general docs; `/docs/adr/` for ADRs; `/docs/domain/` for domain docs (including this glossary); `/docs/runbooks/` for runbooks.

---

## Acceptance Criteria Verification

This glossary meets the brief's acceptance criteria:

1. **Every engineer understands the business language.** — Each term has a Definition, Business Purpose, Examples, and Non-Examples, leaving one interpretation.
2. **Every product manager uses identical terminology.** — The Synonym Table and Forbidden Terminology sections eliminate alternatives.
3. **Every designer labels screens consistently.** — UI labels must use the Ubiquitous Language (with limited exceptions for user-facing phrasing, documented per term).
4. **Every database table uses approved names.** — The Naming Standards section specifies table naming; Forbidden Terminology eliminates ambiguous names.
5. **Every API uses the same vocabulary.** — REST Resources naming standards and the Ubiquitous Language govern endpoint names and DTO fields.
6. **Future AI agents can implement features without ambiguity.** — Every term has one definition, one owner, explicit invariants, and explicit Non-Examples. An AI agent reading this glossary can implement any feature using the correct terms.

---

## Document Control

| Field | Value |
|---|---|
| Document Title | Mastery Engine — Ubiquitous Language & Domain Glossary |
| Version | 1.0 |
| Status | Source of Truth |
| Owner | Domain Modeling Lead |
| Approvers | Engineering Lead, Product Lead, Curriculum Lead |
| Supersedes | None |
| Superseded By | None (future versions will reference this one) |
| Last Updated | 2026-07-02 |
| Companion Document | Mastery Engine — Architecture Specification Document (Task 001) |

### Change Log

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-07-02 | Domain Modeling Lead | Initial Ubiquitous Language, covering ~120 terms across 6 domains plus Synonym Table, Forbidden Terminology, and Naming Standards. |

---

*End of Ubiquitous Language & Domain Glossary.*
