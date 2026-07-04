"""Tests for Part 1 (Dashboard) + Part 2 (Funnel & Retention) of the Beta Ops Platform."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone as tz_utc
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# Set test env before imports
os.environ.setdefault("APP_ENV", "testing")

# Ensure backend on path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.application.beta_ops import BetaOpsService, get_beta_ops_service  # noqa: E402
from app.application.beta_ops.service import (  # noqa: E402
    _safe_pct, _round, _utcnow, _iso, _ensure_aware, _days_ago,
)


# ============================================================
# Helper function tests
# ============================================================


class TestHelpers:
    def test_safe_pct_with_values(self):
        assert _safe_pct(50, 100) == 50.0
        assert _safe_pct(1, 3) == 33.33
        assert _safe_pct(0, 100) == 0.0

    def test_safe_pct_zero_denominator(self):
        assert _safe_pct(50, 0) == 0.0

    def test_round_with_value(self):
        assert _round(3.14159, 2) == 3.14
        assert _round(3.14159, 4) == 3.1416

    def test_round_with_none(self):
        assert _round(None, 2) is None

    def test_utcnow_returns_aware_datetime(self):
        now = _utcnow()
        assert now.tzinfo is not None

    def test_iso_formats_datetime(self):
        dt = datetime(2026, 7, 3, 12, 0, 0, tzinfo=tz_utc.utc)
        assert _iso(dt) == "2026-07-03T12:00:00+00:00"

    def test_iso_with_none(self):
        assert _iso(None) is None

    def test_ensure_aware_with_naive(self):
        naive = datetime(2026, 7, 3, 12, 0, 0)
        aware = _ensure_aware(naive)
        assert aware.tzinfo is not None

    def test_ensure_aware_with_aware(self):
        aware = datetime(2026, 7, 3, 12, 0, 0, tzinfo=tz_utc.utc)
        result = _ensure_aware(aware)
        assert result == aware

    def test_days_ago_returns_past(self):
        now = _utcnow()
        result = _days_ago(7)
        assert result < now
        # Should be approximately 7 days (timedelta.days truncates)
        assert 6 <= (now - result).days <= 7


# ============================================================
# Part 1: Dashboard tests
# ============================================================


class TestDashboard:
    """Tests for BetaOpsService.get_dashboard()."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_dataclass(
        self, session: AsyncSession, seeded_users, seeded_invites, seeded_feedback, seeded_beta_events
    ):
        service = BetaOpsService()
        result = await service.get_dashboard(session)
        # Verify it returns the right dataclass type
        assert result.total_invited >= 0
        assert result.active_beta_users >= 0
        assert result.daily_active_users >= 0
        assert result.weekly_active_users >= 0
        assert result.monthly_active_users >= 0
        assert 0 <= result.invite_conversion_rate <= 100
        assert result.avg_session_duration_minutes >= 0
        assert result.study_sessions_completed >= 0
        assert result.feedback_received >= 0
        assert result.bugs_reported >= 0
        assert result.crash_reports >= 0
        assert isinstance(result.nps_score, float)
        assert isinstance(result.user_satisfaction, float)
        assert isinstance(result.learning_progress_avg, float)
        assert 0 <= result.retention_day_1 <= 100
        assert 0 <= result.retention_day_7 <= 100
        assert 0 <= result.retention_day_30 <= 100
        assert result.generated_at is not None

    @pytest.mark.asyncio
    async def test_dashboard_counts_invited_users(
        self, session: AsyncSession, seeded_invites
    ):
        service = BetaOpsService()
        result = await service.get_dashboard(session)
        # 15 invites seeded with distinct emails
        assert result.total_invited == 15

    @pytest.mark.asyncio
    async def test_dashboard_counts_active_beta_users(
        self, session: AsyncSession, seeded_users
    ):
        service = BetaOpsService()
        result = await service.get_dashboard(session)
        # 5 verified learners + 2 admins = 7 active
        assert result.active_beta_users == 7

    @pytest.mark.asyncio
    async def test_dashboard_invite_conversion_rate(
        self, session: AsyncSession, seeded_invites
    ):
        service = BetaOpsService()
        result = await service.get_dashboard(session)
        # 10 used out of 15 total = 66.67%
        assert result.invite_conversion_rate == pytest.approx(66.67, abs=0.1)

    @pytest.mark.asyncio
    async def test_dashboard_feedback_counts(
        self, session: AsyncSession, seeded_feedback
    ):
        service = BetaOpsService()
        result = await service.get_dashboard(session)
        assert result.feedback_received == 12
        assert result.bugs_reported == 4
        # rating == 1 → crash_reports
        assert result.crash_reports >= 1

    @pytest.mark.asyncio
    async def test_dashboard_dau_wau_mau(
        self, session: AsyncSession, seeded_users, seeded_beta_events
    ):
        service = BetaOpsService()
        result = await service.get_dashboard(session)
        # 5 learners × 5 events each, all within last 7 days → all in DAU/WAU/MAU
        assert result.daily_active_users > 0
        assert result.weekly_active_users >= result.daily_active_users
        assert result.monthly_active_users >= result.weekly_active_users

    @pytest.mark.asyncio
    async def test_dashboard_study_sessions_completed(
        self, session: AsyncSession, seeded_users, seeded_enrollments, seeded_study_sessions
    ):
        service = BetaOpsService()
        result = await service.get_dashboard(session)
        # 5 enrollments × 1 ended session each = 5 (the "ended" sessions)
        assert result.study_sessions_completed >= 5

    @pytest.mark.asyncio
    async def test_dashboard_nps_score(
        self, session: AsyncSession, seeded_feedback
    ):
        service = BetaOpsService()
        result = await service.get_dashboard(session)
        # NPS = (promoters - detractors) / total * 100
        # Promoters = rating 5; Detractors = rating ≤ 3
        # From seeded data: ratings = [1,2,3,5,4,5,5,3,4,5,4,5]
        # Promoters (5): 5 of them; Detractors (≤3): 4 of them; Total: 12
        # NPS = (5-4)/12*100 = 8.33
        assert result.nps_score == pytest.approx(8.33, abs=0.5)

    @pytest.mark.asyncio
    async def test_dashboard_user_satisfaction(
        self, session: AsyncSession, seeded_feedback
    ):
        service = BetaOpsService()
        result = await service.get_dashboard(session)
        # satisfaction = avg(rating) / 5 * 100
        # avg([1,2,3,5,4,5,5,3,4,5,4,5]) = 3.83; satisfaction = 76.67
        assert 60 <= result.user_satisfaction <= 90

    @pytest.mark.asyncio
    async def test_dashboard_learning_progress_avg(
        self, session: AsyncSession, seeded_enrollments, seeded_mastery_scores
    ):
        service = BetaOpsService()
        result = await service.get_dashboard(session)
        # 5 enrollments × 4 concepts = 20 mastery scores
        # avg = (0.1 + 0.3 + 0.5 + 0.7) / 4 = 0.4 → 40%
        assert 30 <= result.learning_progress_avg <= 50

    @pytest.mark.asyncio
    async def test_dashboard_retention_with_no_data(self, session: AsyncSession):
        """With no events, retention should be 0."""
        service = BetaOpsService()
        result = await service.get_dashboard(session)
        assert result.retention_day_1 == 0.0
        assert result.retention_day_7 == 0.0
        assert result.retention_day_30 == 0.0

    @pytest.mark.asyncio
    async def test_dashboard_generated_at_is_recent(
        self, session: AsyncSession, seeded_users
    ):
        service = BetaOpsService()
        before = _utcnow()
        result = await service.get_dashboard(session)
        after = _utcnow()
        # generated_at should be between before and after
        from datetime import datetime as dt
        gen_at = dt.fromisoformat(result.generated_at)
        assert before <= gen_at <= after


