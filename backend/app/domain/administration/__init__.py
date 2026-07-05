"""Administration bounded context — domain layer.

Contains: aggregates, entities, value objects, domain services, domain events,
context-specific exceptions, and the abstract repository contracts.

This package is pure Python — no I/O, no framework dependencies. All
imports are from :mod:`app.domain.shared` (the shared kernel) or from
within this package.

Public surface:

- **Aggregates**: :class:`FeatureFlag`, :class:`Notification`,
  :class:`Organization`
- **Entities**: :class:`AuditLog` (append-only)
- **Events**: :class:`NotificationQueued`, :class:`NotificationSent`,
  :class:`NotificationDelivered`, :class:`NotificationOpened`,
  :class:`NotificationDismissed`, :class:`NotificationFailed`,
  :class:`FeatureFlagCreated`, :class:`FeatureFlagUpdated`,
  :class:`FeatureFlagRetired`, :class:`OrganizationCreated`,
  :class:`OrganizationSuspended`, :class:`OrganizationReactivated`,
  :class:`OrganizationDissolved`, :class:`AuditLogRecorded`
- **Exceptions**: :class:`AdministrationError` and its subclasses
- **Repositories**: :class:`AuditLogRepository`,
  :class:`FeatureFlagRepository`, :class:`NotificationRepository`,
  :class:`OrganizationRepository`
"""

from __future__ import annotations

from app.domain.administration.audit_log import AuditLog
from app.domain.administration.events import (
    AuditLogRecorded,
    FeatureFlagCreated,
    FeatureFlagRetired,
    FeatureFlagUpdated,
    NotificationDelivered,
    NotificationDismissed,
    NotificationFailed,
    NotificationOpened,
    NotificationQueued,
    NotificationSent,
    OrganizationCreated,
    OrganizationDissolved,
    OrganizationReactivated,
    OrganizationSuspended,
)
from app.domain.administration.exceptions import (
    AdministrationError,
    CannotDissolveOrganization,
    CannotReactivateOrganization,
    CannotSuspendOrganization,
    FeatureFlagAlreadyExists,
    FeatureFlagNotActive,
    NotificationFailedError,
    NotificationNotTransitionable,
)
from app.domain.administration.feature_flag import FeatureFlag
from app.domain.administration.notification import Notification
from app.domain.administration.organization import (
    Organization,
    OrganizationStatus,
)
from app.domain.administration.repository import (
    AuditLogRepository,
    FeatureFlagRepository,
    NotificationRepository,
    OrganizationRepository,
)

__all__ = [
    # Aggregates / entities
    "AuditLog",
    "FeatureFlag",
    "Notification",
    "Organization",
    "OrganizationStatus",
    # Events
    "AuditLogRecorded",
    "FeatureFlagCreated",
    "FeatureFlagRetired",
    "FeatureFlagUpdated",
    "NotificationDelivered",
    "NotificationDismissed",
    "NotificationFailed",
    "NotificationOpened",
    "NotificationQueued",
    "NotificationSent",
    "OrganizationCreated",
    "OrganizationDissolved",
    "OrganizationReactivated",
    "OrganizationSuspended",
    # Exceptions
    "AdministrationError",
    "CannotDissolveOrganization",
    "CannotReactivateOrganization",
    "CannotSuspendOrganization",
    "FeatureFlagAlreadyExists",
    "FeatureFlagNotActive",
    "NotificationFailedError",
    "NotificationNotTransitionable",
    # Repositories
    "AuditLogRepository",
    "FeatureFlagRepository",
    "NotificationRepository",
    "OrganizationRepository",
]
