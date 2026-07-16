"""Fraud assessment models."""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.claim import Claim


class FraudAssessment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "fraud_assessments"

    claim_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("claims.id", ondelete="CASCADE"), index=True
    )
    risk_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), default="fraud-engine-1.0")
    reviewed_by: Mapped[Optional[str]] = mapped_column(GUID, ForeignKey("users.id"))
    review_decision: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    claim: Mapped["Claim"] = relationship(back_populates="fraud_assessments")
    signals: Mapped[List["FraudSignal"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class FraudSignal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "fraud_signals"

    assessment_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("fraud_assessments.id", ondelete="CASCADE"), index=True
    )
    signal_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)

    assessment: Mapped[FraudAssessment] = relationship(back_populates="signals")
