"""Identity context — mappers between domain entities and DTOs.

No mapping logic inside handlers. All domain ↔ DTO conversion lives here.
"""

from __future__ import annotations

from app.application.identity.dto import (
    AuthResultDTO,
    SessionDTO,
    UserDTO,
    UserProfileDTO,
    UserSummaryDTO,
    UserWithProfileDTO,
)
from app.domain.identity.user import User


class UserMapper:
    """Maps User aggregate to DTOs."""

    @staticmethod
    def to_dto(user: User) -> UserDTO:
        """Map a User to a UserDTO."""
        return UserDTO(
            id=user.id.value,
            email=user.email.value,
            status=user.status.value,
            mfa_enabled=user.mfa_enabled,
            email_verified_at=user.email_verified_at,
            created_at=user.created_at,
        )

    @staticmethod
    def to_summary_dto(user: User) -> UserSummaryDTO:
        """Map a User to a UserSummaryDTO."""
        return UserSummaryDTO(
            id=user.id.value,
            email=user.email.value,
            status=user.status.value,
            created_at=user.created_at,
        )

    @staticmethod
    def to_profile_dto(user: User) -> UserProfileDTO:
        """Map a User's profile to a UserProfileDTO."""
        profile = user.profile
        return UserProfileDTO(
            display_name=profile.display_name,
            timezone=profile.timezone,
            locale=profile.locale,
            avatar_url=profile.avatar_url,
            preferences=dict(profile.preferences) if profile.preferences else {},
        )

    @staticmethod
    def to_with_profile_dto(user: User) -> UserWithProfileDTO:
        """Map a User to a UserWithProfileDTO."""
        return UserWithProfileDTO(
            user=UserMapper.to_dto(user),
            profile=UserMapper.to_profile_dto(user),
        )

    @staticmethod
    def to_auth_result_dto(user: User, access_token: str, expires_in: int) -> AuthResultDTO:
        """Map a User + token to an AuthResultDTO."""
        return AuthResultDTO(
            access_token=access_token,
            expires_in=expires_in,
            user=UserMapper.to_dto(user),
        )
