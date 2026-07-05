"""Closed Beta service — invite management, registration guard, feedback, analytics."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as tz_utc
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.orm.beta import (
    BetaEventModel,
    BetaFeedbackModel,
    BetaInviteModel,
)
from app.infrastructure.database.orm.identity import UserModel
from app.shared.config import get_settings
from app.shared.logging import get_logger

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(tz_utc.utc)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz_utc.utc)
    return dt


@dataclass(frozen=True)
class BetaInvite:
    id: UUID
    email: str
    invite_token: str
    expires_at: datetime
    used_at: datetime | None
    created_by: UUID
    notes: str | None
    created_at: datetime

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        return _utcnow() > _ensure_aware(self.expires_at)

    @property
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired


@dataclass(frozen=True)
class BetaFeedback:
    id: UUID
    user_id: UUID
    rating: int
    category: str
    comment: str
    screenshot_url: str | None
    correlation_id: str | None
    browser: str | None
    platform: str | None
    route: str | None
    status: str
    created_at: datetime


class BetaService:
    """Application-layer service for beta operations (off / closed / open)."""

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def beta_mode(self) -> str:
        """Current beta mode: 'off' | 'closed' | 'open'.

        Backward-compat: if closed_beta_enabled is True, treat as 'closed'.
        Otherwise use the new beta_mode setting.
        """
        # Backward-compat: legacy flag wins if set
        if self._settings.closed_beta_enabled:
            return "closed"
        mode = (self._settings.beta_mode or "off").lower()
        if mode not in ("off", "closed", "open"):
            return "off"
        return mode

    @property
    def is_beta_enabled(self) -> bool:
        """Backward-compat: True when in closed OR open beta mode."""
        return self.beta_mode in ("closed", "open")

    @property
    def is_open_beta(self) -> bool:
        return self.beta_mode == "open"

    @property
    def is_closed_beta(self) -> bool:
        return self.beta_mode == "closed"

    @property
    def max_beta_users(self) -> int:
        return self._settings.max_beta_users

    # Registration Guard

    async def check_registration_allowed(
        self,
        session: AsyncSession,
        email: str,
        invite_token: str | None,
    ) -> tuple[bool, str | None]:
        mode = self.beta_mode

        # OFF mode — anyone can register, no restrictions
        if mode == "off":
            return (True, None)

        # OPEN mode — anyone can register freely (no invite, no cap).
        # We still log the registration as a beta event for analytics.
        if mode == "open":
            count = await session.scalar(
                select(func.count()).select_from(UserModel).where(
                    UserModel.deleted_at.is_(None)
                )
            )
            logger.info(
                "open_beta_registration",
                email=email,
                current_user_count=count or 0,
            )
            return (True, None)

        # CLOSED mode — invite token required, capped at max_beta_users
        count = await session.scalar(
            select(func.count()).select_from(UserModel).where(
                UserModel.deleted_at.is_(None)
            )
        )

        # First-admin bypass: if no users exist yet, allow registration without invite.
        # This lets you create the initial admin account, then invite others.
        if count is not None and count == 0:
            logger.info("beta_first_admin_bypass", email=email)
            return (True, None)

        if count is not None and count >= self.max_beta_users:
            return (False, f"Beta user limit reached ({self.max_beta_users}).")

        if not invite_token:
            return (False, "Invite token required for closed beta registration.")

        invite = await self._get_invite_by_token(session, invite_token)
        if invite is None:
            return (False, "Invalid invite token.")
        if invite.is_used:
            return (False, "Invite token has already been used.")
        if invite.is_expired:
            return (False, "Invite token has expired.")
        if invite.email.lower() != email.lower():
            return (False, "Email does not match the invite.")

        return (True, None)

    async def mark_invite_used(self, session: AsyncSession, invite_token: str) -> bool:
        stmt = (
            update(BetaInviteModel)
            .where(
                BetaInviteModel.invite_token == invite_token,
                BetaInviteModel.used_at.is_(None),
            )
            .values(used_at=_utcnow())
        )
        result = await session.execute(stmt)
        return result.rowcount > 0

    # Invite Management

    async def create_invite(
        self,
        session: AsyncSession,
        email: str,
        created_by: UUID,
        notes: str | None = None,
    ) -> BetaInvite:
        ttl_hours = self._settings.beta_invite_token_ttl_hours
        token = secrets.token_urlsafe(32)
        expires_at = _utcnow() + timedelta(hours=ttl_hours)

        model = BetaInviteModel(
            id=uuid4(),
            email=email.lower().strip(),
            invite_token=token,
            expires_at=expires_at,
            created_by=created_by,
            notes=notes,
        )
        session.add(model)
        await session.flush()
        logger.info("beta_invite_created", invite_id=str(model.id), email=email)
        return self._model_to_invite(model)

    async def list_invites(
        self,
        session: AsyncSession,
        include_used: bool = False,
    ) -> list[BetaInvite]:
        stmt = select(BetaInviteModel).order_by(BetaInviteModel.created_at.desc())
        if not include_used:
            stmt = stmt.where(BetaInviteModel.used_at.is_(None))
        result = await session.execute(stmt)
        return [self._model_to_invite(m) for m in result.scalars().all()]

    async def delete_invite(self, session: AsyncSession, invite_id: UUID) -> bool:
        stmt = delete(BetaInviteModel).where(
            BetaInviteModel.id == invite_id,
            BetaInviteModel.used_at.is_(None),
        )
        result = await session.execute(stmt)
        return result.rowcount > 0

    async def resend_invite(
        self,
        session: AsyncSession,
        invite_id: UUID,
    ) -> BetaInvite | None:
        existing = await session.get(BetaInviteModel, invite_id)
        if existing is None or existing.used_at is not None:
            return None
        new_token = secrets.token_urlsafe(32)
        ttl_hours = self._settings.beta_invite_token_ttl_hours
        existing.invite_token = new_token
        existing.expires_at = _utcnow() + timedelta(hours=ttl_hours)
        await session.flush()
        return self._model_to_invite(existing)

    # Feedback

    async def submit_feedback(
        self,
        session: AsyncSession,
        user_id: UUID,
        rating: int,
        category: str,
        comment: str,
        screenshot_url: str | None = None,
        correlation_id: str | None = None,
        browser: str | None = None,
        platform: str | None = None,
        route: str | None = None,
        user_agent: str | None = None,
    ) -> BetaFeedback:
        model = BetaFeedbackModel(
            id=uuid4(),
            user_id=user_id,
            rating=rating,
            category=category,
            comment=comment,
            screenshot_url=screenshot_url,
            correlation_id=correlation_id,
            browser=browser,
            platform=platform,
            route=route,
            user_agent=user_agent,
            status="open",
        )
        session.add(model)
        await session.flush()
        return self._model_to_feedback(model)

    async def list_feedback(
        self,
        session: AsyncSession,
        status: str | None = None,
        limit: int = 50,
    ) -> list[BetaFeedback]:
        stmt = select(BetaFeedbackModel).order_by(
            BetaFeedbackModel.created_at.desc()
        ).limit(limit)
        if status:
            stmt = stmt.where(BetaFeedbackModel.status == status)
        result = await session.execute(stmt)
        return [self._model_to_feedback(m) for m in result.scalars().all()]

    # Analytics

    async def track_event(
        self,
        session: AsyncSession,
        event_type: str,
        user_id: UUID | None = None,
        event_data: dict[str, Any] | None = None,
        session_id: str | None = None,
        correlation_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        model = BetaEventModel(
            id=uuid4(),
            user_id=user_id,
            event_type=event_type,
            event_data=event_data or {},
            session_id=session_id,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.add(model)
        await session.flush()

    async def get_beta_analytics(self, session: AsyncSession) -> dict[str, Any]:
        total_users = await session.scalar(
            select(func.count()).select_from(UserModel).where(
                UserModel.deleted_at.is_(None)
            )
        ) or 0

        active_invites = await session.scalar(
            select(func.count()).select_from(BetaInviteModel).where(
                BetaInviteModel.used_at.is_(None)
            )
        ) or 0

        used_invites = await session.scalar(
            select(func.count()).select_from(BetaInviteModel).where(
                BetaInviteModel.used_at.is_not(None)
            )
        ) or 0

        total_feedback = await session.scalar(
            select(func.count()).select_from(BetaFeedbackModel)
        ) or 0

        open_feedback = await session.scalar(
            select(func.count()).select_from(BetaFeedbackModel).where(
                BetaFeedbackModel.status == "open"
            )
        ) or 0

        cutoff = _utcnow() - timedelta(hours=24)
        dau = await session.scalar(
            select(func.count(func.distinct(BetaEventModel.user_id)))
            .select_from(BetaEventModel)
            .where(
                BetaEventModel.created_at >= cutoff,
                BetaEventModel.user_id.is_not(None),
            )
        ) or 0

        event_counts_result = await session.execute(
            select(BetaEventModel.event_type, func.count())
            .group_by(BetaEventModel.event_type)
        )
        event_counts = {row[0]: row[1] for row in event_counts_result.all()}

        return {
            "total_users": total_users,
            "max_beta_users": self.max_beta_users,
            "active_invites": active_invites,
            "used_invites": used_invites,
            "total_feedback": total_feedback,
            "open_feedback": open_feedback,
            "daily_active_users": dau,
            "event_counts": event_counts,
            "beta_enabled": self.is_beta_enabled,
        }

    # Feature Flags

    def get_feature_flags(self) -> dict[str, bool]:
        return {
            "learning_enabled": self._settings.beta_flag_learning_enabled,
            "content_authoring_enabled": self._settings.beta_flag_content_authoring_enabled,
            "ai_enabled": self._settings.beta_flag_ai_enabled,
            "notifications_enabled": self._settings.beta_flag_notifications_enabled,
            "analytics_enabled": self._settings.beta_flag_analytics_enabled,
            "admin_console_enabled": self._settings.beta_flag_admin_console_enabled,
        }

    # Helpers

    async def _get_invite_by_token(
        self, session: AsyncSession, token: str
    ) -> BetaInvite | None:
        stmt = select(BetaInviteModel).where(
            BetaInviteModel.invite_token == token
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_invite(model) if model else None

    @staticmethod
    def _model_to_invite(model: BetaInviteModel) -> BetaInvite:
        return BetaInvite(
            id=model.id,
            email=model.email,
            invite_token=model.invite_token,
            expires_at=model.expires_at,
            used_at=model.used_at,
            created_by=model.created_by,
            notes=model.notes,
            created_at=model.created_at,
        )

    @staticmethod
    def _model_to_feedback(model: BetaFeedbackModel) -> BetaFeedback:
        return BetaFeedback(
            id=model.id,
            user_id=model.user_id,
            rating=model.rating,
            category=model.category,
            comment=model.comment,
            screenshot_url=model.screenshot_url,
            correlation_id=model.correlation_id,
            browser=model.browser,
            platform=model.platform,
            route=model.route,
            status=model.status,
            created_at=model.created_at,
        )


_service: BetaService | None = None


def get_beta_service() -> BetaService:
    global _service
    if _service is None:
        _service = BetaService()
    return _service


__all__ = ["BetaService", "BetaInvite", "BetaFeedback", "get_beta_service"]
