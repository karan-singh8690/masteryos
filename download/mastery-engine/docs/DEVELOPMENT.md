# Development Setup Guide

> How to set up your local development environment for the Mastery Engine.

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.13+ | Backend |
| Node.js | 20+ (LTS) | Frontend |
| Docker | 24+ | Containerization |
| Docker Compose | 2+ | Multi-service orchestration |
| Make | 4+ | Convenience commands (optional) |
| Git | 2.40+ | Version control |

## Option 1: Docker Compose (recommended for quick start)

```bash
# Clone the repository
git clone https://github.com/masteryengine/mastery-engine.git
cd mastery-engine

# Copy environment template
cp .env.example .env

# Start all services
make up
# or: docker compose up -d

# Verify the backend is running
curl http://localhost:8000/api/v1/health
# Expected: {"status":"healthy","app":"mastery-engine","version":"0.1.0","timestamp":...}

# Open the frontend
open http://localhost:3000

# Stop all services
make down
# or: docker compose down
```

## Option 2: Local Development (hot reload)

### Backend

```bash
cd backend

# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run the server (with hot reload)
uvicorn app.main:app --reload --port 8000

# In another terminal, run tests
pytest

# Lint
ruff check .
ruff format --check .

# Type check
mypy app
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run the dev server (with hot reload)
npm run dev

# In another terminal:
npm run lint       # ESLint
npm run typecheck  # TypeScript
npm run build      # Production build
```

### Database (local PostgreSQL)

```bash
# Start only PostgreSQL and Redis
docker compose up -d postgres redis

# Run migrations
cd backend
alembic upgrade head
```

## Option 3: Full Docker with Hot Reload

The `docker-compose.yml` includes volume mounts for hot reload:

```bash
# Start all services with hot reload
docker compose up

# Backend: changes to backend/ reload uvicorn automatically
# Frontend: changes to frontend/ reload Next.js automatically
```

## Services Overview

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | FastAPI server |
| API Docs (Swagger) | http://localhost:8000/docs | OpenAPI UI |
| Frontend | http://localhost:3000 | Next.js app |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3001 | Dashboards (admin/admin) |
| Nginx | http://localhost:80 | Reverse proxy |

## Useful Make Commands

```bash
make help        # Show all available commands
make up          # Start all services
make down        # Stop all services
make lint        # Lint all code
make test        # Run all tests
make format      # Format all code
make migrate     # Run database migrations
make shell       # Shell into backend container
make logs        # Tail logs
make clean       # Clean everything
```

## Troubleshooting

### Port already in use

```bash
# Check what's using a port
lsof -i :8000
lsof -i :3000

# Kill the process or change the port in .env
```

### Database connection failed

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Check logs
docker compose logs postgres

# Reset the database (destructive)
docker compose down -v
docker compose up -d postgres
```

### Pre-commit hooks failing

```bash
# Run all hooks manually
pre-commit run --all-files

# Update hook versions
pre-commit autoupdate
```
