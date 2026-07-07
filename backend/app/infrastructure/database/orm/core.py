"""ORM models for the Learning, Assessment, and Mastery contexts.

Maps to the `learning`, `assessment`, and `mastery` PostgreSQL schemas.
These are the core tables for the learning loop.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer,
    String, Text, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import Index, UniqueConstraint

from app.infrastructure.database.orm.base import Base, TimestampMixin


# ============================================================
# Learning Context
# ============================================================


class LearnerEnrollmentModel(Base):
    """ORM model for learning.learner_enrollments."""

    __tablename__ = "learner_enrollments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_onboarding', 'active', 'dormant', 'unenrolled', 'anonymized')",
            name="chk_learner_enrollments_status",
        ),
        Index(
            "idx_enrollments_user_subject",
            "user_id", "subject_id",
            unique=True,
            postgresql_where=text("status <> 'unenrolled'"),
        ),
        {"schema": "learning"},
    )

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    learning_path_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_onboarding")
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unenrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Phase 1 Indian localization: exam date for countdown + proximity scheduling
    target_exam_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_exam_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Phase 1: negative marking mode (e.g., -0.25 for -1/4 marking)
    negative_marking_factor: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class StudySessionModel(Base):
    """ORM model for learning.study_sessions."""

    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint("intent IN ('drill', 'diagnostic', 'review', 'mixed')", name="chk_study_sessions_intent"),
        CheckConstraint("status IN ('active', 'paused', 'ended', 'abandoned')", name="chk_study_sessions_status"),
        Index("idx_study_sessions_enrollment_active", "learner_enrollment_id",
              postgresql_where=text("status IN ('active', 'paused')")),
        {"schema": "learning"},
    )

    learner_enrollment_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    learning_session_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    intent: Mapped[str] = mapped_column(String(20), nullable=False, default="mixed")
    target_question_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# ============================================================
# Assessment Context
# ============================================================


class QuestionInstanceModel(TimestampMixin, Base):
    """ORM model for assessment.question_instances."""

    __tablename__ = "question_instances"
    __table_args__ = (
        CheckConstraint("status IN ('served', 'answered', 'abandoned')", name="chk_question_instances_status"),
        Index("idx_question_instances_enrollment_served", "learner_enrollment_id", "served_at"),
        {"schema": "assessment"},
    )

    template_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    content_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    learner_enrollment_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    study_session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    parameter_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    parameter_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rendered_prompt: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rendered_choices: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    correct_answer: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    distractors_with_tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    served_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="served")
    abandoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AttemptModel(TimestampMixin, Base):
    """ORM model for assessment.attempts — the data moat (append-only).

    This table is NEVER updated or deleted. Corrections are made by
    appending compensating attempts.
    """

    __tablename__ = "attempts"
    __table_args__ = (
        CheckConstraint("scoring_outcome IN ('correct', 'incorrect', 'partial')", name="chk_attempts_outcome"),
        CheckConstraint("attempt_intent IN ('practice', 'review', 'diagnostic')", name="chk_attempts_intent"),
        CheckConstraint(
            "(scoring_outcome = 'partial' AND partial_credit IS NOT NULL) OR "
            "(scoring_outcome <> 'partial' AND partial_credit IS NULL)",
            name="chk_attempts_partial_credit",
        ),
        CheckConstraint("partial_credit IS NULL OR (partial_credit >= 0.0 AND partial_credit <= 1.0)", name="chk_attempts_credit_range"),
        CheckConstraint("time_to_answer_ms >= 0", name="chk_attempts_time_nonneg"),
        Index("idx_attempts_enrollment_created", "learner_enrollment_id", "created_at"),
        Index("idx_attempts_template_version", "template_version_id"),
        Index("idx_attempts_content_version", "content_version_id"),
        Index("idx_attempts_algorithm_version", "algorithm_version_id"),
        Index("idx_attempts_study_session", "study_session_id"),
        {"schema": "assessment"},
    )

    question_instance_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    learner_enrollment_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    study_session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    content_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    template_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    algorithm_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    scoring_outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    partial_credit: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_to_answer_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    hint_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hint_tiers_used: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    misconception_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    attempt_intent: Mapped[str] = mapped_column(String(20), nullable=False, default="practice")
    # Phase 1 Indian localization: error type tracking (silly mistake tracker)
    error_type: Mapped[str | None] = mapped_column(String(30), nullable=True)  # concept_gap, calculation_error, misread, time_pressure
    # Phase 1: marks gained/lost for negative marking
    marks_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class AnswerModel(TimestampMixin, Base):
    """ORM model for assessment.answers."""

    __tablename__ = "answers"
    __table_args__ = (
        CheckConstraint("answer_type IN ('multiple_choice', 'code', 'free_response')", name="chk_answers_type"),
        {"schema": "assessment"},
    )

    attempt_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, unique=True)
    question_instance_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    answer_type: Mapped[str] = mapped_column(String(30), nullable=False)
    submitted_answer: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    revision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ============================================================
# Mastery Context
# ============================================================


class MasteryScoreModel(Base):
    """ORM model for mastery.mastery_scores."""

    __tablename__ = "mastery_scores"
    __table_args__ = (
        CheckConstraint("memory_score >= 0.0 AND memory_score <= 1.0", name="chk_mastery_memory_range"),
        CheckConstraint("durable_mastery_score >= 0.0 AND durable_mastery_score <= 1.0", name="chk_mastery_durable_range"),
        CheckConstraint("mastery_score_combined >= 0.0 AND mastery_score_combined <= 1.0", name="chk_mastery_combined_range"),
        CheckConstraint("confidence_interval >= 0.0 AND confidence_interval <= 1.0", name="chk_mastery_confidence_range"),
        CheckConstraint("concept_state IN ('unseen', 'novice', 'developing', 'proficient', 'mastered', 'decayed')", name="chk_mastery_state"),
        CheckConstraint("weakness_severity IN ('none', 'mild', 'moderate', 'severe')", name="chk_mastery_weakness"),
        CheckConstraint("version > 0", name="chk_mastery_version_positive"),
        Index("idx_mastery_enrollment_concept", "learner_enrollment_id", "concept_id", unique=True),
        Index("idx_mastery_concept", "concept_id"),
        Index("idx_mastery_algorithm", "algorithm_version_id"),
        {"schema": "mastery"},
    )

    learner_enrollment_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    concept_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    algorithm_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    memory_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    durable_mastery_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mastery_score_combined: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_interval: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    concept_state: Mapped[str] = mapped_column(String(20), nullable=False, default="unseen")
    weakness_severity: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ReviewModel(Base):
    """ORM model for mastery.reviews."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("priority IN ('low', 'medium', 'high')", name="chk_reviews_priority"),
        Index("idx_reviews_enrollment_concept", "learner_enrollment_id", "concept_id", unique=True),
        {"schema": "mastery"},
    )

    learner_enrollment_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    concept_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    algorithm_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    scheduled_by_attempt_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    review_interval: Mapped[str] = mapped_column(Text, nullable=False)  # ISO 8601 duration
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_review_outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)


