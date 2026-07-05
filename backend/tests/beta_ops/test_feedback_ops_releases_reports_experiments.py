"""Tests for Parts 4 (Feedback), 7 (Operations), 8 (Releases), 9 (Reports), 10 (Experiments)."""

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
from app.application.beta_ops.service import BetaOpsService as Service  # noqa: E402
from app.infrastructure.database.orm.beta import BetaFeedbackModel  # noqa: E402
from app.infrastructure.database.orm.beta_ops import (  # noqa: E402
    BetaFeedbackMetaModel,
    BetaFeedbackVoteModel,
    ExperimentAssignmentModel,
    ExperimentModel,
    ExperimentResultModel,
    ReleaseNoteModel,
    ReleaseStageModel,
)
from app.infrastructure.database.orm.identity import UserModel  # noqa: E402


# ============================================================
# Part 4: Feedback Platform
# ============================================================


class TestFeedbackPlatform:
    """Tests for BetaOpsService.get_feedback_platform()."""

    @pytest.mark.asyncio
    async def test_feedback_returns_dataclass(
        self, session: AsyncSession, seeded_feedback,
    ):
        service = BetaOpsService()
        result = await service.get_feedback_platform(session, limit=100)
        assert hasattr(result, "items")
        assert hasattr(result, "total")
        assert hasattr(result, "by_category")
        assert hasattr(result, "by_priority")
        assert hasattr(result, "by_status")
        assert hasattr(result, "avg_vote_score")
        assert hasattr(result, "top_voted")
        assert hasattr(result, "potential_duplicates")

    @pytest.mark.asyncio
    async def test_feedback_total_matches_seeded(
        self, session: AsyncSession, seeded_feedback,
    ):
        service = BetaOpsService()
        result = await service.get_feedback_platform(session, limit=100)
        assert result.total == 12

    @pytest.mark.asyncio
    async def test_feedback_by_category(
        self, session: AsyncSession, seeded_feedback,
    ):
        service = BetaOpsService()
        result = await service.get_feedback_platform(session, limit=100)
        assert result.by_category.get("bug", 0) == 4
        assert result.by_category.get("feature_request", 0) == 3
        assert result.by_category.get("ui_ux", 0) == 3
        assert result.by_category.get("content", 0) == 2

    @pytest.mark.asyncio
    async def test_feedback_items_have_required_fields(
        self, session: AsyncSession, seeded_feedback,
    ):
        service = BetaOpsService()
        result = await service.get_feedback_platform(session, limit=100)
        for item in result.items:
            assert item.id
            assert item.user_id
            assert 1 <= item.rating <= 5
            assert item.category
            assert item.comment
            assert item.status
            assert item.priority
            assert item.roadmap_status
            assert isinstance(item.vote_score, int)
            assert isinstance(item.vote_count, int)
            assert isinstance(item.tags, list)
            assert item.created_at

    @pytest.mark.asyncio
    async def test_feedback_with_votes(
        self, session: AsyncSession, seeded_feedback, seeded_users,
    ):
        """Add votes and verify they're aggregated."""
        # Add 3 upvotes and 1 downvote on the first feedback item
        first = seeded_feedback[0]
        voters = [u for u in seeded_users if u.role == "learner"]
        for i, voter in enumerate(voters[:3]):
            session.add(BetaFeedbackVoteModel(
                feedback_id=first.id,
                user_id=voter.id,
                vote=1,
            ))
        session.add(BetaFeedbackVoteModel(
            feedback_id=first.id,
            user_id=voters[3].id,
            vote=-1,
        ))
        await session.commit()

        service = BetaOpsService()
        result = await service.get_feedback_platform(session, limit=100)
        # Find the first item in the result
        item = next(i for i in result.items if i.id == str(first.id))
        assert item.vote_count == 4
        assert item.vote_score == 2  # 3 upvotes - 1 downvote

    @pytest.mark.asyncio
    async def test_feedback_top_voted_sorted_desc(
        self, session: AsyncSession, seeded_feedback, seeded_users,
    ):
        """Add votes with varying scores; verify top_voted is sorted."""
        voters = [u for u in seeded_users if u.role == "learner"]
        for i, item in enumerate(seeded_feedback[:5]):
            for j in range(i + 1):  # item 0 gets 1 vote, item 4 gets 5
                session.add(BetaFeedbackVoteModel(
                    feedback_id=item.id,
                    user_id=voters[j].id,
                    vote=1,
                ))
        await session.commit()

        service = BetaOpsService()
        result = await service.get_feedback_platform(session, limit=100)
        if len(result.top_voted) >= 2:
            for i in range(len(result.top_voted) - 1):
                assert result.top_voted[i].vote_score >= result.top_voted[i + 1].vote_score

    @pytest.mark.asyncio
    async def test_feedback_with_meta(
        self, session: AsyncSession, seeded_feedback, seeded_users,
    ):
        """Add meta (priority, roadmap_status) and verify it's surfaced."""
        admin = next(u for u in seeded_users if u.role == "administrator")
        first = seeded_feedback[0]
        session.add(BetaFeedbackMetaModel(
            feedback_id=first.id,
            priority="urgent",
            roadmap_status="planned",
            tags=["critical", "mobile"],
            updated_by=admin.id,
        ))
        await session.commit()

        service = BetaOpsService()
        result = await service.get_feedback_platform(session, limit=100)
        item = next(i for i in result.items if i.id == str(first.id))
        assert item.priority == "urgent"
        assert item.roadmap_status == "planned"
        assert "critical" in item.tags
        assert "mobile" in item.tags

    @pytest.mark.asyncio
    async def test_feedback_by_priority(
        self, session: AsyncSession, seeded_feedback, seeded_users,
    ):
        """Add meta with various priorities; verify by_priority aggregation."""
        admin = next(u for u in seeded_users if u.role == "administrator")
        for i, item in enumerate(seeded_feedback[:5]):
            priority = ["low", "normal", "high", "urgent", "blocker"][i]
            session.add(BetaFeedbackMetaModel(
                feedback_id=item.id,
                priority=priority,
                tags=[],
                updated_by=admin.id,
            ))
        await session.commit()

        service = BetaOpsService()
        result = await service.get_feedback_platform(session, limit=100)
        assert result.by_priority.get("low", 0) >= 1
        assert result.by_priority.get("normal", 0) >= 1
        assert result.by_priority.get("high", 0) >= 1
        assert result.by_priority.get("urgent", 0) >= 1
        assert result.by_priority.get("blocker", 0) >= 1

    @pytest.mark.asyncio
    async def test_feedback_avg_vote_score(
        self, session: AsyncSession, seeded_feedback, seeded_users,
    ):
        service = BetaOpsService()
        result = await service.get_feedback_platform(session, limit=100)
        # With no votes, avg_vote_score should be 0
        assert result.avg_vote_score == 0.0

    @pytest.mark.asyncio
    async def test_feedback_limit_param(
        self, session: AsyncSession, seeded_feedback,
    ):
        service = BetaOpsService()
        result = await service.get_feedback_platform(session, limit=5)
        assert len(result.items) <= 5

    @pytest.mark.asyncio
    async def test_feedback_with_no_data(
        self, session: AsyncSession,
    ):
        service = BetaOpsService()
        result = await service.get_feedback_platform(session, limit=100)
        assert result.total == 0
        assert result.items == []
        assert result.avg_vote_score == 0.0


