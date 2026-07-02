"""Billing context — Invoice entity.

The :class:`Invoice` is the entity tracking a single bill issued to a
user for a subscription's billing period. It records the amount, the
provider's invoice ID, and the lifecycle state (``pending`` → ``paid``
or ``failed``, with optional ``refunded`` from ``paid``).

Lifecycle (state machine)::

    pending ──mark_paid()──► paid ──refund()──► refunded
        │
        └──mark_failed()────► failed  (terminal)

The invoice is **not** an aggregate root; its lifecycle is supervised
by the :class:`Subscription` aggregate (which records past-due and
recovered events that pair with invoice state). It is mutated via its
own methods, however, to keep the invoice's payment state transitions
explicit and auditable.

Invariants enforced:
- ``amount`` is a :class:`Money` value object.
- ``provider_invoice_id`` is a non-empty string.
- ``subscription_id`` and ``user_id`` are typed IDs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.billing.events import (
    InvoiceFailed,
    InvoiceIssued,
    InvoicePaid,
    InvoiceRefunded,
)
from app.domain.billing.exceptions import (
    InvoiceAlreadyFailed,
    InvoiceAlreadyPaid,
    InvoiceNotRefundable,
)
from app.domain.shared.ids import InvoiceId, SubscriptionId, UserId
from app.domain.shared.kernel import (
    Entity,
    InvalidStateTransition,
    InvariantViolation,
)
from app.domain.shared.value_objects import Money


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class InvoiceStatus:
    """Status of an invoice (string constants, not an enum)."""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class Invoice(Entity):
    """The Invoice entity.

    Holds the invoice's identity, the subscription and user it belongs
    to, the amount, the provider's invoice ID, and lifecycle state.
    All mutations go through methods on this class, which enforce
    invariants and emit domain events.

    The public constructor is intended for **reconstitution** from
    persistence. To create a *new* invoice, use :meth:`Invoice.issue`.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: InvoiceId,
        subscription_id: SubscriptionId,
        user_id: UserId,
        amount: Money,
        status: str = InvoiceStatus.PENDING,
        provider_invoice_id: str,
        issued_at: datetime | None = None,
        paid_at: datetime | None = None,
        failed_at: datetime | None = None,
        refunded_at: datetime | None = None,
        refund_reason: str | None = None,
    ) -> None:
        self._domain_events: list[Any] = []
        self._id: InvoiceId = id
        self._subscription_id: SubscriptionId = subscription_id
        self._user_id: UserId = user_id
        self._amount: Money = amount
        self._status: str = status
        self._provider_invoice_id: str = provider_invoice_id
        self._issued_at: datetime = issued_at or _utcnow()
        self._paid_at: datetime | None = paid_at
        self._failed_at: datetime | None = failed_at
        self._refunded_at: datetime | None = refunded_at
        self._refund_reason: str | None = refund_reason
        self._validate_invariants()

    # ------------------------------------------------------------------
    # Event-collection machinery (mirror AggregateRoot's surface)
    # ------------------------------------------------------------------

    def _record_event(self, event: Any) -> None:
        """Record a domain event to be published after persistence."""
        if not hasattr(self, "_domain_events") or self._domain_events is None:
            self._domain_events = []
        self._domain_events.append(event)

    def collect_events(self) -> list[Any]:
        """Return all recorded domain events and clear the internal list."""
        events = getattr(self, "_domain_events", []) or []
        self._domain_events = []
        return list(events)

    def clear_events(self) -> None:
        """Clear all recorded events without returning them."""
        self._domain_events = []

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def issue(
        cls,
        subscription_id: SubscriptionId,
        user_id: UserId,
        amount: Money,
        provider_invoice_id: str,
    ) -> Invoice:
        """Issue a new invoice in ``pending`` status.

        Args:
            subscription_id: The subscription this invoice bills.
            user_id: The user being billed.
            amount: The :class:`Money` amount to charge.
            provider_invoice_id: The provider's invoice ID (e.g., the
                Stripe invoice ID).

        Returns:
            A newly created, un-persisted :class:`Invoice` in
            ``pending`` status. The caller must add it to the
            repository and call :meth:`collect_events` to publish the
            recorded events.

        Raises:
            InvariantViolation: If any field fails validation.
        """
        invoice_id = InvoiceId.generate()
        invoice = cls(
            id=invoice_id,
            subscription_id=subscription_id,
            user_id=user_id,
            amount=amount,
            status=InvoiceStatus.PENDING,
            provider_invoice_id=provider_invoice_id,
        )
        invoice._record_event(
            InvoiceIssued(
                invoice_id=invoice.id,
                subscription_id=subscription_id,
                user_id=user_id,
                amount=amount,
                provider_invoice_id=provider_invoice_id,
                issued_at=invoice.issued_at,
            )
        )
        return invoice

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> InvoiceId:
        """The invoice's unique identifier."""
        return self._id

    @property
    def subscription_id(self) -> SubscriptionId:
        """The subscription this invoice bills."""
        return self._subscription_id

    @property
    def user_id(self) -> UserId:
        """The user being billed."""
        return self._user_id

    @property
    def amount(self) -> Money:
        """The :class:`Money` amount to charge."""
        return self._amount

    @property
    def status(self) -> str:
        """The invoice's lifecycle status."""
        return self._status

    @property
    def provider_invoice_id(self) -> str:
        """The provider's invoice ID."""
        return self._provider_invoice_id

    @property
    def issued_at(self) -> datetime:
        """When this invoice was issued."""
        return self._issued_at

    @property
    def paid_at(self) -> datetime | None:
        """When this invoice was paid, or ``None``."""
        return self._paid_at

    @property
    def failed_at(self) -> datetime | None:
        """When this invoice failed, or ``None``."""
        return self._failed_at

    @property
    def refunded_at(self) -> datetime | None:
        """When this invoice was refunded, or ``None``."""
        return self._refunded_at

    @property
    def refund_reason(self) -> str | None:
        """The reason for the refund, or ``None``."""
        return self._refund_reason

    @property
    def is_pending(self) -> bool:
        """True if the invoice is still awaiting payment."""
        return self._status == InvoiceStatus.PENDING

    @property
    def is_paid(self) -> bool:
        """True if the invoice has been paid (and not refunded)."""
        return self._status == InvoiceStatus.PAID

    @property
    def is_failed(self) -> bool:
        """True if the invoice payment failed (terminal)."""
        return self._status == InvoiceStatus.FAILED

    @property
    def is_refunded(self) -> bool:
        """True if a paid invoice was refunded."""
        return self._status == InvoiceStatus.REFUNDED

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants; raise on failure."""
        if not isinstance(self._subscription_id, SubscriptionId):
            raise InvariantViolation(
                "Invoice",
                f"subscription_id must be a SubscriptionId, got {type(self._subscription_id).__name__}",
            )
        if not isinstance(self._user_id, UserId):
            raise InvariantViolation(
                "Invoice",
                f"user_id must be a UserId, got {type(self._user_id).__name__}",
            )
        if not isinstance(self._amount, Money):
            raise InvariantViolation(
                "Invoice",
                f"amount must be a Money value object, got {type(self._amount).__name__}",
            )
        if not isinstance(self._provider_invoice_id, str) or not self._provider_invoice_id.strip():
            raise InvariantViolation(
                "Invoice",
                "provider_invoice_id must be a non-empty string",
            )
        if self._status not in (
            InvoiceStatus.PENDING,
            InvoiceStatus.PAID,
            InvoiceStatus.FAILED,
            InvoiceStatus.REFUNDED,
        ):
            raise InvariantViolation(
                "Invoice",
                f"unknown status {self._status!r}",
            )

    def _assert_status(self, expected: str, action: str) -> None:
        """Raise :class:`InvalidStateTransition` unless in ``expected`` status."""
        if self._status != expected:
            raise InvalidStateTransition(
                entity="Invoice",
                current_state=self._status,
                attempted_action=action,
            )

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def mark_paid(self, now: datetime | None = None) -> None:
        """Transition the invoice from ``pending`` to ``paid``.

        Pre-state: ``pending``.
        Post-state: ``paid`` with ``paid_at`` set.

        Raises:
            InvoiceAlreadyPaid: If the invoice is already ``paid``.
            InvalidStateTransition: If the invoice is ``failed`` or
                ``refunded``.
        """
        if self._status == InvoiceStatus.PAID:
            raise InvoiceAlreadyPaid(self._id)
        self._assert_status(InvoiceStatus.PENDING, "mark_paid")
        timestamp = now or _utcnow()
        self._status = InvoiceStatus.PAID
        self._paid_at = timestamp
        self._record_event(
            InvoicePaid(
                invoice_id=self._id,
                subscription_id=self._subscription_id,
                user_id=self._user_id,
                paid_at=timestamp,
            )
        )

    def mark_failed(self, now: datetime | None = None) -> None:
        """Transition the invoice from ``pending`` to ``failed`` (terminal).

        Pre-state: ``pending``.
        Post-state: ``failed`` with ``failed_at`` set.

        Raises:
            InvoiceAlreadyFailed: If the invoice is already ``failed``.
            InvalidStateTransition: If the invoice is ``paid`` or
                ``refunded`` (a paid invoice cannot be marked failed —
                refund it instead).
        """
        if self._status == InvoiceStatus.FAILED:
            raise InvoiceAlreadyFailed(self._id)
        if self._status in (InvoiceStatus.PAID, InvoiceStatus.REFUNDED):
            raise InvalidStateTransition(
                entity="Invoice",
                current_state=self._status,
                attempted_action="mark_failed",
            )
        self._assert_status(InvoiceStatus.PENDING, "mark_failed")
        timestamp = now or _utcnow()
        self._status = InvoiceStatus.FAILED
        self._failed_at = timestamp
        self._record_event(
            InvoiceFailed(
                invoice_id=self._id,
                subscription_id=self._subscription_id,
                user_id=self._user_id,
                failed_at=timestamp,
            )
        )

    def refund(self, reason: str | None = None, now: datetime | None = None) -> None:
        """Refund a paid invoice.

        Pre-state: ``paid``.
        Post-state: ``refunded`` with ``refunded_at`` set.

        Args:
            reason: Optional reason for the refund (audit).

        Raises:
            InvoiceNotRefundable: If the invoice is not in ``paid``
                status.
        """
        if self._status != InvoiceStatus.PAID:
            raise InvoiceNotRefundable(self._id, self._status)
        timestamp = now or _utcnow()
        self._status = InvoiceStatus.REFUNDED
        self._refunded_at = timestamp
        self._refund_reason = reason
        self._record_event(
            InvoiceRefunded(
                invoice_id=self._id,
                subscription_id=self._subscription_id,
                user_id=self._user_id,
                refunded_at=timestamp,
                reason=reason,
            )
        )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Invoice(id={self._id}, subscription_id={self._subscription_id}, "
            f"amount={self._amount}, status={self._status!r}, "
            f"provider_invoice_id={self._provider_invoice_id!r})"
        )


__all__ = ["Invoice", "InvoiceStatus"]
