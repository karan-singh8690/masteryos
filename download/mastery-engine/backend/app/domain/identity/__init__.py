"""Identity bounded context — domain layer.

Contains: the User aggregate root, its local entities (UserProfile,
UserCredential), domain events, context-specific exceptions, and the
abstract repository contract.

This package is pure Python — no I/O, no framework dependencies. All
imports are from :mod:`app.domain.shared` (the shared kernel) or from
within this package.

Public surface:
- Aggregates/entities: :class:`User`, :class:`UserProfile`, :class:`UserCredential`
- Events: :class:`UserRegistered`, :class:`EmailVerified`, :class:`UserSuspended`,
  :class:`UserReactivated`, :class:`AccountDeletionRequested`,
  :class:`AccountDeletionCancelled`, :class:`UserAnonymized`,
  :class:`MFAEnabled`, :class:`MFADisabled`, :class:`UserProfileUpdated`
- Exceptions: :class:`IdentityError` and its subclasses
- Repository: :class:`UserRepository` (abstract)
"""

from __future__ import annotations

from app.domain.identity.credential import UserCredential
from app.domain.identity.events import (
    AccountDeletionCancelled,
    AccountDeletionRequested,
    EmailVerified,
    MFADisabled,
    MFAEnabled,
    UserAnonymized,
    UserProfileUpdated,
    UserReactivated,
    UserRegistered,
    UserSuspended,
)
from app.domain.identity.exceptions import (
    AlreadyPendingDeletion,
    CannotCancelDeletionPastGrace,
    CannotDisableMFAForAdmin,
    CannotSuspendAdmin,
    EmailAlreadyRegistered,
    EmailNotVerified,
    IdentityError,
    MFAAlreadyEnabled,
    MFANotEnabled,
)
from app.domain.identity.profile import UserProfile
from app.domain.identity.repository import UserRepository
from app.domain.identity.user import User

__all__ = [
    # Aggregate & entities
    "User",
    "UserProfile",
    "UserCredential",
    # Events
    "UserRegistered",
    "EmailVerified",
    "UserSuspended",
    "UserReactivated",
    "AccountDeletionRequested",
    "AccountDeletionCancelled",
    "UserAnonymized",
    "MFAEnabled",
    "MFADisabled",
    "UserProfileUpdated",
    # Exceptions
    "IdentityError",
    "EmailAlreadyRegistered",
    "EmailNotVerified",
    "CannotSuspendAdmin",
    "CannotDisableMFAForAdmin",
    "CannotCancelDeletionPastGrace",
    "AlreadyPendingDeletion",
    "MFAAlreadyEnabled",
    "MFANotEnabled",
    # Repository
    "UserRepository",
]
