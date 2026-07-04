"""Notifications infrastructure package.

Modules:
- service: NotificationService (creates + manages notifications)
- processor: NotificationProcessor (background worker that delivers notifications)
- preferences: NotificationPreferenceService (manages user preferences)
"""

from app.infrastructure.notifications.service import NotificationService

__all__ = ["NotificationService"]
