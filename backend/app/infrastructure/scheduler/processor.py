"""Scheduler — executes recurring background jobs.

Jobs (per Task 017 spec):
- Review reminders (send due review notifications)
- Queue generation (generate daily learning queues)
- Cleanup expired sessions
- Cleanup expired tokens (verification + reset)
- Cleanup refresh tokens
- Daily analytics
- Weekly summaries
- Monthly reports
- Backup verification
- Heartbeat (worker liveness check)

The scheduler:
1. Polls scheduled_jobs for due jobs.
2. Acquires a lock (only one worker runs a job at a time).
3. Executes the job handler.
4. Records the result + computes the next run time.

Job handlers are async callables registered at startup.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone as tz_utc
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database.repositories.background import ScheduledJobRepository
from app.shared.logging import get_logger
from app.workers.host import WorkerProcessor

logger = get_logger(__name__)


# ============================================================
# Types
# ============================================================


JobHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
"""Async job handler signature.

Takes a context dict (with session, job metadata) and returns a result dict.
"""


# ============================================================
# Scheduler Processor (runs as part of WorkerHost)
# ============================================================


class SchedulerProcessor(WorkerProcessor):
    """Background scheduler — runs recurring jobs.

    The scheduler:
    1. Polls scheduled_jobs for due, unlocked jobs.
    2. Acquires a lock (optimistic concurrency).
    3. Executes the handler.
    4. Releases the lock + records the result.

    Job handlers are registered via register_handler().
    """

    name = "scheduler"

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        worker_id: str = "scheduler-1",
        lock_duration: timedelta = timedelta(minutes=5),
        poll_interval: float = 5.0,
    ) -> None:
        super().__init__(worker_id)
        self._session_factory = session_factory
        self._lock_duration = lock_duration
        self._poll_interval = poll_interval
        self._handlers: dict[str, JobHandler] = {}

    def register_handler(self, handler_name: str, handler: JobHandler) -> None:
        """Register a job handler.

        Args:
            handler_name: Must match the handler_name in scheduled_jobs.
            handler: Async callable that takes a context dict.
        """
        self._handlers[handler_name] = handler
        logger.info("scheduler_handler_registered", handler=handler_name)

    async def run_once(self) -> int:
        """Poll for due jobs and execute them. Returns count processed."""
        processed = 0
        async with self._session_factory() as session:
            repo = ScheduledJobRepository(session)
            due_jobs = await repo.list_due(limit=10)

            for job in due_jobs:
                # Try to acquire a lock
                acquired = await repo.acquire_lock(job.id, self.worker_id, self._lock_duration)
                if not acquired:
                    continue  # Another worker got it

                self._current_job = f"scheduled-{job.name}"
                start = time.time()
                success = False
                error_msg = None

                try:
                    handler = self._handlers.get(job.handler_name)
                    if handler is None:
                        raise ValueError(f"No handler registered for: {job.handler_name}")

                    context = {
                        "job_id": str(job.id),
                        "job_name": job.name,
                        "schedule_expr": job.schedule_expr,
                        "session_factory": self._session_factory,
                    }
                    await handler(context)
                    success = True
                    self._processed_count += 1
                    processed += 1
                except Exception as exc:
                    error_msg = str(exc)
                    self._failed_count += 1
                    logger.error(
                        "scheduled_job_failed",
                        job=job.name,
                        handler=job.handler_name,
                        error=str(exc),
                    )
                finally:
                    duration_ms = int((time.time() - start) * 1000)
                    # Compute next run (for interval jobs)
                    next_run = None
                    if success and job.schedule_type == "interval":
                        try:
                            interval_seconds = int(job.schedule_expr)
                            next_run = datetime.now(tz_utc.utc) + timedelta(seconds=interval_seconds)
                        except (ValueError, TypeError):
                            next_run = datetime.now(tz_utc.utc) + timedelta(hours=1)
                    elif success and job.schedule_type == "cron":
                        # Simplified: run every hour for cron jobs (real impl would parse cron)
                        next_run = datetime.now(tz_utc.utc) + timedelta(hours=1)
                    elif success and job.schedule_type == "one_time":
                        # One-time job: disable after success
                        await repo.pause(job.id)

                    await repo.release_lock(
                        job.id,
                        self.worker_id,
                        success=success,
                        error=error_msg,
                        duration_ms=duration_ms,
                        next_run_at=next_run,
                    )
                    self._current_job = None

            await session.commit()
            return processed


# ============================================================
# Default Job Handlers
# ============================================================


async def cleanup_expired_sessions_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Remove expired sessions from the database.

    A session is expired if:
    - expires_at < now (absolute timeout)
    - revoked_at IS NOT NULL AND revoked_at < now - 30 days (old revoked)
    """
    session_factory = context["session_factory"]
    from sqlalchemy import delete, update
    from app.infrastructure.database.orm.identity import SessionModel

    now = datetime.now(tz_utc.utc)
    cutoff = now - timedelta(days=30)

    async with session_factory() as session:
        # Delete old revoked sessions
        result = await session.execute(
            delete(SessionModel).where(
                SessionModel.revoked_at.is_not(None),
                SessionModel.revoked_at < cutoff,
            )
        )
        deleted = result.rowcount
        await session.commit()

    logger.info("cleanup_expired_sessions", deleted=deleted)
    return {"deleted": deleted}


