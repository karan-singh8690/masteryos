"""Tests for the StudySession aggregate (Learning context)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.domain.learning.study_session import StudySession, RESUMPTION_WINDOW
from app.domain.learning.events import (
    StudySessionEnded,
    StudySessionPaused,
    StudySessionResumed,
    StudySessionStarted,
)
from app.domain.shared.ids import LearnerEnrollmentId
from app.domain.shared.kernel import (
    InvalidStateTransition,
    SessionIntent,
    SessionStatus,
)


class TestStudySessionStart:
    """Tests for StudySession.start()."""

    def test_start_creates_active_session(self) -> None:
        enrollment_id = LearnerEnrollmentId.generate()
        session = StudySession.start(enrollment_id, intent=SessionIntent.DRILL)

        assert session.status == SessionStatus.ACTIVE
        assert session.intent == SessionIntent.DRILL
        assert session.question_count == 0
        assert session.started_at is not None

    def test_start_records_event(self) -> None:
        enrollment_id = LearnerEnrollmentId.generate()
        session = StudySession.start(enrollment_id)

        events = session.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], StudySessionStarted)

    def test_start_with_target_question_count(self) -> None:
        enrollment_id = LearnerEnrollmentId.generate()
        session = StudySession.start(enrollment_id, target_question_count=20)

        assert session.target_question_count == 20


class TestStudySessionPause:
    """Tests for pause() and resume()."""

    def test_pause_active_session(self) -> None:
        session = self._make_session()
        session.collect_events()

        session.pause()

        assert session.status == SessionStatus.PAUSED
        events = session.collect_events()
        assert any(isinstance(e, StudySessionPaused) for e in events)

    def test_pause_already_paused_raises(self) -> None:
        session = self._make_session()
        session.pause()

        with pytest.raises(InvalidStateTransition):
            session.pause()

    def test_resume_paused_session(self) -> None:
        session = self._make_session()
        session.pause()
        session.collect_events()

        session.resume()

        assert session.status == SessionStatus.ACTIVE
        events = session.collect_events()
        assert any(isinstance(e, StudySessionResumed) for e in events)

    def test_resume_active_raises(self) -> None:
        session = self._make_session()

        with pytest.raises(InvalidStateTransition):
            session.resume()

    @staticmethod
    def _make_session() -> StudySession:
        return StudySession.start(LearnerEnrollmentId.generate())


class TestStudySessionEnd:
    """Tests for end() and abandon()."""

    def test_end_active_session(self) -> None:
        session = self._make_session()
        session.record_attempt()
        session.collect_events()

        session.end()

        assert session.status == SessionStatus.ENDED
        assert session.ended_at is not None
        events = session.collect_events()
        assert any(isinstance(e, StudySessionEnded) for e in events)

    def test_end_paused_session(self) -> None:
        session = self._make_session()
        session.pause()

        session.end()

        assert session.status == SessionStatus.ENDED

    def test_end_already_ended_is_idempotent(self) -> None:
        session = self._make_session()
        session.end()

        # Second end should not raise
        session.end()
        assert session.status == SessionStatus.ENDED

    def test_abandon_session(self) -> None:
        session = self._make_session()

        session.abandon()

        assert session.status == SessionStatus.ABANDONED

    def test_abandon_ended_is_idempotent(self) -> None:
        session = self._make_session()
        session.end()

        session.abandon()
        assert session.status == SessionStatus.ENDED  # stays ended

    @staticmethod
    def _make_session() -> StudySession:
        return StudySession.start(LearnerEnrollmentId.generate())


class TestStudySessionAttemptRecording:
    """Tests for record_attempt()."""

    def test_record_attempt_increments_count(self) -> None:
        session = self._make_session()
        assert session.question_count == 0

        session.record_attempt()
        assert session.question_count == 1

        session.record_attempt()
        assert session.question_count == 2

    def test_record_attempt_on_ended_session_raises(self) -> None:
        session = self._make_session()
        session.end()

        with pytest.raises(InvalidStateTransition):
            session.record_attempt()

    def test_record_attempt_on_paused_session_raises(self) -> None:
        session = self._make_session()
        session.pause()

        with pytest.raises(InvalidStateTransition):
            session.record_attempt()

    @staticmethod
    def _make_session() -> StudySession:
        return StudySession.start(LearnerEnrollmentId.generate())


class TestStudySessionDuration:
    """Tests for duration calculation."""

    def test_duration_seconds_for_active_session(self) -> None:
        session = StudySession.start(LearnerEnrollmentId.generate())
        # Session just started; duration should be very small
        assert session.duration_seconds >= 0

    def test_duration_seconds_for_ended_session(self) -> None:
        session = StudySession(
            id=session.id if hasattr(session, 'id') else None,
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            started_at=datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 7, 2, 12, 30, tzinfo=timezone.utc),
            status=SessionStatus.ENDED,
        )
        assert session.duration_seconds == 1800  # 30 minutes
