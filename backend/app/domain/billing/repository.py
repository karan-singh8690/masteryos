"""Billing context — abstract repository interfaces.

This module defines the *contracts* for loading and persisting the
Billing-context aggregates and entities. Each interface is an abstract
base class — no implementation is provided here. Concrete
implementations live in the infrastructure layer.

Async contract:
- All methods are ``async`` to match the async SQLAlchemy pattern the
  rest of the backend uses.
- The application layer ``await``s repository calls inside an async
  unit-of-work.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date

from app.domain.billing.billing_plan import BillingPlan
from app.domain.billing.invoice import Invoice
from app.domain.billing.subscription import Subscription
from app.domain.shared.ids import (
    BillingPlanId,
    InvoiceId,
    SubscriptionId,
    UserId,
)
from app.domain.shared.kernel import BillingPeriod, EntityNotFound


# ============================================================
# BillingPlan
# ============================================================


class BillingPlanRepository(ABC):
    """Abstract repository for the :class:`BillingPlan` entity.

    Implementations must:
    - Load a :class:`BillingPlan` or return ``None``.
    - Persist the entity on :meth:`save`.
    - Enforce ``code`` uniqueness at the version level (each
      ``(code, version_number)`` pair is unique). Multiple versions of
      the same code coexist for historical reproducibility.
    - Optionally enforce at most one ``active`` plan per ``code``
      (the application layer typically deprecates the old version
      before activating the new one).
    """

    @abstractmethod
    async def get_by_id(self, plan_id: BillingPlanId) -> BillingPlan | None:
        """Load a BillingPlan by ID.

        Returns the :class:`BillingPlan`, or ``None`` if no plan exists
        with that ID.
        """

    @abstractmethod
    async def get_by_code(
        self,
        code: str,
        *,
        version: int | None = None,
    ) -> BillingPlan | None:
        """Load a BillingPlan by code, optionally at a specific version.

        Args:
            code: The plan code (e.g., ``"pro-monthly"``).
            version: If ``None``, returns the *active* version of the
                plan (or the latest version if none is active). If a
                specific version is requested, returns that version.

        Returns:
            The matching :class:`BillingPlan`, or ``None`` if no plan
            exists with that code (and version).
        """

    @abstractmethod
    async def list_active(self) -> Sequence[BillingPlan]:
        """List all active (non-deprecated) plans.

        Returns:
            A sequence of :class:`BillingPlan` entities whose
            ``is_active`` flag is ``True``. Ordered by ``code``.
        """

    @abstractmethod
    async def add(self, plan: BillingPlan) -> None:
        """Add a *new* BillingPlan to the repository.

        Args:
            plan: The new :class:`BillingPlan` to persist.

        Raises:
            DuplicateEntity: If a plan with the same ``code`` and
                ``version_number`` already exists.
        """

    @abstractmethod
    async def save(self, plan: BillingPlan) -> None:
        """Persist changes to an *existing* BillingPlan.

        Args:
            plan: The modified :class:`BillingPlan` to persist.

        Raises:
            EntityNotFound: If the plan has been deleted by another
                transaction since it was loaded.
            DuplicateEntity: If the version is stale.
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, plan_id: BillingPlanId) -> BillingPlan:
        """Load a BillingPlan by ID, raising :class:`EntityNotFound` if absent."""
        plan = await self.get_by_id(plan_id)
        if plan is None:
            raise EntityNotFound("BillingPlan", plan_id)
        return plan


# ============================================================
# Subscription
# ============================================================


