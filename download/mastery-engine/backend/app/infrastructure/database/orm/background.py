"""ORM models for background processing tables.

Maps to the `infrastructure` PostgreSQL schema.
Tables:
- dead_letter_events (events that exhausted retries)
- notifications (queued/sent/delivered notifications)
- notification_preferences (per-user channel + frequency prefs)
- scheduled_jobs (recurring job definitions)
- worker_heartbeats (worker health tracking)
- email_delivery_log (SMTP delivery audit trail)
- outbox_leases (visibility timeout / worker leasing)
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index

from app.infrastructure.database.orm.base import Base, TimestampMixin


# ============================================================
# Dead Letter Events (exhausted retries)
# ============================================================


class DeadLetterEventModel(Base, TimestampMixin):
    """ORM model for infrastructure.dead_letter_events.

    Events that exhausted all retry attempts. Each record captures:
    - The original event payload + metadata
    - The error that caused the final failure
    - The full stack trace
    - The retry history (timestamps + errors)
    - The worker that performed the final attempt

    Dead-lettered events can be replayed via the admin API.
    """

    __tablename__ = "dead_letter_events"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('warning', 'error', 'critical')",
            name="chk_dead_letter_severity",
        ),
        Index("idx_dead_letters_event_type", "event_type", "created_at"),
        Index("idx_dead_letters_aggregate", "aggregate_id"),
        Index("idx_dead_letters_unresolved", "resolved_at"),
        {"schema": "infrastructure"},
    )

    original_event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    originating_schema: Mapped[str] = mapped_column(String(50), nullable=False)

    # Failure details
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    error_type: Mapped[str] = mapped_column(String(200), nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Retry history: [{attempt, timestamp, error, duration_ms}, ...]
    retry_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    subscriber_handler: Mapped[str | None] = mapped_column(String(255), nullable=True)
    final_worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="error")

    # Resolution
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    replayed_as_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


# ============================================================
# Notifications
# ============================================================


class NotificationModel(Base):
    """ORM model for administration.notifications.

    A notification is a message queued for a user via a channel
    (in-app, email, push). The lifecycle is tracked by status:
    QUEUED → SENT → DELIVERED → OPENED/DISMISSED, or QUEUED → FAILED.

    Notifications are created by the NotificationService in response to
    domain events (e.g., AchievementUnlocked, SecurityIncidentDetected).
    """

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'sent', 'delivered', 'opened', 'dismissed', 'failed')",
            name="chk_notifications_status",
        ),
        CheckConstraint(
            "channel IN ('in_app', 'email', 'push', 'sms')",
            name="chk_notifications_channel",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="chk_notifications_priority",
        ),
        Index("idx_notifications_user_status", "user_id", "status"),
        Index("idx_notifications_status_scheduled", "status", "scheduled_at"),
        Index("idx_notifications_user_unread", "user_id", postgresql_where=text("status IN ('queued', 'sent', 'delivered')")),
        Index("idx_notifications_dedup", "user_id", "notification_type", "dedup_key", unique=True),
        {"schema": "administration"},
    )

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(128), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="in_app")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")

    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en-US")

    # Deduplication (e.g., "don't send 'review due' more than once per day per concept")
    dedup_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Scheduling + expiration
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Lifecycle timestamps
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Related aggregate (e.g., achievement_id, attempt_id)
    related_aggregate_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    related_aggregate_type: Mapped[str | None] = mapped_column(String(50), nullable=True)


# ============================================================
# Notification Preferences
# ============================================================


class NotificationPreferenceModel(Base):
    """ORM model for administration.notification_preferences.

    Per-user preferences for notification channels + frequency.
    Security notifications are always enabled (cannot be opted out).
    """

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_notification_preferences_user"),
        CheckConstraint(
            "digest_frequency IN ('immediate', 'hourly', 'daily', 'weekly', 'never')",
            name="chk_notif_pref_digest",
        ),
        CheckConstraint(
            "quiet_hours_start IS NULL OR quiet_hours_end IS NULL OR "
            "quiet_hours_start <> quiet_hours_end",
            name="chk_notif_pref_quiet_hours",
        ),
        {"schema": "administration"},
    )

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, unique=True)

    # Channel toggles
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Category toggles
    security_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )  # Always True — security notifications are mandatory
    achievement_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    marketing_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    reminder_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Digest
    digest_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="immediate")

    # Quiet hours (HH:MM in user's timezone)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "22:00"
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "07:00"
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")


# ============================================================
# Scheduled Jobs (recurring)
# ============================================================


class ScheduledJobModel(Base, TimestampMixin):
    """ORM model for infrastructure.scheduled_jobs.

    Defines recurring background jobs (cron-style schedule + handler name).
    The scheduler tracks the next_run_at and locks the job while executing.

    Jobs are idempotent: the handler can be safely called multiple times.
    """

    __tablename__ = "scheduled_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'paused', 'disabled')",
            name="chk_scheduled_jobs_status",
        ),
        CheckConstraint(
            "schedule_type IN ('cron', 'interval', 'one_time')",
            name="chk_scheduled_jobs_type",
        ),
        Index("idx_scheduled_jobs_next_run", "next_run_at", postgresql_where=text("status = 'active'")),
        Index("idx_scheduled_jobs_locked", "locked_by", postgresql_where=text("locked_by IS NOT NULL")),
        {"schema": "infrastructure"},
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    handler_name: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    schedule_expr: Mapped[str] = mapped_column(String(100), nullable=False)  # cron expr or interval
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # success/failed
    last_run_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_run_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Worker locking
    locked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)  # worker_id
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Execution stats
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Configuration
    max_runtime_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=3)


# ============================================================
# Worker Heartbeats
# ============================================================


class WorkerHeartbeatModel(Base, TimestampMixin):
    """ORM model for infrastructure.worker_heartbeats.

    Each worker writes a heartbeat every N seconds. If a worker's
    heartbeat is stale (> 60s), it's considered dead and its leases
    are released.
    """

    __tablename__ = "worker_heartbeats"
    __table_args__ = (
        UniqueConstraint("worker_id", name="uq_worker_heartbeats_worker_id"),
        Index("idx_worker_heartbeats_status", "status"),
        Index("idx_worker_heartbeats_last_seen", "last_seen_at"),
        {"schema": "infrastructure"},
    )

    worker_id: Mapped[str] = mapped_column(String(100), nullable=False)
    worker_type: Mapped[str] = mapped_column(String(50), nullable=False)  # dispatcher, scheduler, etc.
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    process_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="starting")
    # starting, running, draining, stopped, crashed

    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Stats
    jobs_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_job: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Graceful shutdown
    shutdown_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ============================================================
# Email Delivery Log
# ============================================================


class EmailDeliveryLogModel(Base, TimestampMixin):
    """ORM model for infrastructure.email_delivery_log.

    Immutable audit trail for every email sent (or attempted).
    Used for:
    - Bounce detection (mark user's email as bouncing)
    - Delivery analytics
    - Troubleshooting
    - Compliance (CAN-SPAM, GDPR)
    """

    __tablename__ = "email_delivery_log"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'sent', 'delivered', 'bounced', 'failed', 'deferred')",
            name="chk_email_delivery_status",
        ),
        Index("idx_email_delivery_user", "user_id"),
        Index("idx_email_delivery_status", "status", "created_at"),
        Index("idx_email_delivery_message_id", "message_id"),
        {"schema": "infrastructure"},
    )

    notification_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    to_address: Mapped[str] = mapped_column(Text, nullable=False)
    from_address: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Failure details
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    bounce_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # hard, soft
    bounce_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Retry
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ============================================================
# Outbox Leases (visibility timeout)
# ============================================================


class OutboxLeaseModel(Base, TimestampMixin):
    """ORM model for infrastructure.outbox_leases.

    When a worker picks up an event from the outbox, it creates a lease.
    The lease has a visibility timeout — if the worker doesn't complete
    the event within the timeout, another worker can pick it up.

    This prevents lost events when a worker crashes mid-processing.
    """

    __tablename__ = "outbox_leases"
    __table_args__ = (
        UniqueConstraint("outbox_event_id", name="uq_outbox_leases_event"),
        Index("idx_outbox_leases_expires", "expires_at", postgresql_where=text("released_at IS NULL")),
        Index("idx_outbox_leases_worker", "worker_id"),
        {"schema": "infrastructure"},
    )

    outbox_event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    worker_id: Mapped[str] = mapped_column(String(100), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)  # completed, failed, timed_out


__all__ = [
    "DeadLetterEventModel",
    "NotificationModel",
    "NotificationPreferenceModel",
    "ScheduledJobModel",
    "WorkerHeartbeatModel",
    "EmailDeliveryLogModel",
    "OutboxLeaseModel",
]
