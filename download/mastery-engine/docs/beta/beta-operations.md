# Beta Operations Manual

> Operations guide for running the Mastery Engine Closed Beta.

## Daily Operations

### Morning Check (5 minutes)

1. **Check health**: `curl https://app.masteryengine.com/api/v1/health/ready`
2. **Check beta analytics**: `GET /api/v1/beta/analytics`
   - How many active users?
   - Any new feedback?
   - Any open issues?
3. **Check workers**: `GET /api/v1/admin/bg/workers`
   - Are all workers running?
   - Any dead letters?
4. **Review feedback**: `GET /api/v1/beta/feedback?status=open`
   - Acknowledge/resolve any new feedback

### Invite Management

1. **Create invite**: `POST /api/v1/admin/beta/invites`
   ```json
   { "email": "newuser@example.com", "notes": "Colleague from team" }
   ```
2. **List invites**: `GET /api/v1/admin/beta/invites`
3. **Resend expired**: `POST /api/v1/admin/beta/invites/resend`
   ```json
   { "invite_id": "uuid-here" }
   ```
4. **Delete unused**: `DELETE /api/v1/admin/beta/invites/{id}`

### User Limit Management

- Default limit: 20 users
- Check current count: `GET /api/v1/beta/analytics` → `total_users`
- To increase limit: Set `MAX_BETA_USERS=30` in environment and restart

### Feature Flag Management

Feature flags are set via environment variables. To change:
1. Update `.env` file
2. Restart backend: `docker compose restart backend worker`
3. Verify: `GET /api/v1/beta/status`

## Weekly Operations

### Beta Report

Generate a weekly summary:
- Total registered users
- Daily active users trend
- Feedback received + resolved
- Top feature requests
- Top bug reports

### Inactive User Outreach

1. Check analytics for users inactive >7 days
2. Send reminder emails (via `beta_reminder` template)
3. Track re-engagement

## Incident Response

### Registration Failure

1. Check if beta is enabled: `GET /api/v1/beta/status`
2. Check user count vs limit
3. Check invite token validity
4. Check database connectivity

### Worker Down

1. `GET /api/v1/admin/bg/workers` — identify dead workers
2. Restart: `docker compose restart worker`
3. Check for dead letters: `GET /api/v1/admin/bg/dead-letters`
4. Replay if needed: `POST /api/v1/admin/bg/dead-letters/{id}/retry`

### Performance Issues

1. Check API latency: `GET /api/v1/admin/bg/workers/metrics`
2. Check cache hit rate
3. Check database connections
4. Review slow queries in logs
