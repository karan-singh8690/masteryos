"""Domain mappers — bidirectional conversion between domain entities and ORM models.

Mappers are the ONLY place where ORM models and domain entities interact.
Repositories use mappers to convert; handlers never see ORM models.

Pattern:
    domain_entity = Mapper.from_orm(orm_model)
    orm_model = Mapper.to_orm(domain_entity)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.domain.assessment.answer import Answer
from app.domain.assessment.attempt import Attempt
from app.domain.assessment.question_instance import QuestionInstance, QuestionInstanceStatus
from app.domain.identity.user import User, UserProfile
from app.domain.identity.credential import UserCredential
from app.domain.learning.enrollment import LearnerEnrollment
from app.domain.learning.study_session import StudySession
from app.domain.mastery.algorithm_version import AlgorithmVersion
from app.domain.mastery.mastery_score import MasteryScore
from app.domain.mastery.review import Review
from app.domain.shared.ids import (
    AlgorithmVersionId,
    AnswerId,
    AttemptId,
    ConceptId,
    ContentVersionId,
    CredentialId,
    LearnerEnrollmentId,
    LearningPathId,
    MasteryScoreId,
    QuestionInstanceId,
    ReviewId,
    StudySessionId,
    SubjectId,
    TemplateVersionId,
    UserId,
)
from app.domain.shared.kernel import (
    AttemptIntent,
    ConceptState,
    CredentialType,
    EnrollmentStatus,
    ScoringOutcome,
    SessionIntent,
    SessionStatus,
    UserStatus,
    VersionNumber,
    WeaknessSeverity,
)
from app.domain.shared.value_objects import Duration, Email, ReviewInterval
from app.infrastructure.database.orm.core import (
    AlgorithmVersionModel,
    AnswerModel,
    AttemptModel,
    MasteryScoreModel,
    OutboxEventModel,
    QuestionInstanceModel,
    ReviewModel,
    StudySessionModel,
    LearnerEnrollmentModel,
)
from app.infrastructure.database.orm.identity import (
    SessionModel,
    UserCredentialModel,
    UserModel,
    UserProfileModel,
)


# ============================================================
# Identity Mappers
# ============================================================


class UserMapper:
    """Maps User aggregate ⇄ UserModel."""

    @staticmethod
    def from_orm(model: UserModel) -> User:
        """Convert ORM model to domain User."""
        # Reconstruct the User from stored state
        user = User.__new__(User)
        AggregateRoot_init = type(user).__mro__[1]  # AggregateRoot
        AggregateRoot_init.__init__(user)  # type: ignore[arg-type]

        user._id = UserId(model.id)  # type: ignore[attr-defined]
        user._email = Email(model.email)  # type: ignore[attr-defined]
        user._status = UserStatus(model.status)  # type: ignore[attr-defined]
        user._mfa_enabled = model.mfa_enabled  # type: ignore[attr-defined]
        user._email_verified_at = model.email_verified_at  # type: ignore[attr-defined]
        user._mfa_secret_encrypted = model.mfa_secret_encrypted  # type: ignore[attr-defined]
        user._created_at = model.created_at  # type: ignore[attr-defined]
        user._updated_at = model.updated_at  # type: ignore[attr-defined]
        user._deleted_at = model.deleted_at  # type: ignore[attr-defined]
        user._anonymized_at = model.anonymized_at  # type: ignore[attr-defined]

        # Reconstruct profile if present
        if model.profile is not None:
            user._profile = UserProfileMapper.from_orm(model.profile)  # type: ignore[attr-defined]
        else:
            user._profile = None  # type: ignore[attr-defined]

        return user

    @staticmethod
    def to_orm(user: User) -> UserModel:
        """Convert domain User to ORM model."""
        model = UserModel(
            id=user.id.value,
            email=user.email.value,
            email_verified_at=user.email_verified_at,
            status=user.status.value,
            mfa_enabled=user.mfa_enabled,
            mfa_secret_encrypted=getattr(user, "_mfa_secret_encrypted", None),
            anonymized_at=getattr(user, "_anonymized_at", None),
            created_at=user.created_at,
            updated_at=getattr(user, "_updated_at", user.created_at),
        )
        if user.profile is not None:
            model.profile = UserProfileMapper.to_orm(user.profile, user.id.value)
        return model


class UserProfileMapper:
    """Maps UserProfile ⇄ UserProfileModel."""

    @staticmethod
    def from_orm(model: UserProfileModel) -> UserProfile:
        return UserProfile(
            display_name=model.display_name,
            timezone=model.timezone,
            locale=model.locale,
            avatar_url=model.avatar_url,
            preferences=model.preferences or {},
        )

    @staticmethod
    def to_orm(profile: UserProfile, user_id: UUID) -> UserProfileModel:
        return UserProfileModel(
            user_id=user_id,
            display_name=profile.display_name,
            timezone=profile.timezone,
            locale=profile.locale,
            avatar_url=profile.avatar_url,
            preferences=profile.preferences,
        )


# ============================================================
# Learning Mappers
# ============================================================


class EnrollmentMapper:
    """Maps LearnerEnrollment ⇄ LearnerEnrollmentModel."""

    @staticmethod
    def from_orm(model: LearnerEnrollmentModel) -> LearnerEnrollment:
        enrollment = LearnerEnrollment.__new__(LearnerEnrollment)
        # Initialize AggregateRoot
        from app.domain.shared.kernel import AggregateRoot
        AggregateRoot.__init__(enrollment)

        enrollment.id = LearnerEnrollmentId(model.id)
        enrollment.user_id = UserId(model.user_id)
        enrollment.subject_id = SubjectId(model.subject_id)
        enrollment.learning_path_id = LearningPathId(model.learning_path_id) if model.learning_path_id else None
        enrollment.status = EnrollmentStatus(model.status)
        enrollment.enrolled_at = model.enrolled_at
        enrollment.onboarded_at = model.onboarded_at
        enrollment.last_active_at = model.last_active_at
        enrollment.unenrolled_at = model.unenrolled_at
        return enrollment

    @staticmethod
    def to_orm(enrollment: LearnerEnrollment) -> LearnerEnrollmentModel:
        return LearnerEnrollmentModel(
            id=enrollment.id.value,
            user_id=enrollment.user_id.value,
            subject_id=enrollment.subject_id.value,
            learning_path_id=enrollment.learning_path_id.value if enrollment.learning_path_id else None,
            status=enrollment.status.value,
            enrolled_at=enrollment.enrolled_at,
            onboarded_at=enrollment.onboarded_at,
            last_active_at=enrollment.last_active_at,
            unenrolled_at=enrollment.unenrolled_at,
        )


class StudySessionMapper:
    """Maps StudySession ⇄ StudySessionModel."""

    @staticmethod
    def from_orm(model: StudySessionModel) -> StudySession:
        session = StudySession.__new__(StudySession)
        from app.domain.shared.kernel import AggregateRoot
        AggregateRoot.__init__(session)

        session.id = StudySessionId(model.id)
        session.learner_enrollment_id = LearnerEnrollmentId(model.learner_enrollment_id)
        session.learning_session_id = None  # Not loaded by default
        session.intent = SessionIntent(model.intent)
        session.target_question_count = model.target_question_count
        session.started_at = model.started_at
        session.ended_at = model.ended_at
        session.status = SessionStatus(model.status)
        session.question_count = model.question_count
        return session

    @staticmethod
    def to_orm(session: StudySession) -> StudySessionModel:
        return StudySessionModel(
            id=session.id.value,
            learner_enrollment_id=session.learner_enrollment_id.value,
            intent=session.intent.value,
            target_question_count=session.target_question_count,
            started_at=session.started_at,
            ended_at=session.ended_at,
            status=session.status.value,
            question_count=session.question_count,
        )


# ============================================================
# Assessment Mappers
# ============================================================


class QuestionInstanceMapper:
    """Maps QuestionInstance ⇄ QuestionInstanceModel."""

    @staticmethod
    def from_orm(model: QuestionInstanceModel) -> QuestionInstance:
        instance = QuestionInstance.__new__(QuestionInstance)
        from app.domain.shared.kernel import AggregateRoot
        AggregateRoot.__init__(instance)

        instance.id = QuestionInstanceId(model.id)
        instance.template_version_id = TemplateVersionId(model.template_version_id)
        instance.content_version_id = ContentVersionId(model.content_version_id)
        instance.learner_enrollment_id = LearnerEnrollmentId(model.learner_enrollment_id)
        instance.study_session_id = StudySessionId(model.study_session_id)
        instance.parameter_seed = model.parameter_seed
        instance.parameter_values = model.parameter_values
        instance.rendered_prompt = model.rendered_prompt
        instance.correct_answer = model.correct_answer
        instance.rendered_choices = model.rendered_choices
        instance.distractors_with_tags = model.distractors_with_tags
        instance.served_at = model.served_at
        instance.answered_at = model.answered_at
        instance.status = model.status
        return instance

    @staticmethod
    def to_orm(instance: QuestionInstance) -> QuestionInstanceModel:
        return QuestionInstanceModel(
            id=instance.id.value,
            template_version_id=instance.template_version_id.value,
            content_version_id=instance.content_version_id.value,
            learner_enrollment_id=instance.learner_enrollment_id.value,
            study_session_id=instance.study_session_id.value,
            parameter_seed=instance.parameter_seed,
            parameter_values=instance.parameter_values,
            rendered_prompt=instance.rendered_prompt,
            correct_answer=instance.correct_answer,
            rendered_choices=instance.rendered_choices,
            distractors_with_tags=instance.distractors_with_tags,
            served_at=instance.served_at,
            answered_at=instance.answered_at,
            status=instance.status,
        )


class AttemptMapper:
    """Maps Attempt ⇄ AttemptModel."""

    @staticmethod
    def from_orm(model: AttemptModel) -> Attempt:
        attempt = Attempt.__new__(Attempt)
        from app.domain.shared.kernel import AggregateRoot
        AggregateRoot.__init__(attempt)

        attempt.id = AttemptId(model.id)
        attempt.question_instance_id = QuestionInstanceId(model.question_instance_id)
        attempt.learner_enrollment_id = LearnerEnrollmentId(model.learner_enrollment_id)
        attempt.study_session_id = StudySessionId(model.study_session_id)
        attempt.content_version_id = ContentVersionId(model.content_version_id)
        attempt.template_version_id = TemplateVersionId(model.template_version_id)
        attempt.algorithm_version_id = AlgorithmVersionId(model.algorithm_version_id)
        attempt.scoring_outcome = ScoringOutcome(model.scoring_outcome)
        attempt.time_to_answer = Duration(model.time_to_answer_ms // 1000)
        attempt.hint_used = model.hint_used
        attempt.hint_tiers_used = model.hint_tiers_used or []
        attempt.attempt_intent = AttemptIntent(model.attempt_intent)
        attempt.answer = None  # Loaded separately if needed
        attempt.partial_credit = model.partial_credit
        attempt.misconception_id = None  # Not always loaded
        attempt.created_at = model.created_at
        return attempt

    @staticmethod
    def to_orm(attempt: Attempt) -> AttemptModel:
        return AttemptModel(
            id=attempt.id.value,
            question_instance_id=attempt.question_instance_id.value,
            learner_enrollment_id=attempt.learner_enrollment_id.value,
            study_session_id=attempt.study_session_id.value,
            content_version_id=attempt.content_version_id.value,
            template_version_id=attempt.template_version_id.value,
            algorithm_version_id=attempt.algorithm_version_id.value,
            scoring_outcome=attempt.scoring_outcome.value,
            partial_credit=attempt.partial_credit,
            time_to_answer_ms=attempt.time_to_answer.milliseconds,
            hint_used=attempt.hint_used,
            hint_tiers_used=attempt.hint_tiers_used,
            misconception_id=attempt.misconception_id.value if attempt.misconception_id else None,
            attempt_intent=attempt.attempt_intent.value,
        )


# ============================================================
# Mastery Mappers
# ============================================================


class MasteryScoreMapper:
    """Maps MasteryScore ⇄ MasteryScoreModel."""

    @staticmethod
    def from_orm(model: MasteryScoreModel) -> MasteryScore:
        score = MasteryScore.__new__(MasteryScore)
        from app.domain.shared.kernel import AggregateRoot
        AggregateRoot.__init__(score)

        score.id = MasteryScoreId(model.id)
        score.learner_enrollment_id = LearnerEnrollmentId(model.learner_enrollment_id)
        score.concept_id = ConceptId(model.concept_id)
        score.algorithm_version_id = AlgorithmVersionId(model.algorithm_version_id)
        score._memory_score = model.memory_score
        score._durable_mastery_score = model.durable_mastery_score
        score._mastery_score_combined = model.mastery_score_combined
        score._confidence_interval = model.confidence_interval
        score.evidence_count = model.evidence_count
        score.concept_state = ConceptState(model.concept_state)
        score.weakness_severity = WeaknessSeverity(model.weakness_severity)
        score.version = model.version
        score.last_attempt_at = model.last_attempt_at
        score.last_updated_at = model.last_updated_at
        score.created_at = model.created_at
        return score

    @staticmethod
    def to_orm(score: MasteryScore) -> MasteryScoreModel:
        return MasteryScoreModel(
            id=score.id.value,
            learner_enrollment_id=score.learner_enrollment_id.value,
            concept_id=score.concept_id.value,
            algorithm_version_id=score.algorithm_version_id.value,
            memory_score=score.memory_score,
            durable_mastery_score=score.durable_mastery_score,
            mastery_score_combined=score.mastery_score_combined,
            confidence_interval=score.confidence_interval,
            evidence_count=score.evidence_count,
            concept_state=score.concept_state.value,
            weakness_severity=score.weakness_severity.value,
            version=score.version,
            last_attempt_at=score.last_attempt_at,
            last_updated_at=score.last_updated_at,
        )


class ReviewMapper:
    """Maps Review ⇄ ReviewModel."""

    @staticmethod
    def from_orm(model: ReviewModel) -> Review:
        review = Review.__new__(Review)
        from app.domain.shared.kernel import AggregateRoot
        AggregateRoot.__init__(review)

        review.id = ReviewId(model.id)
        review.learner_enrollment_id = LearnerEnrollmentId(model.learner_enrollment_id)
        review.concept_id = ConceptId(model.concept_id)
        review.algorithm_version_id = AlgorithmVersionId(model.algorithm_version_id)
        review.due_at = model.due_at
        review.priority = model.priority
        review.review_interval = ReviewInterval(int(model.review_interval.replace(" days", "").replace("P", "").replace("D", "")))
        review.last_reviewed_at = model.last_reviewed_at
        review.last_review_outcome = model.last_review_outcome
        review.created_at = model.created_at
        review.updated_at = model.updated_at
        return review

    @staticmethod
    def to_orm(review: Review) -> ReviewModel:
        return ReviewModel(
            id=review.id.value,
            learner_enrollment_id=review.learner_enrollment_id.value,
            concept_id=review.concept_id.value,
            algorithm_version_id=review.algorithm_version_id.value,
            due_at=review.due_at,
            priority=review.priority.value,
            review_interval=f"P{review.review_interval.days}D",
            last_reviewed_at=review.last_reviewed_at,
            last_review_outcome=review.last_review_outcome.value if review.last_review_outcome else None,
        )


class AlgorithmVersionMapper:
    """Maps AlgorithmVersion ⇄ AlgorithmVersionModel."""

    @staticmethod
    def from_orm(model: AlgorithmVersionModel) -> AlgorithmVersion:
        version = AlgorithmVersion.__new__(AlgorithmVersion)
        from app.domain.shared.kernel import AggregateRoot
        AggregateRoot.__init__(version)

        version.id = AlgorithmVersionId(model.id)
        version.version_number = VersionNumber(model.version_number)
        version.name = model.name
        version.parameters = model.parameters
        version.description = model.description
        version.changelog = model.changelog
        version.is_active = model.is_active
        version.promoted_at = model.promoted_at
        version.created_at = model.created_at
        return version

    @staticmethod
    def to_orm(version: AlgorithmVersion) -> AlgorithmVersionModel:
        return AlgorithmVersionModel(
            id=version.id.value,
            version_number=version.version_number.value,
            name=version.name,
            parameters=version.parameters,
            description=version.description,
            changelog=version.changelog,
            is_active=version.is_active,
            promoted_at=version.promoted_at,
        )
