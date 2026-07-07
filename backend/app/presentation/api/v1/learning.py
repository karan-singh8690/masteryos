"""Learning API routes — enroll, set goal, start session, get adaptive queue.

Maps to the OpenAPI contract (Task 006):
- POST /enrollments
- POST /enrollments/{id}/learning-goals
- POST /study-sessions
- GET /study-sessions/{id}/adaptive-queue
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4
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


# ============================================================
# Phase 1 Indian Localization: Exam Settings
# ============================================================


class ExamSettingsRequest(BaseModel):
    """Request: set exam date + negative marking for an enrollment."""
    target_exam_date: str | None = None
    target_exam_name: str | None = None
    negative_marking_factor: float = Field(default=0.0, ge=0.0, le=1.0, description="e.g., 0.25 for -1/4 marking")


@router.patch(
    "/enrollments/{enrollment_id}/exam-settings",
    summary="Set exam date + negative marking (Phase 1 Indian localization)",
)
async def set_exam_settings(
    enrollment_id: UUID,
    request: ExamSettingsRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Set the target exam date, exam name, and negative marking factor for an enrollment.

    This enables:
    - Exam countdown on the dashboard
    - Exam proximity scheduling (review intervals shrink as exam approaches)
    - Negative marking in scoring (marks deducted for wrong answers)
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import LearnerEnrollmentModel
            from sqlalchemy import update as sql_update
            from datetime import datetime

            values = {}
            if request.target_exam_date is not None:
                values["target_exam_date"] = datetime.fromisoformat(request.target_exam_date)
            if request.target_exam_name is not None:
                values["target_exam_name"] = request.target_exam_name
            if request.negative_marking_factor is not None:
                values["negative_marking_factor"] = request.negative_marking_factor

            if values:
                await session_obj.execute(
                    sql_update(LearnerEnrollmentModel)
                    .where(LearnerEnrollmentModel.id == enrollment_id)
                    .values(**values)
                )
                await _uow.commit()

        return {
            "message": "Exam settings updated",
            "target_exam_date": request.target_exam_date,
            "target_exam_name": request.target_exam_name,
            "negative_marking_factor": request.negative_marking_factor,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Phase 2 Indian Localization: Concept Dependencies + Exam Weightage
# ============================================================


class ConceptDependencyRequest(BaseModel):
    """Request: add a prerequisite to a concept."""
    prerequisite_concept_id: UUID
    min_mastery: float = Field(default=0.3, ge=0.0, le=1.0)


@router.post(
    "/concepts/{concept_id}/prerequisites",
    summary="Add a prerequisite to a concept (Phase 2)",
)
async def add_concept_prerequisite(
    concept_id: UUID,
    request: ConceptDependencyRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Add a prerequisite relationship between concepts."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.content import ConceptDependencyModel
            dep = ConceptDependencyModel(
                concept_id=concept_id,
                prerequisite_concept_id=request.prerequisite_concept_id,
                min_mastery=request.min_mastery,
            )
            session_obj.add(dep)
            await _uow.commit()
        return {"message": "Prerequisite added", "min_mastery": request.min_mastery}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/concepts/{concept_id}/prerequisites",
    summary="List prerequisites for a concept (Phase 2)",
)
async def list_concept_prerequisites(
    concept_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[dict]:
    """List all prerequisites for a concept."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.content import ConceptDependencyModel, ConceptModel
            result = await session_obj.execute(
                select(ConceptDependencyModel, ConceptModel).join(
                    ConceptModel,
                    ConceptDependencyModel.prerequisite_concept_id == ConceptModel.id
                ).where(ConceptDependencyModel.concept_id == concept_id)
            )
            return [
                {
                    "prerequisite_concept_id": str(dep.prerequisite_concept_id),
                    "prerequisite_name": concept.name,
                    "min_mastery": dep.min_mastery,
                }
                for dep, concept in result.all()
            ]
    except Exception:
        return []


class ExamWeightageRequest(BaseModel):
    """Request: set exam weightage for a concept."""
    exam_name: str
    weightage: float = Field(ge=0.0, le=1.0, description="0.0-1.0, e.g., 0.25 for 25%")
    topic_cluster: str | None = None


