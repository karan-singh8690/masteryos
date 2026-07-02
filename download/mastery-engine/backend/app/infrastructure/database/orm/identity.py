"""ORM models for the Identity context.

Maps to the `identity` PostgreSQL schema.
Tables: users, user_profiles, user_credentials, sessions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import Index

from app.infrastructure.database.orm.base import Base


class UserModel(Base):
    """ORM model for identity.users."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_verification', 'active', 'suspended', 'deactivated', 'pending_deletion', 'anonymized')",
            name="chk_users_status",
        ),
        Index("idx_users_email_active", "email", unique=True, postgresql_where=text("deleted_at IS NULL")),
        {"schema": "identity"},
    )

    email: Mapped[str] = mapped_column(Text, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending_verification")
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_secret_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    profile: Mapped[UserProfileModel | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    credentials: Mapped[list[UserCredentialModel]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[SessionModel]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserProfileModel(Base):
    """ORM model for identity.user_profiles."""

    __tablename__ = "user_profiles"
    __table_args__ = (
        {"schema": "identity"},
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="UTC")
    locale: Mapped[str] = mapped_column(Text, nullable=False, default="en-US")
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    user: Mapped[UserModel] = relationship(back_populates="profile")


class UserCredentialModel(Base):
    """ORM model for identity.user_credentials."""

    __tablename__ = "user_credentials"
    __table_args__ = (
        CheckConstraint(
            "credential_type IN ('password', 'oauth')",
            name="chk_user_credentials_type",
        ),
        CheckConstraint(
            "(credential_type = 'password' AND password_hash IS NOT NULL) OR "
            "(credential_type = 'oauth' AND provider IS NOT NULL AND provider_user_id IS NOT NULL)",
            name="chk_user_credentials_fields",
        ),
        Index(
            "idx_user_credentials_oauth",
            "provider", "provider_user_id",
            unique=True,
            postgresql_where=text("credential_type = 'oauth'"),
        ),
        {"schema": "identity"},
    )

    from sqlalchemy.dialects.postgresql import UUID as PGUUID
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False
    )
    credential_type: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[UserModel] = relationship(back_populates="credentials")


class SessionModel(Base):
    """ORM model for identity.sessions."""

    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "(revoked_at IS NULL) OR (revoke_reason IS NOT NULL)",
            name="chk_sessions_revoke_reason",
        ),
        Index("idx_sessions_user_active", "user_id", postgresql_where=text("revoked_at IS NULL")),
        {"schema": "identity"},
    )

    from sqlalchemy.dialects.postgresql import UUID as PGUUID
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    token_family_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    device_fingerprint: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