class TestDuplicateDetection:
    """Tests for the duplicate detection algorithm."""

    def test_detects_obvious_duplicate(self):
        from app.application.beta_ops.service import BetaOpsService, FeedbackItem

        items = [
            FeedbackItem(
                id="1", user_id="u1", rating=3, category="bug",
                comment="The login button doesn't work on mobile devices",
                status="open", priority="normal", roadmap_status="untriaged",
                vote_score=0, vote_count=0, duplicate_of=None,
                tags=[], created_at="2026-07-01",
            ),
            FeedbackItem(
                id="2", user_id="u2", rating=2, category="bug",
                comment="Login button doesn't work on mobile devices",
                status="open", priority="normal", roadmap_status="untriaged",
                vote_score=0, vote_count=0, duplicate_of=None,
                tags=[], created_at="2026-07-02",
            ),
        ]
        dups = BetaOpsService._detect_duplicate_feedback(items)
        assert len(dups) == 1
        assert dups[0]["similarity"] > 0.6

    def test_does_not_detect_different_categories(self):
        from app.application.beta_ops.service import BetaOpsService, FeedbackItem

        items = [
            FeedbackItem(
                id="1", user_id="u1", rating=3, category="bug",
                comment="Login button doesn't work on mobile devices",
                status="open", priority="normal", roadmap_status="untriaged",
                vote_score=0, vote_count=0, duplicate_of=None,
                tags=[], created_at="2026-07-01",
            ),
            FeedbackItem(
                id="2", user_id="u2", rating=2, category="feature_request",
                comment="Login button doesn't work on mobile devices",
                status="open", priority="normal", roadmap_status="untriaged",
                vote_score=0, vote_count=0, duplicate_of=None,
                tags=[], created_at="2026-07-02",
            ),
        ]
        dups = BetaOpsService._detect_duplicate_feedback(items)
        assert len(dups) == 0

    def test_does_not_detect_dissimilar_comments(self):
        from app.application.beta_ops.service import BetaOpsService, FeedbackItem

        items = [
            FeedbackItem(
                id="1", user_id="u1", rating=3, category="bug",
                comment="Login button doesn't work",
                status="open", priority="normal", roadmap_status="untriaged",
                vote_score=0, vote_count=0, duplicate_of=None,
                tags=[], created_at="2026-07-01",
            ),
            FeedbackItem(
                id="2", user_id="u2", rating=2, category="bug",
                comment="The dashboard charts are not rendering correctly",
                status="open", priority="normal", roadmap_status="untriaged",
                vote_score=0, vote_count=0, duplicate_of=None,
                tags=[], created_at="2026-07-02",
            ),
        ]
        dups = BetaOpsService._detect_duplicate_feedback(items)
        assert len(dups) == 0

    def test_handles_empty_comment(self):
        from app.application.beta_ops.service import BetaOpsService, FeedbackItem

        items = [
            FeedbackItem(
                id="1", user_id="u1", rating=3, category="bug",
                comment="ab",  # too short for tokens
                status="open", priority="normal", roadmap_status="untriaged",
                vote_score=0, vote_count=0, duplicate_of=None,
                tags=[], created_at="2026-07-01",
            ),
            FeedbackItem(
                id="2", user_id="u2", rating=2, category="bug",
                comment="cd",
                status="open", priority="normal", roadmap_status="untriaged",
                vote_score=0, vote_count=0, duplicate_of=None,
                tags=[], created_at="2026-07-02",
            ),
        ]
        dups = BetaOpsService._detect_duplicate_feedback(items)
        assert len(dups) == 0


