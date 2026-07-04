# Railway Environment Variables — MasteryOS (Task 028)

> Complete reference for all environment variables needed on Railway.

## Railway-Provided Variables (auto-set by plugins)

| Variable | Source | Description |
|---|---|---|
| `DATABASE_URL` | PostgreSQL plugin | Connection string (postgresql://user:pass@host:port/db) |
| `REDIS_URL` | Redis plugin | Connection string (redis://:pass@host:port/0) |
| `PORT` | Railway | Port assigned to each service |

## Backend Service Variables

### Critical (required)

| Variable | Example | Description |
|---|---|---|
| `APP_ENV` | `production` | Application environment |
| `DATABASE_URL` | *(auto-set by plugin)* | PostgreSQL connection (auto-converted to +asyncpg) |
| `REDIS_URL` | *(auto-set by plugin)* | Redis connection (auto-parsed into host/port/password) |
| `JWT_SECRET_KEY` | `<random 32 chars>` | Required by compose guard (unused in RS256 but must be set) |
| `JWT_ALGORITHM` | `RS256` | JWT signing algorithm |
| `JWT_KEYS_DIR` | `/app/keys` | Path to RSA keypair directory |
| `CORS_ORIGINS` | `https://masteryos-frontend.up.railway.app` | Allowed CORS origins |
| `ENABLE_DOCS` | `false` | Disable OpenAPI docs in production |
| `CLOSED_BETA_ENABLED` | `true` | Enable invite-only registration |
| `MAX_BETA_USERS` | `20` | Maximum beta users |

### SMTP (required for email)

| Variable | Example | Description |
|---|---|---|
| `SMTP_HOST` | `smtp.postmarkapp.com` | SMTP server |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USERNAME` | `your-token` | SMTP username/API key |
| `SMTP_PASSWORD` | `your-token` | SMTP password/API key |
| `SMTP_USE_TLS` | `true` | Use STARTTLS |
| `SMTP_FROM_EMAIL` | `noreply@masteryos.com` | From email address |
| `SMTP_FROM_NAME` | `MasteryOS` | From display name |
| `FRONTEND_BASE_URL` | `https://masteryos-frontend.up.railway.app` | Frontend URL for email links |

### JWT RSA Keys (required for RS256)

Railway doesn't support file mounts, so keys must be provided as environment variables:

| Variable | Description |
|---|---|
| `JWT_PRIVATE_KEY` | RSA private key (PEM format, multi-line — use \n) |
| `JWT_PUBLIC_KEY` | RSA public key (PEM format, multi-line — use \n) |

Generate keys locally:
```bash
openssl genrsa -out jwt-private.pem 4096
openssl rsa -in jwt-private.pem -pubout -out jwt-public.pem
# Copy contents to Railway env vars (replace newlines with \n)
```

### Optional

| Variable | Example | Description |
|---|---|---|
| `SENTRY_DSN` | `https://...@sentry.io/...` | Error tracking |
| `AI_ENABLED` | `false` | Enable AI features |
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5:7b` | AI model name |
| `SENTRY_DSN` | *(empty)* | Sentry DSN |

## Worker Service Variables

The worker needs the **same** variables as the backend (it connects to the same database and Redis). In Railway, you can use "Reference Variables" to share them:

1. Define variables on the backend service
2. On the worker service, reference them: `${{backend.APP_ENV}}`

## Frontend Service Variables

| Variable | Example | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://masteryos-backend.up.railway.app` | Backend API URL (baked into JS at build time) |
| `NEXT_PUBLIC_APP_NAME` | `MasteryOS` | App name |
| `NEXT_PUBLIC_SITE_URL` | `https://masteryos-frontend.up.railway.app` | Frontend URL (for SEO) |
| `NEXT_PUBLIC_WS_URL` | `wss://masteryos-backend.up.railway.app/ws` | WebSocket URL |

## Railway Service Variables (for GitHub Actions CD)

Set these as GitHub repository secrets:

| Secret | Description |
|---|---|
| `RAILWAY_TOKEN` | Railway API token (get from railway.app → Account → Tokens) |
| `RAILWAY_PROJECT_ID` | Railway project ID |
| `RAILWAY_BACKEND_SERVICE_ID` | Backend service ID |
| `RAILWAY_WORKER_SERVICE_ID` | Worker service ID |
| `RAILWAY_FRONTEND_SERVICE_ID` | Frontend service ID |
| `RAILWAY_BACKEND_URL` | Backend public URL (for health checks) |
| `RAILWAY_FRONTEND_URL` | Frontend public URL (for health checks) |

## Variable Setup Order

1. Create Railway project + add PostgreSQL and Redis plugins
2. Note the `DATABASE_URL` and `REDIS_URL` from the plugins
3. Create backend service → set all backend variables
4. Create worker service → reference backend variables
5. Create frontend service → set `NEXT_PUBLIC_API_URL` to backend URL
6. Add GitHub secrets for CD pipeline
