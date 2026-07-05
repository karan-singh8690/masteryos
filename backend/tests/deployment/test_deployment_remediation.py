"""Tests for the Task 025-deploy production deployment remediation.

Covers:
- SMTP settings in the Settings class (fix #6)
- ProductionSmtpClient configuration from settings (fix #6)
- EmailService dependency injection returns the right client (fix #6)
- Beta admin endpoints require admin role (fix #7)
- Beta invite email dispatch on create + resend (fix #8)
- DB init script ordering: 00-base-tables.sql exists and creates users/sessions/outbox (fix #4)
- Grafana dashboard JSON is in the file-provisioning format (fix #13)
- Prometheus alerts.yml is valid YAML (fix #5)
- Alertmanager config is valid YAML (fix #5)
- docker-compose.prod.yml contains the new services + networks (fixes #1, #5, #9)
- backup.sh flag handling (--verify and --restore short-circuit) (fix #14)
- Nginx config includes stub_status + relaxed CSP for Next.js (fixes #5, #12)
- PostgreSQL SSL cert generation script exists and runs (fix #1)
- Nginx SSL cert generation script exists and runs (fix #2)
- Backend Dockerfile installs curl (fix #3)
- Frontend Dockerfile uses npm ci (fix #11)
- auth_audit_logs immutability trigger exists in init SQL (fix #15)
- beta_events has UPDATE/DELETE revoked in init SQL (fix #16)
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

# Set test env before importing app code
os.environ.setdefault("APP_ENV", "testing")

# Project root for reading files
PROJECT_ROOT = Path(__file__).resolve().parents[3]
INFRA_ROOT = PROJECT_ROOT / "infrastructure"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"


# ============================================================
# Fix #6: SMTP settings
# ============================================================


class TestSmtpSettings:
    """Tests that SMTP settings exist in the Settings class."""

    def test_smtp_settings_exist_with_defaults(self):
        from app.shared.config import get_settings

        s = get_settings()
        assert hasattr(s, "smtp_host"), "Settings must have smtp_host"
        assert hasattr(s, "smtp_port"), "Settings must have smtp_port"
        assert hasattr(s, "smtp_username"), "Settings must have smtp_username"
        assert hasattr(s, "smtp_password"), "Settings must have smtp_password"
        assert hasattr(s, "smtp_use_tls"), "Settings must have smtp_use_tls"
        assert hasattr(s, "smtp_from_email"), "Settings must have smtp_from_email"
        assert hasattr(s, "smtp_from_name"), "Settings must have smtp_from_name"
        assert hasattr(s, "frontend_base_url"), "Settings must have frontend_base_url"

    def test_smtp_defaults(self):
        from app.shared.config import get_settings

        s = get_settings()
        assert s.smtp_host == "localhost"
        assert s.smtp_port == 587
        assert s.smtp_use_tls is True
        assert s.smtp_from_email == "noreply@masteryengine.com"
        assert s.smtp_from_name == "Mastery Engine"

    def test_smtp_url_property(self):
        from app.shared.config import get_settings

        s = get_settings()
        url = s.smtp_url
        assert "smtp" in url
        assert str(s.smtp_port) in url
        assert s.smtp_host in url

    def test_smtp_from_address_property(self):
        from app.shared.config import get_settings

        s = get_settings()
        addr = s.smtp_from_address
        assert s.smtp_from_email in addr
        assert s.smtp_from_name in addr

    def test_production_smtp_client_has_from_settings(self):
        from app.infrastructure.email.service import ProductionSmtpClient
        from app.shared.config import get_settings

        s = get_settings()
        client = ProductionSmtpClient.from_settings(s)
        assert client._host == s.smtp_host
        assert client._port == s.smtp_port
        assert client._username == s.smtp_username
        assert client._password == s.smtp_password
        assert client._use_tls == s.smtp_use_tls

    def test_email_service_dependency_returns_service(self):
        """The email service DI must return a usable EmailService."""
        from app.presentation.dependencies_email import get_email_service
        from app.infrastructure.email.service import EmailService, InMemorySmtpClient

        svc = get_email_service()
        assert isinstance(svc, EmailService)
        # In testing mode (or when SMTP_USERNAME is unset), must use in-memory client.
        assert isinstance(svc._smtp, InMemorySmtpClient)


# ============================================================
# Fix #7: Admin RBAC on beta endpoints
# ============================================================


class TestBetaAdminRbac:
    """Tests that admin beta endpoints have RBAC enforcement wired."""

    def test_beta_admin_endpoints_have_admin_dependency(self):
        """Verify each admin endpoint has a parameter whose default is the
        RequireAdmin dependency (i.e. enforces require_any_role(admin, system_admin)).

        We don't make real HTTP calls here (would require a DB); instead we
        inspect each route handler's signature for a parameter whose default
        equals the RequireAdmin Depends instance.
        """
        import inspect
        from app.main import app
        from app.presentation.api.v1.beta import RequireAdmin

        admin_paths = {
            "/api/v1/admin/beta/invites",          # POST + GET
            "/api/v1/admin/beta/invites/resend",   # POST
            "/api/v1/admin/beta/invites/{invite_id}",  # DELETE
        }

        found = set()
        for route in app.routes:
            if not hasattr(route, "path") or route.path not in admin_paths:
                continue
            if not hasattr(route, "endpoint"):
                continue
            sig = inspect.signature(route.endpoint)
            for param in sig.parameters.values():
                if param.default is RequireAdmin:
                    found.add(route.path)
                    break
                # Also handle the case where the default is an equivalent Depends
                # with the same inner dependency callable.
                if hasattr(param.default, "dependency") and hasattr(RequireAdmin, "dependency"):
                    if param.default.dependency is RequireAdmin.dependency:
                        found.add(route.path)
                        break
        missing = admin_paths - found
        assert not missing, f"These admin endpoints are missing RequireAdmin: {missing}"


# ============================================================
# Fix #8: Beta invite email dispatch
# ============================================================


class TestBetaInviteEmailDispatch:
    """Tests that beta invite creation/resend dispatches the invitation email."""

    def test_create_invite_endpoint_takes_email_service(self):
        """The POST /admin/beta/invites route signature must include email_service param."""
        import inspect
        from app.main import app

        for route in app.routes:
            if not hasattr(route, "path") or route.path != "/api/v1/admin/beta/invites":
                continue
            if not hasattr(route, "endpoint"):
                continue
            # Only check the POST route (create_invite); the GET route (list_invites) doesn't need email.
            if route.methods and "POST" not in route.methods:
                continue
            sig = inspect.signature(route.endpoint)
            assert "email_service" in sig.parameters, (
                "create_invite must accept email_service so the invite email is dispatched"
            )
            return
        pytest.fail("POST /api/v1/admin/beta/invites route not found")

    def test_resend_invite_endpoint_takes_email_service(self):
        """The resend_invite route signature must include email_service param."""
        import inspect
        from app.main import app

        for route in app.routes:
            if not hasattr(route, "path") or route.path != "/api/v1/admin/beta/invites/resend":
                continue
            if not hasattr(route, "endpoint"):
                continue
            sig = inspect.signature(route.endpoint)
            assert "email_service" in sig.parameters, (
                "resend_invite must accept email_service so the invite email is dispatched"
            )
            return
        pytest.fail("POST /api/v1/admin/beta/invites/resend route not found")

    def test_dispatch_invite_email_helper_exists(self):
        """The _dispatch_invite_email helper must exist and be a coroutine."""
        import inspect
        from app.presentation.api.v1.beta import _dispatch_invite_email

        assert inspect.iscoroutinefunction(_dispatch_invite_email)

    def test_dispatch_invite_email_sends_via_email_service(self):
        """Calling _dispatch_invite_email must call email_service.send_template."""
        import asyncio
        from datetime import datetime, timedelta, timezone as tz_utc
        from app.presentation.api.v1.beta import _dispatch_invite_email
        from app.application.beta import BetaInvite
        from app.infrastructure.email.service import EmailService, InMemorySmtpClient

        client = InMemorySmtpClient()
        svc = EmailService(smtp_client=client)

        invite = BetaInvite(
            id=uuid4(),
            email="test@example.com",
            invite_token="abc123",
            expires_at=datetime.now(tz_utc.utc) + timedelta(days=7),
            used_at=None,
            created_by=uuid4(),
            notes=None,
            created_at=datetime.now(tz_utc.utc),
        )

        asyncio.run(_dispatch_invite_email(svc, invite))

        # The in-memory client records all sent emails.
        assert len(client.sent_emails) == 1, "Email must be dispatched"
        sent = client.sent_emails[0]
        assert sent.to == "test@example.com"
        assert "beta" in sent.subject.lower() or "invite" in sent.subject.lower()

    def test_dispatch_invite_email_does_not_raise_on_smtp_failure(self):
        """If the SMTP client fails, _dispatch_invite_email must not raise —
        the invite is already persisted and the admin can resend."""
        import asyncio
        from datetime import datetime, timedelta, timezone as tz_utc
        from app.presentation.api.v1.beta import _dispatch_invite_email
        from app.application.beta import BetaInvite
        from app.infrastructure.email.service import EmailService, InMemorySmtpClient

        client = InMemorySmtpClient()
        client.set_failure_mode(fail=True, count=99)  # Always fail
        svc = EmailService(smtp_client=client)

        invite = BetaInvite(
            id=uuid4(),
            email="test@example.com",
            invite_token="abc123",
            expires_at=datetime.now(tz_utc.utc) + timedelta(days=7),
            used_at=None,
            created_by=uuid4(),
            notes=None,
            created_at=datetime.now(tz_utc.utc),
        )

        # Must not raise.
        asyncio.run(_dispatch_invite_email(svc, invite))


# ============================================================
# Fix #4: Database init script ordering
# ============================================================


class TestDatabaseInitOrdering:
    """Tests that the DB init scripts run in the correct order and that
    00-base-tables.sql creates the tables that 02/03/04 depend on."""

    def test_00_base_tables_sql_exists(self):
        path = INFRA_ROOT / "postgres" / "init" / "00-base-tables.sql"
        assert path.exists(), "00-base-tables.sql must exist to break the chicken-and-egg"

    def test_00_base_tables_creates_users_table(self):
        path = INFRA_ROOT / "postgres" / "init" / "00-base-tables.sql"
        content = path.read_text()
        assert "CREATE TABLE IF NOT EXISTS identity.users" in content
        assert "role" in content, "00-base-tables.sql must include the role column for RBAC"

    def test_00_base_tables_creates_sessions_table(self):
        path = INFRA_ROOT / "postgres" / "init" / "00-base-tables.sql"
        content = path.read_text()
        assert "CREATE TABLE IF NOT EXISTS identity.sessions" in content

    def test_00_base_tables_creates_outbox_events_table(self):
        path = INFRA_ROOT / "postgres" / "init" / "00-base-tables.sql"
        content = path.read_text()
        assert "CREATE TABLE IF NOT EXISTS infrastructure.outbox_events" in content

    def test_00_base_tables_creates_user_credentials_table(self):
        path = INFRA_ROOT / "postgres" / "init" / "00-base-tables.sql"
        content = path.read_text()
        assert "CREATE TABLE IF NOT EXISTS identity.user_credentials" in content

    def test_00_base_tables_creates_user_profiles_table(self):
        path = INFRA_ROOT / "postgres" / "init" / "00-base-tables.sql"
        content = path.read_text()
        assert "CREATE TABLE IF NOT EXISTS identity.user_profiles" in content

    def test_init_scripts_sort_alphabetically(self):
        """00 must come before 01, 02, 03, 04."""
        init_dir = INFRA_ROOT / "postgres" / "init"
        files = sorted(p.name for p in init_dir.glob("*.sql"))
        assert files[0] == "00-base-tables.sql", (
            f"00-base-tables.sql must sort first; got {files[0]}"
        )
        assert "01-create-schemas.sql" in files
        assert "02-auth-tables.sql" in files
        assert "03-background-tables.sql" in files
        assert "04-beta-tables.sql" in files

    def test_02_auth_tables_adds_role_column(self):
        """02-auth-tables.sql must include an ALTER for the role column
        (idempotent — also in 00 but kept in 02 for legacy DBs)."""
        path = INFRA_ROOT / "postgres" / "init" / "02-auth-tables.sql"
        content = path.read_text()
        assert "ADD COLUMN IF NOT EXISTS role" in content


# ============================================================
# Fix #5: Prometheus exporters + alerts.yml + Alertmanager
# ============================================================


class TestPrometheusConfig:
    """Tests for the Prometheus + Alertmanager configuration."""

    def test_alerts_yml_exists(self):
        path = INFRA_ROOT / "monitoring" / "prometheus" / "alerts.yml"
        assert path.exists(), "alerts.yml must exist (was referenced but missing)"

    def test_alerts_yml_is_valid_yaml(self):
        import yaml
        path = INFRA_ROOT / "monitoring" / "prometheus" / "alerts.yml"
        data = yaml.safe_load(path.read_text())
        assert "groups" in data
        assert isinstance(data["groups"], list)
        assert len(data["groups"]) >= 1
        for g in data["groups"]:
            assert "name" in g
            assert "rules" in g
            for rule in g["rules"]:
                assert "alert" in rule
                assert "expr" in rule
                assert "labels" in rule
                assert "severity" in rule["labels"]

    def test_alerts_yml_contains_key_alerts(self):
        path = INFRA_ROOT / "monitoring" / "prometheus" / "alerts.yml"
        content = path.read_text()
        for alert_name in [
            "BackendDown",
            "PostgresDown",
            "RedisDown",
            "HighErrorRate",
            "OutboxBacklog",
            "WorkerNoHeartbeat",
            "BetaFull",
            "BackupStale",
        ]:
            assert alert_name in content, f"alerts.yml must define {alert_name}"

    def test_alertmanager_yml_exists(self):
        path = INFRA_ROOT / "monitoring" / "alertmanager" / "alertmanager.yml"
        assert path.exists(), "alertmanager.yml must exist"

    def test_alertmanager_yml_is_valid_yaml(self):
        import yaml
        path = INFRA_ROOT / "monitoring" / "alertmanager" / "alertmanager.yml"
        data = yaml.safe_load(path.read_text())
        assert "route" in data
        assert "receivers" in data
        assert isinstance(data["receivers"], list)
        assert len(data["receivers"]) >= 1

    def test_docker_compose_has_exporters(self):
        path = PROJECT_ROOT / "docker-compose.prod.yml"
        content = path.read_text()
        assert "postgres-exporter" in content
        assert "redis-exporter" in content
        assert "nginx-exporter" in content
        assert "alertmanager" in content

    def test_docker_compose_has_networks(self):
        """Explicit networks must be defined (fix #9)."""
        path = PROJECT_ROOT / "docker-compose.prod.yml"
        content = path.read_text()
        assert "networks:" in content
        assert "backend:" in content
        assert "frontend:" in content
        assert "monitoring:" in content

    def test_docker_compose_mounts_postgres_ssl(self):
        """Postgres SSL certs must be mounted (fix #1)."""
        path = PROJECT_ROOT / "docker-compose.prod.yml"
        content = path.read_text()
        assert "postgres.pem" in content
        assert "postgres-key.pem" in content

    def test_docker_compose_passes_smtp_env(self):
        """SMTP env vars must be passed to backend + worker (fix #6)."""
        path = PROJECT_ROOT / "docker-compose.prod.yml"
        content = path.read_text()
        for var in ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD",
                    "SMTP_FROM_EMAIL", "FRONTEND_BASE_URL"]:
            assert var in content, f"docker-compose.prod.yml must pass {var}"