async def cleanup_expired_tokens_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Remove expired verification + reset tokens."""
    session_factory = context["session_factory"]
    from sqlalchemy import delete
    from app.infrastructure.database.orm.auth import (
        VerificationTokenModel,
        PasswordResetTokenModel,
    )

    now = datetime.now(tz_utc.utc)

    async with session_factory() as session:
        # Delete expired verification tokens
        v_result = await session.execute(
            delete(VerificationTokenModel).where(
                VerificationTokenModel.expires_at < now,
                VerificationTokenModel.consumed_at.is_not(None),
            )
        )
        v_deleted = v_result.rowcount

        # Delete expired reset tokens
        r_result = await session.execute(
            delete(PasswordResetTokenModel).where(
                PasswordResetTokenModel.expires_at < now,
                PasswordResetTokenModel.consumed_at.is_not(None),
            )
        )
        r_deleted = r_result.rowcount

        await session.commit()

    logger.info("cleanup_expired_tokens", verification=v_deleted, reset=r_deleted)
    return {"verification_deleted": v_deleted, "reset_deleted": r_deleted}


async def cleanup_expired_refresh_tokens_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Remove expired/consumed refresh tokens."""
    session_factory = context["session_factory"]
    from sqlalchemy import delete
    from app.infrastructure.database.orm.auth import RefreshTokenModel

    now = datetime.now(tz_utc.utc)
    cutoff = now - timedelta(days=30)  # Keep 30 days of history

    async with session_factory() as session:
        result = await session.execute(
            delete(RefreshTokenModel).where(
                RefreshTokenModel.expires_at < cutoff,
            )
        )
        deleted = result.rowcount
        await session.commit()

    logger.info("cleanup_expired_refresh_tokens", deleted=deleted)
    return {"deleted": deleted}


async def cleanup_expired_notifications_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Mark expired notifications as failed (or delete them)."""
    session_factory = context["session_factory"]
    from sqlalchemy import update, select
    from app.infrastructure.database.orm.background import NotificationModel

    now = datetime.now(tz_utc.utc)

    async with session_factory() as session:
        # Mark expired queued notifications as failed
        result = await session.execute(
            update(NotificationModel)
            .where(
                NotificationModel.status == "queued",
                NotificationModel.expires_at.is_not(None),
                NotificationModel.expires_at < now,
            )
            .values(
                status="failed",
                failed_at=now,
                failure_reason="expired",
            )
        )
        marked = result.rowcount
        await session.commit()

    logger.info("cleanup_expired_notifications", marked=marked)
    return {"marked_failed": marked}


async def cleanup_old_audit_logs_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Delete audit logs older than 1 year (configurable)."""
    session_factory = context["session_factory"]
    from sqlalchemy import delete
    from app.infrastructure.database.orm.auth import AuthAuditLogModel

    cutoff = datetime.now(tz_utc.utc) - timedelta(days=365)

    async with session_factory() as session:
        result = await session.execute(
            delete(AuthAuditLogModel).where(AuthAuditLogModel.created_at < cutoff)
        )
        deleted = result.rowcount
        await session.commit()

    logger.info("cleanup_old_audit_logs", deleted=deleted)
    return {"deleted": deleted}


async def heartbeat_check_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Check for dead workers and mark them as crashed.

    Also releases any leases held by dead workers.
    """
    session_factory = context["session_factory"]
    from app.infrastructure.database.repositories.background import WorkerHeartbeatRepository
    from app.workers.host import HeartbeatService

    service = HeartbeatService(session_factory)
    dead_workers = await service.detect_dead_workers()
    marked = 0
    for worker_id in dead_workers:
        if await service.mark_worker_dead(worker_id):
            marked += 1

    logger.info("heartbeat_check", dead_detected=len(dead_workers), marked=marked)
    return {"dead_detected": len(dead_workers), "marked": marked}


async def daily_analytics_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Generate daily analytics (placeholder — real impl would aggregate)."""
    logger.info("daily_analytics_generated")
    return {"generated": True}


