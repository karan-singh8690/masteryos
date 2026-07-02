# 03 — Queries

> Every read operation in the Mastery Engine, with consistency, latency, caching, and authorization.
> A Query is read-only. Queries never mutate state.

---

## Query Template

Every query follows this structure:

- **Name** — PascalCase, verb + object (e.g., `GetDashboard`).
- **Purpose** — one sentence.
- **Input** — parameters.
- **Output** — return shape.
- **Consistency Requirements** — strong, read-your-writes, or eventually consistent.
- **Expected Latency** — p50/p99 target.
- **Caching Strategy** — cache layer, TTL, invalidation.
- **Authorization** — who can call it.

---

# Identity Queries

## GetUser
- **Purpose**: Fetch the current user's identity and profile.
- **Input**: `user_id`.
- **Output**: `{user, profile}`.
- **Consistency**: strong (own data).
- **Latency**: p50 < 20ms, p99 < 100ms.
- **Caching**: in-process LRU (request-scoped); Redis 5min.
- **Authorization**: self or admin.

## GetUserSessions
- **Purpose**: List active sessions for the current user.
- **Input**: `user_id`.
- **Output**: `[{session_id, device, ip, last_seen_at, expires_at}]`.
- **Consistency**: strong.
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: none.
- **Authorization**: self or admin.

## SearchUsers (admin)
- **Purpose**: Search users (admin portal).
- **Input**: `query, filters, pagination`.
- **Output**: `[{user_id, email, status, created_at}]`.
- **Consistency**: eventually consistent (read replica).
- **Latency**: p50 < 200ms, p99 < 1s.
- **Caching**: none.
- **Authorization**: admin only.

---

# Learning Queries

