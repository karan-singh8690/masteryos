export const metadata = {
  title: 'Deployment — MasteryOS',
  description: 'Deploy MasteryOS to Railway, Docker, or any cloud provider.',
}

export default function DeploymentPage() {
  return (
    <div className="prose prose-neutral max-w-none dark:prose-invert">
      <h1>Deployment Guide</h1>
      <p className="text-lg text-muted-foreground">
        MasteryOS supports multiple deployment options. Railway is the recommended path.
      </p>

      <h2>Railway Deployment (Recommended)</h2>
      <ol>
        <li>Create a Railway project</li>
        <li>Add PostgreSQL and Redis plugins</li>
        <li>Deploy 3 services from the monorepo:
          <ul>
            <li><strong>Backend:</strong> <code>cd backend && pip install -e . && python -m scripts.railway.startup_backend</code></li>
            <li><strong>Worker:</strong> <code>cd backend && python -m scripts.railway.startup_worker</code></li>
            <li><strong>Frontend:</strong> <code>bun install && bun run build && node .next/standalone/server.js</code></li>
          </ul>
        </li>
        <li>Set environment variables (see <code>RAILWAY_ENV_VARS.md</code>)</li>
        <li>Configure custom domain + SSL</li>
      </ol>

      <h2>Docker Compose (Self-Hosted)</h2>
      <pre className="bg-muted p-4 rounded-lg text-sm">{`# Development
docker compose up -d

# Production
docker compose -f docker-compose.prod.yml up -d`}</pre>

      <h2>Environment Variables</h2>
      <p>Required for production:</p>
      <ul>
        <li><code>DATABASE_URL</code> — PostgreSQL connection string</li>
        <li><code>REDIS_URL</code> — Redis connection string</li>
        <li><code>JWT_KEYS_DIR</code> — Directory containing <code>private.pem</code> + <code>public.pem</code></li>
        <li><code>JWT_ISSUER</code> — JWT issuer (e.g., <code>masteryos.com</code>)</li>
        <li><code>JWT_AUDIENCE</code> — JWT audience</li>
        <li><code>CORS_ORIGINS</code> — Allowed CORS origins</li>
        <li><code>FRONTEND_BASE_URL</code> — Frontend URL for email links</li>
        <li><code>CLOSED_BETA_ENABLED</code> — Enable invite-only registration</li>
        <li><code>SMTP_HOST</code> / <code>SMTP_PORT</code> / <code>SMTP_USERNAME</code> / <code>SMTP_PASSWORD</code></li>
        <li><code>SENTRY_DSN</code> — Error tracking (optional)</li>
      </ul>

      <h2>JWT Key Generation</h2>
      <pre className="bg-muted p-4 rounded-lg text-sm">{`# Generate RSA key pair for JWT signing
openssl genrsa -out private.pem 3072
openssl rsa -in private.pem -pubout -out public.pem

# Set JWT_KEYS_DIR to the directory containing these files`}</pre>

      <h2>Database Migrations</h2>
      <p>The backend automatically runs migrations on startup via <code>startup_backend.py</code>:</p>
      <ol>
        <li>Wait for PostgreSQL + Redis</li>
        <li>Run Alembic migrations (if versions exist)</li>
        <li>Fallback to SQL init scripts</li>
        <li>Verify schema</li>
        <li>Start uvicorn</li>
      </ol>

      <h2>Health Checks</h2>
      <ul>
        <li><code>GET /api/v1/health</code> — Liveness</li>
        <li><code>GET /api/v1/health/ready</code> — Readiness (DB + Redis)</li>
        <li><code>GET /api/v1/health/live</code> — Liveness alias</li>
      </ul>

      <h2>Rollback</h2>
      <p>Railway supports one-click rollback to any previous deployment. For database rollback, use:</p>
      <pre className="bg-muted p-4 rounded-lg text-sm">{`alembic downgrade -1`}</pre>
    </div>
  )
}
