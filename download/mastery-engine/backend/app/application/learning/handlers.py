"""Learning context — command handlers."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.application.shared import (
    CommandHandler,
    CommandResult,
    EventPublisher,
    ResourceMissing,
    UnitOfWork,
    ValidationFailed,
)
from app.application.learning.dto import (
    CompleteOnboardingCommand,
    DismissRecommendationCommand,
    EnrollLearnerCommand,
    EndStudySessionCommand,
    EnrollmentDTO,
    PauseStudySessionCommand,
    ResumeStudySessionCommand,
    SessionAnalyticsDTO,
    SetLearningGoalCommand,
    StartStudySessionCommand,
    StudySessionDTO,
    UnenrollCommand,
)
from app.domain.learning.enrollment import LearnerEnrollment
from app.domain.learning.recommendation import Recommendation
from app.domain.learning.study_session import StudySession
from app.domain.learning.learning_goal import LearningGoal
from app.domain.shared.ids import (
    LearnerEnrollmentId,
    SubjectId,
    UserId,
    LearningPathId,
    StudySessionId,
    RecommendationId,
)
from app.domain.shared.kernel import (
    EnrollmentStatus,
    GoalType,
    InvalidStateTransition,
    SessionIntent,
)
from app.domain.shared.ids import LearningGoalId


class EnrollLearnerHandler(CommandHandler[EnrollLearnerCommand, EnrollmentDTO]):
    """Handler for EnrollLearnerCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: EnrollLearnerCommand) -> CommandResult[EnrollmentDTO]:
        async with self._uow as uow:
            # Check for existing active enrollment
            existing = await uow.enrollments.get_by_user_and_subject(
                UserId(command.user_id), SubjectId(command.subject_id)
            )
            if existing is not None and existing.status != EnrollmentStatus.UNENROLLED:
                return CommandResult.fail("Already enrolled", "ALREADY_ENROLLED")

            # Create enrollment
            enrollment = LearnerEnrollment.enroll(
                user_id=UserId(command.user_id),
                subject_id=SubjectId(command.subject_id),
                learning_path_id=LearningPathId(command.learning_path_id) if command.learning_path_id else None,
            )

            await uow.enrollments.add(enrollment)
            events = enrollment.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(self._to_dto(enrollment), events)

    @staticmethod
    def _to_dto(enrollment: LearnerEnrollment) -> EnrollmentDTO:
        return EnrollmentDTO(
            id=enrollment.id.value,
            user_id=enrollment.user_id.value,
            subject_id=enrollment.subject_id.value,
            learning_path_id=enrollment.learning_path_id.value if enrollment.learning_path_id else None,
            status=enrollment.status.value,
            enrolled_at=enrollment.enrolled_at,
            onboarded_at=enrollment.onboarded_at,
            last_active_at=enrollment.last_active_at,
        )


class CompleteOnboardingHandler(CommandHandler[CompleteOnboardingCommand, EnrollmentDTO]):
    """Handler for CompleteOnboardingCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: CompleteOnboardingCommand) -> CommandResult[EnrollmentDTO]:
        async with self._uow as uow:
            enrollment = await uow.enrollments.get_by_id(
                LearnerEnrollmentId(command.enrollment_id)
            )
            if enrollment is None:
                return CommandResult.fail(
                    str(ResourceMissing("Enrollment", command.enrollment_id)),
                    "ENROLLMENT_NOT_FOUND",
                )

            try:
                enrollment.complete_onboarding()
            except InvalidStateTransition as exc:
                return CommandResult.fail(str(exc), "INVALID_STATE_TRANSITION")

            await uow.enrollments.save(enrollment)
            events = enrollment.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(
            EnrollLearnerHandler._to_dto(enrollment), events
        )


class StartStudySessionHandler(CommandHandler[StartStudySessionCommand, StudySessionDTO]):
    """Handler for StartStudySessionCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: StartStudySessionCommand) -> CommandResult[StudySessionDTO]:
        # Validate intent
        try:
            intent = SessionIntent(command.intent)
        except ValueError:
            return CommandResult.fail(f"Invalid intent: {command.intent}", "VALIDATION_FAILED")

        async with self._uow as uow:
            # Check for existing active session
            enrollment_id = LearnerEnrollmentId(command.enrollment_id)
            existing = await uow.study_sessions.get_active_by_enrollment(enrollment_id)
            if existing is not None:
                return CommandResult.fail("Active session already exists", "ACTIVE_SESSION_EXISTS")

            session = StudySession.start(
                learner_enrollment_id=enrollment_id,
                intent=intent,
                target_question_count=command.target_question_count,
            )

            await uow.study_sessions.add(session)
            events = session.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(self._to_dto(session), events)

    @staticmethod
    def _to_dto(session: StudySession) -> StudySessionDTO:
        return StudySessionDTO(
            id=session.id.value,
            learner_enrollment_id=session.learner_enrollment_id.value,
            intent=session.intent.value,
            status=session.status.value,
            started_at=session.started_at,
            ended_at=session.ended_at,
            question_count=session.question_count,
        )


