"""AI API endpoints — exposes the AI Intelligence Platform via REST API.

All endpoints are optional — if AI is disabled, they return 503.
The Rule Engine remains the authoritative source.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.ai import AIConfig, AIProviderType, get_ai_config, set_ai_config
from app.ai.gateway import get_gateway, reset_gateway
from app.ai.prompts import PromptRepository, PromptType, PromptStatus, get_prompt_repository
from app.ai.audit import get_audit_logger
from app.ai.explanations import ExplanationGenerator, ExplanationReviewService
from app.ai.coach import (
    StudyCoach, PredictiveAnalytics, ContentIntelligence,
    AIRecommendationEnhancer, InstructorIntelligence,
    WeeklyReportGenerator, ModelVersionManager, ExperimentFramework,
    OfflineEvaluator,
)
from app.presentation.dependencies import get_current_user_id

router = APIRouter(prefix="/ai", tags=["AI Intelligence"])


# ============================================================
# Request/Response Models
# ============================================================


class AIStatusResponse(BaseModel):
    enabled: bool
    available_providers: list[dict[str, Any]]
    default_provider: str
    metrics: dict[str, Any]


class GenerateExplanationRequest(BaseModel):
    attempt_id: UUID
    question_prompt: str
    student_answer: str
    correct_answer: str
    question_type: str = "multiple_choice"
    difficulty: str = "medium"
    concept_name: str = ""
    misconception: str | None = None
    mastery_score: float = 0.0


class StudyPlanRequest(BaseModel):
    mastery_data: str
    recent_attempts: str
    streak: int = 0
    daily_goal: float = 0.5
    available_time: str = "30 minutes"


class ForecastRequest(BaseModel):
    learner_stats: dict[str, Any] = Field(default_factory=dict)


class ContentAnalysisRequest(BaseModel):
    templates_data: str
    concepts_data: str = ""
    misconceptions_data: str = ""


class EnhanceRecommendationRequest(BaseModel):
    recommendation_type: str
    concept_name: str
    reason: str
    mastery_score: float = 0.0
    recent_activity: str = ""


class WeeklyReportRequest(BaseModel):
    student_name: str
    week_range: str
    questions_answered: int = 0
    accuracy: float = 0.0
    study_time: str = "0 minutes"
    streak: int = 0
    mastery_delta: float = 0.0
    weak_concepts: str = ""
    strong_concepts: str = ""


class InstructorInsightsRequest(BaseModel):
    class_data: str
    concept_performance: str
    misconception_trends: str


class PromptResponse(BaseModel):
    id: str
    prompt_type: str
    version: str
    name: str
    description: str
    status: str
    owner: str


class UpdateAIConfigRequest(BaseModel):
    enabled: bool | None = None
    default_provider: str | None = None
    ollama_host: str | None = None
    ollama_model: str | None = None
    ai_timeout: int | None = None
    temperature: float | None = None


class MessageResponse(BaseModel):
    message: str
    code: str = "OK"


# ============================================================
# AI Status & Configuration
# ============================================================


@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status() -> AIStatusResponse:
    """Get AI platform status."""
    config = get_ai_config()
    gateway = get_gateway()
    return AIStatusResponse(
        enabled=config.enabled,
        available_providers=gateway.get_available_providers(),
        default_provider=config.default_provider.value,
        metrics=gateway.get_metrics_dict(),
    )


@router.patch("/config", response_model=MessageResponse)
async def update_ai_config(
    request: UpdateAIConfigRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> MessageResponse:
    """Update AI configuration (admin only)."""
    config = get_ai_config()
    if request.enabled is not None:
        config.enabled = request.enabled
    if request.default_provider is not None:
        config.default_provider = AIProviderType(request.default_provider)
    if request.ollama_host is not None:
        config.ollama_host = request.ollama_host
    if request.ollama_model is not None:
        config.ollama_model = request.ollama_model
    if request.ai_timeout is not None:
        config.ai_timeout = request.ai_timeout
    if request.temperature is not None:
        config.temperature = request.temperature

    set_ai_config(config)
    reset_gateway()  # Recreate gateway with new config
    return MessageResponse(message="AI configuration updated")


# ============================================================
# AI Explanations
# ============================================================


@router.post("/explanations/generate")
async def generate_explanation(
    request: GenerateExplanationRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Generate an AI explanation for a submitted answer."""
    config = get_ai_config()
    if not config.enabled:
        raise HTTPException(503, detail={"code": "AI_DISABLED", "message": "AI is not enabled"})

    gateway = get_gateway()
    generator = ExplanationGenerator(gateway)
    explanation = await generator.generate(
        attempt_id=request.attempt_id,
        question_prompt=request.question_prompt,
        student_answer=request.student_answer,
        correct_answer=request.correct_answer,
        question_type=request.question_type,
        difficulty=request.difficulty,
        concept_name=request.concept_name,
        misconception=request.misconception,
        mastery_score=request.mastery_score,
        user_id=user_id,
    )
    return {
        "id": str(explanation.id),
        "approval_state": explanation.approval_state.value,
        "content": explanation.display_content,
        "provider": explanation.provider,
        "model": explanation.model,
        "confidence": explanation.confidence,
        "tokens_used": explanation.tokens_used,
        "is_published": explanation.is_published,
    }


