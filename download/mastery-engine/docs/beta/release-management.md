# Release Management — Mastery Engine Closed Beta

> **Audience:** Engineering lead, release manager, on-call SRE.
> **Scope:** How to plan, roll out, and (if needed) roll back releases during the Closed Beta.
> **Source of truth:** `/admin/beta-ops/releases` page; `GET/POST /api/v1/admin/beta-ops/releases/*` APIs.
> **Last updated:** 2026-07-03 (Task 026)

---

## 0. Release Philosophy

During the Closed Beta, releases are **frequent and small**. The goal is to:
1. Ship bug fixes quickly (users are actively reporting them)
2. Avoid large-batch releases that are hard to roll back
3. Use canary releases to catch issues before they affect all users
4. Maintain a clear version timeline so we can correlate issues with releases

---

## 1. Version Numbering

We use semantic versioning with a beta suffix:

```
v1.0.0-beta.1
v1.0.0-beta.2
v1.0.1-beta.1   (bug fix)
v1.1.0-beta.1   (new feature — rare during beta)
```

| Release Type | When to use |
|---|---|
| `major` | Breaking changes (avoid during beta) |
| `minor` | New features (rare during beta — the beta is for validation, not features) |
| `patch` | Bug fixes, small improvements |
| `hotfix` | Urgent fix for a production issue |
| `beta` | Beta-specific release (default during the Closed Beta period) |

---

## 2. Release Stages

Every release goes through these stages:

```
[planned] → [building] → [canary] → [staged] → [live]
                                              ↓
                                        [rolled_back]
                                              ↓
                                        [abandoned]
```

| Stage | Meaning | Rollout % |
|---|---|---|
| `planned` | Release is scheduled but not started | 0% |
| `building` | CI/CD is building the image | 0% |
| `canary` | Deployed to 5-10% of users for smoke testing | 5-10% |
| `staged` | Deployed to 50% of users | 50% |
| `live` | Deployed to 100% of users | 100% |
| `rolled_back` | Reverted to the previous version due to issues | 0% |
| `abandoned` | Cancelled before going live | 0% |

---

## 3. The Release Process

### 3.1 Plan the Release

1. **Determine what's in the release:**
   - List the git commits since the last release
   - Categorize as `features`, `bug_fixes`, `breaking_changes`, `known_issues`
