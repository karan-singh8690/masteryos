"""ORM models for the Content context.

Maps to the `content` PostgreSQL schema.
Tables: subjects, concepts, concept_dependencies, learning_objectives,
misconceptions, question_templates, template_versions, template_concepts,
template_objectives, distractors, hints, explanations, content_versions,
content_packs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer,
    String, Text, text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import Index

from app.infrastructure.database.orm.base import Base


class SubjectModel(Base):
    __tablename__ = "subjects"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'deprecated')", name="chk_subjects_status"),
        UniqueConstraint("code", name="uq_subjects_code"),
        UniqueConstraint("slug", name="uq_subjects_slug"),
        {"schema": "content"},
    )

    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    default_learning_path_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    concepts: Mapped[list[ConceptModel]] = relationship(back_populates="subject")
    templates: Mapped[list[QuestionTemplateModel]] = relationship(back_populates="subject")


class ConceptModel(Base):
    __tablename__ = "concepts"
    __table_args__ = (
        CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="chk_concepts_difficulty"),
        CheckConstraint("importance IN ('low', 'medium', 'high')", name="chk_concepts_importance"),
        CheckConstraint("status IN ('draft', 'published', 'deprecated')", name="chk_concepts_status"),
        UniqueConstraint("subject_id", "slug", name="uq_concepts_subject_slug"),
        {"schema": "content"},
    )

    subject_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.subjects.id"), nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    importance: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    current_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subject: Mapped[SubjectModel] = relationship(back_populates="concepts")
    objectives: Mapped[list[LearningObjectiveModel]] = relationship(back_populates="concept", cascade="all, delete-orphan")
    misconceptions: Mapped[list[MisconceptionModel]] = relationship(back_populates="concept", cascade="all, delete-orphan")


class LearningObjectiveModel(Base):
    __tablename__ = "learning_objectives"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'deprecated')", name="chk_objectives_status"),
        {"schema": "content"},
    )

    concept_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.concepts.id", ondelete="CASCADE"), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    concept: Mapped[ConceptModel] = relationship(back_populates="objectives")


class MisconceptionModel(Base):
    __tablename__ = "misconceptions"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'deprecated')", name="chk_misconceptions_status"),
        {"schema": "content"},
    )

    concept_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.concepts.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    concept: Mapped[ConceptModel] = relationship(back_populates="misconceptions")


class QuestionTemplateModel(Base):
    __tablename__ = "question_templates"
    __table_args__ = (
        CheckConstraint("question_type IN ('multiple_choice', 'code_execution', 'free_response')", name="chk_qt_type"),
        CheckConstraint("status IN ('draft', 'in_review', 'published', 'deprecated')", name="chk_qt_status"),
        UniqueConstraint("subject_id", "code", name="uq_qt_subject_code"),
        {"schema": "content"},
    )

    subject_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.subjects.id"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    current_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Phase 1 Indian localization: PYQ (Previous Year Question) tagging
    pyq_exam: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., "JEE", "GATE", "NEET"
    pyq_year: Mapped[int | None] = mapped_column(Integer, nullable=True)  # e.g., 2023
    pyq_source: Mapped[str | None] = mapped_column(String(200), nullable=True)  # e.g., "JEE Main 2023 Shift 1"

    subject: Mapped[SubjectModel] = relationship(back_populates="templates")
    versions: Mapped[list[TemplateVersionModel]] = relationship(back_populates="template", cascade="all, delete-orphan")


class TemplateVersionModel(Base):
    """Immutable snapshot of a QuestionTemplate at a moment in time."""
    __tablename__ = "template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version_number", name="uq_tv_template_version"),
        CheckConstraint("difficulty_estimate IN ('easy', 'medium', 'hard')", name="chk_tv_difficulty"),
        CheckConstraint("discrimination_estimate >= 0.0 AND discrimination_estimate <= 1.0", name="chk_tv_discrimination"),
        {"schema": "content"},
    )

    template_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.question_templates.id"), nullable=False)
    content_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parameter_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    prompt_template: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    correct_answer_generator: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    distractor_generator: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    explanation_template: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    hint_tiers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    difficulty_estimate: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    discrimination_estimate: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    # Phase 3 Indian localization: Hindi language support
    prompt_template_hindi: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    explanation_template_hindi: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    distractor_generator_hindi: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    template: Mapped[QuestionTemplateModel] = relationship(back_populates="versions")
    concepts: Mapped[list[TemplateConceptModel]] = relationship(back_populates="template_version", cascade="all, delete-orphan")
    explanations: Mapped[list[ExplanationModel]] = relationship(back_populates="template_version", cascade="all, delete-orphan")


class TemplateConceptModel(Base):
    """Links a TemplateVersion to Concepts (many-to-many)."""
    __tablename__ = "template_concepts"
    __table_args__ = (
        UniqueConstraint("template_version_id", "concept_id", name="uq_tc_pair"),
        {"schema": "content"},
    )

    template_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.template_versions.id", ondelete="CASCADE"), nullable=False)
    concept_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.concepts.id"), nullable=False)

    template_version: Mapped[TemplateVersionModel] = relationship(back_populates="concepts")


class ExplanationModel(Base):
    """Explanation variants for a TemplateVersion."""
    __tablename__ = "explanations"
    __table_args__ = (
        UniqueConstraint("template_version_id", "outcome_key", name="uq_explanations_pair"),
        {"schema": "content"},
    )

    template_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.template_versions.id", ondelete="CASCADE"), nullable=False)
    outcome_key: Mapped[str] = mapped_column(Text, nullable=False)  # 'correct', 'incorrect', 'hint', 'interview', 'beginner'
    misconception_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    template_version: Mapped[TemplateVersionModel] = relationship(back_populates="explanations")


class ContentVersionModel(Base):
    """Immutable snapshot of a subject's content at publish time."""
    __tablename__ = "content_versions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'deprecated')", name="chk_cv_status"),
        UniqueConstraint("subject_id", "version_number", name="uq_cv_subject_version"),
        {"schema": "content"},
    )

    subject_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ContentPackModel(Base):
    """Atomic publishing unit."""
    __tablename__ = "content_packs"
    __table_args__ = (
        {"schema": "content"},
    )

    content_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    author_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    artifact_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ============================================================
