"""AI Gateway — request routing, validation, rate limiting, cost accounting.

The gateway is the single entry point for all AI requests. It:
1. Validates requests
2. Selects the best available provider
3. Handles fallback routing
4. Enforces timeouts + retries
5. Applies rate limiting
6. Tracks token usage + cost
7. Logs to the audit trail
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone as tz_utc
from typing import Any, AsyncGenerator
from uuid import UUID

from app.ai import (
    AIConfig,
    AIProvider,
    AIProviderError,
    AIProviderType,
    AIRequest,
    AIResponse,
    AIStreamChunk,
    AIUnavailableError,
    AIRateLimitError,
    AITimeoutError,
    AISafetyError,
    ProviderRegistry,
    SafetyVerdict,
    TokenUsage,
    get_ai_config,
)
from app.ai.safety import SafetyValidator, SafetyResult
from app.ai.audit import AuditLogger, AuditEntry
from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Rate Limiter
# ============================================================


class RateLimiter:
    """Token bucket rate limiter for AI requests."""

    def __init__(self, requests_per_minute: int = 60) -> None:
        self._max = requests_per_minute
        self._tokens = requests_per_minute
        self._last_refill = time.time()
        self._lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None

    async def check(self) -> bool:
        """Check if a request is allowed. Returns True if allowed."""
        now = time.time()
        elapsed = now - self._last_refill
        # Refill tokens
        self._tokens = min(self._max, self._tokens + elapsed * (self._max / 60))
        self._last_refill = now

        if self._tokens < 1:
            return False

        self._tokens -= 1
        return True

    @property
    def remaining(self) -> int:
        return int(self._tokens)


# Need asyncio import
import asyncio  # noqa: E402


# ============================================================
# AI Gateway
# ============================================================


@dataclass
class GatewayMetrics:
    """Gateway metrics for monitoring."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited: int = 0
    timed_out: int = 0
    safety_rejected: int = 0
    fallback_used: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_tokens: int = 0
    total_cost_cents: int = 0
    provider_usage: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    avg_latency_ms: float = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rate_limited": self.rate_limited,
            "timed_out": self.timed_out,
            "safety_rejected": self.safety_rejected,
            "fallback_used": self.fallback_used,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_cents / 100,
            "provider_usage": dict(self.provider_usage),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


