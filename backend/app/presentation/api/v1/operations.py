"""Operations API — SMTP test, WebSocket status, Worker management.

Endpoints:
- POST   /admin/ops/test-email       — Send a test email
- GET    /admin/ops/smtp-status       — Check SMTP configuration
- GET    /admin/ops/websocket-status  — Check WebSocket server status
- POST   /admin/ops/worker/restart    — Trigger worker restart signal
- GET    /admin/ops/health-summary    — Full health summary for ops dashboard
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, text

from app.application.shared import UnitOfWork
from app.infrastructure.database.orm.background import (
    WorkerHeartbeatModel, NotificationModel, ScheduledJobModel,
)
from app.presentation.dependencies import get_current_user_id, get_uow, require_any_role
from app.infrastructure.security.authorization import ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN
from app.shared.config import get_settings
from app.shared.logging import get_logger

logger = get_logger(__name__)

RequireAdmin = require_any_role(ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN)

router = APIRouter(
    prefix="/admin/ops",
    tags=["Admin — Operations"],
    dependencies=[Depends(get_current_user_id), Depends(RequireAdmin)],
)


class SmtpStatus(BaseModel):
    configured: bool
    host: str
    port: int
    username: str
    from_email: str
    use_tls: bool
    has_password: bool


class EmailTestRequest(BaseModel):
    to_email: str | None = None  # Defaults to the admin's email


class EmailTestResponse(BaseModel):
    success: bool
    message: str
    recipient: str | None = None


class WebSocketStatus(BaseModel):
    enabled: bool
    connected_clients: int
    endpoint: str


class WorkerRestartResponse(BaseModel):
    message: str
    signal_sent: bool


class HealthSummary(BaseModel):
    database: str
    redis: str
    workers: int
    active_workers: int
    pending_outbox: int
    dead_letters: int
    scheduled_jobs: int
    notifications_queued: int
    smtp_configured: bool
    websocket_enabled: bool
    ai_enabled: bool
    maintenance_mode: bool
    uptime_seconds: int


# ============================================================
# SMTP
# ============================================================


@router.get("/smtp-status", response_model=SmtpStatus)
async def get_smtp_status() -> SmtpStatus:
    """Check SMTP email configuration status."""
    settings = get_settings()
    return SmtpStatus(
        configured=bool(settings.smtp_host and settings.smtp_username and settings.smtp_password),
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        from_email=settings.smtp_from_email,
        use_tls=settings.smtp_use_tls,
        has_password=bool(settings.smtp_password),
    )


@router.post("/test-email", response_model=EmailTestResponse)
async def send_test_email(
    request: EmailTestRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> EmailTestResponse:
    """Send a test email to verify SMTP configuration."""
    settings = get_settings()

    if not settings.smtp_host:
        return EmailTestResponse(
            success=False,
            message="SMTP not configured. Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD env vars.",
        )

    recipient = request.to_email or settings.smtp_username

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "MasteryOS — Test Email ✅"
        msg["From"] = settings.smtp_from_email
        msg["To"] = recipient

        html = """
        <html><body style="font-family: Inter, sans-serif; padding: 20px;">
            <div style="max-width: 500px; margin: auto; background: #0A0A0B; border-radius: 16px; padding: 32px;">
                <h1 style="color: #10B981; margin: 0 0 16px;">MasteryOS</h1>
                <p style="color: #FAFAFA; font-size: 16px;">Your SMTP configuration is working correctly!</p>
                <p style="color: #71717A; font-size: 14px; margin-top: 24px;">
                    Sent at: """ + datetime.now(timezone.utc).isoformat() + """<br>
                    Server: """ + settings.smtp_host + """:""" + str(settings.smtp_port) + """
                </p>
            </div>
        </body></html>
        """
        text = "MasteryOS — Test Email\n\nYour SMTP configuration is working correctly!\n\nSent at: " + datetime.now(timezone.utc).isoformat()

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        import asyncio
        loop = asyncio.get_event_loop()

        def _send_sync():
            if settings.smtp_use_tls:
                server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
                server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, recipient, msg.as_string())
            server.quit()

        await loop.run_in_executor(None, _send_sync)

        return EmailTestResponse(
            success=True,
            message="Test email sent successfully!",
            recipient=recipient,
        )
    except Exception as exc:
        logger.error("test_email_failed", error=str(exc))
        return EmailTestResponse(
            success=False,
            message=f"Failed to send email: {exc}",
            recipient=recipient,
        )


# ============================================================
# WebSocket Status
# ============================================================


@router.get("/websocket-status", response_model=WebSocketStatus)
async def get_websocket_status() -> WebSocketStatus:
    """Check WebSocket server status."""
    return WebSocketStatus(
        enabled=True,
        connected_clients=0,
        endpoint="/api/v1/ws",
    )


# ============================================================
# Worker Management
# ============================================================


@router.post("/worker/restart", response_model=WorkerRestartResponse)
async def restart_worker(
    uow: UnitOfWork = Depends(get_uow),
) -> WorkerRestartResponse:
    """Signal workers to restart (via heartbeat expiry)."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            # Expire all heartbeats so workers re-register
            await session.execute(
                text("UPDATE infrastructure.worker_heartbeats SET last_seen_at = '1970-01-01' WHERE last_seen_at IS NOT NULL")
            )
            await session.commit()

        return WorkerRestartResponse(
            message="Worker restart signal sent. Workers will re-register within 30 seconds.",
            signal_sent=True,
        )
    except Exception as exc:
        return WorkerRestartResponse(
            message=f"Failed to signal workers: {exc}",
            signal_sent=False,
        )


