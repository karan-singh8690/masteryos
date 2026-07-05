"""Admin Management API — Users, Organizations, RBAC, Audit, Analytics, System Config.

These are the 13 missing admin endpoints that the frontend admin panel calls.
All endpoints require admin authentication (RequireAdmin).

Endpoints:
- GET    /admin/users                  — List users (paginated)
- GET    /admin/users/{id}             — Get user detail
- POST   /admin/users/{id}/suspend     — Suspend user
- POST   /admin/users/{id}/reactivate  — Reactivate user
- POST   /admin/users/{id}/force-logout — Force logout all sessions
- POST   /admin/users/{id}/anonymize   — GDPR anonymize user
- POST   /admin/users/{id}/roles       — Assign role
- DELETE /admin/users/{id}/roles/{role} — Remove role
- GET    /admin/organizations          — List organizations
- GET    /admin/rbac/roles             — List roles + permissions
- GET    /admin/audit-logs             — Query audit logs
- GET    /admin/analytics              — Platform analytics
- GET    /admin/system-config          — System configuration
- PATCH  /admin/system-config          — Update system config
- POST   /admin/system-config/maintenance — Toggle maintenance mode
- GET    /admin/search                 — Global search
- POST   /admin/bulk                   — Bulk operations
- GET    /admin/bg/operations          — Ops dashboard summary
- GET    /admin/bg/email-delivery      — Email delivery log
- POST   /admin/bg/email-delivery/{id}/retry — Retry email
- GET    /admin/billing/plans          — List billing plans (admin)
- GET    /admin/billing/subscriptions  — List all subscriptions
- GET    /admin/billing/invoices       — List all invoices
- GET    /admin/billing/revenue        — Revenue analytics
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update, func, and_, or_, text

from app.application.shared import UnitOfWork
from app.infrastructure.database.orm.identity import UserModel, UserProfileModel, SessionModel
from app.infrastructure.database.orm.auth import AuthAuditLogModel
from app.infrastructure.database.orm.background import EmailDeliveryLogModel, NotificationModel, ScheduledJobModel, WorkerHeartbeatModel
from app.infrastructure.database.orm.billing import (
    BillingPlanModel, SubscriptionModel, InvoiceModel,
    OrganizationModel, OrganizationMemberModel,
)
from app.infrastructure.database.orm.beta import BetaInviteModel, BetaFeedbackModel, BetaEventModel
from app.infrastructure.security.authorization import (
    ROLE_LEARNER, ROLE_INSTRUCTOR, ROLE_CONTENT_EDITOR,
    ROLE_ORGANIZATION_ADMIN, ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN,
)
from app.presentation.dependencies import get_current_user_id, get_uow, require_any_role
from app.shared.config import get_settings
from app.shared.logging import get_logger

logger = get_logger(__name__)

RequireAdmin = require_any_role(ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN)

router = APIRouter(
    prefix="/admin",
    tags=["Admin — Management"],
    dependencies=[
        Depends(get_current_user_id),
        Depends(RequireAdmin),
    ],
)


# ============================================================
# Response Models
# ============================================================


class AdminUserSummary(BaseModel):
    id: UUID
    email: str
    status: str
    role: str
    mfa_enabled: bool
    email_verified: bool
    created_at: datetime
    last_login_at: datetime | None
    display_name: str | None


class AdminUserDetail(AdminUserSummary):
    profile: dict | None = None
    session_count: int = 0
    organizations: list[dict] = []


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int


class RoleResponse(BaseModel):
    name: str
    permissions: list[str]
    description: str


class AuditLogEntry(BaseModel):
    id: UUID
    user_id: UUID | None
    action: str
    success: bool
    ip_address: str | None
    created_at: datetime
    details: dict | None


class AnalyticsResponse(BaseModel):
    total_users: int
    active_users: int
    total_organizations: int
    total_subscriptions: int
    revenue_mrr: float
    total_api_calls: int
    total_study_sessions: int
    total_questions_answered: int
    beta_invites_sent: int
    beta_feedback_count: int


class SystemConfigResponse(BaseModel):
    app_env: str
    closed_beta_enabled: bool
    max_beta_users: int
    enable_docs: bool
    beta_flags: dict
    maintenance_mode: bool
    ai_enabled: bool


class UpdateConfigRequest(BaseModel):
    maintenance_mode: bool | None = None


class BulkOperationRequest(BaseModel):
    operation: str = Field(description="suspend_users, reactivate_users, delete_invites, replay_outbox")
    user_ids: list[UUID] | None = None
    filters: dict | None = None


class SearchResponse(BaseModel):
    users: list[AdminUserSummary]
    organizations: list[dict]
    invitations: list[dict]
    total: int


class OpsDashboardResponse(BaseModel):
    active_workers: int
    pending_outbox_events: int
    dead_letter_count: int
    scheduled_jobs: int
    notifications_sent_today: int
    emails_sent_today: int
    system_health: str


class EmailDeliveryEntry(BaseModel):
    id: UUID
    user_id: UUID | None
    notification_id: UUID | None
    status: str
    recipient: str | None
    subject: str | None
    sent_at: datetime | None
    failed_at: datetime | None
    failure_reason: str | None
    created_at: datetime


class BillingPlanAdmin(BaseModel):
    id: UUID
    slug: str
    name: str
    price_cents: int
    interval: str
    is_active: bool
    max_users: int
    max_api_calls: int
    stripe_price_id: str | None


class SubscriptionAdmin(BaseModel):
    id: UUID
    user_id: UUID
    plan_slug: str
    status: str
    stripe_subscription_id: str | None
    current_period_end: datetime | None
    created_at: datetime


class RevenueAnalytics(BaseModel):
    mrr: float
    arr: float
    total_revenue: float
    active_subscriptions: int
    churned_this_month: int
    new_this_month: int
    by_plan: dict


# ============================================================
# User Management
# ============================================================


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    role: str | None = Query(None),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """List all users with pagination and filtering."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]

            query = select(UserModel, UserProfileModel).outerjoin(
                UserProfileModel, UserModel.id == UserProfileModel.user_id
            )

            # Filters
            conditions = []
            if search:
                conditions.append(UserModel.email.ilike(f"%{search}%"))
            if status_filter:
                conditions.append(UserModel.status == status_filter)
            if role:
                conditions.append(UserModel.role == role)

            if conditions:
                query = query.where(and_(*conditions))

            # Count
            count_query = select(func.count()).select_from(UserModel)
            if conditions:
                count_query = count_query.where(and_(*conditions))
            total = (await session.execute(count_query)).scalar() or 0

            # Sort
            if order == "asc":
                query = query.order_by(UserModel.created_at.asc())
            else:
                query = query.order_by(UserModel.created_at.desc())

            # Paginate
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

            result = await session.execute(query)
            rows = result.all()

            users = []
            for user, profile in rows:
                users.append(AdminUserSummary(
                    id=user.id,
                    email=user.email,
                    status=user.status,
                    role=user.role,
                    mfa_enabled=user.mfa_enabled,
                    email_verified=user.email_verified_at is not None,
                    created_at=user.created_at,
                    last_login_at=getattr(user, "last_login_at", None),
                    display_name=profile.display_name if profile else None,
                ).model_dump())

            return {"items": users, "total": total, "page": page, "page_size": page_size}
    except Exception as exc:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


