"""BetaOpsService — Closed Beta Operations Platform (Task 026).

Pure read-only aggregation service. Surfaces 10 categories of insights:

1.  Beta Operations Dashboard — high-level KPIs
2.  Product Analytics — registration funnel + retention cohorts
3.  Learning Effectiveness — mastery growth, accuracy, hint usage
4.  User Feedback Platform — votes, priority, roadmap, duplicate detection
5.  User Success Center — at-risk users + actionable recommendations
6.  Instructor Analytics — content quality, misconceptions, concept coverage
7.  Operational Monitoring — workers, outbox, email, DB, Redis, AI, cost
8.  Release Management — release notes, version timeline, feature freeze
9.  Beta Reports — daily / weekly / monthly auto-generated summaries
10. Experiment Platform — persistent A/B testing with statistical significance

All queries are read-only SELECTs. No mutations, no domain events.
Tables touched (all pre-existing or added in 05-beta-ops-tables.sql):
  - identity.users, identity.beta_invites, identity.beta_feedback,
    identity.beta_feedback_votes, identity.beta_feedback_meta,
    identity.sessions, identity.learner_enrollments (via learning schema)
  - learning.learner_enrollments, learning.study_sessions
  - assessment.question_instances, assessment.attempts
  - mastery.mastery_scores, mastery.reviews
  - content.subjects, content.concepts, content.question_templates,
    content.template_versions, content.misconceptions
  - analytics.beta_events, analytics.experiments,
    analytics.experiment_assignments, analytics.experiment_results
  - administration.release_notes, administration.release_stages,
    administration.notifications
  - infrastructure.outbox_events, infrastructure.worker_heartbeats,
    infrastructure.email_delivery_log, infrastructure.dead_letter_events
"""

from __future__ import annotations

import hashlib
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone as tz_utc
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, text, distinct, case, literal, Float
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Row

from app.infrastructure.database.orm.background import (
    DeadLetterEventModel,
    EmailDeliveryLogModel,
    NotificationModel,
    OutboxLeaseModel,
    ScheduledJobModel,
    WorkerHeartbeatModel,
)
from app.infrastructure.database.orm.beta import (
    BetaEventModel,
    BetaFeedbackModel,
    BetaInviteModel,
)
from app.infrastructure.database.orm.beta_ops import (
    BetaFeedbackMetaModel,
    BetaFeedbackVoteModel,
    ExperimentAssignmentModel,
    ExperimentModel,
    ExperimentResultModel,
    ReleaseNoteModel,
    ReleaseStageModel,
)
from app.infrastructure.database.orm.content import (
    ConceptModel,
    MisconceptionModel,
    SubjectModel,
)
from app.infrastructure.database.orm.core import (
    LearnerEnrollmentModel,
    MasteryScoreModel,
    OutboxEventModel,
    QuestionInstanceModel,
    ReviewModel,
    StudySessionModel,
    AttemptModel,
)
from app.infrastructure.database.orm.identity import UserModel, SessionModel
from app.shared.config import get_settings
from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Helpers
# ============================================================


def _utcnow() -> datetime:
    return datetime.now(tz_utc.utc)


def _ensure_aware(dt: datetime) -> datetime:
    if dt is None:
        return dt  # type: ignore[return-value]
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz_utc.utc)
    return dt


def _days_ago(days: int) -> datetime:
    return _utcnow() - timedelta(days=days)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return _ensure_aware(dt).isoformat()