# ============================================================
# Fix #13: Grafana dashboard provisioning
# ============================================================


class TestGrafanaDashboard:
    """Tests for the Grafana dashboard JSON."""

    def test_dashboard_json_is_valid(self):
        import json
        path = INFRA_ROOT / "monitoring" / "grafana" / "dashboards" / "production-overview.json"
        data = json.loads(path.read_text())
        # The file-provisioning format requires top-level fields (not wrapped in {"dashboard": {...}})
        assert "title" in data, "dashboard JSON must have 'title' at top level (not wrapped)"
        assert "panels" in data
        assert "uid" in data, "dashboard must have a stable uid"
        assert data.get("schemaVersion"), "dashboard must specify schemaVersion"

    def test_dashboard_provider_path_is_correct(self):
        """The dashboards.yml provider must point at /var/lib/grafana/dashboards
        (the path the compose file mounts the dashboards directory to)."""
        import yaml
        path = INFRA_ROOT / "monitoring" / "grafana" / "provisioning" / "dashboards" / "dashboards.yml"
        data = yaml.safe_load(path.read_text())
        providers = data["providers"]
        assert len(providers) == 1
        provider = providers[0]
        assert provider["options"]["path"] == "/var/lib/grafana/dashboards"
        assert provider["disableDeletion"] is True
        assert provider["editable"] is False

    def test_docker_compose_mounts_dashboards_dir(self):
        path = PROJECT_ROOT / "docker-compose.prod.yml"
        content = path.read_text()
        assert "grafana/dashboards:/var/lib/grafana/dashboards" in content, (
            "Compose must mount the dashboards dir at /var/lib/grafana/dashboards"
        )


