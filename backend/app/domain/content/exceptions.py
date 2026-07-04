"""Content context — domain-specific exceptions.

These exceptions are raised by the Content-context aggregates when
invariants are violated or invalid state transitions are attempted.
They are *narrow* subclasses of :class:`DomainError` so that callers can
catch a specific failure mode without inspecting error messages.

All exceptions are pure Python and carry no framework dependencies.
"""

from __future__ import annotations

from typing import Any

from app.domain.shared.kernel import DomainError


class ContentError(DomainError):
    """Base class for all Content-context domain errors.

    Catch this to handle any content-specific failure generically.
    """


# ------------------------------------------------------------------
# Subject
# ------------------------------------------------------------------


class SubjectNotPublishable(ContentError):
    """Raised when publishing a Subject whose minimum-content gate is not met.

    Invariant: a Subject cannot transition from ``draft`` to ``published``
    until at least one piece of content (e.g., a Concept, QuestionTemplate,
    or ContentVersion) has been associated with it. The application layer
    calls :meth:`Subject.mark_minimum_content_ready` once that gate is met;
    attempting :meth:`Subject.publish` before that raises this exception.
    """

    def __init__(self, subject_id: Any) -> None:
        super().__init__(
            f"Subject {subject_id} is not publishable: minimum-content gate not met",
            code="SUBJECT_NOT_PUBLISHABLE",
        )
        self.subject_id = subject_id


class SubjectAlreadyPublished(ContentError):
    """Raised when publishing an already-published Subject.

    Invariant: a Subject in ``published`` status cannot be re-published.
    To update published content, revise the underlying artifacts and cut a
    new :class:`ContentVersion` instead.
    """

    def __init__(self, subject_id: Any) -> None:
        super().__init__(
            f"Subject {subject_id} is already published",
            code="SUBJECT_ALREADY_PUBLISHED",
        )
        self.subject_id = subject_id


class SubjectAlreadyDeprecated(ContentError):
    """Raised when deprecating an already-deprecated Subject.

    Invariant: deprecation is a one-way transition — once a Subject is
    ``deprecated`` it cannot be deprecated again or transitioned back.
    """

    def __init__(self, subject_id: Any) -> None:
        super().__init__(
            f"Subject {subject_id} is already deprecated",
            code="SUBJECT_ALREADY_DEPRECATED",
        )
        self.subject_id = subject_id


# ------------------------------------------------------------------
# Concept
# ------------------------------------------------------------------


class ConceptSelfDependency(ContentError):
    """Raised when a Concept is wired as a dependency of itself.

    Invariant: a Concept may not depend on itself. Self-dependency would
    create a trivial cycle and is meaningless pedagogically.
    """

    def __init__(self, concept_id: Any) -> None:
        super().__init__(
            f"Concept {concept_id} cannot depend on itself",
            code="CONCEPT_SELF_DEPENDENCY",
        )
        self.concept_id = concept_id


class ConceptDuplicateDependency(ContentError):
    """Raised when adding a duplicate dependency to a Concept.

    Invariant: the pair ``(target_concept_id, dependency_type)`` is unique
    within a Concept's dependency set. A second dependency to the same
    target with the same type must be rejected — use a different type or
    remove the existing dependency first.
    """

    def __init__(self, concept_id: Any, target_concept_id: Any, dependency_type: Any) -> None:
        super().__init__(
            f"Concept {concept_id} already has a {dependency_type!r} dependency "
            f"on concept {target_concept_id}",
            code="CONCEPT_DUPLICATE_DEPENDENCY",
        )
        self.concept_id = concept_id
        self.target_concept_id = target_concept_id
        self.dependency_type = dependency_type


