"""Prompt Management — versioned prompt repository.

Every prompt has:
- Version
- Owner
- Created date
- Approval state

Prompt types:
- Explanation Prompt
- Weakness Summary Prompt
- Teacher Insight Prompt
- Content Review Prompt
- Recommendation Prompt
- Weekly Report Prompt
- Interview Coach Prompt
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone as tz_utc
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class PromptType(str, Enum):
    """Types of AI prompts."""
    EXPLANATION = "explanation"
    WEAKNESS_SUMMARY = "weakness_summary"
    TEACHER_INSIGHT = "teacher_insight"
    CONTENT_REVIEW = "content_review"
    RECOMMENDATION = "recommendation"
    WEEKLY_REPORT = "weekly_report"
    INTERVIEW_COACH = "interview_coach"


class PromptStatus(str, Enum):
    """Approval state for prompts."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass
class PromptVersion:
    """A versioned prompt template."""
    id: UUID
    prompt_type: PromptType
    version: str  # Semantic versioning (e.g., "1.0.0")
    name: str
    description: str
    system_prompt: str
    user_prompt_template: str  # Template with {variable} placeholders
    variables: list[str]  # Required variables
    owner: str  # User ID or "system"
    status: PromptStatus = PromptStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(tz_utc.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz_utc.utc))
    published_at: datetime | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    # Configuration
    temperature: float = 0.7
    max_tokens: int = 2048
    # Metadata
    tags: list[str] = field(default_factory=list)
    notes: str | None = None

    def render(self, variables: dict[str, Any]) -> tuple[str, str]:
        """Render the prompt with the given variables.

        Returns (system_prompt, user_prompt).
        """
        system = self.system_prompt
        user = self.user_prompt_template

        for key, value in variables.items():
            placeholder = "{" + key + "}"
            user = user.replace(placeholder, str(value))
            system = system.replace(placeholder, str(value))

        return system, user

    def validate_variables(self, variables: dict[str, Any]) -> list[str]:
        """Check that all required variables are provided. Returns missing variables."""
        return [v for v in self.variables if v not in variables]


# ============================================================
# Default Prompts
# ============================================================


