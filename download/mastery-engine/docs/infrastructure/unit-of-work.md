# Unit of Work

> How AsyncUnitOfWork manages transactions and event publishing.

---

## Interface (Application Layer)

```python
class UnitOfWork(ABC):
    async def __aenter__(self) -> UnitOfWork: ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
    async def commit(self) -> list[DomainEvent]: ...
    async def rollback(self) -> None: ...

    @property
    def users(self) -> UserRepository: ...
    @property
    def attempts(self) -> AttemptRepository: ...
    # ... all repositories
```

## Implementation (Infrastructure Layer)

```python
class AsyncUnitOfWork:
    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._session = None

    async def __aenter__(self):
        self._session = self._session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self._session.rollback()
        elif not self._committed:
            await self._session.commit()  # auto-commit
        await self._session.close()

    async def commit(self):
        await self._session.commit()
        self._committed = True

    async def rollback(self):
        await self._session.rollback()
        self._committed = True  # prevent auto-commit

    @property
    def users(self):
        return SqlAlchemyUserRepository(self._session)
```

## Transaction Flow

```
1. async with self._uow as uow:
2.     user = await uow.users.get_by_id(id)        # SELECT within transaction
3.     user.verify_email()                          # Domain behavior; collects events
4.     await uow.users.save(user)                   # UPDATE within transaction
5.     events = user.collect_events()               # Collect from aggregate
6.     # Write events to outbox (same transaction)
7.     await OutboxEventWriter.write_events(uow._session, events, "identity")
8.     await uow.commit()                           # COMMIT transaction
9. await self._event_publisher.publish_many(events) # Publish AFTER commit
```

## Key Properties

1. **Single session per UoW** — all repositories share the same AsyncSession.
2. **Auto-commit on exit** — if no exception and no explicit commit, the UoW auto-commits.
3. **Auto-rollback on exception** — if an exception occurs, the UoW rolls back.
4. **Events in same transaction** — outbox events are written before commit, ensuring atomicity.
5. **Events published after commit** — the event publisher is called after `uow.commit()`, ensuring events reflect committed changes.

## Event Publishing Sequence

The event publisher (implemented by the infrastructure) writes events to the outbox table within the same transaction as the domain changes. After commit:

1. The outbox table contains the events (durable).
2. The outbox dispatcher (background worker) polls the outbox.
3. The dispatcher delivers events to subscribers.
4. The dispatcher marks events as dispatched.

If the dispatcher is briefly unavailable, events accumulate in the outbox and are delivered when it resumes. No events are lost.
