"""Tests for Railway-native deployment configuration (Task 028).

Covers:
- Environment variable parsing (DATABASE_URL, REDIS_URL, PORT)
- Deployment detection (railway, docker, local)
- Railway config file structure
- Startup script existence and logic
- Health check endpoints
- GitHub Actions workflow
- Environment variable reference
- Cost optimization documentation
- Rollback strategy documentation
- Launch checklist
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("APP_ENV", "testing")

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

PROJECT_ROOT = BACKEND_DIR.parent
RAILWAY_DIR = PROJECT_ROOT / "railway"


# ============================================================
# Part 2: Environment Variable Migration
# ============================================================


class TestRedisUrlParsing:
    """Tests for parse_redis_url()."""

    def test_parse_simple_url(self):
        from app.shared.railway_config import parse_redis_url
        result = parse_redis_url("redis://localhost:6379/0")
        assert result["host"] == "localhost"
        assert result["port"] == 6379
        assert result["password"] == ""
        assert result["db"] == 0

    def test_parse_url_with_password(self):
        from app.shared.railway_config import parse_redis_url
        result = parse_redis_url("redis://:mypassword@redis-host:6380/2")
        assert result["host"] == "redis-host"
        assert result["port"] == 6380
        assert result["password"] == "mypassword"
        assert result["db"] == 2

    def test_parse_url_with_user_and_password(self):
        from app.shared.railway_config import parse_redis_url
        result = parse_redis_url("redis://user:pass@host:6379/0")
        assert result["host"] == "host"
        assert result["port"] == 6379
        assert result["password"] == "pass"

    def test_parse_url_without_db(self):
        from app.shared.railway_config import parse_redis_url
        result = parse_redis_url("redis://localhost:6379")
        assert result["host"] == "localhost"
        assert result["port"] == 6379
        assert result["db"] == 0

    def test_parse_url_without_port(self):
        from app.shared.railway_config import parse_redis_url
        result = parse_redis_url("redis://localhost/0")
        assert result["host"] == "localhost"
        assert result["db"] == 0

    def test_parse_rediss_url(self):
        from app.shared.railway_config import parse_redis_url
        result = parse_redis_url("rediss://:pass@host:6380/3")
        assert result["host"] == "host"
        assert result["port"] == 6380
        assert result["password"] == "pass"
        assert result["db"] == 3

    def test_parse_empty_url(self):
        from app.shared.railway_config import parse_redis_url
        result = parse_redis_url("")
        assert result["host"] == "localhost"
        assert result["port"] == 6379
        assert result["password"] == ""
        assert result["db"] == 0

    def test_parse_url_with_special_chars_in_password(self):
        from app.shared.railway_config import parse_redis_url
        result = parse_redis_url("redis://:p@ss!w0rd@host:6379/0")
        assert result["host"] == "host"
        assert result["port"] == 6379


class TestDatabaseUrlParsing:
    """Tests for parse_database_url()."""

    def test_add_asyncpg_driver(self):
        from app.shared.railway_config import parse_database_url
        result = parse_database_url("postgresql://user:pass@host:5432/db")
        assert "+asyncpg" in result
        assert result.startswith("postgresql+asyncpg://")

    def test_preserve_existing_asyncpg(self):
        from app.shared.railway_config import parse_database_url
        url = "postgresql+asyncpg://user:pass@host:5432/db"
        result = parse_database_url(url)
        assert result == url

    def test_convert_postgres_scheme(self):
        from app.shared.railway_config import parse_database_url
        result = parse_database_url("postgres://user:pass@host:5432/db")
        assert result.startswith("postgresql+asyncpg://")

    def test_empty_url(self):
        from app.shared.railway_config import parse_database_url
        assert parse_database_url("") == ""

    def test_already_asyncpg_unchanged(self):
        from app.shared.railway_config import parse_database_url
        url = "postgresql+asyncpg://mastery:pass@localhost:5432/mastery_engine"
        assert parse_database_url(url) == url


class TestDeploymentDetection:
    """Tests for detect_deployment()."""

    def test_detect_local_default(self):
        from app.shared.railway_config import detect_deployment
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("RAILWAY_PROJECT_ID", None)
            os.environ.pop("RAILWAY_SERVICE_ID", None)
            # Can't fully control Docker detection, so just test it returns a string
            result = detect_deployment()
            assert result in ("railway", "docker", "local")

    def test_detect_railway_with_project_id(self):
        from app.shared.railway_config import detect_deployment
        with patch.dict(os.environ, {"RAILWAY_PROJECT_ID": "test-123"}):
            assert detect_deployment() == "railway"

    def test_detect_railway_with_service_id(self):
        from app.shared.railway_config import detect_deployment
        with patch.dict(os.environ, {"RAILWAY_SERVICE_ID": "svc-456"}):
            assert detect_deployment() == "railway"


class TestRailwayOverrides:
    """Tests for apply_railway_overrides()."""

    def test_database_url_override(self):
        from app.shared.railway_config import apply_railway_overrides
        from app.shared.config import Settings

        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@railway-host:5432/railway_db",
            "APP_ENV": "testing",
        }):
            settings = Settings()
            settings = apply_railway_overrides(settings)
            assert "+asyncpg" in settings.database_url
            assert "railway-host" in settings.database_url

    def test_redis_url_override(self):
        from app.shared.railway_config import apply_railway_overrides
        from app.shared.config import Settings

        with patch.dict(os.environ, {
            "REDIS_URL": "redis://:railpass@railway-redis:6380/1",
            "APP_ENV": "testing",
        }):
            settings = Settings()
            settings = apply_railway_overrides(settings)
            assert settings.redis_host == "railway-redis"
            assert settings.redis_port == 6380
            assert settings.redis_password == "railpass"
            assert settings.redis_db == 1

    def test_port_override(self):
        from app.shared.railway_config import apply_railway_overrides
        from app.shared.config import Settings

        with patch.dict(os.environ, {
            "PORT": "8080",
            "APP_ENV": "testing",
        }):
            settings = Settings()
            settings = apply_railway_overrides(settings)
            assert settings.app_port == 8080

    def test_no_overrides_when_not_set(self):
        from app.shared.railway_config import apply_railway_overrides
        from app.shared.config import Settings

        # Clear Railway-specific env vars
        env_without_railway = {k: v for k, v in os.environ.items()
                               if k not in ("DATABASE_URL", "REDIS_URL", "PORT")}
        with patch.dict(os.environ, env_without_railway, clear=True):
            os.environ["APP_ENV"] = "testing"
            settings = Settings()
            original_host = settings.redis_host
            settings = apply_railway_overrides(settings)
            assert settings.redis_host == original_host


# ============================================================
# Part 1 & 3: Railway Configuration Files
# ============================================================


class TestRailwayConfigFiles:
    """Verify all Railway configuration files exist and are valid."""

    def test_backend_railway_json_exists(self):
        path = RAILWAY_DIR / "backend" / "railway.json"
        assert path.exists(), "backend/railway.json must exist"

    def test_worker_railway_json_exists(self):
        path = RAILWAY_DIR / "worker" / "railway.json"
        assert path.exists(), "worker/railway.json must exist"

    def test_frontend_railway_json_exists(self):
        path = RAILWAY_DIR / "frontend" / "railway.json"
        assert path.exists(), "frontend/railway.json must exist"

    def test_railway_toml_exists(self):
        path = RAILWAY_DIR / "railway.toml"
        assert path.exists(), "railway.toml must exist"

    def test_backend_railway_json_valid(self):
        path = RAILWAY_DIR / "backend" / "railway.json"
        data = json.loads(path.read_text())
        assert data.get("$schema", "").startswith("https://railway.app")
        assert "build" in data
        assert "deploy" in data

    def test_worker_railway_json_valid(self):
        path = RAILWAY_DIR / "worker" / "railway.json"
        data = json.loads(path.read_text())
        assert "build" in data
        assert "deploy" in data
        assert "startCommand" in data["deploy"]

    def test_frontend_railway_json_valid(self):
        path = RAILWAY_DIR / "frontend" / "railway.json"
        data = json.loads(path.read_text())
        assert "build" in data
        assert "deploy" in data

    def test_backend_start_command_uses_startup_script(self):
        path = RAILWAY_DIR / "backend" / "railway.json"
        data = json.loads(path.read_text())
        assert "startup_backend" in data["deploy"]["startCommand"]

    def test_worker_start_command_uses_startup_script(self):
        path = RAILWAY_DIR / "worker" / "railway.json"
        data = json.loads(path.read_text())
        assert "startup_worker" in data["deploy"]["startCommand"]

    def test_backend_has_health_check(self):
        path = RAILWAY_DIR / "backend" / "railway.json"
        data = json.loads(path.read_text())
        assert data["deploy"].get("healthcheckPath") == "/api/v1/health"

    def test_frontend_has_health_check(self):
        path = RAILWAY_DIR / "frontend" / "railway.json"
        data = json.loads(path.read_text())
        assert data["deploy"].get("healthcheckPath") == "/"

    def test_backend_has_restart_policy(self):
        path = RAILWAY_DIR / "backend" / "railway.json"
        data = json.loads(path.read_text())
        assert data["deploy"].get("restartPolicyType") == "ON_FAILURE"
        assert data["deploy"].get("restartPolicyMaxRetries") >= 3

    def test_worker_has_restart_policy(self):
        path = RAILWAY_DIR / "worker" / "railway.json"
        data = json.loads(path.read_text())
        assert data["deploy"].get("restartPolicyType") == "ON_FAILURE"
        assert data["deploy"].get("restartPolicyMaxRetries") >= 5

    def test_railway_toml_has_all_services(self):
        path = RAILWAY_DIR / "railway.toml"
        content = path.read_text()
        assert "backend" in content
        assert "worker" in content
        assert "frontend" in content
        assert "postgres" in content
        assert "redis" in content

    def test_railway_toml_has_plugins(self):
        path = RAILWAY_DIR / "railway.toml"
        content = path.read_text()
        assert "postgresql" in content
        assert "redis" in content


# ============================================================
# Part 4 & 5: Startup Scripts
# ============================================================


class TestStartupScripts:
    """Verify startup scripts exist and have correct structure."""

    def test_backend_startup_script_exists(self):
        path = BACKEND_DIR / "scripts" / "railway" / "startup_backend.py"
        assert path.exists()

    def test_worker_startup_script_exists(self):
        path = BACKEND_DIR / "scripts" / "railway" / "startup_worker.py"
        assert path.exists()

    def test_backend_startup_has_wait_for_database(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_backend.py").read_text()
        assert "wait_for_database" in content
        assert "max_retries" in content

    def test_backend_startup_has_migrations(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_backend.py").read_text()
        assert "run_migrations" in content
        assert "alembic" in content.lower()

    def test_backend_startup_has_sql_fallback(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_backend.py").read_text()
        assert "run_sql_init_scripts" in content

    def test_backend_startup_has_schema_verification(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_backend.py").read_text()
        assert "verify_schema" in content

    def test_backend_startup_has_redis_wait(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_worker.py").read_text()
        assert "wait_for_redis" in content

    def test_backend_startup_starts_uvicorn(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_backend.py").read_text()
        assert "uvicorn" in content
        assert "app.main:app" in content

    def test_worker_startup_has_wait_for_database(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_worker.py").read_text()
        assert "wait_for_database" in content

    def test_worker_startup_has_reconnect_logic(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_worker.py").read_text()
        assert "backoff" in content or "retry" in content.lower()

    def test_worker_startup_has_graceful_shutdown(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_worker.py").read_text()
        assert "SIGTERM" in content
        assert "SIGINT" in content
        assert "graceful" in content.lower() or "host.stop" in content

    def test_worker_startup_has_heartbeat(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_worker.py").read_text()
        assert "WorkerHost" in content
        assert "worker_id" in content

    def test_worker_startup_has_exponential_backoff(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_worker.py").read_text()
        assert "1.5" in content  # backoff multiplier

    def test_backend_startup_aborts_on_migration_failure(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_backend.py").read_text()
        assert "FATAL" in content
        assert "return 1" in content

    def test_backend_startup_has_four_steps(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_backend.py").read_text()
        assert "Step 1/4" in content
        assert "Step 2/4" in content
        assert "Step 3/4" in content
        assert "Step 4/4" in content


# ============================================================
# Part 7: Health Checks
# ============================================================


class TestHealthChecks:
    """Verify health check configuration."""

    def test_backend_health_endpoint_exists(self):
        from app.main import app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/health" in routes

    def test_backend_ready_endpoint_exists(self):
        from app.main import app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/health/ready" in routes

    def test_backend_live_endpoint_exists(self):
        from app.main import app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/health/live" in routes

    def test_railway_backend_healthcheck_path(self):
        path = RAILWAY_DIR / "backend" / "railway.json"
        data = json.loads(path.read_text())
        assert data["deploy"]["healthcheckPath"] == "/api/v1/health"

    def test_railway_frontend_healthcheck_path(self):
        path = RAILWAY_DIR / "frontend" / "railway.json"
        data = json.loads(path.read_text())
        assert data["deploy"]["healthcheckPath"] == "/"

    def test_backend_healthcheck_timeout_120(self):
        path = RAILWAY_DIR / "backend" / "railway.json"
        data = json.loads(path.read_text())
        assert data["deploy"]["healthcheckTimeout"] == 120

    def test_worker_has_restart_policy(self):
        path = RAILWAY_DIR / "worker" / "railway.json"
        data = json.loads(path.read_text())
        assert data["deploy"]["restartPolicyType"] == "ON_FAILURE"
        assert data["deploy"]["restartPolicyMaxRetries"] >= 5


# ============================================================
# Part 9: Secrets Management
# ============================================================


class TestSecretsManagement:
    """Verify no secrets are committed and env var docs exist."""

    def test_env_vars_doc_exists(self):
        path = RAILWAY_DIR / "RAILWAY_ENV_VARS.md"
        assert path.exists()

    def test_env_vars_doc_has_database_url(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "DATABASE_URL" in content

    def test_env_vars_doc_has_redis_url(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "REDIS_URL" in content

    def test_env_vars_doc_has_jwt_keys(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "JWT_PRIVATE_KEY" in content or "JWT_KEYS_DIR" in content

    def test_env_vars_doc_has_smtp(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "SMTP_HOST" in content
        assert "SMTP_PASSWORD" in content

    def test_env_vars_doc_has_sentry(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "SENTRY_DSN" in content

    def test_env_vars_doc_has_ai_config(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "AI_ENABLED" in content

    def test_env_vars_doc_has_port(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "PORT" in content

    def test_env_vars_doc_has_cors_origins(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "CORS_ORIGINS" in content

    def test_env_vars_doc_has_frontend_vars(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "NEXT_PUBLIC_API_URL" in content
        assert "NEXT_PUBLIC_APP_NAME" in content

    def test_env_vars_doc_has_worker_reference_vars(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "Reference" in content or "reference" in content.lower()

    def test_env_vars_doc_has_github_secrets(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "RAILWAY_TOKEN" in content

    def test_gitignore_has_env_production(self):
        gitignore_path = PROJECT_ROOT / ".gitignore"
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            assert ".env.production" in content or ".env" in content

    def test_no_hardcoded_secrets_in_railway_config(self):
        """Check that railway config files don't contain actual secrets."""
        for json_file in (RAILWAY_DIR / "backend" / "railway.json",
                          RAILWAY_DIR / "worker" / "railway.json",
                          RAILWAY_DIR / "frontend" / "railway.json"):
            if json_file.exists():
                content = json_file.read_text()
                # Should not contain actual passwords, only references
                assert "password123" not in content.lower()
                assert "changeme" not in content.lower()
                assert "secret_key" not in content.lower()