DEFAULT_PROMPTS: dict[PromptType, PromptVersion] = {
    PromptType.EXPLANATION: PromptVersion(
        id=uuid4(),
        prompt_type=PromptType.EXPLANATION,
        version="1.0.0",
        name="Default Explanation Prompt",
        description="Generates beginner + interview explanations for a question after submission",
        system_prompt=(
            "You are an expert Python instructor. Generate clear, accurate explanations "
            "for a student who just answered a question. Never invent facts. "
            "If you're unsure, say so. Keep explanations concise."
        ),
        user_prompt_template=(
            "Question: {question_prompt}\n\n"
            "Student's answer: {student_answer}\n\n"
            "Correct answer: {correct_answer}\n\n"
            "Question type: {question_type}\n"
            "Difficulty: {difficulty}\n"
            "Concept: {concept_name}\n"
            "Misconception (if any): {misconception}\n\n"
            "Mastery score: {mastery_score}\n\n"
            "Generate the following:\n"
            "1. **Beginner explanation**: Simple, jargon-free explanation\n"
            "2. **Interview explanation**: How to explain this in an interview\n"
            "3. **Detailed explanation**: In-depth technical explanation\n"
            "4. **Analogy**: A real-world analogy\n"
            "5. **Common mistakes**: What students typically get wrong\n"
            "6. **Study tips**: How to remember this concept\n\n"
            "Format each section with a markdown header."
        ),
        variables=[
            "question_prompt", "student_answer", "correct_answer",
            "question_type", "difficulty", "concept_name",
            "misconception", "mastery_score",
        ],
        owner="system",
        status=PromptStatus.PUBLISHED,
        published_at=datetime.now(tz_utc.utc),
        temperature=0.5,
        max_tokens=2048,
    ),
    PromptType.WEAKNESS_SUMMARY: PromptVersion(
        id=uuid4(),
        prompt_type=PromptType.WEAKNESS_SUMMARY,
        version="1.0.0",
        name="Default Weakness Summary Prompt",
        description="Summarizes a learner's weak areas with actionable advice",
        system_prompt="You are a learning analytics expert. Analyze weakness patterns and provide specific, actionable recommendations.",
        user_prompt_template=(
            "Learner mastery data:\n{mastery_data}\n\n"
            "Recent attempts:\n{recent_attempts}\n\n"
            "Generate a weakness summary that includes:\n"
            "1. Top 3 weak concepts with explanations\n"
            "2. Pattern analysis (common mistake types)\n"
            "3. Recommended study plan (next 3 sessions)\n"
            "4. Time estimate for improvement\n"
        ),
        variables=["mastery_data", "recent_attempts"],
        owner="system",
        status=PromptStatus.PUBLISHED,
        published_at=datetime.now(tz_utc.utc),
        temperature=0.4,
        max_tokens=1536,
    ),
    PromptType.RECOMMENDATION: PromptVersion(
        id=uuid4(),
        prompt_type=PromptType.RECOMMENDATION,
        version="1.0.0",
        name="Default Recommendation Prompt",
        description="Rewrites rule-based recommendations into natural language",
        system_prompt=(
            "You are a study coach. Rewrite the given recommendation in natural, motivating language. "
            "DO NOT change the recommendation type or target concept. "
            "DO NOT invent new recommendations. "
            "Keep it under 2 sentences."
        ),
        user_prompt_template=(
            "Recommendation type: {recommendation_type}\n"
            "Target concept: {concept_name}\n"
            "Reason: {reason}\n"
            "Learner's current mastery: {mastery_score}\n"
            "Learner's recent activity: {recent_activity}\n\n"
            "Rewrite this recommendation in natural, motivating language."
        ),
        variables=["recommendation_type", "concept_name", "reason", "mastery_score", "recent_activity"],
        owner="system",
        status=PromptStatus.PUBLISHED,
        published_at=datetime.now(tz_utc.utc),
        temperature=0.6,
        max_tokens=256,
    ),
    PromptType.WEEKLY_REPORT: PromptVersion(
        id=uuid4(),
        prompt_type=PromptType.WEEKLY_REPORT,
        version="1.0.0",
        name="Default Weekly Report Prompt",
        description="Generates a weekly learning report for a student",
        system_prompt="You are a learning analytics report generator. Produce clear, data-driven reports with actionable insights.",
        user_prompt_template=(
            "Student: {student_name}\n"
            "Week: {week_range}\n\n"
            "Statistics:\n"
            "- Questions answered: {questions_answered}\n"
            "- Accuracy: {accuracy}%\n"
            "- Time studied: {study_time}\n"
            "- Current streak: {streak} days\n"
            "- Mastery improvement: {mastery_delta}%\n\n"
            "Weak concepts: {weak_concepts}\n"
            "Strong concepts: {strong_concepts}\n\n"
            "Generate a weekly report with:\n"
            "1. Summary of the week\n"
            "2. Key achievements\n"
            "3. Areas needing attention\n"
            "4. Recommendations for next week\n"
            "5. Forecast (mastery prediction)\n"
        ),
        variables=[
            "student_name", "week_range", "questions_answered", "accuracy",
            "study_time", "streak", "mastery_delta", "weak_concepts", "strong_concepts",
        ],
        owner="system",
        status=PromptStatus.PUBLISHED,
        published_at=datetime.now(tz_utc.utc),
        temperature=0.3,
        max_tokens=2048,
    ),
    PromptType.TEACHER_INSIGHT: PromptVersion(
        id=uuid4(),
        prompt_type=PromptType.TEACHER_INSIGHT,
        version="1.0.0",
        name="Default Teacher Insight Prompt",
        description="Provides instructors with class-level insights",
        system_prompt="You are an educational analytics expert. Analyze class data and provide actionable teaching insights.",
        user_prompt_template=(
            "Class data:\n{class_data}\n\n"
            "Concept performance:\n{concept_performance}\n\n"
            "Misconception trends:\n{misconception_trends}\n\n"
            "Generate:\n"
            "1. Class weaknesses summary\n"
            "2. Concept heatmap analysis\n"
            "3. Misconception trend analysis\n"
            "4. Recommended curriculum improvements\n"
            "5. Question quality alerts\n"
            "6. Student engagement summary\n"
        ),
        variables=["class_data", "concept_performance", "misconception_trends"],
        owner="system",
        status=PromptStatus.PUBLISHED,
        published_at=datetime.now(tz_utc.utc),
        temperature=0.4,
        max_tokens=2048,
    ),
    PromptType.CONTENT_REVIEW: PromptVersion(
        id=uuid4(),
        prompt_type=PromptType.CONTENT_REVIEW,
        version="1.0.0",
        name="Default Content Review Prompt",
        description="Analyzes content quality and suggests improvements",
        system_prompt="You are a curriculum quality reviewer. Analyze content for clarity, accuracy, and pedagogical effectiveness.",
        user_prompt_template=(
            "Template code: {template_code}\n"
            "Question type: {question_type}\n"
            "Prompt template: {prompt_template}\n"
            "Correct answer generator: {correct_answer}\n"
            "Distractor generator: {distractor_generator}\n"
            "Explanation template: {explanation_template}\n"
            "Hint tiers: {hint_tiers}\n"
            "Difficulty: {difficulty}\n\n"
            "Analyze this question template for:\n"
            "1. Clarity of the prompt\n"
            "2. Quality of distractors\n"
            "3. Explanation completeness\n"
            "4. Difficulty appropriateness\n"
            "5. Missing elements\n"
            "6. Improvement suggestions\n"
        ),
        variables=[
            "template_code", "question_type", "prompt_template", "correct_answer",
            "distractor_generator", "explanation_template", "hint_tiers", "difficulty",
        ],
        owner="system",
        status=PromptStatus.PUBLISHED,
        published_at=datetime.now(tz_utc.utc),
        temperature=0.3,
        max_tokens=1536,
    ),
    PromptType.INTERVIEW_COACH: PromptVersion(
        id=uuid4(),
        prompt_type=PromptType.INTERVIEW_COACH,
        version="1.0.0",
        name="Default Interview Coach Prompt",
        description="Provides interview preparation advice",
        system_prompt="You are a senior engineering interviewer. Provide specific, actionable interview preparation advice.",
        user_prompt_template=(
            "Learner's interview readiness: {interview_readiness}%\n"
            "Strong areas: {strong_areas}\n"
            "Weak areas: {weak_areas}\n"
            "Target role: {target_role}\n"
            "Available study time: {available_time}\n\n"
            "Generate an interview preparation plan:\n"
            "1. Priority topics to review\n"
            "2. Common interview questions for weak areas\n"
            "3. Mock interview scenarios\n"
            "4. Time allocation recommendations\n"
            "5. Confidence-building tips\n"
        ),
        variables=["interview_readiness", "strong_areas", "weak_areas", "target_role", "available_time"],
        owner="system",
        status=PromptStatus.PUBLISHED,
        published_at=datetime.now(tz_utc.utc),
        temperature=0.5,
        max_tokens=2048,
    ),
}


