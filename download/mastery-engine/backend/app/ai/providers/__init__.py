"""AI Provider implementations — Ollama, OpenAI, Gemini, Anthropic, Mock.

All providers implement the AIProvider interface from app/ai/__init__.py.
No application code depends on any vendor SDK — each provider encapsulates
its own HTTP client logic.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncGenerator

import httpx

from app.ai import (
    AIProvider,
    AIProviderConfig,
    AIProviderError,
    AIProviderType,
    AIRequest,
    AIResponse,
    AIStreamChunk,
    AIRateLimitError,
    AITimeoutError,
    SafetyVerdict,
    TokenUsage,
    calculate_cost,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Mock Provider (for testing)
# ============================================================


class MockProvider(AIProvider):
    """Mock AI provider for testing — returns deterministic responses."""

    def __init__(self, config: AIProviderConfig | None = None) -> None:
        self._config = config or AIProviderConfig(
            provider_type=AIProviderType.MOCK,
            default_model="mock-model",
        )
        self._available = True
        self._responses: dict[str, str] = {}  # prompt → response mapping
        self._call_count = 0

    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.MOCK

    @property
    def is_available(self) -> bool:
        return self._available

    def set_available(self, available: bool) -> None:
        """Set availability for testing."""
        self._available = available

    def set_response(self, prompt_substring: str, response: str) -> None:
        """Set a canned response for prompts containing a substring."""
        self._responses[prompt_substring] = response

    async def generate(self, request: AIRequest) -> AIResponse:
        self._call_count += 1
        if not self._available:
            raise AIProviderError(
                "Mock provider is unavailable",
                provider=AIProviderType.MOCK,
            )

        # Check for canned response
        content = None
        for substring, response in self._responses.items():
            if substring.lower() in request.prompt.lower():
                content = response
                break

        if content is None:
            content = f"[Mock AI Response] Prompt was: {request.prompt[:200]}..."

        prompt_tokens = len(request.prompt) // 4  # Rough estimate
        completion_tokens = len(content) // 4

        return AIResponse(
            request_id=request.id,
            content=content,
            model=self._config.default_model or "mock-model",
            provider=AIProviderType.MOCK,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_cents=0,
            latency_ms=10,
            response_id=f"mock-{self._call_count}",
            finish_reason="stop",
            safety_verdict=SafetyVerdict.SAFE,
            confidence=0.95,
        )

    async def stream(self, request: AIRequest) -> AsyncGenerator[AIStreamChunk, None]:
        if not self._available:
            raise AIProviderError("Mock unavailable", provider=AIProviderType.MOCK)

        content = f"[Mock AI Stream] {request.prompt[:100]}..."
        words = content.split()
        total = 0
        for i, word in enumerate(words):
            total += len(word) // 4
            yield AIStreamChunk(
                request_id=request.id,
                content=word + " ",
                is_final=(i == len(words) - 1),
                total_tokens=total,
            )
            await asyncio.sleep(0.01)  # Simulate streaming delay

    async def check_availability(self) -> bool:
        return self._available

    async def list_models(self) -> list[str]:
        return ["mock-model"]


# ============================================================
# Ollama Provider (default — local AI)
# ============================================================


class OllamaProvider(AIProvider):
    """Ollama provider — runs models locally.

    Default model: Qwen (latest stable 7B/8B class model)
    Configuration:
    - OLLAMA_HOST (default: http://localhost:11434)
    - OLLAMA_MODEL (default: qwen2.5:7b)
    - AI_TIMEOUT
    - MAX_CONTEXT
    - MAX_TOKENS
    - TEMPERATURE
    """

    def __init__(self, config: AIProviderConfig) -> None:
        self._config = config
        self._host = config.host or "http://localhost:11434"
        self._default_model = config.default_model or "qwen2.5:7b"
        self._available: bool | None = None  # Cached availability
        self._client = httpx.AsyncClient(
            base_url=self._host,
            timeout=config.timeout_seconds,
        )

    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.OLLAMA

    @property
    def is_available(self) -> bool:
        if self._available is None:
            return True  # Optimistic — will check on first request
        return self._available

    async def check_availability(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            response = await self._client.get("/api/tags", timeout=5.0)
            if response.status_code != 200:
                self._available = False
                return False
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            # Check if default model is available
            if self._default_model not in models:
                # Try without tag suffix
                base_model = self._default_model.split(":")[0]
                if not any(base_model in m for m in models):
                    logger.warning(
                        "ollama_model_not_found",
                        model=self._default_model,
                        available=models,
                    )
                    self._available = False
                    return False
            self._available = True
            return True
        except Exception as exc:
            logger.warning("ollama_unavailable", error=str(exc))
            self._available = False
            return False

    async def generate(self, request: AIRequest) -> AIResponse:
        start_time = time.time()
        model = request.model or self._default_model

        try:
            payload = {
                "model": model,
                "prompt": request.prompt,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens,
                    "num_ctx": request.max_context,
                },
            }
            if request.system_prompt:
                payload["system"] = request.system_prompt

            response = await self._client.post(
                "/api/generate",
                json=payload,
                timeout=self._config.timeout_seconds,
            )

            if response.status_code == 429:
                raise AIRateLimitError(
                    "Ollama rate limited",
                    provider=AIProviderType.OLLAMA,
                )

            response.raise_for_status()
            data = response.json()

            latency_ms = int((time.time() - start_time) * 1000)
            content = data.get("response", "")
            prompt_tokens = data.get("prompt_eval_count", len(request.prompt) // 4)
            completion_tokens = data.get("eval_count", len(content) // 4)

            return AIResponse(
                request_id=request.id,
                content=content,
                model=model,
                provider=AIProviderType.OLLAMA,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_cents=0,  # Local model — no cost
                latency_ms=latency_ms,
                response_id=data.get("created", ""),
                finish_reason="stop",
                safety_verdict=SafetyVerdict.SAFE,
                confidence=0.7,  # Default confidence for local models
            )

        except httpx.TimeoutException:
            raise AITimeoutError(
                f"Ollama request timed out after {self._config.timeout_seconds}s",
                provider=AIProviderType.OLLAMA,
                timeout_seconds=self._config.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"Ollama request failed: {exc}",
                provider=AIProviderType.OLLAMA,
                is_retryable=True,
            )

    async def stream(self, request: AIRequest) -> AsyncGenerator[AIStreamChunk, None]:
        model = request.model or self._default_model
        payload = {
            "model": model,
            "prompt": request.prompt,
            "stream": True,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt

        total_tokens = 0
        try:
            async with self._client.stream(
                "POST",
                "/api/generate",
                json=payload,
                timeout=self._config.timeout_seconds,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("response", "")
                        done = chunk.get("done", False)
                        total_tokens = chunk.get("eval_count", total_tokens)
                        yield AIStreamChunk(
                            request_id=request.id,
                            content=content,
                            is_final=done,
                            total_tokens=total_tokens,
                        )
                        if done:
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.TimeoutException:
            raise AITimeoutError(
                "Ollama stream timed out",
                provider=AIProviderType.OLLAMA,
                timeout_seconds=self._config.timeout_seconds,
            )

    async def list_models(self) -> list[str]:
        try:
            response = await self._client.get("/api/tags", timeout=5.0)
            if response.status_code != 200:
                return []
            data = response.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    async def close(self) -> None:
        await self._client.aclose()


# ============================================================
# OpenAI Provider
# ============================================================


class OpenAIProvider(AIProvider):
    """OpenAI provider — uses the OpenAI-compatible API."""

    def __init__(self, config: AIProviderConfig) -> None:
        self._config = config
        self._api_key = config.api_key
        self._default_model = config.default_model or "gpt-4o-mini"
        self._base_url = "https://api.openai.com/v1"
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=config.timeout_seconds,
        )

    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.OPENAI

    @property
    def is_available(self) -> bool:
        return self._api_key is not None

    async def check_availability(self) -> bool:
        if not self._api_key:
            return False
        try:
            response = await self._client.get("/models", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def generate(self, request: AIRequest) -> AIResponse:
        start_time = time.time()
        model = request.model or self._default_model

        payload: dict[str, Any] = {
            "model": model,
            "messages": [],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        if request.system_prompt:
            payload["messages"].append({"role": "system", "content": request.system_prompt})
        payload["messages"].append({"role": "user", "content": request.prompt})

        try:
            response = await self._client.post("/chat/completions", json=payload)
            if response.status_code == 429:
                raise AIRateLimitError("OpenAI rate limited", provider=AIProviderType.OPENAI)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            content = choice["message"]["content"]
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            cost = calculate_cost(
                prompt_tokens, completion_tokens,
                self._config.cost_per_1k_input_cents,
                self._config.cost_per_1k_output_cents,
            )

            return AIResponse(
                request_id=request.id,
                content=content,
                model=model,
                provider=AIProviderType.OPENAI,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_cents=cost,
                latency_ms=int((time.time() - start_time) * 1000),
                response_id=data.get("id"),
                finish_reason=choice.get("finish_reason"),
                safety_verdict=SafetyVerdict.SAFE,
                confidence=0.8,
            )
        except httpx.TimeoutException:
            raise AITimeoutError("OpenAI timeout", provider=AIProviderType.OPENAI, timeout_seconds=self._config.timeout_seconds)
        except httpx.HTTPError as exc:
            raise AIProviderError(f"OpenAI failed: {exc}", provider=AIProviderType.OPENAI, is_retryable=True)

    async def stream(self, request: AIRequest) -> AsyncGenerator[AIStreamChunk, None]:
        model = request.model or self._default_model
        payload: dict[str, Any] = {
            "model": model,
            "messages": [],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        if request.system_prompt:
            payload["messages"].append({"role": "system", "content": request.system_prompt})
        payload["messages"].append({"role": "user", "content": request.prompt})

        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        yield AIStreamChunk(request_id=request.id, content="", is_final=True)
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield AIStreamChunk(request_id=request.id, content=content)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        except httpx.TimeoutException:
            raise AITimeoutError("OpenAI stream timeout", provider=AIProviderType.OPENAI, timeout_seconds=self._config.timeout_seconds)

    async def list_models(self) -> list[str]:
        try:
            response = await self._client.get("/models", timeout=5.0)
            if response.status_code != 200:
                return []
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    async def close(self) -> None:
        await self._client.aclose()


# ============================================================
# Gemini Provider
# ============================================================


class GeminiProvider(AIProvider):
    """Google Gemini provider."""

    def __init__(self, config: AIProviderConfig) -> None:
        self._config = config
        self._api_key = config.api_key
        self._default_model = config.default_model or "gemini-1.5-flash"
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._client = httpx.AsyncClient(
            timeout=config.timeout_seconds,
        )

    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.GEMINI

    @property
    def is_available(self) -> bool:
        return self._api_key is not None

    async def check_availability(self) -> bool:
        return self._api_key is not None

    async def generate(self, request: AIRequest) -> AIResponse:
        start_time = time.time()
        model = request.model or self._default_model

        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}

        try:
            response = await self._client.post(
                f"{self._base_url}/models/{model}:generateContent?key={self._api_key}",
                json=payload,
                timeout=self._config.timeout_seconds,
            )
            if response.status_code == 429:
                raise AIRateLimitError("Gemini rate limited", provider=AIProviderType.GEMINI)
            response.raise_for_status()
            data = response.json()

            content = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", 0)
            completion_tokens = usage.get("candidatesTokenCount", 0)
            cost = calculate_cost(
                prompt_tokens, completion_tokens,
                self._config.cost_per_1k_input_cents,
                self._config.cost_per_1k_output_cents,
            )

            return AIResponse(
                request_id=request.id,
                content=content,
                model=model,
                provider=AIProviderType.GEMINI,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_cents=cost,
                latency_ms=int((time.time() - start_time) * 1000),
                finish_reason=data["candidates"][0].get("finishReason"),
                safety_verdict=SafetyVerdict.SAFE,
                confidence=0.8,
            )
        except httpx.TimeoutException:
            raise AITimeoutError("Gemini timeout", provider=AIProviderType.GEMINI, timeout_seconds=self._config.timeout_seconds)
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Gemini failed: {exc}", provider=AIProviderType.GEMINI, is_retryable=True)

    async def stream(self, request: AIRequest) -> AsyncGenerator[AIStreamChunk, None]:
        # Gemini streaming uses SSE
        model = request.model or self._default_model
        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {"temperature": request.temperature, "maxOutputTokens": request.max_tokens},
        }
        try:
            async with self._client.stream(
                "POST",
                f"{self._base_url}/models/{model}:streamGenerateContent?key={self._api_key}",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        chunk = json.loads(line[6:])
                        text = chunk.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text:
                            yield AIStreamChunk(request_id=request.id, content=text)
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
                yield AIStreamChunk(request_id=request.id, content="", is_final=True)
        except httpx.TimeoutException:
            raise AITimeoutError("Gemini stream timeout", provider=AIProviderType.GEMINI, timeout_seconds=self._config.timeout_seconds)

    async def list_models(self) -> list[str]:
        return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]

    async def close(self) -> None:
        await self._client.aclose()


# ============================================================
# Anthropic Provider
# ============================================================


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, config: AIProviderConfig) -> None:
        self._config = config
        self._api_key = config.api_key
        self._default_model = config.default_model or "claude-3-5-sonnet-20241022"
        self._base_url = "https://api.anthropic.com/v1"
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "x-api-key": self._api_key or "",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=config.timeout_seconds,
        )

    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.ANTHROPIC

    @property
    def is_available(self) -> bool:
        return self._api_key is not None

    async def check_availability(self) -> bool:
        return self._api_key is not None

    async def generate(self, request: AIRequest) -> AIResponse:
        start_time = time.time()
        model = request.model or self._default_model

        payload = {
            "model": model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt

        try:
            response = await self._client.post("/messages", json=payload)
            if response.status_code == 429:
                raise AIRateLimitError("Anthropic rate limited", provider=AIProviderType.ANTHROPIC)
            response.raise_for_status()
            data = response.json()

            content = data["content"][0]["text"]
            usage = data.get("usage", {})
            prompt_tokens = usage.get("input_tokens", 0)
            completion_tokens = usage.get("output_tokens", 0)
            cost = calculate_cost(
                prompt_tokens, completion_tokens,
                self._config.cost_per_1k_input_cents,
                self._config.cost_per_1k_output_cents,
            )

            return AIResponse(
                request_id=request.id,
                content=content,
                model=model,
                provider=AIProviderType.ANTHROPIC,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_cents=cost,
                latency_ms=int((time.time() - start_time) * 1000),
                response_id=data.get("id"),
                finish_reason=data.get("stop_reason"),
                safety_verdict=SafetyVerdict.SAFE,
                confidence=0.85,
            )
        except httpx.TimeoutException:
            raise AITimeoutError("Anthropic timeout", provider=AIProviderType.ANTHROPIC, timeout_seconds=self._config.timeout_seconds)
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Anthropic failed: {exc}", provider=AIProviderType.ANTHROPIC, is_retryable=True)

    async def stream(self, request: AIRequest) -> AsyncGenerator[AIStreamChunk, None]:
        model = request.model or self._default_model
        payload = {
            "model": model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [{"role": "user", "content": request.prompt}],
            "stream": True,
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt

        try:
            async with self._client.stream("POST", "/messages", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        chunk = json.loads(line[6:])
                        if chunk.get("type") == "content_block_delta":
                            text = chunk.get("delta", {}).get("text", "")
                            if text:
                                yield AIStreamChunk(request_id=request.id, content=text)
                        elif chunk.get("type") == "message_stop":
                            yield AIStreamChunk(request_id=request.id, content="", is_final=True)
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.TimeoutException:
            raise AITimeoutError("Anthropic stream timeout", provider=AIProviderType.ANTHROPIC, timeout_seconds=self._config.timeout_seconds)

    async def list_models(self) -> list[str]:
        return ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]

    async def close(self) -> None:
        await self._client.aclose()


# ============================================================
# Provider Factory
# ============================================================


def create_provider(
    provider_type: AIProviderType,
    config: AIProviderConfig,
) -> AIProvider:
    """Create a provider instance by type."""
    if provider_type == AIProviderType.OLLAMA:
        return OllamaProvider(config)
    elif provider_type == AIProviderType.OPENAI:
        return OpenAIProvider(config)
    elif provider_type == AIProviderType.GEMINI:
        return GeminiProvider(config)
    elif provider_type == AIProviderType.ANTHROPIC:
        return AnthropicProvider(config)
    elif provider_type == AIProviderType.MOCK:
        return MockProvider(config)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


__all__ = [
    "MockProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "AnthropicProvider",
    "create_provider",
]
