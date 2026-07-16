"""Feature flags and system settings."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin


class FeatureFlag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)


class SystemSetting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