# ============================================================
# Prompt Repository
# ============================================================


class PromptRepository:
    """Repository for versioned prompts.

    In production, this would be backed by a database table.
    For now, it's in-memory with default prompts.
    """

    def __init__(self) -> None:
        self._prompts: dict[UUID, PromptVersion] = {}
        self._by_type: dict[PromptType, list[UUID]] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default prompts."""
        for prompt_type, prompt in DEFAULT_PROMPTS.items():
            self._prompts[prompt.id] = prompt
            self._by_type.setdefault(prompt_type, []).append(prompt.id)

    def get_by_id(self, prompt_id: UUID) -> PromptVersion | None:
        return self._prompts.get(prompt_id)

    def get_published(self, prompt_type: PromptType) -> PromptVersion | None:
        """Get the latest published prompt for a type."""
        ids = self._by_type.get(prompt_type, [])
        published = [
            self._prompts[id]
            for id in ids
            if self._prompts[id].status == PromptStatus.PUBLISHED
        ]
        if not published:
            return None
        # Return the latest version
        return sorted(published, key=lambda p: p.version, reverse=True)[0]

    def list_by_type(self, prompt_type: PromptType) -> list[PromptVersion]:
        """List all versions of a prompt type."""
        ids = self._by_type.get(prompt_type, [])
        return [self._prompts[id] for id in ids]

    def list_all(self) -> list[PromptVersion]:
        """List all prompts."""
        return list(self._prompts.values())

    def create(self, prompt: PromptVersion) -> PromptVersion:
        """Create a new prompt version."""
        self._prompts[prompt.id] = prompt
        self._by_type.setdefault(prompt.prompt_type, []).append(prompt.id)
        return prompt

    def update(self, prompt_id: UUID, **updates: Any) -> PromptVersion | None:
        """Update a prompt version."""
        prompt = self._prompts.get(prompt_id)
        if prompt is None:
            return None
        # Create a new version (prompts are immutable once published)
        updated = PromptVersion(
            id=prompt.id,
            prompt_type=prompt.prompt_type,
            version=updates.get("version", prompt.version),
            name=updates.get("name", prompt.name),
            description=updates.get("description", prompt.description),
            system_prompt=updates.get("system_prompt", prompt.system_prompt),
            user_prompt_template=updates.get("user_prompt_template", prompt.user_prompt_template),
            variables=updates.get("variables", prompt.variables),
            owner=updates.get("owner", prompt.owner),
            status=updates.get("status", prompt.status),
            temperature=updates.get("temperature", prompt.temperature),
            max_tokens=updates.get("max_tokens", prompt.max_tokens),
            tags=updates.get("tags", prompt.tags),
            notes=updates.get("notes", prompt.notes),
        )
        self._prompts[prompt_id] = updated
        return updated

    def publish(self, prompt_id: UUID, approved_by: UUID) -> PromptVersion | None:
        """Publish a prompt (requires approval)."""
        prompt = self._prompts.get(prompt_id)
        if prompt is None:
            return None
        if prompt.status not in (PromptStatus.APPROVED, PromptStatus.DRAFT):
            return None
        # Archive previous published version
        for other_id in self._by_type.get(prompt.prompt_type, []):
            other = self._prompts.get(other_id)
            if other and other.id != prompt_id and other.status == PromptStatus.PUBLISHED:
                self._prompts[other_id] = PromptVersion(
                    id=other.id,
                    prompt_type=other.prompt_type,
                    version=other.version,
                    name=other.name,
                    description=other.description,
                    system_prompt=other.system_prompt,
                    user_prompt_template=other.user_prompt_template,
                    variables=other.variables,
                    owner=other.owner,
                    status=PromptStatus.ARCHIVED,
                    created_at=other.created_at,
                    updated_at=datetime.now(tz_utc.utc),
                    published_at=other.published_at,
                    approved_by=other.approved_by,
                    approved_at=other.approved_at,
                    temperature=other.temperature,
                    max_tokens=other.max_tokens,
                    tags=other.tags,
                    notes=other.notes,
                )

        # Publish the new version
        published = PromptVersion(
            id=prompt.id,
            prompt_type=prompt.prompt_type,
            version=prompt.version,
            name=prompt.name,
            description=prompt.description,
            system_prompt=prompt.system_prompt,
            user_prompt_template=prompt.user_prompt_template,
            variables=prompt.variables,
            owner=prompt.owner,
            status=PromptStatus.PUBLISHED,
            created_at=prompt.created_at,
            updated_at=datetime.now(tz_utc.utc),
            published_at=datetime.now(tz_utc.utc),
            approved_by=approved_by,
            approved_at=datetime.now(tz_utc.utc),
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            tags=prompt.tags,
            notes=prompt.notes,
        )
        self._prompts[prompt_id] = published
        return published


# Singleton repository
_repository: PromptRepository | None = None


def get_prompt_repository() -> PromptRepository:
    global _repository
    if _repository is None:
        _repository = PromptRepository()
    return _repository


__all__ = [
    "PromptType",
    "PromptStatus",
    "PromptVersion",
    "PromptRepository",
    "DEFAULT_PROMPTS",
    "get_prompt_repository",
]
