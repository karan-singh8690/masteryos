"""Content context — LearningObjective entity.

A :class:`LearningObjective` is a single, measurable outcome that a
learner is expected to achieve for a parent :class:`Concept`. For
example, a Concept on "Quicksort" might have objectives like "Given an
array, manually trace the partition step of Quicksort" or "Identify
the worst-case input for Quicksort".

LearningObjectives are authored independently of questions but linked
to them: each :class:`QuestionTemplate` (via its
:class:`TemplateVersion`) is tagged with the objective(s) it assesses.
The mastery engine aggregates evidence at the objective level before
rolling it up to the Concept.

Design notes:

- A LearningObjective is an **entity** (it has identity via
  :class:`LearningObjectiveId`) but is not itself an aggregate root.
  It lives inside the :class:`Concept` aggregate boundary and is
  loaded/saved only through it. (The Concept aggregate may delegate
  management of objectives to an application service that operates
  per-objective, but the consistency boundary remains the Concept.)
- A Misconception (see :mod:`app.domain.content.misconception`) is
  attached to a single LearningObjective — it represents a specific
  way a learner can fail to achieve that objective.

Invariants:
- ``statement`` must be longer than 10 characters. Shorter statements
  rarely express a measurable outcome and are typically authoring
  mistakes.
"""

from __future__ import annotations

from app.domain.content.events import LearningObjectiveCreated
from app.domain.content.exceptions import LearningObjectiveStatementTooShort
from app.domain.shared.ids import ConceptId, LearningObjectiveId
from app.domain.shared.kernel import ContentStatus, Entity, InvariantViolation


class LearningObjective(Entity):
    """A single measurable learning outcome for a Concept.

    Equality is by :class:`LearningObjectiveId` — two objectives with
    the same ID are the same entity, even if their other fields differ.

    Attributes:
        id: The unique identifier for this objective.
        concept_id: The Concept this objective belongs to.
        statement: A single sentence describing the measurable outcome
            (must be > 10 characters).
        status: The lifecycle status of the objective. Newly-created
            objectives are ``draft``; publication to ``published`` is
            orchestrated through the parent Concept's
            :meth:`Concept.publish` flow.
    """

    #: Minimum length of the ``statement`` (exclusive — must be > this).
    MIN_STATEMENT_LENGTH: int = 10

    #: Maximum length of the ``statement``.
    MAX_STATEMENT_LENGTH: int = 500

    def __init__(
        self,
        *,
        id: LearningObjectiveId,
        concept_id: ConceptId,
        statement: str,
        status: ContentStatus = ContentStatus.DRAFT,
    ) -> None:
        self.id = id
        self.concept_id = concept_id
        self.statement = statement
        self.status = status
        self._validate()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, concept_id: ConceptId, statement: str) -> LearningObjective:
        """Create a new LearningObjective in ``draft`` status.

        Args:
            concept_id: The Concept this objective belongs to.
            statement: A single sentence describing the measurable
                outcome. Must be more than 10 characters.

        Returns:
            A newly created :class:`LearningObjective`. The caller (an
            application service) is responsible for attaching it to the
            Concept aggregate and persisting via the ConceptRepository.

        Raises:
            LearningObjectiveStatementTooShort: If ``statement`` is 10
                characters or fewer.
            InvariantViolation: If ``statement`` exceeds the maximum
                length or is not a string.
        """
        objective = cls(
            id=LearningObjectiveId.generate(),
            concept_id=concept_id,
            statement=statement,
            status=ContentStatus.DRAFT,
        )
        # The event is recorded by the parent Concept aggregate when it
        # attaches this objective. We expose it here as a classmethod
        # helper so callers that operate per-objective can still emit
        # the event without reaching into the events module directly.
        objective._pending_event = LearningObjectiveCreated(
            learning_objective_id=objective.id,
            concept_id=objective.concept_id,
            statement=objective.statement,
        )
        return objective

    def pull_creation_event(self) -> LearningObjectiveCreated | None:
        """Return the pending creation event, if any, and clear it.

        Used by the parent Concept aggregate when it adopts this
        objective — the Concept records the event on its own event list
        so that subscribers see a single, consistent event stream per
        aggregate transaction.
        """
        evt = getattr(self, "_pending_event", None)
        if evt is not None:
            self._pending_event = None  # type: ignore[assignment]
        return evt

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        """Enforce field-level invariants."""
        if not isinstance(self.statement, str):
            raise InvariantViolation(
                "LearningObjective",
                f"statement must be a string, got {type(self.statement).__name__}",
            )
        stripped = self.statement.strip()
        if len(stripped) <= self.MIN_STATEMENT_LENGTH:
            raise LearningObjectiveStatementTooShort(stripped)
        if len(stripped) > self.MAX_STATEMENT_LENGTH:
            raise InvariantViolation(
                "LearningObjective",
                f"statement must be at most {self.MAX_STATEMENT_LENGTH} characters",
            )
        # Store the stripped form so callers cannot sneak in whitespace-padded statements.
        self.statement = stripped

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"LearningObjective(id={self.id}, concept_id={self.concept_id}, "
            f"status={self.status.value!r}, statement={self.statement[:40]!r}...)"
        )


__all__ = ["LearningObjective"]
