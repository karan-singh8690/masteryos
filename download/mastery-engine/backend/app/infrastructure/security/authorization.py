"""Authorization service — fine-grained RBAC with object-level checks.

Roles:
- learner: study within enrolled subjects
- instructor: author/review content within assigned subjects
- content_editor: edit content across subjects
- organization_admin: manage org members + view org analytics
- administrator: full platform access

Permissions are fine-grained (e.g., "content:concept:create", "admin:user:suspend").
Object-level authorization checks ownership (e.g., "is this your enrollment?").
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Role Definitions
# ============================================================

ROLE_LEARNER = "learner"
ROLE_INSTRUCTOR = "instructor"
ROLE_CONTENT_EDITOR = "content_editor"
ROLE_ORGANIZATION_ADMIN = "organization_admin"
ROLE_ADMINISTRATOR = "administrator"
ROLE_SYSTEM_ADMIN = "system_admin"

ALL_ROLES = [
    ROLE_LEARNER,
    ROLE_INSTRUCTOR,
    ROLE_CONTENT_EDITOR,
    ROLE_ORGANIZATION_ADMIN,
    ROLE_ADMINISTRATOR,
    ROLE_SYSTEM_ADMIN,
]


# ============================================================
# Permission Definitions
# ============================================================

# Identity
PERM_USER_READ_SELF = "identity:user:read_self"
PERM_USER_UPDATE_SELF = "identity:user:update_self"
PERM_USER_READ_ALL = "identity:user:read_all"
PERM_USER_SUSPEND = "identity:user:suspend"
PERM_USER_REACTIVATE = "identity:user:reactivate"
PERM_USER_ANONYMIZE = "identity:user:anonymize"
PERM_ROLE_GRANT = "identity:role:grant"
PERM_ROLE_REVOKE = "identity:role:revoke"

# Learning
PERM_ENROLLMENT_CREATE = "learning:enrollment:create"
PERM_ENROLLMENT_READ_SELF = "learning:enrollment:read_self"
PERM_ENROLLMENT_READ_ALL = "learning:enrollment:read_all"
PERM_SESSION_CREATE = "learning:session:create"
PERM_ATTEMPT_SUBMIT = "learning:attempt:submit"
PERM_PROGRESS_READ_SELF = "learning:progress:read_self"
PERM_PROGRESS_READ_ALL = "learning:progress:read_all"
PERM_MASTERY_READ_SELF = "learning:mastery:read_self"
PERM_MASTERY_READ_ALL = "learning:mastery:read_all"

# Content
PERM_CONTENT_READ = "content:read"
PERM_CONTENT_CREATE = "content:create"
PERM_CONTENT_UPDATE = "content:update"
PERM_CONTENT_PUBLISH = "content:publish"
PERM_CONTENT_ARCHIVE = "content:archive"
PERM_CONTENT_REVIEW = "content:review"

# Administration
PERM_ADMIN_PORTAL_ACCESS = "admin:portal:access"
PERM_AUDIT_LOG_READ = "admin:audit_log:read"
PERM_FEATURE_FLAG_MANAGE = "admin:feature_flag:manage"
PERM_SYSTEM_SETTING_MANAGE = "admin:system_setting:manage"
PERM_ALGORITHM_PUBLISH = "admin:algorithm:publish"

# Billing
PERM_SUBSCRIPTION_MANAGE_SELF = "billing:subscription:manage_self"
PERM_SUBSCRIPTION_MANAGE_ALL = "billing:subscription:manage_all"
PERM_INVOICE_READ_SELF = "billing:invoice:read_self"
PERM_INVOICE_READ_ALL = "billing:invoice:read_all"
PERM_INVOICE_REFUND = "billing:invoice:refund"

# Organization
PERM_ORG_MANAGE = "organization:manage"
PERM_ORG_ANALYTICS = "organization:analytics"


# ============================================================
# Role → Permission Mapping
# ============================================================

ROLE_PERMISSIONS: dict[str, set[str]] = {
    ROLE_LEARNER: {
        PERM_USER_READ_SELF,
        PERM_USER_UPDATE_SELF,
        PERM_ENROLLMENT_CREATE,
        PERM_ENROLLMENT_READ_SELF,
        PERM_SESSION_CREATE,
        PERM_ATTEMPT_SUBMIT,
        PERM_PROGRESS_READ_SELF,
        PERM_MASTERY_READ_SELF,
        PERM_CONTENT_READ,
        PERM_SUBSCRIPTION_MANAGE_SELF,
        PERM_INVOICE_READ_SELF,
    },
    ROLE_INSTRUCTOR: {
        # All learner permissions
        *{
            PERM_USER_READ_SELF,
            PERM_USER_UPDATE_SELF,
            PERM_ENROLLMENT_CREATE,
            PERM_ENROLLMENT_READ_SELF,
            PERM_SESSION_CREATE,
            PERM_ATTEMPT_SUBMIT,
            PERM_PROGRESS_READ_SELF,
            PERM_MASTERY_READ_SELF,
            PERM_CONTENT_READ,
            PERM_SUBSCRIPTION_MANAGE_SELF,
            PERM_INVOICE_READ_SELF,
        },
        # Plus content authoring
        PERM_CONTENT_CREATE,
        PERM_CONTENT_UPDATE,
        PERM_CONTENT_REVIEW,
    },
    ROLE_CONTENT_EDITOR: {
        *{
            PERM_USER_READ_SELF,
            PERM_USER_UPDATE_SELF,
            PERM_CONTENT_READ,
            PERM_CONTENT_CREATE,
            PERM_CONTENT_UPDATE,
            PERM_CONTENT_PUBLISH,
            PERM_CONTENT_ARCHIVE,
            PERM_CONTENT_REVIEW,
        },
    },
    ROLE_ORGANIZATION_ADMIN: {
        *{
            PERM_USER_READ_SELF,
            PERM_USER_UPDATE_SELF,
            PERM_CONTENT_READ,
            PERM_ORG_MANAGE,
            PERM_ORG_ANALYTICS,
        },
    },
    ROLE_ADMINISTRATOR: {
        # Administrators have all permissions
        PERM_USER_READ_SELF,
        PERM_USER_UPDATE_SELF,
        PERM_USER_READ_ALL,
        PERM_USER_SUSPEND,
        PERM_USER_REACTIVATE,
        PERM_USER_ANONYMIZE,
        PERM_ROLE_GRANT,
        PERM_ROLE_REVOKE,
        PERM_ENROLLMENT_CREATE,
        PERM_ENROLLMENT_READ_SELF,
        PERM_ENROLLMENT_READ_ALL,
        PERM_SESSION_CREATE,
        PERM_ATTEMPT_SUBMIT,
        PERM_PROGRESS_READ_SELF,
        PERM_PROGRESS_READ_ALL,
        PERM_MASTERY_READ_SELF,
        PERM_MASTERY_READ_ALL,
        PERM_CONTENT_READ,
        PERM_CONTENT_CREATE,
        PERM_CONTENT_UPDATE,
        PERM_CONTENT_PUBLISH,
        PERM_CONTENT_ARCHIVE,
        PERM_CONTENT_REVIEW,
        PERM_ADMIN_PORTAL_ACCESS,
        PERM_AUDIT_LOG_READ,
        PERM_FEATURE_FLAG_MANAGE,
        PERM_SYSTEM_SETTING_MANAGE,
        PERM_ALGORITHM_PUBLISH,
        PERM_SUBSCRIPTION_MANAGE_SELF,
        PERM_SUBSCRIPTION_MANAGE_ALL,
        PERM_INVOICE_READ_SELF,
        PERM_INVOICE_READ_ALL,
        PERM_INVOICE_REFUND,
        PERM_ORG_MANAGE,
        PERM_ORG_ANALYTICS,
    },
    ROLE_SYSTEM_ADMIN: {
        # System admin = administrator + can manage other admins
        # (same as administrator for now; could have additional permissions)
        *ROLE_PERMISSIONS.get(ROLE_ADMINISTRATOR, set()),
    },
}


@dataclass
class AuthContext:
    """Authorization context for the current request.

    Carries the user's identity, roles, and scoped resources.
    """

    user_id: UUID
    roles: list[str] = field(default_factory=list)
    subject_scopes: dict[str, list[UUID]] = field(default_factory=dict)  # role → [subject_ids]
    organization_id: UUID | None = None
    permissions: set[str] = field(default_factory=set)

    @classmethod
    def from_jwt_claims(cls, user_id: UUID, roles: list[str]) -> AuthContext:
        """Create an AuthContext from JWT claims."""
        permissions: set[str] = set()
        for role in roles:
            permissions.update(ROLE_PERMISSIONS.get(role, set()))
        return cls(user_id=user_id, roles=roles, permissions=permissions)

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def has_any_role(self, *roles: str) -> bool:
        return any(r in self.roles for r in roles)

    def is_admin(self) -> bool:
        return self.has_any_role(ROLE_ADMINISTRATOR, ROLE_SYSTEM_ADMIN)


class AuthorizationService:
    """Fine-grained authorization service.

    Usage:
        auth_ctx = AuthContext.from_jwt_claims(user_id, roles)
        auth = AuthorizationService(auth_ctx)

        # Check permission
        auth.require_permission(PERM_CONTENT_CREATE)

        # Check object ownership
        auth.require_owner_or_admin(resource_owner_id)

        # Check role
        auth.require_role(ROLE_ADMINISTRATOR)
    """

    def __init__(self, context: AuthContext) -> None:
        self._context = context

    @property
    def context(self) -> AuthContext:
        return self._context

    def can(self, permission: str) -> bool:
        """Check if the user has a permission."""
        return self._context.has_permission(permission)

    def require_permission(self, permission: str) -> None:
        """Require a permission. Raises AuthorizationDenied if not held."""
        if not self._context.has_permission(permission):
            logger.warning(
                "authorization_denied",
                user_id=str(self._context.user_id),
                permission=permission,
                roles=self._context.roles,
            )
            raise AuthorizationDenied(
                action=permission,
                resource=None,
            )

    def require_role(self, role: str) -> None:
        """Require a specific role."""
        if not self._context.has_role(role):
            raise AuthorizationDenied(
                action=f"require_role:{role}",
                resource=None,
            )

    def require_any_role(self, *roles: str) -> None:
        """Require any of the specified roles."""
        if not self._context.has_any_role(*roles):
            raise AuthorizationDenied(
                action=f"require_any_role:{','.join(roles)}",
                resource=None,
            )

    def require_owner_or_admin(self, resource_owner_id: UUID) -> None:
        """Require that the user is the resource owner OR an admin.

        This is the object-level authorization check:
        - If user_id == resource_owner_id → allowed (ownership)
        - If user is admin → allowed (admin override)
        - Otherwise → denied
        """
        if self._context.user_id == resource_owner_id:
            return  # Owner: allowed

        if self._context.is_admin():
            return  # Admin: allowed

        logger.warning(
            "authorization_denied_not_owner",
            user_id=str(self._context.user_id),
            resource_owner=str(resource_owner_id),
        )
        raise AuthorizationDenied(
            action="access_resource",
            resource=str(resource_owner_id),
        )

    def require_owner_or_permission(self, resource_owner_id: UUID, permission: str) -> None:
        """Require ownership OR a specific permission."""
        if self._context.user_id == resource_owner_id:
            return  # Owner: allowed

        if self._context.has_permission(permission):
            return  # Has permission: allowed

        raise AuthorizationDenied(
            action=permission,
            resource=str(resource_owner_id),
        )

    def is_owner(self, resource_owner_id: UUID) -> bool:
        """Check if the user is the resource owner (no raise)."""
        return self._context.user_id == resource_owner_id

    def is_admin(self) -> bool:
        """Check if the user is an admin."""
        return self._context.is_admin()


class AuthorizationDenied(Exception):
    """Raised when authorization is denied."""

    def __init__(self, action: str, resource: str | None = None) -> None:
        msg = f"Authorization denied for action: {action}"
        if resource:
            msg += f" on resource: {resource}"
        super().__init__(msg)
        self.action = action
        self.resource = resource