# ============================================================
# Study Coach
# ============================================================


@router.post("/coach/plan")
async def generate_study_plan(
    request: StudyPlanRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Generate a personalized study plan."""
    config = get_ai_config()
    if not config.enabled:
        raise HTTPException(503, detail={"code": "AI_DISABLED"})

    gateway = get_gateway()
    coach = StudyCoach(gateway)
    plan = await coach.generate_plan(
        user_id=user_id,
        mastery_data=request.mastery_data,
        recent_attempts=request.recent_attempts,
        streak=request.streak,
        daily_goal=request.daily_goal,
        available_time=request.available_time,
    )
    return {
        "daily_plan": plan.daily_plan,
        "weekly_plan": plan.weekly_plan,
        "motivation": plan.motivation,
        "study_tips": plan.study_tips,
        "weakness_summary": plan.weakness_summary,
        "next_objectives": plan.next_objectives,
        "time_recommendations": plan.time_recommendations,
        "provider": plan.provider,
        "model": plan.model,
    }


# ============================================================
# Predictive Analytics
# ============================================================


@router.post("/analytics/forecast")
async def generate_forecast(
    request: ForecastRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Generate learning forecasts."""
    config = get_ai_config()
    if not config.enabled:
        raise HTTPException(503, detail={"code": "AI_DISABLED"})

    gateway = get_gateway()
    analytics = PredictiveAnalytics(gateway)
    forecast = await analytics.forecast(
        user_id=user_id,
        learner_stats=request.learner_stats,
    )
    return {
        "dropout_probability": forecast.dropout_probability,
        "dropout_confidence": forecast.dropout_confidence,
        "completion_probability": forecast.completion_probability,
        "completion_confidence": forecast.completion_confidence,
        "mastery_forecast": forecast.mastery_forecast,
        "mastery_confidence": forecast.mastery_confidence,
        "interview_readiness_forecast": forecast.interview_readiness_forecast,
        "interview_confidence": forecast.interview_confidence,
        "study_consistency_score": forecast.study_consistency_score,
        "future_review_load": forecast.future_review_load,
    }


# ============================================================
# Content Intelligence
# ============================================================


@router.post("/content/analyze")
async def analyze_content(
    request: ContentAnalysisRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Analyze content quality."""
    config = get_ai_config()
    if not config.enabled:
        raise HTTPException(503, detail={"code": "AI_DISABLED"})

    gateway = get_gateway()
    intelligence = ContentIntelligence(gateway)
    analysis = await intelligence.analyze_content(
        templates_data=request.templates_data,
        concepts_data=request.concepts_data,
        misconceptions_data=request.misconceptions_data,
    )
    return {
        "duplicate_templates": analysis.duplicate_templates,
        "unclear_explanations": analysis.unclear_explanations,
        "weak_distractors": analysis.weak_distractors,
        "unused_misconceptions": analysis.unused_misconceptions,
        "difficulty_imbalance": analysis.difficulty_imbalance,
        "missing_objectives": analysis.missing_objectives,
        "coverage_gaps": analysis.coverage_gaps,
        "improvement_suggestions": analysis.improvement_suggestions,
        "provider": analysis.provider,
    }


# ============================================================
# Recommendation Enhancement
# ============================================================


@router.post("/recommendations/enhance")
async def enhance_recommendation(
    request: EnhanceRecommendationRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Enhance a rule-based recommendation with natural language."""
    config = get_ai_config()
    if not config.enabled:
        return {"enhanced_text": request.reason}  # Fallback to original

    gateway = get_gateway()
    enhancer = AIRecommendationEnhancer(gateway)
    enhanced = await enhancer.enhance(
        recommendation_type=request.recommendation_type,
        concept_name=request.concept_name,
        reason=request.reason,
        mastery_score=request.mastery_score,
        recent_activity=request.recent_activity,
        user_id=user_id,
    )
    return {"enhanced_text": enhanced}


# ============================================================
# Weekly Reports
# ============================================================


@router.post("/reports/weekly")
async def generate_weekly_report(
    request: WeeklyReportRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Generate a weekly report."""
    config = get_ai_config()
    if not config.enabled:
        raise HTTPException(503, detail={"code": "AI_DISABLED"})

    gateway = get_gateway()
    generator = WeeklyReportGenerator(gateway)
    report = await generator.generate_student_report(
        student_name=request.student_name,
        week_range=request.week_range,
        questions_answered=request.questions_answered,
        accuracy=request.accuracy,
        study_time=request.study_time,
        streak=request.streak,
        mastery_delta=request.mastery_delta,
        weak_concepts=request.weak_concepts,
        strong_concepts=request.strong_concepts,
        user_id=user_id,
    )
    return {
        "student_name": report.student_name,
        "week_range": report.week_range,
        "content": report.content,
        "provider": report.provider,
        "model": report.model,
    }


# ============================================================
# Instructor Intelligence
# ============================================================


@router.post("/instructor/insights")
async def generate_instructor_insights(
    request: InstructorInsightsRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Generate instructor insights."""
    config = get_ai_config()
    if not config.enabled:
        raise HTTPException(503, detail={"code": "AI_DISABLED"})

    gateway = get_gateway()
    intelligence = InstructorIntelligence(gateway)
    insights = await intelligence.generate_insights(
        class_data=request.class_data,
        concept_performance=request.concept_performance,
        misconception_trends=request.misconception_trends,
    )
    return {
        "class_weaknesses": insights.class_weaknesses,
        "concept_heatmap": insights.concept_heatmap,
        "misconception_trends": insights.misconception_trends,
        "curriculum_improvements": insights.curriculum_improvements,
        "question_quality_alerts": insights.question_quality_alerts,
        "engagement_summary": insights.engagement_summary,
        "provider": insights.provider,
    }


# ============================================================
# Prompt Management
# ============================================================


@router.get("/prompts", response_model=list[PromptResponse])
async def list_prompts(
    user_id: UUID = Depends(get_current_user_id),
) -> list[PromptResponse]:
    """List all AI prompts."""
    repo = get_prompt_repository()
    return [
        PromptResponse(
            id=str(p.id),
            prompt_type=p.prompt_type.value,
            version=p.version,
            name=p.name,
            description=p.description,
            status=p.status.value,
            owner=p.owner,
        )
        for p in repo.list_all()
    ]


@router.get("/prompts/{prompt_type}")
async def get_prompt_by_type(
    prompt_type: str,
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Get published prompt by type."""
    repo = get_prompt_repository()
    try:
        ptype = PromptType(prompt_type)
    except ValueError:
        raise HTTPException(404, detail="Unknown prompt type")

    prompt = repo.get_published(ptype)
    if prompt is None:
        raise HTTPException(404, detail="No published prompt for this type")

    return {
        "id": str(prompt.id),
        "prompt_type": prompt.prompt_type.value,
        "version": prompt.version,
        "name": prompt.name,
        "description": prompt.description,
        "system_prompt": prompt.system_prompt,
        "user_prompt_template": prompt.user_prompt_template,
        "variables": prompt.variables,
        "temperature": prompt.temperature,
        "max_tokens": prompt.max_tokens,
        "status": prompt.status.value,
    }


# ============================================================
# Audit Logs
# ============================================================


@router.get("/audit")
async def list_audit_logs(
    limit: int = 100,
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, Any]:
    """List AI audit log entries."""
    audit = get_audit_logger()
    entries = await audit.list_entries(limit=limit)
    return {
        "entries": [e.to_dict() for e in entries],
        "stats": await audit.get_stats(),
    }


# ============================================================
# Gateway Metrics
# ============================================================


@router.get("/metrics")
async def get_ai_metrics(
    user_id: UUID = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Get AI gateway metrics."""
    gateway = get_gateway()
    return gateway.get_metrics_dict()


__all__ = ["router"]
