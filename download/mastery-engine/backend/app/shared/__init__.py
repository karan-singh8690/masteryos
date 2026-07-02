"""Shared kernel — cross-cutting concerns used by all bounded contexts."""

from app.shared.config import Settings, get_settings
from app.shared.exceptions import (
    ConfigurationError,
    DomainError,
    InfrastructureError,
    MasteryEngineError,
    UseCaseError,
)
from app.shared.logging import bind_context, clear_context, configure_logging, get_logger

__all__ = [
    "Settings",
    "get_settings",
    "MasteryEngineError",
    "DomainError",
    "UseCaseError",
    "InfrastructureError",
    "ConfigurationError",
    "configure_logging",
    "get_logger",
    "bind_context",
    "clear_context",
]
