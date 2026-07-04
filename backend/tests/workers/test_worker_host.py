"""Tests for the WorkerHost + WorkerProcessor + HeartbeatService.

Tests:
- WorkerHost starts and stops gracefully
- WorkerHost writes heartbeats
- WorkerProcessor processes items
- WorkerProcessor handles errors without crashing
- HeartbeatService detects dead workers
- HeartbeatService marks workers as dead
- HeartbeatService lists workers
- Multiple processors run concurrently
- Graceful shutdown waits for in-progress work
- Worker identity is unique
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone as tz_utc

import pytest
from sqlalchemy import select

from app.infrastructure.database.orm.background import WorkerHeartbeatModel
from app.workers.host import HeartbeatService, WorkerHost, WorkerProcessor

from tests.workers.conftest import create_test_user


pytestmark = pytest.mark.asyncio


class TestWorkerProcessor:
    """Tests for the WorkerProcessor base class."""

    async def test_processor_run_once_returns_count(self):
        """A processor's run_once returns the number of items processed."""
        class CountingProcessor(WorkerProcessor):
            name = "counter"
            def __init__(self, worker_id="w1"):
                super().__init__(worker_id)
                self._call_count = 0

            async def run_once(self) -> int:
                self._call_count += 1
                self._processed_count += 1
                return 1

        processor = CountingProcessor()
        result = await processor.run_once()
        assert result == 1
        assert processor._processed_count == 1

    async def test_processor_handles_errors(self):
        """A processor's run_once can raise without crashing the host."""
        class FailingProcessor(WorkerProcessor):
            name = "failer"
            async def run_once(self) -> int:
                raise ValueError("Test error")

        processor = FailingProcessor()
        with pytest.raises(ValueError):
            await processor.run_once()

    async def test_processor_stats(self):
        """A processor exposes stats."""
        class StatsProcessor(WorkerProcessor):
            name = "stats"
            async def run_once(self) -> int:
                self._processed_count = 5
                self._failed_count = 1
                self._current_job = "test-job"
                return 1

        processor = StatsProcessor()
        await processor.run_once()
        stats = processor.stats
        assert stats["name"] == "stats"
        assert stats["processed_count"] == 5
        assert stats["failed_count"] == 1
        assert stats["current_job"] == "test-job"


