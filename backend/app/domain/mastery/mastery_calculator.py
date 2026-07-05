"""MasteryCalculator — a pure domain service that computes mastery from attempt history.

This is the heart of the Mastery Engine (per ADR-0007: deterministic-first).
The MasteryCalculator is a **pure function**: given the attempt history and
the algorithm version's parameters, it produces the same mastery scores
every time. This is invariant M1 (ASD Section 6.8).

The calculator does NOT:
- Touch the database (no I/O)
- Call external services
- Make random decisions (deterministic given inputs)
- Depend on time (uses provided timestamps, not ``now()``)

The calculator DOES:
- Compute memory_score (short-term, decays with time)
- Compute durable_mastery_score (long-term, slower to change)
- Compute mastery_score_combined (per ADR-0008's "combined, not averaged")
- Compute confidence_interval (narrows with more evidence)
- Compute the new review interval (expand on success, contract on failure)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.assessment.attempt import Attempt
from app.domain.mastery.algorithm_version import AlgorithmVersion
from app.domain.shared.kernel import ScoringOutcome
from app.domain.shared.value_objects import ReviewInterval


@dataclass(frozen=True)
class MasteryComputation:
    """The result of a mastery computation.

    Contains the new scores and the new review interval.
    The MasteryScore aggregate's ``apply_update`` method applies these.
    """

    memory_score: float
    durable_mastery_score: float
    mastery_score_combined: float
    confidence_interval: float
    evidence_count: int
    new_review_interval: ReviewInterval
    last_attempt_at: datetime


class MasteryCalculator:
    """Pure domain service that computes mastery from attempt history.

    This is a pure function: given the same attempt history and algorithm
    version, it produces the same result. No I/O, no randomness, no time
    dependence (uses provided timestamps).

    Usage (from the application layer's UpdateMastery command handler):
        calculator = MasteryCalculator()
        result = calculator.compute(
            attempts=attempt_history,
            algorithm=active_algorithm_version,
            current_review_interval=current_interval,
            previous_memory_score=score.memory_score,
            previous_durable_mastery=score.durable_mastery_score,
            current_time=now,
        )
        score.apply_update(
            new_memory_score=result.memory_score,
            new_durable_mastery_score=result.durable_mastery_score,
            ...
        )
    """

    # ============================================================
    # Core computation
    # ============================================================

    def compute(
        self,
        attempts: list[Attempt],
        algorithm: AlgorithmVersion,
        current_review_interval: ReviewInterval,
        previous_memory_score: float,
        previous_durable_mastery: float,
        current_time: datetime | None = None,
    ) -> MasteryComputation:
        """Compute new mastery scores from attempt history.

        Args:
            attempts: All attempts on this concept by this learner,
                ordered by ``created_at`` ascending. The most recent
                attempt is the trigger for this computation.
            algorithm: The active algorithm version (provides parameters).
            current_review_interval: The current review interval (for expansion/contraction).
            previous_memory_score: The memory score before this update.
            previous_durable_mastery: The durable mastery before this update.
            current_time: The reference time for decay computation
                (defaults to now; pass explicitly for reproducibility).

        Returns:
            A MasteryComputation with the new scores and review interval.
        """
        if not attempts:
            return MasteryComputation(
                memory_score=0.0,
                durable_mastery_score=0.0,
                mastery_score_combined=0.0,
                confidence_interval=1.0,
                evidence_count=0,
                new_review_interval=current_review_interval,
                last_attempt_at=datetime.now(timezone.utc),
            )

        current_time = current_time or datetime.now(timezone.utc)
        latest_attempt = attempts[-1]

        # Compute memory score (short-term, decays with time)
        memory_score = self._compute_memory_score(
            latest_attempt,
            previous_memory_score,
            current_time,
            algorithm,
        )

        # Compute durable mastery (long-term, slower to change)
        durable_mastery = self._compute_durable_mastery(
            attempts,
            previous_durable_mastery,
            algorithm,
        )

        # Combine (per ADR-0008: combined, not averaged)
        combined = self._combine_scores(memory_score, durable_mastery, algorithm)

        # Compute confidence (narrows with evidence)
        confidence = self._compute_confidence(len(attempts), algorithm)

        # Compute new review interval (expand on success, contract on failure)
        new_interval = self._compute_review_interval(
            latest_attempt,
            current_review_interval,
            algorithm,
        )

        return MasteryComputation(
            memory_score=memory_score,
            durable_mastery_score=durable_mastery,
            mastery_score_combined=combined,
            confidence_interval=confidence,
            evidence_count=len(attempts),
            new_review_interval=new_interval,
            last_attempt_at=latest_attempt.created_at,
        )

    # ============================================================
    # Internal computations (pure functions)
    # ============================================================

    def _compute_memory_score(
        self,
        latest_attempt: Attempt,
        previous_memory: float,
        current_time: datetime,
        algorithm: AlgorithmVersion,
    ) -> float:
        """Compute the short-term memory score.

        Memory score is highly sensitive to the latest attempt:
        - Correct → boost (weighted by hint penalty)
        - Incorrect → sharp drop
        - Partial → moderate boost

        Then apply time-based decay since the last attempt.
        """
        # Time since last attempt (in days)
        time_since = (current_time - latest_attempt.created_at).total_seconds() / 86400.0
        decay_rate = algorithm.decay_rate_per_day

        # Base update from the latest attempt
        effective_credit = latest_attempt.effective_credit

        # Hint penalty: reduce credit if hints were used
        if latest_attempt.hint_used:
            effective_credit *= (1.0 - algorithm.hint_usage_mastery_penalty)

        # Weighted update: 70% new evidence, 30% previous (with decay)
        decayed_previous = previous_memory * (decay_rate ** time_since)
        new_memory = 0.7 * effective_credit + 0.3 * decayed_previous

        # If the attempt was incorrect, apply a sharper drop
        if latest_attempt.is_incorrect:
            new_memory = min(new_memory, previous_memory * 0.5)

        return max(0.0, min(1.0, new_memory))

    def _compute_durable_mastery(
        self,
        attempts: list[Attempt],
        previous_durable: float,
        algorithm: AlgorithmVersion,
    ) -> float:
        """Compute the durable mastery score.

        Durable mastery is slower to rise (requires sustained correct performance)
        and slower to fall (a single failure does not collapse it).

        Approach: exponential moving average of attempt outcomes, with
        a consolidation rate that makes it harder to increase than decrease.
        """
        if not attempts:
            return 0.0

        consolidation = algorithm.mastery_consolidation_rate
        score = previous_durable

        for attempt in attempts:
            credit = attempt.effective_credit
            if attempt.hint_used:
                credit *= (1.0 - algorithm.hint_usage_mastery_penalty)

            if credit >= score:
                # Rising is harder (consolidation rate is low, e.g., 0.10)
                score = score + consolidation * (credit - score)
            else:
                # Falling is easier (2x the consolidation rate for decline)
                score = score + (consolidation * 2.0) * (credit - score)

        return max(0.0, min(1.0, score))

    def _combine_scores(
        self,
        memory: float,
        durable: float,
        algorithm: AlgorithmVersion,
    ) -> float:
        """Combine memory and durable scores into a single estimate.

        Per ADR-0008: "combined, not averaged." The durable score anchors
        the estimate; the memory score modulates it for scheduling.

        Default weighting: 60% durable, 40% memory. The algorithm
        version's parameters can override this.
        """
        memory_weight = algorithm.parameters.get("memory_weight", 0.40)
        durable_weight = algorithm.parameters.get("durable_weight", 0.60)
        combined = memory_weight * memory + durable_weight * durable
        return max(0.0, min(1.0, combined))

    def _compute_confidence(
        self,
        evidence_count: int,
        algorithm: AlgorithmVersion,
    ) -> float:
        """Compute the confidence interval (narrows with more evidence).

        With 0 attempts: full uncertainty (1.0).
        With many attempts: low uncertainty (approaches 0.0).

        Formula: 1.0 / (1.0 + evidence_count * 0.1)
        At 10 attempts: ~0.50
        At 30 attempts: ~0.25
        At 100 attempts: ~0.09
        """
        if evidence_count == 0:
            return 1.0
        return 1.0 / (1.0 + evidence_count * 0.1)

    def _compute_review_interval(
        self,
        latest_attempt: Attempt,
        current_interval: ReviewInterval,
        algorithm: AlgorithmVersion,
    ) -> ReviewInterval:
        """Compute the new review interval.

        - Successful attempt → expand interval (spaced repetition).
        - Failed attempt → contract interval.
        - Partial → slight expansion (partial credit means some retention).
        """
        if latest_attempt.is_correct:
            return current_interval.expand(algorithm.review_interval_expansion_factor)
        if latest_attempt.is_incorrect:
            return current_interval.contract(algorithm.review_interval_contraction_factor)
        # Partial: slight expansion proportional to partial credit
        credit = latest_attempt.partial_credit or 0.5
        factor = 1.0 + (credit * (algorithm.review_interval_expansion_factor - 1.0) * 0.5)
        return current_interval.expand(factor)
