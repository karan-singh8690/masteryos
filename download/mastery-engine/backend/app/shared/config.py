"""Application configuration using Pydantic Settings.

Environment-based configuration with validation.
Supports: development, testing, staging, production.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(str, Enum):
    """Supported application environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings have sensible defaults for local development.
    Production overrides are provided via environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ================================
    # Application
    # ================================
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_name: str = "mastery-engine"
    app_port: int = 8000
    app_log_level: LogLevel = LogLevel.INFO

    # ================================
    # Database
    # ================================
    database_url: str = Field(
        default="postgresql+asyncpg://mastery:changeme_in_production@localhost:5432/mastery_engine",
        description="Async PostgreSQL connection URL.",
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_echo: bool = False

    # ================================
    # Redis
    # ================================
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        """Build Redis URL from components."""
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ================================
    # Security
    # ================================
    jwt_algorithm: str = "RS256"  # Production: RS256 (asymmetric). Never HS256.
    jwt_issuer: str = "https://api.masteryengine.com"
    jwt_audience: str = "mastery-engine-api"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30
    jwt_keys_dir: str | None = None  # Path to RSA key files; None = generate ephemeral (dev only)
    jwt_clock_skew_seconds: int = 30

    # Password hashing (Argon2id)
    argon2_memory_cost: int = 19456  # KB (19 MB per OWASP 2024)
    argon2_time_cost: int = 2
    argon2_parallelism: int = 1

    # Token TTLs
    email_verification_token_ttl_hours: int = 24
    password_reset_token_ttl_minutes: int = 15

    # Session
    session_idle_timeout_minutes: int = 60
    session_absolute_timeout_days: int = 30

    # ================================
    # CORS
    # ================================
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins.",
    )

    # ================================
    # Feature flags
    # ================================
    enable_docs: bool = True
    """Enable /docs and /redoc OpenAPI UI. Disable in production."""

    # ================================
    # Validators
    # ================================

    @field_validator("app_env")
    @classmethod
    def validate_env(cls, v: AppEnvironment) -> AppEnvironment:
        """Ensure environment is valid."""
        return v

    # ================================
    # Convenience properties
    # ================================

    @property
    def is_production(self) -> bool:
        """True when running in production."""
        return self.app_env == AppEnvironment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        """True when running tests."""
        return self.app_env == AppEnvironment.TESTING

    @property
    def is_development(self) -> bool:
        """True when running in development."""
        return self.app_env == AppEnvironment.DEVELOPMENT


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance.

    The cache ensures settings are loaded only once per process.
    Call `get_settings.cache_clear()` to reload (e.g., in tests).
    """
    return Settings()
