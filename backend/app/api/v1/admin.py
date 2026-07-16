"""Admin, analytics, user management."""
from typing import List

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_meta, require_permissions, require_roles
from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import Permission, permissions_for_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.admin import (
    AuditLogOut,
    DashboardStats,
    UserCreateAdmin,
    UserUpdateAdmin,
)
from app.schemas.auth import UserOut
from app.services.analytics_service import dashboard_stats
from app.services.audit import write_audit

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(
    user=Depends(require_permissions(Permission.ANALYTICS_READ)),
    db: AsyncSession = Depends(get_db),
):
    return DashboardStats(**(await dashboard_stats(db)))


@router.get("/users", response_model=List[UserOut])
async def list_users(
    user=Depends(require_permissions(Permission.USER_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(200))
    users = result.scalars().all()
    return [
        UserOut.model_validate(u).model_copy(update={"permissions": list(permissions_for_role(u.role))})
        for u in users
    ]


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreateAdmin,
    request: Request,
    actor=Depends(require_permissions(Permission.USER_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise ConflictError("Email exists")
    if body.role == "super_admin" and actor.role != "super_admin":
        raise ConflictError("Only super admin can create super admins")
    u = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        phone=body.phone,
        role=body.role,
        is_active=True,
        is_verified=True,
        preferences={},
    )
    db.add(u)
    await db.flush()
    ip, ua = client_meta(request)
    await write_audit(
        db,
        action="user.admin_create",
        resource_type="user",
        resource_id=u.id,
        actor_id=actor.id,
        actor_email=actor.email,
        ip_address=ip,
        user_agent=ua,
    )
    return UserOut.model_validate(u).model_copy(
        update={"permissions": list(permissions_for_role(u.role))}
    )


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UserUpdateAdmin,
    request: Request,
    actor=Depends(require_permissions(Permission.USER_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    u = await db.get(User, user_id)
    if not u:
        raise NotFoundError("User not found")
    data = body.model_dump(exclude_unset=True)
    if data.get("role") == "super_admin" and actor.role != "super_admin":
        raise ConflictError("Only super admin can assign super admin")
    for k, v in data.items():
        setattr(u, k, v)
    ip, ua = client_meta(request)
    await write_audit(
        db,
        action="user.admin_update",
        resource_type="user",
        resource_id=u.id,
        actor_id=actor.id,
        actor_email=actor.email,
        ip_address=ip,
        user_agent=ua,
        after_state=data,
    )
    return UserOut.model_validate(u).model_copy(
        update={"permissions": list(permissions_for_role(u.role))}
    )


@router.get("/audit-logs", response_model=List[AuditLogOut])
async def audit_logs(
    limit: int = Query(50, ge=1, le=200),
    user=Depends(require_permissions(Permission.AUDIT_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    return [AuditLogOut.model_validate(a) for a in result.scalars().all()]


@router.get("/permissions")
async def permission_matrix(user=Depends(require_roles("admin", "super_admin"))):
    from app.core.permissions import ROLE_PERMISSIONS

    return {
        role.value: sorted(p.value for p in perms) for role, perms in ROLE_PERMISSIONS.items()
    }