def _round(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _safe_pct(numerator: int | float, denominator: int | float) -> float:
    """Percentage safely (0 if denominator is 0)."""
    if not denominator:
        return 0.0
    return round(100.0 * numerator / denominator, 2)


# ============================================================
# Response dataclasses
# ============================================================


@dataclass(frozen=True)
class BetaOpsDashboard:
    """Part 1: high-level KPI snapshot."""

    total_invited: int
    active_beta_users: int
    daily_active_users: int
    weekly_active_users: int
    monthly_active_users: int
    invite_conversion_rate: float
    avg_session_duration_minutes: float
    study_sessions_completed: int
    feedback_received: int
    bugs_reported: int
    crash_reports: int
    nps_score: float
    user_satisfaction: float
    learning_progress_avg: float
    retention_day_1: float
    retention_day_7: float
    retention_day_30: float
    generated_at: str


@dataclass(frozen=True)
class FunnelStep:
    step: str
    count: int
    cumulative_pct: float
    step_pct: float
    median_time_from_previous_minutes: float | None


@dataclass(frozen=True)
class RegistrationFunnel:
    """Part 2: registration funnel analysis."""

    steps: list[FunnelStep]
    overall_conversion: float
    biggest_drop_step: str | None
    avg_time_to_first_question_minutes: float | None


@dataclass(frozen=True)
class RetentionCohort:
    """Part 2: retention cohort row."""

    cohort_week: str
    cohort_size: int
    week_0: int
    week_1: int
    week_2: int
    week_3: int
    week_4: int


@dataclass(frozen=True)
class LearningEffectiveness:
    """Part 3: learning effectiveness metrics."""

    mastery_growth_avg: float
    time_to_mastery_hours: float | None
    weak_concepts: list[dict[str, Any]]
    strong_concepts: list[dict[str, Any]]
    review_effectiveness: float
    question_accuracy: float
    average_confidence: float
    hint_usage_rate: float
    recommendation_acceptance: float
    adaptive_queue_quality: float
    interview_readiness_trend: list[dict[str, Any]]


@dataclass(frozen=True)
class FeedbackItem:
    """Part 4: feedback item with votes + meta."""

    id: str
    user_id: str
    rating: int
    category: str
    comment: str
    status: str
    priority: str
    roadmap_status: str
    vote_score: int
    vote_count: int
    duplicate_of: str | None
    tags: list[str]
    created_at: str


@dataclass(frozen=True)
class FeedbackPlatformSummary:
    """Part 4: feedback platform summary."""

    items: list[FeedbackItem]
    total: int
    by_category: dict[str, int]
    by_priority: dict[str, int]
    by_status: dict[str, int]
    avg_vote_score: float
    top_voted: list[FeedbackItem]
    potential_duplicates: list[dict[str, Any]]


@dataclass(frozen=True)
class UserSuccessSignal:
    """Part 5: user success signal for a single user."""

    user_id: str
    email: str
    signal_type: str
    severity: str
    description: str
    last_activity: str | None
    recommendation: str


@dataclass(frozen=True)
class UserSuccessReport:
    """Part 5: aggregated user success report."""

    inactive_users: list[UserSuccessSignal]
    at_risk_users: list[UserSuccessSignal]
    incomplete_onboarding: list[UserSuccessSignal]
    stuck_in_learning: list[UserSuccessSignal]
    no_study_7_days: list[UserSuccessSignal]
    failed_registration: list[UserSuccessSignal]
    email_verification_pending: list[UserSuccessSignal]
    recommendation_ignored: list[UserSuccessSignal]
    summary: dict[str, int]


@dataclass(frozen=True)
class InstructorAnalytics:
    """Part 6: instructor analytics."""

    content_quality: dict[str, Any]
    concept_coverage: dict[str, Any]
    question_quality: dict[str, Any]
    template_usage: list[dict[str, Any]]
    difficulty_balance: dict[str, Any]
    poor_performing_concepts: list[dict[str, Any]]
    frequently_missed_questions: list[dict[str, Any]]
    misconceptions: list[dict[str, Any]]
    explanation_usefulness: dict[str, Any]


@dataclass(frozen=True)
class OperationalHealth:
    """Part 7: operational monitoring snapshot."""

    platform_health: dict[str, Any]
    worker_health: dict[str, Any]
    background_jobs: dict[str, Any]
    queue_status: dict[str, Any]
    email_delivery: dict[str, Any]
    notification_delivery: dict[str, Any]
    database_health: dict[str, Any]
    redis_health: dict[str, Any]
    storage_usage: dict[str, Any]
    api_latency: dict[str, Any]
    ai_usage: dict[str, Any]
    cost_metrics: dict[str, Any]


@dataclass(frozen=True)
class ReleaseNote:
    """Part 8: release note."""

    id: str
    version: str
    release_type: str
    title: str
    summary: str | None
    body: str
    features: list[dict[str, Any]]
    bug_fixes: list[dict[str, Any]]
    breaking_changes: list[dict[str, Any]]
    known_issues: list[dict[str, Any]]
    feature_freeze: bool
    published_at: str | None
    current_stage: str | None
    rollout_percentage: int


@dataclass(frozen=True)
class ReleaseManagement:
    """Part 8: release management summary."""

    releases: list[ReleaseNote]
    current_version: str | None
    feature_freeze_active: bool
    version_timeline: list[dict[str, Any]]
    rollback_history: list[dict[str, Any]]


@dataclass(frozen=True)
class BetaReport:
    """Part 9: auto-generated beta report."""

    period: str
    period_start: str
    period_end: str
    growth: dict[str, Any]
    retention: dict[str, Any]
    learning_outcomes: dict[str, Any]
    feedback_summary: dict[str, Any]
    top_bugs: list[dict[str, Any]]
    top_requests: list[dict[str, Any]]
    system_health: dict[str, Any]
    generated_at: str


@dataclass(frozen=True)
class Experiment:
    """Part 10: experiment definition."""

    id: str
    name: str
    description: str | None
    experiment_type: str
    variant_a: str
    variant_b: str
    rollout_percentage: int
    status: str
    target_metric: str | None
    min_sample_size: int
    started_at: str | None
    ended_at: str | None
    winner: str | None
    sample_size_a: int
    sample_size_b: int
    is_statistically_significant: bool
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ExperimentResults:
    """Part 10: experiment results + significance."""

    experiment: Experiment
    variant_a_results: dict[str, Any]
    variant_b_results: dict[str, Any]
    statistical_significance: dict[str, Any]
    recommendation: str


# ============================================================
# Service
# ============================================================


class BetaOpsService:
    """Read-only aggregation service for Closed Beta Operations."""

    def __init__(self) -> None:
        self._settings = get_settings()

    # ============================================================
    # PART 1: Beta Operations Dashboard
    # ============================================================

    async def get_dashboard(self, session: AsyncSession) -> BetaOpsDashboard:
        """High-level KPI snapshot for the beta operations dashboard."""
        now = _utcnow()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Total invited (distinct emails in beta_invites)
        total_invited = await session.scalar(
            select(func.count(distinct(BetaInviteModel.email)))
        ) or 0

        # Active beta users (registered + email_verified)
        active_beta_users = await session.scalar(
            select(func.count(UserModel.id)).where(
                UserModel.email_verified_at.is_not(None),
                UserModel.deleted_at.is_(None),
            )
        ) or 0

        # DAU/WAU/MAU — distinct users with a beta_event in the window
        dau = await session.scalar(
            select(func.count(distinct(BetaEventModel.user_id))).where(
                BetaEventModel.user_id.is_not(None),
                BetaEventModel.created_at >= day_ago,
            )
        ) or 0
        wau = await session.scalar(
            select(func.count(distinct(BetaEventModel.user_id))).where(
                BetaEventModel.user_id.is_not(None),
                BetaEventModel.created_at >= week_ago,
            )
        ) or 0
        mau = await session.scalar(
            select(func.count(distinct(BetaEventModel.user_id))).where(
                BetaEventModel.user_id.is_not(None),
                BetaEventModel.created_at >= month_ago,
            )
        ) or 0

        # Invite conversion = used / total invites
        used_invites = await session.scalar(
            select(func.count(BetaInviteModel.id)).where(
                BetaInviteModel.used_at.is_not(None)
            )
        ) or 0
        total_invites = await session.scalar(
            select(func.count(BetaInviteModel.id))
        ) or 0
        invite_conversion = _safe_pct(used_invites, total_invites)

        # Avg session duration + sessions completed
        session_rows = (
            await session.execute(
                select(
                    func.count(StudySessionModel.id),
                    func.avg(
                        func.extract(
                            "epoch",
                            StudySessionModel.ended_at - StudySessionModel.started_at,
                        )
                    ),
                ).where(
                    StudySessionModel.status == "ended",
                    StudySessionModel.ended_at.is_not(None),
                )
            )
        ).one()
        sessions_completed = int(session_rows[0] or 0)
        avg_session_seconds = float(session_rows[1] or 0)
        avg_session_minutes = round(avg_session_seconds / 60.0, 2) if avg_session_seconds else 0.0

        # Feedback
        feedback_total = await session.scalar(
            select(func.count(BetaFeedbackModel.id))
        ) or 0
        bugs_reported = await session.scalar(
            select(func.count(BetaFeedbackModel.id)).where(
                BetaFeedbackModel.category == "bug"
            )
        ) or 0
        # Crash reports = feedback with "crash" keyword OR rating == 1
        crash_reports = await session.scalar(
            select(func.count(BetaFeedbackModel.id)).where(
                BetaFeedbackModel.rating == 1,
            )
        ) or 0

        # NPS — 9-10 promoters, 7-8 passive, 0-6 detractors (rating is 1-5 so we
        # approximate: 5=promoter, 4=passive, 1-3=detractor)
        nps_row = (
            await session.execute(
                select(
                    func.count(BetaFeedbackModel.id),
                    func.count(BetaFeedbackModel.id).filter(
                        BetaFeedbackModel.rating == 5
                    ),
                    func.count(BetaFeedbackModel.id).filter(
                        BetaFeedbackModel.rating <= 3
                    ),
                )
            )
        ).one()
        nps_total = int(nps_row[0] or 0)
        nps_promoters = int(nps_row[1] or 0)
        nps_detractors = int(nps_row[2] or 0)
        if nps_total:
            nps_score = round(
                100.0 * (nps_promoters - nps_detractors) / nps_total, 1
            )
        else:
            nps_score = 0.0

        # User satisfaction = avg rating (1-5) normalized to 0-100
        avg_rating = await session.scalar(
            select(func.avg(BetaFeedbackModel.rating))
        )
        user_satisfaction = _safe_pct(float(avg_rating or 0), 5.0)

        # Learning progress avg = avg durable_mastery_score (0-1)
        learning_progress_avg_raw = await session.scalar(
            select(func.avg(MasteryScoreModel.durable_mastery_score))
        )
        learning_progress_avg = _round(float(learning_progress_avg_raw or 0) * 100, 2)

        # Retention (cohort-based): users whose first event was N days ago and
        # who have an event in the last day.
        retention_day_1 = await self._compute_retention(session, days=1)
        retention_day_7 = await self._compute_retention(session, days=7)
        retention_day_30 = await self._compute_retention(session, days=30)

        return BetaOpsDashboard(
            total_invited=int(total_invited),
            active_beta_users=int(active_beta_users),
            daily_active_users=int(dau),
            weekly_active_users=int(wau),
            monthly_active_users=int(mau),
            invite_conversion_rate=invite_conversion,
            avg_session_duration_minutes=avg_session_minutes,
            study_sessions_completed=sessions_completed,
            feedback_received=int(feedback_total),
            bugs_reported=int(bugs_reported),
            crash_reports=int(crash_reports),
            nps_score=nps_score,
            user_satisfaction=user_satisfaction,
            learning_progress_avg=learning_progress_avg,
            retention_day_1=retention_day_1,
            retention_day_7=retention_day_7,
            retention_day_30=retention_day_30,
            generated_at=now.isoformat(),
        )

    async def _compute_retention(
        self, session: AsyncSession, days: int
    ) -> float:
        """Compute Day-N retention: % of users whose first activity was N days
        ago (±1 day) who were active in the last 24h.

        Returns 0.0 if no users in the cohort.
        """
        target_window_start = _days_ago(days + 1)
        target_window_end = _days_ago(days)
        recent_cutoff = _days_ago(1)

        # Users whose first beta event was in the target window
        first_event_subq = (
            select(
                BetaEventModel.user_id,
                func.min(BetaEventModel.created_at).label("first_event"),
            )
            .where(BetaEventModel.user_id.is_not(None))
            .group_by(BetaEventModel.user_id)
            .subquery()
        )

        cohort_size = await session.scalar(
            select(func.count()).select_from(first_event_subq).where(
                first_event_subq.c.first_event >= target_window_start,
                first_event_subq.c.first_event < target_window_end,
            )
        ) or 0

        if not cohort_size:
            return 0.0

        # Of those users, how many were active in the last 24h
        retained = await session.scalar(
            select(func.count(distinct(BetaEventModel.user_id)))
            .select_from(
                first_event_subq.join(
                    BetaEventModel,
                    BetaEventModel.user_id == first_event_subq.c.user_id,
                )
            )
            .where(
                first_event_subq.c.first_event >= target_window_start,
                first_event_subq.c.first_event < target_window_end,
                BetaEventModel.created_at >= recent_cutoff,
            )
        ) or 0

        return _safe_pct(retained, cohort_size)

    # ============================================================
    # PART 2: Product Analytics — Registration Funnel
    # ============================================================

    async def get_registration_funnel(
        self, session: AsyncSession, days: int = 30
    ) -> RegistrationFunnel:
        """Compute the registration funnel for the last N days.

        Steps:
          1. invite_sent
          2. invite_accepted (registration page visited — proxied by
             beta_event 'invite_clicked' OR the user actually registering)
          3. registration (user created)
          4. email_verification
          5. welcome_wizard (beta_event 'welcome_wizard_completed')
          6. first_enrollment
          7. first_study_session
          8. first_completed_question
          9. day_1_retention
        """
        cutoff = _days_ago(days)

        # 1. invites sent
        invites_sent = await session.scalar(
            select(func.count(BetaInviteModel.id)).where(
                BetaInviteModel.created_at >= cutoff
            )
        ) or 0

        # 2. invites accepted (used_at set within window)
        invites_accepted = await session.scalar(
            select(func.count(BetaInviteModel.id)).where(
                BetaInviteModel.used_at.is_not(None),
                BetaInviteModel.created_at >= cutoff,
            )
        ) or 0

        # 3. registrations (users created in window)
        registrations = await session.scalar(
            select(func.count(UserModel.id)).where(
                UserModel.created_at >= cutoff
            )
        ) or 0

        # 4. email verifications
        email_verified = await session.scalar(
            select(func.count(UserModel.id)).where(
                UserModel.created_at >= cutoff,
                UserModel.email_verified_at.is_not(None),
            )
        ) or 0

        # 5. welcome wizard completed (beta_event)
        welcome_completed = await session.scalar(
            select(func.count(distinct(BetaEventModel.user_id))).where(
                BetaEventModel.event_type == "welcome_wizard_completed",
                BetaEventModel.created_at >= cutoff,
            )
        ) or 0

        # 6. first enrollment (learner_enrollments)
        first_enrollments = await session.scalar(
            select(func.count(distinct(LearnerEnrollmentModel.user_id))).where(
                LearnerEnrollmentModel.enrolled_at >= cutoff
            )
        ) or 0

        # 7. first study session
        first_sessions = await session.scalar(
            select(func.count(distinct(StudySessionModel.id))).where(
                StudySessionModel.started_at >= cutoff
            )
        ) or 0

        # 8. first completed question (attempts with scoring_outcome)
        first_questions = await session.scalar(
            select(func.count(distinct(AttemptModel.learner_enrollment_id))).where(
                AttemptModel.created_at >= cutoff
            )
        ) or 0

        # 9. Day-1 retention: users whose first activity was 1+ days ago who
        # were active in the last day
        day_1_retention = await self._compute_retention(session, days=1)

        # Build funnel steps
        step_data = [
            ("invite_sent", int(invites_sent)),
            ("invite_accepted", int(invites_accepted)),
            ("registration", int(registrations)),
            ("email_verification", int(email_verified)),
            ("welcome_wizard", int(welcome_completed)),
            ("first_enrollment", int(first_enrollments)),
            ("first_study_session", int(first_sessions)),
            ("first_completed_question", int(first_questions)),
            ("day_1_retention", int(day_1_retention)),
        ]

        steps: list[FunnelStep] = []
        previous_count: int | None = None
        biggest_drop_step: str | None = None
        biggest_drop_pct = 0.0

        for step_name, count in step_data:
            overall_pct = _safe_pct(count, step_data[0][1]) if step_data[0][1] else 0.0
            if previous_count is None:
                step_pct = 100.0
                median_time = None
            else:
                step_pct = _safe_pct(count, previous_count)
                drop = 100.0 - step_pct
                if drop > biggest_drop_pct and previous_count > 0:
                    biggest_drop_pct = drop
                    biggest_drop_step = step_name
                median_time = await self._median_time_between_steps(
                    session, step_name, cutoff
                )
            steps.append(
                FunnelStep(
                    step=step_name,
                    count=count,
                    cumulative_pct=overall_pct,
                    step_pct=step_pct,
                    median_time_from_previous_minutes=median_time,
                )
            )
            previous_count = count

        overall_conversion = _safe_pct(step_data[-1][1], step_data[0][1]) if step_data[0][1] else 0.0

        avg_time_to_first_question = await self._avg_time_to_first_question(
            session, cutoff
        )

        return RegistrationFunnel(
            steps=steps,
            overall_conversion=overall_conversion,
            biggest_drop_step=biggest_drop_step,
            avg_time_to_first_question_minutes=avg_time_to_first_question,
        )

    async def _median_time_between_steps(
        self, session: AsyncSession, step_name: str, cutoff: datetime
    ) -> float | None:
        """Best-effort median time between consecutive funnel steps.

        For most steps we approximate via the gap between user creation and
        a beta_event of the matching type.
        """
        event_type_map = {
            "welcome_wizard": "welcome_wizard_completed",
            "first_study_session": "study_session_started",
            "first_completed_question": "question_answered",
        }
        event_type = event_type_map.get(step_name)
        if not event_type:
            return None

        # Pair user creation with the matching event
        rows = (
            await session.execute(
                select(
                    UserModel.id,
                    UserModel.created_at,
                    func.min(BetaEventModel.created_at).label("event_at"),
                )
                .join(
                    BetaEventModel,
                    BetaEventModel.user_id == UserModel.id,
                )
                .where(
                    UserModel.created_at >= cutoff,
                    BetaEventModel.event_type == event_type,
                )
                .group_by(UserModel.id, UserModel.created_at)
            )
        ).all()

        if not rows:
            return None
        deltas_minutes = [
            max(0.0, (_ensure_aware(r.event_at) - _ensure_aware(r.created_at)).total_seconds() / 60.0)
            for r in rows
            if r.event_at and r.created_at
        ]
        if not deltas_minutes:
            return None
        return round(statistics.median(deltas_minutes), 2)

    async def _avg_time_to_first_question(
        self, session: AsyncSession, cutoff: datetime
    ) -> float | None:
        """Average time from user creation to first answered question."""
        rows = (
            await session.execute(
                select(
                    UserModel.id,
                    UserModel.created_at,
                    func.min(AttemptModel.created_at).label("first_attempt"),
                )
                .join(
                    LearnerEnrollmentModel,
                    LearnerEnrollmentModel.user_id == UserModel.id,
                )
                .join(
                    AttemptModel,
                    AttemptModel.learner_enrollment_id == LearnerEnrollmentModel.id,
                )
                .where(UserModel.created_at >= cutoff)
                .group_by(UserModel.id, UserModel.created_at)
            )
        ).all()

        if not rows:
            return None
        deltas_minutes = [
            (_ensure_aware(r.first_attempt) - _ensure_aware(r.created_at)).total_seconds() / 60.0
            for r in rows
            if r.first_attempt and r.created_at
        ]
        if not deltas_minutes:
            return None
        return round(statistics.mean(deltas_minutes), 2)

    async def get_retention_cohorts(
        self, session: AsyncSession, weeks: int = 8
    ) -> list[RetentionCohort]:
        """Weekly retention cohorts for the last N weeks."""
        cohorts: list[RetentionCohort] = []
        for w in range(weeks):
            cohort_start = _days_ago((w + 1) * 7)
            cohort_end = _days_ago(w * 7)

            # Users whose first event was in this cohort window
            first_event_subq = (
                select(
                    BetaEventModel.user_id,
                    func.min(BetaEventModel.created_at).label("first_event"),
                )
                .where(BetaEventModel.user_id.is_not(None))
                .group_by(BetaEventModel.user_id)
                .subquery()
            )

            cohort_size = await session.scalar(
                select(func.count()).select_from(first_event_subq).where(
                    first_event_subq.c.first_event >= cohort_start,
                    first_event_subq.c.first_event < cohort_end,
                )
            ) or 0

            week_counts = []
            for wk in range(5):  # week 0-4
                window_start = cohort_start + timedelta(weeks=wk)
                window_end = window_start + timedelta(weeks=1)
                retained = await session.scalar(
                    select(func.count(distinct(BetaEventModel.user_id)))
                    .select_from(
                        first_event_subq.join(
                            BetaEventModel,
                            BetaEventModel.user_id == first_event_subq.c.user_id,
                        )
                    )
                    .where(
                        first_event_subq.c.first_event >= cohort_start,
                        first_event_subq.c.first_event < cohort_end,
                        BetaEventModel.created_at >= window_start,
                        BetaEventModel.created_at < window_end,
                    )
                ) or 0
                week_counts.append(int(retained))

            cohorts.append(
                RetentionCohort(
                    cohort_week=cohort_start.date().isoformat(),
                    cohort_size=int(cohort_size),
                    week_0=week_counts[0],
                    week_1=week_counts[1],
                    week_2=week_counts[2],
                    week_3=week_counts[3],
                    week_4=week_counts[4],
                )
            )
        return cohorts

    # ============================================================
    # PART 3: Learning Effectiveness
    # ============================================================

    async def get_learning_effectiveness(
        self, session: AsyncSession
    ) -> LearningEffectiveness:
        """Compute learning effectiveness metrics from existing tables."""
        # Mastery growth = avg delta between earliest and latest mastery_score
        # version per enrollment
        mastery_growth_rows = (
            await session.execute(
                select(
                    MasteryScoreModel.learner_enrollment_id,
                    func.min(MasteryScoreModel.durable_mastery_score).label("min_score"),
                    func.max(MasteryScoreModel.durable_mastery_score).label("max_score"),
                )
                .group_by(MasteryScoreModel.learner_enrollment_id)
            )
        ).all()
        if mastery_growth_rows:
            growths = [
                float(r.max_score or 0) - float(r.min_score or 0)
                for r in mastery_growth_rows
            ]
            mastery_growth_avg = _round(statistics.mean(growths) * 100, 2)
        else:
            mastery_growth_avg = 0.0

        # Time to mastery = avg time from enrollment to first "proficient"
        # or "mastered" state
        time_to_mastery = await self._compute_time_to_mastery(session)

        # Weak + strong concepts
        weak_concepts = await self._concept_list(session, weakest=True, limit=10)
        strong_concepts = await self._concept_list(session, weakest=False, limit=10)

        # Review effectiveness = % of reviews with last_review_outcome = "correct"
        review_total = await session.scalar(
            select(func.count(ReviewModel.learner_enrollment_id))
        ) or 0
        # last_review_outcome lives on ReviewModel
        review_correct = await session.scalar(
            select(func.count(ReviewModel.id)).where(
                ReviewModel.last_review_outcome == "correct"
            )
        ) or 0
        review_total_with_outcome = await session.scalar(
            select(func.count(ReviewModel.id)).where(
                ReviewModel.last_review_outcome.is_not(None)
            )
        ) or 0
        review_effectiveness = _safe_pct(review_correct, review_total_with_outcome)

        # Question accuracy
        attempts_total = await session.scalar(
            select(func.count(AttemptModel.id))
        ) or 0
        attempts_correct = await session.scalar(
            select(func.count(AttemptModel.id)).where(
                AttemptModel.scoring_outcome == "correct"
            )
        ) or 0
        question_accuracy = _safe_pct(attempts_correct, attempts_total)

        # Average confidence (from mastery_scores.confidence_interval —
        # stored as the half-width; lower = more confident)
        avg_confidence_raw = await session.scalar(
            select(func.avg(MasteryScoreModel.confidence_interval))
        )
        average_confidence = _round(float(avg_confidence_raw or 0), 4)

        # Hint usage rate
        attempts_with_hint = await session.scalar(
            select(func.count(AttemptModel.id)).where(
                AttemptModel.hint_used.is_(True)
            )
        ) or 0
        hint_usage_rate = _safe_pct(attempts_with_hint, attempts_total)

        # Recommendation acceptance — proxied by beta_events
        recs_offered = await session.scalar(
            select(func.count(BetaEventModel.id)).where(
                BetaEventModel.event_type == "recommendation_offered"
            )
        ) or 0
        recs_accepted = await session.scalar(
            select(func.count(BetaEventModel.id)).where(
                BetaEventModel.event_type == "recommendation_accepted"
            )
        ) or 0
        recommendation_acceptance = _safe_pct(recs_accepted, recs_offered)

        # Adaptive queue quality — % of served questions that were answered
        # (not abandoned)
        served_total = await session.scalar(
            select(func.count(QuestionInstanceModel.id))
        ) or 0
        served_answered = await session.scalar(
            select(func.count(QuestionInstanceModel.id)).where(
                QuestionInstanceModel.status == "answered"
            )
        ) or 0
        adaptive_queue_quality = _safe_pct(served_answered, served_total)

        # Interview readiness trend — avg mastery over the last 8 weeks
        readiness_rows = (
            await session.execute(
                select(
                    func.date_trunc("week", MasteryScoreModel.last_updated_at).label("week"),
                    func.avg(MasteryScoreModel.durable_mastery_score).label("avg_score"),
                )
                .where(MasteryScoreModel.last_updated_at >= _days_ago(56))
                .group_by("week")
                .order_by("week")
            )
        ).all()
        interview_readiness_trend = []
        for r in readiness_rows:
            # On PostgreSQL, date_trunc returns a datetime; on SQLite (tests),
            # our custom date_trunc returns an ISO string. Handle both.
            if r.week is None:
                week_str = None
            elif hasattr(r.week, "date"):
                week_str = r.week.date().isoformat()
            elif isinstance(r.week, str):
                # Parse ISO string and take the date part
                try:
                    week_str = r.week.split("T")[0]
                except Exception:
                    week_str = str(r.week)
            else:
                week_str = str(r.week)
            interview_readiness_trend.append({
                "week": week_str,
                "avg_readiness": _round(float(r.avg_score or 0) * 100, 2),
            })

        return LearningEffectiveness(
            mastery_growth_avg=mastery_growth_avg,
            time_to_mastery_hours=time_to_mastery,
            weak_concepts=weak_concepts,
            strong_concepts=strong_concepts,
            review_effectiveness=review_effectiveness,
            question_accuracy=question_accuracy,
            average_confidence=average_confidence,
            hint_usage_rate=hint_usage_rate,
            recommendation_acceptance=recommendation_acceptance,
            adaptive_queue_quality=adaptive_queue_quality,
            interview_readiness_trend=interview_readiness_trend,
        )

    async def _compute_time_to_mastery(
        self, session: AsyncSession
    ) -> float | None:
        """Avg hours from enrollment to first proficient/mastered state."""
        rows = (
            await session.execute(
                select(
                    LearnerEnrollmentModel.id,
                    LearnerEnrollmentModel.enrolled_at,
                    func.min(MasteryScoreModel.last_updated_at).label("first_mastery"),
                )
                .join(
                    MasteryScoreModel,
                    MasteryScoreModel.learner_enrollment_id == LearnerEnrollmentModel.id,
                )
                .where(
                    MasteryScoreModel.concept_state.in_(["proficient", "mastered"]),
                )
                .group_by(
                    LearnerEnrollmentModel.id,
                    LearnerEnrollmentModel.enrolled_at,
                )
            )
        ).all()
        if not rows:
            return None
        deltas_hours = [
            (_ensure_aware(r.first_mastery) - _ensure_aware(r.enrolled_at)).total_seconds() / 3600.0
            for r in rows
            if r.first_mastery and r.enrolled_at
        ]
        if not deltas_hours:
            return None
        return round(statistics.mean(deltas_hours), 2)

    async def _concept_list(
        self, session: AsyncSession, weakest: bool, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Top-N weak or strong concepts by avg mastery score."""
        order = MasteryScoreModel.durable_mastery_score.asc() if weakest else \
            MasteryScoreModel.durable_mastery_score.desc()
        rows = (
            await session.execute(
                select(
                    MasteryScoreModel.concept_id,
                    func.avg(MasteryScoreModel.durable_mastery_score).label("avg_score"),
                    func.avg(MasteryScoreModel.confidence_interval).label("avg_confidence"),
                    func.count().label("enrollment_count"),
                )
                .group_by(MasteryScoreModel.concept_id)
                .order_by(order)
                .limit(limit)
            )
        ).all()
        return [
            {
                "concept_id": str(r.concept_id),
                "avg_mastery": _round(float(r.avg_score or 0), 4),
                "avg_confidence": _round(float(r.avg_confidence or 0), 4),
                "enrollment_count": int(r.enrollment_count or 0),
            }
            for r in rows
        ]

    # ============================================================
    # PART 4: User Feedback Platform
    # ============================================================

    async def get_feedback_platform(
        self, session: AsyncSession, limit: int = 100
    ) -> FeedbackPlatformSummary:
        """Aggregate feedback items with votes, priority, roadmap, duplicates."""
        # Join feedback with meta and vote aggregates
        vote_subq = (
            select(
                BetaFeedbackVoteModel.feedback_id,
                func.sum(BetaFeedbackVoteModel.vote).label("vote_score"),
                func.count(BetaFeedbackVoteModel.id).label("vote_count"),
            )
            .group_by(BetaFeedbackVoteModel.feedback_id)
            .subquery()
        )

        rows = (
            await session.execute(
                select(
                    BetaFeedbackModel.id,
                    BetaFeedbackModel.user_id,
                    BetaFeedbackModel.rating,
                    BetaFeedbackModel.category,
                    BetaFeedbackModel.comment,
                    BetaFeedbackModel.status,
                    BetaFeedbackModel.created_at,
                    BetaFeedbackMetaModel.priority,
                    BetaFeedbackMetaModel.roadmap_status,
                    BetaFeedbackMetaModel.duplicate_of,
                    BetaFeedbackMetaModel.tags,
                    func.coalesce(vote_subq.c.vote_score, 0).label("vote_score"),
                    func.coalesce(vote_subq.c.vote_count, 0).label("vote_count"),
                )
                .outerjoin(
                    BetaFeedbackMetaModel,
                    BetaFeedbackMetaModel.feedback_id == BetaFeedbackModel.id,
                )
                .outerjoin(
                    vote_subq,
                    vote_subq.c.feedback_id == BetaFeedbackModel.id,
                )
                .order_by(BetaFeedbackModel.created_at.desc())
                .limit(limit)
            )
        ).all()

        items: list[FeedbackItem] = []
        by_category: dict[str, int] = defaultdict(int)
        by_priority: dict[str, int] = defaultdict(int)
        by_status: dict[str, int] = defaultdict(int)
        total_vote_score = 0

        for r in rows:
            tags = list(r.tags or [])
            item = FeedbackItem(
                id=str(r.id),
                user_id=str(r.user_id),
                rating=int(r.rating),
                category=r.category,
                comment=r.comment,
                status=r.status,
                priority=r.priority or "normal",
                roadmap_status=r.roadmap_status or "untriaged",
                vote_score=int(r.vote_score or 0),
                vote_count=int(r.vote_count or 0),
                duplicate_of=str(r.duplicate_of) if r.duplicate_of else None,
                tags=tags,
                created_at=_iso(r.created_at) or "",
            )
            items.append(item)
            by_category[r.category] += 1
            by_priority[item.priority] += 1
            by_status[r.status] += 1
            total_vote_score += item.vote_score

        # Top voted
        top_voted = sorted(items, key=lambda x: x.vote_score, reverse=True)[:10]

        # Potential duplicates (same category + similar comment)
        potential_duplicates = self._detect_duplicate_feedback(items)

        avg_vote_score = _round(total_vote_score / len(items), 2) if items else 0.0

        return FeedbackPlatformSummary(
            items=items,
            total=len(items),
            by_category=dict(by_category),
            by_priority=dict(by_priority),
            by_status=dict(by_status),
            avg_vote_score=avg_vote_score,
            top_voted=top_voted,
            potential_duplicates=potential_duplicates,
        )

    @staticmethod
    def _detect_duplicate_feedback(
        items: list[FeedbackItem],
    ) -> list[dict[str, Any]]:
        """Detect potential duplicate feedback via simple text similarity.

        Uses a token-overlap heuristic. Two items are flagged if they share
        the same category AND >60% token overlap in their comment.
        """
        duplicates: list[dict[str, Any]] = []
        seen_pairs: set[tuple[str, str]] = set()

        def _tokens(text: str) -> set[str]:
            return {t.lower().strip(".,!?;:\"'()[]") for t in text.split() if len(t) > 2}

        for i, a in enumerate(items):
            a_tokens = _tokens(a.comment)
            if not a_tokens:
                continue
            for b in items[i + 1:]:
                if a.category != b.category:
                    continue
                b_tokens = _tokens(b.comment)
                if not b_tokens:
                    continue
                overlap = len(a_tokens & b_tokens) / len(a_tokens | b_tokens)
                if overlap > 0.6:
                    pair_key = tuple(sorted([a.id, b.id]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    duplicates.append(
                        {
                            "item_a_id": a.id,
                            "item_b_id": b.id,
                            "category": a.category,
                            "similarity": _round(overlap, 2),
                            "comment_a": a.comment[:200],
                            "comment_b": b.comment[:200],
                        }
                    )
        return duplicates

    # ============================================================
    # PART 5: User Success Center
    # ============================================================

    async def get_user_success_report(
        self, session: AsyncSession
    ) -> UserSuccessReport:
        """Identify at-risk users + generate actionable recommendations."""
        now = _utcnow()
        week_ago = now - timedelta(days=7)
        day_ago = now - timedelta(days=1)

        # All verified beta users
        users_rows = (
            await session.execute(
                select(UserModel.id, UserModel.email, UserModel.created_at, UserModel.last_login_at)
                .where(
                    UserModel.email_verified_at.is_not(None),
                    UserModel.deleted_at.is_(None),
                )
            )
        ).all()
        user_ids = [r.id for r in users_rows]

        # Map: user_id -> last beta event time
        last_event_rows = (
            await session.execute(
                select(
                    BetaEventModel.user_id,
                    func.max(BetaEventModel.created_at).label("last_event"),
                )
                .where(BetaEventModel.user_id.in_(user_ids))
                .group_by(BetaEventModel.user_id)
            )
        ).all()
        last_event_map = {r.user_id: _ensure_aware(r.last_event) for r in last_event_rows}

        # Map: user_id -> enrollment status
        enrollment_rows = (
            await session.execute(
                select(
                    LearnerEnrollmentModel.user_id,
                    LearnerEnrollmentModel.status,
                    LearnerEnrollmentModel.last_active_at,
                )
            )
        ).all()
        enrollment_map = {r.user_id: r for r in enrollment_rows}

        # Map: user_id -> last study session
        session_user_rows = (
            await session.execute(
                select(
                    StudySessionModel.id,
                    StudySessionModel.started_at,
                )
                .join(
                    LearnerEnrollmentModel,
                    LearnerEnrollmentModel.id == StudySessionModel.learner_enrollment_id,
                )
            )
        ).all()
        # We need user_id; do it via a join
        session_user_rows = (
            await session.execute(
                select(
                    LearnerEnrollmentModel.user_id,
                    func.max(StudySessionModel.started_at).label("last_session"),
                )
                .join(
                    StudySessionModel,
                    StudySessionModel.learner_enrollment_id == LearnerEnrollmentModel.id,
                )
                .group_by(LearnerEnrollmentModel.user_id)
            )
        ).all()
        last_session_map = {r.user_id: _ensure_aware(r.last_session) for r in session_user_rows}

        # Recommendations ignored: users who have a recommendation_offered
        # event older than 7 days with no recommendation_accepted event
        rec_offered_rows = (
            await session.execute(
                select(BetaEventModel.user_id)
                .where(
                    BetaEventModel.event_type == "recommendation_offered",
                    BetaEventModel.created_at < week_ago,
                )
            )
        ).all()
        rec_offered_users = {r.user_id for r in rec_offered_rows}
        rec_accepted_rows = (
            await session.execute(
                select(BetaEventModel.user_id).where(
                    BetaEventModel.event_type == "recommendation_accepted"
                )
            )
        ).all()
        rec_accepted_users = {r.user_id for r in rec_accepted_rows}
        rec_ignored_users = rec_offered_users - rec_accepted_users

        # Build signals
        inactive: list[UserSuccessSignal] = []
        at_risk: list[UserSuccessSignal] = []
        incomplete_onboarding: list[UserSuccessSignal] = []
        stuck: list[UserSuccessSignal] = []
        no_study_7d: list[UserSuccessSignal] = []
        failed_registration: list[UserSuccessSignal] = []
        email_pending: list[UserSuccessSignal] = []
        rec_ignored: list[UserSuccessSignal] = []

        # Users with unverified email
        unverified_rows = (
            await session.execute(
                select(UserModel.id, UserModel.email, UserModel.created_at)
                .where(
                    UserModel.email_verified_at.is_(None),
                    UserModel.deleted_at.is_(None),
                    UserModel.created_at >= _days_ago(7),
                )
            )
        ).all()
        for r in unverified_rows:
            email_pending.append(
                UserSuccessSignal(
                    user_id=str(r.id),
                    email=r.email,
                    signal_type="email_verification_pending",
                    severity="medium",
                    description="User registered but hasn't verified email within 7 days",
                    last_activity=_iso(r.created_at),
                    recommendation="Send a reminder email with a verification link.",
                )
            )

        for u in users_rows:
            uid = u.id
            last_event = last_event_map.get(uid)
            last_session = last_session_map.get(uid)
            enrollment = enrollment_map.get(uid)

            # Inactive (no event in 14 days)
            if last_event is None or last_event < _days_ago(14):
                inactive.append(
                    UserSuccessSignal(
                        user_id=str(uid),
                        email=u.email,
                        signal_type="inactive",
                        severity="high" if last_event is None else "medium",
                        description=(
                            "No activity in 14+ days"
                            if last_event else
                            "No activity since registration"
                        ),
                        last_activity=_iso(last_event) or _iso(u.created_at),
                        recommendation="Send a re-engagement email highlighting new content or features.",
                    )
                )

            # At-risk (was active last week but not this week)
            if last_event and last_event < day_ago and last_event > week_ago:
                at_risk.append(
                    UserSuccessSignal(
                        user_id=str(uid),
                        email=u.email,
                        signal_type="at_risk",
                        severity="medium",
                        description="User was active 1-7 days ago but not in the last 24h",
                        last_activity=_iso(last_event),
                        recommendation="Check if they hit a roadblock; offer a personalized nudge.",
                    )
                )

            # Incomplete onboarding (registered > 3 days ago, no enrollment)
            user_created = _ensure_aware(u.created_at) if u.created_at else _utcnow()
            if user_created < _days_ago(3) and (enrollment is None or enrollment.status == "pending_onboarding"):
                incomplete_onboarding.append(
                    UserSuccessSignal(
                        user_id=str(uid),
                        email=u.email,
                        signal_type="incomplete_onboarding",
                        severity="high",
                        description="User registered >3 days ago but hasn't completed onboarding",
                        last_activity=_iso(last_event) or _iso(u.created_at),
                        recommendation="Send onboarding tips and a direct link to the welcome wizard.",
                    )
                )

            # Stuck in learning (enrolled but no mastery growth in 7 days)
            if enrollment and enrollment.status == "active":
                if (
                    enrollment.last_active_at
                    and _ensure_aware(enrollment.last_active_at) < _days_ago(7)
                ):
                    stuck.append(
                        UserSuccessSignal(
                            user_id=str(uid),
                            email=u.email,
                            signal_type="stuck_in_learning",
                            severity="medium",
                            description="Enrolled but no learning activity in 7+ days",
                            last_activity=_iso(enrollment.last_active_at),
                            recommendation="Recommend an easier concept or a review session.",
                        )
                    )

            # No study session in 7 days
            if last_session is None or last_session < week_ago:
                no_study_7d.append(
                    UserSuccessSignal(
                        user_id=str(uid),
                        email=u.email,
                        signal_type="no_study_7_days",
                        severity="medium",
                        description="No study session in the last 7 days",
                        last_activity=_iso(last_session) or _iso(u.created_at),
                        recommendation="Send a 'time to study' reminder with a one-click resume link.",
                    )
                )

            # Recommendation ignored
            if uid in rec_ignored_users:
                rec_ignored.append(
                    UserSuccessSignal(
                        user_id=str(uid),
                        email=u.email,
                        signal_type="recommendation_ignored",
                        severity="low",
                        description="User received a recommendation >7 days ago but didn't accept it",
                        last_activity=_iso(last_event),
                        recommendation="Surface a different recommendation or simplify the call-to-action.",
                    )
                )

        summary = {
            "total_users": len(users_rows),
            "inactive": len(inactive),
            "at_risk": len(at_risk),
            "incomplete_onboarding": len(incomplete_onboarding),
            "stuck_in_learning": len(stuck),
            "no_study_7_days": len(no_study_7d),
            "email_verification_pending": len(email_pending),
            "recommendation_ignored": len(rec_ignored),
        }

        return UserSuccessReport(
            inactive_users=inactive,
            at_risk_users=at_risk,
            incomplete_onboarding=incomplete_onboarding,
            stuck_in_learning=stuck,
            no_study_7_days=no_study_7d,
            failed_registration=failed_registration,
            email_verification_pending=email_pending,
            recommendation_ignored=rec_ignored,
            summary=summary,
        )

    # ============================================================
    # PART 6: Instructor Analytics
    # ============================================================

    async def get_instructor_analytics(
        self, session: AsyncSession
    ) -> InstructorAnalytics:
        """Compute content + question analytics for instructors."""
        # Concept coverage — concepts per subject with at least one published
        # template
        concept_rows = (
            await session.execute(
                select(
                    ConceptModel.subject_id,
                    func.count(ConceptModel.id).label("total_concepts"),
                    func.count(ConceptModel.id).filter(
                        ConceptModel.status == "published"
                    ).label("published_concepts"),
                )
                .group_by(ConceptModel.subject_id)
            )
        ).all()
        concept_coverage = {
            "subjects": [
                {
                    "subject_id": str(r.subject_id),
                    "total_concepts": int(r.total_concepts or 0),
                    "published_concepts": int(r.published_concepts or 0),
                    "coverage_pct": _safe_pct(
                        int(r.published_concepts or 0), int(r.total_concepts or 0)
                    ),
                }
                for r in concept_rows
            ]
        }

        # Question quality — per content_version attempt accuracy
        attempts_by_template = (
            await session.execute(
                select(
                    AttemptModel.template_version_id,
                    func.count(AttemptModel.id).label("attempts"),
                    func.count(AttemptModel.id).filter(
                        AttemptModel.scoring_outcome == "correct"
                    ).label("correct"),
                    func.avg(AttemptModel.time_to_answer_ms).label("avg_time_ms"),
                )
                .group_by(AttemptModel.template_version_id)
            )
        ).all()
        template_usage = [
            {
                "template_version_id": str(r.template_version_id),
                "attempts": int(r.attempts or 0),
                "correct": int(r.correct or 0),
                "accuracy": _safe_pct(int(r.correct or 0), int(r.attempts or 0)),
                "avg_time_ms": _round(float(r.avg_time_ms or 0), 2),
            }
            for r in attempts_by_template
        ]

        # Poor-performing concepts (lowest avg mastery across active enrollments)
        poor_concepts_rows = (
            await session.execute(
                select(
                    MasteryScoreModel.concept_id,
                    func.avg(MasteryScoreModel.durable_mastery_score).label("avg_mastery"),
                    func.count().label("enrollments"),
                )
                .group_by(MasteryScoreModel.concept_id)
                .having(func.avg(MasteryScoreModel.durable_mastery_score) < 0.4)
                .order_by(func.avg(MasteryScoreModel.durable_mastery_score).asc())
                .limit(20)
            )
        ).all()
        poor_performing_concepts = [
            {
                "concept_id": str(r.concept_id),
                "avg_mastery": _round(float(r.avg_mastery or 0), 4),
                "enrollments": int(r.enrollments or 0),
            }
            for r in poor_concepts_rows
        ]

        # Frequently missed questions (lowest accuracy templates with ≥5 attempts)
        frequently_missed = sorted(
            [
                t for t in template_usage
                if t["attempts"] >= 5 and t["accuracy"] < 50.0
            ],
            key=lambda x: x["accuracy"],
        )[:20]

        # Misconceptions — most frequent misconception_id on incorrect attempts
        miscon_rows = (
            await session.execute(
                select(
                    AttemptModel.misconception_id,
                    func.count(AttemptModel.id).label("count"),
                )
                .where(AttemptModel.misconception_id.is_not(None))
                .group_by(AttemptModel.misconception_id)
                .order_by(func.count(AttemptModel.id).desc())
                .limit(20)
            )
        ).all()
        misconceptions = [
            {
                "misconception_id": str(r.misconception_id),
                "occurrences": int(r.count or 0),
            }
            for r in miscon_rows
        ]

        # Difficulty balance — distribution of concept_state
        difficulty_rows = (
            await session.execute(
                select(
                    MasteryScoreModel.concept_state,
                    func.count().label("count"),
                )
                .group_by(MasteryScoreModel.concept_state)
            )
        ).all()
        difficulty_balance = {
            r.concept_state: int(r.count or 0) for r in difficulty_rows
        }

        # Content quality — avg rating from beta feedback where category=content
        content_feedback_rows = (
            await session.execute(
                select(
                    func.count(BetaFeedbackModel.id),
                    func.avg(BetaFeedbackModel.rating),
                )
                .where(BetaFeedbackModel.category == "content")
            )
        ).one()
        content_quality = {
            "feedback_count": int(content_feedback_rows[0] or 0),
            "avg_rating": _round(float(content_feedback_rows[1] or 0), 2),
        }

        # Explanation usefulness — beta feedback where category='content' AND
        # comment mentions "explanation"
        # (Approximation — no separate explanation-feedback table.)
        explanation_rows = (
            await session.execute(
                select(
                    func.count(BetaFeedbackModel.id),
                    func.avg(BetaFeedbackModel.rating),
                )
                .where(
                    BetaFeedbackModel.category == "content",
                    BetaFeedbackModel.comment.ilike("%explanation%"),
                )
            )
        ).one()
        explanation_usefulness = {
            "feedback_count": int(explanation_rows[0] or 0),
            "avg_rating": _round(float(explanation_rows[1] or 0), 2),
        }

        return InstructorAnalytics(
            content_quality=content_quality,
            concept_coverage=concept_coverage,
            question_quality={
                "templates_analyzed": len(template_usage),
                "avg_accuracy_across_templates": _round(
                    statistics.mean([t["accuracy"] for t in template_usage])
                    if template_usage else 0.0,
                    2,
                ),
            },
            template_usage=template_usage,
            difficulty_balance=difficulty_balance,
            poor_performing_concepts=poor_performing_concepts,
            frequently_missed_questions=frequently_missed,
            misconceptions=misconceptions,
            explanation_usefulness=explanation_usefulness,
        )

    # ============================================================
    # PART 7: Operational Monitoring
    # ============================================================

    async def get_operational_health(
        self, session: AsyncSession
    ) -> OperationalHealth:
        """Operational monitoring snapshot."""
        now = _utcnow()

        # Platform health — based on outbox + dead letters + workers
        outbox_pending = await session.scalar(
            select(func.count(OutboxEventModel.id)).where(
                OutboxEventModel.status == "pending"
            )
        ) or 0
        dead_letters_unresolved = await session.scalar(
            select(func.count(DeadLetterEventModel.id)).where(
                DeadLetterEventModel.resolved_at.is_(None)
            )
        ) or 0
        active_workers = await session.scalar(
            select(func.count(WorkerHeartbeatModel.id)).where(
                WorkerHeartbeatModel.status == "running",
                WorkerHeartbeatModel.last_seen_at > now - timedelta(seconds=60),
            )
        ) or 0
        platform_healthy = (
            outbox_pending < 100
            and dead_letters_unresolved < 10
            and active_workers >= 1
        )
        platform_health = {
            "status": "healthy" if platform_healthy else "degraded",
            "outbox_pending": int(outbox_pending),
            "dead_letters_unresolved": int(dead_letters_unresolved),
            "active_workers": int(active_workers),
        }

        # Worker health
        worker_rows = (
            await session.execute(
                select(
                    WorkerHeartbeatModel.worker_id,
                    WorkerHeartbeatModel.status,
                    WorkerHeartbeatModel.last_seen_at,
                    WorkerHeartbeatModel.jobs_processed,
                    WorkerHeartbeatModel.jobs_failed,
                    WorkerHeartbeatModel.current_job,
                )
            )
        ).all()
        worker_health = {
            "total_workers": len(worker_rows),
            "running": sum(1 for r in worker_rows if r.status == "running"),
            "stale": sum(
                1 for r in worker_rows
                if r.last_seen_at
                and _ensure_aware(r.last_seen_at) < now - timedelta(seconds=60)
            ),
            "workers": [
                {
                    "worker_id": r.worker_id,
                    "status": r.status,
                    "last_seen_at": _iso(r.last_seen_at),
                    "jobs_processed": int(r.jobs_processed or 0),
                    "jobs_failed": int(r.jobs_failed or 0),
                    "current_job": r.current_job,
                }
                for r in worker_rows
            ],
        }

        # Background jobs
        job_rows = (
            await session.execute(
                select(
                    ScheduledJobModel.name,
                    ScheduledJobModel.status,
                    ScheduledJobModel.next_run_at,
                    ScheduledJobModel.last_run_at,
                    ScheduledJobModel.consecutive_failures,
                )
            )
        ).all()
        background_jobs = {
            "total": len(job_rows),
            "active": sum(1 for r in job_rows if r.status == "active"),
            "paused": sum(1 for r in job_rows if r.status == "paused"),
            "failing": sum(1 for r in job_rows if (r.consecutive_failures or 0) > 0),
            "jobs": [
                {
                    "name": r.name,
                    "status": r.status,
                    "next_run_at": _iso(r.next_run_at),
                    "last_run_at": _iso(r.last_run_at),
                    "consecutive_failures": int(r.consecutive_failures or 0),
                }
                for r in job_rows
            ],
        }

        # Queue status (outbox)
        queue_rows = (
            await session.execute(
                select(
                    OutboxEventModel.status,
                    func.count(OutboxEventModel.id),
                )
                .group_by(OutboxEventModel.status)
            )
        ).all()
        queue_status = {
            r.status: int(r[1] or 0) for r in queue_rows
        }

        # Email delivery
        email_rows = (
            await session.execute(
                select(
                    EmailDeliveryLogModel.status,
                    func.count(EmailDeliveryLogModel.id),
                )
                .where(EmailDeliveryLogModel.created_at > _days_ago(7))
                .group_by(EmailDeliveryLogModel.status)
            )
        ).all()
        email_delivery = {
            r.status: int(r[1] or 0) for r in email_rows
        }

        # Notification delivery
        notif_rows = (
            await session.execute(
                select(
                    NotificationModel.status,
                    func.count(NotificationModel.id),
                )
                .where(NotificationModel.created_at > _days_ago(7))
                .group_by(NotificationModel.status)
            )
        ).all()
        notification_delivery = {
            r.status: int(r[1] or 0) for r in notif_rows
        }

        # Database health (basic — connection count + table sizes)
        # Use try/except so this works on both PostgreSQL (production) and
        # SQLite (tests) — pg_stat_activity and pg_database_size are PG-only.
        try:
            db_conn_count = await session.scalar(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
            ) or 0
        except Exception:
            db_conn_count = 0
        try:
            db_size_bytes = await session.scalar(
                text("SELECT pg_database_size(current_database())")
            ) or 0
        except Exception:
            # SQLite fallback: page_count * page_size
            try:
                page_count = await session.scalar(text("PRAGMA page_count")) or 0
                page_size = await session.scalar(text("PRAGMA page_size")) or 4096
                db_size_bytes = int(page_count) * int(page_size)
            except Exception:
                db_size_bytes = 0
        database_health = {
            "connections": int(db_conn_count),
            "size_mb": _round(float(db_size_bytes) / (1024 * 1024), 2),
        }

        # Redis health (proxied — no direct access from this service)
        redis_health = {
            "status": "unknown — check Prometheus redis_up metric",
            "note": "Redis stats are exposed via the redis-exporter; see Grafana",
        }

        # Storage usage
        storage_usage = {
            "database_mb": database_health["size_mb"],
            "outbox_events": int(outbox_pending),
            "dead_letters": int(dead_letters_unresolved),
            "beta_events_total": await session.scalar(
                select(func.count(BetaEventModel.id))
            ) or 0,
        }

        # API latency (approximation from beta_events with response_time_ms)
        api_latency_rows = (
            await session.execute(
                select(
                    func.avg(
                        BetaEventModel.event_data["response_time_ms"].astext.cast(Float)
                    ).label("avg_ms"),
                ).where(
                    BetaEventModel.event_type == "api_response",
                    BetaEventModel.created_at > _days_ago(1),
                )
            )
        ).all()
        api_latency = {
            "avg_ms_24h": _round(float(api_latency_rows[0].avg_ms or 0), 2) if api_latency_rows else 0.0,
            "note": "API latency requires the frontend to emit 'api_response' events with response_time_ms",
        }

        # AI usage (count of AI-related beta events)
        ai_events = await session.scalar(
            select(func.count(BetaEventModel.id)).where(
                BetaEventModel.event_type.in_(
                    ["ai_explanation_requested", "ai_coach_consulted", "ai_recommendation_shown"]
                ),
                BetaEventModel.created_at > _days_ago(7),
            )
        ) or 0
        ai_usage = {
            "events_7d": int(ai_events),
            "enabled": self._settings.beta_flag_ai_enabled,
        }

        # Cost metrics (rough estimates)
        # Assume $0.0002 per AI call (Ollama local = free; OpenAI gpt-4o-mini ≈ $0.00015)
        cost_metrics = {
            "ai_cost_estimate_usd_7d": _round(int(ai_events) * 0.0002, 2),
            "email_cost_estimate_usd_7d": _round(
                sum(email_delivery.values()) * 0.0001, 4
            ),
            "note": "Costs are rough estimates; check actual provider billing for accurate numbers",
        }

        return OperationalHealth(
            platform_health=platform_health,
            worker_health=worker_health,
            background_jobs=background_jobs,
            queue_status=queue_status,
            email_delivery=email_delivery,
            notification_delivery=notification_delivery,
            database_health=database_health,
            redis_health=redis_health,
            storage_usage=storage_usage,
            api_latency=api_latency,
            ai_usage=ai_usage,
            cost_metrics=cost_metrics,
        )

    # ============================================================
    # PART 8: Release Management (read-only; writes via separate endpoints)
    # ============================================================

    async def get_release_management(
        self, session: AsyncSession
    ) -> ReleaseManagement:
        """List release notes + version timeline + rollback history."""
        rows = (
            await session.execute(
                select(ReleaseNoteModel).order_by(
                    ReleaseNoteModel.published_at.desc().nullslast(),
                    ReleaseNoteModel.created_at.desc(),
                )
            )
        ).scalars().all()

        releases: list[ReleaseNote] = []
        version_timeline: list[dict[str, Any]] = []
        rollback_history: list[dict[str, Any]] = []

        for r in rows:
            # Current stage = latest release_stage
            stage_row = (
                await session.execute(
                    select(ReleaseStageModel)
                    .where(ReleaseStageModel.release_note_id == r.id)
                    .order_by(ReleaseStageModel.started_at.desc())
                    .limit(1)
                )
            ).scalars().first()
            current_stage = stage_row.stage if stage_row else None
            rollout_pct = stage_row.rollout_percentage if stage_row else 0

            releases.append(
                ReleaseNote(
                    id=str(r.id),
                    version=r.version,
                    release_type=r.release_type,
                    title=r.title,
                    summary=r.summary,
                    body=r.body,
                    features=list(r.features or []),
                    bug_fixes=list(r.bug_fixes or []),
                    breaking_changes=list(r.breaking_changes or []),
                    known_issues=list(r.known_issues or []),
                    feature_freeze=r.feature_freeze,
                    published_at=_iso(r.published_at),
                    current_stage=current_stage,
                    rollout_percentage=int(rollout_pct),
                )
            )
            version_timeline.append(
                {
                    "version": r.version,
                    "release_type": r.release_type,
                    "published_at": _iso(r.published_at),
                    "current_stage": current_stage,
                }
            )
            if current_stage == "rolled_back":
                rollback_history.append(
                    {
                        "version": r.version,
                        "rolled_back_at": _iso(stage_row.completed_at),
                        "notes": stage_row.notes,
                    }
                )

        current_version = (
            releases[0].version if releases and releases[0].published_at else None
        )
        feature_freeze_active = any(r.feature_freeze for r in releases)

        return ReleaseManagement(
            releases=releases,
            current_version=current_version,
            feature_freeze_active=feature_freeze_active,
            version_timeline=version_timeline,
            rollback_history=rollback_history,
        )

    # ============================================================
    # PART 9: Beta Reports
    # ============================================================

    async def generate_report(
        self, session: AsyncSession, period: str = "weekly"
    ) -> BetaReport:
        """Generate a daily / weekly / monthly beta report."""
        if period == "daily":
            days = 1
        elif period == "monthly":
            days = 30
        else:
            days = 7

        now = _utcnow()
        start = now - timedelta(days=days)

        # Growth metrics
        new_users = await session.scalar(
            select(func.count(UserModel.id)).where(
                UserModel.created_at >= start
            )
        ) or 0
        total_users = await session.scalar(
            select(func.count(UserModel.id)).where(
                UserModel.email_verified_at.is_not(None),
                UserModel.deleted_at.is_(None),
            )
        ) or 0
        new_invites = await session.scalar(
            select(func.count(BetaInviteModel.id)).where(
                BetaInviteModel.created_at >= start
            )
        ) or 0
        used_invites = await session.scalar(
            select(func.count(BetaInviteModel.id)).where(
                BetaInviteModel.used_at.is_not(None),
                BetaInviteModel.used_at >= start,
            )
        ) or 0

        growth = {
            "new_users": int(new_users),
            "total_users": int(total_users),
            "new_invites": int(new_invites),
            "used_invites": int(used_invites),
            "invite_conversion": _safe_pct(used_invites, new_invites),
        }

        # Retention
        retention = {
            "day_1": await self._compute_retention(session, days=1),
            "day_7": await self._compute_retention(session, days=7),
            "day_30": await self._compute_retention(session, days=30),
        }

        # Learning outcomes
        sessions_completed = await session.scalar(
            select(func.count(StudySessionModel.id)).where(
                StudySessionModel.status == "ended",
                StudySessionModel.ended_at >= start,
            )
        ) or 0
        questions_answered = await session.scalar(
            select(func.count(AttemptModel.id)).where(
                AttemptModel.created_at >= start
            )
        ) or 0
        questions_correct = await session.scalar(
            select(func.count(AttemptModel.id)).where(
                AttemptModel.created_at >= start,
                AttemptModel.scoring_outcome == "correct",
            )
        ) or 0
        learning_outcomes = {
            "sessions_completed": int(sessions_completed),
            "questions_answered": int(questions_answered),
            "questions_correct": int(questions_correct),
            "accuracy": _safe_pct(questions_correct, questions_answered),
        }

        # Feedback summary
        feedback_total = await session.scalar(
            select(func.count(BetaFeedbackModel.id)).where(
                BetaFeedbackModel.created_at >= start
            )
        ) or 0
        feedback_open = await session.scalar(
            select(func.count(BetaFeedbackModel.id)).where(
                BetaFeedbackModel.created_at >= start,
                BetaFeedbackModel.status == "open",
            )
        ) or 0
        avg_rating = await session.scalar(
            select(func.avg(BetaFeedbackModel.rating)).where(
                BetaFeedbackModel.created_at >= start
            )
        )
        feedback_summary = {
            "total": int(feedback_total),
            "open": int(feedback_open),
            "avg_rating": _round(float(avg_rating or 0), 2),
        }

        # Top bugs + top requests
        top_bugs_rows = (
            await session.execute(
                select(
                    BetaFeedbackModel.id,
                    BetaFeedbackModel.comment,
                    BetaFeedbackModel.created_at,
                )
                .where(
                    BetaFeedbackModel.category == "bug",
                    BetaFeedbackModel.created_at >= start,
                )
                .order_by(BetaFeedbackModel.created_at.desc())
                .limit(10)
            )
        ).all()
        top_bugs = [
            {
                "id": str(r.id),
                "comment": r.comment[:200],
                "created_at": _iso(r.created_at),
            }
            for r in top_bugs_rows
        ]

        top_requests_rows = (
            await session.execute(
                select(
                    BetaFeedbackModel.id,
                    BetaFeedbackModel.comment,
                    BetaFeedbackModel.created_at,
                )
                .where(
                    BetaFeedbackModel.category == "feature_request",
                    BetaFeedbackModel.created_at >= start,
                )
                .order_by(BetaFeedbackModel.created_at.desc())
                .limit(10)
            )
        ).all()
        top_requests = [
            {
                "id": str(r.id),
                "comment": r.comment[:200],
                "created_at": _iso(r.created_at),
            }
            for r in top_requests_rows
        ]

        # System health
        ops = await self.get_operational_health(session)
        system_health = {
            "status": ops.platform_health["status"],
            "outbox_pending": ops.platform_health["outbox_pending"],
            "dead_letters_unresolved": ops.platform_health["dead_letters_unresolved"],
            "active_workers": ops.platform_health["active_workers"],
        }

        return BetaReport(
            period=period,
            period_start=start.isoformat(),
            period_end=now.isoformat(),
            growth=growth,
            retention=retention,
            learning_outcomes=learning_outcomes,
            feedback_summary=feedback_summary,
            top_bugs=top_bugs,
            top_requests=top_requests,
            system_health=system_health,
            generated_at=now.isoformat(),
        )

    # ============================================================
    # PART 10: Experiment Platform
    # ============================================================

    async def list_experiments(
        self, session: AsyncSession
    ) -> list[Experiment]:
        """List all experiments with assignment counts + significance."""
        rows = (
            await session.execute(
                select(ExperimentModel).order_by(
                    ExperimentModel.created_at.desc()
                )
            )
        ).scalars().all()

        experiments: list[Experiment] = []
        for r in rows:
            # Counts per variant
            count_a = await session.scalar(
                select(func.count(ExperimentAssignmentModel.id)).where(
                    ExperimentAssignmentModel.experiment_id == r.id,
                    ExperimentAssignmentModel.variant == r.variant_a,
                )
            ) or 0
            count_b = await session.scalar(
                select(func.count(ExperimentAssignmentModel.id)).where(
                    ExperimentAssignmentModel.experiment_id == r.id,
                    ExperimentAssignmentModel.variant == r.variant_b,
                )
            ) or 0

            # Significance check (only if we have results)
            is_sig = await self._check_significance(session, r.id)

            experiments.append(
                Experiment(
                    id=r.id,
                    name=r.name,
                    description=r.description,
                    experiment_type=r.experiment_type,
                    variant_a=r.variant_a,
                    variant_b=r.variant_b,
                    rollout_percentage=r.rollout_percentage,
                    status=r.status,
                    target_metric=r.target_metric,
                    min_sample_size=r.min_sample_size,
                    started_at=_iso(r.started_at),
                    ended_at=_iso(r.ended_at),
                    winner=r.winner,
                    sample_size_a=int(count_a),
                    sample_size_b=int(count_b),
                    is_statistically_significant=is_sig,
                    metadata=dict(r.metadata_ or {}),
                )
            )
        return experiments

    async def get_experiment_results(
        self, session: AsyncSession, experiment_id: str
    ) -> ExperimentResults | None:
        """Get detailed results for one experiment."""
        exp = (
            await session.execute(
                select(ExperimentModel).where(ExperimentModel.id == experiment_id)
            )
        ).scalars().first()
        if exp is None:
            return None

        results_rows = (
            await session.execute(
                select(ExperimentResultModel).where(
                    ExperimentResultModel.experiment_id == experiment_id
                )
            )
        ).scalars().all()

        variant_results: dict[str, dict[str, Any]] = {
            exp.variant_a: {"sample_size": 0, "metric_value": None, "conversions": 0},
            exp.variant_b: {"sample_size": 0, "metric_value": None, "conversions": 0},
        }
        for r in results_rows:
            if r.variant in variant_results:
                variant_results[r.variant] = {
                    "sample_size": int(r.sample_size or 0),
                    "metric_value": _round(r.metric_value, 4) if r.metric_value is not None else None,
                    "metric_std_error": _round(r.metric_std_error, 4) if r.metric_std_error is not None else None,
                    "conversions": int(r.conversion_count or 0),
                    "computed_at": _iso(r.computed_at),
                }

        # Significance
        sig = await self._compute_significance(session, exp)
        recommendation = self._recommend_winner(exp, variant_results, sig)

        # Build Experiment dataclass
        count_a = variant_results[exp.variant_a]["sample_size"]
        count_b = variant_results[exp.variant_b]["sample_size"]
        is_sig = sig.get("is_significant", False)

        experiment = Experiment(
            id=exp.id,
            name=exp.name,
            description=exp.description,
            experiment_type=exp.experiment_type,
            variant_a=exp.variant_a,
            variant_b=exp.variant_b,
            rollout_percentage=exp.rollout_percentage,
            status=exp.status,
            target_metric=exp.target_metric,
            min_sample_size=exp.min_sample_size,
            started_at=_iso(exp.started_at),
            ended_at=_iso(exp.ended_at),
            winner=exp.winner,
            sample_size_a=count_a,
            sample_size_b=count_b,
            is_statistically_significant=is_sig,
            metadata=dict(exp.metadata_ or {}),
        )

        return ExperimentResults(
            experiment=experiment,
            variant_a_results=variant_results[exp.variant_a],
            variant_b_results=variant_results[exp.variant_b],
            statistical_significance=sig,
            recommendation=recommendation,
        )

    async def _check_significance(
        self, session: AsyncSession, experiment_id: str
    ) -> bool:
        """Quick boolean: is this experiment statistically significant?"""
        sig = await self._compute_significance_by_id(session, experiment_id)
        return sig.get("is_significant", False)

    async def _compute_significance(
        self, session: AsyncSession, exp: ExperimentModel
    ) -> dict[str, Any]:
        """Compute statistical significance for an experiment."""
        return await self._compute_significance_by_id(session, exp.id)

    async def _compute_significance_by_id(
        self, session: AsyncSession, experiment_id: str
    ) -> dict[str, Any]:
        """Compute two-proportion z-test for the experiment's variant results."""
        rows = (
            await session.execute(
                select(ExperimentResultModel).where(
                    ExperimentResultModel.experiment_id == experiment_id
                )
            )
        ).scalars().all()

        if len(rows) < 2:
            return {
                "is_significant": False,
                "p_value": None,
                "z_score": None,
                "reason": "Insufficient data — need results for both variants",
            }

        # Find variant A and B rows
        exp = (
            await session.execute(
                select(ExperimentModel).where(ExperimentModel.id == experiment_id)
            )
        ).scalars().first()
        if exp is None:
            return {"is_significant": False, "p_value": None, "z_score": None, "reason": "Experiment not found"}

        a_row = next((r for r in rows if r.variant == exp.variant_a), None)
        b_row = next((r for r in rows if r.variant == exp.variant_b), None)
        if not a_row or not b_row:
            return {"is_significant": False, "p_value": None, "z_score": None, "reason": "Missing variant results"}

        n_a = int(a_row.sample_size or 0)
        n_b = int(b_row.sample_size or 0)
        c_a = int(a_row.conversion_count or 0)
        c_b = int(b_row.conversion_count or 0)

        if n_a < (exp.min_sample_size or 100) or n_b < (exp.min_sample_size or 100):
            return {
                "is_significant": False,
                "p_value": None,
                "z_score": None,
                "reason": f"Sample size below minimum ({exp.min_sample_size})",
                "sample_size_a": n_a,
                "sample_size_b": n_b,
            }

        p_a = c_a / n_a
        p_b = c_b / n_b
        # Pooled proportion
        p_pooled = (c_a + c_b) / (n_a + n_b)
        if p_pooled == 0 or p_pooled == 1:
            return {
                "is_significant": False,
                "p_value": None,
                "z_score": None,
                "reason": "No variance in conversions",
                "sample_size_a": n_a,
                "sample_size_b": n_b,
            }

        se = math.sqrt(p_pooled * (1 - p_pooled) * (1.0 / n_a + 1.0 / n_b))
        if se == 0:
            return {
                "is_significant": False,
                "p_value": None,
                "z_score": None,
                "reason": "Zero standard error",
            }

        z = (p_b - p_a) / se
        # Two-tailed p-value approximation via the error function
        # p = 2 * (1 - Φ(|z|))
        # Φ(z) ≈ 0.5 * (1 + erf(z / sqrt(2)))
        try:
            p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
        except (OverflowError, ValueError):
            p_value = 0.0 if abs(z) > 10 else 1.0

        return {
            "is_significant": p_value < 0.05,
            "p_value": round(p_value, 6),
            "z_score": round(z, 4),
            "sample_size_a": n_a,
            "sample_size_b": n_b,
            "conversion_rate_a": round(p_a, 4),
            "conversion_rate_b": round(p_b, 4),
            "lift": round((p_b - p_a) / p_a, 4) if p_a > 0 else None,
        }

    @staticmethod
    def _recommend_winner(
        exp: ExperimentModel,
        variant_results: dict[str, dict[str, Any]],
        sig: dict[str, Any],
    ) -> str:
        """Recommend a winner based on significance + lift."""
        if not sig.get("is_significant"):
            return "Do not declare a winner yet — results are not statistically significant."
        p_a = sig.get("conversion_rate_a", 0)
        p_b = sig.get("conversion_rate_b", 0)
        if p_b > p_a:
            return f"Declare {exp.variant_b} the winner — conversion rate {p_b:.4f} vs {p_a:.4f} (p={sig.get('p_value'):.4f})."
        elif p_a > p_b:
            return f"Declare {exp.variant_a} the winner — conversion rate {p_a:.4f} vs {p_b:.4f} (p={sig.get('p_value'):.4f})."
        return "No clear winner — conversion rates are equal."

    async def assign_variant(
        self, session: AsyncSession, experiment_id: str, user_id: UUID
    ) -> str | None:
        """Sticky-bucket a user to a variant for an experiment.

        If the user already has an assignment, return it. Otherwise, assign
        deterministically based on a hash of (experiment_id, user_id) modulo
        the rollout percentage.
        """
        existing = (
            await session.execute(
                select(ExperimentAssignmentModel).where(
                    ExperimentAssignmentModel.experiment_id == experiment_id,
                    ExperimentAssignmentModel.user_id == user_id,
                )
            )
        ).scalars().first()
        if existing:
            return existing.variant

        exp = (
            await session.execute(
                select(ExperimentModel).where(ExperimentModel.id == experiment_id)
            )
        ).scalars().first()
        if exp is None or exp.status != "running":
            return None

        # Deterministic hash: SHA-256 of (experiment_id + user_id) mod 100
        h = hashlib.sha256(f"{experiment_id}:{user_id}".encode()).hexdigest()
        bucket = int(h[:8], 16) % 100
        variant = exp.variant_b if bucket < exp.rollout_percentage else exp.variant_a

        assignment = ExperimentAssignmentModel(
            experiment_id=experiment_id,
            user_id=user_id,
            variant=variant,
        )
        session.add(assignment)
        await session.flush()
        return variant


# ============================================================
# Singleton
# ============================================================


_beta_ops_service: BetaOpsService | None = None


def get_beta_ops_service() -> BetaOpsService:
    """Return the cached BetaOpsService singleton."""
    global _beta_ops_service
    if _beta_ops_service is None:
        _beta_ops_service = BetaOpsService()
    return _beta_ops_service


__all__ = [
    "BetaOpsService",
    "get_beta_ops_service",
    # Dataclasses
    "BetaOpsDashboard",
    "FunnelStep",
    "RegistrationFunnel",
    "RetentionCohort",
    "LearningEffectiveness",
    "FeedbackItem",
    "FeedbackPlatformSummary",
    "UserSuccessSignal",
    "UserSuccessReport",
    "InstructorAnalytics",
    "OperationalHealth",
    "ReleaseNote",
    "ReleaseManagement",
    "BetaReport",
    "Experiment",
    "ExperimentResults",
]
