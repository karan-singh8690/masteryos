"""ORM models for the Study Materials context.

Maps to the `content` PostgreSQL schema.
Tables: study_materials, study_material_progress.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, LargeBinary, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index

from app.infrastructure.database.orm.base import Base, TimestampMixin


class StudyMaterialModel(TimestampMixin, Base):
    """ORM model for content.study_materials — uploaded PDF files.

    PDFs are stored as binary blobs (file_data) — no filesystem needed.
    Pages are rendered on-the-fly with watermarks when requested.
    View-only: no download endpoint exists.
    """

    __tablename__ = "study_materials"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="chk_materials_status"),
        Index("idx_materials_subject", "subject_id"),
        Index("idx_materials_status", "status"),
        {"schema": "content"},
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    concept_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    exam_name: Mapped[str | None] = mapped_column(String(50), nullable=True)  # JEE, GATE, etc.
    exam_year: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 2023, 2024
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")  # en, hi
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published")
    # PDF file stored as binary blob
    file_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Access control
    is_premium: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    coin_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0 = free
    # Metadata
    uploaded_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # ["formulas", "ncert", "pyq"]
    material_type: Mapped[str] = mapped_column(String(30), nullable=False, default="pdf")
    # e.g., "pdf", "notes", "formula_sheet", "pyq_paper", "reference"


class StudyMaterialProgressModel(TimestampMixin, Base):
    """ORM model for content.study_material_progress — per-user reading tracking.

    Tracks which page the user is on, total pages read, and time spent.
    """

    __tablename__ = "study_material_progress"
    __table_args__ = (
        Index("idx_material_progress_user", "user_id", "material_id", unique=True),
        {"schema": "content"},
    )

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    material_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.study_materials.id", ondelete="CASCADE"), nullable=False)
    current_page: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    pages_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_read_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class MaterialConceptLinkModel(Base):
    """ORM model for content.material_concept_links — links PDFs to concepts.

    If is_prerequisite=True, the learner must read at least min_pages_read
    pages of the material before the queue generator serves questions for
    that concept.
    """

    __tablename__ = "material_concept_links"
    __table_args__ = (
        Index("idx_mat_concept_link_material", "material_id"),
        Index("idx_mat_concept_link_concept", "concept_id"),
        {"schema": "content"},
    )

    material_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.study_materials.id", ondelete="CASCADE"), nullable=False)
    concept_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    is_prerequisite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    min_pages_read: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reading_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class MaterialUnlockModel(Base):
    """ORM model for content.material_unlocks — tracks premium material access.

    A user unlocks a premium material by:
    1. Paying coins (deducted from UserCoinModel)
    2. Having an active Pro/Coaching subscription (auto-unlocked)

    Once unlocked, the user can view all pages of the material.
    """

    __tablename__ = "material_unlocks"
    __table_args__ = (
        Index("idx_mat_unlocks_user", "user_id", "material_id", unique=True),
        {"schema": "content"},
    )

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    material_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("content.study_materials.id", ondelete="CASCADE"), nullable=False)
    unlock_method: Mapped[str] = mapped_column(String(20), nullable=False)  # "coins", "subscription", "admin", "free"
    coins_spent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
