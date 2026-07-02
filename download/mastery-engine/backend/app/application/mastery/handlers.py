"""Mastery context — DTOs, commands, and handlers.

The UpdateMasteryHandler is the most critical handler in the system.
It consumes AttemptRecorded events and updates mastery scores using
the MasteryCalculator domain service (per ADR-0007, deterministic-first).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.application.shared import (
    CommandHandler,
    CommandResult,
    ConcurrencyConflict,
    EventPublisher,
    ResourceMissing,
    UnitOfWork,
)
from app.application.learning.dto import MasteryScoreDTO
from app.domain.mastery.algorithm_version import AlgorithmVersion
from app.domain.mastery.mastery_calculator import MasteryCalculator
from app.domain.mastery.mastery_score import MasteryScore
from app.domain.mastery.review import Review
from app.domain.shared.ids import (
    AlgorithmVersionId,
    ConceptId,
    LearnerEnrollmentId,
    MasteryScoreId,
)
from app.domain.shared.kernel import ReviewPriority
from app.domain.shared.value_objects import ReviewInterval


# ============================================================
# Command DTOs
# ============================================================


@dataclass(frozen=True)
class UpdateMasteryCommand:
    """Command: Update mastery score(s) after an attempt.

    This command is issued by the Mastery Engine event subscriber when
    it consumes an AttemptRecorded event. It carries all the information
    needed to recompute mastery for the affected concept(s).
    """

    learner_enrollment_id: UUID
    concept_ids: tuple[UUID, ...]
    algorithm_version_id: UUID
    # The attempt history is loaded by the handler via the attempt repository.


@dataclass(frozen=True)
class PublishAlgorithmVersionCommand:
    """Command: Promote an algorithm version to production."""

    algorithm_version_id: UUID
    admin_user_id: UUID


# ============================================================
# Handler
# ============================================================


class UpdateMasteryHandler(CommandHandler[UpdateMasteryCommand, list[MasteryScoreDTO]]):
    """Handler for UpdateMasteryCommand — the mastery engine's entry point.

    This handler:
    1. Loads the active algorithm version.
    2. For each concept affected by the attempt:
       a. Loads the attempt history for (learner, concept).
       b. Loads the current mastery score (or initializes if unseen).
       c. Uses the MasteryCalculator to compute new scores.
       d. Applies the update to the mastery score aggregate.
       e. Schedules/reschedules the review.
    3. Commits and publishes events (MasteryUpdated, ConceptStateChanged, etc.).

    The MasteryCalculator is a pure function (ADR-0007, invariant M1):
    same inputs → same outputs. This handler is the orchestration layer;
    the computation lives in the domain.
    """

    MAX_RETRIES = 3

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher
        self._calculator = MasteryCalculator()

    async def handle(self, command: UpdateMasteryCommand) -> CommandResult[list[MasteryScoreDTO]]:
        async with self._uow as uow:
            # 1. Load the active algorithm version
            algorithm = await uow.algorithm_versions.get_active()
            if algorithm is None:
                return CommandResult.fail(
                    "No active algorithm version",
                    "ALGORITHM_VERSION_NOT_ACTIVE",
                )

            enrollment_id = LearnerEnrollmentId(command.learner_enrollment_id)
            algo_id = AlgorithmVersionId(command.algorithm_version_id)
            all_events: list[Any] = []
            results: list[MasteryScoreDTO] = []

            # 2. For each concept affected by the attempt
            for concept_id_raw in command.concept_ids:
                concept_id = ConceptId(concept_id_raw)

                # a. Load attempt history
                attempts = await uow.attempts.list_by_enrollment_and_concept(
                    enrollment_id, concept_id_raw
                )

                if not attempts:
                    continue  # No attempts → no mastery update

                # b. Load or initialize mastery score
                score = await uow.mastery_scores.get_by_enrollment_and_concept(
                    enrollment_id, concept_id
                )
                if score is None:
                    score = MasteryScore.initialize(enrollment_id, concept_id, algo_id)
                    await uow.mastery_scores.add(score)

                # Load current review interval (for expansion/contraction)
                review = await uow.reviews.get_by_enrollment_and_concept(
                    enrollment_id, concept_id
                )
                current_interval = review.review_interval if review else ReviewInterval(7)

                # c. Compute new scores using the MasteryCalculator (pure domain service)
                computation = self._calculator.compute(
                    attempts=list(attempts),
                    algorithm=algorithm,
                    current_review_interval=current_interval,
                    previous_memory_score=score.memory_score,
                    previous_durable_mastery=score.durable_mastery_score,
                )

                # d. Apply the update (with optimistic concurrency retry)
                for attempt_num in range(self.MAX_RETRIES):
                    try:
                        score.apply_update(
                            new_memory_score=computation.memory_score,
                            new_durable_mastery_score=computation.durable_mastery_score,
                            new_mastery_score_combined=computation.mastery_score_combined,
                            new_confidence_interval=computation.confidence_interval,
                            new_evidence_count=computation.evidence_count,
                            algorithm_version_id=algo_id,
                            mastered_threshold=algorithm.mastery_threshold_mastered,
                            proficient_threshold=algorithm.mastery_threshold_proficient,
                            memory_threshold=algorithm.memory_threshold,
                            last_attempt_at=computation.last_attempt_at,
                        )
                        await uow.mastery_scores.save(score)
                        break
                    except Exception:
                        if attempt_num == self.MAX_RETRIES - 1:
                            return CommandResult.fail(
                                f"Concurrency conflict on mastery score {score.id}",
                                "CONCURRENCY_CONFLICT",
                            )
                        # Reload and retry
                        score = await uow.mastery_scores.get_by_enrollment_and_concept(
                            enrollment_id, concept_id
                        )
                        if score is None:
                            break

                # e. Schedule/reschedule review
                if review is None:
                    review = Review.schedule(
                        learner_enrollment_id=enrollment_id,
                        concept_id=concept_id,
                        algorithm_version_id=algo_id,
                        interval=computation.new_review_interval,
                        priority=self._derive_priority(computation.memory_score, algorithm.memory_threshold),
                    )
                    await uow.reviews.add(review)
                else:
                    review.reschedule(
                        new_interval=computation.new_review_interval,
                        priority=self._derive_priority(computation.memory_score, algorithm.memory_threshold),
                    )
                    await uow.reviews.save(review)

                # Collect events
                all_events.extend(score.collect_events())
                all_events.extend(review.collect_events())

                # Build DTO
                results.append(MasteryScoreDTO(
                    concept_id=concept_id.value,
                    memory_score=score.memory_score,
                    durable_mastery_score=score.durable_mastery_score,
                    mastery_score_combined=score.mastery_score_combined,
                    concept_state=score.concept_state.value,
                    weakness_severity=score.weakness_severity.value,
                    evidence_count=score.evidence_count,
                    last_attempt_at=score.last_attempt_at,
                ))

            await uow.commit()

        # Publish all events
        await self._event_publisher.publish_many(all_events)
        return CommandResult.ok(results, all_events)

    @staticmethod
    def _derive_priority(memory_score: float, memory_threshold: float) -> ReviewPriority:
        """Derive review priority from the memory score."""
        if memory_score < memory_threshold * 0.5:
            return ReviewPriority.HIGH
        if memory_score < memory_threshold:
            return ReviewPriority.MEDIUM
        return ReviewPriority.LOW


class PublishAlgorithmVersionHandler(CommandHandler[PublishAlgorithmVersionCommand, None]):
    """Handler for PublishAlgorithmVersionCommand."""

    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher) -> None:
        self._uow = uow
        self._event_publisher = event_publisher

    async def handle(self, command: PublishAlgorithmVersionCommand) -> CommandResult[None]:
        async with self._uow as uow:
            version = await uow.algorithm_versions.get_by_id(
                AlgorithmVersionId(command.algorithm_version_id)
            )
            if version is None:
                return CommandResult.fail(
                    str(ResourceMissing("AlgorithmVersion", command.algorithm_version_id)),
                    "ALGORITHM_VERSION_NOT_FOUND",
                )

            # Get previous active version
            previous = await uow.algorithm_versions.get_active()
            previous_number = previous.version_number.value if previous else None

            # Deactivate previous
            if previous is not None and previous.id != version.id:
                # The domain doesn't have a "deactivate" method; the application
                # layer handles this by setting is_active = False on the old version
                # and is_active = True on the new version.
                # In a real implementation, this would be a domain method or
                # the repository would handle the transition.
                pass

            # Promote new version
            try:
                version.promote(previous_version_number=previous_number)
            except Exception as exc:
                return CommandResult.fail(str(exc), "ALGORITHM_VERSION_ALREADY_ACTIVE")

            await uow.algorithm_versions.save(version)
            events = version.collect_events()
            await uow.commit()

        await self._event_publisher.publish_many(events)
        return CommandResult.ok(None, events)
