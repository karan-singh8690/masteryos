"""User profile + security dashboard API routes.

Implements per the OpenAPI contract (Task 006):
- GET /users/me — current user's profile + roles + permissions
- PATCH /users/me — update profile
- GET /users/me/security — security dashboard (sessions, MFA, recent events)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.identity.auth_service import ProductionAuthService
from app.infrastructure.database.orm.identity import UserModel, UserProfileModel
from app.infrastructure.security import (
    AuthContext,
    AuthorizationService,
    ROLE_PERMISSIONS,
)
from app.infrastructure.security.authorization import (
    PERM_USER_READ_SELF,
    PERM_USER_UPDATE_SELF,
)
from app.presentation.dependencies import (
    get_auth_context,
    get_auth_service,
    get_current_user_id,
    get_uow,
)

router = APIRouter(prefix="/users", tags=["Users"])


# ============================================================
# Response Models
# ============================================================


class UserProfileDTO(BaseModel):
    display_name: str
    timezone: str
    locale: str
    avatar_url: str | None
    preferences: dict[str, Any]


class UserDTO(BaseModel):
    id: UUID
    email: str
    status: str
    mfa_enabled: bool
    email_verified_at: str | None
    created_at: str


class CurrentUserResponse(BaseModel):
    user: UserDTO
    profile: UserProfileDTO
    roles: list[str]
    permissions: list[str]


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    timezone: str | None = None
    locale: str | None = None
    avatar_url: str | None = None
    preferences: dict[str, Any] | None = None


class SessionDTO(BaseModel):
    id: UUID
    device_fingerprint: str | None
    last_ip: str | None
    user_agent: str | None
    expires_at: str
    last_seen_at: str
    created_at: str


class SecurityDashboardResponse(BaseModel):
    mfa_enabled: bool
    email_verified: bool
    password_last_changed_at: str | None
    active_sessions: list[SessionDTO]
    recovery_codes_remaining: int
    recent_security_events: list[dict[str, Any]]


# ============================================================
# Helpers
# ============================================================


async def _load_user_with_profile(
    session: AsyncSession, user_id: UUID
) -> tuple[UserModel, UserProfileModel]:
    user_model = await session.get(UserModel, user_id)
    if user_model is None:
        raise HTTPException(status_code=404, detail="User not found")

    profile_stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
    profile_model = (await session.execute(profile_stmt)).scalar_one_or_none()
    if profile_model is None:
        raise HTTPException(status_code=404, detail="User profile not found")

    return user_model, profile_model


def _to_user_dto(user: UserModel) -> UserDTO:
    return UserDTO(
        id=user.id,
        email=user.email,
        status=user.status,
        mfa_enabled=user.mfa_enabled,
        email_verified_at=user.email_verified_at.isoformat() if user.email_verified_at else None,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


def _to_profile_dto(profile: UserProfileModel) -> UserProfileDTO:
    return UserProfileDTO(
        display_name=profile.display_name,
        timezone=profile.timezone,
        locale=profile.locale,
        avatar_url=profile.avatar_url,
        preferences=profile.preferences or {},
    )


# ============================================================
# GET /users/me
# ============================================================


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get current user",
)
async def get_current_user(
    uow = Depends(get_uow),
    user_id: UUID = Depends(get_current_user_id),
    auth_ctx: AuthContext = Depends(get_auth_context),
) -> CurrentUserResponse:
    """Get the current user's profile + roles + permissions."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        user_model, profile_model = await _load_user_with_profile(session, user_id)

    # Compute permissions from roles
    permissions: set[str] = set()
    for role in auth_ctx.roles:
        permissions.update(ROLE_PERMISSIONS.get(role, set()))

    return CurrentUserResponse(
        user=_to_user_dto(user_model),
        profile=_to_profile_dto(profile_model),
        roles=auth_ctx.roles,
        permissions=sorted(permissions),
    )


# ============================================================
# PATCH /users/me
# ============================================================


@router.patch(
    "/me",
    response_model=CurrentUserResponse,
    summary="Update current user's profile",
)
async def update_profile(
    request: UpdateProfileRequest,
    uow = Depends(get_uow),
    user_id: UUID = Depends(get_current_user_id),
    auth_ctx: AuthContext = Depends(get_auth_context),
) -> CurrentUserResponse:
    """Update the current user's profile.

    Only fields explicitly provided (non-None) are updated.
    """
    # Authorization check
    auth_service = AuthorizationService(auth_ctx)
    auth_service.require_permission(PERM_USER_UPDATE_SELF)

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        user_model, profile_model = await _load_user_with_profile(session, user_id)

        # Apply updates
        update_values: dict[str, Any] = {}
        if request.display_name is not None:
            update_values["display_name"] = request.display_name
        if request.timezone is not None:
            update_values["timezone"] = request.timezone
        if request.locale is not None:
            update_values["locale"] = request.locale
        if request.avatar_url is not None:
            update_values["avatar_url"] = request.avatar_url if request.avatar_url else None
        if request.preferences is not None:
            update_values["preferences"] = request.preferences

        if update_values:
            await session.execute(
                update(UserProfileModel)
                .where(UserProfileModel.user_id == user_id)
                .values(**update_values)
            )
            # Refresh the profile model
            await session.refresh(profile_model)

        # Audit log
        from app.infrastructure.database.repositories.auth import AuthAuditLogRepository
        await AuthAuditLogRepository(session).record(
            action="PROFILE_UPDATED",
            user_id=user_id,
            details={"updated_fields": list(update_values.keys())},
        )

        await _uow.commit()

    # Recompute permissions
    permissions: set[str] = set()
    for role in auth_ctx.roles:
        permissions.update(ROLE_PERMISSIONS.get(role, set()))

    return CurrentUserResponse(
        user=_to_user_dto(user_model),
        profile=_to_profile_dto(profile_model),
        roles=auth_ctx.roles,
        permissions=sorted(permissions),
    )


# ============================================================
# GET /users/me/security
# ============================================================


@router.get(
    "/me/security",
    response_model=SecurityDashboardResponse,
    summary="Get security dashboard",
)
async def get_security_dashboard(
    uow = Depends(get_uow),
    auth_service: ProductionAuthService = Depends(get_auth_service),
    user_id: UUID = Depends(get_current_user_id),
) -> SecurityDashboardResponse:
    """Get the current user's security dashboard.

    Includes:
    - MFA enabled status
    - Email verified status
    - Password last changed at
    - Active sessions (all devices)
    - Recovery codes remaining (if MFA enabled)
    - Recent security events (audit log)
    """
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        dashboard = await auth_service.get_security_dashboard(session, user_id)
        await _uow.commit()

    return SecurityDashboardResponse(
        mfa_enabled=dashboard["mfa_enabled"],
        email_verified=dashboard["email_verified"],
        password_last_changed_at=dashboard.get("password_last_changed_at"),
        active_sessions=[
            SessionDTO(
                id=s["id"],
                device_fingerprint=s.get("device_fingerprint"),
                last_ip=s.get("last_ip"),
                user_agent=s.get("user_agent"),
                expires_at=s.get("expires_at", ""),
                last_seen_at=s.get("last_seen_at", ""),
                created_at=s.get("created_at", ""),
            )
            for s in dashboard["active_sessions"]
        ],
        recovery_codes_remaining=dashboard["recovery_codes_remaining"],
        recent_security_events=dashboard["recent_security_events"],
    )


__all__ = ["router"]
