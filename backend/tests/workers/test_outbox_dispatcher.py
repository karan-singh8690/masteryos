"""Tests for the production outbox dispatcher.

Tests:
- Dispatcher processes pending events
- Dispatcher marks events as dispatched on success
- Dispatcher increments retry count on failure
- Dispatcher schedules retry with exponential backoff
- Dispatcher moves events to dead letter queue after max retries
- Dispatcher acquires leases (visibility timeout)
- Dispatcher reclaims expired leases (from crashed workers)
- Dispatcher supports replay
- Dispatcher delivers events to all registered subscribers
- Subscriber failure triggers retry
- Batch polling processes multiple events
- Empty outbox returns 0
- Ordering by created_at
- Concurrent workers don't conflict (SKIP LOCKED)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone as tz_utc
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.infrastructure.database.orm.background import (
    DeadLetterEventModel,
    OutboxLeaseModel,
)
from app.infrastructure.database.orm.core import OutboxEventModel
from app.workers.outbox_dispatcher import (
    DEFAULT_MAX_RETRIES,
    OutboxDispatcherProcessor,
    RETRY_SCHEDULE,
    compute_next_retry,
    get_outbox_stats,
)

from tests.workers.conftest import create_test_outbox_event


pytestmark = pytest.mark.asyncio


class TestOutboxDispatcherBasics:
    """Basic tests for the outbox dispatcher."""

    async def test_dispatch_pending_event(
        self, test_session_factory
    ):
        """The dispatcher processes a pending event."""
        # Create a test event
        async with test_session_factory() as session:
            await create_test_outbox_event(session, event_type="TestEvent")
            await session.commit()

        # Create dispatcher with a subscriber
        received = []

        async def handler(payload):
            received.append(payload)

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w1"
        )
        dispatcher.subscribe("TestEvent", handler)

        # Process one batch
        count = await dispatcher.run_once()
        assert count == 1
        assert len(received) == 1
        assert received[0] == {"test": True}

    async def test_dispatch_marks_event_as_dispatched(
        self, test_session_factory
    ):
        """Successfully dispatched events are marked as 'dispatched'."""
        async with test_session_factory() as session:
            event = await create_test_outbox_event(session, event_type="TestEvent")
            await session.commit()
            event_id = event.id

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w2"
        )

        async def handler(payload):
            pass

        dispatcher.subscribe("TestEvent", handler)
        await dispatcher.run_once()

        async with test_session_factory() as session:
            event = await session.get(OutboxEventModel, event_id)
            assert event.status == "dispatched"
            assert event.dispatched_at is not None

    async def test_dispatch_empty_outbox_returns_zero(
        self, test_session_factory
    ):
        """An empty outbox returns 0 processed."""
        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w3"
        )
        count = await dispatcher.run_once()
        assert count == 0

    async def test_dispatch_delivers_to_all_subscribers(
        self, test_session_factory
    ):
        """An event is delivered to all registered subscribers."""
        async with test_session_factory() as session:
            await create_test_outbox_event(session, event_type="MultiSub")
            await session.commit()

        received_1 = []
        received_2 = []

        async def handler_1(payload):
            received_1.append(payload)

        async def handler_2(payload):
            received_2.append(payload)

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w4"
        )
        dispatcher.subscribe("MultiSub", handler_1, "handler_1")
        dispatcher.subscribe("MultiSub", handler_2, "handler_2")

        await dispatcher.run_once()

        assert len(received_1) == 1
        assert len(received_2) == 1

    async def test_dispatch_no_subscribers_marks_dispatched(
        self, test_session_factory
    ):
        """An event with no subscribers is marked as dispatched (noop)."""
        async with test_session_factory() as session:
            event = await create_test_outbox_event(session, event_type="NoSubs")
            await session.commit()

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w5"
        )
        # No subscribers registered
        count = await dispatcher.run_once()
        assert count == 1  # Still processed (marked dispatched)

    async def test_batch_processing(
        self, test_session_factory
    ):
        """The dispatcher processes multiple events in a batch."""
        async with test_session_factory() as session:
            for i in range(5):
                await create_test_outbox_event(
                    session, event_type="BatchEvent", payload={"i": i}
                )
            await session.commit()

        received = []

        async def handler(payload):
            received.append(payload)

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w6", batch_size=10
        )
        dispatcher.subscribe("BatchEvent", handler)

        count = await dispatcher.run_once()
        assert count == 5
        assert len(received) == 5

    async def test_ordering_by_created_at(
        self, test_session_factory
    ):
        """Events are processed in created_at order."""
        async with test_session_factory() as session:
            # Create events with different timestamps
            from datetime import datetime, timezone as tz_utc
            e1 = OutboxEventModel(
                id=uuid4(),
                event_type="OrderEvent",
                aggregate_id=uuid4(),
                aggregate_type="Test",
                payload={"order": 1},
                payload_schema_version="1",
                originating_schema="test",
                status="pending",
                created_at=datetime(2024, 1, 1, tzinfo=tz_utc.utc),
            )
            e2 = OutboxEventModel(
                id=uuid4(),
                event_type="OrderEvent",
                aggregate_id=uuid4(),
                aggregate_type="Test",
                payload={"order": 2},
                payload_schema_version="1",
                originating_schema="test",
                status="pending",
                created_at=datetime(2024, 1, 2, tzinfo=tz_utc.utc),
            )
            session.add_all([e1, e2])
            await session.commit()

        received = []

        async def handler(payload):
            received.append(payload["order"])

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w7"
        )
        dispatcher.subscribe("OrderEvent", handler)
        await dispatcher.run_once()

        # Should be processed in order: 1 then 2
        assert received == [1, 2]


class TestOutboxRetries:
    """Tests for the retry mechanism."""

    async def test_failed_event_increments_retry_count(
        self, test_session_factory
    ):
        """A failed event has its retry count incremented."""
        async with test_session_factory() as session:
            event = await create_test_outbox_event(session, event_type="FailEvent")
            await session.commit()
            event_id = event.id

        async def failing_handler(payload):
            raise ValueError("Test failure")

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w8"
        )
        dispatcher.subscribe("FailEvent", failing_handler)

        await dispatcher.run_once()

        async with test_session_factory() as session:
            event = await session.get(OutboxEventModel, event_id)
            assert event.dispatch_attempt_count == 1
            assert event.status == "pending"  # Still pending (will retry)
            assert event.next_retry_at is not None
            assert event.last_dispatch_error is not None

    async def test_failed_event_schedules_retry_with_backoff(
        self, test_session_factory
    ):
        """A failed event is scheduled for retry with exponential backoff."""
        async with test_session_factory() as session:
            event = await create_test_outbox_event(session, event_type="RetryEvent")
            await session.commit()

        call_count = 0

        async def fail_twice_then_succeed(payload):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("Transient failure")

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w9"
        )
        dispatcher.subscribe("RetryEvent", fail_twice_then_succeed)

        # First attempt fails
        await dispatcher.run_once()

        # Verify retry is scheduled ~1 minute in the future
        async with test_session_factory() as session:
            stmt = select(OutboxEventModel).where(OutboxEventModel.event_type == "RetryEvent")
            event = (await session.execute(stmt)).scalar_one()
            assert event.dispatch_attempt_count == 1
            assert event.next_retry_at is not None
            # Next retry should be ~1 minute from now (RETRY_SCHEDULE[0])
            now = datetime.now(tz_utc.utc)
            retry_at = event.next_retry_at
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=tz_utc.utc)
            delay = (retry_at - now).total_seconds()
            # Should be roughly 60 seconds (with some jitter)
            assert 50 <= delay <= 70

    async def test_dead_letter_after_max_retries(
        self, test_session_factory
    ):
        """An event that exhausts retries is moved to the dead letter queue."""
        async with test_session_factory() as session:
            event = await create_test_outbox_event(session, event_type="DeadLetterEvent")
            await session.commit()
            event_id = event.id

        async def always_fail(payload):
            raise ValueError("Permanent failure")

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w10", max_retries=3
        )
        dispatcher.subscribe("DeadLetterEvent", always_fail)

        # Simulate max retries by manually setting the attempt count
        async with test_session_factory() as session:
            event = await session.get(OutboxEventModel, event_id)
            event.dispatch_attempt_count = 2  # One more will trigger dead letter
            await session.commit()

        await dispatcher.run_once()

        async with test_session_factory() as session:
            event = await session.get(OutboxEventModel, event_id)
            assert event.status == "dead_lettered"

            # Verify dead letter entry was created
            stmt = select(DeadLetterEventModel).where(
                DeadLetterEventModel.original_event_id == event_id
            )
            result = await session.execute(stmt)
            dl = result.scalar_one_or_none()
            assert dl is not None
            assert dl.event_type == "DeadLetterEvent"
            assert dl.error_message is not None
            assert dl.retry_count >= 2  # At least 2 retries before dead-lettering


class TestOutboxLeases:
    """Tests for the lease/visibility timeout mechanism."""

    async def test_acquire_lease(
        self, test_session_factory
    ):
        """The dispatcher acquires a lease when picking up an event."""
        async with test_session_factory() as session:
            await create_test_outbox_event(session, event_type="LeaseEvent")
            await session.commit()

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w11"
        )

        async def handler(payload):
            pass

        dispatcher.subscribe("LeaseEvent", handler)
        await dispatcher.run_once()

        # Verify a lease was created + released
        async with test_session_factory() as session:
            stmt = select(OutboxLeaseModel)
            result = await session.execute(stmt)
            leases = result.scalars().all()
            assert len(leases) >= 1
            assert leases[0].released_at is not None
            assert leases[0].release_reason == "completed"

    async def test_expired_lease_reclaimed(
        self, test_session_factory
    ):
        """An expired lease (from a crashed worker) is reclaimed."""
        async with test_session_factory() as session:
            event = await create_test_outbox_event(session, event_type="ReclaimEvent")
            # Manually set an expired lease
            event.leased_by = "crashed-worker"
            event.leased_until = datetime.now(tz_utc.utc) - timedelta(seconds=60)
            await session.commit()

            # Also create a lease record
            session.add(OutboxLeaseModel(
                id=uuid4(),
                outbox_event_id=event.id,
                worker_id="crashed-worker",
                acquired_at=datetime.now(tz_utc.utc) - timedelta(seconds=120),
                expires_at=datetime.now(tz_utc.utc) - timedelta(seconds=60),
            ))
            await session.commit()

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w12"
        )

        async def handler(payload):
            pass

        dispatcher.subscribe("ReclaimEvent", handler)

        # The dispatcher should reclaim the expired lease + process the event
        count = await dispatcher.run_once()
        assert count == 1


class TestOutboxReplay:
    """Tests for the replay functionality."""

    async def test_replay_single_event(
        self, test_session_factory
    ):
        """Replaying a single event resets it to pending."""
        async with test_session_factory() as session:
            event = await create_test_outbox_event(session, event_type="ReplayEvent")
            event.status = "dispatched"
            event.dispatch_attempt_count = 2
            await session.commit()
            event_id = event.id

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w13"
        )
        success = await dispatcher.replay_event(event_id)
        assert success is True

        async with test_session_factory() as session:
            event = await session.get(OutboxEventModel, event_id)
            assert event.status == "pending"
            assert event.dispatch_attempt_count == 0
            assert event.next_retry_at is None

    async def test_replay_nonexistent_event_returns_false(
        self, test_session_factory
    ):
        """Replaying a nonexistent event returns False."""
        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w14"
        )
        success = await dispatcher.replay_event(uuid4())
        assert success is False

    async def test_replay_dead_letter(
        self, test_session_factory
    ):
        """Replaying a dead-lettered event creates a new outbox entry."""
        # Create a dead letter entry
        async with test_session_factory() as session:
            dl = DeadLetterEventModel(
                id=uuid4(),
                original_event_id=uuid4(),
                event_type="DLReplayEvent",
                aggregate_id=uuid4(),
                aggregate_type="Test",
                payload={"test": True},
                originating_schema="test",
                error_message="Test error",
                error_type="ValueError",
                retry_count=3,
                retry_history=[],
                severity="error",
            )
            session.add(dl)
            await session.commit()
            dl_id = dl.id

        dispatcher = OutboxDispatcherProcessor(
            test_session_factory, worker_id="test-w15"
        )
        success = await dispatcher.replay_dead_letter(dl_id)
        assert success is True

        # Verify a new outbox event was created
        async with test_session_factory() as session:
            stmt = select(OutboxEventModel).where(
                OutboxEventModel.event_type == "DLReplayEvent"
            )
            result = await session.execute(stmt)
            new_event = result.scalar_one()
            assert new_event.status == "pending"

            # Verify the dead letter is marked as resolved
            dl = await session.get(DeadLetterEventModel, dl_id)
            assert dl.resolved_at is not None
            assert dl.replayed_as_event_id == new_event.id


class TestOutboxStats:
    """Tests for the get_outbox_stats function."""

    async def test_outbox_stats(
        self, test_session_factory
    ):
        """get_outbox_stats returns correct counts."""
        async with test_session_factory() as session:
            # Create events with different statuses
            await create_test_outbox_event(session, event_type="E1", status="pending")
            await create_test_outbox_event(session, event_type="E2", status="pending")
            await create_test_outbox_event(session, event_type="E3", status="dispatched")
            await create_test_outbox_event(session, event_type="E4", status="dead_lettered")
            await session.commit()

        stats = await get_outbox_stats(test_session_factory)
        assert stats["pending"] == 2
        assert stats["dispatched"] == 1
        assert stats["dead_lettered"] == 1

    async def test_outbox_stats_empty(
        self, test_session_factory
    ):
        """get_outbox_stats returns zeros for an empty outbox."""
        stats = await get_outbox_stats(test_session_factory)
        assert stats["pending"] == 0
        assert stats["dispatched"] == 0
        assert stats["dead_lettered"] == 0


class TestRetrySchedule:
    """Tests for the retry schedule constants."""

    def test_retry_schedule_has_6_levels(self):
        """The retry schedule has 6 levels (1m, 5m, 15m, 1h, 6h, 24h)."""
        assert len(RETRY_SCHEDULE) == 6

    def test_retry_schedule_first_level_is_1_minute(self):
        """The first retry is after 1 minute."""
        assert RETRY_SCHEDULE[0] == timedelta(minutes=1)

    def test_retry_schedule_second_level_is_5_minutes(self):
        """The second retry is after 5 minutes."""
        assert RETRY_SCHEDULE[1] == timedelta(minutes=5)

    def test_retry_schedule_third_level_is_15_minutes(self):
        """The third retry is after 15 minutes."""
        assert RETRY_SCHEDULE[2] == timedelta(minutes=15)

    def test_retry_schedule_fourth_level_is_1_hour(self):
        """The fourth retry is after 1 hour."""
        assert RETRY_SCHEDULE[3] == timedelta(hours=1)

    def test_retry_schedule_fifth_level_is_6_hours(self):
        """The fifth retry is after 6 hours."""
        assert RETRY_SCHEDULE[4] == timedelta(hours=6)

    def test_retry_schedule_sixth_level_is_24_hours(self):
        """The sixth retry is after 24 hours."""
        assert RETRY_SCHEDULE[5] == timedelta(hours=24)

    def test_compute_next_retry_first_attempt(self):
        """compute_next_retry for attempt 0 returns ~1 minute from now."""
        now = datetime.now(tz_utc.utc)
        retry = compute_next_retry(0)
        delay = (retry - now).total_seconds()
        # ~60 seconds (with possible jitter)
        assert 50 <= delay <= 70

    def test_compute_next_retry_last_attempt(self):
        """compute_next_retry for the last attempt returns ~24 hours from now."""
        now = datetime.now(tz_utc.utc)
        retry = compute_next_retry(5)
        delay = (retry - now).total_seconds()
        # ~86400 seconds (with possible jitter)
        assert 86300 <= delay <= 86500
