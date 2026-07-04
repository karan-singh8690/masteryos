# Analytics Guide — Mastery Engine Closed Beta

> **Audience:** Product analysts, data engineers, engineering managers.
> **Scope:** Definitions, formulas, and data sources for every metric surfaced in the Beta Operations Platform.
> **Source of truth:** `app/application/beta_ops/service.py` (the `BetaOpsService` class).
> **Last updated:** 2026-07-03 (Task 026)

---

## 0. Design Principles

1. **Read-only.** All analytics queries are SELECTs. No mutations, no domain events.
2. **No new infrastructure.** Analytics run against the existing PostgreSQL tables — no separate analytics database, no ETL pipeline, no column store.
3. **Explainable.** Every metric has a clear formula. No machine learning, no predictions. If you can't explain a number, you can't trust it.
4. **Fast enough.** All queries are indexed and complete in < 1 second on a 100-user dataset. For larger datasets, materialize via cron.
5. **Backward-compatible.** The analytics layer adds no breaking changes to existing tables. The only new tables are operational metadata (feedback votes, release notes, experiments).

---

## 1. Beta Operations Dashboard Metrics

Endpoint: `GET /api/v1/admin/beta-ops/dashboard`

| Metric | Formula | Source table(s) |
|---|---|---|
| `total_invited` | `COUNT(DISTINCT email) FROM identity.beta_invites` | `beta_invites` |
| `active_beta_users` | `COUNT(id) FROM identity.users WHERE email_verified_at IS NOT NULL AND deleted_at IS NULL` | `users` |
| `daily_active_users` | `COUNT(DISTINCT user_id) FROM analytics.beta_events WHERE user_id IS NOT NULL AND created_at > now() - interval '1 day'` | `beta_events` |
| `weekly_active_users` | Same as DAU but 7-day window | `beta_events` |
| `monthly_active_users` | Same as DAU but 30-day window | `beta_events` |
| `invite_conversion_rate` | `100.0 * COUNT(used_at IS NOT NULL) / COUNT(*)` from `beta_invites` | `beta_invites` |
| `avg_session_duration_minutes` | `AVG(EXTRACT(EPOCH FROM (ended_at - started_at))) / 60` from `study_sessions WHERE status = 'ended'` | `study_sessions` |
| `study_sessions_completed` | `COUNT(*) FROM study_sessions WHERE status = 'ended'` | `study_sessions` |
| `feedback_received` | `COUNT(*) FROM identity.beta_feedback` | `beta_feedback` |
| `bugs_reported` | `COUNT(*) FROM beta_feedback WHERE category = 'bug'` | `beta_feedback` |
| `crash_reports` | `COUNT(*) FROM beta_feedback WHERE rating = 1` (1-star = severe) | `beta_feedback` |
| `nps_score` | `100 * (promoters - detractors) / total` where promoters = rating 5, detractors = rating ≤ 3 | `beta_feedback` |
| `user_satisfaction` | `100 * AVG(rating) / 5.0` | `beta_feedback` |
| `learning_progress_avg` | `100 * AVG(durable_mastery_score)` from `mastery_scores` | `mastery_scores` |
| `retention_day_N` | See §3 below | `beta_events` |

### 1.1 NPS Approximation

True NPS uses a 0-10 scale. Our feedback uses 1-5. The mapping:
- 5 → Promoter
- 4 → Passive
- 1-3 → Detractor

This is an approximation. For a more accurate NPS, add a dedicated NPS survey endpoint in a future task.

---

## 2. Registration Funnel

Endpoint: `GET /api/v1/admin/beta-ops/analytics/funnel?days=30`

The funnel has 9 steps:

| # | Step | Formula |
|---|---|---|
| 1 | `invite_sent` | `COUNT(*) FROM beta_invites WHERE created_at >= cutoff` |
| 2 | `invite_accepted` | `COUNT(*) FROM beta_invites WHERE used_at IS NOT NULL AND created_at >= cutoff` |
| 3 | `registration` | `COUNT(*) FROM users WHERE created_at >= cutoff` |
| 4 | `email_verification` | `COUNT(*) FROM users WHERE created_at >= cutoff AND email_verified_at IS NOT NULL` |
| 5 | `welcome_wizard` | `COUNT(DISTINCT user_id) FROM beta_events WHERE event_type = 'welcome_wizard_completed' AND created_at >= cutoff` |
| 6 | `first_enrollment` | `COUNT(DISTINCT user_id) FROM learner_enrollments WHERE enrolled_at >= cutoff` |
| 7 | `first_study_session` | `COUNT(DISTINCT id) FROM study_sessions WHERE started_at >= cutoff` |
| 8 | `first_completed_question` | `COUNT(DISTINCT learner_enrollment_id) FROM attempts WHERE created_at >= cutoff` |
| 9 | `day_1_retention` | See §3 (Day-1 retention) |

