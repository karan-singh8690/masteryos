"""Closed Beta Operations Platform API (Task 026).

All endpoints are admin-only (require ROLE_ADMINISTRATOR or ROLE_SYSTEM_ADMIN).
All endpoints are read-only GETs except:
  - POST   /admin/beta-ops/feedback/{id}/vote         — vote on feedback
  - PATCH  /admin/beta-ops/feedback/{id}/meta         — set priority/roadmap
  - POST   /admin/beta-ops/feedback/{id}/mark-duplicate — mark as duplicate
  - POST   /admin/beta-ops/releases                   — create release note
  - PATCH  /admin/beta-ops/releases/{id}              — update release note
  - POST   /admin/beta-ops/releases/{id}/stage        — add a release stage
  - POST   /admin/beta-ops/experiments                — create experiment
  - PATCH  /admin/beta-ops/experiments/{id}           — update experiment
  - POST   /admin/beta-ops/experiments/{id}/assign    — assign a user to a variant
  - POST   /admin/beta-ops/experiments/{id}/results   — record a result snapshot
  - POST   /admin/beta-ops/reports/generate           — generate a report on demand

These mutations are NOT business-logic changes — they manage operational
metadata (feedback triage, release tracking, experiment configuration)
that did not exist before Task 026.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.beta_ops import (
    BetaOpsService,
    get_beta_ops_service,
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
from app.infrastructure.security.authorization import (
    ROLE_ADMINISTRATOR,
    ROLE_SYSTEM_ADMIN,
)
from app.presentation.dependencies import (
    get_current_user_id,
    get_uow,
    require_any_role,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/beta-ops", tags=["Admin — Beta Operations"])

# All endpoints require admin role.
RequireAdmin = Depends(require_any_role(ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN))


# ============================================================
# Helper to extract raw session from UoW
# ============================================================


async def _session(uow) -> AsyncSession:
    async with uow as _uow:
        # The UoW's session is private; we read it for read-only aggregations.
        # This mirrors the pattern used in beta.py and admin.py.
        yield _uow._session  # type: ignore[union-attr]


# ============================================================
# Pydantic response models
# ============================================================


class DashboardResponse(BaseModel):
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


class FunnelStepResponse(BaseModel):
    step: str
    count: int
    cumulative_pct: float
    step_pct: float
    median_time_from_previous_minutes: float | None


class FunnelResponse(BaseModel):
    steps: list[FunnelStepResponse]
    overall_conversion: float
    biggest_drop_step: str | None
    avg_time_to_first_question_minutes: float | None


class RetentionCohortResponse(BaseModel):
    cohort_week: str
    cohort_size: int
    week_0: int
    week_1: int
    week_2: int
    week_3: int
    week_4: int


class LearningEffectivenessResponse(BaseModel):
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


class FeedbackItemResponse(BaseModel):
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


class FeedbackPlatformResponse(BaseModel):
    items: list[FeedbackItemResponse]
    total: int
    by_category: dict[str, int]
    by_priority: dict[str, int]
    by_status: dict[str, int]
    avg_vote_score: float
    top_voted: list[FeedbackItemResponse]
    potential_duplicates: list[dict[str, Any]]


class UserSuccessSignalResponse(BaseModel):
    user_id: str
    email: str
    signal_type: str
    severity: str
    description: str
    last_activity: str | None
    recommendation: str


class UserSuccessResponse(BaseModel):
    inactive_users: list[UserSuccessSignalResponse]
    at_risk_users: list[UserSuccessSignalResponse]
    incomplete_onboarding: list[UserSuccessSignalResponse]
    stuck_in_learning: list[UserSuccessSignalResponse]
    no_study_7_days: list[UserSuccessSignalResponse]
    failed_registration: list[UserSuccessSignalResponse]
    email_verification_pending: list[UserSuccessSignalResponse]
    recommendation_ignored: list[UserSuccessSignalResponse]
    summary: dict[str, int]


class InstructorAnalyticsResponse(BaseModel):
    content_quality: dict[str, Any]
    concept_coverage: dict[str, Any]
    question_quality: dict[str, Any]
    template_usage: list[dict[str, Any]]
    difficulty_balance: dict[str, Any]
    poor_performing_concepts: list[dict[str, Any]]
    frequently_missed_questions: list[dict[str, Any]]
    misconceptions: list[dict[str, Any]]
    explanation_usefulness: dict[str, Any]


class OperationalHealthResponse(BaseModel):
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


class ReleaseNoteResponse(BaseModel):
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


class ReleaseManagementResponse(BaseModel):
    releases: list[ReleaseNoteResponse]
    current_version: str | None
    feature_freeze_active: bool
    version_timeline: list[dict[str, Any]]
    rollback_history: list[dict[str, Any]]


class BetaReportResponse(BaseModel):
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


class ExperimentResponse(BaseModel):
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


class ExperimentResultsResponse(BaseModel):
    experiment: ExperimentResponse
    variant_a_results: dict[str, Any]
    variant_b_results: dict[str, Any]
    statistical_significance: dict[str, Any]
    recommendation: str


class MessageResponse(BaseModel):
    message: str
    code: str = "OK"


# ============================================================
# Request models for mutations
# ============================================================


class VoteRequest(BaseModel):
    vote: int = Field(ge=-1, le=1, description="1 = upvote, -1 = downvote")


class UpdateFeedbackMetaRequest(BaseModel):
    priority: str | None = Field(None, description="low|normal|high|urgent|blocker")
    roadmap_status: str | None = Field(
        None, description="untriaged|planned|in_progress|shipped|wont_fix|duplicate"
    )
    roadmap_link: str | None = None
    tags: list[str] | None = None
    assigned_to: str | None = None


class MarkDuplicateRequest(BaseModel):
    duplicate_of: str = Field(description="UUID of the canonical feedback item")


class CreateReleaseNoteRequest(BaseModel):
    version: str
    release_type: str = "patch"
    title: str
    summary: str | None = None
    body: str
    features: list[dict[str, Any]] = Field(default_factory=list)
    bug_fixes: list[dict[str, Any]] = Field(default_factory=list)
    breaking_changes: list[dict[str, Any]] = Field(default_factory=list)
    known_issues: list[dict[str, Any]] = Field(default_factory=list)
    feature_freeze: bool = False
    published: bool = False


class UpdateReleaseNoteRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
    body: str | None = None
    features: list[dict[str, Any]] | None = None
    bug_fixes: list[dict[str, Any]] | None = None
    breaking_changes: list[dict[str, Any]] | None = None
    known_issues: list[dict[str, Any]] | None = None
    feature_freeze: bool | None = None
    published: bool | None = None


class AddReleaseStageRequest(BaseModel):
    stage: str = Field(description="planned|building|canary|staged|live|rolled_back|abandoned")
    rollout_percentage: int = Field(0, ge=0, le=100)
    notes: str | None = None


class CreateExperimentRequest(BaseModel):
    id: str
    name: str
    description: str | None = None
    experiment_type: str = "ab"
    variant_a: str
    variant_b: str
    rollout_percentage: int = Field(50, ge=0, le=100)
    target_metric: str | None = None
    min_sample_size: int = 100
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateExperimentRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    rollout_percentage: int | None = Field(None, ge=0, le=100)
    status: str | None = None
    target_metric: str | None = None
    min_sample_size: int | None = None
    winner: str | None = None
    metadata: dict[str, Any] | None = None


class AssignVariantRequest(BaseModel):
    user_id: str


class RecordExperimentResultRequest(BaseModel):
    variant: str
    sample_size: int = Field(ge=0)
    metric_value: float | None = None
    metric_std_error: float | None = None
    conversion_count: int = Field(0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerateReportRequest(BaseModel):
    period: str = Field("weekly", description="daily|weekly|monthly")


# ============================================================
# Helper: dataclass → dict
# ============================================================


def _dc_to_dict(dc: Any) -> dict[str, Any]:
    """Convert a frozen dataclass to a dict (recursively)."""
    import dataclasses

    if dataclasses.is_dataclass(dc) and not isinstance(dc, type):
        return {f.name: _dc_to_dict(getattr(dc, f.name)) for f in dataclasses.fields(dc)}
    if isinstance(dc, list):
        return [_dc_to_dict(x) for x in dc]
    if isinstance(dc, dict):
        return {k: _dc_to_dict(v) for k, v in dc.items()}
    return dc


# ============================================================
# PART 1: Beta Operations Dashboard
# ============================================================


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Beta Operations Dashboard (admin)",
)
async def get_dashboard(
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> DashboardResponse:
    """High-level KPI snapshot for the beta operations dashboard."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.get_dashboard(session)
    return DashboardResponse(**_dc_to_dict(result))


