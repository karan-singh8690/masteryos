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

    # Auto-seed Python interview content on startup (idempotent — skips if already seeded).
    # This ensures learner portal always has at least one subject to enroll in.
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from scripts.seed_content import seed_content as _seed_content
        await _seed_content()
        logger.info("content_seed_completed")
    except Exception as exc:
        logger.warning("content_seed_failed", error=str(exc))

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
    # Redis cache middleware (Phase 5: performance)
    # Note: Can't use await in create_app() — it's a regular function.
    # The CacheMiddleware will connect to Redis lazily on first request.
    try:
        import redis.asyncio as aioredis
        from app.infrastructure.cache.middleware import CacheMiddleware
        cache_redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        app.add_middleware(CacheMiddleware, redis_client=cache_redis)
        logger.info("cache_middleware_registered")
    except Exception as exc:
        logger.warning("cache_middleware_skipped", error=str(exc))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID", "X-Cache"],
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
    # Content seeding
    from app.presentation.api.v1.content_seed import router as content_seed_router
    # Operations (SMTP test, worker restart, health summary)
    from app.presentation.api.v1.operations import router as operations_router
    # WebSocket real-time
    from app.presentation.api.v1.websocket import router as websocket_router
    # Study Materials (PDF viewer, view-only)
    from app.presentation.api.v1.materials import router as materials_router
    # SEO — public question data for search engine indexing
    from app.presentation.api.v1.seo import router as seo_router
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
    app.include_router(content_seed_router, prefix="/api/v1")
    app.include_router(operations_router, prefix="/api/v1")
    app.include_router(websocket_router, prefix="/api/v1")
    app.include_router(materials_router, prefix="/api/v1")
    app.include_router(seo_router, prefix="/api/v1")

    # Global exception handler — ensures all errors (including 500s)
    # return a JSON response with proper CORS headers.
    from fastapi import Request
    from fastapi.responses import JSONResponse

    # AuthorizationDenied → 403 (NOT 500). Two classes exist (infra + app layer).
    from app.infrastructure.security.authorization import (
        AuthorizationDenied as InfraAuthorizationDenied,
    )
    from app.application.shared import (
        AuthorizationDenied as AppAuthorizationDenied,
        ResourceMissing,
        ConcurrencyConflict,
        ApplicationConflict,
    )

    @app.exception_handler(InfraAuthorizationDenied)
    async def infra_authz_handler(request: Request, exc: InfraAuthorizationDenied):
        return JSONResponse(
            status_code=403,
            content={
                "detail": {
                    "code": "FORBIDDEN",
                    "message": str(exc),
                }
            },
        )

    @app.exception_handler(AppAuthorizationDenied)
    async def app_authz_handler(request: Request, exc: AppAuthorizationDenied):
        return JSONResponse(
            status_code=403,
            content={
                "detail": {
                    "code": "FORBIDDEN",
                    "message": str(exc),
                }
            },
        )

    @app.exception_handler(ResourceMissing)
    async def resource_missing_handler(request: Request, exc: ResourceMissing):
        return JSONResponse(
            status_code=404,
            content={
                "detail": {
                    "code": "NOT_FOUND",
                    "message": str(exc),
                }
            },
        )

    @app.exception_handler(ConcurrencyConflict)
    async def concurrency_conflict_handler(request: Request, exc: ConcurrencyConflict):
        return JSONResponse(
            status_code=409,
            content={
                "detail": {
                    "code": "CONCURRENCY_CONFLICT",
                    "message": str(exc),
                }
            },
        )

    @app.exception_handler(ApplicationConflict)
    async def application_conflict_handler(request: Request, exc: ApplicationConflict):
        return JSONResponse(
            status_code=409,
            content={
                "detail": {
                    "code": "CONFLICT",
                    "message": str(exc),
                }
            },
        )

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