For each step, we compute:
- `count` — the absolute number
- `cumulative_pct` — `count / step_1_count * 100`
- `step_pct` — `count / previous_step_count * 100`
- `median_time_from_previous_minutes` — median time between the previous step's timestamp and this step's timestamp, per user

The `biggest_drop_step` is the step with the largest `100 - step_pct` (i.e., the biggest drop-off from the previous step).

### 2.1 Frontend Event Tracking

For the funnel to work, the frontend must emit these `beta_events`:
- `welcome_wizard_completed` — when the user finishes the 4-step wizard
- `study_session_started` — when a study session begins
- `question_answered` — when a question is submitted
- `recommendation_offered` / `recommendation_accepted` — for recommendation tracking
- `api_response` (with `response_time_ms` in `event_data`) — for API latency tracking

If any of these events are not being emitted, the corresponding funnel step will show 0. Check the frontend event tracking code (`frontend/components/beta/feedback-button.tsx` and related) if a step is unexpectedly 0.

---

## 3. Retention

Endpoint: `GET /api/v1/admin/beta-ops/analytics/retention?weeks=8`

### 3.1 Day-N Retention (used in dashboard)

For a given `N`:
1. Define the **cohort window**: users whose **first** `beta_events` row was created between `now - (N+1) days` and `now - N days`.
2. Define the **retention window**: the last 24 hours (`now - 1 day` to `now`).
3. `retention_day_N = 100 * (users in cohort who have an event in the retention window) / (cohort size)`

If the cohort is empty (no users whose first event was exactly N days ago), retention is 0.

### 3.2 Weekly Cohort Retention

For each of the last 8 weeks:
1. Define the **cohort week**: users whose first event was in that week (Monday-Sunday).
2. For each subsequent week (0 through 4), count how many cohort users had an event in that week.

The result is a matrix:
```
              Week 0  Week 1  Week 2  Week 3  Week 4
Cohort W-7    20      12      8       6       5
Cohort W-6    18      10      7       5       —
Cohort W-5    22      14      9       —       —
...
```

Week 0 is always equal to the cohort size (by definition, every user was active in their first week).

---

## 4. Learning Effectiveness Metrics

Endpoint: `GET /api/v1/admin/beta-ops/learning`

| Metric | Formula | Source |
|---|---|---|
| `mastery_growth_avg` | `AVG(max(durable_mastery_score) - min(durable_mastery_score))` per enrollment, averaged across all enrollments | `mastery_scores` |
| `time_to_mastery_hours` | `AVG(first_mastery_timestamp - enrolled_at)` where `concept_state IN ('proficient', 'mastered')` | `mastery_scores` + `learner_enrollments` |
| `review_effectiveness` | `100 * COUNT(last_review_outcome = 'correct') / COUNT(last_review_outcome IS NOT NULL)` | `mastery.reviews` |
| `question_accuracy` | `100 * COUNT(scoring_outcome = 'correct') / COUNT(*)` | `assessment.attempts` |
| `average_confidence` | `AVG(confidence_interval)` from `mastery_scores` (lower = more confident) | `mastery_scores` |
| `hint_usage_rate` | `100 * COUNT(hint_used = true) / COUNT(*)` | `assessment.attempts` |
| `recommendation_acceptance` | `100 * COUNT(recommendation_accepted) / COUNT(recommendation_offered)` from beta_events | `beta_events` |
| `adaptive_queue_quality` | `100 * COUNT(status = 'answered') / COUNT(*)` from question_instances | `question_instances` |

### 4.1 Weak / Strong Concepts

- **Weak concepts**: Top 10 concepts with the lowest `AVG(durable_mastery_score)` across all enrollments.
- **Strong concepts**: Top 10 concepts with the highest `AVG(durable_mastery_score)`.

Use these to identify:
- Content that needs improvement (weak concepts)
- Content that's working well (strong concepts) — use as a model for new content

### 4.2 Interview Readiness Trend

For each of the last 8 weeks:
- `avg_readiness = 100 * AVG(durable_mastery_score)` where `last_updated_at` falls in that week

This is a leading indicator of overall platform effectiveness. If `avg_readiness` is trending up over 8 weeks, the platform is working.

---

## 5. Feedback Platform Metrics

Endpoint: `GET /api/v1/admin/beta-ops/feedback`

