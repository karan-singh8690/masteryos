# Transaction Boundaries

> How transactions are managed in the application layer via the Unit of Work.

---

## Transaction Model

Every command handler operates within a single transaction:

```python
async with self._uow as uow:
    # All repository operations within this block are in one transaction
    user = await uow.users.get_by_id(user_id)
    user.verify_email()
    await uow.users.save(user)
    events = user.collect_events()
    await uow.commit()  # Commits the transaction
```

If any operation within the `async with` block raises an exception:
- The transaction is rolled back (no changes persisted).
- No events are published.
- A failure `CommandResult` is returned.

## Unit of Work Interface

```python
class UnitOfWork(ABC):
    async def __aenter__(self) -> UnitOfWork: ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
    async def commit(self) -> list[DomainEvent]: ...
    async def rollback(self) -> None: ...

    # Repository access (all within the same transaction)
    @property
    def users(self) -> UserRepository: ...
    @property
    def enrollments(self) -> EnrollmentRepository: ...
    # ... all repositories
```

## Transaction Boundary Rules

1. **One transaction per command handler.** A command handler's `handle()` method uses exactly one `async with self._uow` block.

2. **Events are published AFTER commit.** The handler collects events from aggregates, commits the transaction, then publishes events. This ensures events are only published for changes that were actually persisted.

3. **No nested transactions.** A handler does not call another handler that opens its own transaction. If a workflow needs multiple commands, use an Application Service that coordinates multiple handlers — each with its own transaction.

4. **Read-only queries use the UoW but don't commit.** Query handlers open a UoW for repository access but never call `commit()`.

5. **Optimistic concurrency** is handled at the domain level (MasteryScore's `version` field). The handler retries on conflict (max 3 retries).

## Event Publishing Sequence

```
1. async with self._uow as uow:
2.     aggregate = await uow.repo.get_by_id(id)
3.     aggregate.do_something()  # Domain behavior; collects events
4.     await uow.repo.save(aggregate)
5.     events = aggregate.collect_events()
6.     await uow.commit()  # Transaction committed; data is durable
7. await self._event_publisher.publish_many(events)  # Events published AFTER commit
```

This sequence guarantees:
- Events are only published for committed changes.
- If the transaction fails, no events are published.
- If event publishing fails, the data is still committed (the outbox dispatcher will retry).