class AlgorithmVersionModel(Base):
    """ORM model for mastery.algorithm_versions."""

    __tablename__ = "algorithm_versions"
    __table_args__ = (
        CheckConstraint("version_number >= 1", name="chk_algo_version_positive"),
        Index("idx_algo_active", "is_active", unique=True, postgresql_where=text("is_active = true")),
        {"schema": "mastery"},
    )

    version_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ============================================================
# Infrastructure Context
# ============================================================


class OutboxEventModel(TimestampMixin, Base):
    """ORM model for infrastructure.outbox_events.

    The outbox table stores domain events in the same transaction as
    the originating write. A background dispatcher polls the outbox
    and delivers events to subscribers.
    """

    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'dispatched', 'dead_lettered')", name="chk_outbox_status"),
        Index("idx_outbox_pending", "status", "created_at", postgresql_where=text("status = 'pending'")),
        Index("idx_outbox_aggregate", "aggregate_id"),
        Index("idx_outbox_event_type", "event_type", "created_at"),
        {"schema": "infrastructure"},
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_schema_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1")
    originating_schema: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    dispatch_attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_dispatch_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Task 017: visibility timeout + retry tracking
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    leased_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


# ============================================================
# Phase 3 Indian Localization: Mock Test Mode
# ============================================================


class MockTestModel(TimestampMixin, Base):
    """ORM model for assessment.mock_tests — exam-realistic timed sessions.

    Mock tests simulate actual exam conditions:
    - Fixed time limit (e.g., 180 min for JEE)
    - Sectional time limits (e.g., 60 min per section for CAT)
    - Negative marking
    - Question count matches real exam
    """

    __tablename__ = "mock_tests"
    __table_args__ = (
        CheckConstraint("status IN ('not_started', 'in_progress', 'completed', 'abandoned')", name="chk_mock_status"),
        {"schema": "assessment"},
    )

    learner_enrollment_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    study_session_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    exam_name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "JEE Main Mock 1"
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    time_limit_minutes: Mapped[int] = mapped_column(Integer, nullable=False)  # e.g., 180
    negative_marking_factor: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Results (filled when completed)
    total_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_wrong: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_unattempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    marks_scored: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Sectional results (JSON: [{"section": "Physics", "attempted": 25, "correct": 20, ...}])
    sectional_results: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


