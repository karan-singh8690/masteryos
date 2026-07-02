"""Mastery context — abstract repository interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.domain.mastery.algorithm_version import AlgorithmVersion
from app.domain.mastery.mastery_score import MasteryScore
from app.domain.mastery.review import Review
from app.domain.shared.ids import (
    AlgorithmVersionId,
    ConceptId,
    LearnerEnrollmentId,
    MasteryScoreId,
    ReviewId,
)


class MasteryScoreRepository(ABC):
    """Abstract repository for MasteryScore aggregates.

    Single-writer: only the Mastery Engine (via UpdateMastery command)
    writes MasteryScores. No other context may modify them (M3 invariant).
    """

    @abstractmethod
    async def get_by_id(self, id: MasteryScoreId) -> MasteryScore | None:
        ...

    @abstractmethod
    async def get_by_enrollment_and_concept(
        self, learner_enrollment_id: LearnerEnrollmentId, concept_id: ConceptId
    ) -> MasteryScore | None:
        ...

    @abstractmethod
    async def list_by_enrollment(
        self, learner_enrollment_id: LearnerEnrollmentId
    ) -> Sequence[MasteryScore]:
        ...

    @abstractmethod
    async def list_weak_by_enrollment(
        self, learner_enrollment_id: LearnerEnrollmentId
    ) -> Sequence[MasteryScore]:
        ...

    @abstractmethod
    async def add(self, score: MasteryScore) -> MasteryScore:
        ...

    @abstractmethod
    async def save(self, score: MasteryScore) -> None:
        """Save with optimistic concurrency (checks ``version`` field)."""

    @abstractmethod
    async def count_by_algorithm_version(
        self, algorithm_version_id: AlgorithmVersionId
    ) -> int:
        """Count scores computed under a given algorithm version (for recompute job)."""


class ReviewRepository(ABC):
    """Abstract repository for Review aggregates."""

    @abstractmethod
    async def get_by_id(self, id: ReviewId) -> Review | None:
        ...

    @abstractmethod
    async def get_by_enrollment_and_concept(
        self, learner_enrollment_id: LearnerEnrollmentId, concept_id: ConceptId
    ) -> Review | None:
        ...

    @abstractmethod
    async def list_due_by_enrollment(
        self, learner_enrollment_id: LearnerEnrollmentId
    ) -> Sequence[Review]:
        ...

    @abstractmethod
    async def add(self, review: Review) -> Review:
        ...

    @abstractmethod
    async def save(self, review: Review) -> None:
        ...


class AlgorithmVersionRepository(ABC):
    """Abstract repository for AlgorithmVersion aggregates."""

    @abstractmethod
    async def get_by_id(self, id: AlgorithmVersionId) -> AlgorithmVersion | None:
        ...

    @abstractmethod
    async def get_active(self) -> AlgorithmVersion | None:
        """Return the currently active algorithm version."""

    @abstractmethod
    async def list_all(self) -> Sequence[AlgorithmVersion]:
        ...

    @abstractmethod
    async def add(self, version: AlgorithmVersion) -> AlgorithmVersion:
        ...

    @abstractmethod
    async def save(self, version: AlgorithmVersion) -> None:
        ...
