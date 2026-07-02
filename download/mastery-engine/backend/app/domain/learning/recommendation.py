"""Recommendation — an advisory suggestion for a learner.

Recommendations are non-binding; the learner may accept, defer, or dismiss them.
They extend the Engine's "what next?" capability beyond the active session.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.shared.ids import LearnerEnrollmentId, RecommendationId
from app.domain.shared.kernel import (
    AggregateRoot,
    InvariantViolation,
    RecommendationStatus,
)
from app.domain.learning.events import RecommendationDismissed, RecommendationGenerated
from app.domain.learning.exceptions import RecommendationNotDismissable

# Dismissed recommendations don't reappear in identical form for 7 days
DISMISSAL_COOLDOWN = timedelta(days=7)


class Recommendation(AggregateRoot):
    """An advisory suggestion produced by the Scheduler or analytics jobs.

    Invariants:
    - Non-binding; the Engine never auto-acts on a recommendation.
    - Dismissible in one click.
    - A dismissed recommendation does not reappear in identical form for 7 days.
    - Terminal states (ACCEPTED, DISMISSED, EXPIRED) cannot transition.
    """

    def __init__(
        self,
        id: RecommendationId,
        learner_enrollment_id: LearnerEnrollmentId,
        recommendation_type: str,
        payload: dict[str, Any],
        score: float,
        status: RecommendationStatus = RecommendationStatus.PENDING,
        created_at: datetime | None = None,
        presented_at: datetime | None = None,
        acted_at: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        super().__init__()
        if not 0.0 <= score <= 1.0:
            raise InvariantViolation("Recommendation", f"score must be 0.0–1.0, got {score}")
        self.id = id
        self.learner_enrollment_id = learner_enrollment_id
        self.recommendation_type = recommendation_type
        self.payload = payload
        self.score = score
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)
        self.presented_at = presented_at
        self.acted_at = acted_at
        self.expires_at = expires_at

    @classmethod
    def generate(
        cls,
        learner_enrollment_id: LearnerEnrollmentId,
        recommendation_type: str,
        payload: dict[str, Any],
        score: float,
        expires_in_days: int = 7,
    ) -> Recommendation:
        """Generate a new recommendation."""
        rec = cls(
            id=RecommendationId.generate(),
            learner_enrollment_id=learner_enrollment_id,
            recommendation_type=recommendation_type,
            payload=payload,
            score=score,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        )
        rec._record_event(
            RecommendationGenerated(
                recommendation_id=rec.id.value,
                enrollment_id=learner_enrollment_id.value,
                recommendation_type=recommendation_type,
                score=score,
            )
        )
        return rec

    def present(self) -> None:
        """Mark as presented to the learner (shown on dashboard)."""
        if self.status != RecommendationStatus.PENDING:
            return
        self.status = RecommendationStatus.PRESENTED
        self.presented_at = datetime.now(timezone.utc)

    def accept(self) -> None:
        """Learner accepted the recommendation."""
        if self.status in (RecommendationStatus.ACCEPTED, RecommendationStatus.DISMISSED, RecommendationStatus.EXPIRED):
            return
        self.status = RecommendationStatus.ACCEPTED
        self.acted_at = datetime.now(timezone.utc)

    def defer(self) -> None:
        """Learner deferred the recommendation."""
        if self.status in (RecommendationStatus.ACCEPTED, RecommendationStatus.DISMISSED, RecommendationStatus.EXPIRED):
            return
        self.status = RecommendationStatus.PENDING  # back to pending for re-presentation
        self.presented_at = None

    def dismiss(self) -> None:
        """Learner dismissed the recommendation.

        Raises:
            RecommendationNotDismissable: if in a terminal state.
        """
        if self.status in (RecommendationStatus.ACCEPTED, RecommendationStatus.DISMISSED, RecommendationStatus.EXPIRED):
            raise RecommendationNotDismissable(self.id, self.status.value)
        self.status = RecommendationStatus.DISMISSED
        self.acted_at = datetime.now(timezone.utc)
        self._record_event(RecommendationDismissed(recommendation_id=self.id.value))

    def expire(self) -> None:
        """Expire the recommendation (expires_at passed)."""
        if self.status in (RecommendationStatus.ACCEPTED, RecommendationStatus.DISMISSED, RecommendationStatus.EXPIRED):
            return
        self.status = RecommendationStatus.EXPIRED

    @property
    def is_dismissed(self) -> bool:
        return self.status == RecommendationStatus.DISMISSED

    @property
    def is_actionable(self) -> bool:
        return self.status in (RecommendationStatus.PENDING, RecommendationStatus.PRESENTED)
