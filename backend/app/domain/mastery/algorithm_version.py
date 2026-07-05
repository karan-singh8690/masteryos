"""AlgorithmVersion — an immutable snapshot of the Mastery Engine algorithm.

Algorithm versions are the third axis of triple versioning (ADR-0011).
Every MasteryScore records the algorithm version under which it was computed,
enabling historical reconstruction of any mastery state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.domain.shared.ids import AlgorithmVersionId
from app.domain.shared.kernel import AggregateRoot
from app.domain.shared.value_objects import VersionNumber
from app.domain.mastery.events import AlgorithmVersionPublished
from app.domain.mastery.exceptions import AlgorithmVersionAlreadyActive


class AlgorithmVersion(AggregateRoot):
    """An immutable snapshot of the Mastery Engine algorithm.

    Invariants:
    - Immutable after creation (no methods modify algorithm parameters).
    - Only one version can be active at a time (enforced at application level).
    - ``promoted_at`` is set only when ``is_active`` is True.

    The algorithm parameters (decay rates, weights, thresholds) are stored
    as a dict and are versioned with the algorithm. The MasteryCalculator
    domain service uses these parameters to compute mastery scores.
    """

    def __init__(
        self,
        id: AlgorithmVersionId,
        version_number: VersionNumber,
        name: str,
        parameters: dict[str, Any],
        description: str | None = None,
        changelog: str | None = None,
        is_active: bool = False,
        promoted_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.version_number = version_number
        self.name = name
        self.parameters = parameters
        self.description = description
        self.changelog = changelog
        self.is_active = is_active
        self.promoted_at = promoted_at
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def create(
        cls,
        version_number: VersionNumber,
        name: str,
        parameters: dict[str, Any],
        description: str | None = None,
        changelog: str | None = None,
    ) -> AlgorithmVersion:
        """Create a new (inactive) algorithm version."""
        return cls(
            id=AlgorithmVersionId.generate(),
            version_number=version_number,
            name=name,
            parameters=parameters,
            description=description,
            changelog=changelog,
            is_active=False,
        )

    def promote(self, previous_version_number: int | None = None) -> None:
        """Promote this version to active (production).

        This is the only state transition for an AlgorithmVersion.
        Once promoted, the version is immutable and cannot be demoted
        (a new version supersedes it).

        Raises:
            AlgorithmVersionAlreadyActive: if already active.
        """
        if self.is_active:
            raise AlgorithmVersionAlreadyActive(self.id)
        self.is_active = True
        self.promoted_at = datetime.now(timezone.utc)
        self._record_event(
            AlgorithmVersionPublished(
                algorithm_version_id=self.id.value,
                version_number=self.version_number.value,
                previous_version_number=previous_version_number,
            )
        )

    @property
    def decay_rate_per_day(self) -> float:
        """The memory decay rate per day (from parameters)."""
        return self.parameters.get("memory_decay_rate_per_day", 0.05)

    @property
    def mastery_consolidation_rate(self) -> float:
        """The mastery consolidation rate (from parameters)."""
        return self.parameters.get("mastery_consolidation_rate", 0.10)

    @property
    def review_interval_expansion_factor(self) -> float:
        """The review interval expansion factor for successful reviews."""
        return self.parameters.get("review_interval_expansion_factor", 2.5)

    @property
    def review_interval_contraction_factor(self) -> float:
        """The review interval contraction factor for failed reviews."""
        return self.parameters.get("review_interval_contraction_factor", 0.3)

    @property
    def mastery_threshold_proficient(self) -> float:
        """The mastery score threshold for Proficient state."""
        return self.parameters.get("mastery_threshold_proficient", 0.70)

    @property
    def mastery_threshold_mastered(self) -> float:
        """The mastery score threshold for Mastered state."""
        return self.parameters.get("mastery_threshold_mastered", 0.85)

    @property
    def memory_threshold(self) -> float:
        """The memory score threshold for review triggering."""
        return self.parameters.get("memory_threshold", 0.50)

    @property
    def hint_usage_mastery_penalty(self) -> float:
        """The mastery credit penalty for using hints."""
        return self.parameters.get("hint_usage_mastery_penalty", 0.30)