# ============================================================
# Phase 3 Indian Localization: Community Doubt Solving
# ============================================================


class DoubtModel(TimestampMixin, Base):
    """ORM model for community.doubts — student-posted questions.

    Students post doubts (screenshots, text) about questions they got wrong.
    Community members answer, earn coins, and top answers become permanent content.
    """

    __tablename__ = "doubts"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'answered', 'verified', 'closed')", name="chk_doubt_status"),
        Index("idx_doubts_concept", "concept_id"),
        Index("idx_doubts_status", "status"),
        {"schema": "community"},
    )

    posted_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    question_instance_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    concept_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    screenshot_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")  # en, hi, ta, etc.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    upvotes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DoubtAnswerModel(TimestampMixin, Base):
    """ORM model for community.doubt_answers — answers to student doubts."""

    __tablename__ = "doubt_answers"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'verified', 'rejected')", name="chk_danswer_status"),
        Index("idx_doubt_answers_doubt", "doubt_id"),
        {"schema": "community"},
    )

    doubt_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    answered_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    upvotes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")


class UserCoinModel(TimestampMixin, Base):
    """ORM model for community.user_coins — gamified coin system.

    Coins are earned by answering doubts, achieving streaks, etc.
    Coins are spent by posting doubts or unlocking premium content.
    """

    __tablename__ = "user_coins"
    __table_args__ = (
        Index("idx_user_coins_user", "user_id", unique=True),
        {"schema": "community"},
    )

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, unique=True)
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=100)  # Start with 100 coins
    total_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    total_spent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# ============================================================
# Phase 4 Indian Localization: Leaderboards + Peer Comparison
# ============================================================


class LeaderboardModel(TimestampMixin, Base):
    """ORM model for analytics.leaderboards — daily/weekly/all-time rankings.

    Updated periodically by a background worker that aggregates
    user performance into ranked entries.
    """

    __tablename__ = "leaderboards"
    __table_args__ = (
        CheckConstraint("period IN ('daily', 'weekly', 'monthly', 'all_time')", name="chk_leaderboard_period"),
        Index("idx_leaderboard_period_score", "period", "score"),
        {"schema": "analytics"},
    )

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # daily, weekly, monthly, all_time
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # performance_index * 100
    total_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_speed_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subject_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)  # null = all subjects


# ============================================================
# Phase 4 Indian Localization: Question Packs (Delta Sync)
# ============================================================


class QuestionPackModel(TimestampMixin, Base):
    """ORM model for content.question_packs — pre-downloadable offline packs.

    Each pack contains a set of questions for a subject + exam combination.
    Users download packs for offline study, then sync results when online.
    """

    __tablename__ = "question_packs"
    __table_args__ = (
        UniqueConstraint("subject_id", "exam_name", "version", name="uq_qpack_version"),
        {"schema": "content"},
    )

    subject_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    exam_name: Mapped[str | None] = mapped_column(String(50), nullable=True)  # null = general
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pack_size_kb: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # approximate size
    # The actual question data (JSON blob — can be large)
    pack_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, default="")  # for delta sync verification
