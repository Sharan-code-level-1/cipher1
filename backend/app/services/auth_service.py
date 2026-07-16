"""Authentication and session management."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError, ValidationAppError
from app.core.permissions import permissions_for_role
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import EmailVerification, PasswordReset, RefreshToken, User
from app.services.audit import write_audit


LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    phone: Optional[str] = None,
    role: str = "customer",
    ip: Optional[str] = None,
    ua: Optional[str] = None,
) -> User:
    existing = await db.execute(select(User).where(User.email == email.lower()))
    if existing.scalar_one_or_none():
        raise ConflictError("Email already registered")
    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        phone=phone,
        role=role,
        is_active=True,
        is_verified=False,
        preferences={},
    )
    db.add(user)
    await db.flush()

    token = generate_secure_token()
    db.add(
        EmailVerification(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
    )
    await write_audit(
        db,
        action="user.register",
        resource_type="user",
        resource_id=user.id,
        actor_id=user.id,
        actor_email=user.email,
        ip_address=ip,
        user_agent=ua,
        message="User registered",
    )
    # In production, email the token; return via notification service
    user._verification_token = token  # type: ignore[attr-defined]
    return user


async def authenticate(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    ip: Optional[str] = None,
    ua: Optional[str] = None,
) -> Tuple[User, str, str]:
    settings = get_settings()
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("Invalid credentials")

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        raise ForbiddenError("Account temporarily locked due to failed logins")

    if not user.is_active:
        raise ForbiddenError("Account is disabled")

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= LOCKOUT_THRESHOLD:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
        await write_audit(
            db,
            action="auth.login_failed",
            resource_type="user",
            resource_id=user.id,
            actor_email=email,
            ip_address=ip,
            user_agent=ua,
            status="failure",
            message="Invalid password",
        )
        raise UnauthorizedError("Invalid credentials")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now

    perms = list(permissions_for_role(user.role))
    access = create_access_token(user.id, role=user.role, permissions=perms)
    refresh, jti, family = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            jti_hash=hash_token(jti),
            family_id=family,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
            user_agent=ua,
            ip_address=ip,
        )
    )
    await write_audit(
        db,
        action="auth.login",
        resource_type="user",
        resource_id=user.id,
        actor_id=user.id,
        actor_email=user.email,
        ip_address=ip,
        user_agent=ua,
        message="Login success",
    )
    return user, access, refresh


async def refresh_session(
    db: AsyncSession,
    *,
    refresh_token: str,
    ip: Optional[str] = None,
    ua: Optional[str] = None,
) -> Tuple[User, str, str]:
    settings = get_settings()
    try:
        payload = decode_token(refresh_token)
    except Exception as exc:
        raise UnauthorizedError("Invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type")

    jti = payload.get("jti")
    family = payload.get("family")
    sub = payload.get("sub")
    if not jti or not family or not sub:
        raise UnauthorizedError("Malformed refresh token")

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.jti_hash == hash_token(jti))
    )
    stored = result.scalar_one_or_none()
    if not stored or stored.revoked:
        # Possible reuse — revoke entire family
        await db.execute(
            update(RefreshToken).where(RefreshToken.family_id == family).values(revoked=True)
        )
        raise UnauthorizedError("Refresh token revoked or reused")

    if stored.expires_at < datetime.now(timezone.utc):
        stored.revoked = True
        raise UnauthorizedError("Refresh token expired")

    user = await db.get(User, sub)
    if not user or not user.is_active:
        raise UnauthorizedError("User inactive")

    # Rotate
    stored.revoked = True
    new_refresh, new_jti, _ = create_refresh_token(user.id, family_id=family)
    stored.replaced_by = new_jti
    db.add(
        RefreshToken(
            user_id=user.id,
            jti_hash=hash_token(new_jti),
            family_id=family,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
            user_agent=ua,
            ip_address=ip,
        )
    )
    perms = list(permissions_for_role(user.role))
    access = create_access_token(user.id, role=user.role, permissions=perms)
    await write_audit(
        db,
        action="auth.refresh",
        resource_type="user",
        resource_id=user.id,
        actor_id=user.id,
        actor_email=user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return user, access, new_refresh


async def logout(db: AsyncSession, *, refresh_token: str, user_id: str) -> None:
    try:
        payload = decode_token(refresh_token)
        jti = payload.get("jti")
        if jti:
            result = await db.execute(
                select(RefreshToken).where(
                    RefreshToken.jti_hash == hash_token(jti), RefreshToken.user_id == user_id
                )
            )
            stored = result.scalar_one_or_none()
            if stored:
                stored.revoked = True
    except Exception:
        pass



async def logout_all(db: AsyncSession, *, user_id: str) -> None:
    """Revoke all refresh tokens for a user (frontend bodyless logout)."""
    await db.execute(
        update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True)
    )



async def request_password_reset(db: AsyncSession, email: str) -> Optional[str]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if not user:
        return None  # do not leak existence
    token = generate_secure_token()
    db.add(
        PasswordReset(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    return token


async def confirm_password_reset(db: AsyncSession, token: str, new_password: str) -> None:
    result = await db.execute(
        select(PasswordReset).where(
            PasswordReset.token_hash == hash_token(token), PasswordReset.used.is_(False)
        )
    )
    row = result.scalar_one_or_none()
    if not row or row.expires_at < datetime.now(timezone.utc):
        raise ValidationAppError("Invalid or expired reset token")
    user = await db.get(User, row.user_id)
    if not user:
        raise ValidationAppError("Invalid reset token")
    user.password_hash = hash_password(new_password)
    row.used = True
    # Revoke all refresh tokens
    await db.execute(
        update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True)
    )
