"""Tests for the Recommendation aggregate (Learning context)."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from app.domain.learning.recommendation import Recommendation
from app.domain.learning.events import (
    RecommendationDismissed,
    RecommendationGenerated,
)
from app.domain.learning.exceptions import RecommendationNotDismissable
from app.domain.shared.ids import LearnerEnrollmentId
from app.domain.shared.kernel import (
    InvariantViolation,
    RecommendationStatus,
)


class TestRecommendationGenerate:
    """Tests for Recommendation.generate()."""

    def test_generate_creates_pending_recommendation(self) -> None:
        enrollment_id = LearnerEnrollmentId.generate()
        rec = Recommendation.generate(
            learner_enrollment_id=enrollment_id,
            recommendation_type="review_due",
            payload={"concept_ids": ["abc"]},
            score=0.85,
        )

        assert rec.status == RecommendationStatus.PENDING
        assert rec.score == 0.85
        assert rec.expires_at is not None

    def test_generate_records_event(self) -> None:
        enrollment_id = LearnerEnrollmentId.generate()
        rec = Recommendation.generate(
            learner_enrollment_id=enrollment_id,
            recommendation_type="weak_concept",
            payload={},
            score=0.6,
        )

        events = rec.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], RecommendationGenerated)

    def test_invalid_score_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            Recommendation.generate(
                learner_enrollment_id=LearnerEnrollmentId.generate(),
                recommendation_type="test",
                payload={},
                score=1.5,
            )


class TestRecommendationLifecycle:
    """Tests for recommendation state transitions."""

    def test_present_transitions_to_presented(self) -> None:
        rec = self._make_rec()
        rec.present()
        assert rec.status == RecommendationStatus.PRESENTED

    def test_accept_transitions_to_accepted(self) -> None:
        rec = self._make_rec()
        rec.present()
        rec.accept()
        assert rec.status == RecommendationStatus.ACCEPTED

    def test_defer_returns_to_pending(self) -> None:
        rec = self._make_rec()
        rec.present()
        rec.defer()
        assert rec.status == RecommendationStatus.PENDING

    def test_dismiss_transitions_to_dismissed(self) -> None:
        rec = self._make_rec()
        rec.collect_events()

        rec.dismiss()

        assert rec.status == RecommendationStatus.DISMISSED
        events = rec.collect_events()
        assert any(isinstance(e, RecommendationDismissed) for e in events)

    def test_dismiss_accepted_raises(self) -> None:
        rec = self._make_rec()
        rec.present()
        rec.accept()

        with pytest.raises(RecommendationNotDismissable):
            rec.dismiss()

    def test_dismiss_already_dismissed_raises(self) -> None:
        rec = self._make_rec()
        rec.dismiss()

        with pytest.raises(RecommendationNotDismissable):
            rec.dismiss()

    def test_expire_transitions_to_expired(self) -> None:
        rec = self._make_rec()
        rec.expire()
        assert rec.status == RecommendationStatus.EXPIRED

    def test_terminal_states_cannot_accept(self) -> None:
        rec = self._make_rec()
        rec.dismiss()
        rec.accept()  # should be no-op (already terminal)
        assert rec.status == RecommendationStatus.DISMISSED

    def test_is_actionable(self) -> None:
        rec = self._make_rec()
        assert rec.is_actionable  # PENDING is actionable

        rec.present()
        assert rec.is_actionable  # PRESENTED is actionable

        rec.accept()
        assert not rec.is_actionable  # ACCEPTED is not actionable

    @staticmethod
    def _make_rec() -> Recommendation:
        return Recommendation.generate(
            learner_enrollment_id=LearnerEnrollmentId.generate(),
            recommendation_type="test",
            payload={},
            score=0.7,
        )
