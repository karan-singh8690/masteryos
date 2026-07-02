"""Content context — abstract repository interfaces.

This module defines the *contracts* for loading and persisting the
Content-context aggregates and entities. Each interface is an abstract
base class — no implementation is provided here. Concrete
implementations live in the infrastructure layer (e.g., a
SQLAlchemy-backed repository).

Keeping the interfaces in the domain layer ensures that application
services depend only on the domain, not on infrastructure details. It
also enables swapping the persistence mechanism (e.g., for testing)
without touching the domain or application layers.

Concurrency contract:
- Implementations should enforce optimistic concurrency via a version
  column (see :class:`VersionNumber` in the shared kernel). If a
  :meth:`save` call detects a stale version, it must raise
  :class:`DuplicateEntity` or a similar domain error.
- Uniqueness of natural keys (``code``, ``slug``) must be enforced by
  the persistence store (unique index). The repository may surface
  this as :class:`DuplicateEntity` at the application layer's
  discretion.

Async contract:
- All methods are ``async`` to match the async SQLAlchemy pattern the
  rest of the backend uses (see :mod:`backend.app.infrastructure.database`).
- The application layer ``await``s repository calls inside an async
  unit-of-work.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.content.concept import Concept
from app.domain.content.content_pack import ContentPack
from app.domain.content.content_version import ContentVersion
from app.domain.content.question_template import QuestionTemplate
from app.domain.content.subject import Subject
from app.domain.shared.ids import (
    ConceptId,
    ContentPackId,
    ContentVersionId,
    QuestionTemplateId,
    SubjectId,
    TenantId,
)
from app.domain.shared.kernel import ContentStatus, EntityNotFound

# ============================================================
# Subject
# ============================================================


class SubjectRepository(ABC):
    """Abstract repository for the :class:`Subject` aggregate.

    Implementations must:
    - Load the full :class:`Subject` aggregate or return ``None``.
    - Persist the full aggregate on :meth:`save`.
    - Collect and surface domain events recorded on the aggregate via
      :meth:`AggregateRoot.collect_events` *after* a successful save
      (the application layer usually orchestrates this).
    - Enforce ``code`` and ``slug`` uniqueness per Tenant at the storage
      layer.
    """

    @abstractmethod
    async def get_by_id(self, subject_id: SubjectId) -> Subject | None:
        """Load a Subject by ID.

        Args:
            subject_id: The :class:`SubjectId` to look up.

        Returns:
            The fully reconstituted :class:`Subject` aggregate, or
            ``None`` if no Subject exists with that ID. Deprecated
            Subjects are still returned — they remain in storage for
            referential integrity.
        """

    @abstractmethod
    async def get_by_slug(self, tenant_id: TenantId, slug: str) -> Subject | None:
        """Load a Subject by its slug within a Tenant.

        Slug lookups are Tenant-scoped — the same slug may exist in
        multiple Tenants. Comparison is case-sensitive (the slug is
        stored as authored; tenants are encouraged but not required to
        use lowercase kebab-case).

        Args:
            tenant_id: The Tenant to scope the lookup to.
            slug: The slug to look up.

        Returns:
            The matching :class:`Subject`, or ``None`` if not found.
        """

    @abstractmethod
    async def get_by_code(self, tenant_id: TenantId, code: str) -> Subject | None:
        """Load a Subject by its code within a Tenant.

        Like :meth:`get_by_slug`, code lookups are Tenant-scoped.

        Args:
            tenant_id: The Tenant to scope the lookup to.
            code: The code to look up (e.g., ``"CS-101"``).

        Returns:
            The matching :class:`Subject`, or ``None`` if not found.
        """

    @abstractmethod
    async def add(self, subject: Subject) -> None:
        """Add a *new* Subject to the repository.

        Use this for Subjects that have never been persisted (i.e.,
        created via :meth:`Subject.create`). For Subjects loaded via
        ``get_by_*`` and then modified, use :meth:`save`.

        Args:
            subject: The new :class:`Subject` aggregate to persist.

        Raises:
            DuplicateEntity: If a Subject with the same ``code`` or
                ``slug`` already exists in the same Tenant (surfaced
                from the storage-layer unique constraint).
        """

    @abstractmethod
    async def save(self, subject: Subject) -> None:
        """Persist changes to an *existing* Subject.

        Args:
            subject: The modified :class:`Subject` aggregate to persist.

        Raises:
            EntityNotFound: If the Subject has been deleted by another
                transaction since it was loaded.
            DuplicateEntity: If the version is stale (concurrent
                modification by another transaction).
        """

    # ------------------------------------------------------------------
    # Optional helpers (non-abstract; implementations may override)
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, subject_id: SubjectId) -> Subject:
        """Load a Subject by ID, raising :class:`EntityNotFound` if absent."""
        subject = await self.get_by_id(subject_id)
        if subject is None:
            raise EntityNotFound("Subject", subject_id)
        return subject


# ============================================================
# Concept
# ============================================================


class ConceptRepository(ABC):
    """Abstract repository for the :class:`Concept` aggregate.

    Implementations must:
    - Load the full :class:`Concept` aggregate (root + child
      :class:`LearningObjective` entities and their :class:`Misconception`
      children + the dependency set) or return ``None``.
    - Persist the full aggregate on :meth:`save`, including any nested
      entities and dependencies.
    - Enforce ``slug`` uniqueness per Subject at the storage layer.
    """

    @abstractmethod
    async def get_by_id(self, concept_id: ConceptId) -> Concept | None:
        """Load a Concept by ID.

        Returns the fully reconstituted :class:`Concept` aggregate
        (with all child entities and dependencies), or ``None`` if no
        Concept exists with that ID.
        """

    @abstractmethod
    async def get_by_slug(self, subject_id: SubjectId, slug: str) -> Concept | None:
        """Load a Concept by its slug within a Subject.

        Slug lookups are Subject-scoped — the same slug may exist in
        multiple Subjects.

        Args:
            subject_id: The Subject to scope the lookup to.
            slug: The slug to look up.

        Returns:
            The matching :class:`Concept`, or ``None`` if not found.
        """

    @abstractmethod
    async def list_by_subject(self, subject_id: SubjectId) -> list[Concept]:
        """List all Concepts in a Subject.

        Returns every Concept in the Subject, regardless of status
        (draft, published, deprecated). Callers that want only
        learner-visible Concepts should filter by ``status ==
        ContentStatus.PUBLISHED``.

        Args:
            subject_id: The Subject to list Concepts for.

        Returns:
            A list of :class:`Concept` aggregates. Empty if the Subject
            has no Concepts (or does not exist).
        """

    @abstractmethod
    async def add(self, concept: Concept) -> None:
        """Add a *new* Concept to the repository.

        Args:
            concept: The new :class:`Concept` aggregate to persist.

        Raises:
            DuplicateEntity: If a Concept with the same ``slug``
                already exists in the same Subject.
        """

    @abstractmethod
    async def save(self, concept: Concept) -> None:
        """Persist changes to an *existing* Concept.

        Args:
            concept: The modified :class:`Concept` aggregate to persist.

        Raises:
            EntityNotFound: If the Concept has been deleted by another
                transaction since it was loaded.
            DuplicateEntity: If the version is stale (concurrent
                modification).
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, concept_id: ConceptId) -> Concept:
        """Load a Concept by ID, raising :class:`EntityNotFound` if absent."""
        concept = await self.get_by_id(concept_id)
        if concept is None:
            raise EntityNotFound("Concept", concept_id)
        return concept


