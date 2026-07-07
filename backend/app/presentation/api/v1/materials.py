"""Study Materials API — PDF upload, view-only reader, reading progress.

Endpoints:
- POST   /materials/upload         — Upload PDF (admin only)
- GET    /materials                — List materials
- GET    /materials/{id}           — Get material metadata
- GET    /materials/{id}/page/{n}  — Get watermarked page image (view-only)
- POST   /materials/{id}/progress  — Update reading progress
- GET    /materials/{id}/progress  — Get reading progress
- DELETE /materials/{id}           — Delete material (admin only)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.presentation.dependencies import get_current_user_id, get_uow, require_any_role
from app.infrastructure.security.authorization import ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN
from app.application.shared import UnitOfWork
from app.infrastructure.database.orm.identity import UserModel

router = APIRouter(tags=["Study Materials"])

RequireAdmin = require_any_role(ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN)


# ============================================================
# Models
# ============================================================


class MaterialResponse(BaseModel):
    id: str
    title: str
    description: str | None
    subject_id: str | None
    concept_id: str | None
    exam_name: str | None
    exam_year: int | None
    language: str
    status: str
    page_count: int
    file_size_bytes: int
    is_premium: bool
    coin_cost: int
    material_type: str
    tags: list[str]
    uploaded_by: str
    created_at: str


class ProgressRequest(BaseModel):
    current_page: int
    read_time_seconds: int = 0


class ProgressResponse(BaseModel):
    current_page: int
    pages_read: int
    total_read_time_seconds: int
    is_completed: bool
    last_read_at: str | None


# ============================================================
# Endpoints
# ============================================================


@router.post(
    "/materials/upload",
    summary="Upload a PDF study material (admin only)",
)
async def upload_material(
    title: str = Query(..., max_length=200),
    description: str = Query("", max_length=2000),
    subject_id: UUID | None = Query(None),
    concept_id: UUID | None = Query(None),
    exam_name: str | None = Query(None),
    exam_year: int | None = Query(None),
    language: str = Query("en"),
    material_type: str = Query("pdf"),
    is_premium: bool = Query(False),
    coin_cost: int = Query(0, ge=0),
    tags: str = Query("", description="Comma-separated tags"),
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = Depends(RequireAdmin),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Upload a PDF file as a study material.

    The PDF is stored as a binary blob in the database — no filesystem needed.
    Pages are rendered on-the-fly with watermarks when viewed.
    No download endpoint exists — view-only.
    """
    # Validate file type
    if not file.content_type or "pdf" not in file.content_type.lower():
        raise HTTPException(status_code=422, detail="Only PDF files are allowed")

    # Read file data
    file_data = await file.read()
    file_size = len(file_data)

    if file_size > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=413, detail="File too large. Maximum 50MB.")

    # Get page count using PyMuPDF
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_data, filetype="pdf")
        page_count = doc.page_count
        doc.close()
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid PDF file: {exc}")

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import StudyMaterialModel

            material = StudyMaterialModel(
                id=uuid4(),
                title=title,
                description=description or None,
                subject_id=subject_id,
                concept_id=concept_id,
                exam_name=exam_name,
                exam_year=exam_year,
                language=language,
                status="published",
                file_data=file_data,
                file_size_bytes=file_size,
                page_count=page_count,
                is_premium=is_premium,
                coin_cost=coin_cost,
                uploaded_by=user_id,
                tags=tag_list,
                material_type=material_type,
            )
            session_obj.add(material)
            await _uow.commit()

        return {
            "id": str(material.id),
            "title": title,
            "page_count": page_count,
            "file_size_bytes": file_size,
            "message": "Material uploaded successfully. View-only — no download available.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/materials",
    summary="List study materials",
)
async def list_materials(
    subject_id: UUID | None = Query(None),
    exam_name: str | None = Query(None),
    language: str | None = Query(None),
    material_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """List all published study materials. Does NOT return file data."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import StudyMaterialModel, StudyMaterialProgressModel

            query = select(StudyMaterialModel).where(StudyMaterialModel.status == "published")
            if subject_id:
                query = query.where(StudyMaterialModel.subject_id == subject_id)
            if exam_name:
                query = query.where(StudyMaterialModel.exam_name == exam_name)
            if language:
                query = query.where(StudyMaterialModel.language == language)
            if material_type:
                query = query.where(StudyMaterialModel.material_type == material_type)

            # Get total count
            from sqlalchemy import func
            count_query = select(func.count()).select_from(StudyMaterialModel).where(StudyMaterialModel.status == "published")
            if subject_id:
                count_query = count_query.where(StudyMaterialModel.subject_id == subject_id)
            if exam_name:
                count_query = count_query.where(StudyMaterialModel.exam_name == exam_name)
            total = (await session_obj.execute(count_query)).scalar() or 0

            # Paginate
            offset = (page - 1) * page_size
            query = query.order_by(StudyMaterialModel.created_at.desc()).offset(offset).limit(page_size)
            result = await session_obj.execute(query)
            materials = result.scalars().all()

            # Get user's progress for each material
            material_ids = [m.id for m in materials]
            progress_map = {}
            if material_ids:
                progress_result = await session_obj.execute(
                    select(StudyMaterialProgressModel).where(
                        StudyMaterialProgressModel.user_id == user_id,
                        StudyMaterialProgressModel.material_id.in_(material_ids),
                    )
                )
                for p in progress_result.scalars().all():
                    progress_map[str(p.material_id)] = {
                        "current_page": p.current_page,
                        "pages_read": p.pages_read,
                        "is_completed": p.is_completed,
                    }

            return {
                "items": [
                    {
                        "id": str(m.id),
                        "title": m.title,
                        "description": m.description,
                        "subject_id": str(m.subject_id) if m.subject_id else None,
                        "exam_name": m.exam_name,
                        "exam_year": m.exam_year,
                        "language": m.language,
                        "page_count": m.page_count,
                        "file_size_bytes": m.file_size_bytes,
                        "is_premium": m.is_premium,
                        "coin_cost": m.coin_cost,
                        "material_type": m.material_type,
                        "tags": m.tags,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                        "progress": progress_map.get(str(m.id), {"current_page": 0, "pages_read": 0, "is_completed": False}),
                    }
                    for m in materials
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
    except Exception:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


@router.get(
    "/materials/{material_id}",
    summary="Get material metadata (no file data)",
)
async def get_material(
    material_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get metadata for a specific material. Does NOT return file data."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import StudyMaterialModel

            result = await session_obj.execute(
                select(StudyMaterialModel).where(StudyMaterialModel.id == material_id)
            )
            m = result.scalar_one_or_none()
            if not m:
                raise HTTPException(status_code=404, detail="Material not found")

            return {
                "id": str(m.id),
                "title": m.title,
                "description": m.description,
                "subject_id": str(m.subject_id) if m.subject_id else None,
                "concept_id": str(m.concept_id) if m.concept_id else None,
                "exam_name": m.exam_name,
                "exam_year": m.exam_year,
                "language": m.language,
                "status": m.status,
                "page_count": m.page_count,
                "file_size_bytes": m.file_size_bytes,
                "is_premium": m.is_premium,
                "coin_cost": m.coin_cost,
                "material_type": m.material_type,
                "tags": m.tags,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Phase B: Material-Concept Links (Reading Prerequisites)
# ============================================================


class ConceptLinkRequest(BaseModel):
    """Request: link a material to a concept."""
    concept_id: UUID
    is_prerequisite: bool = False
    min_pages_read: int = 1
    reading_order: int = 1


@router.post(
    "/materials/{material_id}/concept-links",
    summary="Link a material to a concept (Phase B — admin only)",
)
async def link_material_to_concept(
    material_id: UUID,
    request: ConceptLinkRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = Depends(RequireAdmin),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Link a study material to a concept.

    If is_prerequisite=True, the learner must read at least min_pages_read
    pages before the queue generator serves questions for that concept.
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import MaterialConceptLinkModel

            link = MaterialConceptLinkModel(
                material_id=material_id,
                concept_id=request.concept_id,
                is_prerequisite=request.is_prerequisite,
                min_pages_read=request.min_pages_read,
                reading_order=request.reading_order,
            )
            session_obj.add(link)
            await _uow.commit()

        return {
            "message": "Material linked to concept",
            "is_prerequisite": request.is_prerequisite,
            "min_pages_read": request.min_pages_read,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/concepts/{concept_id}/materials",
    summary="List materials linked to a concept (Phase B)",
)
async def get_concept_materials(
    concept_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[dict]:
    """Get all study materials linked to a concept, with the user's reading progress."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import (
                MaterialConceptLinkModel, StudyMaterialModel, StudyMaterialProgressModel
            )

            result = await session_obj.execute(
                select(MaterialConceptLinkModel, StudyMaterialModel)
                .join(StudyMaterialModel, MaterialConceptLinkModel.material_id == StudyMaterialModel.id)
                .where(MaterialConceptLinkModel.concept_id == concept_id)
                .where(StudyMaterialModel.status == "published")
                .order_by(MaterialConceptLinkModel.reading_order.asc())
            )
            rows = result.all()

            # Get user's progress for these materials
            material_ids = [str(m.id) for _, m in rows]
            progress_map = {}
            if material_ids:
                prog_result = await session_obj.execute(
                    select(StudyMaterialProgressModel).where(
                        StudyMaterialProgressModel.user_id == user_id,
                        StudyMaterialProgressModel.material_id.in_(material_ids),
                    )
                )
                for p in prog_result.scalars().all():
                    progress_map[str(p.material_id)] = p

            return [
                {
                    "material_id": str(m.id),
                    "title": m.title,
                    "description": m.description,
                    "page_count": m.page_count,
                    "material_type": m.material_type,
                    "tags": m.tags,
                    "is_prerequisite": link.is_prerequisite,
                    "min_pages_read": link.min_pages_read,
                    "reading_order": link.reading_order,
                    "pages_read": progress_map.get(str(m.id), None).pages_read if str(m.id) in progress_map else 0,
                    "is_completed": progress_map.get(str(m.id), None).is_completed if str(m.id) in progress_map else False,
                    "prerequisite_met": (
                        not link.is_prerequisite or
                        (progress_map.get(str(m.id)) is not None and
                         progress_map[str(m.id)].pages_read >= link.min_pages_read)
                    ),
                }
                for link, m in rows
            ]
    except Exception:
        return []


