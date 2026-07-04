"""Scheduling context — SchedulingConfig entity.

The :class:`SchedulingConfig` is the entity that holds the
subject-scoped tuning parameters for the scheduling engine: queue size,
cooldown, priority weights, difficulty-adjustment bounds, and the
mastery/memory thresholds that gate graduation and review scheduling.

The config is **versioned**. Updating parameters via
:meth:`update_parameters` produces a new version number; the previous
version is preserved immutably so that any historical DailyQueue can be
reproduced deterministically from its stored config version
(ADR-0011 — triple versioning). The config is **not** an aggregate
root; its lifecycle is supervised by the :class:`Subject` aggregate in
the Content context (subject scope) — but it lives here in the
Scheduling context because that is the context that consumes it.

Invariants enforced:
- ``default_queue_size`` ∈ [5, 50].
- ``cooldown_minutes`` ∈ [5, 240].
- ``mastery_threshold_proficient`` and ``mastery_threshold_mastered``
  ∈ [0.0, 1.0], and ``mastered > proficient``.
- ``memory_threshold`` ∈ [0.0, 1.0].
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.scheduling.events import (
    SchedulingConfigCreated,
    SchedulingConfigDeactivated,
    SchedulingConfigUpdated,
)
from app.domain.scheduling.exceptions import (
    InvalidCooldownDuration,
    InvalidThresholdRange,
    SchedulingError,
)
from app.domain.shared.ids import SchedulingConfigId, SubjectId
from app.domain.shared.kernel import (
    Entity,
    InvariantViolation,
)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class SchedulingConfig(Entity):
    """The SchedulingConfig entity.

    Holds the subject-scoped scheduling parameters, a version counter,
    an active flag, and creation/update timestamps. All mutations go
    through methods on this class, which enforce invariants and emit
    domain events via :meth:`Entity._record_event` (re-using the same
    event-collection mechanism as the :class:`AggregateRoot`, since the
    application layer expects ``collect_events`` on every persisted
    domain object — see note below).

    The public constructor is intended for **reconstitution** from
    persistence. To create a *new* config, use :meth:`SchedulingConfig.create`.

    Note:
        :class:`SchedulingConfig` extends :class:`Entity`, not
        :class:`AggregateRoot`, but it still records domain events for
        the application layer to publish. We attach the event-collection
        machinery here so the application layer can treat every domain
        object uniformly (call ``collect_events`` after a save). This is
        consistent with how the Assessment context's non-root entities
        behave.
    """

    #: Minimum and maximum default queue size.
    MIN_QUEUE_SIZE: int = 5
    MAX_QUEUE_SIZE: int = 50

    #: Minimum and maximum cooldown between two attempts on the same concept.
    MIN_COOLDOWN_MINUTES: int = 5
    MAX_COOLDOWN_MINUTES: int = 240

    #: Inclusive bounds for all probability thresholds.
    THRESHOLD_MIN: float = 0.0
    THRESHOLD_MAX: float = 1.0

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: SchedulingConfigId,
        subject_id: SubjectId,
        default_queue_size: int,
        cooldown_minutes: int,
        priority_weights: dict[str, float] | None = None,
        difficulty_adjustment_bounds: dict[str, float] | None = None,
        mastery_threshold_proficient: float,
        mastery_threshold_mastered: float,
        memory_threshold: float,
        is_active: bool = True,
        version: int = 1,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._domain_events: list[Any] = []
        self._id: SchedulingConfigId = id
        self._subject_id: SubjectId = subject_id
        self._default_queue_size: int = default_queue_size
        self._cooldown_minutes: int = cooldown_minutes
        self._priority_weights: dict[str, float] = dict(priority_weights) if priority_weights else {}
        self._difficulty_adjustment_bounds: dict[str, float] = (
            dict(difficulty_adjustment_bounds) if difficulty_adjustment_bounds else {}
        )
        self._mastery_threshold_proficient: float = mastery_threshold_proficient
        self._mastery_threshold_mastered: float = mastery_threshold_mastered
        self._memory_threshold: float = memory_threshold
        self._is_active: bool = bool(is_active)
        self._version: int = version
        now = _utcnow()
        self._created_at: datetime = created_at or now
        self._updated_at: datetime = updated_at or now
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
        subject_id: SubjectId,
        *,
        default_queue_size: int,
        cooldown_minutes: int,
        priority_weights: dict[str, float] | None = None,
        difficulty_adjustment_bounds: dict[str, float] | None = None,
        mastery_threshold_proficient: float,
        mastery_threshold_mastered: float,
        memory_threshold: float,
    ) -> SchedulingConfig:
        """Create a new SchedulingConfig at version 1, in ``active`` status.

        Args:
            subject_id: The :class:`SubjectId` this config is scoped to.
            default_queue_size: Default number of questions in a daily
                queue. Must be in ``[5, 50]``.
            cooldown_minutes: Minimum gap between two attempts on the
                same concept. Must be in ``[5, 240]``.
            priority_weights: Optional mapping of priority signal →
                weight (e.g., ``{"weakness": 0.5, "decay": 0.3}``).
            difficulty_adjustment_bounds: Optional mapping of bound name
                → value (e.g., ``{"min": 0.1, "max": 0.9}``).
            mastery_threshold_proficient: Mastery score at or above
                which a concept is considered ``proficient``.
            mastery_threshold_mastered: Mastery score at or above which
                a concept is considered ``mastered``. Must strictly
                exceed ``mastery_threshold_proficient``.
            memory_threshold: Memory score below which a concept is
                flagged for review.

        Returns:
            A newly created, un-persisted :class:`SchedulingConfig` at
            version 1 in ``active`` status. The caller must add it to
            the repository and call :meth:`collect_events` to publish
            the recorded events.

        Raises:
            InvalidQueueSize: If ``default_queue_size`` is out of bounds.
            InvalidCooldownDuration: If ``cooldown_minutes`` is out of
                bounds.
            InvalidThresholdRange: If any threshold is out of [0.0, 1.0]
                or ``mastered <= proficient``.
        """
        config_id = SchedulingConfigId.generate()
        config = cls(
            id=config_id,
            subject_id=subject_id,
            default_queue_size=default_queue_size,
            cooldown_minutes=cooldown_minutes,
            priority_weights=priority_weights,
            difficulty_adjustment_bounds=difficulty_adjustment_bounds,
            mastery_threshold_proficient=mastery_threshold_proficient,
            mastery_threshold_mastered=mastery_threshold_mastered,
            memory_threshold=memory_threshold,
            is_active=True,
            version=1,
        )
        config._record_event(
            SchedulingConfigCreated(
                config_id=config.id,
                subject_id=config.subject_id,
                version=config.version,
            )
        )
        return config

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> SchedulingConfigId:
        """The config's unique identifier."""
        return self._id

    @property
    def subject_id(self) -> SubjectId:
        """The Subject this config is scoped to."""
        return self._subject_id

    @property
    def default_queue_size(self) -> int:
        """Default number of questions in a daily queue."""
        return self._default_queue_size

    @property
    def cooldown_minutes(self) -> int:
        """Minimum gap (minutes) between two attempts on the same concept."""
        return self._cooldown_minutes

    @property
    def priority_weights(self) -> dict[str, float]:
        """Mapping of priority signal → weight. Returns a copy."""
        return dict(self._priority_weights)

    @property
    def difficulty_adjustment_bounds(self) -> dict[str, float]:
        """Difficulty adjustment bounds. Returns a copy."""
        return dict(self._difficulty_adjustment_bounds)

    @property
    def mastery_threshold_proficient(self) -> float:
        """Mastery score at or above which a concept is ``proficient``."""
        return self._mastery_threshold_proficient

    @property
    def mastery_threshold_mastered(self) -> float:
        """Mastery score at or above which a concept is ``mastered``."""
        return self._mastery_threshold_mastered

    @property
    def memory_threshold(self) -> float:
        """Memory score below which a concept is flagged for review."""
        return self._memory_threshold

    @property
    def is_active(self) -> bool:
        """True if this config is eligible to drive scheduling."""
        return self._is_active

    @property
    def version(self) -> int:
        """The monotonically-increasing version number."""
        return self._version

    @property
    def created_at(self) -> datetime:
        """When this config was created."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """When this config was last modified."""
        return self._updated_at

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants; raise on failure."""
        if not isinstance(self._default_queue_size, int) or isinstance(
            self._default_queue_size, bool
        ):
            raise InvariantViolation(
                "SchedulingConfig",
                "default_queue_size must be an int",
            )
        if not (self.MIN_QUEUE_SIZE <= self._default_queue_size <= self.MAX_QUEUE_SIZE):
            raise InvalidQueueSize(
                self._default_queue_size,
                min_size=self.MIN_QUEUE_SIZE,
                max_size=self.MAX_QUEUE_SIZE,
            )

        if not isinstance(self._cooldown_minutes, int) or isinstance(
            self._cooldown_minutes, bool
        ):
            raise InvariantViolation(
                "SchedulingConfig",
                "cooldown_minutes must be an int",
            )
        if not (self.MIN_COOLDOWN_MINUTES <= self._cooldown_minutes <= self.MAX_COOLDOWN_MINUTES):
            raise InvalidCooldownDuration(
                self._cooldown_minutes,
                min_minutes=self.MIN_COOLDOWN_MINUTES,
                max_minutes=self.MAX_COOLDOWN_MINUTES,
            )

        for name, value in (
            ("mastery_threshold_proficient", self._mastery_threshold_proficient),
            ("mastery_threshold_mastered", self._mastery_threshold_mastered),
            ("memory_threshold", self._memory_threshold),
        ):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise InvalidThresholdRange(name, value, reason=f"{name} must be a float")
            if not (self.THRESHOLD_MIN <= float(value) <= self.THRESHOLD_MAX):
                raise InvalidThresholdRange(name, value)

        if not (self._mastery_threshold_mastered > self._mastery_threshold_proficient):
            raise InvalidThresholdRange(
                "mastery_threshold_mastered",
                self._mastery_threshold_mastered,
                reason=(
                    f"mastery_threshold_mastered ({self._mastery_threshold_mastered}) "
                    f"must strictly exceed mastery_threshold_proficient "
                    f"({self._mastery_threshold_proficient})"
                ),
            )

        if self._version < 1:
            raise InvariantViolation(
                "SchedulingConfig",
                f"version must be >= 1, got {self._version}",
            )

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def update_parameters(
        self,
        *,
        default_queue_size: int | None = None,
        cooldown_minutes: int | None = None,
        priority_weights: dict[str, float] | None = None,
        difficulty_adjustment_bounds: dict[str, float] | None = None,
        mastery_threshold_proficient: float | None = None,
        mastery_threshold_mastered: float | None = None,
        memory_threshold: float | None,
        now: datetime | None = None,
    ) -> None:
        """Update one or more scheduling parameters, producing a new version.

        Only fields explicitly passed (not ``None``) are considered for
        update. ``memory_threshold`` is required (it is the most-tuned
        parameter) — pass the current value if you do not want to change
        it. Invariants are re-checked against the merged state.

        A :class:`SchedulingConfigUpdated` event is recorded with the
        new version, the previous version, and a ``changed_fields`` map
        of field name → new value for any field that actually changed.

        Raises:
            SchedulingError: If the config is not active.
            InvalidQueueSize | InvalidCooldownDuration | InvalidThresholdRange:
                If any new value violates an invariant (checked against
                the *merged* state, so e.g. lowering ``proficient``
                below ``mastered`` is detected even if only one of the
                two is updated).
        """
        if not self._is_active:
            raise SchedulingError(
                f"Cannot update inactive SchedulingConfig {self._id}",
                code="INACTIVE_SCHEDULING_CONFIG",
            )

        previous = {
            "default_queue_size": self._default_queue_size,
            "cooldown_minutes": self._cooldown_minutes,
            "priority_weights": dict(self._priority_weights),
            "difficulty_adjustment_bounds": dict(self._difficulty_adjustment_bounds),
            "mastery_threshold_proficient": self._mastery_threshold_proficient,
            "mastery_threshold_mastered": self._mastery_threshold_mastered,
            "memory_threshold": self._memory_threshold,
        }

        # Snapshot the current state so we can roll back on validation
        # failure (validate against the *merged* candidate state).
        snapshot = (
            self._default_queue_size,
            self._cooldown_minutes,
            dict(self._priority_weights),
            dict(self._difficulty_adjustment_bounds),
            self._mastery_threshold_proficient,
            self._mastery_threshold_mastered,
            self._memory_threshold,
            self._version,
        )

        if default_queue_size is not None:
            self._default_queue_size = default_queue_size
        if cooldown_minutes is not None:
            self._cooldown_minutes = cooldown_minutes
        if priority_weights is not None:
            self._priority_weights = dict(priority_weights)
        if difficulty_adjustment_bounds is not None:
            self._difficulty_adjustment_bounds = dict(difficulty_adjustment_bounds)
        if mastery_threshold_proficient is not None:
            self._mastery_threshold_proficient = mastery_threshold_proficient
        if mastery_threshold_mastered is not None:
            self._mastery_threshold_mastered = mastery_threshold_mastered
        # memory_threshold is required; always set it.
        self._memory_threshold = memory_threshold

        try:
            self._validate_invariants()
        except (InvariantViolation, SchedulingError):
            # Roll back to the snapshot so a failed update leaves the
            # entity in its prior consistent state.
            (
                self._default_queue_size,
                self._cooldown_minutes,
                self._priority_weights,
                self._difficulty_adjustment_bounds,
                self._mastery_threshold_proficient,
                self._mastery_threshold_mastered,
                self._memory_threshold,
                self._version,
            ) = snapshot
            raise

        changed_fields: dict[str, object] = {}
        if self._default_queue_size != previous["default_queue_size"]:
            changed_fields["default_queue_size"] = self._default_queue_size
        if self._cooldown_minutes != previous["cooldown_minutes"]:
            changed_fields["cooldown_minutes"] = self._cooldown_minutes
        if self._priority_weights != previous["priority_weights"]:
            changed_fields["priority_weights"] = dict(self._priority_weights)
        if self._difficulty_adjustment_bounds != previous["difficulty_adjustment_bounds"]:
            changed_fields["difficulty_adjustment_bounds"] = dict(
                self._difficulty_adjustment_bounds
            )
        if self._mastery_threshold_proficient != previous["mastery_threshold_proficient"]:
            changed_fields["mastery_threshold_proficient"] = self._mastery_threshold_proficient
        if self._mastery_threshold_mastered != previous["mastery_threshold_mastered"]:
            changed_fields["mastery_threshold_mastered"] = self._mastery_threshold_mastered
        if self._memory_threshold != previous["memory_threshold"]:
            changed_fields["memory_threshold"] = self._memory_threshold

        previous_version = self._version
        self._version = self._version + 1
        timestamp = now or _utcnow()
        self._updated_at = timestamp

        self._record_event(
            SchedulingConfigUpdated(
                config_id=self._id,
                subject_id=self._subject_id,
                new_version=self._version,
                previous_version=previous_version,
                changed_fields=changed_fields,
            )
        )

    def deactivate(self, now: datetime | None = None) -> None:
        """Mark this config as inactive.

        Deactivation pauses new queue generation for the Subject without
        destroying the config — historical queues remain reproducible
        from their stored config version. Idempotent — calling it again
        when already inactive is a no-op (no event recorded).

        Raises:
            SchedulingError: Never; deactivation of an already-inactive
                config is a silent no-op.
        """
        if not self._is_active:
            return
        timestamp = now or _utcnow()
        self._is_active = False
        self._updated_at = timestamp
        self._record_event(
            SchedulingConfigDeactivated(
                config_id=self._id,
                subject_id=self._subject_id,
                deactivated_at=timestamp,
            )
        )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"SchedulingConfig(id={self._id}, subject_id={self._subject_id}, "
            f"version={self._version}, is_active={self._is_active})"
        )


__all__ = ["SchedulingConfig"]
