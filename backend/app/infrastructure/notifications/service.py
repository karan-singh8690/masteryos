"""Notification service — creates + delivers notifications.

This service is the application-layer facade for the notification system.
It:
1. Creates Notification records in response to domain events.
2. Checks user preferences (channel enabled, quiet hours, digest).
3. Applies deduplication (don't send the same notification twice).
4. Routes to the appropriate channel (in-app, email, push).
5. Handles priority + expiration.

The actual delivery (SMTP send, push API call) is done by the
NotificationProcessor (a background worker), NOT by this service.
This service only creates the Notification record.

Usage:
    service = NotificationService(session)
    await service.create_notification(
        user_id=user_id,
        notification_type="achievement_unlocked",
        title="Achievement Unlocked!",
        body="You mastered Python decorators.",
        channel="in_app",
        category="achievement",
        related_aggregate_id=achievement_id,
        related_aggregate_type="Achievement",
    )
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as tz_utc
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories.background import (
    NotificationPreferenceRepository,
    NotificationRepository,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Notification categories (map to preference toggles)
# ============================================================

CATEGORY_SECURITY = "security"
CATEGORY_ACHIEVEMENT = "achievement"
CATEGORY_MARKETING = "marketing"
CATEGORY_REMINDER = "reminder"
CATEGORY_SYSTEM = "system"

ALL_CATEGORIES = [
    CATEGORY_SECURITY,
    CATEGORY_ACHIEVEMENT,
    CATEGORY_MARKETING,
    CATEGORY_REMINDER,
    CATEGORY_SYSTEM,
]


# ============================================================
# Priorities
# ============================================================

PRIORITY_LOW = "low"
PRIORITY_NORMAL = "normal"
PRIORITY_HIGH = "high"
PRIORITY_URGENT = "urgent"


# ============================================================
# Notification Service
# ============================================================


class NotificationService:
    """Application-layer service for creating + managing notifications.

    The service does NOT deliver notifications — it only creates them.
    The NotificationProcessor (background worker) handles delivery.

    Channel routing logic:
    - If channel="in_app": always create (in-app respects quiet hours less strictly)
    - If channel="email": check email_enabled + category toggle + quiet hours
    - Security notifications bypass quiet hours + preference overrides (mandatory)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._notification_repo = NotificationRepository(session)
        self._preference_repo = NotificationPreferenceRepository(session)

    async def create_notification(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        body: str,
        channel: str = "in_app",
        priority: str = PRIORITY_NORMAL,
        category: str | None = None,
        payload: dict[str, Any] | None = None,
        locale: str = "en-US",
        dedup_key: str | None = None,
        scheduled_at: datetime | None = None,
        expires_at: datetime | None = None,
        related_aggregate_id: UUID | None = None,
        related_aggregate_type: str | None = None,
        bypass_preferences: bool = False,
    ) -> dict[str, Any] | None:
        """Create a notification.

        Returns the notification dict if created, or None if:
        - Dedup key already exists (duplicate suppressed)
        - Channel disabled in preferences (and not bypass_preferences)
        - In quiet hours (and not bypass_preferences)
        - Security notifications always bypass preferences

        Args:
            bypass_preferences: If True, skip preference/quiet-hours checks.
                Used for security notifications (mandatory).
        """
        # Security notifications always bypass preferences
        if category == CATEGORY_SECURITY:
            bypass_preferences = True

        # Check dedup
        if dedup_key:
            exists = await self._notification_repo.check_dedup(
                user_id, notification_type, dedup_key
            )
            if exists:
                logger.info(
                    "notification_deduped",
                    user_id=str(user_id),
                    notification_type=notification_type,
                    dedup_key=dedup_key,
                )
                return None

        # Check preferences (unless bypassing)
        if not bypass_preferences:
            channel_enabled = await self._preference_repo.is_channel_enabled(
                user_id, channel, category
            )
            if not channel_enabled:
                logger.info(
                    "notification_channel_disabled",
                    user_id=str(user_id),
                    channel=channel,
                    category=category,
                )
                return None

            # Check quiet hours (defers non-urgent notifications)
            if priority != PRIORITY_URGENT:
                in_quiet = await self._preference_repo.is_in_quiet_hours(user_id)
                if in_quiet:
                    # Defer until quiet hours end
                    scheduled_at = await self._compute_quiet_hours_end(user_id)
                    logger.info(
                        "notification_deferred_quiet_hours",
                        user_id=str(user_id),
                        deferred_to=scheduled_at.isoformat() if scheduled_at else None,
                    )

        # Create the notification
        notification = await self._notification_repo.create(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            channel=channel,
            priority=priority,
            payload=payload or {},
            locale=locale,
            dedup_key=dedup_key,
            scheduled_at=scheduled_at,
            expires_at=expires_at,
            related_aggregate_id=related_aggregate_id,
            related_aggregate_type=related_aggregate_type,
        )

        logger.info(
            "notification_created",
            notification_id=str(notification.id),
            user_id=str(user_id),
            notification_type=notification_type,
            channel=channel,
            priority=priority,
        )

        return {
            "id": str(notification.id),
            "user_id": str(notification.user_id),
            "notification_type": notification.notification_type,
            "channel": notification.channel,
            "priority": notification.priority,
            "status": notification.status,
            "title": notification.title,
            "body": notification.body,
            "scheduled_at": notification.scheduled_at.isoformat()
            if notification.scheduled_at else None,
        }

    async def mark_opened(self, notification_id: UUID) -> bool:
        """Mark a notification as opened (by the user)."""
        return await self._notification_repo.mark_opened(notification_id)

    async def mark_dismissed(self, notification_id: UUID) -> bool:
        """Mark a notification as dismissed."""
        return await self._notification_repo.mark_dismissed(notification_id)

    async def list_user_notifications(
        self,
        user_id: UUID,
        include_read: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List a user's notifications."""
        notifications = await self._notification_repo.list_by_user(
            user_id, include_read=include_read, limit=limit, offset=offset
        )
        return [self._to_dict(n) for n in notifications]

    async def count_unread(self, user_id: UUID) -> int:
        """Count a user's unread notifications."""
        return await self._notification_repo.count_unread(user_id)

    async def _compute_quiet_hours_end(self, user_id: UUID) -> datetime | None:
        """Compute when quiet hours end for the user."""
        prefs = await self._preference_repo.get_by_user(user_id)
        if prefs is None or not prefs.quiet_hours_end:
            return None

        # Parse the quiet_hours_end (HH:MM) and compute the next occurrence
        try:
            import zoneinfo
            from datetime import datetime as dt
            hour, minute = prefs.quiet_hours_end.split(":")
            tz = zoneinfo.ZoneInfo(prefs.timezone)
            now = datetime.now(tz_utc.utc).astimezone(tz)
            end_time = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
            if end_time <= now:
                end_time += timedelta(days=1)
            return end_time.astimezone(tz_utc.utc)
        except Exception as exc:
            logger.warning("compute_quiet_hours_end_failed", error=str(exc))
            return None

    @staticmethod
    def _to_dict(n) -> dict[str, Any]:
        return {
            "id": str(n.id),
            "user_id": str(n.user_id),
            "notification_type": n.notification_type,
            "channel": n.channel,
            "priority": n.priority,
            "status": n.status,
            "title": n.title,
            "body": n.body,
            "payload": n.payload,
            "locale": n.locale,
            "scheduled_at": n.scheduled_at.isoformat() if n.scheduled_at else None,
            "sent_at": n.sent_at.isoformat() if n.sent_at else None,
            "delivered_at": n.delivered_at.isoformat() if n.delivered_at else None,
            "opened_at": n.opened_at.isoformat() if n.opened_at else None,
            "dismissed_at": n.dismissed_at.isoformat() if n.dismissed_at else None,
            "related_aggregate_id": str(n.related_aggregate_id) if n.related_aggregate_id else None,
            "related_aggregate_type": n.related_aggregate_type,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }


__all__ = [
    "NotificationService",
    "CATEGORY_SECURITY",
    "CATEGORY_ACHIEVEMENT",
    "CATEGORY_MARKETING",
    "CATEGORY_REMINDER",
    "CATEGORY_SYSTEM",
    "ALL_CATEGORIES",
    "PRIORITY_LOW",
    "PRIORITY_NORMAL",
    "PRIORITY_HIGH",
    "PRIORITY_URGENT",
]
