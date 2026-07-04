"""Admin API endpoints for background processing.

Endpoints:
- GET  /admin/workers — list all workers
- GET  /admin/workers/metrics — background metrics
- GET  /admin/outbox — list outbox events
- GET  /admin/outbox/{id} — get a single outbox event
- POST /admin/outbox/{id}/replay — replay a single event
- GET  /admin/dead-letters — list dead-lettered events
- POST /admin/dead-letters/{id}/retry — retry a dead-lettered event
- GET  /admin/notifications — list all notifications
- GET  /admin/jobs — list scheduled jobs
- POST /admin/jobs/run — manually trigger a scheduled job
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.orm.background import (
    DeadLetterEventModel,
    NotificationModel,
    ScheduledJobModel,
    WorkerHeartbeatModel,
)
from app.infrastructure.database.orm.core import OutboxEventModel
from app.infrastructure.database.repositories.background import (
    DeadLetterEventRepository,
    NotificationRepository,
    ScheduledJobRepository,
    WorkerHeartbeatRepository,
)
from app.presentation.dependencies import (
    get_uow,
    get_session_factory,
    get_current_user_id,
    require_any_role,
)
from app.infrastructure.security.authorization import (
    ROLE_ADMINISTRATOR,
    ROLE_SYSTEM_ADMIN,
)
from app.shared.logging import get_logger
from app.workers.host import HeartbeatService
from app.workers.metrics import MetricsCollector
from app.workers.outbox_dispatcher import OutboxDispatcherProcessor, get_outbox_stats

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin/bg",
    tags=["Admin — Background Processing"],
    dependencies=[
        Depends(get_current_user_id),
        Depends(require_any_role(ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN)),
    ],
)


# ============================================================
# Response Models
# ============================================================


class WorkerDTO(BaseModel):
    worker_id: str
    worker_type: str
    hostname: str | None
    process_id: int | None
    status: str
    last_seen_at: str | None
    started_at: str | None
    jobs_processed: int
    jobs_failed: int
    current_job: str | None
    shutdown_requested: bool
    is_stale: bool


class OutboxEventDTO(BaseModel):
    id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    status: str
    dispatch_attempt_count: int
    last_dispatch_error: str | None
    created_at: str
    dispatched_at: str | None
    leased_by: str | None
    next_retry_at: str | None


class DeadLetterDTO(BaseModel):
    id: str
    original_event_id: str
    event_type: str
    aggregate_id: str
    error_message: str
    error_type: str
    retry_count: int
    severity: str
    resolved_at: str | None
    created_at: str


class NotificationDTO(BaseModel):
    id: str
    user_id: str
    notification_type: str
    channel: str
    priority: str
    status: str
    title: str
    body: str
    created_at: str
    scheduled_at: str
    sent_at: str | None
    delivered_at: str | None


class ScheduledJobDTO(BaseModel):
    id: str
    name: str
    description: str | None
    handler_name: str
    schedule_type: str
    schedule_expr: str
    status: str
    next_run_at: str
    last_run_at: str | None
    last_run_status: str | None
    run_count: int
    failure_count: int
    consecutive_failures: int


class MessageResponse(BaseModel):
    message: str
    code: str = "OK"


# ============================================================
# Helper to get session directly (without UoW)
# ============================================================


async def _get_session():
    """Get a raw session for read queries."""
    from app.presentation.dependencies import get_db_session
    async for session in get_db_session():
        yield session


# ============================================================
# Workers endpoints
# ============================================================


@router.get("/workers", response_model=list[WorkerDTO])
async def list_workers(
    uow = Depends(get_uow),
) -> list[WorkerDTO]:
    """List all workers (active + recently dead)."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        repo = WorkerHeartbeatRepository(session)
        workers = await repo.list_all()

    now = datetime.utcnow()
    result = []
    for w in workers:
        is_stale = (
            (now - w.last_seen_at.replace(tzinfo=None)).total_seconds() > 60
            if w.last_seen_at else True
        )
        result.append(WorkerDTO(
            worker_id=w.worker_id,
            worker_type=w.worker_type,
            hostname=w.hostname,
            process_id=w.process_id,
            status=w.status,
            last_seen_at=w.last_seen_at.isoformat() if w.last_seen_at else None,
            started_at=w.started_at.isoformat() if w.started_at else None,
            jobs_processed=w.jobs_processed,
            jobs_failed=w.jobs_failed,
            current_job=w.current_job,
            shutdown_requested=w.shutdown_requested,
            is_stale=is_stale,
        ))
    return result


@router.get("/workers/metrics")
async def get_worker_metrics(
    uow = Depends(get_uow),
) -> dict[str, Any]:
    """Get background processing metrics."""
    session_factory = await get_session_factory()
    collector = MetricsCollector(session_factory)
    metrics = await collector.collect()
    return metrics.to_dict()


