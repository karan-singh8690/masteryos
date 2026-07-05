"""Repositories for background processing tables.

Provides typed access to:
- DeadLetterEventRepository (dead_letter_events)
- NotificationRepository (notifications)
- NotificationPreferenceRepository (notification_preferences)
- ScheduledJobRepository (scheduled_jobs)
- WorkerHeartbeatRepository (worker_heartbeats)
- EmailDeliveryLogRepository (email_delivery_log)
- OutboxLeaseRepository (outbox_leases)
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone as tz_utc
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.orm.background import (
    DeadLetterEventModel,
    EmailDeliveryLogModel,
    NotificationModel,
    NotificationPreferenceModel,
    OutboxLeaseModel,
    ScheduledJobModel,
    WorkerHeartbeatModel,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(tz_utc.utc)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz_utc.utc)
    return dt


# ============================================================
# Dead Letter Repository
# ============================================================


class DeadLetterEventRepository:
    """Repository for infrastructure.dead_letter_events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        original_event_id: UUID,
        event_type: str,
        aggregate_id: UUID,
        aggregate_type: str,
        payload: dict[str, Any],
        originating_schema: str,
        error_message: str,
        error_type: str,
        retry_count: int = 0,
        retry_history: list[dict] | None = None,
        stack_trace: str | None = None,
        subscriber_handler: str | None = None,
        final_worker_id: str | None = None,
        severity: str = "error",
        actor_user_id: UUID | None = None,
    ) -> DeadLetterEventModel:
        model = DeadLetterEventModel(
            id=uuid4(),
            original_event_id=original_event_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            actor_user_id=actor_user_id,
            payload=payload,
            originating_schema=originating_schema,
            error_message=error_message,
            error_type=error_type,
            stack_trace=stack_trace,
            retry_count=retry_count,
            retry_history=retry_history or [],
            subscriber_handler=subscriber_handler,
            final_worker_id=final_worker_id,
            severity=severity,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_id(self, id: UUID) -> DeadLetterEventModel | None:
        return await self._session.get(DeadLetterEventModel, id)

    async def list_unresolved(
        self, limit: int = 100, offset: int = 0
    ) -> Sequence[DeadLetterEventModel]:
        stmt = (
            select(DeadLetterEventModel)
            .where(DeadLetterEventModel.resolved_at.is_(None))
            .order_by(DeadLetterEventModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_by_event_type(
        self, event_type: str, limit: int = 100
    ) -> Sequence[DeadLetterEventModel]:
        stmt = (
            select(DeadLetterEventModel)
            .where(DeadLetterEventModel.event_type == event_type)
            .order_by(DeadLetterEventModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def resolve(
        self,
        id: UUID,
        resolved_by: UUID | None = None,
        notes: str | None = None,
    ) -> bool:
        stmt = (
            update(DeadLetterEventModel)
            .where(
                DeadLetterEventModel.id == id,
                DeadLetterEventModel.resolved_at.is_(None),
            )
            .values(
                resolved_at=_utcnow(),
                resolved_by=resolved_by,
                resolution_notes=notes,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def count_unresolved(self) -> int:
        stmt = (
            select(func.count())
            .select_from(DeadLetterEventModel)
            .where(DeadLetterEventModel.resolved_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete_old(self, before: datetime) -> int:
        """Delete resolved dead letters older than `before`."""
        stmt = delete(DeadLetterEventModel).where(
            DeadLetterEventModel.resolved_at.is_not(None),
            DeadLetterEventModel.resolved_at < before,
        )
        result = await self._session.execute(stmt)
        return result.rowcount


# ============================================================
# Notification Repository
# ============================================================


class NotificationRepository:
    """Repository for administration.notifications."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        body: str,
        channel: str = "in_app",
        priority: str = "normal",
        payload: dict[str, Any] | None = None,
        locale: str = "en-US",
        dedup_key: str | None = None,
        scheduled_at: datetime | None = None,
        expires_at: datetime | None = None,
        related_aggregate_id: UUID | None = None,
        related_aggregate_type: str | None = None,
    ) -> NotificationModel:
        model = NotificationModel(
            id=uuid4(),
            user_id=user_id,
            notification_type=notification_type,
            channel=channel,
            priority=priority,
            status="queued",
            title=title,
            body=body,
            payload=payload or {},
            locale=locale,
            dedup_key=dedup_key,
            scheduled_at=scheduled_at or _utcnow(),
            expires_at=expires_at,
            related_aggregate_id=related_aggregate_id,
            related_aggregate_type=related_aggregate_type,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_id(self, id: UUID) -> NotificationModel | None:
        return await self._session.get(NotificationModel, id)

    async def list_by_user(
        self,
        user_id: UUID,
        include_read: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[NotificationModel]:
        stmt = (
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
        )
        if not include_read:
            stmt = stmt.where(
                NotificationModel.status.in_(["queued", "sent", "delivered"])
            )
        stmt = stmt.order_by(NotificationModel.scheduled_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_queued_for_delivery(
        self, limit: int = 100
    ) -> Sequence[NotificationModel]:
        """List notifications that are queued and due for delivery."""
        now = _utcnow()
        stmt = (
            select(NotificationModel)
            .where(
                NotificationModel.status == "queued",
                NotificationModel.scheduled_at <= now,
            )
            .order_by(
                # Priority order: urgent first, then by scheduled_at
                NotificationModel.priority.desc(),
                NotificationModel.scheduled_at.asc(),
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_expired(self, limit: int = 100) -> Sequence[NotificationModel]:
        """List notifications that have expired (should be marked failed)."""
        now = _utcnow()
        stmt = (
            select(NotificationModel)
            .where(
                NotificationModel.status == "queued",
                NotificationModel.expires_at.is_not(None),
                NotificationModel.expires_at < now,
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def mark_sent(self, id: UUID) -> bool:
        stmt = (
            update(NotificationModel)
            .where(NotificationModel.id == id, NotificationModel.status == "queued")
            .values(status="sent", sent_at=_utcnow())
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def mark_delivered(self, id: UUID) -> bool:
        stmt = (
            update(NotificationModel)
            .where(NotificationModel.id == id, NotificationModel.status == "sent")
            .values(status="delivered", delivered_at=_utcnow())
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def mark_opened(self, id: UUID) -> bool:
        stmt = (
            update(NotificationModel)
            .where(NotificationModel.id == id, NotificationModel.status == "delivered")
            .values(status="opened", opened_at=_utcnow())
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def mark_dismissed(self, id: UUID) -> bool:
        stmt = (
            update(NotificationModel)
            .where(
                NotificationModel.id == id,
                NotificationModel.status.in_(["queued", "sent", "delivered", "opened"]),
            )
            .values(status="dismissed", dismissed_at=_utcnow())
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def mark_failed(self, id: UUID, reason: str) -> bool:
        stmt = (
            update(NotificationModel)
            .where(NotificationModel.id == id, NotificationModel.status == "queued")
            .values(status="failed", failed_at=_utcnow(), failure_reason=reason)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def count_unread(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.status.in_(["queued", "sent", "delivered"]),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def check_dedup(
        self, user_id: UUID, notification_type: str, dedup_key: str
    ) -> bool:
        """Check if a notification with this dedup key already exists."""
        stmt = (
            select(func.count())
            .select_from(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.notification_type == notification_type,
                NotificationModel.dedup_key == dedup_key,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0


# ============================================================
# Notification Preference Repository
# ============================================================


class NotificationPreferenceRepository:
    """Repository for administration.notification_preferences."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user(self, user_id: UUID) -> NotificationPreferenceModel | None:
        stmt = select(NotificationPreferenceModel).where(
            NotificationPreferenceModel.user_id == user_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: UUID) -> NotificationPreferenceModel:
        """Get the user's preferences, creating defaults if none exist."""
        prefs = await self.get_by_user(user_id)
        if prefs is None:
            prefs = NotificationPreferenceModel(
                id=uuid4(),
                user_id=user_id,
            )
            self._session.add(prefs)
            await self._session.flush()
        return prefs

    async def update(
        self,
        user_id: UUID,
        **updates: Any,
    ) -> NotificationPreferenceModel | None:
        prefs = await self.get_by_user(user_id)
        if prefs is None:
            return None

        for key, value in updates.items():
            if hasattr(prefs, key) and value is not None:
                setattr(prefs, key, value)

        await self._session.flush()
        return prefs

    async def is_channel_enabled(
        self, user_id: UUID, channel: str, category: str | None = None
    ) -> bool:
        """Check if a channel is enabled for the user (with category override)."""
        prefs = await self.get_by_user(user_id)
        if prefs is None:
            # Defaults: email + in_app enabled, others disabled
            if channel in ("email", "in_app"):
                return True
            return False

        # Check category first (security is always enabled)
        if category == "security":
            return prefs.security_notifications_enabled

        # Check channel
        if channel == "email":
            enabled = prefs.email_enabled
        elif channel == "in_app":
            enabled = prefs.in_app_enabled
        elif channel == "push":
            enabled = prefs.push_enabled
        elif channel == "sms":
            enabled = prefs.sms_enabled
        else:
            enabled = False

        if not enabled:
            return False

        # Check category overrides
        if category == "achievement":
            return prefs.achievement_notifications_enabled
        if category == "marketing":
            return prefs.marketing_notifications_enabled
        if category == "reminder":
            return prefs.reminder_notifications_enabled

        return True

    async def is_in_quiet_hours(self, user_id: UUID, now: datetime | None = None) -> bool:
        """Check if the user is currently in quiet hours."""
        prefs = await self.get_by_user(user_id)
        if prefs is None or not prefs.quiet_hours_start or not prefs.quiet_hours_end:
            return False

        # Convert now to user's timezone
        import zoneinfo
        try:
            tz = zoneinfo.ZoneInfo(prefs.timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        local_now = (now or _utcnow()).astimezone(tz)
        local_hour_min = local_now.strftime("%H:%M")

        start = prefs.quiet_hours_start
        end = prefs.quiet_hours_end

        # Handle overnight quiet hours (e.g., 22:00 - 07:00)
        if start <= end:
            return start <= local_hour_min < end
        else:
            return local_hour_min >= start or local_hour_min < end


# ============================================================
# Scheduled Job Repository
# ============================================================


class ScheduledJobRepository:
    """Repository for infrastructure.scheduled_jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        name: str,
        handler_name: str,
        schedule_type: str,
        schedule_expr: str,
        next_run_at: datetime,
        description: str | None = None,
        max_runtime_seconds: int = 300,
    ) -> ScheduledJobModel:
        model = ScheduledJobModel(
            id=uuid4(),
            name=name,
            description=description,
            handler_name=handler_name,
            schedule_type=schedule_type,
            schedule_expr=schedule_expr,
            status="active",
            next_run_at=next_run_at,
            max_runtime_seconds=max_runtime_seconds,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_id(self, id: UUID) -> ScheduledJobModel | None:
        return await self._session.get(ScheduledJobModel, id)

    async def get_by_name(self, name: str) -> ScheduledJobModel | None:
        stmt = select(ScheduledJobModel).where(ScheduledJobModel.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self) -> Sequence[ScheduledJobModel]:
        stmt = (
            select(ScheduledJobModel)
            .where(ScheduledJobModel.status == "active")
            .order_by(ScheduledJobModel.next_run_at)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_due(self, limit: int = 10) -> Sequence[ScheduledJobModel]:
        """List jobs that are due to run (next_run_at <= now) and not locked."""
        now = _utcnow()
        stmt = (
            select(ScheduledJobModel)
            .where(
                ScheduledJobModel.status == "active",
                ScheduledJobModel.next_run_at <= now,
                ScheduledJobModel.locked_by.is_(None),
            )
            .order_by(ScheduledJobModel.next_run_at)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def acquire_lock(
        self, job_id: UUID, worker_id: str, lock_duration: timedelta
    ) -> bool:
        """Try to acquire a lock on a job. Returns True if acquired."""
        now = _utcnow()
        expires = now + lock_duration
        stmt = (
            update(ScheduledJobModel)
            .where(
                ScheduledJobModel.id == job_id,
                (ScheduledJobModel.locked_by.is_(None))
                | (ScheduledJobModel.lock_expires_at < now),
            )
            .values(
                locked_by=worker_id,
                locked_at=now,
                lock_expires_at=expires,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def release_lock(
        self,
        job_id: UUID,
        worker_id: str,
        success: bool,
        error: str | None = None,
        duration_ms: int | None = None,
        next_run_at: datetime | None = None,
    ) -> bool:
        """Release the lock on a job and record the run result."""
        now = _utcnow()
        # Expire any cached objects so we get fresh data from the DB
        self._session.expire_all()
        # Get current values
        job = await self.get_by_id(job_id)
        if job is None or job.locked_by != worker_id:
            return False

        new_consecutive_failures = job.consecutive_failures + (0 if success else 1)

        values = {
            "locked_by": None,
            "locked_at": None,
            "lock_expires_at": None,
            "last_run_at": now,
            "last_run_status": "success" if success else "failed",
            "last_run_error": error,
            "last_run_duration_ms": duration_ms,
            "run_count": job.run_count + 1,
            "failure_count": job.failure_count + (0 if success else 1),
            "consecutive_failures": new_consecutive_failures,
        }
        if next_run_at:
            values["next_run_at"] = next_run_at
        elif success:
            # Reset consecutive failures on success
            values["consecutive_failures"] = 0
            # Compute next run based on schedule (simplified: interval-based)
            try:
                interval_seconds = int(job.schedule_expr)
                values["next_run_at"] = now + timedelta(seconds=interval_seconds)
            except (ValueError, TypeError):
                values["next_run_at"] = now + timedelta(hours=1)  # Default

        stmt = (
            update(ScheduledJobModel)
            .where(ScheduledJobModel.id == job_id, ScheduledJobModel.locked_by == worker_id)
            .values(**values)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def pause(self, job_id: UUID) -> bool:
        stmt = (
            update(ScheduledJobModel)
            .where(ScheduledJobModel.id == job_id)
            .values(status="paused")
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def resume(self, job_id: UUID) -> bool:
        stmt = (
            update(ScheduledJobModel)
            .where(ScheduledJobModel.id == job_id)
            .values(status="active")
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def list_all(self) -> Sequence[ScheduledJobModel]:
        stmt = select(ScheduledJobModel).order_by(ScheduledJobModel.name)
        result = await self._session.execute(stmt)
        return result.scalars().all()


# ============================================================
# Worker Heartbeat Repository
# ============================================================


class WorkerHeartbeatRepository:
    """Repository for infrastructure.worker_heartbeats."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        worker_id: str,
        worker_type: str,
        status: str,
        hostname: str | None = None,
        process_id: int | None = None,
        jobs_processed: int = 0,
        jobs_failed: int = 0,
        current_job: str | None = None,
        shutdown_requested: bool = False,
    ) -> WorkerHeartbeatModel:
        now = _utcnow()
        existing = await self.get_by_worker_id(worker_id)
        if existing is None:
            model = WorkerHeartbeatModel(
                id=uuid4(),
                worker_id=worker_id,
                worker_type=worker_type,
                hostname=hostname,
                process_id=process_id,
                status=status,
                last_seen_at=now,
                started_at=now,
                jobs_processed=jobs_processed,
                jobs_failed=jobs_failed,
                current_job=current_job,
                shutdown_requested=shutdown_requested,
            )
            self._session.add(model)
        else:
            existing.worker_type = worker_type
            existing.hostname = hostname or existing.hostname
            existing.process_id = process_id or existing.process_id
            existing.status = status
            existing.last_seen_at = now
            existing.jobs_processed = jobs_processed
            existing.jobs_failed = jobs_failed
            existing.current_job = current_job
            existing.shutdown_requested = shutdown_requested
            model = existing
        await self._session.flush()
        return model

    async def get_by_worker_id(self, worker_id: str) -> WorkerHeartbeatModel | None:
        stmt = select(WorkerHeartbeatModel).where(
            WorkerHeartbeatModel.worker_id == worker_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[WorkerHeartbeatModel]:
        stmt = (
            select(WorkerHeartbeatModel)
            .order_by(WorkerHeartbeatModel.last_seen_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_active(self, stale_after_seconds: float = 60.0) -> Sequence[WorkerHeartbeatModel]:
        """List workers with a recent heartbeat."""
        cutoff = _utcnow() - timedelta(seconds=stale_after_seconds)
        stmt = (
            select(WorkerHeartbeatModel)
            .where(
                WorkerHeartbeatModel.last_seen_at >= cutoff,
                WorkerHeartbeatModel.status.in_(["starting", "running", "draining"]),
            )
            .order_by(WorkerHeartbeatModel.last_seen_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_dead(self, stale_after_seconds: float = 60.0) -> Sequence[WorkerHeartbeatModel]:
        """List workers whose heartbeat is stale (likely crashed)."""
        cutoff = _utcnow() - timedelta(seconds=stale_after_seconds)
        stmt = (
            select(WorkerHeartbeatModel)
            .where(
                WorkerHeartbeatModel.last_seen_at < cutoff,
                WorkerHeartbeatModel.status.in_(["starting", "running", "draining"]),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def mark_dead(self, worker_id: str) -> bool:
        stmt = (
            update(WorkerHeartbeatModel)
            .where(WorkerHeartbeatModel.worker_id == worker_id)
            .values(status="crashed")
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def request_shutdown(self, worker_id: str) -> bool:
        stmt = (
            update(WorkerHeartbeatModel)
            .where(WorkerHeartbeatModel.worker_id == worker_id)
            .values(shutdown_requested=True)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def delete_old(self, before: datetime) -> int:
        """Delete stopped/crashed worker records older than `before`."""
        stmt = delete(WorkerHeartbeatModel).where(
            WorkerHeartbeatModel.status.in_(["stopped", "crashed"]),
            WorkerHeartbeatModel.last_seen_at < before,
        )
        result = await self._session.execute(stmt)
        return result.rowcount


# ============================================================
# Email Delivery Log Repository
# ============================================================


class EmailDeliveryLogRepository:
    """Repository for infrastructure.email_delivery_log."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        to_address: str,
        from_address: str,
        subject: str,
        template_name: str,
        notification_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> EmailDeliveryLogModel:
        model = EmailDeliveryLogModel(
            id=uuid4(),
            notification_id=notification_id,
            user_id=user_id,
            to_address=to_address,
            from_address=from_address,
            subject=subject,
            template_name=template_name,
            status="queued",
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_id(self, id: UUID) -> EmailDeliveryLogModel | None:
        return await self._session.get(EmailDeliveryLogModel, id)

    async def mark_sent(
        self,
        id: UUID,
        message_id: str | None = None,
        smtp_response: str | None = None,
    ) -> bool:
        stmt = (
            update(EmailDeliveryLogModel)
            .where(EmailDeliveryLogModel.id == id)
            .values(
                status="sent",
                message_id=message_id,
                smtp_response=smtp_response,
                sent_at=_utcnow(),
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def mark_delivered(self, id: UUID) -> bool:
        stmt = (
            update(EmailDeliveryLogModel)
            .where(EmailDeliveryLogModel.id == id)
            .values(status="delivered", delivered_at=_utcnow())
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def mark_bounced(
        self,
        id: UUID,
        bounce_type: str = "hard",
        bounce_reason: str | None = None,
    ) -> bool:
        stmt = (
            update(EmailDeliveryLogModel)
            .where(EmailDeliveryLogModel.id == id)
            .values(
                status="bounced",
                bounce_type=bounce_type,
                bounce_reason=bounce_reason,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def mark_failed(
        self,
        id: UUID,
        error: str,
        next_retry_at: datetime | None = None,
    ) -> bool:
        stmt = (
            update(EmailDeliveryLogModel)
            .where(EmailDeliveryLogModel.id == id)
            .values(
                status="failed",
                error_message=error,
                next_retry_at=next_retry_at,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def increment_attempt(self, id: UUID) -> bool:
        stmt = (
            update(EmailDeliveryLogModel)
            .where(EmailDeliveryLogModel.id == id)
            .values(attempt_count=EmailDeliveryLogModel.attempt_count + 1)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def list_by_user(
        self, user_id: UUID, limit: int = 50
    ) -> Sequence[EmailDeliveryLogModel]:
        stmt = (
            select(EmailDeliveryLogModel)
            .where(EmailDeliveryLogModel.user_id == user_id)
            .order_by(EmailDeliveryLogModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_pending_retry(self, limit: int = 50) -> Sequence[EmailDeliveryLogModel]:
        """List failed emails scheduled for retry."""
        now = _utcnow()
        stmt = (
            select(EmailDeliveryLogModel)
            .where(
                EmailDeliveryLogModel.status.in_(["failed", "deferred"]),
                EmailDeliveryLogModel.next_retry_at.is_not(None),
                EmailDeliveryLogModel.next_retry_at <= now,
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_by_status(self) -> dict[str, int]:
        """Count emails by status."""
        stmt = (
            select(EmailDeliveryLogModel.status, func.count())
            .group_by(EmailDeliveryLogModel.status)
        )
        result = await self._session.execute(stmt)
        return dict(result.all())


__all__ = [
    "DeadLetterEventRepository",
    "NotificationRepository",
    "NotificationPreferenceRepository",
    "ScheduledJobRepository",
    "WorkerHeartbeatRepository",
    "EmailDeliveryLogRepository",
]
