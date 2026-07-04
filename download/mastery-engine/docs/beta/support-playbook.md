# Support Playbook — Mastery Engine Closed Beta

> **Audience:** Support engineers, customer success, founders doing support.
> **Scope:** How to handle individual user support requests during the Closed Beta.
> **Source of truth:** `/admin/beta-ops/feedback` page; `GET /api/v1/admin/beta/feedback` API.
> **Last updated:** 2026-07-03 (Task 026)

---

## 0. The Support Mission

Every beta user should feel heard. With 20-100 users, we can — and should — respond to every piece of feedback within 24 hours. This is the single highest-leverage retention activity during the beta.

**The rule:** No feedback item goes unanswered. No bug report goes unresolved without a response.

---

## 1. Feedback Categories

The feedback platform supports 6 categories:

| Category | Typical response time | Owner |
|---|---|---|
| `bug` | 24 hours | Engineering |
| `feature_request` | 1 week | Product |
| `ui_ux` | 3 days | Design |
| `content` | 2 days | Content |
| `performance` | 2 days | Engineering |
| `other` | 1 week | Product |

---

## 2. The Support Workflow

### 2.1 Triage (Daily)

1. Open `/admin/beta-ops/feedback`
2. Filter by status = `open`, sort by created_at desc
3. For each new item:
   - Read the comment + auto-captured context (browser, platform, route, correlation_id)
   - Set **priority** (low/normal/high/urgent/blocker)
   - Set **roadmap status** (untriaged/planned/in_progress/shipped/wont_fix/duplicate)
   - If it's a duplicate → mark as duplicate (see §3)
   - If it's a bug → reproduce (see §4)

### 2.2 Respond (Within 24 Hours)

For every feedback item, send a personal email to the user:

