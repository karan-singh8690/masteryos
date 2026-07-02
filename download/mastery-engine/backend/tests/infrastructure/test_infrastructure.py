"""Tests for infrastructure layer components.

Tests the mappers, repository contracts, clock, ID generation, and cache
using in-memory fakes (no real PostgreSQL needed for these unit tests).
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.infrastructure.clock import FixedClock, SystemClock
from app.infrastructure.ids import DeterministicIdGenerator, UuidV4Generator, UuidV7Generator
from app.infrastructure.cache import LocalCache
from app.infrastructure.events.outbox.serializer import EventSerializer
from app.domain.shared.kernel import DomainEvent, ScoringOutcome
from app.domain.assessment.events import AttemptRecorded
from app.domain.shared.value_objects import Email, Duration, ReviewInterval, MasteryValue, MemoryValue


# ============================================================
# Clock Tests
# ============================================================


class TestSystemClock:
    def test_now_returns_utc(self) -> None:
        clock = SystemClock()
        now = clock.now()
        assert now.tzinfo is not None
        assert now.tzinfo.utcoffset(now) == timedelta(0)

    def test_utcnow_equals_now(self) -> None:
        clock = SystemClock()
        assert clock.now() == clock.utcnow()


class TestFixedClock:
    def test_fixed_time(self) -> None:
        fixed = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed)
        assert clock.now() == fixed
        assert clock.utcnow() == fixed

    def test_advance(self) -> None:
        fixed = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed)
        clock.advance(hours=1)
        assert clock.now() == fixed + timedelta(hours=1)

    def test_set(self) -> None:
        clock = FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
        new_time = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
        clock.set(new_time)
        assert clock.now() == new_time


# ============================================================
# ID Generation Tests
# ============================================================


class TestUuidV4Generator:
    def test_generates_unique_ids(self) -> None:
        gen = UuidV4Generator()
        id1 = gen.generate()
        id2 = gen.generate()
        assert id1 != id2

    def test_generates_uuid(self) -> None:
        from uuid import UUID
        gen = UuidV4Generator()
        assert isinstance(gen.generate(), UUID)


class TestUuidV7Generator:
    def test_generates_unique_ids(self) -> None:
        gen = UuidV7Generator()
        id1 = gen.generate()
        id2 = gen.generate()
        assert id1 != id2

    def test_time_ordered(self) -> None:
        """UUID v7 IDs generated later should be greater (sortable)."""
        gen = UuidV7Generator()
        id1 = gen.generate()
        id2 = gen.generate()
        # The second ID should be >= the first (time-ordered)
        assert id2 >= id1


class TestDeterministicIdGenerator:
    def test_deterministic_sequence(self) -> None:
        gen = DeterministicIdGenerator(start=0)
        id1 = gen.generate()
        id2 = gen.generate()
        assert id1 != id2

    def test_reset(self) -> None:
        gen = DeterministicIdGenerator(start=0)
        id1 = gen.generate()
        gen.reset(0)
        id2 = gen.generate()
        assert id1 == id2  # Same after reset


# ============================================================
# Cache Tests
# ============================================================


class TestLocalCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self) -> None:
        cache = LocalCache()
        await cache.set("key", {"value": 42})
        result = await cache.get("key")
        assert result == {"value": 42}

    @pytest.mark.asyncio
    async def test_get_missing_key(self) -> None:
        cache = LocalCache()
        result = await cache.get("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        cache = LocalCache()
        await cache.set("key", "value")
        await cache.delete("key")
        assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_exists(self) -> None:
        cache = LocalCache()
        await cache.set("key", "value")
        assert await cache.exists("key")
        assert not await cache.exists("missing")

    @pytest.mark.asyncio
    async def test_increment(self) -> None:
        cache = LocalCache()
        result = await cache.increment("counter")
        assert result == 1
        result = await cache.increment("counter", 5)
        assert result == 6

    @pytest.mark.asyncio
    async def test_ttl_expiration(self) -> None:
        cache = LocalCache()
        await cache.set("key", "value", ttl_seconds=0)  # Expires immediately
        # The TTL is 0 seconds, so it should be expired
        import time
        time.sleep(0.01)
        result = await cache.get("key")
        assert result is None


# ============================================================
# Event Serializer Tests
# ============================================================


class TestEventSerializer:
    def test_serialize_attempt_recorded(self) -> None:
        concept_id = uuid4()
        event = AttemptRecorded(
            attempt_id=uuid4(),
            learner_enrollment_id=uuid4(),
            concept_ids=(concept_id,),
            scoring_outcome=ScoringOutcome.CORRECT,
            content_version_id=uuid4(),
            template_version_id=uuid4(),
            algorithm_version_id=uuid4(),
            hint_used=False,
            attempt_intent="practice",
        )

        serialized = EventSerializer.serialize(
            event,
            actor_user_id=uuid4(),
            correlation_id="test-correlation",
            originating_schema="assessment",
        )

        assert serialized["event_type"] == "AttemptRecorded"
        assert serialized["payload"]["scoring_outcome"] == "correct"
        assert serialized["payload"]["hint_used"] is False
        assert serialized["metadata"]["originating_schema"] == "assessment"
        assert serialized["payload_schema_version"] == "1"

    def test_serialize_includes_aggregate_id(self) -> None:
        attempt_id = uuid4()
        enrollment_id = uuid4()

        event = AttemptRecorded(
            attempt_id=attempt_id,
            learner_enrollment_id=enrollment_id,
            concept_ids=(uuid4(),),
            scoring_outcome=ScoringOutcome.CORRECT,
            content_version_id=uuid4(),
            template_version_id=uuid4(),
            algorithm_version_id=uuid4(),
            hint_used=False,
            attempt_intent="practice",
        )

        serialized = EventSerializer.serialize(event)

        # The aggregate_id should be the first recognized ID field
        assert serialized["aggregate_id"] == str(attempt_id)

    def test_deserialize(self) -> None:
        original = {
            "event_type": "AttemptRecorded",
            "event_id": str(uuid4()),
            "occurred_at": "2026-07-02T12:00:00+00:00",
            "aggregate_id": str(uuid4()),
            "payload": {"scoring_outcome": "correct"},
            "metadata": {"originating_schema": "assessment"},
        }

        deserialized = EventSerializer.deserialize(original)

        assert deserialized["event_type"] == "AttemptRecorded"
        assert deserialized["payload"]["scoring_outcome"] == "correct"


# ============================================================
# Value Object Round-Trip Tests (verify domain purity)
# ============================================================


class TestValueObjectIntegrity:
    """Verify that value objects from the domain layer work correctly
    when used by infrastructure components."""

    def test_email_normalization(self) -> None:
        email = Email("Alex@Example.COM")
        assert email.value == "alex@example.com"
        assert email.domain == "example.com"
        assert email.local_part == "alex"

    def test_review_interval_expand_contract(self) -> None:
        ri = ReviewInterval(10)
        expanded = ri.expand(2.5)
        assert expanded.days == 25
        contracted = expanded.contract(0.3)
        assert contracted.days == 7  # 25 * 0.3 = 7.5 → 7

    def test_mastery_value_bounds(self) -> None:
        from app.domain.shared.kernel import InvariantViolation
        with pytest.raises(InvariantViolation):
            MasteryValue(1.5)
        with pytest.raises(InvariantViolation):
            MemoryValue(-0.1)

    def test_duration_arithmetic(self) -> None:
        d1 = Duration(100)
        d2 = Duration(200)
        assert (d1 + d2).seconds == 300
        assert (d2 - d1).seconds == 100
