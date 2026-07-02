"""Base exception classes for the Mastery Engine.

Domain exceptions are raised by Domain Services and caught by Use Case Services.
Use Case exceptions are caught by the presentation layer and translated to HTTP responses.
"""

from __future__ import annotations

from typing import Any


class MasteryEngineError(Exception):
    """Base exception for all Mastery Engine errors."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DomainError(MasteryEngineError):
    """Raised by Domain Services when a business rule is violated."""


class UseCaseError(MasteryEngineError):
    """Raised by Use Case Services when an orchestration invariant is violated.

    These are caught by the presentation layer and translated to 4xx responses.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = 422,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.code = code
        self.status_code = status_code


class InfrastructureError(MasteryEngineError):
    """Raised by infrastructure components (database, cache, external services)."""


class ConfigurationError(MasteryEngineError):
    """Raised when configuration is invalid or missing."""
