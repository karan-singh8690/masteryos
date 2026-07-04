# Product Validation — Mastery Engine Closed Beta

> **Audience:** Product manager, engineering lead, founders.
> **Scope:** The framework for turning the Closed Beta into validated product decisions.
> **Last updated:** 2026-07-03 (Task 026)

---

## 0. What "Product Validation" Means

The Closed Beta is not a marketing exercise. It is a **structured experiment** to answer:

1. **Desirability**: Do users want this? (Do they complete onboarding? Do they come back?)
2. **Usability**: Can users use this? (Where do they get stuck? What confuses them?)
3. **Value**: Does this help users? (Are they learning? Do their mastery scores go up?)
4. **Viability**: Can we sustain this? (What does it cost? What breaks at scale?)

If we cannot answer these four questions with data by the end of the beta, the beta has failed.

---

## 1. The Validation Framework

For each of the 4 questions, we define:
- **Hypothesis**: What we believe will be true
- **Metric**: How we'll measure it
- **Threshold**: The number that proves the hypothesis
- **Source**: Where the data comes from

### 1.1 Desirability

| Hypothesis | Metric | Threshold | Source |
|---|---|---|---|
| Users who are invited will register | Invite conversion rate | > 60% | `/admin/beta-ops/dashboard` |
| Registered users will complete onboarding | Welcome wizard completion | > 70% | `/admin/beta-ops/funnel` |
| Onboarded users will start a study session | First study session rate | > 60% | `/admin/beta-ops/funnel` |
| Users will return after Day 1 | Day-1 retention | > 40% | `/admin/beta-ops/dashboard` |
| Users will return after Day 7 | Day-7 retention | > 30% | `/admin/beta-ops/dashboard` |
| Users will return after Day 30 | Day-30 retention | > 20% | `/admin/beta-ops/dashboard` |

### 1.2 Usability

| Hypothesis | Metric | Threshold | Source |
|---|---|---|---|
| The registration flow is frictionless | Time to first question | < 10 min | `/admin/beta-ops/funnel` |
| Users don't get stuck in onboarding | Incomplete onboarding rate | < 20% | `/admin/beta-ops/success` |
| Users don't abandon study sessions | Session completion rate | > 60% | `/admin/beta-ops/learning` (adaptive_queue_quality) |
| The UI is intuitive | UI/UX feedback as % of total | < 20% | `/admin/beta-ops/feedback` (by_category) |
| Users don't need hints excessively | Hint usage rate | < 40% | `/admin/beta-ops/learning` |

### 1.3 Value

| Hypothesis | Metric | Threshold | Source |
|---|---|---|---|
| Users' mastery improves over time | Mastery growth avg | > 10pp | `/admin/beta-ops/learning` |
| Users answer questions correctly | Question accuracy | > 60% | `/admin/beta-ops/learning` |
| Reviews are effective | Review effectiveness | > 70% | `/admin/beta-ops/learning` |
| Users accept recommendations | Recommendation acceptance | > 30% | `/admin/beta-ops/learning` |
| Users are satisfied | User satisfaction | > 80% | `/admin/beta-ops/dashboard` |
| Users would recommend us | NPS | > 0 | `/admin/beta-ops/dashboard` |

### 1.4 Viability

| Hypothesis | Metric | Threshold | Source |
|---|---|---|---|
| The platform is stable | Uptime | > 99.5% | `/admin/beta-ops/operations` |
| The platform is fast | p95 API latency | < 500ms | `/admin/beta-ops/operations` |
| Errors are rare | 5xx error rate | < 0.1% | `/admin/beta-ops/operations` |
| AI cost is sustainable | AI cost per user per month | < $2 | `/admin/beta-ops/operations` (cost_metrics) |
| Email delivery works | Email delivery rate | > 95% | `/admin/beta-ops/operations` |
| Backups work | Restore drill success | 100% | Weekly ops drill |

---

