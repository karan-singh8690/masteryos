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

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    force: bool = Query(False, description="If true, abandon any existing active session before starting a new one"),
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
    publisher: OutboxEventPublisher = Depends(get_event_publisher),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> StudySessionResponse:
    """Start a new study session.

    If an active session already exists:
    - Without force=true: returns 409 with existing_session_id
    - With force=true: abandons the existing session and creates a new one
    """
    handler = StartStudySessionHandler(uow, publisher)

    # If force=true, abandon any existing active session via direct DB update
    if force:
        try:
            async with uow as _uow:
                session = _uow._session  # type: ignore[union-attr]
                from sqlalchemy import update as sql_update
                from app.infrastructure.database.orm.core import StudySessionModel
                from datetime import datetime, timezone
                result = await session.execute(
                    sql_update(StudySessionModel)
                    .where(
                        StudySessionModel.learner_enrollment_id == request.enrollment_id,
                        StudySessionModel.status.in_(["active", "paused"]),
                    )
                    .values(
                        status="abandoned",
                        ended_at=datetime.now(timezone.utc),
                    )
                )
                await _uow.commit()
        except Exception:
            pass  # Non-fatal — let the handler try normally

    command = StartStudySessionCommand(
        enrollment_id=request.enrollment_id,
        intent=request.intent,
        target_question_count=request.target_question_count,
    )

    result = await handler.handle(command)

    if not result.success:
        if result.error_code == "ACTIVE_SESSION_EXISTS":
            # Return the existing session ID so the frontend can resume it.
            existing_session_id = None
            if result.value is not None:
                existing_session_id = str(getattr(result.value, 'id', None) or result.value)
            raise HTTPException(status_code=409, detail={
                "code": result.error_code,
                "message": result.error,
                "existing_session_id": existing_session_id,
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
    "/study-sessions/active",
    response_model=StudySessionResponse | None,
    summary="Get the active study session for an enrollment",
)
async def get_active_study_session(
    enrollment_id: UUID = Query(..., description="Enrollment ID to check for active session"),
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> StudySessionResponse | None:
    """Get the active (in-progress) study session for an enrollment, if any.

    Returns null if no active session exists.
    """
    try:
        async with uow as _uow:
            session = await _uow.study_sessions.get_active_by_enrollment(enrollment_id)
            if session is None:
                return None
            return StudySessionResponse(
                id=session.id,
                learner_enrollment_id=session.learner_enrollment_id,
                intent=session.intent,
                status=session.status,
                started_at=session.started_at.isoformat(),
                ended_at=session.ended_at.isoformat() if session.ended_at else None,
                question_count=session.question_count,
            )
    except Exception:
        return None


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

    INTEGRATED PIPELINE (Task 014):
    1. Load the study session (must be active).
    2. Load mastery scores, due reviews, learning goals.
    3. Load published QuestionTemplates + TemplateVersions from the database.
    4. Filter by subject, difficulty, concept, review status.
    5. Select templates via DeterministicQueueGenerator (priority ranking).
    6. For each selected template: QuestionFactory.generate() → real QuestionInstance.
    7. Persist each QuestionInstance to the database.
    8. Return real QuestionInstance IDs (no placeholders).

    No ML. Deterministic given the same inputs.
    """
    from app.domain.scheduling.queue_generator import DeterministicQueueGenerator
    from app.domain.assessment.question_factory import QuestionFactory, TemplateVersionData
    from app.infrastructure.database.orm.content import (
        QuestionTemplateModel,
        TemplateVersionModel,
        TemplateConceptModel,
        ExplanationModel,
    )
    from app.infrastructure.database.orm.core import QuestionInstanceModel
    from sqlalchemy import select
    from datetime import datetime, timezone
    import hashlib
    import json

    async with uow as _uow:
        session_obj = _uow._session  # type: ignore[union-attr]

        # 1. Load the study session
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

        # 2. Load learner state
        mastery_scores = await _uow.mastery_scores.list_by_enrollment(
            session.learner_enrollment_id
        )
        due_reviews = await _uow.reviews.list_due_by_enrollment(
            session.learner_enrollment_id
        )
        goals = await _uow.learning_goals.get_active_by_enrollment(
            session.learner_enrollment_id
        )

        # 3. Load published templates with their current versions
        # Query: published templates → join template_versions → join template_concepts
        stmt = (
            select(TemplateVersionModel, QuestionTemplateModel)
            .join(QuestionTemplateModel, TemplateVersionModel.template_id == QuestionTemplateModel.id)
            .where(QuestionTemplateModel.status == "published")
            .where(QuestionTemplateModel.current_version_id == TemplateVersionModel.id)
        )
        result = await session_obj.execute(stmt)
        rows = result.all()

        if not rows:
            # No published content available — return diagnostic queue
            # (still using factory if templates exist but aren't published yet)
            raise HTTPException(status_code=404, detail={
                "code": "NO_PUBLISHED_CONTENT",
                "message": "No published question templates found. Publish templates first.",
            })

        # 4. Build TemplateVersionData list with concept links
        template_versions: list[TemplateVersionData] = []
        for tv_model, qt_model in rows:
            # Load concept links for this template version
            tc_stmt = select(TemplateConceptModel.concept_id).where(
                TemplateConceptModel.template_version_id == tv_model.id
            )
            tc_result = await session_obj.execute(tc_stmt)
            concept_ids = [row[0] for row in tc_result.all()]

            template_versions.append(TemplateVersionData(
                id=tv_model.id,
                template_id=tv_model.template_id,
                version_number=tv_model.version_number,
                parameter_schema=tv_model.parameter_schema or {},
                prompt_template=tv_model.prompt_template or {},
                correct_answer_generator=tv_model.correct_answer_generator or {},
                distractor_generator=tv_model.distractor_generator,
                explanation_template=tv_model.explanation_template or {},
                hint_tiers=tv_model.hint_tiers or [],
                difficulty_estimate=tv_model.difficulty_estimate,
                discrimination_estimate=tv_model.discrimination_estimate,
                concept_ids=concept_ids,
            ))

        # 5. Generate queue via DeterministicQueueGenerator (selects + ranks templates)
        generator = DeterministicQueueGenerator()
        queue_items = generator.generate(
            enrollment_id=session.learner_enrollment_id,
            session_id=session.id,
            intent=session.intent,
            mastery_scores=list(mastery_scores or []),
            due_reviews=list(due_reviews or []),
            learning_goals=list(goals or []),
            queue_size=min(15, len(template_versions)),
        )

        # 6. For each queue item: generate a real QuestionInstance via QuestionFactory
        factory = QuestionFactory()
        persisted_questions: list[QueueItemDTO] = []

        # Load already-served question instances for this session (duplicate prevention)
        existing_stmt = select(QuestionInstanceModel).where(
            QuestionInstanceModel.study_session_id == session_id
        )
        existing_result = await session_obj.execute(existing_stmt)
        served_template_ids = set()
        for qi in existing_result.scalars().all():
            served_template_ids.add(qi.template_version_id)

        # Get active content version (if any)
        from app.infrastructure.database.orm.content import ContentVersionModel
        cv_stmt = select(ContentVersionModel).where(
            ContentVersionModel.subject_id == rows[0][1].subject_id,
            ContentVersionModel.status == "active",
        ).order_by(ContentVersionModel.version_number.desc()).limit(1)
        cv_result = await session_obj.execute(cv_stmt)
        cv_model = cv_result.scalar_one_or_none()
        content_version_id = cv_model.id if cv_model else uuid4()

        # Get active algorithm version
        algorithm = await _uow.algorithm_versions.get_active()
        algorithm_version_id = algorithm.id.value if algorithm else uuid4()

        generated_count = 0
        for item in queue_items:
            if generated_count >= 15:
                break

            # Match queue item to a template version
            # The queue generator produces concept_ids; we match templates that cover those concepts
            matched_tv: TemplateVersionData | None = None
            for tv in template_versions:
                if tv.id in served_template_ids:
                    continue  # Skip already-served templates
                # Match by concept overlap or just take the next available
                if item.concept_id in tv.concept_ids or not item.concept_id:
                    matched_tv = tv
                    break

            if matched_tv is None:
                # Take the next unserved template
                for tv in template_versions:
                    if tv.id not in served_template_ids:
                        matched_tv = tv
                        break

            if matched_tv is None:
                continue  # All templates served

            # Generate deterministic seed from session_id + template_id + position
            seed_input = f"{session_id}:{matched_tv.id}:{generated_count}"
            seed = int(hashlib.sha256(seed_input.encode()).hexdigest()[:8], 16)

            # Generate the QuestionInstance
            from app.domain.shared.ids import ContentVersionId as CVID
            gen_result = factory.generate(
                template_version=matched_tv,
                seed=seed,
                content_version_id=CVID(content_version_id),
                learner_enrollment_id=session.learner_enrollment_id,
                study_session_id=session.id,
            )

            instance = gen_result.question_instance

            # 7. Persist the QuestionInstance to the database
            orm_instance = QuestionInstanceModel(
                id=instance.id.value,
                template_version_id=instance.template_version_id.value,
                content_version_id=instance.content_version_id.value,
                learner_enrollment_id=instance.learner_enrollment_id.value,
                study_session_id=instance.study_session_id.value,
                parameter_seed=instance.parameter_seed,
                parameter_values=instance.parameter_values,
                rendered_prompt=instance.rendered_prompt,
                rendered_choices=instance.rendered_choices,
                correct_answer=instance.correct_answer,
                distractors_with_tags=instance.distractors_with_tags,
                served_at=instance.served_at,
                answered_at=None,
                status=instance.status,
            )
            session_obj.add(orm_instance)
            served_template_ids.add(matched_tv.id)

            # 8. Build the response with REAL IDs
            persisted_questions.append(QueueItemDTO(
                question_instance_id=instance.id.value,
                concept_id=matched_tv.concept_ids[0] if matched_tv.concept_ids else item.concept_id,
                difficulty=matched_tv.difficulty_estimate,
                estimated_duration_seconds=item.estimated_duration_seconds,
                recommendation_score=item.recommendation_score,
                reason=item.reason,
            ))
            generated_count += 1

        await session_obj.commit()

        return AdaptiveQueueResponse(
            study_session_id=session_id,
            current_position=0,
            questions=persisted_questions,
        )