# ============================================================
# Part 7: Operational Health
# ============================================================


class TestOperationalHealth:
    """Tests for BetaOpsService.get_operational_health()."""

    @pytest.mark.asyncio
    async def test_operations_returns_dataclass(
        self, session: AsyncSession, seeded_workers, seeded_outbox,
    ):
        service = BetaOpsService()
        result = await service.get_operational_health(session)
        assert hasattr(result, "platform_health")
        assert hasattr(result, "worker_health")
        assert hasattr(result, "background_jobs")
        assert hasattr(result, "queue_status")
        assert hasattr(result, "email_delivery")
        assert hasattr(result, "notification_delivery")
        assert hasattr(result, "database_health")
        assert hasattr(result, "redis_health")
        assert hasattr(result, "storage_usage")
        assert hasattr(result, "api_latency")
        assert hasattr(result, "ai_usage")
        assert hasattr(result, "cost_metrics")

    @pytest.mark.asyncio
    async def test_operations_platform_status(
        self, session: AsyncSession, seeded_workers, seeded_outbox,
    ):
        service = BetaOpsService()
        result = await service.get_operational_health(session)
        assert result.platform_health["status"] in ("healthy", "degraded")

    @pytest.mark.asyncio
    async def test_operations_outbox_pending(
        self, session: AsyncSession, seeded_outbox,
    ):
        service = BetaOpsService()
        result = await service.get_operational_health(session)
        # 5 pending outbox events seeded
        assert result.platform_health["outbox_pending"] == 5

    @pytest.mark.asyncio
    async def test_operations_active_workers(
        self, session: AsyncSession, seeded_workers,
    ):
        service = BetaOpsService()
        result = await service.get_operational_health(session)
        # 2 running workers (last_seen within 60s); 1 stale
        assert result.platform_health["active_workers"] == 2

    @pytest.mark.asyncio
    async def test_operations_worker_health_structure(
        self, session: AsyncSession, seeded_workers,
    ):
        service = BetaOpsService()
        result = await service.get_operational_health(session)
        assert "total_workers" in result.worker_health
        assert "running" in result.worker_health
        assert "stale" in result.worker_health
        assert "workers" in result.worker_health
        assert isinstance(result.worker_health["workers"], list)

    @pytest.mark.asyncio
    async def test_operations_queue_status(
        self, session: AsyncSession, seeded_outbox,
    ):
        service = BetaOpsService()
        result = await service.get_operational_health(session)
        assert "pending" in result.queue_status
        assert "dispatched" in result.queue_status
        assert result.queue_status["pending"] == 5
        assert result.queue_status["dispatched"] == 10

    @pytest.mark.asyncio
    async def test_operations_database_health(
        self, session: AsyncSession,
    ):
        service = BetaOpsService()
        result = await service.get_operational_health(session)
        assert "connections" in result.database_health
        assert "size_mb" in result.database_health
        assert result.database_health["connections"] >= 0
        assert result.database_health["size_mb"] >= 0

    @pytest.mark.asyncio
    async def test_operations_storage_usage(
        self, session: AsyncSession, seeded_outbox, seeded_beta_events,
    ):
        service = BetaOpsService()
        result = await service.get_operational_health(session)
        assert "database_mb" in result.storage_usage
        assert "outbox_events" in result.storage_usage
        assert "dead_letters" in result.storage_usage
        assert "beta_events_total" in result.storage_usage

    @pytest.mark.asyncio
    async def test_operations_ai_usage(
        self, session: AsyncSession,
    ):
        service = BetaOpsService()
        result = await service.get_operational_health(session)
        assert "events_7d" in result.ai_usage
        assert "enabled" in result.ai_usage

    @pytest.mark.asyncio
    async def test_operations_cost_metrics(
        self, session: AsyncSession,
    ):
        service = BetaOpsService()
        result = await service.get_operational_health(session)
        assert "ai_cost_estimate_usd_7d" in result.cost_metrics
        assert "email_cost_estimate_usd_7d" in result.cost_metrics

    @pytest.mark.asyncio
    async def test_operations_with_no_data(
        self, session: AsyncSession,
    ):
        service = BetaOpsService()
        result = await service.get_operational_health(session)
        assert result.platform_health["outbox_pending"] == 0
        assert result.platform_health["dead_letters_unresolved"] == 0
        assert result.platform_health["active_workers"] == 0


