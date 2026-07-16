"""Notification endpoints."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter()


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    channel: str
    title: str
    body: str
    is_read: bool
    link: str | None
    created_at: datetime


@router.get("", response_model=List[NotificationOut])
async def list_notifications(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    return [NotificationOut.model_validate(n) for n in result.scalars().all()]


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user.id)
        .values(is_read=True)
    )
    return {"message": "ok"}