class SubscriptionRepository(ABC):
    """Abstract repository for the :class:`Subscription` aggregate.

    Implementations must:
    - Load the :class:`Subscription` or return ``None``.
    - Persist the full aggregate on :meth:`save`.
    - Enforce uniqueness of ``(user_id, status)`` for non-terminal
        statuses — a user may hold at most one ``active`` or
        ``past_due`` subscription.
    """

    @abstractmethod
    async def get_by_id(self, subscription_id: SubscriptionId) -> Subscription | None:
        """Load a Subscription by ID.

        Returns the fully reconstituted :class:`Subscription`
        aggregate, or ``None`` if no subscription exists with that ID.
        """

    @abstractmethod
    async def get_active_by_user(self, user_id: UserId) -> Subscription | None:
        """Load the user's currently-active-or-past-due subscription.

        A user may hold at most one subscription in a non-terminal
        status (``active``, ``past_due``, or ``canceled``). This method
        returns that subscription, or ``None`` if the user has none.

        Args:
            user_id: The user to look up.

        Returns:
            The user's :class:`Subscription`, or ``None``.
        """

    @abstractmethod
    async def list_by_user(self, user_id: UserId) -> Sequence[Subscription]:
        """List all of a user's subscriptions (active, canceled, expired).

        Ordered by ``created_at`` descending.
        """

    @abstractmethod
    async def list_expiring(
        self,
        *,
        on_or_before: date,
        limit: int = 100,
    ) -> Sequence[Subscription]:
        """List active or canceled subscriptions expiring on or before a date.

        Used by the renewal/expiry job to find subscriptions whose
        ``current_period_end`` is on or before the given date.

        Args:
            on_or_before: The cutoff date (inclusive).
            limit: Maximum number of subscriptions to return.

        Returns:
            A sequence of :class:`Subscription` aggregates whose
            ``current_period_end <= on_or_before`` and whose status is
            ``active``, ``past_due``, or ``canceled``.
        """

    @abstractmethod
    async def add(self, subscription: Subscription) -> None:
        """Add a *new* Subscription to the repository.

        Args:
            subscription: The new :class:`Subscription` to persist.

        Raises:
            DuplicateEntity: If the user already has a non-terminal
                subscription.
        """

    @abstractmethod
    async def save(self, subscription: Subscription) -> None:
        """Persist changes to an *existing* Subscription.

        Args:
            subscription: The modified :class:`Subscription` to
                persist.

        Raises:
            EntityNotFound: If the subscription has been deleted by
                another transaction since it was loaded.
            DuplicateEntity: If the version is stale.
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, subscription_id: SubscriptionId) -> Subscription:
        """Load a Subscription by ID, raising :class:`EntityNotFound` if absent."""
        sub = await self.get_by_id(subscription_id)
        if sub is None:
            raise EntityNotFound("Subscription", subscription_id)
        return sub


# ============================================================
# Invoice
# ============================================================


class InvoiceRepository(ABC):
    """Abstract repository for the :class:`Invoice` entity.

    Implementations must:
    - Load the :class:`Invoice` or return ``None``.
    - Persist the entity on :meth:`save`.
    - Enforce uniqueness of ``provider_invoice_id`` per
        ``payment_provider`` (each provider's invoice ID must be
        unique within that provider's namespace).
    """

    @abstractmethod
    async def get_by_id(self, invoice_id: InvoiceId) -> Invoice | None:
        """Load an Invoice by ID.

        Returns the :class:`Invoice`, or ``None`` if no invoice exists
        with that ID.
        """

    @abstractmethod
    async def get_by_provider_invoice_id(
        self,
        provider: str,
        provider_invoice_id: str,
    ) -> Invoice | None:
        """Load an Invoice by its provider-side invoice ID.

        Used by webhook handlers to find the invoice corresponding to a
        provider event.

        Args:
            provider: The payment provider name (e.g., ``"stripe"``).
            provider_invoice_id: The provider's invoice ID.

        Returns:
            The matching :class:`Invoice`, or ``None`` if not found.
        """

    @abstractmethod
    async def list_by_subscription(
        self,
        subscription_id: SubscriptionId,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Invoice]:
        """List invoices for a subscription, most recent first.
        """

    @abstractmethod
    async def list_by_user(
        self,
        user_id: UserId,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Invoice]:
        """List invoices for a user, most recent first.
        """

    @abstractmethod
    async def list_pending(self, *, limit: int = 100) -> Sequence[Invoice]:
        """List invoices in ``pending`` status (for payment-retry jobs).
        """

    @abstractmethod
    async def add(self, invoice: Invoice) -> None:
        """Add a *new* Invoice to the repository.

        Args:
            invoice: The new :class:`Invoice` to persist.

        Raises:
            DuplicateEntity: If an invoice with the same
                ``provider_invoice_id`` already exists for the same
                provider.
        """

    @abstractmethod
    async def save(self, invoice: Invoice) -> None:
        """Persist changes to an *existing* Invoice.

        Args:
            invoice: The modified :class:`Invoice` to persist.

        Raises:
            EntityNotFound: If the invoice has been deleted by another
                transaction since it was loaded.
            DuplicateEntity: If the version is stale.
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, invoice_id: InvoiceId) -> Invoice:
        """Load an Invoice by ID, raising :class:`EntityNotFound` if absent."""
        invoice = await self.get_by_id(invoice_id)
        if invoice is None:
            raise EntityNotFound("Invoice", invoice_id)
        return invoice


__all__ = [
    "BillingPlanRepository",
    "InvoiceRepository",
    "SubscriptionRepository",
]