@router.get(
    "/materials/prerequisites/check",
    summary="Check reading prerequisites for concepts (Phase B)",
)
async def check_reading_prerequisites(
    enrollment_id: UUID = Query(..., description="Enrollment to check prerequisites for"),
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Check which concepts have unread prerequisite materials.

    Returns:
    - concepts_with_unread_prerequisites: concepts that can't be served yet
    - read_first_materials: materials the user should read first
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import (
                MaterialConceptLinkModel, StudyMaterialModel, StudyMaterialProgressModel
            )
            from app.infrastructure.database.orm.content import ConceptModel
            from app.infrastructure.database.orm.core import LearnerEnrollmentModel
            from sqlalchemy import func

            # Get the subject_id for this enrollment
            enroll_result = await session_obj.execute(
                select(LearnerEnrollmentModel).where(LearnerEnrollmentModel.id == enrollment_id)
            )
            enrollment = enroll_result.scalar_one_or_none()
            if not enrollment:
                return {"concepts_with_unread_prerequisites": [], "read_first_materials": []}

            # Get all concepts for this subject
            concepts_result = await session_obj.execute(
                select(ConceptModel).where(ConceptModel.subject_id == enrollment.subject_id)
            )
            concepts = {str(c.id): c.name for c in concepts_result.scalars().all()}

            # Get all prerequisite material links for these concepts
            concept_ids = list(concepts.keys())
            if not concept_ids:
                return {"concepts_with_unread_prerequisites": [], "read_first_materials": []}

            links_result = await session_obj.execute(
                select(MaterialConceptLinkModel, StudyMaterialModel)
                .join(StudyMaterialModel, MaterialConceptLinkModel.material_id == StudyMaterialModel.id)
                .where(
                    MaterialConceptLinkModel.concept_id.in_(concept_ids),
                    MaterialConceptLinkModel.is_prerequisite.is_(True),
                    StudyMaterialModel.status == "published",
                )
                .order_by(MaterialConceptLinkModel.reading_order.asc())
            )
            links = links_result.all()

            if not links:
                return {"concepts_with_unread_prerequisites": [], "read_first_materials": []}

            # Get user's progress for all linked materials
            material_ids = [str(m.id) for _, m in links]
            prog_result = await session_obj.execute(
                select(StudyMaterialProgressModel).where(
                    StudyMaterialProgressModel.user_id == user_id,
                    StudyMaterialProgressModel.material_id.in_(material_ids),
                )
            )
            progress_map = {}
            for p in prog_result.scalars().all():
                progress_map[str(p.material_id)] = p

            # Find unread prerequisites
            unread_concepts = set()
            read_first = []
            seen_materials = set()

            for link, material in links:
                cid = str(link.concept_id)
                mid = str(material.id)
                progress = progress_map.get(mid)
                pages_read = progress.pages_read if progress else 0

                if pages_read < link.min_pages_read:
                    # Prerequisite not met
                    unread_concepts.add(cid)
                    if mid not in seen_materials:
                        seen_materials.add(mid)
                        read_first.append({
                            "material_id": mid,
                            "title": material.title,
                            "description": material.description,
                            "page_count": material.page_count,
                            "material_type": material.material_type,
                            "concept_name": concepts.get(cid, "Unknown"),
                            "min_pages_read": link.min_pages_read,
                            "pages_read": pages_read,
                            "remaining_pages": max(0, link.min_pages_read - pages_read),
                            "reading_order": link.reading_order,
                        })

            return {
                "concepts_with_unread_prerequisites": [
                    {"concept_id": cid, "concept_name": concepts.get(cid, "Unknown")}
                    for cid in unread_concepts
                ],
                "read_first_materials": sorted(read_first, key=lambda x: x["reading_order"]),
            }
    except Exception:
        return {"concepts_with_unread_prerequisites": [], "read_first_materials": []}


@router.get(
    "/materials/{material_id}/page/{page_num}",
    summary="Get watermarked page image (view-only, no download)",
)
async def get_material_page(
    material_id: UUID,
    page_num: int,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> StreamingResponse:
    """Get a single page of the PDF as a watermarked image.

    - PDF is rendered server-side using PyMuPDF
    - Each page is watermarked with the user's email + timestamp
    - Returns PNG image — no PDF file is ever sent to the client
    - Right-click and download are disabled on the frontend
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import StudyMaterialModel
            from app.infrastructure.database.orm.identity import UserModel

            # Load material
            result = await session_obj.execute(
                select(StudyMaterialModel).where(StudyMaterialModel.id == material_id)
            )
            m = result.scalar_one_or_none()
            if not m:
                raise HTTPException(status_code=404, detail="Material not found")

            if page_num < 1 or page_num > m.page_count:
                raise HTTPException(status_code=404, detail=f"Page {page_num} not found. Material has {m.page_count} pages.")

            # Load user email for watermark
            user_result = await session_obj.execute(
                select(UserModel.email).where(UserModel.id == user_id)
            )
            user_email = user_result.scalar_one_or_none() or "unknown@masteryos.com"

            # Render PDF page to image using PyMuPDF
            import fitz  # PyMuPDF
            from PIL import Image, ImageDraw, ImageFont
            import io as _io

            doc = fitz.open(stream=m.file_data, filetype="pdf")
            page = doc[page_num - 1]  # 0-indexed

            # Render at 2x resolution for clarity
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            doc.close()

            # Convert to PIL Image for watermarking
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Add watermark — user email + timestamp, semi-transparent diagonal
            draw = ImageDraw.Draw(img, "RGBA")

            # Try to use a font, fallback to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            except Exception:
                font = ImageFont.load_default()

            watermark_text = f"{user_email} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} | MasteryOS"

            # Diagonal watermark across center
            text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            # Draw multiple watermarks
            for y_offset in range(0, pix.height, 200):
                for x_offset in range(0, pix.width, text_width + 100):
                    draw.text(
                        (x_offset, y_offset),
                        watermark_text,
                        fill=(128, 128, 128, 45),  # Semi-transparent gray
                        font=font,
                    )

            # Convert to PNG bytes
            img_byte_arr = _io.BytesIO()
            img.save(img_byte_arr, format="PNG", optimize=True)
            img_byte_arr.seek(0)

            return StreamingResponse(
                img_byte_arr,
                media_type="image/png",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate",
                    "X-Material-Page": f"{page_num}/{m.page_count}",
                    "X-Watermarked": "true",
                    "Content-Security-Policy": "no-download",
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to render page: {exc}")


@router.post(
    "/materials/{material_id}/progress",
    summary="Update reading progress",
)
async def update_progress(
    material_id: UUID,
    request: ProgressRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Update the user's reading progress for a material."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import StudyMaterialModel, StudyMaterialProgressModel

            # Get material for page count
            mat_result = await session_obj.execute(
                select(StudyMaterialModel).where(StudyMaterialModel.id == material_id)
            )
            material = mat_result.scalar_one_or_none()
            if not material:
                raise HTTPException(status_code=404, detail="Material not found")

            # Check if progress record exists
            prog_result = await session_obj.execute(
                select(StudyMaterialProgressModel).where(
                    StudyMaterialProgressModel.user_id == user_id,
                    StudyMaterialProgressModel.material_id == material_id,
                )
            )
            progress = prog_result.scalar_one_or_none()

            is_completed = request.current_page >= material.page_count

            if progress:
                await session_obj.execute(
                    sql_update(StudyMaterialProgressModel).where(
                        StudyMaterialProgressModel.user_id == user_id,
                        StudyMaterialProgressModel.material_id == material_id,
                    ).values(
                        current_page=min(request.current_page, material.page_count),
                        pages_read=max(progress.pages_read, request.current_page),
                        total_read_time_seconds=progress.total_read_time_seconds + request.read_time_seconds,
                        last_read_at=datetime.now(timezone.utc),
                        is_completed=is_completed,
                    )
                )
            else:
                progress = StudyMaterialProgressModel(
                    id=uuid4(),
                    user_id=user_id,
                    material_id=material_id,
                    current_page=min(request.current_page, material.page_count),
                    pages_read=request.current_page,
                    total_read_time_seconds=request.read_time_seconds,
                    last_read_at=datetime.now(timezone.utc),
                    is_completed=is_completed,
                )
                session_obj.add(progress)

            await _uow.commit()

        return {
            "current_page": min(request.current_page, material.page_count),
            "is_completed": is_completed,
            "message": "Progress updated",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Phase B: Material-Concept Links (Reading Prerequisites)
# ============================================================


class ConceptLinkRequest(BaseModel):
    """Request: link a material to a concept."""
    concept_id: UUID
    is_prerequisite: bool = False
    min_pages_read: int = 1
    reading_order: int = 1


@router.post(
    "/materials/{material_id}/concept-links",
    summary="Link a material to a concept (Phase B — admin only)",
)
async def link_material_to_concept(
    material_id: UUID,
    request: ConceptLinkRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = Depends(RequireAdmin),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Link a study material to a concept.

    If is_prerequisite=True, the learner must read at least min_pages_read
    pages before the queue generator serves questions for that concept.
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import MaterialConceptLinkModel

            link = MaterialConceptLinkModel(
                material_id=material_id,
                concept_id=request.concept_id,
                is_prerequisite=request.is_prerequisite,
                min_pages_read=request.min_pages_read,
                reading_order=request.reading_order,
            )
            session_obj.add(link)
            await _uow.commit()

        return {
            "message": "Material linked to concept",
            "is_prerequisite": request.is_prerequisite,
            "min_pages_read": request.min_pages_read,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/concepts/{concept_id}/materials",
    summary="List materials linked to a concept (Phase B)",
)
async def get_concept_materials(
    concept_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[dict]:
    """Get all study materials linked to a concept, with the user's reading progress."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import (
                MaterialConceptLinkModel, StudyMaterialModel, StudyMaterialProgressModel
            )

            result = await session_obj.execute(
                select(MaterialConceptLinkModel, StudyMaterialModel)
                .join(StudyMaterialModel, MaterialConceptLinkModel.material_id == StudyMaterialModel.id)
                .where(MaterialConceptLinkModel.concept_id == concept_id)
                .where(StudyMaterialModel.status == "published")
                .order_by(MaterialConceptLinkModel.reading_order.asc())
            )
            rows = result.all()

            # Get user's progress for these materials
            material_ids = [str(m.id) for _, m in rows]
            progress_map = {}
            if material_ids:
                prog_result = await session_obj.execute(
                    select(StudyMaterialProgressModel).where(
                        StudyMaterialProgressModel.user_id == user_id,
                        StudyMaterialProgressModel.material_id.in_(material_ids),
                    )
                )
                for p in prog_result.scalars().all():
                    progress_map[str(p.material_id)] = p

            return [
                {
                    "material_id": str(m.id),
                    "title": m.title,
                    "description": m.description,
                    "page_count": m.page_count,
                    "material_type": m.material_type,
                    "tags": m.tags,
                    "is_prerequisite": link.is_prerequisite,
                    "min_pages_read": link.min_pages_read,
                    "reading_order": link.reading_order,
                    "pages_read": progress_map.get(str(m.id), None).pages_read if str(m.id) in progress_map else 0,
                    "is_completed": progress_map.get(str(m.id), None).is_completed if str(m.id) in progress_map else False,
                    "prerequisite_met": (
                        not link.is_prerequisite or
                        (progress_map.get(str(m.id)) is not None and
                         progress_map[str(m.id)].pages_read >= link.min_pages_read)
                    ),
                }
                for link, m in rows
            ]
    except Exception:
        return []


@router.get(
    "/materials/prerequisites/check",
    summary="Check reading prerequisites for concepts (Phase B)",
)
async def check_reading_prerequisites(
    enrollment_id: UUID = Query(..., description="Enrollment to check prerequisites for"),
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Check which concepts have unread prerequisite materials.

    Returns:
    - concepts_with_unread_prerequisites: concepts that can't be served yet
    - read_first_materials: materials the user should read first
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import (
                MaterialConceptLinkModel, StudyMaterialModel, StudyMaterialProgressModel
            )
            from app.infrastructure.database.orm.content import ConceptModel
            from app.infrastructure.database.orm.core import LearnerEnrollmentModel
            from sqlalchemy import func

            # Get the subject_id for this enrollment
            enroll_result = await session_obj.execute(
                select(LearnerEnrollmentModel).where(LearnerEnrollmentModel.id == enrollment_id)
            )
            enrollment = enroll_result.scalar_one_or_none()
            if not enrollment:
                return {"concepts_with_unread_prerequisites": [], "read_first_materials": []}

            # Get all concepts for this subject
            concepts_result = await session_obj.execute(
                select(ConceptModel).where(ConceptModel.subject_id == enrollment.subject_id)
            )
            concepts = {str(c.id): c.name for c in concepts_result.scalars().all()}

            # Get all prerequisite material links for these concepts
            concept_ids = list(concepts.keys())
            if not concept_ids:
                return {"concepts_with_unread_prerequisites": [], "read_first_materials": []}

            links_result = await session_obj.execute(
                select(MaterialConceptLinkModel, StudyMaterialModel)
                .join(StudyMaterialModel, MaterialConceptLinkModel.material_id == StudyMaterialModel.id)
                .where(
                    MaterialConceptLinkModel.concept_id.in_(concept_ids),
                    MaterialConceptLinkModel.is_prerequisite.is_(True),
                    StudyMaterialModel.status == "published",
                )
                .order_by(MaterialConceptLinkModel.reading_order.asc())
            )
            links = links_result.all()

            if not links:
                return {"concepts_with_unread_prerequisites": [], "read_first_materials": []}

            # Get user's progress for all linked materials
            material_ids = [str(m.id) for _, m in links]
            prog_result = await session_obj.execute(
                select(StudyMaterialProgressModel).where(
                    StudyMaterialProgressModel.user_id == user_id,
                    StudyMaterialProgressModel.material_id.in_(material_ids),
                )
            )
            progress_map = {}
            for p in prog_result.scalars().all():
                progress_map[str(p.material_id)] = p

            # Find unread prerequisites
            unread_concepts = set()
            read_first = []
            seen_materials = set()

            for link, material in links:
                cid = str(link.concept_id)
                mid = str(material.id)
                progress = progress_map.get(mid)
                pages_read = progress.pages_read if progress else 0

                if pages_read < link.min_pages_read:
                    # Prerequisite not met
                    unread_concepts.add(cid)
                    if mid not in seen_materials:
                        seen_materials.add(mid)
                        read_first.append({
                            "material_id": mid,
                            "title": material.title,
                            "description": material.description,
                            "page_count": material.page_count,
                            "material_type": material.material_type,
                            "concept_name": concepts.get(cid, "Unknown"),
                            "min_pages_read": link.min_pages_read,
                            "pages_read": pages_read,
                            "remaining_pages": max(0, link.min_pages_read - pages_read),
                            "reading_order": link.reading_order,
                        })

            return {
                "concepts_with_unread_prerequisites": [
                    {"concept_id": cid, "concept_name": concepts.get(cid, "Unknown")}
                    for cid in unread_concepts
                ],
                "read_first_materials": sorted(read_first, key=lambda x: x["reading_order"]),
            }
    except Exception:
        return {"concepts_with_unread_prerequisites": [], "read_first_materials": []}


@router.get(
    "/materials/{material_id}/progress",
    summary="Get reading progress",
)
async def get_progress(
    material_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Get the user's reading progress for a material."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import StudyMaterialProgressModel

            result = await session_obj.execute(
                select(StudyMaterialProgressModel).where(
                    StudyMaterialProgressModel.user_id == user_id,
                    StudyMaterialProgressModel.material_id == material_id,
                )
            )
            p = result.scalar_one_or_none()
            if not p:
                return {"current_page": 0, "pages_read": 0, "total_read_time_seconds": 0, "is_completed": False, "last_read_at": None}

            return {
                "current_page": p.current_page,
                "pages_read": p.pages_read,
                "total_read_time_seconds": p.total_read_time_seconds,
                "is_completed": p.is_completed,
                "last_read_at": p.last_read_at.isoformat() if p.last_read_at else None,
            }
    except Exception:
        return {"current_page": 0, "pages_read": 0, "total_read_time_seconds": 0, "is_completed": False, "last_read_at": None}


@router.delete(
    "/materials/{material_id}",
    summary="Delete a study material (admin only)",
)
async def delete_material(
    material_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = Depends(RequireAdmin),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Delete a study material and all associated progress records."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import StudyMaterialModel

            result = await session_obj.execute(
                select(StudyMaterialModel).where(StudyMaterialModel.id == material_id)
            )
            material = result.scalar_one_or_none()
            if not material:
                raise HTTPException(status_code=404, detail="Material not found")

            await session_obj.delete(material)
            await _uow.commit()

        return {"message": "Material deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Phase B: Material-Concept Links (Reading Prerequisites)
# ============================================================


class ConceptLinkRequest(BaseModel):
    """Request: link a material to a concept."""
    concept_id: UUID
    is_prerequisite: bool = False
    min_pages_read: int = 1
    reading_order: int = 1


@router.post(
    "/materials/{material_id}/concept-links",
    summary="Link a material to a concept (Phase B — admin only)",
)
async def link_material_to_concept(
    material_id: UUID,
    request: ConceptLinkRequest,
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = Depends(RequireAdmin),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Link a study material to a concept.

    If is_prerequisite=True, the learner must read at least min_pages_read
    pages before the queue generator serves questions for that concept.
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import MaterialConceptLinkModel

            link = MaterialConceptLinkModel(
                material_id=material_id,
                concept_id=request.concept_id,
                is_prerequisite=request.is_prerequisite,
                min_pages_read=request.min_pages_read,
                reading_order=request.reading_order,
            )
            session_obj.add(link)
            await _uow.commit()

        return {
            "message": "Material linked to concept",
            "is_prerequisite": request.is_prerequisite,
            "min_pages_read": request.min_pages_read,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/concepts/{concept_id}/materials",
    summary="List materials linked to a concept (Phase B)",
)
async def get_concept_materials(
    concept_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[dict]:
    """Get all study materials linked to a concept, with the user's reading progress."""
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import (
                MaterialConceptLinkModel, StudyMaterialModel, StudyMaterialProgressModel
            )

            result = await session_obj.execute(
                select(MaterialConceptLinkModel, StudyMaterialModel)
                .join(StudyMaterialModel, MaterialConceptLinkModel.material_id == StudyMaterialModel.id)
                .where(MaterialConceptLinkModel.concept_id == concept_id)
                .where(StudyMaterialModel.status == "published")
                .order_by(MaterialConceptLinkModel.reading_order.asc())
            )
            rows = result.all()

            # Get user's progress for these materials
            material_ids = [str(m.id) for _, m in rows]
            progress_map = {}
            if material_ids:
                prog_result = await session_obj.execute(
                    select(StudyMaterialProgressModel).where(
                        StudyMaterialProgressModel.user_id == user_id,
                        StudyMaterialProgressModel.material_id.in_(material_ids),
                    )
                )
                for p in prog_result.scalars().all():
                    progress_map[str(p.material_id)] = p

            return [
                {
                    "material_id": str(m.id),
                    "title": m.title,
                    "description": m.description,
                    "page_count": m.page_count,
                    "material_type": m.material_type,
                    "tags": m.tags,
                    "is_prerequisite": link.is_prerequisite,
                    "min_pages_read": link.min_pages_read,
                    "reading_order": link.reading_order,
                    "pages_read": progress_map.get(str(m.id), None).pages_read if str(m.id) in progress_map else 0,
                    "is_completed": progress_map.get(str(m.id), None).is_completed if str(m.id) in progress_map else False,
                    "prerequisite_met": (
                        not link.is_prerequisite or
                        (progress_map.get(str(m.id)) is not None and
                         progress_map[str(m.id)].pages_read >= link.min_pages_read)
                    ),
                }
                for link, m in rows
            ]
    except Exception:
        return []


@router.get(
    "/materials/prerequisites/check",
    summary="Check reading prerequisites for concepts (Phase B)",
)
async def check_reading_prerequisites(
    enrollment_id: UUID = Query(..., description="Enrollment to check prerequisites for"),
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """Check which concepts have unread prerequisite materials.

    Returns:
    - concepts_with_unread_prerequisites: concepts that can't be served yet
    - read_first_materials: materials the user should read first
    """
    try:
        async with uow as _uow:
            session_obj = _uow._session  # type: ignore[union-attr]
            from app.infrastructure.database.orm.materials import (
                MaterialConceptLinkModel, StudyMaterialModel, StudyMaterialProgressModel
            )
            from app.infrastructure.database.orm.content import ConceptModel
            from app.infrastructure.database.orm.core import LearnerEnrollmentModel
            from sqlalchemy import func

            # Get the subject_id for this enrollment
            enroll_result = await session_obj.execute(
                select(LearnerEnrollmentModel).where(LearnerEnrollmentModel.id == enrollment_id)
            )
            enrollment = enroll_result.scalar_one_or_none()
            if not enrollment:
                return {"concepts_with_unread_prerequisites": [], "read_first_materials": []}

            # Get all concepts for this subject
            concepts_result = await session_obj.execute(
                select(ConceptModel).where(ConceptModel.subject_id == enrollment.subject_id)
            )
            concepts = {str(c.id): c.name for c in concepts_result.scalars().all()}

            # Get all prerequisite material links for these concepts
            concept_ids = list(concepts.keys())
            if not concept_ids:
                return {"concepts_with_unread_prerequisites": [], "read_first_materials": []}

            links_result = await session_obj.execute(
                select(MaterialConceptLinkModel, StudyMaterialModel)
                .join(StudyMaterialModel, MaterialConceptLinkModel.material_id == StudyMaterialModel.id)
                .where(
                    MaterialConceptLinkModel.concept_id.in_(concept_ids),
                    MaterialConceptLinkModel.is_prerequisite.is_(True),
                    StudyMaterialModel.status == "published",
                )
                .order_by(MaterialConceptLinkModel.reading_order.asc())
            )
            links = links_result.all()

            if not links:
                return {"concepts_with_unread_prerequisites": [], "read_first_materials": []}

            # Get user's progress for all linked materials
            material_ids = [str(m.id) for _, m in links]
            prog_result = await session_obj.execute(
                select(StudyMaterialProgressModel).where(
                    StudyMaterialProgressModel.user_id == user_id,
                    StudyMaterialProgressModel.material_id.in_(material_ids),
                )
            )
            progress_map = {}
            for p in prog_result.scalars().all():
                progress_map[str(p.material_id)] = p

            # Find unread prerequisites
            unread_concepts = set()
            read_first = []
            seen_materials = set()

            for link, material in links:
                cid = str(link.concept_id)
                mid = str(material.id)
                progress = progress_map.get(mid)
                pages_read = progress.pages_read if progress else 0

                if pages_read < link.min_pages_read:
                    # Prerequisite not met
                    unread_concepts.add(cid)
                    if mid not in seen_materials:
                        seen_materials.add(mid)
                        read_first.append({
                            "material_id": mid,
                            "title": material.title,
                            "description": material.description,
                            "page_count": material.page_count,
                            "material_type": material.material_type,
                            "concept_name": concepts.get(cid, "Unknown"),
                            "min_pages_read": link.min_pages_read,
                            "pages_read": pages_read,
                            "remaining_pages": max(0, link.min_pages_read - pages_read),
                            "reading_order": link.reading_order,
                        })

            return {
                "concepts_with_unread_prerequisites": [
                    {"concept_id": cid, "concept_name": concepts.get(cid, "Unknown")}
                    for cid in unread_concepts
                ],
                "read_first_materials": sorted(read_first, key=lambda x: x["reading_order"]),
            }
    except Exception:
        return {"concepts_with_unread_prerequisites": [], "read_first_materials": []}
