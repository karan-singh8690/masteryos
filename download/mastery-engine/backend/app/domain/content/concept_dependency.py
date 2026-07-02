"""Content context — ConceptDependency value object.

A :class:`ConceptDependency` is an immutable record of one Concept's
pedagogical relationship to another. It is owned by the source Concept's
aggregate and persisted as part of it.

The three dependency types (see :class:`DependencyType`) have distinct
semantics:

- ``PREREQUISITE`` — the source Concept cannot be meaningfully studied
  before the target Concept. Used by the scheduler to gate concept
  introduction.
- ``RELATED`` — the two Concepts share subject matter but neither gates
  the other. Used by the recommendation engine to surface adjacent
  topics.
- ``REINFORCES`` — practicing the source Concept also strengthens the
  target. Used by the mastery engine to propagate evidence across
  linked Concepts.

The ``weight`` (:class:`DependencyWeight`) qualifies how strongly the
relationship holds — ``STRONG`` dependencies are preferred for gating,
``WEAK`` ones for soft recommendations.

Invariants:
- ``source_concept_id`` must differ from ``target_concept_id``. A
  self-dependency is meaningless and would create a trivial cycle.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.shared.ids import ConceptId
from app.domain.shared.kernel import (
    DependencyType,
    DependencyWeight,
    InvariantViolation,
    ValueObject,
)


@dataclass(frozen=True)
class ConceptDependency(ValueObject):
    """An immutable, value-equal record of a directed Concept dependency.

    Two :class:`ConceptDependency` instances are equal iff all four
    fields match. Equality is by value, not by identity — there is no
    ``ConceptDependencyId`` because dependencies are owned by their
    source Concept and identified positionally within its dependency
    set.

    Attributes:
        source_concept_id: The Concept that *has* this dependency.
        target_concept_id: The Concept that the source depends on.
        dependency_type: The semantic type of the dependency
            (prerequisite, related, reinforces).
        weight: The strength of the dependency (weak, strong).

    Raises:
        InvariantViolation: If ``source_concept_id`` equals
            ``target_concept_id`` (self-dependency).
    """

    source_concept_id: ConceptId
    target_concept_id: ConceptId
    dependency_type: DependencyType
    weight: DependencyWeight

    def __post_init__(self) -> None:
        if self.source_concept_id == self.target_concept_id:
            raise InvariantViolation(
                "ConceptDependency",
                f"Concept {self.source_concept_id} cannot depend on itself",
            )

    # ------------------------------------------------------------------
    # Convenience predicates
    # ------------------------------------------------------------------

    @property
    def is_prerequisite(self) -> bool:
        """True if this is a prerequisite dependency (gating)."""
        return self.dependency_type == DependencyType.PREREQUISITE

    @property
    def is_reinforces(self) -> bool:
        """True if this is a reinforces dependency (evidence propagation)."""
        return self.dependency_type == DependencyType.REINFORCES

    @property
    def is_strong(self) -> bool:
        """True if this dependency is strong."""
        return self.weight == DependencyWeight.STRONG

    def matches(self, *, target_concept_id: ConceptId, dependency_type: DependencyType) -> bool:
        """True if this dependency targets ``target_concept_id`` with ``dependency_type``.

        Used by :meth:`Concept.add_dependency` and
        :meth:`Concept.remove_dependency` to detect duplicates and locate
        entries for removal. Note that ``weight`` is intentionally
        excluded — a ``(target, type)`` pair is the natural key.
        """
        return (
            self.target_concept_id == target_concept_id
            and self.dependency_type == dependency_type
        )

    def __repr__(self) -> str:
        return (
            f"ConceptDependency(source={self.source_concept_id}, "
            f"target={self.target_concept_id}, type={self.dependency_type.value}, "
            f"weight={self.weight.value})"
        )


__all__ = ["ConceptDependency"]
