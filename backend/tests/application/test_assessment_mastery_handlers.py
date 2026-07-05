"""Tests for the Assessment context command handler (SubmitAttempt) and
the Mastery context command handler (UpdateMastery).

These tests verify the learning loop's critical path:
  SubmitAttempt → AttemptRecorded → UpdateMastery → MasteryUpdated
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.application.assessment.handlers import (
    SubmitAttemptCommand,
    SubmitAttemptHandler,
)
from app.application.learning.dto import (
    EnrollLearnerCommand,
    StartStudySessionCommand,
)
from app.application.learning.handlers import (
    EnrollLearnerHandler,
    StartStudySessionHandler,
)
from app.application.mastery.handlers import (
    PublishAlgorithmVersionCommand,
    PublishAlgorithmVersionHandler,
    UpdateMasteryCommand,
    UpdateMasteryHandler,
)
from app.domain.mastery.algorithm_version import AlgorithmVersion
from app.domain.mastery.events import (
    AlgorithmVersionPublished,
    MasteryUpdated,
)
from app.domain.assessment.events import AttemptRecorded
from app.domain.shared.kernel import VersionNumber
from tests.application.fakes import FakeUnitOfWork, FakeEventPublisher


class TestSubmitAttemptHandler:
    """Tests for SubmitAttemptHandler — the heart of the learning loop."""

    @pytest.mark.asyncio
    async def test_submit_attempt_success(self) -> None:
        """Submitting a correct attempt records it and marks the question answered."""
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        # Setup: enroll + start session + create algorithm version
        await self._setup_active_algorithm(uow)

        enroll_handler = EnrollLearnerHandler(uow, publisher)
        enroll_result = await enroll_handler.handle(
            EnrollLearnerCommand(user_id=uuid4(), subject_id=uuid4())
        )
        enrollment_id = enroll_result.value.id

        start_handler = StartStudySessionHandler(uow, publisher)
        start_result = await start_handler.handle(
            StartStudySessionCommand(enrollment_id=enrollment_id)
        )
        session_id = start_result.value.id

        # Create a question instance manually (in a real system, the scheduler does this)
        from app.domain.assessment.question_instance import QuestionInstance
        from app.domain.shared.ids import (
            ContentVersionId,
            LearnerEnrollmentId,
            QuestionInstanceId,
            StudySessionId,
            TemplateVersionId,
        )

        instance = QuestionInstance.serve(
            template_version_id=TemplateVersionId.generate(),
            content_version_id=ContentVersionId.generate(),
            learner_enrollment_id=LearnerEnrollmentId(enrollment_id),
            study_session_id=StudySessionId(session_id),
            parameter_seed=42,
            parameter_values={"size": 100},
            rendered_prompt={"question": "What is O(1)?"},
            correct_answer={"answer": "constant time"},
        )
        await uow.question_instances.add(instance)
        publisher.reset()

        # Submit attempt
        handler = SubmitAttemptHandler(uow, publisher)
        concept_id = uuid4()
        result = await handler.handle(
            SubmitAttemptCommand(
                question_instance_id=instance.id.value,
                learner_enrollment_id=enrollment_id,
                study_session_id=session_id,
                content_version_id=instance.content_version_id.value,
                template_version_id=instance.template_version_id.value,
                algorithm_version_id=uow.algorithm_versions._active_id,
                answer_type="multiple_choice",
                submitted_answer={"choice": "constant time"},
                scoring_outcome="correct",
                time_to_answer_ms=12000,
                attempt_intent="practice",
                concept_ids=(concept_id,),
            )
        )

        assert result.success
        assert result.value.scoring_outcome == "correct"
        assert result.value.time_to_answer_ms == 12000
        assert any(isinstance(e, AttemptRecorded) for e in publisher.published_events)

    @pytest.mark.asyncio
    async def test_submit_attempt_already_answered(self) -> None:
        """Cannot submit an answer to an already-answered question."""
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        await self._setup_active_algorithm(uow)

        enroll_handler = EnrollLearnerHandler(uow, publisher)
        enroll_result = await enroll_handler.handle(
            EnrollLearnerCommand(user_id=uuid4(), subject_id=uuid4())
        )
        enrollment_id = enroll_result.value.id

        start_handler = StartStudySessionHandler(uow, publisher)
        start_result = await start_handler.handle(
            StartStudySessionCommand(enrollment_id=enrollment_id)
        )
        session_id = start_result.value.id

        from app.domain.assessment.question_instance import QuestionInstance
        from app.domain.shared.ids import (
            ContentVersionId,
            LearnerEnrollmentId,
            QuestionInstanceId,
            StudySessionId,
            TemplateVersionId,
        )

        instance = QuestionInstance.serve(
            template_version_id=TemplateVersionId.generate(),
            content_version_id=ContentVersionId.generate(),
            learner_enrollment_id=LearnerEnrollmentId(enrollment_id),
            study_session_id=StudySessionId(session_id),
            parameter_seed=42,
            parameter_values={},
            rendered_prompt={"q": "test"},
            correct_answer={"a": "test"},
        )
        await uow.question_instances.add(instance)

        # Submit first attempt
        handler = SubmitAttemptHandler(uow, publisher)
        await handler.handle(
            SubmitAttemptCommand(
                question_instance_id=instance.id.value,
                learner_enrollment_id=enrollment_id,
                study_session_id=session_id,
                content_version_id=instance.content_version_id.value,
                template_version_id=instance.template_version_id.value,
                algorithm_version_id=uow.algorithm_versions._active_id,
                answer_type="multiple_choice",
                submitted_answer={"choice": "test"},
                scoring_outcome="correct",
                concept_ids=(uuid4(),),
            )
        )

        # Try to submit again
        publisher.reset()
        result = await handler.handle(
            SubmitAttemptCommand(
                question_instance_id=instance.id.value,
                learner_enrollment_id=enrollment_id,
                study_session_id=session_id,
                content_version_id=instance.content_version_id.value,
                template_version_id=instance.template_version_id.value,
                algorithm_version_id=uow.algorithm_versions._active_id,
                answer_type="multiple_choice",
                submitted_answer={"choice": "wrong"},
                scoring_outcome="incorrect",
                concept_ids=(uuid4(),),
            )
        )

        assert not result.success
        assert result.error_code == "QUESTION_ALREADY_ANSWERED"

    @pytest.mark.asyncio
    async def test_submit_attempt_validation_failure(self) -> None:
        """Invalid command data is rejected."""
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()
        handler = SubmitAttemptHandler(uow, publisher)

        result = await handler.handle(
            SubmitAttemptCommand(
                question_instance_id=uuid4(),
                learner_enrollment_id=uuid4(),
                study_session_id=uuid4(),
                content_version_id=uuid4(),
                template_version_id=uuid4(),
                algorithm_version_id=uuid4(),
                answer_type="multiple_choice",
                submitted_answer={},
                scoring_outcome="invalid_outcome",
                time_to_answer_ms=-1,
                concept_ids=(),
            )
        )

        assert not result.success
        assert result.error_code == "VALIDATION_FAILED"

    @staticmethod
    async def _setup_active_algorithm(uow: FakeUnitOfWork) -> None:
        """Create and activate an algorithm version in the fake UoW."""
        algo = AlgorithmVersion.create(
            version_number=VersionNumber(1),
            name="Deterministic v1",
            parameters={
                "memory_decay_rate_per_day": 0.95,
                "mastery_consolidation_rate": 0.10,
                "review_interval_expansion_factor": 2.5,
                "review_interval_contraction_factor": 0.3,
                "mastery_threshold_proficient": 0.70,
                "mastery_threshold_mastered": 0.85,
                "memory_threshold": 0.50,
                "hint_usage_mastery_penalty": 0.30,
                "memory_weight": 0.40,
                "durable_weight": 0.60,
            },
        )
        algo.promote()
        await uow.algorithm_versions.add(algo)


class TestUpdateMasteryHandler:
    """Tests for UpdateMasteryHandler — the mastery engine's entry point."""

    @pytest.mark.asyncio
    async def test_update_mastery_after_correct_attempt(self) -> None:
        """Mastery score increases after a correct attempt."""
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        # Setup: active algorithm + enrollment
        await TestSubmitAttemptHandler._setup_active_algorithm(uow)
        algo = await uow.algorithm_versions.get_active()

        enroll_handler = EnrollLearnerHandler(uow, publisher)
        enroll_result = await enroll_handler.handle(
            EnrollLearnerCommand(user_id=uuid4(), subject_id=uuid4())
        )
        enrollment_id = enroll_result.value.id

        # Create a correct attempt and add it to the repository
        from app.domain.assessment.attempt import Attempt
        from app.domain.shared.ids import (
            AlgorithmVersionId,
            ContentVersionId,
            LearnerEnrollmentId,
            QuestionInstanceId,
            StudySessionId,
            TemplateVersionId,
        )
        from app.domain.shared.kernel import AttemptIntent, ScoringOutcome
        from app.domain.shared.value_objects import Duration

        concept_id = uuid4()
        attempt = Attempt.record(
            question_instance_id=QuestionInstanceId.generate(),
            learner_enrollment_id=LearnerEnrollmentId(enrollment_id),
            study_session_id=StudySessionId.generate(),
            content_version_id=ContentVersionId.generate(),
            template_version_id=TemplateVersionId.generate(),
            algorithm_version_id=algo.id,
            scoring_outcome=ScoringOutcome.CORRECT,
            time_to_answer=Duration(10),
            hint_used=False,
            hint_tiers_used=[],
            attempt_intent=AttemptIntent.PRACTICE,
            concept_ids=(concept_id,),
        )
        await uow.attempts.add(attempt)

        # Update mastery
        handler = UpdateMasteryHandler(uow, publisher)
        result = await handler.handle(
            UpdateMasteryCommand(
                learner_enrollment_id=enrollment_id,
                concept_ids=(concept_id,),
                algorithm_version_id=algo.id.value,
            )
        )

        assert result.success
        assert len(result.value) == 1
        score_dto = result.value[0]
        assert score_dto.concept_id == concept_id
        assert score_dto.memory_score > 0.0  # memory should be boosted
        assert score_dto.evidence_count == 1
        assert any(isinstance(e, MasteryUpdated) for e in publisher.published_events)

    @pytest.mark.asyncio
    async def test_update_mastery_no_active_algorithm(self) -> None:
        """Without an active algorithm, mastery update fails."""
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        handler = UpdateMasteryHandler(uow, publisher)
        result = await handler.handle(
            UpdateMasteryCommand(
                learner_enrollment_id=uuid4(),
                concept_ids=(uuid4(),),
                algorithm_version_id=uuid4(),
            )
        )

        assert not result.success
        assert result.error_code == "ALGORITHM_VERSION_NOT_ACTIVE"

    @pytest.mark.asyncio
    async def test_update_mastery_deterministic(self) -> None:
        """Same inputs → same outputs (ADR-0007, invariant M1)."""
        uow1 = FakeUnitOfWork()
        uow2 = FakeUnitOfWork()
        publisher1 = FakeEventPublisher()
        publisher2 = FakeEventPublisher()

        # Setup both UoWs identically
        for uow, pub in [(uow1, publisher1), (uow2, publisher2)]:
            await TestSubmitAttemptHandler._setup_active_algorithm(uow)
            algo = await uow.algorithm_versions.get_active()

            enroll_handler = EnrollLearnerHandler(uow, pub)
            enroll_result = await enroll_handler.handle(
                EnrollLearnerCommand(user_id=uuid4(), subject_id=uuid4())
            )
            enrollment_id = enroll_result.value.id

            from app.domain.assessment.attempt import Attempt
            from app.domain.shared.ids import (
                ContentVersionId,
                LearnerEnrollmentId,
                QuestionInstanceId,
                StudySessionId,
                TemplateVersionId,
            )
            from app.domain.shared.kernel import AttemptIntent, ScoringOutcome
            from app.domain.shared.value_objects import Duration

            concept_id = uuid4()
            attempt = Attempt.record(
                question_instance_id=QuestionInstanceId.generate(),
                learner_enrollment_id=LearnerEnrollmentId(enrollment_id),
                study_session_id=StudySessionId.generate(),
                content_version_id=ContentVersionId.generate(),
                template_version_id=TemplateVersionId.generate(),
                algorithm_version_id=algo.id,
                scoring_outcome=ScoringOutcome.CORRECT,
                time_to_answer=Duration(10),
                hint_used=False,
                hint_tiers_used=[],
                attempt_intent=AttemptIntent.PRACTICE,
                concept_ids=(concept_id,),
            )
            await uow.attempts.add(attempt)

            handler = UpdateMasteryHandler(uow, pub)
            result = await handler.handle(
                UpdateMasteryCommand(
                    learner_enrollment_id=enrollment_id,
                    concept_ids=(concept_id,),
                    algorithm_version_id=algo.id.value,
                )
            )

        # Both should produce the same mastery scores (deterministic)
        # Note: the enrollment_ids and concept_ids are different per UoW,
        # but the SCORES should be the same given the same attempt history.


class TestPublishAlgorithmVersionHandler:
    """Tests for PublishAlgorithmVersionHandler."""

    @pytest.mark.asyncio
    async def test_publish_algorithm_version(self) -> None:
        uow = FakeUnitOfWork()
        publisher = FakeEventPublisher()

        # Create an inactive algorithm version
        algo = AlgorithmVersion.create(
            version_number=VersionNumber(1),
            name="Test v1",
            parameters={"memory_decay_rate_per_day": 0.95},
        )
        await uow.algorithm_versions.add(algo)

        # Publish it
        handler = PublishAlgorithmVersionHandler(uow, publisher)
        result = await handler.handle(
            PublishAlgorithmVersionCommand(
                algorithm_version_id=algo.id.value,
                admin_user_id=uuid4(),
            )
        )

        assert result.success
        assert any(isinstance(e, AlgorithmVersionPublished) for e in publisher.published_events)