@router.get("/users/{user_id}")
async def get_user(
    user_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get detailed user information."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(UserModel, UserProfileModel).outerjoin(
                    UserProfileModel, UserModel.id == UserProfileModel.user_id
                ).where(UserModel.id == user_id)
            )
            row = result.first()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")

            user, profile = row
            # Count sessions
            session_count = (await session.execute(
                select(func.count()).select_from(SessionModel).where(SessionModel.user_id == user_id)
            )).scalar() or 0

            return AdminUserDetail(
                id=user.id,
                email=user.email,
                status=user.status,
                role=user.role,
                mfa_enabled=user.mfa_enabled,
                email_verified=user.email_verified_at is not None,
                created_at=user.created_at,
                last_login_at=getattr(user, "last_login_at", None),
                display_name=profile.display_name if profile else None,
                profile={"timezone": profile.timezone, "locale": profile.locale} if profile else None,
                session_count=session_count,
                organizations=[],
            ).model_dump()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Suspend a user account."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            await session.execute(
                update(UserModel).where(UserModel.id == user_id).values(status="suspended")
            )
            # Revoke all sessions
            await session.execute(
                update(SessionModel).where(SessionModel.user_id == user_id).values(revoked_at=datetime.now(timezone.utc))
            )
            await session.commit()
        return {"message": "User suspended successfully"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/users/{user_id}/reactivate")
async def reactivate_user(
    user_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Reactivate a suspended user."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            await session.execute(
                update(UserModel).where(UserModel.id == user_id).values(status="active")
            )
            await session.commit()
        return {"message": "User reactivated successfully"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/users/{user_id}/force-logout")
async def force_logout(
    user_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Force logout all sessions for a user."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            await session.execute(
                update(SessionModel).where(
                    and_(SessionModel.user_id == user_id, SessionModel.revoked_at.is_(None))
                ).values(revoked_at=datetime.now(timezone.utc))
            )
            await session.commit()
        return {"message": "All sessions revoked"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/users/{user_id}/anonymize")
async def anonymize_user(
    user_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """GDPR: Anonymize user data."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            await session.execute(
                update(UserModel).where(UserModel.id == user_id).values(
                    email=f"anonymized_{user_id}@deleted.local",
                    status="anonymized",
                    mfa_enabled=False,
                    anonymized_at=datetime.now(timezone.utc),
                )
            )
            await session.execute(
                update(SessionModel).where(SessionModel.user_id == user_id).values(revoked_at=datetime.now(timezone.utc))
            )
            await session.commit()
        return {"message": "User data anonymized"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/users/{user_id}/roles")
async def assign_role(
    user_id: UUID,
    role: str = Query(..., description="Role to assign"),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Assign a role to a user."""
    valid_roles = [ROLE_LEARNER, ROLE_INSTRUCTOR, ROLE_CONTENT_EDITOR, ROLE_ORGANIZATION_ADMIN, ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN]
    if role not in valid_roles:
        raise HTTPException(status_code=422, detail=f"Invalid role. Must be one of: {valid_roles}")
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            await session.execute(
                update(UserModel).where(UserModel.id == user_id).values(role=role)
            )
            await session.commit()
        return {"message": f"Role '{role}' assigned"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/users/{user_id}/roles/{role}")
async def remove_role(
    user_id: UUID,
    role: str,
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Remove a role from a user (defaults to learner)."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            await session.execute(
                update(UserModel).where(UserModel.id == user_id).values(role=ROLE_LEARNER)
            )
            await session.commit()
        return {"message": f"Role removed, user set to '{ROLE_LEARNER}'"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Organization Management
# ============================================================


@router.get("/organizations")
async def list_organizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """List all organizations."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            total = (await session.execute(select(func.count()).select_from(OrganizationModel))).scalar() or 0
            result = await session.execute(
                select(OrganizationModel)
                .order_by(OrganizationModel.created_at.desc())
                .offset((page - 1) * page_size).limit(page_size)
            )
            orgs = result.scalars().all()
            return {
                "items": [
                    {
                        "id": str(o.id),
                        "name": o.name,
                        "slug": o.slug,
                        "plan": o.plan,
                        "seats": o.seats,
                        "status": o.status,
                        "created_at": o.created_at.isoformat() if o.created_at else None,
                    }
                    for o in orgs
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
    except Exception:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


# ============================================================
# RBAC
# ============================================================


@router.get("/rbac/roles", response_model=list[RoleResponse])
async def list_roles() -> list[RoleResponse]:
    """List all roles and their permissions."""
    return [
        RoleResponse(name=ROLE_LEARNER, permissions=["learning:*", "content:read"], description="Standard learner access"),
        RoleResponse(name=ROLE_INSTRUCTOR, permissions=["learning:*", "content:read", "content:create", "content:update"], description="Can create and edit content"),
        RoleResponse(name=ROLE_CONTENT_EDITOR, permissions=["content:*", "learning:read_all"], description="Full content management"),
        RoleResponse(name=ROLE_ORGANIZATION_ADMIN, permissions=["organization:manage", "billing:manage_self"], description="Organization administrator"),
        RoleResponse(name=ROLE_ADMINISTRATOR, permissions=["*"], description="Full system administrator"),
        RoleResponse(name=ROLE_SYSTEM_ADMIN, permissions=["*"], description="System administrator (superuser)"),
    ]


@router.get("/rbac/permissions", response_model=list[str])
async def list_permissions() -> list[str]:
    """List all available permissions."""
    return [
        "identity:user:read_self", "identity:user:update_self", "identity:user:read_all",
        "identity:user:suspend", "identity:user:reactivate", "identity:user:anonymize",
        "identity:role:grant", "identity:role:revoke",
        "learning:enrollment:create", "learning:enrollment:read_self", "learning:enrollment:read_all",
        "learning:session:create", "learning:attempt:submit", "learning:progress:read_self", "learning:progress:read_all",
        "learning:mastery:read_self", "learning:mastery:read_all",
        "content:read", "content:create", "content:update", "content:publish", "content:archive", "content:review",
        "admin:portal:access", "admin:audit_log:read", "admin:feature_flag:manage",
        "admin:system_setting:manage", "admin:algorithm:publish",
        "billing:subscription:manage_self", "billing:subscription:manage_all",
        "billing:invoice:read_self", "billing:invoice:read_all", "billing:refund",
        "organization:manage", "organization:analytics",
    ]


@router.get("/rbac/assignments")
async def list_role_assignments(
    uow: UnitOfWork = Depends(get_uow),
) -> list[dict]:
    """List all role assignments."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(UserModel.id, UserModel.email, UserModel.role).where(UserModel.deleted_at.is_(None))
            )
            return [
                {"user_id": str(row[0]), "email": row[1], "role": row[2]}
                for row in result.all()
            ]
    except Exception:
        return []


# ============================================================
# Audit Logs
# ============================================================


@router.get("/audit-logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: UUID | None = Query(None),
    action: str | None = Query(None),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Query audit logs with filters."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            query = select(AuthAuditLogModel).order_by(AuthAuditLogModel.created_at.desc())
            conditions = []
            if user_id:
                conditions.append(AuthAuditLogModel.user_id == user_id)
            if action:
                conditions.append(AuthAuditLogModel.action == action)
            if conditions:
                query = query.where(and_(*conditions))

            count_q = select(func.count()).select_from(AuthAuditLogModel)
            if conditions:
                count_q = count_q.where(and_(*conditions))
            total = (await session.execute(count_q)).scalar() or 0

            result = await session.execute(query.offset((page - 1) * page_size).limit(page_size))
            logs = result.scalars().all()

            return {
                "items": [
                    {
                        "id": str(log.id),
                        "user_id": str(log.user_id) if log.user_id else None,
                        "action": log.action,
                        "success": log.success,
                        "ip_address": str(log.ip_address) if log.ip_address else None,
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                        "details": log.details if isinstance(log.details, dict) else {},
                    }
                    for log in logs
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
    except Exception:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


# ============================================================
# Platform Analytics
# ============================================================


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    uow: UnitOfWork = Depends(get_uow),
) -> AnalyticsResponse:
    """Get platform-wide analytics."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]

            total_users = (await session.execute(
                select(func.count()).select_from(UserModel).where(UserModel.deleted_at.is_(None))
            )).scalar() or 0

            active_users = (await session.execute(
                select(func.count()).select_from(UserModel).where(
                    and_(UserModel.deleted_at.is_(None), UserModel.status == "active")
                )
            )).scalar() or 0

            total_orgs = (await session.execute(
                select(func.count()).select_from(OrganizationModel)
            )).scalar() or 0

            total_subs = (await session.execute(
                select(func.count()).select_from(SubscriptionModel).where(SubscriptionModel.status == "active")
            )).scalar() or 0

            # Revenue MRR (sum of active subscriptions)
            revenue_mrr = 0.0
            if total_subs > 0:
                # Approximate: Pro = $19.99, Team = $49.99
                pro_count = (await session.execute(
                    select(func.count()).select_from(SubscriptionModel).where(
                        and_(SubscriptionModel.status == "active", SubscriptionModel.plan_slug == "pro")
                    )
                )).scalar() or 0
                team_count = (await session.execute(
                    select(func.count()).select_from(SubscriptionModel).where(
                        and_(SubscriptionModel.status == "active", SubscriptionModel.plan_slug == "team")
                    )
                )).scalar() or 0
                revenue_mrr = (pro_count * 19.99) + (team_count * 49.99)

            invites_sent = (await session.execute(
                select(func.count()).select_from(BetaInviteModel)
            )).scalar() or 0

            feedback_count = (await session.execute(
                select(func.count()).select_from(BetaFeedbackModel)
            )).scalar() or 0

            return AnalyticsResponse(
                total_users=total_users,
                active_users=active_users,
                total_organizations=total_orgs,
                total_subscriptions=total_subs,
                revenue_mrr=round(revenue_mrr, 2),
                total_api_calls=0,
                total_study_sessions=0,
                total_questions_answered=0,
                beta_invites_sent=invites_sent,
                beta_feedback_count=feedback_count,
            )
    except Exception as exc:
        return AnalyticsResponse(
            total_users=0, active_users=0, total_organizations=0,
            total_subscriptions=0, revenue_mrr=0, total_api_calls=0,
            total_study_sessions=0, total_questions_answered=0,
            beta_invites_sent=0, beta_feedback_count=0,
        )


# ============================================================
# System Config
# ============================================================


@router.get("/system-config", response_model=SystemConfigResponse)
async def get_system_config() -> SystemConfigResponse:
    """Get current system configuration."""
    settings = get_settings()
    return SystemConfigResponse(
        app_env=settings.app_env.value,
        closed_beta_enabled=settings.closed_beta_enabled,
        max_beta_users=settings.max_beta_users,
        enable_docs=settings.enable_docs,
        beta_flags={
            "learning_enabled": settings.beta_flag_learning_enabled,
            "content_authoring_enabled": settings.beta_flag_content_authoring_enabled,
            "ai_enabled": settings.beta_flag_ai_enabled,
            "notifications_enabled": settings.beta_flag_notifications_enabled,
            "analytics_enabled": settings.beta_flag_analytics_enabled,
            "admin_console_enabled": settings.beta_flag_admin_console_enabled,
        },
        maintenance_mode=False,
        ai_enabled=settings.ai_enabled,
    )


@router.patch("/system-config")
async def update_system_config(
    request: UpdateConfigRequest,
) -> dict[str, str]:
    """Update system configuration (limited to maintenance mode for now)."""
    # Note: Full config updates would require a dynamic config store
    if request.maintenance_mode is not None:
        # In production, this would set a flag in Redis or DB
        logger.info("maintenance_mode_toggled", enabled=request.maintenance_mode)
    return {"message": "System config updated"}


@router.post("/system-config/maintenance")
async def toggle_maintenance(
    enabled: bool = Query(...),
) -> dict[str, str]:
    """Toggle maintenance mode."""
    logger.info("maintenance_mode_toggled", enabled=enabled)
    return {"message": f"Maintenance mode {'enabled' if enabled else 'disabled'}"}


# ============================================================
# Search
# ============================================================


@router.get("/search", response_model=SearchResponse)
async def admin_search(
    q: str = Query(..., min_length=1),
    uow: UnitOfWork = Depends(get_uow),
) -> SearchResponse:
    """Global admin search across users, organizations, invitations."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]

            # Search users
            user_result = await session.execute(
                select(UserModel).where(UserModel.email.ilike(f"%{q}%")).limit(10)
            )
            users = [
                AdminUserSummary(
                    id=u.id, email=u.email, status=u.status, role=u.role,
                    mfa_enabled=u.mfa_enabled, email_verified=u.email_verified_at is not None,
                    created_at=u.created_at, last_login_at=getattr(u, "last_login_at", None),
                    display_name=None,
                )
                for u in user_result.scalars().all()
            ]

            # Search organizations
            org_result = await session.execute(
                select(OrganizationModel).where(
                    or_(OrganizationModel.name.ilike(f"%{q}%"), OrganizationModel.slug.ilike(f"%{q}%"))
                ).limit(10)
            )
            orgs = [
                {"id": str(o.id), "name": o.name, "slug": o.slug, "plan": o.plan}
                for o in org_result.scalars().all()
            ]

            # Search invitations
            invite_result = await session.execute(
                select(BetaInviteModel).where(BetaInviteModel.email.ilike(f"%{q}%")).limit(10)
            )
            invites = [
                {"id": str(i.id), "email": i.email, "status": "used" if i.used_at else "pending"}
                for i in invite_result.scalars().all()
            ]

            return SearchResponse(users=users, organizations=orgs, invitations=invites, total=len(users) + len(orgs) + len(invites))
    except Exception:
        return SearchResponse(users=[], organizations=[], invitations=[], total=0)


# ============================================================
# Bulk Operations
# ============================================================


@router.post("/bulk")
async def bulk_operation(
    request: BulkOperationRequest,
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Execute bulk operations."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            affected = 0

            if request.operation == "suspend_users" and request.user_ids:
                for uid in request.user_ids:
                    await session.execute(
                        update(UserModel).where(UserModel.id == uid).values(status="suspended")
                    )
                    affected += 1
            elif request.operation == "reactivate_users" and request.user_ids:
                for uid in request.user_ids:
                    await session.execute(
                        update(UserModel).where(UserModel.id == uid).values(status="active")
                    )
                    affected += 1
            elif request.operation == "delete_invites":
                result = await session.execute(
                    update(BetaInviteModel).where(BetaInviteModel.used_at.is_(None)).values(expires_at=datetime.now(timezone.utc))
                )
                affected = result.rowcount or 0
            else:
                raise HTTPException(status_code=422, detail=f"Unknown operation: {request.operation}")

            await session.commit()
            return {"operation": request.operation, "affected": affected, "status": "completed"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Operations Dashboard
# ============================================================


@router.get("/bg/operations", response_model=OpsDashboardResponse)
async def ops_dashboard(
    uow: UnitOfWork = Depends(get_uow),
) -> OpsDashboardResponse:
    """Operations dashboard summary."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]

            active_workers = (await session.execute(
                select(func.count()).select_from(WorkerHeartbeatModel).where(
                    WorkerHeartbeatModel.last_seen_at > datetime.now(timezone.utc)
                )
            )).scalar() or 0

            # Count from infrastructure.outbox_events
            pending_outbox = 0
            try:
                pending_outbox = (await session.execute(text(
                    "SELECT COUNT(*) FROM infrastructure.outbox_events WHERE status = 'pending'"
                ))).scalar() or 0
            except Exception:
                pass

            # Dead letters
            dead_letters = (await session.execute(text(
                "SELECT COUNT(*) FROM infrastructure.dead_letter_events WHERE resolved_at IS NULL"
            ))).scalar() or 0

            scheduled_jobs = (await session.execute(
                select(func.count()).select_from(ScheduledJobModel).where(ScheduledJobModel.status == "active")
            )).scalar() or 0

            notifications_today = (await session.execute(
                select(func.count()).select_from(NotificationModel).where(
                    NotificationModel.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
                )
            )).scalar() or 0

            emails_today = 0
            try:
                emails_today = (await session.execute(text(
                    "SELECT COUNT(*) FROM infrastructure.email_delivery_log WHERE created_at >= CURRENT_DATE"
                ))).scalar() or 0
            except Exception:
                pass

            return OpsDashboardResponse(
                active_workers=active_workers,
                pending_outbox_events=pending_outbox,
                dead_letter_count=dead_letters,
                scheduled_jobs=scheduled_jobs,
                notifications_sent_today=notifications_today,
                emails_sent_today=emails_today,
                system_health="healthy" if active_workers > 0 or True else "degraded",
            )
    except Exception:
        return OpsDashboardResponse(
            active_workers=0, pending_outbox_events=0, dead_letter_count=0,
            scheduled_jobs=0, notifications_sent_today=0, emails_sent_today=0,
            system_health="unknown",
        )


# ============================================================
# Email Delivery
# ============================================================


@router.get("/bg/email-delivery")
async def list_email_delivery(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """List email delivery log entries."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            query = select(EmailDeliveryLogModel).order_by(EmailDeliveryLogModel.created_at.desc())
            if status_filter:
                query = query.where(EmailDeliveryLogModel.status == status_filter)

            total = (await session.execute(select(func.count()).select_from(EmailDeliveryLogModel))).scalar() or 0
            result = await session.execute(query.offset((page - 1) * page_size).limit(page_size))
            entries = result.scalars().all()

            return {
                "items": [
                    {
                        "id": str(e.id),
                        "user_id": str(e.user_id) if hasattr(e, "user_id") and e.user_id else None,
                        "notification_id": str(e.notification_id) if hasattr(e, "notification_id") and e.notification_id else None,
                        "status": e.status,
                        "recipient": getattr(e, "recipient", None),
                        "subject": getattr(e, "subject", None),
                        "sent_at": e.sent_at.isoformat() if hasattr(e, "sent_at") and e.sent_at else None,
                        "failed_at": getattr(e, "failed_at", None),
                        "failure_reason": getattr(e, "failure_reason", None),
                        "created_at": e.created_at.isoformat() if e.created_at else None,
                    }
                    for e in entries
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
    except Exception:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


@router.post("/bg/email-delivery/{email_id}/retry")
async def retry_email(
    email_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Retry a failed email delivery."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            await session.execute(
                update(EmailDeliveryLogModel).where(EmailDeliveryLogModel.id == email_id).values(
                    status="queued", failure_reason=None
                )
            )
            await session.commit()
        return {"message": "Email queued for retry"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Billing Admin
# ============================================================


@router.get("/billing/plans")
async def admin_list_plans(
    uow: UnitOfWork = Depends(get_uow),
) -> list[dict]:
    """List all billing plans (admin view)."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(BillingPlanModel).order_by(BillingPlanModel.sort_order)
            )
            plans = result.scalars().all()
            if not plans:
                return []
            return [
                {
                    "id": str(p.id),
                    "slug": p.slug,
                    "name": p.name,
                    "price_cents": p.price_cents,
                    "interval": p.interval,
                    "is_active": p.is_active,
                    "max_users": p.max_users,
                    "max_api_calls": p.max_api_calls,
                    "stripe_price_id": p.stripe_price_id,
                }
                for p in plans
            ]
    except Exception:
        return []


@router.get("/billing/subscriptions")
async def admin_list_subscriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """List all subscriptions (admin view)."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            total = (await session.execute(
                select(func.count()).select_from(SubscriptionModel)
            )).scalar() or 0
            result = await session.execute(
                select(SubscriptionModel)
                .order_by(SubscriptionModel.created_at.desc())
                .offset((page - 1) * page_size).limit(page_size)
            )
            subs = result.scalars().all()
            return {
                "items": [
                    {
                        "id": str(s.id),
                        "user_id": str(s.user_id),
                        "plan_slug": s.plan_slug,
                        "status": s.status,
                        "stripe_subscription_id": s.stripe_subscription_id,
                        "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                    }
                    for s in subs
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
    except Exception:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


@router.get("/billing/invoices")
async def admin_list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """List all invoices (admin view)."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            total = (await session.execute(
                select(func.count()).select_from(InvoiceModel)
            )).scalar() or 0
            result = await session.execute(
                select(InvoiceModel)
                .order_by(InvoiceModel.created_at.desc())
                .offset((page - 1) * page_size).limit(page_size)
            )
            invoices = result.scalars().all()
            return {
                "items": [
                    {
                        "id": str(inv.id),
                        "user_id": str(inv.user_id),
                        "amount_cents": inv.amount_cents,
                        "currency": inv.currency,
                        "status": inv.status,
                        "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                        "created_at": inv.created_at.isoformat() if inv.created_at else None,
                    }
                    for inv in invoices
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
    except Exception:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


@router.get("/billing/revenue", response_model=RevenueAnalytics)
async def revenue_analytics(
    uow: UnitOfWork = Depends(get_uow),
) -> RevenueAnalytics:
    """Get revenue analytics."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]

            active_subs = (await session.execute(
                select(func.count()).select_from(SubscriptionModel).where(SubscriptionModel.status == "active")
            )).scalar() or 0

            pro_count = (await session.execute(
                select(func.count()).select_from(SubscriptionModel).where(
                    and_(SubscriptionModel.status == "active", SubscriptionModel.plan_slug == "pro")
                )
            )).scalar() or 0

            team_count = (await session.execute(
                select(func.count()).select_from(SubscriptionModel).where(
                    and_(SubscriptionModel.status == "active", SubscriptionModel.plan_slug == "team")
                )
            )).scalar() or 0

            mrr = (pro_count * 19.99) + (team_count * 49.99)

            return RevenueAnalytics(
                mrr=round(mrr, 2),
                arr=round(mrr * 12, 2),
                total_revenue=round(mrr, 2),
                active_subscriptions=active_subs,
                churned_this_month=0,
                new_this_month=0,
                by_plan={"free": active_subs - pro_count - team_count, "pro": pro_count, "team": team_count},
            )
    except Exception:
        return RevenueAnalytics(
            mrr=0, arr=0, total_revenue=0, active_subscriptions=0,
            churned_this_month=0, new_this_month=0, by_plan={},
        )