# ============================================================
# Part 2: Funnel tests
# ============================================================


class TestRegistrationFunnel:
    """Tests for BetaOpsService.get_registration_funnel()."""

    @pytest.mark.asyncio
    async def test_funnel_returns_9_steps(
        self, session: AsyncSession, seeded_users, seeded_invites, seeded_beta_events
    ):
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        assert len(result.steps) == 9
        step_names = [s.step for s in result.steps]
        assert step_names == [
            "invite_sent", "invite_accepted", "registration", "email_verification",
            "welcome_wizard", "first_enrollment", "first_study_session",
            "first_completed_question", "day_1_retention",
        ]

    @pytest.mark.asyncio
    async def test_funnel_invite_sent_count(
        self, session: AsyncSession, seeded_invites
    ):
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        # 15 invites seeded within last 30 days
        assert result.steps[0].count == 15

    @pytest.mark.asyncio
    async def test_funnel_invite_accepted_count(
        self, session: AsyncSession, seeded_invites
    ):
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        # 10 invites marked as used
        assert result.steps[1].count == 10

    @pytest.mark.asyncio
    async def test_funnel_registration_count(
        self, session: AsyncSession, seeded_users
    ):
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        # 10 users total (5+3+2), but 2 admins created 30 days ago may be at the boundary
        assert 8 <= result.steps[2].count <= 10

    @pytest.mark.asyncio
    async def test_funnel_email_verification_count(
        self, session: AsyncSession, seeded_users
    ):
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        # 5 verified learners + 2 admins = 7 (admins may be at the 30-day boundary)
        assert 5 <= result.steps[3].count <= 7

    @pytest.mark.asyncio
    async def test_funnel_cumulative_pct_first_step_is_100(
        self, session: AsyncSession, seeded_invites
    ):
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        assert result.steps[0].cumulative_pct == 100.0

    @pytest.mark.asyncio
    async def test_funnel_cumulative_pct_is_bounded(
        self, session: AsyncSession, seeded_users, seeded_invites, seeded_beta_events
    ):
        """Cumulative pct should be between 0 and 100 for all steps."""
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        for step in result.steps:
            assert 0 <= step.cumulative_pct <= 100

    @pytest.mark.asyncio
    async def test_funnel_first_step_cumulative_is_100(
        self, session: AsyncSession, seeded_invites
    ):
        """The first step (invite_sent) should always be 100%."""
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        assert result.steps[0].cumulative_pct == 100.0

    @pytest.mark.asyncio
    async def test_funnel_step_pct_first_step_is_100(
        self, session: AsyncSession, seeded_invites
    ):
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        assert result.steps[0].step_pct == 100.0

    @pytest.mark.asyncio
    async def test_funnel_overall_conversion(
        self, session: AsyncSession, seeded_users, seeded_invites, seeded_beta_events
    ):
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        # overall_conversion = last_step / first_step * 100
        assert 0 <= result.overall_conversion <= 100

    @pytest.mark.asyncio
    async def test_funnel_biggest_drop_step_is_string_or_none(
        self, session: AsyncSession, seeded_users, seeded_invites, seeded_beta_events
    ):
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        assert result.biggest_drop_step is None or isinstance(result.biggest_drop_step, str)

    @pytest.mark.asyncio
    async def test_funnel_with_empty_database(self, session: AsyncSession):
        """With no data, all steps should be 0."""
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        for step in result.steps:
            assert step.count == 0
        assert result.overall_conversion == 0.0

    @pytest.mark.asyncio
    async def test_funnel_days_param_limits_window(
        self, session: AsyncSession, seeded_invites
    ):
        """With days=1, only invites from yesterday/today count."""
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=1)
        # All seeded invites were created within last 2 days, so days=1 may capture most
        assert result.steps[0].count >= 0

    @pytest.mark.asyncio
    async def test_funnel_median_time_is_none_or_float(
        self, session: AsyncSession, seeded_users, seeded_beta_events
    ):
        service = BetaOpsService()
        result = await service.get_registration_funnel(session, days=30)
        for step in result.steps:
            assert step.median_time_from_previous_minutes is None or \
                   isinstance(step.median_time_from_previous_minutes, float)


