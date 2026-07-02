"""Fake infrastructure for testing the application layer.

These fakes implement the domain's repository interfaces and the application
layer's Unit of Work and Event Publisher — entirely in memory. They enable
testing the application layer without a database, HTTP, or any infrastructure.

Usage:
    fakes = FakeInfrastructure()
    handler = RegisterUserHandler(fakes.uow, fakes.event_publisher)
    result = await handler.handle(RegisterUserCommand(...))
    assert result.success
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.domain.shared.kernel import DomainEvent, Email
from app.domain.shared.ids import (
    LearnerEnrollmentId,
    StudySessionId,
    UserId,
    SubjectId,
)


class FakeUserRepository:
    """In-memory user repository for testing."""

    def __init__(self) -> None:
        self._users: dict[UUID, Any] = {}
        self._by_email: dict[str, Any] = {}

    async def get_by_id(self, id: UserId) -> Any | None:
        return self._users.get(id.value)

    async def get_by_email(self, email: Email) -> Any | None:
        return self._by_email.get(email.value)

    async def add(self, user: Any) -> Any:
        self._users[user.id.value] = user
        self._by_email[user.email.value] = user
        return user

    async def save(self, user: Any) -> None:
        self._users[user.id.value] = user
        self._by_email[user.email.value] = user


class FakeEnrollmentRepository:
    """In-memory enrollment repository."""

    def __init__(self) -> None:
        self._enrollments: dict[UUID, Any] = {}

    async def get_by_id(self, id: LearnerEnrollmentId) -> Any | None:
        return self._enrollments.get(id.value)

    async def get_by_user_and_subject(self, user_id: UserId, subject_id: SubjectId) -> Any | None:
        for e in self._enrollments.values():
            if e.user_id == user_id and e.subject_id == subject_id:
                return e
        return None

    async def list_by_user(self, user_id: UserId) -> list[Any]:
        return [e for e in self._enrollments.values() if e.user_id == user_id]

    async def add(self, enrollment: Any) -> Any:
        self._enrollments[enrollment.id.value] = enrollment
        return enrollment

    async def save(self, enrollment: Any) -> None:
        self._enrollments[enrollment.id.value] = enrollment


class FakeStudySessionRepository:
    """In-memory study session repository."""

    def __init__(self) -> None:
        self._sessions: dict[UUID, Any] = {}

    async def get_by_id(self, id: StudySessionId) -> Any | None:
        return self._sessions.get(id.value)

    async def get_active_by_enrollment(self, enrollment_id: LearnerEnrollmentId) -> Any | None:
        for s in self._sessions.values():
            if s.learner_enrollment_id == enrollment_id and s.status.value == "active":
                return s
        return None

    async def list_by_enrollment(self, enrollment_id: LearnerEnrollmentId, limit: int = 50, offset: int = 0) -> list[Any]:
        result = [s for s in self._sessions.values() if s.learner_enrollment_id == enrollment_id]
        return result[offset : offset + limit]

    async def add(self, session: Any) -> Any:
        self._sessions[session.id.value] = session
        return session

    async def save(self, session: Any) -> None:
        self._sessions[session.id.value] = session


class FakeAttemptRepository:
    """In-memory attempt repository (append-only — no save)."""

    def __init__(self) -> None:
        self._attempts: dict[UUID, Any] = {}
        self._by_enrollment: dict[UUID, list[Any]] = {}

    async def get_by_id(self, id: Any) -> Any | None:
        return self._attempts.get(id.value)

    async def add(self, attempt: Any) -> Any:
        self._attempts[attempt.id.value] = attempt
        enrollment_id = attempt.learner_enrollment_id.value
        if enrollment_id not in self._by_enrollment:
            self._by_enrollment[enrollment_id] = []
        self._by_enrollment[enrollment_id].append(attempt)
        return attempt

    async def list_by_enrollment(self, enrollment_id: Any, limit: int = 100, offset: int = 0) -> list[Any]:
        attempts = self._by_enrollment.get(enrollment_id.value, [])
        return sorted(attempts, key=lambda a: a.created_at, reverse=True)[offset : offset + limit]

    async def list_by_enrollment_and_concept(self, enrollment_id: Any, concept_id: UUID) -> list[Any]:
        # In a real implementation, this would filter by concept via template_concepts join.
        # For testing, we return all attempts (the test sets up the data).
        return self._by_enrollment.get(enrollment_id.value, [])

    async def count_by_enrollment(self, enrollment_id: Any) -> int:
        return len(self._by_enrollment.get(enrollment_id.value, []))


class FakeQuestionInstanceRepository:
    """In-memory question instance repository."""

    def __init__(self) -> None:
        self._instances: dict[UUID, Any] = {}

    async def get_by_id(self, id: Any) -> Any | None:
        return self._instances.get(id.value)

    async def add(self, instance: Any) -> Any:
        self._instances[instance.id.value] = instance
        return instance

    async def save(self, instance: Any) -> None:
        self._instances[instance.id.value] = instance

    async def list_by_session(self, session_id: Any) -> list[Any]:
        return [i for i in self._instances.values() if i.study_session_id == session_id]


class FakeMasteryScoreRepository:
    """In-memory mastery score repository."""

    def __init__(self) -> None:
        self._scores: dict[UUID, Any] = {}

    async def get_by_id(self, id: Any) -> Any | None:
        return self._scores.get(id.value)

    async def get_by_enrollment_and_concept(self, enrollment_id: Any, concept_id: Any) -> Any | None:
        for s in self._scores.values():
            if s.learner_enrollment_id == enrollment_id and s.concept_id == concept_id:
                return s
        return None

    async def list_by_enrollment(self, enrollment_id: Any) -> list[Any]:
        return [s for s in self._scores.values() if s.learner_enrollment_id == enrollment_id]

    async def list_weak_by_enrollment(self, enrollment_id: Any) -> list[Any]:
        return [
            s
            for s in self._scores.values()
            if s.learner_enrollment_id == enrollment_id and s.is_weak
        ]

    async def add(self, score: Any) -> Any:
        self._scores[score.id.value] = score
        return score

    async def save(self, score: Any) -> None:
        self._scores[score.id.value] = score

    async def count_by_algorithm_version(self, algorithm_version_id: Any) -> int:
        return sum(1 for s in self._scores.values() if s.algorithm_version_id == algorithm_version_id)


class FakeReviewRepository:
    """In-memory review repository."""

    def __init__(self) -> None:
        self._reviews: dict[UUID, Any] = {}

    async def get_by_id(self, id: Any) -> Any | None:
        return self._reviews.get(id.value)

    async def get_by_enrollment_and_concept(self, enrollment_id: Any, concept_id: Any) -> Any | None:
        for r in self._reviews.values():
            if r.learner_enrollment_id == enrollment_id and r.concept_id == concept_id:
                return r
        return None

    async def list_due_by_enrollment(self, enrollment_id: Any) -> list[Any]:
        return [r for r in self._reviews.values() if r.learner_enrollment_id == enrollment_id and r.is_due]

    async def add(self, review: Any) -> Any:
        self._reviews[review.id.value] = review
        return review

    async def save(self, review: Any) -> None:
        self._reviews[review.id.value] = review


class FakeAlgorithmVersionRepository:
    """In-memory algorithm version repository."""

    def __init__(self) -> None:
        self._versions: dict[UUID, Any] = {}
        self._active_id: UUID | None = None

    async def get_by_id(self, id: Any) -> Any | None:
        return self._versions.get(id.value)

    async def get_active(self) -> Any | None:
        if self._active_id is None:
            return None
        return self._versions.get(self._active_id)

    async def list_all(self) -> list[Any]:
        return list(self._versions.values())

    async def add(self, version: Any) -> Any:
        self._versions[version.id.value] = version
        if version.is_active:
            self._active_id = version.id.value
        return version

    async def save(self, version: Any) -> None:
        self._versions[version.id.value] = version
        if version.is_active:
            # Deactivate previous
            for v in self._versions.values():
                if v.id != version.id:
                    v.is_active = False
            self._active_id = version.id.value


class FakeRecommendationRepository:
    """In-memory recommendation repository."""

    def __init__(self) -> None:
        self._recs: dict[UUID, Any] = {}

    async def get_by_id(self, id: Any) -> Any | None:
        return self._recs.get(id.value)

    async def list_by_enrollment(self, enrollment_id: Any, active_only: bool = False) -> list[Any]:
        result = [r for r in self._recs.values() if r.learner_enrollment_id == enrollment_id]
        if active_only:
            result = [r for r in result if r.is_actionable]
        return result

    async def add(self, rec: Any) -> Any:
        self._recs[rec.id.value] = rec
        return rec

    async def save(self, rec: Any) -> None:
        self._recs[rec.id.value] = rec


class FakeStreakRepository:
    """In-memory streak repository."""

    def __init__(self) -> None:
        self._streaks: dict[UUID, Any] = {}

    async def get_by_enrollment(self, enrollment_id: Any) -> Any | None:
        return self._streaks.get(enrollment_id.value)

    async def save(self, streak: Any) -> None:
        self._streaks[streak.learner_enrollment_id.value] = streak


class FakeEventPublisher:
    """In-memory event publisher — collects events for testing."""

    def __init__(self) -> None:
        self.published_events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.published_events.append(event)

    async def publish_many(self, events: Sequence[DomainEvent]) -> None:
        self.published_events.extend(events)

    def reset(self) -> None:
        self.published_events.clear()


class FakeUnitOfWork:
    """In-memory Unit of Work for testing.

    Implements the UnitOfWork interface with in-memory repositories.
    The ``commit()`` method is a no-op (data is already in memory);
    it returns events collected from aggregates during the transaction.
    """

    def __init__(self) -> None:
        self._users = FakeUserRepository()
        self._enrollments = FakeEnrollmentRepository()
        self._study_sessions = FakeStudySessionRepository()
        self._attempts = FakeAttemptRepository()
        self._question_instances = FakeQuestionInstanceRepository()
        self._mastery_scores = FakeMasteryScoreRepository()
        self._reviews = FakeReviewRepository()
        self._algorithm_versions = FakeAlgorithmVersionRepository()
        self._recommendations = FakeRecommendationRepository()
        self._streaks = FakeStreakRepository()
        self._committed = False
        self._rolled_back = False

    async def __aenter__(self) -> FakeUnitOfWork:
        self._committed = False
        self._rolled_back = False
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object | None) -> None:
        if exc_type is not None:
            self._rolled_back = True
        elif not self._committed:
            # Auto-commit if no exception and no explicit commit
            pass

    async def commit(self) -> list[DomainEvent]:
        self._committed = True
        return []  # Events are collected by handlers, not by the UoW in this fake

    async def rollback(self) -> None:
        self._rolled_back = True

    # Repository access
    @property
    def users(self) -> Any:
        return self._users

    @property
    def enrollments(self) -> Any:
        return self._enrollments

    @property
    def study_sessions(self) -> Any:
        return self._study_sessions

    @property
    def attempts(self) -> Any:
        return self._attempts

    @property
    def question_instances(self) -> Any:
        return self._question_instances

    @property
    def mastery_scores(self) -> Any:
        return self._mastery_scores

    @property
    def reviews(self) -> Any:
        return self._reviews

    @property
    def algorithm_versions(self) -> Any:
        return self._algorithm_versions

    @property
    def recommendations(self) -> Any:
        return self._recommendations

    @property
    def streaks(self) -> Any:
        return self._streaks

    # Stub properties for remaining repositories
    @property
    def subjects(self) -> Any:
        return _NullRepository()

    @property
    def concepts(self) -> Any:
        return _NullRepository()

    @property
    def question_templates(self) -> Any:
        return _NullRepository()

    @property
    def content_packs(self) -> Any:
        return _NullRepository()

    @property
    def content_versions(self) -> Any:
        return _NullRepository()

    @property
    def achievements(self) -> Any:
        return _NullRepository()

    @property
    def learning_goals(self) -> Any:
        return _NullRepository()

    @property
    def subscriptions(self) -> Any:
        return _NullRepository()

    @property
    def billing_plans(self) -> Any:
        return _NullRepository()

    @property
    def invoices(self) -> Any:
        return _NullRepository()

    @property
    def notifications(self) -> Any:
        return _NullRepository()

    @property
    def feature_flags(self) -> Any:
        return _NullRepository()

    @property
    def audit_logs(self) -> Any:
        return _NullRepository()

    @property
    def organizations(self) -> Any:
        return _NullRepository()

    @property
    def scheduling_configs(self) -> Any:
        return _NullRepository()

    @property
    def daily_queues(self) -> Any:
        return _NullRepository()


class _NullRepository:
    """Null repository for contexts not under test."""

    async def get_by_id(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def add(self, *args: Any, **kwargs: Any) -> Any:
        return args[0] if args else None

    async def save(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def list_by_user(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []

    async def get_by_user_and_subject(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def get_active_by_enrollment(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def list_by_enrollment(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []

    async def list_weak_by_enrollment(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []

    async def get_by_enrollment_and_concept(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def get_active(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def list_all(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []
