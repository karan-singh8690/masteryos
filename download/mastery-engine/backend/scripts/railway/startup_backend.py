#!/usr/bin/env python3
"""Backend startup script for Railway (Task 028).

Runs before uvicorn starts:
1. Wait for PostgreSQL (with retries)
2. Run Alembic migrations (or SQL init scripts as fallback)
3. Verify database schema
4. Start FastAPI via uvicorn

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


def run_migrations() -> bool:
    """Run Alembic migrations to the latest revision."""
    print("[startup] Running database migrations...")
    try:
        from alembic.config import Config
        from alembic import command
        from app.shared.config import get_settings

        settings = get_settings()
        alembic_cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
        sync_url = settings.database_url.replace("+asyncpg", "")
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(alembic_cfg, "head")
        print("[startup] Migrations completed successfully")
        return True
    except Exception as e:
        print(f"[startup] Alembic migration failed: {e}")
        return False


def run_sql_init_scripts() -> bool:
    """Fallback: run SQL init scripts when Alembic has no migrations."""
    print("[startup] Running SQL init scripts...")
    try:
        import glob
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.shared.config import get_settings

        settings = get_settings()
        engine = create_async_engine(settings.database_url)
        init_dir = os.path.join(BACKEND_DIR, "..", "infrastructure", "postgres", "init")
        sql_files = sorted(glob.glob(os.path.join(init_dir, "*.sql")))

        if not sql_files:
            print("[startup] No SQL init scripts found — skipping")
            return True

        async def run_scripts():
            async with engine.begin() as conn:
                for sql_file in sql_files:
                    filename = os.path.basename(sql_file)
                    print(f"[startup] Running {filename}...")
                    with open(sql_file, "r") as f:
                        sql_content = f.read()
                    statements = [s.strip() for s in sql_content.split(";") if s.strip()]
                    for stmt in statements:
                        try:
                            await conn.execute(text(stmt))
                        except Exception as e:
                            if "already exists" not in str(e).lower():
                                print(f"[startup] Warning in {filename}: {e}")

        asyncio.run(run_scripts())
        asyncio.run(engine.dispose())
        print("[startup] SQL init scripts completed")
        return True
    except Exception as e:
        print(f"[startup] ERROR: SQL init scripts failed: {e}")
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

    # Step 3: Run migrations (Alembic first, SQL fallback)
    print("[startup] Step 3/4: Running database migrations...")
    if not run_migrations():
        print("[startup] Alembic failed, trying SQL init scripts...")
        if not run_sql_init_scripts():
            print("[startup] FATAL: Database migration failed. Aborting.")
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
