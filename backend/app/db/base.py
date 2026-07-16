"""SQLAlchemy declarative base, portable types, and mixins."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Portable column types:
#   PostgreSQL -> native UUID / JSONB (production)
#   SQLite/others -> String(36) / JSON  (tests, lightweight dev)
GUID = PG_UUID(as_uuid=False).with_variant(String(36), "sqlite")
JSONVariant = JSONB().with_variant(JSON(), "sqlite")


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: str(uuid4()))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
