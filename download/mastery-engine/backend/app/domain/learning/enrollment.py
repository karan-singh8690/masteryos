"""LearnerEnrollment — the Learner role (a User enrolled in a Subject).

Per Task 002: a Learner is the role a User adopts when enrolled in a Subject.
The LearnerEnrollment is the unit of learning measurement: every Attempt,
MasteryScore, and StudySession belongs to a LearnerEnrollment, not to the
User in the abstract.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.shared.ids import (
    LearnerEnrollmentId,
    LearningPathId,
    SubjectId,
    UserId,
)
from app.domain.shared.kernel import (
    AggregateRoot,
    EnrollmentStatus,
    InvalidStateTransition,
)
from app.domain.learning.events import LearnerEnrolled, LearnerUnenrolled, OnboardingCompleted


class LearnerEnrollment(AggregateRoot):
    """A user's enrollment as a learner in a subject.

    State machine:
        PENDING_ONBOARDING → ACTIVE → (DORMANT ↔ ACTIVE) → UNENROLLED → ANONYMIZED

    Invariants:
    - A learner exists in exactly one subject.
    - A user may be a learner in N subjects, each with independent state.
    - Enrollment transitions are one-way (no re-enrollment after unenroll
      without creating a new enrollment).
    """

    def __init__(
        self,
        id: LearnerEnrollmentId,
        user_id: UserId,
        subject_id: SubjectId,
        learning_path_id: LearningPathId | None = None,
        status: EnrollmentStatus = EnrollmentStatus.PENDING_ONBOARDING,
        enrolled_at: datetime | None = None,
        onboarded_at: datetime | None = None,
        last_active_at: datetime | None = None,
        unenrolled_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.user_id = user_id
        self.subject_id = subject_id
        self.learning_path_id = learning_path_id
        self.status = status
        self.enrolled_at = enrolled_at or datetime.now(timezone.utc)
        self.onboarded_at = onboarded_at
        self.last_active_at = last_active_at
        self.unenrolled_at = unenrolled_at

    @classmethod
    def enroll(
        cls,
        user_id: UserId,
        subject_id: SubjectId,
        learning_path_id: LearningPathId | None = None,
    ) -> LearnerEnrollment:
        """Enroll a user as a learner in a subject."""
        enrollment = cls(
            id=LearnerEnrollmentId.generate(),
            user_id=user_id,
            subject_id=subject_id,
            learning_path_id=learning_path_id,
            status=EnrollmentStatus.PENDING_ONBOARDING,
        )
        enrollment._record_event(
            LearnerEnrolled(
                enrollment_id=enrollment.id.value,
                user_id=user_id.value,
                subject_id=subject_id.value,
            )
        )
        return enrollment

    def complete_onboarding(self) -> None:
        """Complete onboarding (after diagnostic). Transitions to ACTIVE."""
        if self.status != EnrollmentStatus.PENDING_ONBOARDING:
            raise InvalidStateTransition(
                "LearnerEnrollment", self.status.value, "complete_onboarding"
            )
        self.status = EnrollmentStatus.ACTIVE
        self.onboarded_at = datetime.now(timezone.utc)
        self._record_event(OnboardingCompleted(enrollment_id=self.id.value))

    def mark_dormant(self) -> None:
        """Mark as dormant (30 days of inactivity)."""
        if self.status != EnrollmentStatus.ACTIVE:
            return
        self.status = EnrollmentStatus.DORMANT

    def reactivate(self) -> None:
        """Reactivate a dormant enrollment (on next session)."""
        if self.status != EnrollmentStatus.DORMANT:
            return
        self.status = EnrollmentStatus.ACTIVE
        self.last_active_at = datetime.now(timezone.utc)

    def unenroll(self) -> None:
        """Unenroll from the subject."""
        if self.status == EnrollmentStatus.UNENROLLED:
            return
        if self.status == EnrollmentStatus.ANONYMIZED:
            raise InvalidStateTransition(
                "LearnerEnrollment", self.status.value, "unenroll"
            )
        self.status = EnrollmentStatus.UNENROLLED
        self.unenrolled_at = datetime.now(timezone.utc)
        self._record_event(LearnerUnenrolled(enrollment_id=self.id.value))

    def touch(self) -> None:
        """Update last_active_at (called on each study session)."""
        self.last_active_at = datetime.now(timezone.utc)
        if self.status == EnrollmentStatus.DORMANT:
            self.reactivate()

    @property
    def is_active(self) -> bool:
        return self.status == EnrollmentStatus.ACTIVE

    @property
    def is_pending_onboarding(self) -> bool:
        return self.status == EnrollmentStatus.PENDING_ONBOARDING

    @property
    def is_unenrolled(self) -> bool:
        return self.status == EnrollmentStatus.UNENROLLED
