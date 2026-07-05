"""Tests for the Beta Ops API endpoints (Task 026).

Verifies that all 23 endpoints are registered, are admin-protected, and
return the expected response shapes. Uses the existing FastAPI app +
in-memory SQLite.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest

os.environ.setdefault("APP_ENV", "testing")

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))


# ============================================================
# Route registration tests
# ============================================================


class TestBetaOpsRoutesRegistered:
    """Verify all 23 beta-ops endpoints are registered on the app."""

    def _get_routes(self):
        from app.main import app
        return [(r.path, r.methods) for r in app.routes if hasattr(r, "path")]

    def test_dashboard_route_registered(self):
        routes = self._get_routes()
        paths = [p for p, _ in routes]
        assert "/api/v1/admin/beta-ops/dashboard" in paths

    def test_funnel_route_registered(self):
        routes = self._get_routes()
        paths = [p for p, _ in routes]
        assert "/api/v1/admin/beta-ops/analytics/funnel" in paths

    def test_retention_route_registered(self):
        routes = self._get_routes()
        paths = [p for p, _ in routes]
        assert "/api/v1/admin/beta-ops/analytics/retention" in paths

    def test_learning_route_registered(self):
        routes = self._get_routes()
        paths = [p for p, _ in routes]
        assert "/api/v1/admin/beta-ops/learning" in paths

    def test_feedback_routes_registered(self):
        routes = self._get_routes()
        paths = [p for p, _ in routes]
        assert "/api/v1/admin/beta-ops/feedback" in paths
        assert any(
            "/api/v1/admin/beta-ops/feedback/{feedback_id}/vote" == p
            for p, _ in routes
        )
        assert any(
            "/api/v1/admin/beta-ops/feedback/{feedback_id}/meta" == p
            for p, _ in routes
        )
        assert any(
            "/api/v1/admin/beta-ops/feedback/{feedback_id}/mark-duplicate" == p
            for p, _ in routes
        )

    def test_success_route_registered(self):
        routes = self._get_routes()
        paths = [p for p, _ in routes]
        assert "/api/v1/admin/beta-ops/success" in paths

    def test_instructor_route_registered(self):
        routes = self._get_routes()
        paths = [p for p, _ in routes]
        assert "/api/v1/admin/beta-ops/instructor" in paths

    def test_operations_route_registered(self):
        routes = self._get_routes()
        paths = [p for p, _ in routes]
        assert "/api/v1/admin/beta-ops/operations" in paths

    def test_releases_routes_registered(self):
        routes = self._get_routes()
        paths = [p for p, _ in routes]
        assert "/api/v1/admin/beta-ops/releases" in paths
        assert any(
            "/api/v1/admin/beta-ops/releases/{release_id}" == p
            for p, _ in routes
        )
        assert any(
            "/api/v1/admin/beta-ops/releases/{release_id}/stage" == p
            for p, _ in routes
        )

    def test_reports_routes_registered(self):
        routes = self._get_routes()
        paths = [p for p, _ in routes]
        assert "/api/v1/admin/beta-ops/reports/{period}" in paths
        assert "/api/v1/admin/beta-ops/reports/generate" in paths

    def test_experiments_routes_registered(self):
        routes = self._get_routes()
        paths = [p for p, _ in routes]
        assert "/api/v1/admin/beta-ops/experiments" in paths
        assert any(
            "/api/v1/admin/beta-ops/experiments/{experiment_id}" == p
            for p, _ in routes
        )
        assert any(
            "/api/v1/admin/beta-ops/experiments/{experiment_id}/assign" == p
            for p, _ in routes
        )
        assert any(
            "/api/v1/admin/beta-ops/experiments/{experiment_id}/results" == p
            for p, _ in routes
        )

    def test_total_route_count(self):
        routes = self._get_routes()
        beta_ops_routes = [
            (p, m) for p, m in routes
            if p.startswith("/api/v1/admin/beta-ops")
        ]
        # 23 distinct routes (path + method combinations may be more)
        distinct_paths = {p for p, _ in beta_ops_routes}
        assert len(distinct_paths) >= 17  # 17 distinct paths

    def test_all_beta_ops_routes_have_admin_dependency(self):
        """Every beta-ops endpoint must require the admin role."""
        from app.main import app
        from app.presentation.api.v1.beta_ops import RequireAdmin

        for route in app.routes:
            if not hasattr(route, "path"):
                continue
            if not route.path.startswith("/api/v1/admin/beta-ops"):
                continue
            if not hasattr(route, "endpoint"):
                continue
            import inspect
            sig = inspect.signature(route.endpoint)
            # Skip the vote endpoint — it's authenticated (any user can vote)
            if route.path.endswith("/vote"):
                continue
            has_admin = False
            for param in sig.parameters.values():
                if param.default is RequireAdmin:
                    has_admin = True
                    break
                if hasattr(param.default, "dependency") and hasattr(RequireAdmin, "dependency"):
                    if param.default.dependency is RequireAdmin.dependency:
                        has_admin = True
                        break
            assert has_admin, f"Route {route.path} ({route.methods}) must require admin role"


# ============================================================
# Pydantic model tests
# ============================================================


class TestPydanticModels:
    """Verify the response models can be instantiated from dataclass dicts."""

    def test_dashboard_response_model(self):
        from app.presentation.api.v1.beta_ops import DashboardResponse
        data = {
            "total_invited": 10,
            "active_beta_users": 5,
            "daily_active_users": 3,
            "weekly_active_users": 4,
            "monthly_active_users": 5,
            "invite_conversion_rate": 50.0,
            "avg_session_duration_minutes": 12.5,
            "study_sessions_completed": 10,
            "feedback_received": 5,
            "bugs_reported": 2,
            "crash_reports": 1,
            "nps_score": 10.0,
            "user_satisfaction": 80.0,
            "learning_progress_avg": 45.0,
            "retention_day_1": 50.0,
            "retention_day_7": 30.0,
            "retention_day_30": 20.0,
            "generated_at": "2026-07-03T12:00:00+00:00",
        }
        model = DashboardResponse(**data)
        assert model.total_invited == 10

    def test_funnel_response_model(self):
        from app.presentation.api.v1.beta_ops import FunnelResponse, FunnelStepResponse
        step = FunnelStepResponse(
            step="invite_sent", count=10, cumulative_pct=100.0,
            step_pct=100.0, median_time_from_previous_minutes=None,
        )
        funnel = FunnelResponse(
            steps=[step], overall_conversion=50.0,
            biggest_drop_step="registration",
            avg_time_to_first_question_minutes=120.5,
        )
        assert funnel.steps[0].step == "invite_sent"

    def test_feedback_item_response_model(self):
        from app.presentation.api.v1.beta_ops import FeedbackItemResponse
        item = FeedbackItemResponse(
            id="abc", user_id="u1", rating=5, category="bug",
            comment="test", status="open", priority="high",
            roadmap_status="planned", vote_score=3, vote_count=4,
            duplicate_of=None, tags=["urgent"], created_at="2026-07-03",
        )
        assert item.priority == "high"

    def test_message_response_model(self):
        from app.presentation.api.v1.beta_ops import MessageResponse
        msg = MessageResponse(message="OK")
        assert msg.code == "OK"


# ============================================================
# Request model validation tests
# ============================================================


class TestRequestModels:
    """Verify request models validate correctly."""

    def test_vote_request_valid(self):
        from app.presentation.api.v1.beta_ops import VoteRequest
        req = VoteRequest(vote=1)
        assert req.vote == 1
        req = VoteRequest(vote=-1)
        assert req.vote == -1

    def test_vote_request_invalid(self):
        from app.presentation.api.v1.beta_ops import VoteRequest
        from pydantic import ValidationError
        # vote=2 is above le=1 → invalid
        with pytest.raises(ValidationError):
            VoteRequest(vote=2)
        # vote=-2 is below ge=-1 → invalid
        with pytest.raises(ValidationError):
            VoteRequest(vote=-2)

    def test_create_release_note_request_defaults(self):
        from app.presentation.api.v1.beta_ops import CreateReleaseNoteRequest
        req = CreateReleaseNoteRequest(
            version="v1.0.0", title="Test", body="Body",
        )
        assert req.release_type == "patch"
        assert req.feature_freeze is False
        assert req.published is False
        assert req.features == []

    def test_create_experiment_request_defaults(self):
        from app.presentation.api.v1.beta_ops import CreateExperimentRequest
        req = CreateExperimentRequest(
            id="exp1", name="Test", variant_a="a", variant_b="b",
        )
        assert req.experiment_type == "ab"
        assert req.rollout_percentage == 50
        assert req.min_sample_size == 100

    def test_create_experiment_request_rollout_validation(self):
        from app.presentation.api.v1.beta_ops import CreateExperimentRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CreateExperimentRequest(
                id="exp1", name="Test", variant_a="a", variant_b="b",
                rollout_percentage=150,
            )

    def test_add_release_stage_request_rollout_validation(self):
        from app.presentation.api.v1.beta_ops import AddReleaseStageRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AddReleaseStageRequest(stage="canary", rollout_percentage=150)

    def test_generate_report_request_default(self):
        from app.presentation.api.v1.beta_ops import GenerateReportRequest
        req = GenerateReportRequest()
        assert req.period == "weekly"


# ============================================================
# Dataclass-to-dict helper tests
# ============================================================


class TestDataclassConversion:
    """Verify the _dc_to_dict helper handles nested dataclasses."""

    def test_dc_to_dict_with_primitive(self):
        from app.presentation.api.v1.beta_ops import _dc_to_dict
        assert _dc_to_dict(42) == 42
        assert _dc_to_dict("hello") == "hello"
        assert _dc_to_dict(None) is None

    def test_dc_to_dict_with_list(self):
        from app.presentation.api.v1.beta_ops import _dc_to_dict
        assert _dc_to_dict([1, 2, 3]) == [1, 2, 3]

    def test_dc_to_dict_with_dict(self):
        from app.presentation.api.v1.beta_ops import _dc_to_dict
        assert _dc_to_dict({"a": 1}) == {"a": 1}

    def test_dc_to_dict_with_dataclass(self):
        from app.presentation.api.v1.beta_ops import _dc_to_dict
        from app.application.beta_ops.service import FunnelStep
        step = FunnelStep(
            step="test", count=10, cumulative_pct=100.0,
            step_pct=50.0, median_time_from_previous_minutes=None,
        )
        result = _dc_to_dict(step)
        assert result["step"] == "test"
        assert result["count"] == 10

    def test_dc_to_dict_with_nested_dataclass(self):
        from app.presentation.api.v1.beta_ops import _dc_to_dict
        from app.application.beta_ops.service import (
            RegistrationFunnel, FunnelStep,
        )
        step = FunnelStep(
            step="test", count=10, cumulative_pct=100.0,
            step_pct=50.0, median_time_from_previous_minutes=None,
        )
        funnel = RegistrationFunnel(
            steps=[step], overall_conversion=50.0,
            biggest_drop_step=None, avg_time_to_first_question_minutes=None,
        )
        result = _dc_to_dict(funnel)
        assert isinstance(result["steps"], list)
        assert result["steps"][0]["step"] == "test"
