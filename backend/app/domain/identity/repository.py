"""Identity context — abstract repository interface.

The :class:`UserRepository` defines the *contract* for loading and
persisting :class:`User` aggregates. It is an abstract base class — no
implementation is provided here. Concrete implementations live in the
infrastructure layer (e.g., a SQLAlchemy-backed repository).

Keeping the interface in the domain layer ensures that application
services depend only on the domain, not on infrastructure details. It
also enables swapping the persistence mechanism (e.g., for testing)
without touching the domain or application layers.

Concurrency contract:
- Implementations should enforce optimistic concurrency via a version
  column (see :class:`VersionNumber` in the shared kernel). If a
  :meth:`save` call detects a stale version, it must raise
  :class:`DuplicateEntity` or a similar domain error.
- Uniqueness of email addresses must be enforced by the persistence
  store (unique index). The repository may surface this as
  :class:`EmailAlreadyRegistered` at the application layer's discretion.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.identity.user import User
from app.domain.shared.ids import UserId
from app.domain.shared.kernel import EntityNotFound
from app.domain.shared.value_objects import Email


class UserRepository(ABC):
    """Abstract repository for the :class:`User` aggregate.

    Implementations must:
    - Load the *full* aggregate (root + nested entities) or return ``None``.
    - Persist the full aggregate on :meth:`save`, including any nested
      :class:`UserProfile` and :class:`UserCredential` entities.
    - Collect and surface domain events recorded on the aggregate via
      :meth:`AggregateRoot.collect_events` *after* a successful save
      (the application layer usually orchestrates this).
    - Enforce email uniqueness at the storage layer.
    """

    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> User | None:
        """Load a user by ID.

        Args:
            user_id: The :class:`UserId` to look up.

        Returns:
            The fully reconstituted :class:`User` aggregate, or ``None``
            if no user exists with that ID. Anonymized users are still
            returned — they remain in storage for referential integrity.
        """

    @abstractmethod
    async def get_by_email(self, email: Email) -> User | None:
        """Load a user by email address.

        Email comparison is case-insensitive (enforced by :class:`Email`).

        Args:
            email: The :class:`Email` to look up.

        Returns:
            The matching :class:`User`, or ``None`` if not found.
        """

    @abstractmethod
    async def add(self, user: User) -> None:
        """Add a *new* user to the repository.

        Use this for users that have never been persisted (i.e., created
        via :meth:`User.register`). For users loaded via :meth:`get_by_id`
        or :meth:`get_by_email` and then modified, use :meth:`save`.

        Args:
            user: The new :class:`User` aggregate to persist.

        Raises:
            EmailAlreadyRegistered: If a user with the same email already
                exists (surfaced from the storage-layer unique constraint).
        """

    @abstractmethod
    async def save(self, user: User) -> None:
        """Persist changes to an *existing* user.

        Use this for users that were loaded via :meth:`get_by_id` or
        :meth:`get_by_email` and then mutated. Implementations should
        use optimistic concurrency control based on a version field.

        Args:
            user: The modified :class:`User` aggregate to persist.

        Raises:
            EntityNotFound: If the user has been deleted by another
                transaction since it was loaded.
            DuplicateEntity: If the version is stale (concurrent
                modification by another transaction).
        """

    # ------------------------------------------------------------------
    # Optional helpers (non-abstract; implementations may override)
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, user_id: UserId) -> User:
        """Load a user by ID, raising :class:`EntityNotFound` if absent.

        Convenience method for application services that expect the user
        to exist. Implementations may override for efficiency.
        """
        user = await self.get_by_id(user_id)
        if user is None:
            raise EntityNotFound("User", user_id)
        return user

    async def get_by_email_or_raise(self, email: Email) -> User:
        """Load a user by email, raising :class:`EntityNotFound` if absent."""
        user = await self.get_by_email(email)
        if user is None:
            raise EntityNotFound("User", email.value)
        return user


__all__ = ["UserRepository"]
