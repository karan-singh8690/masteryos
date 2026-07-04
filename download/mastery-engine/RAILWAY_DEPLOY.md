# Deploying MasteryOS on Railway

> Railway supports Docker Compose natively — each service in `docker-compose.railway.yml` becomes a separate Railway service with its own URL and scaling.

## Quick Start (5 minutes)

### Option A: Via Railway Dashboard (easiest)

1. **Go to [railway.app](https://railway.app)** → New Project → Deploy from GitHub Repo
2. Select your repo: `karan-singh8690/masteryos`
3. Railway detects `docker-compose.railway.yml` in `download/mastery-engine/`
4. Railway creates 5 services automatically:
   - `postgres` — PostgreSQL 16
   - `redis` — Redis 7
   - `backend` — FastAPI API
   - `worker` — Background worker
   - `frontend` — Next.js app
5. Set environment variables (see below)
6. Railway builds and deploys everything

### Option B: Via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Go to the project directory
cd /home/z/my-project/download/mastery-engine

# Create a new Railway project
railway init

# Deploy using the Railway Docker Compose
railway up --service postgres
railway up --service redis
railway up --service backend
railway up --service worker
railway up --service frontend
```

## Required Environment Variables

Set these in the Railway dashboard (Project Settings → Variables):

### Critical (required)
```
DATABASE_PASSWORD=<openssl rand -base64 32>
JWT_SECRET_KEY=<openssl rand -base64 32>
GRAFANA_PASSWORD=<openssl rand -base64 24>
```

### Backend
```
DATABASE_USER=mastery
DATABASE_NAME=mastery_engine
CORS_ORIGINS=https://your-frontend-url.up.railway.app
FRONTEND_BASE_URL=https://your-frontend-url.up.railway.app
ENABLE_DOCS=false
CLOSED_BETA_ENABLED=true
MAX_BETA_USERS=20
```

### SMTP (for email)
```
SMTP_HOST=smtp.postmarkapp.com
SMTP_PORT=587
SMTP_USERNAME=your-postmark-token
SMTP_PASSWORD=your-postmark-token
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@masteryos.com
```

### Frontend
```
NEXT_PUBLIC_API_URL=https://your-backend-url.up.railway.app
NEXT_PUBLIC_APP_NAME=MasteryOS
API_URL=https://your-backend-url.up.railway.app
```

### Optional
```
SENTRY_DSN=<your-sentry-dsn>
AI_ENABLED=false
```

## RSA Keys

Generate JWT keys before deploying the backend:

```bash
mkdir -p keys
openssl genrsa -out keys/jwt-private.pem 4096
openssl rsa -in keys/jwt-private.pem -pubout -out keys/jwt-public.pem
chmod 600 keys/jwt-private.pem
```

Railway will mount `./keys` as a volume in the backend container.

## Cost Estimate

| Service | RAM | Cost/month |
|---------|-----|------------|
| PostgreSQL | 512MB | ~$15 |
| Redis | 256MB | ~$7 |
| Backend | 512MB | ~$15 |
| Worker | 256MB | ~$7 |
| Frontend | 256MB | ~$7 |
| **Total** | | **~$51/month** |

Railway gives **$5 free credit** on signup (covers ~3 days).
After that, you pay only for what you use (per-second billing).

## Free Alternative

If you need completely free hosting, use **Oracle Cloud Always Free**:
- 24GB RAM ARM VM (free forever)
- Run the same `docker-compose.railway.yml` with `docker compose up -d`
- See `docs/operations/deployment-guide.md` for instructions

## After Deployment

1. **Get your Railway URLs** — each service gets a `*.up.railway.app` URL
2. **Update CORS_ORIGINS** — set to your frontend Railway URL
3. **Update NEXT_PUBLIC_API_URL** — set to your backend Railway URL
4. **Generate SSL** — Railway provides HTTPS automatically (no Caddyfile needed)
5. **Bootstrap admin user** — see `docs/beta/beta-launch-guide.md` §1.1
6. **Create beta invites** — see `docs/beta/beta-launch-guide.md` §2.2

## Custom Domain

To use `masteryos.com` instead of `*.up.railway.app`:

1. Go to Railway → Frontend service → Settings → Networking
2. Add custom domain: `masteryos.com`
3. Add CNAME record in your DNS: `masteryos.com → *.up.railway.app`
4. Railway handles SSL automatically

## Monitoring

Railway provides built-in:
- **Logs** — real-time logs for each service
- **Metrics** — CPU, memory, network per service
- **Deployments** — version history with one-click rollback
- **Health checks** — automatic restart on failure

For advanced monitoring (Prometheus + Grafana), deploy them as additional Railway services or use an external service like Grafana Cloud (free tier).
