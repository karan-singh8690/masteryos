# Closed Beta Playbook — Mastery Engine

> **Audience:** Product manager, beta program lead, on-call SRE.
> **Scope:** End-to-end playbook for running the 20–100 user Closed Beta.
> **Related docs:** `user-success.md`, `analytics-guide.md`, `experimentation.md`, `release-management.md`, `operations-handbook.md`, `support-playbook.md`, `product-validation.md`
> **Last updated:** 2026-07-03 (Task 026)

---

## 0. The Beta Mission

The Closed Beta is **not** a feature launch — it is a **product validation exercise**. The goal is to answer four questions with data:

1. **Do users complete onboarding?** (Funnel: invite → first question)
2. **Do users come back?** (Retention: Day-1, Day-7, Day-30)
3. **Are they learning?** (Mastery growth, accuracy, time-to-mastery)
4. **What should we build next?** (Feedback themes, vote scores)

If we cannot answer these four questions, the beta has failed — regardless of how many users signed up.

---

## 1. Beta Phases

### Phase 1: Canary (Days 0–3)
- **Cohort:** 5 invited users (friends, colleagues)
- **Goal:** Smoke-test the registration → first-session flow end-to-end
- **Exit criteria:**
  - All 5 users complete registration
  - At least 3 complete a study session
  - No SEV-1 incidents
  - At least 1 piece of feedback submitted
- **Action:** If exit criteria pass, proceed to Phase 2. If not, fix and re-invite.

### Phase 2: Expanding (Days 4–14)
- **Cohort:** 5 → 20 users
- **Goal:** Validate the learning loop + collect feedback at scale
- **Exit criteria:**
  - DAU/MAU > 30%
  - Day-1 retention > 40%
  - At least 10 feedback items submitted
  - At least 5 bugs resolved
- **Action:** If exit criteria pass, proceed to Phase 3.

### Phase 3: Validation (Days 15–42)
- **Cohort:** 20 → 50 users (if capacity allows)
- **Goal:** Validate learning outcomes + run experiments
- **Exit criteria:**
  - Day-7 retention > 30%
  - Average mastery growth > 10 percentage points
  - At least 1 A/B experiment with statistical significance
  - NPS > 0 (i.e., more promoters than detractors)
- **Action:** If exit criteria pass, plan the transition to Public Beta.

### Phase 4: Transition (Days 43–60)
- **Cohort:** 50 → 100 users
- **Goal:** Stress-test capacity + finalize the Public Beta checklist
- **Exit criteria:**
  - No SEV-1 incidents in 4 weeks
  - Backup/restore drill completed
  - Security audit passed
  - Public documentation written
- **Action:** Set `CLOSED_BETA_ENABLED=false` and announce Public Beta.

---

## 2. Daily Operating Rhythm (15 minutes/day)

Every morning at 08:00 UTC:

### 2.1 Open the Beta Operations Dashboard
- URL: `https://app.masteryengine.com/admin/beta-ops`
- Check the 17 KPI cards. Look for:
  - **DAU drop** > 30% from yesterday → investigate
  - **Crash reports** > 0 → investigate immediately
  - **NPS** trending down → read new feedback
  - **Outbox pending** > 100 → check Operations page

### 2.2 Review New Feedback
- URL: `https://app.masteryengine.com/admin/beta-ops/feedback`
- Filter by status = `open`, sort by created_at desc
- For each new item:
  - Reproduce (if bug)
  - Set priority (low/normal/high/urgent/blocker)
  - Set roadmap status (untriaged/planned/in_progress/shipped/wont_fix/duplicate)
  - Respond to the user via email within 24 hours

### 2.3 Check User Success Center
- URL: `https://app.masteryengine.com/admin/beta-ops/success`
- Look at the 8 signal counts
- For each "high severity" user, send a personalized re-engagement email

### 2.4 Glance at Operations
- URL: `https://app.masteryengine.com/admin/beta-ops/operations`
- Verify platform status = `healthy`
- Check that all workers are `running` and `last_seen` < 60s ago
- Verify no dead letters are accumulating

---

## 3. Weekly Operating Rhythm (60 minutes/week)

Every Monday at 09:00 UTC:

### 3.1 Generate the Weekly Report
- URL: `https://app.masteryengine.com/admin/beta-ops/reports`
- Click "Generate Report" with period = weekly
- Save the report (screenshot or copy text) for the stakeholder update

### 3.2 Funnel & Retention Review
- URL: `https://app.masteryengine.com/admin/beta-ops/funnel`
- Compare this week's funnel to last week's
- Identify the biggest drop-off step — that's the week's optimization target

### 3.3 Learning Effectiveness Review
- URL: `https://app.masteryengine.com/admin/beta-ops/learning`
- Check the interview readiness trend — is it going up?
- Review the weak concepts list — are they converging (multiple users stuck on the same concept)?
- If yes, schedule a content improvement task

