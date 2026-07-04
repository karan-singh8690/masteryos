"""Retry engine — exponential backoff for failed operations.

Implements the retry schedule per Task 017 spec:
- 1 minute
- 5 minutes
- 15 minutes
- 1 hour
- 6 hours
- 24 hours

After the maximum number of retries, the operation is moved to the
dead letter queue.

The retry engine is used by:
- The outbox dispatcher (for failed event dispatches)
- The email processor (for failed SMTP sends)
- The notification processor (for failed deliveries)

Each retry engine instance is independent — they don't share state.
The schedule is configurable per instance (e.g., emails may have a
different schedule than event dispatches).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone as tz_utc
from typing import Any, TypeVar

from app.shared.logging import get_logger

logger = get_logger(__name__)


T = TypeVar("T")


# ============================================================
# Retry Schedule
# ============================================================


DEFAULT_RETRY_SCHEDULE: list[timedelta] = [
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
    timedelta(hours=6),
    timedelta(hours=24),
]
"""Default retry schedule: 1m, 5m, 15m, 1h, 6h, 24h (per Task 017)."""

FAST_RETRY_SCHEDULE: list[timedelta] = [
    timedelta(seconds=5),
    timedelta(seconds=30),
    timedelta(minutes=2),
    timedelta(minutes=10),
    timedelta(hours=1),
]
"""Faster retry schedule for transient failures (e.g., SMTP)."""


# ============================================================
# Retry Result
# ============================================================


@dataclass
class RetryResult:
    """Result of a retry operation."""

    success: bool
    attempts: int
    final_error: str | None = None
    total_delay_seconds: float = 0.0
    history: list[dict[str, Any]] = field(default_factory=list)


# ============================================================
# Retry Engine
# ============================================================


class RetryEngine:
    """Exponential backoff retry engine.

    Usage:
        engine = RetryEngine(schedule=DEFAULT_RETRY_SCHEDULE)
        result = await engine.execute_with_retry(
            func=my_async_func,
            args=(arg1, arg2),
            kwargs={"key": "value"},
        )
        if not result.success:
            # Move to dead letter queue
            ...

    The engine does NOT execute the retries itself — it computes the
    next retry time and returns it. The caller (e.g., the outbox dispatcher)
    is responsible for scheduling the retry.

    For inline retries (where the caller waits), use execute_with_retry().
    """

    def __init__(
        self,
        schedule: list[timedelta] | None = None,
        max_retries: int | None = None,
        jitter: bool = True,
    ) -> None:
        self._schedule = schedule or DEFAULT_RETRY_SCHEDULE
        self._max_retries = max_retries or len(self._schedule)
        self._jitter = jitter

    @property
    def max_retries(self) -> int:
        return self._max_retries

    @property
    def schedule(self) -> list[timedelta]:
        return self._schedule

    def get_retry_delay(self, attempt: int) -> timedelta:
        """Get the delay before the next retry.

        Args:
            attempt: The attempt number (0-indexed: 0 = first failure).

        Returns:
            The delay before the next retry. Returns None if no more retries.
        """
        if attempt >= self._max_retries:
            return None  # type: ignore[return-value]
        if attempt >= len(self._schedule):
            return self._schedule[-1]  # Use the last (longest) delay

        delay = self._schedule[attempt]

        # Add jitter (±10%) to avoid thundering herd
        if self._jitter and delay.total_seconds() > 0:
            import random
            jitter_factor = 0.9 + (random.random() * 0.2)  # 0.9 to 1.1
            delay = timedelta(seconds=delay.total_seconds() * jitter_factor)

        return delay

    def get_next_retry_time(self, attempt: int) -> datetime:
        """Get the absolute next retry time."""
        delay = self.get_retry_delay(attempt)
        if delay is None:
            # Should not happen — caller should check max_retries first
            return datetime.now(tz_utc.utc) + self._schedule[-1]
        return datetime.now(tz_utc.utc) + delay

    def should_retry(self, attempt: int) -> bool:
        """Return True if the operation should be retried."""
        return attempt < self._max_retries

    async def execute_with_retry(
        self,
        func: Callable[..., Awaitable[T]],
        args: tuple = (),
        kwargs: dict[str, Any] | None = None,
        retryable_exceptions: tuple[type[Exception], ...] | None = None,
    ) -> RetryResult:
        """Execute a function with inline retries.

        This is for cases where the caller can block (e.g., a worker
        processing a job). For outbox dispatch, use get_next_retry_time()
        instead and let the dispatcher schedule the retry.

        Args:
            func: Async function to call.
            args: Positional args for func.
            kwargs: Keyword args for func.
            retryable_exceptions: Tuple of exception types to retry on.
                Other exceptions are not retried. Defaults to (Exception,)
                which retries on all exceptions.

        Returns:
            RetryResult with success/failure + history.
        """
        kwargs = kwargs or {}
        retryable = retryable_exceptions or (Exception,)
        history: list[dict[str, Any]] = []
        total_delay = 0.0
        attempt = 0

        while True:
            try:
                start = datetime.now(tz_utc.utc)
                result = await func(*args, **kwargs)
                duration = (datetime.now(tz_utc.utc) - start).total_seconds()
                history.append({
                    "attempt": attempt,
                    "timestamp": start.isoformat(),
                    "duration_seconds": duration,
                    "success": True,
                })
                return RetryResult(
                    success=True,
                    attempts=attempt + 1,
                    total_delay_seconds=total_delay,
                    history=history,
                )
            except retryable as exc:
                duration = (datetime.now(tz_utc.utc) - start).total_seconds()
                history.append({
                    "attempt": attempt,
                    "timestamp": start.isoformat(),
                    "duration_seconds": duration,
                    "success": False,
                    "error": str(exc)[:500],
                    "error_type": type(exc).__name__,
                })

                if not self.should_retry(attempt):
                    return RetryResult(
                        success=False,
                        attempts=attempt + 1,
                        final_error=str(exc),
                        total_delay_seconds=total_delay,
                        history=history,
                    )

                delay = self.get_retry_delay(attempt)
                logger.info(
                    "retry_scheduled",
                    attempt=attempt + 1,
                    delay_seconds=delay.total_seconds(),
                    error=str(exc)[:200],
                )
                await asyncio.sleep(delay.total_seconds())
                total_delay += delay.total_seconds()
                attempt += 1


__all__ = [
    "RetryEngine",
    "RetryResult",
    "DEFAULT_RETRY_SCHEDULE",
    "FAST_RETRY_SCHEDULE",
]
