"""AI Provider Abstraction — vendor-independent interface for all AI providers.

The Rule Engine always owns:
- Correct answer validation
- Scoring
- Mastery computation
- Review scheduling
- Adaptive queue ordering
- Achievement logic

AI may only consume the outputs of those systems.

All providers implement identical interfaces.
No application code depends on any vendor SDK.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone as tz_utc
from enum import Enum
from typing import Any, AsyncGenerator
from uuid import UUID, uuid4

from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Enums
# ============================================================


class AIProviderType(str, Enum):
    """Supported AI provider types."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class AIRequestStatus(str, Enum):
    """Status of an AI request."""
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    REJECTED = "rejected"  # Rejected by safety layer


class PromptApprovalState(str, Enum):
    """Approval state for AI-generated content."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"


class SafetyVerdict(str, Enum):
    """Safety validation verdict."""
    SAFE = "safe"
    UNSAFE = "unsafe"
    REQUIRES_REVIEW = "requires_review"


# ============================================================
# Data Classes
# ============================================================


@dataclass(frozen=True)
class AIRequest:
    """A request to an AI provider."""
    id: UUID
    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 2048
    max_context: int = 4096
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    # For audit
    prompt_version: str | None = None
    request_type: str = "generic"
    user_id: UUID | None = None

    @classmethod
    def create(
        cls,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        request_type: str = "generic",
        user_id: UUID | None = None,
        prompt_version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AIRequest:
        return cls(
            id=uuid4(),
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            request_type=request_type,
            user_id=user_id,
            prompt_version=prompt_version,
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class AIResponse:
    """A response from an AI provider."""
    request_id: UUID
    content: str
    model: str
    provider: AIProviderType
    # Token accounting
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    # Cost accounting (in USD cents)
    cost_cents: int = 0
    # Metadata
    latency_ms: int = 0
    response_id: str | None = None  # Provider-specific response ID
    finish_reason: str | None = None
    # Safety
    safety_verdict: SafetyVerdict = SafetyVerdict.SAFE
    safety_notes: str | None = None
    # Confidence (0.0-1.0) — model's self-reported confidence
    confidence: float = 0.5


@dataclass(frozen=True)
class AIStreamChunk:
    """A chunk from a streaming AI response."""
    request_id: UUID
    content: str
    is_final: bool = False
    total_tokens: int = 0


@dataclass
class AIProviderConfig:
    """Configuration for an AI provider."""
    provider_type: AIProviderType
    enabled: bool = True
    # Provider-specific settings
    host: str | None = None  # For Ollama
    api_key: str | None = None  # For cloud providers
    default_model: str | None = None
    timeout_seconds: int = 30
    max_retries: int = 2
    # Rate limiting
    requests_per_minute: int = 60
    # Cost tracking
    cost_per_1k_input_cents: int = 0
    cost_per_1k_output_cents: int = 0


# ============================================================
# Abstract Provider Interface
# ============================================================


class AIProvider(ABC):
    """Abstract AI provider — all providers implement this interface.

    No application code may depend on any vendor SDK.
    All vendor-specific logic is encapsulated within provider implementations.
    """

    @property
    @abstractmethod
    def provider_type(self) -> AIProviderType:
        """Return the provider type."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available (model loaded, API key set, etc.)."""
        ...

    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse:
        """Generate a response (non-streaming).

        Args:
            request: The AI request with prompt + parameters.

        Returns:
            AIResponse with the generated content + metadata.

        Raises:
            AIProviderError: If the request fails.
        """
        ...

    @abstractmethod
    async def stream(self, request: AIRequest) -> AsyncGenerator[AIStreamChunk, None]:
        """Generate a streaming response.

        Args:
            request: The AI request with stream=True.

        Yields:
            AIStreamChunk — partial content as it arrives.
        """
        ...

    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if the provider is available (e.g., Ollama is running)."""
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models for this provider."""
        ...


# ============================================================
# Exceptions
# ============================================================


class AIError(Exception):
    """Base exception for AI-related errors."""
    def __init__(self, message: str, *, provider: AIProviderType | None = None) -> None:
        super().__init__(message)
        self.provider = provider


class AIProviderError(AIError):
    """Raised when a provider request fails."""
    def __init__(
        self,
        message: str,
        *,
        provider: AIProviderType,
        status_code: int | None = None,
        is_retryable: bool = False,
    ) -> None:
        super().__init__(message, provider=provider)
        self.status_code = status_code
        self.is_retryable = is_retryable


class AIUnavailableError(AIError):
    """Raised when AI is unavailable (all providers down)."""
    pass


class AIRateLimitError(AIProviderError):
    """Raised when a provider rate-limits the request."""
    def __init__(self, message: str, *, provider: AIProviderType, retry_after: int = 60) -> None:
        super().__init__(message, provider=provider, status_code=429, is_retryable=True)
        self.retry_after = retry_after


