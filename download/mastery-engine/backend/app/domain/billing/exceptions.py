"""Billing context — domain-specific exceptions.

These exceptions are raised by the Billing-context aggregates when
invariants are violated or invalid state transitions are attempted.
They are *narrow* subclasses of :class:`DomainError` so that callers can
catch a specific failure mode without inspecting error messages.

All exceptions are pure Python and carry no framework dependencies.
"""

from __future__ import annotations

from typing import Any

from app.domain.shared.kernel import DomainError


class BillingError(DomainError):
    """Base class for all Billing-context domain errors.

    Catch this to handle any billing-specific failure generically.
    """


class AlreadySubscribed(BillingError):
    """Raised when subscribing a user who already has an active subscription.

    Invariant: a user may hold at most one active or past-due
    subscription at a time. To change plans, use
    :meth:`Subscription.upgrade` or :meth:`Subscription.downgrade`
    rather than re-subscribing.
    """

    def __init__(self, user_id: Any) -> None:
        super().__init__(
            f"User {user_id} already has an active subscription",
            code="ALREADY_SUBSCRIBED",
        )
        self.user_id = user_id


class NotSubscribed(BillingError):
    """Raised when an operation requires an active subscription but none exists.

    Invariant: upgrade, downgrade, cancel, recover, and renew all
    require a subscription in an appropriate state. Calling them on a
    user with no subscription (or a subscription that has expired) is
    rejected.
    """

    def __init__(self, user_id: Any) -> None:
        super().__init__(
            f"User {user_id} has no active subscription",
            code="NOT_SUBSCRIBED",
        )
        self.user_id = user_id


class PaymentFailed(BillingError):
    """Raised when a payment attempt fails.

    Carries the provider-side failure reason. The subscription typically
    transitions to ``past_due`` as a result; this exception is raised
    when the failure should bubble to the caller (e.g., an invoice
    cannot be retried further).
    """

    def __init__(self, reason: str, *, invoice_id: Any | None = None) -> None:
        super().__init__(
            f"Payment failed{f' for invoice {invoice_id}' if invoice_id else ''}: {reason}",
            code="PAYMENT_FAILED",
        )
        self.reason = reason
        self.invoice_id = invoice_id


class InvalidUpgrade(BillingError):
    """Raised when an upgrade is attempted with an invalid target plan.

    Invariant: an upgrade must move to a *different* plan whose price
    is greater than or equal to the current plan's price (within the
    same currency). Downgrades go through :meth:`Subscription.downgrade`.
    """

    def __init__(self, current_plan_id: Any, new_plan_id: Any, reason: str) -> None:
        super().__init__(
            f"Invalid upgrade from plan {current_plan_id} to plan {new_plan_id}: {reason}",
            code="INVALID_UPGRADE",
        )
        self.current_plan_id = current_plan_id
        self.new_plan_id = new_plan_id
        self.reason = reason


class InvalidDowngrade(BillingError):
    """Raised when a downgrade is attempted with an invalid target plan.

    Invariant: a downgrade must move to a *different* plan whose price
    is less than the current plan's price (within the same currency).
    Downgrades take effect at the end of the current billing period to
    preserve already-paid entitlements.
    """

    def __init__(self, current_plan_id: Any, new_plan_id: Any, reason: str) -> None:
        super().__init__(
            f"Invalid downgrade from plan {current_plan_id} to plan {new_plan_id}: {reason}",
            code="INVALID_DOWNGRADE",
        )
        self.current_plan_id = current_plan_id
        self.new_plan_id = new_plan_id
        self.reason = reason


class PlanNotActive(BillingError):
    """Raised when operating on a BillingPlan that is not active.

    Invariant: only active plans can be subscribed to. Deprecated plans
    can still be queried for historical invoices but cannot start new
    subscriptions.
    """

    def __init__(self, plan_id: Any) -> None:
        super().__init__(
            f"BillingPlan {plan_id} is not active",
            code="PLAN_NOT_ACTIVE",
        )
        self.plan_id = plan_id


class InvoiceAlreadyPaid(BillingError):
    """Raised when marking paid an invoice that is already paid.

    Invariant: an invoice's ``paid`` status is terminal (modulo
    refunds). Re-marking it paid is a no-op for callers that check
    status first, but raising here surfaces caller bugs.
    """

    def __init__(self, invoice_id: Any) -> None:
        super().__init__(
            f"Invoice {invoice_id} is already paid",
            code="INVOICE_ALREADY_PAID",
        )
        self.invoice_id = invoice_id


class InvoiceAlreadyFailed(BillingError):
    """Raised when marking failed an invoice that is already failed."""

    def __init__(self, invoice_id: Any) -> None:
        super().__init__(
            f"Invoice {invoice_id} has already failed",
            code="INVOICE_ALREADY_FAILED",
        )
        self.invoice_id = invoice_id


class InvoiceNotRefundable(BillingError):
    """Raised when refunding an invoice that is not in a refundable state.

    Invariant: only a paid invoice can be refunded. Refunding a
    pending, failed, or already-refunded invoice is rejected.
    """

    def __init__(self, invoice_id: Any, current_status: Any) -> None:
        super().__init__(
            f"Invoice {invoice_id} in status {current_status!r} cannot be refunded",
            code="INVOICE_NOT_REFUNDABLE",
        )
        self.invoice_id = invoice_id
        self.current_status = current_status


__all__ = [
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
]
