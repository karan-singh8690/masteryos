"""Content context — Concept aggregate root.

A :class:`Concept` is a single, assessable unit of knowledge within a
:class:`Subject`. It carries its own lifecycle (draft → published →
deprecated), a set of pedagogical attributes (difficulty, importance),
and a directed graph of dependencies on sibling Concepts (within the
same Subject).

The Concept also owns — transitively, via its :class:`LearningObjective`
children — the :class:`Misconception` entities that describe how
learners can fail to achieve each objective. The objective and
misconception children are stored as part of the Concept aggregate
boundary and loaded/saved through the ConceptRepository.

Lifecycle (state machine)::

        DRAFT ──publish()──► PUBLISHED ──deprecate()──► DEPRECATED
                              (terminal-ish)

Invariants enforced:
- A Concept cannot depend on itself (see :class:`ConceptDependency`).
- A Concept cannot have two dependencies with the same
  ``(target_concept_id, dependency_type)`` — the pair is the natural
  key. Use a different type or remove the existing dependency first.
- A dependency may only target a Concept in the **same Subject**. The
  caller may pass ``target_subject_id`` to :meth:`add_dependency` for
  the aggregate to verify this; if it is omitted, the cross-subject
  check is deferred to the application service (which has access to a
  ConceptRepository).
- A Concept cannot be revised once published — to change a published
  Concept, cut a new :class:`ContentVersion` that supersedes the old
  one.
- A Concept cannot be re-published from PUBLISHED or DEPRECATED.
- A Concept cannot be deprecated from DRAFT (must be PUBLISHED first).

The Concept does **not** enforce acyclicity of the dependency graph
across multiple Concepts — that requires a global view of all Concepts
in a Subject and is the responsibility of a domain service
(typically invoked by the application layer on
:meth:`Concept.publish` or as a batch job).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.content.concept_dependency import ConceptDependency
from app.domain.content.events import (
    ConceptCreated,
    ConceptDependencyAdded,
    ConceptDependencyRemoved,
    ConceptDeprecated,
    ConceptPublished,
    ConceptRevised,
)
from app.domain.content.exceptions import (
    ConceptAlreadyDeprecated,
    ConceptAlreadyPublished,
    ConceptDependencyNotFound,
    ConceptDependencySubjectMismatch,
    ConceptDuplicateDependency,
    ConceptSelfDependency,
)
from app.domain.content.learning_objective import LearningObjective
from app.domain.content.misconception import Misconception
from app.domain.shared.ids import ConceptId, SubjectId
from app.domain.shared.kernel import (
    AggregateRoot,
    ContentStatus,
    DependencyType,
    DependencyWeight,
    Difficulty,
    Importance,
    InvalidStateTransition,
    InvariantViolation,
)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class Concept(AggregateRoot):
    """The Concept aggregate root.

    Holds the Concept's identity, pedagogical attributes, lifecycle
    state, and its directed dependency set. All mutations go through
    methods on this class, which enforce invariants and emit domain
    events via :meth:`AggregateRoot._record_event`.

    The public constructor is intended for **reconstitution** from
    persistence (the repository uses it to rebuild an aggregate from
    stored state). To create a *new* Concept, use :meth:`Concept.create`.

    The Concept also keeps an in-memory list of its child
    :class:`LearningObjective` entities (and, transitively, their
    :class:`Misconception` children). These are loaded and saved
    alongside the Concept via the ConceptRepository.
    """

    #: Maximum length of the URL-safe ``slug``.
    MAX_SLUG_LENGTH: int = 128

    #: Maximum length of the human-readable ``name``.
    MAX_NAME_LENGTH: int = 200

    #: Maximum length of the ``description``.
    MAX_DESCRIPTION_LENGTH: int = 4000

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        id: ConceptId,
        subject_id: SubjectId,
        slug: str,
        name: str,
        description: str,
        difficulty: Difficulty,
        importance: Importance,
        status: ContentStatus = ContentStatus.DRAFT,
        dependencies: list[ConceptDependency] | None = None,
        learning_objectives: list[LearningObjective] | None = None,
        created_at: datetime | None = None,
        published_at: datetime | None = None,
        deprecated_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self._id: ConceptId = id
        self._subject_id: SubjectId = subject_id
        self._slug: str = slug
        self._name: str = name
        self._description: str = description
        self._difficulty: Difficulty = difficulty
        self._importance: Importance = importance
        self._status: ContentStatus = status
        self._dependencies: list[ConceptDependency] = list(dependencies) if dependencies else []
        self._learning_objectives: list[LearningObjective] = (
            list(learning_objectives) if learning_objectives else []
        )
        self._created_at: datetime = created_at or _utcnow()
        self._published_at: datetime | None = published_at
        self._deprecated_at: datetime | None = deprecated_at
        self._validate_invariants()
        self._validate_dependencies()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        subject_id: SubjectId,
        slug: str,
        name: str,
        description: str,
        difficulty: Difficulty,
        importance: Importance,
    ) -> Concept:
        """Create a new Concept in ``draft`` status with no dependencies.

        Args:
            subject_id: The Subject this Concept belongs to. A Concept
                is always scoped to exactly one Subject.
            slug: A URL-safe slug, unique within the Subject.
            name: A human-readable name (e.g., ``"Quicksort"``).
            description: A longer description of the Concept's scope.
            difficulty: The authored difficulty of the Concept
                (easy / medium / hard).
            importance: The curriculum importance of the Concept
                (low / medium / high) — drives graduation gates.

        Returns:
            A newly created, un-persisted :class:`Concept` in ``draft``
            status with an empty dependency set. The caller (an
            application service) must add it to the repository and then
            call :meth:`collect_events` to publish the recorded events.

        Raises:
            InvariantViolation: If any field fails validation.
        """
        concept_id = ConceptId.generate()
        concept = cls(
            id=concept_id,
            subject_id=subject_id,
            slug=slug,
            name=name,
            description=description,
            difficulty=difficulty,
            importance=importance,
            status=ContentStatus.DRAFT,
            dependencies=None,
            learning_objectives=None,
            created_at=None,
            published_at=None,
            deprecated_at=None,
        )
        concept._record_event(
            ConceptCreated(
                concept_id=concept.id,
                subject_id=concept.subject_id,
                slug=concept.slug,
                name=concept.name,
                difficulty=concept.difficulty,
                importance=concept.importance,
            )
        )
        return concept

    # ------------------------------------------------------------------
    # Properties (read-only views of state)
    # ------------------------------------------------------------------

    @property
    def id(self) -> ConceptId:
        """The Concept's unique identifier."""
        return self._id

    @property
    def subject_id(self) -> SubjectId:
        """The Subject this Concept belongs to."""
        return self._subject_id

    @property
    def slug(self) -> str:
        """A URL-safe slug, unique within the Subject."""
        return self._slug

    @property
    def name(self) -> str:
        """A human-readable name."""
        return self._name

    @property
    def description(self) -> str:
        """A longer description of the Concept's scope."""
        return self._description

    @property
    def difficulty(self) -> Difficulty:
        """The authored difficulty of the Concept."""
        return self._difficulty

    @property
    def importance(self) -> Importance:
        """The curriculum importance of the Concept."""
        return self._importance

    @property
    def status(self) -> ContentStatus:
        """The Concept's current lifecycle status."""
        return self._status

    @property
    def dependencies(self) -> list[ConceptDependency]:
        """A snapshot of the Concept's directed dependencies.

        Returns a copy so callers cannot mutate the aggregate's internal
        list directly — dependency changes must go through
        :meth:`add_dependency` and :meth:`remove_dependency`.
        """
        return list(self._dependencies)

    @property
    def learning_objectives(self) -> list[LearningObjective]:
        """A snapshot of the Concept's child LearningObjectives.

        Returns a copy so callers cannot mutate the aggregate's internal
        list directly.
        """
        return list(self._learning_objectives)

    @property
    def created_at(self) -> datetime:
        """When the Concept was created."""
        return self._created_at

    @property
    def published_at(self) -> datetime | None:
        """When the Concept was published, or ``None`` if not yet published."""
        return self._published_at

    @property
    def deprecated_at(self) -> datetime | None:
        """When the Concept was deprecated, or ``None`` if not deprecated."""
        return self._deprecated_at

    @property
    def is_draft(self) -> bool:
        """True if the Concept is in ``draft`` status."""
        return self._status == ContentStatus.DRAFT

    @property
    def is_published(self) -> bool:
        """True if the Concept is in ``published`` status."""
        return self._status == ContentStatus.PUBLISHED

    @property
    def is_deprecated(self) -> bool:
        """True if the Concept is in ``deprecated`` status."""
        return self._status == ContentStatus.DEPRECATED

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_invariants(self) -> None:
        """Enforce field-level invariants."""
        if not isinstance(self._slug, str) or not self._slug.strip():
            raise InvariantViolation(
                "Concept",
                "slug must be a non-empty string",
            )
        if len(self._slug) > self.MAX_SLUG_LENGTH:
            raise InvariantViolation(
                "Concept",
                f"slug must be at most {self.MAX_SLUG_LENGTH} characters",
            )
        self._slug = self._slug.strip()

        if not isinstance(self._name, str) or not self._name.strip():
            raise InvariantViolation(
                "Concept",
                "name must be a non-empty string",
            )
        if len(self._name) > self.MAX_NAME_LENGTH:
            raise InvariantViolation(
                "Concept",
                f"name must be at most {self.MAX_NAME_LENGTH} characters",
            )
        self._name = self._name.strip()

        if not isinstance(self._description, str):
            raise InvariantViolation(
                "Concept",
                "description must be a string",
            )
        if len(self._description) > self.MAX_DESCRIPTION_LENGTH:
            raise InvariantViolation(
                "Concept",
                f"description must be at most {self.MAX_DESCRIPTION_LENGTH} characters",
            )

        if not isinstance(self._difficulty, Difficulty):
            raise InvariantViolation(
                "Concept",
                f"difficulty must be a Difficulty enum, got {type(self._difficulty).__name__}",
            )
        if not isinstance(self._importance, Importance):
            raise InvariantViolation(
                "Concept",
                f"importance must be an Importance enum, got {type(self._importance).__name__}",
            )

    def _validate_dependencies(self) -> None:
        """Re-validate the dependency set on (re)construction.

        Catches corrupt state loaded from persistence — e.g., a
        self-dependency that slipped past an older code path, or a
        duplicate ``(target, type)`` pair caused by a botched migration.
        """
        seen: set[tuple[Any, Any]] = set()
        for dep in self._dependencies:
            # ``ConceptDependency.__post_init__`` already rejects self-deps at
            # construction time, but a reconstituted aggregate bypasses that.
            if dep.source_concept_id != self._id:
                raise InvariantViolation(
                    "Concept",
                    f"dependency {dep!r} has source_concept_id != this Concept's id",
                )
            key = (dep.target_concept_id, dep.dependency_type)
            if key in seen:
                raise InvariantViolation(
                    "Concept",
                    f"duplicate dependency on {dep.target_concept_id}/{dep.dependency_type}",
                )
            seen.add(key)

    def _assert_status(self, expected: ContentStatus, action: str) -> None:
        """Raise :class:`InvalidStateTransition` unless in ``expected`` status."""
        if self._status != expected:
            raise InvalidStateTransition(
                entity="Concept",
                current_state=self._status.value,
                attempted_action=action,
            )

    def _find_dependency(
        self,
        target_concept_id: ConceptId,
        dependency_type: DependencyType,
    ) -> ConceptDependency | None:
        """Return the matching dependency, or ``None`` if not present."""
        for dep in self._dependencies:
            if dep.matches(target_concept_id=target_concept_id, dependency_type=dependency_type):
                return dep
        return None

    # ------------------------------------------------------------------
    # Dependency management
    # ------------------------------------------------------------------

    def add_dependency(
        self,
        target_concept_id: ConceptId,
        dependency_type: DependencyType,
        weight: DependencyWeight,
        *,
        target_subject_id: SubjectId | None = None,
    ) -> ConceptDependency:
        """Add a directed dependency from this Concept to ``target_concept_id``.

        Args:
            target_concept_id: The Concept this Concept depends on.
            dependency_type: The semantic type of the dependency
                (prerequisite, related, reinforces).
            weight: The strength of the dependency (weak, strong).
            target_subject_id: Optional — the Subject of the target
                Concept. When provided, the aggregate verifies that the
                target is in the same Subject as this Concept and
                raises :class:`ConceptDependencySubjectMismatch`
                otherwise. When omitted, the cross-subject check is
                deferred to the application service (which has access
                to a ConceptRepository).

        Returns:
            The newly-added :class:`ConceptDependency` (also recorded
            in ``self.dependencies``).

        Raises:
            ConceptSelfDependency: If ``target_concept_id`` is this
                Concept's own id.
            ConceptDuplicateDependency: If a dependency with the same
                ``(target_concept_id, dependency_type)`` already exists.
            ConceptDependencySubjectMismatch: If ``target_subject_id``
                is provided and differs from this Concept's Subject.
            InvalidStateTransition: If the Concept is deprecated
                (dependencies cannot be added to a terminal Concept).
            InvariantViolation: If the underlying
                :class:`ConceptDependency` rejects the pair (e.g., a
                self-dependency caught at VO construction).
        """
        if self._status == ContentStatus.DEPRECATED:
            raise InvalidStateTransition(
                entity="Concept",
                current_state=self._status.value,
                attempted_action="add_dependency",
            )

        if target_concept_id == self._id:
            raise ConceptSelfDependency(self._id)

        if self._find_dependency(target_concept_id, dependency_type) is not None:
            raise ConceptDuplicateDependency(self._id, target_concept_id, dependency_type)

        if target_subject_id is not None and target_subject_id != self._subject_id:
            raise ConceptDependencySubjectMismatch(
                concept_id=self._id,
                concept_subject_id=self._subject_id,
                target_concept_id=target_concept_id,
                target_subject_id=target_subject_id,
            )

        dependency = ConceptDependency(
            source_concept_id=self._id,
            target_concept_id=target_concept_id,
            dependency_type=dependency_type,
            weight=weight,
        )
        self._dependencies.append(dependency)
        self._record_event(
            ConceptDependencyAdded(
                concept_id=self._id,
                subject_id=self._subject_id,
                target_concept_id=target_concept_id,
                dependency_type=dependency_type,
                weight=weight,
            )
        )
        return dependency

    def remove_dependency(
        self,
        target_concept_id: ConceptId,
        dependency_type: DependencyType,
    ) -> None:
        """Remove the dependency on ``target_concept_id`` of ``dependency_type``.

        The ``(target_concept_id, dependency_type)`` pair is the natural
        key — if multiple weights were somehow allowed, this method
        would still remove a single deterministic entry.

        Args:
            target_concept_id: The Concept the dependency points to.
            dependency_type: The semantic type of the dependency.

        Raises:
            ConceptDependencyNotFound: If no such dependency exists.
            InvalidStateTransition: If the Concept is deprecated.
        """
        if self._status == ContentStatus.DEPRECATED:
            raise InvalidStateTransition(
                entity="Concept",
                current_state=self._status.value,
                attempted_action="remove_dependency",
            )

        match = self._find_dependency(target_concept_id, dependency_type)
        if match is None:
            raise ConceptDependencyNotFound(self._id, target_concept_id, dependency_type)

        self._dependencies.remove(match)
        self._record_event(
            ConceptDependencyRemoved(
                concept_id=self._id,
                subject_id=self._subject_id,
                target_concept_id=target_concept_id,
                dependency_type=dependency_type,
            )
        )

    # ------------------------------------------------------------------
    # Revision
    # ------------------------------------------------------------------

    def revise(
        self,
        name: str,
        description: str,
        difficulty: Difficulty,
        importance: Importance,
    ) -> dict[str, Any]:
        """Revise the Concept's pedagogical attributes.

        Only applies to a ``draft`` Concept. Revising a published Concept
        requires a new :class:`ContentVersion` — see the ContentVersion
        aggregate.

        Args:
            name: New name (validated).
            description: New description (validated).
            difficulty: New difficulty.
            importance: New importance.

        Returns:
            A mapping of ``field_name → new_value`` for any field that
            actually changed. Callers may use this to emit a more
            detailed event or audit entry.

        Raises:
            InvalidStateTransition: If the Concept is not in ``draft``
                status.
            InvariantViolation: If any new value fails validation.
        """
        self._assert_status(ContentStatus.DRAFT, "revise")

        changed: dict[str, Any] = {}
        if name.strip() != self._name:
            self._name = name
            changed["name"] = self._name
        if description != self._description:
            self._description = description
            changed["description"] = self._description
        if difficulty != self._difficulty:
            self._difficulty = difficulty
            changed["difficulty"] = self._difficulty
        if importance != self._importance:
            self._importance = importance
            changed["importance"] = self._importance

        # Re-validate after applying changes — invariant violations on
        # the new values will surface here before the caller commits.
        self._validate_invariants()

        if changed:
            self._record_event(
                ConceptRevised(
                    concept_id=self._id,
                    subject_id=self._subject_id,
                    changed_fields=changed,
                )
            )
        return changed

    # ------------------------------------------------------------------
    # Child entities: learning objectives & misconceptions
    # ------------------------------------------------------------------

    def add_learning_objective(self, objective: LearningObjective) -> None:
        """Adopt a :class:`LearningObjective` as a child of this Concept.

        The objective must already reference this Concept's id (set at
        :meth:`LearningObjective.create` time). The Concept records the
        objective's creation event on its own event stream so
        subscribers see a single, consistent event stream per aggregate
        transaction.

        Args:
            objective: The LearningObjective to adopt. Its
                ``concept_id`` must equal this Concept's id.

        Raises:
            InvalidStateTransition: If the Concept is deprecated.
            InvariantViolation: If the objective's ``concept_id``
                does not match this Concept's id.
        """
        if self._status == ContentStatus.DEPRECATED:
            raise InvalidStateTransition(
                entity="Concept",
                current_state=self._status.value,
                attempted_action="add_learning_objective",
            )
        if objective.concept_id != self._id:
            raise InvariantViolation(
                "Concept",
                f"LearningObjective {objective.id} belongs to concept "
                f"{objective.concept_id}, not {self._id}",
            )
        self._learning_objectives.append(objective)
        evt = objective.pull_creation_event()
        if evt is not None:
            self._record_event(evt)

    def add_misconception(self, misconception: Misconception) -> None:
        """Adopt a :class:`Misconception` for a child LearningObjective.

        The misconception must reference a LearningObjective that is
        already a child of this Concept. The Concept records the
        misconception's creation event on its own event stream.

        Args:
            misconception: The Misconception to adopt.

        Raises:
            InvalidStateTransition: If the Concept is deprecated.
            InvariantViolation: If the misconception's parent
                LearningObjective is not a child of this Concept.
        """
        if self._status == ContentStatus.DEPRECATED:
            raise InvalidStateTransition(
                entity="Concept",
                current_state=self._status.value,
                attempted_action="add_misconception",
            )
        parent_ids = {lo.id for lo in self._learning_objectives}
        if misconception.learning_objective_id not in parent_ids:
            raise InvariantViolation(
                "Concept",
                f"Misconception {misconception.id} references learning objective "
                f"{misconception.learning_objective_id}, which is not a child of "
                f"concept {self._id}",
            )
        # Store the misconception on its parent LearningObjective (the
        # LearningObjective entity owns its misconceptions in this
        # design). For now, we just record the creation event.
        evt = misconception.pull_creation_event()
        if evt is not None:
            self._record_event(evt)

    def get_learning_objective(self, objective_id: Any) -> LearningObjective | None:
        """Return the child LearningObjective with the given id, or ``None``."""
        for lo in self._learning_objectives:
            if lo.id == objective_id:
                return lo
        return None

    # ------------------------------------------------------------------
    # Lifecycle: publish / deprecate
    # ------------------------------------------------------------------

    def publish(self, now: datetime | None = None) -> None:
        """Transition the Concept from ``draft`` to ``published``.

        Pre-state: ``draft``.
        Post-state: ``published`` with ``published_at`` set.

        Note:
            This method does **not** check that the dependency graph is
            acyclic across the whole Subject. That is a domain-service
            responsibility — see the module docstring.

        Raises:
            ConceptAlreadyPublished: If the Concept is already
                ``published``.
            InvalidStateTransition: If the Concept is ``deprecated``.
        """
        if self._status == ContentStatus.PUBLISHED:
            raise ConceptAlreadyPublished(self._id)
        if self._status == ContentStatus.DEPRECATED:
            raise InvalidStateTransition(
                entity="Concept",
                current_state=self._status.value,
                attempted_action="publish",
            )
        self._assert_status(ContentStatus.DRAFT, "publish")

        timestamp = now or _utcnow()
        self._status = ContentStatus.PUBLISHED
        self._published_at = timestamp
        self._record_event(
            ConceptPublished(
                concept_id=self._id,
                subject_id=self._subject_id,
            )
        )

    def deprecate(self, now: datetime | None = None) -> None:
        """Transition the Concept from ``published`` to ``deprecated``.

        Pre-state: ``published``.
        Post-state: ``deprecated`` with ``deprecated_at`` set.

        Deprecation hides the Concept from new learners but keeps it in
        the dependency graph for reference. It is one-way.

        Raises:
            ConceptAlreadyDeprecated: If the Concept is already
                ``deprecated``.
            InvalidStateTransition: If the Concept is in ``draft``
                (cannot deprecate something never published).
        """
        if self._status == ContentStatus.DEPRECATED:
            raise ConceptAlreadyDeprecated(self._id)
        self._assert_status(ContentStatus.PUBLISHED, "deprecate")

        timestamp = now or _utcnow()
        self._status = ContentStatus.DEPRECATED
        self._deprecated_at = timestamp
        self._record_event(
            ConceptDeprecated(
                concept_id=self._id,
                subject_id=self._subject_id,
            )
        )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Concept(id={self._id}, subject_id={self._subject_id}, "
            f"slug={self._slug!r}, status={self._status.value!r}, "
            f"dependencies={len(self._dependencies)})"
        )


__all__ = ["Concept"]
