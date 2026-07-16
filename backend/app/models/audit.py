"""Immutable audit trail."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, GUID, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    actor_id: Mapped[Optional[str]] = mapped_column(GUID, index=True, nullable=True)
    actor_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    before_state: Mapped[Optional[dict]] = mapped_column(JSONVariant, nullable=True)
    after_state: Mapped[Optional[dict]] = mapped_column(JSONVariant, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