# ============================================================
# QuestionTemplate
# ============================================================


class QuestionTemplateRepository(ABC):
    """Abstract repository for the :class:`QuestionTemplate` aggregate.

    Implementations must:
    - Load the full :class:`QuestionTemplate` aggregate (root + its
      :class:`TemplateVersion` history) or return ``None``.
    - Persist the full aggregate on :meth:`save`, including all
      versions. Versions are appended-only — the repository must
      never overwrite or delete a version row.
    - Enforce ``code`` uniqueness per Subject at the storage layer.
    """

    @abstractmethod
    async def get_by_id(self, template_id: QuestionTemplateId) -> QuestionTemplate | None:
        """Load a QuestionTemplate by ID.

        Returns the fully reconstituted :class:`QuestionTemplate`
        aggregate (with all :class:`TemplateVersion` snapshots in
        order), or ``None`` if no template exists with that ID.
        """

    @abstractmethod
    async def get_by_code(self, subject_id: SubjectId, code: str) -> QuestionTemplate | None:
        """Load a QuestionTemplate by its code within a Subject.

        Args:
            subject_id: The Subject to scope the lookup to.
            code: The code to look up.

        Returns:
            The matching :class:`QuestionTemplate`, or ``None`` if not
            found.
        """

    @abstractmethod
    async def list_by_subject(self, subject_id: SubjectId) -> list[QuestionTemplate]:
        """List all QuestionTemplates in a Subject.

        Returns every template in the Subject, regardless of status.

        Args:
            subject_id: The Subject to list templates for.

        Returns:
            A list of :class:`QuestionTemplate` aggregates. Empty if
            the Subject has no templates.
        """

    @abstractmethod
    async def add(self, template: QuestionTemplate) -> None:
        """Add a *new* QuestionTemplate to the repository.

        Args:
            template: The new :class:`QuestionTemplate` aggregate to
                persist.

        Raises:
            DuplicateEntity: If a template with the same ``code``
                already exists in the same Subject.
        """

    @abstractmethod
    async def save(self, template: QuestionTemplate) -> None:
        """Persist changes to an *existing* QuestionTemplate.

        Args:
            template: The modified :class:`QuestionTemplate` aggregate
                to persist.

        Raises:
            EntityNotFound: If the template has been deleted by another
                transaction since it was loaded.
            DuplicateEntity: If the version is stale.
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, template_id: QuestionTemplateId) -> QuestionTemplate:
        """Load a QuestionTemplate by ID, raising :class:`EntityNotFound` if absent."""
        template = await self.get_by_id(template_id)
        if template is None:
            raise EntityNotFound("QuestionTemplate", template_id)
        return template


# ============================================================
# ContentVersion
# ============================================================


class ContentVersionRepository(ABC):
    """Abstract repository for the :class:`ContentVersion` entity.

    Implementations must:
    - Load the :class:`ContentVersion` or return ``None``.
    - Persist a new version on :meth:`add`. Updates to an existing
      version (e.g., the draft → published transition) go through
      :meth:`add` as well — ContentVersion is an entity with its own
      repository, not an aggregate root, so there is no separate
      ``save`` method. The repository performs an upsert keyed on
      :class:`ContentVersionId`.
    - Enforce ``version_number`` uniqueness per Subject at the storage
      layer.
    """

    @abstractmethod
    async def get_by_id(self, content_version_id: ContentVersionId) -> ContentVersion | None:
        """Load a ContentVersion by ID.

        Returns the :class:`ContentVersion`, or ``None`` if no version
        exists with that ID.
        """

    @abstractmethod
    async def get_active_by_subject(self, subject_id: SubjectId) -> ContentVersion | None:
        """Load the active (published) ContentVersion for a Subject.

        At most one ContentVersion per Subject is in the ``published``
        status at any time — publishing a new version implicitly
        deprecates the previous one (the application service
        orchestrates this).

        Args:
            subject_id: The Subject to look up the active version for.

        Returns:
            The published :class:`ContentVersion` for the Subject, or
            ``None`` if no version has been published yet.
        """

    @abstractmethod
    async def add(self, content_version: ContentVersion) -> None:
        """Add a *new* ContentVersion (or upsert an existing one).

        Args:
            content_version: The :class:`ContentVersion` to persist.

        Raises:
            DuplicateEntity: If a ContentVersion with the same
                ``version_number`` already exists in the same Subject
                (for new versions only — upserts of existing versions
                by ID are allowed).
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, content_version_id: ContentVersionId) -> ContentVersion:
        """Load a ContentVersion by ID, raising :class:`EntityNotFound` if absent."""
        version = await self.get_by_id(content_version_id)
        if version is None:
            raise EntityNotFound("ContentVersion", content_version_id)
        return version


