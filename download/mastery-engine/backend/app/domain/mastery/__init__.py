"""Mastery bounded context — domain layer.

Contains: MasteryScore, Review, AlgorithmVersion aggregates,
MasteryCalculator domain service.
Pure Python; no I/O, no framework dependencies.
"""

from app.domain.mastery.algorithm_version import AlgorithmVersion
from app.domain.mastery.exceptions import (
    AlgorithmEvaluationFailed,
    AlgorithmVersionAlreadyActive,
    AlgorithmVersionNotFound,
    AlgorithmVersionNotActive,
    MasteryError,
    MasteryScoreNotFound,
    OptimisticConcurrencyConflict,
    ReviewNotFound,
)
from app.domain.mastery.events import (
    AlgorithmVersionPublished,
    ConceptStateChanged,
    LearnerMisconceptionCleared,
    MasteryUpdated,
    ReviewScheduled,
    WeakConceptDetected,
)
from app.domain.mastery.mastery_calculator import MasteryComputation, MasteryCalculator
from app.domain.mastery.mastery_score import MasteryScore
from app.domain.mastery.repository import (
    AlgorithmVersionRepository,
    MasteryScoreRepository,
    ReviewRepository,
)
from app.domain.mastery.review import Review

__all__ = [
    "AlgorithmVersion",
    "MasteryScore",
    "Review",
    "MasteryCalculator",
    "MasteryComputation",
    "MasteryScoreRepository",
    "ReviewRepository",
    "AlgorithmVersionRepository",
    "MasteryError",
    "AlgorithmVersionNotActive",
    "OptimisticConcurrencyConflict",
    "MasteryScoreNotFound",
    "ReviewNotFound",
    "AlgorithmVersionNotFound",
    "AlgorithmVersionAlreadyActive",
    "AlgorithmEvaluationFailed",
    "MasteryUpdated",
    "ConceptStateChanged",
    "WeakConceptDetected",
    "ReviewScheduled",
    "AlgorithmVersionPublished",
    "LearnerMisconceptionCleared",
]
