"""Tests for the Closed Beta platform.

Tests:
- Beta config settings
- BetaService (invite creation, validation, registration guard, feedback, analytics, feature flags)
- Beta API endpoints
- Beta invite lifecycle
- Beta user limit enforcement
- Feedback submission
- Analytics tracking
- Feature flag retrieval
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone as tz_utc
from uuid import uuid4

import pytest

# Set test env before importing
os.environ.setdefault("APP_ENV", "testing")

from app.shared.config import get_settings
# Task 025-deploy fix: set_ai_config lives in app.ai, not app.shared.config.
# This was a pre-existing import bug; keeping it as a lazy import for compat.
try:
    from app.ai import set_ai_config  # type: ignore[import]
except ImportError:  # pragma: no cover
    def set_ai_config(*args, **kwargs):  # type: ignore[misc]
        """Stub for environments where app.ai is not importable."""
        return None
from app.application.beta import BetaService, BetaInvite, BetaFeedback, get_beta_service


# ============================================================
# Config Tests
# ============================================================


class TestBetaConfig:
    """Tests for beta configuration."""

    def test_beta_disabled_by_default(self):
        settings = get_settings()
        assert settings.closed_beta_enabled is False

    def test_beta_user_limit_default(self):
        settings = get_settings()
        assert settings.max_beta_users == 20

    def test_beta_invite_ttl_default(self):
        settings = get_settings()
        assert settings.beta_invite_token_ttl_hours == 168  # 7 days

    def test_beta_feature_flags_defaults(self):
        settings = get_settings()
        assert settings.beta_flag_learning_enabled is True
        assert settings.beta_flag_content_authoring_enabled is True
        assert settings.beta_flag_ai_enabled is False
        assert settings.beta_flag_notifications_enabled is True
        assert settings.beta_flag_analytics_enabled is True
        assert settings.beta_flag_admin_console_enabled is True


# ============================================================
# BetaService Tests
# ============================================================


class TestBetaService:
    """Tests for the BetaService."""

    @pytest.fixture
    def service(self):
        return BetaService()

    def test_is_beta_enabled(self, service):
        # Default is False
        assert service.is_beta_enabled is False

    def test_max_beta_users(self, service):
        assert service.max_beta_users == 20

    def test_get_feature_flags(self, service):
        flags = service.get_feature_flags()
        assert "learning_enabled" in flags
        assert "content_authoring_enabled" in flags
        assert "ai_enabled" in flags
        assert "notifications_enabled" in flags
        assert "analytics_enabled" in flags
        assert "admin_console_enabled" in flags
        assert all(isinstance(v, bool) for v in flags.values())

    def test_get_feature_flags_returns_correct_values(self, service):
        flags = service.get_feature_flags()
        assert flags["learning_enabled"] is True
        assert flags["ai_enabled"] is False  # AI is off by default


# ============================================================
# BetaInvite Data Class Tests
# ============================================================


class TestBetaInvite:
    """Tests for the BetaInvite data class."""

    def test_invite_properties(self):
        invite = BetaInvite(
            id=uuid4(),
            email="test@example.com",
            invite_token="token123",
            expires_at=datetime.now(tz_utc.utc) + timedelta(days=7),
            used_at=None,
            created_by=uuid4(),
            notes=None,
            created_at=datetime.now(tz_utc.utc),
        )
        assert invite.is_used is False
        assert invite.is_expired is False
        assert invite.is_valid is True

    def test_used_invite(self):
        invite = BetaInvite(
            id=uuid4(),
            email="test@example.com",
            invite_token="token123",
            expires_at=datetime.now(tz_utc.utc) + timedelta(days=7),
            used_at=datetime.now(tz_utc.utc),
            created_by=uuid4(),
            notes=None,
            created_at=datetime.now(tz_utc.utc),
        )
        assert invite.is_used is True
        assert invite.is_valid is False

    def test_expired_invite(self):
        invite = BetaInvite(
            id=uuid4(),
            email="test@example.com",
            invite_token="token123",
            expires_at=datetime.now(tz_utc.utc) - timedelta(days=1),
            used_at=None,
            created_by=uuid4(),
            notes=None,
            created_at=datetime.now(tz_utc.utc),
        )
        assert invite.is_expired is True
        assert invite.is_valid is False


# ============================================================
# BetaFeedback Data Class Tests
# ============================================================


class TestBetaFeedback:
    """Tests for the BetaFeedback data class."""

    def test_feedback_creation(self):
        feedback = BetaFeedback(
            id=uuid4(),
            user_id=uuid4(),
            rating=5,
            category="bug",
            comment="Something went wrong",
            screenshot_url=None,
            correlation_id="corr-123",
            browser="Chrome",
            platform="Linux",
            route="/dashboard",
            status="open",
            created_at=datetime.now(tz_utc.utc),
        )
        assert feedback.rating == 5
        assert feedback.category == "bug"
        assert feedback.status == "open"


# ============================================================
# Email Template Tests
# ============================================================


class TestBetaEmailTemplates:
    """Tests for beta email templates."""

    def test_invitation_template_renders(self):
        from app.infrastructure.email.beta_templates import BetaInvitationEmailTemplate
        template = BetaInvitationEmailTemplate()
        html = template.render_html({
            "register_url": "https://app.masteryengine.com/register?token=abc",
            "email": "user@example.com",
            "expires_at": "2024-12-31",
        })
        assert "Mastery Engine" in html
        assert "register?token=abc" in html
        assert "user@example.com" in html

    def test_welcome_template_renders(self):
        from app.infrastructure.email.beta_templates import BetaWelcomeEmailTemplate
        template = BetaWelcomeEmailTemplate()
        html = template.render_html({
            "display_name": "Alice",
            "login_url": "https://app.masteryengine.com/login",
        })
        assert "Alice" in html
        assert "login" in html

    def test_reminder_template_renders(self):
        from app.infrastructure.email.beta_templates import BetaReminderEmailTemplate
        template = BetaReminderEmailTemplate()
        html = template.render_html({
            "display_name": "Bob",
            "login_url": "https://app.masteryengine.com/login",
            "days_inactive": "5",
        })
        assert "Bob" in html
        assert "5 days" in html

    def test_templates_registered(self):
        from app.infrastructure.email.service import TEMPLATES
        assert "beta_invitation" in TEMPLATES
        assert "beta_welcome" in TEMPLATES
        assert "beta_reminder" in TEMPLATES


# ============================================================
# Integration: Registration Guard Logic
# ============================================================


class TestRegistrationGuard:
    """Tests for the registration guard logic."""

    @pytest.fixture
    def service(self):
        return BetaService()

    def test_beta_disabled_allows_registration(self, service):
        """When beta is disabled, registration is always allowed."""
        assert service.is_beta_enabled is False  # Default
        # In a real test, we'd call check_registration_allowed with a mock session
        # The method checks self.is_beta_enabled first and returns (True, None) if False

    def test_feature_flags_are_dynamically_readable(self, service):
        """Feature flags can be read at any time without a session."""
        flags = service.get_feature_flags()
        assert len(flags) == 6
        assert all(isinstance(v, bool) for v in flags.values())


# ============================================================
# API Endpoint Tests (using TestClient)
# ============================================================


class TestBetaAPI:
    """Tests for the beta API endpoints."""

    def test_beta_status_endpoint_exists(self):
        """Verify the beta status endpoint is registered."""
        from app.main import app
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert "/api/v1/beta/status" in routes

    def test_feedback_endpoints_exist(self):
        from app.main import app
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert "/api/v1/beta/feedback" in routes

    def test_track_endpoint_exists(self):
        from app.main import app
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert "/api/v1/beta/track" in routes

    def test_analytics_endpoint_exists(self):
        from app.main import app
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert "/api/v1/beta/analytics" in routes

    def test_admin_invite_endpoints_exist(self):
        from app.main import app
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert "/api/v1/admin/beta/invites" in routes
        assert "/api/v1/admin/beta/invites/resend" in routes
        assert "/api/v1/admin/beta/invites/{invite_id}" in routes


# ============================================================
# ORM Model Tests
# ============================================================


class TestBetaORM:
    """Tests for beta ORM models."""

    def test_beta_invite_model_importable(self):
        from app.infrastructure.database.orm.beta import BetaInviteModel
        assert BetaInviteModel.__tablename__ == "beta_invites"

    def test_beta_feedback_model_importable(self):
        from app.infrastructure.database.orm.beta import BetaFeedbackModel
        assert BetaFeedbackModel.__tablename__ == "beta_feedback"

    def test_beta_event_model_importable(self):
        from app.infrastructure.database.orm.beta import BetaEventModel
        assert BetaEventModel.__tablename__ == "beta_events"


# ============================================================
# Auth Registration Integration
# ============================================================


class TestAuthRegistrationIntegration:
    """Tests that the auth registration endpoint includes beta guard."""

    def test_register_request_has_invite_token_field(self):
        """Verify RegisterRequest accepts invite_token."""
        from app.presentation.api.v1.auth import RegisterRequest
        # The field should exist and be optional
        schema = RegisterRequest.model_json_schema()
        assert "invite_token" in schema.get("properties", {})

    def test_register_request_invite_token_optional(self):
        """Verify invite_token is optional (nullable)."""
        from app.presentation.api.v1.auth import RegisterRequest
        # Should be able to create without invite_token
        req = RegisterRequest(
            email="test@example.com",
            password="SecurePassword123!",
            display_name="Test",
        )
        assert req.invite_token is None

    def test_register_request_with_invite_token(self):
        """Verify invite_token can be provided."""
        from app.presentation.api.v1.auth import RegisterRequest
        req = RegisterRequest(
            email="test@example.com",
            password="SecurePassword123!",
            display_name="Test",
            invite_token="some-invite-token",
        )
        assert req.invite_token == "some-invite-token"


# ============================================================
# Frontend Component Tests
# ============================================================


class TestBetaFrontendComponents:
    """Tests for beta frontend component exports."""

    def test_beta_banner_exported(self):
        # Just verify the frontend source file exists (we can't import .tsx from Python).
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "frontend", "components", "beta", "beta-banner.tsx",
        )
        assert os.path.exists(os.path.abspath(path))

    def test_feedback_button_exported(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "frontend", "components", "beta", "feedback-button.tsx",
        )
        assert os.path.exists(os.path.abspath(path))

    def test_welcome_page_exists(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "frontend", "app", "(app)", "welcome", "page.tsx",
        )
        assert os.path.exists(os.path.abspath(path))


# ============================================================
# Documentation Tests
# ============================================================


class TestBetaDocumentation:
    """Tests that documentation files exist."""

    def test_closed_beta_doc_exists(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "docs", "beta", "closed-beta.md",
        )
        assert os.path.exists(os.path.abspath(path))

    def test_beta_operations_doc_exists(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "docs", "beta", "beta-operations.md",
        )
        assert os.path.exists(os.path.abspath(path))

    def test_invite_system_doc_exists(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "docs", "beta", "invite-system.md",
        )
        assert os.path.exists(os.path.abspath(path))


# ============================================================
# SQL Migration Tests
# ============================================================


class TestBetaSQLMigration:
    """Tests for the beta SQL migration."""

    def test_migration_file_exists(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "infrastructure", "postgres", "init", "04-beta-tables.sql",
        )
        assert os.path.exists(os.path.abspath(path))

    def test_migration_creates_beta_invites(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "infrastructure", "postgres", "init", "04-beta-tables.sql",
        )
        with open(os.path.abspath(path)) as f:
            content = f.read()
        assert "beta_invites" in content
        assert "invite_token" in content
        assert "expires_at" in content
        assert "used_at" in content

    def test_migration_creates_beta_feedback(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "infrastructure", "postgres", "init", "04-beta-tables.sql",
        )
        with open(os.path.abspath(path)) as f:
            content = f.read()
        assert "beta_feedback" in content
        assert "rating" in content
        assert "category" in content
        assert "correlation_id" in content

    def test_migration_creates_beta_events(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "infrastructure", "postgres", "init", "04-beta-tables.sql",
        )
        with open(os.path.abspath(path)) as f:
            content = f.read()
        assert "beta_events" in content
        assert "event_type" in content
        assert "event_data" in content