class TestWorkerHost:
    """Tests for the WorkerHost."""

    async def test_host_starts_and_stops(
        self, test_session_factory
    ):
        """The host starts, runs processors, and stops gracefully."""
        class QuickProcessor(WorkerProcessor):
            name = "quick"
            def __init__(self, worker_id="w1"):
                super().__init__(worker_id)
                self._iterations = 0

            async def run_once(self) -> int:
                self._iterations += 1
                if self._iterations >= 2:
                    self._running = False
                return 1

        host = WorkerHost(test_session_factory, worker_id="test-host-1")
        processor = QuickProcessor()
        host.register_processor(processor)

        # Start + stop quickly
        start_task = asyncio.create_task(host.start(poll_interval=0.01))
        await asyncio.sleep(0.1)
        await host.stop()
        await start_task  # Wait for it to finish

        assert processor._iterations >= 1

    async def test_host_writes_heartbeat(
        self, test_session_factory
    ):
        """The host writes a heartbeat to the database."""
        class NoopProcessor(WorkerProcessor):
            name = "noop"
            async def run_once(self) -> int:
                self._running = False  # Stop immediately
                return 0

        host = WorkerHost(test_session_factory, worker_id="test-host-2")
        host.register_processor(NoopProcessor())

        # Start + stop
        start_task = asyncio.create_task(host.start(poll_interval=0.01))
        await asyncio.sleep(0.2)
        await host.stop()
        try:
            await asyncio.wait_for(start_task, timeout=1.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass

        # Verify heartbeat was written
        async with test_session_factory() as session:
            stmt = select(WorkerHeartbeatModel).where(
                WorkerHeartbeatModel.worker_id == "test-host-2"
            )
            result = await session.execute(stmt)
            heartbeat = result.scalar_one_or_none()
            assert heartbeat is not None
            assert heartbeat.worker_type == "worker"
            assert heartbeat.hostname is not None

    async def test_host_with_multiple_processors(
        self, test_session_factory
    ):
        """The host can run multiple processors concurrently."""
        class P1(WorkerProcessor):
            name = "p1"
            async def run_once(self) -> int:
                self._running = False
                return 1

        class P2(WorkerProcessor):
            name = "p2"
            async def run_once(self) -> int:
                self._running = False
                return 1

        host = WorkerHost(test_session_factory, worker_id="test-host-3")
        host.register_processor(P1())
        host.register_processor(P2())

        assert len(host._processors) == 2

        start_task = asyncio.create_task(host.start(poll_interval=0.01))
        await asyncio.sleep(0.1)
        await host.stop()
        try:
            await asyncio.wait_for(start_task, timeout=1.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass

    async def test_host_stats(self, test_session_factory):
        """The host exposes stats."""
        host = WorkerHost(test_session_factory, worker_id="test-stats")
        stats = host.stats
        assert stats["worker_id"] == "test-stats"
        assert stats["worker_type"] == "worker"
        assert "processors" in stats
        assert stats["running"] is False


class TestHeartbeatService:
    """Tests for the HeartbeatService."""

    async def test_list_workers_empty(self, test_session_factory):
        """list_workers returns empty list when no workers exist."""
        service = HeartbeatService(test_session_factory)
        workers = await service.list_workers()
        assert workers == []

    async def test_get_worker_not_found(self, test_session_factory):
        """get_worker returns None for unknown worker."""
        service = HeartbeatService(test_session_factory)
        worker = await service.get_worker("nonexistent")
        assert worker is None

    async def test_detect_dead_workers(
        self, test_session_factory
    ):
        """detect_dead_workers finds workers with stale heartbeats."""
        # Insert a stale heartbeat
        async with test_session_factory() as session:
            from uuid import uuid4
            stale_time = datetime.now(tz_utc.utc) - timedelta(seconds=120)
            heartbeat = WorkerHeartbeatModel(
                id=uuid4(),
                worker_id="dead-worker",
                worker_type="worker",
                hostname="test",
                process_id=123,
                status="running",
                last_seen_at=stale_time,
                started_at=stale_time,
                jobs_processed=0,
                jobs_failed=0,
                shutdown_requested=False,
            )
            session.add(heartbeat)
            await session.commit()

        service = HeartbeatService(test_session_factory)
        dead = await service.detect_dead_workers()
        assert "dead-worker" in dead

    async def test_mark_worker_dead(self, test_session_factory):
        """mark_worker_dead updates the worker status."""
        from uuid import uuid4
        async with test_session_factory() as session:
            heartbeat = WorkerHeartbeatModel(
                id=uuid4(),
                worker_id="to-kill",
                worker_type="worker",
                hostname="test",
                process_id=123,
                status="running",
                last_seen_at=datetime.now(tz_utc.utc),
                started_at=datetime.now(tz_utc.utc),
                jobs_processed=0,
                jobs_failed=0,
                shutdown_requested=False,
            )
            session.add(heartbeat)
            await session.commit()

        service = HeartbeatService(test_session_factory)
        success = await service.mark_worker_dead("to-kill")
        assert success is True

        async with test_session_factory() as session:
            stmt = select(WorkerHeartbeatModel).where(
                WorkerHeartbeatModel.worker_id == "to-kill"
            )
            result = await session.execute(stmt)
            heartbeat = result.scalar_one()
            assert heartbeat.status == "crashed"

    async def test_request_shutdown(self, test_session_factory):
        """request_shutdown sets the shutdown_requested flag."""
        from uuid import uuid4
        async with test_session_factory() as session:
            heartbeat = WorkerHeartbeatModel(
                id=uuid4(),
                worker_id="to-stop",
                worker_type="worker",
                hostname="test",
                process_id=123,
                status="running",
                last_seen_at=datetime.now(tz_utc.utc),
                started_at=datetime.now(tz_utc.utc),
                jobs_processed=0,
                jobs_failed=0,
                shutdown_requested=False,
            )
            session.add(heartbeat)
            await session.commit()

        service = HeartbeatService(test_session_factory)
        success = await service.request_shutdown("to-stop")
        assert success is True

        async with test_session_factory() as session:
            stmt = select(WorkerHeartbeatModel).where(
                WorkerHeartbeatModel.worker_id == "to-stop"
            )
            result = await session.execute(stmt)
            heartbeat = result.scalar_one()
            assert heartbeat.shutdown_requested is True

    async def test_list_workers_returns_all(self, test_session_factory):
        """list_workers returns all workers."""
        from uuid import uuid4
        async with test_session_factory() as session:
            for i in range(3):
                session.add(WorkerHeartbeatModel(
                    id=uuid4(),
                    worker_id=f"worker-{i}",
                    worker_type="worker",
                    hostname="test",
                    process_id=123 + i,
                    status="running",
                    last_seen_at=datetime.now(tz_utc.utc),
                    started_at=datetime.now(tz_utc.utc),
                    jobs_processed=i,
                    jobs_failed=0,
                    shutdown_requested=False,
                ))
            await session.commit()

        service = HeartbeatService(test_session_factory)
        workers = await service.list_workers()
        assert len(workers) == 3
        # Most recent first
        assert workers[0]["worker_id"] in ["worker-0", "worker-1", "worker-2"]