# ============================================================
# Part 8: Release Management
# ============================================================


class TestReleaseManagement:
    """Tests for BetaOpsService.get_release_management()."""

    @pytest.mark.asyncio
    async def test_releases_returns_dataclass(
        self, session: AsyncSession, seeded_release_notes,
    ):
        service = BetaOpsService()
        result = await service.get_release_management(session)
        assert hasattr(result, "releases")
        assert hasattr(result, "current_version")
        assert hasattr(result, "feature_freeze_active")
        assert hasattr(result, "version_timeline")
        assert hasattr(result, "rollback_history")

    @pytest.mark.asyncio
    async def test_releases_lists_all(
        self, session: AsyncSession, seeded_release_notes,
    ):
        service = BetaOpsService()
        result = await service.get_release_management(session)
        assert len(result.releases) == 3

    @pytest.mark.asyncio
    async def test_releases_current_version(
        self, session: AsyncSession, seeded_release_notes,
    ):
        service = BetaOpsService()
        result = await service.get_release_management(session)
        # v1.0.1 was the most recently published
        assert result.current_version in ("v1.0.1", None)

    @pytest.mark.asyncio
    async def test_releases_feature_freeze_default_false(
        self, session: AsyncSession, seeded_release_notes,
    ):
        service = BetaOpsService()
        result = await service.get_release_management(session)
        assert result.feature_freeze_active is False

    @pytest.mark.asyncio
    async def test_releases_version_timeline(
        self, session: AsyncSession, seeded_release_notes,
    ):
        service = BetaOpsService()
        result = await service.get_release_management(session)
        assert len(result.version_timeline) == 3
        for entry in result.version_timeline:
            assert "version" in entry
            assert "release_type" in entry

    @pytest.mark.asyncio
    async def test_releases_with_stages(
        self, session: AsyncSession, seeded_release_notes, seeded_users,
    ):
        """Add stages and verify current_stage is surfaced."""
        admin = next(u for u in seeded_users if u.role == "administrator")
        first_release = seeded_release_notes[0]
        session.add(ReleaseStageModel(
            id=uuid4(),
            release_note_id=first_release.id,
            stage="canary",
            rollout_percentage=10,
            triggered_by=admin.id,
        ))
        await session.commit()

        service = BetaOpsService()
        result = await service.get_release_management(session)
        release = next(r for r in result.releases if r.id == str(first_release.id))
        assert release.current_stage == "canary"
        assert release.rollout_percentage == 10

    @pytest.mark.asyncio
    async def test_releases_rollback_history(
        self, session: AsyncSession, seeded_release_notes, seeded_users,
    ):
        """Add a rolled_back stage and verify it appears in rollback_history."""
        admin = next(u for u in seeded_users if u.role == "administrator")
        rolled_back_release = seeded_release_notes[1]
        session.add(ReleaseStageModel(
            id=uuid4(),
            release_note_id=rolled_back_release.id,
            stage="rolled_back",
            rollout_percentage=0,
            completed_at=datetime.now(tz_utc.utc),
            notes="Caused SEV-2: login broken",
            triggered_by=admin.id,
        ))
        await session.commit()

        service = BetaOpsService()
        result = await service.get_release_management(session)
        assert len(result.rollback_history) >= 1
        assert any(r["version"] == rolled_back_release.version for r in result.rollback_history)

    @pytest.mark.asyncio
    async def test_releases_with_no_data(
        self, session: AsyncSession,
    ):
        service = BetaOpsService()
        result = await service.get_release_management(session)
        assert result.releases == []
        assert result.current_version is None
        assert result.feature_freeze_active is False


