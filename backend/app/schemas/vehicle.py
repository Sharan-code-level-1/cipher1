"""Vehicle and policy schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VehicleCreate(BaseModel):
    vin: str = Field(min_length=11, max_length=17)
    registration_number: str = Field(min_length=3, max_length=32)
    make: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    year: int = Field(ge=1980, le=2100)
    color: Optional[str] = Field(default=None, max_length=40)
    body_type: Optional[str] = Field(default=None, max_length=40)
    odometer_km: Optional[int] = Field(default=None, ge=0)

    @field_validator("vin")
    @classmethod
    def normalize_vin(cls, v: str) -> str:
        return v.upper().replace(" ", "")


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    vin: str
    registration_number: str
    make: str
    model: str
    year: int
    color: Optional[str] = None
    body_type: Optional[str] = None
    odometer_km: Optional[int] = None
    created_at: datetime


class PolicyCreate(BaseModel):
    vehicle_id: str
    policy_number: str = Field(min_length=3, max_length=64)
    insurer_name: str = Field(min_length=2, max_length=120)
    coverage_type: str = Field(pattern="^(comprehensive|third_party|zero_dep)$")
    start_date: date
    end_date: date
    sum_insured: float = Field(gt=0)
    deductible: float = Field(ge=0, default=0)
    warranty_notes: Optional[str] = None


class PolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vehicle_id: str
    policy_number: str
    insurer_name: str
    coverage_type: str
    start_date: date
    end_date: date
    sum_insured: float
    deductible: float
    status: str
    warranty_notes: Optional[str] = None
    created_at: datetime
