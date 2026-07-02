"""Learning + Mastery + Assessment context — query handlers.

Query handlers are read-only. They load data from repositories, build DTOs,
and return them. They NEVER modify state.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.application.shared import (
    AuthorizationDenied,
    Query,
    QueryHandler,
    ResourceMissing,
    UnitOfWork,
)
from app.application.learning.dto import (
    AttemptDTO,
    DashboardDTO,
    EnrollmentDTO,
    MasteryScoreDTO,
    RecommendationDTO,
    StudySessionDTO,
)
from app.domain.shared.ids import (
    LearnerEnrollmentId,
    StudySessionId,
)


# ============================================================
# Queries
# ============================================================


class GetDashboardQuery(Query):
    """Query: Get the learner's dashboard."""

    def __init__(self, enrollment_id: UUID) -> None:
        self.enrollment_id = enrollment_id


class GetMasteryScoresQuery(Query):
    """Query: Get mastery scores for a learner."""

    def __init__(self, enrollment_id: UUID, weak_only: bool = False) -> None:
        self.enrollment_id = enrollment_id
        self.weak_only = weak_only


class GetAttemptHistoryQuery(Query):
    """Query: Get attempt history for a learner."""

    def __init__(self, enrollment_id: UUID, limit: int = 50, offset: int = 0) -> None:
        self.enrollment_id = enrollment_id
        self.limit = limit
        self.offset = offset


class GetRecommendationsQuery(Query):
    """Query: Get recommendations for a learner."""

    def __init__(self, enrollment_id: UUID, active_only: bool = False) -> None:
        self.enrollment_id = enrollment_id
        self.active_only = active_only


class GetStudySessionQuery(Query):
    """Query: Get a study session by ID."""

    def __init__(self, session_id: UUID) -> None:
        self.session_id = session_id


# ============================================================
# Query Handlers
# ============================================================


class GetDashboardHandler(QueryHandler[GetDashboardQuery, DashboardDTO]):
    """Handler for GetDashboardQuery."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, query: GetDashboardQuery) -> DashboardDTO:
        enrollment_id = LearnerEnrollmentId(query.enrollment_id)

        async with self._uow as uow:
            # Load enrollment
            enrollment = await uow.enrollments.get_by_id(enrollment_id)
            if enrollment is None:
                raise ResourceMissing("Enrollment", query.enrollment_id)

            # Load weak concepts
            weak_scores = await uow.mastery_scores.list_weak_by_enrollment(enrollment_id)
            weak_dtos = [
                MasteryScoreDTO(
                    concept_id=s.concept_id.value,
                    memory_score=s.memory_score,
                    durable_mastery_score=s.durable_mastery_score,
                    mastery_score_combined=s.mastery_score_combined,
                    concept_state=s.concept_state.value,
                    weakness_severity=s.weakness_severity.value,
                    evidence_count=s.evidence_count,
                    last_attempt_at=s.last_attempt_at,
                )
                for s in weak_scores
            ]

            # Load streak
            streak = await uow.streaks.get_by_enrollment(enrollment_id)
            current_streak = streak.current_streak if streak else 0

            # Determine recommended action
            active_session = await uow.study_sessions.get_active_by_enrollment(enrollment_id)
            if active_session is not None:
                recommended_action = "continue_session"
            elif weak_dtos:
                recommended_action = "drill_weak_concepts"
            else:
                recommended_action = "start_session"

            return DashboardDTO(
                enrollment_id=query.enrollment_id,
                recommended_action=recommended_action,
                current_streak=current_streak,
                weak_concepts=weak_dtos,
            )


class GetMasteryScoresHandler(QueryHandler[GetMasteryScoresQuery, list[MasteryScoreDTO]]):
    """Handler for GetMasteryScoresQuery."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, query: GetMasteryScoresQuery) -> list[MasteryScoreDTO]:
        enrollment_id = LearnerEnrollmentId(query.enrollment_id)

        async with self._uow as uow:
            if query.weak_only:
                scores = await uow.mastery_scores.list_weak_by_enrollment(enrollment_id)
            else:
                scores = await uow.mastery_scores.list_by_enrollment(enrollment_id)

            return [
                MasteryScoreDTO(
                    concept_id=s.concept_id.value,
                    memory_score=s.memory_score,
                    durable_mastery_score=s.durable_mastery_score,
                    mastery_score_combined=s.mastery_score_combined,
                    concept_state=s.concept_state.value,
                    weakness_severity=s.weakness_severity.value,
                    evidence_count=s.evidence_count,
                    last_attempt_at=s.last_attempt_at,
                )
                for s in scores
            ]


class GetAttemptHistoryHandler(QueryHandler[GetAttemptHistoryQuery, list[AttemptDTO]]):
    """Handler for GetAttemptHistoryQuery."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, query: GetAttemptHistoryQuery) -> list[AttemptDTO]:
        enrollment_id = LearnerEnrollmentId(query.enrollment_id)

        async with self._uow as uow:
            attempts = await uow.attempts.list_by_enrollment(
                enrollment_id, limit=query.limit, offset=query.offset
            )

            return [
                AttemptDTO(
                    id=a.id.value,
                    scoring_outcome=a.scoring_outcome.value,
                    time_to_answer_ms=a.time_to_answer.milliseconds,
                    hint_used=a.hint_used,
                    attempt_intent=a.attempt_intent.value,
                    created_at=a.created_at,
                )
                for a in attempts
            ]


class GetRecommendationsHandler(QueryHandler[GetRecommendationsQuery, list[RecommendationDTO]]):
    """Handler for GetRecommendationsQuery."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, query: GetRecommendationsQuery) -> list[RecommendationDTO]:
        enrollment_id = LearnerEnrollmentId(query.enrollment_id)

        async with self._uow as uow:
            recs = await uow.recommendations.list_by_enrollment(
                enrollment_id, active_only=query.active_only
            )

            return [
                RecommendationDTO(
                    id=r.id.value,
                    enrollment_id=r.learner_enrollment_id.value,
                    recommendation_type=r.recommendation_type,
                    score=r.score,
                    status=r.status.value,
                )
                for r in recs
            ]


class GetStudySessionHandler(QueryHandler[GetStudySessionQuery, StudySessionDTO]):
    """Handler for GetStudySessionQuery."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def handle(self, query: GetStudySessionQuery) -> StudySessionDTO:
        async with self._uow as uow:
            session = await uow.study_sessions.get_by_id(
                StudySessionId(query.session_id)
            )
            if session is None:
                raise ResourceMissing("StudySession", query.session_id)

            return StudySessionDTO(
                id=session.id.value,
                learner_enrollment_id=session.learner_enrollment_id.value,
                intent=session.intent.value,
                status=session.status.value,
                started_at=session.started_at,
                ended_at=session.ended_at,
                question_count=session.question_count,
            )
