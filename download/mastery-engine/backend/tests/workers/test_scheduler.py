"""Tests for the scheduler + scheduled jobs.

Tests:
- SchedulerProcessor runs due jobs
- SchedulerProcessor skips locked jobs
- SchedulerProcessor records run results
- SchedulerProcessor computes next run time
- Default scheduled jobs are defined
- ensure_default_jobs_scheduled creates jobs
- Job handlers can be registered
- Job locking prevents concurrent execution
- Pause/resume jobs
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as tz_utc
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.infrastructure.database.orm.background import ScheduledJobModel
from app.infrastructure.database.repositories.background import ScheduledJobRepository
from app.infrastructure.scheduler.processor import (
    DEFAULT_HANDLERS,
    DEFAULT_SCHEDULED_JOBS,
    SchedulerProcessor,
    cleanup_expired_notifications_handler,
    cleanup_expired_sessions_handler,
    cleanup_expired_tokens_handler,
    ensure_default_jobs_scheduled,
    heartbeat_check_handler,
)

from tests.workers.conftest import create_test_user


pytestmark = pytest.mark.asyncio


class TestScheduledJobRepository:
    """Tests for the ScheduledJobRepository."""

    async def test_create_job(self, test_session):
        repo = ScheduledJobRepository(test_session)
        job = await repo.create(
            name="test-job",
            handler_name="test_handler",
            schedule_type="interval",
            schedule_expr="60",
            next_run_at=datetime.now(tz_utc.utc) + timedelta(minutes=5),
        )
        await test_session.commit()

        assert job.id is not None
        assert job.status == "active"
        assert job.run_count == 0

    async def test_get_by_name(self, test_session):
        repo = ScheduledJobRepository(test_session)
        await repo.create(
            name="named-job",
            handler_name="handler",
            schedule_type="interval",
            schedule_expr="60",
            next_run_at=datetime.now(tz_utc.utc),
        )
        await test_session.commit()

        job = await repo.get_by_name("named-job")
        assert job is not None
        assert job.name == "named-job"

    async def test_list_active(self, test_session):
        repo = ScheduledJobRepository(test_session)
        await repo.create(
            name="active-1",
            handler_name="h",
            schedule_type="interval",
            schedule_expr="60",
            next_run_at=datetime.now(tz_utc.utc),
        )
        await repo.create(
            name="paused-1",
            handler_name="h",
            schedule_type="interval",
            schedule_expr="60",
            next_run_at=datetime.now(tz_utc.utc),
        )
        await test_session.commit()
        # Manually pause the second one
        await repo.pause((await repo.get_by_name("paused-1")).id)
        await test_session.commit()

        active = await repo.list_active()
        assert len(active) == 1
        assert active[0].name == "active-1"

    async def test_list_due(self, test_session):
        repo = ScheduledJobRepository(test_session)
        # Due job
        await repo.create(
            name="due",
            handler_name="h",
            schedule_type="interval",
            schedule_expr="60",
            next_run_at=datetime.now(tz_utc.utc) - timedelta(minutes=5),
        )
        # Future job
        await repo.create(
            name="future",
            handler_name="h",
            schedule_type="interval",
            schedule_expr="60",
            next_run_at=datetime.now(tz_utc.utc) + timedelta(hours=1),
        )
        await test_session.commit()

        due = await repo.list_due()
        assert len(due) == 1
        assert due[0].name == "due"

    async def test_acquire_lock(self, test_session):
        repo = ScheduledJobRepository(test_session)
        job = await repo.create(
            name="lockable",
            handler_name="h",
            schedule_type="interval",
            schedule_expr="60",
            next_run_at=datetime.now(tz_utc.utc),
        )
        await test_session.commit()

        # First worker acquires
        acquired = await repo.acquire_lock(job.id, "worker-1", timedelta(minutes=5))
        assert acquired is True

        # Second worker cannot acquire
        acquired = await repo.acquire_lock(job.id, "worker-2", timedelta(minutes=5))
        assert acquired is False

    async def test_release_lock_success(self, test_session):
        repo = ScheduledJobRepository(test_session)
        job = await repo.create(
            name="releasable",
            handler_name="h",
            schedule_type="interval",
            schedule_expr="60",
            next_run_at=datetime.now(tz_utc.utc),
        )
        await test_session.commit()
        await repo.acquire_lock(job.id, "worker-1", timedelta(minutes=5))

        released = await repo.release_lock(
            job.id, "worker-1", success=True, duration_ms=100,
            next_run_at=datetime.now(tz_utc.utc) + timedelta(hours=1),
        )
        await test_session.commit()
        assert released is True

        updated = await repo.get_by_id(job.id)
        assert updated.locked_by is None
        assert updated.last_run_status == "success"
        assert updated.run_count == 1

    async def test_release_lock_failure(self, test_session):
        repo = ScheduledJobRepository(test_session)
        job = await repo.create(
            name="failable",
            handler_name="h",
            schedule_type="interval",
            schedule_expr="60",
            next_run_at=datetime.now(tz_utc.utc),
        )
        await test_session.commit()
        await repo.acquire_lock(job.id, "worker-1", timedelta(minutes=5))

        released = await repo.release_lock(
            job.id, "worker-1", success=False, error="Test error", duration_ms=50,
        )
        await test_session.commit()
        assert released is True

        updated = await repo.get_by_id(job.id)
        assert updated.last_run_status == "failed"
        assert updated.failure_count == 1
        assert updated.consecutive_failures == 1

    async def test_pause_resume(self, test_session):
        repo = ScheduledJobRepository(test_session)
        job = await repo.create(
            name="pausable",
            handler_name="h",
            schedule_type="interval",
            schedule_expr="60",
            next_run_at=datetime.now(tz_utc.utc),
        )
        await test_session.commit()

        assert await repo.pause(job.id) is True
        assert (await repo.get_by_id(job.id)).status == "paused"

        assert await repo.resume(job.id) is True
        assert (await repo.get_by_id(job.id)).status == "active"


class TestSchedulerProcessor:
    """Tests for the SchedulerProcessor."""

    async def test_run_once_no_jobs(self, test_session_factory):
        """run_once returns 0 when no jobs are due."""
        scheduler = SchedulerProcessor(
            test_session_factory, worker_id="test-sched-1"
        )
        count = await scheduler.run_once()
        assert count == 0

    async def test_run_once_executes_due_job(self, test_session_factory):
        """run_once executes a due job."""
        # Create a due job
        async with test_session_factory() as session:
            repo = ScheduledJobRepository(session)
            await repo.create(
                name="due-job",
                handler_name="test_handler",
                schedule_type="interval",
                schedule_expr="60",
                next_run_at=datetime.now(tz_utc.utc) - timedelta(minutes=1),
            )
            await session.commit()

        # Register a handler
        scheduler = SchedulerProcessor(
            test_session_factory, worker_id="test-sched-2"
        )

        handler_called = False

        async def test_handler(context):
            nonlocal handler_called
            handler_called = True

        scheduler.register_handler("test_handler", test_handler)

        count = await scheduler.run_once()
        assert count == 1
        assert handler_called is True

    async def test_run_once_skips_unknown_handler(self, test_session_factory):
        """run_once handles unknown handlers gracefully (fails but doesn't crash)."""
        async with test_session_factory() as session:
            repo = ScheduledJobRepository(session)
            await repo.create(
                name="unknown-handler-job",
                handler_name="nonexistent_handler",
                schedule_type="interval",
                schedule_expr="60",
                next_run_at=datetime.now(tz_utc.utc) - timedelta(minutes=1),
            )
            await session.commit()

        scheduler = SchedulerProcessor(
            test_session_factory, worker_id="test-sched-3"
        )
        # No handlers registered

        count = await scheduler.run_once()
        # The job fails (unknown handler) — count is 0 (no successful processing)
        # but the job's last_run_status should be "failed"
        assert scheduler._failed_count >= 1

        # Verify the job was attempted (lock acquired + released with failure)
        async with test_session_factory() as session:
            repo = ScheduledJobRepository(session)
            job = await repo.get_by_name("unknown-handler-job")
            assert job.last_run_status == "failed"
            assert job.failure_count == 1

    async def test_run_once_locks_job(self, test_session_factory):
        """run_once acquires a lock on the job."""
        async with test_session_factory() as session:
            repo = ScheduledJobRepository(session)
            job = await repo.create(
                name="lock-test",
                handler_name="test_handler",
                schedule_type="interval",
                schedule_expr="60",
                next_run_at=datetime.now(tz_utc.utc) - timedelta(minutes=1),
            )
            await session.commit()
            job_id = job.id

        scheduler = SchedulerProcessor(
            test_session_factory, worker_id="test-sched-4"
        )

        async def handler(context):
            pass

        scheduler.register_handler("test_handler", handler)
        await scheduler.run_once()

        # Verify the lock was released (job completed)
        async with test_session_factory() as session:
            job = await session.get(ScheduledJobModel, job_id)
            assert job.locked_by is None
            assert job.last_run_status == "success"
            assert job.run_count == 1


class TestDefaultScheduledJobs:
    """Tests for the default scheduled jobs."""

    def test_8_default_jobs_defined(self):
        """8 default scheduled jobs are defined."""
        assert len(DEFAULT_SCHEDULED_JOBS) == 8

    def test_cleanup_sessions_job_defined(self):
        assert any(j["name"] == "cleanup_expired_sessions" for j in DEFAULT_SCHEDULED_JOBS)

    def test_cleanup_tokens_job_defined(self):
        assert any(j["name"] == "cleanup_expired_tokens" for j in DEFAULT_SCHEDULED_JOBS)

    def test_cleanup_refresh_tokens_job_defined(self):
        assert any(j["name"] == "cleanup_expired_refresh_tokens" for j in DEFAULT_SCHEDULED_JOBS)

    def test_cleanup_notifications_job_defined(self):
        assert any(j["name"] == "cleanup_expired_notifications" for j in DEFAULT_SCHEDULED_JOBS)

    def test_heartbeat_check_job_defined(self):
        assert any(j["name"] == "heartbeat_check" for j in DEFAULT_SCHEDULED_JOBS)

    def test_daily_analytics_job_defined(self):
        assert any(j["name"] == "daily_analytics" for j in DEFAULT_SCHEDULED_JOBS)

    def test_weekly_summary_job_defined(self):
        assert any(j["name"] == "weekly_summary" for j in DEFAULT_SCHEDULED_JOBS)

    def test_8_default_handlers_defined(self):
        """8 default handlers are defined."""
        assert len(DEFAULT_HANDLERS) == 8

    async def test_ensure_default_jobs_scheduled(self, test_session_factory):
        """ensure_default_jobs_scheduled creates all default jobs."""
        await ensure_default_jobs_scheduled(test_session_factory)

        async with test_session_factory() as session:
            repo = ScheduledJobRepository(session)
            jobs = await repo.list_all()
            assert len(jobs) == 8

    async def test_ensure_default_jobs_scheduled_idempotent(self, test_session_factory):
        """ensure_default_jobs_scheduled is idempotent."""
        await ensure_default_jobs_scheduled(test_session_factory)
        await ensure_default_jobs_scheduled(test_session_factory)

        async with test_session_factory() as session:
            repo = ScheduledJobRepository(session)
            jobs = await repo.list_all()
            assert len(jobs) == 8  # Not 16


class TestCleanupHandlers:
    """Tests for the cleanup handler functions."""

    async def test_cleanup_expired_sessions_handler(self, test_session_factory):
        """cleanup_expired_sessions_handler runs without error."""
        context = {"session_factory": test_session_factory}
        result = await cleanup_expired_sessions_handler(context)
        assert "deleted" in result

    async def test_cleanup_expired_tokens_handler(self, test_session_factory):
        """cleanup_expired_tokens_handler runs without error."""
        context = {"session_factory": test_session_factory}
        result = await cleanup_expired_tokens_handler(context)
        assert "verification_deleted" in result
        assert "reset_deleted" in result

    async def test_cleanup_expired_notifications_handler(self, test_session_factory):
        """cleanup_expired_notifications_handler runs without error."""
        # Create an expired notification
        from app.infrastructure.database.orm.background import NotificationModel
        user_id = await create_test_user(test_session_factory() if False else None) if False else uuid4()
        # Just create a notification directly
        async with test_session_factory() as session:
            from tests.workers.conftest import create_test_user
            user_id = await create_test_user(session)
            session.add(NotificationModel(
                id=uuid4(),
                user_id=user_id,
                notification_type="test",
                channel="in_app",
                priority="normal",
                status="queued",
                title="Expired",
                body="body",
                scheduled_at=datetime.now(tz_utc.utc) - timedelta(hours=2),
                expires_at=datetime.now(tz_utc.utc) - timedelta(hours=1),
            ))
            await session.commit()

        context = {"session_factory": test_session_factory}
        result = await cleanup_expired_notifications_handler(context)
        assert "marked_failed" in result
        assert result["marked_failed"] >= 1

    async def test_heartbeat_check_handler(self, test_session_factory):
        """heartbeat_check_handler runs without error."""
        context = {"session_factory": test_session_factory}
        result = await heartbeat_check_handler(context)
        assert "dead_detected" in result
        assert "marked" in result