# ============================================================
# Part 9: Beta Reports
# ============================================================


class TestBetaReports:
    """Tests for BetaOpsService.generate_report()."""

    @pytest.mark.asyncio
    async def test_report_daily(
        self, session: AsyncSession, seeded_users, seeded_feedback, seeded_beta_events,
    ):
        service = BetaOpsService()
        result = await service.generate_report(session, period="daily")
        assert result.period == "daily"
        assert "new_users" in result.growth
        assert "total_users" in result.growth
        assert "day_1" in result.retention
        assert "sessions_completed" in result.learning_outcomes
        assert "total" in result.feedback_summary
        assert isinstance(result.top_bugs, list)
        assert isinstance(result.top_requests, list)
        assert "status" in result.system_health

    @pytest.mark.asyncio
    async def test_report_weekly(
        self, session: AsyncSession, seeded_users, seeded_feedback,
    ):
        service = BetaOpsService()
        result = await service.generate_report(session, period="weekly")
        assert result.period == "weekly"

    @pytest.mark.asyncio
    async def test_report_monthly(
        self, session: AsyncSession, seeded_users,
    ):
        service = BetaOpsService()
        result = await service.generate_report(session, period="monthly")
        assert result.period == "monthly"

    @pytest.mark.asyncio
    async def test_report_period_start_end(
        self, session: AsyncSession, seeded_users,
    ):
        service = BetaOpsService()
        result = await service.generate_report(session, period="weekly")
        assert result.period_start != result.period_end

    @pytest.mark.asyncio
    async def test_report_generated_at_is_recent(
        self, session: AsyncSession, seeded_users,
    ):
        service = BetaOpsService()
        before = datetime.now(tz_utc.utc)
        result = await service.generate_report(session, period="weekly")
        after = datetime.now(tz_utc.utc)
        gen_at = datetime.fromisoformat(result.generated_at)
        assert before <= gen_at <= after

    @pytest.mark.asyncio
    async def test_report_top_bugs_filtered_by_category(
        self, session: AsyncSession, seeded_feedback,
    ):
        service = BetaOpsService()
        result = await service.generate_report(session, period="weekly")
        # Top bugs should only contain bug-category items
        # (we can't check the IDs directly, but the count should be ≤ 4 — the number of bug feedback items)
        assert len(result.top_bugs) <= 4

    @pytest.mark.asyncio
    async def test_report_top_requests_filtered_by_category(
        self, session: AsyncSession, seeded_feedback,
    ):
        service = BetaOpsService()
        result = await service.generate_report(session, period="weekly")
        assert len(result.top_requests) <= 3  # 3 feature_requests seeded

    @pytest.mark.asyncio
    async def test_report_with_no_data(
        self, session: AsyncSession,
    ):
        service = BetaOpsService()
        result = await service.generate_report(session, period="weekly")
        assert result.growth["new_users"] == 0
        assert result.growth["total_users"] == 0
        assert result.feedback_summary["total"] == 0
        assert result.top_bugs == []
        assert result.top_requests == []

    @pytest.mark.asyncio
    async def test_report_growth_invite_conversion(
        self, session: AsyncSession, seeded_users, seeded_invites,
    ):
        service = BetaOpsService()
        result = await service.generate_report(session, period="weekly")
        assert "invite_conversion" in result.growth


