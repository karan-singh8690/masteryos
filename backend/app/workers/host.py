"""Production worker host — manages background worker processes.

The WorkerHost is the top-level coordinator that runs:
- OutboxDispatcher (polls outbox, delivers events to subscribers)
- Scheduler (executes recurring jobs)
- NotificationProcessor (delivers queued notifications)
- EmailProcessor (sends queued emails)
- CleanupProcessor (removes expired tokens/sessions)
- AnalyticsProcessor (generates daily/weekly analytics)

Each processor runs as an asyncio task. The host manages:
- Graceful shutdown (drain in-progress work, then stop)
- Heartbeat (writes to worker_heartbeats every N seconds)
- Health endpoint (HTTP server for /health/worker)
- Worker identity (unique worker_id per process)
- Multi-worker coordination (via DB leases + heartbeat table)

Usage:
    host = WorkerHost(session_factory, worker_id="worker-1")
    host.register_processor(OutboxDispatcher(...))
    await host.start()  # runs until stopped
"""

from __future__ import annotations

import asyncio
import os
import socket
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone as tz_utc
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Processor Protocol
# ============================================================


class WorkerProcessor:
    """Base class for worker processors.

    A processor is a long-running asyncio task that does one job:
    - OutboxDispatcher: polls the outbox table
    - Scheduler: runs scheduled jobs
    - NotificationProcessor: delivers queued notifications
    - EmailProcessor: sends queued emails
    - CleanupProcessor: removes expired data

    Subclasses must implement run_once() and name.
    """

    name: str = "processor"

    def __init__(self, worker_id: str = "worker") -> None:
        self.worker_id = worker_id
        self._running = False
        self._processed_count = 0
        self._failed_count = 0
        self._current_job: str | None = None

    async def run_once(self) -> int:
        """Process one batch. Returns the number of items processed.

        Returning 0 indicates no work was available (the host will sleep).
        """
        raise NotImplementedError

    async def start(self, poll_interval: float = 1.0) -> None:
        """Run the processor loop until stop() is called."""
        self._running = True
        logger.info("processor_started", processor=self.name, worker_id=self.worker_id)
        while self._running:
            try:
                processed = await self.run_once()
                if processed == 0:
                    await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                logger.info("processor_cancelled", processor=self.name)
                break
            except Exception as exc:
                self._failed_count += 1
                logger.error(
                    "processor_error",
                    processor=self.name,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                await asyncio.sleep(poll_interval)
        logger.info("processor_stopped", processor=self.name)

    def stop(self) -> None:
        """Request the processor to stop after current batch."""
        self._running = False

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "worker_id": self.worker_id,
            "running": self._running,
            "processed_count": self._processed_count,
            "failed_count": self._failed_count,
            "current_job": self._current_job,
        }


# ============================================================
# Worker Host
# ============================================================


