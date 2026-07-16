"""Claim-related schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ClaimCreate(BaseModel):
    vehicle_id: str
    policy_id: Optional[str] = None
    incident_date: Optional[datetime] = None
    incident_location: Optional[str] = Field(default=None, max_length=255)
    incident_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    incident_lng: Optional[float] = Field(default=None, ge=-180, le=180)
    description: Optional[str] = Field(default=None, max_length=5000)


class ClaimUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=5000)
    incident_location: Optional[str] = Field(default=None, max_length=255)
    incident_lat: Optional[float] = None
    incident_lng: Optional[float] = None
    surveyor_notes: Optional[str] = Field(default=None, max_length=5000)


class ClaimStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = Field(default=None, max_length=2000)
    approved_amount: Optional[float] = Field(default=None, ge=0)
    rejection_reason: Optional[str] = Field(default=None, max_length=2000)


class ClaimImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    width: Optional[int] = None
    height: Optional[int] = None
    angle_label: Optional[str] = None
    virus_scan_status: str
    created_at: datetime


class DamageDetectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_version: str
    parts: list
    damages: list
    severity: str
    damage_area_pct: float
    confidence: float
    explanation: dict
    created_at: datetime


class CostEstimateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    currency: str
    parts_total: float
    labour_total: float
    painting_total: float
    taxes_total: float
    grand_total: float
    repair_days: int
    line_items: list
    invoice_json: dict
    explanation: dict
    created_at: datetime


class FraudSignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    signal_type: str
    severity: str
    weight: float
    message: str
    evidence: dict


class FraudAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    risk_score: float
    risk_level: str
    summary: str
    explanation: dict
    model_version: str
    signals: List[FraudSignalOut] = []
    created_at: datetime


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claim_number: str
    customer_id: str
    vehicle_id: str
    policy_id: Optional[str] = None
    assigned_surveyor_id: Optional[str] = None
    status: str
    incident_date: Optional[datetime] = None
    incident_location: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    fraud_score: Optional[float] = None
    estimated_cost: Optional[float] = None
    approved_amount: Optional[float] = None
    surveyor_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    warranty_valid: Optional[bool] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    images: List[ClaimImageOut] = []
    detections: List[DamageDetectionOut] = []
    cost_estimates: List[CostEstimateOut] = []
    fraud_assessments: List[FraudAssessmentOut] = []


class ClaimListOut(BaseModel):
    items: List[ClaimOut]
    total: int
    page: int
    page_size: int
