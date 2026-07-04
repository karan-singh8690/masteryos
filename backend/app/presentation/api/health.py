"""Health check endpoints.

The application exposes three health endpoints:
- /health: Liveness probe (is the process running?)
- /ready: Readiness probe (can the application serve requests?)
- /live: Liveness probe alias (for Kubernetes-style health checks)

These are the ONLY endpoints in this scaffold. Business endpoints will be
added in future tasks per the OpenAPI contract (Task 006).
"""

from __future__ import annotations

import time
from typing import Any

import redis.asyncio as redis
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.shared.config import get_settings
from app.shared.logging import get_logger

router = APIRouter(prefix="/health", tags=["Health"])
logger = get_logger(__name__)


class HealthResponse(BaseModel):
    """Liveness check response."""

    status: str = "healthy"
    app: str
    version: str
    timestamp: float


class ReadinessCheck(BaseModel):
    """Individual readiness check result."""

    name: str
    status: str
    latency_ms: float | None = None
    details: dict[str, Any] | None = None


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    status: str
    checks: list[ReadinessCheck]


@router.get(
    "",
    summary="Liveness check",
    description="Returns 200 if the application process is running.",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
async def health() -> HealthResponse:
    """Liveness probe — process is running."""
    settings = get_settings()
    return HealthResponse(
        app=settings.app_name,
        version="0.1.0",
        timestamp=time.time(),
    )


@router.get(
    "/ready",
    summary="Readiness check",
    description="Returns 200 if the application can serve requests (database, cache connected).",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
)
async def readiness(
    db_session: AsyncSession = Depends(get_db_session),
) -> ReadinessResponse:
    """Readiness probe — dependencies are connected."""
    checks: list[ReadinessCheck] = []
    overall_status = "ready"

    # Check database
    try:
        start = time.perf_counter()
        await db_session.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        checks.append(
            ReadinessCheck(
                name="database",
                status="pass",
                latency_ms=round(latency, 2),
            )
        )
    except Exception as exc:
        logger.warning("database_readiness_check_failed", error=str(exc))
        checks.append(
            ReadinessCheck(
                name="database",
                status="fail",
                details={"error": str(exc)},
            )
        )
        overall_status = "not_ready"

    # Check Redis
    try:
        settings = get_settings()
        start = time.perf_counter()
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.aclose()
        latency = (time.perf_counter() - start) * 1000
        checks.append(
            ReadinessCheck(
                name="redis",
                status="pass",
                latency_ms=round(latency, 2),
            )
        )
    except Exception as exc:
        logger.warning("redis_readiness_check_failed", error=str(exc))
        checks.append(
            ReadinessCheck(
                name="redis",
                status="fail",
                details={"error": str(exc)},
            )
        )
        overall_status = "not_ready"

    return ReadinessResponse(status=overall_status, checks=checks)


@router.get(
    "/live",
    summary="Liveness check (Kubernetes-style)",
    description="Returns 200 if the application process is running. Alias for /health.",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
async def live() -> HealthResponse:
    """Liveness probe — Kubernetes-style alias."""
    return await health()
