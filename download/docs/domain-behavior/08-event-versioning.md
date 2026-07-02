# 08 — Event Versioning

> Event schema evolution, backward compatibility, replay, deprecation, migration, version numbering.

---

## Versioning Principles

1. **Events are immutable once published** — a published event's schema cannot change; changes produce a new version.
2. **Backward compatibility is the default** — new subscribers can read old events; old subscribers can read new events (with unknown fields ignored).
3. **Breaking changes produce a new event version** — e.g., `AttemptRecorded` v2 alongside v1.
4. **Versioning is per event type** — each event type has its own version trajectory.
5. **Versions are documented** — every event version has a changelog.

---

## Version Numbering

- **Format**: `vMAJOR` (e.g., `v1`, `v2`).
- **Stored in**: `outbox_events.payload_schema_version` (per event).
- **Default**: `v1` for new events.
- **Bump on**: breaking schema changes (field removal, type change, semantic change).
- **No bump on**: additive changes (new optional field).

---

## Schema Evolution Rules

### Backward-compatible changes (no version bump)

- **Adding a field** (optional, with default or nullable) — old subscribers ignore the new field; new subscribers use it.
- **Adding an enum value** — old subscribers handle the unknown value gracefully (default behavior).
- **Relaxing a constraint** (e.g., making a required field optional).

### Breaking changes (version bump required)

- **Removing a field** — old subscribers expect it; new events don't have it.
- **Changing a field type** (e.g., string → integer) — old subscribers can't parse.
- **Changing a field's semantic meaning** (e.g., `amount` was cents, now dollars).
- **Restricting a constraint** (e.g., making an optional field required).
- **Removing an enum value**.

### When a breaking change is needed

1. **Create a new event version** (e.g., `AttemptRecorded` v2).
2. **Publish both versions in parallel** during the migration period: the producer writes both v1 and v2 to the outbox (v2 with the new schema, v1 with the old schema derived from v2).
3. **Migrate subscribers** to v2.
4. **Deprecate v1** after all subscribers have migrated (no consumers for v1).
5. **Stop publishing v1** (the producer writes only v2).

---

## Backward Compatibility in Practice

### Subscribers reading old events

A v2 subscriber reading a v1 event:
- The subscriber's handler accepts both v1 and v2 payloads.
- For v1, the subscriber uses defaults for v2-only fields.
- The subscriber's handler is version-aware (checks `payload_schema_version`).

### Old subscribers reading new events

A v1 subscriber reading a v2 event (additive change only):
- The v1 subscriber ignores v2-only fields.
- The v1 fields are unchanged.

A v1 subscriber cannot read a v2 event with breaking changes — hence the parallel-publishing strategy.

---

## Replay

Replay (re-processing historical events) requires:

1. **Version-aware subscribers** — the subscriber's handler can process any version of the event.
2. **Payload preservation** — the outbox stores the original payload (including `payload_schema_version`); replay re-publishes the original payload, not a re-serialized version.
3. **Idempotent subscribers** — re-processing the same event produces the same result (see `11-idempotency.md`).

**Replay procedure**:
1. Administrator selects an event type and date range.
2. Dispatcher re-publishes events from the outbox (original payloads).
3. Subscribers process them, applying version-aware logic.
4. Idempotency ensures no double-application.

**Limitations**:
- Replay cannot undo side effects of the original processing (e.g., an email already sent). Replay is for state reconstruction, not side-effect reversal.
- Replay of events with external side effects (e.g., `NotificationSent`) is no-op (the notification was already sent; re-publishing has no effect).

---

## Deprecation

An event version is deprecated when:
- All subscribers have migrated to the new version.
- The producer stops publishing the old version.

**Deprecation process**:
1. **Announce** the deprecation (engineering team, ADR if significant).
2. **Stop publishing** the old version (producer writes only new version).
3. **Retain** the old version's historical events in the outbox (for replay and audit).
4. **Mark as deprecated** in the event catalog.

Deprecated event versions are never deleted; they remain in the outbox for the event's retention period.

---

## Migration

Migrating subscribers from v1 to v2:

1. **Deploy v2-aware subscriber** (handles both v1 and v2).
2. **Verify** v2 handling is correct (staging).
3. **Producer starts publishing v2** (in parallel with v1 during migration).
4. **Monitor** v2 processing.
5. **Producer stops publishing v1** (after confirming all subscribers handle v2).
6. **Remove v1 handling** from subscribers (future cleanup; optional).

**Migration duration**: typically 2–4 weeks (one release cycle for producer + subscribers to be deployed).

---

## Versioning and the Outbox

The outbox stores:
- `event_type` — the event name (e.g., `AttemptRecorded`).
- `payload` — the event payload (JSONB).
- `payload_schema_version` — the version (e.g., `v1`, `v2`).

The dispatcher routes events to subscribers by `event_type`; subscribers check `payload_schema_version` to apply version-aware logic.

---

## Versioning and Eventual Consistency

During a migration (parallel publishing of v1 and v2), subscribers may process v1 and v2 events for the same aggregate. Idempotency ensures no double-application; the final state is consistent.

See `09-eventual-consistency.md` for the consistency model.

---

## Event Version Changelog

Every event type maintains a changelog documenting each version:

```
AttemptRecorded:
  v1 (2026-07-02): Initial version. Payload: {attempt_id, learner_enrollment_id, concept_ids, scoring_outcome, content_version_id, template_version_id, algorithm_version_id, recorded_at}.
  v2 (future): Added `time_to_answer_ms` to payload (additive; backward-compatible).
  v3 (future): Removed `concept_ids` (breaking; replaced by query through template_concepts). Migration: parallel publish v2 and v3 for 4 weeks.
```

The changelog is maintained in the event catalog (`07-event-catalog.md`) and in the event's schema definition (a versioned Pydantic model in the codebase).

---

*End of Event Versioning.*
