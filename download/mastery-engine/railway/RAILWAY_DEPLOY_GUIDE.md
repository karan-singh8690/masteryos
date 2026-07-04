# MasteryOS Railway Deployment Guide (Task 028)

> Complete guide for deploying MasteryOS on Railway with automatic migrations, health checks, and GitHub CD.

## Architecture

```
GitHub (main push)
      │
      ▼
GitHub Actions CI/CD
      │
      ├── Run tests
      ├── Deploy Backend ──▶ Railway Backend Service
      ├── Deploy Worker  ──▶ Railway Worker Service
      └── Deploy Frontend ──▶ Railway Frontend Service
                                    │
                                    ├── PostgreSQL (Railway Plugin)
                                    └── Redis (Railway Plugin)
```

## Prerequisites

1. **GitHub account** with the repo: `karan-singh8690/masteryos`
2. **Railway account** — sign up at [railway.app](https://railway.app) (includes $5 free credit)
3. **Railway CLI** (optional) — `npm install -g @railway/cli`

## Step-by-Step Deployment

### Step 1: Create Railway Project

1. Go to [railway.app](https://railway.app) → **New Project**
2. Select **Deploy from GitHub Repo**
3. Choose `karan-singh8690/masteryos`
4. Railway detects the `railway/railway.toml` config

### Step 2: Add Plugins

1. In the Railway project, click **+ New** → **Database** → **PostgreSQL**
2. Click **+ New** → **Database** → **Redis**
3. Railway auto-sets `DATABASE_URL` and `REDIS_URL` environment variables

### Step 3: Create Backend Service

1. Click **+ New** → **GitHub Repo** → select the repo
2. Set **Root Directory** to `download/mastery-engine`
3. Set **Build Command**: `cd backend && pip install -e .`
4. Set **Start Command**: `cd backend && python -m scripts.railway.startup_backend`
5. Add environment variables (see `railway/RAILWAY_ENV_VARS.md`)

### Step 4: Create Worker Service

1. Click **+ New** → **GitHub Repo** → select the repo
2. Set **Root Directory** to `download/mastery-engine`
3. Set **Build Command**: `cd backend && pip install -e .`
4. Set **Start Command**: `cd backend && python -m scripts.railway.startup_worker`
5. Reference backend variables: `${{backend.APP_ENV}}`, `${{backend.DATABASE_URL}}`, etc.

### Step 5: Create Frontend Service

1. Click **+ New** → **GitHub Repo** → select the repo
2. Set **Root Directory** to `download/mastery-engine`
3. Set **Build Command**: `cd frontend && npm ci && npm run build`
4. Set **Start Command**: `cd frontend && npm start`
5. Set `NEXT_PUBLIC_API_URL` to the backend's Railway URL

### Step 6: Generate JWT RSA Keys

```bash
openssl genrsa -out jwt-private.pem 4096
openssl rsa -in jwt-private.pem -pubout -out jwt-public.pem
```

Copy the contents to Railway environment variables:
- `JWT_PRIVATE_KEY` — contents of jwt-private.pem (replace newlines with `\n`)
- `JWT_PUBLIC_KEY` — contents of jwt-public.pem (replace newlines with `\n`)
- `JWT_KEYS_DIR` — set to `/app/keys`

### Step 7: Configure GitHub CD

Add these secrets to the GitHub repo (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `RAILWAY_TOKEN` | Railway API token |
| `RAILWAY_PROJECT_ID` | Project ID from Railway |
| `RAILWAY_BACKEND_SERVICE_ID` | Backend service ID |
| `RAILWAY_WORKER_SERVICE_ID` | Worker service ID |
| `RAILWAY_FRONTEND_SERVICE_ID` | Frontend service ID |
| `RAILWAY_BACKEND_URL` | `https://masteryos-backend.up.railway.app` |
| `RAILWAY_FRONTEND_URL` | `https://masteryos-frontend.up.railway.app` |

### Step 8: Deploy

Push to `main`:
```bash
git push origin main
```

GitHub Actions will:
1. Run tests
2. Deploy backend (waits for health check)
3. Deploy worker
4. Deploy frontend (waits for health check)
5. Verify the full deployment

## Automatic Database Migrations

The `startup_backend.py` script handles migrations automatically:

```
Service starts
    ↓
Wait for PostgreSQL (30 retries, 2s delay)
    ↓
Wait for Redis (15 retries, 2s delay, non-fatal)
    ↓
Run Alembic migrations (alembic upgrade head)
    ↓  ↘ (fallback if no migrations)
    ↓    Run SQL init scripts (00-05)
    ↓
Verify schema (check critical tables exist)
    ↓
Start uvicorn (FastAPI)
```

If migrations fail → the script exits with code 1 → Railway marks the deployment as failed → no bad code goes live.

## Health Checks

| Service | Endpoint | Railway Config |
|---|---|---|
| Backend | `GET /api/v1/health` | `healthcheckPath: /api/v1/health` |
| Backend Ready | `GET /api/v1/health/ready` | (checked by startup script) |
| Frontend | `GET /` | `healthcheckPath: /` |
| Worker | Heartbeat table | (no HTTP — Railway checks process liveness) |

## Observability

### Logs
- **Where**: Railway dashboard → Service → **Logs** tab
- **What**: Real-time stdout/stderr from each service
- **Search**: Filter by service, time range, text

### Metrics
- **Where**: Railway dashboard → Service → **Metrics** tab
- **What**: CPU, Memory, Network per service
- **Alerts**: Railway Pro can send alerts on high usage

### Deployments
- **Where**: Railway dashboard → Service → **Deployments** tab
- **What**: Version history with rollback button
- **Click any previous deployment → "Redeploy"** for instant rollback

### Health Status
- **Where**: Railway dashboard → Service overview
- **What**: Green (healthy) / Yellow (deploying) / Red (failed)

## Cost Estimates

| Users | Backend | Worker | Frontend | Postgres | Redis | Total/month |
|---|---|---|---|---|---|---|
| 20 (beta) | $7 | $5 | $5 | $5 | $3 | **~$25** |
| 100 | $15 | $10 | $7 | $10 | $5 | **~$47** |
| 500 | $31 | $20 | $15 | $20 | $10 | **~$96** |
| 1000 | $62 | $40 | $31 | $35 | $15 | **~$183** |

### Cost Optimization Tips

1. **Enable sleeping** on non-critical services (worker can sleep when no jobs)
2. **Use shared CPU** (1x is enough for 20 beta users)
3. **Reduce pool sizes** (DATABASE_POOL_SIZE=5, DATABASE_MAX_OVERFLOW=10)
4. **Disable AI** (AI_ENABLED=false — saves the most resources)
5. **Use Railway's free tier** ($5 credit covers ~6 hours of full stack)

## Rollback Strategy

### Automatic Rollback (via GitHub Actions)
The CD pipeline runs health checks after each deploy. If health checks fail:
1. The GitHub Action exits with error code
2. Railway keeps the previous deployment running
3. You get a Slack/email notification

### Manual Rollback (via Railway Dashboard)
1. Go to Railway dashboard → Service → **Deployments**
2. Find the last known-good deployment (green checkmark)
3. Click **Redeploy**
4. Railway rolls back instantly (no rebuild needed)

### Database Rollback
```bash
# Connect to Railway PostgreSQL
railway connect postgres

# Run Alembic downgrade
cd backend && alembic downgrade -1
```

## Troubleshooting

### Backend won't start
- Check logs: Railway → Backend → Logs
- Common causes:
  - `DATABASE_URL` not set → add PostgreSQL plugin
  - `JWT_KEYS_DIR` points to missing files → set `JWT_PRIVATE_KEY` and `JWT_PUBLIC_KEY` env vars instead
  - Migration failure → check logs for SQL errors

### Worker won't start
- Check logs: Railway → Worker → Logs
- Common causes:
  - Can't connect to database → verify `DATABASE_URL` is referenced from backend
  - Can't connect to Redis → verify `REDIS_URL` is referenced from backend

### Frontend shows blank page
- Check `NEXT_PUBLIC_API_URL` is set to the backend's Railway URL
- Check browser console for CORS errors → verify `CORS_ORIGINS` includes the frontend URL
- Check that the build succeeded (Railway → Frontend → Deployments)

### Database migration fails
- Check if the SQL init scripts ran (they run as fallback)
- Check if schemas exist: `SELECT schema_name FROM information_schema.schemata`
- If tables are missing, manually run: `cd backend && alembic upgrade head`

## FAQ

**Q: Can I use a custom domain?**
A: Yes. Railway → Frontend → Settings → Networking → Add Custom Domain. Add CNAME in your DNS.

**Q: How do I run database commands?**
A: `railway connect postgres` opens a psql shell.

**Q: Can I scale to multiple workers?**
A: Yes. Railway → Worker → Settings → Replicas. Set to 2+ for HA.

**Q: What happens if PostgreSQL goes down?**
A: The backend health check fails → Railway auto-restarts it. The worker retry logic handles transient failures.

**Q: How do I see Sentry errors?**
A: Set `SENTRY_DSN` on the backend service. Errors appear in your Sentry dashboard.

## Backward Compatibility

This Railway deployment preserves 100% backward compatibility with the existing Docker Compose deployment. The same codebase, database schema, and API contracts are used — only the deployment infrastructure changes.
