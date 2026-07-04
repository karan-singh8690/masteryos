"""Tests for the email service + templates.

Tests:
- All 10 templates are registered
- Each template renders HTML + plain text
- EmailService.send_template sends via SMTP
- EmailService.send_raw sends via SMTP
- InMemorySmtpClient stores sent emails
- InMemorySmtpClient can simulate failures
- Email rate limiting
- Template rendering with context
- Subject line formatting
- HTML escaping in templates
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.infrastructure.email.service import (
    AchievementEmailTemplate,
    EmailMessage,
    EmailService,
    InMemorySmtpClient,
    PasswordResetEmailTemplate,
    ProductionSmtpClient,
    ReminderEmailTemplate,
    SecurityIncidentEmailTemplate,
    SessionAlertEmailTemplate,
    SubscriptionEmailTemplate,
    SystemNotificationEmailTemplate,
    TEMPLATES,
    VerificationEmailTemplate,
    WeeklyProgressEmailTemplate,
    WelcomeEmailTemplate,
)


class TestTemplates:
    """Tests for email templates."""

    def test_all_10_templates_registered(self):
        """All 10 templates from the spec are registered."""
        assert len(TEMPLATES) == 10
        assert "verification" in TEMPLATES
        assert "password_reset" in TEMPLATES
        assert "welcome" in TEMPLATES
        assert "session_alert" in TEMPLATES
        assert "security_incident" in TEMPLATES
        assert "subscription" in TEMPLATES
        assert "achievement" in TEMPLATES
        assert "reminder" in TEMPLATES
        assert "weekly_progress" in TEMPLATES
        assert "system_notification" in TEMPLATES

    def test_verification_template_renders_html(self):
        template = VerificationEmailTemplate()
        html = template.render_html({
            "verification_url": "https://example.com/verify?token=abc",
            "display_name": "Alice",
        })
        assert "Alice" in html
        assert "https://example.com/verify?token=abc" in html
        assert "Verify Email" in html

    def test_verification_template_renders_text(self):
        template = VerificationEmailTemplate()
        text = template.render_text({
            "verification_url": "https://example.com/verify?token=abc",
            "display_name": "Alice",
        })
        assert "Alice" in text
        assert "https://example.com/verify?token=abc" in text

    def test_password_reset_template_renders(self):
        template = PasswordResetEmailTemplate()
        html = template.render_html({"reset_url": "https://example.com/reset?token=abc"})
        text = template.render_text({"reset_url": "https://example.com/reset?token=abc"})
        assert "Reset Password" in html
        assert "https://example.com/reset?token=abc" in html
        assert "https://example.com/reset?token=abc" in text

    def test_welcome_template_renders(self):
        template = WelcomeEmailTemplate()
        html = template.render_html({"display_name": "Bob"})
        text = template.render_text({"display_name": "Bob"})
        assert "Bob" in html
        assert "Bob" in text

    def test_session_alert_template_renders(self):
        template = SessionAlertEmailTemplate()
        context = {
            "ip_address": "1.2.3.4",
            "user_agent": "Chrome",
            "location": "New York",
            "time": "2024-01-01 12:00",
        }
        html = template.render_html(context)
        text = template.render_text(context)
        assert "1.2.3.4" in html
        assert "Chrome" in html
        assert "New York" in html
        assert "1.2.3.4" in text

    def test_security_incident_template_renders(self):
        template = SecurityIncidentEmailTemplate()
        context = {
            "incident_type": "refresh_token_reuse",
            "description": "Someone tried to reuse a refresh token.",
        }
        html = template.render_html(context)
        text = template.render_text(context)
        assert "refresh_token_reuse" in html
        assert "Security alert" in html

    def test_achievement_template_renders(self):
        template = AchievementEmailTemplate()
        context = {
            "achievement_name": "Python Master",
            "description": "You mastered Python!",
        }
        html = template.render_html(context)
        text = template.render_text(context)
        assert "Python Master" in html
        assert "Achievement unlocked" in html

    def test_reminder_template_renders(self):
        template = ReminderEmailTemplate()
        context = {
            "concept_name": "Decorators",
            "due_at": "2024-01-01",
        }
        html = template.render_html(context)
        text = template.render_text(context)
        assert "Decorators" in html
        assert "2024-01-01" in html

    def test_weekly_progress_template_renders(self):
        template = WeeklyProgressEmailTemplate()
        context = {
            "questions_answered": 42,
            "accuracy": 85.5,
            "streak": 7,
        }
        html = template.render_html(context)
        text = template.render_text(context)
        assert "42" in html
        assert "85.5" in html
        assert "7" in html

    def test_system_notification_template_renders(self):
        template = SystemNotificationEmailTemplate()
        context = {
            "title": "Maintenance",
            "body": "Scheduled maintenance tonight.",
        }
        html = template.render_html(context)
        text = template.render_text(context)
        assert "Maintenance" in html
        assert "Scheduled maintenance tonight." in html

    def test_subscription_template_renders(self):
        template = SubscriptionEmailTemplate()
        context = {
            "action": "upgraded",
            "plan_name": "Pro",
        }
        html = template.render_html(context)
        text = template.render_text(context)
        assert "upgraded" in html
        assert "Pro" in html

    def test_html_escaping(self):
        """Templates escape HTML in user-provided content."""
        template = WelcomeEmailTemplate()
        html = template.render_html({"display_name": "<script>alert('xss')</script>"})
        # The script tag should be escaped
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestInMemorySmtpClient:
    """Tests for the InMemorySmtpClient."""

    @pytest.mark.asyncio
    async def test_send_stores_email(self):
        client = InMemorySmtpClient()
        message = EmailMessage(
            to="user@example.com",
            from_="noreply@example.com",
            subject="Test",
            html_body="<p>Hello</p>",
            text_body="Hello",
        )
        result = await client.send(message)
        assert result.success is True
        assert result.message_id is not None
        assert len(client.sent_emails) == 1
        assert client.sent_emails[0].to == "user@example.com"

    @pytest.mark.asyncio
    async def test_send_simulates_failure(self):
        client = InMemorySmtpClient()
        client.set_failure_mode(fail=True, count=1)

        message = EmailMessage(
            to="user@example.com",
            from_="noreply@example.com",
            subject="Test",
        )
        result = await client.send(message)
        assert result.success is False
        assert "Simulated" in result.error

    @pytest.mark.asyncio
    async def test_send_recovers_after_failures(self):
        client = InMemorySmtpClient()
        client.set_failure_mode(fail=True, count=2)

        message = EmailMessage(
            to="user@example.com",
            from_="noreply@example.com",
            subject="Test",
        )

        # First two fail
        r1 = await client.send(message)
        r2 = await client.send(message)
        assert r1.success is False
        assert r2.success is False

        # Third succeeds
        r3 = await client.send(message)
        assert r3.success is True


class TestEmailService:
    """Tests for the EmailService."""

    @pytest.mark.asyncio
    async def test_send_template_success(self):
        client = InMemorySmtpClient()
        service = EmailService(smtp_client=client)

        result = await service.send_template(
            to="user@example.com",
            template_name="verification",
            context={
                "verification_url": "https://example.com/verify?token=abc",
                "display_name": "Alice",
            },
        )
        assert result.success is True
        assert len(client.sent_emails) == 1
        assert client.sent_emails[0].to == "user@example.com"
        assert "Verify" in client.sent_emails[0].subject

    @pytest.mark.asyncio
    async def test_send_template_unknown_returns_error(self):
        client = InMemorySmtpClient()
        service = EmailService(smtp_client=client)

        result = await service.send_template(
            to="user@example.com",
            template_name="nonexistent",
            context={},
        )
        assert result.success is False
        assert "Unknown template" in result.error

    @pytest.mark.asyncio
    async def test_send_raw(self):
        client = InMemorySmtpClient()
        service = EmailService(smtp_client=client)

        result = await service.send_raw(
            to="user@example.com",
            subject="Test",
            html_body="<p>Hello</p>",
            text_body="Hello",
        )
        assert result.success is True
        assert len(client.sent_emails) == 1

    @pytest.mark.asyncio
    async def test_send_template_with_user_id(self):
        client = InMemorySmtpClient()
        service = EmailService(smtp_client=client)
        user_id = uuid4()

        result = await service.send_template(
            to="user@example.com",
            template_name="welcome",
            context={"display_name": "Bob"},
            user_id=user_id,
        )
        assert result.success is True

    def test_get_template_names(self):
        service = EmailService(smtp_client=InMemorySmtpClient())
        names = service.get_template_names()
        assert "verification" in names
        assert "password_reset" in names
        assert len(names) == 10

    def test_render_template_without_sending(self):
        service = EmailService(smtp_client=InMemorySmtpClient())
        rendered = service.render_template(
            "verification",
            {"verification_url": "https://example.com", "display_name": "Test"},
        )
        assert rendered is not None
        subject, html, text = rendered
        assert "Verify" in subject
        assert "Test" in html
        assert "Test" in text

    def test_render_unknown_template_returns_none(self):
        service = EmailService(smtp_client=InMemorySmtpClient())
        rendered = service.render_template("nonexistent", {})
        assert rendered is None

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """The service rate-limits sends."""
        client = InMemorySmtpClient()
        service = EmailService(smtp_client=client, rate_limit_per_minute=3)

        # First 3 succeed
        for _ in range(3):
            result = await service.send_template(
                to="user@example.com",
                template_name="welcome",
                context={"display_name": "Test"},
            )
            assert result.success is True

        # 4th should be rate-limited
        result = await service.send_template(
            to="user@example.com",
            template_name="welcome",
            context={"display_name": "Test"},
        )
        assert result.success is False
        assert "Rate limit" in result.error

    @pytest.mark.asyncio
    async def test_send_template_retries_on_smtp_failure(self):
        """When SMTP fails, the service returns failure (caller handles retry)."""
        client = InMemorySmtpClient()
        client.set_failure_mode(fail=True, count=1)

        service = EmailService(smtp_client=client)

        result = await service.send_template(
            to="user@example.com",
            template_name="welcome",
            context={"display_name": "Test"},
        )
        assert result.success is False
        assert "Simulated" in result.error