| Metric | Formula |
|---|---|
| `total` | `COUNT(*) FROM beta_feedback` (limited by `limit` param) |
| `by_category` | Group by `category`, count |
| `by_priority` | Group by `beta_feedback_meta.priority`, count |
| `by_status` | Group by `status`, count |
| `avg_vote_score` | `AVG(SUM(vote))` per feedback item |
| `top_voted` | Top 10 items by `vote_score` |
| `potential_duplicates` | Pairs of items with same `category` AND >60% token overlap in `comment` |

### 5.1 Duplicate Detection Algorithm

The duplicate detection is a simple token-overlap heuristic:
1. Tokenize each comment (split on whitespace, lowercase, strip punctuation, drop tokens of length ≤ 2)
2. For each pair of items in the same category, compute the Jaccard similarity: `|A ∩ B| / |A ∪ B|`
3. If similarity > 0.6, flag as a potential duplicate

This is intentionally simple. For a production system, consider:
- TF-IDF cosine similarity
- Sentence embeddings (e.g., `sentence-transformers`)
- LLM-based semantic similarity

The simple heuristic catches obvious duplicates without any ML dependencies.

---

## 6. User Success Signals

Endpoint: `GET /api/v1/admin/beta-ops/success`

See `user-success.md` for the detailed signal definitions and recommendations.

---

## 7. Instructor Analytics

Endpoint: `GET /api/v1/admin/beta-ops/instructor`

| Metric | Formula |
|---|---|
| `content_quality.feedback_count` | `COUNT(*) FROM beta_feedback WHERE category = 'content'` |
| `content_quality.avg_rating` | `AVG(rating) FROM beta_feedback WHERE category = 'content'` |
| `concept_coverage.subjects[].coverage_pct` | `100 * published_concepts / total_concepts` per subject |
| `question_quality.avg_accuracy_across_templates` | Mean of per-template accuracy |
| `template_usage[].accuracy` | `100 * correct / attempts` per template_version_id |
| `difficulty_balance` | Group by `concept_state`, count |
| `poor_performing_concepts` | Concepts with `AVG(durable_mastery_score) < 0.4`, sorted ascending, limit 20 |
| `frequently_missed_questions` | Templates with `attempts >= 5 AND accuracy < 50%`, sorted by accuracy, limit 20 |
| `misconceptions` | Group by `misconception_id` from attempts where it's not null, count, limit 20 |
| `explanation_usefulness` | Same as content_quality but filtered to comments containing "explanation" |

---

## 8. Operational Health Metrics

Endpoint: `GET /api/v1/admin/beta-ops/operations`

| Metric | Formula |
|---|---|
| `platform_health.status` | `healthy` if outbox_pending < 100 AND dead_letters < 10 AND active_workers >= 1; else `degraded` |
| `worker_health.running` | `COUNT(*) FROM worker_heartbeats WHERE status = 'running' AND last_seen_at > now() - 60s` |
| `background_jobs.failing` | `COUNT(*) FROM scheduled_jobs WHERE consecutive_failures > 0` |
| `queue_status` | Group by `status` from `outbox_events`, count |
| `email_delivery` | Group by `status` from `email_delivery_log` where `created_at > now() - 7 days`, count |
| `database_health.connections` | `SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()` |
| `database_health.size_mb` | `pg_database_size(current_database()) / 1024 / 1024` |
| `api_latency.avg_ms_24h` | `AVG(event_data->>'response_time_ms') FROM beta_events WHERE event_type = 'api_response' AND created_at > now() - 1 day` |
| `ai_usage.events_7d` | `COUNT(*) FROM beta_events WHERE event_type IN ('ai_explanation_requested', 'ai_coach_consulted', 'ai_recommendation_shown') AND created_at > now() - 7 days` |
| `cost_metrics.ai_cost_estimate_usd_7d` | `ai_usage.events_7d * 0.0002` (rough estimate) |
| `cost_metrics.email_cost_estimate_usd_7d` | `total_emails_7d * 0.0001` |

### 8.1 Cost Estimate Caveats

Cost metrics are **rough estimates** based on assumed per-call costs:
- AI: $0.0002 per call (Ollama local = free; OpenAI gpt-4o-mini ≈ $0.00015)
- Email: $0.0001 per email (Postmark = $0.00125; SES = $0.0001)

For accurate numbers, check the actual provider billing dashboard.

---

## 9. Release Management Metrics

Endpoint: `GET /api/v1/admin/beta-ops/releases`

