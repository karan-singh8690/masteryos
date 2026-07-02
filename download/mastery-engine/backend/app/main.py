"""Mastery Engine — FastAPI Application Entry Point.

This is the main application factory. It:
1. Configures structured logging.
2. Creates the FastAPI application with CORS and middleware.
3. Registers health check routes.
4. Manages database lifecycle (startup/shutdown).

Business endpoints (authentication, learning, content, etc.) will be
registered here in future tasks per the OpenAPI contract (Task 006).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.database import close_database, init_database
from app.presentation.api.health import router as health_router
from app.presentation.middleware.correlation import CorrelationMiddleware
from app.shared.config import get_settings
from app.shared.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown handlers."""
    # --- Startup ---
    configure_logging()
    logger.info("application_starting", version="0.1.0")
    await init_database()
    logger.info("application_started")

    yield

    # --- Shutdown ---
    logger.info("application_stopping")
    await close_database()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    This is the application factory pattern, allowing:
    - Different configurations per environment
    - Easy testing (create a fresh app per test)
    - Cleaner main.py
    """
    settings = get_settings()

    app = FastAPI(
        title="Mastery Engine API",
        description=(
            "A Learning Operating System that determines the single highest-value "
            "learning activity for every user based on measurable mastery."
        ),
        version="0.1.0",
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
        lifespan=lifespan,
    )

    # ================================
    # Middleware
    # ================================
    app.add_middleware(CorrelationMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
    )

    # ================================
    # Routes
    # ================================
    app.include_router(health_router, prefix="/api/v1")

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        """Root endpoint — basic service info."""
        return {
            "service": "Mastery Engine API",
            "version": "0.1.0",
            "docs": "/docs" if settings.enable_docs else "disabled",
            "health": "/api/v1/health",
        }

    return app


# Create the application instance
app = create_app()
