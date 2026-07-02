"""Identity context — UserCredential local entity.

A :class:`UserCredential` represents one authentication factor for a user.
A user may have several: a password credential, plus one or more OAuth
credentials (Google, GitHub, etc.). All credentials live inside the
:class:`User` aggregate boundary and are loaded/saved only through it.

There are two credential kinds:

- **Password** — set via :meth:`UserCredential.for_password`. Stores a
  ``password_hash`` (never a plaintext password). Provider fields are
  ``None``.
- **OAuth** — set via :meth:`UserCredential.for_oauth`. Stores a
  ``provider`` (e.g., ``"google"``) and the ``provider_user_id`` (the
  stable identifier returned by the IdP). ``password_hash`` is ``None``.

Invariants:
- A PASSWORD credential must have a non-empty ``password_hash``.
- An OAUTH credential must have both ``provider`` and ``provider_user_id``.
- A credential cannot be both password and oauth simultaneously.
"""

from __future__ import annotations

from app.domain.shared.ids import CredentialId, UserId
from app.domain.shared.kernel import CredentialType, Entity, InvariantViolation


class UserCredential(Entity):
    """A single authentication factor for a user.

    Equality is by :class:`CredentialId` — two credentials with the same
    ID are the same entity, even if their other fields differ.
    """

    def __init__(
        self,
        *,
        id: CredentialId,
        user_id: UserId,
        credential_type: CredentialType,
        password_hash: str | None = None,
        provider: str | None = None,
        provider_user_id: str | None = None,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.credential_type = credential_type
        self.password_hash = password_hash
        self.provider = provider
        self.provider_user_id = provider_user_id
        self._validate()

    # ----- factories ---------------------------------------------------

    @classmethod
    def for_password(cls, user_id: UserId, password_hash: str) -> UserCredential:
        """Create a password credential.

        Args:
            user_id: The user this credential belongs to.
            password_hash: A pre-hashed password (e.g., Argon2id output).
                The domain never accepts or stores plaintext passwords.

        Returns:
            A new :class:`UserCredential` of type ``PASSWORD``.
        """
        return cls(
            id=CredentialId.generate(),
            user_id=user_id,
            credential_type=CredentialType.PASSWORD,
            password_hash=password_hash,
            provider=None,
            provider_user_id=None,
        )

    @classmethod
    def for_oauth(
        cls,
        user_id: UserId,
        provider: str,
        provider_user_id: str,
    ) -> UserCredential:
        """Create an OAuth credential.

        Args:
            user_id: The user this credential belongs to.
            provider: The IdP identifier (e.g., ``"google"``, ``"github"``).
            provider_user_id: The stable subject identifier issued by the IdP.

        Returns:
            A new :class:`UserCredential` of type ``OAUTH``.
        """
        return cls(
            id=CredentialId.generate(),
            user_id=user_id,
            credential_type=CredentialType.OAUTH,
            password_hash=None,
            provider=provider,
            provider_user_id=provider_user_id,
        )

    # ----- validation --------------------------------------------------

    def _validate(self) -> None:
        """Enforce credential-type invariants."""
        if self.credential_type == CredentialType.PASSWORD:
            if not self.password_hash or not isinstance(self.password_hash, str):
                raise InvariantViolation(
                    "UserCredential",
                    "PASSWORD credentials must have a non-empty password_hash",
                )
            if self.provider is not None or self.provider_user_id is not None:
                raise InvariantViolation(
                    "UserCredential",
                    "PASSWORD credentials must not set provider fields",
                )
        elif self.credential_type == CredentialType.OAUTH:
            if not self.provider or not isinstance(self.provider, str):
                raise InvariantViolation(
                    "UserCredential",
                    "OAUTH credentials must have a non-empty provider",
                )
            if not self.provider_user_id or not isinstance(self.provider_user_id, str):
                raise InvariantViolation(
                    "UserCredential",
                    "OAUTH credentials must have a non-empty provider_user_id",
                )
            if self.password_hash is not None:
                raise InvariantViolation(
                    "UserCredential",
                    "OAUTH credentials must not set a password_hash",
                )
        else:
            raise InvariantViolation(
                "UserCredential",
                f"Unknown credential type: {self.credential_type!r}",
            )

    # ----- behaviour ---------------------------------------------------

    @property
    def is_password(self) -> bool:
        """True if this is a password credential."""
        return self.credential_type == CredentialType.PASSWORD

    @property
    def is_oauth(self) -> bool:
        """True if this is an OAuth credential."""
        return self.credential_type == CredentialType.OAUTH

    def matches_oauth(self, provider: str, provider_user_id: str) -> bool:
        """True if this credential matches the given OAuth identity."""
        return (
            self.is_oauth
            and self.provider == provider
            and self.provider_user_id == provider_user_id
        )

    # ----- repr --------------------------------------------------------

    def __repr__(self) -> str:
        if self.is_password:
            return (
                f"UserCredential(id={self.id}, user_id={self.user_id}, "
                f"type=password)"
            )
        return (
            f"UserCredential(id={self.id}, user_id={self.user_id}, "
            f"type=oauth, provider={self.provider!r})"
        )


__all__ = ["UserCredential"]
