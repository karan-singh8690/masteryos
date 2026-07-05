"""Structured logging configuration using Structlog.

Every log entry includes:
- Request ID (from correlation middleware)
- Correlation ID (from X-Correlation-Id header or generated)
- Timestamp (ISO 8601)
- Logger name
- Log level
- Event message
- Structured key-value pairs
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.shared.config import LogLevel, get_settings


def _add_app_context(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to every log entry."""
    settings = get_settings()
    event_dict["app"] = settings.app_name
    event_dict["env"] = settings.app_env.value
    return event_dict


def configure_logging() -> None:
    """Configure structured logging for the application.

    Call this once at application startup.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.app_log_level.value, logging.INFO)

    # Shared processors for both structlog and stdlib logging
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_app_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.JSONRenderer()
            if settings.is_production
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=log_level,
    )

    # Route uvicorn and sqlalchemy logs through structlog
    for logger_name in ["uvicorn", "uvicorn.access", "sqlalchemy.engine"]:
        stdlib_logger = logging.getLogger(logger_name)
        stdlib_logger.handlers = []
        stdlib_logger.propagate = True


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Return a structured logger bound to the given name.

    Usage:
        logger = get_logger(__name__)
        logger.info("event_message", user_id="...", action="...")
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind key-value pairs to the current logging context.

    All subsequent log entries in the same async context will include these.
    Typically used by middleware to bind request_id, correlation_id, user_id.
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all context variables. Called at the end of each request."""
    structlog.contextvars.clear_contextvars()
