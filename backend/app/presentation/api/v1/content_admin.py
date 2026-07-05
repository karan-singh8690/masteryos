"""Content Administration API — CRUD for subjects, concepts, templates.

These endpoints allow an administrator to build an entire curriculum
without touching code. Everything is data.

Endpoints:
- POST /api/v1/admin/subjects — Create a subject
- POST /api/v1/admin/subjects/{id}/concepts — Create a concept
- POST /api/v1/admin/concepts/{id}/objectives — Create a learning objective
- POST /api/v1/admin/concepts/{id}/misconceptions — Create a misconception
- POST /api/v1/admin/subjects/{id}/question-templates — Create a question template
- POST /api/v1/admin/question-templates/{id}/publish — Publish a template
- GET  /api/v1/admin/subjects — List subjects
- GET  /api/v1/admin/subjects/{id}/concepts — List concepts
- GET  /api/v1/admin/subjects/{id}/question-templates — List templates
- GET  /api/v1/admin/question-templates/{id} — Get template detail
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.shared import UnitOfWork
from app.domain.shared.kernel import ContentStatus, Difficulty, Importance, QuestionType
from app.infrastructure.database.orm.content import (
    ConceptModel,
    ContentPackModel,
    ContentVersionModel,
    ExplanationModel,
    LearningObjectiveModel,
    MisconceptionModel,
    QuestionTemplateModel,
    SubjectModel,
    TemplateConceptModel,
    TemplateVersionModel,
)
from app.presentation.dependencies import get_current_user_id, get_uow, require_any_role
from app.infrastructure.security.authorization import (
    ROLE_ADMINISTRATOR,
    ROLE_SYSTEM_ADMIN,
    ROLE_CONTENT_EDITOR,
    ROLE_INSTRUCTOR,
)

router = APIRouter(
    prefix="/admin",
    tags=["Content Administration"],
    dependencies=[
        Depends(get_current_user_id),
        Depends(require_any_role(
            ROLE_ADMINISTRATOR,
            ROLE_SYSTEM_ADMIN,
            ROLE_CONTENT_EDITOR,
            ROLE_INSTRUCTOR,
        )),
    ],
)


# ============================================================
# Request Models
# ============================================================


class CreateSubjectRequest(BaseModel):
    code: str
    name: str
    slug: str
    description: str | None = None


class CreateConceptRequest(BaseModel):
    slug: str
    name: str
    description: str
    difficulty: str = "medium"
    importance: str = "medium"


class CreateObjectiveRequest(BaseModel):
    statement: str


class CreateMisconceptionRequest(BaseModel):
    name: str
    description: str
    remediation: str | None = None


class CreateQuestionTemplateRequest(BaseModel):
    code: str
    question_type: str = "multiple_choice"
    # Template version data:
    prompt_template: dict[str, Any]
    parameter_schema: dict[str, Any] = Field(default_factory=dict)
    correct_answer_generator: dict[str, Any]
    distractor_generator: dict[str, Any] | None = None
    explanation_template: dict[str, Any] = Field(default_factory=dict)
    hint_tiers: list[str] = Field(default_factory=list)
    difficulty_estimate: str = "medium"
    discrimination_estimate: float = 0.5
    concept_ids: list[UUID] = Field(default_factory=list)
    explanations: list[dict[str, str]] = Field(default_factory=list)


class PublishTemplateRequest(BaseModel):
    pass  # No body needed; just the action


# ============================================================
# Response Models
# ============================================================


class SubjectResponse(BaseModel):
    id: UUID
    code: str
    name: str
    slug: str
    description: str | None
    status: str
    published_at: str | None


class ConceptResponse(BaseModel):
    id: UUID
    subject_id: UUID
    slug: str
    name: str
    description: str
    difficulty: str
    importance: str
    status: str


class ObjectiveResponse(BaseModel):
    id: UUID
    concept_id: UUID
    statement: str
    status: str


class MisconceptionResponse(BaseModel):
    id: UUID
    concept_id: UUID
    name: str
    description: str
    remediation: str | None
    status: str


class QuestionTemplateResponse(BaseModel):
    id: UUID
    subject_id: UUID
    code: str
    question_type: str
    status: str
    current_version_id: UUID | None


class TemplateVersionResponse(BaseModel):
    id: UUID
    template_id: UUID
    version_number: int
    prompt_template: dict[str, Any]
    difficulty_estimate: str
    concept_ids: list[UUID]


# ============================================================
# Endpoints
# ============================================================


@router.post("/subjects", response_model=SubjectResponse, status_code=201)
async def create_subject(
    request: CreateSubjectRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> SubjectResponse:
    """Create a new subject (tenant)."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]

        subject = SubjectModel(
            id=uuid4(),
            tenant_id=uuid4(),  # 1:1 with subject for now
            code=request.code,
            name=request.name,
            slug=request.slug,
            description=request.description,
            status="draft",
        )
        session.add(subject)
        await session.commit()
        await session.refresh(subject)

        return SubjectResponse(
            id=subject.id,
            code=subject.code,
            name=subject.name,
            slug=subject.slug,
            description=subject.description,
            status=subject.status,
            published_at=subject.published_at.isoformat() if subject.published_at else None,
        )


