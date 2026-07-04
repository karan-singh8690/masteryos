"""Railway-native environment configuration (Task 028).

Extends the base Settings class to support Railway's environment variable
conventions:
  - DATABASE_URL (Railway PostgreSQL plugin provides this directly)
  - REDIS_URL (Railway Redis plugin provides this directly)
  - PORT (Railway sets this for each service)

Auto-detects the deployment environment (Railway, Docker, local) and
configures connections accordingly — no code duplication.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def detect_deployment() -> str:
    """Detect the current deployment environment.

    Returns one of: 'railway', 'docker', 'local'
    """
    # Railway sets these environment variables
    if os.environ.get("RAILWAY_PROJECT_ID") or os.environ.get("RAILWAY_SERVICE_ID"):
        return "railway"
    # Docker: check for .dockerenv file or DOCKER_CONTAINER env var
    if os.environ.get("DOCKER_CONTAINER") or os.path.exists("/.dockerenv"):
        return "docker"
    return "local"


def parse_redis_url(url: str) -> dict[str, Any]:
    """Parse a Redis URL into host, port, password, db components.

    Supports: redis://[:password@]host:port/db
    """
    result: dict[str, Any] = {"host": "localhost", "port": 6379, "password": "", "db": 0}
    if not url:
        return result

    # Strip redis:// prefix
    stripped = url
    if stripped.startswith("redis://"):
        stripped = stripped[8:]
    elif stripped.startswith("rediss://"):
        stripped = stripped[9:]

    # Extract password
    if "@" in stripped:
        auth, stripped = stripped.rsplit("@", 1)
        if ":" in auth:
            result["password"] = auth.split(":", 1)[1]
        else:
            result["password"] = auth

    # Extract db
    if "/" in stripped:
        host_port, db_str = stripped.rsplit("/", 1)
        try:
            result["db"] = int(db_str)
        except ValueError:
            pass
    else:
        host_port = stripped

    # Extract host and port
    if ":" in host_port:
        result["host"], port_str = host_port.rsplit(":", 1)
        try:
            result["port"] = int(port_str)
        except ValueError:
            pass
    else:
        result["host"] = host_port

    return result


def parse_database_url(url: str) -> str:
    """Normalize a DATABASE_URL for asyncpg.

    Railway provides DATABASE_URL as: postgresql://user:pass@host:port/db
    asyncpg needs: postgresql+asyncpg://user:pass@host:port/db

    This function ensures the +asyncpg driver is present.
    """
    if not url:
        return url

    # If already has +asyncpg, return as-is
    if "+asyncpg" in url:
        return url

    # Replace postgresql:// with postgresql+asyncpg://
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Replace postgres:// (older format) with postgresql+asyncpg://
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)

    return url


def get_railway_port(default: int = 8000) -> int:
    """Get the port Railway assigned to this service."""
    return int(os.environ.get("PORT", default))


class RailwaySettings(BaseSettings):
    """Railway-specific deployment settings.

    These are loaded ON TOP of the base Settings class via model_validator.
    Railway provides DATABASE_URL and REDIS_URL directly from its plugins,
    so we need to parse those into the individual components the app expects.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Railway-provided (auto-set by Railway plugins)
    database_url_railway: str | None = None
    """Raw DATABASE_URL from Railway PostgreSQL plugin (postgresql://...)."""
    redis_url_railway: str | None = None
    """Raw REDIS_URL from Railway Redis plugin (redis://...)."""
    port: int | None = None
    """Port assigned by Railway (auto-set via PORT env var)."""

    @property
    def deployment_type(self) -> str:
        """Detect the deployment type."""
        return detect_deployment()

    @property
    def is_railway(self) -> bool:
        return self.deployment_type == "railway"

    @property
    def is_docker(self) -> bool:
        return self.deployment_type == "docker"

    @property
    def is_local(self) -> bool:
        return self.deployment_type == "local"


def apply_railway_overrides(settings: Any) -> Any:
    """Apply Railway environment variable overrides to a Settings instance.

    This function is called after the base Settings is loaded. It checks for
    Railway-provided environment variables and overrides the corresponding
    settings fields.

    Supported Railway variables:
      - DATABASE_URL → overrides database_url (converted to +asyncpg)
      - REDIS_URL → overrides redis_host, redis_port, redis_password, redis_db
      - PORT → overrides app_port
    """
    import os

    # DATABASE_URL override (Railway PostgreSQL plugin)
    raw_db_url = os.environ.get("DATABASE_URL")
    if raw_db_url:
        settings.database_url = parse_database_url(raw_db_url)

    # REDIS_URL override (Railway Redis plugin)
    raw_redis_url = os.environ.get("REDIS_URL")
    if raw_redis_url:
        redis_parts = parse_redis_url(raw_redis_url)
        settings.redis_host = redis_parts["host"]
        settings.redis_port = redis_parts["port"]
        settings.redis_password = redis_parts["password"]
        settings.redis_db = redis_parts["db"]

    # PORT override (Railway sets PORT for each service)
    raw_port = os.environ.get("PORT")
    if raw_port:
        try:
            settings.app_port = int(raw_port)
        except (ValueError, TypeError):
            pass

    return settings


__all__ = [
    "RailwaySettings",
    "detect_deployment",
    "parse_redis_url",
    "parse_database_url",
    "get_railway_port",
    "apply_railway_overrides",
]