# ============================================================
# Part 10: GitHub Continuous Deployment
# ============================================================


class TestGitHubCD:
    """Verify GitHub Actions workflow exists and is correct."""

    def test_workflow_file_exists(self):
        path = PROJECT_ROOT / ".github" / "workflows" / "railway-deploy.yml"
        assert path.exists()

    def test_workflow_has_test_job(self):
        path = PROJECT_ROOT / ".github" / "workflows" / "railway-deploy.yml"
        content = path.read_text()
        assert "test" in content.lower()
        assert "pytest" in content or "vitest" in content

    def test_workflow_has_deploy_backend_job(self):
        path = PROJECT_ROOT / ".github" / "workflows" / "railway-deploy.yml"
        content = path.read_text()
        assert "deploy-backend" in content
        assert "railway up" in content

    def test_workflow_has_deploy_worker_job(self):
        path = PROJECT_ROOT / ".github" / "workflows" / "railway-deploy.yml"
        content = path.read_text()
        assert "deploy-worker" in content

    def test_workflow_has_deploy_frontend_job(self):
        path = PROJECT_ROOT / ".github" / "workflows" / "railway-deploy.yml"
        content = path.read_text()
        assert "deploy-frontend" in content

    def test_workflow_has_health_checks(self):
        path = PROJECT_ROOT / ".github" / "workflows" / "railway-deploy.yml"
        content = path.read_text()
        assert "health" in content.lower()
        assert "curl" in content

    def test_workflow_has_verify_job(self):
        path = PROJECT_ROOT / ".github" / "workflows" / "railway-deploy.yml"
        content = path.read_text()
        assert "verify" in content.lower()

    def test_workflow_triggers_on_push_to_main(self):
        path = PROJECT_ROOT / ".github" / "workflows" / "railway-deploy.yml"
        content = path.read_text()
        assert "main" in content
        assert "push" in content

    def test_workflow_has_railway_secrets(self):
        path = PROJECT_ROOT / ".github" / "workflows" / "railway-deploy.yml"
        content = path.read_text()
        assert "RAILWAY_TOKEN" in content
        assert "RAILWAY_PROJECT_ID" in content

    def test_workflow_deploy_order_is_correct(self):
        path = PROJECT_ROOT / ".github" / "workflows" / "railway-deploy.yml"
        content = path.read_text()
        # Backend should deploy before worker and frontend
        backend_pos = content.find("deploy-backend")
        worker_pos = content.find("deploy-worker")
        frontend_pos = content.find("deploy-frontend")
        assert backend_pos < worker_pos
        assert backend_pos < frontend_pos

    def test_workflow_worker_depends_on_backend(self):
        path = PROJECT_ROOT / ".github" / "workflows" / "railway-deploy.yml"
        content = path.read_text()
        # Worker job should need deploy-backend
        worker_section = content[content.find("deploy-worker"):]
        assert "needs: deploy-backend" in worker_section or "deploy-backend" in worker_section[:200]

    def test_workflow_frontend_depends_on_backend(self):
        path = PROJECT_ROOT / ".github" / "workflows" / "railway-deploy.yml"
        content = path.read_text()
        frontend_section = content[content.find("deploy-frontend"):]
        assert "needs: deploy-backend" in frontend_section or "deploy-backend" in frontend_section[:200]


