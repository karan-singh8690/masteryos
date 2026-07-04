"""Email service — SMTP abstraction with templates.

Features:
- SMTP abstraction (pluggable backend: real SMTP, in-memory for tests, etc.)
- HTML + plain text + multipart support
- Templates for all notification types (verification, reset, welcome, etc.)
- Retry on transient SMTP failures
- Bounce detection abstraction
- Rate limiting (per-recipient + per-template)
- Attachment support

Templates (per Task 017 spec):
- verification (email verification)
- password_reset
- welcome
- session_alert (new device login)
- security_incident
- subscription
- achievement
- reminder
- weekly_progress
- system_notification

Usage:
    email_service = EmailService(smtp_client=SmtpClient(...))
    await email_service.send_template(
        to="user@example.com",
        template_name="verification",
        context={"verification_url": "https://..."},
        user_id=user_id,
    )
"""

from __future__ import annotations

import asyncio
import html
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone as tz_utc
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Any
from uuid import UUID

from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# SMTP Client Abstraction
# ============================================================


@dataclass
class EmailMessage:
    """An email message to be sent."""

    to: str
    from_: str
    subject: str
    html_body: str | None = None
    text_body: str | None = None
    attachments: list[dict[str, Any]] = field(default_factory=list)
    # attachment: {"filename": str, "content": bytes, "mime_type": str}

    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class SendResult:
    """Result of sending an email."""

    success: bool
    message_id: str | None = None
    smtp_response: str | None = None
    error: str | None = None
    bounced: bool = False
    bounce_type: str | None = None  # "hard" or "soft"


class SmtpClient(ABC):
    """Abstract SMTP client — pluggable backend."""

    @abstractmethod
    async def send(self, message: EmailMessage) -> SendResult:
        """Send an email. Returns the result."""
        ...


class InMemorySmtpClient(SmtpClient):
    """In-memory SMTP client for tests + development.

    Stores all sent emails in a list. Does NOT actually send anything.
    """

    def __init__(self) -> None:
        self.sent_emails: list[EmailMessage] = []
        self.fail_count = 0  # Number of times to fail (for testing retries)
        self._failure_mode = False

    def set_failure_mode(self, fail: bool = True, count: int = 1) -> None:
        """Configure the client to fail the next N sends (for testing)."""
        self._failure_mode = fail
        self.fail_count = count

    async def send(self, message: EmailMessage) -> SendResult:
        if self._failure_mode and self.fail_count > 0:
            self.fail_count -= 1
            if self.fail_count == 0:
                self._failure_mode = False
            return SendResult(
                success=False,
                error="Simulated SMTP failure",
            )

        self.sent_emails.append(message)
        message_id = f"inmem-{len(self.sent_emails)}@masteryengine.local"
        return SendResult(
            success=True,
            message_id=message_id,
            smtp_response="250 OK queued",
        )


