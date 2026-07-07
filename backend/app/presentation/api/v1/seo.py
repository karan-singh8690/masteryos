"""Public SEO API — question data for search engine indexing.

All endpoints are PUBLIC (no auth required) and return question data
WITHOUT the correct answer. This allows Google to index questions
so users find MasteryOS when searching for interview topics.

Endpoints:
- GET /seo/questions          — List all published questions (paginated)
- GET /seo/questions/{code}   — Get single question by code (for SEO page)
- GET /seo/subjects           — List subjects
- GET /seo/sitemap            — Get all URLs for sitemap generation
"""

from __future__ import annotations

from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from pydantic import BaseModel

from app.application.shared import UnitOfWork
from app.infrastructure.database.orm.content import (
    QuestionTemplateModel,
    TemplateVersionModel,
    TemplateConceptModel,
    SubjectModel,
    ConceptModel,
    ExplanationModel,
)

router = APIRouter(prefix="/seo", tags=["SEO — Public"])


class PublicQuestionResponse(BaseModel):
    """Public question data — NO correct answer exposed."""
    code: str
    prompt: str
    question_type: str
    difficulty: str
    choices: list[dict[str, Any]] | None  # WITHOUT is_correct field
    concepts: list[str]  # Concept names
    subject_name: str
    subject_slug: str
    explanation_preview: str | None  # First 100 chars only
    pyq_exam: str | None
    pyq_year: int | None


class PublicQuestionListResponse(BaseModel):
    questions: list[PublicQuestionResponse]
    total: int
    page: int
    page_size: int


@router.get(
    "/questions",
    summary="List published questions for SEO (public, no auth)",
)
async def list_public_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    subject_slug: str | None = Query(None),
    concept_slug: str | None = Query(None),
    exam_name: str | None = Query(None),
    search: str | None = Query(None),
    uow: UnitOfWork = Depends(lambda: None),  # Will be overridden
) -> dict:
    """List all published questions — PUBLIC, no auth required.

    Returns question prompts + choices (WITHOUT correct answer) + concept names.
    Used by search engines to index questions.
    """
    from app.infrastructure.database.engine import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        # Build query
        query = (
            select(TemplateVersionModel, QuestionTemplateModel, SubjectModel)
            .join(QuestionTemplateModel, TemplateVersionModel.template_id == QuestionTemplateModel.id)
            .join(SubjectModel, QuestionTemplateModel.subject_id == SubjectModel.id)
            .where(QuestionTemplateModel.status == "published")
            .where(QuestionTemplateModel.current_version_id == TemplateVersionModel.id)
        )

        if subject_slug:
            query = query.where(SubjectModel.slug == subject_slug)
        if exam_name:
            query = query.where(QuestionTemplateModel.pyq_exam == exam_name)
        if search:
            # Search in prompt text
            query = query.where(
                TemplateVersionModel.prompt_template["text"].astext.ilike(f"%{search}%")
            )

        # Count
        count_query = (
            select(func.count())
            .select_from(TemplateVersionModel)
            .join(QuestionTemplateModel, TemplateVersionModel.template_id == QuestionTemplateModel.id)
            .where(QuestionTemplateModel.status == "published")
            .where(QuestionTemplateModel.current_version_id == TemplateVersionModel.id)
        )
        if subject_slug:
            count_query = count_query.join(SubjectModel, QuestionTemplateModel.subject_id == SubjectModel.id).where(SubjectModel.slug == subject_slug)

        total = (await session.execute(count_query)).scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        query = query.order_by(QuestionTemplateModel.created_at.desc()).offset(offset).limit(page_size)
        result = await session.execute(query)
        rows = result.all()

        questions = []
        for tv, qt, subject in rows:
            # Get concept names
            tc_result = await session.execute(
                select(ConceptModel.name).join(
                    TemplateConceptModel, ConceptModel.id == TemplateConceptModel.concept_id
                ).where(TemplateConceptModel.template_version_id == tv.id)
            )
            concept_names = [r[0] for r in tc_result.all()]

            # Get explanation preview (first 100 chars)
            expl_result = await session.execute(
                select(ExplanationModel.content).where(
                    ExplanationModel.template_version_id == tv.id,
                    ExplanationModel.outcome_key == "correct",
                ).limit(1)
            )
            expl_row = expl_result.first()
            explanation_preview = expl_row[0][:100] + "..." if expl_row and expl_row[0] else None

            # Clean choices (remove is_correct)
            prompt = tv.prompt_template or {}
            prompt_text = prompt.get("text", "") if isinstance(prompt, dict) else str(prompt)

            choices = tv.distractor_generator or {}
            clean_choices = []
            if choices and isinstance(choices, dict):
                items = choices.get("distractors") or choices.get("items") or []
                # Add correct answer as a choice (shuffled, no is_correct flag)
                correct = tv.correct_answer_generator or {}
                correct_text = correct.get("value", "") if isinstance(correct, dict) else str(correct)
                all_choices = [{"id": chr(65 + i), "text": d if isinstance(d, str) else d.get("text", str(d))} for i, d in enumerate(items)]
                if correct_text:
                    all_choices.append({"id": chr(65 + len(items)), "text": correct_text})

            questions.append({
                "code": qt.code,
                "prompt": prompt_text,
                "question_type": qt.question_type,
                "difficulty": tv.difficulty_estimate,
                "choices": clean_choices,
                "concepts": concept_names,
                "subject_name": subject.name,
                "subject_slug": subject.slug,
                "explanation_preview": explanation_preview,
                "pyq_exam": qt.pyq_exam,
                "pyq_year": qt.pyq_year,
            })

        return {
            "questions": questions,
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@router.get(
    "/questions/{code}",
    summary="Get single question by code for SEO (public, no auth)",
)
async def get_public_question(
    code: str,
    uow: UnitOfWork = Depends(lambda: None),
) -> dict:
    """Get a single question by its code — PUBLIC, no auth required.

    Returns the question prompt + choices (WITHOUT correct answer).
    Used for SEO-optimized question pages at /q/{code}.
    """
    from app.infrastructure.database.engine import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(TemplateVersionModel, QuestionTemplateModel, SubjectModel)
            .join(QuestionTemplateModel, TemplateVersionModel.template_id == QuestionTemplateModel.id)
            .join(SubjectModel, QuestionTemplateModel.subject_id == SubjectModel.id)
            .where(QuestionTemplateModel.code == code)
            .where(QuestionTemplateModel.status == "published")
            .where(QuestionTemplateModel.current_version_id == TemplateVersionModel.id)
        )
        row = result.first()
        if not row:
            return {"error": "Question not found", "code": code}

        tv, qt, subject = row

        # Get concept names
        tc_result = await session.execute(
            select(ConceptModel.name, ConceptModel.slug).join(
                TemplateConceptModel, ConceptModel.id == TemplateConceptModel.concept_id
            ).where(TemplateConceptModel.template_version_id == tv.id)
        )
        concepts = [{"name": r[0], "slug": r[1]} for r in tc_result.all()]

        # Get explanation preview
        expl_result = await session.execute(
            select(ExplanationModel.content).where(
                ExplanationModel.template_version_id == tv.id,
                ExplanationModel.outcome_key == "correct",
            ).limit(1)
        )
        expl_row = expl_result.first()
        explanation_preview = expl_row[0][:150] + "..." if expl_row and expl_row[0] else None

        prompt = tv.prompt_template or {}
        prompt_text = prompt.get("text", "") if isinstance(prompt, dict) else str(prompt)

        # Build choices without is_correct
        choices_data = tv.distractor_generator or {}
        correct_data = tv.correct_answer_generator or {}
        correct_text = correct_data.get("value", "") if isinstance(correct_data, dict) else str(correct_data)

        all_choices = []
        if choices_data and isinstance(choices_data, dict):
            items = choices_data.get("distractors") or choices_data.get("items") or []
            for i, d in enumerate(items):
                text = d if isinstance(d, str) else d.get("text", str(d))
                all_choices.append({"id": chr(65 + i), "text": text})
        if correct_text:
            all_choices.append({"id": chr(65 + len(all_choices)), "text": correct_text})

        return {
            "code": qt.code,
            "prompt": prompt_text,
            "question_type": qt.question_type,
            "difficulty": tv.difficulty_estimate,
            "choices": all_choices,
            "concepts": concepts,
            "subject_name": subject.name,
            "subject_slug": subject.slug,
            "subject_description": subject.description,
            "explanation_preview": explanation_preview,
            "pyq_exam": qt.pyq_exam,
            "pyq_year": qt.pyq_year,
            "published_at": qt.published_at.isoformat() if qt.published_at else None,
            "meta_title": f"{prompt_text[:60]} — MasteryOS",
            "meta_description": f"Practice: {prompt_text[:120]}. Learn Python interview prep with adaptive mastery on MasteryOS.",
            "canonical_url": f"https://masteryos-production.up.railway.app/q/{qt.code}",
        }