> Subject: Re: Your Mastery Engine feedback
>
> Hi {name},
>
> Thanks for taking the time to share this — it's exactly the kind of feedback we need during the beta.
>
> {acknowledge the specific issue}
>
> {what we're doing about it}
>
> {next steps / ETA}
>
> — {founder_name}

**Do not use templated responses.** Beta users can tell. Reference the specific issue they reported.

### 2.3 Resolve

When the issue is fixed:
1. Update the feedback status to `resolved`
2. Add resolution notes (what was fixed, in which version)
3. Email the user:
   > Subject: Your feedback led to a fix 🎉
   >
   > Hi {name},
   >
   > You reported {issue} on {date}. We've fixed it in v{version}.
   >
   > Thanks for making Mastery Engine better.
   >
   > — {founder_name}

This closes the loop and dramatically increases user retention.

---

## 3. Handling Duplicates

The feedback platform automatically detects potential duplicates (same category + >60% token overlap in comment).

### 3.1 When You See a Potential Duplicate

1. Open the "Potential Duplicates" section at the bottom of `/admin/beta-ops/feedback`
2. For each pair, read both comments
3. If they're truly duplicates:
   - Pick the more detailed one as the canonical item
   - Click "Mark Duplicate" on the other item, entering the canonical item's ID
   - Email both users: "Thanks for reporting this — another user reported the same issue, so I'm merging them. You'll get the resolution update."

### 3.2 When Duplicates Are NOT Duplicates

Sometimes two feedback items look similar but are actually different issues. In that case:
- Leave both as `open`
- Add a tag to each (e.g., `not-duplicate`) for future reference

---

## 4. Reproducing Bugs

When a user reports a bug:

### 4.1 Gather Context

The feedback platform auto-captures:
- `browser` (Chrome, Firefox, Safari, Edge, Unknown)
- `platform` (Windows, Mac, Linux, etc.)
- `route` (the page they were on, e.g., `/study/123`)
- `correlation_id` (links to the request in backend logs)
- `user_agent` (full UA string)

Use the `correlation_id` to find the exact request in the backend logs:

```bash
docker compose -f docker-compose.prod.yml logs backend --since 24h | grep "$CORRELATION_ID"
```

### 4.2 Reproduce

1. Try to reproduce on the same browser + platform
2. If you can't reproduce, ask the user for a screenshot or screen recording
3. Check Sentry for the same time window — there may be an exception captured

### 4.3 File the Bug

If reproduced:
- File a ticket in the issue tracker
- Set the feedback item's `roadmap_status` to `planned`
- Set `priority` based on severity:
  - `blocker` — platform unusable (login broken, data loss)
  - `urgent` — major feature broken for >50% of users
  - `high` — minor feature broken or major feature broken for <50%
  - `normal` — cosmetic or low-impact
  - `low` — nice-to-have fix

---

## 5. Handling Feature Requests

Feature requests during the beta are tricky — the beta is for validation, not feature accumulation.

### 5.1 The Default Response

> Thanks for the suggestion! During the Closed Beta, we're focused on validating the core learning experience rather than adding new features. I've logged this for consideration after Public Beta.

### 5.2 Exceptions

If the request is:
- A small UX improvement (< 1 day of work)
- Directly unblocks the user's learning
- Reported by multiple users (check vote score)

...then it's worth doing during the beta. Set `roadmap_status = planned` and add it to the next release.

### 5.3 Voting

Users can upvote feature requests. Use the vote count to prioritize:
- 1-2 votes → backlog
- 3-5 votes → planned for Public Beta
- 6+ votes → planned for next beta release

---

## 6. Handling UI/UX Feedback

UI/UX feedback is subjective. The rule:

1. **Acknowledge** — "Thanks for the feedback on the study session layout."
2. **Investigate** — Is this a one-off preference or a pattern? Check if other users reported similar.
3. **Decide** — If it's a pattern, schedule a design review. If it's a one-off, explain the design rationale.
4. **Respond** — Tell the user what you decided and why.

---

## 7. Handling Content Feedback

Content feedback (about questions, explanations, concepts) is the most valuable for the beta.

### 7.1 Question Errors

If a user reports a wrong answer or ambiguous question:
1. Find the question via the `route` field (it contains the question ID)
2. Review the question + correct answer + explanation
3. If the user is right:
   - Fix the question in the content authoring portal
   - Publish a new version
   - Email the user: "You were right — the answer was wrong. We've fixed it."
4. If the question is correct but confusing:
   - Improve the explanation
   - Email the user with the clarification

### 7.2 Difficulty Feedback

If a user says a question is too hard/easy:
1. Check the question's accuracy in `/admin/beta-ops/instructor` → frequently_missed_questions
2. If accuracy < 30% → too hard, adjust difficulty
3. If accuracy > 90% → too easy, adjust difficulty

---

## 8. Handling Performance Feedback

If a user reports slowness:

1. Check the `correlation_id` in backend logs for the request duration
2. Check `/admin/beta-ops/operations` → API Latency
3. If the request was genuinely slow (> 2s):
   - Investigate the slow query (see `operations-handbook.md` §3.5)
   - Email the user: "Thanks for reporting this — we've identified the cause and are working on a fix."
4. If the request was fast (< 500ms):
   - It may be a client-side issue (slow device, slow network)
   - Email the user: "Thanks for reporting this. We checked our logs and the request completed in 200ms. Could you tell us more about your device and network?"

---

## 9. Communication Templates

### 9.1 Bug Acknowledgment

> Subject: Re: Your bug report — {short description}
>
> Hi {name},
>
> Thanks for reporting this. I was able to reproduce the issue — it's a real bug.
>
> What's happening: {brief technical explanation}
>
> What we're doing: I've filed this as {ticket-id} and it's in our next release (v{version}, targeting {date}).
>
> I'll email you again when the fix is live.
>
> — {founder_name}

### 9.2 Bug Fixed

> Subject: Your bug report is fixed 🎉
>
> Hi {name},
>
> The bug you reported ({short description}) is fixed in v{version}, which went live today.
>
> Thanks for catching this — it directly improved the platform for everyone.
>
> — {founder_name}

### 9.3 Feature Request — Backlogged

> Subject: Re: Your feature request — {short description}
>
> Hi {name},
>
> Thanks for the suggestion! This is a great idea.
>
> During the Closed Beta, we're focused on validating the core learning experience rather than adding new features. I've logged this in our backlog for consideration after Public Beta.
>
> I'll let you know if we decide to build it.
>
> — {founder_name}

### 9.4 Feature Request — Planned

> Subject: Re: Your feature request — {short description}
>
> Hi {name},
>
> Great news — multiple users have requested this, so we've moved it into our plan for the next beta release (v{version}, targeting {date}).
>
> I'll email you when it ships.
>
> — {founder_name}

### 9.5 Duplicate

> Subject: Re: Your feedback — merged with another report
>
> Hi {name},
>
> Thanks for reporting this. Another user reported the same issue, so I've merged the two reports to make sure we track it once.
>
> You'll get the resolution update when it's fixed.
>
> — {founder_name}

---

## 10. Tracking Support Metrics

Track these weekly:

| Metric | Target | How to measure |
|---|---|---|
| Avg response time | < 24 hours | Time from feedback created to first response |
| Bug resolution rate | > 80% within 1 week | `resolved` count / `open` count |
| User satisfaction (post-resolution) | > 4.0/5 | Send a follow-up survey after resolving |
| Repeat feedback | < 20% | Users who submit > 1 bug about the same issue |

---

## 11. Escalation

| Situation | Escalate to |
|---|---|
| Bug affecting > 50% of users | Engineering lead + Product manager |
| Data loss | Engineering lead immediately |
| Security issue | Security lead immediately |
| User asks for a refund | Product manager |
| User threatens legal action | Legal counsel |
| User requests feature outside beta scope | Product manager |

---

## 12. Tools

| Tool | When to use |
|---|---|
| `/admin/beta-ops/feedback` | Triage + manage feedback items |
| `/admin/beta-ops/success` | Identify users who need proactive outreach |
| `/admin/beta-ops/operations` | Verify platform health when a user reports an issue |
| Sentry | Find the underlying exception for a bug |
| Backend logs (`docker compose logs backend`) | Trace a specific request via `correlation_id` |
| Email (SMTP provider) | Send responses to users |

---

## 13. Anti-Patterns

1. **"This is a known issue"** — Don't say this to the user without explaining what you're doing about it.
2. **"We'll fix it in the next release"** — Only say this if you actually have a release planned.
3. **Ignoring low-priority feedback** — A user who reports a typo is invested enough to read carefully. Acknowledge it.
4. **Arguing with the user** — If they say the UX is confusing, it is. Don't explain why it "should" be clear.
5. **Going silent** — Even if you don't have an update, send a "still working on this" email every 3 days.

---

**Next:** Read `product-validation.md` for the overall validation framework, or `closed-beta-playbook.md` for the end-to-end playbook.