## GetDashboard
- **Purpose**: The "what next?" landing page.
- **Input**: `user_id`.
- **Output**: `{recommended_next_action, streak, weak_concepts, subject_switcher}`.
- **Consistency**: read-your-writes (learner's own recent activity).
- **Latency**: p50 < 100ms, p99 < 300ms.
- **Caching**: Redis 60s; invalidated on session end or mastery update.
- **Authorization**: self.

## GetAdaptiveQueue
- **Purpose**: Fetch the current adaptive queue for a session.
- **Input**: `study_session_id`.
- **Output**: `{current_position, questions: [...]}`.
- **Consistency**: strong (session state).
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: Redis (session-scoped); invalidated on regeneration.
- **Authorization**: session owner.

## GetDailyQueue
- **Purpose**: Fetch today's daily queue.
- **Input**: `learner_enrollment_id, date`.
- **Output**: `{questions: [...], completed_count}`.
- **Consistency**: read-your-writes.
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: Redis 24h (or until completed).
- **Authorization**: enrollment owner.

## GetConceptProgress
- **Purpose**: Per-concept mastery for a learner.
- **Input**: `learner_enrollment_id, [concept_ids]`.
- **Output**: `[{concept_id, mastery_score, concept_state, last_attempt_at}]`.
- **Consistency**: read-your-writes.
- **Latency**: p50 < 50ms, p99 < 200ms.
- **Caching**: Redis 60s; invalidated on mastery update.
- **Authorization**: enrollment owner or admin.

## GetWeakConcepts
- **Purpose**: Concepts below mastery threshold.
- **Input**: `learner_enrollment_id, [severity_filter]`.
- **Output**: `[{concept_id, severity, mastery_score}]`.
- **Consistency**: read-your-writes.
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: Redis 60s.
- **Authorization**: enrollment owner.

## GetAttemptHistory
- **Purpose**: Paginated attempt history for a learner.
- **Input**: `learner_enrollment_id, date_range, pagination`.
- **Output**: `[{attempt_id, concept_id, outcome, created_at}]`.
- **Consistency**: strong (append-only).
- **Latency**: p50 < 50ms, p99 < 200ms.
- **Caching**: Redis 5min for recent; none for historical.
- **Authorization**: enrollment owner or admin.

## GetLearningVelocity
- **Purpose**: Concepts reaching Proficient per week.
- **Input**: `learner_enrollment_id, window_weeks`.
- **Output**: `{velocity_per_week, trend}`.
- **Consistency**: eventually consistent (analytics).
- **Latency**: p50 < 100ms, p99 < 500ms.
- **Caching**: Redis 1h (nightly recomputed).
- **Authorization**: enrollment owner.

## GetRetentionAnalytics
- **Purpose**: Retention curves (30/90/180-day).
- **Input**: `[subject_id], cohort_filter`.
- **Output**: `{retention_curves}`.
- **Consistency**: eventually consistent (analytics).
- **Latency**: p50 < 500ms, p99 < 2s.
- **Caching**: Redis 24h (nightly recomputed).
- **Authorization**: admin only.

## GetInterviewReadiness
- **Purpose**: Composite readiness score.
- **Input**: `learner_enrollment_id`.
- **Output**: `{readiness_score, confidence_interval, breakdown}`.
- **Consistency**: read-your-writes.
- **Latency**: p50 < 100ms, p99 < 300ms.
- **Caching**: Redis 5min.
- **Authorization**: enrollment owner.

## GetStudyPlan
- **Purpose**: Projected graduation plan.
- **Input**: `learner_enrollment_id`.
- **Output**: `{projected_graduation_date, weekly_schedule, feasibility}`.
- **Consistency**: read-your-writes.
- **Latency**: p50 < 50ms, p99 < 200ms.
- **Caching**: Redis 1h; invalidated on goal change.
- **Authorization**: enrollment owner.

## GetRecommendations
- **Purpose**: Active recommendations for a learner.
- **Input**: `learner_enrollment_id, [status_filter]`.
- **Output**: `[{recommendation_id, type, payload, score}]`.
- **Consistency**: read-your-writes.
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: Redis 5min.
- **Authorization**: enrollment owner.

## GetSessionAnalytics
- **Purpose**: Per-session metrics (after session end).
- **Input**: `study_session_id`.
- **Output**: `{question_count, success_rate, mastery_delta, duration}`.
- **Consistency**: strong.
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: Redis 1h.
- **Authorization**: session owner.

## GetAchievements
- **Purpose**: Learner's earned achievements.
- **Input**: `learner_enrollment_id`.
- **Output**: `[{achievement_type_code, awarded_at}]`.
- **Consistency**: strong.
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: Redis 1h.
- **Authorization**: enrollment owner.

## GetStreak
- **Purpose**: Current and longest streak.
- **Input**: `learner_enrollment_id`.
- **Output**: `{current_streak, longest_streak, last_study_date}`.
- **Consistency**: strong.
- **Latency**: p50 < 20ms, p99 < 50ms.
- **Caching**: Redis 5min.
- **Authorization**: enrollment owner.

---

# Content Queries

## GetSubject
- **Purpose**: Fetch subject details.
- **Input**: `subject_id or slug`.
- **Output**: `{subject, default_learning_path}`.
- **Consistency**: strong.
- **Latency**: p50 < 20ms, p99 < 50ms.
- **Caching**: Redis 1h; invalidated on publish.
- **Authorization**: any authenticated user.

## GetConcept
- **Purpose**: Fetch concept details (current version).
- **Input**: `concept_id or (subject_slug, concept_slug)`.
- **Output**: `{concept, objectives, misconceptions, dependencies}`.
- **Consistency**: strong.
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: Redis 1h; invalidated on publish.
- **Authorization**: any authenticated user (published) or instructor (draft).

## GetLearningPath
- **Purpose**: Fetch path with ordered concepts.
- **Input**: `learning_path_id`.
- **Output**: `{path, items: [{position, concept}]}`.
- **Consistency**: strong.
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: Redis 1h.
- **Authorization**: any authenticated user.

## SearchConcepts
- **Purpose**: Fuzzy search concepts (admin portal).
- **Input**: `query, subject_id, filters`.
- **Output**: `[{concept_id, name, slug, status}]`.
- **Consistency**: strong.
- **Latency**: p50 < 50ms, p99 < 200ms.
- **Caching**: none.
- **Authorization**: instructor or admin.

## SearchQuestionTemplates
- **Purpose**: Search templates (admin portal).
- **Input**: `query, subject_id, filters`.
- **Output**: `[{template_id, code, question_type, status}]`.
- **Consistency**: strong.
- **Latency**: p50 < 50ms, p99 < 200ms.
- **Caching**: none.
- **Authorization**: instructor or admin.

## GetQuestionTemplate
- **Purpose**: Fetch template details (current version).
- **Input**: `template_id`.
- **Output**: `{template, current_version, objectives, concepts, distractors, hints, explanations}`.
- **Consistency**: strong.
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: Redis 1h.
- **Authorization**: instructor or admin.

## GetContentVersion
- **Purpose**: Fetch a content version snapshot.
- **Input**: `content_version_id`.
- **Output**: `{version, included_artifacts}`.
- **Consistency**: strong.
- **Latency**: p50 < 50ms, p99 < 200ms.
- **Caching**: Redis 24h (immutable).
- **Authorization**: instructor or admin.

## GetContentReviewQueue
- **Purpose**: Packs awaiting review (per stage).
- **Input**: `reviewer_user_id, stage`.
- **Output**: `[{content_pack_id, name, author, submitted_at}]`.
- **Consistency**: strong.
- **Latency**: p50 < 50ms, p99 < 200ms.
- **Caching**: none.
- **Authorization**: instructor or admin.

---

# Mastery Queries

## GetMasteryScore
- **Purpose**: Single concept mastery for a learner.
- **Input**: `learner_enrollment_id, concept_id`.
- **Output**: `{memory_score, durable_mastery_score, combined, concept_state, confidence}`.
- **Consistency**: read-your-writes.
- **Latency**: p50 < 20ms, p99 < 50ms.
- **Caching**: Redis 60s.
- **Authorization**: enrollment owner or admin.

## GetAllMasteryScores
- **Purpose**: All concept mastery for a learner (scheduler use).
- **Input**: `learner_enrollment_id`.
- **Output**: `[{concept_id, scores, state}]`.
- **Consistency**: read-your-writes.
- **Latency**: p50 < 50ms, p99 < 200ms.
- **Caching**: Redis 60s; invalidated on mastery update.
- **Authorization**: enrollment owner or admin (scheduler internal).

## GetDueReviews
- **Purpose**: Reviews due for a learner.
- **Input**: `learner_enrollment_id`.
- **Output**: `[{concept_id, due_at, priority}]`.
- **Consistency**: read-your-writes.
- **Latency**: p50 < 20ms, p99 < 50ms.
- **Caching**: Redis 60s.
- **Authorization**: enrollment owner.

## GetAlgorithmVersion
- **Purpose**: Current or specific algorithm version.
- **Input**: `[version_id]`.
- **Output**: `{version_number, parameters, is_active}`.
- **Consistency**: strong.
- **Latency**: p50 < 10ms, p99 < 30ms.
- **Caching**: Redis 24h (immutable once published).
- **Authorization**: any authenticated user (current); admin (all versions).

## GetLearnerMisconceptions
- **Purpose**: Active misconceptions for a learner.
- **Input**: `learner_enrollment_id`.
- **Output**: `[{misconception_id, severity, detection_count}]`.
- **Consistency**: read-your-writes.
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: Redis 60s.
- **Authorization**: enrollment owner or admin.

---

# Scheduling Queries

## GetSchedulingConfig
- **Purpose**: Active scheduling config for a subject.
- **Input**: `subject_id`.
- **Output**: `{queue_size, cooldown, weights, thresholds}`.
- **Consistency**: strong.
- **Latency**: p50 < 10ms, p99 < 30ms.
- **Caching**: Redis 1h; invalidated on update.
- **Authorization**: any internal (scheduler); admin (portal).

---

# Analytics Queries

## GetConceptStatistics
- **Purpose**: Per-concept aggregate stats (admin).
- **Input**: `concept_id, [content_version_id], date_range`.
- **Output**: `{avg_mastery, success_rate, time_to_mastery, retention}`.
- **Consistency**: eventually consistent (nightly snapshots).
- **Latency**: p50 < 100ms, p99 < 500ms.
- **Caching**: Redis 24h.
- **Authorization**: instructor or admin.

## GetTemplateStatistics
- **Purpose**: Per-template aggregate stats (admin).
- **Input**: `template_version_id, date_range`.
- **Output**: `{success_rate, discrimination, distractor_distribution, hint_usage}`.
- **Consistency**: eventually consistent.
- **Latency**: p50 < 100ms, p99 < 500ms.
- **Caching**: Redis 24h.
- **Authorization**: instructor or admin.

## GetCohortAnalytics
- **Purpose**: Cohort retention and engagement (admin).
- **Input**: `cohort_filter, metrics`.
- **Output**: `{retention_curves, engagement_metrics}`.
- **Consistency**: eventually consistent.
- **Latency**: p50 < 500ms, p99 < 2s.
- **Caching**: Redis 24h.
- **Authorization**: admin only.

## GetLearnerDailySnapshots
- **Purpose**: Mastery-over-time for a learner.
- **Input**: `learner_enrollment_id, concept_id, date_range`.
- **Output**: `[{snapshot_date, mastery_score}]`.
- **Consistency**: eventually consistent.
- **Latency**: p50 < 100ms, p99 < 500ms.
- **Caching**: Redis 1h.
- **Authorization**: enrollment owner or admin.

---

# Billing Queries

## GetSubscription
- **Purpose**: User's active subscription.
- **Input**: `user_id`.
- **Output**: `{plan, status, current_period_end, entitlements}`.
- **Consistency**: strong.
- **Latency**: p50 < 20ms, p99 < 50ms.
- **Caching**: Redis 5min; invalidated on change.
- **Authorization**: self or admin.

## GetBillingPlans
- **Purpose**: Available billing plans.
- **Input**: none.
- **Output**: `[{code, name, price, entitlements}]`.
- **Consistency**: strong.
- **Latency**: p50 < 20ms, p99 < 50ms.
- **Caching**: Redis 1h.
- **Authorization**: any authenticated user.

## GetInvoices
- **Purpose**: User's invoice history.
- **Input**: `user_id, pagination`.
- **Output**: `[{invoice_id, amount, status, issued_at}]`.
- **Consistency**: strong.
- **Latency**: p50 < 50ms, p99 < 200ms.
- **Caching**: none.
- **Authorization**: self or admin.

---

# Administration Queries

## GetNotifications
- **Purpose**: User's notification center.
- **Input**: `user_id, [status_filter], pagination`.
- **Output**: `[{notification_id, type, channel, payload, status, created_at}]`.
- **Consistency**: read-your-writes.
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: none.
- **Authorization**: self.

## GetAuditLogs
- **Purpose**: Audit log search (admin).
- **Input**: `filters (actor, action, target, date_range), pagination`.
- **Output**: `[{log_id, actor, action, target, metadata, created_at}]`.
- **Consistency**: strong (append-only).
- **Latency**: p50 < 100ms, p99 < 500ms.
- **Caching**: none.
- **Authorization**: admin only.

## GetFeatureFlags
- **Purpose**: Feature flags (admin).
- **Input**: `[key_filter]`.
- **Output**: `[{key, targeting_rules, is_active, owner}]`.
- **Consistency**: strong.
- **Latency**: p50 < 20ms, p99 < 50ms.
- **Caching**: Redis 1min (evaluated frequently).
- **Authorization**: admin only.

## EvaluateFeatureFlag
- **Purpose**: Evaluate a flag for a user (internal, called frequently).
- **Input**: `key, user_id, [context]`.
- **Output**: `{enabled, variant, reason}`.
- **Consistency**: eventually consistent (1min propagation).
- **Latency**: p50 < 5ms, p99 < 20ms.
- **Caching**: Redis 1min; in-process 30s.
- **Authorization**: any internal (application).

## GetSystemSettings
- **Purpose**: All or specific system settings.
- **Input**: `[key_filter]`.
- **Output**: `[{key, value, value_type}]`.
- **Consistency**: strong.
- **Latency**: p50 < 10ms, p99 < 30ms.
- **Caching**: Redis 5min; in-process 1min.
- **Authorization**: admin only (most); any internal (some, by key).

## GetGDPRRequests
- **Purpose**: GDPR request queue (admin).
- **Input**: `[status_filter], pagination`.
- **Output**: `[{request_id, user_id, type, status, requested_at, due_at}]`.
- **Consistency**: strong.
- **Latency**: p50 < 50ms, p99 < 200ms.
- **Caching**: none.
- **Authorization**: admin only.

## GetOrganization
- **Purpose**: Organization details and members.
- **Input**: `organization_id`.
- **Output**: `{organization, members}`.
- **Consistency**: strong.
- **Latency**: p50 < 30ms, p99 < 100ms.
- **Caching**: Redis 5min.
- **Authorization**: org admin or platform admin.

---

## Query Count Summary

| Context | Query Count |
|---|---|
| identity | 3 |
| learning | 13 |
| content | 8 |
| mastery | 5 |
| scheduling | 1 |
| analytics | 4 |
| billing | 3 |
| administration | 7 |
| **Total** | **44** |

---

## Consistency Model Summary

| Consistency | Queries | Rationale |
|---|---|---|
| **Strong** | GetUser, GetUserSessions, GetSubject, GetConcept, GetAttemptHistory, GetAlgorithmVersion, GetAuditLogs, GetSubscription, GetInvoices, etc. | Own data or immutable records; reads from primary. |
| **Read-your-writes** | GetDashboard, GetAdaptiveQueue, GetConceptProgress, GetWeakConcepts, GetMasteryScore, GetDueReviews, etc. | Learner's own recent activity; reads from primary or replica with < 1s lag check. |
| **Eventually consistent** | SearchUsers (admin), GetRetentionAnalytics, GetConceptStatistics, GetCohortAnalytics, GetLearnerDailySnapshots | Aggregates or admin searches; reads from read replica or analytics warehouse. |

---

*End of Queries.*