2. **Create the release note** via `/admin/beta-ops/releases`:
   - Click "Create Release"
   - Fill in version, release_type, title, summary, body
   - Add features / bug_fixes / breaking_changes / known_issues as JSON arrays
   - Set `feature_freeze = false` (unless this is a freeze release)
   - Set `published = false` (we'll publish after canary)
3. **Add the `planned` stage:**
   - Click "Add Stage" on the release
   - Stage = `planned`, rollout = 0

### 3.2 Build the Release

1. Tag the git commit: `git tag v1.0.1-beta.1`
2. Push the tag: `git push origin v1.0.1-beta.1`
3. CI/CD builds the Docker images and pushes to the registry
4. **Add the `building` stage** to the release note

### 3.3 Canary Deployment (5-10%)

1. **Add the `canary` stage** with rollout = 10
2. Deploy via `docker compose --env-file .env.production -f docker-compose.prod.yml up -d --scale backend=2`
3. Wait 30 minutes
4. Monitor:
   - `/admin/beta-ops/operations` — platform health
   - Sentry — new errors
   - `/admin/beta-ops/feedback` — user-reported issues
5. If any SEV-1/SEV-2 issue → rollback (see §5)
6. If stable → proceed to staged

### 3.4 Staged Deployment (50%)

1. **Add the `staged` stage** with rollout = 50
2. Wait 1-2 hours
3. Monitor the same metrics
4. If any issue → rollback
5. If stable → proceed to live

### 3.5 Live Deployment (100%)

1. **Add the `live` stage** with rollout = 100
2. **Publish the release note** (PATCH the release with `published = true`)
3. Notify beta users via in-app notification:
   ```
   {
     "title": "New release: v1.0.1-beta.1",
     "body": "Bug fixes and improvements. See the release notes for details."
   }
   ```
4. Monitor for 24 hours
5. If any issue → rollback

---

## 4. Feature Freeze Mode

When `feature_freeze = true` on a release, no new features should be merged until the freeze is lifted.

Use feature freeze:
- 3 days before a major milestone (e.g., Public Beta launch)
- During a SEV-1 incident investigation
- When the team is on-call with reduced capacity

To set a feature freeze:
1. Create or update a release note with `feature_freeze = true`
2. The `/admin/beta-ops/releases` page will show a "Feature Freeze Active" banner
3. The CI/CD pipeline should enforce the freeze (future enhancement — for now, it's a manual convention)

To lift the freeze:
1. PATCH the release note with `feature_freeze = false`
2. Announce in Slack that the freeze is lifted

---

## 5. Rollback Procedure

If a release causes issues, roll back immediately:

### 5.1 Quick Rollback (config change)

If the issue is a config or feature-flag change:
```bash
# Revert the config in .env.production
# Restart backend + worker
make prod-restart
```

### 5.2 Image Rollback (bad deployment)

If the issue is in the code:
```bash
# Find the previous good git tag
git tag --sort=-creatordate | head -5

# Checkout the previous tag
git checkout v1.0.0-beta.5

# Rebuild and restart
make prod-build
make prod-up
```

### 5.3 Database Rollback (migration issue)

If a migration broke the schema:
```bash
# Downgrade to the previous Alembic revision
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1

# If the DB is unrecoverable, restore from backup
make restore FILE=/opt/mastery-engine/backups/mastery_engine_<latest>.tar.gz.enc
```

### 5.4 Record the Rollback

After rolling back:
1. Add a `rolled_back` stage to the release note
2. Include notes explaining why (e.g., "Caused SEV-2: login broken for users with MFA")
3. The release will appear in the "Rollback History" section

---

## 6. Release Notes Format

### 6.1 Body

The `body` field is a markdown-formatted description of the release. Example:

```markdown
## What's New

This release fixes several bugs reported during the Closed Beta and adds
small UX improvements to the study session flow.

## Bug Fixes

- Fixed an issue where the feedback button was not clickable on mobile devices
- Fixed a race condition that caused duplicate study sessions to be created
- Fixed the mastery chart not updating after a review session

## Improvements

- The study session summary now shows time spent per question
- The welcome wizard is now skippable (but discouraged)

## Known Issues

- AI explanations may take up to 5 seconds to generate on the first request
- The offline banner may appear briefly when switching tabs
```

### 6.2 Features / Bug Fixes / Breaking Changes / Known Issues

Each of these fields is a JSON array of objects. Example:

```json
[
  {"title": "Mobile feedback button fix", "description": "Button now has a 44x44px tap target", "ticket": "BETA-123"},
  {"title": "Duplicate study session fix", "description": "Added idempotency key to session creation", "ticket": "BETA-124"}
]
```

This structured format allows the frontend to render them consistently and allows future tooling to query them.

---

## 7. Version Timeline

The `/admin/beta-ops/releases` page shows a vertical timeline of all releases with their current stage. Use this to:
1. See the current version at a glance
2. Track how long each release spent in each stage
3. Identify patterns (e.g., "we always roll back after staged — maybe our canary is too short")

---

## 8. Rollback History

The "Rollback History" section lists all releases that were rolled back. For each:
- Version
- When it was rolled back
- Notes explaining why

Use this to:
1. Identify recurring issues
2. Track rollback frequency (target: < 10% of releases)
3. Learn from past mistakes

---

## 9. CI/CD Integration

The CI/CD pipeline (GitHub Actions) handles:
1. Building Docker images on tag push
2. Running all tests
3. Deploying to staging
4. Manual approval gate
5. Blue-green deploy to production

The release notes in `/admin/beta-ops/releases` are **separate from** the CI/CD pipeline — they're the human-readable record of what shipped and why. The CI/CD pipeline handles the technical deployment; the release notes handle the communication.

Future enhancement: wire the CI/CD pipeline to automatically create a release note when a tag is pushed.

---

## 10. Communication

### 10.1 Internal

- **Slack `#beta-releases`**: Post a message when a release goes live:
  > 🚀 v1.0.1-beta.1 is live. 3 bug fixes, 2 improvements. Release notes: {link}
- **Slack `#beta-status`**: Post if there's a rollback or known issue

### 10.2 External (Beta Users)

- **In-app notification**: Sent on every live release (see §3.5)
- **Email**: Only for major releases or breaking changes
- **Status page**: Update if there's downtime

---

## 11. API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/admin/beta-ops/releases` | List all releases + timeline + rollback history |
| POST | `/api/v1/admin/beta-ops/releases` | Create a release note |
| PATCH | `/api/v1/admin/beta-ops/releases/{id}` | Update a release note (e.g., publish) |
| POST | `/api/v1/admin/beta-ops/releases/{id}/stage` | Add a stage (canary/staged/live/rolled_back) |

All endpoints require `ROLE_ADMINISTRATOR` or `ROLE_SYSTEM_ADMIN`.

---

## 12. Release Cadence During Beta

| Phase | Cadence | Reason |
|---|---|---|
| Phase 1 (Canary) | Daily | Fixing smoke-test issues |
| Phase 2 (Expanding) | 2-3x/week | Bug fixes from growing user base |
| Phase 3 (Validation) | Weekly | Stabilize for validation |
| Phase 4 (Transition) | Weekly | Prepare for Public Beta |

Avoid releasing on Fridays — if something breaks, no one wants to debug it on the weekend.

---

**Next:** Read `operations-handbook.md` for operational runbooks, or `support-playbook.md` for handling user support requests.
