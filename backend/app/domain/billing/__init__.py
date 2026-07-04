"""Billing bounded context — domain layer.

Contains: aggregates, entities, value objects, domain services, domain events,
context-specific exceptions, and the abstract repository contracts.

This package is pure Python — no I/O, no framework dependencies. All
imports are from :mod:`app.domain.shared` (the shared kernel) or from
within this package.

Public surface:

- **Aggregates**: :class:`Subscription`
- **Entities**: :class:`BillingPlan`, :class:`Invoice`
- **Events**: :class:`BillingPlanCreated`, :class:`BillingPlanDeprecated`,
  :class:`SubscriptionActivated`, :class:`SubscriptionRenewed`,
  :class:`SubscriptionUpgraded`, :class:`SubscriptionDowngradeScheduled`,
  :class:`SubscriptionCanceled`, :class:`SubscriptionPastDue`,
  :class:`SubscriptionRecovered`, :class:`SubscriptionExpired`,
  :class:`InvoiceIssued`, :class:`InvoicePaid`, :class:`InvoiceFailed`,
  :class:`InvoiceRefunded`
- **Exceptions**: :class:`BillingError` and its subclasses
- **Repositories**: :class:`BillingPlanRepository`,
  :class:`SubscriptionRepository`, :class:`InvoiceRepository`
"""

from __future__ import annotations

from app.domain.billing.billing_plan import BillingPlan
from app.domain.billing.events import (
    BillingPlanCreated,
    BillingPlanDeprecated,
    InvoiceFailed,
    InvoiceIssued,
    InvoicePaid,
    InvoiceRefunded,
    SubscriptionActivated,
    SubscriptionCanceled,
    SubscriptionDowngradeScheduled,
    SubscriptionExpired,
    SubscriptionPastDue,
    SubscriptionRecovered,
    SubscriptionRenewed,
    SubscriptionUpgraded,
)
from app.domain.billing.exceptions import (
    AlreadySubscribed,
    BillingError,
    InvoiceAlreadyFailed,
    InvoiceAlreadyPaid,
    InvoiceNotRefundable,
    InvalidDowngrade,
    InvalidUpgrade,
    NotSubscribed,
    PaymentFailed,
    PlanNotActive,
)
from app.domain.billing.invoice import Invoice, InvoiceStatus
from app.domain.billing.repository import (
    BillingPlanRepository,
    InvoiceRepository,
    SubscriptionRepository,
)
from app.domain.billing.subscription import Subscription

__all__ = [
    # Aggregates / entities
    "BillingPlan",
    "Invoice",
    "InvoiceStatus",
    "Subscription",
    # Events
    "BillingPlanCreated",
    "BillingPlanDeprecated",
    "InvoiceFailed",
    "InvoiceIssued",
    "InvoicePaid",
    "InvoiceRefunded",
    "SubscriptionActivated",
    "SubscriptionCanceled",
    "SubscriptionDowngradeScheduled",
    "SubscriptionExpired",
    "SubscriptionPastDue",
    "SubscriptionRecovered",
    "SubscriptionRenewed",
    "SubscriptionUpgraded",
    # Exceptions
    "AlreadySubscribed",
    "BillingError",
    "InvoiceAlreadyFailed",
    "InvoiceAlreadyPaid",
    "InvoiceNotRefundable",
    "InvalidDowngrade",
    "InvalidUpgrade",
    "NotSubscribed",
    "PaymentFailed",
    "PlanNotActive",
    # Repositories
    "BillingPlanRepository",
    "InvoiceRepository",
    "SubscriptionRepository",
]
