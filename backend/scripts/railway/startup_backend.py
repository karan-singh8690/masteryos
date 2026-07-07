#!/usr/bin/env python3
"""Backend startup script for Railway (Task 028).

Runs before uvicorn starts:
1. Wait for PostgreSQL (with retries)
2. Wait for Redis (non-fatal)
3. Create all database tables from ORM models (Base.metadata.create_all)
4. Verify database schema
5. Start FastAPI via uvicorn

If any step fails, the script exits with code 1 and Railway marks
the deployment as failed.
"""

from __future__ import annotations

import asyncio
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)


async def wait_for_database(max_retries: int = 30, delay: float = 2.0) -> bool:
    """Wait for PostgreSQL to be available."""
    from app.shared.config import get_settings
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = get_settings()
    safe_url = settings.database_url.split("@")[1] if "@" in settings.database_url else "unknown"
    print(f"[startup] Waiting for database at {safe_url}...")

    for attempt in range(1, max_retries + 1):
        try:
            engine = create_async_engine(settings.database_url)
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    print(f"[startup] Database available (attempt {attempt})")
                    await engine.dispose()
                    return True
            await engine.dispose()
        except Exception as e:
            print(f"[startup] Database not ready (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                await asyncio.sleep(delay)

    print(f"[startup] ERROR: Database not available after {max_retries} attempts")
    return False


async def wait_for_redis(max_retries: int = 15, delay: float = 2.0) -> bool:
    """Wait for Redis to be available. Non-fatal if unavailable."""
    from app.shared.config import get_settings
    import redis.asyncio as redis

    settings = get_settings()
    print(f"[startup] Waiting for Redis at {settings.redis_host}:{settings.redis_port}...")

    for attempt in range(1, max_retries + 1):
        try:
            client = redis.from_url(settings.redis_url)
            pong = await client.ping()
            await client.aclose()
            if pong:
                print(f"[startup] Redis available (attempt {attempt})")
                return True
        except Exception as e:
            print(f"[startup] Redis not ready (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                await asyncio.sleep(delay)

    print(f"[startup] WARNING: Redis not available after {max_retries} attempts (continuing)")
    return False


async def create_tables() -> bool:
    """Create all database tables from ORM models using Base.metadata.create_all().

    If the database is empty (fresh), creates all schemas + tables.
    If the database already has the critical tables, skips creation.
    If the database has partial/broken tables, drops everything and recreates.
    """
    print("[startup] Setting up database tables...")
    try:
        from sqlalchemy import text, inspect
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.shared.config import get_settings
        from app.infrastructure.database.orm.base import Base
        # Import all ORM modules to populate Base.metadata
        from app.infrastructure.database.orm import (  # noqa: F401
            identity,
            auth,
            background,
            beta,
            beta_ops,
            core,
            content,
        )

        settings = get_settings()
        engine = create_async_engine(settings.database_url)

        async with engine.begin() as conn:
            # Step 1: Create all schemas first
            print("[startup] Creating database schemas...")
            schemas = [
                "identity", "content", "learning", "assessment", "mastery",
                "scheduling", "administration", "analytics", "billing",
                "infrastructure",
            ]
            for schema in schemas:
                await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {schema}'))
            print(f"[startup] Created {len(schemas)} schemas")

            # Step 2: Check if identity.users table exists and is complete
            result = await conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'identity' AND table_name = 'users')"
            ))
            users_table_exists = result.scalar()

            if users_table_exists:
                # Check if the table has the 'status' column (indicates complete creation)
                result = await conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = 'identity' AND table_name = 'users' AND column_name = 'status')"
                ))
                has_status_column = result.scalar()

                if has_status_column:
                    print("[startup] Database already initialized — running column migrations only")
                    # Run ALTER TABLE migrations for new columns (Phase 1-4)
                    print("[startup] Adding new columns for Indian localization phases...")
                    alter_statements = [
                        "ALTER TABLE learning.learner_enrollments ADD COLUMN IF NOT EXISTS target_exam_date TIMESTAMPTZ",
                        "ALTER TABLE learning.learner_enrollments ADD COLUMN IF NOT EXISTS target_exam_name VARCHAR(100)",
                        "ALTER TABLE learning.learner_enrollments ADD COLUMN IF NOT EXISTS negative_marking_factor FLOAT DEFAULT 0.0",
                        "ALTER TABLE assessment.attempts ADD COLUMN IF NOT EXISTS error_type VARCHAR(30)",
                        "ALTER TABLE assessment.attempts ADD COLUMN IF NOT EXISTS marks_delta FLOAT DEFAULT 0.0",
                        "ALTER TABLE content.question_templates ADD COLUMN IF NOT EXISTS pyq_exam VARCHAR(50)",
                        "ALTER TABLE content.question_templates ADD COLUMN IF NOT EXISTS pyq_year INTEGER",
                        "ALTER TABLE content.question_templates ADD COLUMN IF NOT EXISTS pyq_source VARCHAR(200)",
                        "ALTER TABLE content.template_versions ADD COLUMN IF NOT EXISTS prompt_template_hindi JSONB",
                        "ALTER TABLE content.template_versions ADD COLUMN IF NOT EXISTS explanation_template_hindi JSONB",
                        "ALTER TABLE content.template_versions ADD COLUMN IF NOT EXISTS distractor_generator_hindi JSONB",
                        "ALTER TABLE content.template_versions ADD COLUMN IF NOT EXISTS solution_traditional JSONB",
                        "ALTER TABLE content.template_versions ADD COLUMN IF NOT EXISTS solution_shortcut JSONB",
                        "ALTER TABLE content.template_versions ADD COLUMN IF NOT EXISTS solution_elimination JSONB",
                    ]
                    for stmt in alter_statements:
                        try:
                            await conn.execute(text(stmt))
                        except Exception:
                            pass
                    print("[startup] Column migration complete")
                    await engine.dispose()
                    return True
                else:
                    print("[startup] Database has partial/broken tables — dropping everything and recreating")
                    await conn.run_sync(Base.metadata.drop_all)
                    # Also drop any orphaned tables from partial creation
                    for schema in schemas:
                        await conn.execute(text(
                            f'DROP SCHEMA IF EXISTS {schema} CASCADE'
                        ))
                        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {schema}'))
                    print("[startup] Dropped all schemas + tables, recreating...")

            # Step 3: Create all tables from ORM models
            print("[startup] Creating tables from ORM models...")
            await conn.run_sync(Base.metadata.create_all)

            # Phase 1-4: Add new columns to existing tables (ALTER TABLE)
            # create_all only creates missing tables — it doesn't add columns to existing tables.
            # We use ADD COLUMN IF NOT EXISTS for safe idempotent migration.
            print("[startup] Adding new columns for Indian localization phases...")
            alter_statements = [
                # Phase 1: LearnerEnrollmentModel
                "ALTER TABLE learning.learner_enrollments ADD COLUMN IF NOT EXISTS target_exam_date TIMESTAMPTZ",
                "ALTER TABLE learning.learner_enrollments ADD COLUMN IF NOT EXISTS target_exam_name VARCHAR(100)",
                "ALTER TABLE learning.learner_enrollments ADD COLUMN IF NOT EXISTS negative_marking_factor FLOAT DEFAULT 0.0",
                # Phase 1: AttemptModel
                "ALTER TABLE assessment.attempts ADD COLUMN IF NOT EXISTS error_type VARCHAR(30)",
                "ALTER TABLE assessment.attempts ADD COLUMN IF NOT EXISTS marks_delta FLOAT DEFAULT 0.0",
                # Phase 1: QuestionTemplateModel
                "ALTER TABLE content.question_templates ADD COLUMN IF NOT EXISTS pyq_exam VARCHAR(50)",
                "ALTER TABLE content.question_templates ADD COLUMN IF NOT EXISTS pyq_year INTEGER",
                "ALTER TABLE content.question_templates ADD COLUMN IF NOT EXISTS pyq_source VARCHAR(200)",
                # Phase 3: TemplateVersionModel — Hindi
                "ALTER TABLE content.template_versions ADD COLUMN IF NOT EXISTS prompt_template_hindi JSONB",
                "ALTER TABLE content.template_versions ADD COLUMN IF NOT EXISTS explanation_template_hindi JSONB",
                "ALTER TABLE content.template_versions ADD COLUMN IF NOT EXISTS distractor_generator_hindi JSONB",
                # Phase 4: TemplateVersionModel — Solution styles
                "ALTER TABLE content.template_versions ADD COLUMN IF NOT EXISTS solution_traditional JSONB",
                "ALTER TABLE content.template_versions ADD COLUMN IF NOT EXISTS solution_shortcut JSONB",
                "ALTER TABLE content.template_versions ADD COLUMN IF NOT EXISTS solution_elimination JSONB",
            ]
            for stmt in alter_statements:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass  # Column may already exist or table may not exist yet
            print("[startup] Column migration complete")

        await engine.dispose()
        print("[startup] Database tables created successfully")

        # Step 4: Auto-seed Python interview content
        print("[startup] Seeding Python interview content...")
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from scripts.seed_content import seed_content
            await seed_content()
        except Exception as seed_err:
            print(f"[startup] Content seeding skipped: {seed_err}")

        return True
    except Exception as e:
        print(f"[startup] ERROR: Table creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_schema() -> bool:
    """Verify that critical database tables exist."""
    print("[startup] Verifying database schema...")
    required_tables = [
        ("identity", "users"),
        ("identity", "sessions"),
        ("infrastructure", "outbox_events"),
        ("infrastructure", "worker_heartbeats"),
    ]
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.shared.config import get_settings

        settings = get_settings()
        engine = create_async_engine(settings.database_url)

        async with engine.connect() as conn:
            for schema, name in required_tables:
                result = await conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :name)"
                ), {"schema": schema, "name": name})
                if not result.scalar():
                    print(f"[startup] ERROR: Missing required table: {schema}.{name}")
                    await engine.dispose()
                    return False

        await engine.dispose()
        print("[startup] Schema verification passed")
        return True
    except Exception as e:
        print(f"[startup] ERROR: Schema verification failed: {e}")
        return False


