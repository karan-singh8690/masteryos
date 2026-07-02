"""Answer — the learner's response to a question instance.

Answers are separate from attempts so that multiple pre-submission revisions
(for code questions with iterative execution) can be stored without
duplicating attempt metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.shared.kernel import AnswerType, InvariantViolation, ValueObject
from app.domain.shared.ids import AnswerId, AttemptId, QuestionInstanceId


@dataclass(frozen=True)
class Answer(ValueObject):
    """A learner's submitted answer to a question instance.

    Immutable after creation. Pre-submission revisions are captured
    in ``revision_history`` for analytics on the learner's
    problem-solving process.
    """

    id: AnswerId
    attempt_id: AttemptId | None
    question_instance_id: QuestionInstanceId
    answer_type: AnswerType
    submitted_answer: dict[str, Any]
    execution_result: dict[str, Any] | None = None
    revision_count: int = 0
    revision_history: list[dict[str, Any]] = field(default_factory=list)
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.revision_count < 0:
            raise InvariantViolation("Answer", "revision_count must be non-negative")
        if not self.submitted_answer:
            raise InvariantViolation("Answer", "submitted_answer must not be empty")

    @classmethod
    def create(
        cls,
        question_instance_id: QuestionInstanceId,
        answer_type: AnswerType,
        submitted_answer: dict[str, Any],
        execution_result: dict[str, Any] | None = None,
    ) -> Answer:
        """Create a new answer (pre-attempt; attempt_id set later)."""
        return cls(
            id=AnswerId.generate(),
            attempt_id=None,
            question_instance_id=question_instance_id,
            answer_type=answer_type,
            submitted_answer=submitted_answer,
            execution_result=execution_result,
        )

    def attach_to_attempt(self, attempt_id: AttemptId) -> Answer:
        """Return a new Answer with the attempt_id set (called when the attempt is recorded)."""
        return Answer(
            id=self.id,
            attempt_id=attempt_id,
            question_instance_id=self.question_instance_id,
            answer_type=self.answer_type,
            submitted_answer=self.submitted_answer,
            execution_result=self.execution_result,
            revision_count=self.revision_count,
            revision_history=self.revision_history,
            submitted_at=self.submitted_at,
        )
