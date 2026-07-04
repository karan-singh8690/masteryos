"""Closed Beta API endpoints — invite management, feedback, analytics, feature flags.

All admin endpoints require administrator role.
Feedback + analytics endpoints require authentication.
Feature flags + beta status are public.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from app.application.beta import BetaInvite, BetaService, get_beta_service
from app.infrastructure.email.service import EmailService
from app.presentation.dependencies import (
    get_current_user_id,
    get_uow,
    get_request_ip,
    get_request_user_agent,
    require_any_role,
)
from app.presentation.dependencies_email import get_email_service
from app.shared.config import get_settings
from app.infrastructure.security.authorization import (
    ROLE_ADMINISTRATOR,
    ROLE_SYSTEM_ADMIN,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Closed Beta"])

# Dependency that requires the user to be an administrator or system admin.
# Used by all /admin/beta/* endpoints + the admin-only /beta/feedback (GET)
# and /beta/analytics (GET) endpoints.
RequireAdmin = Depends(
    require_any_role(ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN)
)


# ============================================================
# Request/Response Models
# ============================================================


class CreateInviteRequest(BaseModel):
    email: EmailStr
    notes: str | None = None


class InviteResponse(BaseModel):
    id: str
    email: str
    invite_token: str
    expires_at: str
    used_at: str | None
    created_by: str
    notes: str | None
    created_at: str
    is_used: bool
    is_expired: bool
    is_valid: bool


class ResendInviteRequest(BaseModel):
    invite_id: UUID


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5, description="Rating from 1-5")
    category: str = Field(description="bug, feature_request, ui_ux, content, performance, other")
    comment: str = Field(min_length=1, max_length=5000)
    screenshot_url: str | None = None
    # Auto-captured context (sent from frontend)
    correlation_id: str | None = None
    browser: str | None = None
    platform: str | None = None
    route: str | None = None


class FeedbackResponse(BaseModel):
    id: str
    user_id: str
    rating: int
    category: str
    comment: str
    screenshot_url: str | None
    status: str
    created_at: str


class TrackEventRequest(BaseModel):
    event_type: str
    event_data: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None


class BetaStatusResponse(BaseModel):
    closed_beta_enabled: bool
    max_beta_users: int
    current_user_count: int | None = None
    feature_flags: dict[str, bool]


class MessageResponse(BaseModel):
    message: str
    code: str = "OK"


# ============================================================
# Helpers
# ============================================================


def _invite_to_response(invite: BetaInvite) -> InviteResponse:
    return InviteResponse(
        id=str(invite.id),
        email=invite.email,
        invite_token=invite.invite_token,
        expires_at=invite.expires_at.isoformat() if invite.expires_at else "",
        used_at=invite.used_at.isoformat() if invite.used_at else None,
        created_by=str(invite.created_by),
        notes=invite.notes,
        created_at=invite.created_at.isoformat() if invite.created_at else "",
        is_used=invite.is_used,
        is_expired=invite.is_expired,
        is_valid=invite.is_valid,
    )


# ============================================================
# Public Endpoints
# ============================================================


@router.get(
    "/beta/status",
    response_model=BetaStatusResponse,
    summary="Get closed beta status",
)
async def get_beta_status(
    beta_service: BetaService = Depends(get_beta_service),
) -> BetaStatusResponse:
    """Get the closed beta status + feature flags (public endpoint)."""
    return BetaStatusResponse(
        closed_beta_enabled=beta_service.is_beta_enabled,
        max_beta_users=beta_service.max_beta_users,
        feature_flags=beta_service.get_feature_flags(),
    )


# ============================================================
# Feedback (Authenticated)
# ============================================================


@router.post(
    "/beta/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit beta feedback",
)
async def submit_feedback(
    request: FeedbackRequest,
    raw_request: Request,
    user_id: UUID = Depends(get_current_user_id),
    uow = Depends(get_uow),
    beta_service: BetaService = Depends(get_beta_service),
) -> FeedbackResponse:
    """Submit beta feedback with auto-captured context."""
    ip = get_request_ip(raw_request)
    user_agent = get_request_user_agent(raw_request)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        feedback = await beta_service.submit_feedback(
            session=session,
            user_id=user_id,
            rating=request.rating,
            category=request.category,
            comment=request.comment,
            screenshot_url=request.screenshot_url,
            correlation_id=request.correlation_id,
            browser=request.browser,
            platform=request.platform,
            route=request.route,
            user_agent=user_agent,
        )
        await _uow.commit()

    return FeedbackResponse(
        id=str(feedback.id),
        user_id=str(feedback.user_id),
        rating=feedback.rating,
        category=feedback.category,
        comment=feedback.comment,
        screenshot_url=feedback.screenshot_url,
        status=feedback.status,
        created_at=feedback.created_at.isoformat() if feedback.created_at else "",
    )


@router.get(
    "/beta/feedback",
    response_model=list[FeedbackResponse],
    summary="List beta feedback (admin)",
)
async def list_feedback(
    status_filter: str | None = None,
    user_id: UUID = Depends(get_current_user_id),
    _admin_check: Any = RequireAdmin,
    uow = Depends(get_uow),
    beta_service: BetaService = Depends(get_beta_service),
) -> list[FeedbackResponse]:
    """List beta feedback (admin only).

    RBAC: requires ROLE_ADMINISTRATOR or ROLE_SYSTEM_ADMIN.
    """
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        feedbacks = await beta_service.list_feedback(
            session=session,
            status=status_filter,
        )
    return [
        FeedbackResponse(
            id=str(f.id),
            user_id=str(f.user_id),
            rating=f.rating,
            category=f.category,
            comment=f.comment,
            screenshot_url=f.screenshot_url,
            status=f.status,
            created_at=f.created_at.isoformat() if f.created_at else "",
        )
        for f in feedbacks
    ]


# ============================================================
# Analytics Tracking (Authenticated)
# ============================================================


@router.post(
    "/beta/track",
    response_model=MessageResponse,
    summary="Track beta analytics event",
)
async def track_event(
    request: TrackEventRequest,
    raw_request: Request,
    user_id: UUID = Depends(get_current_user_id),
    uow = Depends(get_uow),
    beta_service: BetaService = Depends(get_beta_service),
) -> MessageResponse:
    """Track a beta analytics event."""
    ip = get_request_ip(raw_request)
    user_agent = get_request_user_agent(raw_request)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        await beta_service.track_event(
            session=session,
            event_type=request.event_type,
            user_id=user_id,
            event_data=request.event_data,
            session_id=request.session_id,
            ip_address=ip,
            user_agent=user_agent,
        )
        await _uow.commit()

    return MessageResponse(message="Event tracked", code="OK")


@router.get(
    "/beta/analytics",
    summary="Get beta analytics (admin)",
)
async def get_beta_analytics(
    user_id: UUID = Depends(get_current_user_id),
    _admin_check: Any = RequireAdmin,
    uow = Depends(get_uow),
    beta_service: BetaService = Depends(get_beta_service),
) -> dict[str, Any]:
    """Get beta analytics summary (admin only).

    RBAC: requires ROLE_ADMINISTRATOR or ROLE_SYSTEM_ADMIN.
    """
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        return await beta_service.get_beta_analytics(session)


# ============================================================
# Admin Invite Management (Admin only)
# ============================================================


@router.post(
    "/admin/beta/invites",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create beta invite (admin)",
)
async def create_invite(
    request: CreateInviteRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin_check: Any = RequireAdmin,
    uow = Depends(get_uow),
    beta_service: BetaService = Depends(get_beta_service),
    email_service: EmailService = Depends(get_email_service),
) -> InviteResponse:
    """Create a new beta invitation (admin only).

    RBAC: requires ROLE_ADMINISTRATOR or ROLE_SYSTEM_ADMIN.

    Side effect: dispatches a `beta_invitation` email to the invitee via the
    configured SMTP server. Email failures are logged but do NOT fail the
    request — the invite is still created and the admin can resend later.
    """
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        invite = await beta_service.create_invite(
            session=session,
            email=request.email,
            created_by=user_id,
            notes=request.notes,
        )
        await _uow.commit()

    # Dispatch the invitation email (best-effort).
    await _dispatch_invite_email(email_service, invite)

    return _invite_to_response(invite)


@router.get(
    "/admin/beta/invites",
    response_model=list[InviteResponse],
    summary="List beta invites (admin)",
)
async def list_invites(
    include_used: bool = False,
    user_id: UUID = Depends(get_current_user_id),
    _admin_check: Any = RequireAdmin,
    uow = Depends(get_uow),
    beta_service: BetaService = Depends(get_beta_service),
) -> list[InviteResponse]:
    """List all beta invitations (admin only).

    RBAC: requires ROLE_ADMINISTRATOR or ROLE_SYSTEM_ADMIN.
    """
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        invites = await beta_service.list_invites(
            session=session,
            include_used=include_used,
        )
    return [_invite_to_response(i) for i in invites]


@router.delete(
    "/admin/beta/invites/{invite_id}",
    response_model=MessageResponse,
    summary="Delete beta invite (admin)",
)
async def delete_invite(
    invite_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    _admin_check: Any = RequireAdmin,
    uow = Depends(get_uow),
    beta_service: BetaService = Depends(get_beta_service),
) -> MessageResponse:
    """Delete a beta invitation (admin only, unused invites only).

    RBAC: requires ROLE_ADMINISTRATOR or ROLE_SYSTEM_ADMIN.
    """
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        deleted = await beta_service.delete_invite(session, invite_id)
        await _uow.commit()

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Invite not found or already used"},
        )
    return MessageResponse(message="Invite deleted", code="OK")


@router.post(
    "/admin/beta/invites/resend",
    response_model=InviteResponse,
    summary="Resend beta invite (admin)",
)
async def resend_invite(
    request: ResendInviteRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin_check: Any = RequireAdmin,
    uow = Depends(get_uow),
    beta_service: BetaService = Depends(get_beta_service),
    email_service: EmailService = Depends(get_email_service),
) -> InviteResponse:
    """Resend a beta invitation with a new token (admin only).

    RBAC: requires ROLE_ADMINISTRATOR or ROLE_SYSTEM_ADMIN.

    Side effect: dispatches a fresh `beta_invitation` email with the new
    token via the configured SMTP server.
    """
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        invite = await beta_service.resend_invite(session, request.invite_id)
        await _uow.commit()

    if invite is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Invite not found or already used"},
        )

    # Dispatch the fresh invitation email (best-effort).
    await _dispatch_invite_email(email_service, invite)

    return _invite_to_response(invite)


# ============================================================
# Email Dispatch Helper
# ============================================================


async def _dispatch_invite_email(email_service: EmailService, invite: BetaInvite) -> None:
    """Send the beta_invitation email for an invite.

    Best-effort: logs warnings on failure but does NOT raise. The invite
    is already persisted; the admin can resend via the resend endpoint.
    """
    settings = get_settings()
    # Build the registration URL the invitee will click.
    register_url = f"{settings.frontend_base_url.rstrip('/')}/register?invite_token={invite.invite_token}&email={invite.email}"
    expires_at_str = invite.expires_at.isoformat() if invite.expires_at else ""

    try:
        result = await email_service.send_template(
            to=invite.email,
            template_name="beta_invitation",
            context={
                "register_url": register_url,
                "email": invite.email,
                "expires_at": expires_at_str,
            },
        )
        if not result.success:
            logger.warning(
                "beta_invite_email_failed",
                invite_id=str(invite.id),
                email=invite.email,
                error=result.error,
            )
        else:
            logger.info(
                "beta_invite_email_sent",
                invite_id=str(invite.id),
                email=invite.email,
                message_id=result.message_id,
            )
    except Exception as exc:  # noqa: BLE001
        # Never let email failure roll back the invite creation.
        logger.error(
            "beta_invite_email_exception",
            invite_id=str(invite.id),
            email=invite.email,
            error=str(exc),
        )


__all__ = ["router"]
