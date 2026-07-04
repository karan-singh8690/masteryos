"""Outbox dispatcher — polls the outbox table and delivers events to subscribers.

The dispatcher runs as a background worker. It:
1. Polls the outbox table for pending events.
2. Delivers each event to registered subscribers (in-process).
3. Marks events as dispatched (or dead-letters on repeated failure).

The dispatcher is idempotent: subscribers may receive the same event multiple
times (at-least-once delivery). Subscribers must be idempotent (ADR-0012).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Awaitable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database.orm.core import OutboxEventModel
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Type for subscriber handlers
SubscriberHandler = Callable[[dict[str, Any]], Awaitable[None]]


class OutboxDispatcher:
    """Polls the outbox table and delivers events to subscribers.

    Usage:
        dispatcher = OutboxDispatcher(session_factory)
        dispatcher.subscribe("AttemptRecorded", mastery_handler)
        dispatcher.subscribe("AttemptRecorded", analytics_handler)
        await dispatcher.run(poll_interval=1.0)
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        max_retries: int = 5,
        batch_size: int = 100,
    ) -> None:
        self._session_factory = session_factory
        self._max_retries = max_retries
        self._batch_size = batch_size
        self._subscribers: dict[str, list[SubscriberHandler]] = {}
        self._running = False

    def subscribe(self, event_type: str, handler: SubscriberHandler) -> None:
        """Register a subscriber for an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.info("subscriber_registered", event_type=event_type, handler=handler.__name__)

    async def run(self, poll_interval: float = 1.0) -> None:
        """Run the dispatcher loop. Call from a background task."""
        self._running = True
        logger.info("outbox_dispatcher_started", poll_interval=poll_interval)
        while self._running:
            try:
                dispatched = await self._dispatch_batch()
                if dispatched == 0:
                    await asyncio.sleep(poll_interval)
            except Exception as exc:
                logger.error("outbox_dispatcher_error", error=str(exc))
                await asyncio.sleep(poll_interval)

    async def stop(self) -> None:
        """Stop the dispatcher loop."""
        self._running = False
        logger.info("outbox_dispatcher_stopped")

    async def _dispatch_batch(self) -> int:
        """Dispatch a batch of pending events. Returns the number dispatched."""
        async with self._session_factory() as session:
            # Fetch pending events
            stmt = (
                select(OutboxEventModel)
                .where(OutboxEventModel.status == "pending")
                .order_by(OutboxEventModel.created_at)
                .limit(self._batch_size)
            )
            result = await session.execute(stmt)
            events = result.scalars().all()

            if not events:
                return 0

            for event in events:
                try:
                    await self._deliver_event(event)
                    # Mark as dispatched
                    await session.execute(
                        update(OutboxEventModel)
                        .where(OutboxEventModel.id == event.id)
                        .values(
                            status="dispatched",
                            dispatched_at=datetime.now(timezone.utc),
                        )
                    )
                except Exception as exc:
                    logger.warning(
                        "outbox_event_dispatch_failed",
                        event_id=str(event.id),
                        event_type=event.event_type,
                        error=str(exc),
                    )
                    # Increment attempt count
                    new_count = event.dispatch_attempt_count + 1
                    if new_count >= self._max_retries:
                        await session.execute(
                            update(OutboxEventModel)
                            .where(OutboxEventModel.id == event.id)
                            .values(
                                status="dead_lettered",
                                dispatch_attempt_count=new_count,
                                last_dispatch_error=str(exc)[:1000],
                            )
                        )
                    else:
                        await session.execute(
                            update(OutboxEventModel)
                            .where(OutboxEventModel.id == event.id)
                            .values(
                                dispatch_attempt_count=new_count,
                                last_dispatch_error=str(exc)[:1000],
                            )
                        )

            await session.commit()
            return len(events)

    async def _deliver_event(self, event: OutboxEventModel) -> None:
        """Deliver an event to all registered subscribers."""
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            await handler(event.payload)

    async def replay_events(
        self,
        event_type: str | None = None,
        from_date: datetime | None = None,
    ) -> int:
        """Replay events from the outbox (for recovery or new subscriber backfill).

        Returns the number of events replayed.
        """
        async with self._session_factory() as session:
            stmt = select(OutboxEventModel).where(
                OutboxEventModel.status.in_(["dispatched", "pending"])
            )
            if event_type:
                stmt = stmt.where(OutboxEventModel.event_type == event_type)
            if from_date:
                stmt = stmt.where(OutboxEventModel.created_at >= from_date)
            stmt = stmt.order_by(OutboxEventModel.created_at)

            result = await session.execute(stmt)
            events = result.scalars().all()

            for event in events:
                await self._deliver_event(event)

            return len(events)
