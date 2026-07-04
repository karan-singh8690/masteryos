"""Tests for the job queue (in-memory + Redis stub).

Tests:
- Enqueue a job
- Dequeue a job
- Complete a job (success)
- Complete a job (failure → retry)
- Dead letter after max attempts
- Priority ordering (urgent first)
- Delayed jobs (not due yet)
- Lease extension
- Get depth
- Get metrics
- QueueWorker processes jobs
- Concurrent dequeue doesn't conflict
- Empty queue returns None
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest

from app.infrastructure.queue.job_queue import (
    InMemoryJobQueue,
    Job,
    JobResult,
    QueueWorker,
    RedisJobQueue,
)


pytestmark = pytest.mark.asyncio


class TestInMemoryJobQueue:
    """Tests for the InMemoryJobQueue."""

    async def test_enqueue_returns_job_id(self):
        queue = InMemoryJobQueue()
        job_id = await queue.enqueue("test", {"key": "value"})
        assert job_id is not None
        assert isinstance(job_id, str)

    async def test_dequeue_returns_job(self):
        queue = InMemoryJobQueue()
        await queue.enqueue("test", {"key": "value"})
        job = await queue.dequeue("test", "worker-1", timedelta(minutes=5))
        assert job is not None
        assert job.payload == {"key": "value"}
        assert job.leased_by == "worker-1"

    async def test_dequeue_empty_queue_returns_none(self):
        queue = InMemoryJobQueue()
        job = await queue.dequeue("test", "worker-1", timedelta(minutes=5))
        assert job is None

    async def test_complete_success(self):
        queue = InMemoryJobQueue()
        job_id = await queue.enqueue("test", {"key": "value"})
        job = await queue.dequeue("test", "worker-1", timedelta(minutes=5))

        result = JobResult(success=True)
        await queue.complete("test", job_id, result)

        # Queue should be empty now
        assert await queue.get_depth("test") == 0

    async def test_complete_failure_retries(self):
        queue = InMemoryJobQueue()
        job_id = await queue.enqueue("test", {"key": "value"})
        job = await queue.dequeue("test", "worker-1", timedelta(minutes=5))

        result = JobResult(success=False, error="Test error")
        await queue.complete("test", job_id, result)

        # Job should be in delayed (waiting for retry)
        metrics = await queue.get_metrics()
        assert metrics["stats"]["retried"] == 1

    async def test_dead_letter_after_max_attempts(self):
        queue = InMemoryJobQueue()
        job_id = await queue.enqueue("test", {"key": "value"})
        job = await queue.dequeue("test", "worker-1", timedelta(minutes=5))
        job.max_attempts = 2

        # First failure → retry
        await queue.complete("test", job_id, JobResult(success=False, error="fail 1"))

        # The retried job needs to be promoted (it's delayed)
        # Force promotion by manipulating the queue
        queue._promote_delayed_jobs()

        # Dequeue again
        job2 = await queue.dequeue("test", "worker-1", timedelta(minutes=5))
        assert job2 is not None

        # Second failure → dead letter
        await queue.complete("test", job2.id, JobResult(success=False, error="fail 2"))

        metrics = await queue.get_metrics()
        assert metrics["stats"]["failed"] == 1

    async def test_priority_ordering(self):
        """Higher-priority jobs are dequeued first."""
        queue = InMemoryJobQueue()
        await queue.enqueue("test", {"priority": "low"}, priority=0)
        await queue.enqueue("test", {"priority": "urgent"}, priority=10)
        await queue.enqueue("test", {"priority": "normal"}, priority=5)

        job1 = await queue.dequeue("test", "w1", timedelta(minutes=5))
        assert job1.payload["priority"] == "urgent"

        job2 = await queue.dequeue("test", "w1", timedelta(minutes=5))
        assert job2.payload["priority"] == "normal"

        job3 = await queue.dequeue("test", "w1", timedelta(minutes=5))
        assert job3.payload["priority"] == "low"

    async def test_delayed_job_not_immediately_available(self):
        """A delayed job is not immediately available for dequeue."""
        queue = InMemoryJobQueue()
        await queue.enqueue(
            "test", {"key": "value"}, delay=timedelta(seconds=60)
        )

        job = await queue.dequeue("test", "worker-1", timedelta(minutes=5))
        assert job is None  # Not due yet

    async def test_extend_lease(self):
        """extend_lease extends the lease on a job."""
        queue = InMemoryJobQueue()
        job_id = await queue.enqueue("test", {"key": "value"})
        job = await queue.dequeue("test", "worker-1", timedelta(minutes=5))

        extended = await queue.extend_lease("test", job_id, timedelta(minutes=10))
        assert extended is True

    async def test_extend_lease_unknown_job(self):
        """extend_lease returns False for unknown job."""
        queue = InMemoryJobQueue()
        extended = await queue.extend_lease("test", "nonexistent", timedelta(minutes=10))
        assert extended is False

    async def test_get_depth(self):
        queue = InMemoryJobQueue()
        await queue.enqueue("test", {"key": "1"})
        await queue.enqueue("test", {"key": "2"})
        await queue.enqueue("test", {"key": "3"})

        depth = await queue.get_depth("test")
        assert depth == 3

    async def test_get_depth_after_dequeue(self):
        queue = InMemoryJobQueue()
        await queue.enqueue("test", {"key": "1"})
        await queue.enqueue("test", {"key": "2"})
        await queue.dequeue("test", "w1", timedelta(minutes=5))

        depth = await queue.get_depth("test")
        assert depth == 1  # One is leased (not in depth count)

    async def test_get_metrics(self):
        queue = InMemoryJobQueue()
        await queue.enqueue("test", {"key": "1"})
        await queue.enqueue("test", {"key": "2"})
        await queue.dequeue("test", "w1", timedelta(minutes=5))

        metrics = await queue.get_metrics()
        assert "queues" in metrics
        assert "processing" in metrics
        assert metrics["processing"] == 1
        assert metrics["stats"]["enqueued"] == 2

    async def test_separate_queues_dont_conflict(self):
        """Jobs in different queues don't interfere."""
        queue = InMemoryJobQueue()
        await queue.enqueue("queue-a", {"key": "a1"})
        await queue.enqueue("queue-b", {"key": "b1"})

        job_a = await queue.dequeue("queue-a", "w1", timedelta(minutes=5))
        job_b = await queue.dequeue("queue-b", "w1", timedelta(minutes=5))

        assert job_a.payload == {"key": "a1"}
        assert job_b.payload == {"key": "b1"}


