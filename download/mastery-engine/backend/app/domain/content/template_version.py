"""Content context — TemplateVersion value object.

A :class:`TemplateVersion` is an immutable snapshot of a
:class:`QuestionTemplate`'s generation logic at a specific point in
time. Each :class:`QuestionTemplate` has zero or more versions; one of
them (the ``current_version_id``) is the version actively used to
generate question instances for learners.

Why versions are immutable:

Question generation is parameterized: a single template produces many
concrete questions by varying its input parameters. Once a version has
been used to generate even one learner-facing question instance, its
behaviour **must not change** — otherwise the historical scoring,
analytics, and mastery evidence attached to that instance would become
inconsistent with the logic that produced it. Immutability is therefore
a hard correctness requirement, not a stylistic choice.

When a template's logic needs to change, the author creates a *new*
:class:`TemplateVersion` (with the next :class:`VersionNumber`) and
publishes it via :meth:`QuestionTemplate.publish`. The old version
remains queryable for historical analysis; new question instances are
drawn from the new version.

The version carries six authoring payloads (all dicts so the domain
layer stays free of any specific schema-validation framework):

- ``parameter_schema`` — JSON-Schema-ish description of the parameters
  the generator accepts (used by the UI to render an authoring form).
- ``prompt_template`` — the prompt template (often Jinja2 or a similar
  mini-language) that produces the question stem.
- ``correct_answer_generator`` — the logic (or reference to it) that
  computes the correct answer for a given parameter set.
- ``distractor_generator`` — optional; for multiple-choice templates,
  the logic that produces the incorrect options.
- ``explanation_template`` — the template that produces the worked
  explanation shown after a learner answers.

Plus two pedagogical priors used by the scheduler before enough attempt
data has accumulated:

- ``difficulty_estimate`` — an :class:`DifficultyEstimate` (easy /
  medium / hard).
- ``discrimination_estimate`` — a :class:`DiscriminationEstimate`
  (0.0–1.0) for how well the template separates mastered from
  non-mastered learners.

Invariants:
- ``version_number`` must be >= 1 (enforced by :class:`VersionNumber`).
- All six payload dicts must be present (``distractor_generator`` may
  be ``None`` for non-MC question types, but the field itself is
  required at construction).
- ``content_version_id`` ties this version to a specific
  :class:`ContentVersion`, scoping its active lifetime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.shared.ids import (
    ContentVersionId,
    QuestionTemplateId,
    TemplateVersionId,
)
from app.domain.shared.kernel import InvariantViolation, ValueObject
from app.domain.shared.value_objects import (
    DifficultyEstimate,
    DiscriminationEstimate,
    VersionNumber,
)


@dataclass(frozen=True)
class TemplateVersion(ValueObject):
    """An immutable snapshot of a QuestionTemplate's generation logic.

    Equality is by value — two :class:`TemplateVersion` instances are
    equal iff every field (including ``id``) matches. In practice the
    ``id`` (:class:`TemplateVersionId`) is globally unique, so
    value-equality coincides with identity-equality.

    Attributes:
        id: The unique identifier for this version.
        template_id: The :class:`QuestionTemplate` this version
            belongs to.
        content_version_id: The :class:`ContentVersion` this version
            is scoped to. A version is only "live" while its content
            version is ``published``.
        version_number: The monotonically-increasing version number
            within the parent template (starts at 1).
        parameter_schema: A dict describing the parameters the
            generator accepts. Format is conventionally JSON-Schema,
            but the domain does not validate the contents.
        prompt_template: A dict carrying the prompt template and its
            metadata (e.g., ``{"engine": "jinja2", "source": "..."}``).
        correct_answer_generator: A dict carrying the correct-answer
            generator (e.g., a reference to a callable plus its
            configuration).
        distractor_generator: Optional dict for multiple-choice
            templates; ``None`` for free-response and code-execution
            templates.
        explanation_template: A dict carrying the explanation template,
            in the same shape as ``prompt_template``.
        difficulty_estimate: An authored prior on the version's
            difficulty.
        discrimination_estimate: An authored prior on the version's
            discrimination (0.0–1.0).
        published_at: When this version was published (set by the
            parent :class:`QuestionTemplate` aggregate when the version
            becomes the current one). ``None`` for versions that have
            been created but not yet published.

    Raises:
        InvariantViolation: If any payload field is missing or of the
            wrong type, or if ``version_number`` is invalid.
    """

    id: TemplateVersionId
    template_id: QuestionTemplateId
    content_version_id: ContentVersionId
    version_number: VersionNumber
    parameter_schema: dict[str, Any]
    prompt_template: dict[str, Any]
    correct_answer_generator: dict[str, Any]
    explanation_template: dict[str, Any]
    difficulty_estimate: DifficultyEstimate
    discrimination_estimate: DiscriminationEstimate
    distractor_generator: dict[str, Any] | None = None
    published_at: datetime | None = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.parameter_schema, dict):
            raise InvariantViolation(
                "TemplateVersion",
                f"parameter_schema must be a dict, got {type(self.parameter_schema).__name__}",
            )
        if not isinstance(self.prompt_template, dict):
            raise InvariantViolation(
                "TemplateVersion",
                f"prompt_template must be a dict, got {type(self.prompt_template).__name__}",
            )
        if not isinstance(self.correct_answer_generator, dict):
            raise InvariantViolation(
                "TemplateVersion",
                f"correct_answer_generator must be a dict, got "
                f"{type(self.correct_answer_generator).__name__}",
            )
        if not isinstance(self.explanation_template, dict):
            raise InvariantViolation(
                "TemplateVersion",
                f"explanation_template must be a dict, got "
                f"{type(self.explanation_template).__name__}",
            )
        if self.distractor_generator is not None and not isinstance(self.distractor_generator, dict):
            raise InvariantViolation(
                "TemplateVersion",
                f"distractor_generator must be a dict or None, got "
                f"{type(self.distractor_generator).__name__}",
            )
        if not isinstance(self.difficulty_estimate, DifficultyEstimate):
            raise InvariantViolation(
                "TemplateVersion",
                "difficulty_estimate must be a DifficultyEstimate",
            )
        if not isinstance(self.discrimination_estimate, DiscriminationEstimate):
            raise InvariantViolation(
                "TemplateVersion",
                "discrimination_estimate must be a DiscriminationEstimate",
            )

    # ------------------------------------------------------------------
    # Convenience predicates
    # ------------------------------------------------------------------

    @property
    def is_published(self) -> bool:
        """True if this version has been published (``published_at`` is set)."""
        return self.published_at is not None

    @property
    def has_distractors(self) -> bool:
        """True if this version produces distractors (i.e., is multiple-choice)."""
        return self.distractor_generator is not None

    def __repr__(self) -> str:
        return (
            f"TemplateVersion(id={self.id}, template_id={self.template_id}, "
            f"version_number={self.version_number.value}, "
            f"content_version_id={self.content_version_id}, "
            f"published={self.is_published})"
        )


__all__ = ["TemplateVersion"]
