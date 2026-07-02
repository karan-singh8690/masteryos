# Handler Guidelines

> Patterns and rules for writing command and query handlers.

---

## Command Handler Checklist

Every command handler MUST:

1. **Validate the command** — check shape, presence, application-level constraints. Business invariants are in the domain; don't duplicate them.

2. **Use the Unit of Work** — all repository access within `async with self._uow as uow:`.

3. **Load aggregates** — use repository interfaces. Never construct aggregates from raw data; always load them via the repository so the domain manages invariants.

4. **Call domain behavior** — invoke methods on aggregates or domain services. The domain layer enforces invariants and records events.

5. **Persist** — `await uow.repo.save(aggregate)`. For append-only aggregates (Attempt), use `add` (no `save`).

6. **Collect events** — `events = aggregate.collect_events()`. Do this after all domain behavior is complete.

7. **Commit** — `await uow.commit()`. This makes changes durable.

8. **Publish events** — `await self._event_publisher.publish_many(events)`. After commit, so events reflect committed changes.

9. **Return DTO** — `CommandResult.ok(dto, events)`. Never return a domain entity.

## What Handlers Must NOT Do

- ❌ **Contain business rules** — if logic is a business rule, it belongs in the domain.
- ❌ **Access infrastructure directly** — no SQLAlchemy, no Redis, no HTTP.
- ❌ **Call other command handlers** — use Application Services for multi-step workflows.
- ❌ **Return domain entities** — always map to DTOs.
- ❌ **Make decisions the domain should make** — e.g., don't compute mastery in the handler; call the MasteryCalculator.
- ❌ **Skip the Unit of Work** — all persistence goes through the UoW for transactional integrity.

## Query Handler Checklist

1. **Read-only** — never modify state.
2. **Use the Unit of Work** — for repository access.
3. **Apply authorization** — check that the current user can access the requested data.
4. **Build DTOs** — never return domain entities.
5. **No events** — queries don't produce events.

## Error Handling

```python
async def handle(self, command: TCommand) -> CommandResult[TResult]:
    # Validation error → CommandResult.fail with VALIDATION_FAILED
    if not valid:
        return CommandResult.fail("...", "VALIDATION_FAILED")

    async with self._uow as uow:
        # Resource not found → CommandResult.fail with RESOURCE_MISSING
        aggregate = await uow.repo.get_by_id(id)
        if aggregate is None:
            return CommandResult.fail("...", "RESOURCE_NOT_FOUND")

        # Domain error → CommandResult.fail with domain error code
        try:
            aggregate.do_something()
        except InvalidStateTransition as exc:
            return CommandResult.fail(str(exc), "INVALID_STATE_TRANSITION")

        await uow.repo.save(aggregate)
        events = aggregate.collect_events()
        await uow.commit()

    await self._event_publisher.publish_many(events)
    return CommandResult.ok(Mapper.to_dto(aggregate), events)
```

## Handler Constructor

```python
class MyCommandHandler(CommandHandler[MyCommand, MyDTO]):
    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher
```

Handlers depend on:
- `UnitOfWork` — for transactional repository access.
- `EventPublisher` — for publishing domain events after commit.
- (Optional) Domain services — if the handler orchestrates a domain service (e.g., MasteryCalculator).

Handlers do NOT depend on:
- Concrete repositories (the UoW provides them).
- Infrastructure (no SQLAlchemy, no Redis).
- Other handlers (use Application Services for cross-handler workflows).
