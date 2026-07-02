# Mastery Engine

> A Learning Operating System that determines the single highest-value learning activity for every user based on measurable mastery.
>
> **Status:** Foundation scaffold — ready for feature implementation.
> **First tenant:** Python Technical Interview Preparation.

---

## What is this?

Mastery Engine is an adaptive learning platform built around a simple question:

> Given everything we know about this learner right now, what should they study next?

This repository is the **production monorepo** containing the backend, frontend, infrastructure, and documentation for the Mastery Engine.

## Repository Structure

```
mastery-engine/
├── backend/          # FastAPI backend (Clean Architecture, Python 3.13)
├── frontend/         # Next.js frontend (TypeScript, Tailwind CSS, App Router)
├── docs/             # Architecture specs, ADRs, glossary, API contract, DB design
├── infrastructure/   # Docker, Nginx, PostgreSQL, Redis, monitoring
├── packages/         # Shared packages (future: types, contracts)
├── scripts/          # Utility scripts
├── tests/            # End-to-end and integration tests
├── .github/          # CI/CD workflows
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 20+ (LTS)
- Docker and Docker Compose
- Make (optional, for convenience commands)

### Using Docker Compose (recommended)

```bash
# Copy environment template
cp .env.example .env

# Start all services
make up

# Or with docker-compose directly
docker compose up -d

# Check health
curl http://localhost:8000/health
curl http://localhost:3000
```

### Local Development

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Documentation

| Document | Location |
|---|---|
| Architecture Specification | `docs/mastery-engine-architecture-spec.md` |
| Ubiquitous Language | `docs/domain/ubiquitous-language.md` |
| ADR Repository | `docs/adr/` |
| Database Architecture | `docs/database/` |
| Domain Behavior | `docs/domain-behavior/` |
| API Contract | `docs/api/` |

## Make Commands

```bash
make up          # Start all services (Docker Compose)
make down        # Stop all services
make build       # Build all images
make backend     # Run backend in development mode
make frontend    # Run frontend in development mode
make lint        # Lint all code (backend + frontend)
make test        # Run all tests
make format      # Format all code
make migrate     # Run database migrations
make shell       # Open a shell in the backend container
make logs        # Tail logs from all services
make clean       # Remove containers, volumes, and build artifacts
```

## Tech Stack

### Backend
- **Language:** Python 3.13
- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.x
- **Migrations:** Alembic
- **Validation:** Pydantic v2
- **Server:** Uvicorn
- **Testing:** Pytest, httpx
- **Linting:** Ruff, MyPy
- **Logging:** Structlog

### Frontend
- **Framework:** Next.js (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Data fetching:** React Query
- **Validation:** Zod
- **Forms:** React Hook Form
- **Linting:** ESLint, Prettier

### Infrastructure
- **Database:** PostgreSQL 16
- **Cache:** Redis 7
- **Reverse proxy:** Nginx
- **Monitoring:** Prometheus, Grafana
- **Containerization:** Docker, Docker Compose

## Development Workflow

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes following the coding standards (see `docs/adr/` and `docs/domain/ubiquitous-language.md`)
3. Run linting and tests: `make lint && make test`
4. Create a pull request (requires approval and passing CI)
5. Squash-merge to `main`

## License

Proprietary. See `LICENSE`.

---

*Built for the next decade of adaptive learning.*
