"""Billing context — BillingPlan entity.

The :class:`BillingPlan` is the entity describing a sellable plan: a
unique code, a versioned name and price, a billing period, an
entitlements dictionary, and an active flag.

The plan is **versioned**. Each new revision (a price change, an
entitlement change) produces a new ``BillingPlan`` row with the same
``code`` and an incremented ``version_number``. Old versions remain
immutable so historical invoices can be reproduced deterministically
(ADR-0011). A plan may be deprecated (removed from the catalogue)
without being deleted.

The plan is **not** an aggregate root; its lifecycle is supervised by
the Billing context's application services. It lives as a standalone
entity here because no single aggregate owns it — subscriptions
*reference* a plan by ID rather than owning it.

Invariants enforced:
- ``code`` is a non-empty string (1–64 chars).
- ``name`` is a non-empty string (1–200 chars).
- ``version_number`` is an int >= 1.
- ``entitlements`` is a dict (may be empty).
- ``price`` is a :class:`Money` value object (validated at
  construction).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.billing.events import BillingPlanCreated, BillingPlanDeprecated
from app.domain.billing.exceptions import BillingError
from app.domain.shared.ids import BillingPlanId
from app.domain.shared.kernel import (
    BillingPeriod,
    Entity,
    InvariantViolation,
)
from app.domain.shared.value_objects import Money


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class BillingPlan(Entity):
    """The BillingPlan entity.

    Holds the plan's identity (id, code, version), descriptive
    attributes (name, price, billing_period), entitlements, an active
    flag, and timestamps. All mutations go through methods on this
    class, which enforce invariants and emit domain events.

    The public constructor is intended for **reconstitution** from
    persistence. To create a *new* plan, use :meth:`BillingPlan.create`.
    """

    #: Maximum length of the plan code (e.g., ``"pro-monthly"``).
    MAX_CODE_LENGTH: int = 64

    #: Maximum length of the human-readable name.
    MAX_NAME_LENGTH: int = 200

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: BillingPlanId,
        code: str,
        version_number: int,
        name: str,
        price: Money,
        billing_period: BillingPeriod,
        entitlements: dict[str, Any] | None = None,
        is_active: bool = True,
        created_at: datetime | None = None,
        deprecated_at: datetime | None = None,
    ) -> None:
        self._domain_events: list[Any] = []
        self._id: BillingPlanId = id
        self._code: str = code
        self._version_number: int = version_number
        self._name: str = name
        self._price: Money = price
        self._billing_period: BillingPeriod = billing_period
        self._entitlements: dict[str, Any] = dict(entitlements) if entitlements else {}
        self._is_active: bool = bool(is_active)
        self._created_at: datetime = created_at or _utcnow()
        self._deprecated_at: datetime | None = deprecated_at
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
    def create(
        cls,
        code: str,
        name: str,
        price: Money,
        billing_period: BillingPeriod,
        entitlements: dict[str, Any] | None = None,
    ) -> BillingPlan:
        """Create a new BillingPlan at version 1, in ``active`` status.

        Args:
            code: A short, system-unique code (e.g., ``"pro-monthly"``).
            name: A human-readable name (e.g., ``"Pro — Monthly"``).
            price: A :class:`Money` value object with the plan's price.
            billing_period: The billing cadence
                (:class:`BillingPeriod.MONTHLY` or ``ANNUAL``).
            entitlements: A dict of entitlement keys → values
                (e.g., ``{"max_subjects": 5, "ai_credits": 1000}``).

        Returns:
            A newly created, un-persisted :class:`BillingPlan` at
            version 1 in ``active`` status. The caller must add it to
            the repository and call :meth:`collect_events` to publish
            the recorded events.

        Raises:
            InvariantViolation: If any field fails validation.
        """
        plan_id = BillingPlanId.generate()
        plan = cls(
            id=plan_id,
            code=code,
            version_number=1,
            name=name,
            price=price,
            billing_period=billing_period,
            entitlements=entitlements,
            is_active=True,
        )
        plan._record_event(
            BillingPlanCreated(
                plan_id=plan.id,
                code=plan.code,
                name=plan.name,
                price=plan.price,
                billing_period=plan.billing_period,
            )
        )
        return plan

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> BillingPlanId:
        """The plan's unique identifier."""
        return self._id

    @property
    def code(self) -> str:
        """The system-unique plan code."""
        return self._code

    @property
    def version_number(self) -> int:
        """The version number of this plan revision (>= 1)."""
        return self._version_number

    @property
    def name(self) -> str:
        """The human-readable plan name."""
        return self._name

    @property
    def price(self) -> Money:
        """The plan's :class:`Money` price."""
        return self._price

    @property
    def billing_period(self) -> BillingPeriod:
        """The billing cadence."""
        return self._billing_period

    @property
    def entitlements(self) -> dict[str, Any]:
        """The entitlement dict. Returns a copy."""
        return dict(self._entitlements)

    @property
    def is_active(self) -> bool:
        """True if the plan is in the catalogue (not deprecated)."""
        return self._is_active

    @property
    def created_at(self) -> datetime:
        """When this plan revision was created."""
        return self._created_at

    @property
    def deprecated_at(self) -> datetime | None:
        """When this plan was deprecated, or ``None`` if still active."""
        return self._deprecated_at

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants; raise on failure."""
        if not isinstance(self._code, str) or not self._code.strip():
            raise InvariantViolation("BillingPlan", "code must be a non-empty string")
        if len(self._code) > self.MAX_CODE_LENGTH:
            raise InvariantViolation(
                "BillingPlan",
                f"code must be at most {self.MAX_CODE_LENGTH} characters",
            )
        self._code = self._code.strip()

        if not isinstance(self._name, str) or not self._name.strip():
            raise InvariantViolation("BillingPlan", "name must be a non-empty string")
        if len(self._name) > self.MAX_NAME_LENGTH:
            raise InvariantViolation(
                "BillingPlan",
                f"name must be at most {self.MAX_NAME_LENGTH} characters",
            )
        self._name = self._name.strip()

        if not isinstance(self._version_number, int) or isinstance(
            self._version_number, bool
        ):
            raise InvariantViolation(
                "BillingPlan",
                "version_number must be an int",
            )
        if self._version_number < 1:
            raise InvariantViolation(
                "BillingPlan",
                f"version_number must be >= 1, got {self._version_number}",
            )

        if not isinstance(self._price, Money):
            raise InvariantViolation(
                "BillingPlan",
                f"price must be a Money value object, got {type(self._price).__name__}",
            )

        if not isinstance(self._billing_period, BillingPeriod):
            raise InvariantViolation(
                "BillingPlan",
                f"billing_period must be a BillingPeriod, got {type(self._billing_period).__name__}",
            )

        if not isinstance(self._entitlements, dict):
            raise InvariantViolation(
                "BillingPlan",
                "entitlements must be a dict",
            )

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def deprecate(self, now: datetime | None = None) -> None:
        """Mark this plan as deprecated (removed from the catalogue).

        Existing subscriptions remain in force; new subscriptions
        cannot start on a deprecated plan. Idempotent — calling it
        again when already deprecated is a no-op (no event recorded).
        """
        if not self._is_active:
            return
        timestamp = now or _utcnow()
        self._is_active = False
        self._deprecated_at = timestamp
        self._record_event(
            BillingPlanDeprecated(
                plan_id=self._id,
                deprecated_at=timestamp,
            )
        )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"BillingPlan(id={self._id}, code={self._code!r}, "
            f"version={self._version_number}, price={self._price}, "
            f"period={self._billing_period.value!r}, active={self._is_active})"
        )


__all__ = ["BillingPlan"]
