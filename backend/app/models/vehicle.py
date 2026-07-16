"""Vehicle and insurance policy models."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.claim import Claim
    from app.models.user import User


class Vehicle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vehicles"

    owner_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    vin: Mapped[str] = mapped_column(String(17), index=True, nullable=False)
    registration_number: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    make: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    body_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    odometer_km: Mapped[Optional[int]] = mapped_column(nullable=True)

    owner: Mapped["User"] = relationship(back_populates="vehicles")
    policies: Mapped[List["Policy"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")
    claims: Mapped[List["Claim"]] = relationship(back_populates="vehicle")


class Policy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "policies"

    vehicle_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )
    policy_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    insurer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    coverage_type: Mapped[str] = mapped_column(String(40), nullable=False)  # comprehensive, third_party
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    sum_insured: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    deductible: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    warranty_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    vehicle: Mapped[Vehicle] = relationship(back_populates="policies")
