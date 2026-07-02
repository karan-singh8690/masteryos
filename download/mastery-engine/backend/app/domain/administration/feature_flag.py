"""Administration context — FeatureFlag aggregate root.

The :class:`FeatureFlag` is the aggregate root controlling the rollout
of a single feature toggle. It carries the flag's key, a human-readable
description, a set of targeting rules (evaluated by the application
layer against a context dict), a default value, an active flag, an
owner, an optional retirement plan, and lifecycle timestamps.

Lifecycle (state machine)::

    active ──retire()──► retired  (terminal)

A retired flag is **immutable** — :meth:`update` and :meth:`retire`
both raise if called on a retired flag. To change behaviour after
retirement, create a new flag with a different key (the application
layer can migrate callers from the old key to the new one).

Invariants enforced:
- ``key`` is a non-empty string (1–128 chars), and matches the
  ``^[a-z][a-z0-9_\\.\\-]*$`` pattern (lowercase, dotted or kebab'd).
- ``description`` is a non-empty string (<= 2000 chars).
- ``owner`` is a non-empty string (1–200 chars).
- ``targeting_rules`` is a dict (may be empty).
- ``default_value`` is any JSON-serialisable value.
- ``retirement_plan`` is ``None`` or a non-empty string.

The targeting rules' format is intentionally opaque at the domain
layer — the application layer interprets them (e.g., percentage
rollouts, allow-lists, attribute matches). The domain only enforces
that they are a dict and that updates to them are recorded as events.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.domain.administration.events import (
    FeatureFlagCreated,
    FeatureFlagRetired,
    FeatureFlagUpdated,
)
from app.domain.administration.exceptions import FeatureFlagNotActive
from app.domain.shared.ids import FeatureFlagId
from app.domain.shared.kernel import (
    AggregateRoot,
    InvariantViolation,
)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


# Lowercase, optionally dotted or kebab'd, starting with a letter.
# Examples: "ai_credits", "new_dashboard.v2", "export-csv".
_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_.\-]*$")


class FeatureFlag(AggregateRoot):
    """The FeatureFlag aggregate root.

    Holds the flag's identity (id, key), descriptive attributes
    (description, owner, retirement_plan), evaluation state
    (targeting_rules, default_value), lifecycle state (is_active,
    retired_at), and timestamps. All mutations go through methods on
    this class, which enforce invariants and emit domain events.

    The public constructor is intended for **reconstitution** from
    persistence. To create a *new* flag, use :meth:`FeatureFlag.create`.
    """

    #: Maximum length of the flag key.
    MAX_KEY_LENGTH: int = 128

    #: Maximum length of the description.
    MAX_DESCRIPTION_LENGTH: int = 2000

    #: Maximum length of the owner string (e.g., ``"team:learning"``).
    MAX_OWNER_LENGTH: int = 200

    #: Maximum length of the retirement plan.
    MAX_RETIREMENT_PLAN_LENGTH: int = 1000

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: FeatureFlagId,
        key: str,
        description: str,
        targeting_rules: dict[str, Any] | None = None,
        default_value: Any = None,
        is_active: bool = True,
        owner: str,
        retirement_plan: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        retired_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self._id: FeatureFlagId = id
        self._key: str = key
        self._description: str = description
        self._targeting_rules: dict[str, Any] = dict(targeting_rules) if targeting_rules else {}
        self._default_value: Any = default_value
        self._is_active: bool = bool(is_active)
        self._owner: str = owner
        self._retirement_plan: str | None = retirement_plan
        now = _utcnow()
        self._created_at: datetime = created_at or now
        self._updated_at: datetime = updated_at or now
        self._retired_at: datetime | None = retired_at
        self._validate_invariants()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        key: str,
        description: str,
        owner: str,
        *,
        targeting_rules: dict[str, Any] | None = None,
        default_value: Any = None,
        retirement_plan: str | None = None,
    ) -> FeatureFlag:
        """Create a new FeatureFlag in ``active`` status.

        Args:
            key: A unique, lowercase, dotted-or-kebab'd key
                (e.g., ``"new_dashboard.v2"``).
            description: A human-readable description of what the flag
                controls.
            owner: The owning team or individual (e.g.,
                ``"team:learning"``).
            targeting_rules: Initial targeting rules (may be empty).
            default_value: The value returned when no targeting rule
                matches. Any JSON-serialisable value.
            retirement_plan: An optional note describing when and how
                the flag will be retired (e.g.,
                ``"Remove after v2 GA, ETA 2024-Q3"``).

        Returns:
            A newly created, un-persisted :class:`FeatureFlag` in
            ``active`` status. The caller must add it to the repository
            and call :meth:`collect_events` to publish the recorded
            events.

        Raises:
            InvariantViolation: If any field fails validation.
        """
        flag_id = FeatureFlagId.generate()
        flag = cls(
            id=flag_id,
            key=key,
            description=description,
            targeting_rules=targeting_rules,
            default_value=default_value,
            is_active=True,
            owner=owner,
            retirement_plan=retirement_plan,
        )
        flag._record_event(
            FeatureFlagCreated(
                flag_id=flag.id,
                key=flag.key,
                description=flag.description,
                owner=flag.owner,
                default_value=flag.default_value,
            )
        )
        return flag

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> FeatureFlagId:
        """The flag's unique identifier."""
        return self._id

    @property
    def key(self) -> str:
        """The unique, lowercase flag key."""
        return self._key

    @property
    def description(self) -> str:
        """The human-readable description."""
        return self._description

    @property
    def targeting_rules(self) -> dict[str, Any]:
        """The targeting-rules dict. Returns a copy."""
        return dict(self._targeting_rules)

    @property
    def default_value(self) -> Any:
        """The default value returned when no targeting rule matches."""
        return self._default_value

    @property
    def is_active(self) -> bool:
        """True if the flag is active (not retired)."""
        return self._is_active

    @property
    def owner(self) -> str:
        """The owning team or individual."""
        return self._owner

    @property
    def retirement_plan(self) -> str | None:
        """An optional note on when/how the flag will be retired."""
        return self._retirement_plan

    @property
    def created_at(self) -> datetime:
        """When this flag was created."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """When this flag was last modified."""
        return self._updated_at

    @property
    def retired_at(self) -> datetime | None:
        """When this flag was retired, or ``None`` if still active."""
        return self._retired_at

    @property
    def is_retired(self) -> bool:
        """True if the flag has been retired (terminal)."""
        return not self._is_active

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants; raise on failure."""
        if not isinstance(self._key, str) or not self._key.strip():
            raise InvariantViolation("FeatureFlag", "key must be a non-empty string")
        if len(self._key) > self.MAX_KEY_LENGTH:
            raise InvariantViolation(
                "FeatureFlag",
                f"key must be at most {self.MAX_KEY_LENGTH} characters",
            )
        if not _KEY_PATTERN.match(self._key):
            raise InvariantViolation(
                "FeatureFlag",
                f"key {self._key!r} must match {_KEY_PATTERN.pattern}",
            )

        if not isinstance(self._description, str) or not self._description.strip():
            raise InvariantViolation("FeatureFlag", "description must be a non-empty string")
        if len(self._description) > self.MAX_DESCRIPTION_LENGTH:
            raise InvariantViolation(
                "FeatureFlag",
                f"description must be at most {self.MAX_DESCRIPTION_LENGTH} characters",
            )
        self._description = self._description.strip()

        if not isinstance(self._owner, str) or not self._owner.strip():
            raise InvariantViolation("FeatureFlag", "owner must be a non-empty string")
        if len(self._owner) > self.MAX_OWNER_LENGTH:
            raise InvariantViolation(
                "FeatureFlag",
                f"owner must be at most {self.MAX_OWNER_LENGTH} characters",
            )
        self._owner = self._owner.strip()

        if not isinstance(self._targeting_rules, dict):
            raise InvariantViolation("FeatureFlag", "targeting_rules must be a dict")

        if self._retirement_plan is not None:
            if not isinstance(self._retirement_plan, str) or not self._retirement_plan.strip():
                raise InvariantViolation(
                    "FeatureFlag",
                    "retirement_plan must be None or a non-empty string",
                )
            if len(self._retirement_plan) > self.MAX_RETIREMENT_PLAN_LENGTH:
                raise InvariantViolation(
                    "FeatureFlag",
                    f"retirement_plan must be at most {self.MAX_RETIREMENT_PLAN_LENGTH} characters",
                )

    def _touch(self, now: datetime | None = None) -> None:
        """Update the ``updated_at`` timestamp."""
        self._updated_at = now or _utcnow()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def update(
        self,
        *,
        targeting_rules: dict[str, Any] | None = None,
        default_value: Any = None,
        description: str | None = None,
        now: datetime | None = None,
    ) -> None:
        """Update the flag's targeting rules, default value, or description.

        Only fields explicitly passed (not ``None``) are considered for
        update. A :class:`FeatureFlagUpdated` event is recorded with a
        ``changed_fields`` map of field name → new value for any field
        that actually changed.

        Args:
            targeting_rules: New targeting-rules dict (replaces
                existing).
            default_value: New default value.
            description: New description.
            now: Optional timestamp (for testing).

        Raises:
            FeatureFlagNotActive: If the flag has been retired.
        """
        if not self._is_active:
            raise FeatureFlagNotActive(self._key)

        changed_fields: dict[str, Any] = {}
        if targeting_rules is not None and targeting_rules != self._targeting_rules:
            self._targeting_rules = dict(targeting_rules)
            changed_fields["targeting_rules"] = dict(self._targeting_rules)
        if default_value is not None and default_value != self._default_value:
            self._default_value = default_value
            changed_fields["default_value"] = self._default_value
        if description is not None and description != self._description:
            self._description = description
            # Re-validate the new description.
            if not isinstance(self._description, str) or not self._description.strip():
                raise InvariantViolation("FeatureFlag", "description must be a non-empty string")
            if len(self._description) > self.MAX_DESCRIPTION_LENGTH:
                raise InvariantViolation(
                    "FeatureFlag",
                    f"description must be at most {self.MAX_DESCRIPTION_LENGTH} characters",
                )
            self._description = self._description.strip()
            changed_fields["description"] = self._description

        if not changed_fields:
            return  # nothing actually changed

        timestamp = now or _utcnow()
        self._touch(timestamp)
        self._record_event(
            FeatureFlagUpdated(
                flag_id=self._id,
                key=self._key,
                changed_fields=changed_fields,
            )
        )

    def retire(self, now: datetime | None = None) -> None:
        """Retire the flag (terminal).

        Retirement makes the flag immutable: subsequent calls to
        :meth:`update` or :meth:`retire` will raise
        :class:`FeatureFlagNotActive`. The flag's evaluation continues
        to return its last ``default_value`` snapshot — subscribers
        should cache that snapshot for a grace period before purging
        the flag entirely.

        Idempotent — calling it again when already retired is a no-op
        (no event recorded).
        """
        if not self._is_active:
            return
        timestamp = now or _utcnow()
        self._is_active = False
        self._retired_at = timestamp
        self._touch(timestamp)
        self._record_event(
            FeatureFlagRetired(
                flag_id=self._id,
                key=self._key,
                retired_at=timestamp,
            )
        )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"FeatureFlag(id={self._id}, key={self._key!r}, "
            f"owner={self._owner!r}, active={self._is_active})"
        )


__all__ = ["FeatureFlag"]
