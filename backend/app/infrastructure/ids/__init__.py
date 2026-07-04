"""UUID v7 generation service.

UUID v7 is time-ordered (sortable) and globally unique, making it ideal for
database primary keys. The time-ordered property improves B-tree index
locality for insert-heavy tables (attempts, outbox_events).

For testing, a deterministic ID generator is provided.
"""

from __future__ import annotations

import os
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any


class IdGenerator(ABC):
    """Abstract ID generator."""

    @abstractmethod
    def generate(self) -> uuid.UUID:
        """Generate a new UUID."""
        ...


class UuidV7Generator(IdGenerator):
    """Generates UUID v7 (time-ordered).

    UUID v7 format:
    - 48 bits: Unix timestamp in milliseconds
    - 12 bits: version (0x7) + random
    - 62 bits: random + variant

    This implementation uses a simple approach. For production, consider
    using the `uuid_utils` library or PostgreSQL's `uuidv7()` function.
    """

    def __init__(self) -> None:
        self._last_timestamp_ms = 0
        self._counter = 0

    def generate(self) -> uuid.UUID:
        """Generate a UUID v7."""
        timestamp_ms = int(time.time() * 1000)

        # Ensure monotonicity within the same millisecond
        if timestamp_ms <= self._last_timestamp_ms:
            self._counter += 1
            timestamp_ms = self._last_timestamp_ms
        else:
            self._last_timestamp_ms = timestamp_ms
            self._counter = 0

        # Build UUID v7
        # 48-bit timestamp | 4-bit version (7) | 12-bit random_a | 2-bit variant | 62-bit random_b
        timestamp_bytes = timestamp_ms.to_bytes(6, byteorder="big")

        # Random bytes for the rest
        random_bytes = os.urandom(10)

        # Set version (7) in the 7th byte
        versioned_byte = (random_bytes[0] & 0x0F) | 0x70  # version 7
        # Set variant (10) in the 9th byte
        variant_byte = (random_bytes[2] & 0x3F) | 0x80

        uuid_bytes = (
            timestamp_bytes
            + bytes([versioned_byte, random_bytes[1]])
            + bytes([variant_byte])
            + random_bytes[3:]
        )

        return uuid.UUID(bytes=uuid_bytes)


class UuidV4Generator(IdGenerator):
    """Generates UUID v4 (random). Used for development/testing."""

    def generate(self) -> uuid.UUID:
        return uuid.uuid4()


class DeterministicIdGenerator(IdGenerator):
    """Generates deterministic UUIDs for testing.

    Each call to generate() returns the next UUID in a sequence,
    making test assertions predictable.
    """

    def __init__(self, start: int = 0) -> None:
        self._counter = start

    def generate(self) -> uuid.UUID:
        """Generate a deterministic UUID based on a counter."""
        result = uuid.uuid5(uuid.NAMESPACE_DNS, str(self._counter))
        self._counter += 1
        return result

    def reset(self, start: int = 0) -> None:
        """Reset the counter."""
        self._counter = start