@router.post("/subjects/{subject_id}/publish", response_model=SubjectResponse)
async def publish_subject(
    subject_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> SubjectResponse:
    """Publish a subject — makes it available for enrollment."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        subject = await session.get(SubjectModel, subject_id)
        if subject is None:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Subject not found"})

        subject.status = "published"
        subject.published_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(subject)

        return SubjectResponse(
            id=subject.id, code=subject.code, name=subject.name, slug=subject.slug,
            description=subject.description, status=subject.status,
            published_at=subject.published_at.isoformat() if subject.published_at else None,
        )


@router.get("/subjects", response_model=list[SubjectResponse])
async def list_subjects(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[SubjectResponse]:
    """List all subjects."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await session.execute(select(SubjectModel))
        subjects = result.scalars().all()
        return [
            SubjectResponse(
                id=s.id, code=s.code, name=s.name, slug=s.slug,
                description=s.description, status=s.status,
                published_at=s.published_at.isoformat() if s.published_at else None,
            )
            for s in subjects
        ]


@router.post("/subjects/{subject_id}/concepts", response_model=ConceptResponse, status_code=201)
async def create_concept(
    subject_id: UUID,
    request: CreateConceptRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> ConceptResponse:
    """Create a concept within a subject."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]

        # Verify subject exists
        subject = await session.get(SubjectModel, subject_id)
        if subject is None:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Subject not found"})

        concept = ConceptModel(
            id=uuid4(),
            subject_id=subject_id,
            slug=request.slug,
            name=request.name,
            description=request.description,
            difficulty=request.difficulty,
            importance=request.importance,
            status="draft",
        )
        session.add(concept)
        await session.commit()
        await session.refresh(concept)

        return ConceptResponse(
            id=concept.id, subject_id=concept.subject_id, slug=concept.slug,
            name=concept.name, description=concept.description,
            difficulty=concept.difficulty, importance=concept.importance,
            status=concept.status,
        )


@router.post("/concepts/{concept_id}/objectives", response_model=ObjectiveResponse, status_code=201)
async def create_objective(
    concept_id: UUID,
    request: CreateObjectiveRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> ObjectiveResponse:
    """Create a learning objective for a concept."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        obj = LearningObjectiveModel(
            id=uuid4(), concept_id=concept_id, statement=request.statement, status="draft",
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return ObjectiveResponse(id=obj.id, concept_id=obj.concept_id, statement=obj.statement, status=obj.status)


@router.post("/concepts/{concept_id}/misconceptions", response_model=MisconceptionResponse, status_code=201)
async def create_misconception(
    concept_id: UUID,
    request: CreateMisconceptionRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> MisconceptionResponse:
    """Create a misconception for a concept."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        mis = MisconceptionModel(
            id=uuid4(), concept_id=concept_id, name=request.name,
            description=request.description, remediation=request.remediation, status="draft",
        )
        session.add(mis)
        await session.commit()
        await session.refresh(mis)
        return MisconceptionResponse(
            id=mis.id, concept_id=mis.concept_id, name=mis.name,
            description=mis.description, remediation=mis.remediation, status=mis.status,
        )


@router.post("/subjects/{subject_id}/question-templates", response_model=QuestionTemplateResponse, status_code=201)
async def create_question_template(
    subject_id: UUID,
    request: CreateQuestionTemplateRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> QuestionTemplateResponse:
    """Create a question template with its first version.

    This creates:
    1. QuestionTemplate (the template entity)
    2. TemplateVersion v1 (the immutable specification)
    3. TemplateConcept links (connecting to concepts)
    4. Explanation variants (if provided)
    """
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]

        # Verify subject exists
        subject = await session.get(SubjectModel, subject_id)
        if subject is None:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Subject not found"})

        # Create the template
        template = QuestionTemplateModel(
            id=uuid4(),
            subject_id=subject_id,
            code=request.code,
            question_type=request.question_type,
            status="draft",
        )
        session.add(template)
        await session.flush()

        # Create template version v1
        tv = TemplateVersionModel(
            id=uuid4(),
            template_id=template.id,
            version_number=1,
            parameter_schema=request.parameter_schema,
            prompt_template=request.prompt_template,
            correct_answer_generator=request.correct_answer_generator,
            distractor_generator=request.distractor_generator,
            explanation_template=request.explanation_template,
            hint_tiers=request.hint_tiers,
            difficulty_estimate=request.difficulty_estimate,
            discrimination_estimate=request.discrimination_estimate,
        )
        session.add(tv)
        await session.flush()

        # Link concepts
        for concept_id in request.concept_ids:
            tc = TemplateConceptModel(
                id=uuid4(),
                template_version_id=tv.id,
                concept_id=concept_id,
            )
            session.add(tc)

        # Create explanations
        for expl in request.explanations:
            explanation = ExplanationModel(
                id=uuid4(),
                template_version_id=tv.id,
                outcome_key=expl.get("outcome_key", "correct"),
                content=expl.get("content", ""),
            )
            session.add(explanation)

        # Update template's current version
        template.current_version_id = tv.id

        await session.commit()
        await session.refresh(template)

        return QuestionTemplateResponse(
            id=template.id, subject_id=template.subject_id,
            code=template.code, question_type=template.question_type,
            status=template.status, current_version_id=template.current_version_id,
        )


@router.post("/question-templates/{template_id}/publish", response_model=QuestionTemplateResponse)
async def publish_template(
    template_id: UUID,
    request: PublishTemplateRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> QuestionTemplateResponse:
    """Publish a question template — makes it available for question generation."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        template = await session.get(QuestionTemplateModel, template_id)
        if template is None:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Template not found"})

        template.status = "published"
        template.published_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(template)

        return QuestionTemplateResponse(
            id=template.id, subject_id=template.subject_id,
            code=template.code, question_type=template.question_type,
            status=template.status, current_version_id=template.current_version_id,
        )


@router.get("/subjects/{subject_id}/concepts", response_model=list[ConceptResponse])
async def list_concepts(
    subject_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[ConceptResponse]:
    """List concepts in a subject."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await session.execute(
            select(ConceptModel).where(ConceptModel.subject_id == subject_id)
        )
        concepts = result.scalars().all()
        return [
            ConceptResponse(
                id=c.id, subject_id=c.subject_id, slug=c.slug, name=c.name,
                description=c.description, difficulty=c.difficulty,
                importance=c.importance, status=c.status,
            )
            for c in concepts
        ]


@router.get("/subjects/{subject_id}/question-templates", response_model=list[QuestionTemplateResponse])
async def list_templates(
    subject_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[QuestionTemplateResponse]:
    """List question templates in a subject."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        result = await session.execute(
            select(QuestionTemplateModel).where(QuestionTemplateModel.subject_id == subject_id)
        )
        templates = result.scalars().all()
        return [
            QuestionTemplateResponse(
                id=t.id, subject_id=t.subject_id, code=t.code,
                question_type=t.question_type, status=t.status,
                current_version_id=t.current_version_id,
            )
            for t in templates
        ]


@router.get("/question-templates/{template_id}", response_model=TemplateVersionResponse)
async def get_template_detail(
    template_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> TemplateVersionResponse:
    """Get template detail including the current version and concept links."""
    async with uow as _uow:
        session = _uow._session  # type: ignore[union-attr]
        template = await session.get(QuestionTemplateModel, template_id)
        if template is None:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Template not found"})

        if template.current_version_id is None:
            raise HTTPException(404, detail={"code": "NO_VERSION", "message": "Template has no version"})

        tv = await session.get(TemplateVersionModel, template.current_version_id)
        if tv is None:
            raise HTTPException(404, detail={"code": "VERSION_NOT_FOUND", "message": "Version not found"})

        # Load concept links
        tc_result = await session.execute(
            select(TemplateConceptModel.concept_id).where(
                TemplateConceptModel.template_version_id == tv.id
            )
        )
        concept_ids = [row[0] for row in tc_result.all()]

        return TemplateVersionResponse(
            id=tv.id, template_id=tv.template_id, version_number=tv.version_number,
            prompt_template=tv.prompt_template, difficulty_estimate=tv.difficulty_estimate,
            concept_ids=concept_ids,
        )