| Metric | Formula |
|---|---|
| `current_version` | The version of the most recently published release note |
| `feature_freeze_active` | `true` if any release note has `feature_freeze = true` |
| `version_timeline` | List of all releases with version, type, published_at, current_stage |
| `rollback_history` | Releases where the latest stage is `rolled_back` |

---

## 10. Beta Reports

Endpoint: `GET /api/v1/admin/beta-ops/reports/{period}` where period is `daily`, `weekly`, or `monthly`

Reports aggregate the metrics from sections 1-9 over the specified time window:
- `daily` → last 24 hours
- `weekly` → last 7 days
- `monthly` → last 30 days

Each report includes:
- `growth` — new users, total users, new invites, used invites, conversion rate
- `retention` — Day-1, Day-7, Day-30
- `learning_outcomes` — sessions completed, questions answered/correct, accuracy
- `feedback_summary` — total, open, avg rating
- `top_bugs` — top 10 bugs by created_at
- `top_requests` — top 10 feature requests by created_at
- `system_health` — platform status, outbox, dead letters, workers

---

## 11. Experiment Metrics

Endpoint: `GET /api/v1/admin/beta-ops/experiments`

For each experiment:
- `sample_size_a` / `sample_size_b` — count of `experiment_assignments` per variant
- `is_statistically_significant` — result of the two-proportion z-test (see §11.1)

### 11.1 Statistical Significance

We use a **two-proportion z-test** to determine if the difference between variant A and variant B is statistically significant.

Given:
- `n_a`, `n_b` — sample sizes
- `c_a`, `c_b` — conversion counts
- `p_a = c_a / n_a`, `p_b = c_b / n_b` — conversion rates
- `p_pooled = (c_a + c_b) / (n_a + n_b)` — pooled proportion

The z-score is:
```
z = (p_b - p_a) / sqrt(p_pooled * (1 - p_pooled) * (1/n_a + 1/n_b))
```

The two-tailed p-value is:
```
p = 2 * (1 - Φ(|z|))
```

where `Φ` is the standard normal CDF, approximated via `math.erf`.

The result is **statistically significant** if `p < 0.05`.

### 11.2 Sample Size Requirement

An experiment is only evaluated for significance if both variants have at least `min_sample_size` samples (default: 100). This prevents false positives from small-sample noise.

### 11.3 Recommendation Logic

- If `is_statistically_significant = false`: "Do not declare a winner yet — results are not statistically significant."
- If `is_statistically_significant = true` AND `p_b > p_a`: "Declare variant_b the winner — conversion rate {p_b} vs {p_a} (p={p_value})."
- If `is_statistically_significant = true` AND `p_a > p_b`: "Declare variant_a the winner — conversion rate {p_a} vs {p_b} (p={p_value})."
- If `p_a == p_b`: "No clear winner — conversion rates are equal."

---

## 12. Query Performance

All analytics queries are designed to complete in < 1 second on a 100-user dataset. The key indexes that make this possible:

| Table | Index | Used by |
|---|---|---|
| `beta_events` | `idx_beta_events_type_created` | Funnel, retention, AI usage |
| `beta_events` | `idx_beta_events_user` | User success signals |
| `beta_events` | `idx_beta_events_created` | Time-window queries |
| `beta_feedback` | `idx_beta_feedback_status` | Feedback platform |
| `beta_feedback` | `idx_beta_feedback_category` | Instructor analytics |
| `attempts` | `idx_attempts_enrollment_created` | Learning effectiveness |
| `mastery_scores` | (unique on enrollment + concept) | Mastery growth, weak/strong concepts |
| `learner_enrollments` | `idx_enrollments_user_subject` | User success |
| `study_sessions` | `idx_study_sessions_enrollment_active` | Session metrics |

If a query becomes slow at scale (> 1000 users), consider:
1. Materializing the dashboard metrics in a `beta_ops_snapshot` table via a cron job
2. Adding a read replica for analytics queries
3. Migrating to a columnar store (e.g., TimescaleDB) for time-series data

---

## 13. Data Freshness

| Metric | Freshness | Reason |
|---|---|---|
| Dashboard KPIs | Real-time (cached 60s) | Direct SELECT |
| Funnel | Real-time | Direct SELECT |
| Retention | Real-time | Direct SELECT |
| Learning effectiveness | Real-time | Direct SELECT |
| Feedback platform | Real-time | Direct SELECT |
| User success signals | Real-time | Direct SELECT |
| Operational health | Real-time (cached 30s) | Direct SELECT |
| Beta reports | Generated on demand | Computed at request time |

There is no overnight batch job. All numbers are live.

---

**Next:** Read `experimentation.md` for the experiment platform guide, or `operations-handbook.md` for operational runbooks.
