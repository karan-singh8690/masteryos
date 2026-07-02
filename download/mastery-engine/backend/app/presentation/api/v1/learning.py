"""Learning API routes — enroll, set goal, start session, get adaptive queue.

Maps to the OpenAPI contract (Task 006):
- POST /enrollments
- POST /enrollments/{id}/learning-goals
- POST /study-sessions
- GET /study-sessions/{id}/adaptive-queue
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.application.learning.dto import (
    EnrollLearnerCommand,
    SetLearningGoalCommand,
    StartStudySessionCommand,
    EnrollmentDTO,
    StudySessionDTO,
)
from app.application.learning.handlers import (
    EnrollLearnerHandler,
    StartStudySessionHandler,
)
from app.application.shared import UnitOfWork
from app.presentation.dependencies import (
    OutboxEventPublisher,
    get_current_user_id,
    get_event_publisher,
    get_idempotency_key,
    get_uow,
)
from app.domain.learning.learning_goal import LearningGoal
from app.domain.shared.ids import LearnerEnrollmentId, StudySessionId
from app.domain.shared.kernel import GoalType
from app.shared.config import get_settings

router = APIRouter(tags=["Learning"])


# ============================================================
# Request/Response Models
# ============================================================


class EnrollRequest(BaseModel):
    subject_id: UUID


class EnrollmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    subject_id: UUID
    learning_path_id: UUID | None
    status: str
    enrolled_at: str
    onboarded_at: str | None
    last_active_at: str | None


class SetGoalRequest(BaseModel):
    goal_type: str = Field(description="interview_date, daily_commitment, session_intent, mastery_target")
    target_date: date | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class LearningGoalResponse(BaseModel):
    id: UUID
    enrollment_id: UUID
    goal_type: str
    target_date: str | None
    status: str


class StartSessionRequest(BaseModel):
    enrollment_id: UUID
    intent: str = Field(default="mixed", description="drill, diagnostic, review, mixed")
    target_question_count: int | None = Field(default=None, ge=1, le=50)


class StudySessionResponse(BaseModel):
    id: UUID
    learner_enrollment_id: UUID
    intent: str
    status: str
    started_at: str
    ended_at: str | None
    question_count: int


class QueueItemDTO(BaseModel):
    question_instance_id: UUID
    concept_id: UUID
    difficulty: str
    estimated_duration_seconds: int
    recommendation_score: float
    reason: str


class AdaptiveQueueResponse(BaseModel):
    study_session_id: UUID
    current_position: int
    questions: list[QueueItemDTO]


# ============================================================
# Endpoints
# ============================================================


@router.post(
    "/enrollments",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll in a subject",
)
async def enroll(
    request: EnrollRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
    publisher: OutboxEventPublisher = Depends(get_event_publisher),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> EnrollmentResponse:
    """Enroll the current user as a learner in a subject."""
    handler = EnrollLearnerHandler(uow, publisher)

    command = EnrollLearnerCommand(
        user_id=user_id,
        subject_id=request.subject_id,
    )

    result = await handler.handle(command)

    if not result.success:
        if result.error_code == "ALREADY_ENROLLED":
            raise HTTPException(status_code=409, detail={
                "code": result.error_code,
                "message": result.error,
            })
        raise HTTPException(status_code=422, detail={
            "code": result.error_code or "VALIDATION_FAILED",
            "message": result.error,
        })

    # Flush events to outbox
    async with uow as _uow:
        await publisher.flush_to_outbox(_uow._session, actor_user_id=user_id)  # type: ignore[union-attr]
        await _uow.commit()

    enrollment = result.value
    return EnrollmentResponse(
        id=enrollment.id,
        user_id=enrollment.user_id,
        subject_id=enrollment.subject_id,
        learning_path_id=enrollment.learning_path_id,
        status=enrollment.status,
        enrolled_at=enrollment.enrolled_at.isoformat(),
        onboarded_at=enrollment.onboarded_at.isoformat() if enrollment.onboarded_at else None,
        last_active_at=enrollment.last_active_at.isoformat() if enrollment.last_active_at else None,
    )


@router.post(
    "/enrollments/{enrollment_id}/learning-goals",
    response_model=LearningGoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set a learning goal",
)
async def set_learning_goal(
    enrollment_id: UUID,
    request: SetGoalRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
    publisher: OutboxEventPublisher = Depends(get_event_publisher),
) -> LearningGoalResponse:
    """Set a learning goal for an enrollment."""
    # Validate goal type
    try:
        goal_type = GoalType(request.goal_type)
    except ValueError:
        raise HTTPException(status_code=422, detail={
            "code": "INVALID_GOAL_TYPE",
            "message": f"Invalid goal type: {request.goal_type}",
        })

    # Create the goal via domain
    from app.domain.shared.ids import LearnerEnrollmentId
    async with uow as _uow:
        # Verify enrollment exists and belongs to user
        enrollment = await _uow.enrollments.get_by_id(LearnerEnrollmentId(enrollment_id))
        if enrollment is None:
            raise HTTPException(status_code=404, detail={
                "code": "ENROLLMENT_NOT_FOUND",
                "message": "Enrollment not found",
            })
        if enrollment.user_id.value != user_id:
            raise HTTPException(status_code=403, detail={
                "code": "NOT_AUTHORIZED",
                "message": "Not your enrollment",
            })

        # Check for existing active time-bound goal
        if goal_type == GoalType.INTERVIEW_DATE:
            existing = await _uow.learning_goals.get_active_by_enrollment(enrollment.id)
            for g in existing:
                if g.is_time_bound and g.is_active:
                    raise HTTPException(status_code=422, detail={
                        "code": "MULTIPLE_TIME_BOUND_GOALS",
                        "message": "Only one active time-bound goal allowed",
                    })

        goal = LearningGoal.set(
            learner_enrollment_id=enrollment.id,
            goal_type=goal_type,
            target_date=request.target_date,
            parameters=request.parameters,
        )

        await _uow.learning_goals.add(goal)
        events = goal.collect_events()
        await publisher.flush_to_outbox(_uow._session, actor_user_id=user_id)  # type: ignore[union-attr]
        await _uow.commit()

    return LearningGoalResponse(
        id=goal.id.value,
        enrollment_id=enrollment_id,
        goal_type=goal.goal_type.value,
        target_date=goal.target_date.isoformat() if goal.target_date else None,
        status=goal.status.value,
    )


@router.post(
    "/study-sessions",
    response_model=StudySessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a study session",
)
async def start_study_session(
    request: StartSessionRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
    publisher: OutboxEventPublisher = Depends(get_event_publisher),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> StudySessionResponse:
    """Start a new study session."""
    handler = StartStudySessionHandler(uow, publisher)

    command = StartStudySessionCommand(
        enrollment_id=request.enrollment_id,
        intent=request.intent,
        target_question_count=request.target_question_count,
    )

    result = await handler.handle(command)

    if not result.success:
        if result.error_code == "ACTIVE_SESSION_EXISTS":
            raise HTTPException(status_code=409, detail={
                "code": result.error_code,
                "message": result.error,
            })
        if result.error_code == "VALIDATION_FAILED":
            raise HTTPException(status_code=422, detail={
                "code": result.error_code,
                "message": result.error,
            })
        raise HTTPException(status_code=500, detail={
            "code": result.error_code or "INTERNAL_ERROR",
            "message": result.error,
        })

    # Flush events
    async with uow as _uow:
        await publisher.flush_to_outbox(_uow._session, actor_user_id=user_id)  # type: ignore[union-attr]
        await _uow.commit()

    session = result.value
    return StudySessionResponse(
        id=session.id,
        learner_enrollment_id=session.learner_enrollment_id,
        intent=session.intent,
        status=session.status,
        started_at=session.started_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
        question_count=session.question_count,
    )


@router.get(
    "/study-sessions/{session_id}/adaptive-queue",
    response_model=AdaptiveQueueResponse,
    summary="Get the adaptive queue for a study session",
)
async def get_adaptive_queue(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> AdaptiveQueueResponse:
    """Get the adaptive queue for the current study session.

    The queue is generated deterministically based on:
    - The learner's current mastery scores
    - Due reviews
    - Weak concepts
    - The learning goal (if set)
    - The session intent

    No ML. Deterministic given the same inputs.
    """
    from app.domain.scheduling.queue_generator import DeterministicQueueGenerator

    async with uow as _uow:
        # Load the study session
        session = await _uow.study_sessions.get_by_id(StudySessionId(session_id))
        if session is None:
            raise HTTPException(status_code=404, detail={
                "code": "SESSION_NOT_FOUND",
                "message": "Study session not found",
            })

        if not session.is_active:
            raise HTTPException(status_code=409, detail={
                "code": "SESSION_NOT_ACTIVE",
                "message": f"Session is not active (status: {session.status})",
            })

        # Load mastery scores for the learner
        mastery_scores = await _uow.mastery_scores.list_by_enrollment(
            session.learner_enrollment_id
        )

        # Load due reviews
        due_reviews = await _uow.reviews.list_due_by_enrollment(
            session.learner_enrollment_id
        )

        # Load learning goals
        goals = await _uow.learning_goals.get_active_by_enrollment(
            session.learner_enrollment_id
        )

        # Generate the queue deterministically
        generator = DeterministicQueueGenerator()
        queue_items = generator.generate(
            enrollment_id=session.learner_enrollment_id,
            session_id=session.id,
            intent=session.intent,
            mastery_scores=list(mastery_scores),
            due_reviews=list(due_reviews),
            learning_goals=list(goals),
            queue_size=15,
        )

        return AdaptiveQueueResponse(
            study_session_id=session_id,
            current_position=0,
            questions=[
                QueueItemDTO(
                    question_instance_id=item.question_instance_id,
                    concept_id=item.concept_id,
                    difficulty=item.difficulty,
                    estimated_duration_seconds=item.estimated_duration_seconds,
                    recommendation_score=item.recommendation_score,
                    reason=item.reason,
                )
                for item in queue_items
            ],
        )