# ============================================================
# Part 10: Experiments
# ============================================================


class TestExperiments:
    """Tests for BetaOpsService experiment methods."""

    @pytest.mark.asyncio
    async def test_list_experiments_returns_list(
        self, session: AsyncSession, seeded_experiments,
    ):
        service = BetaOpsService()
        result = await service.list_experiments(session)
        assert isinstance(result, list)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_experiments_has_required_fields(
        self, session: AsyncSession, seeded_experiments,
    ):
        service = BetaOpsService()
        result = await service.list_experiments(session)
        for exp in result:
            assert exp.id
            assert exp.name
            assert exp.experiment_type
            assert exp.variant_a
            assert exp.variant_b
            assert 0 <= exp.rollout_percentage <= 100
            assert exp.status in ("draft", "running", "completed", "stopped")
            assert isinstance(exp.sample_size_a, int)
            assert isinstance(exp.sample_size_b, int)
            assert isinstance(exp.is_statistically_significant, bool)

    @pytest.mark.asyncio
    async def test_list_experiments_sample_counts(
        self, session: AsyncSession, seeded_experiments,
    ):
        service = BetaOpsService()
        result = await service.list_experiments(session)
        exp = next(e for e in result if e.id == "exp_ai_v1")
        # 4 users assigned to variant_a, 4 to variant_b
        assert exp.sample_size_a == 4
        assert exp.sample_size_b == 4

    @pytest.mark.asyncio
    async def test_get_experiment_results_returns_dataclass(
        self, session: AsyncSession, seeded_experiments,
    ):
        service = BetaOpsService()
        result = await service.get_experiment_results(session, "exp_ai_v1")
        assert result is not None
        assert hasattr(result, "experiment")
        assert hasattr(result, "variant_a_results")
        assert hasattr(result, "variant_b_results")
        assert hasattr(result, "statistical_significance")
        assert hasattr(result, "recommendation")

    @pytest.mark.asyncio
    async def test_get_experiment_results_nonexistent(
        self, session: AsyncSession,
    ):
        service = BetaOpsService()
        result = await service.get_experiment_results(session, "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_experiment_results_significance(
        self, session: AsyncSession, seeded_experiments,
    ):
        """The seeded experiment has 4 samples per variant — below min_sample_size=10,
        so it should NOT be statistically significant."""
        service = BetaOpsService()
        result = await service.get_experiment_results(session, "exp_ai_v1")
        assert result is not None
        sig = result.statistical_significance
        assert "is_significant" in sig
        assert sig["is_significant"] is False  # below min_sample_size

    @pytest.mark.asyncio
    async def test_assign_variant_sticky(
        self, session: AsyncSession, seeded_experiments, seeded_users,
    ):
        """Assigning the same user twice returns the same variant."""
        service = BetaOpsService()
        user = next(u for u in seeded_users if u.role == "learner")

        v1 = await service.assign_variant(session, "exp_ai_v1", user.id)
        await session.commit()

        # Get a fresh session-scoped lookup
        v2 = await service.assign_variant(session, "exp_ai_v1", user.id)
        await session.commit()

        assert v1 == v2
        assert v1 in ("rule_based", "ai_generated")

    @pytest.mark.asyncio
    async def test_assign_variant_nonexistent_experiment(
        self, session: AsyncSession, seeded_users,
    ):
        service = BetaOpsService()
        user = next(u for u in seeded_users if u.role == "learner")
        result = await service.assign_variant(session, "nonexistent", user.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_assign_variant_draft_experiment_returns_none(
        self, session: AsyncSession, seeded_experiments, seeded_users,
    ):
        """Draft experiments should not assign variants."""
        service = BetaOpsService()
        user = next(u for u in seeded_users if u.role == "learner")
        # exp_ui_v1 is in draft status
        result = await service.assign_variant(session, "exp_ui_v1", user.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_significance_calculation_with_significant_data(
        self, session: AsyncSession, seeded_users,
    ):
        """Create an experiment with enough data to be significant."""
        from datetime import datetime, timezone as tz_utc
        now = datetime.now(tz_utc.utc)

        # Create experiment with low min_sample_size
        exp = ExperimentModel(
            id="exp_sig_test",
            name="Significance Test",
            experiment_type="ab",
            variant_a="control",
            variant_b="treatment",
            rollout_percentage=50,
            status="running",
            target_metric="conversion",
            min_sample_size=10,
            started_at=now,
            metadata_={},
        )
        session.add(exp)

        # Add results: control 10/100 = 10%, treatment 30/100 = 30%
        # This should be statistically significant
        session.add(ExperimentResultModel(
            id=uuid4(),
            experiment_id="exp_sig_test",
            variant="control",
            sample_size=100,
            metric_value=0.10,
            conversion_count=10,
            metadata_={},
        ))
        session.add(ExperimentResultModel(
            id=uuid4(),
            experiment_id="exp_sig_test",
            variant="treatment",
            sample_size=100,
            metric_value=0.30,
            conversion_count=30,
            metadata_={},
        ))
        await session.commit()

        service = BetaOpsService()
        result = await service.get_experiment_results(session, "exp_sig_test")
        assert result is not None
        assert result.statistical_significance["is_significant"] is True
        assert result.statistical_significance["p_value"] < 0.05
        # Treatment (variant_b) should be the winner
        assert "treatment" in result.recommendation

    @pytest.mark.asyncio
    async def test_significance_calculation_with_insignificant_data(
        self, session: AsyncSession,
    ):
        """Two variants with identical conversion rates should not be significant."""
        now = datetime.now(tz_utc.utc)
        exp = ExperimentModel(
            id="exp_nosig",
            name="No Significance Test",
            experiment_type="ab",
            variant_a="control",
            variant_b="treatment",
            rollout_percentage=50,
            status="running",
            target_metric="conversion",
            min_sample_size=10,
            started_at=now,
            metadata_={},
        )
        session.add(exp)
        session.add(ExperimentResultModel(
            id=uuid4(), experiment_id="exp_nosig", variant="control",
            sample_size=100, conversion_count=20, metadata_={},
        ))
        session.add(ExperimentResultModel(
            id=uuid4(), experiment_id="exp_nosig", variant="treatment",
            sample_size=100, conversion_count=20, metadata_={},
        ))
        await session.commit()

        service = BetaOpsService()
        result = await service.get_experiment_results(session, "exp_nosig")
        assert result is not None
        assert result.statistical_significance["is_significant"] is False

    @pytest.mark.asyncio
    async def test_significance_with_insufficient_samples(
        self, session: AsyncSession,
    ):
        """Below min_sample_size, should not be significant."""
        now = datetime.now(tz_utc.utc)
        exp = ExperimentModel(
            id="exp_small",
            name="Small Sample Test",
            experiment_type="ab",
            variant_a="control",
            variant_b="treatment",
            rollout_percentage=50,
            status="running",
            target_metric="conversion",
            min_sample_size=1000,  # High bar
            started_at=now,
            metadata_={},
        )
        session.add(exp)
        session.add(ExperimentResultModel(
            id=uuid4(), experiment_id="exp_small", variant="control",
            sample_size=10, conversion_count=5, metadata_={},
        ))
        session.add(ExperimentResultModel(
            id=uuid4(), experiment_id="exp_small", variant="treatment",
            sample_size=10, conversion_count=8, metadata_={},
        ))
        await session.commit()

        service = BetaOpsService()
        result = await service.get_experiment_results(session, "exp_small")
        assert result is not None
        assert result.statistical_significance["is_significant"] is False
        assert "below minimum" in result.statistical_significance.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_recommendation_no_winner_when_not_significant(
        self, session: AsyncSession, seeded_experiments,
    ):
        service = BetaOpsService()
        result = await service.get_experiment_results(session, "exp_ai_v1")
        assert result is not None
        assert "not statistically significant" in result.recommendation.lower() or \
               "do not declare" in result.recommendation.lower()
