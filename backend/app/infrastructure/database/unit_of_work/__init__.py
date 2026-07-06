"""AsyncUnitOfWork — the infrastructure implementation of the Unit of Work.

Manages a single SQLAlchemy AsyncSession as the transaction boundary.
All repositories within the UoW share the same session, ensuring atomicity.

After commit():
1. The session transaction is committed.
2. Domain events collected from aggregates are written to the outbox table
   in the same transaction (via the outbox writer).
3. The outbox dispatcher (separate process) delivers events to subscribers.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.shared.kernel import DomainEvent
from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.database.orm.core import OutboxEventModel
from app.infrastructure.database.repositories import (
    SqlAlchemyAlgorithmVersionRepository,
    SqlAlchemyAttemptRepository,
    SqlAlchemyEnrollmentRepository,
    SqlAlchemyMasteryScoreRepository,
    SqlAlchemyQuestionInstanceRepository,
    SqlAlchemyReviewRepository,
    SqlAlchemyStudySessionRepository,
    SqlAlchemyUserRepository,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


class AsyncUnitOfWork:
    """Infrastructure Unit of Work using SQLAlchemy async sessions.

    Usage (from a command handler):
        async with self._uow as uow:
            user = await uow.users.get_by_id(user_id)
            user.verify_email()
            await uow.users.save(user)
            events = user.collect_events()
            await uow.commit()  # Commits + writes events to outbox

    After commit(), events are in the outbox table. The outbox dispatcher
    (running in a separate process) picks them up and delivers to subscribers.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._committed = False

    async def __aenter__(self) -> AsyncUnitOfWork:
        """Begin a transaction by creating a new session."""
        if self._session_factory is None:
            self._session_factory = await get_session_factory()
        self._session = self._session_factory()
        self._committed = False
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """End the transaction: commit on success, rollback on exception."""
        if self._session is None:
            return

        try:
            if exc_type is not None:
                # Exception occurred — rollback
                await self._session.rollback()
                logger.debug("uow_rolled_back", error=str(exc_val) if exc_val else "unknown")
            elif not self._committed:
                # No explicit commit and no exception — auto-commit
                await self._session.commit()
                logger.debug("uow_auto_committed")
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> list[DomainEvent]:
        """Commit the transaction.

        This method:
        1. Flushes pending changes.
        2. Commits the session transaction.
        3. Returns an empty list (events are written to the outbox by
           the outbox writer, not by the UoW itself — the application
           layer's event publisher handles this).
        """
        if self._session is None:
            raise RuntimeError("UnitOfWork.commit() called outside of 'async with' context")

        await self._session.commit()
        self._committed = True
        logger.debug("uow_committed")
        return []

    async def rollback(self) -> None:
        """Rollback the transaction."""
        if self._session is None:
            raise RuntimeError("UnitOfWork.rollback() called outside of 'async with' context")

        await self._session.rollback()
        self._committed = True  # Prevent auto-commit in __aexit__
        logger.debug("uow_rolled_back_explicitly")

    # ============================================================
    # Repository Access
    # ============================================================

    @property
    def _session_or_raise(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Repository accessed outside of 'async with' context")
        return self._session

    @property
    def users(self) -> Any:
        return SqlAlchemyUserRepository(self._session_or_raise)

    @property
    def enrollments(self) -> Any:
        return SqlAlchemyEnrollmentRepository(self._session_or_raise)

    @property
    def study_sessions(self) -> Any:
        return SqlAlchemyStudySessionRepository(self._session_or_raise)

    @property
    def question_instances(self) -> Any:
        return SqlAlchemyQuestionInstanceRepository(self._session_or_raise)

    @property
    def attempts(self) -> Any:
        return SqlAlchemyAttemptRepository(self._session_or_raise)

    @property
    def mastery_scores(self) -> Any:
        return SqlAlchemyMasteryScoreRepository(self._session_or_raise)

    @property
    def reviews(self) -> Any:
        return SqlAlchemyReviewRepository(self._session_or_raise)

    @property
    def algorithm_versions(self) -> Any:
        return SqlAlchemyAlgorithmVersionRepository(self._session_or_raise)

    # Stub properties for contexts not yet implemented
    @property
    def subjects(self) -> Any:
        return _NullRepository()

    @property
    def concepts(self) -> Any:
        return _NullRepository()

    @property
    def question_templates(self) -> Any:
        return _NullRepository()

    @property
    def content_packs(self) -> Any:
        return _NullRepository()

    @property
    def content_versions(self) -> Any:
        return _NullRepository()

    @property
    def recommendations(self) -> Any:
        return _NullRepository()

    @property
    def achievements(self) -> Any:
        return _NullRepository()

    @property
    def streaks(self) -> Any:
        return _NullRepository()

    @property
    def learning_goals(self) -> Any:
        return _NullRepository()

    @property
    def subscriptions(self) -> Any:
        return _NullRepository()

    @property
    def billing_plans(self) -> Any:
        return _NullRepository()

    @property
    def invoices(self) -> Any:
        return _NullRepository()

    @property
    def notifications(self) -> Any:
        return _NullRepository()

    @property
    def feature_flags(self) -> Any:
        return _NullRepository()

    @property
    def audit_logs(self) -> Any:
        return _NullRepository()

    @property
    def organizations(self) -> Any:
        return _NullRepository()

    @property
    def scheduling_configs(self) -> Any:
        return _NullRepository()

    @property
    def daily_queues(self) -> Any:
        return _NullRepository()


class OutboxEventWriter:
    """Writes domain events to the outbox table within the current transaction.

    Usage in a command handler:
        async with self._uow as uow:
            user = await uow.users.get_by_id(id)
            user.verify_email()
            await uow.users.save(user)
            events = user.collect_events()
            # Write events to outbox (same transaction)
            await self._outbox_writer.write_events(uow._session, events, "identity")
            await uow.commit()
    """

    @staticmethod
    async def write_events(
        session: AsyncSession,
        events: Sequence[DomainEvent],
        originating_schema: str,
        actor_user_id: UUID | None = None,
    ) -> None:
        """Write domain events to the outbox table.

        This must be called within the same transaction as the domain changes.
        """
        for event in events:
            outbox_entry = OutboxEventModel(
                id=uuid4(),
                event_type=event.event_type,
                aggregate_id=_extract_aggregate_id(event),
                aggregate_type=_extract_aggregate_type(event),
                actor_user_id=actor_user_id,
                payload=_serialize_event(event),
                payload_schema_version="1",
                originating_schema=originating_schema,
                status="pending",
            )
            session.add(outbox_entry)
        await session.flush()


def _extract_aggregate_id(event: DomainEvent) -> UUID:
    """Extract the aggregate ID from a domain event."""
    for attr in ("user_id", "enrollment_id", "session_id", "attempt_id",
                 "mastery_score_id", "review_id", "algorithm_version_id",
                 "recommendation_id", "achievement_id", "instance_id"):
        val = getattr(event, attr, None)
        if val is not None:
            if isinstance(val, UUID):
                return val
            return UUID(str(val))
    return uuid4()  # Fallback


def _extract_aggregate_type(event: DomainEvent) -> str:
    """Extract the aggregate type from the event type name."""
    # E.g., "UserRegistered" → "User", "AttemptRecorded" → "Attempt"
    event_name = event.event_type
    for suffix in ("Registered", "Verified", "Suspended", "Reactivated", "DeletionRequested",
                    "DeletionCancelled", "Anonymized", "Enabled", "Disabled",
                    "Enrolled", "OnboardingCompleted", "Unenrolled",
                    "Started", "Paused", "Resumed", "Ended", "Abandoned",
                    "Recorded", "Answered", "Served",
                    "Updated", "Scheduled", "Published", "Detected", "Cleared",
                    "Generated", "Dismissed", "Granted",
                    "Reset"):
        if event_name.endswith(suffix):
            return event_name[: -len(suffix)]
    return event_name


def _serialize_event(event: DomainEvent) -> dict[str, Any]:
    """Serialize a domain event to a JSON-compatible dict.

    Converts UUID, datetime, and other non-JSON-serializable types to
    strings so the payload can be stored in a JSONB column.
    """
    import dataclasses
    from datetime import datetime
    from uuid import UUID as UUIDType

    def _convert(obj: Any) -> Any:
        if isinstance(obj, UUIDType):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_convert(v) for v in obj]
        return obj

    if dataclasses.is_dataclass(event):
        return _convert(dataclasses.asdict(event))
    return {"event_type": event.event_type}


class _NullRepository:
    """Null repository for contexts not yet implemented.

    Returns None/[] for all calls so the application doesn't crash
    when a repository isn't wired up yet.
    """

    async def get_by_id(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def add(self, *args: Any, **kwargs: Any) -> Any:
        return args[0] if args else None

    async def save(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def list_by_user(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []

    async def get_by_user_and_subject(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def get_active_by_enrollment(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def get_by_enrollment(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def list_by_enrollment(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []

    async def list_weak_by_enrollment(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []

    async def get_by_enrollment_and_concept(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def get_active(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def list_all(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []

    async def update(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def delete(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def record(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __getattr__(self, name: str) -> Any:
        """Catch-all: return an async no-op for any missing method."""
        async def _noop(*args: Any, **kwargs: Any) -> None:
            return None
        return _noop