# Phase 2 Indian Localization: Concept Dependency Graph
# ============================================================


class ConceptDependencyModel(Base):
    """ORM model for content.concept_dependencies — prerequisite chain (DAG).

    If concept A requires concept B, the learner must achieve minimum mastery
    on B before the queue generator serves A's questions.
    """

    __tablename__ = "concept_dependencies"
    __table_args__ = (
        UniqueConstraint("concept_id", "prerequisite_concept_id", name="uq_concept_deps"),
        CheckConstraint("concept_id <> prerequisite_concept_id", name="chk_no_self_dependency"),
        CheckConstraint("min_mastery >= 0.0 AND min_mastery <= 1.0", name="chk_dep_min_mastery"),
        {"schema": "content"},
    )

    concept_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.concepts.id", ondelete="CASCADE"), nullable=False)
    prerequisite_concept_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.concepts.id", ondelete="CASCADE"), nullable=False)
    min_mastery: Mapped[float] = mapped_column(Float, nullable=False, default=0.3, description="Minimum mastery required on prerequisite before serving this concept")


# ============================================================
# Phase 2 Indian Localization: Exam Weightage Clusters
# ============================================================


class ExamWeightageModel(Base):
    """ORM model for content.exam_weightage — maps concepts to exam weightage.

    Example: In JEE Physics, Mechanics has 25% weightage.
    The weighted readiness dashboard uses this to prioritize high-weightage topics.
    """

    __tablename__ = "exam_weightage"
    __table_args__ = (
        UniqueConstraint("exam_name", "concept_id", name="uq_exam_concept_weightage"),
        CheckConstraint("weightage >= 0.0 AND weightage <= 1.0", name="chk_weightage_range"),
        {"schema": "content"},
    )

    exam_name: Mapped[str] = mapped_column(String(50), nullable=False, description="e.g., 'JEE', 'GATE', 'NEET'")
    concept_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.concepts.id", ondelete="CASCADE"), nullable=False)
    weightage: Mapped[float] = mapped_column(Float, nullable=False, description="0.0-1.0, e.g., 0.25 for 25% of exam marks")
    topic_cluster: Mapped[str | None] = mapped_column(String(100), nullable=True, description="e.g., 'Mechanics', 'Algorithms'")
