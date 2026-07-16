"""RBAC permission matrix and helpers."""
from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Set


class Role(str, Enum):
    CUSTOMER = "customer"
    SURVEYOR = "surveyor"
    INSURANCE_OFFICER = "insurance_officer"
    REPAIR_WORKSHOP = "repair_workshop"
    FRAUD_ANALYST = "fraud_analyst"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Permission(str, Enum):
    CLAIM_CREATE = "claim:create"
    CLAIM_READ_OWN = "claim:read_own"
    CLAIM_READ_ALL = "claim:read_all"
    CLAIM_UPDATE = "claim:update"
    CLAIM_APPROVE = "claim:approve"
    CLAIM_REJECT = "claim:reject"
    CLAIM_ASSIGN = "claim:assign"
    CLAIM_PAY = "claim:pay"

    VEHICLE_MANAGE = "vehicle:manage"
    POLICY_MANAGE = "policy:manage"

    FRAUD_REVIEW = "fraud:review"
    FRAUD_OVERRIDE = "fraud:override"

    USER_READ = "user:read"
    USER_MANAGE = "user:manage"
    ROLE_MANAGE = "role:manage"

    ANALYTICS_READ = "analytics:read"
    AUDIT_READ = "audit:read"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_BACKUP = "system:backup"
    AI_CONFIG = "ai:config"


ROLE_PERMISSIONS: dict[Role, FrozenSet[Permission]] = {
    Role.CUSTOMER: frozenset(
        {
            Permission.CLAIM_CREATE,
            Permission.CLAIM_READ_OWN,
            Permission.VEHICLE_MANAGE,
            Permission.POLICY_MANAGE,
        }
    ),
    Role.SURVEYOR: frozenset(
        {
            Permission.CLAIM_READ_ALL,
            Permission.CLAIM_UPDATE,
            Permission.CLAIM_APPROVE,
            Permission.CLAIM_REJECT,
            Permission.CLAIM_ASSIGN,
        }
    ),
    Role.INSURANCE_OFFICER: frozenset(
        {
            Permission.CLAIM_READ_ALL,
            Permission.CLAIM_UPDATE,
            Permission.CLAIM_APPROVE,
            Permission.CLAIM_REJECT,
            Permission.CLAIM_PAY,
            Permission.POLICY_MANAGE,
            Permission.ANALYTICS_READ,
        }
    ),
    Role.REPAIR_WORKSHOP: frozenset(
        {
            Permission.CLAIM_READ_ALL,
            Permission.CLAIM_UPDATE,
        }
    ),
    Role.FRAUD_ANALYST: frozenset(
        {
            Permission.CLAIM_READ_ALL,
            Permission.FRAUD_REVIEW,
            Permission.FRAUD_OVERRIDE,
            Permission.ANALYTICS_READ,
            Permission.AUDIT_READ,
        }
    ),
    Role.ADMIN: frozenset(
        {
            Permission.CLAIM_READ_ALL,
            Permission.CLAIM_UPDATE,
            Permission.CLAIM_APPROVE,
            Permission.CLAIM_REJECT,
            Permission.CLAIM_ASSIGN,
            Permission.CLAIM_PAY,
            Permission.VEHICLE_MANAGE,
            Permission.POLICY_MANAGE,
            Permission.FRAUD_REVIEW,
            Permission.USER_READ,
            Permission.USER_MANAGE,
            Permission.ANALYTICS_READ,
            Permission.AUDIT_READ,
            Permission.SYSTEM_CONFIG,
            Permission.AI_CONFIG,
        }
    ),
    Role.SUPER_ADMIN: frozenset(set(Permission)),
}


def permissions_for_role(role: str | Role) -> Set[str]:
    try:
        r = Role(role)
    except ValueError:
        return set()
    return {p.value for p in ROLE_PERMISSIONS.get(r, frozenset())}


def has_permission(role: str, permission: str | Permission) -> bool:
    perm = permission.value if isinstance(permission, Permission) else permission
    return perm in permissions_for_role(role)