class AIGateway:
    """AI Gateway — the single entry point for all AI requests.

    Features:
    - Request validation
    - Provider selection with fallback routing
    - Timeout + retry handling
    - Rate limiting (global + per-provider)
    - Token accounting + cost tracking
    - Response validation (safety layer)
    - Audit logging
    - Response caching
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        config: AIConfig | None = None,
        safety_validator: SafetyValidator | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._registry = registry
        self._config = config or get_ai_config()
        self._safety = safety_validator or SafetyValidator()
        self._audit = audit_logger or AuditLogger()
        self._rate_limiter = RateLimiter(self._config.global_requests_per_minute)
        self._metrics = GatewayMetrics()
        self._cache: dict[str, AIResponse] = {}  # Simple in-memory cache (prompt_hash → response)
        self._max_cache_size = 100

    async def generate(
        self,
        request: AIRequest,
        *,
        skip_safety: bool = False,
        use_cache: bool = True,
    ) -> AIResponse:
        """Generate an AI response with full gateway processing.

        Flow:
        1. Check if AI is enabled
        2. Check rate limit
        3. Check cache
        4. Select provider
        5. Generate response (with fallback)
        6. Safety validation
        7. Audit log
        8. Update metrics

        Raises:
            AIUnavailableError: If AI is disabled or all providers are down.
            AISafetyError: If the response is rejected by the safety layer.
        """
        if not self._config.enabled:
            raise AIUnavailableError("AI is not enabled")

        self._metrics.total_requests += 1

        # Rate limit check
        if not await self._rate_limiter.check():
            self._metrics.rate_limited += 1
            raise AIRateLimitError(
                "AI rate limit exceeded",
                provider=AIProviderType.MOCK,
            )

        # Cache check
        if use_cache:
            cache_key = self._cache_key(request)
            cached = self._cache.get(cache_key)
            if cached:
                self._metrics.cache_hits += 1
                return cached
            self._metrics.cache_misses += 1

        # Provider selection + fallback
        response = await self._generate_with_fallback(request)

        # Safety validation
        if not skip_safety and self._config.safety_enabled:
            safety_result = await self._safety.validate(response.content, request)
            if not safety_result.is_safe:
                self._metrics.safety_rejected += 1
                # Log the rejection
                await self._audit.log(AuditEntry(
                    request_id=request.id,
                    provider=response.provider,
                    model=response.model,
                    prompt_version=request.prompt_version,
                    action="safety_rejected",
                    verdict=safety_result.verdict,
                    notes=safety_result.notes,
                    latency_ms=response.latency_ms,
                    tokens=response.total_tokens,
                    cost_cents=response.cost_cents,
                ))
                if self._config.fallback_to_rule_based:
                    raise AISafetyError(
                        f"AI response rejected by safety: {safety_result.notes}",
                        verdict=safety_result.verdict,
                        notes=safety_result.notes,
                    )
                else:
                    raise AISafetyError(
                        f"AI response rejected: {safety_result.notes}",
                        verdict=safety_result.verdict,
                        notes=safety_result.notes,
                    )

        # Audit log
        await self._audit.log(AuditEntry(
            request_id=request.id,
            provider=response.provider,
            model=response.model,
            prompt_version=request.prompt_version,
            action="generate",
            verdict=SafetyVerdict.SAFE,
            latency_ms=response.latency_ms,
            tokens=response.total_tokens,
            cost_cents=response.cost_cents,
            response_id=response.response_id,
            user_id=request.user_id,
            request_type=request.request_type,
        ))

        # Update metrics
        self._update_metrics(response)

        # Cache the response
        if use_cache:
            self._cache[cache_key] = response
            if len(self._cache) > self._max_cache_size:
                # Remove oldest entry (simple LRU)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]

        return response

    async def stream(
        self,
        request: AIRequest,
        *,
        skip_safety: bool = False,
    ) -> AsyncGenerator[AIStreamChunk, None]:
        """Stream an AI response with gateway processing."""
        if not self._config.enabled:
            raise AIUnavailableError("AI is not enabled")

        if not await self._rate_limiter.check():
            raise AIRateLimitError("Rate limited", provider=AIProviderType.MOCK)

        provider = self._registry.get_best_available()
        if provider is None:
            raise AIUnavailableError("No AI providers available")

        async for chunk in provider.stream(request):
            # Note: Safety validation on streaming is limited (can only check after completion)
            yield chunk

    async def _generate_with_fallback(self, request: AIRequest) -> AIResponse:
        """Try providers in priority order with fallback."""
        providers = self._registry.get_available_providers()
        if not providers:
            raise AIUnavailableError("No AI providers available")

        last_error: Exception | None = None

        for i, provider_type in enumerate(providers):
            provider = self._registry.get(provider_type)
            if provider is None:
                continue

            try:
                response = await provider.generate(request)
                if i > 0:
                    self._metrics.fallback_used += 1
                    logger.info("ai_fallback_used", primary=providers[0], fallback=provider_type)
                return response

            except AITimeoutError as exc:
                last_error = exc
                logger.warning("ai_provider_timeout", provider=provider_type, error=str(exc))
                continue
            except AIRateLimitError as exc:
                last_error = exc
                logger.warning("ai_provider_rate_limited", provider=provider_type)
                continue
            except AIProviderError as exc:
                last_error = exc
                logger.warning("ai_provider_error", provider=provider_type, error=str(exc))
                if not exc.is_retryable:
                    raise
                continue

        # All providers failed
        self._metrics.failed_requests += 1
        if last_error:
            raise AIUnavailableError(f"All AI providers failed. Last error: {last_error}")
        raise AIUnavailableError("All AI providers failed")

    def _cache_key(self, request: AIRequest) -> str:
        """Generate a cache key from a request."""
        import hashlib
        key_str = f"{request.prompt}:{request.system_prompt}:{request.model}:{request.temperature}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _update_metrics(self, response: AIResponse) -> None:
        """Update gateway metrics after a successful response."""
        self._metrics.successful_requests += 1
        self._metrics.total_tokens += response.total_tokens
        self._metrics.total_cost_cents += response.cost_cents
        self._metrics.provider_usage[response.provider.value] += 1

        # Update rolling average latency
        total = self._metrics.successful_requests
        self._metrics.avg_latency_ms = (
            (self._metrics.avg_latency_ms * (total - 1) + response.latency_ms) / total
        )

    @property
    def metrics(self) -> GatewayMetrics:
        return self._metrics

    def get_metrics_dict(self) -> dict[str, Any]:
        return self._metrics.to_dict()

    def clear_cache(self) -> int:
        """Clear the response cache. Returns number of entries cleared."""
        count = len(self._cache)
        self._cache.clear()
        return count

    def is_enabled(self) -> bool:
        """Check if AI is enabled."""
        return self._config.enabled

    def get_available_providers(self) -> list[dict[str, Any]]:
        """List all registered providers with their status."""
        return self._registry.list_all()


# ============================================================
# Gateway Factory
# ============================================================


_gateway: AIGateway | None = None


def get_gateway() -> AIGateway:
    """Get the singleton AI gateway instance."""
    global _gateway
    if _gateway is None:
        from app.ai.providers import MockProvider, create_provider
        from app.ai import AIProviderConfig

        config = get_ai_config()
        registry = ProviderRegistry()

        # Register providers based on config
        if config.enabled:
            # Ollama (default)
            ollama_config = AIProviderConfig(
                provider_type=AIProviderType.OLLAMA,
                host=config.ollama_host,
                default_model=config.ollama_model,
                timeout_seconds=config.ai_timeout,
            )
            registry.register(
                create_provider(AIProviderType.OLLAMA, ollama_config),
                ollama_config,
            )

            # Cloud providers (if API keys are available)
            # These would be configured via environment variables
            # For now, we only register the mock provider for testing

        # Always register mock provider for testing
        mock_config = AIProviderConfig(
            provider_type=AIProviderType.MOCK,
            enabled=False,  # Disabled by default
        )
        registry.register(MockProvider(mock_config), mock_config)

        _gateway = AIGateway(registry, config)

    return _gateway


def reset_gateway() -> None:
    """Reset the gateway (for testing)."""
    global _gateway
    _gateway = None


__all__ = [
    "AIGateway",
    "GatewayMetrics",
    "RateLimiter",
    "get_gateway",
    "reset_gateway",
]