# ============================================================
# Outbox endpoints
# ============================================================


@router.get("/outbox", response_model=list[OutboxEventDTO])
async def list_outbox(
    status_filter: str | None = Query(default=None, alias="status"),
    event_type: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    uow = Depends(get_uow),
) -> list[OutboxEventDTO]:
    """List outbox events."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        stmt = select(OutboxEventModel).order_by(OutboxEventModel.created_at.desc())
        if status_filter:
            stmt = stmt.where(OutboxEventModel.status == status_filter)
        if event_type:
            stmt = stmt.where(OutboxEventModel.event_type == event_type)
        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        events = result.scalars().all()

    return [
        OutboxEventDTO(
            id=str(e.id),
            event_type=e.event_type,
            aggregate_id=str(e.aggregate_id),
            aggregate_type=e.aggregate_type,
            status=e.status,
            dispatch_attempt_count=e.dispatch_attempt_count,
            last_dispatch_error=e.last_dispatch_error,
            created_at=e.created_at.isoformat() if e.created_at else "",
            dispatched_at=e.dispatched_at.isoformat() if e.dispatched_at else None,
            leased_by=e.leased_by,
            next_retry_at=e.next_retry_at.isoformat() if e.next_retry_at else None,
        )
        for e in events
    ]


@router.get("/outbox/stats")
async def get_outbox_metrics(
    uow = Depends(get_uow),
) -> dict[str, Any]:
    """Get outbox statistics."""
    session_factory = await get_session_factory()
    return await get_outbox_stats(session_factory)


@router.get("/outbox/{event_id}", response_model=OutboxEventDTO)
async def get_outbox_event(
    event_id: UUID,
    uow = Depends(get_uow),
) -> OutboxEventDTO:
    """Get a single outbox event by ID."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        event = await session.get(OutboxEventModel, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Outbox event not found")

    return OutboxEventDTO(
        id=str(event.id),
        event_type=event.event_type,
        aggregate_id=str(event.aggregate_id),
        aggregate_type=event.aggregate_type,
        status=event.status,
        dispatch_attempt_count=event.dispatch_attempt_count,
        last_dispatch_error=event.last_dispatch_error,
        created_at=event.created_at.isoformat() if event.created_at else "",
        dispatched_at=event.dispatched_at.isoformat() if event.dispatched_at else None,
        leased_by=event.leased_by,
        next_retry_at=event.next_retry_at.isoformat() if event.next_retry_at else None,
    )


