# User Success Center — Mastery Engine Closed Beta

> **Audience:** Customer success, product managers, support engineers.
> **Scope:** Identifying at-risk users and taking action to retain them.
> **Source of truth:** `/admin/beta-ops/success` page; `GET /api/v1/admin/beta-ops/success` API.
> **Last updated:** 2026-07-03 (Task 026)

---

## 0. What Is the User Success Center?

The User Success Center is a **proactive** retention tool. Instead of waiting for users to cancel or churn, it surfaces 8 distinct signals that indicate a user is at risk of disengaging — and provides a specific, actionable recommendation for each.

The goal: **no beta user quietly drifts away**. If a user is going to churn, we want to know why, and we want to have tried to save them first.

---

## 1. The 8 Signals

| # | Signal | Severity | What it means | Recommendation |
|---|---|---|---|---|
| 1 | `inactive` | high/medium | No activity in 14+ days | Send a re-engagement email highlighting new content or features. |
| 2 | `at_risk` | medium | Was active 1-7 days ago but not in the last 24h | Check if they hit a roadblock; offer a personalized nudge. |
| 3 | `incomplete_onboarding` | high | Registered >3 days ago but hasn't completed onboarding | Send onboarding tips and a direct link to the welcome wizard. |
| 4 | `stuck_in_learning` | medium | Enrolled but no learning activity in 7+ days | Recommend an easier concept or a review session. |
| 5 | `no_study_7_days` | medium | No study session in the last 7 days | Send a 'time to study' reminder with a one-click resume link. |
| 6 | `failed_registration` | (placeholder) | Registration attempt failed (e.g., invalid invite token) | Manually verify and re-invite. |
| 7 | `email_verification_pending` | medium | Registered but hasn't verified email within 7 days | Send a reminder email with a verification link. |
| 8 | `recommendation_ignored` | low | Received a recommendation >7 days ago but didn't accept it | Surface a different recommendation or simplify the call-to-action. |

---

## 2. How Signals Are Computed

Each signal is computed by the `BetaOpsService.get_user_success_report()` method. The logic is intentionally simple and explainable — no machine learning, no predictive models. The goal is to give the operations team a clear, defensible list of users to contact.

### 2.1 `inactive`
- **Query:** Users with `email_verified_at IS NOT NULL` AND `deleted_at IS NULL` whose most recent `beta_events` row is older than 14 days (or has no events at all).
- **Severity:** `high` if no events since registration; `medium` if last event was 14+ days ago.

### 2.2 `at_risk`
- **Query:** Users whose most recent event was 1-7 days ago (i.e., they were active last week but not today).
- **Severity:** `medium`. This is the "golden window" — a nudge now is most effective.

### 2.3 `incomplete_onboarding`
- **Query:** Users who registered >3 days ago AND have no `learner_enrollments` row OR have one with `status = 'pending_onboarding'`.
- **Severity:** `high`. Onboarding is the single biggest predictor of retention.

### 2.4 `stuck_in_learning`
- **Query:** Users with an active enrollment whose `last_active_at` is >7 days ago.
- **Severity:** `medium`. They started but stalled — usually a difficulty spike or a confusing concept.

### 2.5 `no_study_7_days`
- **Query:** Users whose most recent `study_sessions` row is >7 days old (or who have no study sessions at all).
- **Severity:** `medium`. Distinct from `stuck_in_learning` because it doesn't require an enrollment.

### 2.6 `failed_registration`
- **Status:** Placeholder — currently an empty list. The backend tracks failed registrations via the audit log (`identity.auth_audit_logs` with `action = 'LOGIN_FAILURE'`), but the signal is not yet wired. Track as a future enhancement.

### 2.7 `email_verification_pending`
- **Query:** Users who registered in the last 7 days AND `email_verified_at IS NULL`.
- **Severity:** `medium`. Email verification is required for password reset and email-based notifications — unverified users are locked out of key flows.

### 2.8 `recommendation_ignored`
- **Query:** Users who have a `beta_events` row with `event_type = 'recommendation_offered'` older than 7 days, but no `recommendation_accepted` event.
- **Severity:** `low`. This is a product-design signal, not a user failure.

---

## 3. Triage Workflow

### 3.1 Daily Triage (10 minutes)

1. Open `/admin/beta-ops/success`
2. Review the 8 summary counts at the top
3. For each section with count > 0:
   - Sort by severity (high first)
   - For each user, read the recommendation
   - Take the recommended action (see §4 below)
4. Log the action taken in the user's feedback thread (if applicable) or in a spreadsheet

### 3.2 Weekly Triage (30 minutes)

1. Compare this week's signal counts to last week's
2. Identify trends:
   - Is `incomplete_onboarding` growing? → Onboarding UX issue
   - Is `stuck_in_learning` growing? → Content difficulty issue
   - Is `recommendation_ignored` growing? → Recommendation quality issue
3. For each trend, file a product task with the underlying signal data

---

