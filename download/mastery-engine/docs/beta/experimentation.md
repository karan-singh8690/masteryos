# Experimentation Guide — Mastery Engine Closed Beta

> **Audience:** Product managers, engineers running A/B tests.
> **Scope:** How to design, run, and analyze experiments on the Mastery Engine platform.
> **Source of truth:** `/admin/beta-ops/experiments` page; `GET/POST /api/v1/admin/beta-ops/experiments/*` APIs.
> **Last updated:** 2026-07-03 (Task 026)

---

## 0. Why Experiment?

The Closed Beta is the first time real users interact with the platform. Many design decisions were made on assumptions — now we can validate them.

Experiments let us:
1. **Measure causal impact** — did variant B actually improve the metric, or was it noise?
2. **Avoid HiPPO decisions** (Highest Paid Person's Opinion) — let the data decide.
3. **De-risk changes** — roll out to 10% first, measure, then expand.

---

## 1. Supported Experiment Types

| Type | Use case | Example |
|---|---|---|
| `ab` | Generic A/B test | Button color, copy text |
| `feature_rollout` | Gradual feature release | New recommendation algorithm to 10% → 50% → 100% |
| `recommendation` | Compare recommendation strategies | Rule engine vs AI-enhanced |
| `queue` | Compare adaptive queue algorithms | Difficulty-based vs mastery-based ordering |
| `explanation` | Compare explanation generators | Template-based vs AI-generated |
| `ai_vs_rule` | AI vs deterministic engine | AI explanations vs rule-based explanations |

---

## 2. The Experiment Lifecycle

```
[draft] → [running] → [completed]
              ↓
          [stopped]  (manual stop, no winner declared)
```

1. **Draft**: Experiment is configured but not assigning users. Edit any field.
2. **Running**: Users are being assigned to variants. `started_at` is set.
3. **Completed**: Experiment reached significance + min sample size, winner declared. `ended_at` is set.
4. **Stopped**: Manually stopped before completion. `ended_at` is set, but `winner` may be null.

---

## 3. Designing an Experiment

### 3.1 Define the Hypothesis

Every experiment starts with a falsifiable hypothesis:

> **Hypothesis**: Showing AI-generated explanations after incorrect answers will increase Day-1 retention by at least 5 percentage points.

### 3.2 Choose the Metric

- **Primary metric** (`target_metric`): The one number you're trying to move. e.g., `day_1_retention`.
- **Guardrail metrics**: Metrics you don't want to harm. e.g., `question_accuracy`, `page_load_time`. (Track these manually — the experiment platform doesn't enforce guardrails yet.)

### 3.3 Calculate Sample Size