## 2. The Validation Cadence

### 2.1 Daily (5 minutes)
- Check `/admin/beta-ops/dashboard` for any metric that dropped > 30% from yesterday
- Check `/admin/beta-ops/feedback` for new urgent issues
- Check `/admin/beta-ops/success` for high-severity user signals

### 2.2 Weekly (60 minutes)
- Generate the weekly report (`/admin/beta-ops/reports` → weekly)
- Compare this week's metrics to last week's
- Update the validation scorecard (§3)
- Identify the week's biggest insight

### 2.3 Monthly (2 hours)
- Generate the monthly report
- Review all 4 validation questions (§1)
- Decide: continue beta, expand beta, or transition to Public Beta
- Write a 1-page monthly review (see `docs/operations/monthly-reviews/`)

### 2.4 Beta Exit Review (4 hours, end of beta)
- Compile all the data
- Answer the 4 validation questions definitively
- List what we learned (validated assumptions + invalidated assumptions)
- List what we still don't know (for Public Beta)
- Make the Public Beta go/no-go decision

---

## 3. The Validation Scorecard

Maintain this scorecard in a shared document (Google Sheet, Notion, etc.):

```
| Metric                     | Target | Week 1 | Week 2 | Week 3 | Week 4 | ... |
|----------------------------|--------|--------|--------|--------|--------|-----|
| Invite conversion rate     | > 60%  | 80%    | 75%    | 70%    | 68%    |     |
| Welcome wizard completion  | > 70%  | 60%    | 65%    | 72%    | 75%    |     |
| Day-1 retention            | > 40%  | 30%    | 35%    | 42%    | 45%    |     |
| Day-7 retention            | > 30%  | —      | —      | 25%    | 32%    |     |
| Mastery growth avg         | > 10pp | 5pp    | 7pp    | 9pp    | 12pp   |     |
| Question accuracy          | > 60%  | 55%    | 58%    | 62%    | 65%    |     |
| NPS                        | > 0    | -10    | -5     | 5      | 12     |     |
| Uptime                     | > 99.5%| 99.1%  | 99.6%  | 99.8%  | 99.9%  |     |
| p95 latency                | < 500ms| 850ms  | 620ms  | 450ms  | 380ms  |     |
```

Color-code each cell:
- 🟢 Green: meets or exceeds target
- 🟡 Yellow: within 20% of target
- 🔴 Red: more than 20% below target

At the end of each week, identify:
- The metric that improved the most → what caused it?
- The metric that dropped the most → what caused it?
- The metric furthest from target → what's the plan to close the gap?

---

## 4. Validated Learning

The output of the beta is not just metrics — it's **validated learning**. Each week, capture:

### 4.1 Validated Assumptions
Things we believed that the data confirmed:
> "We assumed users would complete the welcome wizard in < 5 minutes. Data shows median time is 4.2 minutes. ✅ Validated."

### 4.2 Invalidated Assumptions
Things we believed that the data disproved:
> "We assumed users would use the AI coach daily. Data shows only 15% of users have tried it. ❌ Invalidated — AI coach needs better discovery."

### 4.3 Surprises
Things we didn't expect:
> "Surprise: 40% of feedback is about the question timer being too short. We didn't anticipate this — adding a 'pause' option to the next release."

### 4.4 Open Questions
Things we still don't know:
> "We don't know why Day-7 retention drops to 25% — is it the difficulty curve, the lack of notifications, or something else? Need to interview churned users."

---

## 5. User Interviews

Metrics tell you **what** is happening. User interviews tell you **why**.

### 5.1 Who to Interview
- 5 users who completed onboarding and are active → what's working?
- 5 users who started but churned → what went wrong?
- 5 users who are power users → what would they pay for?
- 5 users who reported bugs → how did it affect their experience?

### 5.2 Interview Script

