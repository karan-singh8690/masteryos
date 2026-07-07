"""Question API routes — retrieve question, submit answer, complete learning loop.

Maps to the OpenAPI contract (Task 006):
- GET  /api/v1/questions/{question_instance_id}
- POST /api/v1/questions/{question_instance_id}/submit

The submit endpoint executes the FULL learning loop:
  Submit Answer → Record Attempt → Update Mastery → Schedule Review → Return Explanation + Recommendation

This is the heart of the Mastery Engine.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.application.assessment.handlers import (
    SubmitAttemptCommand,
    SubmitAttemptHandler,
)
from app.application.mastery.handlers import (
    UpdateMasteryCommand,
    UpdateMasteryHandler,
)
from app.application.shared import UnitOfWork
from app.domain.assessment.answer import Answer
from app.domain.assessment.attempt import Attempt
from app.domain.assessment.question_instance import QuestionInstance
from app.domain.mastery.mastery_calculator import MasteryCalculator
from app.domain.mastery.mastery_score import MasteryScore
from app.domain.mastery.review import Review
from app.domain.mastery.algorithm_version import AlgorithmVersion
from app.domain.learning.recommendation import Recommendation
from app.domain.learning.streak import Streak
from app.domain.shared.ids import (
    AlgorithmVersionId,
    AnswerId,
    AttemptId,
    ConceptId,
    ContentVersionId,
    LearnerEnrollmentId,
    MasteryScoreId,
    QuestionInstanceId,
    RecommendationId,
    ReviewId,
    StudySessionId,
    TemplateVersionId,
)
from app.domain.shared.kernel import (
    AnswerType,
    AttemptIntent,
    ConceptState,
    Difficulty,
    ReviewPriority,
    ScoringOutcome,
    WeaknessSeverity,
)
from app.domain.shared.value_objects import Duration, ReviewInterval
from app.presentation.dependencies import (
    OutboxEventPublisher,
    get_current_user_id,
    get_event_publisher,
    get_idempotency_key,
    get_uow,
)
from app.infrastructure.database.orm.core import (
    AttemptModel,
    MasteryScoreModel,
    QuestionInstanceModel,
    ReviewModel,
    StudySessionModel,
    AlgorithmVersionModel,
)
from app.infrastructure.database.mappers import (
    AttemptMapper,
    MasteryScoreMapper,
    QuestionInstanceMapper,
    ReviewMapper,
    AlgorithmVersionMapper,
)
from app.infrastructure.database.unit_of_work import OutboxEventWriter
from app.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/questions", tags=["Questions"])


# ============================================================
# Request/Response Models
# ============================================================


class QuestionResponse(BaseModel):
    """Response: a question ready for the learner to answer."""

    question_instance_id: UUID
    concept_ids: list[UUID]
    difficulty: str
    estimated_duration_seconds: int
    question_type: str
    prompt: dict[str, Any]
    choices: list[dict[str, Any]] | None
    metadata: dict[str, Any]


class SubmitAnswerRequest(BaseModel):
    """Request: submit an answer to a question."""

    answer: dict[str, Any] = Field(description="The learner's answer (choice, code, or text)")
    answer_type: str = Field(default="multiple_choice", description="multiple_choice, code, free_response")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Learner's confidence (0.0-1.0)")
    time_spent_seconds: int = Field(ge=0, description="Time spent answering in seconds")
    hint_used: bool = Field(default=False)
    hint_tiers_used: list[int] = Field(default_factory=list)


class AttemptResultResponse(BaseModel):
    """Response: the complete result of submitting an answer."""

    attempt_id: UUID
    scoring_outcome: str
    partial_credit: float | None
    time_to_answer_ms: int
    hint_used: bool
    created_at: str
    # Phase 1 Indian localization: Performance Index
    marks_delta: float = 0.0  # +1 for correct, -negative_marking for incorrect, 0 for unattempted
    error_type: str | None = None  # concept_gap, calculation_error, misread, time_pressure
    speed_score: float = 0.0  # 0-1, higher = faster relative to benchmark
    performance_index: float = 0.0  # weighted: accuracy*0.4 + speed*0.3 + risk_efficiency*0.3


class MasteryScoreDTO(BaseModel):
    concept_id: UUID
    concept_name: str | None = None
    memory_score: float
    durable_mastery_score: float
    mastery_score_combined: float
    concept_state: str
    weakness_severity: str
    evidence_count: int
    last_attempt_at: str | None


class ReviewDTO(BaseModel):
    concept_id: UUID
    due_at: str
    priority: str
    interval_days: int


class ExplanationDTO(BaseModel):
    content: str
    outcome_key: str


class RecommendationDTO(BaseModel):
    id: UUID
    recommendation_type: str
    score: float
    reason: str


class SubmitAnswerResponse(BaseModel):
    """The complete learning loop response."""

    attempt: AttemptResultResponse
    mastery: MasteryScoreDTO | None
    review: ReviewDTO | None
    explanation: ExplanationDTO
    recommendation: RecommendationDTO | None


class DashboardResponse(BaseModel):
    """Enriched dashboard with mastery, reviews, streak, and readiness."""

    enrollment_id: UUID | None
    recommended_action: str
    current_streak: int
    longest_streak: int
    weak_concepts: list[MasteryScoreDTO]
    strong_concepts: list[MasteryScoreDTO]
    today_reviews: int
    today_queue_remaining: int
    daily_progress: float
    interview_readiness: float
    memory_trend: list[dict[str, Any]]
    mastery_trend: list[dict[str, Any]]
    # Phase 1 Indian localization
    exam_countdown_days: int | None = None
    target_exam_name: str | None = None
    negative_marking_factor: float = 0.0
    performance_index: float = 0.0  # aggregate accuracy + speed + risk
    total_marks: float = 0.0  # net marks (correct - negative)
    error_breakdown: dict[str, int] = {}  # {concept_gap: 5, misread: 2, time_pressure: 1}
    # Phase 2 Indian localization
    weighted_readiness: float = 0.0  # mastery weighted by exam weightage
    high_weightage_weak: list[dict[str, Any]] = []  # RED ALERT: weak concepts with high weightage
    exam_proximity_mode: str | None = None  # normal, revision, mock, cram


# ============================================================
# Endpoints
# ============================================================


# IMPORTANT: Static routes (like /dashboard) MUST be declared BEFORE
# parameterized routes (like /{question_instance_id}) so FastAPI matches
# them first. Otherwise /dashboard would match /{question_instance_id}
# and fail UUID parsing → 422 Unprocessable Entity.
@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    tags=["Dashboard"],
    summary="Get the enriched learner dashboard",
)
async def get_dashboard(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> DashboardResponse:
    """Get the enriched dashboard with mastery, reviews, streak, and readiness."""
    try:
        from sqlalchemy import select, func

        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]

            # Load enrollments for the user
            enrollments = await _uow.enrollments.list_by_user(
                __import__("app.domain.shared.ids", fromlist=["UserId"]).UserId(user_id)
            )

            if not enrollments:
                return DashboardResponse(
                    enrollment_id=None,
                    recommended_action="enroll_in_subject",
                    current_streak=0,
                    longest_streak=0,
                    weak_concepts=[],
                    strong_concepts=[],
                    today_reviews=0,
                    today_queue_remaining=0,
                    daily_progress=0.0,
                    interview_readiness=0.0,
                    memory_trend=[],
                    mastery_trend=[],
                )

            # Use the first enrollment (simplified — in production, the learner selects)
            enrollment = enrollments[0]
            enrollment_id = enrollment.id

            # Load mastery scores
            all_scores = await _uow.mastery_scores.list_by_enrollment(enrollment_id)
            weak_scores = [s for s in all_scores if s.is_weak]
            strong_scores = [s for s in all_scores if s.is_proficient_or_above]

            # Load concept names for weak + strong concepts
            concept_names: dict[str, str] = {}
            all_concept_ids = [s.concept_id.value for s in all_scores]
            if all_concept_ids:
                from app.infrastructure.database.orm.content import ConceptModel
                from sqlalchemy import select as sa_select
                concept_result = await session.execute(
                    sa_select(ConceptModel.id, ConceptModel.name).where(
                        ConceptModel.id.in_(all_concept_ids)
                    )
                )
                for cid, cname in concept_result.all():
                    concept_names[str(cid)] = cname

            # Load due reviews
            due_reviews = await _uow.reviews.list_due_by_enrollment(enrollment_id)
            today_reviews = len(due_reviews)

            # Load streak
            streak = await _uow.streaks.get_by_enrollment(enrollment_id)

            # Phase 1 Indian localization: exam countdown + performance index
            from app.infrastructure.database.orm.core import LearnerEnrollmentModel, AttemptModel
            enroll_result = await session.execute(
                select(LearnerEnrollmentModel).where(LearnerEnrollmentModel.id == enrollment_id)
            )
            enroll_model = enroll_result.scalar_one_or_none()

            exam_countdown = None
            target_exam_name = None
            neg_marking = 0.0
            perf_index = 0.0
            total_marks = 0.0
            error_breakdown: dict[str, int] = {}

            if enroll_model:
                neg_marking = enroll_model.negative_marking_factor
                target_exam_name = enroll_model.target_exam_name
                if enroll_model.target_exam_date:
                    from datetime import datetime, timezone as tz
                    now = datetime.now(tz.utc)
                    delta = enroll_model.target_exam_date - now
                    exam_countdown = max(0, delta.days)

                # Load recent attempts for performance index + error breakdown
                attempts_result = await session.execute(
                    select(AttemptModel).where(
                        AttemptModel.learner_enrollment_id == enrollment_id
                    ).order_by(AttemptModel.created_at.desc()).limit(50)
                )
                recent_attempts = attempts_result.scalars().all()
                if recent_attempts:
                    correct = sum(1 for a in recent_attempts if a.scoring_outcome == "correct")
                    total = len(recent_attempts)
                    accuracy = correct / total if total > 0 else 0.0
                    avg_speed = sum(a.time_to_answer_ms for a in recent_attempts) / total / 1000  # seconds
                    speed = max(0.0, min(1.0, 1.0 - (avg_speed / 30.0)))
                    total_marks = sum(getattr(a, 'marks_delta', 0.0) for a in recent_attempts)
                    risk_eff = max(0, total_marks / total) if total > 0 else 0.0
                    perf_index = round((accuracy * 0.4) + (speed * 0.3) + (risk_eff * 0.3), 4)

                    # Error breakdown
                    for a in recent_attempts:
                        et = getattr(a, 'error_type', None)
                        if et:
                            error_breakdown[et] = error_breakdown.get(et, 0) + 1

                # Phase 2: Weighted readiness + high-weightage weak concepts
                weighted_readiness = 0.0
                high_weightage_weak = []
                exam_proximity_mode = None

                if target_exam_name:
                    # Load exam weightage
                    from app.infrastructure.database.orm.content import ExamWeightageModel, ConceptModel
                    weightage_result = await session.execute(
                        select(ExamWeightageModel, ConceptModel).join(
                            ConceptModel,
                            ExamWeightageModel.concept_id == ConceptModel.id
                        ).where(ExamWeightageModel.exam_name == target_exam_name)
                    )
                    weightage_map = {}  # concept_id -> (weightage, name, cluster)
                    for w, c in weightage_result.all():
                        weightage_map[str(c.id)] = (w.weightage, c.name, w.topic_cluster)

                    if weightage_map and all_scores:
                        # Weighted readiness = sum(mastery * weightage) / sum(weightage)
                        total_weight = sum(w[0] for w in weightage_map.values())
                        if total_weight > 0:
                            weighted_sum = 0.0
                            for score in all_scores:
                                cid = str(score.concept_id.value)
                                if cid in weightage_map:
                                    w_val = weightage_map[cid][0]
                                    weighted_sum += score.mastery_score_combined * w_val
                            weighted_readiness = round(weighted_sum / total_weight, 4)

                        # Find weak concepts with high weightage (RED ALERT)
                        for score in all_scores:
                            if score.is_weak:
                                cid = str(score.concept_id.value)
                                if cid in weightage_map:
                                    w_val, name, cluster = weightage_map[cid]
                                    if w_val >= 0.1:  # >10% weightage = high priority
                                        high_weightage_weak.append({
                                            "concept_id": cid,
                                            "concept_name": name,
                                            "mastery": round(score.mastery_score_combined, 4),
                                            "weightage": w_val,
                                            "topic_cluster": cluster,
                                        })

                    # Phase 2: Exam proximity mode
                    if exam_countdown is not None:
                        if exam_countdown > 90:
                            exam_proximity_mode = "normal"
                        elif exam_countdown > 60:
                            exam_proximity_mode = "revision"
                        elif exam_countdown > 30:
                            exam_proximity_mode = "intensive"
                        elif exam_countdown > 15:
                            exam_proximity_mode = "mock"
                        else:
                            exam_proximity_mode = "cram"

            # Check for active session
            active_session = await _uow.study_sessions.get_active_by_enrollment(enrollment_id)

        # Compute interview readiness (simplified: average mastery of strong concepts)
        if all_scores:
            avg_mastery = sum(s.mastery_score_combined for s in all_scores) / len(all_scores)
            interview_readiness = round(avg_mastery, 4)
        else:
            interview_readiness = 0.0

        # Determine recommended action
        if active_session is not None:
            recommended_action = "continue_session"
        elif weak_scores:
            recommended_action = "drill_weak_concepts"
        elif today_reviews > 0:
            recommended_action = "review_due"
        else:
            recommended_action = "start_session"

        # Build mastery trend (simplified — in production, from analytics snapshots)
        mastery_trend = [
            {"date": (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat(),
             "avg_mastery": interview_readiness}
            for i in range(7, 0, -1)
        ]

        memory_trend = [
            {"date": (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat(),
             "avg_memory": sum(s.memory_score for s in all_scores) / max(len(all_scores), 1)}
            for i in range(7, 0, -1)
        ]

        return DashboardResponse(
            enrollment_id=enrollment_id.value,
            recommended_action=recommended_action,
            current_streak=streak.current_streak if streak else 0,
            longest_streak=streak.longest_streak if streak else 0,
            weak_concepts=[
                MasteryScoreDTO(
                    concept_id=s.concept_id.value,
                    concept_name=concept_names.get(str(s.concept_id.value), "Unknown concept"),
                    memory_score=s.memory_score,
                    durable_mastery_score=s.durable_mastery_score,
                    mastery_score_combined=s.mastery_score_combined,
                    concept_state=s.concept_state.value,
                    weakness_severity=s.weakness_severity.value,
                    evidence_count=s.evidence_count,
                    last_attempt_at=s.last_attempt_at.isoformat() if s.last_attempt_at else None,
                )
                for s in weak_scores[:10]
            ],
            strong_concepts=[
                MasteryScoreDTO(
                    concept_id=s.concept_id.value,
                    concept_name=concept_names.get(str(s.concept_id.value), "Unknown concept"),
                    memory_score=s.memory_score,
                    durable_mastery_score=s.durable_mastery_score,
                    mastery_score_combined=s.mastery_score_combined,
                    concept_state=s.concept_state.value,
                    weakness_severity=s.weakness_severity.value,
                    evidence_count=s.evidence_count,
                    last_attempt_at=s.last_attempt_at.isoformat() if s.last_attempt_at else None,
                )
                for s in strong_scores[:10]
            ],
            today_reviews=today_reviews,
            today_queue_remaining=max(0, 15 - (active_session.question_count if active_session else 0)),
            daily_progress=round((active_session.question_count / 15) if active_session else 0.0, 4),
            interview_readiness=interview_readiness,
            memory_trend=memory_trend,
            mastery_trend=mastery_trend,
            # Phase 1 Indian localization
            exam_countdown_days=exam_countdown,
            target_exam_name=target_exam_name,
            negative_marking_factor=neg_marking,
            performance_index=perf_index,
            total_marks=total_marks,
            error_breakdown=error_breakdown,
            # Phase 2 Indian localization
            weighted_readiness=weighted_readiness,
            high_weightage_weak=high_weightage_weak,
            exam_proximity_mode=exam_proximity_mode,
        )
    except Exception as exc:
        # If anything goes wrong, return an empty dashboard instead of 500
        import traceback
        traceback.print_exc()
        return DashboardResponse(
            enrollment_id=None,
            recommended_action="start_session",
            current_streak=0,
            longest_streak=0,
            weak_concepts=[],
            strong_concepts=[],
            today_reviews=0,
            today_queue_remaining=0,
            daily_progress=0.0,
            interview_readiness=0.0,
            memory_trend=[],
            mastery_trend=[],
        )


@router.get(
    "/{question_instance_id}",
    response_model=QuestionResponse,
    summary="Retrieve a question for answering",
)
async def get_question(
    question_instance_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> QuestionResponse:
    """Retrieve a question instance for the learner to answer.

    Returns the prompt, choices, and metadata. NEVER exposes the correct answer.
    Even if the question has already been answered, the question data is returned
    so the frontend can display it (the frontend checks the answered state separately).
    """
    async with uow as _uow:
        instance = await _uow.question_instances.get_by_id(
            QuestionInstanceId(question_instance_id)
        )
        if instance is None:
            raise HTTPException(status_code=404, detail={
                "code": "QUESTION_NOT_FOUND",
                "message": "Question instance not found",
            })

        # Build response — NEVER include correct_answer
        # Note: we return the question even if already answered or abandoned,
        # so the frontend can display it and advance to the next one.
        return QuestionResponse(
            question_instance_id=instance.id.value,
            concept_ids=[],  # Would come from template_concepts join in full implementation
            difficulty=Difficulty.MEDIUM.value,  # Would come from template version
            estimated_duration_seconds=60,
            question_type="multiple_choice",
            prompt=instance.rendered_prompt,
            choices=instance.rendered_choices,
            metadata={
                "served_at": instance.served_at.isoformat(),
                "session_id": str(instance.study_session_id.value),
                "status": instance.status,  # "served", "answered", or "abandoned"
            },
        )


@router.post(
    "/{question_instance_id}/submit",
    response_model=SubmitAnswerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an answer and complete the learning loop",
)
async def submit_answer(
    question_instance_id: UUID,
    request: SubmitAnswerRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
    publisher: OutboxEventPublisher = Depends(get_event_publisher),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> SubmitAnswerResponse:
    """Submit an answer to a question.

    This endpoint executes the FULL learning loop:
    1. Score the answer (deterministic)
    2. Record the attempt (append-only)
    3. Update mastery score (via MasteryCalculator)
    4. Schedule/reschedule review (spaced repetition)
    5. Return explanation
    6. Generate recommendation
    7. Update streak
    8. Write all events to outbox
    9. Commit transaction
    """
    from sqlalchemy import select, update as sa_update
    from app.infrastructure.database.orm.core import (
        LearnerEnrollmentModel,
    )

    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]

        # ============================================================
        # 1. Load the question instance
        # ============================================================
        instance = await _uow.question_instances.get_by_id(
            QuestionInstanceId(question_instance_id)
        )
        if instance is None:
            raise HTTPException(status_code=404, detail={
                "code": "QUESTION_NOT_FOUND",
                "message": "Question instance not found",
            })

        if instance.is_answered:
            # Instead of 409, return a friendly response indicating the question
            # was already answered. The frontend can use this to skip to the next.
            raise HTTPException(status_code=409, detail={
                "code": "QUESTION_ALREADY_ANSWERED",
                "message": "This question has already been answered. Move to the next question.",
            })

        # ============================================================
        # 2. Score the answer (deterministic — compare to correct_answer)
        # ============================================================
        correct_answer = instance.correct_answer
        learner_answer = request.answer

        # The frontend sends {"choice_id": "A"} for multiple_choice questions.
        # The instance.rendered_choices is a list of {id, text, is_correct} dicts.
        # The instance.correct_answer is {"answer": "correct answer text"}.
        #
        # Scoring logic:
        # 1. Find the learner's selected choice by choice_id
        # 2. Check if that choice's is_correct flag is True
        # 3. Fallback: compare choice text to correct_answer text
        scoring_outcome = ScoringOutcome.INCORRECT
        partial_credit = None

        learner_choice_id = learner_answer.get("choice_id") or learner_answer.get("choice")
        rendered_choices = instance.rendered_choices or []

        # Try to find the learner's choice in rendered_choices
        learner_choice = None
        for ch in rendered_choices:
            if ch.get("id") == learner_choice_id:
                learner_choice = ch
                break

        if learner_choice is not None:
            # Primary: use the is_correct flag from rendered_choices
            if learner_choice.get("is_correct"):
                scoring_outcome = ScoringOutcome.CORRECT
            else:
                # Fallback: compare text to correct_answer
                correct_text = correct_answer.get("answer", "")
                if correct_text and learner_choice.get("text") == correct_text:
                    scoring_outcome = ScoringOutcome.CORRECT
                else:
                    scoring_outcome = ScoringOutcome.INCORRECT
        elif correct_answer.get("answer") is not None:
            # No rendered_choices match — compare raw answer text
            learner_text = learner_answer.get("answer") or learner_answer.get("text") or ""
            if learner_text == correct_answer["answer"]:
                scoring_outcome = ScoringOutcome.CORRECT
            else:
                scoring_outcome = ScoringOutcome.INCORRECT
        elif correct_answer.get("choices") is not None:
            # Multi-part answer
            if learner_choice_id in correct_answer["choices"]:
                scoring_outcome = ScoringOutcome.CORRECT
            elif learner_choice_id is not None:
                scoring_outcome = ScoringOutcome.PARTIAL
                partial_credit = 0.5

        # ============================================================
        # 2.5 Phase 1 Indian Localization: Performance Index + Negative Marking
        # ============================================================
        # Load enrollment for negative marking factor
        from app.infrastructure.database.orm.core import LearnerEnrollmentModel
        enrollment_result = await session.execute(
            select(LearnerEnrollmentModel).where(
                LearnerEnrollmentModel.id == instance.learner_enrollment_id.value
            )
        )
        enrollment_model = enrollment_result.scalar_one_or_none()
        neg_marking = enrollment_model.negative_marking_factor if enrollment_model else 0.0

        # Calculate marks_delta: +1 for correct, -neg_marking for incorrect, 0 for partial
        if scoring_outcome == ScoringOutcome.CORRECT:
            marks_delta = 1.0
        elif scoring_outcome == ScoringOutcome.INCORRECT:
            marks_delta = -neg_marking  # e.g., -0.25 for -1/4 marking
        else:
            marks_delta = 0.0

        # Calculate speed score: 1.0 if very fast, 0.0 if very slow
        # Benchmark: 30 seconds for medium questions
        benchmark_time = 30  # seconds
        speed_score = max(0.0, min(1.0, 1.0 - (request.time_spent_seconds / benchmark_time)))

        # Determine error type for incorrect answers (silly mistake tracker)
        error_type = None
        if scoring_outcome == ScoringOutcome.INCORRECT:
            if request.time_spent_seconds < 5:
                error_type = "time_pressure"  # Answered too fast — didn't think
            elif request.confidence > 0.7:
                error_type = "misread"  # High confidence but wrong — likely misread question
            else:
                error_type = "concept_gap"  # Genuinely doesn't know

        # Performance Index: weighted combination
        accuracy_score = 1.0 if scoring_outcome == ScoringOutcome.CORRECT else 0.0
        risk_efficiency = marks_delta  # Positive = gained marks, negative = lost marks
        performance_index = round(
            (accuracy_score * 0.4) + (speed_score * 0.3) + (max(0, risk_efficiency) * 0.3),
            4
        )

        # ============================================================
        # 3. Load the active algorithm version
        # ============================================================
        algorithm = await _uow.algorithm_versions.get_active()
        if algorithm is None:
            raise HTTPException(status_code=500, detail={
                "code": "ALGORITHM_VERSION_NOT_ACTIVE",
                "message": "No active algorithm version configured",
            })

        # ============================================================
        # 4. Record the attempt (append-only — the data moat)
        # ============================================================
        # INTEGRATED (Task 014): Load REAL concept_ids from template_concepts
        # via the QuestionInstance's template_version_id. No more empty tuples.
        from app.infrastructure.database.orm.content import (
            TemplateConceptModel as TCModelForAttempt,
        )
        from sqlalchemy import select as sa_select_for_attempt

        tc_for_attempt_stmt = sa_select_for_attempt(TCModelForAttempt.concept_id).where(
            TCModelForAttempt.template_version_id == instance.template_version_id.value
        )
        tc_for_attempt_result = await session.execute(tc_for_attempt_stmt)
        concept_ids: tuple[UUID, ...] = tuple(row[0] for row in tc_for_attempt_result.all())

        # Parse answer type
        try:
            answer_type = AnswerType(request.answer_type)
        except ValueError:
            answer_type = AnswerType.MULTIPLE_CHOICE

        # Create the answer value object
        answer = Answer.create(
            question_instance_id=instance.id,
            answer_type=answer_type,
            submitted_answer=request.answer,
        )

        # Record the attempt
        attempt = Attempt.record(
            question_instance_id=instance.id,
            learner_enrollment_id=instance.learner_enrollment_id,
            study_session_id=instance.study_session_id,
            content_version_id=instance.content_version_id,
            template_version_id=instance.template_version_id,
            algorithm_version_id=algorithm.id,
            scoring_outcome=scoring_outcome,
            time_to_answer=Duration(request.time_spent_seconds),
            hint_used=request.hint_used,
            hint_tiers_used=request.hint_tiers_used,
            attempt_intent=AttemptIntent.PRACTICE,
            answer=answer,
            partial_credit=partial_credit,
            concept_ids=concept_ids,
        )

        await _uow.attempts.add(attempt)

        # Mark question instance as answered
        instance.mark_answered(attempt.id.value)
        await _uow.question_instances.save(instance)

        # Record attempt in study session
        study_session = await _uow.study_sessions.get_by_id(instance.study_session_id)
        if study_session is not None and study_session.is_active:
            study_session.record_attempt()
            await _uow.study_sessions.save(study_session)

        # ============================================================
        # 5. Update mastery score (via MasteryCalculator)
        # ============================================================
        mastery_result: MasteryScore | None = None
        review_result: Review | None = None

        # Load attempt history for this learner+concept (simplified: use current attempt)
        attempt_history = await _uow.attempts.list_by_enrollment(
            instance.learner_enrollment_id, limit=100
        )

        # INTEGRATED (Task 014): Load REAL concept_ids from the TemplateVersion
        # via the template_concepts join table. No more placeholder UUIDs.
        from app.infrastructure.database.orm.content import (
            TemplateVersionModel as TVModel,
            TemplateConceptModel as TCModel,
            ExplanationModel as ExplModel,
        )
        from sqlalchemy import select as sa_select

        tc_stmt = sa_select(TCModel.concept_id).where(
            TCModel.template_version_id == instance.template_version_id.value
        )
        tc_result = await session.execute(tc_stmt)
        real_concept_ids: tuple[UUID, ...] = tuple(row[0] for row in tc_result.all())

        if not real_concept_ids:
            # Fallback: if no concept links exist, skip mastery update
            # (this should not happen with properly authored content)
            real_concept_ids = ()

        # Load explanation from the Explanation table (not dynamically built)
        explanation_stmt = sa_select(ExplModel).where(
            ExplModel.template_version_id == instance.template_version_id.value,
            ExplModel.outcome_key == scoring_outcome.value,
        )
        explanation_result = await session.execute(explanation_stmt)
        explanation_model = explanation_result.scalar_one_or_none()

        if explanation_model is not None:
            explanation_content = explanation_model.content
        else:
            # Fallback: try 'correct' or 'incorrect' generic explanations
            fallback_key = "correct" if scoring_outcome == ScoringOutcome.CORRECT else "incorrect"
            fallback_stmt = sa_select(ExplModel).where(
                ExplModel.template_version_id == instance.template_version_id.value,
                ExplModel.outcome_key == fallback_key,
            )
            fallback_result = await session.execute(fallback_stmt)
            fallback_model = fallback_result.scalar_one_or_none()
            if fallback_model is not None:
                explanation_content = fallback_model.content
            else:
                # Last resort: build dynamically (backward compatible)
                explanation_content = _build_explanation(
                    scoring_outcome=scoring_outcome,
                    hint_used=request.hint_used,
                    correct_answer=correct_answer,
                    learner_answer=learner_answer,
                    rendered_choices=instance.rendered_choices,
                )

        concept_ids_for_mastery = real_concept_ids

        for concept_id_raw in concept_ids_for_mastery:
            concept_id = ConceptId(concept_id_raw) if isinstance(concept_id_raw, UUID) else ConceptId.from_string(str(concept_id_raw))

            # Load or initialize mastery score
            mastery_score = await _uow.mastery_scores.get_by_enrollment_and_concept(
                instance.learner_enrollment_id, concept_id
            )
            if mastery_score is None:
                mastery_score = MasteryScore.initialize(
                    instance.learner_enrollment_id, concept_id, algorithm.id
                )
                await _uow.mastery_scores.add(mastery_score)

            # Load current review interval
            existing_review = await _uow.reviews.get_by_enrollment_and_concept(
                instance.learner_enrollment_id, concept_id
            )
            current_interval = existing_review.review_interval if existing_review else ReviewInterval(7)

            # Compute new scores
            calculator = MasteryCalculator()
            computation = calculator.compute(
                attempts=list(attempt_history),
                algorithm=algorithm,
                current_review_interval=current_interval,
                previous_memory_score=mastery_score.memory_score,
                previous_durable_mastery=mastery_score.durable_mastery_score,
            )

            # Apply the update
            mastery_score.apply_update(
                new_memory_score=computation.memory_score,
                new_durable_mastery_score=computation.durable_mastery_score,
                new_mastery_score_combined=computation.mastery_score_combined,
                new_confidence_interval=computation.confidence_interval,
                new_evidence_count=computation.evidence_count,
                algorithm_version_id=algorithm.id,
                mastered_threshold=algorithm.mastery_threshold_mastered,
                proficient_threshold=algorithm.mastery_threshold_proficient,
                memory_threshold=algorithm.memory_threshold,
                last_attempt_at=computation.last_attempt_at,
            )

            try:
                await _uow.mastery_scores.save(mastery_score)
            except Exception:
                # Optimistic concurrency — reload and retry
                mastery_score = await _uow.mastery_scores.get_by_enrollment_and_concept(
                    instance.learner_enrollment_id, concept_id
                )
                if mastery_score is not None:
                    mastery_score.apply_update(
                        new_memory_score=computation.memory_score,
                        new_durable_mastery_score=computation.durable_mastery_score,
                        new_mastery_score_combined=computation.mastery_score_combined,
                        new_confidence_interval=computation.confidence_interval,
                        new_evidence_count=computation.evidence_count,
                        algorithm_version_id=algorithm.id,
                        mastered_threshold=algorithm.mastery_threshold_mastered,
                        proficient_threshold=algorithm.mastery_threshold_proficient,
                        memory_threshold=algorithm.memory_threshold,
                    )
                    await _uow.mastery_scores.save(mastery_score)

            mastery_result = mastery_score

            # ============================================================
            # 6. Schedule/reschedule review
            # ============================================================
            review_priority = _derive_review_priority(
                computation.memory_score, algorithm.memory_threshold
            )

            if existing_review is None:
                review_result = Review.schedule(
                    learner_enrollment_id=instance.learner_enrollment_id,
                    concept_id=concept_id,
                    algorithm_version_id=algorithm.id,
                    interval=computation.new_review_interval,
                    priority=review_priority,
                )
                await _uow.reviews.add(review_result)
            else:
                existing_review.reschedule(
                    new_interval=computation.new_review_interval,
                    priority=review_priority,
                    review_outcome=scoring_outcome,
                )
                await _uow.reviews.save(existing_review)
                review_result = existing_review

        # ============================================================
        # 7. Update streak
        # ============================================================
        streak = await _uow.streaks.get_by_enrollment(instance.learner_enrollment_id)
        if streak is None:
            streak = Streak(learner_enrollment_id=instance.learner_enrollment_id)
        streak.record_study()
        await _uow.streaks.save(streak)

        # ============================================================
        # 8. Generate recommendation (rule-based, no AI)
        # ============================================================
        recommendation: Recommendation | None = None
        if mastery_result is not None and mastery_result.is_weak:
            rec_type = "weak_concept_remediation"
            rec_score = 0.8 if mastery_result.weakness_severity == WeaknessSeverity.SEVERE else 0.6
            recommendation = Recommendation.generate(
                learner_enrollment_id=instance.learner_enrollment_id,
                recommendation_type=rec_type,
                payload={"concept_id": str(mastery_result.concept_id.value)},
                score=rec_score,
            )
            await _uow.recommendations.add(recommendation)
        elif mastery_result is not None and mastery_result.is_mastered:
            recommendation = Recommendation.generate(
                learner_enrollment_id=instance.learner_enrollment_id,
                recommendation_type="advance_to_next",
                payload={"concept_id": str(mastery_result.concept_id.value)},
                score=0.7,
            )
            await _uow.recommendations.add(recommendation)

        # ============================================================
        # 9. Explanation already loaded from Explanation table above (Task 014)
        # No dynamic building — content comes from the database.
        # ============================================================

        # ============================================================
        # 10. Collect all domain events
        # ============================================================
        all_events = (
            attempt.collect_events()
            + instance.collect_events()
            + (study_session.collect_events() if study_session else [])
            + (mastery_result.collect_events() if mastery_result else [])
            + (review_result.collect_events() if review_result else [])
            + (recommendation.collect_events() if recommendation else [])
            + streak.collect_events()
        )

        # Write events to outbox (same transaction)
        await OutboxEventWriter.write_events(
            session,
            all_events,
            originating_schema="assessment",
            actor_user_id=user_id,
        )

        # ============================================================
        # 11. Commit
        # ============================================================
        await _uow.commit()

    # ============================================================
    # 12. Build response
    # ============================================================
    return SubmitAnswerResponse(
        attempt=AttemptResultResponse(
            attempt_id=attempt.id.value,
            scoring_outcome=attempt.scoring_outcome.value,
            partial_credit=attempt.partial_credit,
            time_to_answer_ms=attempt.time_to_answer.milliseconds,
            hint_used=attempt.hint_used,
            created_at=attempt.created_at.isoformat(),
            # Phase 1 Indian localization
            marks_delta=marks_delta,
            error_type=error_type,
            speed_score=round(speed_score, 4),
            performance_index=performance_index,
        ),
        mastery=MasteryScoreDTO(
            concept_id=mastery_result.concept_id.value,
            memory_score=mastery_result.memory_score,
            durable_mastery_score=mastery_result.durable_mastery_score,
            mastery_score_combined=mastery_result.mastery_score_combined,
            concept_state=mastery_result.concept_state.value,
            weakness_severity=mastery_result.weakness_severity.value,
            evidence_count=mastery_result.evidence_count,
            last_attempt_at=mastery_result.last_attempt_at.isoformat() if mastery_result.last_attempt_at else None,
        ) if mastery_result else None,
        review=ReviewDTO(
            concept_id=review_result.concept_id.value,
            due_at=review_result.due_at.isoformat(),
            priority=review_result.priority.value,
            interval_days=review_result.review_interval.days,
        ) if review_result else None,
        explanation=ExplanationDTO(
            content=explanation_content,
            outcome_key=scoring_outcome.value,
        ),
        recommendation=RecommendationDTO(
            id=recommendation.id.value,
            recommendation_type=recommendation.recommendation_type,
            score=recommendation.score,
            reason=recommendation.recommendation_type,
        ) if recommendation else None,
    )


# ============================================================
# Dashboard endpoint (enriched)
# ============================================================


# ============================================================
# Helper Functions
# ============================================================


def _derive_review_priority(memory_score: float, memory_threshold: float) -> ReviewPriority:
    """Derive review priority from the memory score."""
    if memory_score < memory_threshold * 0.5:
        return ReviewPriority.HIGH
    if memory_score < memory_threshold:
        return ReviewPriority.MEDIUM
    return ReviewPriority.LOW


def _build_explanation(
    scoring_outcome: ScoringOutcome,
    hint_used: bool,
    correct_answer: dict[str, Any],
    learner_answer: dict[str, Any],
    rendered_choices: list[dict[str, Any]] | None = None,
) -> str:
    """Build an explanation based on the scoring outcome.

    Rules:
    - Correct → short reinforcement
    - Incorrect → detailed explanation
    - Hint used → expanded explanation
    """
    correct_value = correct_answer.get("answer", "the correct answer")

    if scoring_outcome == ScoringOutcome.CORRECT:
        if hint_used:
            return f"Correct! You used a hint, but you got there. The answer is '{correct_value}'. " \
                   f"Try to recall it without hints next time to strengthen your memory."
        return f"Correct! The answer is '{correct_value}'. Well done."

    if scoring_outcome == ScoringOutcome.PARTIAL:
        return f"Partially correct. The full answer is '{correct_value}'. " \
               f"Review the parts you missed and try again."

    # Incorrect — find the learner's selected choice text
    learner_value = "your answer"
    learner_choice_id = learner_answer.get("choice_id") or learner_answer.get("choice")
    if learner_choice_id and rendered_choices:
        for ch in rendered_choices:
            if ch.get("id") == learner_choice_id:
                learner_value = ch.get("text", "your answer")
                break
    elif learner_answer.get("answer"):
        learner_value = learner_answer["answer"]
    elif learner_answer.get("text"):
        learner_value = learner_answer["text"]

    if hint_used:
        return f"Incorrect. You chose '{learner_value}' but the correct answer is '{correct_value}'. " \
               f"Since you used a hint, here's a more detailed explanation: " \
               f"the key insight is that '{correct_value}' is correct because it directly " \
               f"addresses the question's core requirement. Review the concept and try again."

    return f"Incorrect. You chose '{learner_value}' but the correct answer is '{correct_value}'. " \
           f"Review the concept and try again. The key is understanding why " \
           f"'{correct_value}' is the right choice."
