"""Admin and analytics schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreateAdmin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str
    role: str
    phone: Optional[str] = None


class UserUpdateAdmin(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    phone: Optional[str] = None


class DashboardStats(BaseModel):
    total_claims: int
    pending_claims: int
    approved_claims: int
    rejected_claims: int
    fraud_cases: int
    average_claim_cost: float
    average_processing_hours: float
    revenue: float
    claims_by_status: Dict[str, int]
    severity_distribution: Dict[str, int]
    brand_distribution: Dict[str, int]
    monthly_claims: List[Dict[str, Any]]
    fraud_trend: List[Dict[str, Any]]


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_id: Optional[str]
    actor_email: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    ip_address: Optional[str]
    status: str
    message: Optional[str]
    created_at: datetime


class HealthStatus(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    storage: str
    uptime_seconds: float
