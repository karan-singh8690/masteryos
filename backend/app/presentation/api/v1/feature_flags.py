"""Feature Flags API — returns beta feature flags from configuration.

Endpoints:
- GET /api/v1/admin/feature-flags — list all feature flags (admin only)
- GET /api/v1/feature-flags — list public feature flags (authenticated)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.presentation.dependencies import get_current_user_id, require_any_role
from app.infrastructure.security.authorization import (
    ROLE_ADMINISTRATOR,
    ROLE_SYSTEM_ADMIN,
)
from app.shared.config import get_settings
from uuid import UUID

router = APIRouter(tags=["Feature Flags"])


class FeatureFlag(BaseModel):
    key: str
    name: str
    enabled: bool
    description: str


class FeatureFlagsResponse(BaseModel):
    flags: list[FeatureFlag]


@router.get(
    "/admin/feature-flags",
    response_model=FeatureFlagsResponse,
    summary="List all feature flags (admin only)",
)
async def list_feature_flags_admin(
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = Depends(require_any_role(ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN)),
) -> FeatureFlagsResponse:
    """List all feature flags — admin only."""
    settings = get_settings()
    return FeatureFlagsResponse(
        flags=[
            FeatureFlag(
                key="learning_enabled",
                name="Learning Module",
                enabled=settings.beta_flag_learning_enabled,
                description="Enable the learning module (dashboard, study sessions, mastery).",
            ),
            FeatureFlag(
                key="content_authoring_enabled",
                name="Content Authoring",
                enabled=settings.beta_flag_content_authoring_enabled,
                description="Enable content authoring (subjects, concepts, templates).",
            ),
            FeatureFlag(
                key="ai_enabled",
                name="AI Features",
                enabled=settings.beta_flag_ai_enabled,
                description="Enable AI-powered features (explanations, coach, analytics).",
            ),
            FeatureFlag(
                key="notifications_enabled",
                name="Notifications",
                enabled=settings.beta_flag_notifications_enabled,
                description="Enable in-app notifications.",
            ),
            FeatureFlag(
                key="analytics_enabled",
                name="Analytics",
                enabled=settings.beta_flag_analytics_enabled,
                description="Enable analytics tracking and dashboards.",
            ),
            FeatureFlag(
                key="admin_console_enabled",
                name="Admin Console",
                enabled=settings.beta_flag_admin_console_enabled,
                description="Enable the admin console.",
            ),
        ]
    )


@router.get(
    "/feature-flags",
    response_model=FeatureFlagsResponse,
    summary="List public feature flags",
)
async def list_feature_flags_public(
    user_id: UUID = Depends(get_current_user_id),
) -> FeatureFlagsResponse:
    """List public feature flags for the current user."""
    settings = get_settings()
    return FeatureFlagsResponse(
        flags=[
            FeatureFlag(
                key="learning_enabled",
                name="Learning Module",
                enabled=settings.beta_flag_learning_enabled,
                description="Enable the learning module.",
            ),
            FeatureFlag(
                key="ai_enabled",
                name="AI Features",
                enabled=settings.beta_flag_ai_enabled,
                description="Enable AI-powered features.",
            ),
            FeatureFlag(
                key="notifications_enabled",
                name="Notifications",
                enabled=settings.beta_flag_notifications_enabled,
                description="Enable notifications.",
            ),
        ]
    )
