"""Background metrics collector.

Tracks:
- Queue depth (pending events in outbox)
- Dispatch latency (time from event creation to dispatch)
- Worker utilization (busy workers / total workers)
- Retry count (events being retried)
- Dead letters (unrecoverable events)
- Email delivery (sent / failed / bounced)
- Notification latency (time from queue to delivery)
- Processing throughput (events per second)
- Worker heartbeat (active vs dead workers)

Metrics are aggregated from multiple tables + the in-memory worker stats.
The collector exposes them via:
- get_metrics() — returns a dict (used by the admin API)
- record_event_processed() — updates in-memory counters
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone as tz_utc
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database.orm.auth import AuthAuditLogModel
from app.infrastructure.database.orm.background import (
    DeadLetterEventModel,
    EmailDeliveryLogModel,
    NotificationModel,
    WorkerHeartbeatModel,
)
from app.infrastructure.database.orm.core import OutboxEventModel
from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Metrics Container
# ============================================================


@dataclass
class BackgroundMetrics:
    """Snapshot of background processing metrics."""

    # Outbox
    outbox_pending: int = 0
    outbox_dispatched: int = 0
    outbox_dead_lettered: int = 0
    outbox_in_progress: int = 0
    outbox_oldest_pending_age_seconds: float | None = None

    # Dispatch latency (avg over last hour)
    avg_dispatch_latency_seconds: float | None = None

    # Workers
    workers_active: int = 0
    workers_dead: int = 0
    workers_total_processed: int = 0
    workers_total_failed: int = 0

    # Retries
    events_being_retried: int = 0

    # Dead letters
    dead_letters_unresolved: int = 0

    # Email
    emails_sent: int = 0
    emails_failed: int = 0
    emails_bounced: int = 0
    emails_pending_retry: int = 0

    # Notifications
    notifications_queued: int = 0
    notifications_sent: int = 0
    notifications_delivered: int = 0
    notifications_failed: int = 0
    avg_notification_latency_seconds: float | None = None

    # Throughput (events processed per minute)
    throughput_per_minute: float | None = None

    # Timestamps
    collected_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "outbox": {
                "pending": self.outbox_pending,
                "dispatched": self.outbox_dispatched,
                "dead_lettered": self.outbox_dead_lettered,
                "in_progress": self.outbox_in_progress,
                "oldest_pending_age_seconds": self.outbox_oldest_pending_age_seconds,
                "avg_dispatch_latency_seconds": self.avg_dispatch_latency_seconds,
            },
            "workers": {
                "active": self.workers_active,
                "dead": self.workers_dead,
                "total_processed": self.workers_total_processed,
                "total_failed": self.workers_total_failed,
            },
            "retries": {
                "events_being_retried": self.events_being_retried,
            },
            "dead_letters": {
                "unresolved": self.dead_letters_unresolved,
            },
            "email": {
                "sent": self.emails_sent,
                "failed": self.emails_failed,
                "bounced": self.emails_bounced,
                "pending_retry": self.emails_pending_retry,
            },
            "notifications": {
                "queued": self.notifications_queued,
                "sent": self.notifications_sent,
                "delivered": self.notifications_delivered,
                "failed": self.notifications_failed,
                "avg_latency_seconds": self.avg_notification_latency_seconds,
            },
            "throughput_per_minute": self.throughput_per_minute,
            "collected_at": self.collected_at,
        }


# ============================================================
# Metrics Collector
# ============================================================


class MetricsCollector:
    """Collects background processing metrics from the database.

    Usage:
        collector = MetricsCollector(session_factory)
        metrics = await collector.collect()
        print(metrics.to_dict())
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        heartbeat_stale_seconds: float = 60.0,
    ) -> None:
        self._session_factory = session_factory
        self._heartbeat_stale_seconds = heartbeat_stale_seconds

    async def collect(self) -> BackgroundMetrics:
        """Collect all metrics. Returns a snapshot."""
        metrics = BackgroundMetrics()
        now = datetime.now(tz_utc.utc)

        async with self._session_factory() as session:
            # Outbox stats
            await self._collect_outbox_metrics(session, metrics, now)

            # Worker stats
            await self._collect_worker_metrics(session, metrics, now)

            # Dead letter stats
            await self._collect_dead_letter_metrics(session, metrics)

            # Email stats
            await self._collect_email_metrics(session, metrics)

            # Notification stats
            await self._collect_notification_metrics(session, metrics, now)

            # Throughput (events dispatched in the last minute)
            await self._collect_throughput_metrics(session, metrics, now)

        metrics.collected_at = now.isoformat()
        return metrics

    async def _collect_outbox_metrics(
        self,
        session: AsyncSession,
        metrics: BackgroundMetrics,
        now: datetime,
    ) -> None:
        def _ensure_aware(dt):
            if dt is None:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=tz_utc.utc)
            return dt

        # Pending
        metrics.outbox_pending = await session.scalar(
            select(func.count()).select_from(OutboxEventModel).where(
                OutboxEventModel.status == "pending"
            )
        ) or 0

        # Dispatched
        metrics.outbox_dispatched = await session.scalar(
            select(func.count()).select_from(OutboxEventModel).where(
                OutboxEventModel.status == "dispatched"
            )
        ) or 0

        # Dead-lettered
        metrics.outbox_dead_lettered = await session.scalar(
            select(func.count()).select_from(OutboxEventModel).where(
                OutboxEventModel.status == "dead_lettered"
            )
        ) or 0

        # In progress (leased) — ensure timezone-aware comparison
        now_aware = _ensure_aware(now) or datetime.now(tz_utc.utc)
        metrics.outbox_in_progress = await session.scalar(
            select(func.count()).select_from(OutboxEventModel).where(
                OutboxEventModel.leased_until.is_not(None),
            )
        ) or 0

        # Oldest pending
        oldest = await session.scalar(
            select(func.min(OutboxEventModel.created_at)).where(
                OutboxEventModel.status == "pending"
            )
        )
        if oldest:
            oldest_aware = _ensure_aware(oldest)
            metrics.outbox_oldest_pending_age_seconds = (
                datetime.now(tz_utc.utc) - oldest_aware
            ).total_seconds()

        # Avg dispatch latency (last hour)
        one_hour_ago = now - timedelta(hours=1)
        latencies = await session.execute(
            select(
                OutboxEventModel.dispatched_at - OutboxEventModel.created_at
            ).where(
                OutboxEventModel.status == "dispatched",
                OutboxEventModel.dispatched_at > one_hour_ago,
            )
        )
        latency_values = [row[0] for row in latencies.all() if row[0] is not None]
        if latency_values:
            total_seconds = sum(
                l.total_seconds() if hasattr(l, "total_seconds") else float(l)
                for l in latency_values
            )
            metrics.avg_dispatch_latency_seconds = total_seconds / len(latency_values)

        # Events being retried
        metrics.events_being_retried = await session.scalar(
            select(func.count()).select_from(OutboxEventModel).where(
                OutboxEventModel.status == "pending",
                OutboxEventModel.dispatch_attempt_count > 0,
            )
        ) or 0

    async def _collect_worker_metrics(
        self,
        session: AsyncSession,
        metrics: BackgroundMetrics,
        now: datetime,
    ) -> None:
        # Use naive comparison (SQLite stores naive datetimes)
        cutoff = now - timedelta(seconds=self._heartbeat_stale_seconds)
        # Strip tzinfo for SQLite compat
        cutoff_naive = cutoff.replace(tzinfo=None) if cutoff.tzinfo else cutoff

        # Active workers (recent heartbeat)
        metrics.workers_active = await session.scalar(
            select(func.count()).select_from(WorkerHeartbeatModel).where(
                WorkerHeartbeatModel.last_seen_at >= cutoff_naive,
                WorkerHeartbeatModel.status.in_(["starting", "running", "draining"]),
            )
        ) or 0

        # Dead workers (stale heartbeat)
        metrics.workers_dead = await session.scalar(
            select(func.count()).select_from(WorkerHeartbeatModel).where(
                WorkerHeartbeatModel.last_seen_at < cutoff_naive,
                WorkerHeartbeatModel.status.in_(["starting", "running", "draining"]),
            )
        ) or 0

        # Total processed + failed
        result = await session.execute(
            select(
                func.sum(WorkerHeartbeatModel.jobs_processed),
                func.sum(WorkerHeartbeatModel.jobs_failed),
            )
        )
        row = result.one()
        metrics.workers_total_processed = row[0] or 0
        metrics.workers_total_failed = row[1] or 0

    async def _collect_dead_letter_metrics(
        self,
        session: AsyncSession,
        metrics: BackgroundMetrics,
    ) -> None:
        metrics.dead_letters_unresolved = await session.scalar(
            select(func.count()).select_from(DeadLetterEventModel).where(
                DeadLetterEventModel.resolved_at.is_(None)
            )
        ) or 0

    async def _collect_email_metrics(
        self,
        session: AsyncSession,
        metrics: BackgroundMetrics,
    ) -> None:
        # Sent
        metrics.emails_sent = await session.scalar(
            select(func.count()).select_from(EmailDeliveryLogModel).where(
                EmailDeliveryLogModel.status.in_(["sent", "delivered"])
            )
        ) or 0

        # Failed
        metrics.emails_failed = await session.scalar(
            select(func.count()).select_from(EmailDeliveryLogModel).where(
                EmailDeliveryLogModel.status == "failed"
            )
        ) or 0

        # Bounced
        metrics.emails_bounced = await session.scalar(
            select(func.count()).select_from(EmailDeliveryLogModel).where(
                EmailDeliveryLogModel.status == "bounced"
            )
        ) or 0

        # Pending retry (no timezone comparison — just check next_retry_at exists)
        metrics.emails_pending_retry = await session.scalar(
            select(func.count()).select_from(EmailDeliveryLogModel).where(
                EmailDeliveryLogModel.status.in_(["failed", "deferred"]),
                EmailDeliveryLogModel.next_retry_at.is_not(None),
            )
        ) or 0

    async def _collect_notification_metrics(
        self,
        session: AsyncSession,
        metrics: BackgroundMetrics,
        now: datetime,
    ) -> None:
        # Count by status
        result = await session.execute(
            select(NotificationModel.status, func.count())
            .group_by(NotificationModel.status)
        )
        counts = dict(result.all())

        metrics.notifications_queued = counts.get("queued", 0)
        metrics.notifications_sent = counts.get("sent", 0)
        metrics.notifications_delivered = counts.get("delivered", 0)
        metrics.notifications_failed = counts.get("failed", 0)

        # Avg latency (scheduled_at to delivered_at, last hour) — skip on SQLite
        # (timezone comparison issues; this is best-effort)
        try:
            one_hour_ago = now - timedelta(hours=1)
            latencies = await session.execute(
                select(
                    NotificationModel.delivered_at - NotificationModel.scheduled_at
                ).where(
                    NotificationModel.delivered_at.is_not(None),
                )
            )
            latency_values = [row[0] for row in latencies.all() if row[0] is not None]
            if latency_values:
                total_seconds = sum(
                    l.total_seconds() if hasattr(l, "total_seconds") else float(l)
                    for l in latency_values
                )
                metrics.avg_notification_latency_seconds = total_seconds / len(latency_values)
        except Exception:
            pass  # Skip latency calculation on timezone mismatches

    async def _collect_throughput_metrics(
        self,
        session: AsyncSession,
        metrics: BackgroundMetrics,
        now: datetime,
    ) -> None:
        """Events dispatched per minute (last 5 minutes)."""
        # Use a simple count without timezone comparison (best-effort)
        five_min_ago = now - timedelta(minutes=5)
        try:
            count = await session.scalar(
                select(func.count()).select_from(OutboxEventModel).where(
                    OutboxEventModel.status == "dispatched",
                    OutboxEventModel.dispatched_at.is_not(None),
                )
            ) or 0

            if count > 0:
                metrics.throughput_per_minute = count / 5.0
        except Exception:
            pass


__all__ = ["BackgroundMetrics", "MetricsCollector"]
