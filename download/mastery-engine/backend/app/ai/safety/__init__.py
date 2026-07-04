"""AI Safety Layer — validates all AI outputs before they reach users.

Features:
- Prompt injection protection
- PII removal
- Output validation
- Toxicity detection
- Hallucination confidence
- Maximum response length
- Citation support
- Unsafe output rejection

Fallback to deterministic explanations if validation fails.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.ai import AIRequest, SafetyVerdict
from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Safety Result
# ============================================================


@dataclass(frozen=True)
class SafetyResult:
    """Result of safety validation."""
    is_safe: bool
    verdict: SafetyVerdict
    notes: str | None = None
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)


# ============================================================
# Safety Patterns
# ============================================================

# Prompt injection patterns
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(the\s+)?above",
    r"you\s+are\s+now\s+a\s+",
    r"system\s*:\s*",
    r"<\|im_start\|>",
    r"<\|system\|>",
    r"forget\s+(everything|all)",
    r"reset\s+your\s+instructions",
    r"new\s+instructions?\s*:",
]

# PII patterns (email, phone, SSN, credit card)
PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL REDACTED]"),
    (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE REDACTED]"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN REDACTED]"),
    (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD REDACTED]"),
]

# Toxicity keywords (simplified — production would use a toxicity classifier)
TOXICITY_KEYWORDS = [
    "hate", "kill", "suicide", "self-harm", "racist", "nazi",
    "bomb", "terrorist", "drug dealer", "child abuse",
]

# Code injection patterns
CODE_INJECTION_PATTERNS = [
    r"```(?:python|bash|sh|javascript|js)\s*",
    r"import\s+os\s*;",
    r"eval\s*\(",
    r"exec\s*\(",
    r"subprocess\.",
    r"os\.system\s*\(",
]


# ============================================================
# Safety Validator
# ============================================================


class SafetyValidator:
    """Validates AI outputs for safety.

    All AI outputs pass through this validator before reaching users.
    If validation fails, the system falls back to deterministic explanations.
    """

    def __init__(
        self,
        max_response_length: int = 4096,
        enable_pii_removal: bool = True,
        enable_toxicity_check: bool = True,
        enable_injection_check: bool = True,
    ) -> None:
        self._max_length = max_response_length
        self._enable_pii = enable_pii_removal
        self._enable_toxicity = enable_toxicity_check
        self._enable_injection = enable_injection_check

    async def validate(
        self,
        content: str,
        request: AIRequest,
    ) -> SafetyResult:
        """Validate AI output for safety.

        Checks:
        1. Maximum response length
        2. Prompt injection protection
        3. PII detection
        4. Toxicity detection
        5. Code injection
        6. Hallucination indicators

        Returns:
            SafetyResult with verdict + notes.
        """
        checks_passed: list[str] = []
        checks_failed: list[str] = []
        notes_parts: list[str] = []

        # 1. Length check
        if len(content) > self._max_length:
            checks_failed.append("max_length")
            notes_parts.append(f"Response exceeds max length ({len(content)} > {self._max_length})")
        else:
            checks_passed.append("max_length")

        # 2. Prompt injection check
        if self._enable_injection:
            injection_found = self._check_prompt_injection(content)
            if injection_found:
                checks_failed.append("prompt_injection")
                notes_parts.append(f"Prompt injection detected: {injection_found}")
            else:
                checks_passed.append("prompt_injection")

        # 3. PII check
        if self._enable_pii:
            pii_found = self._check_pii(content)
            if pii_found:
                checks_failed.append("pii_detected")
                notes_parts.append(f"PII detected: {pii_found}")
            else:
                checks_passed.append("pii_clean")

        # 4. Toxicity check
        if self._enable_toxicity:
            toxicity_found = self._check_toxicity(content)
            if toxicity_found:
                checks_failed.append("toxicity")
                notes_parts.append(f"Toxic content detected: {toxicity_found}")
            else:
                checks_passed.append("toxicity_clean")

        # 5. Code injection check
        code_injection = self._check_code_injection(content)
        if code_injection:
            checks_failed.append("code_injection")
            notes_parts.append(f"Code injection detected: {code_injection}")
        else:
            checks_passed.append("code_injection_clean")

        # 6. Hallucination indicators
        hallucination_indicators = self._check_hallucination_indicators(content)
        if hallucination_indicators:
            checks_failed.append("hallucination_risk")
            notes_parts.append(f"Hallucination risk: {hallucination_indicators}")
        else:
            checks_passed.append("hallucination_clean")

        # Determine verdict
        if checks_failed:
            # Critical checks that always reject
            critical_failures = {"prompt_injection", "toxicity", "code_injection"}
            if any(c in checks_failed for c in critical_failures):
                verdict = SafetyVerdict.UNSAFE
                is_safe = False
            else:
                # Non-critical failures require review
                verdict = SafetyVerdict.REQUIRES_REVIEW
                is_safe = False
        else:
            verdict = SafetyVerdict.SAFE
            is_safe = True

        notes = "; ".join(notes_parts) if notes_parts else None

        if not is_safe:
            logger.warning(
                "ai_safety_rejection",
                verdict=verdict.value,
                checks_failed=checks_failed,
                notes=notes,
                request_id=str(request.id),
            )

        return SafetyResult(
            is_safe=is_safe,
            verdict=verdict,
            notes=notes,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )

    def sanitize(self, content: str) -> str:
        """Remove PII from content (for logging/storage)."""
        sanitized = content
        for pattern, replacement in PII_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized

    def _check_prompt_injection(self, content: str) -> str | None:
        """Check for prompt injection patterns."""
        content_lower = content.lower()
        for pattern in PROMPT_INJECTION_PATTERNS:
            match = re.search(pattern, content_lower, re.IGNORECASE)
            if match:
                return match.group()
        return None

    def _check_pii(self, content: str) -> str | None:
        """Check for PII patterns."""
        for pattern, _ in PII_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group()
        return None

    def _check_toxicity(self, content: str) -> str | None:
        """Check for toxic content."""
        content_lower = content.lower()
        for keyword in TOXICITY_KEYWORDS:
            if keyword in content_lower:
                return keyword
        return None

    def _check_code_injection(self, content: str) -> str | None:
        """Check for code injection patterns."""
        for pattern in CODE_INJECTION_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group()
        return None

    def _check_hallucination_indicators(self, content: str) -> str | None:
        """Check for hallucination indicators."""
        indicators = [
            "as an ai language model, i",
            "i don't have access to",
            "i cannot verify",
            "this may not be accurate",
            "i'm not sure if this is correct",
            "based on my training data",
        ]
        content_lower = content.lower()
        for indicator in indicators:
            if indicator in content_lower:
                return indicator
        return None


__all__ = [
    "SafetyValidator",
    "SafetyResult",
]
