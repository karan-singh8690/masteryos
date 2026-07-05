"""Mastery Engine — FastAPI Application Entry Point.

This is the main application factory. It:
1. Configures structured logging.
2. Creates the FastAPI application with CORS and middleware.
3. Registers health check + business routes.
4. Manages database lifecycle (startup/shutdown).

Business endpoints are registered per the OpenAPI contract (Task 006):
- /auth/* — Authentication (register, verify-email, login)
- /enrollments — Learner enrollment
- /study-sessions — Study session lifecycle
- /study-sessions/{id}/adaptive-queue — Adaptive queue generation
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

    # Initialize Sentry error tracking (Task 027-verify)
    settings = get_settings()
    if settings.sentry_dsn:
        from app.infrastructure.observability import SentryIntegration
        sentry = SentryIntegration(dsn=settings.sentry_dsn, environment=settings.app_env.value)
        sentry.initialize()
        logger.info("sentry_integration_started")
    else:
        logger.info("sentry_not_configured")

    await init_database()
    logger.info("database_initialized")

    # Initialize Redis cache (Task 024: platform hardening)
    try:
        import redis.asyncio as aioredis
        from app.infrastructure.cache.redis_cache import init_cache
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=False,
        )
        await redis_client.ping()
        await init_cache(redis_client)
        logger.info("redis_cache_initialized")
    except Exception as exc:
        logger.warning("redis_cache_init_skipped", error=str(exc))

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
    # Security middleware (Task 015: production security hardening)
    from app.presentation.middleware.security import (
        SecurityHeadersMiddleware,
        RateLimitMiddleware,
        CSRFMiddleware,
    )
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    # Performance middleware (Task 024: compression + ETag)
    from app.infrastructure.performance.middleware import (
        CompressionMiddleware,
        ETagMiddleware,
    )
    app.add_middleware(ETagMiddleware)
    app.add_middleware(CompressionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
    )

    # ================================
    # Routes
    # ================================
    # Health checks
    app.include_router(health_router, prefix="/api/v1")

    # Business routes (Task 011–013: vertical slices)
    from app.presentation.api.v1.auth import router as auth_router
    from app.presentation.api.v1.learning import router as learning_router
    from app.presentation.api.v1.questions import router as questions_router
    from app.presentation.api.v1.content_admin import router as content_admin_router
    from app.presentation.api.v1.users import router as users_router
    from app.presentation.api.v1.admin import router as admin_router
    from app.presentation.api.v1.beta import router as beta_router
    # Task 026: Closed Beta Operations Platform router (admin-only analytics + ops endpoints).
    from app.presentation.api.v1.beta_ops import router as beta_ops_router
    # Task 023: AI Intelligence Platform router
    from app.presentation.api.v1.ai import router as ai_router
    # Learner portal endpoints (dashboard, mastery, reviews, recommendations, achievements, notifications)
    from app.presentation.api.v1.learner import router as learner_router
    # Feature flags endpoint
    from app.presentation.api.v1.feature_flags import router as feature_flags_router
    # Billing + Stripe + API keys
    from app.presentation.api.v1.billing import router as billing_router
    # Admin management (users, orgs, RBAC, audit, analytics, system config, billing admin)
    from app.presentation.api.v1.admin_management import router as admin_management_router
    # Task 025-deploy: import beta_templates so its email templates register
    # into the TEMPLATES dict at app startup.
    from app.infrastructure.email import beta_templates  # noqa: F401

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(learning_router, prefix="/api/v1")
    app.include_router(questions_router, prefix="/api/v1")
    app.include_router(content_admin_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(beta_router, prefix="/api/v1")
    app.include_router(beta_ops_router, prefix="/api/v1")
    app.include_router(ai_router, prefix="/api/v1")
    app.include_router(learner_router, prefix="/api/v1")
    app.include_router(feature_flags_router, prefix="/api/v1")
    app.include_router(billing_router, prefix="/api/v1")
    app.include_router(admin_management_router, prefix="/api/v1")

    # Global exception handler — ensures all errors (including 500s)
    # return a JSON response with proper CORS headers.
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "detail": {
                    "code": "INTERNAL_ERROR",
                    "message": str(exc),
                }
            },
        )

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

    # Prometheus metrics endpoint (Task 024: observability)
    @app.get("/metrics", tags=["Monitoring"])
    async def prometheus_metrics():
        """Prometheus-compatible metrics endpoint."""
        from fastapi import Response
        from app.infrastructure.observability import get_metrics_registry
        try:
            registry = get_metrics_registry()
            content = registry.format_prometheus()
            return Response(
                content=content,
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )
        except Exception as exc:
            return Response(
                content=f"# Error generating metrics: {exc}\n",
                media_type="text/plain",
                status_code=200,
            )

    return app


# Create the application instance
app = create_app()