class EndStudySessionHandler(CommandHandler[EndStudySessionCommand, SessionAnalyticsDTO]):
    """Handler for EndStudySessionCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: EndStudySessionCommand) -> CommandResult[SessionAnalyticsDTO]:
        async with self._uow as uow:
            session = await uow.study_sessions.get_by_id(
                StudySessionId(command.session_id)
            )
            if session is None:
                return CommandResult.fail(
                    str(ResourceMissing("StudySession", command.session_id)),
                    "SESSION_NOT_FOUND",
                )

            try:
                session.end()
            except InvalidStateTransition as exc:
                return CommandResult.fail(str(exc), "INVALID_STATE_TRANSITION")

            await uow.study_sessions.save(session)
            events = session.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(
            SessionAnalyticsDTO(
                study_session_id=session.id.value,
                question_count=session.question_count,
                duration_seconds=session.duration_seconds,
            ),
            events,
        )


class PauseStudySessionHandler(CommandHandler[PauseStudySessionCommand, StudySessionDTO]):
    """Handler for PauseStudySessionCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: PauseStudySessionCommand) -> CommandResult[StudySessionDTO]:
        async with self._uow as uow:
            session = await uow.study_sessions.get_by_id(
                StudySessionId(command.session_id)
            )
            if session is None:
                return CommandResult.fail(
                    str(ResourceMissing("StudySession", command.session_id)),
                    "SESSION_NOT_FOUND",
                )

            try:
                session.pause()
            except InvalidStateTransition as exc:
                return CommandResult.fail(str(exc), "INVALID_STATE_TRANSITION")

            await uow.study_sessions.save(session)
            events = session.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(StartStudySessionHandler._to_dto(session), events)


class ResumeStudySessionHandler(CommandHandler[ResumeStudySessionCommand, StudySessionDTO]):
    """Handler for ResumeStudySessionCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: ResumeStudySessionCommand) -> CommandResult[StudySessionDTO]:
        async with self._uow as uow:
            session = await uow.study_sessions.get_by_id(
                StudySessionId(command.session_id)
            )
            if session is None:
                return CommandResult.fail(
                    str(ResourceMissing("StudySession", command.session_id)),
                    "SESSION_NOT_FOUND",
                )

            try:
                session.resume()
            except InvalidStateTransition as exc:
                return CommandResult.fail(str(exc), "INVALID_STATE_TRANSITION")

            await uow.study_sessions.save(session)
            events = session.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(StartStudySessionHandler._to_dto(session), events)


class DismissRecommendationHandler(CommandHandler[DismissRecommendationCommand, None]):
    """Handler for DismissRecommendationCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: DismissRecommendationCommand) -> CommandResult[None]:
        async with self._uow as uow:
            rec = await uow.recommendations.get_by_id(
                RecommendationId(command.recommendation_id)
            )
            if rec is None:
                return CommandResult.fail(
                    str(ResourceMissing("Recommendation", command.recommendation_id)),
                    "RECOMMENDATION_NOT_FOUND",
                )

            try:
                rec.dismiss()
            except Exception as exc:
                return CommandResult.fail(str(exc), "RECOMMENDATION_NOT_DISMISSABLE")

            await uow.recommendations.save(rec)
            events = rec.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(None, events)
