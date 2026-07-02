"""Content context — Subject aggregate root.

The :class:`Subject` is the top-level aggregate root of the Content
context for a single tenant. It groups a coherent body of knowledge
(e.g., "Algorithms and Data Structures", "Organic Chemistry") and owns
the Concepts, QuestionTemplates, and ContentVersions that materialize
that body of knowledge for learners.

Lifecycle (state machine)::

        DRAFT ──publish()──► PUBLISHED ──deprecate()──► DEPRECATED
                              (terminal-ish; recoverable only via
                               a new ContentVersion, not via this
                               aggregate's transitions)

Invariants enforced:
- A Subject cannot be published until at least one piece of content
  has been associated with it. The application layer signals this by
  calling :meth:`mark_minimum_content_ready` once the gate is met;
  :meth:`publish` raises :class:`SubjectNotPublishable` otherwise.
- A Subject cannot be re-published from PUBLISHED or DEPRECATED.
- A Subject cannot be deprecated from DRAFT (must be PUBLISHED first).
- A Subject cannot be deprecated more than once.

The Subject does not own its child aggregates (Concept, QuestionTemplate,
ContentVersion). Each of those is its own aggregate root, scoped to the
Subject via ``subject_id``. This keeps the Subject aggregate small and
transaction-bounded; the Subject exists primarily to enforce the
publish/deprecate lifecycle and the minimum-content gate.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.content.events import (
    SubjectCreated,
    SubjectDeprecated,
    SubjectPublished,
)
from app.domain.content.exceptions import (
    SubjectAlreadyDeprecated,
    SubjectAlreadyPublished,
    SubjectNotPublishable,
)
from app.domain.shared.ids import SubjectId, TenantId
from app.domain.shared.kernel import (
    AggregateRoot,
    ContentStatus,
    InvalidStateTransition,
    InvariantViolation,
)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class Subject(AggregateRoot):
    """The Subject aggregate root.

    Holds the Subject's identity (id, tenant, code, slug), descriptive
    attributes (name, description), lifecycle state (status,
    published_at, deprecated_at), and the minimum-content gate flag.
    All mutations go through methods on this class, which enforce
    invariants and emit domain events via
    :meth:`AggregateRoot._record_event`.

    The public constructor is intended for **reconstitution** from
    persistence (the repository uses it to rebuild an aggregate from
    stored state). To create a *new* Subject, use :meth:`Subject.create`.
    """

    #: Maximum length of the human-readable ``code`` (e.g., "CS-101").
    MAX_CODE_LENGTH: int = 64

    #: Maximum length of the URL-safe ``slug``.
    MAX_SLUG_LENGTH: int = 128

    #: Maximum length of the human-readable ``name``.
    MAX_NAME_LENGTH: int = 200

    #: Maximum length of the ``description``.
    MAX_DESCRIPTION_LENGTH: int = 2000

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: SubjectId,
        tenant_id: TenantId,
        code: str,
        name: str,
        slug: str,
        description: str,
        status: ContentStatus = ContentStatus.DRAFT,
        minimum_content_ready: bool = False,
        published_at: datetime | None = None,
        deprecated_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self._id: SubjectId = id
        self._tenant_id: TenantId = tenant_id
        self._code: str = code
        self._name: str = name
        self._slug: str = slug
        self._description: str = description
        self._status: ContentStatus = status
        self._minimum_content_ready: bool = bool(minimum_content_ready)
        self._published_at: datetime | None = published_at
        self._deprecated_at: datetime | None = deprecated_at
        self._created_at: datetime = created_at or _utcnow()
        self._validate_invariants()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        code: str,
        name: str,
        slug: str,
        description: str,
    ) -> Subject:
        """Create a new Subject in ``draft`` status.

        Args:
            tenant_id: The Tenant that owns this Subject. A Subject is
                always scoped to exactly one Tenant.
            code: A short, tenant-unique code (e.g., ``"CS-101"``).
            name: A human-readable name (e.g., ``"Algorithms and Data
                Structures"``).
            slug: A URL-safe slug, unique within the Tenant. Lowercase,
                kebab-case is conventional but not enforced here.
            description: A longer description of the Subject's scope and
                intended audience.

        Returns:
            A newly created, un-persisted :class:`Subject` in ``draft``
            status with ``minimum_content_ready=False``. The caller (an
            application service) must add it to the repository and then
            call :meth:`collect_events` to publish the recorded events.

        Raises:
            InvariantViolation: If any field fails validation
                (empties, length limits).
        """
        subject_id = SubjectId.generate()
        subject = cls(
            id=subject_id,
            tenant_id=tenant_id,
            code=code,
            name=name,
            slug=slug,
            description=description,
            status=ContentStatus.DRAFT,
            minimum_content_ready=False,
            published_at=None,
            deprecated_at=None,
            created_at=None,
        )
        subject._record_event(
            SubjectCreated(
                subject_id=subject.id,
                tenant_id=subject.tenant_id,
                code=subject.code,
                slug=subject.slug,
                name=subject.name,
            )
        )
        return subject

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> SubjectId:
        """The Subject's unique identifier."""
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        """The Tenant that owns this Subject."""
        return self._tenant_id

    @property
    def code(self) -> str:
        """A short, tenant-unique code (e.g., ``"CS-101"``)."""
        return self._code

    @property
    def name(self) -> str:
        """A human-readable name."""
        return self._name

    @property
    def slug(self) -> str:
        """A URL-safe slug, unique within the Tenant."""
        return self._slug

    @property
    def description(self) -> str:
        """A longer description of the Subject's scope."""
        return self._description

    @property
    def status(self) -> ContentStatus:
        """The Subject's current lifecycle status."""
        return self._status

    @property
    def minimum_content_ready(self) -> bool:
        """True if the minimum-content gate has been met.

        Set by the application layer (typically via
        :meth:`mark_minimum_content_ready`) once at least one Concept or
        QuestionTemplate has been associated with this Subject. Required
        for :meth:`publish`.
        """
        return self._minimum_content_ready

    @property
    def published_at(self) -> datetime | None:
        """When the Subject was published, or ``None`` if not yet published."""
        return self._published_at

    @property
    def deprecated_at(self) -> datetime | None:
        """When the Subject was deprecated, or ``None`` if not deprecated."""
        return self._deprecated_at

    @property
    def created_at(self) -> datetime:
        """When the Subject was created."""
        return self._created_at

    @property
    def is_published(self) -> bool:
        """True if the Subject is in ``published`` status."""
        return self._status == ContentStatus.PUBLISHED

    @property
    def is_deprecated(self) -> bool:
        """True if the Subject is in ``deprecated`` status."""
        return self._status == ContentStatus.DEPRECATED

    @property
    def is_draft(self) -> bool:
        """True if the Subject is in ``draft`` status."""
        return self._status == ContentStatus.DRAFT

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants; raise :class:`InvariantViolation` on failure."""
        if not isinstance(self._code, str) or not self._code.strip():
            raise InvariantViolation(
                "Subject",
                "code must be a non-empty string",
            )
        if len(self._code) > self.MAX_CODE_LENGTH:
            raise InvariantViolation(
                "Subject",
                f"code must be at most {self.MAX_CODE_LENGTH} characters",
            )
        self._code = self._code.strip()

        if not isinstance(self._name, str) or not self._name.strip():
            raise InvariantViolation(
                "Subject",
                "name must be a non-empty string",
            )
        if len(self._name) > self.MAX_NAME_LENGTH:
            raise InvariantViolation(
                "Subject",
                f"name must be at most {self.MAX_NAME_LENGTH} characters",
            )
        self._name = self._name.strip()

        if not isinstance(self._slug, str) or not self._slug.strip():
            raise InvariantViolation(
                "Subject",
                "slug must be a non-empty string",
            )
        if len(self._slug) > self.MAX_SLUG_LENGTH:
            raise InvariantViolation(
                "Subject",
                f"slug must be at most {self.MAX_SLUG_LENGTH} characters",
            )
        self._slug = self._slug.strip()

        if not isinstance(self._description, str):
            raise InvariantViolation(
                "Subject",
                "description must be a string",
            )
        if len(self._description) > self.MAX_DESCRIPTION_LENGTH:
            raise InvariantViolation(
                "Subject",
                f"description must be at most {self.MAX_DESCRIPTION_LENGTH} characters",
            )

    def _assert_status(self, expected: ContentStatus, action: str) -> None:
        """Raise :class:`InvalidStateTransition` unless in ``expected`` status."""
        if self._status != expected:
            raise InvalidStateTransition(
                entity="Subject",
                current_state=self._status.value,
                attempted_action=action,
            )

    # ------------------------------------------------------------------
    # Minimum-content gate
    # ------------------------------------------------------------------

    def mark_minimum_content_ready(self) -> None:
        """Mark the minimum-content gate as met.

        Called by the application layer once at least one Concept or
        QuestionTemplate has been associated with this Subject. This is
        a precondition for :meth:`publish`. Idempotent — calling it
        again when already ready is a no-op (no event recorded).
        """
        if self._minimum_content_ready:
            return
        self._minimum_content_ready = True

    # ------------------------------------------------------------------
    # Lifecycle: publish / deprecate
    # ------------------------------------------------------------------

    def publish(self, now: datetime | None = None) -> None:
        """Transition the Subject from ``draft`` to ``published``.

        Pre-state: ``draft``.
        Post-state: ``published`` with ``published_at`` set.

        Raises:
            SubjectAlreadyPublished: If the Subject is already
                ``published``.
            SubjectNotPublishable: If the minimum-content gate has not
                been met (see :meth:`mark_minimum_content_ready`).
            InvalidStateTransition: If the Subject is ``deprecated``
                (deprecation is terminal).
        """
        if self._status == ContentStatus.PUBLISHED:
            raise SubjectAlreadyPublished(self._id)
        if self._status == ContentStatus.DEPRECATED:
            raise InvalidStateTransition(
                entity="Subject",
                current_state=self._status.value,
                attempted_action="publish",
            )
        self._assert_status(ContentStatus.DRAFT, "publish")
        if not self._minimum_content_ready:
            raise SubjectNotPublishable(self._id)

        timestamp = now or _utcnow()
        self._status = ContentStatus.PUBLISHED
        self._published_at = timestamp
        self._record_event(
            SubjectPublished(
                subject_id=self._id,
                tenant_id=self._tenant_id,
            )
        )

    def deprecate(self, now: datetime | None = None) -> None:
        """Transition the Subject from ``published`` to ``deprecated``.

        Pre-state: ``published``.
        Post-state: ``deprecated`` with ``deprecated_at`` set.

        Deprecation hides the Subject from new enrollees but keeps it
        accessible to existing learners. It is one-way: there is no
        ``unpublish`` or ``undeprecate``.

        Raises:
            SubjectAlreadyDeprecated: If the Subject is already
                ``deprecated``.
            InvalidStateTransition: If the Subject is in ``draft``
                (cannot deprecate something never published).
        """
        if self._status == ContentStatus.DEPRECATED:
            raise SubjectAlreadyDeprecated(self._id)
        self._assert_status(ContentStatus.PUBLISHED, "deprecate")

        timestamp = now or _utcnow()
        self._status = ContentStatus.DEPRECATED
        self._deprecated_at = timestamp
        self._record_event(
            SubjectDeprecated(
                subject_id=self._id,
                tenant_id=self._tenant_id,
            )
        )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Subject(id={self._id}, tenant_id={self._tenant_id}, "
            f"code={self._code!r}, status={self._status.value!r})"
        )


__all__ = ["Subject"]