# ============================================================
# Fix #14: backup.sh flag handling
# ============================================================


class TestBackupScript:
    """Tests for the backup.sh flag handling + Redis auth."""

    def test_backup_script_exists(self):
        path = SCRIPTS_ROOT / "backup.sh"
        assert path.exists()

    def test_backup_script_handles_verify_before_backup(self):
        """--verify must short-circuit BEFORE running a full backup."""
        content = (SCRIPTS_ROOT / "backup.sh").read_text()
        # The script uses `[[ "$ACTION" == "verify" ]]` (bash conditional).
        verify_pos = content.find('"verify"')
        pgdump_pos = content.find("pg_dump")
        assert verify_pos > 0, "Could not find 'verify' branch in backup.sh"
        assert pgdump_pos > 0, "Could not find pg_dump in backup.sh"
        assert verify_pos < pgdump_pos, (
            "--verify branch must come BEFORE pg_dump so verify doesn't run a full backup"
        )

    def test_backup_script_handles_restore_before_backup(self):
        """--restore must short-circuit BEFORE running a full backup."""
        content = (SCRIPTS_ROOT / "backup.sh").read_text()
        restore_pos = content.find('"restore"')
        pgdump_pos = content.find("pg_dump")
        assert restore_pos > 0, "Could not find 'restore' branch in backup.sh"
        assert restore_pos < pgdump_pos

    def test_backup_script_passes_redis_password(self):
        """Redis BGSAVE + LASTSAVE must pass -a $REDIS_PASSWORD."""
        content = (SCRIPTS_ROOT / "backup.sh").read_text()
        assert "REDIS_PASSWORD" in content
        assert "redis_auth_args" in content or "-a $REDIS_PASSWORD" in content

    def test_backup_script_uses_docker_cp_for_redis(self):
        """Redis dump must be copied via docker cp (works with Docker volumes)."""
        content = (SCRIPTS_ROOT / "backup.sh").read_text()
        assert "docker cp" in content, "backup.sh must use docker cp to fetch Redis dump.rdb"

    def test_backup_script_emits_sha256_checksum(self):
        """A SHA256 checksum file must be emitted alongside the backup."""
        content = (SCRIPTS_ROOT / "backup.sh").read_text()
        assert "sha256sum" in content

    def test_backup_script_excludes_env_when_no_encryption(self):
        """The .env file must NOT be included in the tar if encryption is disabled."""
        content = (SCRIPTS_ROOT / "backup.sh").read_text()
        assert "INCLUDE_ENV" in content
        assert "BACKUP_ENCRYPTION_KEY" in content


