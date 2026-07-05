"""Application configuration using Pydantic Settings.

Environment-based configuration with validation.
Supports: development, testing, staging, production.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
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

    @property
    def smtp_url(self) -> str:
        """Build smtp:// URL for SMTP connections (uses starttls= scheme hint)."""
        scheme = "smtp+starttls" if self.smtp_use_tls else "smtp"
        user_part = f"{self.smtp_username}:" if self.smtp_username else ""
        pass_part = f"{self.smtp_password}@" if self.smtp_password else ""
        return f"{scheme}://{user_part}{pass_part}{self.smtp_host}:{self.smtp_port}"

    @property
    def smtp_from_address(self) -> str:
        """Build a 'Name <email>' formatted From address."""
        return f"{self.smtp_from_name} <{self.smtp_from_email}>"

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
    # Stored as string to avoid pydantic-settings trying json.loads() on it.
    # Use the `cors_origins_list` property to get the parsed list.
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Allowed CORS origins (comma-separated or single URL).",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse cors_origins string into a list, handling:
        - JSON array: '["https://example.com"]'
        - Comma-separated: 'https://a.com,https://b.com'
        - Single URL: 'https://example.com'
        - Escaped JSON from Railway: '[\\"https://example.com\\"]'
        """
        import json
        s = self.cors_origins.strip()
        if not s:
            return ["http://localhost:3000", "http://localhost:8000"]
        # If it looks like JSON array, try parsing
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
            except json.JSONDecodeError:
                # Try unescaping backslashes (Railway double-escapes)
                try:
                    unescaped = s.replace('\\"', '"')
                    parsed = json.loads(unescaped)
                    if isinstance(parsed, list):
                        return [str(x) for x in parsed]
                except json.JSONDecodeError:
                    pass
        # Treat as comma-separated
        return [origin.strip() for origin in s.split(",") if origin.strip()]

    # ================================
    # Feature flags
    # ================================
    enable_docs: bool = True
    """Enable /docs and /redoc OpenAPI UI. Disable in production."""

    # ================================
    # Closed Beta
    # ================================
    closed_beta_enabled: bool = False
    """When True, registration requires a valid invite token."""
    max_beta_users: int = 20
    """Maximum number of registered users allowed during closed beta."""
    beta_invite_token_ttl_hours: int = 168  # 7 days
    """How long invite tokens remain valid."""

    # ================================
    # Stripe (SaaS payments)
    # ================================
    stripe_secret_key: str = ""
    """Stripe API secret key. Empty = dev mode (no real payments)."""
    stripe_webhook_secret: str = ""
    """Stripe webhook signing secret."""
    stripe_publishable_key: str = ""
    """Stripe publishable key for frontend."""

    # ================================
    # AI Configuration
    # ================================
    ai_enabled: bool = False
    """Enable AI features."""
    ai_default_provider: str = "ollama"
    """Default AI provider."""
    ollama_host: str = "http://localhost:11434"
    """Ollama API host."""
    ollama_model: str = "qwen2.5:7b"
    """Default Ollama model."""
    ai_timeout: int = 30
    """AI request timeout in seconds."""
    ai_max_tokens: int = 2000
    """Max tokens for AI responses."""
    ai_temperature: float = 0.7
    """AI temperature for response generation."""

    # ================================
    # Beta Feature Flags (dynamically configurable)
    # ================================
    beta_flag_learning_enabled: bool = True
    beta_flag_content_authoring_enabled: bool = True
    beta_flag_ai_enabled: bool = False
    beta_flag_notifications_enabled: bool = True
    beta_flag_analytics_enabled: bool = True
    beta_flag_admin_console_enabled: bool = True

    # ================================
    # SMTP / Email (Task 025-deploy)
    # ================================
    smtp_host: str = "localhost"
    """SMTP server hostname (e.g. smtp.postmarkapp.com)."""
    smtp_port: int = 587
    """SMTP server port (587 for STARTTLS, 465 for implicit TLS)."""
    smtp_username: str | None = None
    """SMTP username (often the API key for providers like Postmark)."""
    smtp_password: str | None = None
    """SMTP password / API key secret."""
    smtp_use_tls: bool = True
    """Whether to use STARTTLS (port 587) or implicit TLS (port 465)."""
    smtp_from_email: str = "noreply@masteryengine.com"
    """Default From address for outbound email."""
    smtp_from_name: str = "Mastery Engine"
    """Default From display name."""
    # Frontend base URL (used to construct links in emails)
    frontend_base_url: str = "http://localhost:3000"
    """Base URL of the frontend (for building email links)."""

    # ================================
    # Observability — Sentry (Task 027-verify)
    # ================================
    sentry_dsn: str | None = None
    """Sentry DSN for error tracking. When set, Sentry SDK is initialized at startup."""

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

    Task 028: Automatically applies Railway environment variable overrides
    (DATABASE_URL, REDIS_URL, PORT) when running on Railway.
    """
    settings = Settings()

    # Task 028: Apply Railway environment overrides
    from app.shared.railway_config import apply_railway_overrides
    settings = apply_railway_overrides(settings)

    return settings