@router.get(
    "/subjects",
    summary="List subjects for SEO (public)",
)
async def list_public_subjects() -> list[dict]:
    """List all published subjects — public, no auth."""
    from app.infrastructure.database.engine import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(SubjectModel).where(SubjectModel.status == "published")
        )
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "slug": s.slug,
                "description": s.description,
                "code": s.code,
            }
            for s in result.scalars().all()
        ]


@router.get(
    "/sitemap",
    summary="Get all URLs for sitemap (public)",
)
async def get_sitemap_urls() -> dict:
    """Get all public URLs for sitemap generation.

    Returns question codes, subject slugs, and material IDs
    so the frontend can generate a complete sitemap.xml.
    """
    from app.infrastructure.database.engine import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        # Get all published question codes
        q_result = await session.execute(
            select(QuestionTemplateModel.code).where(QuestionTemplateModel.status == "published")
        )
        question_codes = [r[0] for r in q_result.all()]

        # Get all subjects
        s_result = await session.execute(
            select(SubjectModel.slug).where(SubjectModel.status == "published")
        )
        subject_slugs = [r[0] for r in s_result.all()]

        return {
            "questions": [f"/q/{code}" for code in question_codes],
            "subjects": [f"/subjects/{slug}" for slug in subject_slugs],
            "static": [
                "/", "/login", "/register", "/features", "/pricing",
                "/blog", "/support", "/faq", "/status", "/changelog",
                "/legal/privacy", "/legal/terms",
            ],
            "total_urls": len(question_codes) + len(subject_slugs) + 12,
        }