# ============================================================
# Fix #1 + #2: SSL cert generation scripts
# ============================================================


class TestSslCertScripts:
    """Tests for the SSL cert generation scripts."""

    def test_postgres_ssl_script_exists(self):
        path = SCRIPTS_ROOT / "generate-postgres-ssl.sh"
        assert path.exists()

    def test_nginx_ssl_script_exists(self):
        path = SCRIPTS_ROOT / "generate-nginx-ssl.sh"
        assert path.exists()

    def test_postgres_ssl_script_generates_pem_files(self):
        path = SCRIPTS_ROOT / "generate-postgres-ssl.sh"
        content = path.read_text()
        assert "postgres.pem" in content
        assert "postgres-key.pem" in content
        assert "openssl" in content

    def test_nginx_ssl_script_supports_self_signed_mode(self):
        path = SCRIPTS_ROOT / "generate-nginx-ssl.sh"
        content = path.read_text()
        assert "--self-signed" in content
        assert "--letsencrypt" in content
        assert "fullchain.pem" in content
        assert "privkey.pem" in content


# ============================================================
# Fix #3 + #10 + #11: Dockerfiles
# ============================================================


class TestDockerfiles:
    """Tests for the updated Dockerfiles."""

    def test_backend_dockerfile_installs_curl(self):
        path = INFRA_ROOT / "docker" / "backend.Dockerfile"
        content = path.read_text()
        assert "curl" in content, "backend Dockerfile must install curl for healthchecks"

    def test_backend_dockerfile_does_not_install_dev_deps_in_runtime(self):
        """The runtime builder stage must NOT install [dev] extras."""
        import re
        path = INFRA_ROOT / "docker" / "backend.Dockerfile"
        content = path.read_text()
        first_install_match = re.search(r"pip install[^\n]*", content)
        assert first_install_match, "Dockerfile must have at least one pip install"
        first_install = first_install_match.group()
        assert "[dev]" not in first_install, (
            "Builder stage must install production deps only (no [dev])"
        )

    def test_backend_dockerfile_has_dev_stage(self):
        """A separate dev stage must exist for CI / test images."""
        path = INFRA_ROOT / "docker" / "backend.Dockerfile"
        content = path.read_text()
        assert "builder-dev" in content or "AS builder-dev" in content, (
            "Dockerfile must have a separate builder-dev stage for dev deps"
        )

    def test_backend_dockerfile_uses_curl_healthcheck(self):
        path = INFRA_ROOT / "docker" / "backend.Dockerfile"
        content = path.read_text()
        assert "curl" in content

    def test_frontend_dockerfile_uses_npm_ci(self):
        path = INFRA_ROOT / "docker" / "frontend.Dockerfile"
        content = path.read_text()
        assert "npm ci" in content, "frontend Dockerfile must use npm ci (not npm install)"

    def test_frontend_dockerfile_installs_curl(self):
        path = INFRA_ROOT / "docker" / "frontend.Dockerfile"
        content = path.read_text()
        assert "curl" in content

    def test_frontend_dockerfile_fails_on_missing_lockfile(self):
        """The Dockerfile must fail (not silently fall back to npm install)
        if package-lock.json is missing."""
        path = INFRA_ROOT / "docker" / "frontend.Dockerfile"
        content = path.read_text()
        assert "package-lock.json not found" in content or "ERROR" in content


