"""Administration context — Organization aggregate root.

The :class:`Organization` is the aggregate root of a tenant
organization. It tracks the organization's identity, name, lifecycle
state, and timestamps. Organizations group users and resources for
billing, access control, and data isolation.

Lifecycle (state machine)::

    active ──suspend()──► suspended ──reactivate()──► active
       │                     │
       │                     └──dissolve()──► dissolved  (terminal)
       │
       └──dissolve()────────────────────────► dissolved  (terminal)

``dissolved`` is terminal — a dissolved organization cannot be
reactivated. To restore service, create a new organization.

Invariants enforced:
- ``name`` is a non-empty string (1–200 chars).
- ``status`` is one of ``active`` / ``suspended`` / ``dissolved``.
- ``suspend`` requires ``active`` status.
- ``reactivate`` requires ``suspended`` status.
- ``dissolve`` requires ``active`` or ``suspended`` status.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.administration.events import (
    OrganizationCreated,
    OrganizationDissolved,
    OrganizationReactivated,
    OrganizationSuspended,
)
from app.domain.administration.exceptions import (
    CannotDissolveOrganization,
    CannotReactivateOrganization,
    CannotSuspendOrganization,
)
from app.domain.shared.ids import OrganizationId
from app.domain.shared.kernel import (
    AggregateRoot,
    InvariantViolation,
)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class OrganizationStatus:
    """Status of an organization (string constants, not an enum)."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISSOLVED = "dissolved"