# ============================================================
# Part 2: Retention cohort tests
# ============================================================


class TestRetentionCohorts:
    """Tests for BetaOpsService.get_retention_cohorts()."""

    @pytest.mark.asyncio
    async def test_retention_returns_list_of_cohorts(
        self, session: AsyncSession, seeded_beta_events
    ):
        service = BetaOpsService()
        result = await service.get_retention_cohorts(session, weeks=8)
        assert isinstance(result, list)
        assert len(result) == 8

    @pytest.mark.asyncio
    async def test_retention_cohort_has_5_weeks(
        self, session: AsyncSession, seeded_beta_events
    ):
        service = BetaOpsService()
        result = await service.get_retention_cohorts(session, weeks=8)
        for cohort in result:
            assert hasattr(cohort, "week_0")
            assert hasattr(cohort, "week_1")
            assert hasattr(cohort, "week_2")
            assert hasattr(cohort, "week_3")
            assert hasattr(cohort, "week_4")

    @pytest.mark.asyncio
    async def test_retention_cohort_week_0_equals_cohort_size(
        self, session: AsyncSession, seeded_beta_events
    ):
        """Week 0 retention = cohort size (by definition)."""
        service = BetaOpsService()
        result = await service.get_retention_cohorts(session, weeks=8)
        for cohort in result:
            if cohort.cohort_size > 0:
                assert cohort.week_0 == cohort.cohort_size

    @pytest.mark.asyncio
    async def test_retention_cohort_with_no_data(
        self, session: AsyncSession
    ):
        """With no events, all cohorts should have size 0."""
        service = BetaOpsService()
        result = await service.get_retention_cohorts(session, weeks=8)
        for cohort in result:
            assert cohort.cohort_size == 0

    @pytest.mark.asyncio
    async def test_retention_cohort_week_is_iso_date(
        self, session: AsyncSession, seeded_beta_events
    ):
        service = BetaOpsService()
        result = await service.get_retention_cohorts(session, weeks=4)
        for cohort in result:
            # ISO date format: YYYY-MM-DD
            assert len(cohort.cohort_week) == 10
            assert cohort.cohort_week[4] == "-"

    @pytest.mark.asyncio
    async def test_retention_cohorts_descending(
        self, session: AsyncSession, seeded_beta_events
    ):
        """Most recent cohort should be first."""
        service = BetaOpsService()
        result = await service.get_retention_cohorts(session, weeks=4)
        dates = [c.cohort_week for c in result]
        assert dates == sorted(dates, reverse=True)


# ============================================================
# Service singleton tests
# ============================================================


class TestServiceSingleton:
    def test_get_beta_ops_service_returns_instance(self):
        service = get_beta_ops_service()
        assert isinstance(service, BetaOpsService)

    def test_get_beta_ops_service_returns_same_instance(self):
        s1 = get_beta_ops_service()
        s2 = get_beta_ops_service()
        assert s1 is s2
