# Application Layer — Mastery Engine

> **Status:** v1.0 — Authoritative source for the application layer.
> **Owner:** Principal Engineer
> **Depends on:** Domain Layer (Task 008)

---

## What This Is

The Application Layer orchestrates domain behavior. It contains no business rules; those live in the domain layer. The application layer's job is to:

1. **Receive commands and queries** from the presentation layer.
2. **Validate** command shape and application-level constraints.
3. **Load aggregates** via repository interfaces (through the Unit of Work).
4. **Call domain behavior** — entities, domain services.
5. **Persist** via the Unit of Work (transactional).
6. **Collect and publish domain events** via the Event Publisher.
7. **Return DTOs** — never domain entities.

## Document Index

| File | Topic |
|---|---|
| `README.md` | This file — overview and architecture. |
| `command-catalog.md` | Every command with its handler and DTO. |
| `query-catalog.md` | Every query with its handler and response DTO. |
| `application-services.md` | Orchestration services for multi-handler workflows. |
| `transaction-boundaries.md` | How transactions are managed via the Unit of Work. |
| `handler-guidelines.md` | Patterns and rules for writing command/query handlers. |

## Architecture

```
Presentation (FastAPI) → Application Layer → Domain Layer
                              ↓
                        Unit of Work (ABC)
                              ↓
                        Repository Interfaces (ABCs)
                              ↓
                        Infrastructure (SQLAlchemy, Redis)
```

## Key Abstractions

### Unit of Work (ABC)
- Defines transaction boundaries (`__aenter__`, `__aexit__`, `commit`, `rollback`).
- Provides access to all repositories within a transaction.
- Infrastructure provides the concrete implementation (SQLAlchemy async session).

### Event Publisher (ABC)
- Publishes domain events after a successful commit.
- Infrastructure provides the concrete implementation (outbox table + dispatcher).

### Authorization (ABCs)
- `CurrentUserProvider`: identifies the authenticated user.
- `PermissionChecker`: checks role-based and resource-level permissions.
- `AuthorizationService`: high-level authorization (require_authenticated, require_role, require_owner_or_admin).

### Command Handler (ABC)
- Each command has exactly one handler.
- Handler validates, loads, calls domain, persists, publishes events, returns DTO.
- Handlers NEVER contain business rules.

### Query Handler (ABC)
- Each query has exactly one handler.
- Handler reads from repositories, builds DTOs, returns.
- Query handlers NEVER modify state.

## Testing

The application layer is fully testable with **fake repositories** and a **fake Unit of Work** (see `tests/application/fakes.py`). No database, no HTTP, no infrastructure needed.

```python
uow = FakeUnitOfWork()
publisher = FakeEventPublisher()
handler = RegisterUserHandler(uow, publisher)
result = await handler.handle(RegisterUserCommand(...))
assert result.success
```

## Purity Guarantee

The application layer contains:
- ✅ Domain layer imports
- ✅ Python stdlib
- ❌ No SQLAlchemy, FastAPI, Pydantic, or Redis
- ❌ No HTTP handlers
- ❌ No SQL
- ❌ No database queries