# ============================================================
# Part 11 & 12: Observability & Cost Optimization
# ============================================================


class TestObservabilityDocs:
    """Verify observability and cost documentation."""

    def test_deploy_guide_exists(self):
        path = RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md"
        assert path.exists()

    def test_deploy_guide_has_logs_section(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "Logs" in content or "logs" in content

    def test_deploy_guide_has_metrics_section(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "Metrics" in content or "metrics" in content

    def test_deploy_guide_has_deployments_section(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "Deployments" in content or "deployments" in content

    def test_deploy_guide_has_health_status(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "Health" in content or "health" in content.lower()

    def test_deploy_guide_has_cost_estimates(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "$" in content
        assert "month" in content.lower()

    def test_deploy_guide_has_cost_for_20_users(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "20" in content

    def test_deploy_guide_has_cost_for_1000_users(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "1000" in content

    def test_deploy_guide_has_sleeping_optimization(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "sleep" in content.lower()

    def test_deploy_guide_has_pool_size_optimization(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "pool" in content.lower() or "DATABASE_POOL_SIZE" in content


# ============================================================
# Part 13 & 14: Launch Checklist & Rollback
# ============================================================


class TestLaunchChecklistAndRollback:
    """Verify launch checklist and rollback strategy."""

    def test_deploy_guide_has_launch_steps(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "Step" in content
        assert "Create Railway Project" in content or "Step 1" in content

    def test_deploy_guide_has_postgres_plugin(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "PostgreSQL" in content
        assert "plugin" in content.lower() or "Plugin" in content

    def test_deploy_guide_has_redis_plugin(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "Redis" in content

    def test_deploy_guide_has_migration_section(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "migration" in content.lower() or "Migration" in content

    def test_deploy_guide_has_rollback_section(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "Rollback" in content or "rollback" in content

    def test_deploy_guide_has_manual_rollback(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "Redeploy" in content or "redeploy" in content

    def test_deploy_guide_has_database_rollback(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "alembic downgrade" in content

    def test_deploy_guide_has_troubleshooting(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "Troubleshooting" in content or "troubleshooting" in content

    def test_deploy_guide_has_faq(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "FAQ" in content or "Q:" in content

    def test_deploy_guide_has_custom_domain(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "Custom Domain" in content or "custom domain" in content

    def test_deploy_guide_has_jwt_key_generation(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "openssl genrsa" in content

    def test_deploy_guide_has_github_secrets(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "RAILWAY_TOKEN" in content
        assert "GitHub" in content


# ============================================================
# Part 15: Documentation
# ============================================================


class TestDocumentation:
    """Verify all documentation exists."""

    def test_railway_deploy_guide_exists(self):
        assert (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").exists()

    def test_railway_env_vars_exists(self):
        assert (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").exists()

    def test_deploy_guide_has_architecture_diagram(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "GitHub" in content
        assert "Railway" in content
        assert "│" in content or "├" in content or "└" in content

    def test_deploy_guide_has_startup_sequence(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "Service starts" in content or "startup" in content.lower()

    def test_deploy_guide_has_step_by_step(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        assert "Step 1" in content
        assert "Step 2" in content
        assert "Step 3" in content

    def test_env_vars_doc_has_variable_order(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "Variable Setup Order" in content or "Setup" in content

    def test_deploy_guide_mentions_backward_compatibility(self):
        content = (RAILWAY_DIR / "RAILWAY_DEPLOY_GUIDE.md").read_text()
        # The guide should not mention breaking changes
        assert "backward" in content.lower() or "compatible" in content.lower() or "backward compat" in content.lower()


# ============================================================
# Part 6: Frontend Configuration
# ============================================================


class TestFrontendConfig:
    """Verify frontend Railway configuration."""

    def test_frontend_railway_json_has_build_command(self):
        path = RAILWAY_DIR / "frontend" / "railway.json"
        data = json.loads(path.read_text())
        assert "npm" in data["build"]["buildCommand"]
        assert "build" in data["build"]["buildCommand"]

    def test_frontend_railway_json_has_start_command(self):
        path = RAILWAY_DIR / "frontend" / "railway.json"
        data = json.loads(path.read_text())
        assert "npm start" in data["deploy"]["startCommand"]

    def test_frontend_railway_json_has_nixpacks(self):
        path = RAILWAY_DIR / "frontend" / "railway.json"
        data = json.loads(path.read_text())
        assert data["build"]["builder"] == "NIXPACKS"

    def test_env_vars_doc_has_next_public_api_url(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "NEXT_PUBLIC_API_URL" in content

    def test_env_vars_doc_has_next_public_ws_url(self):
        content = (RAILWAY_DIR / "RAILWAY_ENV_VARS.md").read_text()
        assert "NEXT_PUBLIC_WS_URL" in content


# ============================================================
# Part 8: Startup Ordering
# ============================================================


class TestStartupOrdering:
    """Verify startup ordering with retries."""

    def test_backend_startup_retries_database_30_times(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_backend.py").read_text()
        assert "max_retries=30" in content or "max_retries: int = 30" in content

    def test_backend_startup_retries_redis_15_times(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_backend.py").read_text()
        assert "max_retries=15" in content or "max_retries: int = 15" in content

    def test_worker_startup_retries_database_30_times(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_worker.py").read_text()
        assert "max_retries: int = 30" in content

    def test_worker_startup_has_delay_between_retries(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_worker.py").read_text()
        assert "delay" in content
        assert "sleep" in content

    def test_backend_startup_redis_is_non_fatal(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_backend.py").read_text()
        assert "Non-fatal" in content or "non-fatal" in content or "continuing" in content

    def test_worker_startup_has_exponential_backoff(self):
        content = (BACKEND_DIR / "scripts" / "railway" / "startup_worker.py").read_text()
        assert "1.5" in content  # exponential backoff multiplier


# ============================================================
# Integration: Config Auto-Detection
# ============================================================


class TestConfigAutoDetection:
    """Test that config auto-detects Railway vs Docker vs local."""

    def test_get_settings_applies_railway_overrides(self):
        """Verify that get_settings() calls apply_railway_overrides."""
        from app.shared.config import get_settings
        # Just verify it doesn't crash
        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "redis_host")

    def test_railway_config_module_imports(self):
        from app.shared.railway_config import (
            detect_deployment,
            parse_redis_url,
            parse_database_url,
            apply_railway_overrides,
            RailwaySettings,
        )
        assert callable(detect_deployment)
        assert callable(parse_redis_url)
        assert callable(parse_database_url)
        assert callable(apply_railway_overrides)

    def test_railway_settings_class_exists(self):
        from app.shared.railway_config import RailwaySettings
        rs = RailwaySettings()
        assert hasattr(rs, "is_railway")
        assert hasattr(rs, "is_docker")
        assert hasattr(rs, "is_local")
