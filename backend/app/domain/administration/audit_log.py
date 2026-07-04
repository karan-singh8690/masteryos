"""Administration context — AuditLog entity (append-only).

The :class:`AuditLog` is the entity recording a single audit-worthy
action taken by an actor (a user or a system process) against a target
entity. It is **strictly append-only**: there are no methods that
modify state. Once recorded, an AuditLog entry is immutable for the
lifetime of the system — this is the compliance invariant that lets
the log serve as legal evidence (GDPR Art. 30, SOC 2 CC7).

The entity captures:
- ``actor_user_id``: the user who performed the action (``None`` for
  system-initiated actions like a cron job).
- ``action``: a stable, dotted action code (e.g.,
  ``"user.suspend"``, ``"billing_plan.deprecate"``).
- ``target_type`` and ``target_id``: the type and ID of the entity
  the action was performed on (e.g., ``"User"`` / ``UUID(...)``).
- ``metadata``: a free-form dict carrying the action's parameters and
  before/after state (serialised as JSON at the infrastructure layer).
- ``actor_ip`` and ``user_agent``: the network identity of the actor
  (``None`` for system actions).
- ``correlation_id``: an optional tracing ID that links the audit
  entry to the request that triggered the action.
- ``outcome``: ``"success"`` or ``"failure"``. Failed actions are
  audited too — the audit log must record both successful and
  unsuccessful attempts to perform privileged operations.
- ``failure_reason``: an optional reason for failed actions.

Invariants enforced:
- ``action`` is a non-empty string.
- ``target_type`` is a non-empty string.
- ``outcome`` is one of ``"success"`` / ``"failure"``.
- ``failure_reason`` may be set only when ``outcome == "failure"``.

There are **no mutation methods**. The entity is created via
:meth:`AuditLog.record` and never modified again.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.domain.administration.events import AuditLogRecorded
from app.domain.shared.ids import AuditLogId
from app.domain.shared.kernel import (
    Entity,
    InvariantViolation,
)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class AuditLog(Entity):
    """The AuditLog entity (append-only).

    Holds the audit entry's identity, actor information, action
    description, target reference, contextual metadata, network
    identity, correlation ID, outcome, and failure reason. There are
    no mutation methods — the entity is created via :meth:`record` and
    never modified again.

    The public constructor is intended for **reconstitution** from
    persistence. To create a *new* entry, use :meth:`AuditLog.record`.
    """

    #: Maximum length of the ``action`` code.
    MAX_ACTION_LENGTH: int = 128

    #: Maximum length of the ``target_type`` code.
    MAX_TARGET_TYPE_LENGTH: int = 64

    #: Allowed values for ``outcome``.
    OUTCOME_SUCCESS: str = "success"
    OUTCOME_FAILURE: str = "failure"
    _ALLOWED_OUTCOMES: frozenset[str] = frozenset({OUTCOME_SUCCESS, OUTCOME_FAILURE})

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: AuditLogId,
        actor_user_id: UUID | None,
        action: str,
        target_type: str,
        target_id: UUID | None,
        metadata: dict[str, Any] | None = None,
        actor_ip: str | None = None,
        user_agent: str | None = None,
        correlation_id: str | None = None,
        outcome: str = OUTCOME_SUCCESS,
        failure_reason: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self._domain_events: list[Any] = []
        self._id: AuditLogId = id
        self._actor_user_id: UUID | None = actor_user_id
        self._action: str = action
        self._target_type: str = target_type
        self._target_id: UUID | None = target_id
        self._metadata: dict[str, Any] = dict(metadata) if metadata else {}
        self._actor_ip: str | None = actor_ip
        self._user_agent: str | None = user_agent
        self._correlation_id: str | None = correlation_id
        self._outcome: str = outcome
        self._failure_reason: str | None = failure_reason
        self._created_at: datetime = created_at or _utcnow()
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
    def record(
        cls,
        actor_user_id: UUID | None,
        action: str,
        target_type: str,
        target_id: UUID | None,
        *,
        metadata: dict[str, Any] | None = None,
        actor_ip: str | None = None,
        user_agent: str | None = None,
        correlation_id: str | None = None,
        outcome: str = "success",
        failure_reason: str | None = None,
    ) -> AuditLog:
        """Record a new audit-log entry.

        Args:
            actor_user_id: The user who performed the action, or
                ``None`` for system-initiated actions (e.g., a cron
                job).
            action: A stable, dotted action code (e.g.,
                ``"user.suspend"``, ``"billing_plan.deprecate"``).
            target_type: The type name of the target entity (e.g.,
                ``"User"``, ``"BillingPlan"``).
            target_id: The ID of the target entity, or ``None`` if the
                action does not target a specific entity (e.g., a
                ``"export.run"`` action).
            metadata: Free-form dict carrying the action's parameters
                and before/after state.
            actor_ip: The actor's IP address, or ``None`` for system
                actions.
            user_agent: The actor's User-Agent string, or ``None``.
            correlation_id: An optional tracing ID linking the entry
                to the triggering request.
            outcome: ``"success"`` (default) or ``"failure"``. Failed
                actions are audited too.
            failure_reason: An optional reason for failed actions. May
                only be set when ``outcome == "failure"``.

        Returns:
            A newly created, un-persisted :class:`AuditLog` entry. The
            caller must add it to the repository and call
            :meth:`collect_events` to publish the recorded events.

        Raises:
            InvariantViolation: If any field fails validation.
        """
        entry_id = AuditLogId.generate()
        entry = cls(
            id=entry_id,
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata,
            actor_ip=actor_ip,
            user_agent=user_agent,
            correlation_id=correlation_id,
            outcome=outcome,
            failure_reason=failure_reason,
        )
        entry._record_event(
            AuditLogRecorded(
                audit_log_id=entry.id,
                actor_user_id=entry.actor_user_id,
                action=entry.action,
                target_type=entry.target_type,
                target_id=entry.target_id,
                outcome=entry.outcome,
            )
        )
        return entry

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------
    # NOTE: AuditLog is append-only — there are no mutation methods.
    # The properties below are the *only* way to read state.
    # ------------------------------------------------------------------

    @property
    def id(self) -> AuditLogId:
        """The entry's unique identifier."""
        return self._id

    @property
    def actor_user_id(self) -> UUID | None:
        """The user who performed the action, or ``None`` for system actions."""
        return self._actor_user_id

    @property
    def action(self) -> str:
        """The stable, dotted action code."""
        return self._action

    @property
    def target_type(self) -> str:
        """The type name of the target entity."""
        return self._target_type

    @property
    def target_id(self) -> UUID | None:
        """The ID of the target entity, or ``None``."""
        return self._target_id

    @property
    def metadata(self) -> dict[str, Any]:
        """Free-form metadata dict. Returns a copy."""
        return dict(self._metadata)

    @property
    def actor_ip(self) -> str | None:
        """The actor's IP address, or ``None``."""
        return self._actor_ip

    @property
    def user_agent(self) -> str | None:
        """The actor's User-Agent string, or ``None``."""
        return self._user_agent

    @property
    def correlation_id(self) -> str | None:
        """The tracing ID linking this entry to its triggering request."""
        return self._correlation_id

    @property
    def outcome(self) -> str:
        """``"success"`` or ``"failure"``."""
        return self._outcome

    @property
    def failure_reason(self) -> str | None:
        """The failure reason, or ``None`` (only set on failures)."""
        return self._failure_reason

    @property
    def created_at(self) -> datetime:
        """When this entry was recorded (immutable)."""
        return self._created_at

    @property
    def is_success(self) -> bool:
        """True if the action succeeded."""
        return self._outcome == self.OUTCOME_SUCCESS

    @property
    def is_failure(self) -> bool:
        """True if the action failed."""
        return self._outcome == self.OUTCOME_FAILURE

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants; raise on failure."""
        if not isinstance(self._action, str) or not self._action.strip():
            raise InvariantViolation("AuditLog", "action must be a non-empty string")
        if len(self._action) > self.MAX_ACTION_LENGTH:
            raise InvariantViolation(
                "AuditLog",
                f"action must be at most {self.MAX_ACTION_LENGTH} characters",
            )
        self._action = self._action.strip()

        if not isinstance(self._target_type, str) or not self._target_type.strip():
            raise InvariantViolation("AuditLog", "target_type must be a non-empty string")
        if len(self._target_type) > self.MAX_TARGET_TYPE_LENGTH:
            raise InvariantViolation(
                "AuditLog",
                f"target_type must be at most {self.MAX_TARGET_TYPE_LENGTH} characters",
            )
        self._target_type = self._target_type.strip()

        if self._actor_user_id is not None and not isinstance(self._actor_user_id, UUID):
            raise InvariantViolation(
                "AuditLog",
                f"actor_user_id must be a UUID or None, got {type(self._actor_user_id).__name__}",
            )
        if self._target_id is not None and not isinstance(self._target_id, UUID):
            raise InvariantViolation(
                "AuditLog",
                f"target_id must be a UUID or None, got {type(self._target_id).__name__}",
            )

        if self._outcome not in self._ALLOWED_OUTCOMES:
            raise InvariantViolation(
                "AuditLog",
                f"outcome must be one of {sorted(self._ALLOWED_OUTCOMES)}, got {self._outcome!r}",
            )

        if self._failure_reason is not None:
            if not isinstance(self._failure_reason, str) or not self._failure_reason.strip():
                raise InvariantViolation(
                    "AuditLog",
                    "failure_reason must be None or a non-empty string",
                )
            if self._outcome != self.OUTCOME_FAILURE:
                raise InvariantViolation(
                    "AuditLog",
                    "failure_reason may only be set when outcome is 'failure'",
                )

        if not isinstance(self._metadata, dict):
            raise InvariantViolation("AuditLog", "metadata must be a dict")

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"AuditLog(id={self._id}, action={self._action!r}, "
            f"target_type={self._target_type!r}, target_id={self._target_id}, "
            f"outcome={self._outcome!r})"
        )


__all__ = ["AuditLog"]
