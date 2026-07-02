"""Tests for the Learning context command handlers."""

from __future__ import annotations

import pytest
from uuid import uuid4

from app.application.identity.dto import RegisterUserCommand
from app.application.identity.handlers import RegisterUserHandler
from app.application.learning.dto import (
    EnrollLearnerCommand,
    StartStudySessionCommand,
    EndStudySessionCommand,
    PauseStudySessionCommand,
    ResumeStudySessionCommand,
)
from app.application.learning.handlers import (
    EnrollLearnerHandler,
    StartStudySessionHandler,
    EndStudySessionHandler,
    PauseStudySessionHandler,
    ResumeStudySessionHandler,
)
from app.domain.learning.events import (
    LearnerEnrolled,
    StudySessionEnded,
    StudySessionPaused,
    StudySessionResumed,
    StudySessionStarted,
)
from tests.application.fakes import FakeUnitOfWork, FakeEventPublisher


class TestEnrollLearnerHandler:
    """Tests for EnrollLearnerHandler."""

    @pytest.mark.asyncio
    async def test_enroll_success(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()
        handler = EnrollLearnerHandler(uow, publisher)

        user_id = uuid4()
        subject_id = uuid4()
        command = EnrollLearnerCommand(user_id=user_id, subject_id=subject_id)

        result = await handler.handle(command)

        assert result.success
        assert result.value is not None
        assert result.value.user_id == user_id
        assert result.value.subject_id == subject_id
        assert result.value.status == "pending_onboarding"
        assert any(isinstance(e, LearnerEnrolled) for e in publisher.published_events)

    @pytest.mark.asyncio
    async def test_enroll_duplicate_rejected(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()
        handler = EnrollLearnerHandler(uow, publisher)

        user_id = uuid4()
        subject_id = uuid4()
        command = EnrollLearnerCommand(user_id=user_id, subject_id=subject_id)

        # First enrollment
        await handler.handle(command)

        # Second enrollment (same user + subject)
        result = await handler.handle(command)

        assert not result.success
        assert result.error_code == "ALREADY_ENROLLED"


class TestStartStudySessionHandler:
    """Tests for StartStudySessionHandler."""

    @pytest.mark.asyncio
    async def test_start_session_success(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        # Create enrollment first
        enroll_handler = EnrollLearnerHandler(uow, publisher)
        enroll_result = await enroll_handler.handle(
            EnrollLearnerCommand(user_id=uuid4(), subject_id=uuid4())
        )
        enrollment_id = enroll_result.value.id
        publisher.reset()

        # Start session
        handler = StartStudySessionHandler(uow, publisher)
        result = await handler.handle(
            StartStudySessionCommand(
                enrollment_id=enrollment_id,
                intent="drill",
                target_question_count=15,
            )
        )

        assert result.success
        assert result.value.status == "active"
        assert result.value.intent == "drill"
        assert any(isinstance(e, StudySessionStarted) for e in publisher.published_events)

    @pytest.mark.asyncio
    async def test_start_session_duplicate_rejected(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        # Create enrollment
        enroll_handler = EnrollLearnerHandler(uow, publisher)
        enroll_result = await enroll_handler.handle(
            EnrollLearnerCommand(user_id=uuid4(), subject_id=uuid4())
        )
        enrollment_id = enroll_result.value.id

        # Start first session
        handler = StartStudySessionHandler(uow, publisher)
        await handler.handle(
            StartStudySessionCommand(enrollment_id=enrollment_id)
        )

        # Try to start second session
        result = await handler.handle(
            StartStudySessionCommand(enrollment_id=enrollment_id)
        )

        assert not result.success
        assert result.error_code == "ACTIVE_SESSION_EXISTS"

    @pytest.mark.asyncio
    async def test_start_session_invalid_intent(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        enroll_handler = EnrollLearnerHandler(uow, publisher)
        enroll_result = await enroll_handler.handle(
            EnrollLearnerCommand(user_id=uuid4(), subject_id=uuid4())
        )
        enrollment_id = enroll_result.value.id

        handler = StartStudySessionHandler(uow, publisher)
        result = await handler.handle(
            StartStudySessionCommand(enrollment_id=enrollment_id, intent="invalid")
        )

        assert not result.success
        assert result.error_code == "VALIDATION_FAILED"


class TestEndStudySessionHandler:
    """Tests for EndStudySessionHandler."""

    @pytest.mark.asyncio
    async def test_end_session_success(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        # Setup: enroll + start session
        enroll_handler = EnrollLearnerHandler(uow, publisher)
        enroll_result = await enroll_handler.handle(
            EnrollLearnerCommand(user_id=uuid4(), subject_id=uuid4())
        )
        enrollment_id = enroll_result.value.id

        start_handler = StartStudySessionHandler(uow, publisher)
        start_result = await start_handler.handle(
            StartStudySessionCommand(enrollment_id=enrollment_id)
        )
        session_id = start_result.value.id
        publisher.reset()

        # End session
        handler = EndStudySessionHandler(uow, publisher)
        result = await handler.handle(EndStudySessionCommand(session_id=session_id))

        assert result.success
        assert result.value.question_count == 0
        assert any(isinstance(e, StudySessionEnded) for e in publisher.published_events)

    @pytest.mark.asyncio
    async def test_end_nonexistent_session(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()
        handler = EndStudySessionHandler(uow, publisher)

        result = await handler.handle(EndStudySessionCommand(session_id=uuid4()))

        assert not result.success
        assert result.error_code == "SESSION_NOT_FOUND"


class TestPauseResumeStudySession:
    """Tests for PauseStudySessionHandler and ResumeStudySessionHandler."""

    @pytest.mark.asyncio
    async def test_pause_and_resume(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        # Setup: enroll + start session
        enroll_handler = EnrollLearnerHandler(uow, publisher)
        enroll_result = await enroll_handler.handle(
            EnrollLearnerCommand(user_id=uuid4(), subject_id=uuid4())
        )
        enrollment_id = enroll_result.value.id

        start_handler = StartStudySessionHandler(uow, publisher)
        start_result = await start_handler.handle(
            StartStudySessionCommand(enrollment_id=enrollment_id)
        )
        session_id = start_result.value.id

        # Pause
        publisher.reset()
        pause_handler = PauseStudySessionHandler(uow, publisher)
        result = await pause_handler.handle(PauseStudySessionCommand(session_id=session_id))

        assert result.success
        assert result.value.status == "paused"
        assert any(isinstance(e, StudySessionPaused) for e in publisher.published_events)

        # Resume
        publisher.reset()
        resume_handler = ResumeStudySessionHandler(uow, publisher)
        result = await resume_handler.handle(ResumeStudySessionCommand(session_id=session_id))

        assert result.success
        assert result.value.status == "active"
        assert any(isinstance(e, StudySessionResumed) for e in publisher.published_events)
