"""Review — a scheduled future encounter with a concept.

A Review is produced by the Mastery Engine after every attempt (via the
ScheduleReview command). It records when the concept should next be
reviewed (due_at) and the priority of that review.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain.shared.ids import (
    AlgorithmVersionId,
    ConceptId,
    LearnerEnrollmentId,
    ReviewId,
)
from app.domain.shared.kernel import (
    AggregateRoot,
    InvariantViolation,
    ReviewPriority,
    ScoringOutcome,
)
from app.domain.shared.value_objects import ReviewInterval
from app.domain.mastery.events import ReviewScheduled


class Review(AggregateRoot):
    """A scheduled review of a concept for a learner.

    Invariants:
    - One review per (learner_enrollment_id, concept_id).
    - ``due_at`` is always in the future relative to creation.
    - ``review_interval`` is bounded by ReviewInterval.MIN_DAYS and MAX_DAYS.
    """

    def __init__(
        self,
        id: ReviewId,
        learner_enrollment_id: LearnerEnrollmentId,
        concept_id: ConceptId,
        algorithm_version_id: AlgorithmVersionId,
        due_at: datetime,
        priority: ReviewPriority,
        review_interval: ReviewInterval,
        last_reviewed_at: datetime | None = None,
        last_review_outcome: ScoringOutcome | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.learner_enrollment_id = learner_enrollment_id
        self.concept_id = concept_id
        self.algorithm_version_id = algorithm_version_id
        self.due_at = due_at
        self.priority = priority
        self.review_interval = review_interval
        self.last_reviewed_at = last_reviewed_at
        self.last_review_outcome = last_review_outcome
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    @classmethod
    def schedule(
        cls,
        learner_enrollment_id: LearnerEnrollmentId,
        concept_id: ConceptId,
        algorithm_version_id: AlgorithmVersionId,
        interval: ReviewInterval,
        priority: ReviewPriority = ReviewPriority.MEDIUM,
    ) -> Review:
        """Schedule a new review for a concept."""
        now = datetime.now(timezone.utc)
        due_at = now + interval.to_timedelta()
        review = cls(
            id=ReviewId.generate(),
            learner_enrollment_id=learner_enrollment_id,
            concept_id=concept_id,
            algorithm_version_id=algorithm_version_id,
            due_at=due_at,
            priority=priority,
            review_interval=interval,
        )
        review._record_event(
            ReviewScheduled(
                review_id=review.id.value,
                learner_enrollment_id=learner_enrollment_id.value,
                concept_id=concept_id.value,
                due_at=due_at,
                priority=priority,
                interval_days=interval.days,
            )
        )
        return review

    def reschedule(
        self,
        new_interval: ReviewInterval,
        priority: ReviewPriority | None = None,
        review_outcome: ScoringOutcome | None = None,
    ) -> None:
        """Reschedule this review with a new interval (after a review attempt)."""
        now = datetime.now(timezone.utc)
        self.due_at = now + new_interval.to_timedelta()
        self.review_interval = new_interval
        self.last_reviewed_at = now
        self.last_review_outcome = review_outcome
        self.updated_at = now
        if priority is not None:
            self.priority = priority
        self._record_event(
            ReviewScheduled(
                review_id=self.id.value,
                learner_enrollment_id=self.learner_enrollment_id.value,
                concept_id=self.concept_id.value,
                due_at=self.due_at,
                priority=self.priority,
                interval_days=new_interval.days,
            )
        )

    @property
    def is_due(self) -> bool:
        """True if this review's due date has passed."""
        return datetime.now(timezone.utc) >= self.due_at

    @property
    def is_overdue(self) -> bool:
        """True if this review is more than 1 day overdue."""
        return datetime.now(timezone.utc) > self.due_at + timedelta(days=1)
