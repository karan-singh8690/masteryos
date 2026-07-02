"""Content bounded context — domain layer.

Contains: aggregates (Subject, Concept, QuestionTemplate, ContentPack),
entities (LearningObjective, Misconception, ContentVersion), value
objects (ConceptDependency, TemplateVersion), domain events,
context-specific exceptions, and the abstract repository contracts.

This package is pure Python — no I/O, no framework dependencies. All
imports are from :mod:`app.domain.shared` (the shared kernel) or from
within this package.

Public surface:

- **Aggregates**: :class:`Subject`, :class:`Concept`,
  :class:`QuestionTemplate`, :class:`ContentPack`
- **Entities**: :class:`LearningObjective`, :class:`Misconception`,
  :class:`ContentVersion`
- **Value objects**: :class:`ConceptDependency`,
  :class:`TemplateVersion`
- **Events**: :class:`SubjectCreated`, :class:`SubjectPublished`,
  :class:`SubjectDeprecated`, :class:`ConceptCreated`,
  :class:`ConceptRevised`, :class:`ConceptDependencyAdded`,
  :class:`ConceptDependencyRemoved`, :class:`ConceptPublished`,
  :class:`ConceptDeprecated`, :class:`LearningObjectiveCreated`,
  :class:`MisconceptionCreated`, :class:`QuestionTemplateCreated`,
  :class:`QuestionTemplatePublished`,
  :class:`QuestionTemplateDeprecated`,
  :class:`ContentVersionCreated`, :class:`ContentVersionDeprecated`,
  :class:`ContentPackCreated`, :class:`ContentPackSubmittedForReview`,
  :class:`ContentPackApproved`, :class:`ContentPackChangesRequested`,
  :class:`ContentPackRejected`, :class:`ContentPackPublished`,
  :class:`TemplateVersionCreated`
- **Exceptions**: :class:`ContentError` and its subclasses
- **Repositories**: :class:`SubjectRepository`,
  :class:`ConceptRepository`, :class:`QuestionTemplateRepository`,
  :class:`ContentVersionRepository`, :class:`ContentPackRepository`
"""

from __future__ import annotations

from app.domain.content.concept import Concept
from app.domain.content.concept_dependency import ConceptDependency
from app.domain.content.content_pack import DEFAULT_REQUIRED_STAGES, ContentPack
from app.domain.content.content_version import ContentVersion
from app.domain.content.events import (
    ConceptCreated,
    ConceptDependencyAdded,
    ConceptDependencyRemoved,
    ConceptDeprecated,
    ConceptPublished,
    ConceptRevised,
    ContentPackApproved,
    ContentPackChangesRequested,
    ContentPackCreated,
    ContentPackPublished,
    ContentPackRejected,
    ContentPackSubmittedForReview,
    ContentVersionCreated,
    ContentVersionDeprecated,
    LearningObjectiveCreated,
    MisconceptionCreated,
    QuestionTemplateCreated,
    QuestionTemplateDeprecated,
    QuestionTemplatePublished,
    SubjectCreated,
    SubjectDeprecated,
    SubjectPublished,
    TemplateVersionCreated,
)
from app.domain.content.exceptions import (
    ConceptAlreadyDeprecated,
    ConceptAlreadyPublished,
    ConceptDependencyNotFound,
    ConceptDependencySubjectMismatch,
    ConceptDuplicateDependency,
    ConceptSelfDependency,
    ContentError,
    ContentPackAlreadyPublished,
    ContentPackAlreadyRejected,
    ContentPackAlreadySubmitted,
    ContentPackNotInReview,
    ContentPackReviewIncomplete,
    ContentPackStageAlreadyApproved,
    ContentVersionAlreadyDeprecated,
    LearningObjectiveStatementTooShort,
    QuestionTemplateAlreadyDeprecated,
    QuestionTemplateAlreadyPublished,
    SubjectAlreadyDeprecated,
    SubjectAlreadyPublished,
    SubjectNotPublishable,
)
from app.domain.content.learning_objective import LearningObjective
from app.domain.content.misconception import Misconception
from app.domain.content.question_template import QuestionTemplate
from app.domain.content.repository import (
    ConceptRepository,
    ContentPackRepository,
    ContentVersionRepository,
    QuestionTemplateRepository,
    SubjectRepository,
)
from app.domain.content.subject import Subject
from app.domain.content.template_version import TemplateVersion

__all__ = [
    # Aggregates
    "Subject",
    "Concept",
    "QuestionTemplate",
    "ContentPack",
    # Entities
    "LearningObjective",
    "Misconception",
    "ContentVersion",
    # Value objects
    "ConceptDependency",
    "TemplateVersion",
    # Constants
    "DEFAULT_REQUIRED_STAGES",
    # Events — Subject
    "SubjectCreated",
    "SubjectPublished",
    "SubjectDeprecated",
    # Events — Concept
    "ConceptCreated",
    "ConceptRevised",
    "ConceptDependencyAdded",
    "ConceptDependencyRemoved",
    "ConceptPublished",
    "ConceptDeprecated",
    # Events — LearningObjective
    "LearningObjectiveCreated",
    # Events — Misconception
    "MisconceptionCreated",
    # Events — QuestionTemplate
    "QuestionTemplateCreated",
    "QuestionTemplatePublished",
    "QuestionTemplateDeprecated",
    # Events — TemplateVersion
    "TemplateVersionCreated",
    # Events — ContentVersion
    "ContentVersionCreated",
    "ContentVersionDeprecated",
    # Events — ContentPack
    "ContentPackCreated",
    "ContentPackSubmittedForReview",
    "ContentPackApproved",
    "ContentPackChangesRequested",
    "ContentPackRejected",
    "ContentPackPublished",
    # Exceptions
    "ContentError",
    "SubjectNotPublishable",
    "SubjectAlreadyPublished",
    "SubjectAlreadyDeprecated",
    "ConceptSelfDependency",
    "ConceptDuplicateDependency",
    "ConceptDependencySubjectMismatch",
    "ConceptDependencyNotFound",
    "ConceptAlreadyPublished",
    "ConceptAlreadyDeprecated",
    "LearningObjectiveStatementTooShort",
    "QuestionTemplateAlreadyPublished",
    "QuestionTemplateAlreadyDeprecated",
    "ContentVersionAlreadyDeprecated",
    "ContentPackAlreadySubmitted",
    "ContentPackNotInReview",
    "ContentPackStageAlreadyApproved",
    "ContentPackReviewIncomplete",
    "ContentPackAlreadyPublished",
    "ContentPackAlreadyRejected",
    # Repositories
    "SubjectRepository",
    "ConceptRepository",
    "QuestionTemplateRepository",
    "ContentVersionRepository",
    "ContentPackRepository",
]
