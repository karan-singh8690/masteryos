"""Billing context — Subscription aggregate root.

The :class:`Subscription` is the aggregate root of a user's billing
relationship. It tracks the active plan, the current billing period,
the payment provider's subscription ID, and the lifecycle state.

Lifecycle (state machine)::

    ACTIVE ──renew()────────────► ACTIVE  (new period_end)
       │
       ├──cancel()──► CANCELED ──expire()──► EXPIRED
       │
       ├──mark_past_due()──► PAST_DUE ──recover()──► ACTIVE
       │                        │
       │                        └──cancel()──► CANCELED ──► EXPIRED
       │
       └──expire()──────────────────────────► EXPIRED

``EXPIRED`` is terminal. ``ACTIVE`` is the only state from which
``renew``, ``upgrade``, and ``downgrade`` may be called. ``PAST_DUE``
allows ``recover`` and ``cancel`` only — an upgrade while past-due is
rejected (the dunning workflow must complete first).

Invariants enforced:
- ``current_period_end`` must be strictly after ``current_period_start``.
- ``payment_provider`` must be a non-empty string.
- ``upgrade`` must move to a plan with a price >= the current plan's
  price (within the same currency). The actual price comparison is
  done by the application service that loads both plans — the
  aggregate accepts the new plan ID and records the event.
- ``downgrade`` is recorded as *scheduled* (effective at period end);
  the actual plan swap happens via :meth:`renew` at the period boundary.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from app.domain.billing.events import (
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
    BillingError,
    InvalidDowngrade,
    InvalidUpgrade,
)
from app.domain.shared.ids import BillingPlanId, SubscriptionId, UserId
from app.domain.shared.kernel import (
    AggregateRoot,
    InvalidStateTransition,
    InvariantViolation,
    SubscriptionStatus,
)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class Subscription(AggregateRoot):
    """The Subscription aggregate root.

    Holds the subscription's identity, the user and plan it belongs to,
    the current billing period, the payment provider's subscription ID,
    and lifecycle state. All mutations go through methods on this
    class, which enforce invariants and emit domain events via
    :meth:`AggregateRoot._record_event`.

    The public constructor is intended for **reconstitution** from
    persistence. To create a *new* subscription, use
    :meth:`Subscription.subscribe`.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: SubscriptionId,
        user_id: UserId,
        billing_plan_id: BillingPlanId,
        status: SubscriptionStatus,
        current_period_start: date,
        current_period_end: date,
        payment_provider: str,
        provider_subscription_id: str | None = None,
        scheduled_downgrade_plan_id: BillingPlanId | None = None,
        canceled_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self._id: SubscriptionId = id
        self._user_id: UserId = user_id
        self._billing_plan_id: BillingPlanId = billing_plan_id
        self._status: SubscriptionStatus = status
        self._current_period_start: date = current_period_start
        self._current_period_end: date = current_period_end
        self._payment_provider: str = payment_provider
        self._provider_subscription_id: str | None = provider_subscription_id
        self._scheduled_downgrade_plan_id: BillingPlanId | None = scheduled_downgrade_plan_id
        self._canceled_at: datetime | None = canceled_at
        now = _utcnow()
        self._created_at: datetime = created_at or now
        self._updated_at: datetime = updated_at or now
        self._validate_invariants()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def subscribe(
        cls,
        user_id: UserId,
        billing_plan_id: BillingPlanId,
        period_start: date,
        period_end: date,
        provider: str,
        provider_sub_id: str | None = None,
    ) -> Subscription:
        """Create a new subscription in ``active`` status.

        Args:
            user_id: The user subscribing.
            billing_plan_id: The plan being subscribed to.
            period_start: The first day of the first billing period.
            period_end: The last day of the first billing period
                (exclusive in some providers; the domain treats both
                bounds as inclusive dates and only requires
                ``period_end > period_start``).
            provider: The payment provider name (e.g., ``"stripe"``).
            provider_sub_id: The provider's subscription ID, if any.

        Returns:
            A newly created, un-persisted :class:`Subscription` in
            ``active`` status. The caller must add it to the
            repository and call :meth:`collect_events` to publish the
            recorded events.

        Raises:
            InvariantViolation: If any field fails validation.
        """
        sub_id = SubscriptionId.generate()
        sub = cls(
            id=sub_id,
            user_id=user_id,
            billing_plan_id=billing_plan_id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=period_start,
            current_period_end=period_end,
            payment_provider=provider,
            provider_subscription_id=provider_sub_id,
        )
        sub._record_event(
            SubscriptionActivated(
                subscription_id=sub.id,
                user_id=user_id,
                billing_plan_id=billing_plan_id,
                current_period_start=period_start,
                current_period_end=period_end,
                payment_provider=provider,
            )
        )
        return sub

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> SubscriptionId:
        """The subscription's unique identifier."""
        return self._id

    @property
    def user_id(self) -> UserId:
        """The user who owns this subscription."""
        return self._user_id

    @property
    def billing_plan_id(self) -> BillingPlanId:
        """The currently-billed plan ID."""
        return self._billing_plan_id

    @property
    def status(self) -> SubscriptionStatus:
        """The subscription's lifecycle status."""
        return self._status

    @property
    def current_period_start(self) -> date:
        """The first day of the current billing period."""
        return self._current_period_start

    @property
    def current_period_end(self) -> date:
        """The last day of the current billing period."""
        return self._current_period_end

    @property
    def payment_provider(self) -> str:
        """The payment provider name (e.g., ``"stripe"``)."""
        return self._payment_provider

    @property
    def provider_subscription_id(self) -> str | None:
        """The provider's subscription ID, or ``None`` if not yet synced."""
        return self._provider_subscription_id

    @property
    def scheduled_downgrade_plan_id(self) -> BillingPlanId | None:
        """A pending downgrade target, or ``None``.

        Set by :meth:`downgrade`; cleared by :meth:`renew` when the
        downgrade takes effect at the period boundary.
        """
        return self._scheduled_downgrade_plan_id

    @property
    def canceled_at(self) -> datetime | None:
        """When the subscription was canceled, or ``None``."""
        return self._canceled_at

    @property
    def created_at(self) -> datetime:
        """When the subscription was created."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """When the subscription was last modified."""
        return self._updated_at

    @property
    def is_active(self) -> bool:
        """True if the subscription is in ``active`` status."""
        return self._status == SubscriptionStatus.ACTIVE

    @property
    def is_past_due(self) -> bool:
        """True if the subscription is in ``past_due`` status."""
        return self._status == SubscriptionStatus.PAST_DUE

    @property
    def is_canceled(self) -> bool:
        """True if the subscription is in ``canceled`` status."""
        return self._status == SubscriptionStatus.CANCELED

    @property
    def is_expired(self) -> bool:
        """True if the subscription is in ``expired`` status."""
        return self._status == SubscriptionStatus.EXPIRED

    @property
    def has_scheduled_downgrade(self) -> bool:
        """True if a downgrade is pending at the period boundary."""
        return self._scheduled_downgrade_plan_id is not None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants; raise on failure."""
        if not isinstance(self._user_id, UserId):
            raise InvariantViolation(
                "Subscription",
                f"user_id must be a UserId, got {type(self._user_id).__name__}",
            )
        if not isinstance(self._billing_plan_id, BillingPlanId):
            raise InvariantViolation(
                "Subscription",
                f"billing_plan_id must be a BillingPlanId, got {type(self._billing_plan_id).__name__}",
            )
        if not isinstance(self._status, SubscriptionStatus):
            raise InvariantViolation(
                "Subscription",
                f"status must be a SubscriptionStatus, got {type(self._status).__name__}",
            )
        if not isinstance(self._current_period_start, date) or isinstance(
            self._current_period_start, datetime
        ):
            raise InvariantViolation(
                "Subscription",
                "current_period_start must be a date (not datetime)",
            )
        if not isinstance(self._current_period_end, date) or isinstance(
            self._current_period_end, datetime
        ):
            raise InvariantViolation(
                "Subscription",
                "current_period_end must be a date (not datetime)",
            )
        if self._current_period_end <= self._current_period_start:
            raise InvariantViolation(
                "Subscription",
                f"current_period_end ({self._current_period_end}) must be strictly after "
                f"current_period_start ({self._current_period_start})",
            )
        if not isinstance(self._payment_provider, str) or not self._payment_provider.strip():
            raise InvariantViolation(
                "Subscription",
                "payment_provider must be a non-empty string",
            )
        self._payment_provider = self._payment_provider.strip()
        if self._provider_subscription_id is not None and (
            not isinstance(self._provider_subscription_id, str)
            or not self._provider_subscription_id.strip()
        ):
            raise InvariantViolation(
                "Subscription",
                "provider_subscription_id must be None or a non-empty string",
            )

    def _touch(self, now: datetime | None = None) -> None:
        """Update the ``updated_at`` timestamp."""
        self._updated_at = now or _utcnow()

    def _assert_status(self, expected: SubscriptionStatus, action: str) -> None:
        """Raise :class:`InvalidStateTransition` unless in ``expected`` status."""
        if self._status != expected:
            raise InvalidStateTransition(
                entity="Subscription",
                current_state=self._status.value,
                attempted_action=action,
            )

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def renew(self, new_period_end: date, now: datetime | None = None) -> None:
        """Renew the subscription for the next billing period.

        Pre-state: ``active``.
        Post-state: ``active`` with a new ``current_period_start`` (the
        day after the previous ``current_period_end``) and
        ``current_period_end = new_period_end``. If a downgrade is
        pending, the plan swap takes effect here (the
        ``scheduled_downgrade_plan_id`` becomes the new
        ``billing_plan_id`` and the pending field is cleared).

        Args:
            new_period_end: The last day of the new billing period.
                Must be strictly after the new ``current_period_start``.

        Raises:
            InvalidStateTransition: If the subscription is not in
                ``active`` status.
            InvariantViolation: If ``new_period_end`` is not after the
                new ``current_period_start``.
        """
        self._assert_status(SubscriptionStatus.ACTIVE, "renew")
        new_period_start = self._current_period_end
        if not isinstance(new_period_end, date) or isinstance(new_period_end, datetime):
            raise InvariantViolation(
                "Subscription",
                "new_period_end must be a date (not datetime)",
            )
        if new_period_end <= new_period_start:
            raise InvariantViolation(
                "Subscription",
                f"new_period_end ({new_period_end}) must be strictly after "
                f"the new period start ({new_period_start})",
            )

        # Apply a pending downgrade, if any.
        previous_plan_id = self._billing_plan_id
        if self._scheduled_downgrade_plan_id is not None:
            self._billing_plan_id = self._scheduled_downgrade_plan_id
            self._scheduled_downgrade_plan_id = None

        self._current_period_start = new_period_start
        self._current_period_end = new_period_end
        timestamp = now or _utcnow()
        self._touch(timestamp)
        self._record_event(
            SubscriptionRenewed(
                subscription_id=self._id,
                user_id=self._user_id,
                billing_plan_id=self._billing_plan_id,
                new_period_end=new_period_end,
            )
        )

    def upgrade(self, new_plan_id: BillingPlanId, now: datetime | None = None) -> None:
        """Upgrade the subscription to a higher-tier plan immediately.

        Pre-state: ``active``.
        Post-state: ``active`` with ``billing_plan_id = new_plan_id``.

        The aggregate cannot compare prices directly — it does not load
        the plan objects. The application service is responsible for
        verifying that the new plan's price is >= the current plan's
        price (within the same currency) and raising
        :class:`InvalidUpgrade` if not. To support that, this method
        accepts the new plan ID and assumes the caller has done the
        comparison. If the caller passes the same plan ID as the
        current plan, :class:`InvalidUpgrade` is raised here.

        Args:
            new_plan_id: The plan to upgrade to.

        Raises:
            InvalidStateTransition: If the subscription is not in
                ``active`` status.
            InvalidUpgrade: If ``new_plan_id`` is the same as the
                current plan ID, or if a downgrade is pending (clear
                it first via :meth:`renew`).
        """
        self._assert_status(SubscriptionStatus.ACTIVE, "upgrade")
        if new_plan_id == self._billing_plan_id:
            raise InvalidUpgrade(
                self._billing_plan_id,
                new_plan_id,
                "new plan is the same as the current plan",
            )
        if self._scheduled_downgrade_plan_id is not None:
            raise InvalidUpgrade(
                self._billing_plan_id,
                new_plan_id,
                "a downgrade is pending; renew or clear it first",
            )
        previous_plan_id = self._billing_plan_id
        self._billing_plan_id = new_plan_id
        timestamp = now or _utcnow()
        self._touch(timestamp)
        self._record_event(
            SubscriptionUpgraded(
                subscription_id=self._id,
                user_id=self._user_id,
                previous_plan_id=previous_plan_id,
                new_plan_id=new_plan_id,
            )
        )

    def downgrade(self, new_plan_id: BillingPlanId, now: datetime | None = None) -> None:
        """Schedule a downgrade to a lower-tier plan, effective at period end.

        Pre-state: ``active``.
        Post-state: ``active`` with
        ``scheduled_downgrade_plan_id = new_plan_id``. The actual plan
        swap happens via :meth:`renew` at the period boundary.

        As with :meth:`upgrade`, the price comparison is the
        application service's responsibility. This method rejects
        same-plan downgrades and downgrades while a downgrade is
        already pending.

        Args:
            new_plan_id: The plan to downgrade to at the period end.

        Raises:
            InvalidStateTransition: If the subscription is not in
                ``active`` status.
            InvalidDowngrade: If ``new_plan_id`` is the same as the
                current plan ID, or if a downgrade is already pending.
        """
        self._assert_status(SubscriptionStatus.ACTIVE, "downgrade")
        if new_plan_id == self._billing_plan_id:
            raise InvalidDowngrade(
                self._billing_plan_id,
                new_plan_id,
                "new plan is the same as the current plan",
            )
        if self._scheduled_downgrade_plan_id is not None:
            raise InvalidDowngrade(
                self._billing_plan_id,
                new_plan_id,
                "a downgrade is already pending",
            )
        timestamp = now or _utcnow()
        self._scheduled_downgrade_plan_id = new_plan_id
        self._touch(timestamp)
        self._record_event(
            SubscriptionDowngradeScheduled(
                subscription_id=self._id,
                user_id=self._user_id,
                current_plan_id=self._billing_plan_id,
                scheduled_plan_id=new_plan_id,
                effective_at=self._current_period_end,
            )
        )

    def cancel(self, now: datetime | None = None) -> None:
        """Cancel the subscription, effective at the end of the current period.

        Pre-state: ``active`` or ``past_due``.
        Post-state: ``canceled`` with ``canceled_at`` set. Entitlements
        remain in force until ``current_period_end``; the
        :meth:`expire` transition is triggered separately at that
        point.

        Raises:
            InvalidStateTransition: If the subscription is in
                ``canceled`` or ``expired`` status.
        """
        if self._status in (SubscriptionStatus.CANCELED, SubscriptionStatus.EXPIRED):
            raise InvalidStateTransition(
                entity="Subscription",
                current_state=self._status.value,
                attempted_action="cancel",
            )
        timestamp = now or _utcnow()
        self._status = SubscriptionStatus.CANCELED
        self._canceled_at = timestamp
        self._scheduled_downgrade_plan_id = None  # a cancellation supersedes a downgrade
        self._touch(timestamp)
        self._record_event(
            SubscriptionCanceled(
                subscription_id=self._id,
                user_id=self._user_id,
                canceled_at=timestamp,
                effective_at=self._current_period_end,
            )
        )

    def mark_past_due(self, now: datetime | None = None) -> None:
        """Transition the subscription from ``active`` to ``past_due``.

        Pre-state: ``active``.
        Post-state: ``past_due``. The dunning workflow takes over;
        entitlements typically remain in force during the grace window.

        Raises:
            InvalidStateTransition: If the subscription is not in
                ``active`` status.
        """
        self._assert_status(SubscriptionStatus.ACTIVE, "mark_past_due")
        timestamp = now or _utcnow()
        self._status = SubscriptionStatus.PAST_DUE
        self._touch(timestamp)
        self._record_event(
            SubscriptionPastDue(
                subscription_id=self._id,
                user_id=self._user_id,
                billing_plan_id=self._billing_plan_id,
            )
        )

    def recover(self, now: datetime | None = None) -> None:
        """Recover a past-due subscription back to ``active``.

        Pre-state: ``past_due``.
        Post-state: ``active``. The dunning workflow is cancelled by
        the subscriber listening to the emitted event.

        Raises:
            InvalidStateTransition: If the subscription is not in
                ``past_due`` status.
        """
        self._assert_status(SubscriptionStatus.PAST_DUE, "recover")
        timestamp = now or _utcnow()
        self._status = SubscriptionStatus.ACTIVE
        self._touch(timestamp)
        self._record_event(
            SubscriptionRecovered(
                subscription_id=self._id,
                user_id=self._user_id,
                billing_plan_id=self._billing_plan_id,
            )
        )

    def expire(self, now: datetime | None = None) -> None:
        """Transition the subscription to terminal ``expired`` status.

        Pre-state: ``active``, ``past_due``, or ``canceled``.
        Post-state: ``expired`` (terminal). Entitlements should be
        revoked by subscribers listening to the emitted event.

        Raises:
            InvalidStateTransition: If the subscription is already
                ``expired``.
        """
        if self._status == SubscriptionStatus.EXPIRED:
            raise InvalidStateTransition(
                entity="Subscription",
                current_state=self._status.value,
                attempted_action="expire",
            )
        timestamp = now or _utcnow()
        previous_status = self._status
        self._status = SubscriptionStatus.EXPIRED
        self._scheduled_downgrade_plan_id = None
        self._touch(timestamp)
        self._record_event(
            SubscriptionExpired(
                subscription_id=self._id,
                user_id=self._user_id,
                billing_plan_id=self._billing_plan_id,
                expired_at=timestamp,
            )
        )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Subscription(id={self._id}, user_id={self._user_id}, "
            f"plan_id={self._billing_plan_id}, status={self._status.value!r}, "
            f"period_end={self._current_period_end})"
        )


__all__ = ["Subscription"]
