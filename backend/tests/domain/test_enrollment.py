"""Tests for the LearnerEnrollment aggregate (Learning context)."""

from __future__ import annotations

import pytest

from app.domain.learning.enrollment import LearnerEnrollment
from app.domain.learning.events import (
    LearnerEnrolled,
    LearnerUnenrolled,
    OnboardingCompleted,
)
from app.domain.shared.ids import LearnerEnrollmentId, SubjectId, UserId
from app.domain.shared.kernel import (
    EnrollmentStatus,
    InvalidStateTransition,
)


class TestEnrollment:
    """Tests for the LearnerEnrollment aggregate."""

    def test_enroll_creates_pending_onboarding(self) -> None:
        user_id = UserId.generate()
        subject_id = SubjectId.generate()
        enrollment = LearnerEnrollment.enroll(user_id, subject_id)

        assert enrollment.status == EnrollmentStatus.PENDING_ONBOARDING
        assert enrollment.user_id == user_id
        assert enrollment.subject_id == subject_id
        assert enrollment.enrolled_at is not None

    def test_enroll_records_event(self) -> None:
        enrollment = LearnerEnrollment.enroll(UserId.generate(), SubjectId.generate())

        events = enrollment.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], LearnerEnrolled)

    def test_complete_onboarding_transitions_to_active(self) -> None:
        enrollment = LearnerEnrollment.enroll(UserId.generate(), SubjectId.generate())
        enrollment.collect_events()

        enrollment.complete_onboarding()

        assert enrollment.status == EnrollmentStatus.ACTIVE
        assert enrollment.onboarded_at is not None
        events = enrollment.collect_events()
        assert any(isinstance(e, OnboardingCompleted) for e in events)

    def test_complete_onboarding_on_active_raises(self) -> None:
        enrollment = LearnerEnrollment.enroll(UserId.generate(), SubjectId.generate())
        enrollment.complete_onboarding()

        with pytest.raises(InvalidStateTransition):
            enrollment.complete_onboarding()

    def test_mark_dormant(self) -> None:
        enrollment = LearnerEnrollment.enroll(UserId.generate(), SubjectId.generate())
        enrollment.complete_onboarding()

        enrollment.mark_dormant()

        assert enrollment.status == EnrollmentStatus.DORMANT

    def test_mark_dormant_on_non_active_is_noop(self) -> None:
        enrollment = LearnerEnrollment.enroll(UserId.generate(), SubjectId.generate())
        enrollment.mark_dormant()
        assert enrollment.status == EnrollmentStatus.PENDING_ONBOARDING

    def test_reactivate(self) -> None:
        enrollment = LearnerEnrollment.enroll(UserId.generate(), SubjectId.generate())
        enrollment.complete_onboarding()
        enrollment.mark_dormant()

        enrollment.reactivate()

        assert enrollment.status == EnrollmentStatus.ACTIVE
        assert enrollment.last_active_at is not None

    def test_reactivate_on_active_is_noop(self) -> None:
        enrollment = LearnerEnrollment.enroll(UserId.generate(), SubjectId.generate())
        enrollment.complete_onboarding()

        enrollment.reactivate()

        assert enrollment.status == EnrollmentStatus.ACTIVE

    def test_unenroll(self) -> None:
        enrollment = LearnerEnrollment.enroll(UserId.generate(), SubjectId.generate())
        enrollment.complete_onboarding()
        enrollment.collect_events()

        enrollment.unenroll()

        assert enrollment.status == EnrollmentStatus.UNENROLLED
        assert enrollment.unenrolled_at is not None
        events = enrollment.collect_events()
        assert any(isinstance(e, LearnerUnenrolled) for e in events)

    def test_unenroll_already_unenrolled_is_idempotent(self) -> None:
        enrollment = LearnerEnrollment.enroll(UserId.generate(), SubjectId.generate())
        enrollment.unenroll()
        enrollment.unenroll()  # should not raise
        assert enrollment.status == EnrollmentStatus.UNENROLLED

    def test_touch_updates_last_active_at(self) -> None:
        enrollment = LearnerEnrollment.enroll(UserId.generate(), SubjectId.generate())
        enrollment.complete_onboarding()
        enrollment.mark_dormant()

        enrollment.touch()

        assert enrollment.last_active_at is not None
        assert enrollment.status == EnrollmentStatus.ACTIVE  # reactivated by touch

    def test_is_active_property(self) -> None:
        enrollment = LearnerEnrollment.enroll(UserId.generate(), SubjectId.generate())
        assert not enrollment.is_active

        enrollment.complete_onboarding()
        assert enrollment.is_active

    def test_is_pending_onboarding_property(self) -> None:
        enrollment = LearnerEnrollment.enroll(UserId.generate(), SubjectId.generate())
        assert enrollment.is_pending_onboarding

        enrollment.complete_onboarding()
        assert not enrollment.is_pending_onboarding
