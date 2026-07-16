"""ORM models package — import all for Alembic metadata."""
from app.models.user import User, RefreshToken, EmailVerification, PasswordReset
from app.models.vehicle import Vehicle, Policy
from app.models.claim import Claim, ClaimImage, ClaimStatusHistory, DamageDetection, CostEstimate
from app.models.fraud import FraudAssessment, FraudSignal
from app.models.ai import AIProviderSettings, AIProviderTestHistory, AIReport
from app.models.evidence import (
    EvidenceStore,
    ConsolidatedDamage,
    EvidenceRiskAssessment,
    EvidenceRiskSignal,
)
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.models.system import FeatureFlag, SystemSetting

__all__ = [
    "User",
    "RefreshToken",
    "EmailVerification",
    "PasswordReset",
    "Vehicle",
    "Policy",
    "Claim",
    "ClaimImage",
    "ClaimStatusHistory",
    "DamageDetection",
    "CostEstimate",
    "FraudAssessment",
    "FraudSignal",
    "AIProviderSettings",
    "AIProviderTestHistory",
    "AIReport",
    "EvidenceStore",
    "ConsolidatedDamage",
    "EvidenceRiskAssessment",
    "EvidenceRiskSignal",
    "AuditLog",
    "Notification",
    "FeatureFlag",
    "SystemSetting",
]
