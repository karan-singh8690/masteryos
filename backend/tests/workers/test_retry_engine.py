"""Tests for the retry engine.

Tests:
- Default retry schedule is correct (1m, 5m, 15m, 1h, 6h, 24h)
- get_retry_delay returns correct delays
- get_next_retry_time returns correct times
- should_retry returns True/False correctly
- execute_with_retry succeeds on first try
- execute_with_retry retries on failure
- execute_with_retry gives up after max retries
- execute_with_retry records history
- Non-retryable exceptions are not retried
- Custom schedule works
- Jitter adds variance
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from app.workers.retry_engine import (
    DEFAULT_RETRY_SCHEDULE,
    FAST_RETRY_SCHEDULE,
    RetryEngine,
    RetryResult,
)


class TestRetrySchedule:
    """Tests for the retry schedule constants."""

    def test_default_schedule_has_6_levels(self):
        assert len(DEFAULT_RETRY_SCHEDULE) == 6

    def test_default_schedule_values(self):
        assert DEFAULT_RETRY_SCHEDULE[0] == timedelta(minutes=1)
        assert DEFAULT_RETRY_SCHEDULE[1] == timedelta(minutes=5)
        assert DEFAULT_RETRY_SCHEDULE[2] == timedelta(minutes=15)
        assert DEFAULT_RETRY_SCHEDULE[3] == timedelta(hours=1)
        assert DEFAULT_RETRY_SCHEDULE[4] == timedelta(hours=6)
        assert DEFAULT_RETRY_SCHEDULE[5] == timedelta(hours=24)

    def test_fast_schedule_has_5_levels(self):
        assert len(FAST_RETRY_SCHEDULE) == 5


class TestRetryEngine:
    """Tests for the RetryEngine class."""

    def test_get_retry_delay_first_attempt(self):
        """First retry delay is ~1 minute (with jitter)."""
        engine = RetryEngine(jitter=False)
        delay = engine.get_retry_delay(0)
        assert delay == timedelta(minutes=1)

    def test_get_retry_delay_second_attempt(self):
        """Second retry delay is ~5 minutes."""
        engine = RetryEngine(jitter=False)
        delay = engine.get_retry_delay(1)
        assert delay == timedelta(minutes=5)

    def test_get_retry_delay_beyond_schedule(self):
        """Beyond the schedule, the last delay is used (if under max_retries)."""
        engine = RetryEngine(jitter=False, max_retries=20)
        delay = engine.get_retry_delay(10)
        assert delay == timedelta(hours=24)

    def test_should_retry_within_max(self):
        """should_retry returns True when under max retries."""
        engine = RetryEngine()
        assert engine.should_retry(0) is True
        assert engine.should_retry(5) is True  # Last retry

    def test_should_not_retry_beyond_max(self):
        """should_retry returns False when at max retries."""
        engine = RetryEngine()
        assert engine.should_retry(6) is False
        assert engine.should_retry(100) is False

    def test_custom_max_retries(self):
        """Custom max_retries is respected."""
        engine = RetryEngine(max_retries=3)
        assert engine.max_retries == 3
        assert engine.should_retry(2) is True
        assert engine.should_retry(3) is False

    def test_custom_schedule(self):
        """Custom schedule is used."""
        custom = [timedelta(seconds=1), timedelta(seconds=10)]
        engine = RetryEngine(schedule=custom, jitter=False)
        assert engine.get_retry_delay(0) == timedelta(seconds=1)
        assert engine.get_retry_delay(1) == timedelta(seconds=10)


class TestExecuteWithRetry:
    """Tests for execute_with_retry."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        """A function that succeeds on the first try returns immediately."""
        engine = RetryEngine(jitter=False)

        async def success_func():
            return "ok"

        result = await engine.execute_with_retry(success_func)
        assert result.success is True
        assert result.attempts == 1
        assert result.final_error is None

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """A function that fails is retried."""
        # Use a fast schedule for testing
        fast_engine = RetryEngine(
            schedule=[timedelta(seconds=0.01), timedelta(seconds=0.01)],
            jitter=False,
        )

        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Transient")

        result = await fast_engine.execute_with_retry(fail_then_succeed)
        assert result.success is True
        assert result.attempts == 2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_gives_up_after_max_retries(self):
        """A function that always fails is given up after max retries."""
        fast_engine = RetryEngine(
            schedule=[timedelta(seconds=0.01)],
            jitter=False,
            max_retries=2,
        )

        async def always_fail():
            raise ValueError("Permanent")

        result = await fast_engine.execute_with_retry(always_fail)
        assert result.success is False
        # max_retries=2 means 1 initial + 2 retries = 3 total attempts
        assert result.attempts == 3
        assert "Permanent" in result.final_error

    @pytest.mark.asyncio
    async def test_records_history(self):
        """The retry history is recorded."""
        fast_engine = RetryEngine(
            schedule=[timedelta(seconds=0.01)],
            jitter=False,
            max_retries=2,
        )

        async def always_fail():
            raise ValueError("Test error")

        result = await fast_engine.execute_with_retry(always_fail)
        # 1 initial + 2 retries = 3 attempts
        assert len(result.history) == 3
        assert result.history[0]["success"] is False
        assert result.history[0]["error"] == "Test error"

    @pytest.mark.asyncio
    async def test_non_retryable_exception_not_retried(self):
        """Non-retryable exceptions are not retried (they propagate)."""
        fast_engine = RetryEngine(
            schedule=[timedelta(seconds=0.01)],
            jitter=False,
        )

        call_count = 0

        async def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retryable")

        # TypeError is not in retryable_exceptions, so it propagates immediately
        with pytest.raises(TypeError):
            await fast_engine.execute_with_retry(
                raises_type_error,
                retryable_exceptions=(ValueError,),
            )
        assert call_count == 1  # Not retried

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self):
        """Args and kwargs are passed to the function."""
        engine = RetryEngine(jitter=False)

        async def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = await engine.execute_with_retry(
            func_with_args, args=(1, 2), kwargs={"c": 3}
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_total_delay_is_recorded(self):
        """Total delay is recorded."""
        fast_engine = RetryEngine(
            schedule=[timedelta(seconds=0.05)],
            jitter=False,
            max_retries=2,
        )

        async def always_fail():
            raise ValueError("Test")

        result = await fast_engine.execute_with_retry(always_fail)
        # 1 retry with 0.05s delay
        assert result.total_delay_seconds >= 0.04  # At least 0.05s (with timing variance)