# ============================================================
# PART 2: Product Analytics — Funnel + Retention
# ============================================================


@router.get(
    "/analytics/funnel",
    response_model=FunnelResponse,
    summary="Registration funnel (admin)",
)
async def get_registration_funnel(
    days: int = Query(30, ge=1, le=365),
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> FunnelResponse:
    """Registration funnel for the last N days."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.get_registration_funnel(session, days=days)
    return FunnelResponse(**_dc_to_dict(result))


@router.get(
    "/analytics/retention",
    response_model=list[RetentionCohortResponse],
    summary="Weekly retention cohorts (admin)",
)
async def get_retention_cohorts(
    weeks: int = Query(8, ge=1, le=52),
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> list[RetentionCohortResponse]:
    """Weekly retention cohorts for the last N weeks."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.get_retention_cohorts(session, weeks=weeks)
    return [RetentionCohortResponse(**_dc_to_dict(c)) for c in result]


# ============================================================
# PART 3: Learning Effectiveness
# ============================================================


@router.get(
    "/learning",
    response_model=LearningEffectivenessResponse,
    summary="Learning effectiveness metrics (admin)",
)
async def get_learning_effectiveness(
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> LearningEffectivenessResponse:
    """Mastery growth, accuracy, hint usage, recommendation acceptance."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.get_learning_effectiveness(session)
    return LearningEffectivenessResponse(**_dc_to_dict(result))


# ============================================================
# PART 4: User Feedback Platform
# ============================================================


@router.get(
    "/feedback",
    response_model=FeedbackPlatformResponse,
    summary="Feedback platform summary (admin)",
)
async def get_feedback_platform(
    limit: int = Query(100, ge=1, le=500),
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> FeedbackPlatformResponse:
    """Feedback items with votes, priority, roadmap, and duplicate detection."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.get_feedback_platform(session, limit=limit)
    return FeedbackPlatformResponse(**_dc_to_dict(result))


@router.post(
    "/feedback/{feedback_id}/vote",
    response_model=MessageResponse,
    summary="Vote on a feedback item (authenticated)",
)
async def vote_on_feedback(
    feedback_id: UUID,
    request: VoteRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow=Depends(get_uow),
) -> MessageResponse:
    """Cast or update a vote on a feedback item. Any authenticated user can vote."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        # Upsert the vote (unique on feedback_id + user_id)
        existing = (
            await session.execute(
                select(BetaFeedbackVoteModel).where(
                    BetaFeedbackVoteModel.feedback_id == feedback_id,
                    BetaFeedbackVoteModel.user_id == user_id,
                )
            )
        ).scalars().first()
        if existing:
            existing.vote = request.vote
        else:
            session.add(
                BetaFeedbackVoteModel(
                    feedback_id=feedback_id,
                    user_id=user_id,
                    vote=request.vote,
                )
            )
        await _uow.commit()
    return MessageResponse(message="Vote recorded")


@router.patch(
    "/feedback/{feedback_id}/meta",
    response_model=MessageResponse,
    summary="Update feedback priority / roadmap status (admin)",
)
async def update_feedback_meta(
    feedback_id: UUID,
    request: UpdateFeedbackMetaRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
) -> MessageResponse:
    """Update the priority, roadmap status, tags, or assignee of a feedback item."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        existing = (
            await session.execute(
                select(BetaFeedbackMetaModel).where(
                    BetaFeedbackMetaModel.feedback_id == feedback_id
                )
            )
        ).scalars().first()
        if existing is None:
            existing = BetaFeedbackMetaModel(
                feedback_id=feedback_id,
                priority=request.priority or "normal",
                roadmap_status=request.roadmap_status or "untriaged",
                roadmap_link=request.roadmap_link,
                tags=request.tags or [],
                assigned_to=UUID(request.assigned_to) if request.assigned_to else None,
                updated_by=user_id,
            )
            session.add(existing)
        else:
            if request.priority is not None:
                existing.priority = request.priority
            if request.roadmap_status is not None:
                existing.roadmap_status = request.roadmap_status
            if request.roadmap_link is not None:
                existing.roadmap_link = request.roadmap_link
            if request.tags is not None:
                existing.tags = request.tags
            if request.assigned_to is not None:
                existing.assigned_to = (
                    UUID(request.assigned_to) if request.assigned_to else None
                )
            existing.updated_by = user_id
            existing.updated_at = datetime.utcnow()
        await _uow.commit()
    return MessageResponse(message="Feedback metadata updated")


@router.post(
    "/feedback/{feedback_id}/mark-duplicate",
    response_model=MessageResponse,
    summary="Mark a feedback item as duplicate of another (admin)",
)
async def mark_feedback_duplicate(
    feedback_id: UUID,
    request: MarkDuplicateRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
) -> MessageResponse:
    """Mark feedback_id as a duplicate of the canonical item."""
    if str(feedback_id) == request.duplicate_of:
        raise HTTPException(
            status_code=400,
            detail="Cannot mark an item as a duplicate of itself",
        )
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        existing = (
            await session.execute(
                select(BetaFeedbackMetaModel).where(
                    BetaFeedbackMetaModel.feedback_id == feedback_id
                )
            )
        ).scalars().first()
        canonical_id = UUID(request.duplicate_of)
        if existing is None:
            existing = BetaFeedbackMetaModel(
                feedback_id=feedback_id,
                priority="normal",
                roadmap_status="duplicate",
                duplicate_of=canonical_id,
                tags=[],
                updated_by=user_id,
            )
            session.add(existing)
        else:
            existing.roadmap_status = "duplicate"
            existing.duplicate_of = canonical_id
            existing.updated_by = user_id
            existing.updated_at = datetime.utcnow()
        await _uow.commit()
    return MessageResponse(message="Marked as duplicate")


# ============================================================
# PART 5: User Success Center
# ============================================================


@router.get(
    "/success",
    response_model=UserSuccessResponse,
    summary="User success report (admin)",
)
async def get_user_success_report(
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> UserSuccessResponse:
    """At-risk users + actionable recommendations."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.get_user_success_report(session)
    return UserSuccessResponse(**_dc_to_dict(result))


# ============================================================
# PART 6: Instructor Analytics
# ============================================================


@router.get(
    "/instructor",
    response_model=InstructorAnalyticsResponse,
    summary="Instructor analytics (admin)",
)
async def get_instructor_analytics(
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> InstructorAnalyticsResponse:
    """Content quality, concept coverage, misconceptions, frequently missed questions."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.get_instructor_analytics(session)
    return InstructorAnalyticsResponse(**_dc_to_dict(result))


# ============================================================
# PART 7: Operational Monitoring
# ============================================================


@router.get(
    "/operations",
    response_model=OperationalHealthResponse,
    summary="Operational health snapshot (admin)",
)
async def get_operational_health(
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> OperationalHealthResponse:
    """Workers, outbox, email, DB, Redis, AI usage, cost metrics."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.get_operational_health(session)
    return OperationalHealthResponse(**_dc_to_dict(result))


# ============================================================
# PART 8: Release Management
# ============================================================


@router.get(
    "/releases",
    response_model=ReleaseManagementResponse,
    summary="Release management (admin)",
)
async def get_releases(
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> ReleaseManagementResponse:
    """List release notes + version timeline + rollback history."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.get_release_management(session)
    return ReleaseManagementResponse(**_dc_to_dict(result))


@router.post(
    "/releases",
    response_model=ReleaseNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a release note (admin)",
)
async def create_release(
    request: CreateReleaseNoteRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
) -> ReleaseNoteResponse:
    """Create a new release note."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        note = ReleaseNoteModel(
            version=request.version,
            release_type=request.release_type,
            title=request.title,
            summary=request.summary,
            body=request.body,
            features=request.features,
            bug_fixes=request.bug_fixes,
            breaking_changes=request.breaking_changes,
            known_issues=request.known_issues,
            feature_freeze=request.feature_freeze,
            published_at=datetime.utcnow() if request.published else None,
            created_by=user_id,
        )
        session.add(note)
        await _uow.commit()
        await session.refresh(note)
    return ReleaseNoteResponse(
        id=str(note.id),
        version=note.version,
        release_type=note.release_type,
        title=note.title,
        summary=note.summary,
        body=note.body,
        features=list(note.features or []),
        bug_fixes=list(note.bug_fixes or []),
        breaking_changes=list(note.breaking_changes or []),
        known_issues=list(note.known_issues or []),
        feature_freeze=note.feature_freeze,
        published_at=note.published_at.isoformat() if note.published_at else None,
        current_stage=None,
        rollout_percentage=0,
    )


@router.patch(
    "/releases/{release_id}",
    response_model=MessageResponse,
    summary="Update a release note (admin)",
)
async def update_release(
    release_id: UUID,
    request: UpdateReleaseNoteRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
) -> MessageResponse:
    """Update a release note."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        note = await session.get(ReleaseNoteModel, release_id)
        if note is None:
            raise HTTPException(status_code=404, detail="Release note not found")
        if request.title is not None:
            note.title = request.title
        if request.summary is not None:
            note.summary = request.summary
        if request.body is not None:
            note.body = request.body
        if request.features is not None:
            note.features = request.features
        if request.bug_fixes is not None:
            note.bug_fixes = request.bug_fixes
        if request.breaking_changes is not None:
            note.breaking_changes = request.breaking_changes
        if request.known_issues is not None:
            note.known_issues = request.known_issues
        if request.feature_freeze is not None:
            note.feature_freeze = request.feature_freeze
        if request.published is not None and request.published and note.published_at is None:
            note.published_at = datetime.utcnow()
        await _uow.commit()
    return MessageResponse(message="Release note updated")


@router.post(
    "/releases/{release_id}/stage",
    response_model=MessageResponse,
    summary="Add a release stage (canary/staged/live/rolled_back) (admin)",
)
async def add_release_stage(
    release_id: UUID,
    request: AddReleaseStageRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
) -> MessageResponse:
    """Add a stage to a release's rollout timeline."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        note = await session.get(ReleaseNoteModel, release_id)
        if note is None:
            raise HTTPException(status_code=404, detail="Release note not found")
        stage = ReleaseStageModel(
            release_note_id=release_id,
            stage=request.stage,
            rollout_percentage=request.rollout_percentage,
            notes=request.notes,
            triggered_by=user_id,
        )
        session.add(stage)
        await _uow.commit()
    return MessageResponse(message=f"Stage '{request.stage}' added")


# ============================================================
# PART 9: Beta Reports
# ============================================================


@router.get(
    "/reports/{period}",
    response_model=BetaReportResponse,
    summary="Get an auto-generated beta report (admin)",
)
async def get_report(
    period: str,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> BetaReportResponse:
    """Generate a daily/weekly/monthly beta report on demand."""
    if period not in ("daily", "weekly", "monthly"):
        raise HTTPException(
            status_code=400,
            detail="period must be one of: daily, weekly, monthly",
        )
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.generate_report(session, period=period)
    return BetaReportResponse(**_dc_to_dict(result))


@router.post(
    "/reports/generate",
    response_model=BetaReportResponse,
    summary="Generate a beta report on demand (admin)",
)
async def generate_report(
    request: GenerateReportRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> BetaReportResponse:
    """Generate a beta report on demand."""
    if request.period not in ("daily", "weekly", "monthly"):
        raise HTTPException(
            status_code=400,
            detail="period must be one of: daily, weekly, monthly",
        )
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.generate_report(session, period=request.period)
    return BetaReportResponse(**_dc_to_dict(result))


# ============================================================
# PART 10: Experiment Platform
# ============================================================


@router.get(
    "/experiments",
    response_model=list[ExperimentResponse],
    summary="List experiments (admin)",
)
async def list_experiments(
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> list[ExperimentResponse]:
    """List all experiments with assignment counts + significance."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.list_experiments(session)
    return [ExperimentResponse(**_dc_to_dict(e)) for e in result]


@router.get(
    "/experiments/{experiment_id}",
    response_model=ExperimentResultsResponse,
    summary="Get experiment results + statistical significance (admin)",
)
async def get_experiment(
    experiment_id: str,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> ExperimentResultsResponse:
    """Get detailed results for one experiment."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await service.get_experiment_results(session, experiment_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentResultsResponse(**_dc_to_dict(result))


@router.post(
    "/experiments",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an experiment (admin)",
)
async def create_experiment(
    request: CreateExperimentRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
) -> ExperimentResponse:
    """Create a new A/B experiment."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        existing = await session.get(ExperimentModel, request.id)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Experiment '{request.id}' already exists",
            )
        exp = ExperimentModel(
            id=request.id,
            name=request.name,
            description=request.description,
            experiment_type=request.experiment_type,
            variant_a=request.variant_a,
            variant_b=request.variant_b,
            rollout_percentage=request.rollout_percentage,
            status="draft",
            target_metric=request.target_metric,
            min_sample_size=request.min_sample_size,
            metadata_=request.metadata,
        )
        session.add(exp)
        await _uow.commit()
    return ExperimentResponse(
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
        started_at=None,
        ended_at=None,
        winner=None,
        sample_size_a=0,
        sample_size_b=0,
        is_statistically_significant=False,
        metadata=dict(exp.metadata_ or {}),
    )


@router.patch(
    "/experiments/{experiment_id}",
    response_model=MessageResponse,
    summary="Update an experiment (admin)",
)
async def update_experiment(
    experiment_id: str,
    request: UpdateExperimentRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
) -> MessageResponse:
    """Update experiment status, rollout %, winner, etc."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        exp = await session.get(ExperimentModel, experiment_id)
        if exp is None:
            raise HTTPException(status_code=404, detail="Experiment not found")
        if request.name is not None:
            exp.name = request.name
        if request.description is not None:
            exp.description = request.description
        if request.rollout_percentage is not None:
            exp.rollout_percentage = request.rollout_percentage
        if request.status is not None:
            exp.status = request.status
            if request.status == "running" and exp.started_at is None:
                exp.started_at = datetime.utcnow()
            if request.status in ("completed", "stopped") and exp.ended_at is None:
                exp.ended_at = datetime.utcnow()
        if request.target_metric is not None:
            exp.target_metric = request.target_metric
        if request.min_sample_size is not None:
            exp.min_sample_size = request.min_sample_size
        if request.winner is not None:
            exp.winner = request.winner
        if request.metadata is not None:
            exp.metadata_ = request.metadata
        await _uow.commit()
    return MessageResponse(message="Experiment updated")


@router.post(
    "/experiments/{experiment_id}/assign",
    response_model=MessageResponse,
    summary="Assign a user to an experiment variant (admin)",
)
async def assign_variant(
    experiment_id: str,
    request: AssignVariantRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
    service: BetaOpsService = Depends(get_beta_ops_service),
) -> MessageResponse:
    """Sticky-bucket a user to a variant for an experiment."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        target_user_id = UUID(request.user_id)
        variant = await service.assign_variant(session, experiment_id, target_user_id)
        if variant is None:
            raise HTTPException(
                status_code=400,
                detail="Experiment not found or not running",
            )
        await _uow.commit()
    return MessageResponse(message=f"Assigned to variant: {variant}", code=variant)


@router.post(
    "/experiments/{experiment_id}/results",
    response_model=MessageResponse,
    summary="Record an experiment result snapshot (admin)",
)
async def record_experiment_result(
    experiment_id: str,
    request: RecordExperimentResultRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = RequireAdmin,
    uow=Depends(get_uow),
) -> MessageResponse:
    """Record a result snapshot for a variant of an experiment."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        exp = await session.get(ExperimentModel, experiment_id)
        if exp is None:
            raise HTTPException(status_code=404, detail="Experiment not found")
        if request.variant not in (exp.variant_a, exp.variant_b):
            raise HTTPException(
                status_code=400,
                detail=f"Variant must be '{exp.variant_a}' or '{exp.variant_b}'",
            )
        result = ExperimentResultModel(
            experiment_id=experiment_id,
            variant=request.variant,
            sample_size=request.sample_size,
            metric_value=request.metric_value,
            metric_std_error=request.metric_std_error,
            conversion_count=request.conversion_count,
            metadata_=request.metadata,
        )
        session.add(result)
        await _uow.commit()
    return MessageResponse(message="Result recorded")


__all__ = ["router"]