class AITimeoutError(AIProviderError):
    """Raised when a provider request times out."""
    def __init__(self, message: str, *, provider: AIProviderType, timeout_seconds: int) -> None:
        super().__init__(message, provider=provider, status_code=408, is_retryable=True)
        self.timeout_seconds = timeout_seconds


class AISafetyError(AIError):
    """Raised when AI output is rejected by the safety layer."""
    def __init__(self, message: str, *, verdict: SafetyVerdict, notes: str | None = None) -> None:
        super().__init__(message)
        self.verdict = verdict
        self.notes = notes


# ============================================================
# Token/Cost Accounting
# ============================================================


@dataclass
class TokenUsage:
    """Tracks token usage for cost accounting."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_cents: int = 0
    provider: AIProviderType | None = None
    model: str | None = None

    def add(self, other: TokenUsage) -> None:
        """Add another usage record."""
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens
        self.cost_cents += other.cost_cents

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_cents": self.cost_cents,
            "cost_usd": self.cost_cents / 100,
            "provider": self.provider.value if self.provider else None,
            "model": self.model,
        }


def calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    input_rate_per_1k: int,  # cents per 1K tokens
    output_rate_per_1k: int,
) -> int:
    """Calculate cost in cents."""
    input_cost = (prompt_tokens / 1000) * input_rate_per_1k
    output_cost = (completion_tokens / 1000) * output_rate_per_1k
    return int(input_cost + output_cost)


# ============================================================
# Provider Registry
# ============================================================


class ProviderRegistry:
    """Registry of available AI providers.

    The gateway uses this to select the best available provider
    and handle fallback routing.
    """

    def __init__(self) -> None:
        self._providers: dict[AIProviderType, AIProvider] = {}
        self._configs: dict[AIProviderType, AIProviderConfig] = {}
        self._priority: list[AIProviderType] = []

    def register(
        self,
        provider: AIProvider,
        config: AIProviderConfig,
        priority: int = 0,
    ) -> None:
        """Register a provider with its configuration."""
        self._providers[provider.provider_type] = provider
        self._configs[provider.provider_type] = config
        # Insert by priority
        self._priority.append(provider.provider_type)
        self._priority.sort(key=lambda p: self._configs[p].priority if hasattr(self._configs[p], 'priority') else 0)

    def get(self, provider_type: AIProviderType) -> AIProvider | None:
        """Get a provider by type."""
        return self._providers.get(provider_type)

    def get_config(self, provider_type: AIProviderType) -> AIProviderConfig | None:
        """Get a provider's configuration."""
        return self._configs.get(provider_type)

    def get_available_providers(self) -> list[AIProviderType]:
        """Get all enabled provider types in priority order."""
        return [
            p for p in self._priority
            if p in self._configs and self._configs[p].enabled
        ]

    def get_best_available(self) -> AIProvider | None:
        """Get the highest-priority available provider."""
        for provider_type in self.get_available_providers():
            provider = self._providers.get(provider_type)
            if provider and provider.is_available:
                return provider
        return None

    def list_all(self) -> list[dict[str, Any]]:
        """List all registered providers with their status."""
        result = []
        for ptype, config in self._configs.items():
            provider = self._providers.get(ptype)
            result.append({
                "provider_type": ptype.value,
                "enabled": config.enabled,
                "available": provider.is_available if provider else False,
                "default_model": config.default_model,
                "host": config.host,
            })
        return result


# ============================================================
# AI Configuration
# ============================================================


@dataclass
class AIConfig:
    """Global AI configuration."""
    enabled: bool = False  # AI is OFF by default
    default_provider: AIProviderType = AIProviderType.OLLAMA
    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"  # Default to Qwen
    # General settings
    ai_timeout: int = 30
    max_context: int = 4096
    max_tokens: int = 2048
    temperature: float = 0.7
    # Rate limiting
    global_requests_per_minute: int = 60
    # Safety
    safety_enabled: bool = True
    max_response_length: int = 4096
    # Fallback
    fallback_to_rule_based: bool = True
    # Cost tracking
    enable_cost_tracking: bool = True


# Singleton config instance
_config: AIConfig | None = None


def get_ai_config() -> AIConfig:
    """Get the global AI configuration."""
    global _config
    if _config is None:
        _config = AIConfig()
    return _config


def set_ai_config(config: AIConfig) -> None:
    """Set the global AI configuration."""
    global _config
    _config = config


__all__ = [
    # Enums
    "AIProviderType",
    "AIRequestStatus",
    "PromptApprovalState",
    "SafetyVerdict",
    # Data classes
    "AIRequest",
    "AIResponse",
    "AIStreamChunk",
    "AIProviderConfig",
    "TokenUsage",
    "AIConfig",
    # Abstract
    "AIProvider",
    # Registry
    "ProviderRegistry",
    # Exceptions
    "AIError",
    "AIProviderError",
    "AIUnavailableError",
    "AIRateLimitError",
    "AITimeoutError",
    "AISafetyError",
    # Functions
    "get_ai_config",
    "set_ai_config",
    "calculate_cost",
]
