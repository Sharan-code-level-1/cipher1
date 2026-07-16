"""Authentication endpoints."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_meta, get_current_user
from app.core.config import get_settings
from app.core.permissions import permissions_for_role
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip, ua = client_meta(request)
    user = await auth_service.register_user(
        db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        phone=body.phone,
        ip=ip,
        ua=ua,
    )
    return UserOut.model_validate(user).model_copy(
        update={"permissions": list(permissions_for_role(user.role))}
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip, ua = client_meta(request)
    user, access, refresh = await auth_service.authenticate(
        db, email=body.email, password=body.password, ip=ip, ua=ua
    )
    settings = get_settings()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip, ua = client_meta(request)
    _, access, refresh_tok = await auth_service.refresh_session(
        db, refresh_token=body.refresh_token, ip=ip, ua=ua
    )
    settings = get_settings()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_tok,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accepts empty body (frontend) or optional {refresh_token}."""
    refresh_token = None
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            payload = await request.json()
            if isinstance(payload, dict):
                refresh_token = payload.get("refresh_token")
        except Exception:
            refresh_token = None

    if refresh_token:
        await auth_service.logout(db, refresh_token=refresh_token, user_id=user.id)
    else:
        await auth_service.logout_all(db, user_id=user.id)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return UserOut.model_validate(user).model_copy(
        update={"permissions": list(permissions_for_role(user.role))}
    )


@router.post("/password-reset/request", response_model=MessageResponse)
async def password_reset_request(body: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.request_password_reset(db, body.email)
    return MessageResponse(message="If the account exists, a reset link was sent")


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def password_reset_confirm(body: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    await auth_service.confirm_password_reset(db, body.token, body.new_password)
    return MessageResponse(message="Password updated")
