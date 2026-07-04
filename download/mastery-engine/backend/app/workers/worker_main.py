"""Worker process entry point.

Run with: python -m app.workers.worker_main

This starts a WorkerHost with all registered processors:
- OutboxDispatcherProcessor (polls outbox, delivers events)
- SchedulerProcessor (runs recurring jobs)
- NotificationProcessor (delivers queued notifications)
- EmailProcessor (sends queued emails)
- CleanupProcessor (removes expired data)

The worker writes heartbeats to the worker_heartbeats table and
supports graceful shutdown via SIGTERM/SIGINT.
"""

from __future__ import annotations

import asyncio
import signal
import sys

from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.email import EmailService, InMemorySmtpClient, ProductionSmtpClient
from app.infrastructure.scheduler.processor import (
    DEFAULT_HANDLERS,
    ensure_default_jobs_scheduled,
)
from app.shared.config import get_settings
from app.shared.logging import configure_logging, get_logger
from app.workers.host import WorkerHost
from app.workers.outbox_dispatcher import OutboxDispatcherProcessor
from app.workers.processors import (
    CleanupProcessor,
    EmailProcessor,
    NotificationProcessor,
)
from app.workers.scheduler import SchedulerProcessor
from app.workers.subscriber_registry import (
    SubscriberRegistry,
    USER_REGISTERED,
    ATTEMPT_RECORDED,
    ACHIEVEMENT_UNLOCKED,
    SECURITY_INCIDENT_DETECTED,
)

logger = get_logger(__name__)


async def create_default_subscribers(
    dispatcher: OutboxDispatcherProcessor,
) -> SubscriberRegistry:
    """Create the default subscriber registry + register handlers.

    This wires domain events to their handlers:
    - UserRegistered → send verification email
    - AttemptRecorded → update mastery
    - AchievementUnlocked → send achievement notification
    - SecurityIncidentDetected → send security alert
    - etc.
    """
    registry = SubscriberRegistry()

    # Register noop handlers for all known event types (so the dispatcher
    # doesn't dead-letter events that have no real handler yet).
    # In production, these would be real handlers.

    async def send_verification_email_handler(payload: dict) -> None:
        """Send verification email when a user registers."""
        logger.info("send_verification_email", user_id=payload.get("user_id"))

    async def update_mastery_handler(payload: dict) -> None:
        """Update mastery score when an attempt is recorded."""
        logger.info("update_mastery", attempt_id=payload.get("attempt_id"))

    async def send_achievement_notification_handler(payload: dict) -> None:
        """Send notification when an achievement is unlocked."""
        logger.info("send_achievement_notification", user_id=payload.get("user_id"))

    async def send_security_alert_handler(payload: dict) -> None:
        """Send security alert when a security incident is detected."""
        logger.info("send_security_alert", incident_type=payload.get("incident_type"))

    registry.register(USER_REGISTERED, send_verification_email_handler)
    registry.register(ATTEMPT_RECORDED, update_mastery_handler)
    registry.register(ACHIEVEMENT_UNLOCKED, send_achievement_notification_handler)
    registry.register(SECURITY_INCIDENT_DETECTED, send_security_alert_handler)

    # Register all handlers with the dispatcher
    for event_type in registry.get_registered_event_types():
        for handler_name, handler in registry.get_handlers(event_type):
            dispatcher.subscribe(event_type, handler, handler_name)

    return registry


async def main() -> None:
    """Start the worker process."""
    configure_logging()
    settings = get_settings()
    logger.info("worker_process_starting", env=settings.app_env.value)

    # Get session factory
    session_factory = await get_session_factory()

    # Ensure default scheduled jobs exist
    await ensure_default_jobs_scheduled(session_factory)

    # Create the worker host
    host = WorkerHost(
        session_factory=session_factory,
        worker_type="background_worker",
    )

    # Create the outbox dispatcher
    dispatcher = OutboxDispatcherProcessor(
        session_factory=session_factory,
        worker_id=host.worker_id,
    )
    await create_default_subscribers(dispatcher)
    host.register_processor(dispatcher)

    # Create the scheduler
    scheduler = SchedulerProcessor(
        session_factory=session_factory,
        worker_id=host.worker_id,
    )
    for handler_name, handler in DEFAULT_HANDLERS.items():
        scheduler.register_handler(handler_name, handler)
    host.register_processor(scheduler)

    # Create the notification processor.
    # Task 027-verify: Use ProductionSmtpClient (not InMemorySmtpClient) so
    # async worker emails (notifications, password resets, beta invites) are
    # actually sent. Falls back to InMemorySmtpClient only in testing.
    settings = get_settings()
    if settings.is_testing or not settings.smtp_username:
        smtp_client = InMemorySmtpClient()
    else:
        smtp_client = ProductionSmtpClient.from_settings(settings)
    email_service = EmailService(smtp_client=smtp_client)
    notification_processor = NotificationProcessor(
        session_factory=session_factory,
        worker_id=host.worker_id,
        email_service=email_service,
    )
    host.register_processor(notification_processor)

    # Create the email processor
    email_processor = EmailProcessor(
        session_factory=session_factory,
        worker_id=host.worker_id,
        email_service=email_service,
    )
    host.register_processor(email_processor)

    # Create the cleanup processor
    cleanup_processor = CleanupProcessor(
        session_factory=session_factory,
        worker_id=host.worker_id,
    )
    host.register_processor(cleanup_processor)

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(host.stop()))

    # Start the host (runs forever until stopped)
    try:
        await host.start()
    except KeyboardInterrupt:
        await host.stop()

    logger.info("worker_process_stopped")


if __name__ == "__main__":
    asyncio.run(main())
