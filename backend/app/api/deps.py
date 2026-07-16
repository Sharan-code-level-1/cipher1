"""FastAPI dependencies for auth, RBAC, and request context."""
from __future__ import annotations

from typing import Annotated, Callable, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.permissions import Permission, has_permission
from app.core.security import safe_decode
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> User:
    if not creds or creds.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing bearer token")
    payload = safe_decode(creds.credentials)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired access token")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token subject")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    request.state.user = user
    request.state.token_payload = payload
    return user


def require_permissions(*perms: Permission | str) -> Callable:
    async def _checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        for p in perms:
            key = p.value if isinstance(p, Permission) else p
            if not has_permission(user.role, key) and user.role != "super_admin":
                raise ForbiddenError(f"Missing permission: {key}")
        return user

    return _checker


def require_roles(*roles: str) -> Callable:
    async def _checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles and user.role != "super_admin":
            raise ForbiddenError("Role not permitted")
        return user

    return _checker


def client_meta(request: Request) -> tuple[Optional[str], Optional[str]]:
    ip = request.client.host if request.client else None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    ua = request.headers.get("User-Agent")
    return ip, ua
