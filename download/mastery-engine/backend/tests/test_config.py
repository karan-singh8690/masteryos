"""Tests for application configuration."""

from __future__ import annotations

import pytest

from app.shared.config import AppEnvironment, Settings, get_settings


class TestSettings:
    """Tests for application settings."""

    def test_default_environment_is_development(self) -> None:
        """Default environment is development."""
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.app_env == AppEnvironment.DEVELOPMENT

    def test_is_development_flag(self) -> None:
        """is_development returns True for development env."""
        settings = Settings(app_env=AppEnvironment.DEVELOPMENT)
        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.is_testing is False

    def test_is_production_flag(self) -> None:
        """is_production returns True for production env."""
        settings = Settings(app_env=AppEnvironment.PRODUCTION)
        assert settings.is_production is True
        assert settings.is_development is False

    def test_redis_url_without_password(self) -> None:
        """Redis URL is correct without password."""
        settings = Settings(redis_host="localhost", redis_port=6379, redis_db=0)
        assert settings.redis_url == "redis://localhost:6379/0"

    def test_redis_url_with_password(self) -> None:
        """Redis URL includes password when set."""
        settings = Settings(
            redis_host="localhost", redis_port=6379, redis_db=0, redis_password="secret"
        )
        assert settings.redis_url == "redis://:secret@localhost:6379/0"

    def test_cors_origins_default(self) -> None:
        """Default CORS origins include localhost."""
        settings = Settings()
        assert "http://localhost:3000" in settings.cors_origins
        assert "http://localhost:8000" in settings.cors_origins
