"""SQLAlchemy ORM base model with common columns and utilities.

All ORM models inherit from Base. The ORM models are persistence models
only — they are NOT domain entities. Mappers convert between ORM models
and domain entities.

Per Task 004:
- All primary keys are UUID (v7 in production, v4 for development).
- All timestamps are timestamptz.
- Soft delete via deleted_at where applicable.
- Append-only enforcement via triggers + REVOKE for certain tables.
- JSONB for semi-structured data.
- text + CHECK constraints instead of ENUM types.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models.

    Provides:
    - id: UUID primary key (default: uuid4; production uses uuid7 via the ID service)
    - created_at: timestamptz, server default now()
    - updated_at: timestamptz, server default now(), updated on each UPDATE via trigger
    - deleted_at: timestamptz, nullable (soft delete)
    """

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )


class TimestampMixin:
    """Mixin for tables that only need created_at (no updated_at).

    Used by append-only tables (attempts, audit_logs, outbox_events)
    where rows are never updated.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


def utcnow() -> datetime:
    """Return current UTC time. Used as a default factory."""
    return datetime.now(timezone.utc)


def jsonb_default() -> dict[str, Any]:
    """Default empty JSONB object."""
    return {}
