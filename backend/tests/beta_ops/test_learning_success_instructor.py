"""Tests for Parts 3 (Learning) + 5 (User Success) + 6 (Instructor) of the Beta Ops Platform."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone as tz_utc
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("APP_ENV", "testing")

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.application.beta_ops import BetaOpsService  # noqa: E402
from app.infrastructure.database.orm.beta import BetaEventModel  # noqa: E402
from app.infrastructure.database.orm.identity import UserModel  # noqa: E402


# ============================================================
# Part 3: Learning Effectiveness
# ============================================================


class TestLearningEffectiveness:
    """Tests for BetaOpsService.get_learning_effectiveness()."""

    @pytest.mark.asyncio
    async def test_learning_returns_dataclass(
        self, session: AsyncSession, seeded_enrollments, seeded_mastery_scores,
        seeded_attempts, seeded_beta_events,
    ):
        service = BetaOpsService()
        result = await service.get_learning_effectiveness(session)
        assert result.mastery_growth_avg >= 0
        assert result.time_to_mastery_hours is None or isinstance(result.time_to_mastery_hours, float)
        assert isinstance(result.weak_concepts, list)
        assert isinstance(result.strong_concepts, list)
        assert 0 <= result.review_effectiveness <= 100
        assert 0 <= result.question_accuracy <= 100
        assert isinstance(result.average_confidence, float)
        assert 0 <= result.hint_usage_rate <= 100
        assert 0 <= result.recommendation_acceptance <= 100
        assert 0 <= result.adaptive_queue_quality <= 100
        assert isinstance(result.interview_readiness_trend, list)

    @pytest.mark.asyncio
    async def test_learning_question_accuracy(
        self, session: AsyncSession, seeded_enrollments, seeded_attempts,
    ):
        service = BetaOpsService()
        result = await service.get_learning_effectiveness(session)
        # 12 correct + 6 incorrect + 2 partial = 20 total
        # accuracy = 12/20 = 60%
        assert result.question_accuracy == 60.0

    @pytest.mark.asyncio
    async def test_learning_hint_usage_rate(
        self, session: AsyncSession, seeded_enrollments, seeded_attempts,
    ):
        service = BetaOpsService()
        result = await service.get_learning_effectiveness(session)
        # 20 attempts, every 3rd (i % 3 == 0) has hint_used = True
        # i = 0, 3, 6, 9, 12, 15, 18 → 7 hints
        # rate = 7/20 = 35%
        assert 30 <= result.hint_usage_rate <= 40

    @pytest.mark.asyncio
    async def test_learning_recommendation_acceptance(
        self, session: AsyncSession, seeded_beta_events,
    ):
        service = BetaOpsService()
        result = await service.get_learning_effectiveness(session)
        # beta_events has recommendation_offered and recommendation_accepted
        # Per user: 1 offered + 1 accepted (5 each total)
        # acceptance = 5/5 = 100%
        assert result.recommendation_acceptance == 100.0

    @pytest.mark.asyncio
    async def test_learning_weak_concepts_sorted_ascending(
        self, session: AsyncSession, seeded_enrollments, seeded_mastery_scores,
    ):
        service = BetaOpsService()
        result = await service.get_learning_effectiveness(session)
        if len(result.weak_concepts) > 1:
            scores = [c["avg_mastery"] for c in result.weak_concepts]
            assert scores == sorted(scores)

    @pytest.mark.asyncio
    async def test_learning_strong_concepts_sorted_descending(
        self, session: AsyncSession, seeded_enrollments, seeded_mastery_scores,
    ):
        service = BetaOpsService()
        result = await service.get_learning_effectiveness(session)
        if len(result.strong_concepts) > 1:
            scores = [c["avg_mastery"] for c in result.strong_concepts]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_learning_weak_concepts_have_lower_mastery_than_strong(
        self, session: AsyncSession, seeded_enrollments, seeded_mastery_scores,
    ):
        service = BetaOpsService()
        result = await service.get_learning_effectiveness(session)
        if result.weak_concepts and result.strong_concepts:
            assert result.weak_concepts[0]["avg_mastery"] <= result.strong_concepts[0]["avg_mastery"]

    @pytest.mark.asyncio
    async def test_learning_interview_readiness_trend_entries(
        self, session: AsyncSession, seeded_enrollments, seeded_mastery_scores,
    ):
        service = BetaOpsService()
        result = await service.get_learning_effectiveness(session)
        for entry in result.interview_readiness_trend:
            assert "week" in entry
            assert "avg_readiness" in entry
            assert 0 <= entry["avg_readiness"] <= 100

    @pytest.mark.asyncio
    async def test_learning_with_no_data(
        self, session: AsyncSession,
    ):
        service = BetaOpsService()
        result = await service.get_learning_effectiveness(session)
        assert result.mastery_growth_avg == 0.0
        assert result.question_accuracy == 0.0
        assert result.hint_usage_rate == 0.0
        assert result.recommendation_acceptance == 0.0
        assert result.adaptive_queue_quality == 0.0
        assert result.weak_concepts == []
        assert result.strong_concepts == []

    @pytest.mark.asyncio
    async def test_learning_mastery_growth_avg_nonnegative(
        self, session: AsyncSession, seeded_enrollments, seeded_mastery_scores,
    ):
        service = BetaOpsService()
        result = await service.get_learning_effectiveness(session)
        assert result.mastery_growth_avg >= 0


# ============================================================
# Part 5: User Success Center
# ============================================================


class TestUserSuccess:
    """Tests for BetaOpsService.get_user_success_report()."""

    @pytest.mark.asyncio
    async def test_user_success_returns_dataclass(
        self, session: AsyncSession, seeded_users, seeded_beta_events,
    ):
        service = BetaOpsService()
        result = await service.get_user_success_report(session)
        assert hasattr(result, "inactive_users")
        assert hasattr(result, "at_risk_users")
        assert hasattr(result, "incomplete_onboarding")
        assert hasattr(result, "stuck_in_learning")
        assert hasattr(result, "no_study_7_days")
        assert hasattr(result, "failed_registration")
        assert hasattr(result, "email_verification_pending")
        assert hasattr(result, "recommendation_ignored")
        assert hasattr(result, "summary")

    @pytest.mark.asyncio
    async def test_user_success_summary_has_counts(
        self, session: AsyncSession, seeded_users, seeded_beta_events,
    ):
        service = BetaOpsService()
        result = await service.get_user_success_report(session)
        assert "total_users" in result.summary
        assert "inactive" in result.summary
        assert "at_risk" in result.summary
        assert "incomplete_onboarding" in result.summary
        assert "stuck_in_learning" in result.summary
        assert "no_study_7_days" in result.summary
        assert "email_verification_pending" in result.summary
        assert "recommendation_ignored" in result.summary

    @pytest.mark.asyncio
    async def test_user_success_email_verification_pending(
        self, session: AsyncSession, seeded_users,
    ):
        service = BetaOpsService()
        result = await service.get_user_success_report(session)
        # 3 unverified users seeded
        assert result.summary["email_verification_pending"] == 3

    @pytest.mark.asyncio
    async def test_user_success_signal_has_required_fields(
        self, session: AsyncSession, seeded_users, seeded_beta_events,
    ):
        service = BetaOpsService()
        result = await service.get_user_success_report(session)
        all_signals = (
            result.inactive_users + result.at_risk_users +
            result.incomplete_onboarding + result.stuck_in_learning +
            result.no_study_7_days + result.email_verification_pending +
            result.recommendation_ignored
        )
        for signal in all_signals:
            assert signal.user_id
            assert signal.email
            assert signal.signal_type
            assert signal.severity in ("low", "medium", "high")
            assert signal.description
            assert signal.recommendation

    @pytest.mark.asyncio
    async def test_user_success_no_study_7_days_includes_users_without_sessions(
        self, session: AsyncSession, seeded_users,
    ):
        """Users who never started a study session should appear in no_study_7_days."""
        service = BetaOpsService()
        result = await service.get_user_success_report(session)
        # All 5 learners + 3 unverified have no study sessions
        # (only enrollments were seeded, no study sessions linked to them via user_id lookup)
        assert result.summary["no_study_7_days"] >= 5

    @pytest.mark.asyncio
    async def test_user_success_with_no_users(self, session: AsyncSession):
        service = BetaOpsService()
        result = await service.get_user_success_report(session)
        assert result.summary["total_users"] == 0
        assert result.inactive_users == []
        assert result.at_risk_users == []

    @pytest.mark.asyncio
    async def test_user_success_severity_is_valid(
        self, session: AsyncSession, seeded_users, seeded_beta_events,
    ):
        service = BetaOpsService()
        result = await service.get_user_success_report(session)
        all_signals = (
            result.inactive_users + result.at_risk_users +
            result.incomplete_onboarding + result.stuck_in_learning +
            result.no_study_7_days + result.email_verification_pending +
            result.recommendation_ignored
        )
        for signal in all_signals:
            assert signal.severity in ("low", "medium", "high")

    @pytest.mark.asyncio
    async def test_user_success_recommendation_is_actionable(
        self, session: AsyncSession, seeded_users, seeded_beta_events,
    ):
        """Every signal should have a non-empty recommendation."""
        service = BetaOpsService()
        result = await service.get_user_success_report(session)
        all_signals = (
            result.inactive_users + result.at_risk_users +
            result.incomplete_onboarding + result.stuck_in_learning +
            result.no_study_7_days + result.email_verification_pending +
            result.recommendation_ignored
        )
        for signal in all_signals:
            assert len(signal.recommendation) > 10  # non-trivial recommendation

    @pytest.mark.asyncio
    async def test_user_success_signal_types_are_distinct(
        self, session: AsyncSession, seeded_users, seeded_beta_events,
    ):
        """Each signal list should contain only its designated signal_type."""
        service = BetaOpsService()
        result = await service.get_user_success_report(session)
        for signal in result.inactive_users:
            assert signal.signal_type == "inactive"
        for signal in result.at_risk_users:
            assert signal.signal_type == "at_risk"
        for signal in result.incomplete_onboarding:
            assert signal.signal_type == "incomplete_onboarding"
        for signal in result.stuck_in_learning:
            assert signal.signal_type == "stuck_in_learning"
        for signal in result.no_study_7_days:
            assert signal.signal_type == "no_study_7_days"
        for signal in result.email_verification_pending:
            assert signal.signal_type == "email_verification_pending"
        for signal in result.recommendation_ignored:
            assert signal.signal_type == "recommendation_ignored"


# ============================================================
# Part 6: Instructor Analytics
# ============================================================


class TestInstructorAnalytics:
    """Tests for BetaOpsService.get_instructor_analytics()."""

    @pytest.mark.asyncio
    async def test_instructor_returns_dataclass(
        self, session: AsyncSession, seeded_enrollments, seeded_attempts,
        seeded_mastery_scores, seeded_feedback,
    ):
        service = BetaOpsService()
        result = await service.get_instructor_analytics(session)
        assert hasattr(result, "content_quality")
        assert hasattr(result, "concept_coverage")
        assert hasattr(result, "question_quality")
        assert hasattr(result, "template_usage")
        assert hasattr(result, "difficulty_balance")
        assert hasattr(result, "poor_performing_concepts")
        assert hasattr(result, "frequently_missed_questions")
        assert hasattr(result, "misconceptions")
        assert hasattr(result, "explanation_usefulness")

    @pytest.mark.asyncio
    async def test_instructor_content_quality_has_feedback_count(
        self, session: AsyncSession, seeded_feedback,
    ):
        service = BetaOpsService()
        result = await service.get_instructor_analytics(session)
        assert "feedback_count" in result.content_quality
        assert "avg_rating" in result.content_quality
        # 2 content-category feedback items seeded
        assert result.content_quality["feedback_count"] == 2

    @pytest.mark.asyncio
    async def test_instructor_template_usage_has_accuracy(
        self, session: AsyncSession, seeded_attempts,
    ):
        service = BetaOpsService()
        result = await service.get_instructor_analytics(session)
        for item in result.template_usage:
            assert "template_version_id" in item
            assert "attempts" in item
            assert "correct" in item
            assert "accuracy" in item
            assert 0 <= item["accuracy"] <= 100
            assert "avg_time_ms" in item

    @pytest.mark.asyncio
    async def test_instructor_difficulty_balance_sums_correctly(
        self, session: AsyncSession, seeded_enrollments, seeded_mastery_scores,
    ):
        service = BetaOpsService()
        result = await self._call_analytics(session)
        # 5 enrollments × 4 concepts = 20 mastery scores
        # States: unseen, novice, developing, proficient (5 each)
        assert sum(result.difficulty_balance.values()) == 20

    async def _call_analytics(self, session):
        service = BetaOpsService()
        return await service.get_instructor_analytics(session)

    @pytest.mark.asyncio
    async def test_instructor_misconceptions_have_count(
        self, session: AsyncSession, seeded_attempts,
    ):
        service = BetaOpsService()
        result = await service.get_instructor_analytics(session)
        for item in result.misconceptions:
            assert "misconception_id" in item
            assert "occurrences" in item
            assert item["occurrences"] > 0

    @pytest.mark.asyncio
    async def test_instructor_poor_concepts_below_threshold(
        self, session: AsyncSession, seeded_enrollments, seeded_mastery_scores,
    ):
        service = BetaOpsService()
        result = await service.get_instructor_analytics(session)
        for item in result.poor_performing_concepts:
            assert item["avg_mastery"] < 0.4

    @pytest.mark.asyncio
    async def test_instructor_with_no_data(
        self, session: AsyncSession,
    ):
        service = BetaOpsService()
        result = await service.get_instructor_analytics(session)
        assert result.content_quality["feedback_count"] == 0
        assert result.template_usage == []
        assert result.misconceptions == []
        assert result.poor_performing_concepts == []

    @pytest.mark.asyncio
    async def test_instructor_concept_coverage_structure(
        self, session: AsyncSession, seeded_enrollments, seeded_mastery_scores,
    ):
        service = BetaOpsService()
        result = await service.get_instructor_analytics(session)
        assert "subjects" in result.concept_coverage
        assert isinstance(result.concept_coverage["subjects"], list)

    @pytest.mark.asyncio
    async def test_instructor_question_quality_avg_accuracy(
        self, session: AsyncSession, seeded_attempts,
    ):
        service = BetaOpsService()
        result = await service.get_instructor_analytics(session)
        assert "templates_analyzed" in result.question_quality
        assert "avg_accuracy_across_templates" in result.question_quality
        assert result.question_quality["templates_analyzed"] > 0