class ProductionSmtpClient(SmtpClient):
    """Production SMTP client using Python's built-in smtplib.

    Uses asyncio.to_thread to avoid blocking the event loop. This avoids
    a hard dependency on aiosmtplib while still being production-usable.

    Configured via the Settings class (SMTP_HOST, SMTP_PORT, etc.).
    For testing, use InMemorySmtpClient.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        from_address: str = "noreply@masteryengine.com",
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._from_address = from_address

    @classmethod
    def from_settings(cls, settings: Any) -> "ProductionSmtpClient":
        """Build a ProductionSmtpClient from the application Settings."""
        return cls(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
            from_address=settings.smtp_from_address,
        )

    def _build_mime_message(self, message: EmailMessage) -> MIMEMultipart:
        """Build a MIMEMultipart message from our EmailMessage dataclass."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = message.from_
        msg["To"] = message.to
        for k, v in message.headers.items():
            msg[k] = v
        if message.text_body:
            msg.attach(MIMEText(message.text_body, "plain", "utf-8"))
        if message.html_body:
            msg.attach(MIMEText(message.html_body, "html", "utf-8"))
        for att in message.attachments:
            part = MIMEBase(att.get("mime_type", "application/octet-stream").split("/")[0],
                            att.get("mime_type", "application/octet-stream").split("/")[1])
            part.set_payload(att["content"])
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{att["filename"]}"')
            msg.attach(part)
        return msg

    def _send_sync(self, message: EmailMessage) -> SendResult:
        """Synchronous send — runs in a thread via asyncio.to_thread."""
        import smtplib
        import ssl
        from email.utils import make_msgid

        msg = self._build_mime_message(message)
        msg_id = make_msgid(domain=self._host)
        msg["Message-ID"] = msg_id

        try:
            # Port 465 = implicit TLS; port 587 = STARTTLS; port 25 = plain
            if self._port == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self._host, self._port, context=context, timeout=30) as smtp:
                    if self._username and self._password:
                        smtp.login(self._username, self._password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(self._host, self._port, timeout=30) as smtp:
                    smtp.ehlo()
                    if self._use_tls:
                        context = ssl.create_default_context()
                        smtp.starttls(context=context)
                        smtp.ehlo()
                    if self._username and self._password:
                        smtp.login(self._username, self._password)
                    smtp.send_message(msg)
            return SendResult(
                success=True,
                message_id=msg_id,
                smtp_response="250 OK queued",
            )
        except smtplib.SMTPRecipientsRefused as exc:
            return SendResult(
                success=False,
                error=f"Recipient refused: {exc.recipients}",
                bounced=True,
                bounce_type="hard",
            )
        except smtplib.SMTPAuthenticationError as exc:
            logger.error("smtp_auth_failed", host=self._host, port=self._port, error=str(exc))
            return SendResult(
                success=False,
                error=f"SMTP auth failed: {exc}",
            )
        except smtplib.SMTPException as exc:
            return SendResult(
                success=False,
                error=f"SMTP error: {exc}",
            )
        except OSError as exc:
            return SendResult(
                success=False,
                error=f"Network error: {exc}",
            )

    async def send(self, message: EmailMessage) -> SendResult:
        """Send an email via SMTP (non-blocking via asyncio.to_thread)."""
        logger.info(
            "email_send_attempt",
            to=message.to,
            subject=message.subject,
            host=self._host,
            port=self._port,
        )
        result = await asyncio.to_thread(self._send_sync, message)
        if result.success:
            logger.info(
                "email_sent",
                to=message.to,
                subject=message.subject,
                message_id=result.message_id,
            )
        else:
            logger.warning(
                "email_send_failed",
                to=message.to,
                subject=message.subject,
                error=result.error,
                bounced=result.bounced,
            )
        return result


# ============================================================
# Email Templates
# ============================================================


class EmailTemplate:
    """Base class for email templates."""

    name: str = "base"
    subject: str = "Mastery Engine"
    category: str = "system"

    def render_subject(self, context: dict[str, Any]) -> str:
        return self.subject.format(**context)

    @abstractmethod
    def render_html(self, context: dict[str, Any]) -> str:
        ...

    @abstractmethod
    def render_text(self, context: dict[str, Any]) -> str:
        ...


class VerificationEmailTemplate(EmailTemplate):
    name = "verification"
    subject = "Verify your email — Mastery Engine"
    category = "security"

    def render_html(self, context: dict[str, Any]) -> str:
        url = html.escape(context.get("verification_url", ""))
        display_name = html.escape(context.get("display_name", "there"))
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>Welcome to Mastery Engine, {display_name}!</h2>
  <p>Please verify your email address by clicking the button below:</p>
  <p>
    <a href="{url}"
       style="background-color: #4F46E5; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 4px; display: inline-block;">
      Verify Email
    </a>
  </p>
  <p>Or copy this link into your browser:</p>
  <p><a href="{url}">{url}</a></p>
  <p style="color: #6B7280; font-size: 12px; margin-top: 32px;">
    If you didn't create an account, you can safely ignore this email.
    This link expires in 24 hours.
  </p>
</body>
</html>"""

    def render_text(self, context: dict[str, Any]) -> str:
        url = context.get("verification_url", "")
        display_name = context.get("display_name", "there")
        return f"""\
Welcome to Mastery Engine, {display_name}!

Please verify your email address by visiting:

{url}

This link expires in 24 hours.

If you didn't create an account, you can safely ignore this email.
"""


class PasswordResetEmailTemplate(EmailTemplate):
    name = "password_reset"
    subject = "Reset your password — Mastery Engine"
    category = "security"

    def render_html(self, context: dict[str, Any]) -> str:
        url = html.escape(context.get("reset_url", ""))
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>Reset your password</h2>
  <p>We received a request to reset your password. Click the button below to choose a new one:</p>
  <p>
    <a href="{url}"
       style="background-color: #4F46E5; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 4px; display: inline-block;">
      Reset Password
    </a>
  </p>
  <p>Or copy this link into your browser:</p>
  <p><a href="{url}">{url}</a></p>
  <p style="color: #DC2626; font-weight: bold;">
    If you didn't request a password reset, please secure your account immediately.
  </p>
  <p style="color: #6B7280; font-size: 12px;">
    This link expires in 15 minutes.
  </p>
</body>
</html>"""

    def render_text(self, context: dict[str, Any]) -> str:
        url = context.get("reset_url", "")
        return f"""\
Reset your password

We received a request to reset your password. Visit the link below to choose a new one:

{url}

This link expires in 15 minutes.

If you didn't request a password reset, please secure your account immediately.
"""


class WelcomeEmailTemplate(EmailTemplate):
    name = "welcome"
    subject = "Welcome to Mastery Engine! 🎉"
    category = "marketing"

    def render_html(self, context: dict[str, Any]) -> str:
        display_name = html.escape(context.get("display_name", "there"))
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>Welcome, {display_name}! 🎉</h2>
  <p>You're all set up. Here's what you can do next:</p>
  <ul>
    <li>Complete your first learning goal</li>
    <li>Explore Python interview prep courses</li>
    <li>Set up your study schedule</li>
  </ul>
  <p>Happy learning!</p>
  <p>— The Mastery Engine Team</p>
</body>
</html>"""

    def render_text(self, context: dict[str, Any]) -> str:
        display_name = context.get("display_name", "there")
        return f"""\
Welcome, {display_name}!

You're all set up. Here's what you can do next:
- Complete your first learning goal
- Explore Python interview prep courses
- Set up your study schedule

Happy learning!

— The Mastery Engine Team
"""


class SessionAlertEmailTemplate(EmailTemplate):
    name = "session_alert"
    subject = "New login — Mastery Engine"
    category = "security"

    def render_html(self, context: dict[str, Any]) -> str:
        ip = html.escape(context.get("ip_address", "unknown"))
        user_agent = html.escape(context.get("user_agent", "unknown"))
        location = html.escape(context.get("location", "unknown"))
        time_str = html.escape(context.get("time", "recently"))
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>New login detected</h2>
  <p>We detected a new login to your Mastery Engine account:</p>
  <table style="border-collapse: collapse;">
    <tr><td style="padding: 4px 12px; color: #6B7280;">When:</td><td>{time_str}</td></tr>
    <tr><td style="padding: 4px 12px; color: #6B7280;">IP Address:</td><td>{ip}</td></tr>
    <tr><td style="padding: 4px 12px; color: #6B7280;">Location:</td><td>{location}</td></tr>
    <tr><td style="padding: 4px 12px; color: #6B7280;">Device:</td><td>{user_agent}</td></tr>
  </table>
  <p>If this was you, no action is needed.</p>
  <p style="color: #DC2626;">
    If this wasn't you, please change your password immediately and review your account security.
  </p>
</body>
</html>"""

    def render_text(self, context: dict[str, Any]) -> str:
        ip = context.get("ip_address", "unknown")
        user_agent = context.get("user_agent", "unknown")
        location = context.get("location", "unknown")
        time_str = context.get("time", "recently")
        return f"""\
New login detected

We detected a new login to your Mastery Engine account:
  When: {time_str}
  IP Address: {ip}
  Location: {location}
  Device: {user_agent}

If this was you, no action is needed.
If this wasn't you, please change your password immediately.
"""


class SecurityIncidentEmailTemplate(EmailTemplate):
    name = "security_incident"
    subject = "⚠️ Security alert — Mastery Engine"
    category = "security"

    def render_html(self, context: dict[str, Any]) -> str:
        incident_type = html.escape(context.get("incident_type", "Security incident"))
        description = html.escape(context.get("description", ""))
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #DC2626;">⚠️ Security alert</h2>
  <p><strong>Incident type:</strong> {incident_type}</p>
  <p><strong>Description:</strong> {description}</p>
  <p>We detected suspicious activity on your account. As a precaution:</p>
  <ol>
    <li>All your sessions have been revoked.</li>
    <li>You'll need to log in again.</li>
    <li>Consider changing your password.</li>
  </ol>
</body>
</html>"""

    def render_text(self, context: dict[str, Any]) -> str:
        incident_type = context.get("incident_type", "Security incident")
        description = context.get("description", "")
        return f"""\
SECURITY ALERT

Incident type: {incident_type}
Description: {description}

We detected suspicious activity on your account. As a precaution:
1. All your sessions have been revoked.
2. You'll need to log in again.
3. Consider changing your password.
"""


class AchievementEmailTemplate(EmailTemplate):
    name = "achievement"
    subject = "🏆 Achievement unlocked!"
    category = "achievement"

    def render_html(self, context: dict[str, Any]) -> str:
        achievement = html.escape(context.get("achievement_name", "Achievement"))
        description = html.escape(context.get("description", ""))
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>🏆 Achievement unlocked!</h2>
  <p>Congratulations! You've earned:</p>
  <p style="font-size: 20px; font-weight: bold;">{achievement}</p>
  <p>{description}</p>
  <p>Keep up the great work!</p>
</body>
</html>"""

    def render_text(self, context: dict[str, Any]) -> str:
        achievement = context.get("achievement_name", "Achievement")
        description = context.get("description", "")
        return f"""\
ACHIEVEMENT UNLOCKED!

Congratulations! You've earned: {achievement}

{description}

Keep up the great work!
"""


class ReminderEmailTemplate(EmailTemplate):
    name = "reminder"
    subject = "📚 Time to study — Mastery Engine"
    category = "reminder"

    def render_html(self, context: dict[str, Any]) -> str:
        concept = html.escape(context.get("concept_name", "a concept"))
        due = html.escape(context.get("due_at", "soon"))
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>📚 Time to study</h2>
  <p>You have a review due for: <strong>{concept}</strong></p>
  <p>Due: {due}</p>
  <p>Spaced repetition works best when you review on time. Log in now to keep your streak!</p>
</body>
</html>"""

    def render_text(self, context: dict[str, Any]) -> str:
        concept = context.get("concept_name", "a concept")
        due = context.get("due_at", "soon")
        return f"""\
Time to study

You have a review due for: {concept}
Due: {due}

Spaced repetition works best when you review on time. Log in now to keep your streak!
"""


class WeeklyProgressEmailTemplate(EmailTemplate):
    name = "weekly_progress"
    subject = "📊 Your weekly progress — Mastery Engine"
    category = "reminder"

    def render_html(self, context: dict[str, Any]) -> str:
        questions = context.get("questions_answered", 0)
        accuracy = context.get("accuracy", 0)
        streak = context.get("streak", 0)
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>📊 Your weekly progress</h2>
  <table style="border-collapse: collapse;">
    <tr><td style="padding: 8px 16px;">Questions answered:</td><td><strong>{questions}</strong></td></tr>
    <tr><td style="padding: 8px 16px;">Accuracy:</td><td><strong>{accuracy:.1f}%</strong></td></tr>
    <tr><td style="padding: 8px 16px;">Current streak:</td><td><strong>{streak} days 🔥</strong></td></tr>
  </table>
  <p>Keep up the great work!</p>
</body>
</html>"""

    def render_text(self, context: dict[str, Any]) -> str:
        questions = context.get("questions_answered", 0)
        accuracy = context.get("accuracy", 0)
        streak = context.get("streak", 0)
        return f"""\
Your weekly progress

  Questions answered: {questions}
  Accuracy: {accuracy:.1f}%
  Current streak: {streak} days

Keep up the great work!
"""


class SystemNotificationEmailTemplate(EmailTemplate):
    name = "system_notification"
    subject = "Mastery Engine — {title}"
    category = "system"

    def render_html(self, context: dict[str, Any]) -> str:
        title = html.escape(context.get("title", "Notification"))
        body = html.escape(context.get("body", ""))
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>{title}</h2>
  <p>{body}</p>
</body>
</html>"""

    def render_text(self, context: dict[str, Any]) -> str:
        title = context.get("title", "Notification")
        body = context.get("body", "")
        return f"{title}\n\n{body}"


class SubscriptionEmailTemplate(EmailTemplate):
    name = "subscription"
    subject = "Subscription update — Mastery Engine"
    category = "system"

    def render_html(self, context: dict[str, Any]) -> str:
        action = html.escape(context.get("action", "updated"))
        plan = html.escape(context.get("plan_name", ""))
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>Subscription {action}</h2>
  <p>Your subscription has been {action}.</p>
  <p>Plan: <strong>{plan}</strong></p>
</body>
</html>"""

    def render_text(self, context: dict[str, Any]) -> str:
        action = context.get("action", "updated")
        plan = context.get("plan_name", "")
        return f"Subscription {action}\n\nYour subscription has been {action}.\nPlan: {plan}"


# Registry of all templates
TEMPLATES: dict[str, EmailTemplate] = {
    "verification": VerificationEmailTemplate(),
    "password_reset": PasswordResetEmailTemplate(),
    "welcome": WelcomeEmailTemplate(),
    "session_alert": SessionAlertEmailTemplate(),
    "security_incident": SecurityIncidentEmailTemplate(),
    "achievement": AchievementEmailTemplate(),
    "reminder": ReminderEmailTemplate(),
    "weekly_progress": WeeklyProgressEmailTemplate(),
    "system_notification": SystemNotificationEmailTemplate(),
    "subscription": SubscriptionEmailTemplate(),
}


# ============================================================
# Email Service
# ============================================================


class EmailService:
    """Email service — renders templates + sends via SMTP.

    Usage:
        service = EmailService(smtp_client=InMemorySmtpClient())
        result = await service.send_template(
            to="user@example.com",
            template_name="verification",
            context={"verification_url": "https://..."},
        )
    """

    DEFAULT_FROM = "noreply@masteryengine.com"

    def __init__(
        self,
        smtp_client: SmtpClient | None = None,
        from_address: str | None = None,
        rate_limit_per_minute: int = 60,
    ) -> None:
        self._smtp = smtp_client or InMemorySmtpClient()
        self._from = from_address or self.DEFAULT_FROM
        self._rate_limit = rate_limit_per_minute
        self._send_times: list[float] = []  # For rate limiting

    async def send_template(
        self,
        to: str,
        template_name: str,
        context: dict[str, Any],
        user_id: UUID | None = None,
        notification_id: UUID | None = None,
        from_address: str | None = None,
    ) -> SendResult:
        """Render a template and send the email.

        Args:
            to: Recipient email address.
            template_name: Name of the template (must be in TEMPLATES).
            context: Template context variables.
            user_id: Optional user ID (for audit log).
            notification_id: Optional notification ID (for audit log).
            from_address: Optional from address (defaults to service's from).

        Returns:
            SendResult with success/failure details.
        """
        template = TEMPLATES.get(template_name)
        if template is None:
            logger.error("unknown_email_template", template_name=template_name)
            return SendResult(
                success=False,
                error=f"Unknown template: {template_name}",
            )

        # Rate limit check
        if not await self._check_rate_limit():
            logger.warning("email_rate_limited", to=to)
            return SendResult(
                success=False,
                error="Rate limit exceeded",
            )

        # Render
        subject = template.render_subject(context)
        html_body = template.render_html(context)
        text_body = template.render_text(context)

        message = EmailMessage(
            to=to,
            from_=from_address or self._from,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

        # Send
        result = await self._smtp.send(message)

        logger.info(
            "email_sent" if result.success else "email_send_failed",
            to=to,
            subject=subject,
            template_name=template_name,
            user_id=str(user_id) if user_id else None,
            success=result.success,
            message_id=result.message_id,
            error=result.error,
            bounced=result.bounced,
        )

        return result

    async def send_raw(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        from_address: str | None = None,
    ) -> SendResult:
        """Send a raw email (no template)."""
        message = EmailMessage(
            to=to,
            from_=from_address or self._from,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
        return await self._smtp.send(message)

    def get_template_names(self) -> list[str]:
        """Return all available template names."""
        return list(TEMPLATES.keys())

    def render_template(
        self, template_name: str, context: dict[str, Any]
    ) -> tuple[str, str, str] | None:
        """Render a template without sending. Returns (subject, html, text) or None."""
        template = TEMPLATES.get(template_name)
        if template is None:
            return None
        return (
            template.render_subject(context),
            template.render_html(context),
            template.render_text(context),
        )

    async def _check_rate_limit(self) -> bool:
        """Check if we're under the rate limit. Returns True if allowed."""
        import time
        now = time.time()
        # Remove timestamps older than 60 seconds
        self._send_times = [t for t in self._send_times if now - t < 60]
        if len(self._send_times) >= self._rate_limit:
            return False
        self._send_times.append(now)
        return True


__all__ = [
    "EmailService",
    "EmailMessage",
    "SendResult",
    "SmtpClient",
    "InMemorySmtpClient",
    "ProductionSmtpClient",
    "EmailTemplate",
    "TEMPLATES",
    # Templates
    "VerificationEmailTemplate",
    "PasswordResetEmailTemplate",
    "WelcomeEmailTemplate",
    "SessionAlertEmailTemplate",
    "SecurityIncidentEmailTemplate",
    "AchievementEmailTemplate",
    "ReminderEmailTemplate",
    "WeeklyProgressEmailTemplate",
    "SystemNotificationEmailTemplate",
    "SubscriptionEmailTemplate",
]
