"""AI provider (BYOK VLM) configuration, test history, and generated reports."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.claim import Claim


class AIProviderSettings(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """System-wide BYOK vision-LLM provider configuration (admin managed).

    The API key is stored encrypted at rest (AES-256-GCM via app.core.security)
    and is NEVER returned to the frontend.
    """

    __tablename__ = "ai_provider_settings"

    # openai | anthropic | google | custom (OpenAI-compatible base_url)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # AES-GCM ciphertext, base64-url encoded. Nullable so a row can exist before a key is set.
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    # temperature, max_tokens, timeout_seconds, extra headers, etc.
    config: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_test_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    test_history: Mapped[List["AIProviderTestHistory"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class AIProviderTestHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Record of each connectivity/inference test run against a provider."""

    __tablename__ = "ai_provider_test_history"

    provider_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("ai_provider_settings.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success | failure
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_summary: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    response_summary: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    tested_by: Mapped[Optional[str]] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)

    provider: Mapped[AIProviderSettings] = relationship(back_populates="test_history")


class AIReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A vision-LLM generated narrative + structured report for a claim."""

    __tablename__ = "ai_reports"

    claim_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("claims.id", ondelete="CASCADE"), index=True
    )
    provider_id: Mapped[Optional[str]] = mapped_column(
        GUID, ForeignKey("ai_provider_settings.id", ondelete="SET NULL"), nullable=True
    )
    provider_name: Mapped[str] = mapped_column(String(120), default="unconfigured")
    model: Mapped[str] = mapped_column(String(120), default="none")
    status: Mapped[str] = mapped_column(String(20), default="skipped", nullable=False)
    # generated | skipped | error
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_json: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    claim: Mapped["Claim"] = relationship(back_populates="ai_reports")
