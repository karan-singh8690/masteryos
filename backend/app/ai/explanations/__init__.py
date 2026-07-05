"""AI Explanations — generates enhanced explanations after answer submission.

After answer submission, AI receives:
- Question
- Student answer
- Correct answer
- Misconception
- Mastery
- Difficulty
- Learning objective

Generates:
- Beginner explanation
- Interview explanation
- Detailed explanation
- Simple explanation
- Analogy
- Common mistakes
- Study tips

Rule-based explanation remains fallback.

AI explanations are NEVER automatically published.
Workflow: Draft → Content Editor Review → Approve → Published → Student Visible
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone as tz_utc
from typing import Any
from uuid import UUID, uuid4

from app.ai import AIRequest, AIResponse, AIUnavailableError, AISafetyError, PromptApprovalState
from app.ai.gateway import AIGateway
from app.ai.prompts import PromptRepository, PromptType, get_prompt_repository
from app.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AIExplanation:
    """An AI-generated explanation (pending review)."""
    id: UUID = field(default_factory=uuid4)
    attempt_id: UUID = field(default_factory=uuid4)
    concept_id: UUID | None = None
    # Content sections
    beginner_explanation: str = ""
    interview_explanation: str = ""
    detailed_explanation: str = ""
    analogy: str = ""
    common_mistakes: str = ""
    study_tips: str = ""
    # Metadata
    raw_ai_response: str = ""
    provider: str = ""
    model: str = ""
    prompt_version: str = ""
    tokens_used: int = 0
    cost_cents: int = 0
    latency_ms: int = 0
    confidence: float = 0.5
    # Review workflow
    approval_state: PromptApprovalState = PromptApprovalState.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(tz_utc.utc))
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    # Revision history
    revision_count: int = 0
    edited_content: str | None = None  # Editor's modified version

    @property
    def is_published(self) -> bool:
        return self.approval_state == PromptApprovalState.PUBLISHED

    @property
    def display_content(self) -> str:
        """Return the content to display (edited version if available, else raw)."""
        return self.edited_content or self._format_sections()

    def _format_sections(self) -> str:
        """Format all sections into a single markdown string."""
        sections = []
        if self.beginner_explanation:
            sections.append(f"## Beginner Explanation\n\n{self.beginner_explanation}")
        if self.interview_explanation:
            sections.append(f"## Interview Explanation\n\n{self.interview_explanation}")
        if self.detailed_explanation:
            sections.append(f"## Detailed Explanation\n\n{self.detailed_explanation}")
        if self.analogy:
            sections.append(f"## Analogy\n\n{self.analogy}")
        if self.common_mistakes:
            sections.append(f"## Common Mistakes\n\n{self.common_mistakes}")
        if self.study_tips:
            sections.append(f"## Study Tips\n\n{self.study_tips}")
        return "\n\n---\n\n".join(sections)


class ExplanationGenerator:
    """Generates AI-enhanced explanations after answer submission.

    The Rule Engine's explanation is always the fallback.
    AI explanations go through human review before being shown to students.
    """

    def __init__(
        self,
        gateway: AIGateway,
        prompt_repo: PromptRepository | None = None,
    ) -> None:
        self._gateway = gateway
        self._prompt_repo = prompt_repo or get_prompt_repository()

    async def generate(
        self,
        *,
        attempt_id: UUID,
        question_prompt: str,
        student_answer: str,
        correct_answer: str,
        question_type: str,
        difficulty: str,
        concept_name: str,
        misconception: str | None = None,
        mastery_score: float = 0.0,
        user_id: UUID | None = None,
    ) -> AIExplanation:
        """Generate an AI explanation for a submitted answer.

        If AI is unavailable or safety validation fails, returns a draft
        with empty content (the rule-based explanation will be used instead).
        """
        # Get the published explanation prompt
        prompt = self._prompt_repo.get_published(PromptType.EXPLANATION)
        if prompt is None:
            logger.warning("no_explanation_prompt_published")
            return AIExplanation(
                attempt_id=attempt_id,
                concept_id=None,
                approval_state=PromptApprovalState.DRAFT,
                raw_ai_response="",
            )

        # Render the prompt with variables
        variables = {
            "question_prompt": question_prompt,
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "question_type": question_type,
            "difficulty": difficulty,
            "concept_name": concept_name,
            "misconception": misconception or "None identified",
            "mastery_score": f"{mastery_score:.1%}",
        }

        # Validate required variables
        missing = prompt.validate_variables(variables)
        if missing:
            logger.error("missing_prompt_variables", missing=missing)
            return AIExplanation(
                attempt_id=attempt_id,
                approval_state=PromptApprovalState.DRAFT,
            )

        system_prompt, user_prompt = prompt.render(variables)

        # Create AI request
        request = AIRequest.create(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=None,  # Use default
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            request_type="explanation",
            user_id=user_id,
            prompt_version=prompt.version,
        )

        try:
            response = await self._gateway.generate(request)

            # Parse the AI response into sections
            sections = self._parse_sections(response.content)

            return AIExplanation(
                attempt_id=attempt_id,
                beginner_explanation=sections.get("beginner", ""),
                interview_explanation=sections.get("interview", ""),
                detailed_explanation=sections.get("detailed", ""),
                analogy=sections.get("analogy", ""),
                common_mistakes=sections.get("common_mistakes", ""),
                study_tips=sections.get("study_tips", ""),
                raw_ai_response=response.content,
                provider=response.provider.value,
                model=response.model,
                prompt_version=prompt.version,
                tokens_used=response.total_tokens,
                cost_cents=response.cost_cents,
                latency_ms=response.latency_ms,
                confidence=response.confidence,
                approval_state=PromptApprovalState.DRAFT,
            )

        except AIUnavailableError as exc:
            logger.info("ai_unavailable_for_explanation", error=str(exc))
            return AIExplanation(
                attempt_id=attempt_id,
                approval_state=PromptApprovalState.DRAFT,
                raw_ai_response="",
            )
        except AISafetyError as exc:
            logger.warning("ai_explanation_safety_rejected", notes=exc.notes)
            return AIExplanation(
                attempt_id=attempt_id,
                approval_state=PromptApprovalState.DRAFT,
                raw_ai_response="",
                review_notes=f"Safety rejected: {exc.notes}",
            )

    def _parse_sections(self, content: str) -> dict[str, str]:
        """Parse AI response into sections by markdown headers."""
        sections: dict[str, str] = {}
        current_section: str | None = None
        current_content: list[str] = []

        for line in content.split("\n"):
            if line.startswith("## "):
                # Save previous section
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content).strip()

                # Parse section name
                header = line[3:].strip().lower()
                if "beginner" in header:
                    current_section = "beginner"
                elif "interview" in header:
                    current_section = "interview"
                elif "detailed" in header:
                    current_section = "detailed"
                elif "analogy" in header:
                    current_section = "analogy"
                elif "common" in header or "mistake" in header:
                    current_section = "common_mistakes"
                elif "study" in header or "tip" in header:
                    current_section = "study_tips"
                else:
                    current_section = header.replace(" ", "_")

                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section and current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections


# ============================================================
# Human Review Workflow
# ============================================================


class ExplanationReviewService:
    """Manages the human review workflow for AI explanations.

    Workflow: Draft → Content Editor Review → Approve → Published → Student Visible
    """

    def __init__(self) -> None:
        self._explanations: dict[UUID, AIExplanation] = {}

    async def submit_for_review(self, explanation: AIExplanation) -> AIExplanation:
        """Submit a draft explanation for review."""
        if explanation.approval_state != PromptApprovalState.DRAFT:
            return explanation
        explanation.approval_state = PromptApprovalState.IN_REVIEW
        self._explanations[explanation.id] = explanation
        return explanation

    async def approve(
        self,
        explanation_id: UUID,
        reviewer_id: UUID,
        edited_content: str | None = None,
        notes: str | None = None,
    ) -> AIExplanation | None:
        """Approve an explanation (optionally with edits)."""
        exp = self._explanations.get(explanation_id)
        if exp is None or exp.approval_state != PromptApprovalState.IN_REVIEW:
            return None

        exp.approval_state = PromptApprovalState.APPROVED
        exp.reviewed_by = reviewer_id
        exp.reviewed_at = datetime.now(tz_utc.utc)
        exp.review_notes = notes
        if edited_content:
            exp.edited_content = edited_content
            exp.revision_count += 1
        return exp

    async def reject(
        self,
        explanation_id: UUID,
        reviewer_id: UUID,
        reason: str,
    ) -> AIExplanation | None:
        """Reject an explanation."""
        exp = self._explanations.get(explanation_id)
        if exp is None:
            return None
        exp.approval_state = PromptApprovalState.REJECTED
        exp.reviewed_by = reviewer_id
        exp.reviewed_at = datetime.now(tz_utc.utc)
        exp.review_notes = reason
        return exp

    async def publish(self, explanation_id: UUID) -> AIExplanation | None:
        """Publish an approved explanation (makes it student-visible)."""
        exp = self._explanations.get(explanation_id)
        if exp is None or exp.approval_state != PromptApprovalState.APPROVED:
            return None
        exp.approval_state = PromptApprovalState.PUBLISHED
        return exp

    async def get_pending_reviews(self) -> list[AIExplanation]:
        """Get all explanations pending review."""
        return [
            e for e in self._explanations.values()
            if e.approval_state == PromptApprovalState.IN_REVIEW
        ]

    async def get_published(self, attempt_id: UUID) -> AIExplanation | None:
        """Get the published explanation for an attempt."""
        for exp in self._explanations.values():
            if exp.attempt_id == attempt_id and exp.is_published:
                return exp
        return None


__all__ = [
    "AIExplanation",
    "ExplanationGenerator",
    "ExplanationReviewService",
]
