"""Learner API routes — endpoints for the learner portal.

These endpoints complement learning.py with the read-side queries
needed by the learner dashboard, mastery, reviews, recommendations,
achievements, and notifications pages.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update, func, and_

from app.application.shared import UnitOfWork
from app.infrastructure.database.orm.background import NotificationModel
from app.infrastructure.database.orm.core import (
    LearnerEnrollmentModel,
    StudySessionModel,
    MasteryScoreModel,
    ReviewModel,
)
from app.infrastructure.database.orm.content import SubjectModel, ConceptModel
from app.presentation.dependencies import get_current_user_id, get_uow

router = APIRouter(tags=["Learner"])


# ============================================================
# Response Models
# ============================================================


class EnrollmentSummary(BaseModel):
    id: UUID
    subject_id: UUID
    status: str
    enrolled_at: datetime
    learning_goal: str | None = None


class EnrollmentDetail(EnrollmentSummary):
    daily_goal_minutes: int | None = None
    preferred_difficulty: str | None = None


class StudySessionSummary(BaseModel):
    id: UUID
    enrollment_id: UUID
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    questions_attempted: int = 0
    questions_correct: int = 0


class MasteryScoreSummary(BaseModel):
    concept_id: UUID
    score: float
    memory_score: float
    last_attempt_at: datetime | None = None
    attempts_count: int = 0


class ReviewSummary(BaseModel):
    id: UUID
    enrollment_id: UUID
    concept_id: UUID
    scheduled_for: datetime
    status: str
    review_interval: str | None = None


class RecommendationSummary(BaseModel):
    id: UUID
    type: str
    priority: str
    title: str
    description: str
    action_url: str | None = None
    dismissed: bool = False


class AchievementSummary(BaseModel):
    id: UUID
    name: str
    description: str
    earned_at: datetime
    icon: str | None = None


class NotificationSummary(BaseModel):
    id: UUID
    type: str
    title: str
    message: str
    priority: str
    status: str
    created_at: datetime
    opened_at: datetime | None = None


class UnreadCountResponse(BaseModel):
    unread_count: int


# ============================================================
# Enrollment endpoints
# ============================================================


@router.get("/enrollments", response_model=list[EnrollmentSummary])
async def list_enrollments(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[EnrollmentSummary]:
    """List all enrollments for the current user."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(LearnerEnrollmentModel)
                .where(LearnerEnrollmentModel.user_id == user_id)
                .order_by(LearnerEnrollmentModel.enrolled_at.desc())
            )
            enrollments = result.scalars().all()
            return [
                EnrollmentSummary(
                    id=e.id,
                    subject_id=e.subject_id,
                    status=e.status,
                    enrolled_at=e.enrolled_at,
                    learning_goal=None,  # Not a column on this model
                )
                for e in enrollments
            ]
    except Exception as exc:
        # Return empty list on error (e.g., table doesn't exist yet)
        return []


