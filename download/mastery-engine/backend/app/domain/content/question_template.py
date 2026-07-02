"""Content context — QuestionTemplate aggregate root.

A :class:`QuestionTemplate` is the *recipe* for generating questions of
a particular shape (multiple-choice, code-execution, free-response) for
a given :class:`Subject`. It owns a sequence of immutable
:class:`TemplateVersion` snapshots, exactly one of which (the
``current_version_id``) is the version actively used to generate
question instances for learners.

Lifecycle (state machine)::

        DRAFT ──publish(version_id)──► PUBLISHED ──deprecate()──► DEPRECATED
                                        (terminal-ish)

A newly-created template has no versions and no current version —
versions are attached by an application service (typically via a
``add_version`` flow that constructs a :class:`TemplateVersion` and
appends it to the template's history) before the template is
published. The :meth:`publish` method takes a ``version_id`` and
designates it as the current version atomically with the
draft → published transition.

Why templates are aggregate roots (and not part of the Concept
aggregate):

A single Concept is assessed by many templates (different shapes,
different difficulties, different parameterizations), and a single
template may assess multiple Concepts (e.g., a code-execution template
that exercises two prerequisite Concepts together). Many-to-many
relationships are best modelled as separate aggregates with a
reference (``subject_id`` here) rather than nested ownership.

Invariants enforced:
- A template cannot be published without a designated current version
  (``version_id`` argument to :meth:`publish`).
- A template cannot be re-published from PUBLISHED or DEPRECATED.
- A template cannot be deprecated from DRAFT (must be PUBLISHED first).
- A template cannot be deprecated more than once.

The template keeps an in-memory history of its
:class:`TemplateVersion` snapshots. Versions are appended-only; the
aggregate never mutates or removes a version once added.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.content.events import (
    QuestionTemplateCreated,
    QuestionTemplateDeprecated,
    QuestionTemplatePublished,
    TemplateVersionCreated,
)
from app.domain.content.exceptions import (
    QuestionTemplateAlreadyDeprecated,
    QuestionTemplateAlreadyPublished,
)
from app.domain.content.template_version import TemplateVersion
from app.domain.shared.ids import QuestionTemplateId, SubjectId, TemplateVersionId
from app.domain.shared.kernel import (
    AggregateRoot,
    ContentStatus,
    InvalidStateTransition,
    InvariantViolation,
    QuestionType,
)
from app.domain.shared.value_objects import VersionNumber


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class QuestionTemplate(AggregateRoot):
    """The QuestionTemplate aggregate root.

    Holds the template's identity (id, subject_id, code, question_type),
    lifecycle state (status, current_version_id, published_at,
    deprecated_at, created_at), and its appended-only history of
    :class:`TemplateVersion` snapshots.

    The public constructor is intended for **reconstitution** from
    persistence (the repository uses it to rebuild an aggregate from
    stored state). To create a *new* template, use
    :meth:`QuestionTemplate.create`.
    """

    #: Maximum length of the tenant-unique ``code``.
    MAX_CODE_LENGTH: int = 128

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: QuestionTemplateId,
        subject_id: SubjectId,
        code: str,
        question_type: QuestionType,
        status: ContentStatus = ContentStatus.DRAFT,
        current_version_id: TemplateVersionId | None = None,
        versions: list[TemplateVersion] | None = None,
        created_at: datetime | None = None,
        published_at: datetime | None = None,
        deprecated_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self._id: QuestionTemplateId = id
        self._subject_id: SubjectId = subject_id
        self._code: str = code
        self._question_type: QuestionType = question_type
        self._status: ContentStatus = status
        self._current_version_id: TemplateVersionId | None = current_version_id
        self._versions: list[TemplateVersion] = list(versions) if versions else []
        self._created_at: datetime = created_at or _utcnow()
        self._published_at: datetime | None = published_at
        self._deprecated_at: datetime | None = deprecated_at
        self._validate_invariants()
        self._validate_versions()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        subject_id: SubjectId,
        code: str,
        question_type: QuestionType,
    ) -> QuestionTemplate:
        """Create a new QuestionTemplate in ``draft`` status.

        The new template has no versions and no current version. An
        application service attaches a first :class:`TemplateVersion`
        via :meth:`add_version` before publishing.

        Args:
            subject_id: The Subject this template assesses content for.
            code: A short, subject-unique code (e.g.,
                ``"ALGO-QS-PARTITION-MC-01"``).
            question_type: The shape of question this template
                generates (multiple-choice, code-execution,
                free-response).

        Returns:
            A newly created, un-persisted :class:`QuestionTemplate` in
            ``draft`` status. The caller must add it to the repository
            and then call :meth:`collect_events` to publish the
            recorded events.

        Raises:
            InvariantViolation: If any field fails validation.
        """
        template_id = QuestionTemplateId.generate()
        template = cls(
            id=template_id,
            subject_id=subject_id,
            code=code,
            question_type=question_type,
            status=ContentStatus.DRAFT,
            current_version_id=None,
            versions=None,
            created_at=None,
            published_at=None,
            deprecated_at=None,
        )
        template._record_event(
            QuestionTemplateCreated(
                template_id=template.id,
                subject_id=template.subject_id,
                code=template.code,
                question_type=template.question_type,
            )
        )
        return template

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> QuestionTemplateId:
        """The template's unique identifier."""
        return self._id

    @property
    def subject_id(self) -> SubjectId:
        """The Subject this template assesses content for."""
        return self._subject_id

    @property
    def code(self) -> str:
        """A short, subject-unique code."""
        return self._code

    @property
    def question_type(self) -> QuestionType:
        """The shape of question this template generates."""
        return self._question_type

    @property
    def status(self) -> ContentStatus:
        """The template's current lifecycle status."""
        return self._status

    @property
    def current_version_id(self) -> TemplateVersionId | None:
        """The id of the version actively generating question instances.

        ``None`` for a template that has never been published.
        """
        return self._current_version_id

    @property
    def versions(self) -> list[TemplateVersion]:
        """A snapshot of the template's version history (appended-only).

        Returns a copy so callers cannot mutate the aggregate's internal
        list directly.
        """
        return list(self._versions)

    @property
    def created_at(self) -> datetime:
        """When the template was created."""
        return self._created_at

    @property
    def published_at(self) -> datetime | None:
        """When the template was published, or ``None`` if not yet published."""
        return self._published_at

    @property
    def deprecated_at(self) -> datetime | None:
        """When the template was deprecated, or ``None`` if not deprecated."""
        return self._deprecated_at

    @property
    def is_draft(self) -> bool:
        """True if the template is in ``draft`` status."""
        return self._status == ContentStatus.DRAFT

    @property
    def is_published(self) -> bool:
        """True if the template is in ``published`` status."""
        return self._status == ContentStatus.PUBLISHED

    @property
    def is_deprecated(self) -> bool:
        """True if the template is in ``deprecated`` status."""
        return self._status == ContentStatus.DEPRECATED

    @property
    def current_version(self) -> TemplateVersion | None:
        """The current :class:`TemplateVersion`, or ``None`` if none designated."""
        if self._current_version_id is None:
            return None
        for v in self._versions:
            if v.id == self._current_version_id:
                return v
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants."""
        if not isinstance(self._code, str) or not self._code.strip():
            raise InvariantViolation(
                "QuestionTemplate",
                "code must be a non-empty string",
            )
        if len(self._code) > self.MAX_CODE_LENGTH:
            raise InvariantViolation(
                "QuestionTemplate",
                f"code must be at most {self.MAX_CODE_LENGTH} characters",
            )
        self._code = self._code.strip()

        if not isinstance(self._question_type, QuestionType):
            raise InvariantViolation(
                "QuestionTemplate",
                f"question_type must be a QuestionType enum, got "
                f"{type(self._question_type).__name__}",
            )

    def _validate_versions(self) -> None:
        """Re-validate the version history on (re)construction.

        Catches corrupt state loaded from persistence — e.g., a
        ``current_version_id`` that does not match any version in the
        history, or duplicate version ids/numbers.
        """
        seen_ids: set = set()
        seen_numbers: set = set()
        for v in self._versions:
            if v.template_id != self._id:
                raise InvariantViolation(
                    "QuestionTemplate",
                    f"version {v.id} belongs to template {v.template_id}, not {self._id}",
                )
            if v.id in seen_ids:
                raise InvariantViolation(
                    "QuestionTemplate",
                    f"duplicate version id {v.id} in template history",
                )
            if v.version_number in seen_numbers:
                raise InvariantViolation(
                    "QuestionTemplate",
                    f"duplicate version number {v.version_number} in template history",
                )
            seen_ids.add(v.id)
            seen_numbers.add(v.version_number)

        if self._current_version_id is not None and self._current_version_id not in seen_ids:
            raise InvariantViolation(
                "QuestionTemplate",
                f"current_version_id {self._current_version_id} not found in version history",
            )

    def _assert_status(self, expected: ContentStatus, action: str) -> None:
        """Raise :class:`InvalidStateTransition` unless in ``expected`` status."""
        if self._status != expected:
            raise InvalidStateTransition(
                entity="QuestionTemplate",
                current_state=self._status.value,
                attempted_action=action,
            )

    # ------------------------------------------------------------------
    # Version management
    # ------------------------------------------------------------------

    def add_version(self, version: TemplateVersion) -> None:
        """Append a new :class:`TemplateVersion` to the template's history.

        Versions are appended-only — the aggregate never mutates or
        removes a version once added. The version's ``template_id``
        must match this template's id, and its ``version_number`` must
        be exactly one greater than the current highest (or 1 if this
        is the first version).

        Args:
            version: The :class:`TemplateVersion` to append.

        Raises:
            InvalidStateTransition: If the template is deprecated.
            InvariantViolation: If the version's ``template_id`` does
                not match, or if its ``version_number`` is not the
                next sequential number.
        """
        if self._status == ContentStatus.DEPRECATED:
            raise InvalidStateTransition(
                entity="QuestionTemplate",
                current_state=self._status.value,
                attempted_action="add_version",
            )

        if version.template_id != self._id:
            raise InvariantViolation(
                "QuestionTemplate",
                f"version {version.id} belongs to template {version.template_id}, "
                f"not {self._id}",
            )

        expected_number = (
            VersionNumber(1)
            if not self._versions
            else self._versions[-1].version_number.next()
        )
        if version.version_number != expected_number:
            raise InvariantViolation(
                "QuestionTemplate",
                f"version number must be {expected_number.value} (next sequential), "
                f"got {version.version_number.value}",
            )

        self._versions.append(version)
        self._record_event(
            TemplateVersionCreated(
                version_id=version.id,
                template_id=self._id,
                content_version_id=version.content_version_id,
                version_number=version.version_number,
                difficulty_estimate=version.difficulty_estimate,
                discrimination_estimate=version.discrimination_estimate,
            )
        )

    def get_version(self, version_id: TemplateVersionId) -> TemplateVersion | None:
        """Return the version with the given id, or ``None`` if not present."""
        for v in self._versions:
            if v.id == version_id:
                return v
        return None

    # ------------------------------------------------------------------
    # Lifecycle: publish / deprecate
    # ------------------------------------------------------------------

    def publish(
        self,
        version_id: TemplateVersionId,
        now: datetime | None = None,
    ) -> None:
        """Transition the template from ``draft`` to ``published`` and designate ``version_id`` as current.

        Pre-state: ``draft`` (for the lifecycle transition) — but a
        template that is already ``published`` may also call this to
        update its current version (e.g., when a new version is
        published and becomes the active one). See the note below.

        Post-state: ``published`` with ``current_version_id`` set to
        ``version_id`` and ``published_at`` set.

        Note:
            This method serves double duty: it transitions a draft
            template to published **and** updates the current version
            of an already-published template. The latter use case
            (rolling out a new version of an existing template) is
            common and is the only way to change ``current_version_id``
            after publication. To distinguish: if the template was
            already published, only a :class:`QuestionTemplatePublished`
            event is recorded (no state-transition semantics); if it
            was draft, the transition is atomic with the version
            designation.

        Args:
            version_id: The :class:`TemplateVersionId` to designate as
                the current version. Must already be in the template's
                version history (added via :meth:`add_version`).
            now: Optional timestamp (for testing); defaults to UTC now.

        Raises:
            QuestionTemplateAlreadyPublished: If the template is
                ``published`` **and** ``version_id`` is already the
                current version (no-op rejected).
            QuestionTemplateAlreadyDeprecated: If the template is
                ``deprecated``.
            InvariantViolation: If ``version_id`` is not in the
                template's version history.
        """
        if self._status == ContentStatus.DEPRECATED:
            raise QuestionTemplateAlreadyDeprecated(self._id)

        if version_id not in {v.id for v in self._versions}:
            raise InvariantViolation(
                "QuestionTemplate",
                f"version {version_id} not found in template {self._id} history",
            )

        if self._status == ContentStatus.PUBLISHED:
            if self._current_version_id == version_id:
                raise QuestionTemplateAlreadyPublished(self._id)
            # Already-published template: just rotate the current version.
            timestamp = now or _utcnow()
            self._current_version_id = version_id
            # ``published_at`` keeps the original publication timestamp.
            self._record_event(
                QuestionTemplatePublished(
                    template_id=self._id,
                    subject_id=self._subject_id,
                    version_id=version_id,
                )
            )
            return

        # Draft → published transition.
        self._assert_status(ContentStatus.DRAFT, "publish")
        timestamp = now or _utcnow()
        self._status = ContentStatus.PUBLISHED
        self._current_version_id = version_id
        self._published_at = timestamp
        self._record_event(
            QuestionTemplatePublished(
                template_id=self._id,
                subject_id=self._subject_id,
                version_id=version_id,
            )
        )

    def deprecate(self, now: datetime | None = None) -> None:
        """Transition the template from ``published`` to ``deprecated``.

        Pre-state: ``published``.
        Post-state: ``deprecated`` with ``deprecated_at`` set.

        Deprecation stops new question instances from being drawn from
        this template but does not affect instances already in flight.
        It is one-way.

        Raises:
            QuestionTemplateAlreadyDeprecated: If the template is
                already ``deprecated``.
            InvalidStateTransition: If the template is in ``draft``
                (cannot deprecate something never published).
        """
        if self._status == ContentStatus.DEPRECATED:
            raise QuestionTemplateAlreadyDeprecated(self._id)
        self._assert_status(ContentStatus.PUBLISHED, "deprecate")

        timestamp = now or _utcnow()
        self._status = ContentStatus.DEPRECATED
        self._deprecated_at = timestamp
        self._record_event(
            QuestionTemplateDeprecated(
                template_id=self._id,
                subject_id=self._subject_id,
            )
        )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"QuestionTemplate(id={self._id}, subject_id={self._subject_id}, "
            f"code={self._code!r}, type={self._question_type.value!r}, "
            f"status={self._status.value!r}, versions={len(self._versions)})"
        )


__all__ = ["QuestionTemplate"]
