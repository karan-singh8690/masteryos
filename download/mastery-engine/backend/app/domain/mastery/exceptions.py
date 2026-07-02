"""Mastery context — exceptions."""

from __future__ import annotations

from app.domain.shared.kernel import DomainError


class MasteryError(DomainError):
    """Base for all mastery domain errors."""


class AlgorithmVersionNotActive(MasteryError):
    def __init__(self, version_id: object) -> None:
        super().__init__(
            f"Algorithm version {version_id} is not active",
            code="ALGORITHM_VERSION_NOT_ACTIVE",
        )


class OptimisticConcurrencyConflict(MasteryError):
    def __init__(self, aggregate: str, expected_version: int) -> None:
        super().__init__(
            f"Optimistic concurrency conflict on {aggregate}: expected version {expected_version}",
            code="OPTIMISTIC_CONCURRENCY_CONFLICT",
        )


class MasteryScoreNotFound(MasteryError):
    def __init__(self, enrollment_id: object, concept_id: object) -> None:
        super().__init__(
            f"Mastery score not found for enrollment {enrollment_id}, concept {concept_id}",
            code="MASTERY_SCORE_NOT_FOUND",
        )


class ReviewNotFound(MasteryError):
    def __init__(self, review_id: object) -> None:
        super().__init__(f"Review {review_id} not found", code="REVIEW_NOT_FOUND")


class AlgorithmVersionNotFound(MasteryError):
    def __init__(self, version_id: object) -> None:
        super().__init__(
            f"Algorithm version {version_id} not found",
            code="ALGORITHM_VERSION_NOT_FOUND",
        )


class AlgorithmVersionAlreadyActive(MasteryError):
    def __init__(self, version_id: object) -> None:
        super().__init__(
            f"Algorithm version {version_id} is already active",
            code="ALGORITHM_VERSION_ALREADY_ACTIVE",
        )


class AlgorithmEvaluationFailed(MasteryError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            f"Algorithm evaluation failed: {reason}",
            code="ALGORITHM_EVALUATION_FAILED",
        )