@router.post(
    "/concepts/{concept_id}/exam-weightage",
    summary="Set exam weightage for a concept (Phase 2)",
)
async def set_exam_weightage(
    concept_id: UUID,
    request: ExamWeightageRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Set the weightage of a concept for a specific exam."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.content import ExamWeightageModel
            from sqlalchemy import update as sql_update
            existing = await session_obj.execute(
                select(ExamWeightageModel).where(
                    ExamWeightageModel.exam_name == request.exam_name,
                    ExamWeightageModel.concept_id == concept_id,
                )
            )
            if existing.scalar_one_or_none():
                await session_obj.execute(
                    sql_update(ExamWeightageModel).where(
                        ExamWeightageModel.exam_name == request.exam_name,
                        ExamWeightageModel.concept_id == concept_id,
                    ).values(weightage=request.weightage, topic_cluster=request.topic_cluster)
                )
            else:
                w = ExamWeightageModel(
                    exam_name=request.exam_name,
                    concept_id=concept_id,
                    weightage=request.weightage,
                    topic_cluster=request.topic_cluster,
                )
                session_obj.add(w)
            await _uow.commit()
        return {"message": "Exam weightage set", "exam_name": request.exam_name, "weightage": request.weightage}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/exam-weightage/{exam_name}",
    summary="Get exam weightage for all concepts (Phase 2)",
)
async def get_exam_weightage(
    exam_name: str,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[dict]:
    """Get the weightage of all concepts for a specific exam."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.content import ExamWeightageModel, ConceptModel
            result = await session_obj.execute(
                select(ExamWeightageModel, ConceptModel).join(
                    ConceptModel,
                    ExamWeightageModel.concept_id == ConceptModel.id
                ).where(ExamWeightageModel.exam_name == exam_name)
            )
            return [
                {
                    "concept_id": str(w.concept_id),
                    "concept_name": concept.name,
                    "weightage": w.weightage,
                    "topic_cluster": w.topic_cluster,
                }
                for w, concept in result.all()
            ]
    except Exception:
        return []


# ============================================================
# Phase 3 Indian Localization: Mock Test Mode
# ============================================================


class CreateMockTestRequest(BaseModel):
    """Request: create a mock test."""
    enrollment_id: UUID
    exam_name: str = "Mock Test"
    total_questions: int = Field(default=30, ge=5, le=100)
    time_limit_minutes: int = Field(default=180, ge=10, le=300)
    negative_marking_factor: float = Field(default=0.25, ge=0.0, le=1.0)


@router.post(
    "/mock-tests",
    summary="Create a mock test (Phase 3 — exam-realistic mode)",
)
async def create_mock_test(
    request: CreateMockTestRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Create a mock test with exam-realistic conditions:
    - Fixed time limit
    - Negative marking
    - Fixed question count
    - No hints allowed
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import MockTestModel
            from uuid import uuid4

            mock = MockTestModel(
                id=uuid4(),
                learner_enrollment_id=request.enrollment_id,
                exam_name=request.exam_name,
                total_questions=request.total_questions,
                time_limit_minutes=request.time_limit_minutes,
                negative_marking_factor=request.negative_marking_factor,
                max_marks=float(request.total_questions),
            )
            session_obj.add(mock)
            await _uow.commit()

        return {
            "id": str(mock.id),
            "exam_name": request.exam_name,
            "total_questions": request.total_questions,
            "time_limit_minutes": request.time_limit_minutes,
            "negative_marking_factor": request.negative_marking_factor,
            "status": "not_started",
            "message": "Mock test created. Start it to begin the timer.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/mock-tests/{mock_test_id}/start",
    summary="Start a mock test (begins the timer)",
)
async def start_mock_test(
    mock_test_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Start the mock test — timer begins now."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import MockTestModel
            from sqlalchemy import update as sql_update
            from datetime import datetime, timezone

            await session_obj.execute(
                sql_update(MockTestModel)
                .where(MockTestModel.id == mock_test_id)
                .values(status="in_progress", started_at=datetime.now(timezone.utc))
            )
            await _uow.commit()

        return {"message": "Mock test started. Timer is running."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/mock-tests/{mock_test_id}/submit",
    summary="Submit a mock test (calculate results)",
)
class MockTestResultsRequest(BaseModel):
    """Request: submit mock test results."""
    correct: int = 0
    wrong: int = 0
    unattempted: int = 0


async def submit_mock_test(
    mock_test_id: UUID,
    request: MockTestResultsRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Submit the mock test and calculate results including negative marking."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import MockTestModel
            from sqlalchemy import update as sql_update
            from datetime import datetime, timezone

            mock_result = await session_obj.execute(
                select(MockTestModel).where(MockTestModel.id == mock_test_id)
            )
            mock = mock_result.scalar_one_or_none()
            if not mock:
                raise HTTPException(status_code=404, detail="Mock test not found")

            correct = request.correct
            wrong = request.wrong
            unattempted = request.unattempted or (mock.total_questions - correct - wrong)
            attempted = correct + wrong

            marks = correct - (wrong * mock.negative_marking_factor)
            accuracy = (correct / attempted) if attempted > 0 else 0.0

            await session_obj.execute(
                sql_update(MockTestModel)
                .where(MockTestModel.id == mock_test_id)
                .values(
                    status="completed",
                    ended_at=datetime.now(timezone.utc),
                    total_attempted=attempted,
                    total_correct=correct,
                    total_wrong=wrong,
                    total_unattempted=unattempted,
                    marks_scored=marks,
                    accuracy=round(accuracy, 4),
                )
            )
            await _uow.commit()

        return {
            "id": str(mock_test_id),
            "status": "completed",
            "total_questions": mock.total_questions,
            "attempted": attempted,
            "correct": correct,
            "wrong": wrong,
            "unattempted": unattempted,
            "marks_scored": marks,
            "max_marks": mock.max_marks,
            "accuracy": round(accuracy, 4),
            "negative_marking_factor": mock.negative_marking_factor,
            "time_limit_minutes": mock.time_limit_minutes,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/mock-tests/{mock_test_id}",
    summary="Get mock test details + results",
)
async def get_mock_test(
    mock_test_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get mock test details and results."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import MockTestModel
            result = await session_obj.execute(
                select(MockTestModel).where(MockTestModel.id == mock_test_id)
            )
            mock = result.scalar_one_or_none()
            if not mock:
                raise HTTPException(status_code=404, detail="Mock test not found")

            return {
                "id": str(mock.id),
                "exam_name": mock.exam_name,
                "total_questions": mock.total_questions,
                "time_limit_minutes": mock.time_limit_minutes,
                "negative_marking_factor": mock.negative_marking_factor,
                "status": mock.status,
                "started_at": mock.started_at.isoformat() if mock.started_at else None,
                "ended_at": mock.ended_at.isoformat() if mock.ended_at else None,
                "results": {
                    "attempted": mock.total_attempted,
                    "correct": mock.total_correct,
                    "wrong": mock.total_wrong,
                    "unattempted": mock.total_unattempted,
                    "marks_scored": mock.marks_scored,
                    "max_marks": mock.max_marks,
                    "accuracy": mock.accuracy,
                } if mock.status == "completed" else None,
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Phase 3 Indian Localization: Community Doubt Solving
# ============================================================


class PostDoubtRequest(BaseModel):
    """Request: post a doubt."""
    title: str = Field(max_length=200)
    description: str
    question_instance_id: UUID | None = None
    concept_id: UUID | None = None
    screenshot_url: str | None = None
    language: str = Field(default="en", max_length=10)


@router.post(
    "/doubts",
    summary="Post a doubt (Phase 3 — community doubt solving)",
)
async def post_doubt(
    request: PostDoubtRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Post a doubt to the community. Costs 5 coins.

    Other users can answer to earn 10 coins + 2 mastery points.
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import DoubtModel, UserCoinModel
            from uuid import uuid4
            from sqlalchemy import update as sql_update

            # Check coin balance + deduct 5 coins
            coin_result = await session_obj.execute(
                select(UserCoinModel).where(UserCoinModel.user_id == user_id)
            )
            coins = coin_result.scalar_one_or_none()
            if coins is None:
                # Auto-create coin account with 100 starting coins
                coins = UserCoinModel(user_id=user_id, balance=100, total_earned=100, total_spent=0)
                session_obj.add(coins)
                await session_obj.flush()

            if coins.balance < 5:
                raise HTTPException(status_code=402, detail={
                    "code": "INSUFFICIENT_COINS",
                    "message": f"Not enough coins. You have {coins.balance}, need 5. Answer doubts to earn more.",
                })

            await session_obj.execute(
                sql_update(UserCoinModel)
                .where(UserCoinModel.user_id == user_id)
                .values(balance=UserCoinModel.balance - 5, total_spent=UserCoinModel.total_spent + 5)
            )

            doubt = DoubtModel(
                id=uuid4(),
                posted_by_user_id=user_id,
                question_instance_id=request.question_instance_id,
                concept_id=request.concept_id,
                title=request.title,
                description=request.description,
                screenshot_url=request.screenshot_url,
                language=request.language,
            )
            session_obj.add(doubt)
            await _uow.commit()

        return {"id": str(doubt.id), "message": "Doubt posted. Cost: 5 coins."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/doubts",
    summary="List open doubts (Phase 3)",
)
async def list_doubts(
    status_filter: str = Query("open", alias="status"),
    concept_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """List doubts — filter by status, concept, or language."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import DoubtModel
            from app.infrastructure.database.orm.identity import UserModel

            query = (
                select(DoubtModel, UserModel.email)
                .outerjoin(UserModel, DoubtModel.posted_by_user_id == UserModel.id)
                .where(DoubtModel.status == status_filter)
            )
            if concept_id:
                query = query.where(DoubtModel.concept_id == concept_id)

            query = query.order_by(DoubtModel.upvotes.desc(), DoubtModel.created_at.desc())
            query = query.offset((page - 1) * page_size).limit(page_size)

            result = await session_obj.execute(query)
            rows = result.all()

            return {
                "items": [
                    {
                        "id": str(d.id),
                        "title": d.title,
                        "description": d.description[:200] + "..." if len(d.description) > 200 else d.description,
                        "posted_by": email or "Anonymous",
                        "language": d.language,
                        "upvotes": d.upvotes,
                        "view_count": d.view_count,
                        "status": d.status,
                        "created_at": d.created_at.isoformat() if d.created_at else None,
                        "screenshot_url": d.screenshot_url,
                    }
                    for d, email in rows
                ],
                "page": page,
                "page_size": page_size,
            }
    except Exception:
        return {"items": [], "page": page, "page_size": page_size}


class AnswerDoubtRequest(BaseModel):
    """Request: answer a doubt."""
    content: str
    language: str = Field(default="en", max_length=10)


@router.post(
    "/doubts/{doubt_id}/answers",
    summary="Answer a doubt (Phase 3 — earn 10 coins)",
)
async def answer_doubt(
    doubt_id: UUID,
    request: AnswerDoubtRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Answer a doubt. Earn 10 coins + update doubt status to 'answered'."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import DoubtModel, DoubtAnswerModel, UserCoinModel
            from uuid import uuid4
            from sqlalchemy import update as sql_update

            # Post the answer
            answer = DoubtAnswerModel(
                id=uuid4(),
                doubt_id=doubt_id,
                answered_by_user_id=user_id,
                content=request.content,
                language=request.language,
            )
            session_obj.add(answer)

            # Update doubt status
            await session_obj.execute(
                sql_update(DoubtModel)
                .where(DoubtModel.id == doubt_id)
                .values(status="answered")
            )

            # Award 10 coins to the answerer
            coin_result = await session_obj.execute(
                select(UserCoinModel).where(UserCoinModel.user_id == user_id)
            )
            coins = coin_result.scalar_one_or_none()
            if coins is None:
                coins = UserCoinModel(user_id=user_id, balance=110, total_earned=110, total_spent=0)
                session_obj.add(coins)
            else:
                await session_obj.execute(
                    sql_update(UserCoinModel)
                    .where(UserCoinModel.user_id == user_id)
                    .values(balance=UserCoinModel.balance + 10, total_earned=UserCoinModel.total_earned + 10)
                )

            await _uow.commit()

        return {"id": str(answer.id), "message": "Answer posted. Earned 10 coins!"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/doubts/{doubt_id}/answers",
    summary="List answers for a doubt (Phase 3)",
)
async def list_doubt_answers(
    doubt_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[dict]:
    """List all answers for a doubt, sorted by upvotes."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import DoubtAnswerModel
            from app.infrastructure.database.orm.identity import UserModel

            result = await session_obj.execute(
                select(DoubtAnswerModel, UserModel.email)
                .outerjoin(UserModel, DoubtAnswerModel.answered_by_user_id == UserModel.id)
                .where(DoubtAnswerModel.doubt_id == doubt_id)
                .order_by(DoubtAnswerModel.upvotes.desc(), DoubtAnswerModel.created_at.asc())
            )
            return [
                {
                    "id": str(a.id),
                    "content": a.content,
                    "answered_by": email or "Anonymous",
                    "language": a.language,
                    "upvotes": a.upvotes,
                    "is_verified": a.is_verified,
                    "status": a.status,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a, email in result.all()
            ]
    except Exception:
        return []


@router.get(
    "/coins",
    summary="Get coin balance (Phase 3)",
)
async def get_coin_balance(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get the current user's coin balance + earned/spent totals."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import UserCoinModel
            result = await session_obj.execute(
                select(UserCoinModel).where(UserCoinModel.user_id == user_id)
            )
            coins = result.scalar_one_or_none()
            if coins is None:
                # Auto-create with 100 starting coins
                coins = UserCoinModel(user_id=user_id, balance=100, total_earned=100, total_spent=0)
                session_obj.add(coins)
                await _uow.commit()

            return {
                "balance": coins.balance,
                "total_earned": coins.total_earned,
                "total_spent": coins.total_spent,
            }
    except Exception:
        return {"balance": 100, "total_earned": 100, "total_spent": 0}


# ============================================================
# Phase 3 Indian Localization: UPI Payment + India Pricing
# ============================================================


class UpiPaymentRequest(BaseModel):
    """Request: create a UPI payment order."""
    plan: str = Field(description="free, plus, pro, coaching")
    upi_id: str = Field(description="User's UPI ID (e.g., user@paytm)")
    months: int = Field(default=1, ge=1, le=12)


# India-specific pricing in ₹
INDIA_PRICING = {
    "free": {"monthly": 0, "name": "Free", "features": ["All content", "Adaptive engine", "Mastery tracking"]},
    "plus": {"monthly": 99, "name": "Plus", "features": ["Everything in Free", "Mock tests", "PYQs", "Performance analytics"]},
    "pro": {"monthly": 299, "name": "Pro", "features": ["Everything in Plus", "AI explanations", "Doubt solving", "Community", "Offline mode"]},
    "coaching": {"monthly": 999, "name": "Coaching", "features": ["Everything in Pro", "Live sessions", "Mentor", "Custom study plan"]},
}


@router.get(
    "/billing/plans-inr",
    summary="Get India-specific pricing in ₹ (Phase 3)",
)
async def get_india_pricing(
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    """Get pricing tiers for the Indian market in Rupees."""
    return {
        "currency": "INR",
        "plans": INDIA_PRICING,
        "payment_methods": ["UPI", "PhonePe", "Google Pay", "Paytm", "Card"],
        "note": "Prices in ₹. UPI is the preferred payment method in India.",
    }


@router.post(
    "/billing/upi-payment",
    summary="Create a UPI payment order (Phase 3)",
)
async def create_upi_payment(
    request: UpiPaymentRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Create a UPI payment order.

    In production, this would integrate with Razorpay/UPI Gateway.
    For now, it creates a payment record and returns UPI intent URL.
    """
    try:
        plan = INDIA_PRICING.get(request.plan)
        if not plan:
            raise HTTPException(status_code=422, detail=f"Invalid plan. Must be one of: {list(INDIA_PRICING.keys())}")

        if plan["monthly"] == 0:
            raise HTTPException(status_code=422, detail="Free plan doesn't require payment")

        amount = plan["monthly"] * request.months
        amount_paise = amount * 100  # UPI expects amount in paise

        # In production: integrate with Razorpay/UPI gateway here
        # For now: generate a UPI intent URL
        upi_intent = f"upi://pay?pa=masteryos@upi&pn=MasteryOS&am={amount}&cu=INR&tn={request.plan}_plan_{request.months}m"

        return {
            "status": "pending",
            "plan": request.plan,
            "plan_name": plan["name"],
            "amount": amount,
            "amount_paise": amount_paise,
            "currency": "INR",
            "months": request.months,
            "upi_id": request.upi_id,
            "upi_intent_url": upi_intent,
            "message": f"Pay ₹{amount} via UPI to activate {plan['name']} for {request.months} month(s).",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Phase 4 Indian Localization: Delta Sync + Question Packs
# ============================================================


@router.get(
    "/sync/question-packs",
    summary="Download question packs for offline study (Phase 4)",
)
async def get_question_packs(
    subject_id: UUID | None = Query(None),
    exam_name: str | None = Query(None),
    since_version: int = Query(0, description="Only return packs newer than this version"),
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get question packs for offline download.

    - First sync: returns all packs (full download ~50-200 KB each)
    - Delta sync: pass since_version=N to get only packs with version > N
    - Each pack contains questions + answers + explanations as a JSON blob
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import QuestionPackModel

            query = select(QuestionPackModel).where(QuestionPackModel.version > since_version)
            if subject_id:
                query = query.where(QuestionPackModel.subject_id == subject_id)
            if exam_name:
                query = query.where(QuestionPackModel.exam_name == exam_name)

            result = await session_obj.execute(query.order_by(QuestionPackModel.version.desc()))
            packs = result.scalars().all()

            return {
                "packs": [
                    {
                        "id": str(p.id),
                        "name": p.name,
                        "description": p.description,
                        "subject_id": str(p.subject_id),
                        "exam_name": p.exam_name,
                        "version": p.version,
                        "question_count": p.question_count,
                        "pack_size_kb": p.pack_size_kb,
                        "checksum": p.checksum,
                        "pack_data": p.pack_data,
                    }
                    for p in packs
                ],
                "latest_version": max((p.version for p in packs), default=0),
                "total_packs": len(packs),
            }
    except Exception:
        return {"packs": [], "latest_version": 0, "total_packs": 0}


@router.post(
    "/sync/offline-results",
    summary="Sync offline study results (Phase 4)",
)
class OfflineResultsRequest(BaseModel):
    """Request: sync offline study results."""
    results: list[dict[str, Any]] = []


async def sync_offline_results(
    request: OfflineResultsRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Sync study results from offline sessions."""
    try:
        synced = 0
        failed = 0
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import AttemptModel, QuestionInstanceModel
            from uuid import uuid4

            for r in request.results:
                try:
                    instance = QuestionInstanceModel(
                        id=uuid4(),
                        template_version_id=UUID(r.get("template_version_id", str(uuid4()))),
                        content_version_id=UUID(r.get("content_version_id", str(uuid4()))),
                        learner_enrollment_id=UUID(r["enrollment_id"]),
                        study_session_id=UUID(r["session_id"]),
                        parameter_seed=r.get("seed", 0),
                        parameter_values=r.get("parameters", {}),
                        rendered_prompt=r.get("prompt", {"text": "Offline question"}),
                        rendered_choices=r.get("choices"),
                        correct_answer=r.get("correct_answer", {}),
                        distractors_with_tags=r.get("distractors"),
                        served_at=datetime.fromisoformat(r["served_at"]) if r.get("served_at") else datetime.now(timezone.utc),
                        status="answered",
                        answered_at=datetime.now(timezone.utc),
                    )
                    session_obj.add(instance)
                    await session_obj.flush()

                    attempt = AttemptModel(
                        id=uuid4(),
                        question_instance_id=instance.id,
                        learner_enrollment_id=UUID(r["enrollment_id"]),
                        study_session_id=UUID(r["session_id"]),
                        content_version_id=instance.content_version_id,
                        template_version_id=instance.template_version_id,
                        algorithm_version_id=UUID(r.get("algorithm_version_id", str(uuid4()))),
                        scoring_outcome="correct" if r.get("correct") else "incorrect",
                        time_to_answer_ms=r.get("time_spent", 0) * 1000,
                        hint_used=r.get("hint_used", False),
                        hint_tiers_used=r.get("hint_tiers", []),
                        attempt_intent="practice",
                        marks_delta=1.0 if r.get("correct") else -r.get("negative_marking", 0.0),
                        error_type=r.get("error_type"),
                    )
                    session_obj.add(attempt)
                    synced += 1
                except Exception:
                    failed += 1

            await _uow.commit()

        return {
            "synced": synced,
            "failed": failed,
            "message": f"Synced {synced} offline results." + (f" {failed} failed." if failed else ""),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Phase 4 Indian Localization: WhatsApp Sharing
# ============================================================


@router.get(
    "/share/question/{question_instance_id}",
    summary="Get shareable question data for WhatsApp (Phase 4)",
)
async def get_shareable_question(
    question_instance_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get a question formatted for WhatsApp sharing."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import QuestionInstanceModel
            result = await session_obj.execute(
                select(QuestionInstanceModel).where(QuestionInstanceModel.id == question_instance_id)
            )
            instance = result.scalar_one_or_none()
            if not instance:
                raise HTTPException(status_code=404, detail="Question not found")

            prompt = instance.rendered_prompt or {}
            choices = instance.rendered_choices or []
            prompt_text = prompt.get("text", str(prompt)) if isinstance(prompt, dict) else str(prompt)

            wa_text = f"🐍 *MasteryOS Question of the Day*\n\n"
            wa_text += f"❓ {prompt_text}\n\n"
            for ch in choices:
                wa_text += f"{ch.get('id', '?')}. {ch.get('text', '')}\n"
            wa_text += f"\n🔗 Answer here: https://masteryos-production.up.railway.app/study/start"
            wa_text += f"\n📱 Can you beat my score?"

            import urllib.parse
            wa_url = f"https://wa.me/?text={urllib.parse.quote(wa_text)}"

            return {
                "whatsapp_text": wa_text,
                "whatsapp_url": wa_url,
                "question_id": str(question_instance_id),
                "deep_link": f"https://masteryos-production.up.railway.app/study/start?q={question_instance_id}",
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/share/score",
    summary="Get shareable score for WhatsApp (Phase 4)",
)
async def get_shareable_score(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get the user's latest performance formatted for WhatsApp score sharing."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import AttemptModel, LearnerEnrollmentModel

            attempts_result = await session_obj.execute(
                select(AttemptModel).where(
                    AttemptModel.learner_enrollment_id.in_(
                        select(LearnerEnrollmentModel.id).where(LearnerEnrollmentModel.user_id == user_id)
                    )
                ).order_by(AttemptModel.created_at.desc()).limit(20)
            )
            recent = attempts_result.scalars().all()

            if not recent:
                wa_text = "🐍 I just started learning on MasteryOS! Join me: https://masteryos-production.up.railway.app/register"
            else:
                correct = sum(1 for a in recent if a.scoring_outcome == "correct")
                accuracy = round((correct / len(recent)) * 100)
                marks = sum(getattr(a, 'marks_delta', 0.0) for a in recent)

                wa_text = f"🔥 *My MasteryOS Stats*\n\n"
                wa_text += f"✅ Accuracy: {accuracy}%\n"
                wa_text += f"📝 Questions: {len(recent)}\n"
                wa_text += f"⭐ Net marks: {marks:.1f}\n\n"
                wa_text += f"Can you beat my score? 🎯\n"
                wa_text += f"🔗 https://masteryos-production.up.railway.app/register"

            import urllib.parse
            wa_url = f"https://wa.me/?text={urllib.parse.quote(wa_text)}"

            return {
                "whatsapp_text": wa_text,
                "whatsapp_url": wa_url,
            }
    except Exception:
        return {
            "whatsapp_text": "Join me on MasteryOS! https://masteryos-production.up.railway.app/register",
            "whatsapp_url": "https://wa.me/?text=Join%20me%20on%20MasteryOS!",
        }


@router.get(
    "/share/daily-question",
    summary="Get daily question for WhatsApp bot (Phase 4)",
)
async def get_daily_question(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get a daily question for WhatsApp distribution."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.content import QuestionTemplateModel, TemplateVersionModel
            import sqlalchemy

            result = await session_obj.execute(
                select(TemplateVersionModel, QuestionTemplateModel)
                .join(QuestionTemplateModel, TemplateVersionModel.template_id == QuestionTemplateModel.id)
                .where(QuestionTemplateModel.status == "published")
                .where(QuestionTemplateModel.current_version_id == TemplateVersionModel.id)
                .order_by(sqlalchemy.func.random())
                .limit(1)
            )
            row = result.first()
            if not row:
                raise HTTPException(status_code=404, detail="No published questions available")

            tv, qt = row
            prompt = tv.prompt_template or {}
            prompt_text = prompt.get("text", str(prompt)) if isinstance(prompt, dict) else str(prompt)

            solutions = {}
            if tv.solution_traditional:
                solutions["traditional"] = tv.solution_traditional.get("text", "")
            if tv.solution_shortcut:
                solutions["shortcut"] = tv.solution_shortcut.get("text", "")
            if tv.solution_elimination:
                solutions["elimination"] = tv.solution_elimination.get("text", "")

            wa_text = f"🐍 *Daily Python Interview Question*\n\n❓ {prompt_text}\n\n"
            wa_text += f"Think you know the answer?\n"
            wa_text += f"🔗 Practice here: https://masteryos-production.up.railway.app/register"
            import urllib.parse
            wa_url = f"https://wa.me/?text={urllib.parse.quote(wa_text)}"

            return {
                "question_text": prompt_text,
                "whatsapp_text": wa_text,
                "whatsapp_url": wa_url,
                "template_id": str(qt.id),
                "difficulty": tv.difficulty_estimate,
                "solutions_available": list(solutions.keys()),
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Phase 4 Indian Localization: Solution Styles
# ============================================================


@router.get(
    "/questions/{question_instance_id}/solutions",
    summary="Get all solution styles for a question (Phase 4)",
)
async def get_solution_styles(
    question_instance_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get all available solution methods for a question.

    Indian coaching institutes teach multiple methods:
    - traditional: NCERT-style detailed step-by-step
    - shortcut: Vedic Maths / trick-based (10-second solution)
    - elimination: How to eliminate wrong options without solving
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import QuestionInstanceModel
            from app.infrastructure.database.orm.content import TemplateVersionModel

            instance_result = await session_obj.execute(
                select(QuestionInstanceModel).where(QuestionInstanceModel.id == question_instance_id)
            )
            instance = instance_result.scalar_one_or_none()
            if not instance:
                raise HTTPException(status_code=404, detail="Question not found")

            tv_result = await session_obj.execute(
                select(TemplateVersionModel).where(TemplateVersionModel.id == instance.template_version_id)
            )
            tv = tv_result.scalar_one_or_none()
            if not tv:
                raise HTTPException(status_code=404, detail="Template version not found")

            solutions: dict[str, str | None] = {}
            if tv.solution_traditional:
                solutions["traditional"] = tv.solution_traditional.get("text", str(tv.solution_traditional))
            if tv.solution_shortcut:
                solutions["shortcut"] = tv.solution_shortcut.get("text", str(tv.solution_shortcut))
            if tv.solution_elimination:
                solutions["elimination"] = tv.solution_elimination.get("text", str(tv.solution_elimination))

            return {
                "question_instance_id": str(question_instance_id),
                "solutions": solutions,
                "available_methods": list(solutions.keys()),
                "has_multiple_methods": len(solutions) > 1,
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Phase 4 Indian Localization: Leaderboards + Peer Comparison
# ============================================================


@router.get(
    "/leaderboard",
    summary="Get leaderboard rankings (Phase 4)",
)
async def get_leaderboard(
    period: str = Query("weekly", description="daily, weekly, monthly, all_time"),
    subject_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get leaderboard rankings for peer comparison."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import LeaderboardModel
            from app.infrastructure.database.orm.identity import UserModel

            query = (
                select(LeaderboardModel, UserModel.email)
                .outerjoin(UserModel, LeaderboardModel.user_id == UserModel.id)
                .where(LeaderboardModel.period == period)
            )
            if subject_id:
                query = query.where(LeaderboardModel.subject_id == subject_id)

            query = query.order_by(LeaderboardModel.rank.asc()).limit(limit)
            result = await session_obj.execute(query)
            rows = result.all()

            user_rank = None
            user_entry = None
            for lb, email in rows:
                if lb.user_id == user_id:
                    user_rank = lb.rank
                    user_entry = lb
                    break

            if user_rank is None:
                user_result = await session_obj.execute(
                    select(LeaderboardModel).where(
                        LeaderboardModel.user_id == user_id,
                        LeaderboardModel.period == period,
                    )
                )
                user_lb = user_result.scalar_one_or_none()
                if user_lb:
                    user_rank = user_lb.rank
                    user_entry = user_lb

            total_users_result = await session_obj.execute(
                select(func.count()).select_from(LeaderboardModel).where(
                    LeaderboardModel.period == period
                )
            )
            total_users = total_users_result.scalar() or 0

            return {
                "period": period,
                "rankings": [
                    {
                        "rank": lb.rank,
                        "email": email or "Anonymous" if lb.user_id != user_id else f"{email} (You)",
                        "score": round(lb.score, 2),
                        "accuracy": round(lb.accuracy * 100, 1),
                        "total_correct": lb.total_correct,
                        "total_attempted": lb.total_attempted,
                        "avg_speed_seconds": round(lb.avg_speed_seconds, 1),
                        "streak_days": lb.streak_days,
                        "is_you": lb.user_id == user_id,
                    }
                    for lb, email in rows
                ],
                "your_rank": user_rank,
                "your_score": round(user_entry.score, 2) if user_entry else 0.0,
                "your_percentile": round((1 - (user_rank / max(total_users, 1))) * 100, 1) if user_rank else 0.0,
                "total_users": total_users,
            }
    except Exception:
        return {
            "period": period,
            "rankings": [],
            "your_rank": None,
            "your_score": 0.0,
            "your_percentile": 0.0,
            "total_users": 0,
        }


@router.get(
    "/peer-comparison",
    summary="Get peer comparison stats (Phase 4)",
)
async def get_peer_comparison(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get peer comparison statistics.

    Shows how the user compares to other learners:
    - 'You're in the top 15% for Algorithms'
    - 'Your accuracy is 85% vs peer average of 72%'
    - 'Your speed is 12s vs peer average of 18s'
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.core import LeaderboardModel, AttemptModel, LearnerEnrollmentModel

            user_attempts = await session_obj.execute(
                select(AttemptModel).where(
                    AttemptModel.learner_enrollment_id.in_(
                        select(LearnerEnrollmentModel.id).where(LearnerEnrollmentModel.user_id == user_id)
                    )
                ).order_by(AttemptModel.created_at.desc()).limit(50)
            )
            user_recent = user_attempts.scalars().all()

            if not user_recent:
                return {
                    "your_accuracy": 0.0,
                    "peer_avg_accuracy": 0.0,
                    "your_speed": 0.0,
                    "peer_avg_speed": 0.0,
                    "your_percentile": 0.0,
                    "messages": ["Answer some questions to see how you compare!"],
                }

            user_correct = sum(1 for a in user_recent if a.scoring_outcome == "correct")
            user_accuracy = user_correct / len(user_recent)
            user_speed = sum(a.time_to_answer_ms for a in user_recent) / len(user_recent) / 1000

            peer_result = await session_obj.execute(
                select(
                    func.avg(LeaderboardModel.accuracy).label("avg_accuracy"),
                    func.avg(LeaderboardModel.avg_speed_seconds).label("avg_speed"),
                    func.count().label("total"),
                ).where(LeaderboardModel.period == "all_time")
            )
            peer_row = peer_result.one()
            peer_accuracy = float(peer_row.avg_accuracy or 0.0)
            peer_speed = float(peer_row.avg_speed or 0.0)
            total_users = int(peer_row.total or 0)

            user_rank_result = await session_obj.execute(
                select(LeaderboardModel.rank).where(
                    LeaderboardModel.user_id == user_id,
                    LeaderboardModel.period == "all_time",
                )
            )
            user_rank = user_rank_result.scalar()
            percentile = round((1 - (user_rank / max(total_users, 1))) * 100, 1) if user_rank else 0.0

            messages = []
            if user_accuracy > peer_accuracy:
                messages.append(f"Your accuracy ({round(user_accuracy*100)}%) is above peer average ({round(peer_accuracy*100)}%) 🎯")
            else:
                messages.append(f"Your accuracy ({round(user_accuracy*100)}%) is below peer average ({round(peer_accuracy*100)}%) — keep practicing!")
            if user_speed < peer_speed:
                messages.append(f"Your speed ({round(user_speed)}s) is faster than peer average ({round(peer_speed)}s) ⚡")
            else:
                messages.append(f"Your speed ({round(user_speed)}s) is slower than peer average ({round(peer_speed)}s) — try accuracy drills!")
            if percentile >= 75:
                messages.append(f"You're in the top {100 - percentile:.0f}% of all learners! 🔥")
            elif percentile >= 50:
                messages.append(f"You're in the top {100 - percentile:.0f}% — keep climbing! 📈")
            else:
                messages.append(f"You're in the bottom {percentile:.0f}% — every expert was once a beginner! 💪")

            return {
                "your_accuracy": round(user_accuracy * 100, 1),
                "peer_avg_accuracy": round(peer_accuracy * 100, 1),
                "your_speed": round(user_speed, 1),
                "peer_avg_speed": round(peer_speed, 1),
                "your_percentile": percentile,
                "total_peers": total_users,
                "messages": messages,
            }
    except Exception:
        return {
            "your_accuracy": 0.0,
            "peer_avg_accuracy": 0.0,
            "your_speed": 0.0,
            "peer_avg_speed": 0.0,
            "your_percentile": 0.0,
            "total_peers": 0,
            "messages": ["Answer some questions to see how you compare!"],
        }


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


@router.post(
    "/study-sessions/{session_id}/abandon",
    summary="Abandon a study session",
)
async def abandon_study_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Abandon a study session (marks it as abandoned, not completed)."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from sqlalchemy import update as sql_update
            from app.infrastructure.database.orm.core import StudySessionModel
            from datetime import datetime, timezone
            await session_obj.execute(
                sql_update(StudySessionModel)
                .where(
                    StudySessionModel.id == session_id,
                    StudySessionModel.status.in_(["active", "paused"]),
                )
                .values(
                    status="abandoned",
                    ended_at=datetime.now(timezone.utc),
                )
            )
            await _uow.commit()
        return {"message": "Session abandoned"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/study-sessions/{session_id}/end",
    summary="End a study session",
)
async def end_study_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """End a study session (marks it as completed)."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from sqlalchemy import update as sql_update
            from app.infrastructure.database.orm.core import StudySessionModel
            from datetime import datetime, timezone
            await session_obj.execute(
                sql_update(StudySessionModel)
                .where(
                    StudySessionModel.id == session_id,
                    StudySessionModel.status.in_(["active", "paused"]),
                )
                .values(
                    status="ended",
                    ended_at=datetime.now(timezone.utc),
                )
            )
            await _uow.commit()
        return {"message": "Session ended"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/study-sessions/{session_id}/summary",
    summary="Get session summary",
)
async def get_session_summary(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get a summary of a completed (or in-progress) study session.

    Returns questions answered, accuracy, time spent, mastery changes,
    weak/strong concepts, recommendations, and review schedule.
    """
    from sqlalchemy import select, func
    from app.infrastructure.database.orm.core import (
        QuestionInstanceModel, AttemptModel, StudySessionModel,
    )

    async with uow as _uow:
        session_obj = _uow._session  # type: ignore[union-attr]

        # Load the session
        study_session = await _uow.study_sessions.get_by_id(StudySessionId(session_id))
        if study_session is None:
            raise HTTPException(status_code=404, detail={
                "code": "SESSION_NOT_FOUND",
                "message": "Study session not found",
            })

        # Count question instances for this session
        instances_result = await session_obj.execute(
            select(QuestionInstanceModel).where(
                QuestionInstanceModel.study_session_id == session_id
            )
        )
        instances = instances_result.scalars().all()
        questions_answered = sum(1 for i in instances if i.status == "answered")

        # Load attempts for this session's instances
        instance_ids = [i.id for i in instances]
        attempts: list = []
        if instance_ids:
            attempts_result = await session_obj.execute(
                select(AttemptModel).where(
                    AttemptModel.question_instance_id.in_(instance_ids)
                ).order_by(AttemptModel.created_at.desc())
            )
            attempts = attempts_result.scalars().all()

        # Compute accuracy
        correct_count = sum(1 for a in attempts if a.scoring_outcome == "correct")
        total_attempts = len(attempts)
        accuracy = (correct_count / total_attempts) if total_attempts > 0 else 0.0

        # Compute time spent
        started_at = study_session.started_at
        ended_at = study_session.ended_at or datetime.now(timezone.utc)
        time_spent = int((ended_at - started_at).total_seconds()) if started_at else 0

        # Load mastery scores for this enrollment
        all_scores = await _uow.mastery_scores.list_by_enrollment(study_session.learner_enrollment_id)
        weak_scores = [s for s in all_scores if s.is_weak][:5]
        strong_scores = [s for s in all_scores if s.is_proficient_or_above][:5]

        # Load concept names
        concept_names: dict[str, str] = {}
        all_concept_ids = [s.concept_id.value for s in all_scores]
        if all_concept_ids:
            from app.infrastructure.database.orm.content import ConceptModel
            concept_result = await session_obj.execute(
                select(ConceptModel.id, ConceptModel.name).where(
                    ConceptModel.id.in_(all_concept_ids)
                )
            )
            for cid, cname in concept_result.all():
                concept_names[str(cid)] = cname

        # Build weak/strong concept lists
        weak_concepts = [
            {
                "concept_id": str(s.concept_id.value),
                "concept_name": concept_names.get(str(s.concept_id.value), "Unknown"),
                "mastery_score_combined": s.mastery_score_combined,
            }
            for s in weak_scores
        ]
        strong_concepts = [
            {
                "concept_id": str(s.concept_id.value),
                "concept_name": concept_names.get(str(s.concept_id.value), "Unknown"),
                "mastery_score_combined": s.mastery_score_combined,
            }
            for s in strong_scores
        ]

        # Load due reviews
        due_reviews = await _uow.reviews.list_due_by_enrollment(study_session.learner_enrollment_id)
        review_schedule = [
            {
                "concept_id": str(r.concept_id.value),
                "concept_name": concept_names.get(str(r.concept_id.value), "Unknown"),
                "interval_days": max(1, (r.due_at - datetime.now(timezone.utc)).days) if r.due_at else 1,
            }
            for r in due_reviews[:5]
        ]

        # Load recommendations (empty for now — no recommendations table wired)
        recommendations: list = []

        return {
            "session_id": str(session_id),
            "questions_answered": questions_answered,
            "questions_total": len(instances),
            "accuracy": accuracy,
            "time_spent_seconds": time_spent,
            "mastery_gained": 0.0,  # Would need before/after comparison
            "weak_concepts": weak_concepts,
            "strong_concepts": strong_concepts,
            "recommendations": recommendations,
            "review_schedule": review_schedule,
            "achievements_unlocked": [],
        }


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
        existing_instances = existing_result.scalars().all()
        served_template_ids = set()
        for qi in existing_instances:
            served_template_ids.add(qi.template_version_id)

        # If questions already exist for this session, return them directly
        # (avoids returning empty queue on page refresh / second call)
        # IMPORTANT: Only return UNANSWERED questions (status='served').
        # Answered questions would cause 409 on submit.
        if existing_instances:
            unanswered = [qi for qi in existing_instances if qi.status == "served"]
            if unanswered:
                return AdaptiveQueueResponse(
                    study_session_id=session_id,
                    current_position=0,
                    questions=[
                        QueueItemDTO(
                            question_instance_id=qi.id,
                            concept_id=uuid4(),  # Concept not stored on instance; placeholder
                            difficulty="medium",
                            estimated_duration_seconds=30,
                            recommendation_score=0.5,
                            reason="existing",
                        )
                        for qi in unanswered
                    ],
                )
            # All questions answered — fall through to generate new ones

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
            seed = int(hashlib.sha256(seed_input.encode()).hexdigest()[:8], 16) & 0x7FFFFFFF  # Mask to positive int32

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
