"""Content context — Misconception entity.

A :class:`Misconception` is a specific, named way that a learner can
fail to achieve a parent :class:`LearningObjective`. For example, for
an objective on Quicksort partitioning, a misconception might be
"off-by-one error in the pivot index" with a remediation that walks
through the partition loop with explicit index tracking.

Misconceptions serve two purposes in the Mastery Engine:

1. **Diagnostic tagging.** When a learner answers a question
   incorrectly, the assessment engine tags the attempt with one or
   more misconceptions based on which distractor they chose or which
   pattern their free response matches. These tags feed the mastery
   engine's per-misconception weakness tracking.
2. **Remediation.** When the scheduler detects that a learner has a
   given misconception, it can surface the ``remediation`` content
   (typically a short explainer or worked example) before scheduling
   another attempt on the parent objective.

Design notes:

- A Misconception is an **entity** (it has identity via
  :class:`MisconceptionId`) but is not itself an aggregate root. It
  lives inside the :class:`Concept` aggregate boundary (transitively,
  via its parent :class:`LearningObjective`) and is loaded/saved only
  through it.
- Misconceptions are scoped to a single LearningObjective — the same
  underlying mistake might manifest differently across objectives, so
  we do not attempt to share misconception definitions globally.

Invariants:
- ``name`` must be a non-empty string.
- ``description`` must be a non-empty string.
- ``remediation`` is required (may be an empty string if authoring is
  incomplete, but the field itself must be present).
"""

from __future__ import annotations

from app.domain.content.events import MisconceptionCreated
from app.domain.shared.ids import LearningObjectiveId, MisconceptionId
from app.domain.shared.kernel import ContentStatus, Entity, InvariantViolation


class Misconception(Entity):
    """A named, diagnosable mistake pattern for a LearningObjective.

    Equality is by :class:`MisconceptionId` — two misconceptions with
    the same ID are the same entity, even if their other fields differ.

    Attributes:
        id: The unique identifier for this misconception.
        learning_objective_id: The LearningObjective this misconception
            is scoped to.
        name: A short, human-readable name (e.g., ``"off-by-one in
            pivot index"``).
        description: A longer explanation of how the misconception
            manifests — used by content authors and reviewers.
        remediation: Authoritative content that addresses the
            misconception — surfaced to learners by the scheduler when
            the misconception is detected. May be empty during drafting.
        status: The lifecycle status of the misconception. Newly-created
            misconceptions are ``draft``.
    """

    #: Maximum length of the ``name``.
    MAX_NAME_LENGTH: int = 200

    #: Maximum length of the ``description``.
    MAX_DESCRIPTION_LENGTH: int = 2000

    #: Maximum length of the ``remediation``.
    MAX_REMEDIATION_LENGTH: int = 4000

    def __init__(
        self,
        *,
        id: MisconceptionId,
        learning_objective_id: LearningObjectiveId,
        name: str,
        description: str,
        remediation: str,
        status: ContentStatus = ContentStatus.DRAFT,
    ) -> None:
        self.id = id
        self.learning_objective_id = learning_objective_id
        self.name = name
        self.description = description
        self.remediation = remediation
        self.status = status
        self._validate()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        learning_objective_id: LearningObjectiveId,
        name: str,
        description: str,
        remediation: str,
    ) -> Misconception:
        """Create a new Misconception in ``draft`` status.

        Args:
            learning_objective_id: The LearningObjective this
                misconception is scoped to.
            name: A short, human-readable name.
            description: A longer explanation of how the misconception
                manifests.
            remediation: Authoritative content that addresses the
                misconception. May be empty during drafting; must be
                filled in before the parent objective is published.

        Returns:
            A newly created :class:`Misconception`. The caller (an
            application service) is responsible for attaching it to the
            parent LearningObjective and persisting via the
            ConceptRepository.

        Raises:
            InvariantViolation: If any field fails validation (empties,
                length limits, wrong types).
        """
        misconception = cls(
            id=MisconceptionId.generate(),
            learning_objective_id=learning_objective_id,
            name=name,
            description=description,
            remediation=remediation,
            status=ContentStatus.DRAFT,
        )
        misconception._pending_event = MisconceptionCreated(
            misconception_id=misconception.id,
            learning_objective_id=misconception.learning_objective_id,
            name=misconception.name,
        )
        return misconception

    def pull_creation_event(self) -> MisconceptionCreated | None:
        """Return the pending creation event, if any, and clear it.

        Used by the parent Concept aggregate when it adopts this
        misconception — the Concept records the event on its own event
        list so subscribers see a single, consistent event stream per
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
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvariantViolation(
                "Misconception",
                "name must be a non-empty string",
            )
        if len(self.name) > self.MAX_NAME_LENGTH:
            raise InvariantViolation(
                "Misconception",
                f"name must be at most {self.MAX_NAME_LENGTH} characters",
            )
        self.name = self.name.strip()

        if not isinstance(self.description, str) or not self.description.strip():
            raise InvariantViolation(
                "Misconception",
                "description must be a non-empty string",
            )
        if len(self.description) > self.MAX_DESCRIPTION_LENGTH:
            raise InvariantViolation(
                "Misconception",
                f"description must be at most {self.MAX_DESCRIPTION_LENGTH} characters",
            )
        self.description = self.description.strip()

        if not isinstance(self.remediation, str):
            raise InvariantViolation(
                "Misconception",
                "remediation must be a string",
            )
        if len(self.remediation) > self.MAX_REMEDIATION_LENGTH:
            raise InvariantViolation(
                "Misconception",
                f"remediation must be at most {self.MAX_REMEDIATION_LENGTH} characters",
            )
        # ``remediation`` may be empty during drafting; do not strip-and-reject empty.

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Misconception(id={self.id}, "
            f"learning_objective_id={self.learning_objective_id}, "
            f"name={self.name!r}, status={self.status.value!r})"
        )


__all__ = ["Misconception"]
