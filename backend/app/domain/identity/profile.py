"""Identity context — UserProfile local entity.

The :class:`UserProfile` is a *local entity* that lives inside the
:class:`User` aggregate. It holds the user's display attributes and
preferences. It has no identity of its own — its identity is derived
from its parent User (one profile per user).

Because it is part of the User aggregate boundary, it is only ever
loaded or saved through the User aggregate root. All mutations go
through the User so the aggregate can record domain events and enforce
invariants.

Validation rules:
- ``display_name``: 1–100 characters after stripping whitespace.
- ``timezone``: a non-empty IANA timezone string (e.g., ``"Europe/Berlin"``).
- ``locale``: a non-empty locale tag (e.g., ``"en-US"``).
- ``avatar_url``: optional; if present, must be a non-empty string.
- ``preferences``: an arbitrary dict of preference key/values; defaults to ``{}``.
"""

from __future__ import annotations

from typing import Any

from app.domain.shared.ids import UserId
from app.domain.shared.kernel import Entity, InvariantViolation


class UserProfile(Entity):
    """Local entity holding a user's display attributes and preferences.

    Invariants:
        - ``display_name`` must be 1–100 characters.
        - ``timezone`` must be a non-empty string (IANA name).
        - ``locale`` must be a non-empty string (BCP 47 tag).
        - ``avatar_url``, if set, must be non-empty.
        - ``preferences`` must be a dict (may be empty).

    Equality is by parent ``user_id`` — there is at most one profile per
    user, so two profiles with the same ``user_id`` are the same entity.
    """

    MAX_DISPLAY_NAME_LENGTH = 100
    MIN_DISPLAY_NAME_LENGTH = 1

    def __init__(
        self,
        *,
        user_id: UserId,
        display_name: str,
        timezone: str = "UTC",
        locale: str = "en-US",
        avatar_url: str | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> None:
        self._user_id = user_id
        self.display_name = display_name
        self.timezone = timezone
        self.locale = locale
        self.avatar_url = avatar_url
        self.preferences: dict[str, Any] = dict(preferences) if preferences else {}
        self._validate()

    # ----- identity ----------------------------------------------------

    @property
    def _identity_key(self) -> Any:
        """Identity is the parent user's ID — one profile per user."""
        return self._user_id

    @property
    def user_id(self) -> UserId:
        """The ID of the User that owns this profile."""
        return self._user_id

    # ----- validation --------------------------------------------------

    def _validate(self) -> None:
        """Run all field validations; raise :class:`InvariantViolation` on failure."""
        name = self.display_name.strip() if isinstance(self.display_name, str) else ""
        if len(name) < self.MIN_DISPLAY_NAME_LENGTH:
            raise InvariantViolation(
                "UserProfile",
                f"display_name must be at least {self.MIN_DISPLAY_NAME_LENGTH} character(s)",
            )
        if len(name) > self.MAX_DISPLAY_NAME_LENGTH:
            raise InvariantViolation(
                "UserProfile",
                f"display_name must be at most {self.MAX_DISPLAY_NAME_LENGTH} characters",
            )
        # Store the stripped form so callers cannot sneak in whitespace-only names.
        self.display_name = name

        if not isinstance(self.timezone, str) or not self.timezone.strip():
            raise InvariantViolation(
                "UserProfile",
                f"timezone must be a non-empty IANA string, got {self.timezone!r}",
            )
        self.timezone = self.timezone.strip()

        if not isinstance(self.locale, str) or not self.locale.strip():
            raise InvariantViolation(
                "UserProfile",
                f"locale must be a non-empty string, got {self.locale!r}",
            )
        self.locale = self.locale.strip()

        if self.avatar_url is not None:
            if not isinstance(self.avatar_url, str) or not self.avatar_url.strip():
                raise InvariantViolation(
                    "UserProfile",
                    "avatar_url, when present, must be a non-empty string",
                )
            self.avatar_url = self.avatar_url.strip()

        if not isinstance(self.preferences, dict):
            raise InvariantViolation(
                "UserProfile",
                f"preferences must be a dict, got {type(self.preferences).__name__}",
            )

    # ----- mutation ----------------------------------------------------

    def update(
        self,
        *,
        display_name: str | None = None,
        timezone: str | None = None,
        locale: str | None = None,
        avatar_url: str | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply a partial update and return the map of fields that changed.

        Only fields explicitly passed (not ``None``) are considered for
        update. The returned dict maps ``field_name → new_value`` for any
        field whose value actually changed. Callers (the User aggregate)
        use this to emit a ``UserProfileUpdated`` event with the diff.

        Note: ``avatar_url=None`` is treated as "no change" rather than
        "clear the avatar" — clearing must be expressed via an empty
        string. This avoids ambiguity between "omit" and "clear".
        """
        changed: dict[str, Any] = {}

        if display_name is not None and display_name.strip() != self.display_name:
            self.display_name = display_name
            changed["display_name"] = self.display_name

        if timezone is not None and timezone.strip() != self.timezone:
            self.timezone = timezone
            changed["timezone"] = self.timezone

        if locale is not None and locale.strip() != self.locale:
            self.locale = locale
            changed["locale"] = self.locale

        if avatar_url is not None and avatar_url != (self.avatar_url or ""):
            self.avatar_url = avatar_url
            changed["avatar_url"] = self.avatar_url

        if preferences is not None and preferences != self.preferences:
            self.preferences = dict(preferences)
            changed["preferences"] = dict(self.preferences)

        # Re-validate after applying changes — invariant violations on the
        # new values will surface here before the caller commits.
        self._validate()
        return changed

    # ----- repr --------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"UserProfile(user_id={self._user_id}, display_name={self.display_name!r}, "
            f"timezone={self.timezone!r}, locale={self.locale!r})"
        )


__all__ = ["UserProfile"]
