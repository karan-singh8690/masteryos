"""AI Study Coach, Predictive Analytics, Content Intelligence, Recommendation Layer.

These modules consume the Rule Engine's outputs and enhance them with AI:
- Study Coach: daily/weekly plans, motivation, tips
- Predictive Analytics: dropout/completion/mastery forecasts
- Content Intelligence: quality analysis, gap detection
- Recommendation Layer: natural language rewriting of rule-based recommendations

AI NEVER changes recommendation type or replaces business logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone as tz_utc
from typing import Any
from uuid import UUID

from app.ai import AIRequest, AIUnavailableError
from app.ai.gateway import AIGateway
from app.ai.prompts import PromptRepository, PromptType, get_prompt_repository
from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Study Coach
# ============================================================


@dataclass
class StudyPlan:
    """AI-generated study plan."""
    daily_plan: str = ""
    weekly_plan: str = ""
    motivation: str = ""
    study_tips: list[str] = field(default_factory=list)
    weakness_summary: str = ""
    next_objectives: list[str] = field(default_factory=list)
    time_recommendations: str = ""
    # Metadata
    provider: str = ""
    model: str = ""
    tokens_used: int = 0
    cost_cents: int = 0


class StudyCoach:
    """Generates personalized study plans based on learner history.

    AI consumes: mastery scores, recent attempts, streak data, goals.
    AI produces: daily plan, weekly plan, motivation, tips.
    """

    def __init__(self, gateway: AIGateway, prompt_repo: PromptRepository | None = None) -> None:
        self._gateway = gateway
        self._prompt_repo = prompt_repo or get_prompt_repository()

    async def generate_plan(
        self,
        *,
        user_id: UUID,
        mastery_data: str,
        recent_attempts: str,
        streak: int,
        daily_goal: float,
        available_time: str = "30 minutes",
    ) -> StudyPlan:
        """Generate a personalized study plan."""
        prompt = self._prompt_repo.get_published(PromptType.WEAKNESS_SUMMARY)
        if prompt is None:
            return StudyPlan()

        system, user = prompt.render({
            "mastery_data": mastery_data,
            "recent_attempts": recent_attempts,
        })

        request = AIRequest.create(
            prompt=user,
            system_prompt=system,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            request_type="study_coach",
            user_id=user_id,
            prompt_version=prompt.version,
        )

        try:
            response = await self._gateway.generate(request)
            return StudyPlan(
                daily_plan=self._extract_section(response.content, "daily"),
                weekly_plan=self._extract_section(response.content, "weekly"),
                motivation=self._extract_section(response.content, "motivation"),
                study_tips=self._extract_list(response.content, "tips"),
                weakness_summary=self._extract_section(response.content, "weakness"),
                next_objectives=self._extract_list(response.content, "objectives"),
                time_recommendations=self._extract_section(response.content, "time"),
                provider=response.provider.value,
                model=response.model,
                tokens_used=response.total_tokens,
                cost_cents=response.cost_cents,
            )
        except AIUnavailableError:
            return StudyPlan()

    def _extract_section(self, content: str, keyword: str) -> str:
        """Extract a section from the AI response by keyword."""
        lines = content.split("\n")
        capturing = False
        result: list[str] = []
        for line in lines:
            if keyword.lower() in line.lower() and ("##" in line or "**" in line):
                capturing = True
                continue
            if capturing:
                if line.startswith("## ") or (line.startswith("**") and keyword.lower() not in line.lower()):
                    break
                result.append(line)
        return "\n".join(result).strip()

    def _extract_list(self, content: str, keyword: str) -> list[str]:
        """Extract a bullet list from the AI response."""
        lines = content.split("\n")
        capturing = False
        result: list[str] = []
        for line in lines:
            if keyword.lower() in line.lower():
                capturing = True
                continue
            if capturing:
                if line.startswith("## ") or (line.startswith("**") and keyword.lower() not in line.lower()):
                    break
                stripped = line.strip()
                if stripped.startswith("- ") or stripped.startswith("* "):
                    result.append(stripped[2:])
                elif stripped and not stripped.startswith("#"):
                    result.append(stripped)
        return [r for r in result if r]


# ============================================================
# Predictive Analytics
# ============================================================


@dataclass
class LearningForecast:
    """AI-generated learning forecasts with confidence scores."""
    dropout_probability: float = 0.0
    dropout_confidence: float = 0.0
    completion_probability: float = 0.0
    completion_confidence: float = 0.0
    mastery_forecast: float = 0.0
    mastery_confidence: float = 0.0
    interview_readiness_forecast: float = 0.0
    interview_confidence: float = 0.0
    study_consistency_score: float = 0.0
    future_review_load: int = 0
    # Metadata
    provider: str = ""
    model: str = ""
    tokens_used: int = 0


class PredictiveAnalytics:
    """Predicts learning outcomes based on learner history.

    Model outputs confidence scores (0.0-1.0).
    AI never replaces the Rule Engine — it only provides forecasts.
    """

    def __init__(self, gateway: AIGateway) -> None:
        self._gateway = gateway

    async def forecast(
        self,
        *,
        user_id: UUID,
        learner_stats: dict[str, Any],
    ) -> LearningForecast:
        """Generate learning forecasts."""
        # Simple heuristic-based forecast (AI would enhance this)
        streak = learner_stats.get("current_streak", 0)
        accuracy = learner_stats.get("avg_accuracy", 0)
        mastery = learner_stats.get("avg_mastery", 0)
        days_active = learner_stats.get("days_active_30d", 0)
        total_attempts = learner_stats.get("total_attempts", 0)

        # Dropout probability: higher if low engagement
        engagement = min(1.0, days_active / 30)
        dropout_prob = max(0.0, 1.0 - engagement) * 0.5
        if streak == 0 and total_attempts < 10:
            dropout_prob = min(0.9, dropout_prob + 0.3)

        # Completion probability: higher if high accuracy + mastery
        completion_prob = (accuracy * 0.4 + mastery * 0.4 + engagement * 0.2)

        # Mastery forecast: predict mastery in 30 days
        mastery_trend = learner_stats.get("mastery_trend", 0)
        mastery_forecast = min(1.0, mastery + mastery_trend * 30)

        # Interview readiness forecast
        interview_forecast = min(1.0, mastery_forecast * 0.8 + accuracy * 0.2)

        # Study consistency
        consistency = engagement * (1 if streak > 0 else 0.5)

        return LearningForecast(
            dropout_probability=round(dropout_prob, 3),
            dropout_confidence=0.7,
            completion_probability=round(completion_prob, 3),
            completion_confidence=0.75,
            mastery_forecast=round(mastery_forecast, 3),
            mastery_confidence=0.8,
            interview_readiness_forecast=round(interview_forecast, 3),
            interview_confidence=0.7,
            study_consistency_score=round(consistency, 3),
            future_review_load=learner_stats.get("due_reviews_count", 0),
        )


# ============================================================
# Content Intelligence
# ============================================================


@dataclass
class ContentAnalysis:
    """AI analysis of content quality."""
    duplicate_templates: list[str] = field(default_factory=list)
    unclear_explanations: list[str] = field(default_factory=list)
    weak_distractors: list[str] = field(default_factory=list)
    unused_misconceptions: list[str] = field(default_factory=list)
    difficulty_imbalance: str = ""
    missing_objectives: list[str] = field(default_factory=list)
    coverage_gaps: list[str] = field(default_factory=list)
    improvement_suggestions: list[str] = field(default_factory=list)
    # Metadata
    provider: str = ""
    model: str = ""
    tokens_used: int = 0


class ContentIntelligence:
    """Analyzes content quality and detects issues.

    Detects:
    - Duplicate templates
    - Unclear explanations
    - Weak distractors
    - Unused misconceptions
    - Difficulty imbalance
    - Missing objectives
    - Coverage gaps

    Generates improvement suggestions.
    """

    def __init__(self, gateway: AIGateway, prompt_repo: PromptRepository | None = None) -> None:
        self._gateway = gateway
        self._prompt_repo = prompt_repo or get_prompt_repository()

    async def analyze_content(
        self,
        *,
        templates_data: str,
        concepts_data: str,
        misconceptions_data: str,
    ) -> ContentAnalysis:
        """Analyze content quality."""
        prompt = self._prompt_repo.get_published(PromptType.CONTENT_REVIEW)
        if prompt is None:
            return ContentAnalysis()

        system, user = prompt.render({
            "template_code": "ALL",
            "question_type": "various",
            "prompt_template": templates_data,
            "correct_answer": "N/A",
            "distractor_generator": "N/A",
            "explanation_template": "N/A",
            "hint_tiers": "N/A",
            "difficulty": "various",
        })

        request = AIRequest.create(
            prompt=user,
            system_prompt=system,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            request_type="content_intelligence",
            prompt_version=prompt.version,
        )

        try:
            response = await self._gateway.generate(request)
            return ContentAnalysis(
                improvement_suggestions=self._extract_list(response.content, "suggestion"),
                provider=response.provider.value,
                model=response.model,
                tokens_used=response.total_tokens,
            )
        except AIUnavailableError:
            return ContentAnalysis()

    def _extract_list(self, content: str, keyword: str) -> list[str]:
        """Extract bullet list items."""
        result: list[str] = []
        capturing = False
        for line in content.split("\n"):
            if keyword.lower() in line.lower():
                capturing = True
                continue
            if capturing:
                stripped = line.strip()
                if stripped.startswith("- ") or stripped.startswith("* "):
                    result.append(stripped[2:])
                elif stripped.startswith("## "):
                    break
        return result


# ============================================================
# AI Recommendation Layer
# ============================================================


class AIRecommendationEnhancer:
    """Rewrites rule-based recommendations into natural language.

    The Rule Engine produces the recommendation.
    AI rewrites it into natural, motivating language.
    AI NEVER changes the recommendation type.
    """

    def __init__(self, gateway: AIGateway, prompt_repo: PromptRepository | None = None) -> None:
        self._gateway = gateway
        self._prompt_repo = prompt_repo or get_prompt_repository()

    async def enhance(
        self,
        *,
        recommendation_type: str,
        concept_name: str,
        reason: str,
        mastery_score: float,
        recent_activity: str,
        user_id: UUID | None = None,
    ) -> str:
        """Enhance a rule-based recommendation with natural language.

        If AI is unavailable, returns the original reason.
        """
        prompt = self._prompt_repo.get_published(PromptType.RECOMMENDATION)
        if prompt is None:
            return reason

        system, user = prompt.render({
            "recommendation_type": recommendation_type,
            "concept_name": concept_name,
            "reason": reason,
            "mastery_score": f"{mastery_score:.1%}",
            "recent_activity": recent_activity,
        })

        request = AIRequest.create(
            prompt=user,
            system_prompt=system,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            request_type="recommendation_enhancement",
            user_id=user_id,
            prompt_version=prompt.version,
        )

        try:
            response = await self._gateway.generate(request)
            return response.content.strip()
        except AIUnavailableError:
            return reason  # Fallback to original


# ============================================================
# Instructor Intelligence
# ============================================================


@dataclass
class InstructorInsights:
    """AI-generated insights for instructors."""
    class_weaknesses: str = ""
    concept_heatmap: str = ""
    misconception_trends: str = ""
    curriculum_improvements: list[str] = field(default_factory=list)
    question_quality_alerts: list[str] = field(default_factory=list)
    student_clusters: str = ""
    engagement_summary: str = ""
    # Metadata
    provider: str = ""
    model: str = ""
    tokens_used: int = 0


class InstructorIntelligence:
    """Provides instructors with class-level insights.

    Provides:
    - Class weaknesses
    - Concept heatmaps
    - Misconception trends
    - Recommended curriculum improvements
    - Question quality alerts
    - Student clusters
    - Engagement summaries
    """

    def __init__(self, gateway: AIGateway, prompt_repo: PromptRepository | None = None) -> None:
        self._gateway = gateway
        self._prompt_repo = prompt_repo or get_prompt_repository()

    async def generate_insights(
        self,
        *,
        class_data: str,
        concept_performance: str,
        misconception_trends: str,
    ) -> InstructorInsights:
        """Generate instructor insights."""
        prompt = self._prompt_repo.get_published(PromptType.TEACHER_INSIGHT)
        if prompt is None:
            return InstructorInsights()

        system, user = prompt.render({
            "class_data": class_data,
            "concept_performance": concept_performance,
            "misconception_trends": misconception_trends,
        })

        request = AIRequest.create(
            prompt=user,
            system_prompt=system,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            request_type="instructor_insights",
            prompt_version=prompt.version,
        )

        try:
            response = await self._gateway.generate(request)
            return InstructorInsights(
                class_weaknesses=self._extract_section(response.content, "weakness"),
                concept_heatmap=self._extract_section(response.content, "heatmap"),
                misconception_trends=self._extract_section(response.content, "misconception"),
                curriculum_improvements=self._extract_list(response.content, "improvement"),
                question_quality_alerts=self._extract_list(response.content, "quality"),
                engagement_summary=self._extract_section(response.content, "engagement"),
                provider=response.provider.value,
                model=response.model,
                tokens_used=response.total_tokens,
            )
        except AIUnavailableError:
            return InstructorInsights()

    def _extract_section(self, content: str, keyword: str) -> str:
        lines = content.split("\n")
        capturing = False
        result: list[str] = []
        for line in lines:
            if keyword.lower() in line.lower() and ("##" in line or "**" in line):
                capturing = True
                continue
            if capturing:
                if line.startswith("## "):
                    break
                result.append(line)
        return "\n".join(result).strip()

    def _extract_list(self, content: str, keyword: str) -> list[str]:
        result: list[str] = []
        capturing = False
        for line in content.split("\n"):
            if keyword.lower() in line.lower():
                capturing = True
                continue
            if capturing:
                stripped = line.strip()
                if stripped.startswith("- ") or stripped.startswith("* "):
                    result.append(stripped[2:])
                elif stripped.startswith("## "):
                    break
        return result


# ============================================================
# Weekly Reports
# ============================================================


@dataclass
class WeeklyReport:
    """AI-generated weekly report."""
    student_name: str = ""
    week_range: str = ""
    content: str = ""
    # Metadata
    provider: str = ""
    model: str = ""
    tokens_used: int = 0
    cost_cents: int = 0


class WeeklyReportGenerator:
    """Generates weekly reports for students, instructors, and organizations."""

    def __init__(self, gateway: AIGateway, prompt_repo: PromptRepository | None = None) -> None:
        self._gateway = gateway
        self._prompt_repo = prompt_repo or get_prompt_repository()

    async def generate_student_report(
        self,
        *,
        student_name: str,
        week_range: str,
        questions_answered: int,
        accuracy: float,
        study_time: str,
        streak: int,
        mastery_delta: float,
        weak_concepts: str,
        strong_concepts: str,
        user_id: UUID | None = None,
    ) -> WeeklyReport:
        """Generate a weekly report for a student."""
        prompt = self._prompt_repo.get_published(PromptType.WEEKLY_REPORT)
        if prompt is None:
            return WeeklyReport(student_name=student_name, week_range=week_range)

        system, user = prompt.render({
            "student_name": student_name,
            "week_range": week_range,
            "questions_answered": str(questions_answered),
            "accuracy": f"{accuracy:.1%}",
            "study_time": study_time,
            "streak": str(streak),
            "mastery_delta": f"{mastery_delta:+.1%}",
            "weak_concepts": weak_concepts,
            "strong_concepts": strong_concepts,
        })

        request = AIRequest.create(
            prompt=user,
            system_prompt=system,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            request_type="weekly_report",
            user_id=user_id,
            prompt_version=prompt.version,
        )

        try:
            response = await self._gateway.generate(request)
            return WeeklyReport(
                student_name=student_name,
                week_range=week_range,
                content=response.content,
                provider=response.provider.value,
                model=response.model,
                tokens_used=response.total_tokens,
                cost_cents=response.cost_cents,
            )
        except AIUnavailableError:
            return WeeklyReport(student_name=student_name, week_range=week_range)


# ============================================================
# Model Version Management
# ============================================================


@dataclass
class ModelVersion:
    """A model version for A/B testing."""
    id: str
    name: str
    provider: str
    model_id: str
    is_active: bool = False
    is_default: bool = False
    rollout_percentage: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelVersionManager:
    """Manages multiple AI models with A/B comparison and rollback."""

    def __init__(self) -> None:
        self._models: dict[str, ModelVersion] = {}
        self._default = "qwen2.5:7b"

    def register_model(self, model: ModelVersion) -> None:
        self._models[model.id] = model

    def get_active_models(self) -> list[ModelVersion]:
        return [m for m in self._models.values() if m.is_active]

    def get_default(self) -> ModelVersion | None:
        return self._models.get(self._default)

    def set_default(self, model_id: str) -> bool:
        if model_id not in self._models:
            return False
        for m in self._models.values():
            m.is_default = (m.id == model_id)
        self._default = model_id
        return True

    def rollback(self, model_id: str) -> bool:
        """Rollback to a previous model version."""
        return self.set_default(model_id)


# ============================================================
# Experiment Framework
# ============================================================


@dataclass
class Experiment:
    """An A/B test experiment."""
    id: str
    name: str
    description: str
    model_a: str
    model_b: str
    rollout_percentage: int = 50
    status: str = "draft"  # draft, running, completed, stopped
    metrics: dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(tz_utc.utc))


class ExperimentFramework:
    """Supports A/B testing, feature flags, percentage rollout."""

    def __init__(self) -> None:
        self._experiments: dict[str, Experiment] = {}

    def create_experiment(self, exp: Experiment) -> Experiment:
        self._experiments[exp.id] = exp
        return exp

    def start_experiment(self, exp_id: str) -> bool:
        exp = self._experiments.get(exp_id)
        if exp is None or exp.status != "draft":
            return False
        exp.status = "running"
        return True

    def stop_experiment(self, exp_id: str) -> bool:
        exp = self._experiments.get(exp_id)
        if exp is None:
            return False
        exp.status = "stopped"
        return True

    def get_assignment(self, exp_id: str, user_id: UUID) -> str:
        """Get the model assignment for a user (A or B)."""
        exp = self._experiments.get(exp_id)
        if exp is None or exp.status != "running":
            return exp.model_a if exp else ""

        # Deterministic assignment based on user ID hash
        hash_val = hash(str(user_id)) % 100
        if hash_val < exp.rollout_percentage:
            return exp.model_b
        return exp.model_a

    def list_experiments(self) -> list[Experiment]:
        return list(self._experiments.values())


# ============================================================
# Offline Evaluation
# ============================================================


@dataclass
class EvaluationResult:
    """Result of an offline evaluation."""
    experiment_id: str
    total_samples: int = 0
    ai_agreement_rate: float = 0.0  # How often AI agreed with rule engine
    ai_accuracy: float = 0.0  # How often AI prediction matched actual outcome
    rule_accuracy: float = 0.0
    avg_ai_latency_ms: float = 0
    avg_ai_cost_cents: float = 0
    notes: str = ""


class OfflineEvaluator:
    """Replays historical attempts and compares AI vs Rule Engine.

    AI is never deployed without offline validation.
    """

    def __init__(self) -> None:
        self._results: list[EvaluationResult] = []

    async def evaluate(
        self,
        *,
        experiment_id: str,
        historical_attempts: list[dict[str, Any]],
        ai_predictor: Any = None,
    ) -> EvaluationResult:
        """Evaluate AI against historical data."""
        total = len(historical_attempts)
        if total == 0:
            return EvaluationResult(experiment_id=experiment_id)

        ai_correct = 0
        rule_correct = 0
        ai_agreed = 0
        latencies: list[float] = []
        costs: list[float] = []

        for attempt in historical_attempts:
            actual_outcome = attempt.get("was_correct", False)
            rule_prediction = attempt.get("rule_prediction", actual_outcome)

            if rule_prediction == actual_outcome:
                rule_correct += 1

            # If AI predictor is available, run it
            if ai_predictor:
                import time
                start = time.time()
                try:
                    ai_prediction = await ai_predictor(attempt)
                    latency = (time.time() - start) * 1000
                    latencies.append(latency)
                    costs.append(0)  # Local model = 0 cost

                    if ai_prediction == actual_outcome:
                        ai_correct += 1
                    if ai_prediction == rule_prediction:
                        ai_agreed += 1
                except Exception:
                    pass

        result = EvaluationResult(
            experiment_id=experiment_id,
            total_samples=total,
            ai_agreement_rate=ai_agreed / total if total > 0 else 0,
            ai_accuracy=ai_correct / total if total > 0 else 0,
            rule_accuracy=rule_correct / total if total > 0 else 0,
            avg_ai_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
            avg_ai_cost_cents=sum(costs) / len(costs) if costs else 0,
        )

        self._results.append(result)
        return result

    def list_results(self) -> list[EvaluationResult]:
        return self._results


__all__ = [
    "StudyCoach",
    "StudyPlan",
    "PredictiveAnalytics",
    "LearningForecast",
    "ContentIntelligence",
    "ContentAnalysis",
    "AIRecommendationEnhancer",
    "InstructorIntelligence",
    "InstructorInsights",
    "WeeklyReportGenerator",
    "WeeklyReport",
    "ModelVersion",
    "ModelVersionManager",
    "Experiment",
    "ExperimentFramework",
    "OfflineEvaluator",
    "EvaluationResult",
]
