"""Tests for the metrics collector.

Tests:
- Collect returns a BackgroundMetrics snapshot
- Outbox metrics (pending, dispatched, dead_lettered)
- Worker metrics (active, dead)
- Dead letter metrics
- Email metrics
- Notification metrics
- Throughput metrics
- to_dict serialization
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as tz_utc
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.infrastructure.database.orm.auth import AuthAuditLogModel
from app.infrastructure.database.orm.background import (
    DeadLetterEventModel,
    EmailDeliveryLogModel,
    NotificationModel,
    WorkerHeartbeatModel,
)
from app.infrastructure.database.orm.core import OutboxEventModel
from app.workers.metrics import BackgroundMetrics, MetricsCollector

from tests.workers.conftest import create_test_outbox_event, create_test_user


pytestmark = pytest.mark.asyncio


class TestMetricsCollector:
    """Tests for the MetricsCollector."""

    async def test_collect_returns_snapshot(self, test_session_factory):
        """collect returns a BackgroundMetrics object."""
        collector = MetricsCollector(test_session_factory)
        metrics = await collector.collect()
        assert isinstance(metrics, BackgroundMetrics)
        assert metrics.collected_at != ""

    async def test_collect_empty_database(self, test_session_factory):
        """Metrics are zero for an empty database."""
        collector = MetricsCollector(test_session_factory)
        metrics = await collector.collect()
        assert metrics.outbox_pending == 0
        assert metrics.outbox_dispatched == 0
        assert metrics.workers_active == 0
        assert metrics.dead_letters_unresolved == 0

    async def test_outbox_pending_count(self, test_session_factory):
        """outbox_pending counts pending events."""
        async with test_session_factory() as session:
            await create_test_outbox_event(session, status="pending")
            await create_test_outbox_event(session, status="pending")
            await create_test_outbox_event(session, status="dispatched")
            await session.commit()

        collector = MetricsCollector(test_session_factory)
        metrics = await collector.collect()
        assert metrics.outbox_pending == 2
        assert metrics.outbox_dispatched == 1

    async def test_outbox_dead_lettered_count(self, test_session_factory):
        """outbox_dead_lettered counts dead-lettered events."""
        async with test_session_factory() as session:
            await create_test_outbox_event(session, status="dead_lettered")
            await session.commit()

        collector = MetricsCollector(test_session_factory)
        metrics = await collector.collect()
        assert metrics.outbox_dead_lettered == 1

    async def test_worker_metrics(self, test_session_factory):
        """Worker metrics are collected correctly."""
        from datetime import datetime, timezone as tz_utc
        async with test_session_factory() as session:
            # Active worker
            session.add(WorkerHeartbeatModel(
                id=uuid4(),
                worker_id="active-1",
                worker_type="worker",
                hostname="test",
                process_id=123,
                status="running",
                last_seen_at=datetime.now(tz_utc.utc),
                started_at=datetime.now(tz_utc.utc),
                jobs_processed=10,
                jobs_failed=1,
                shutdown_requested=False,
            ))
            # Dead worker (stale heartbeat)
            stale = datetime.now(tz_utc.utc) - timedelta(seconds=120)
            session.add(WorkerHeartbeatModel(
                id=uuid4(),
                worker_id="dead-1",
                worker_type="worker",
                hostname="test",
                process_id=124,
                status="running",
                last_seen_at=stale,
                started_at=stale,
                jobs_processed=5,
                jobs_failed=2,
                shutdown_requested=False,
            ))
            await session.commit()

        collector = MetricsCollector(test_session_factory)
        metrics = await collector.collect()
        assert metrics.workers_active == 1
        assert metrics.workers_dead == 1
        assert metrics.workers_total_processed == 15  # 10 + 5
        assert metrics.workers_total_failed == 3  # 1 + 2

    async def test_dead_letter_metrics(self, test_session_factory):
        """Dead letter metrics are collected correctly."""
        async with test_session_factory() as session:
            for _ in range(3):
                session.add(DeadLetterEventModel(
                    id=uuid4(),
                    original_event_id=uuid4(),
                    event_type="TestEvent",
                    aggregate_id=uuid4(),
                    aggregate_type="Test",
                    payload={},
                    originating_schema="test",
                    error_message="error",
                    error_type="ValueError",
                    retry_count=3,
                    retry_history=[],
                    severity="error",
                ))
            await session.commit()

        collector = MetricsCollector(test_session_factory)
        metrics = await collector.collect()
        assert metrics.dead_letters_unresolved == 3

    async def test_email_metrics(self, test_session_factory):
        """Email metrics are collected correctly."""
        async with test_session_factory() as session:
            for status in ["sent", "sent", "failed", "bounced"]:
                session.add(EmailDeliveryLogModel(
                    id=uuid4(),
                    to_address="user@example.com",
                    from_address="noreply@example.com",
                    subject="Test",
                    template_name="test",
                    status=status,
                ))
            await session.commit()

        collector = MetricsCollector(test_session_factory)
        metrics = await collector.collect()
        assert metrics.emails_sent == 2  # 2 "sent"
        assert metrics.emails_failed == 1
        assert metrics.emails_bounced == 1

    async def test_notification_metrics(self, test_session_factory):
        """Notification metrics are collected correctly."""
        async with test_session_factory() as session:
            user_id = await create_test_user(session)
            for status in ["queued", "queued", "sent", "delivered", "failed"]:
                session.add(NotificationModel(
                    id=uuid4(),
                    user_id=user_id,
                    notification_type="test",
                    channel="in_app",
                    priority="normal",
                    status=status,
                    title="Test",
                    body="body",
                    scheduled_at=datetime.now(tz_utc.utc),
                ))
            await session.commit()

        collector = MetricsCollector(test_session_factory)
        metrics = await collector.collect()
        assert metrics.notifications_queued == 2
        assert metrics.notifications_sent == 1
        assert metrics.notifications_delivered == 1
        assert metrics.notifications_failed == 1

    async def test_to_dict_serialization(self, test_session_factory):
        """to_dict returns a serializable dict."""
        collector = MetricsCollector(test_session_factory)
        metrics = await collector.collect()
        d = metrics.to_dict()
        assert isinstance(d, dict)
        assert "outbox" in d
        assert "workers" in d
        assert "email" in d
        assert "notifications" in d
        assert "throughput_per_minute" in d
        assert "collected_at" in d

    async def test_events_being_retried(self, test_session_factory):
        """events_being_retried counts pending events with attempt_count > 0."""
        async with test_session_factory() as session:
            # Pending event that has been retried
            event = await create_test_outbox_event(session, status="pending")
            event.dispatch_attempt_count = 2
            await session.commit()

        collector = MetricsCollector(test_session_factory)
        metrics = await collector.collect()
        assert metrics.events_being_retried == 1


class TestBackgroundMetrics:
    """Tests for the BackgroundMetrics dataclass."""

    def test_default_values(self):
        metrics = BackgroundMetrics()
        assert metrics.outbox_pending == 0
        assert metrics.workers_active == 0
        assert metrics.collected_at == ""

    def test_to_dict(self):
        metrics = BackgroundMetrics(
            outbox_pending=5,
            workers_active=2,
        )
        d = metrics.to_dict()
        assert d["outbox"]["pending"] == 5
        assert d["workers"]["active"] == 2
