"""Assessment context — domain-specific exceptions."""

from __future__ import annotations

from app.domain.shared.kernel import DomainError


class AssessmentError(DomainError):
    """Base for all assessment domain errors."""


class QuestionAlreadyAnswered(AssessmentError):
    def __init__(self, instance_id: object) -> None:
        super().__init__(
            f"Question instance {instance_id} has already been answered",
            code="QUESTION_ALREADY_ANSWERED",
        )


class QuestionNotAnswered(AssessmentError):
    def __init__(self, instance_id: object) -> None:
        super().__init__(
            f"Question instance {instance_id} has not been answered",
            code="QUESTION_NOT_ANSWERED",
        )


class AttemptAlreadyScored(AssessmentError):
    def __init__(self, attempt_id: object) -> None:
        super().__init__(
            f"Attempt {attempt_id} has already been scored",
            code="ATTEMPT_ALREADY_SCORED",
        )


class DuplicateAttempt(AssessmentError):
    def __init__(self, instance_id: object) -> None:
        super().__init__(
            f"Duplicate attempt for question instance {instance_id}",
            code="DUPLICATE_ATTEMPT",
        )


class AnswerTypeMismatch(AssessmentError):
    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(
            f"Answer type mismatch: expected {expected}, got {actual}",
            code="ANSWER_TYPE_MISMATCH",
        )


class QuestionInstanceNotServed(AssessmentError):
    def __init__(self, instance_id: object) -> None:
        super().__init__(
            f"Question instance {instance_id} has not been served",
            code="QUESTION_INSTANCE_NOT_SERVED",
        )
