"""ORM models for Closed Beta tables.

Maps to the `identity` and `analytics` PostgreSQL schemas.
Tables: beta_invites, beta_feedback, beta_events.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index

from app.infrastructure.database.orm.base import Base, TimestampMixin


class BetaInviteModel(Base):
    """ORM model for identity.beta_invites."""

    __tablename__ = "beta_invites"
    __table_args__ = (
        Index("idx_beta_invites_token", "invite_token", unique=True),
        Index("idx_beta_invites_email", "email"),
        Index("idx_beta_invites_unused", "used_at", postgresql_where=text("used_at IS NULL")),
        {"schema": "identity"},
    )

    email: Mapped[str] = mapped_column(Text, nullable=False)
    invite_token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class BetaFeedbackModel(Base, TimestampMixin):
    """ORM model for identity.beta_feedback."""

    __tablename__ = "beta_feedback"
    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="chk_beta_feedback_rating",
        ),
        CheckConstraint(
            "category IN ('bug', 'feature_request', 'ui_ux', 'content', 'performance', 'other')",
            name="chk_beta_feedback_category",
        ),
        CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved', 'closed')",
            name="chk_beta_feedback_status",
        ),
        Index("idx_beta_feedback_user", "user_id"),
        Index("idx_beta_feedback_status", "status"),
        Index("idx_beta_feedback_category", "category"),
        {"schema": "identity"},
    )

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    screenshot_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Auto-captured context
    correlation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    browser: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str | None] = mapped_column(Text, nullable=True)
    route: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class BetaEventModel(Base, TimestampMixin):
    """ORM model for analytics.beta_events."""

    __tablename__ = "beta_events"
    __table_args__ = (
        Index("idx_beta_events_type_created", "event_type", "created_at"),
        Index("idx_beta_events_user", "user_id"),
        Index("idx_beta_events_created", "created_at"),
        {"schema": "analytics"},
    )

    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)


__all__ = ["BetaInviteModel", "BetaFeedbackModel", "BetaEventModel"]
