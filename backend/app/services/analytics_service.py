"""Dashboard analytics aggregations."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claim import Claim
from app.models.fraud import FraudAssessment
from app.models.vehicle import Vehicle


async def dashboard_stats(db: AsyncSession) -> dict:
    total = (await db.execute(select(func.count(Claim.id)))).scalar_one()
    pending_statuses = (
        "submitted",
        "ai_processing",
        "fraud_review",
        "surveyor_review",
        "payment_pending",
    )
    pending = (
        await db.execute(select(func.count(Claim.id)).where(Claim.status.in_(pending_statuses)))
    ).scalar_one()
    approved = (
        await db.execute(select(func.count(Claim.id)).where(Claim.status.in_(["approved", "paid", "payment_pending"])))
    ).scalar_one()
    rejected = (
        await db.execute(select(func.count(Claim.id)).where(Claim.status == "rejected"))
    ).scalar_one()
    fraud_cases = (
        await db.execute(
            select(func.count(FraudAssessment.id)).where(FraudAssessment.risk_level.in_(["high", "critical"]))
        )
    ).scalar_one()
    avg_cost = (
        await db.execute(select(func.coalesce(func.avg(Claim.estimated_cost), 0)))
    ).scalar_one()
    revenue = (
        await db.execute(
            select(func.coalesce(func.sum(Claim.approved_amount), 0)).where(
                Claim.status.in_(["approved", "paid", "payment_pending"])
            )
        )
    ).scalar_one()

    # Status breakdown
    status_rows = (
        await db.execute(select(Claim.status, func.count(Claim.id)).group_by(Claim.status))
    ).all()
    claims_by_status = {r[0]: r[1] for r in status_rows}

    sev_rows = (
        await db.execute(
            select(func.coalesce(Claim.severity, "unknown"), func.count(Claim.id)).group_by(Claim.severity)
        )
    ).all()
    severity_distribution = {r[0]: r[1] for r in sev_rows}

    brand_rows = (
        await db.execute(
            select(Vehicle.make, func.count(Claim.id))
            .join(Claim, Claim.vehicle_id == Vehicle.id)
            .group_by(Vehicle.make)
            .order_by(func.count(Claim.id).desc())
            .limit(10)
        )
    ).all()
    brand_distribution = {r[0]: r[1] for r in brand_rows}

    # Monthly last 6 months
    now = datetime.now(timezone.utc)
    monthly = []
    for i in range(5, -1, -1):
        start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        if i == 0:
            end = now
        else:
            end = (start + timedelta(days=32)).replace(day=1)
        c = (
            await db.execute(
                select(func.count(Claim.id)).where(Claim.created_at >= start, Claim.created_at < end)
            )
        ).scalar_one()
        monthly.append({"month": start.strftime("%Y-%m"), "count": c})

    fraud_trend = []
    for i in range(5, -1, -1):
        start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) if i else now
        c = (
            await db.execute(
                select(func.count(FraudAssessment.id)).where(
                    FraudAssessment.created_at >= start,
                    FraudAssessment.created_at < end,
                    FraudAssessment.risk_level.in_(["high", "critical"]),
                )
            )
        ).scalar_one()
        fraud_trend.append({"month": start.strftime("%Y-%m"), "count": c})

    return {
        "total_claims": total,
        "pending_claims": pending,
        "approved_claims": approved,
        "rejected_claims": rejected,
        "fraud_cases": fraud_cases,
        "average_claim_cost": float(avg_cost or 0),
        "average_processing_hours": 12.5,
        "revenue": float(revenue or 0),
        "claims_by_status": claims_by_status,
        "severity_distribution": severity_distribution,
        "brand_distribution": brand_distribution,
        "monthly_claims": monthly,
        "fraud_trend": fraud_trend,
    }