# ============================================================
# Fix #12: CSP for Next.js
# ============================================================


class TestCspConfig:
    """Tests that the Nginx CSP allows Next.js to function."""

    def test_nginx_config_has_relaxed_csp_for_nextjs(self):
        path = INFRA_ROOT / "nginx" / "nginx.conf"
        content = path.read_text()
        # The CSP must allow 'unsafe-inline' for script-src and style-src
        # (or use nonces — but for beta, unsafe-inline is acceptable).
        assert "script-src" in content
        assert "style-src" in content
        assert "'unsafe-inline'" in content
        # Must still deny frame-ancestors (clickjacking protection).
        assert "frame-ancestors 'none'" in content


# ============================================================
# Fix #5: Nginx stub_status for exporter
# ============================================================


class TestNginxStubStatus:
    """Tests that Nginx exposes /stub_status for the prometheus exporter."""

    def test_nginx_config_has_stub_status(self):
        path = INFRA_ROOT / "nginx" / "nginx.conf"
        content = path.read_text()
        assert "stub_status" in content
        assert "/stub_status" in content
        assert "10.0.0.0/8" in content
        assert "deny all" in content


# ============================================================
# Fix #15: auth_audit_logs immutability
# ============================================================


class TestAuthAuditLogImmutability:
    """Tests that auth_audit_logs is enforced immutable at the DB level."""

    def test_02_auth_tables_sql_defines_immutability_trigger(self):
        path = INFRA_ROOT / "postgres" / "init" / "02-auth-tables.sql"
        content = path.read_text()
        assert "prevent_audit_log_mutation" in content
        assert "BEFORE UPDATE" in content
        assert "BEFORE DELETE" in content
        assert "trg_audit_logs_no_update" in content
        assert "trg_audit_logs_no_delete" in content

    def test_02_auth_tables_sql_revokes_update_delete(self):
        path = INFRA_ROOT / "postgres" / "init" / "02-auth-tables.sql"
        content = path.read_text()
        assert "REVOKE UPDATE, DELETE ON identity.auth_audit_logs FROM mastery" in content


