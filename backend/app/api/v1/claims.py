"""Claim management endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_meta, get_current_user, require_permissions
from app.core.config import get_settings
from app.core.exceptions import ValidationAppError
from app.core.permissions import Permission
from app.db.session import get_db
from app.schemas.claim import (
    ClaimCreate,
    ClaimListOut,
    ClaimOut,
    ClaimStatusUpdate,
)
from app.services.claim_service import ClaimService

router = APIRouter()


@router.post("", response_model=ClaimOut, status_code=201)
async def create_claim(
    body: ClaimCreate,
    request: Request,
    user=Depends(require_permissions(Permission.CLAIM_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    ip, ua = client_meta(request)
    svc = ClaimService(db)
    claim = await svc.create_claim(user, body.model_dump(), ip=ip, ua=ua)
    return await svc.get_claim(claim.id, user)


@router.get("", response_model=ClaimListOut)
async def list_claims(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ClaimService(db)
    items, total = await svc.list_claims(user, page=page, page_size=page_size, status=status)
    return ClaimListOut(
        items=[ClaimOut.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{claim_id}", response_model=ClaimOut)
async def get_claim(
    claim_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ClaimService(db)
    claim = await svc.get_claim(claim_id, user)
    return ClaimOut.model_validate(claim)


@router.post("/{claim_id}/images", response_model=ClaimOut, status_code=201)
async def upload_image(
    claim_id: str,
    request: Request,
    file: UploadFile = File(...),
    angle_label: Optional[str] = Form(default=None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise ValidationAppError("File too large")
    ip, ua = client_meta(request)
    svc = ClaimService(db)
    await svc.add_image(
        claim_id,
        user,
        filename=file.filename or "upload.jpg",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        angle_label=angle_label,
        ip=ip,
        ua=ua,
    )
    return ClaimOut.model_validate(await svc.get_claim(claim_id, user))


@router.post("/{claim_id}/submit", response_model=ClaimOut)
async def submit_claim(
    claim_id: str,
    request: Request,
    user=Depends(require_permissions(Permission.CLAIM_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    ip, ua = client_meta(request)
    svc = ClaimService(db)
    claim = await svc.submit(claim_id, user, ip=ip, ua=ua)
    return ClaimOut.model_validate(claim)


@router.patch("/{claim_id}/status", response_model=ClaimOut)
async def update_status(
    claim_id: str,
    body: ClaimStatusUpdate,
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip, ua = client_meta(request)
    svc = ClaimService(db)
    claim = await svc.update_status(
        claim_id,
        user,
        status=body.status,
        note=body.note,
        approved_amount=body.approved_amount,
        rejection_reason=body.rejection_reason,
        ip=ip,
        ua=ua,
    )
    return ClaimOut.model_validate(claim)
