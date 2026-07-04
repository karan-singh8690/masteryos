"""ORM models for the Closed Beta Operations Platform (Task 026).

Maps the new tables added in 05-beta-ops-tables.sql:
- identity.beta_feedback_votes       — votes on feedback items
- identity.beta_feedback_meta        — priority + roadmap linkage
- administration.release_notes       — versioned release notes
- administration.release_stages      — canary/staged/live/rolled_back tracking
- analytics.experiments              — A/B experiment definitions
- analytics.experiment_assignments   — sticky user→variant assignments
- analytics.experiment_results       — aggregated outcomes per variant
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index

from app.infrastructure.database.orm.base import Base, TimestampMixin


# ============================================================
# Part 4: Feedback votes + meta
# ============================================================


class BetaFeedbackVoteModel(Base):
    """ORM model for identity.beta_feedback_votes."""

    __tablename__ = "beta_feedback_votes"
    __table_args__ = (
        Index("idx_beta_feedback_votes_unique", "feedback_id", "user_id", unique=True),
        Index("idx_beta_feedback_votes_feedback", "feedback_id"),
        Index("idx_beta_feedback_votes_user", "user_id"),
        {"schema": "identity"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=text("gen_random_uuid()"))
    feedback_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.beta_feedback.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    vote: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=text("now()")
    )


class BetaFeedbackMetaModel(Base):
    """ORM model for identity.beta_feedback_meta."""

    __tablename__ = "beta_feedback_meta"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent', 'blocker')",
            name="chk_beta_feedback_meta_priority",
        ),
        CheckConstraint(
            "roadmap_status IN ('untriaged', 'planned', 'in_progress', 'shipped', 'wont_fix', 'duplicate')",
            name="chk_beta_feedback_meta_roadmap",
        ),
        Index("idx_beta_feedback_meta_priority", "priority"),
        Index("idx_beta_feedback_meta_roadmap", "roadmap_status"),
        {"schema": "identity"},
    )

    feedback_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.beta_feedback.id", ondelete="CASCADE"),
        primary_key=True,
    )
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    roadmap_status: Mapped[str] = mapped_column(String(20), nullable=False, default="untriaged")
    roadmap_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    duplicate_of: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.beta_feedback.id", ondelete="SET NULL"),
        nullable=True,
    )
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    assigned_to: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=text("now()")
    )
    updated_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


# ============================================================
# Part 8: Release Management
# ============================================================


class ReleaseNoteModel(TimestampMixin, Base):
    """ORM model for administration.release_notes."""

    __tablename__ = "release_notes"
    __table_args__ = (
        CheckConstraint(
            "release_type IN ('major', 'minor', 'patch', 'hotfix', 'beta')",
            name="chk_release_notes_type",
        ),
        Index(
            "idx_release_notes_published",
            "published_at",
            postgresql_where=text("published_at IS NOT NULL"),
        ),
        Index("idx_release_notes_type", "release_type"),
        {"schema": "administration"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=text("gen_random_uuid()"))
    version: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    release_type: Mapped[str] = mapped_column(String(20), nullable=False, default="patch")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    features: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    bug_fixes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    breaking_changes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    known_issues: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    feature_freeze: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class ReleaseStageModel(Base):
    """ORM model for administration.release_stages."""

    __tablename__ = "release_stages"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('planned', 'building', 'canary', 'staged', 'live', 'rolled_back', 'abandoned')",
            name="chk_release_stages_stage",
        ),
        Index("idx_release_stages_release", "release_note_id"),
        Index("idx_release_stages_stage", "stage"),
        {"schema": "administration"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=text("gen_random_uuid()"))
    release_note_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("administration.release_notes.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(String(20), nullable=False)
    rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


# ============================================================
# Part 10: Experiment Platform
# ============================================================


class ExperimentModel(TimestampMixin, Base):
    """ORM model for analytics.experiments."""

    __tablename__ = "experiments"
    __table_args__ = (
        CheckConstraint(
            "experiment_type IN ('ab', 'feature_rollout', 'recommendation', 'queue', 'explanation', 'ai_vs_rule')",
            name="chk_experiments_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'running', 'completed', 'stopped')",
            name="chk_experiments_status",
        ),
        CheckConstraint(
            "rollout_percentage BETWEEN 0 AND 100",
            name="chk_experiments_rollout",
        ),
        Index("idx_experiments_status", "status"),
        {"schema": "analytics"},
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    experiment_type: Mapped[str] = mapped_column(String(30), nullable=False, default="ab")
    variant_a: Mapped[str] = mapped_column(Text, nullable=False)
    variant_b: Mapped[str] = mapped_column(Text, nullable=False)
    rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    target_metric: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    winner: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )


class ExperimentAssignmentModel(Base):
    """ORM model for analytics.experiment_assignments."""

    __tablename__ = "experiment_assignments"
    __table_args__ = (
        Index(
            "idx_experiment_assignments_unique",
            "experiment_id",
            "user_id",
            unique=True,
        ),
        Index("idx_experiment_assignments_exp", "experiment_id"),
        Index("idx_experiment_assignments_user", "user_id"),
        {"schema": "analytics"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=text("gen_random_uuid()"))
    experiment_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("analytics.experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    variant: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=text("now()")
    )


class ExperimentResultModel(Base):
    """ORM model for analytics.experiment_results."""

    __tablename__ = "experiment_results"
    __table_args__ = (
        Index("idx_experiment_results_exp", "experiment_id", "variant"),
        {"schema": "analytics"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=text("gen_random_uuid()"))
    experiment_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("analytics.experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    variant: Mapped[str] = mapped_column(Text, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metric_value: Mapped[float | None] = mapped_column(nullable=True)
    metric_std_error: Mapped[float | None] = mapped_column(nullable=True)
    conversion_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=text("now()")
    )


__all__ = [
    "BetaFeedbackVoteModel",
    "BetaFeedbackMetaModel",
    "ReleaseNoteModel",
    "ReleaseStageModel",
    "ExperimentModel",
    "ExperimentAssignmentModel",
    "ExperimentResultModel",
]
