# Task: identity-domain — Identity bounded context (domain layer)

**Agent:** identity-domain
**Started:** 2026-07-02
**Status:** ✅ Complete
**Scope:** `backend/app/domain/identity/` (pure Python, no infrastructure)

## Objective

Implement the Identity bounded context of the Mastery Engine domain layer:
the `User` aggregate root, its local entities (`UserProfile`,
`UserCredential`), domain events, context-specific exceptions, and the
abstract `UserRepository` contract.

## Files written

| Path | Purpose |
| --- | --- |
| `backend/app/domain/identity/exceptions.py` | `IdentityError` base + 8 specific exception subclasses (`EmailAlreadyRegistered`, `EmailNotVerified`, `CannotSuspendAdmin`, `CannotDisableMFAForAdmin`, `CannotCancelDeletionPastGrace`, `AlreadyPendingDeletion`, `MFAAlreadyEnabled`, `MFANotEnabled`). |
| `backend/app/domain/identity/events.py` | 10 frozen-dataclass domain events inheriting from `DomainEvent`, all `kw_only=True` so required fields like `user_id` can follow the inherited defaulted `event_id`/`occurred_at` fields. |
| `backend/app/domain/identity/profile.py` | `UserProfile` local entity. Validates display_name (1–100 chars), timezone, locale, avatar_url, preferences. Identity is the parent `user_id`. Exposes a partial `update()` that returns the diff of changed fields. |
| `backend/app/domain/identity/credential.py` | `UserCredential` local entity with two factories: `for_password` (requires `password_hash`, no provider fields) and `for_oauth` (requires `provider` + `provider_user_id`, no password_hash). Type-specific invariants enforced in `_validate()`. |
| `backend/app/domain/identity/user.py` | `User` aggregate root. Factory `User.register(...)` creates user in `PENDING_VERIFICATION`. Implements the full state machine via `verify_email`, `suspend(reason, *, is_admin)`, `reactivate`, `request_deletion`, `cancel_deletion`, `anonymize`, `enable_mfa`, `disable_mfa(*, is_admin)`, `update_profile`. Every transition validates current state, mutates, records a domain event via `_record_event`. `anonymize` scrubs PII (email → placeholder, profile → defaults, credentials cleared). |
| `backend/app/domain/identity/repository.py` | `UserRepository(ABC)` with abstract `get_by_id`, `get_by_email`, `add`, `save` (all `async`). Two non-abstract convenience helpers `get_by_id_or_raise` / `get_by_email_or_raise` raising `EntityNotFound`. |
| `backend/app/domain/identity/__init__.py` | Re-exports the full public surface (`User`, `UserProfile`, `UserCredential`, all 10 events, all 8+1 exceptions, `UserRepository`). |

## State machine enforced

```
PENDING_VERIFICATION
       │ verify_email()
       ▼
     ACTIVE ◄──────► SUSPENDED        (suspend / reactivate)
       │ request_deletion()
       ▼
  PENDING_DELETION ──cancel_deletion()──► ACTIVE   (within grace window)
       │ anonymize()
       ▼
    ANONYMIZED  (terminal)
```

Every transition checks `self._assert_status(expected, action)` and raises
`InvalidStateTransition` on mismatch. Every transition calls
`self._record_event(...)`.

## Invariants enforced

- Email must be verified (`email_verified_at` set) before status can go
  ACTIVE — happens atomically inside `verify_email()`.
- `suspend(reason, is_admin=True)` raises `CannotSuspendAdmin`.
- `disable_mfa(is_admin=True)` raises `CannotDisableMFAForAdmin`.
- `anonymize()` requires `PENDING_DELETION` (raises `InvalidStateTransition`).
- `cancel_deletion(now=...)` raises `CannotCancelDeletionPastGrace` if
  `now >= scheduled_anonymization_at`.
- `request_deletion()` raises `AlreadyPendingDeletion` if already pending,
  and `InvalidStateTransition` if `scheduled_anonymization_at <= now`.
- `enable_mfa()` raises `MFAAlreadyEnabled` if already on.
- `disable_mfa()` raises `MFANotEnabled` if already off.
- `UserProfile` validates display_name length, non-empty timezone/locale,
  non-empty avatar_url (when set), preferences is a dict.
- `UserCredential` enforces PASSWORD-has-hash / OAUTH-has-provider pairings.

## Side-effect on shared kernel

While wiring up imports I discovered a **pre-existing bug** in
`backend/app/domain/shared/__init__.py`:

```python
from app.domain.shared.kernel import (
    ...
    Email as _Email,  # re-exported from value_objects instead
    ...
)
```

The line attempted to import `Email` from `kernel`, but `Email` actually
lives in `value_objects.py`. The comment even said "re-exported from
value_objects instead", yet the import was never removed. This broke
**every** `from app.domain.shared import ...` statement project-wide.

I removed the dead/broken `Email as _Email` line (it was unreferenced
anywhere in the repo — verified with grep). `Email` is still correctly
re-exported lower in the same file from `value_objects`. After this fix,
all identity imports resolve cleanly.

## Validation

- All 7 files parse cleanly under Python 3.13 (`ast.parse` + `compile`).
- All imports resolve (verified end-to-end).
- Comprehensive smoke test (21 sections) covers: registration, email
  normalization, display_name stripping, all state-transition guards,
  suspend/reactivate, deletion request/cancel/anonymize, MFA
  enable/disable + admin guards, profile update + no-op, credential
  factories + invariants, UserProfile validation, abstract repository
  instantiation refusal. **All passing.**
- Verified no infrastructure imports leak in (no `sqlalchemy`, `fastapi`,
  `pydantic`, `redis`, `asyncpg`, `alembic`). Only stdlib +
  `app.domain.shared` + intra-package imports.
- `ruff check --fix` applied (auto-fixed F401 unused imports, I001
  unsorted imports, UP017 timezone.utc). 22 remaining warnings are all
  in categories the shared kernel itself triggers (N818 exception name
  suffix, RUF002 unicode dashes in docstrings, RUF022 unsorted
  `__all__`, A002 `id` builtin shadowing — which is required by the
  shared `Entity._identity_key = getattr(self, "id", None)` convention,
  TC001/TC003 type-checking blocks). Style is consistent with the
  shared kernel; project does not strictly enforce these rules.

## Notes for downstream agents

- The `User` constructor is **public** and intended for reconstitution
  from persistence (repositories use it to rebuild aggregates from
  stored state). New users go through `User.register(...)`.
- The `is_admin` flag on `suspend` and `disable_mfa` is passed by the
  caller — the Identity context does not track admin status itself.
  The Administration context (or an application service) owns that
  determination and passes it in.
- `User.credentials` returns a copy of the internal list — credential
  mutations must go through aggregate methods (none provided yet; add
  `add_credential` / `replace_password_hash` when needed).
- `UserRepository` methods are `async` to match the async SQLAlchemy
  pattern the rest of the backend uses (see
  `backend/app/infrastructure/database.py`).
- Anonymized users are kept in storage for referential integrity —
  repository implementations should still return them from
  `get_by_id`. Email becomes `anonymized+{uuid}@anonymized.invalid`
  (the `.invalid` TLD guarantees no collision with real addresses).
- `DELETION_GRACE_PERIOD` defaults to 30 days; per-call override is
  available via the `scheduled_anonymization_at` parameter on
  `request_deletion()`.
