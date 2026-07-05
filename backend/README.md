# Backend — Mastery Engine API

> FastAPI backend with Clean Architecture, Python 3.13.

## Structure

```
backend/
├── app/
│   ├── domain/              # Domain layer (pure business logic, no I/O)
│   │   ├── identity/        # User authentication, sessions
│   │   ├── learning/        # Enrollments, study sessions, goals
│   │   ├── assessment/      # Attempts, answers, scoring
│   │   ├── mastery/         # Mastery scores, reviews, algorithm versions
│   │   ├── content/         # Subjects, concepts, templates, versions
│   │   ├── scheduling/      # Adaptive queues, daily queues, configs
│   │   ├── analytics/       # Snapshots, statistics
│   │   ├── billing/         # Subscriptions, invoices
│   │   └── administration/  # Audit logs, feature flags, settings
│   ├── application/         # Application layer (use case orchestration, DTOs)
│   │   └── (same sub-contexts as domain)
│   ├── infrastructure/      # Infrastructure layer (database, cache, events)
│   │   ├── database.py      # Async SQLAlchemy engine + session
│   │   ├── persistence/     # Repository implementations
│   │   ├── cache/           # Redis client
│   │   ├── events/          # Outbox + event bus
│   │   ├── external/        # External service clients (Stripe, OAuth)
│   │   └── config/          # Infrastructure config
│   ├── presentation/        # Presentation layer (HTTP transport)
│   │   ├── api/
│   │   │   └── health.py    # Health check endpoints
│   │   └── middleware/
│   │       └── correlation.py  # Request/correlation ID middleware
│   ├── shared/              # Shared kernel
│   │   ├── config.py        # Pydantic Settings (env-based config)
│   │   ├── logging.py       # Structlog configuration
│   │   └── exceptions.py    # Base exception hierarchy
│   └── main.py              # Application factory + entry point
├── tests/
│   ├── test_health.py       # Health endpoint tests
│   ├── test_config.py       # Configuration tests
│   └── test_middleware.py   # Correlation middleware tests
├── alembic/                 # Database migrations
│   ├── env.py
│   └── versions/
├── pyproject.toml           # Dependencies + pytest config
├── ruff.toml                # Linter + formatter config
├── mypy.ini                 # Type checker config
├── alembic.ini              # Alembic config
└── README.md                # This file
```

## Development

```bash
# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run the server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest

# Lint
ruff check .
ruff format --check .

# Type check
mypy app

# Run migrations
alembic upgrade head
```

## Health Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/health` | Liveness — process is running |
| `GET /api/v1/health/ready` | Readiness — dependencies connected |
| `GET /api/v1/health/live` | Liveness (Kubernetes alias) |

## Architecture

This backend follows **Clean Architecture** (ADR-0005) with **Domain-Driven Design** (ADR-0006):

- **Domain layer**: pure Python, no I/O, no framework dependencies.
- **Application layer**: orchestrates domain services via repositories; defines transaction boundaries.
- **Infrastructure layer**: database, cache, external services.
- **Presentation layer**: FastAPI routes, middleware, DTOs.

Dependencies flow inward: presentation → application → domain. The domain depends on nothing outside itself.

## Configuration

All configuration is environment-based (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | development | Environment (development, testing, staging, production) |
| `DATABASE_URL` | postgresql+asyncpg://... | Async PostgreSQL URL |
| `REDIS_HOST` | localhost | Redis host |
| `JWT_SECRET_KEY` | changeme... | JWT signing secret (MUST override in production) |
| `CORS_ORIGINS` | localhost:3000,8000 | Allowed CORS origins |