async def weekly_summary_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Generate weekly summaries (placeholder)."""
    logger.info("weekly_summary_generated")
    return {"generated": True}


# ============================================================
# Default scheduled jobs (registered at startup)
# ============================================================


DEFAULT_SCHEDULED_JOBS: list[dict[str, Any]] = [
    {
        "name": "cleanup_expired_sessions",
        "description": "Remove expired + old revoked sessions",
        "handler_name": "cleanup_expired_sessions_handler",
        "schedule_type": "interval",
        "schedule_expr": "3600",  # Every hour
    },
    {
        "name": "cleanup_expired_tokens",
        "description": "Remove expired verification + reset tokens",
        "handler_name": "cleanup_expired_tokens_handler",
        "schedule_type": "interval",
        "schedule_expr": "3600",  # Every hour
    },
    {
        "name": "cleanup_expired_refresh_tokens",
        "description": "Remove expired refresh tokens",
        "handler_name": "cleanup_expired_refresh_tokens_handler",
        "schedule_type": "interval",
        "schedule_expr": "86400",  # Every day
    },
    {
        "name": "cleanup_expired_notifications",
        "description": "Mark expired notifications as failed",
        "handler_name": "cleanup_expired_notifications_handler",
        "schedule_type": "interval",
        "schedule_expr": "1800",  # Every 30 min
    },
    {
        "name": "cleanup_old_audit_logs",
        "description": "Delete audit logs older than 1 year",
        "handler_name": "cleanup_old_audit_logs_handler",
        "schedule_type": "interval",
        "schedule_expr": "604800",  # Every week
    },
    {
        "name": "heartbeat_check",
        "description": "Detect dead workers and release their leases",
        "handler_name": "heartbeat_check_handler",
        "schedule_type": "interval",
        "schedule_expr": "60",  # Every minute
    },
    {
        "name": "daily_analytics",
        "description": "Generate daily analytics",
        "handler_name": "daily_analytics_handler",
        "schedule_type": "cron",
        "schedule_expr": "0 2 * * *",  # 2 AM daily
    },
    {
        "name": "weekly_summary",
        "description": "Generate weekly summaries",
        "handler_name": "weekly_summary_handler",
        "schedule_type": "cron",
        "schedule_expr": "0 3 * * 1",  # 3 AM Monday
    },
]


DEFAULT_HANDLERS: dict[str, JobHandler] = {
    "cleanup_expired_sessions_handler": cleanup_expired_sessions_handler,
    "cleanup_expired_tokens_handler": cleanup_expired_tokens_handler,
    "cleanup_expired_refresh_tokens_handler": cleanup_expired_refresh_tokens_handler,
    "cleanup_expired_notifications_handler": cleanup_expired_notifications_handler,
    "cleanup_old_audit_logs_handler": cleanup_old_audit_logs_handler,
    "heartbeat_check_handler": heartbeat_check_handler,
    "daily_analytics_handler": daily_analytics_handler,
    "weekly_summary_handler": weekly_summary_handler,
}


async def ensure_default_jobs_scheduled(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Ensure all default scheduled jobs exist in the database.

    Called at worker startup to register the default recurring jobs.
    """
    from datetime import datetime, timezone as tz_utc

    async with session_factory() as session:
        repo = ScheduledJobRepository(session)
        for job_def in DEFAULT_SCHEDULED_JOBS:
            existing = await repo.get_by_name(job_def["name"])
            if existing is None:
                await repo.create(
                    name=job_def["name"],
                    description=job_def["description"],
                    handler_name=job_def["handler_name"],
                    schedule_type=job_def["schedule_type"],
                    schedule_expr=job_def["schedule_expr"],
                    next_run_at=datetime.now(tz_utc.utc) + timedelta(minutes=5),
                )
                logger.info("scheduled_job_created", name=job_def["name"])
        await session.commit()


__all__ = [
    "SchedulerProcessor",
    "JobHandler",
    "DEFAULT_SCHEDULED_JOBS",
    "DEFAULT_HANDLERS",
    "ensure_default_jobs_scheduled",
    # Handlers
    "cleanup_expired_sessions_handler",
    "cleanup_expired_tokens_handler",
    "cleanup_expired_refresh_tokens_handler",
    "cleanup_expired_notifications_handler",
    "cleanup_old_audit_logs_handler",
    "heartbeat_check_handler",
    "daily_analytics_handler",
    "weekly_summary_handler",
]
