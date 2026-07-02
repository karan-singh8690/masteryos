# Contributing to the Mastery Engine

> How to contribute to the Mastery Engine project.

## Getting Started

1. **Fork and clone** the repository.
2. **Read the docs**: start with the Architecture Specification (`docs/mastery-engine-architecture-spec.md`) and the Ubiquitous Language (`docs/domain/ubiquitous-language.md`).
3. **Set up your environment**: follow the Development Setup Guide (`docs/DEVELOPMENT.md`).
4. **Install pre-commit hooks**: `pre-commit install` (from the repo root).

## Development Workflow

### Branching

- Trunk-based development: short-lived branches merge into `main`.
- Branch naming: `<type>/<short-description>` (e.g., `feature/mastery-engine-v1`, `fix/health-endpoint-timeout`).
- Commit messages: Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`). The body explains *why*, not *what*.

### Pull Requests

A PR is mergeable when:
- All CI checks pass (lint, type check, tests, build, security scan).
- Reviewed by at least one engineer who did not author it.
- Includes tests for new behavior.
- Includes documentation updates where the public surface changed.
- Includes an ADR if it changes a documented architectural decision.
- The PR description explains what changed, why, and how to test it.

### Squash-and-Merge

PRs are squashed on merge to keep `main` history linear and reviewable.

## Coding Standards

### Backend (Python)

- **Ruff** for linting and formatting (`backend/ruff.toml`).
- **MyPy** for type checking (`backend/mypy.ini`, strict mode).
- **Clean Architecture**: domain layer is pure (no I/O); application layer orchestrates; infrastructure layer persists.
- **DDD**: each bounded context owns its code; cross-context communication is via domain events (not direct repository access).
- **Naming**: follows the Ubiquitous Language (Task 002).

### Frontend (TypeScript)

- **ESLint** (`next/core-web-vitals` config).
- **Prettier** with `prettier-plugin-tailwindcss`.
- **TypeScript** strict mode.
- **App Router** conventions (Server Components by default; Client Components only where interactivity requires).

### General

- Small files (max 400 lines; flag at 300).
- Small functions (max 50 lines; flag at 30).
- No `any` types without explicit justification.
- No business logic in Controllers or UI components.

## Testing

- **Unit tests**: domain services (pure functions, fast).
- **Integration tests**: repositories against real PostgreSQL.
- **API tests**: FastAPI TestClient.
- **E2E tests**: Playwright (future).
- **Load tests**: nightly against staging (future).

Coverage targets: 90% domain, 80% application, 70% infrastructure, 60% API.

## ADRs

Any non-obvious architectural decision requires an Architecture Decision Record (ADR) in `docs/adr/`. See `docs/adr/README.md` for the process.

## Ubiquitous Language

All code, documentation, UI labels, and conversations use the terms defined in the Ubiquitous Language (`docs/domain/ubiquitous-language.md`). If a term is ambiguous, open a glossary change request.

## Questions?

- Architecture: see `docs/adr/` or the Architecture Specification.
- API: see `docs/api/` or the OpenAPI spec.
- Database: see `docs/database/`.
- Domain behavior: see `docs/domain-behavior/`.
