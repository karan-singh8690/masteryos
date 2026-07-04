# Email Service

> **Component:** EmailService + SmtpClient + Templates

## Overview

The email service provides an SMTP abstraction with template rendering, retry, and bounce detection.

## Architecture

```
NotificationProcessor
       │
       ▼
EmailService
       │
       ├── render_template(template_name, context)
       │      │
       │      └── TEMPLATES[template_name].render_html(context)
       │          TEMPLATES[template_name].render_text(context)
       │
       └── send_via_smtp(message)
              │
              └── SmtpClient.send(message)
                     │
                     ├── InMemorySmtpClient (tests/dev)
                     └── ProductionSmtpClient (aiosmtplib)
```

## SMTP Client Abstraction

```python
class SmtpClient(ABC):
    @abstractmethod
    async def send(self, message: EmailMessage) -> SendResult:
        ...
```

### InMemorySmtpClient

- Stores all sent emails in a list (for testing).
- Can simulate failures (for testing retries).

```python
client = InMemorySmtpClient()
client.set_failure_mode(fail=True, count=2)  # Fail the next 2 sends
```

### ProductionSmtpClient

- Uses `aiosmtplib` to connect to an SMTP server.
- Configured via environment variables: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`.

## Templates

10 templates are available:

| Template | Purpose | Category |
|---|---|---|
| `verification` | Email verification on registration | security |
| `password_reset` | Password reset link | security |
| `welcome` | Welcome email after registration | marketing |
| `session_alert` | New device login alert | security |
| `security_incident` | Security incident (e.g., token reuse) | security |
| `subscription` | Subscription changes | system |
| `achievement` | Achievement unlocked | achievement |
| `reminder` | Review due reminder | reminder |
| `weekly_progress` | Weekly progress summary | reminder |
| `system_notification` | Generic system notification | system |

### Template Structure

Each template extends `EmailTemplate`:

```python
class VerificationEmailTemplate(EmailTemplate):
    name = "verification"
    subject = "Verify your email — Mastery Engine"
    category = "security"

    def render_html(self, context: dict) -> str:
        url = html.escape(context["verification_url"])
        return f"""<!DOCTYPE html>..."""

    def render_text(self, context: dict) -> str:
        url = context["verification_url"]
        return f"Verify your email: {url}"
```

### HTML Escaping

All user-provided content is HTML-escaped to prevent XSS:

```python
html.escape(context["display_name"])
```

### Multipart Support

Each template renders both HTML and plain text. The email is sent as multipart/alternative:

```
Content-Type: multipart/alternative
  ├── text/plain (plain text version)
  └── text/html (HTML version)
```

## Sending Emails

### Via Template

```python
service = EmailService(smtp_client=client)

result = await service.send_template(
    to="user@example.com",
    template_name="verification",
    context={
        "verification_url": "https://app.masteryengine.com/verify?token=abc",
        "display_name": "Alice",
    },
    user_id=user_id,           # For audit log
    notification_id=notif_id,  # For audit log
)
```

### Raw (No Template)

```python
result = await service.send_raw(
    to="user@example.com",
    subject="Custom Subject",
    html_body="<p>Hello</p>",
    text_body="Hello",
)
```

## Email Delivery Log

Every email send (or attempt) is recorded in `email_delivery_log`:

```sql
CREATE TABLE infrastructure.email_delivery_log (
    id              UUID PRIMARY KEY,
    notification_id UUID,
    user_id         UUID,
    to_address      TEXT NOT NULL,
    from_address    TEXT NOT NULL,
    subject         TEXT NOT NULL,
    template_name   VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued', 'sent', 'delivered', 'bounced', 'failed', 'deferred')),
    message_id      TEXT,
    smtp_response   TEXT,
    error_message   TEXT,
    bounce_type     VARCHAR(50),
    bounce_reason   TEXT,
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    next_retry_at   TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ,
    delivered_at    TIMESTAMPTZ,
    ...
);
```

## Retry on Failure

The `EmailProcessor` (background worker) retries failed emails:

1. Polls `email_delivery_log` for entries with `status='failed'` and `next_retry_at <= now`.
2. Re-sends the email.
3. On success: marks as `sent`.
4. On failure: schedules next retry (with exponential backoff: 5s, 30s, 2min, 10min, 1h).
5. After 5 failed attempts: marks as permanently failed.

## Rate Limiting

The `EmailService` enforces a per-instance rate limit (default: 60 emails/minute):

```python
service = EmailService(smtp_client=client, rate_limit_per_minute=60)
```

If the rate limit is exceeded, `send_template` returns a failure with `error="Rate limit exceeded"`.

## Bounce Detection

Bounce detection is handled via webhooks (future work):

1. The email provider (e.g., SendGrid, AWS SES) sends a webhook notification on bounce.
2. The webhook handler updates `email_delivery_log.status = 'bounced'` and records `bounce_type` (hard/soft).
3. For hard bounces: the user's email is marked as undeliverable (no future sends).
4. For soft bounces: retried with backoff.

## Attachments

Attachments are supported via the `EmailMessage.attachments` field:

```python
message = EmailMessage(
    to="user@example.com",
    from_="noreply@masteryengine.com",
    subject="Your invoice",
    html_body="<p>See attached invoice.</p>",
    attachments=[
        {
            "filename": "invoice.pdf",
            "content": pdf_bytes,
            "mime_type": "application/pdf",
        }
    ],
)
```

## Related

- [notifications.md](notifications.md) — Notification service (creates email notifications)
- [operations.md](operations.md) — Monitoring email delivery