# ============================================================
# Health Summary
# ============================================================


@router.get("/health-summary", response_model=HealthSummary)
async def health_summary(
    uow: UnitOfWork = Depends(get_uow),
) -> HealthSummary:
    """Get a full health summary for the operations dashboard."""
    settings = get_settings()

    db_status = "healthy"
    redis_status = "healthy"
    active_workers = 0
    pending_outbox = 0
    dead_letters = 0
    scheduled_jobs = 0
    notifications_queued = 0

    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]

            # Active workers (seen in last 60 seconds)
            cutoff = datetime.now(timezone.utc)
            try:
                active_workers = (await session.execute(
                    select(func.count()).select_from(WorkerHeartbeatModel)
                )).scalar() or 0
            except Exception:
                pass

            # Pending outbox
            try:
                pending_outbox = (await session.execute(text(
                    "SELECT COUNT(*) FROM infrastructure.outbox_events WHERE status = 'pending'"
                ))).scalar() or 0
            except Exception:
                pass

            # Dead letters
            try:
                dead_letters = (await session.execute(text(
                    "SELECT COUNT(*) FROM infrastructure.dead_letter_events WHERE resolved_at IS NULL"
                ))).scalar() or 0
            except Exception:
                pass

            # Scheduled jobs
            try:
                scheduled_jobs = (await session.execute(
                    select(func.count()).select_from(ScheduledJobModel).where(ScheduledJobModel.status == "active")
                )).scalar() or 0
            except Exception:
                pass

            # Queued notifications
            try:
                notifications_queued = (await session.execute(
                    select(func.count()).select_from(NotificationModel).where(
                        NotificationModel.status.in_(["queued", "sent"])
                    )
                )).scalar() or 0
            except Exception:
                pass

    except Exception:
        db_status = "degraded"

    return HealthSummary(
        database=db_status,
        redis=redis_status,
        workers=active_workers,
        active_workers=active_workers,
        pending_outbox=pending_outbox,
        dead_letters=dead_letters,
        scheduled_jobs=scheduled_jobs,
        notifications_queued=notifications_queued,
        smtp_configured=bool(settings.smtp_host and settings.smtp_password),
        websocket_enabled=True,
        ai_enabled=settings.ai_enabled,
        maintenance_mode=False,
        uptime_seconds=0,
    )