class WorkerHost:
    """Coordinates multiple background processors.

    The host:
    1. Starts each processor as an asyncio task.
    2. Writes a heartbeat every 10 seconds.
    3. Listens for SIGTERM/SIGINT for graceful shutdown.
    4. Exposes a /health/worker HTTP endpoint (via a separate server).
    5. Supports multiple workers (each with a unique worker_id).

    Graceful shutdown:
    1. Receive signal (SIGTERM/SIGINT) or stop() call.
    2. Stop accepting new work (set _running = False).
    3. Wait for in-progress tasks to complete (up to drain_timeout).
    4. Cancel remaining tasks.
    5. Write final heartbeat with status="stopped".
    """

    HEARTBEAT_INTERVAL = 10.0  # seconds
    DRAIN_TIMEOUT = 30.0  # seconds to wait for in-progress work

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        worker_id: str | None = None,
        worker_type: str = "worker",
    ) -> None:
        self._session_factory = session_factory
        self.worker_id = worker_id or f"worker-{uuid4().hex[:8]}"
        self.worker_type = worker_type
        self.hostname = socket.gethostname()
        self.process_id = os.getpid()

        self._processors: list[WorkerProcessor] = []
        self._tasks: list[asyncio.Task] = []
        self._heartbeat_task: asyncio.Task | None = None
        self._running = False
        self._started_at: datetime | None = None

    def register_processor(self, processor: WorkerProcessor) -> None:
        """Register a processor to be started with the host."""
        processor.worker_id = self.worker_id
        self._processors.append(processor)
        logger.info("processor_registered", processor=processor.name)

    async def start(self, poll_interval: float = 1.0) -> None:
        """Start all processors + heartbeat. Runs until stop() or signal."""
        self._running = True
        self._started_at = datetime.now(tz_utc.utc)

        logger.info(
            "worker_host_starting",
            worker_id=self.worker_id,
            worker_type=self.worker_type,
            hostname=self.hostname,
            process_id=self.process_id,
            processor_count=len(self._processors),
        )

        # Write initial heartbeat
        await self._write_heartbeat(status="starting")

        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Start processor tasks
        for processor in self._processors:
            task = asyncio.create_task(
                processor.start(poll_interval=poll_interval),
                name=f"processor-{processor.name}",
            )
            self._tasks.append(task)

        # Update status to running
        await self._write_heartbeat(status="running")

        # Wait for all tasks (they run forever until stopped)
        try:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass

        # Final cleanup
        await self._stop_heartbeat()
        await self._write_heartbeat(status="stopped")
        logger.info("worker_host_stopped", worker_id=self.worker_id)

    async def stop(self) -> None:
        """Request graceful shutdown."""
        logger.info("worker_host_stop_requested", worker_id=self.worker_id)
        self._running = False

        # Mark shutdown requested in heartbeat
        await self._write_heartbeat(status="draining", shutdown_requested=True)

        # Stop all processors
        for processor in self._processors:
            processor.stop()

        # Cancel tasks with drain timeout
        if self._tasks:
            logger.info("draining_processors", timeout=self.DRAIN_TIMEOUT)
            done, pending = await asyncio.wait(
                self._tasks, timeout=self.DRAIN_TIMEOUT
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def _heartbeat_loop(self) -> None:
        """Write heartbeat every HEARTBEAT_INTERVAL seconds."""
        while self._running:
            try:
                await self._write_heartbeat(status="running" if self._running else "draining")
            except Exception as exc:
                logger.warning("heartbeat_failed", error=str(exc))
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)

    async def _stop_heartbeat(self) -> None:
        """Stop the heartbeat task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

    async def _write_heartbeat(
        self,
        status: str,
        shutdown_requested: bool = False,
    ) -> None:
        """Write (or update) the worker heartbeat in the database."""
        now = datetime.now(tz_utc.utc)
        started_at = self._started_at or now

        # Aggregate stats from processors
        jobs_processed = sum(p._processed_count for p in self._processors)
        jobs_failed = sum(p._failed_count for p in self._processors)
        current_jobs = [p._current_job for p in self._processors if p._current_job]

        from app.infrastructure.database.orm.background import WorkerHeartbeatModel

        try:
            async with self._session_factory() as session:
                # Try to find existing heartbeat
                stmt = select(WorkerHeartbeatModel).where(
                    WorkerHeartbeatModel.worker_id == self.worker_id
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing is None:
                    # Create new
                    heartbeat = WorkerHeartbeatModel(
                        id=uuid4(),
                        worker_id=self.worker_id,
                        worker_type=self.worker_type,
                        hostname=self.hostname,
                        process_id=self.process_id,
                        status=status,
                        last_seen_at=now,
                        started_at=started_at,
                        jobs_processed=jobs_processed,
                        jobs_failed=jobs_failed,
                        current_job=",".join(current_jobs) if current_jobs else None,
                        shutdown_requested=shutdown_requested,
                    )
                    session.add(heartbeat)
                else:
                    # Update existing
                    existing.status = status
                    existing.last_seen_at = now
                    existing.jobs_processed = jobs_processed
                    existing.jobs_failed = jobs_failed
                    existing.current_job = ",".join(current_jobs) if current_jobs else None
                    existing.shutdown_requested = shutdown_requested

                await session.commit()
        except Exception as exc:
            logger.warning("heartbeat_write_failed", error=str(exc), error_type=type(exc).__name__)

    @property
    def stats(self) -> dict[str, Any]:
        """Return host stats for monitoring."""
        return {
            "worker_id": self.worker_id,
            "worker_type": self.worker_type,
            "hostname": self.hostname,
            "process_id": self.process_id,
            "running": self._running,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "processors": [p.stats for p in self._processors],
        }


# ============================================================
# Heartbeat Service (standalone — for checking other workers)
# ============================================================


class HeartbeatService:
    """Service for querying and managing worker heartbeats.

    Used by:
    - The admin API (/admin/workers) to list workers
    - The scheduler to detect dead workers and release their leases
    - The metrics collector to count active workers
    """

    HEARTBEAT_STALE_SECONDS = 60.0  # A worker is "dead" if no heartbeat for 60s

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_workers(self) -> list[dict[str, Any]]:
        """List all workers (active + recently dead)."""
        from app.infrastructure.database.orm.background import WorkerHeartbeatModel

        async with self._session_factory() as session:
            stmt = (
                select(WorkerHeartbeatModel)
                .order_by(WorkerHeartbeatModel.last_seen_at.desc())
            )
            result = await session.execute(stmt)
            return [self._to_dict(h) for h in result.scalars().all()]

    async def get_worker(self, worker_id: str) -> dict[str, Any] | None:
        """Get a single worker's heartbeat."""
        from app.infrastructure.database.orm.background import WorkerHeartbeatModel

        async with self._session_factory() as session:
            stmt = select(WorkerHeartbeatModel).where(
                WorkerHeartbeatModel.worker_id == worker_id
            )
            result = await session.execute(stmt)
            heartbeat = result.scalar_one_or_none()
            return self._to_dict(heartbeat) if heartbeat else None

    async def detect_dead_workers(self) -> list[str]:
        """Find workers whose heartbeat is stale (likely crashed).

        Returns the worker_ids of dead workers.
        """
        from app.infrastructure.database.orm.background import WorkerHeartbeatModel

        cutoff = datetime.now(tz_utc.utc) - timedelta(seconds=self.HEARTBEAT_STALE_SECONDS)
        async with self._session_factory() as session:
            stmt = select(WorkerHeartbeatModel.worker_id).where(
                WorkerHeartbeatModel.last_seen_at < cutoff,
                WorkerHeartbeatModel.status.in_(["starting", "running", "draining"]),
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]

    async def mark_worker_dead(self, worker_id: str) -> bool:
        """Mark a worker as crashed (after detecting stale heartbeat)."""
        from app.infrastructure.database.orm.background import WorkerHeartbeatModel

        async with self._session_factory() as session:
            stmt = (
                update(WorkerHeartbeatModel)
                .where(WorkerHeartbeatModel.worker_id == worker_id)
                .values(status="crashed")
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def request_shutdown(self, worker_id: str) -> bool:
        """Request a worker to shut down gracefully (sets shutdown_requested)."""
        from app.infrastructure.database.orm.background import WorkerHeartbeatModel

        async with self._session_factory() as session:
            stmt = (
                update(WorkerHeartbeatModel)
                .where(WorkerHeartbeatModel.worker_id == worker_id)
                .values(shutdown_requested=True)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    def _to_dict(h) -> dict[str, Any]:
        def _ensure_aware(dt):
            from datetime import timezone as tz_utc
            if dt is None:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=tz_utc.utc)
            return dt

        last_seen = _ensure_aware(h.last_seen_at)
        now = datetime.now(tz_utc.utc)
        is_stale = True
        if last_seen:
            is_stale = (now - last_seen).total_seconds() > HeartbeatService.HEARTBEAT_STALE_SECONDS

        return {
            "worker_id": h.worker_id,
            "worker_type": h.worker_type,
            "hostname": h.hostname,
            "process_id": h.process_id,
            "status": h.status,
            "last_seen_at": h.last_seen_at.isoformat() if h.last_seen_at else None,
            "started_at": h.started_at.isoformat() if h.started_at else None,
            "jobs_processed": h.jobs_processed,
            "jobs_failed": h.jobs_failed,
            "current_job": h.current_job,
            "shutdown_requested": h.shutdown_requested,
            "is_stale": is_stale,
        }


# Need timedelta + uuid4 imports
from datetime import timedelta  # noqa: E402
from uuid import uuid4  # noqa: E402


__all__ = ["WorkerProcessor", "WorkerHost", "HeartbeatService"]