## 4. Recommended Actions Per Signal

### 4.1 For `inactive` users
Send a personalized re-engagement email:

> Subject: We miss you at Mastery Engine
>
> Hi {name},
>
> It's been a while since you last logged in to Mastery Engine. We've added some great new content since then:
> - {new feature 1}
> - {new content pack}
>
> Your progress is right where you left it. Click here to jump back in: {login_url}
>
> — The Mastery Engine team

Use the `beta_reminder` email template via the email service.

### 4.2 For `at_risk` users
Send a **personalized** nudge — not a templated email. Reference what they were last working on:

> Subject: Stuck on {concept_name}?
>
> Hi {name},
>
> I noticed you were working on {concept_name} last week but haven't been back. Want me to recommend an easier starting point, or would a review session help?
>
> Reply to this email and I'll personally help you get unstuck.
>
> — {founder_name}

### 4.3 For `incomplete_onboarding` users
Send a direct link to the welcome wizard:

> Subject: Your Mastery Engine account is ready
>
> Hi {name},
>
> You're almost set up — just 4 quick steps away from your first study session:
> 1. Set your display name
> 2. Pick a learning goal
> 3. Choose a subject
> 4. Take the tutorial
>
> It takes less than 5 minutes: {welcome_wizard_url}

### 4.4 For `stuck_in_learning` users
Recommend an easier concept or a review session:

> Subject: A fresh start on {subject_name}
>
> Hi {name},
>
> Sometimes it helps to step back and review what you've already learned. I've queued up a 5-question review session for you — no new material, just a confidence boost.
>
> Click here to start: {review_session_url}

### 4.5 For `no_study_7_days` users
Send a "time to study" reminder:

> Subject: 10 minutes today keeps your streak alive
>
> Hi {name},
>
> You haven't studied in 7 days. Just 10 minutes today will keep your streak going and reinforce what you've learned.
>
> One-click resume: {resume_url}

### 4.6 For `email_verification_pending` users
Resend the verification email:

> Subject: Please verify your email
>
> Hi {name},
>
> We noticed you haven't verified your email yet. Verification is required for password resets and important notifications.
>
> Click here to verify: {verification_url}

---

## 5. Measuring Success

Track these metrics weekly to evaluate whether the User Success Center is working:

| Metric | Target | How to measure |
|---|---|---|
| Re-engagement rate | > 20% of contacted users return | Compare `inactive` count before/after email send |
| Onboarding completion rate | > 70% of registered users | `incomplete_onboarding` count / total registered |
| Day-7 retention | > 30% | `/admin/beta-ops/funnel` retention tab |
| Time to first study session | < 24 hours after registration | `avg_time_to_first_question_minutes` in funnel |
| Recommendation acceptance | > 30% | `recommendation_acceptance` in learning effectiveness |

---

## 6. Edge Cases

### 6.1 A user appears in multiple signals
This is expected. A user might be both `inactive` AND `incomplete_onboarding`. Triage the highest-severity signal first.

### 6.2 A user's email bounces
- Mark the user's email as invalid in the audit log
- Do NOT remove them from the success center — they're still at risk
- If possible, contact them via an alternate channel (Slack, Discord)

### 6.3 A user explicitly asks to stop receiving emails
- Honor the request immediately
- Add a `notification_preferences.email_opt_out = true` flag (future enhancement)
- The user will still appear in the success center, but the recommendation should be "Do not email — contact via Slack"

---

## 7. Integration with the Email System

The recommendations above reference email templates that already exist:
- `beta_invitation` — invite email
- `beta_welcome` — welcome email
- `beta_reminder` — re-engagement email

To trigger any of these programmatically:

```bash
docker compose -f docker-compose.prod.yml exec backend python -c "
from app.infrastructure.email.service import EmailService, InMemorySmtpClient
from app.shared.config import get_settings
import asyncio

async def send():
    settings = get_settings()
    from app.infrastructure.email.service import ProductionSmtpClient
    client = ProductionSmtpClient.from_settings(settings)
    svc = EmailService(smtp_client=client)
    await svc.send_template(
        to='user@example.com',
        template_name='beta_reminder',
        context={
            'display_name': 'Jane',
            'login_url': 'https://app.masteryengine.com/login',
            'days_inactive': '14'
        }
    )
asyncio.run(send())
"
```

---

## 8. Future Enhancements (Out of Scope for Task 026)

- **Predictive churn model**: Use the AI platform to predict which users are most likely to churn based on their event history.
- **Automated re-engagement**: Trigger the `beta_reminder` email automatically when a user hits the `inactive` threshold.
- **In-app nudges**: Show a dismissible banner in the learner portal when a user is at risk.
- **Slack integration**: Ping a `#beta-success` Slack channel when a high-severity signal appears.

These are product features, not operational tooling, so they're deferred to post-beta.

---

**Next:** Read `analytics-guide.md` for the full metric definitions, or `support-playbook.md` for handling individual user support requests.
