"""Content context — domain events.

Domain events are immutable records of something that *happened* in the
Content context. They are named in past tense and carry all the data a
subscriber needs to react.

All events inherit from :class:`DomainEvent` (which provides ``event_id``
and ``occurred_at``) and use ``@dataclass(frozen=True, kw_only=True)`` so
that required fields like ``subject_id`` can follow the inherited defaulted
fields without ordering issues.

These events are *pure data*. They contain no behaviour and no side
effects. Subscribers (search indexing, content cache invalidation,
analytics) live in the application and infrastructure layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.shared.ids import (
    ConceptId,
    ContentPackId,
    ContentVersionId,
    LearningObjectiveId,
    MisconceptionId,
    QuestionTemplateId,
    SubjectId,
    TemplateVersionId,
    TenantId,
    UserId,
)
from app.domain.shared.kernel import (
    DependencyType,
    DependencyWeight,
    Difficulty,
    DomainEvent,
    Importance,
    QuestionType,
    ReviewStage,
)
from app.domain.shared.value_objects import (
    DifficultyEstimate,
    DiscriminationEstimate,
    VersionNumber,
)

# ============================================================
# Subject events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class SubjectCreated(DomainEvent):
    """Emitted when a new Subject is created.

    Fired by :meth:`Subject.create`. The Subject starts in ``draft``
    status. Subscribers may provision per-tenant infrastructure (search
    index shard, analytics partition) keyed by ``tenant_id`` and
    ``subject_id``.
    """

    subject_id: SubjectId
    tenant_id: TenantId
    code: str
    slug: str
    name: str


@dataclass(frozen=True, kw_only=True)
class SubjectPublished(DomainEvent):
    """Emitted when a Subject transitions from ``draft`` to ``published``.

    Fired by :meth:`Subject.publish`. The Subject is now visible to
    learners. Subscribers should invalidate any cached subject listings
    and notify the catalogue projection.
    """

    subject_id: SubjectId
    tenant_id: TenantId


@dataclass(frozen=True, kw_only=True)
class SubjectDeprecated(DomainEvent):
    """Emitted when a published Subject is deprecated.

    Fired by :meth:`Subject.deprecate`. The Subject is hidden from new
    enrollees but remains accessible to existing learners for reference.
    Subscribers should stop scheduling new sessions for this Subject and
    notify learners currently enrolled.
    """

    subject_id: SubjectId
    tenant_id: TenantId


# ============================================================
# Concept events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class ConceptCreated(DomainEvent):
    """Emitted when a new Concept is created.

    Fired by :meth:`Concept.create`. The Concept starts in ``draft``
    status with no dependencies. Subscribers may pre-warm the concept
    graph projection for the parent Subject.
    """

    concept_id: ConceptId
    subject_id: SubjectId
    slug: str
    name: str
    difficulty: Difficulty
    importance: Importance


@dataclass(frozen=True, kw_only=True)
class ConceptRevised(DomainEvent):
    """Emitted when a draft Concept's pedagogical attributes are revised.

    Fired by :meth:`Concept.revise`. ``changed_fields`` is a mapping of
    field name → new value for any field that actually changed. The
    Concept remains in ``draft`` status after revision. Revising a
    published Concept requires a new ContentVersion — see
    :class:`ContentVersion`.
    """

    concept_id: ConceptId
    subject_id: SubjectId
    changed_fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class ConceptDependencyAdded(DomainEvent):
    """Emitted when a dependency is added to a Concept.

    Fired by :meth:`Concept.add_dependency`. Subscribers update the
    concept dependency graph projection and may re-run topological-sort
    checks for cycles (though cross-concept cycles span multiple
    Concepts and are detected by a domain service, not the aggregate).
    """

    concept_id: ConceptId
    subject_id: SubjectId
    target_concept_id: ConceptId
    dependency_type: DependencyType
    weight: DependencyWeight


@dataclass(frozen=True, kw_only=True)
class ConceptDependencyRemoved(DomainEvent):
    """Emitted when a dependency is removed from a Concept.

    Fired by :meth:`Concept.remove_dependency`. Subscribers update the
    concept dependency graph projection.
    """

    concept_id: ConceptId
    subject_id: SubjectId
    target_concept_id: ConceptId
    dependency_type: DependencyType


@dataclass(frozen=True, kw_only=True)
class ConceptPublished(DomainEvent):
    """Emitted when a Concept transitions from ``draft`` to ``published``.

    Fired by :meth:`Concept.publish`. Subscribers should invalidate any
    cached concept graph and update the catalogue projection.
    """

    concept_id: ConceptId
    subject_id: SubjectId


@dataclass(frozen=True, kw_only=True)
class ConceptDeprecated(DomainEvent):
    """Emitted when a published Concept is deprecated.

    Fired by :meth:`Concept.deprecate`. The Concept is hidden from new
    learners but remains in the dependency graph for reference.
    """

    concept_id: ConceptId
    subject_id: SubjectId


# ============================================================
# LearningObjective events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class LearningObjectiveCreated(DomainEvent):
    """Emitted when a new LearningObjective is created for a Concept.

    Fired by :meth:`LearningObjective.create`. The objective starts in
    ``draft`` status. Subscribers update the concept learning-objectives
    projection used by the assessment authoring UI.
    """

    learning_objective_id: LearningObjectiveId
    concept_id: ConceptId
    statement: str


# ============================================================
# Misconception events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class MisconceptionCreated(DomainEvent):
    """Emitted when a new Misconception is recorded for a LearningObjective.

    Fired by :meth:`Misconception.create`. Subscribers update the
    misconception library used by the assessment generator and the
    remediation recommender.
    """

    misconception_id: MisconceptionId
    learning_objective_id: LearningObjectiveId
    name: str


# ============================================================
# QuestionTemplate events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class QuestionTemplateCreated(DomainEvent):
    """Emitted when a new QuestionTemplate is created.

    Fired by :meth:`QuestionTemplate.create`. The template starts in
    ``draft`` status with no current version. Subscribers may pre-warm
    the template catalogue for the parent Subject.
    """

    template_id: QuestionTemplateId
    subject_id: SubjectId
    code: str
    question_type: QuestionType


@dataclass(frozen=True, kw_only=True)
class QuestionTemplatePublished(DomainEvent):
    """Emitted when a QuestionTemplate transitions to ``published``.

    Fired by :meth:`QuestionTemplate.publish`. The ``version_id`` field
    identifies the :class:`TemplateVersion` that becomes the current
    version. Subscribers should invalidate any cached question pool for
    the parent Subject.
    """

    template_id: QuestionTemplateId
    subject_id: SubjectId
    version_id: TemplateVersionId


@dataclass(frozen=True, kw_only=True)
class QuestionTemplateDeprecated(DomainEvent):
    """Emitted when a published QuestionTemplate is deprecated.

    Fired by :meth:`QuestionTemplate.deprecate`. Existing question
    instances may continue to be served until their parent ContentVersion
    is itself deprecated; new instances should not be drawn from this
    template.
    """

    template_id: QuestionTemplateId
    subject_id: SubjectId


# ============================================================
# ContentVersion events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class ContentVersionCreated(DomainEvent):
    """Emitted when a new ContentVersion is created for a Subject.

    Fired by :meth:`ContentVersion.create`. The version starts in
    ``draft`` status. Subscribers update the version history projection
    used by the content authoring UI.
    """

    content_version_id: ContentVersionId
    subject_id: SubjectId
    tenant_id: TenantId
    version_number: VersionNumber
    changelog: str


@dataclass(frozen=True, kw_only=True)
class ContentVersionDeprecated(DomainEvent):
    """Emitted when a ContentVersion transitions to ``deprecated``.

    Fired by :meth:`ContentVersion.deprecate`. Subscribers should stop
    serving questions from templates associated with this version and
    notify learners currently mid-session.
    """

    content_version_id: ContentVersionId
    subject_id: SubjectId
    deprecated_at: datetime


# ============================================================
# ContentPack events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class ContentPackCreated(DomainEvent):
    """Emitted when a new ContentPack is created.

    Fired by :meth:`ContentPack.create`. The pack starts in ``draft``
    status with an empty artifact set. Subscribers may pre-create the
    artifact storage bucket for the pack.
    """

    content_pack_id: ContentPackId
    subject_id: SubjectId
    author_id: UserId
    name: str


@dataclass(frozen=True, kw_only=True)
class ContentPackSubmittedForReview(DomainEvent):
    """Emitted when a draft ContentPack is submitted for review.

    Fired by :meth:`ContentPack.submit_for_review`. The pack transitions
    from ``draft`` to ``in_review``. Subscribers should notify the
    reviewers responsible for the first review stage
    (typically :class:`ReviewStage.PEER_REVIEW`).
    """

    content_pack_id: ContentPackId
    subject_id: SubjectId
    author_id: UserId


@dataclass(frozen=True, kw_only=True)
class ContentPackApproved(DomainEvent):
    """Emitted when a review stage approves a ContentPack.

    Fired by :meth:`ContentPack.approve`. The pack stays in ``in_review``
    status until every required :class:`ReviewStage` has approved it.
    Subscribers should advance the review to the next stage and notify
    the next set of reviewers, or — when this was the final stage —
    notify the author that the pack is ready to publish.
    """

    content_pack_id: ContentPackId
    subject_id: SubjectId
    stage: ReviewStage
    reviewer_id: UserId


@dataclass(frozen=True, kw_only=True)
class ContentPackChangesRequested(DomainEvent):
    """Emitted when a reviewer requests changes on a ContentPack.

    Fired by :meth:`ContentPack.request_changes`. The pack returns to
    ``draft`` status with the reviewer's notes attached. Subscribers
    should notify the author and clear any previously-recorded stage
    approvals (a fresh review cycle is required after the changes are
    addressed).
    """

    content_pack_id: ContentPackId
    subject_id: SubjectId
    reviewer_id: UserId
    notes: str


@dataclass(frozen=True, kw_only=True)
class ContentPackRejected(DomainEvent):
    """Emitted when a reviewer rejects a ContentPack.

    Fired by :meth:`ContentPack.reject`. The pack transitions to the
    terminal ``rejected`` status. Subscribers should notify the author
    and archive the pack's artifacts.
    """

    content_pack_id: ContentPackId
    subject_id: SubjectId
    reviewer_id: UserId
    reason: str


@dataclass(frozen=True, kw_only=True)
class ContentPackPublished(DomainEvent):
    """Emitted when a fully-reviewed ContentPack is published.

    Fired by :meth:`ContentPack.publish`. The pack transitions from
    ``in_review`` to ``published`` and is bound to a
    :class:`ContentVersionId`. Subscribers should materialize the pack's
    artifacts into the active content set and notify the catalogue
    projection.
    """

    content_pack_id: ContentPackId
    subject_id: SubjectId
    content_version_id: ContentVersionId
    published_at: datetime


# ============================================================
# TemplateVersion events
# ============================================================


@dataclass(frozen=True, kw_only=True)
class TemplateVersionCreated(DomainEvent):
    """Emitted when a new TemplateVersion is created for a QuestionTemplate.

    Fired at :class:`TemplateVersion` construction. The version is
    immutable after creation. Subscribers update the template version
    history projection used by the question authoring UI.

    Note:
        :class:`TemplateVersion` is a value object inside the
        :class:`QuestionTemplate` aggregate. This event is recorded on
        the parent :class:`QuestionTemplate` aggregate when a new
        version is attached via :meth:`QuestionTemplate.publish` (or an
        equivalent application-service orchestration step).
    """

    version_id: TemplateVersionId
    template_id: QuestionTemplateId
    content_version_id: ContentVersionId
    version_number: VersionNumber
    difficulty_estimate: DifficultyEstimate
    discrimination_estimate: DiscriminationEstimate


__all__ = [
    "ConceptCreated",
    "ConceptDependencyAdded",
    "ConceptDependencyRemoved",
    "ConceptDeprecated",
    "ConceptPublished",
    "ConceptRevised",
    "ContentPackApproved",
    "ContentPackChangesRequested",
    "ContentPackCreated",
    "ContentPackPublished",
    "ContentPackRejected",
    "ContentPackSubmittedForReview",
    "ContentVersionCreated",
    "ContentVersionDeprecated",
    "LearningObjectiveCreated",
    "MisconceptionCreated",
    "QuestionTemplateCreated",
    "QuestionTemplateDeprecated",
    "QuestionTemplatePublished",
    "SubjectCreated",
    "SubjectDeprecated",
    "SubjectPublished",
    "TemplateVersionCreated",
]