class ConceptDependencySubjectMismatch(ContentError):
    """Raised when a dependency targets a Concept in a different Subject.

    Invariant: dependencies are scoped within a Subject — a Concept may
    only depend on Concepts in the same Subject. Cross-subject dependencies
    would violate the Subject aggregate's consistency boundary.
    """

    def __init__(
        self,
        concept_id: Any,
        concept_subject_id: Any,
        target_concept_id: Any,
        target_subject_id: Any,
    ) -> None:
        super().__init__(
            f"Concept {concept_id} (subject {concept_subject_id}) cannot depend on "
            f"concept {target_concept_id} (subject {target_subject_id}): subject mismatch",
            code="CONCEPT_DEPENDENCY_SUBJECT_MISMATCH",
        )
        self.concept_id = concept_id
        self.concept_subject_id = concept_subject_id
        self.target_concept_id = target_concept_id
        self.target_subject_id = target_subject_id


class ConceptDependencyNotFound(ContentError):
    """Raised when removing a dependency that does not exist on the Concept."""

    def __init__(self, concept_id: Any, target_concept_id: Any, dependency_type: Any) -> None:
        super().__init__(
            f"Concept {concept_id} has no {dependency_type!r} dependency on "
            f"concept {target_concept_id} to remove",
            code="CONCEPT_DEPENDENCY_NOT_FOUND",
        )
        self.concept_id = concept_id
        self.target_concept_id = target_concept_id
        self.dependency_type = dependency_type


class ConceptAlreadyPublished(ContentError):
    """Raised when publishing a Concept that is already published."""

    def __init__(self, concept_id: Any) -> None:
        super().__init__(
            f"Concept {concept_id} is already published",
            code="CONCEPT_ALREADY_PUBLISHED",
        )
        self.concept_id = concept_id


class ConceptAlreadyDeprecated(ContentError):
    """Raised when deprecating a Concept that is already deprecated."""

    def __init__(self, concept_id: Any) -> None:
        super().__init__(
            f"Concept {concept_id} is already deprecated",
            code="CONCEPT_ALREADY_DEPRECATED",
        )
        self.concept_id = concept_id


# ------------------------------------------------------------------
# LearningObjective
# ------------------------------------------------------------------


class LearningObjectiveStatementTooShort(ContentError):
    """Raised when creating a LearningObjective with a too-short statement.

    Invariant: a learning objective statement must be more than 10
    characters. Statements shorter than that rarely express a measurable
    learning outcome and are typically authoring mistakes.
    """

    def __init__(self, statement: str) -> None:
        super().__init__(
            f"Learning objective statement must be > 10 characters, got {len(statement)}",
            code="LEARNING_OBJECTIVE_STATEMENT_TOO_SHORT",
        )
        self.statement = statement


# ------------------------------------------------------------------
# QuestionTemplate
# ------------------------------------------------------------------


class QuestionTemplateAlreadyPublished(ContentError):
    """Raised when publishing a QuestionTemplate that is already published."""

    def __init__(self, template_id: Any) -> None:
        super().__init__(
            f"Question template {template_id} is already published",
            code="QUESTION_TEMPLATE_ALREADY_PUBLISHED",
        )
        self.template_id = template_id


class QuestionTemplateAlreadyDeprecated(ContentError):
    """Raised when deprecating a QuestionTemplate that is already deprecated."""

    def __init__(self, template_id: Any) -> None:
        super().__init__(
            f"Question template {template_id} is already deprecated",
            code="QUESTION_TEMPLATE_ALREADY_DEPRECATED",
        )
        self.template_id = template_id


# ------------------------------------------------------------------
# ContentVersion
# ------------------------------------------------------------------


class ContentVersionAlreadyDeprecated(ContentError):
    """Raised when deprecating a ContentVersion that is already deprecated."""

    def __init__(self, version_id: Any) -> None:
        super().__init__(
            f"Content version {version_id} is already deprecated",
            code="CONTENT_VERSION_ALREADY_DEPRECATED",
        )
        self.version_id = version_id


# ------------------------------------------------------------------
# ContentPack
# ------------------------------------------------------------------


