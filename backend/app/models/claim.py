"""Claim lifecycle, images, detections, and cost models."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.fraud import FraudAssessment
    from app.models.user import User
    from app.models.vehicle import Vehicle


class Claim(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "claims"

    claim_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    customer_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("users.id"), index=True, nullable=False
    )
    vehicle_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("vehicles.id"), index=True, nullable=False
    )
    policy_id: Mapped[Optional[str]] = mapped_column(
        GUID, ForeignKey("policies.id"), nullable=True
    )
    assigned_surveyor_id: Mapped[Optional[str]] = mapped_column(
        GUID, ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True, nullable=False)
    # draft, submitted, ai_processing, fraud_review, surveyor_review,
    # approved, rejected, payment_pending, paid, closed
    incident_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    incident_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    incident_lat: Mapped[Optional[float]] = mapped_column(nullable=True)
    incident_lng: Mapped[Optional[float]] = mapped_column(nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fraud_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    approved_amount: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    surveyor_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    warranty_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped["User"] = relationship(foreign_keys=[customer_id], back_populates="claims")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="claims")
    images: Mapped[List["ClaimImage"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    status_history: Mapped[List["ClaimStatusHistory"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    detections: Mapped[List["DamageDetection"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    cost_estimates: Mapped[List["CostEstimate"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    fraud_assessments: Mapped[List["FraudAssessment"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class ClaimImage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "claim_images"

    claim_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("claims.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    phash: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)
    thumbnail_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exif_json: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    angle_label: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    virus_scan_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    claim: Mapped[Claim] = relationship(back_populates="images")


class ClaimStatusHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "claim_status_history"

    claim_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("claims.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(GUID, ForeignKey("users.id"))
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    claim: Mapped[Claim] = relationship(back_populates="status_history")


class DamageDetection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "damage_detections"

    claim_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("claims.id", ondelete="CASCADE"), index=True
    )
    image_id: Mapped[Optional[str]] = mapped_column(
        GUID, ForeignKey("claim_images.id", ondelete="SET NULL"), nullable=True
    )
    model_version: Mapped[str] = mapped_column(String(40), default="yolov11-sim-1.0")
    parts: Mapped[list] = mapped_column(JSONVariant, default=list, nullable=False)
    damages: Mapped[list] = mapped_column(JSONVariant, default=list, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    damage_area_pct: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=0)
    explanation: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    heatmap_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    claim: Mapped[Claim] = relationship(back_populates="detections")


class CostEstimate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cost_estimates"

    claim_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("claims.id", ondelete="CASCADE"), index=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    parts_total: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    labour_total: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    painting_total: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    taxes_total: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    grand_total: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    repair_days: Mapped[int] = mapped_column(Integer, default=1)
    line_items: Mapped[list] = mapped_column(JSONVariant, default=list, nullable=False)
    invoice_json: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)
    explanation: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)

    claim: Mapped[Claim] = relationship(back_populates="cost_estimates")