async def main() -> int:
    """Main startup sequence. Returns 0 on success, 1 on failure."""
    from app.shared.logging import configure_logging
    from app.shared.railway_config import detect_deployment

    configure_logging()
    print(f"[startup] Deployment environment: {detect_deployment()}")

    # Step 1: Wait for PostgreSQL
    print("[startup] Step 1/4: Waiting for PostgreSQL...")
    if not await wait_for_database(max_retries=30, delay=2.0):
        print("[startup] FATAL: Cannot connect to PostgreSQL. Aborting.")
        return 1

    # Step 2: Wait for Redis (non-fatal)
    print("[startup] Step 2/4: Waiting for Redis...")
    await wait_for_redis(max_retries=15, delay=2.0)

    # Step 3: Create tables from ORM models (replaces Alembic + SQL init)
    print("[startup] Step 3/4: Creating database tables...")
    if not await create_tables():
        print("[startup] FATAL: Database table creation failed. Aborting.")
        return 1

    # Step 4: Verify schema
    print("[startup] Step 4/4: Verifying schema...")
    if not await verify_schema():
        print("[startup] FATAL: Schema verification failed. Aborting.")
        return 1

    print("[startup] All checks passed. Starting uvicorn...")
    import uvicorn
    from app.shared.config import get_settings

    settings = get_settings()
    config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        log_level="info",
        access_log=True,
        workers=1,
    )
    server = uvicorn.Server(config)
    await server.serve()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