### 3.4 Experiment Review
- URL: `https://app.masteryengine.com/admin/beta-ops/experiments`
- For each running experiment:
  - Check sample sizes — are we close to `min_sample_size`?
  - Check `is_statistically_significant` — if true, declare a winner and stop
  - If no experiment is running, design the next one

### 3.5 Stakeholder Update
Send a Slack message or email to stakeholders with:
- Total users, DAU trend
- Top 3 feedback themes
- Top bug fixed this week
- Top feature request
- Next week's focus

---

## 4. Invite Strategy

### 4.1 Who to Invite
The 20-user beta should include:
- **5 power users** — Python experts who will give technical feedback
- **5 intermediate users** — the target persona
- **5 beginners** — to test onboarding UX
- **5 external users** — people who don't know the team (unbiased feedback)

### 4.2 When to Invite
- Phase 1: invite 5 users on Day 0
- Phase 2: invite 5 more on Day 4 (if Phase 1 passed)
- Phase 2: invite 10 more on Day 7 (if Day 4 cohort succeeded)
- Phase 3: invite 20 more on Day 15

### 4.3 Invite Personalization
Each invite email should include:
- The invitee's name
- Why they were selected
- What they'll get out of it (early access, founder badge, etc.)
- A clear call-to-action (the invite link)
- An expiry date (7 days)

The `beta_invitation` email template handles this automatically — see `POST /api/v1/admin/beta/invites`.

---

## 5. Communication Channels

| Channel | When to use | Tool |
|---|---|---|
| Email | Formal announcements, individual follow-up | SMTP provider |
| In-app notification | Product updates, new features | Notification system |
| Slack/Discord | Real-time discussion | External channel |
| Status page | Incidents, scheduled maintenance | StatusPage.io or simple webpage |
| Beta dashboard | Daily metrics review | `/admin/beta-ops` |

---

## 6. Incident Response (Beta-specific)

### 6.1 SEV-1 (platform down)
1. Acknowledge in `#beta-status` Slack
2. Check `/admin/beta-ops/operations` for the failing component
3. Follow the runbook in `operations-handbook.md`
4. Notify beta users via email if downtime > 1 hour
5. Postmortem within 48 hours

### 6.2 SEV-2 (major feature broken)
1. Check if a specific user flow is affected (login, study session, etc.)
2. Triage via `/admin/beta-ops/feedback` — are multiple users reporting it?
3. Hotfix or rollback per `release-management.md`
4. Email affected users with the fix

### 6.3 SEV-3 (minor bug)
- Triage in the next daily review
- Add to the backlog with appropriate priority

---

## 7. Exit Criteria for Public Beta

The Closed Beta transitions to Public Beta when ALL of the following are true:

- [ ] Closed Beta ran for at least 6 weeks
- [ ] All P1 bugs resolved
- [ ] User retention > 60% week-over-week (Phase 3)
- [ ] Average rating > 4.0/5
- [ ] No SEV-1 incidents in the last 4 weeks
- [ ] Capacity validated for 5x current load (load test)
- [ ] Backup/restore drill completed
- [ ] Security audit passed
- [ ] Public documentation (help center, FAQ) written
- [ ] At least 1 experiment completed with a clear winner

To execute the transition:
1. Set `CLOSED_BETA_ENABLED=false` in `.env.production`
2. Restart backend + worker: `make prod-restart`
3. Verify public registration works (no invite required)
4. Raise `MAX_BETA_USERS` or remove the cap
5. Email all beta users thanking them and announcing the transition
6. Announce Public Beta publicly

---

## 8. Anti-Patterns to Avoid

1. **"Let's add this feature for the beta"** — No. The beta is for validation, not feature accumulation. New features go to Public Beta.
2. **"We can skip the report this week"** — No. The weekly report is the only way to spot slow trends.
3. **"The user is just complaining"** — Every feedback item has a vote score and a category. Treat them all as data.
4. **"Let's invite everyone at once"** — No. Phased rollout (5 → 20 → 50) catches issues early.
5. **"We'll fix the analytics later"** — No. If the analytics are broken, the beta is useless.

---

## 9. Quick Reference

| What | URL | Frequency |
|---|---|---|
| Beta Dashboard | `/admin/beta-ops` | Daily |
| Feedback Review | `/admin/beta-ops/feedback` | Daily |
| User Success | `/admin/beta-ops/success` | Daily |
| Operations | `/admin/beta-ops/operations` | Daily + on alert |
| Funnel & Retention | `/admin/beta-ops/funnel` | Weekly |
| Learning Insights | `/admin/beta-ops/learning` | Weekly |
| Instructor Analytics | `/admin/beta-ops/instructor` | Weekly |
| Releases | `/admin/beta-ops/releases` | On each release |
| Reports | `/admin/beta-ops/reports` | Weekly + monthly |
| Experiments | `/admin/beta-ops/experiments` | Weekly |

---

**Next:** Read `user-success.md` for the detailed user success playbook, or `analytics-guide.md` for how each metric is computed.
