"""Assessment context — DTOs, commands, and handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.application.shared import (
    CommandHandler,
    CommandResult,
    EventPublisher,
    ResourceMissing,
    UnitOfWork,
    ValidationFailed,
)
from app.domain.assessment.attempt import Attempt
from app.domain.assessment.answer import Answer
from app.domain.assessment.question_instance import QuestionInstance
from app.domain.shared.ids import (
    AlgorithmVersionId,
    AnswerId,
    AttemptId,
    ContentVersionId,
    LearnerEnrollmentId,
    MisconceptionId,
    QuestionInstanceId,
    StudySessionId,
    TemplateVersionId,
)
from app.domain.shared.kernel import (
    AnswerType,
    AttemptIntent,
    ScoringOutcome,
)
from app.domain.shared.value_objects import Duration


# ============================================================
# Command DTOs
# ============================================================


@dataclass(frozen=True)
class SubmitAttemptCommand:
    """Command: Submit an answer (create an attempt)."""

    question_instance_id: UUID
    learner_enrollment_id: UUID
    study_session_id: UUID
    content_version_id: UUID
    template_version_id: UUID
    algorithm_version_id: UUID
    answer_type: str
    submitted_answer: dict[str, Any]
    execution_result: dict[str, Any] | None = None
    scoring_outcome: str = "correct"
    partial_credit: float | None = None
    time_to_answer_ms: int = 0
    hint_used: bool = False
    hint_tiers_used: list[int] = field(default_factory=list)
    attempt_intent: str = "practice"
    misconception_id: UUID | None = None
    concept_ids: tuple[UUID, ...] = ()


# ============================================================
# Response DTOs
# ============================================================


@dataclass(frozen=True)
class AttemptResultDTO:
    """Response: the result of submitting an attempt."""

    attempt_id: UUID
    scoring_outcome: str
    partial_credit: float | None
    time_to_answer_ms: int
    hint_used: bool
    created_at: datetime


# ============================================================
# Handler
# ============================================================


class SubmitAttemptHandler(CommandHandler[SubmitAttemptCommand, AttemptResultDTO]):
    """Handler for SubmitAttemptCommand — the heart of the learning loop.

    This handler:
    1. Validates the command.
    2. Loads the question instance (to mark it answered).
    3. Records the attempt (append-only).
    4. Marks the question instance as answered.
    5. Records the attempt in the study session.
    6. Commits and publishes events (AttemptRecorded flows to Mastery Engine).
    """

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: SubmitAttemptCommand) -> CommandResult[AttemptResultDTO]:
        # 1. Validate
        errors: dict[str, str] = {}
        if not command.question_instance_id:
            errors["question_instance_id"] = "Required"
        if not command.submitted_answer:
            errors["submitted_answer"] = "Required"
        if command.time_to_answer_ms < 0:
            errors["time_to_answer_ms"] = "Must be non-negative"
        if command.scoring_outcome not in ("correct", "incorrect", "partial"):
            errors["scoring_outcome"] = "Invalid outcome"
        if command.scoring_outcome == "partial" and command.partial_credit is None:
            errors["partial_credit"] = "Required when outcome is partial"
        if errors:
            return CommandResult.fail(str(ValidationFailed(errors)), "VALIDATION_FAILED")

        # Parse enums
        outcome = ScoringOutcome(command.scoring_outcome)
        intent = AttemptIntent(command.attempt_intent)

        async with self._uow as uow:
            # 2. Load question instance
            instance = await uow.question_instances.get_by_id(
                QuestionInstanceId(command.question_instance_id)
            )
            if instance is None:
                return CommandResult.fail(
                    str(ResourceMissing("QuestionInstance", command.question_instance_id)),
                    "QUESTION_NOT_FOUND",
                )

            if instance.is_answered:
                return CommandResult.fail("Question already answered", "QUESTION_ALREADY_ANSWERED")

            # 3. Create answer
            answer = Answer.create(
                question_instance_id=instance.id,
                answer_type=AnswerType(command.answer_type),
                submitted_answer=command.submitted_answer,
                execution_result=command.execution_result,
            )

            # 4. Record attempt (append-only — the data moat)
            attempt = Attempt.record(
                question_instance_id=instance.id,
                learner_enrollment_id=LearnerEnrollmentId(command.learner_enrollment_id),
                study_session_id=StudySessionId(command.study_session_id),
                content_version_id=ContentVersionId(command.content_version_id),
                template_version_id=TemplateVersionId(command.template_version_id),
                algorithm_version_id=AlgorithmVersionId(command.algorithm_version_id),
                scoring_outcome=outcome,
                time_to_answer=Duration(command.time_to_answer_ms // 1000),
                hint_used=command.hint_used,
                hint_tiers_used=command.hint_tiers_used,
                attempt_intent=intent,
                answer=answer,
                partial_credit=command.partial_credit,
                misconception_id=MisconceptionId(command.misconception_id) if command.misconception_id else None,
                concept_ids=command.concept_ids,
            )

            # 5. Mark question instance as answered
            instance.mark_answered(attempt.id.value)

            # 6. Record attempt in study session
            session = await uow.study_sessions.get_by_id(instance.study_session_id)
            if session is not None and session.is_active:
                session.record_attempt()

            # 7. Persist (attempt is append-only; instance and session are updated)
            await uow.attempts.add(attempt)
            await uow.question_instances.save(instance)
            if session is not None:
                await uow.study_sessions.save(session)

            # 8. Collect events from all aggregates
            events = attempt.collect_events() + instance.collect_events()
            if session is not None:
                events += session.collect_events()

            await uow.commit()

        # 9. Publish events (AttemptRecorded flows to Mastery Engine)
        await self._event_publisher.publish_many(events)

        # 10. Return result
        return CommandResult.ok(
            AttemptResultDTO(
                attempt_id=attempt.id.value,
                scoring_outcome=attempt.scoring_outcome.value,
                partial_credit=attempt.partial_credit,
                time_to_answer_ms=attempt.time_to_answer.milliseconds,
                hint_used=attempt.hint_used,
                created_at=attempt.created_at,
            ),
            events,
        )
