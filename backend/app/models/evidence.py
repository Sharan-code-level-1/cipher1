"""Evidence pipeline models: per-image evidence, consolidated damage, risk."""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.claim import Claim, ClaimImage


class EvidenceStore(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-image evidence record produced by the layered engine pipeline.

    Captures the output of the image, validation, verification, damage, and
    similarity engines for a single uploaded image so the full chain of
    evidence is auditable.
    """

    __tablename__ = "evidence_store"

    claim_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("claims.id", ondelete="CASCADE"), index=True
    )
    image_id: Mapped[Optional[str]] = mapped_column(
        GUID, ForeignKey("claim_images.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sha256: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    phash: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)
    # Perceptual / semantic embedding vector (DINOv2 stub) stored as JSON list.
    embedding: Mapped[list] = mapped_column(JSONVariant, default=list, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    validation_result: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    verification_result: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    damage_result: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    similarity_result: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)

    claim: Mapped["Claim"] = relationship(back_populates="evidence_items")


class ConsolidatedDamage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Fused, claim-level damage output merged across all images."""

    __tablename__ = "consolidated_damages"

    claim_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("claims.id", ondelete="CASCADE"), index=True
    )
    model_version: Mapped[str] = mapped_column(String(60), default="fusion-1.0")
    fusion_method: Mapped[str] = mapped_column(String(60), default="max_confidence_union")
    parts: Mapped[list] = mapped_column(JSONVariant, default=list, nullable=False)
    damages: Mapped[list] = mapped_column(JSONVariant, default=list, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="minor")
    damage_area_pct: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=0)
    image_count: Mapped[int] = mapped_column(default=0)
    explanation: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)

    claim: Mapped["Claim"] = relationship(back_populates="consolidated_damages")


class EvidenceRiskAssessment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Explainable evidence-risk score derived from metadata + risk rules.

    Supersedes the legacy fraud engine output while remaining structurally
    compatible (risk_score / risk_level / signals).
    """

    __tablename__ = "evidence_risk_assessments"

    claim_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("claims.id", ondelete="CASCADE"), index=True
    )
    risk_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)  # low|medium|high|critical
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_findings: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    rules_fired: Mapped[list] = mapped_column(JSONVariant, default=list, nullable=False)
    explanation: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), default="risk-engine-1.0")
    reviewed_by: Mapped[Optional[str]] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)
    review_decision: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    claim: Mapped["Claim"] = relationship(back_populates="risk_assessments")
    signals: Mapped[List["EvidenceRiskSignal"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class EvidenceRiskSignal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual weighted risk signal contributing to an assessment."""

    __tablename__ = "evidence_risk_signals"

    assessment_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("evidence_risk_assessments.id", ondelete="CASCADE"), index=True
    )
    signal_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)

    assessment: Mapped[EvidenceRiskAssessment] = relationship(back_populates="signals")
