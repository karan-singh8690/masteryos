"""Background processors for notifications + emails.

- NotificationProcessor: Delivers queued notifications (in-app + email routing)
- EmailProcessor: Sends queued emails via SMTP (with retry)
- CleanupProcessor: Removes expired data (delegates to scheduler handlers)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone as tz_utc
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database.repositories.background import (
    EmailDeliveryLogRepository,
    NotificationRepository,
)
from app.infrastructure.email import EmailService, InMemorySmtpClient
from app.shared.logging import get_logger
from app.workers.host import WorkerProcessor
from app.workers.retry_engine import RetryEngine, FAST_RETRY_SCHEDULE

logger = get_logger(__name__)


# ============================================================
# Notification Processor
# ============================================================


class NotificationProcessor(WorkerProcessor):
    """Delivers queued notifications.

    For in-app notifications: marks as 'sent' immediately (the frontend
    polls for new notifications).

    For email notifications: creates an EmailDeliveryLog entry + sends
    via the EmailService. The actual SMTP send is done here (synchronously
    within the worker).

    The processor polls the notifications table for queued notifications
    that are due (scheduled_at <= now).
    """

    name = "notification_processor"

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        worker_id: str = "notif-1",
        batch_size: int = 50,
        email_service: EmailService | None = None,
    ) -> None:
        super().__init__(worker_id)
        self._session_factory = session_factory
        self._batch_size = batch_size
        self._email_service = email_service or EmailService(smtp_client=InMemorySmtpClient())

    async def run_once(self) -> int:
        """Process a batch of queued notifications."""
        async with self._session_factory() as session:
            repo = NotificationRepository(session)
            notifications = await repo.list_queued_for_delivery(limit=self._batch_size)

            if not notifications:
                return 0

            processed = 0
            for notification in notifications:
                self._current_job = f"notif-{notification.id}"
                try:
                    await self._deliver_notification(session, repo, notification)
                    self._processed_count += 1
                    processed += 1
                except Exception as exc:
                    await repo.mark_failed(notification.id, str(exc)[:500])
                    self._failed_count += 1
                    logger.error(
                        "notification_delivery_failed",
                        notification_id=str(notification.id),
                        error=str(exc),
                    )
                finally:
                    self._current_job = None

            await session.commit()
            return processed

    async def _deliver_notification(
        self,
        session: AsyncSession,
        repo: NotificationRepository,
        notification,
    ) -> None:
        """Deliver a single notification."""
        if notification.channel == "in_app":
            # In-app: mark as sent (frontend polls for new)
            await repo.mark_sent(notification.id)
            # Also mark as delivered (in-app is instant)
            await repo.mark_delivered(notification.id)
        elif notification.channel == "email":
            # Email: send via EmailService
            # Look up the user's email address
            from app.infrastructure.database.orm.identity import UserModel
            from sqlalchemy import select

            user_stmt = select(UserModel.email).where(UserModel.id == notification.user_id)
            result = await session.execute(user_stmt)
            email_address = result.scalar_one_or_none()

            if email_address is None:
                await repo.mark_failed(notification.id, "User email not found")
                return

            # Create email delivery log
            log_repo = EmailDeliveryLogRepository(session)
            log = await log_repo.create(
                to_address=email_address,
                from_address=self._email_service._from,
                subject=notification.title,
                template_name=notification.notification_type,
                notification_id=notification.id,
                user_id=notification.user_id,
            )

            # Send the email (use system_notification template as fallback)
            template_name = notification.notification_type
            if template_name not in self._email_service.get_template_names():
                template_name = "system_notification"

            context = {
                "title": notification.title,
                "body": notification.body,
                **notification.payload,
            }

            result = await self._email_service.send_template(
                to=email_address,
                template_name=template_name,
                context=context,
                user_id=notification.user_id,
                notification_id=notification.id,
            )

            if result.success:
                await log_repo.mark_sent(
                    log.id,
                    message_id=result.message_id,
                    smtp_response=result.smtp_response,
                )
                await repo.mark_sent(notification.id)
                await repo.mark_delivered(notification.id)
            else:
                await log_repo.mark_failed(log.id, result.error or "Unknown error")
                await repo.mark_failed(notification.id, result.error or "Email send failed")
        else:
            # Other channels (push, sms) — not implemented
            await repo.mark_failed(notification.id, f"Channel {notification.channel} not supported")


# ============================================================
# Email Processor (retries failed emails)
# ============================================================


class EmailProcessor(WorkerProcessor):
    """Retries failed email deliveries.

    Polls email_delivery_log for entries with status='failed' and
    next_retry_at <= now. Re-sends them via the EmailService.

    Uses FAST_RETRY_SCHEDULE (5s, 30s, 2min, 10min, 1h).
    """

    name = "email_processor"

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        worker_id: str = "email-1",
        batch_size: int = 50,
        email_service: EmailService | None = None,
    ) -> None:
        super().__init__(worker_id)
        self._session_factory = session_factory
        self._batch_size = batch_size
        self._email_service = email_service or EmailService(smtp_client=InMemorySmtpClient())
        self._retry_engine = RetryEngine(schedule=FAST_RETRY_SCHEDULE, jitter=False)

    async def run_once(self) -> int:
        """Process a batch of failed emails."""
        async with self._session_factory() as session:
            log_repo = EmailDeliveryLogRepository(session)
            pending = await log_repo.list_pending_retry(limit=self._batch_size)

            if not pending:
                return 0

            processed = 0
            for log in pending:
                self._current_job = f"email-{log.id}"
                try:
                    # Re-send the email (raw, since we don't have the template context)
                    # In production, we'd store the rendered body in the log
                    result = await self._email_service.send_raw(
                        to=log.to_address,
                        subject=log.subject,
                        html_body=f"<p>{log.subject}</p>",  # Simplified
                        text_body=log.subject,
                        from_address=log.from_address,
                    )

                    if result.success:
                        await log_repo.mark_sent(
                            log.id,
                            message_id=result.message_id,
                            smtp_response=result.smtp_response,
                        )
                        self._processed_count += 1
                        processed += 1
                    else:
                        # Schedule next retry or give up
                        if log.attempt_count + 1 >= self._retry_engine.max_retries:
                            await log_repo.mark_failed(log.id, result.error or "Max retries exceeded")
                        else:
                            next_retry = self._retry_engine.get_next_retry_time(log.attempt_count)
                            await log_repo.mark_failed(log.id, result.error or "Failed", next_retry_at=next_retry)
                            await log_repo.increment_attempt(log.id)
                        self._failed_count += 1
                except Exception as exc:
                    await log_repo.mark_failed(log.id, str(exc)[:500])
                    self._failed_count += 1
                finally:
                    self._current_job = None

            await session.commit()
            return processed


# ============================================================
# Cleanup Processor (delegates to scheduler handlers)
# ============================================================


class CleanupProcessor(WorkerProcessor):
    """Runs cleanup tasks (expired sessions, tokens, etc.).

    This processor delegates to the scheduler handlers — it's a thin
    wrapper that runs them on a fixed interval (separate from the
    scheduler's cron-based schedule, for testing + flexibility).
    """

    name = "cleanup_processor"

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        worker_id: str = "cleanup-1",
        cleanup_interval: int = 3600,  # 1 hour
    ) -> None:
        super().__init__(worker_id)
        self._session_factory = session_factory
        self._cleanup_interval = cleanup_interval
        self._last_run: float = 0

    async def run_once(self) -> int:
        """Run cleanup tasks if interval has elapsed."""
        now = time.time()
        if now - self._last_run < self._cleanup_interval:
            return 0

        self._last_run = now
        from app.infrastructure.scheduler.processor import (
            cleanup_expired_sessions_handler,
            cleanup_expired_tokens_handler,
            cleanup_expired_refresh_tokens_handler,
            cleanup_expired_notifications_handler,
        )

        context = {"session_factory": self._session_factory}
        processed = 0

        for handler in [
            cleanup_expired_sessions_handler,
            cleanup_expired_tokens_handler,
            cleanup_expired_refresh_tokens_handler,
            cleanup_expired_notifications_handler,
        ]:
            self._current_job = f"cleanup-{handler.__name__}"
            try:
                await handler(context)
                self._processed_count += 1
                processed += 1
            except Exception as exc:
                self._failed_count += 1
                logger.error("cleanup_task_failed", handler=handler.__name__, error=str(exc))
            finally:
                self._current_job = None

        return processed


__all__ = [
    "NotificationProcessor",
    "EmailProcessor",
    "CleanupProcessor",
]
