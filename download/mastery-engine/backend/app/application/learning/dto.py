"""Learning context — DTOs for commands and queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import UUID


# ============================================================
# Command DTOs
# ============================================================


@dataclass(frozen=True)
class EnrollLearnerCommand:
    """Command: Enroll a user as a learner in a subject."""

    user_id: UUID
    subject_id: UUID
    learning_path_id: UUID | None = None


@dataclass(frozen=True)
class CompleteOnboardingCommand:
    """Command: Complete subject onboarding (after diagnostic)."""

    enrollment_id: UUID


@dataclass(frozen=True)
class UnenrollCommand:
    """Command: Unenroll from a subject."""

    enrollment_id: UUID


@dataclass(frozen=True)
class SetLearningGoalCommand:
    """Command: Set a learning goal."""

    enrollment_id: UUID
    goal_type: str
    target_date: date | None = None
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StartStudySessionCommand:
    """Command: Start a study session."""

    enrollment_id: UUID
    intent: str = "mixed"
    target_question_count: int | None = None


@dataclass(frozen=True)
class PauseStudySessionCommand:
    """Command: Pause a study session."""

    session_id: UUID


@dataclass(frozen=True)
class ResumeStudySessionCommand:
    """Command: Resume a paused study session."""

    session_id: UUID


@dataclass(frozen=True)
class EndStudySessionCommand:
    """Command: End a study session."""

    session_id: UUID


@dataclass(frozen=True)
class DismissRecommendationCommand:
    """Command: Dismiss a recommendation."""

    recommendation_id: UUID
    user_id: UUID


# ============================================================
# Response DTOs
# ============================================================


@dataclass(frozen=True)
class EnrollmentDTO:
    """Read model: a learner enrollment."""

    id: UUID
    user_id: UUID
    subject_id: UUID
    learning_path_id: UUID | None
    status: str
    enrolled_at: datetime
    onboarded_at: datetime | None
    last_active_at: datetime | None


@dataclass(frozen=True)
class StudySessionDTO:
    """Read model: a study session."""

    id: UUID
    learner_enrollment_id: UUID
    intent: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    question_count: int


@dataclass(frozen=True)
class SessionAnalyticsDTO:
    """Read model: session analytics (after end)."""

    study_session_id: UUID
    question_count: int
    duration_seconds: int


@dataclass(frozen=True)
class MasteryScoreDTO:
    """Read model: a mastery score."""

    concept_id: UUID
    memory_score: float
    durable_mastery_score: float
    mastery_score_combined: float
    concept_state: str
    weakness_severity: str
    evidence_count: int
    last_attempt_at: datetime | None


@dataclass(frozen=True)
class DashboardDTO:
    """Read model: the dashboard."""

    enrollment_id: UUID
    recommended_action: str
    current_streak: int
    weak_concepts: list[MasteryScoreDTO]


@dataclass(frozen=True)
class RecommendationDTO:
    """Read model: a recommendation."""

    id: UUID
    enrollment_id: UUID
    recommendation_type: str
    score: float
    status: str


@dataclass(frozen=True)
class AttemptResultDTO:
    """Response: the result of submitting an attempt."""

    attempt_id: UUID
    scoring_outcome: str
    explanation_content: str | None
    next_question_id: UUID | None
    updated_mastery: MasteryScoreDTO | None


@dataclass(frozen=True)
class AttemptDTO:
    """Read model: an attempt in history."""

    id: UUID
    scoring_outcome: str
    time_to_answer_ms: int
    hint_used: bool
    attempt_intent: str
    created_at: datetime
