"""Comprehensive unit tests for the Subscription aggregate (Billing context).

Tests cover:
- ``Subscription.subscribe()`` factory creates an ACTIVE subscription
- State machine: active → past_due → active/canceled → expired
- ``renew``, ``upgrade``, ``downgrade``, ``cancel``, ``recover``, ``expire``
- ``downgrade`` schedules a plan swap effective at period end
- ``renew`` applies the scheduled downgrade
- ``upgrade`` rejects a pending downgrade
- Invariants (period_end > period_start; non-empty provider)
- Domain events for each transition

These tests exercise only the pure-Python domain layer — no database,
HTTP or infrastructure.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

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
from app.domain.billing.exceptions import InvalidDowngrade, InvalidUpgrade
from app.domain.billing.subscription import Subscription
from app.domain.shared.ids import BillingPlanId, SubscriptionId, UserId
from app.domain.shared.kernel import (
    InvariantViolation,
    InvalidStateTransition,
    SubscriptionStatus,
)


# ============================================================
# Helpers
# ============================================================


def _user_id() -> UserId:
    return UserId.generate()


def _plan_id() -> BillingPlanId:
    return BillingPlanId.generate()


def _subscribe(
    *,
    plan_id: BillingPlanId | None = None,
    period_start: date = date(2024, 1, 1),
    period_end: date = date(2024, 2, 1),
    provider: str = "stripe",
    provider_sub_id: str | None = "sub_abc",
) -> Subscription:
    return Subscription.subscribe(
        user_id=_user_id(),
        billing_plan_id=plan_id or _plan_id(),
        period_start=period_start,
        period_end=period_end,
        provider=provider,
        provider_sub_id=provider_sub_id,
    )


# ============================================================
# Factory
# ============================================================


class TestSubscriptionSubscribe:
    """Tests for the ``Subscription.subscribe()`` factory."""

    def test_subscribe_creates_active_subscription(self) -> None:
        s = _subscribe()
        assert s.status == SubscriptionStatus.ACTIVE
        assert s.is_active is True

    def test_subscribe_generates_id(self) -> None:
        s = _subscribe()
        assert isinstance(s.id, SubscriptionId)

    def test_subscribe_sets_user_and_plan(self) -> None:
        uid = _user_id()
        pid = _plan_id()
        s = Subscription.subscribe(
            user_id=uid,
            billing_plan_id=pid,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 2, 1),
            provider="stripe",
        )
        assert s.user_id == uid
        assert s.billing_plan_id == pid

    def test_subscribe_sets_period_bounds(self) -> None:
        s = _subscribe(period_start=date(2024, 1, 1), period_end=date(2024, 2, 1))
        assert s.current_period_start == date(2024, 1, 1)
        assert s.current_period_end == date(2024, 2, 1)

    def test_subscribe_sets_provider(self) -> None:
        s = _subscribe(provider="stripe")
        assert s.payment_provider == "stripe"

    def test_subscribe_sets_provider_subscription_id(self) -> None:
        s = _subscribe(provider_sub_id="sub_xyz")
        assert s.provider_subscription_id == "sub_xyz"

    def test_subscribe_default_no_scheduled_downgrade(self) -> None:
        s = _subscribe()
        assert s.scheduled_downgrade_plan_id is None
        assert s.has_scheduled_downgrade is False

    def test_subscribe_default_no_canceled_at(self) -> None:
        s = _subscribe()
        assert s.canceled_at is None

    def test_subscribe_records_subscription_activated_event(self) -> None:
        s = _subscribe()
        events = s.collect_events()
        assert len(events) == 1
        evt = events[0]
        assert isinstance(evt, SubscriptionActivated)
        assert evt.subscription_id == s.id

    def test_subscribe_rejects_period_end_not_after_start(self) -> None:
        with pytest.raises(InvariantViolation):
            Subscription.subscribe(
                user_id=_user_id(),
                billing_plan_id=_plan_id(),
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 1),  # equal → not strictly after
                provider="stripe",
            )

    def test_subscribe_rejects_empty_provider(self) -> None:
        with pytest.raises(InvariantViolation):
            Subscription.subscribe(
                user_id=_user_id(),
                billing_plan_id=_plan_id(),
                period_start=date(2024, 1, 1),
                period_end=date(2024, 2, 1),
                provider="",
            )


# ============================================================
# renew
# ============================================================


class TestSubscriptionRenew:
    """Tests for ``renew()``."""

    def test_renew_keeps_active_status(self) -> None:
        s = _subscribe(period_start=date(2024, 1, 1), period_end=date(2024, 2, 1))
        s.renew(new_period_end=date(2024, 3, 1))
        assert s.status == SubscriptionStatus.ACTIVE

    def test_renew_advances_period_bounds(self) -> None:
        s = _subscribe(period_start=date(2024, 1, 1), period_end=date(2024, 2, 1))
        s.renew(new_period_end=date(2024, 3, 1))
        # new period_start = old period_end
        assert s.current_period_start == date(2024, 2, 1)
        assert s.current_period_end == date(2024, 3, 1)

    def test_renew_records_event(self) -> None:
        s = _subscribe()
        s.clear_events()
        s.renew(new_period_end=date(2024, 3, 1))
        events = s.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], SubscriptionRenewed)

    def test_renew_applies_scheduled_downgrade(self) -> None:
        """A scheduled downgrade takes effect at renew time."""
        s = _subscribe()
        original_plan = s.billing_plan_id
        new_plan = _plan_id()
        s.downgrade(new_plan)
        assert s.has_scheduled_downgrade is True
        s.renew(new_period_end=date(2024, 3, 1))
        assert s.billing_plan_id == new_plan
        assert s.has_scheduled_downgrade is False
        assert s.billing_plan_id != original_plan

    def test_renew_when_past_due_raises(self) -> None:
        s = _subscribe()
        s.mark_past_due()
        with pytest.raises(InvalidStateTransition):
            s.renew(new_period_end=date(2024, 3, 1))

    def test_renew_when_canceled_raises(self) -> None:
        s = _subscribe()
        s.cancel()
        with pytest.raises(InvalidStateTransition):
            s.renew(new_period_end=date(2024, 3, 1))

    def test_renew_rejects_new_period_end_not_after_new_start(self) -> None:
        s = _subscribe(period_start=date(2024, 1, 1), period_end=date(2024, 2, 1))
        with pytest.raises(InvariantViolation):
            # new_period_end == new_period_start (which is old period_end)
            s.renew(new_period_end=date(2024, 2, 1))


# ============================================================
# upgrade
# ============================================================


class TestSubscriptionUpgrade:
    """Tests for ``upgrade()``."""

    def test_upgrade_changes_plan_immediately(self) -> None:
        s = _subscribe()
        original = s.billing_plan_id
        new_plan = _plan_id()
        s.upgrade(new_plan)
        assert s.billing_plan_id == new_plan
        assert s.billing_plan_id != original

    def test_upgrade_keeps_active_status(self) -> None:
        s = _subscribe()
        s.upgrade(_plan_id())
        assert s.status == SubscriptionStatus.ACTIVE

    def test_upgrade_records_event_with_previous_and_new(self) -> None:
        s = _subscribe()
        original = s.billing_plan_id
        new_plan = _plan_id()
        s.clear_events()
        s.upgrade(new_plan)
        events = s.collect_events()
        assert len(events) == 1
        evt = events[0]
        assert isinstance(evt, SubscriptionUpgraded)
        assert evt.previous_plan_id == original
        assert evt.new_plan_id == new_plan

    def test_upgrade_to_same_plan_raises(self) -> None:
        s = _subscribe()
        with pytest.raises(InvalidUpgrade):
            s.upgrade(s.billing_plan_id)

    def test_upgrade_when_past_due_raises(self) -> None:
        s = _subscribe()
        s.mark_past_due()
        with pytest.raises(InvalidStateTransition):
            s.upgrade(_plan_id())

    def test_upgrade_when_canceled_raises(self) -> None:
        s = _subscribe()
        s.cancel()
        with pytest.raises(InvalidStateTransition):
            s.upgrade(_plan_id())

    def test_upgrade_with_pending_downgrade_raises(self) -> None:
        s = _subscribe()
        s.downgrade(_plan_id())
        with pytest.raises(InvalidUpgrade):
            s.upgrade(_plan_id())


# ============================================================
# downgrade
# ============================================================


class TestSubscriptionDowngrade:
    """Tests for ``downgrade()``."""

    def test_downgrade_schedules_plan_swap(self) -> None:
        s = _subscribe()
        original = s.billing_plan_id
        new_plan = _plan_id()
        s.downgrade(new_plan)
        assert s.scheduled_downgrade_plan_id == new_plan
        assert s.has_scheduled_downgrade is True
        # Current plan unchanged until renew
        assert s.billing_plan_id == original

    def test_downgrade_records_event(self) -> None:
        s = _subscribe()
        original = s.billing_plan_id
        new_plan = _plan_id()
        s.clear_events()
        s.downgrade(new_plan)
        events = s.collect_events()
        assert len(events) == 1
        evt = events[0]
        assert isinstance(evt, SubscriptionDowngradeScheduled)
        assert evt.current_plan_id == original
        assert evt.scheduled_plan_id == new_plan

    def test_downgrade_to_same_plan_raises(self) -> None:
        s = _subscribe()
        with pytest.raises(InvalidDowngrade):
            s.downgrade(s.billing_plan_id)

    def test_downgrade_twice_raises(self) -> None:
        s = _subscribe()
        s.downgrade(_plan_id())
        with pytest.raises(InvalidDowngrade):
            s.downgrade(_plan_id())

    def test_downgrade_when_past_due_raises(self) -> None:
        s = _subscribe()
        s.mark_past_due()
        with pytest.raises(InvalidStateTransition):
            s.downgrade(_plan_id())

    def test_downgrade_when_canceled_raises(self) -> None:
        s = _subscribe()
        s.cancel()
        with pytest.raises(InvalidStateTransition):
            s.downgrade(_plan_id())

    def test_downgrade_effective_at_period_end(self) -> None:
        s = _subscribe(period_end=date(2024, 2, 1))
        s.downgrade(_plan_id())
        events = s.collect_events()
        evt = next(e for e in events if isinstance(e, SubscriptionDowngradeScheduled))
        assert evt.effective_at == date(2024, 2, 1)


# ============================================================
# cancel
# ============================================================


class TestSubscriptionCancel:
    """Tests for ``cancel()``."""

    def test_cancel_from_active_transitions_to_canceled(self) -> None:
        s = _subscribe()
        s.cancel()
        assert s.status == SubscriptionStatus.CANCELED
        assert s.is_canceled is True

    def test_cancel_from_past_due_transitions_to_canceled(self) -> None:
        s = _subscribe()
        s.mark_past_due()
        s.cancel()
        assert s.status == SubscriptionStatus.CANCELED

    def test_cancel_sets_canceled_at(self) -> None:
        s = _subscribe()
        when = datetime(2024, 6, 1, tzinfo=UTC)
        s.cancel(now=when)
        assert s.canceled_at == when

    def test_cancel_clears_scheduled_downgrade(self) -> None:
        """A cancellation supersedes a pending downgrade."""
        s = _subscribe()
        s.downgrade(_plan_id())
        s.cancel()
        assert s.has_scheduled_downgrade is False

    def test_cancel_records_event_with_effective_at(self) -> None:
        s = _subscribe(period_end=date(2024, 2, 1))
        s.clear_events()
        s.cancel()
        events = s.collect_events()
        assert len(events) == 1
        evt = events[0]
        assert isinstance(evt, SubscriptionCanceled)
        assert evt.effective_at == date(2024, 2, 1)

    def test_cancel_when_canceled_raises(self) -> None:
        s = _subscribe()
        s.cancel()
        with pytest.raises(InvalidStateTransition):
            s.cancel()

    def test_cancel_when_expired_raises(self) -> None:
        s = _subscribe()
        s.expire()
        with pytest.raises(InvalidStateTransition):
            s.cancel()


# ============================================================
# mark_past_due / recover
# ============================================================


class TestSubscriptionPastDueAndRecover:
    """Tests for ``mark_past_due()`` and ``recover()``."""

    def test_mark_past_due_transitions_from_active(self) -> None:
        s = _subscribe()
        s.mark_past_due()
        assert s.status == SubscriptionStatus.PAST_DUE
        assert s.is_past_due is True

    def test_mark_past_due_records_event(self) -> None:
        s = _subscribe()
        s.clear_events()
        s.mark_past_due()
        events = s.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], SubscriptionPastDue)

    def test_mark_past_due_when_past_due_raises(self) -> None:
        s = _subscribe()
        s.mark_past_due()
        with pytest.raises(InvalidStateTransition):
            s.mark_past_due()

    def test_mark_past_due_when_canceled_raises(self) -> None:
        s = _subscribe()
        s.cancel()
        with pytest.raises(InvalidStateTransition):
            s.mark_past_due()

    def test_recover_transitions_from_past_due_to_active(self) -> None:
        s = _subscribe()
        s.mark_past_due()
        s.recover()
        assert s.status == SubscriptionStatus.ACTIVE

    def test_recover_records_event(self) -> None:
        s = _subscribe()
        s.mark_past_due()
        s.clear_events()
        s.recover()
        events = s.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], SubscriptionRecovered)

    def test_recover_when_active_raises(self) -> None:
        s = _subscribe()
        with pytest.raises(InvalidStateTransition):
            s.recover()

    def test_recover_when_canceled_raises(self) -> None:
        s = _subscribe()
        s.cancel()
        with pytest.raises(InvalidStateTransition):
            s.recover()


# ============================================================
# expire
# ============================================================


class TestSubscriptionExpire:
    """Tests for ``expire()``."""

    @pytest.mark.parametrize(
        "pre_state_setup",
        [
            lambda s: None,  # ACTIVE → EXPIRED
            lambda s: s.mark_past_due(),  # PAST_DUE → EXPIRED
            lambda s: s.cancel(),  # CANCELED → EXPIRED
        ],
    )
    def test_expire_from_allowed_states(self, pre_state_setup) -> None:
        s = _subscribe()
        pre_state_setup(s)
        s.expire()
        assert s.status == SubscriptionStatus.EXPIRED
        assert s.is_expired is True

    def test_expire_clears_scheduled_downgrade(self) -> None:
        s = _subscribe()
        s.downgrade(_plan_id())
        s.expire()
        assert s.has_scheduled_downgrade is False

    def test_expire_records_event(self) -> None:
        s = _subscribe()
        s.clear_events()
        s.expire()
        events = s.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], SubscriptionExpired)

    def test_expire_when_expired_raises(self) -> None:
        s = _subscribe()
        s.expire()
        with pytest.raises(InvalidStateTransition):
            s.expire()


# ============================================================
# Lifecycle scenarios
# ============================================================


class TestSubscriptionLifecycleScenario:
    """End-to-end lifecycle scenarios."""

    def test_active_to_expired_via_cancel(self) -> None:
        s = _subscribe()
        s.cancel()
        assert s.is_canceled is True
        s.expire()
        assert s.is_expired is True

    def test_active_to_past_due_to_recovered(self) -> None:
        s = _subscribe()
        s.mark_past_due()
        s.recover()
        assert s.is_active is True

    def test_active_to_past_due_to_canceled_to_expired(self) -> None:
        s = _subscribe()
        s.mark_past_due()
        s.cancel()
        s.expire()
        assert s.is_expired is True

    def test_downgrade_then_renew_swaps_plan(self) -> None:
        s = _subscribe(period_start=date(2024, 1, 1), period_end=date(2024, 2, 1))
        new_plan = _plan_id()
        s.downgrade(new_plan)
        # While still in the current period, plan is unchanged
        assert s.billing_plan_id != new_plan
        # Renew at period boundary
        s.renew(new_period_end=date(2024, 3, 1))
        assert s.billing_plan_id == new_plan

    def test_event_sequence_for_active_to_expired(self) -> None:
        s = _subscribe()
        s.cancel()
        s.expire()
        events = s.collect_events()
        types = [type(e).__name__ for e in events]
        assert types == [
            "SubscriptionActivated",
            "SubscriptionCanceled",
            "SubscriptionExpired",
        ]