1. **Warm-up** (5 min): "Tell me about your experience with Python interviews."
2. **Onboarding** (5 min): "Walk me through your first time using Mastery Engine."
3. **Habits** (5 min): "How often do you use Mastery Engine? When? For how long?"
4. **Value** (5 min): "What's the most useful thing about Mastery Engine?"
5. **Pain points** (5 min): "What's the most frustrating thing?"
6. **Alternatives** (5 min): "What would you use if Mastery Engine didn't exist?"
7. **Recommendation** (5 min): "Would you recommend this to a friend? Why or why not?"

Record (with permission), transcribe, and tag key quotes.

### 5.3 Synthesis

After each interview round:
1. Tag every quote with a theme (e.g., `onboarding-friction`, `content-difficulty`, `ui-confusion`)
2. Count the themes — which come up most often?
3. For the top 3 themes, write a one-paragraph insight:
   > "Onboarding friction: 4 of 5 churned users mentioned the welcome wizard was 'too long' or 'asked too many questions'. The data confirms this — median wizard completion time is 8 minutes for churned users vs 3 minutes for active users. Action: simplify the wizard to 2 steps."

---

## 6. The Public Beta Go/No-Go Decision

At the end of the Closed Beta (6-8 weeks), make a formal go/no-go decision for Public Beta.

### 6.1 Go Criteria (ALL must be met)

- [ ] **Desirability**: Invite conversion > 60%, Day-1 retention > 40%, Day-7 retention > 30%
- [ ] **Usability**: Onboarding completion > 70%, Session completion > 60%
- [ ] **Value**: Mastery growth > 10pp, NPS > 0
- [ ] **Viability**: Uptime > 99.5%, p95 < 500ms, AI cost < $2/user/month
- [ ] **Quality**: All P1 bugs resolved, no SEV-1 in 4 weeks
- [ ] **Operations**: Backup/restore drill passed, security audit passed
- [ ] **Documentation**: Public docs written, support playbook ready

### 6.2 No-Go Criteria (ANY triggers a no-go)

- Day-1 retention < 20% (users don't see value)
- NPS < -20 (users are actively unhappy)
- Uptime < 95% (platform is unstable)
- A SEV-1 data loss incident in the last 2 weeks
- Major security vulnerability unpatched

### 6.3 The Decision Meeting

Attendees: Product manager, Engineering lead, Design lead, Founder.

Agenda:
1. Walk through the validation scorecard (§3)
2. Review the validated learning (§4)
3. Discuss user interview themes (§5)
4. Vote: Go, Go with conditions, or No-Go
5. If Go: define the Public Beta launch date + marketing plan
6. If No-Go: define what needs to change before re-evaluating

---

## 7. Common Validation Anti-Patterns

1. **"The metrics look good"** — Which metrics? Compared to what? Always cite specific numbers + thresholds.
2. **"Users seem happy"** — How do you know? NPS? Feedback? Retention? Use the data.
3. **"We just need more users"** — More users won't fix a 20% Day-1 retention. Fix the funnel first.
4. **"Let's add this feature, it'll help"** — The beta is for validation, not features. New features don't fix bad metrics.
5. **"We'll figure it out in Public Beta"** — No. If you can't figure it out with 20 users, you can't with 2000.

---

## 8. The Validation Output

By the end of the Closed Beta, you should have:

1. **A completed validation scorecard** — all 16 metrics with 6-8 weeks of data
2. **A list of validated assumptions** — what you believed that turned out to be true
3. **A list of invalidated assumptions** — what you believed that turned out to be false
4. **A list of surprises** — things you didn't anticipate
5. **A list of open questions** — things you still need to learn in Public Beta
6. **20+ user interview transcripts** — tagged and synthesized
7. **A Public Beta go/no-go decision** — with clear criteria and rationale

This is the deliverable of the Closed Beta. Not features. Not users. **Validated learning.**

---

**Next:** Read `closed-beta-playbook.md` for the end-to-end operating playbook, or `analytics-guide.md` for metric definitions.
