"""Repository implementations using SQLAlchemy 2.x async.

Each repository implements the domain's abstract repository interface.
Repositories return domain entities (via mappers); they never expose ORM models.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, update, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.assessment.attempt import Attempt
from app.domain.assessment.question_instance import QuestionInstance
from app.domain.assessment.repository import (
    AttemptRepository as AttemptRepositoryInterface,
    QuestionInstanceRepository as QuestionInstanceRepositoryInterface,
)
from app.domain.identity.repository import (
    UserRepository as UserRepositoryInterface,
)
from app.domain.identity.user import User
from app.domain.learning.enrollment import LearnerEnrollment
from app.domain.learning.repository import (
    EnrollmentRepository as EnrollmentRepositoryInterface,
    StudySessionRepository as StudySessionRepositoryInterface,
)
from app.domain.learning.study_session import StudySession
from app.domain.mastery.algorithm_version import AlgorithmVersion
from app.domain.mastery.mastery_score import MasteryScore
from app.domain.mastery.repository import (
    AlgorithmVersionRepository as AlgorithmVersionRepositoryInterface,
    MasteryScoreRepository as MasteryScoreRepositoryInterface,
    ReviewRepository as ReviewRepositoryInterface,
)
from app.domain.mastery.review import Review
from app.domain.shared.ids import (
    AlgorithmVersionId,
    AttemptId,
    ConceptId,
    LearnerEnrollmentId,
    MasteryScoreId,
    QuestionInstanceId,
    ReviewId,
    StudySessionId,
    SubjectId,
    UserId,
)
from app.domain.shared.kernel import (
    EnrollmentStatus,
    SessionStatus,
)
from app.domain.shared.value_objects import Email
from app.infrastructure.database.mappers import (
    AlgorithmVersionMapper,
    AttemptMapper,
    EnrollmentMapper,
    MasteryScoreMapper,
    QuestionInstanceMapper,
    ReviewMapper,
    StudySessionMapper,
    UserMapper,
)
from app.infrastructure.database.orm.core import (
    AlgorithmVersionModel,
    AttemptModel,
    LearnerEnrollmentModel,
    MasteryScoreModel,
    QuestionInstanceModel,
    ReviewModel,
    StudySessionModel,
)
from app.infrastructure.database.orm.identity import UserModel


# ============================================================
# Identity
# ============================================================


class SqlAlchemyUserRepository(UserRepositoryInterface):
    """SQLAlchemy implementation of UserRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UserId) -> User | None:
        result = await self._session.get(UserModel, id.value)
        if result is None:
            return None
        return UserMapper.from_orm(result)

    async def get_by_email(self, email: Email) -> User | None:
        stmt = select(UserModel).where(
            UserModel.email == email.value,
            UserModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return UserMapper.from_orm(model) if model else None

    async def add(self, user: User) -> User:
        model = UserMapper.to_orm(user)
        self._session.add(model)
        await self._session.flush()
        return user

    async def save(self, user: User) -> None:
        model = UserMapper.to_orm(user)
        merged = await self._session.merge(model)
        await self._session.flush()


# ============================================================
# Learning
# ============================================================


class SqlAlchemyEnrollmentRepository(EnrollmentRepositoryInterface):
    """SQLAlchemy implementation of EnrollmentRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: LearnerEnrollmentId) -> LearnerEnrollment | None:
        model = await self._session.get(LearnerEnrollmentModel, id.value)
        return EnrollmentMapper.from_orm(model) if model else None

    async def get_by_user_and_subject(
        self, user_id: UserId, subject_id: SubjectId
    ) -> LearnerEnrollment | None:
        stmt = select(LearnerEnrollmentModel).where(
            LearnerEnrollmentModel.user_id == user_id.value,
            LearnerEnrollmentModel.subject_id == subject_id.value,
            LearnerEnrollmentModel.status != EnrollmentStatus.UNENROLLED.value,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return EnrollmentMapper.from_orm(model) if model else None

    async def list_by_user(self, user_id: UserId) -> Sequence[LearnerEnrollment]:
        stmt = select(LearnerEnrollmentModel).where(
            LearnerEnrollmentModel.user_id == user_id.value,
        )
        result = await self._session.execute(stmt)
        return [EnrollmentMapper.from_orm(m) for m in result.scalars().all()]

    async def add(self, enrollment: LearnerEnrollment) -> LearnerEnrollment:
        model = EnrollmentMapper.to_orm(enrollment)
        self._session.add(model)
        await self._session.flush()
        return enrollment

    async def save(self, enrollment: LearnerEnrollment) -> None:
        model = EnrollmentMapper.to_orm(enrollment)
        await self._session.merge(model)
        await self._session.flush()


class SqlAlchemyStudySessionRepository(StudySessionRepositoryInterface):
    """SQLAlchemy implementation of StudySessionRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: StudySessionId) -> StudySession | None:
        model = await self._session.get(StudySessionModel, id.value)
        return StudySessionMapper.from_orm(model) if model else None

    async def get_active_by_enrollment(
        self, enrollment_id: LearnerEnrollmentId
    ) -> StudySession | None:
        stmt = select(StudySessionModel).where(
            StudySessionModel.learner_enrollment_id == enrollment_id.value,
            StudySessionModel.status.in_([SessionStatus.ACTIVE.value, SessionStatus.PAUSED.value]),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return StudySessionMapper.from_orm(model) if model else None

    async def list_by_enrollment(
        self, enrollment_id: LearnerEnrollmentId, limit: int = 50, offset: int = 0
    ) -> Sequence[StudySession]:
        stmt = (
            select(StudySessionModel)
            .where(StudySessionModel.learner_enrollment_id == enrollment_id.value)
            .order_by(StudySessionModel.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [StudySessionMapper.from_orm(m) for m in result.scalars().all()]

    async def add(self, session: StudySession) -> StudySession:
        model = StudySessionMapper.to_orm(session)
        self._session.add(model)
        await self._session.flush()
        return session

    async def save(self, session: StudySession) -> None:
        model = StudySessionMapper.to_orm(session)
        await self._session.merge(model)
        await self._session.flush()


# ============================================================
# Assessment
# ============================================================


class SqlAlchemyQuestionInstanceRepository(QuestionInstanceRepositoryInterface):
    """SQLAlchemy implementation of QuestionInstanceRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: QuestionInstanceId) -> QuestionInstance | None:
        model = await self._session.get(QuestionInstanceModel, id.value)
        return QuestionInstanceMapper.from_orm(model) if model else None

    async def add(self, instance: QuestionInstance) -> QuestionInstance:
        model = QuestionInstanceMapper.to_orm(instance)
        self._session.add(model)
        await self._session.flush()
        return instance

    async def save(self, instance: QuestionInstance) -> None:
        model = QuestionInstanceMapper.to_orm(instance)
        await self._session.merge(model)
        await self._session.flush()

    async def list_by_session(self, study_session_id: StudySessionId) -> Sequence[QuestionInstance]:
        stmt = select(QuestionInstanceModel).where(
            QuestionInstanceModel.study_session_id == study_session_id.value
        )
        result = await self._session.execute(stmt)
        return [QuestionInstanceMapper.from_orm(m) for m in result.scalars().all()]


class SqlAlchemyAttemptRepository(AttemptRepositoryInterface):
    """SQLAlchemy implementation of AttemptRepository.

    Attempts are append-only — there is no ``save`` or ``update`` method.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: AttemptId) -> Attempt | None:
        model = await self._session.get(AttemptModel, id.value)
        return AttemptMapper.from_orm(model) if model else None

    async def add(self, attempt: Attempt) -> Attempt:
        model = AttemptMapper.to_orm(attempt)
        self._session.add(model)
        await self._session.flush()
        return attempt

    async def list_by_enrollment(
        self, enrollment_id: LearnerEnrollmentId, limit: int = 100, offset: int = 0
    ) -> Sequence[Attempt]:
        stmt = (
            select(AttemptModel)
            .where(AttemptModel.learner_enrollment_id == enrollment_id.value)
            .order_by(AttemptModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [AttemptMapper.from_orm(m) for m in result.scalars().all()]

    async def list_by_enrollment_and_concept(
        self, enrollment_id: LearnerEnrollmentId, concept_id: UUID
    ) -> Sequence[Attempt]:
        # Note: In a full implementation, this requires a join through
        # template_versions → template_concepts to filter by concept.
        # For the scaffold, we return all attempts for the enrollment
        # and let the application layer filter.
        # The production implementation would add the join.
        stmt = (
            select(AttemptModel)
            .where(AttemptModel.learner_enrollment_id == enrollment_id.value)
            .order_by(AttemptModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [AttemptMapper.from_orm(m) for m in result.scalars().all()]

    async def count_by_enrollment(self, enrollment_id: LearnerEnrollmentId) -> int:
        stmt = (
            select(func.count())
            .select_from(AttemptModel)
            .where(AttemptModel.learner_enrollment_id == enrollment_id.value)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()


# ============================================================
# Mastery
# ============================================================


class SqlAlchemyMasteryScoreRepository(MasteryScoreRepositoryInterface):
    """SQLAlchemy implementation of MasteryScoreRepository.

    Implements optimistic concurrency: ``save`` checks the ``version`` field.
    If the version in the database doesn't match, the save fails (no rows updated).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: MasteryScoreId) -> MasteryScore | None:
        model = await self._session.get(MasteryScoreModel, id.value)
        return MasteryScoreMapper.from_orm(model) if model else None

    async def get_by_enrollment_and_concept(
        self, enrollment_id: LearnerEnrollmentId, concept_id: ConceptId
    ) -> MasteryScore | None:
        stmt = select(MasteryScoreModel).where(
            MasteryScoreModel.learner_enrollment_id == enrollment_id.value,
            MasteryScoreModel.concept_id == concept_id.value,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return MasteryScoreMapper.from_orm(model) if model else None

    async def list_by_enrollment(
        self, enrollment_id: LearnerEnrollmentId
    ) -> Sequence[MasteryScore]:
        stmt = select(MasteryScoreModel).where(
            MasteryScoreModel.learner_enrollment_id == enrollment_id.value
        )
        result = await self._session.execute(stmt)
        return [MasteryScoreMapper.from_orm(m) for m in result.scalars().all()]

    async def list_weak_by_enrollment(
        self, enrollment_id: LearnerEnrollmentId
    ) -> Sequence[MasteryScore]:
        stmt = select(MasteryScoreModel).where(
            MasteryScoreModel.learner_enrollment_id == enrollment_id.value,
            MasteryScoreModel.weakness_severity != "none",
        )
        result = await self._session.execute(stmt)
        return [MasteryScoreMapper.from_orm(m) for m in result.scalars().all()]

    async def add(self, score: MasteryScore) -> MasteryScore:
        model = MasteryScoreMapper.to_orm(score)
        self._session.add(model)
        await self._session.flush()
        return score

    async def save(self, score: MasteryScore) -> None:
        """Save with optimistic concurrency check.

        If the version in the database doesn't match ``score.version``,
        no rows are updated — the caller must retry.
        """
        model = MasteryScoreMapper.to_orm(score)
        # Use UPDATE with WHERE version = expected_version
        stmt = (
            update(MasteryScoreModel)
            .where(
                MasteryScoreModel.id == model.id,
                MasteryScoreModel.version == model.version - 1,  # The old version
            )
            .values(
                memory_score=model.memory_score,
                durable_mastery_score=model.durable_mastery_score,
                mastery_score_combined=model.mastery_score_combined,
                confidence_interval=model.confidence_interval,
                evidence_count=model.evidence_count,
                concept_state=model.concept_state,
                weakness_severity=model.weakness_severity,
                version=model.version,  # The new version
                last_attempt_at=model.last_attempt_at,
                last_updated_at=model.last_updated_at,
                algorithm_version_id=model.algorithm_version_id,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise ConcurrentUpdateError(f"MasteryScore {model.id}: version conflict")
        await self._session.flush()

    async def count_by_algorithm_version(
        self, algorithm_version_id: AlgorithmVersionId
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(MasteryScoreModel)
            .where(MasteryScoreModel.algorithm_version_id == algorithm_version_id.value)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()


class SqlAlchemyReviewRepository(ReviewRepositoryInterface):
    """SQLAlchemy implementation of ReviewRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: ReviewId) -> Review | None:
        model = await self._session.get(ReviewModel, id.value)
        return ReviewMapper.from_orm(model) if model else None

    async def get_by_enrollment_and_concept(
        self, enrollment_id: LearnerEnrollmentId, concept_id: ConceptId
    ) -> Review | None:
        stmt = select(ReviewModel).where(
            ReviewModel.learner_enrollment_id == enrollment_id.value,
            ReviewModel.concept_id == concept_id.value,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return ReviewMapper.from_orm(model) if model else None

    async def list_due_by_enrollment(
        self, enrollment_id: LearnerEnrollmentId
    ) -> Sequence[Review]:
        stmt = select(ReviewModel).where(
            ReviewModel.learner_enrollment_id == enrollment_id.value,
            ReviewModel.due_at <= func.now(),
        )
        result = await self._session.execute(stmt)
        return [ReviewMapper.from_orm(m) for m in result.scalars().all()]

    async def add(self, review: Review) -> Review:
        model = ReviewMapper.to_orm(review)
        self._session.add(model)
        await self._session.flush()
        return review

    async def save(self, review: Review) -> None:
        model = ReviewMapper.to_orm(review)
        await self._session.merge(model)
        await self._session.flush()


class SqlAlchemyAlgorithmVersionRepository(AlgorithmVersionRepositoryInterface):
    """SQLAlchemy implementation of AlgorithmVersionRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: AlgorithmVersionId) -> AlgorithmVersion | None:
        model = await self._session.get(AlgorithmVersionModel, id.value)
        return AlgorithmVersionMapper.from_orm(model) if model else None

    async def get_active(self) -> AlgorithmVersion | None:
        stmt = select(AlgorithmVersionModel).where(
            AlgorithmVersionModel.is_active == True  # noqa: E712
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return AlgorithmVersionMapper.from_orm(model) if model else None

    async def list_all(self) -> Sequence[AlgorithmVersion]:
        stmt = select(AlgorithmVersionModel).order_by(AlgorithmVersionModel.version_number)
        result = await self._session.execute(stmt)
        return [AlgorithmVersionMapper.from_orm(m) for m in result.scalars().all()]

    async def add(self, version: AlgorithmVersion) -> AlgorithmVersion:
        model = AlgorithmVersionMapper.to_orm(version)
        self._session.add(model)
        await self._session.flush()
        return version

    async def save(self, version: AlgorithmVersion) -> None:
        model = AlgorithmVersionMapper.to_orm(version)
        await self._session.merge(model)
        await self._session.flush()


# ============================================================
# Concurrency Error
# ============================================================


class ConcurrentUpdateError(Exception):
    """Raised when optimistic concurrency check fails (version mismatch)."""
