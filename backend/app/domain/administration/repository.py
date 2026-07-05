"""Administration context — abstract repository interfaces.

This module defines the *contracts* for loading and persisting the
Administration-context aggregates and entities. Each interface is an
abstract base class — no implementation is provided here. Concrete
implementations live in the infrastructure layer.

Async contract:
- All methods are ``async`` to match the async SQLAlchemy pattern the
  rest of the backend uses.
- The application layer ``await``s repository calls inside an async
  unit-of-work.

Append-only contract:
- :class:`AuditLog` entries are append-only. The
  :class:`AuditLogRepository` exposes only :meth:`add` and
  :meth:`list_by_*` — there is no ``save`` or ``delete``. The storage
  layer must enforce this (e.g., deny UPDATE and DELETE permissions on
  the audit-log table).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.administration.audit_log import AuditLog
from app.domain.administration.feature_flag import FeatureFlag
from app.domain.administration.notification import Notification
from app.domain.administration.organization import Organization
from app.domain.shared.ids import (
    AuditLogId,
    FeatureFlagId,
    NotificationId,
    OrganizationId,
    UserId,
)
from app.domain.shared.kernel import EntityNotFound, NotificationChannel, NotificationStatus


# ============================================================
# AuditLog
# ============================================================


class AuditLogRepository(ABC):
    """Abstract repository for the :class:`AuditLog` entity (append-only).

    Implementations must:
    - Persist entries via :meth:`add` only. There is no ``save`` or
      ``delete`` — the storage layer must enforce append-only semantics
      (e.g., deny UPDATE and DELETE on the audit-log table).
    - Index entries by ``actor_user_id``, ``target_type`` +
      ``target_id``, ``action``, and ``created_at`` for fast querying.
    """

    @abstractmethod
    async def get_by_id(self, audit_log_id: AuditLogId) -> AuditLog | None:
        """Load an AuditLog entry by ID.

        Returns the :class:`AuditLog`, or ``None`` if no entry exists
        with that ID.
        """

    @abstractmethod
    async def add(self, entry: AuditLog) -> None:
        """Append a new AuditLog entry.

        Args:
            entry: The new :class:`AuditLog` entry to persist.

        Raises:
            DuplicateEntity: If an entry with the same ID already
                exists (extremely unlikely for UUIDs, but possible on
                replay).
        """

    @abstractmethod
    async def list_by_actor(
        self,
        actor_user_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[AuditLog]:
        """List audit entries by the actor who performed them.

        Ordered by ``created_at`` descending.
        """

    @abstractmethod
    async def list_by_target(
        self,
        target_type: str,
        target_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[AuditLog]:
        """List audit entries for a target entity.

        Ordered by ``created_at`` descending.
        """

    @abstractmethod
    async def list_by_action(
        self,
        action: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[AuditLog]:
        """List audit entries for a specific action code.

        Ordered by ``created_at`` descending.
        """

    @abstractmethod
    async def list_in_time_range(
        self,
        start: datetime,
        end: datetime,
        *,
        limit: int = 1000,
    ) -> Sequence[AuditLog]:
        """List audit entries within a time range (inclusive).

        Used by compliance export jobs. Ordered by ``created_at``
        ascending.
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, audit_log_id: AuditLogId) -> AuditLog:
        """Load an AuditLog by ID, raising :class:`EntityNotFound` if absent."""
        entry = await self.get_by_id(audit_log_id)
        if entry is None:
            raise EntityNotFound("AuditLog", audit_log_id)
        return entry


# ============================================================
# FeatureFlag
# ============================================================