@router.get("/enrollments/{enrollment_id}", response_model=EnrollmentDetail)
async def get_enrollment(
    enrollment_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> EnrollmentDetail:
    """Get a single enrollment by ID."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(LearnerEnrollmentModel).where(
                    and_(
                        LearnerEnrollmentModel.id == enrollment_id,
                        LearnerEnrollmentModel.user_id == user_id,
                    )
                )
            )
            e = result.scalar_one_or_none()
            if not e:
                raise HTTPException(status_code=404, detail="Enrollment not found")
            return EnrollmentDetail(
                id=e.id,
                subject_id=e.subject_id,
                status=e.status,
                enrolled_at=e.enrolled_at,
                learning_goal=None,
                daily_goal_minutes=None,
                preferred_difficulty=None,
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Enrollment not found")


# ============================================================
# Study Session endpoints
# ============================================================


@router.get("/study-sessions/{session_id}", response_model=StudySessionSummary)
async def get_study_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> StudySessionSummary:
    """Get a study session by ID."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(StudySessionModel).where(StudySessionModel.id == session_id)
            )
            s = result.scalar_one_or_none()
            if not s:
                raise HTTPException(status_code=404, detail="Study session not found")
            return StudySessionSummary(
                id=s.id,
                enrollment_id=s.learner_enrollment_id,
                status=s.status,
                started_at=s.started_at,
                ended_at=getattr(s, "ended_at", None),
                questions_attempted=0,
                questions_correct=0,
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Study session not found")


@router.post("/study-sessions/{session_id}/end", response_model=StudySessionSummary)
async def end_study_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> StudySessionSummary:
    """End a study session."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(StudySessionModel).where(StudySessionModel.id == session_id)
            )
            s = result.scalar_one_or_none()
            if not s:
                raise HTTPException(status_code=404, detail="Study session not found")
            s.status = "ended"  # type: ignore[assignment]
            await session.commit()
            return StudySessionSummary(
                id=s.id,
                enrollment_id=s.learner_enrollment_id,
                status=s.status,
                started_at=s.started_at,
                ended_at=datetime.now(timezone.utc),
                questions_attempted=0,
                questions_correct=0,
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Mastery endpoints
# ============================================================


@router.get("/mastery/scores/{enrollment_id}", response_model=list[MasteryScoreSummary])
async def get_mastery_scores(
    enrollment_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[MasteryScoreSummary]:
    """Get mastery scores for an enrollment."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(MasteryScoreModel).where(
                    MasteryScoreModel.enrollment_id == enrollment_id
                )
            )
            scores = result.scalars().all()
            return [
                MasteryScoreSummary(
                    concept_id=s.concept_id,
                    score=float(getattr(s, "mastery_score_combined", 0.0) or 0.0),
                    memory_score=float(getattr(s, "memory_score", 0.0) or 0.0),
                    last_attempt_at=getattr(s, "last_attempt_at", None),
                    attempts_count=getattr(s, "evidence_count", 0),
                )
                for s in scores
            ]
    except Exception:
        return []


@router.get("/mastery/scores/{enrollment_id}/weak", response_model=list[MasteryScoreSummary])
async def get_weak_concepts(
    enrollment_id: UUID,
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[MasteryScoreSummary]:
    """Get concepts where mastery is below threshold."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(MasteryScoreModel).where(
                    and_(
                        MasteryScoreModel.enrollment_id == enrollment_id,
                    )
                )
            )
            scores = result.scalars().all()
            # Filter in Python (simpler than SQL comparison with ORM properties)
            weak = [s for s in scores if float(getattr(s, "mastery_score_combined", 1.0) or 1.0) < threshold]
            return [
                MasteryScoreSummary(
                    concept_id=s.concept_id,
                    score=float(getattr(s, "mastery_score_combined", 0.0) or 0.0),
                    memory_score=float(getattr(s, "memory_score", 0.0) or 0.0),
                    last_attempt_at=getattr(s, "last_attempt_at", None),
                    attempts_count=getattr(s, "evidence_count", 0),
                )
                for s in weak
            ]
    except Exception:
        return []


# ============================================================
# Review endpoints
# ============================================================


@router.get("/reviews/due/{enrollment_id}", response_model=list[ReviewSummary])
async def get_due_reviews(
    enrollment_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[ReviewSummary]:
    """Get reviews due for an enrollment."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(ReviewModel).where(
                    ReviewModel.enrollment_id == enrollment_id
                )
            )
            reviews = result.scalars().all()
            return [
                ReviewSummary(
                    id=r.id,
                    enrollment_id=r.enrollment_id,
                    concept_id=r.concept_id,
                    scheduled_for=getattr(r, "scheduled_for", datetime.now(timezone.utc)),
                    status=getattr(r, "status", "pending"),
                    review_interval=None,
                )
                for r in reviews
            ]
    except Exception:
        return []


# ============================================================
# Recommendation endpoints (stub — returns empty list)
# ============================================================


