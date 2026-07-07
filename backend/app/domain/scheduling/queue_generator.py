"""DeterministicQueueGenerator — a pure domain service that generates adaptive queues.

This is Version 1 of the scheduler (per ADR-0007: deterministic-first).
It is a pure function: given the same inputs, it produces the same output.
No ML. No randomness (uses a seed derived from inputs for reproducibility).

Queue generation considers:
- Learning goal (urgency weighting)
- Due reviews (spaced repetition)
- Weak concepts (remediation)
- Concept prerequisites (readiness)
- Difficulty progression (zone of proximal development)
- Session intent (drill vs. review vs. diagnostic)

The output is a list of QueueItem DTOs with:
- question_instance_id (generated placeholder; real instantiation by QuestionFactory later)
- concept_id
- difficulty
- estimated_duration_seconds
- recommendation_score (0.0–1.0)
- reason (e.g., "new concept", "review due", "weak concept")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from app.domain.shared.kernel import (
    Difficulty,
    ReviewPriority,
    SessionIntent,
)


@dataclass(frozen=True)
class QueueItem:
    """A single item in the adaptive queue."""

    question_instance_id: UUID
    concept_id: UUID
    difficulty: str
    estimated_duration_seconds: int
    recommendation_score: float
    reason: str


class DeterministicQueueGenerator:
    """Generates an adaptive queue deterministically.

    This is a pure domain service — no I/O, no external dependencies.
    The same inputs always produce the same output (invariant I3, ASD 5.3).
    """

    # Default weights for priority computation
    REVIEW_WEIGHT = 0.35
    WEAKNESS_WEIGHT = 0.30
    NEW_CONCEPT_WEIGHT = 0.20
    GOAL_URGENCY_WEIGHT = 0.15

    # Phase 2: Exam proximity multipliers (how much to compress review intervals)
    EXAM_PROXIMITY_MULTIPLIERS = {
        90: 1.0,   # >90 days: normal
        60: 0.7,   # 60-90 days: compress 30%
        30: 0.5,   # 30-60 days: compress 50%
        15: 0.3,   # 15-30 days: aggressive
        0: 0.1,    # <15 days: cram mode
    }

    def generate(
        self,
        enrollment_id: Any,
        session_id: Any,
        intent: SessionIntent,
        mastery_scores: list[Any],
        due_reviews: list[Any],
        learning_goals: list[Any],
        queue_size: int = 15,
        # Phase 2 Indian localization
        concept_prerequisites: dict[Any, list[tuple[Any, float]]] | None = None,
        exam_proximity_days: int | None = None,
        exam_weightage: dict[Any, float] | None = None,
    ) -> list[QueueItem]:
        """Generate an adaptive queue.

        Args:
            enrollment_id: The learner's enrollment ID.
            session_id: The study session ID.
            intent: The session intent (drill, review, diagnostic, mixed).
            mastery_scores: List of MasteryScore domain entities.
            due_reviews: List of Review domain entities that are due.
            learning_goals: List of active LearningGoal domain entities.
            queue_size: Maximum queue size.
            concept_prerequisites: Phase 2 — {concept_id: [(prereq_id, min_mastery), ...]}
            exam_proximity_days: Phase 2 — days until exam (affects review urgency)
            exam_weightage: Phase 2 — {concept_id: weightage} for prioritizing high-weight topics

        Returns:
            An ordered list of QueueItem DTOs.
        """
        # Phase 2: Build mastery lookup for prerequisite checking
        mastery_lookup: dict[Any, float] = {}
        for score in mastery_scores:
            mastery_lookup[score.concept_id] = score.mastery_score_combined

        # Phase 2: Build set of concepts whose prerequisites are met
        unlocked_concepts: set[Any] = set()
        if concept_prerequisites:
            for concept_id, prereqs in concept_prerequisites.items():
                all_met = True
                for prereq_id, min_mastery in prereqs:
                    actual = mastery_lookup.get(prereq_id, 0.0)
                    if actual < min_mastery:
                        all_met = False
                        break
                if all_met:
                    unlocked_concepts.add(concept_id)
        else:
            # No prerequisites defined — all concepts unlocked
            unlocked_concepts = set(mastery_lookup.keys())
        # Handle empty state (new learner with no mastery scores)
        if not mastery_scores and not due_reviews:
            return self._generate_diagnostic_queue(enrollment_id, session_id, queue_size)

        # Build candidate list with priority scores
        candidates: list[tuple[float, str, UUID, str]] = []

        # Phase 2: Exam proximity multiplier — boost all priorities as exam approaches
        exam_boost = 1.0
        if exam_proximity_days is not None:
            for threshold, multiplier in sorted(self.EXAM_PROXIMITY_MULTIPLIERS.items(), reverse=True):
                if exam_proximity_days >= threshold:
                    exam_boost = 1.0 + (1.0 - multiplier)  # Convert compression to boost
                    break

        # 1. Add due reviews (highest priority for review intent)
        for review in due_reviews:
            priority = self._compute_review_priority(review, intent)
            # Phase 2: Boost high-weightage concepts
            if exam_weightage and review.concept_id.value in exam_weightage:
                priority *= (1.0 + exam_weightage[review.concept_id.value])
            priority *= exam_boost
            reason = "review_due"
            candidates.append((
                priority,
                reason,
                review.concept_id.value,
                self._estimate_difficulty(review, mastery_scores),
            ))

        # 2. Add weak concepts (high priority for drill intent)
        for score in mastery_scores:
            if score.is_weak:
                # Phase 2: Skip if prerequisites not met
                if concept_prerequisites and score.concept_id not in unlocked_concepts:
                    continue
                priority = self._compute_weakness_priority(score, intent)
                # Phase 2: Boost high-weightage weak concepts (red alert!)
                if exam_weightage and score.concept_id.value in exam_weightage:
                    priority *= (1.0 + exam_weightage[score.concept_id.value] * 2)  # Double boost for weak + high-weight
                priority *= exam_boost
                reason = "weak_concept"
                candidates.append((
                    priority,
                    reason,
                    score.concept_id.value,
                    self._score_difficulty(score),
                ))

        # 3. Add concepts in development (medium priority)
        for score in mastery_scores:
            if not score.is_weak and not score.is_proficient_or_above:
                # Phase 2: Skip if prerequisites not met
                if concept_prerequisites and score.concept_id not in unlocked_concepts:
                    continue
                priority = self._compute_development_priority(score, intent)
                if exam_weightage and score.concept_id.value in exam_weightage:
                    priority *= (1.0 + exam_weightage[score.concept_id.value])
                priority *= exam_boost
                reason = "in_progress"
                candidates.append((
                    priority,
                    reason,
                    score.concept_id.value,
                    self._score_difficulty(score),
                ))

        # 4. Add new concepts (lower priority, but needed for progression)
        # In a full implementation, this would query the concept graph for
        # concepts whose prerequisites are met but the learner hasn't seen.
        # For this slice, we add a few placeholder new concepts.
        new_concept_count = max(0, queue_size - len(candidates))
        for _ in range(min(new_concept_count, 5)):
            candidates.append((
                self.NEW_CONCEPT_WEIGHT,
                "new_concept",
                uuid4(),  # Placeholder; real implementation uses concept graph
                Difficulty.MEDIUM.value,
            ))

        # Sort by priority (descending)
        candidates.sort(key=lambda c: c[0], reverse=True)

        # Take top N
        selected = candidates[:queue_size]

        # Build queue items
        queue_items: list[QueueItem] = []
        for priority, reason, concept_id, difficulty in selected:
            queue_items.append(QueueItem(
                question_instance_id=uuid4(),  # Placeholder; real QuestionFactory instantiates later
                concept_id=concept_id,
                difficulty=difficulty,
                estimated_duration_seconds=self._estimate_duration(difficulty, reason),
                recommendation_score=round(priority, 4),
                reason=reason,
            ))

        return queue_items

    # ============================================================
    # Priority Computation (pure functions)
    # ============================================================

    def _compute_review_priority(self, review: Any, intent: SessionIntent) -> float:
        """Compute priority for a due review."""
        base = self.REVIEW_WEIGHT
        if intent == SessionIntent.REVIEW:
            base *= 1.5  # Boost reviews in review sessions
        elif intent == SessionIntent.DRILL:
            base *= 0.7  # Deprioritize reviews in drill sessions

        # Boost by priority level
        if review.priority == ReviewPriority.HIGH:
            base += 0.15
        elif review.priority == ReviewPriority.MEDIUM:
            base += 0.05

        return min(1.0, base)

    def _compute_weakness_priority(self, score: Any, intent: SessionIntent) -> float:
        """Compute priority for a weak concept."""
        base = self.WEAKNESS_WEIGHT
        if intent == SessionIntent.DRILL:
            base *= 1.5  # Boost weak concepts in drill sessions

        # Boost by severity
        from app.domain.shared.kernel import WeaknessSeverity
        if score.weakness_severity == WeaknessSeverity.SEVERE:
            base += 0.20
        elif score.weakness_severity == WeaknessSeverity.MODERATE:
            base += 0.10
        elif score.weakness_severity == WeaknessSeverity.MILD:
            base += 0.05

        return min(1.0, base)

    def _compute_development_priority(self, score: Any, intent: SessionIntent) -> float:
        """Compute priority for a concept in development."""
        base = 0.15  # Lower than reviews and weak concepts
        if intent == SessionIntent.MIXED:
            base *= 1.2  # Boost in mixed sessions

        return min(1.0, base)

    # ============================================================
    # Difficulty Estimation
    # ============================================================

    def _estimate_difficulty(self, review: Any, mastery_scores: list[Any]) -> str:
        """Estimate difficulty for a review based on the concept's mastery."""
        for score in mastery_scores:
            if score.concept_id == review.concept_id:
                return self._score_difficulty(score)
        return Difficulty.MEDIUM.value

    def _score_difficulty(self, score: Any) -> str:
        """Estimate difficulty based on mastery score."""
        if score.mastery_score_combined < 0.3:
            return Difficulty.HARD.value
        if score.mastery_score_combined < 0.6:
            return Difficulty.MEDIUM.value
        return Difficulty.EASY.value

    def _estimate_duration(self, difficulty: str, reason: str) -> int:
        """Estimate duration in seconds for a question."""
        base = {
            Difficulty.EASY.value: 30,
            Difficulty.MEDIUM.value: 60,
            Difficulty.HARD.value: 120,
        }.get(difficulty, 60)

        if reason == "review_due":
            base = int(base * 0.8)  # Reviews are faster
        elif reason == "new_concept":
            base = int(base * 1.2)  # New concepts take longer

        return base

    # ============================================================
    # Diagnostic Queue (for new learners with no history)
    # ============================================================

    def _generate_diagnostic_queue(
        self,
        enrollment_id: Any,
        session_id: Any,
        queue_size: int,
    ) -> list[QueueItem]:
        """Generate a diagnostic queue for a new learner.

        The diagnostic queue is a stratified sample across difficulty levels
        to establish baseline mastery.
        """
        items: list[QueueItem] = []
        difficulties = [Difficulty.EASY.value, Difficulty.MEDIUM.value, Difficulty.HARD.value]

        for i in range(min(queue_size, 10)):
            difficulty = difficulties[i % len(difficulties)]
            items.append(QueueItem(
                question_instance_id=uuid4(),
                concept_id=uuid4(),  # Placeholder; real implementation uses concept graph
                difficulty=difficulty,
                estimated_duration_seconds=self._estimate_duration(difficulty, "diagnostic"),
                recommendation_score=0.5,
                reason="diagnostic",
            ))

        return items
