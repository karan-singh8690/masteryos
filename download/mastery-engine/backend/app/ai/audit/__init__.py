"""AI Audit Trail — logs every AI interaction for traceability.

Logs:
- Provider
- Model
- Prompt version
- Latency
- Tokens
- Cost
- Response ID
- Approval status
- Reviewer

Every AI interaction must be traceable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone as tz_utc
from typing import Any
from uuid import UUID

from app.ai import AIProviderType, SafetyVerdict
from app.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AuditEntry:
    """A single AI audit log entry."""
    id: UUID = field(default_factory=lambda: __import__('uuid').uuid4())
    request_id: UUID = field(default_factory=lambda: __import__('uuid').uuid4())
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz_utc.utc))
    # Provider info
    provider: AIProviderType = AIProviderType.MOCK
    model: str = ""
    # Prompt info
    prompt_version: str | None = None
    request_type: str = "generic"
    # Performance
    latency_ms: int = 0
    # Token accounting
    tokens: int = 0
    cost_cents: int = 0
    # Response
    response_id: str | None = None
    # Safety
    action: str = "generate"  # generate, stream, safety_rejected, error
    verdict: SafetyVerdict = SafetyVerdict.SAFE
    notes: str | None = None
    # User
    user_id: UUID | None = None
    # Approval
    approval_status: str = "auto"  # auto, pending, approved, rejected
    reviewer: UUID | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "request_id": str(self.request_id),
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider.value,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "request_type": self.request_type,
            "latency_ms": self.latency_ms,
            "tokens": self.tokens,
            "cost_cents": self.cost_cents,
            "cost_usd": self.cost_cents / 100,
            "response_id": self.response_id,
            "action": self.action,
            "verdict": self.verdict.value,
            "notes": self.notes,
            "user_id": str(self.user_id) if self.user_id else None,
            "approval_status": self.approval_status,
            "reviewer": str(self.reviewer) if self.reviewer else None,
        }


class AuditLogger:
    """Logs AI interactions for audit + compliance.

    In production, this writes to a database table (ai_audit_logs).
    For now, it's in-memory with structured logging.
    """

    def __init__(self, max_entries: int = 10000) -> None:
        self._entries: list[AuditEntry] = []
        self._max_entries = max_entries

    async def log(self, entry: AuditEntry) -> None:
        """Log an AI interaction."""
        self._entries.append(entry)

        # Trim if over max
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        # Structured log
        logger.info(
            "ai_audit",
            request_id=str(entry.request_id),
            provider=entry.provider.value,
            model=entry.model,
            action=entry.action,
            latency_ms=entry.latency_ms,
            tokens=entry.tokens,
            cost_cents=entry.cost_cents,
            verdict=entry.verdict.value,
            request_type=entry.request_type,
        )

    async def list_entries(
        self,
        *,
        provider: AIProviderType | None = None,
        request_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """List audit entries with optional filters."""
        results = self._entries

        if provider:
            results = [e for e in results if e.provider == provider]
        if request_type:
            results = [e for e in results if e.request_type == request_type]
        if start_date:
            results = [e for e in results if e.timestamp >= start_date]
        if end_date:
            results = [e for e in results if e.timestamp <= end_date]

        # Most recent first
        results = sorted(results, key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    async def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics."""
        total = len(self._entries)
        if total == 0:
            return {
                "total_interactions": 0,
                "total_tokens": 0,
                "total_cost_usd": 0,
                "avg_latency_ms": 0,
                "by_provider": {},
                "by_request_type": {},
                "safety_rejection_rate": 0,
            }

        total_tokens = sum(e.tokens for e in self._entries)
        total_cost = sum(e.cost_cents for e in self._entries)
        total_latency = sum(e.latency_ms for e in self._entries)
        safety_rejections = sum(1 for e in self._entries if e.action == "safety_rejected")

        by_provider: dict[str, int] = {}
        by_request_type: dict[str, int] = {}
        for e in self._entries:
            by_provider[e.provider.value] = by_provider.get(e.provider.value, 0) + 1
            by_request_type[e.request_type] = by_request_type.get(e.request_type, 0) + 1

        return {
            "total_interactions": total,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost / 100,
            "avg_latency_ms": round(total_latency / total, 2),
            "by_provider": by_provider,
            "by_request_type": by_request_type,
            "safety_rejection_rate": round(safety_rejections / total * 100, 2),
        }


# Singleton logger
_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    global _logger
    if _logger is None:
        _logger = AuditLogger()
    return _logger


__all__ = [
    "AuditEntry",
    "AuditLogger",
    "get_audit_logger",
]
