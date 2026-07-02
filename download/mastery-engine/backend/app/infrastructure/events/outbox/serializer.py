"""Event serializer — serializes domain events to JSON for the outbox.

Each event is serialized with:
- event_type: the event class name
- event_id: unique UUID
- occurred_at: ISO 8601 timestamp
- aggregate_id: the aggregate's UUID
- payload: the event's data fields
- payload_schema_version: for schema evolution
- metadata: correlation_id, actor_user_id, etc.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.shared.kernel import DomainEvent


class EventSerializer:
    """Serializes domain events to JSON-compatible dicts for the outbox."""

    @staticmethod
    def serialize(
        event: DomainEvent,
        *,
        actor_user_id: UUID | None = None,
        correlation_id: str | None = None,
        originating_schema: str = "unknown",
    ) -> dict[str, Any]:
        """Serialize a domain event to a JSON-compatible dict.

        The dict is stored in the outbox_events.payload JSONB column.
        """
        payload = {}
        if dataclasses.is_dataclass(event):
            for field in dataclasses.fields(event):
                value = getattr(event, field.name)
                payload[field.name] = EventSerializer._serialize_value(value)

        return {
            "event_type": event.event_type,
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "aggregate_id": str(EventSerializer._extract_aggregate_id(event)),
            "payload": payload,
            "payload_schema_version": "1",
            "metadata": {
                "actor_user_id": str(actor_user_id) if actor_user_id else None,
                "correlation_id": correlation_id,
                "originating_schema": originating_schema,
            },
        }

    @staticmethod
    def deserialize(data: dict[str, Any]) -> dict[str, Any]:
        """Deserialize an outbox payload back to a dict.

        Note: This does NOT reconstruct the domain event object — it
        returns the payload dict for subscribers to process. The
        subscriber decides how to interpret the payload.
        """
        return {
            "event_type": data["event_type"],
            "event_id": data["event_id"],
            "occurred_at": data["occurred_at"],
            "aggregate_id": data["aggregate_id"],
            "payload": data["payload"],
            "metadata": data.get("metadata", {}),
        }

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """Serialize a single value to JSON-compatible format."""
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (list, tuple)):
            return [EventSerializer._serialize_value(v) for v in value]
        if isinstance(value, dict):
            return {k: EventSerializer._serialize_value(v) for k, v in value.items()}
        if hasattr(value, "value"):  # Enum
            return value.value
        return value

    @staticmethod
    def _extract_aggregate_id(event: DomainEvent) -> UUID:
        """Extract the aggregate ID from a domain event."""
        for attr in ("user_id", "enrollment_id", "session_id", "attempt_id",
                     "mastery_score_id", "review_id", "algorithm_version_id",
                     "recommendation_id", "achievement_id", "instance_id"):
            val = getattr(event, attr, None)
            if val is not None:
                if isinstance(val, UUID):
                    return val
                return UUID(str(val))
        return event.event_id
