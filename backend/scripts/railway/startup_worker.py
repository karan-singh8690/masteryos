#!/usr/bin/env python3
"""Worker startup script for Railway (Task 028).

Runs the background worker with:
1. Wait for PostgreSQL (with retries + reconnect logic)
2. Wait for Redis (with retries)
3. Start the worker host (outbox dispatcher, scheduler, notifications, email)
4. Graceful shutdown on SIGTERM/SIGINT

The worker writes heartbeats to the worker_heartbeats table and
reconnects automatically if the database connection is lost.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)


async def wait_for_database(max_retries: int = 30, delay: float = 2.0) -> bool:
    """Wait for PostgreSQL with exponential backoff."""
    from app.shared.config import get_settings
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = get_settings()
    safe_url = settings.database_url.split("@")[1] if "@" in settings.database_url else "unknown"
    print(f"[worker] Waiting for database at {safe_url}...")

    for attempt in range(1, max_retries + 1):
        try:
            engine = create_async_engine(settings.database_url)
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    print(f"[worker] Database available (attempt {attempt})")
                    await engine.dispose()
                    return True
            await engine.dispose()
        except Exception as e:
            backoff = min(delay * (1.5 ** (attempt - 1)), 30.0)
            print(f"[worker] Database not ready (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                print(f"[worker] Retrying in {backoff:.1f}s...")
                await asyncio.sleep(backoff)

    print(f"[worker] FATAL: Database not available after {max_retries} attempts")
    return False


async def wait_for_redis(max_retries: int = 15, delay: float = 2.0) -> bool:
    """Wait for Redis with exponential backoff."""
    from app.shared.config import get_settings
    import redis.asyncio as redis

    settings = get_settings()
    print(f"[worker] Waiting for Redis at {settings.redis_host}:{settings.redis_port}...")

    for attempt in range(1, max_retries + 1):
        try:
            client = redis.from_url(settings.redis_url)
            pong = await client.ping()
            await client.aclose()
            if pong:
                print(f"[worker] Redis available (attempt {attempt})")
                return True
        except Exception as e:
            backoff = min(delay * (1.5 ** (attempt - 1)), 30.0)
            print(f"[worker] Redis not ready (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                print(f"[worker] Retrying in {backoff:.1f}s...")
                await asyncio.sleep(backoff)

    print(f"[worker] WARNING: Redis not available after {max_retries} attempts")
    return False


async def main() -> int:
    """Main worker startup sequence."""
    from app.shared.logging import configure_logging
    from app.shared.railway_config import detect_deployment
    from app.shared.config import get_settings

    configure_logging()
    settings = get_settings()
    print(f"[worker] Deployment environment: {detect_deployment()}")
    print(f"[worker] Starting worker process (env={settings.app_env.value})")

    # Step 1: Wait for PostgreSQL
    print("[worker] Step 1/3: Waiting for PostgreSQL...")
    if not await wait_for_database(max_retries=30, delay=2.0):
        print("[worker] FATAL: Cannot connect to PostgreSQL. Aborting.")
        return 1

    # Step 2: Wait for Redis
    print("[worker] Step 2/3: Waiting for Redis...")
    await wait_for_redis(max_retries=15, delay=2.0)

    # Step 3: Start the worker
    print("[worker] Step 3/3: Starting worker host...")
    from app.infrastructure.database.engine import get_session_factory
    from app.infrastructure.email import EmailService, InMemorySmtpClient, ProductionSmtpClient
    from app.infrastructure.scheduler.processor import (
        DEFAULT_HANDLERS,
        ensure_default_jobs_scheduled,
    )
    from app.workers.host import WorkerHost
    from app.workers.outbox_dispatcher import OutboxDispatcherProcessor
    from app.workers.processors import (
        CleanupProcessor,
        EmailProcessor,
        NotificationProcessor,
    )
    from app.infrastructure.scheduler import SchedulerProcessor
    from app.workers.subscriber_registry import (
        SubscriberRegistry,
        USER_REGISTERED,
        ATTEMPT_RECORDED,
        ACHIEVEMENT_UNLOCKED,
        SECURITY_INCIDENT_DETECTED,
    )

    session_factory = await get_session_factory()

    # Ensure default scheduled jobs exist
    await ensure_default_jobs_scheduled(session_factory)

    # Create the worker host
    host = WorkerHost(
        session_factory=session_factory,
        worker_type="background_worker",
    )
    print(f"[worker] Worker ID: {host.worker_id}")

    # Create the outbox dispatcher
    dispatcher = OutboxDispatcherProcessor(
        session_factory=session_factory,
        worker_id=host.worker_id,
    )

    # Register default subscribers
    registry = SubscriberRegistry()

    async def send_verification_email_handler(payload: dict) -> None:
        print(f"[worker] send_verification_email: user_id={payload.get('user_id')}")

    async def update_mastery_handler(payload: dict) -> None:
        print(f"[worker] update_mastery: attempt_id={payload.get('attempt_id')}")

    async def send_achievement_notification_handler(payload: dict) -> None:
        print(f"[worker] send_achievement_notification: user_id={payload.get('user_id')}")

    async def send_security_alert_handler(payload: dict) -> None:
        print(f"[worker] send_security_alert: incident_type={payload.get('incident_type')}")

    registry.register(USER_REGISTERED, send_verification_email_handler)
    registry.register(ATTEMPT_RECORDED, update_mastery_handler)
    registry.register(ACHIEVEMENT_UNLOCKED, send_achievement_notification_handler)
    registry.register(SECURITY_INCIDENT_DETECTED, send_security_alert_handler)

    for event_type in registry.get_registered_event_types():
        for handler_name, handler in registry.get_handlers(event_type):
            dispatcher.subscribe(event_type, handler, handler_name)

    host.register_processor(dispatcher)

    # Create the scheduler
    scheduler = SchedulerProcessor(
        session_factory=session_factory,
        worker_id=host.worker_id,
    )
    for handler_name, handler in DEFAULT_HANDLERS.items():
        scheduler.register_handler(handler_name, handler)
    host.register_processor(scheduler)

    # Create the notification + email processor
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

    email_processor = EmailProcessor(
        session_factory=session_factory,
        worker_id=host.worker_id,
        email_service=email_service,
    )
    host.register_processor(email_processor)

    cleanup_processor = CleanupProcessor(
        session_factory=session_factory,
        worker_id=host.worker_id,
    )
    host.register_processor(cleanup_processor)

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def signal_handler():
        print("[worker] Shutdown signal received, stopping gracefully...")
        asyncio.create_task(host.stop()).add_done_callback(lambda _: shutdown_event.set())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Start the worker (runs forever until stopped)
    print("[worker] Worker started. Processing background jobs...")
    try:
        await host.start()
    except KeyboardInterrupt:
        await host.stop()

    print("[worker] Worker stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
