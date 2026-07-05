"""StudySession — a single sitting during which a learner practices.

The StudySession is the unit of engagement analytics: streaks, total time,
and questions-per-session are computed from it. It is also the unit of
focus for the learner (one session = one study episode).

State machine:
    ACTIVE → PAUSED → ACTIVE (resume)
    ACTIVE → ENDED (learner ends or goal complete)
    PAUSED → ENDED (timeout)
    ACTIVE/PAUSED → ABANDONED (24h inactivity)

Invariants:
    - A learner has at most one active session per subject at a time.
    - An attempt belongs to exactly one session.
    - A completed (ENDED/ABANDONED) session cannot receive new attempts.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain.shared.ids import (
    LearnerEnrollmentId,
    LearningSessionId,
    StudySessionId,
)
from app.domain.shared.kernel import (
    AggregateRoot,
    InvalidStateTransition,
    SessionIntent,
    SessionStatus,
)
from app.domain.learning.events import (
    StudySessionAbandoned,
    StudySessionEnded,
    StudySessionPaused,
    StudySessionResumed,
    StudySessionStarted,
)

# Sessions can be resumed within 24 hours
RESUMPTION_WINDOW = timedelta(hours=24)


class StudySession(AggregateRoot):
    """A single practice sitting.

    Invariants:
    - Cannot add attempts to a completed session (ENDED/ABANDONED).
    - Cannot resume a session past the 24h resumption window.
    - One active session per enrollment (enforced at application level).
    """

    def __init__(
        self,
        id: StudySessionId,
        learner_enrollment_id: LearnerEnrollmentId,
        learning_session_id: LearningSessionId | None = None,
        intent: SessionIntent = SessionIntent.MIXED,
        target_question_count: int | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        status: SessionStatus = SessionStatus.ACTIVE,
        question_count: int = 0,
    ) -> None:
        super().__init__()
        self.id = id
        self.learner_enrollment_id = learner_enrollment_id
        self.learning_session_id = learning_session_id
        self.intent = intent
        self.target_question_count = target_question_count
        self.started_at = started_at or datetime.now(timezone.utc)
        self.ended_at = ended_at
        self.status = status
        self.question_count = question_count

    @classmethod
    def start(
        cls,
        learner_enrollment_id: LearnerEnrollmentId,
        intent: SessionIntent = SessionIntent.MIXED,
        target_question_count: int | None = None,
    ) -> StudySession:
        """Start a new study session."""
        session = cls(
            id=StudySessionId.generate(),
            learner_enrollment_id=learner_enrollment_id,
            intent=intent,
            target_question_count=target_question_count,
        )
        session._record_event(
            StudySessionStarted(
                session_id=session.id.value,
                enrollment_id=learner_enrollment_id.value,
                intent=intent,
            )
        )
        return session

    def pause(self) -> None:
        """Pause the session."""
        if self.status != SessionStatus.ACTIVE:
            raise InvalidStateTransition("StudySession", self.status.value, "pause")
        self.status = SessionStatus.PAUSED
        self._record_event(StudySessionPaused(session_id=self.id.value))

    def resume(self) -> None:
        """Resume a paused session."""
        if self.status != SessionStatus.PAUSED:
            raise InvalidStateTransition("StudySession", self.status.value, "resume")
        if self._is_past_resumption_window():
            raise InvalidStateTransition(
                "StudySession", self.status.value, "resume (past 24h window)"
            )
        self.status = SessionStatus.ACTIVE
        self._record_event(StudySessionResumed(session_id=self.id.value))

    def end(self) -> None:
        """End the session (learner ends or goal complete)."""
        if self.status in (SessionStatus.ENDED, SessionStatus.ABANDONED):
            return  # idempotent
        if self.status not in (SessionStatus.ACTIVE, SessionStatus.PAUSED):
            raise InvalidStateTransition("StudySession", self.status.value, "end")
        self.status = SessionStatus.ENDED
        self.ended_at = datetime.now(timezone.utc)
        duration = int((self.ended_at - self.started_at).total_seconds())
        self._record_event(
            StudySessionEnded(
                session_id=self.id.value,
                question_count=self.question_count,
                duration_seconds=duration,
            )
        )

    def abandon(self) -> None:
        """Abandon the session (24h inactivity timeout)."""
        if self.status in (SessionStatus.ENDED, SessionStatus.ABANDONED):
            return
        self.status = SessionStatus.ABANDONED
        self.ended_at = datetime.now(timezone.utc)
        self._record_event(StudySessionAbandoned(session_id=self.id.value))

    def record_attempt(self) -> None:
        """Record that an attempt was made in this session."""
        if self.status not in (SessionStatus.ACTIVE,):
            raise InvalidStateTransition(
                "StudySession",
                self.status.value,
                "record_attempt (session not active)",
            )
        self.question_count += 1

    def _is_past_resumption_window(self) -> bool:
        """Check if the session is past the 24h resumption window."""
        return datetime.now(timezone.utc) > self.started_at + RESUMPTION_WINDOW

    @property
    def is_active(self) -> bool:
        return self.status == SessionStatus.ACTIVE

    @property
    def is_ended(self) -> bool:
        return self.status in (SessionStatus.ENDED, SessionStatus.ABANDONED)

    @property
    def duration_seconds(self) -> int:
        end = self.ended_at or datetime.now(timezone.utc)
        return int((end - self.started_at).total_seconds())