Use an online sample size calculator (e.g., [Evan Miller's](https://www.evanmiller.org/ab-testing/sample-size.html)).

For a typical experiment:
- Baseline conversion rate: 30%
- Minimum detectable effect: 5 percentage points
- Significance level (α): 0.05
- Statistical power: 80%

→ Required sample size per variant: ~1,000 users

**With only 20-100 beta users, you will NOT reach significance for most experiments.** This is a known limitation. Use the experiment framework to:
1. Roll out features gradually (feature_rollout type)
2. Collect data for later analysis (when you have more users)
3. Run qualitative experiments (survey users about their experience)

### 3.4 Set `min_sample_size`

Default is 100. Set this to the sample size from §3.3. The significance check will return `false` until both variants reach this threshold.

### 3.5 Choose Variants

- `variant_a` — the control (current behavior)
- `variant_b` — the treatment (new behavior)

Variant names should be descriptive: `rule_engine` vs `ai_enhanced`, not `a` vs `b`.

---

## 4. Creating an Experiment

### 4.1 Via the UI

1. Go to `/admin/beta-ops/experiments`
2. Click "Create Experiment"
3. Fill in:
   - **ID**: A stable identifier (e.g., `ai_explanations_v1`). Cannot be changed.
   - **Name**: Human-readable name
   - **Description**: What you're testing and why
   - **Experiment Type**: One of the 6 types
   - **Variant A**: Control variant name
   - **Variant B**: Treatment variant name
   - **Rollout Percentage**: % of users assigned to variant B (default 50)
   - **Target Metric**: The primary metric you're measuring
   - **Min Sample Size**: Minimum samples per variant for significance
4. Click "Create" — the experiment is in `draft` status.

### 4.2 Via the API

```bash
curl -X POST https://app.masteryengine.com/api/v1/admin/beta-ops/experiments \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "ai_explanations_v1",
    "name": "AI Explanations vs Rule-Based",
    "description": "Test whether AI-generated explanations after incorrect answers improve Day-1 retention",
    "experiment_type": "ai_vs_rule",
    "variant_a": "rule_based",
    "variant_b": "ai_generated",
    "rollout_percentage": 50,
    "target_metric": "day_1_retention",
    "min_sample_size": 100,
    "metadata": {
      "hypothesis": "AI explanations improve retention by 5pp",
      "guardrail_metrics": ["question_accuracy", "page_load_time"]
    }
  }'
```

### 4.3 Start the Experiment

Via UI: Click "Start" on the experiment row.
Via API:
```bash
curl -X PATCH https://app.masteryengine.com/api/v1/admin/beta-ops/experiments/ai_explanations_v1 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"status": "running"}'
```

---

## 5. Assigning Users to Variants

### 5.1 Automatic Assignment

When a user first encounters the experiment (via the application code calling `BetaOpsService.assign_variant(session, experiment_id, user_id)`), they are **sticky-bucketed** to a variant:

1. Check if the user already has an assignment → if yes, return it.
2. Otherwise, compute a deterministic hash: `SHA-256(experiment_id + user_id) mod 100`.
3. If the hash < `rollout_percentage`, assign to `variant_b`; else assign to `variant_a`.
4. Persist the assignment in `analytics.experiment_assignments`.

The hash is deterministic — the same user always gets the same variant (until the experiment ends or the rollout % changes).

### 5.2 Manual Assignment (Admin)

Admins can force-assign a specific user to an experiment:

```bash
curl -X POST https://app.masteryengine.com/api/v1/admin/beta-ops/experiments/ai_explanations_v1/assign \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "<uuid>"}'
```

This is useful for testing — assign yourself to both variants to verify the UI renders correctly.

### 5.3 Reading the Assignment in Application Code

The application code (e.g., the recommendation engine) should call:

```python
from app.application.beta_ops import get_beta_ops_service

async def get_recommendation(session, user_id):
    service = get_beta_ops_service()
    variant = await service.assign_variant(session, "recommendation_v1", user_id)
    if variant == "ai_enhanced":
        return await ai_recommendation(user_id)
    else:
        return rule_based_recommendation(user_id)
```

---

## 6. Recording Results

### 6.1 Snapshot Results Periodically

As the experiment runs, record result snapshots (e.g., daily):

```bash
curl -X POST https://app.masteryengine.com/api/v1/admin/beta-ops/experiments/ai_explanations_v1/results \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "variant": "rule_based",
    "sample_size": 45,
    "conversion_count": 14,
    "metric_value": 0.311,
    "metric_std_error": 0.069,
    "metadata": {"snapshot_date": "2026-07-03"}
  }'
```

Repeat for `variant_b`. The latest snapshot per variant is used for significance calculation.

### 6.2 Automate Snapshot Recording

For production use, automate this via a scheduled job that runs daily:

```python
# In the worker scheduler
async def snapshot_experiment_results(session):
    for exp in await service.list_experiments(session):
        if exp.status != "running":
            continue
        # Compute conversions per variant from beta_events
        for variant in [exp.variant_a, exp.variant_b]:
            count_a = await compute_conversion_count(session, exp, variant)
            sample = await compute_sample_size(session, exp, variant)
            await record_result(session, exp.id, variant, sample, count_a)
```

This is a future enhancement — for the Closed Beta, record snapshots manually or via a cron script.

---

## 7. Analyzing Results

### 7.1 View Results

1. Go to `/admin/beta-ops/experiments`
2. Click on the experiment row
3. The detail dialog shows:
   - Sample sizes per variant
   - Conversion rates per variant
   - Statistical significance (p-value, z-score)
   - Lift (relative improvement of B over A)
   - Recommendation (declare winner / keep waiting)

### 7.2 Significance Calculation

The platform uses a **two-proportion z-test** (see `analytics-guide.md` §11.1 for the formula).

The result is significant if `p_value < 0.05`.

### 7.3 Interpreting the Recommendation

| Recommendation | Meaning |
|---|---|
| "Do not declare a winner yet" | Sample size too small OR p ≥ 0.05. Keep waiting. |
| "Declare variant_b the winner" | p < 0.05 AND variant_b conversion > variant_a. Ship it. |
| "Declare variant_a the winner" | p < 0.05 AND variant_a conversion > variant_b. Don't ship the change. |
| "No clear winner" | Conversion rates are equal. Either variant is fine. |

### 7.4 Declaring a Winner

Once the recommendation says to declare a winner:

1. Via UI: Click "Stop" on the experiment row, then update the `winner` field.
2. Via API:
   ```bash
   curl -X PATCH https://app.masteryengine.com/api/v1/admin/beta-ops/experiments/ai_explanations_v1 \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H 'Content-Type: application/json' \
     -d '{"status": "completed", "winner": "ai_generated"}'
   ```

The application code should then check `exp.winner` and only serve the winning variant.

---

## 8. Experiment Types in Detail

### 8.1 `feature_rollout`

Use this to gradually roll out a new feature:
- Start with `rollout_percentage = 10`
- Monitor for bugs and feedback
- If stable, increase to 50, then 100
- At 100%, the feature is fully rolled out — you can mark the experiment `completed` with `winner = variant_b`

### 8.2 `recommendation`

Compare two recommendation strategies. The `target_metric` is usually `recommendation_acceptance` (from `beta_events`).

### 8.3 `queue`

Compare two adaptive queue algorithms. The `target_metric` is usually `adaptive_queue_quality` (the % of served questions that were answered, not abandoned).

### 8.4 `explanation`

Compare two explanation generators. The `target_metric` is usually `explanation_usefulness` (from feedback ratings on explanations).

### 8.5 `ai_vs_rule`

Special case of `ab` for comparing the AI provider against the deterministic rule engine. The `target_metric` depends on the feature being tested (e.g., `day_1_retention`, `question_accuracy`).

---

## 9. Common Pitfalls

### 9.1 Peeking
Don't check the results every hour and stop the experiment as soon as p < 0.05. This inflates false positives. Wait until you reach `min_sample_size`.

### 9.2 Multiple Comparisons
If you track 10 metrics, one will appear significant by chance (at α = 0.05). Pre-declare your primary metric and guardrails before starting.

### 9.3 Changing Rollout Mid-Experiment
If you change `rollout_percentage` from 50 to 80 mid-experiment, users who were in variant A may switch to variant B. This contaminates the data. If you need to change rollout, stop the experiment and start a new one.

### 9.4 Not Sticky-Bucketing
If users see variant A on Monday and variant B on Tuesday, they'll be confused and your data will be noisy. The platform enforces sticky bucketing — don't bypass it.

### 9.5 Survivorship Bias
If you only look at users who completed the experiment, you miss those who churned mid-experiment. Always use intent-to-treat analysis: once a user is assigned, they're counted in that variant regardless of what they did next.

---

## 10. Sample Experiment: AI vs Rule-Based Explanations

### 10.1 Setup
- **ID**: `ai_explanations_v1`
- **Type**: `ai_vs_rule`
- **Variant A**: `rule_based` (current behavior — template explanations)
- **Variant B**: `ai_generated` (new behavior — Ollama/OpenAI explanations)
- **Rollout**: 50%
- **Target metric**: `day_1_retention`
- **Min sample size**: 100 (we won't reach this with 20 users, but we'll collect data)

### 10.2 Hypothesis
AI-generated explanations are more conversational and contextual, leading to better understanding and higher Day-1 retention.

### 10.3 Guardrail Metrics
- `question_accuracy` — AI explanations shouldn't make users worse at answering
- `ai_cost` — track the cost of AI calls
- `page_load_time` — AI generation adds latency; ensure it doesn't exceed 3s

### 10.4 Duration
With 20 users at 50/50 split, we'll have ~10 users per variant. We won't reach significance, so the experiment will run for the full beta period (6 weeks) to collect as much data as possible.

### 10.5 Decision Criteria
- If `day_1_retention` is **directionally** better for `ai_generated` AND no guardrail metric is harmed → enable AI for all users in Public Beta.
- If `day_1_retention` is directionally worse → keep rule-based for Public Beta, iterate on the AI prompt, and re-test.
- If results are inconclusive → default to rule-based (simpler, cheaper, deterministic).

---

## 11. API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/admin/beta-ops/experiments` | List all experiments |
| POST | `/api/v1/admin/beta-ops/experiments` | Create an experiment |
| GET | `/api/v1/admin/beta-ops/experiments/{id}` | Get results + significance |
| PATCH | `/api/v1/admin/beta-ops/experiments/{id}` | Update status, winner, etc. |
| POST | `/api/v1/admin/beta-ops/experiments/{id}/assign` | Assign a user to a variant |
| POST | `/api/v1/admin/beta-ops/experiments/{id}/results` | Record a result snapshot |

All endpoints require `ROLE_ADMINISTRATOR` or `ROLE_SYSTEM_ADMIN`.

---

**Next:** Read `release-management.md` for the release process, or `operations-handbook.md` for operational runbooks.