class ContentPackAlreadySubmitted(ContentError):
    """Raised when submitting an already-in-review ContentPack.

    Invariant: a ContentPack in ``in_review`` status cannot be re-submitted.
    To request additional review after changes, use ``submit_for_review``
    after the requested changes have been addressed (which returns the pack
    to ``draft``).
    """

    def __init__(self, pack_id: Any) -> None:
        super().__init__(
            f"Content pack {pack_id} has already been submitted for review",
            code="CONTENT_PACK_ALREADY_SUBMITTED",
        )
        self.pack_id = pack_id


class ContentPackNotInReview(ContentError):
    """Raised when acting on a ContentPack that is not in review.

    Invariant: ``approve``, ``request_changes``, and ``reject`` only apply
    to a ContentPack in ``in_review`` status. Acting on a draft, published,
    or rejected pack is an invalid transition.
    """

    def __init__(self, pack_id: Any, current_status: Any) -> None:
        super().__init__(
            f"Content pack {pack_id} is not in review (current status: {current_status!r})",
            code="CONTENT_PACK_NOT_IN_REVIEW",
        )
        self.pack_id = pack_id
        self.current_status = current_status


class ContentPackStageAlreadyApproved(ContentError):
    """Raised when approving a ContentPack stage that has already been approved.

    Invariant: a review stage can only be approved once per submission
    cycle. Repeated approvals of the same stage are ignored or rejected —
    this prevents accidental double-signoff from masking audit gaps.
    """

    def __init__(self, pack_id: Any, stage: Any) -> None:
        super().__init__(
            f"Content pack {pack_id} stage {stage!r} has already been approved",
            code="CONTENT_PACK_STAGE_ALREADY_APPROVED",
        )
        self.pack_id = pack_id
        self.stage = stage


class ContentPackReviewIncomplete(ContentError):
    """Raised when publishing a ContentPack whose review is incomplete.

    Invariant: a ContentPack may only transition to ``published`` after
    every required review stage (:class:`ReviewStage`) has approved it.
    Attempting to publish before all stages approve is rejected.
    """

    def __init__(self, pack_id: Any, missing_stages: list[Any]) -> None:
        super().__init__(
            f"Content pack {pack_id} cannot be published: review stages "
            f"{missing_stages!r} have not approved",
            code="CONTENT_PACK_REVIEW_INCOMPLETE",
        )
        self.pack_id = pack_id
        self.missing_stages = list(missing_stages)


class ContentPackAlreadyPublished(ContentError):
    """Raised when publishing a ContentPack that is already published."""

    def __init__(self, pack_id: Any) -> None:
        super().__init__(
            f"Content pack {pack_id} is already published",
            code="CONTENT_PACK_ALREADY_PUBLISHED",
        )
        self.pack_id = pack_id


class ContentPackAlreadyRejected(ContentError):
    """Raised when acting on a ContentPack that has already been rejected.

    Invariant: ``rejected`` is a terminal state. A rejected pack cannot be
    re-submitted, approved, or published — the author must create a new
    ContentPack with the requested corrections.
    """

    def __init__(self, pack_id: Any) -> None:
        super().__init__(
            f"Content pack {pack_id} has already been rejected (terminal state)",
            code="CONTENT_PACK_ALREADY_REJECTED",
        )
        self.pack_id = pack_id


__all__ = [
    "ConceptAlreadyDeprecated",
    "ConceptAlreadyPublished",
    "ConceptDependencyNotFound",
    "ConceptDependencySubjectMismatch",
    "ConceptDuplicateDependency",
    "ConceptSelfDependency",
    "ContentError",
    "ContentPackAlreadyPublished",
    "ContentPackAlreadyRejected",
    "ContentPackAlreadySubmitted",
    "ContentPackNotInReview",
    "ContentPackReviewIncomplete",
    "ContentPackStageAlreadyApproved",
    "ContentVersionAlreadyDeprecated",
    "LearningObjectiveStatementTooShort",
    "QuestionTemplateAlreadyDeprecated",
    "QuestionTemplateAlreadyPublished",
    "SubjectAlreadyDeprecated",
    "SubjectAlreadyPublished",
    "SubjectNotPublishable",
]