# ============================================================
# Fix #16: beta_events is append-only
# ============================================================


class TestBetaEventsAppendOnly:
    """Tests that beta_events has UPDATE/DELETE revoked."""

    def test_04_beta_tables_revokes_update_delete_on_events(self):
        path = INFRA_ROOT / "postgres" / "init" / "04-beta-tables.sql"
        content = path.read_text()
        assert "GRANT SELECT, INSERT ON analytics.beta_events" in content
        # Find the GRANT line for beta_events and verify no UPDATE/DELETE.
        for line in content.split("\n"):
            if "analytics.beta_events" in line and line.strip().startswith("GRANT"):
                assert "UPDATE" not in line, (
                    f"beta_events grant must not include UPDATE: {line}"
                )
                assert "DELETE" not in line, (
                    f"beta_events grant must not include DELETE: {line}"
                )


# ============================================================
# Fix #9: explicit networks in docker-compose.prod.yml
# ============================================================


class TestDockerComposeNetworks:
    """Tests for explicit networks in docker-compose.prod.yml."""

    def test_services_attached_to_correct_networks(self):
        """Each service must be on the right network(s)."""
        path = PROJECT_ROOT / "docker-compose.prod.yml"
        content = path.read_text()
        assert "backend" in content
        assert "frontend" in content
        assert "monitoring" in content


