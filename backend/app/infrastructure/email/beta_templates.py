"""Beta email templates — invitation, welcome, reminder.

These templates are used by the EmailService (from Task 017).
"""

from __future__ import annotations

from app.infrastructure.email.service import EmailTemplate


class BetaInvitationEmailTemplate(EmailTemplate):
    name = "beta_invitation"
    subject = "You're invited to the Mastery Engine Closed Beta! 🎉"
    category = "system"

    def render_html(self, context: dict[str, str]) -> str:
        from html import escape
        register_url = escape(context.get("register_url", ""))
        email = escape(context.get("email", ""))
        expiry = escape(context.get("expires_at", ""))
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>🎉 You're invited to the Mastery Engine Closed Beta!</h2>
  <p>You've been invited to join the closed beta of <strong>Mastery Engine</strong> — an adaptive learning platform for Python interview preparation.</p>
  <p>To accept your invitation and create your account, click the button below:</p>
  <p>
    <a href="{register_url}"
       style="background-color: #4F46E5; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 4px; display: inline-block;">
      Accept Invitation
    </a>
  </p>
  <p>Or copy this link into your browser:</p>
  <p><a href="{register_url}">{register_url}</a></p>
  <p>This invitation is for <strong>{email}</strong> and expires on <strong>{expiry}</strong>.</p>
  <p style="color: #6B7280; font-size: 12px; margin-top: 32px;">
    If you weren't expecting this invitation, you can safely ignore this email.
  </p>
</body>
</html>"""

    def render_text(self, context: dict[str, str]) -> str:
        register_url = context.get("register_url", "")
        email = context.get("email", "")
        expiry = context.get("expires_at", "")
        return f"""\
You're invited to the Mastery Engine Closed Beta!

You've been invited to join the closed beta of Mastery Engine — an adaptive learning platform for Python interview preparation.

To accept your invitation and create your account, visit:

{register_url}

This invitation is for {email} and expires on {expiry}.

If you weren't expecting this invitation, you can safely ignore this email.
"""


class BetaWelcomeEmailTemplate(EmailTemplate):
    name = "beta_welcome"
    subject = "Welcome to the Mastery Engine Beta! 🚀"
    category = "system"

    def render_html(self, context: dict[str, str]) -> str:
        from html import escape
        name = escape(context.get("display_name", "there"))
        login_url = escape(context.get("login_url", "https://app.masteryengine.com/login"))
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>Welcome to the Beta, {name}! 🚀</h2>
  <p>Your account is ready. Here's what you can do next:</p>
  <ul>
    <li>Complete your profile and set a learning goal</li>
    <li>Browse available subjects and enroll</li>
    <li>Start your first study session</li>
    <li>Track your mastery progress</li>
  </ul>
  <p>As a beta tester, your feedback shapes the platform. Use the feedback button (bottom-right) to report bugs, suggest features, or share your experience.</p>
  <p>
    <a href="{login_url}"
       style="background-color: #4F46E5; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 4px; display: inline-block;">
      Get Started
    </a>
  </p>
  <p>Thank you for helping us build the future of learning!</p>
  <p>— The Mastery Engine Team</p>
</body>
</html>"""

    def render_text(self, context: dict[str, str]) -> str:
        name = context.get("display_name", "there")
        login_url = context.get("login_url", "https://app.masteryengine.com/login")
        return f"""\
Welcome to the Beta, {name}!

Your account is ready. Here's what you can do next:
- Complete your profile and set a learning goal
- Browse available subjects and enroll
- Start your first study session
- Track your mastery progress

As a beta tester, your feedback shapes the platform. Use the feedback button to report bugs, suggest features, or share your experience.

Get started: {login_url}

Thank you for helping us build the future of learning!

— The Mastery Engine Team
"""


class BetaReminderEmailTemplate(EmailTemplate):
    name = "beta_reminder"
    subject = "We miss you at Mastery Engine Beta 💙"
    category = "system"

    def render_html(self, context: dict[str, str]) -> str:
        from html import escape
        name = escape(context.get("display_name", "there"))
        login_url = escape(context.get("login_url", "https://app.masteryengine.com/login"))
        days_inactive = context.get("days_inactive", "a few")
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>We miss you, {name}! 💙</h2>
  <p>It's been {days_inactive} days since you last visited Mastery Engine.</p>
  <p>Your learning streak may have ended, but it's not too late to pick up where you left off! Here's what's waiting for you:</p>
  <ul>
    <li>Due reviews that need your attention</li>
    <li>New concepts to master</li>
    <li>Your personalized study plan</li>
  </ul>
  <p>
    <a href="{login_url}"
       style="background-color: #4F46E5; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 4px; display: inline-block;">
      Continue Learning
    </a>
  </p>
  <p style="color: #6B7280; font-size: 12px;">
    You're receiving this because you're a valued beta tester. Thank you for your participation!
  </p>
</body>
</html>"""

    def render_text(self, context: dict[str, str]) -> str:
        name = context.get("display_name", "there")
        login_url = context.get("login_url", "https://app.masteryengine.com/login")
        days_inactive = context.get("days_inactive", "a few")
        return f"""\
We miss you, {name}!

It's been {days_inactive} days since you last visited Mastery Engine.

Your learning streak may have ended, but it's not too late to pick up where you left off!

Continue learning: {login_url}

You're receiving this because you're a valued beta tester. Thank you for your participation!
"""


# Register templates
from app.infrastructure.email.service import TEMPLATES
TEMPLATES["beta_invitation"] = BetaInvitationEmailTemplate()
TEMPLATES["beta_welcome"] = BetaWelcomeEmailTemplate()
TEMPLATES["beta_reminder"] = BetaReminderEmailTemplate()


__all__ = [
    "BetaInvitationEmailTemplate",
    "BetaWelcomeEmailTemplate",
    "BetaReminderEmailTemplate",
]
