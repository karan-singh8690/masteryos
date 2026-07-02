"""Assessment context — abstract repository interfaces.

No implementations. No SQL. No ORM. Only ABCs defining the contract
that infrastructure-layer repositories must fulfill.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.domain.assessment.attempt import Attempt
from app.domain.assessment.question_instance import QuestionInstance
from app.domain.shared.ids import (
    AttemptId,
    LearnerEnrollmentId,
    QuestionInstanceId,
    StudySessionId,
)


class QuestionInstanceRepository(ABC):
    """Abstract repository for QuestionInstance aggregates."""

    @abstractmethod
    async def get_by_id(self, id: QuestionInstanceId) -> QuestionInstance | None:
        """Load a question instance by ID. Returns None if not found."""

    @abstractmethod
    async def add(self, instance: QuestionInstance) -> QuestionInstance:
        """Persist a new question instance."""

    @abstractmethod
    async def save(self, instance: QuestionInstance) -> None:
        """Save changes to an existing question instance."""

    @abstractmethod
    async def list_by_session(
        self, study_session_id: StudySessionId
    ) -> Sequence[QuestionInstance]:
        """List all question instances served in a study session."""


class AttemptRepository(ABC):
    """Abstract repository for Attempt aggregates.

    Attempts are append-only — there is no ``save`` or ``update`` method.
    Once an attempt is recorded, it is never modified. This is the
    data moat invariant (ASD Section 5.3, I1).
    """

    @abstractmethod
    async def get_by_id(self, id: AttemptId) -> Attempt | None:
        """Load an attempt by ID. Returns None if not found."""

    @abstractmethod
    async def add(self, attempt: Attempt) -> Attempt:
        """Persist a new attempt. The attempt must not already exist."""

    @abstractmethod
    async def list_by_enrollment(
        self,
        learner_enrollment_id: LearnerEnrollmentId,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Attempt]:
        """List attempts by learner enrollment, most recent first."""

    @abstractmethod
    async def list_by_enrollment_and_concept(
        self,
        learner_enrollment_id: LearnerEnrollmentId,
        concept_id: UUID,
    ) -> Sequence[Attempt]:
        """List all attempts by a learner on a specific concept.

        This is the primary query for mastery recompute — the Mastery
        Engine uses this to reconstruct mastery from attempt history.
        """

    @abstractmethod
    async def count_by_enrollment(
        self, learner_enrollment_id: LearnerEnrollmentId
    ) -> int:
        """Count total attempts by a learner."""