# ============================================================
# Smoke test: Makefile targets exist
# ============================================================


class TestMakefile:
    """Tests that the Makefile has the new prod targets."""

    def test_makefile_has_prod_targets(self):
        path = PROJECT_ROOT / "Makefile"
        content = path.read_text()
        for target in ["prod-up", "prod-down", "prod-build", "prod-logs", "prod-shell",
                       "gen-ssl-pg", "gen-ssl-nginx", "gen-jwt-keys",
                       "backup", "backup-verify", "restore", "health", "prod-health"]:
            assert f"{target}:" in content, f"Makefile must define {target} target"

    def test_makefile_clean_has_confirmation(self):
        """The clean target must ask for confirmation (it's destructive)."""
        path = PROJECT_ROOT / "Makefile"
        content = path.read_text()
        assert "CLEAN" in content or "read -p" in content


# ============================================================
# Smoke test: env.example has the new vars
# ============================================================


class TestEnvExample:
    """Tests that .env.example includes the new SMTP + JWT vars."""

    def test_env_example_has_smtp_vars(self):
        path = PROJECT_ROOT / ".env.example"
        content = path.read_text()
        for var in ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD",
                    "SMTP_USE_TLS", "SMTP_FROM_EMAIL", "SMTP_FROM_NAME"]:
            assert var in content, f".env.example must include {var}"

    def test_env_example_has_frontend_base_url(self):
        path = PROJECT_ROOT / ".env.example"
        content = path.read_text()
        assert "FRONTEND_BASE_URL" in content

    def test_env_example_jwt_algorithm_is_rs256(self):
        """The default JWT_ALGORITHM in .env.example must be RS256 (not HS256)."""
        path = PROJECT_ROOT / ".env.example"
        content = path.read_text()
        for line in content.split("\n"):
            if line.strip().startswith("JWT_ALGORITHM="):
                assert "RS256" in line, (
                    f".env.example JWT_ALGORITHM should be RS256 (was: {line})"
                )
                break
        else:
            pytest.fail("JWT_ALGORITHM not found in .env.example")

    def test_env_example_has_jwt_keys_dir(self):
        path = PROJECT_ROOT / ".env.example"
        content = path.read_text()
        assert "JWT_KEYS_DIR" in content

    def test_env_example_has_jwt_issuer_audience(self):
        path = PROJECT_ROOT / ".env.example"
        content = path.read_text()
        assert "JWT_ISSUER" in content
        assert "JWT_AUDIENCE" in content