class TestQueueWorker:
    """Tests for the QueueWorker."""

    async def test_worker_processes_job(self):
        """The worker processes a job from the queue."""
        queue = InMemoryJobQueue()
        await queue.enqueue("test", {"key": "value"})

        processed = []

        async def handler(payload):
            processed.append(payload)
            return JobResult(success=True)

        worker = QueueWorker(
            queue=queue,
            queue_name="test",
            handler=handler,
            worker_id="w1",
            poll_interval=0.01,
        )

        # Start the worker
        task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.1)
        worker.stop()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass

        assert len(processed) == 1
        assert worker._processed == 1

    async def test_worker_handles_handler_failure(self):
        """The worker handles a handler that raises an exception."""
        queue = InMemoryJobQueue()
        await queue.enqueue("test", {"key": "value"})

        async def failing_handler(payload):
            raise ValueError("Handler error")

        worker = QueueWorker(
            queue=queue,
            queue_name="test",
            handler=failing_handler,
            worker_id="w2",
            poll_interval=0.01,
        )

        task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.1)
        worker.stop()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass

        assert worker._failed >= 1

    async def test_worker_stats(self):
        """The worker exposes stats."""
        queue = InMemoryJobQueue()
        worker = QueueWorker(
            queue=queue,
            queue_name="test",
            handler=lambda p: asyncio.sleep(0),
            worker_id="w3",
        )
        stats = worker.stats
        assert stats["worker_id"] == "w3"
        assert stats["queue"] == "test"
        assert stats["running"] is False


class TestRedisJobQueue:
    """Tests for the RedisJobQueue (without Redis — just interface checks)."""

    def test_redis_queue_requires_client(self):
        """RedisJobQueue raises if no Redis client is configured."""
        queue = RedisJobQueue(redis_client=None)
        # Operations should raise RuntimeError
        import asyncio
        with pytest.raises(RuntimeError):
            asyncio.get_event_loop().run_until_complete(
                queue.enqueue("test", {})
            )

    def test_redis_queue_priority_queue_naming(self):
        """Priority queue names are generated correctly."""
        queue = RedisJobQueue(redis_client=None)
        assert "urgent" in queue._priority_queue_name("test", 10)
        assert "high" in queue._priority_queue_name("test", 5)
        assert "normal" in queue._priority_queue_name("test", 0)
        assert "low" in queue._priority_queue_name("test", -5)
