"""Billing context — domain events.

Domain events are immutable records of something that *happened* in the
Billing context. They are named in past tense and carry all the data a
subscriber needs to react.

All events inherit from :class:`DomainEvent` (which provides ``event_id``
and ``occurred_at``) and use ``@dataclass(frozen=True, kw_only=True)`` so
that required fields can follow the inherited defaulted fields without
ordering issues.

These events are *pure data*. They contain no behaviour and no side
effects. Subscribers (invoice generation, entitlement provisioning,
dunning emails) live in the application and infrastructure layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.domain.shared.ids import (
    BillingPlanId,
    InvoiceId,
    SubscriptionId,
    UserId,
)
from app.domain.shared.kernel import (
    BillingPeriod,
    DomainEvent,
    SubscriptionStatus,
)
from app.domain.shared.value_objects import Money


# ============================================================
# BillingPlan events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class BillingPlanCreated(DomainEvent):
    """Emitted when a new BillingPlan is created.

    Fired by :meth:`BillingPlan.create`. The plan starts at version 1
    in ``active`` status. Subscribers may provision plan-level
    entitlement defaults (seat counts, rate limits) keyed by
    ``plan_id``.
    """

    plan_id: BillingPlanId
    code: str
    name: str
    price: Money
    billing_period: BillingPeriod


@dataclass(frozen=True, kw_only=True)
class BillingPlanDeprecated(DomainEvent):
    """Emitted when a BillingPlan is deprecated.

    Fired by :meth:`BillingPlan.deprecate`. Existing subscriptions
    remain in force until they renew, cancel, or expire; new
    subscriptions cannot start on a deprecated plan. Subscribers should
    hide the plan from the upgrade/downgrade catalogue.
    """

    plan_id: BillingPlanId
    deprecated_at: datetime


# ============================================================
# Subscription events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class SubscriptionActivated(DomainEvent):
    """Emitted when a new subscription is created in ``active`` status.

    Fired by :meth:`Subscription.subscribe`. Subscribers should
    provision the plan's entitlements for the user and emit a welcome
    notification.
    """

    subscription_id: SubscriptionId
    user_id: UserId
    billing_plan_id: BillingPlanId
    current_period_start: date
    current_period_end: date
    payment_provider: str


@dataclass(frozen=True, kw_only=True)
class SubscriptionRenewed(DomainEvent):
    """Emitted when a subscription's billing period is renewed.

    Fired by :meth:`Subscription.renew`. Subscribers should generate a
    new invoice and refresh entitlement validity.
    """

    subscription_id: SubscriptionId
    user_id: UserId
    billing_plan_id: BillingPlanId
    new_period_end: date


@dataclass(frozen=True, kw_only=True)
class SubscriptionUpgraded(DomainEvent):
    """Emitted when a subscription is upgraded to a higher-tier plan.

    Fired by :meth:`Subscription.upgrade`. The upgrade takes effect
    immediately; subscribers should re-provision entitlements and
    issue a prorated invoice for the remainder of the current period.
    """

    subscription_id: SubscriptionId
    user_id: UserId
    previous_plan_id: BillingPlanId
    new_plan_id: BillingPlanId


@dataclass(frozen=True, kw_only=True)
class SubscriptionDowngradeScheduled(DomainEvent):
    """Emitted when a downgrade is scheduled to take effect at period end.

    Fired by :meth:`Subscription.downgrade`. Downgrades preserve
    already-paid entitlements; the new plan takes effect at the start
    of the next billing period. Subscribers should not revoke any
    entitlements now.
    """

    subscription_id: SubscriptionId
    user_id: UserId
    current_plan_id: BillingPlanId
    scheduled_plan_id: BillingPlanId
    effective_at: date


@dataclass(frozen=True, kw_only=True)
class SubscriptionCanceled(DomainEvent):
    """Emitted when a subscription is canceled.

    Fired by :meth:`Subscription.cancel`. The subscription remains
    ``active`` until the end of the current billing period, then
    transitions to ``expired``. Subscribers should not revoke
    entitlements immediately but should schedule their revocation at
    ``current_period_end``.
    """

    subscription_id: SubscriptionId
    user_id: UserId
    canceled_at: datetime
    effective_at: date


@dataclass(frozen=True, kw_only=True)
class SubscriptionPastDue(DomainEvent):
    """Emitted when a subscription enters ``past_due`` status.

    Fired by :meth:`Subscription.mark_past_due`. Subscribers should
    trigger the dunning workflow (retry emails, grace-period
    countdown). Entitlements typically remain in force during the
    grace window.
    """

    subscription_id: SubscriptionId
    user_id: UserId
    billing_plan_id: BillingPlanId


@dataclass(frozen=True, kw_only=True)
class SubscriptionRecovered(DomainEvent):
    """Emitted when a past-due subscription is recovered to ``active``.

    Fired by :meth:`Subscription.recover`. Subscribers should cancel
    the dunning workflow and refresh entitlement validity.
    """

    subscription_id: SubscriptionId
    user_id: UserId
    billing_plan_id: BillingPlanId


@dataclass(frozen=True, kw_only=True)
class SubscriptionExpired(DomainEvent):
    """Emitted when a subscription transitions to ``expired``.

    Fired by :meth:`Subscription.expire`. The subscription is now
    terminal; subscribers should revoke entitlements and emit an
    expiration notification.
    """

    subscription_id: SubscriptionId
    user_id: UserId
    billing_plan_id: BillingPlanId
    expired_at: datetime


# ============================================================
# Invoice events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class InvoiceIssued(DomainEvent):
    """Emitted when a new invoice is issued for a subscription.

    Carries the amount, the provider's invoice ID, and the issuance
    timestamp. Subscribers should send the invoice to the user and
    schedule payment retry.
    """

    invoice_id: InvoiceId
    subscription_id: SubscriptionId
    user_id: UserId
    amount: Money
    provider_invoice_id: str
    issued_at: datetime


@dataclass(frozen=True, kw_only=True)
class InvoicePaid(DomainEvent):
    """Emitted when an invoice is paid.

    Fired by :meth:`Invoice.mark_paid`. Subscribers should update the
    subscription's status (e.g., recover from ``past_due``) and emit a
    receipt.
    """

    invoice_id: InvoiceId
    subscription_id: SubscriptionId
    user_id: UserId
    paid_at: datetime


@dataclass(frozen=True, kw_only=True)
class InvoiceFailed(DomainEvent):
    """Emitted when an invoice payment fails.

    Fired by :meth:`Invoice.mark_failed`. Subscribers should trigger
    dunning and, if appropriate, transition the subscription to
    ``past_due``.
    """

    invoice_id: InvoiceId
    subscription_id: SubscriptionId
    user_id: UserId
    failed_at: datetime


@dataclass(frozen=True, kw_only=True)
class InvoiceRefunded(DomainEvent):
    """Emitted when a paid invoice is refunded.

    Fired by :meth:`Invoice.refund`. Subscribers should reverse any
    entitlement effects of the original payment and notify the user.
    """

    invoice_id: InvoiceId
    subscription_id: SubscriptionId
    user_id: UserId
    refunded_at: datetime
    reason: str | None = None


__all__ = [
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
]