@router.post("/outbox/{event_id}/replay", response_model=MessageResponse)
async def replay_outbox_event(
    event_id: UUID,
    uow = Depends(get_uow),
) -> MessageResponse:
    """Replay a single outbox event (resets status to pending)."""
    session_factory = await get_session_factory()
    # Create a temporary dispatcher just for replay (no subscribers needed)
    dispatcher = OutboxDispatcherProcessor(session_factory)
    success = await dispatcher.replay_event(event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Outbox event not found")
    return MessageResponse(message="Event queued for replay", code="OK")


# ============================================================
# Dead Letter endpoints
# ============================================================


@router.get("/dead-letters", response_model=list[DeadLetterDTO])
async def list_dead_letters(
    resolved: bool = False,
    event_type: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    uow = Depends(get_uow),
) -> list[DeadLetterDTO]:
    """List dead-lettered events."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        repo = DeadLetterEventRepository(session)
        if resolved:
            # List resolved (for audit)
            stmt = (
                select(DeadLetterEventModel)
                .where(DeadLetterEventModel.resolved_at.is_not(None))
                .order_by(DeadLetterEventModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            dead_letters = result.scalars().all()
        else:
            dead_letters = await repo.list_unresolved(limit=limit, offset=offset)

    return [
        DeadLetterDTO(
            id=str(dl.id),
            original_event_id=str(dl.original_event_id),
            event_type=dl.event_type,
            aggregate_id=str(dl.aggregate_id),
            error_message=dl.error_message,
            error_type=dl.error_type,
            retry_count=dl.retry_count,
            severity=dl.severity,
            resolved_at=dl.resolved_at.isoformat() if dl.resolved_at else None,
            created_at=dl.created_at.isoformat() if dl.created_at else "",
        )
        for dl in dead_letters
    ]


@router.post("/dead-letters/{dead_letter_id}/retry", response_model=MessageResponse)
async def retry_dead_letter(
    dead_letter_id: UUID,
    uow = Depends(get_uow),
) -> MessageResponse:
    """Retry a dead-lettered event (creates a new outbox entry)."""
    session_factory = await get_session_factory()
    dispatcher = OutboxDispatcherProcessor(session_factory)
    success = await dispatcher.replay_dead_letter(dead_letter_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dead letter not found")
    return MessageResponse(message="Dead letter queued for retry", code="OK")


@router.post("/dead-letters/{dead_letter_id}/resolve", response_model=MessageResponse)
async def resolve_dead_letter(
    dead_letter_id: UUID,
    notes: str | None = None,
    uow = Depends(get_uow),
) -> MessageResponse:
    """Mark a dead-lettered event as resolved (without retrying)."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        repo = DeadLetterEventRepository(session)
        success = await repo.resolve(dead_letter_id, notes=notes)
        await _uow.commit()

    if not success:
        raise HTTPException(status_code=404, detail="Dead letter not found or already resolved")
    return MessageResponse(message="Dead letter resolved", code="OK")


# ============================================================
# Notifications endpoints
# ============================================================


@router.get("/notifications", response_model=list[NotificationDTO])
async def list_notifications(
    status_filter: str | None = Query(default=None, alias="status"),
    user_id: UUID | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    uow = Depends(get_uow),
) -> list[NotificationDTO]:
    """List notifications (all users, or filter by user)."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        stmt = select(NotificationModel).order_by(NotificationModel.created_at.desc())
        if status_filter:
            stmt = stmt.where(NotificationModel.status == status_filter)
        if user_id:
            stmt = stmt.where(NotificationModel.user_id == user_id)
        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        notifications = result.scalars().all()

    return [
        NotificationDTO(
            id=str(n.id),
            user_id=str(n.user_id),
            notification_type=n.notification_type,
            channel=n.channel,
            priority=n.priority,
            status=n.status,
            title=n.title,
            body=n.body,
            created_at=n.created_at.isoformat() if n.created_at else "",
            scheduled_at=n.scheduled_at.isoformat() if n.scheduled_at else "",
            sent_at=n.sent_at.isoformat() if n.sent_at else None,
            delivered_at=n.delivered_at.isoformat() if n.delivered_at else None,
        )
        for n in notifications
    ]


# ============================================================
# Scheduled Jobs endpoints
# ============================================================


@router.get("/jobs", response_model=list[ScheduledJobDTO])
async def list_jobs(
    uow = Depends(get_uow),
) -> list[ScheduledJobDTO]:
    """List all scheduled jobs."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        repo = ScheduledJobRepository(session)
        jobs = await repo.list_all()

    return [
        ScheduledJobDTO(
            id=str(j.id),
            name=j.name,
            description=j.description,
            handler_name=j.handler_name,
            schedule_type=j.schedule_type,
            schedule_expr=j.schedule_expr,
            status=j.status,
            next_run_at=j.next_run_at.isoformat() if j.next_run_at else "",
            last_run_at=j.last_run_at.isoformat() if j.last_run_at else None,
            last_run_status=j.last_run_status,
            run_count=j.run_count,
            failure_count=j.failure_count,
            consecutive_failures=j.consecutive_failures,
        )
        for j in jobs
    ]


class RunJobRequest(BaseModel):
    job_name: str


@router.post("/jobs/run", response_model=MessageResponse)
async def run_job(
    request: RunJobRequest,
    uow = Depends(get_uow),
) -> MessageResponse:
    """Manually trigger a scheduled job by name."""
    from app.infrastructure.scheduler.processor import DEFAULT_HANDLERS

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        repo = ScheduledJobRepository(session)
        job = await repo.get_by_name(request.job_name)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

        handler = DEFAULT_HANDLERS.get(job.handler_name)
        if handler is None:
            raise HTTPException(
                status_code=500,
                detail=f"No handler registered for: {job.handler_name}",
            )

        # Execute the handler
        session_factory = await get_session_factory()
        context = {
            "job_id": str(job.id),
            "job_name": job.name,
            "schedule_expr": job.schedule_expr,
            "session_factory": session_factory,
        }
        try:
            await handler(context)
            return MessageResponse(message=f"Job '{request.job_name}' executed successfully")
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Job execution failed: {exc}",
            )


@router.post("/jobs/{job_id}/pause", response_model=MessageResponse)
async def pause_job(
    job_id: UUID,
    uow = Depends(get_uow),
) -> MessageResponse:
    """Pause a scheduled job."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        repo = ScheduledJobRepository(session)
        success = await repo.pause(job_id)
        await _uow.commit()
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return MessageResponse(message="Job paused", code="OK")


@router.post("/jobs/{job_id}/resume", response_model=MessageResponse)
async def resume_job(
    job_id: UUID,
    uow = Depends(get_uow),
) -> MessageResponse:
    """Resume a paused scheduled job."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        repo = ScheduledJobRepository(session)
        success = await repo.resume(job_id)
        await _uow.commit()
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return MessageResponse(message="Job resumed", code="OK")


__all__ = ["router"]