class Organization(AggregateRoot):
    """The Organization aggregate root.

    Holds the organization's identity, name, lifecycle state, and
    timestamps. All mutations go through methods on this class, which
    enforce the state machine and emit domain events.

    The public constructor is intended for **reconstitution** from
    persistence. To create a *new* organization, use
    :meth:`Organization.create`.
    """

    #: Maximum length of the organization name.
    MAX_NAME_LENGTH: int = 200

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: OrganizationId,
        name: str,
        status: str = OrganizationStatus.ACTIVE,
        created_at: datetime | None = None,
        suspended_at: datetime | None = None,
        dissolved_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self._id: OrganizationId = id
        self._name: str = name
        self._status: str = status
        now = _utcnow()
        self._created_at: datetime = created_at or now
        self._suspended_at: datetime | None = suspended_at
        self._dissolved_at: datetime | None = dissolved_at
        self._updated_at: datetime = updated_at or now
        self._validate_invariants()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, name: str) -> Organization:
        """Create a new Organization in ``active`` status.

        Args:
            name: A human-readable name (e.g., ``"Acme University"``).

        Returns:
            A newly created, un-persisted :class:`Organization` in
            ``active`` status. The caller must add it to the repository
            and call :meth:`collect_events` to publish the recorded
            events.

        Raises:
            InvariantViolation: If the name fails validation.
        """
        org_id = OrganizationId.generate()
        org = cls(
            id=org_id,
            name=name,
            status=OrganizationStatus.ACTIVE,
        )
        org._record_event(
            OrganizationCreated(
                organization_id=org.id,
                name=org.name,
            )
        )
        return org

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> OrganizationId:
        """The organization's unique identifier."""
        return self._id

    @property
    def name(self) -> str:
        """The human-readable organization name."""
        return self._name

    @property
    def status(self) -> str:
        """The organization's lifecycle status."""
        return self._status

    @property
    def created_at(self) -> datetime:
        """When this organization was created."""
        return self._created_at

    @property
    def suspended_at(self) -> datetime | None:
        """When this organization was suspended, or ``None``."""
        return self._suspended_at

    @property
    def dissolved_at(self) -> datetime | None:
        """When this organization was dissolved, or ``None``."""
        return self._dissolved_at

    @property
    def updated_at(self) -> datetime:
        """When this organization was last modified."""
        return self._updated_at

    @property
    def is_active(self) -> bool:
        """True if the organization is in ``active`` status."""
        return self._status == OrganizationStatus.ACTIVE

    @property
    def is_suspended(self) -> bool:
        """True if the organization is in ``suspended`` status."""
        return self._status == OrganizationStatus.SUSPENDED

    @property
    def is_dissolved(self) -> bool:
        """True if the organization is in ``dissolved`` (terminal) status."""
        return self._status == OrganizationStatus.DISSOLVED

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants; raise on failure."""
        if not isinstance(self._name, str) or not self._name.strip():
            raise InvariantViolation("Organization", "name must be a non-empty string")
        if len(self._name) > self.MAX_NAME_LENGTH:
            raise InvariantViolation(
                "Organization",
                f"name must be at most {self.MAX_NAME_LENGTH} characters",
            )
        self._name = self._name.strip()
        if self._status not in (
            OrganizationStatus.ACTIVE,
            OrganizationStatus.SUSPENDED,
            OrganizationStatus.DISSOLVED,
        ):
            raise InvariantViolation(
                "Organization",
                f"unknown status {self._status!r}",
            )

    def _touch(self, now: datetime | None = None) -> None:
        """Update the ``updated_at`` timestamp."""
        self._updated_at = now or _utcnow()

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def suspend(self, now: datetime | None = None) -> None:
        """Suspend an active organization.

        Pre-state: ``active``.
        Post-state: ``suspended`` with ``suspended_at`` set.

        Subscribers should revoke access for the organization's members
        (typically by invalidating their sessions) and pause any
        scheduled jobs scoped to the organization.

        Raises:
            CannotSuspendOrganization: If the organization is not in
                ``active`` status.
        """
        if self._status != OrganizationStatus.ACTIVE:
            raise CannotSuspendOrganization(self._id, self._status)
        timestamp = now or _utcnow()
        self._status = OrganizationStatus.SUSPENDED
        self._suspended_at = timestamp
        self._touch(timestamp)
        self._record_event(
            OrganizationSuspended(
                organization_id=self._id,
                suspended_at=timestamp,
            )
        )

    def reactivate(self, now: datetime | None = None) -> None:
        """Reactivate a suspended organization.

        Pre-state: ``suspended``.
        Post-state: ``active`` with ``suspended_at`` cleared.

        Subscribers may resume scheduled jobs and notify members that
        access has been restored.

        Raises:
            CannotReactivateOrganization: If the organization is not in
                ``suspended`` status (e.g., it is already active or
                dissolved).
        """
        if self._status != OrganizationStatus.SUSPENDED:
            raise CannotReactivateOrganization(self._id, self._status)
        timestamp = now or _utcnow()
        self._status = OrganizationStatus.ACTIVE
        self._suspended_at = None
        self._touch(timestamp)
        self._record_event(
            OrganizationReactivated(
                organization_id=self._id,
                reactivated_at=timestamp,
            )
        )

    def dissolve(self, now: datetime | None = None) -> None:
        """Dissolve the organization (terminal).

        Pre-state: ``active`` or ``suspended``.
        Post-state: ``dissolved`` (terminal) with ``dissolved_at`` set.

        The organization is now non-functional — its members can no
        longer authenticate, and its data is queued for archival.
        Subscribers must trigger the data-retention workflow (archive,
        then erase after the legal retention window).

        Raises:
            CannotDissolveOrganization: If the organization is already
                ``dissolved``.
        """
        if self._status == OrganizationStatus.DISSOLVED:
            raise CannotDissolveOrganization(self._id, self._status)
        if self._status not in (OrganizationStatus.ACTIVE, OrganizationStatus.SUSPENDED):
            # Defensive — _validate_invariants already guards against
            # unknown statuses, but this keeps the error path explicit.
            raise CannotDissolveOrganization(self._id, self._status)
        timestamp = now or _utcnow()
        self._status = OrganizationStatus.DISSOLVED
        self._dissolved_at = timestamp
        self._touch(timestamp)
        self._record_event(
            OrganizationDissolved(
                organization_id=self._id,
                dissolved_at=timestamp,
            )
        )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Organization(id={self._id}, name={self._name!r}, "
            f"status={self._status!r})"
        )


__all__ = ["Organization", "OrganizationStatus"]
