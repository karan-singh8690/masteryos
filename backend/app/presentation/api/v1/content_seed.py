"""Content seeding API — seed Python interview content into the database.

POST /api/v1/admin/seed-content — Seeds the database with Python interview content
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any
from uuid import UUID

from app.presentation.dependencies import get_current_user_id, get_uow, require_any_role
from app.infrastructure.security.authorization import ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN
from app.application.shared import UnitOfWork

router = APIRouter(prefix="/admin", tags=["Admin — Content Seeding"])

RequireAdmin = require_any_role(ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN)


class SeedResponse(BaseModel):
    message: str
    subject: str | None = None
    concepts: int = 0
    templates: int = 0


@router.post("/seed-content", response_model=SeedResponse)
async def seed_content(
    user_id: UUID = Depends(get_current_user_id),
    _admin: Any = Depends(RequireAdmin),
    uow: UnitOfWork = Depends(get_uow),
) -> SeedResponse:
    """Seed the database with Python interview content (subjects, concepts, templates).

    This creates:
    - 1 Subject: Python Technical Interview Prep
    - 5 Concepts: Data Structures, OOP, Algorithms, Python Internals, System Design
    - 15 Learning Objectives
    - 10 Misconceptions
    - 10 Question Templates with explanations

    Safe to call multiple times — checks if content already exists.
    """
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from scripts.seed_content import seed_content as do_seed
        await do_seed()
        return SeedResponse(
            message="Content seeded successfully",
            subject="Python Technical Interview Prep",
            concepts=5,
            templates=10,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Seeding failed: {exc}")