class FeatureFlagRepository(ABC):
    """Abstract repository for the :class:`FeatureFlag` aggregate.

    Implementations must:
    - Load the :class:`FeatureFlag` or return ``None``.
    - Persist the full aggregate on :meth:`save`.
    - Enforce uniqueness of ``key`` at the storage layer.
    """

    @abstractmethod
    async def get_by_id(self, flag_id: FeatureFlagId) -> FeatureFlag | None:
        """Load a FeatureFlag by ID.

        Returns the :class:`FeatureFlag`, or ``None`` if no flag exists
        with that ID.
        """

    @abstractmethod
    async def get_by_key(self, key: str) -> FeatureFlag | None:
        """Load a FeatureFlag by its unique key.

        Args:
            key: The flag key (e.g., ``"new_dashboard.v2"``).

        Returns:
            The matching :class:`FeatureFlag`, or ``None`` if not
            found. Both active and retired flags are returned — the
            caller decides whether to use a retired flag's snapshot.
        """

    @abstractmethod
    async def list_active(self) -> Sequence[FeatureFlag]:
        """List all active (non-retired) FeatureFlags.

        Returns:
            A sequence of :class:`FeatureFlag` aggregates whose
            ``is_active`` flag is ``True``. Ordered by ``key``.
        """

    @abstractmethod
    async def add(self, flag: FeatureFlag) -> None:
        """Add a *new* FeatureFlag to the repository.

        Args:
            flag: The new :class:`FeatureFlag` to persist.

        Raises:
            DuplicateEntity: If a flag with the same ``key`` already
                exists.
        """

    @abstractmethod
    async def save(self, flag: FeatureFlag) -> None:
        """Persist changes to an *existing* FeatureFlag.

        Args:
            flag: The modified :class:`FeatureFlag` to persist.

        Raises:
            EntityNotFound: If the flag has been deleted by another
                transaction since it was loaded.
            DuplicateEntity: If the version is stale.
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, flag_id: FeatureFlagId) -> FeatureFlag:
        """Load a FeatureFlag by ID, raising :class:`EntityNotFound` if absent."""
        flag = await self.get_by_id(flag_id)
        if flag is None:
            raise EntityNotFound("FeatureFlag", flag_id)
        return flag

    async def get_by_key_or_raise(self, key: str) -> FeatureFlag:
        """Load a FeatureFlag by key, raising :class:`EntityNotFound` if absent."""
        flag = await self.get_by_key(key)
        if flag is None:
            raise EntityNotFound("FeatureFlag", key)
        return flag


# ============================================================
# Notification
# ============================================================


class NotificationRepository(ABC):
    """Abstract repository for the :class:`Notification` aggregate.

    Implementations must:
    - Load the :class:`Notification` or return ``None``.
    - Persist the full aggregate on :meth:`save`.
    - Index notifications by ``(user_id, status)`` for fast inbox
      queries and by ``(status, scheduled_at)`` for the dispatcher's
      pending-send scan.
    """

    @abstractmethod
    async def get_by_id(self, notification_id: NotificationId) -> Notification | None:
        """Load a Notification by ID.

        Returns the :class:`Notification`, or ``None`` if no
        notification exists with that ID.
        """

    @abstractmethod
    async def list_by_user(
        self,
        user_id: UserId,
        *,
        status: NotificationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Notification]:
        """List a user's notifications, most recent first.

        Args:
            user_id: The user to list notifications for.
            status: Optional status filter (e.g., ``DELIVERED`` for the
                in-app inbox).
            limit: Maximum number to return.
            offset: Pagination offset.
        """

    @abstractmethod
    async def list_queued_for_send(
        self,
        *,
        on_or_before: datetime,
        channel: NotificationChannel | None = None,
        limit: int = 100,
    ) -> Sequence[Notification]:
        """List ``queued`` notifications due to be sent.

        Used by the dispatcher job to find notifications whose
        ``scheduled_at`` is on or before the given timestamp.

        Args:
            on_or_before: The cutoff timestamp (inclusive).
            channel: Optional channel filter (e.g., send only emails
                in one batch, only pushes in another).
            limit: Maximum number to return.
        """

    @abstractmethod
    async def add(self, notification: Notification) -> None:
        """Add a *new* Notification to the repository.

        Args:
            notification: The new :class:`Notification` to persist.
        """

    @abstractmethod
    async def save(self, notification: Notification) -> None:
        """Persist changes to an *existing* Notification.

        Args:
            notification: The modified :class:`Notification` to
                persist.

        Raises:
            EntityNotFound: If the notification has been deleted by
                another transaction since it was loaded.
            DuplicateEntity: If the version is stale.
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, notification_id: NotificationId) -> Notification:
        """Load a Notification by ID, raising :class:`EntityNotFound` if absent."""
        notification = await self.get_by_id(notification_id)
        if notification is None:
            raise EntityNotFound("Notification", notification_id)
        return notification


# ============================================================
# Organization
# ============================================================


class OrganizationRepository(ABC):
    """Abstract repository for the :class:`Organization` aggregate.

    Implementations must:
    - Load the :class:`Organization` or return ``None``.
    - Persist the full aggregate on :meth:`save`.
    - Enforce uniqueness of ``name`` (case-insensitive) at the storage
      layer.
    """

    @abstractmethod
    async def get_by_id(self, organization_id: OrganizationId) -> Organization | None:
        """Load an Organization by ID.

        Returns the :class:`Organization`, or ``None`` if no
        organization exists with that ID. Dissolved organizations are
        still returned — they remain in storage for archival and
        audit purposes.
        """

    @abstractmethod
    async def get_by_name(self, name: str) -> Organization | None:
        """Load an Organization by its (case-insensitive) name.

        Args:
            name: The organization name to look up.

        Returns:
            The matching :class:`Organization`, or ``None`` if not
            found.
        """

    @abstractmethod
    async def list_active(self) -> Sequence[Organization]:
        """List all active (non-suspended, non-dissolved) organizations."""

    @abstractmethod
    async def list_suspended(self) -> Sequence[Organization]:
        """List all suspended organizations."""

    @abstractmethod
    async def add(self, organization: Organization) -> None:
        """Add a *new* Organization to the repository.

        Args:
            organization: The new :class:`Organization` to persist.

        Raises:
            DuplicateEntity: If an organization with the same name
                already exists.
        """

    @abstractmethod
    async def save(self, organization: Organization) -> None:
        """Persist changes to an *existing* Organization.

        Args:
            organization: The modified :class:`Organization` to
                persist.

        Raises:
            EntityNotFound: If the organization has been deleted by
                another transaction since it was loaded.
            DuplicateEntity: If the version is stale.
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, organization_id: OrganizationId) -> Organization:
        """Load an Organization by ID, raising :class:`EntityNotFound` if absent."""
        org = await self.get_by_id(organization_id)
        if org is None:
            raise EntityNotFound("Organization", organization_id)
        return org


__all__ = [
    "AuditLogRepository",
    "FeatureFlagRepository",
    "NotificationRepository",
    "OrganizationRepository",
]
