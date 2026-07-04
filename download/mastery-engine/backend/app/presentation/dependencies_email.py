"""Email service dependency for FastAPI.

Provides a singleton EmailService wired with the production SMTP client
(ProductionSmtpClient) or an in-memory client (for tests / dev).
"""

from __future__ import annotations

from functools import lru_cache

from app.infrastructure.email.service import (
    EmailService,
    InMemorySmtpClient,
    ProductionSmtpClient,
)
from app.shared.config import get_settings


@lru_cache
def get_email_service() -> EmailService:
    """Provide the singleton EmailService.

    In production: returns an EmailService backed by ProductionSmtpClient
    configured from SMTP_* env vars.
    In testing/development: returns an EmailService backed by
    InMemorySmtpClient (no real emails sent).
    """
    settings = get_settings()

    # In testing or development without SMTP configured, use the in-memory client.
    if settings.is_testing or not settings.smtp_username:
        return EmailService(smtp_client=InMemorySmtpClient())

    # Production: real SMTP client wired from settings.
    smtp_client = ProductionSmtpClient.from_settings(settings)
    return EmailService(
        smtp_client=smtp_client,
        from_address=settings.smtp_from_address,
    )


__all__ = ["get_email_service"]
