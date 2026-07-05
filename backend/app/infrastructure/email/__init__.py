"""Email infrastructure package.

Modules:
- service: EmailService (SMTP abstraction + templates)
- processor: EmailProcessor (background worker that sends queued emails)
"""

from app.infrastructure.email.service import (
    EmailService,
    EmailMessage,
    SendResult,
    SmtpClient,
    InMemorySmtpClient,
    ProductionSmtpClient,
    TEMPLATES,
)

__all__ = [
    "EmailService",
    "EmailMessage",
    "SendResult",
    "SmtpClient",
    "InMemorySmtpClient",
    "ProductionSmtpClient",
    "TEMPLATES",
]
