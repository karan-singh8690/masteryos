"""Assessment bounded context — domain layer.

Contains: QuestionInstance, Attempt, Answer aggregates and entities.
Pure Python; no I/O, no framework dependencies.
"""

from app.domain.assessment.answer import Answer
from app.domain.assessment.attempt import Attempt
from app.domain.assessment.events import (
    AttemptRecorded,
    QuestionInstanceAbandoned,
    QuestionInstanceAnswered,
    QuestionInstanceServed,
)
from app.domain.assessment.exceptions import (
    AnswerTypeMismatch,
    AssessmentError,
    AttemptAlreadyScored,
    DuplicateAttempt,
    QuestionAlreadyAnswered,
    QuestionInstanceNotServed,
    QuestionNotAnswered,
)
from app.domain.assessment.question_instance import (
    QuestionInstance,
    QuestionInstanceStatus,
)
from app.domain.assessment.repository import (
    AttemptRepository,
    QuestionInstanceRepository,
)

__all__ = [
    "Answer",
    "Attempt",
    "QuestionInstance",
    "QuestionInstanceStatus",
    "AttemptRecorded",
    "QuestionInstanceServed",
    "QuestionInstanceAnswered",
    "QuestionInstanceAbandoned",
    "AssessmentError",
    "QuestionAlreadyAnswered",
    "QuestionNotAnswered",
    "AttemptAlreadyScored",
    "DuplicateAttempt",
    "AnswerTypeMismatch",
    "QuestionInstanceNotServed",
    "AttemptRepository",
    "QuestionInstanceRepository",
]