# ============================================================
# ContentPack
# ============================================================


class ContentPackRepository(ABC):
    """Abstract repository for the :class:`ContentPack` aggregate.

    Implementations must:
    - Load the full :class:`ContentPack` aggregate (root + artifact
      references + approved stages + change-request notes) or return
      ``None``.
    - Persist the full aggregate on :meth:`save`.
    - Enforce ``name`` uniqueness per Subject+Author at the storage
      layer (optional — duplicates are pedagogically confusing but not
      strictly invalid).
    """

    @abstractmethod
    async def get_by_id(self, content_pack_id: ContentPackId) -> ContentPack | None:
        """Load a ContentPack by ID.

        Returns the fully reconstituted :class:`ContentPack` aggregate,
        or ``None`` if no pack exists with that ID.
        """

    @abstractmethod
    async def list_by_status(
        self,
        subject_id: SubjectId,
        status: ContentStatus,
    ) -> list[ContentPack]:
        """List ContentPacks in a Subject filtered by status.

        Args:
            subject_id: The Subject to list packs for.
            status: The lifecycle status to filter by (e.g.,
                :class:`ContentStatus.IN_REVIEW` to find packs awaiting
                review).

        Returns:
            A list of :class:`ContentPack` aggregates matching the
            filter. Empty if none match.
        """

    @abstractmethod
    async def add(self, content_pack: ContentPack) -> None:
        """Add a *new* ContentPack to the repository.

        Args:
            content_pack: The new :class:`ContentPack` aggregate to
                persist.
        """

    @abstractmethod
    async def save(self, content_pack: ContentPack) -> None:
        """Persist changes to an *existing* ContentPack.

        Args:
            content_pack: The modified :class:`ContentPack` aggregate
                to persist.

        Raises:
            EntityNotFound: If the pack has been deleted by another
                transaction since it was loaded.
            DuplicateEntity: If the version is stale.
        """

    # ------------------------------------------------------------------
    # Optional helpers
    # ------------------------------------------------------------------

    async def get_by_id_or_raise(self, content_pack_id: ContentPackId) -> ContentPack:
        """Load a ContentPack by ID, raising :class:`EntityNotFound` if absent."""
        pack = await self.get_by_id(content_pack_id)
        if pack is None:
            raise EntityNotFound("ContentPack", content_pack_id)
        return pack


__all__ = [
    "ConceptRepository",
    "ContentPackRepository",
    "ContentVersionRepository",
    "QuestionTemplateRepository",
    "SubjectRepository",
]