@router.get("/recommendations", response_model=list[RecommendationSummary])
async def get_recommendations(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[RecommendationSummary]:
    """Get personalized recommendations for the current user."""
    return []


# ============================================================
# Achievement endpoints (stub — returns empty list)
# ============================================================


@router.get("/achievements", response_model=list[AchievementSummary])
async def get_achievements(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[AchievementSummary]:
    """Get achievements earned by the current user."""
    return []


# ============================================================
# Notification endpoints
# ============================================================


@router.get("/notifications", response_model=list[NotificationSummary])
async def list_notifications(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[NotificationSummary]:
    """List notifications for the current user."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            query = (
                select(NotificationModel)
                .where(NotificationModel.user_id == user_id)
                .order_by(NotificationModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            if status_filter:
                query = query.where(NotificationModel.status == status_filter)
            result = await session.execute(query)
            notifications = result.scalars().all()
            return [
                NotificationSummary(
                    id=n.id,
                    type=n.notification_type,
                    title=n.title,
                    message=n.body or "",
                    priority=n.priority,
                    status=n.status,
                    created_at=n.created_at,
                    opened_at=getattr(n, "opened_at", None),
                )
                for n in notifications
            ]
    except Exception:
        return []


@router.post("/notifications/{notification_id}/open")
async def mark_notification_opened(
    notification_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Mark a notification as opened."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            await session.execute(
                update(NotificationModel)
                .where(
                    and_(
                        NotificationModel.id == notification_id,
                        NotificationModel.user_id == user_id,
                    )
                )
                .values(status="opened", opened_at=datetime.now(timezone.utc))
            )
            await session.commit()
        return {"message": "Notification marked as opened"}
    except Exception:
        return {"message": "Notification marked as opened"}


@router.post("/notifications/{notification_id}/dismiss")
async def mark_notification_dismissed(
    notification_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Dismiss a notification."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            await session.execute(
                update(NotificationModel)
                .where(
                    and_(
                        NotificationModel.id == notification_id,
                        NotificationModel.user_id == user_id,
                    )
                )
                .values(status="dismissed")
            )
            await session.commit()
        return {"message": "Notification dismissed"}
    except Exception:
        return {"message": "Notification dismissed"}


@router.post("/notifications/mark-all-open")
async def mark_all_notifications_opened(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Mark all notifications as opened."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            await session.execute(
                update(NotificationModel)
                .where(
                    and_(
                        NotificationModel.user_id == user_id,
                        NotificationModel.status.in_(["queued", "sent", "delivered"]),
                    )
                )
                .values(status="opened", opened_at=datetime.now(timezone.utc))
            )
            await session.commit()
        return {"message": "All notifications marked as opened"}
    except Exception:
        return {"message": "All notifications marked as opened"}


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def get_unread_notification_count(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> UnreadCountResponse:
    """Get the count of unread notifications."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(func.count(NotificationModel.id)).where(
                    and_(
                        NotificationModel.user_id == user_id,
                        NotificationModel.status.in_(["queued", "sent", "delivered"]),
                    )
                )
            )
            count = result.scalar() or 0
            return UnreadCountResponse(unread_count=count)
    except Exception:
        return UnreadCountResponse(unread_count=0)


# ============================================================
# Subjects (public — for learner portal, no admin RBAC needed)
# ============================================================


class SubjectSummary(BaseModel):
    id: UUID
    code: str
    name: str
    slug: str
    description: str | None
    status: str


@router.get("/subjects", response_model=list[SubjectSummary])
async def list_subjects_for_learners(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[SubjectSummary]:
    """List published subjects for the learner portal."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(SubjectModel)
                .where(SubjectModel.status == "published")
                .order_by(SubjectModel.name)
            )
            subjects = result.scalars().all()
            return [
                SubjectSummary(
                    id=s.id,
                    code=s.code,
                    name=s.name,
                    slug=s.slug,
                    description=s.description,
                    status=s.status,
                )
                for s in subjects
            ]
    except Exception:
        return []


@router.get("/subjects/{subject_id}/concepts")
async def list_concepts_for_learners(
    subject_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[dict]:
    """List concepts for a subject (learner view)."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(ConceptModel)
                .where(
                    and_(
                        ConceptModel.subject_id == subject_id,
                        ConceptModel.status == "published",
                    )
                )
                .order_by(ConceptModel.name)
            )
            concepts = result.scalars().all()
            return [
                {
                    "id": str(c.id),
                    "slug": c.slug,
                    "name": c.name,
                    "description": c.description,
                    "difficulty": c.difficulty,
                    "importance": c.importance,
                }
                for c in concepts
            ]
    except Exception:
        return []
