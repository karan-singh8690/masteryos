"""Content context — ContentVersion entity.

A :class:`ContentVersion` is a named, numbered snapshot of *all*
content artifacts (Concepts, QuestionTemplates and their versions,
LearningObjectives, Misconceptions) for a single :class:`Subject` at a
point in time. It is the unit of atomic publication: when a ContentVersion
is published, every artifact referenced by it becomes visible to
learners simultaneously, and when it is deprecated, every referenced
artifact disappears from new sessions simultaneously.

Why versions exist:

Learner-facing content must change in a controlled way. A learner
mid-session must not see Concept A "v1" turn into Concept A "v2"
halfway through an attempt — that would corrupt their mastery
evidence. ContentVersion gives operators a way to stage a coherent
set of changes (a "content pack") and cut it over atomically.

Design notes:

- A ContentVersion is an **entity** (it has identity via
  :class:`ContentVersionId`), not an aggregate root of its own — but
  for pragmatic reasons it is loaded/saved via its own
  :class:`ContentVersionRepository` rather than through the Subject
  aggregate. This is a deliberate deviation from the strict
  "one-aggregate-per-repository" rule: Subject would otherwise become
  a god-aggregate over every Concept and QuestionTemplate in the
  tenant, which is unworkable. See ADR-0012 for the full rationale.
- A ContentVersion's ``version_number`` is scoped to its Subject
  (1, 2, 3, ...) and is assigned by the application service at
  creation time, typically by querying the repository for the highest
  existing number and incrementing.

Lifecycle (state machine)::

        DRAFT ──publish()──► PUBLISHED ──deprecate()──► DEPRECATED
                              (terminal-ish)

Note: this entity exposes ``deprecate()`` (the only state transition
explicitly required by the spec) but does not expose ``publish()``.
Publication of a ContentVersion is orchestrated by the
:class:`ContentPack` aggregate: when a fully-reviewed pack is
published via :meth:`ContentPack.publish`, the application service
also marks the bound ContentVersion as published. This keeps the
review gate (which lives on ContentPack) as the single chokepoint
for content going live.

Invariants:
- ``version_number`` must be >= 1 (enforced by :class:`VersionNumber`).
- ``changelog`` must be a non-empty string (a version with no
  changelog is unreviewable).
- ``status`` is one of :class:`ContentStatus` (DRAFT, PUBLISHED,
  DEPRECATED — the IN_REVIEW and REJECTED values are not used here).
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.content.events import (
    ContentVersionCreated,
    ContentVersionDeprecated,
)
from app.domain.content.exceptions import ContentVersionAlreadyDeprecated
from app.domain.shared.ids import ContentVersionId, SubjectId, TenantId
from app.domain.shared.kernel import (
    ContentStatus,
    Entity,
    InvalidStateTransition,
    InvariantViolation,
)
from app.domain.shared.value_objects import VersionNumber


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class ContentVersion(Entity):
    """A named, numbered snapshot of all content artifacts for a Subject.

    Equality is by :class:`ContentVersionId` — two versions with the
    same ID are the same entity, even if their other fields differ.

    Attributes:
        id: The unique identifier for this version.
        subject_id: The Subject this version snapshots content for.
        tenant_id: The Tenant that owns the Subject (denormalized for
            tenant-scoped queries).
        version_number: The monotonically-increasing version number
            within the parent Subject (starts at 1).
        status: The lifecycle status of the version. Newly-created
            versions are ``draft``; publication is orchestrated by the
            :class:`ContentPack` aggregate.
        changelog: A human-readable summary of what changed in this
            version relative to the previous one. Required.
        published_at: When the version was published, or ``None`` if
            not yet published.
        deprecated_at: When the version was deprecated, or ``None`` if
            not deprecated.
    """

    #: Maximum length of the ``changelog``.
    MAX_CHANGELOG_LENGTH: int = 4000

    def __init__(
        self,
        *,
        id: ContentVersionId,
        subject_id: SubjectId,
        tenant_id: TenantId,
        version_number: VersionNumber,
        status: ContentStatus = ContentStatus.DRAFT,
        changelog: str,
        published_at: datetime | None = None,
        deprecated_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.subject_id = subject_id
        self.tenant_id = tenant_id
        self.version_number = version_number
        self.status = status
        self.changelog = changelog
        self.published_at = published_at
        self.deprecated_at = deprecated_at
        self.created_at: datetime = created_at or _utcnow()
        self._validate()
        # List of domain events accumulated by this entity. Unlike an
        # AggregateRoot, an entity does not own its event stream — but
        # for pragmatic reasons (ContentVersion has its own repository
        # and may be acted on without a wrapping aggregate), we collect
        # events here and let the repository/application service
        # retrieve them via :meth:`collect_events`.
        self._domain_events: list = []

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        subject_id: SubjectId,
        tenant_id: TenantId,
        version_number: VersionNumber,
        changelog: str,
    ) -> ContentVersion:
        """Create a new ContentVersion in ``draft`` status.

        Args:
            subject_id: The Subject this version snapshots content for.
            tenant_id: The Tenant that owns the Subject.
            version_number: The version number (must be >= 1, scoped to
                the Subject).
            changelog: A human-readable summary of what changed in this
                version relative to the previous one.

        Returns:
            A newly created, un-persisted :class:`ContentVersion` in
            ``draft`` status. The caller must add it to the repository
            and then call :meth:`collect_events` to publish the
            recorded events.

        Raises:
            InvariantViolation: If any field fails validation.
        """
        version = cls(
            id=ContentVersionId.generate(),
            subject_id=subject_id,
            tenant_id=tenant_id,
            version_number=version_number,
            status=ContentStatus.DRAFT,
            changelog=changelog,
            published_at=None,
            deprecated_at=None,
            created_at=None,
        )
        version._record_event(
            ContentVersionCreated(
                content_version_id=version.id,
                subject_id=version.subject_id,
                tenant_id=version.tenant_id,
                version_number=version.version_number,
                changelog=version.changelog,
            )
        )
        return version

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        """Enforce field-level invariants."""
        if not isinstance(self.version_number, VersionNumber):
            raise InvariantViolation(
                "ContentVersion",
                f"version_number must be a VersionNumber, got {type(self.version_number).__name__}",
            )
        if not isinstance(self.changelog, str) or not self.changelog.strip():
            raise InvariantViolation(
                "ContentVersion",
                "changelog must be a non-empty string",
            )
        if len(self.changelog) > self.MAX_CHANGELOG_LENGTH:
            raise InvariantViolation(
                "ContentVersion",
                f"changelog must be at most {self.MAX_CHANGELOG_LENGTH} characters",
            )
        self.changelog = self.changelog.strip()

        # Restrict the status to the values that make sense for a ContentVersion.
        allowed = {ContentStatus.DRAFT, ContentStatus.PUBLISHED, ContentStatus.DEPRECATED}
        if self.status not in allowed:
            raise InvariantViolation(
                "ContentVersion",
                f"status must be one of {[s.value for s in allowed]}, got {self.status.value!r}",
            )

    # ------------------------------------------------------------------
    # Event collection (mirrors AggregateRoot's surface for entities
    # that have their own repository but no enclosing aggregate root)
    # ------------------------------------------------------------------

    def _record_event(self, event) -> None:  # type: ignore[no-untyped-def]
        """Record a domain event to be published after persistence."""
        if not hasattr(self, "_domain_events") or self._domain_events is None:
            self._domain_events = []
        self._domain_events.append(event)

    def collect_events(self) -> list:
        """Return all recorded domain events and clear the internal list."""
        events = getattr(self, "_domain_events", []) or []
        self._domain_events = []
        return list(events)

    def clear_events(self) -> None:
        """Clear all recorded events without returning them."""
        self._domain_events = []

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _assert_status(self, expected: ContentStatus, action: str) -> None:
        """Raise :class:`InvalidStateTransition` unless in ``expected`` status."""
        if self.status != expected:
            raise InvalidStateTransition(
                entity="ContentVersion",
                current_state=self.status.value,
                attempted_action=action,
            )

    # ------------------------------------------------------------------
    # Lifecycle: publish / deprecate
    # ------------------------------------------------------------------

    def publish(self, now: datetime | None = None) -> None:
        """Transition the version from ``draft`` to ``published``.

        Pre-state: ``draft``.
        Post-state: ``published`` with ``published_at`` set.

        Note:
            In normal operation, this method is invoked by the
            application service in the same transaction as
            :meth:`ContentPack.publish` — the ContentPack review gate
            is the chokepoint, and this method just records the
            lifecycle transition.

        Raises:
            InvalidStateTransition: If the version is not in ``draft``
                status (already published or deprecated).
        """
        self._assert_status(ContentStatus.DRAFT, "publish")
        timestamp = now or _utcnow()
        self.status = ContentStatus.PUBLISHED
        self.published_at = timestamp

    def deprecate(self, now: datetime | None = None) -> None:
        """Transition the version from ``published`` to ``deprecated``.

        Pre-state: ``published``.
        Post-state: ``deprecated`` with ``deprecated_at`` set.

        Deprecation stops new question instances from being drawn from
        any template version bound to this content version. It is
        one-way.

        Raises:
            ContentVersionAlreadyDeprecated: If the version is already
                ``deprecated``.
            InvalidStateTransition: If the version is in ``draft``
                (cannot deprecate something never published).
        """
        if self.status == ContentStatus.DEPRECATED:
            raise ContentVersionAlreadyDeprecated(self.id)
        self._assert_status(ContentStatus.PUBLISHED, "deprecate")

        timestamp = now or _utcnow()
        self.status = ContentStatus.DEPRECATED
        self.deprecated_at = timestamp
        self._record_event(
            ContentVersionDeprecated(
                content_version_id=self.id,
                subject_id=self.subject_id,
                deprecated_at=timestamp,
            )
        )

    # ------------------------------------------------------------------
    # Convenience predicates
    # ------------------------------------------------------------------

    @property
    def is_draft(self) -> bool:
        """True if the version is in ``draft`` status."""
        return self.status == ContentStatus.DRAFT

    @property
    def is_published(self) -> bool:
        """True if the version is in ``published`` status."""
        return self.status == ContentStatus.PUBLISHED

    @property
    def is_deprecated(self) -> bool:
        """True if the version is in ``deprecated`` status."""
        return self.status == ContentStatus.DEPRECATED

    @property
    def is_active(self) -> bool:
        """True if the version is the active published version for its Subject.

        Convenience predicate: a version is "active" iff it is
        published (not draft, not deprecated). The repository's
        :meth:`get_active_by_subject` returns at most one such version
        per Subject.
        """
        return self.status == ContentStatus.PUBLISHED

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"ContentVersion(id={self.id}, subject_id={self.subject_id}, "
            f"version_number={self.version_number.value}, status={self.status.value!r})"
        )


__all__ = ["ContentVersion"]
