"""Global search across claims, users, vehicles."""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.claim import Claim
from app.models.user import User
from app.models.vehicle import Policy, Vehicle

router = APIRouter()


@router.get("")
async def global_search(
    q: str = Query(..., min_length=2, max_length=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, List[Dict[str, Any]]]:
    term = f"%{q.strip()}%"
    results: Dict[str, List[Dict[str, Any]]] = {"claims": [], "vehicles": [], "users": [], "policies": []}

    cq = select(Claim).where(
        or_(Claim.claim_number.ilike(term), Claim.description.ilike(term))
    ).limit(20)
    if user.role == "customer":
        cq = cq.where(Claim.customer_id == user.id)
    for c in (await db.execute(cq)).scalars().all():
        results["claims"].append(
            {"id": c.id, "claim_number": c.claim_number, "status": c.status}
        )

    vq = select(Vehicle).where(
        or_(
            Vehicle.vin.ilike(term),
            Vehicle.registration_number.ilike(term),
            Vehicle.make.ilike(term),
            Vehicle.model.ilike(term),
        )
    ).limit(20)
    if user.role == "customer":
        vq = vq.where(Vehicle.owner_id == user.id)
    for v in (await db.execute(vq)).scalars().all():
        results["vehicles"].append(
            {
                "id": v.id,
                "vin": v.vin,
                "registration_number": v.registration_number,
                "make": v.make,
                "model": v.model,
            }
        )

    if user.role in {"admin", "super_admin", "insurance_officer", "fraud_analyst"}:
        uq = select(User).where(or_(User.email.ilike(term), User.full_name.ilike(term))).limit(20)
        for u in (await db.execute(uq)).scalars().all():
            results["users"].append({"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role})

        pq = select(Policy).where(Policy.policy_number.ilike(term)).limit(20)
        for p in (await db.execute(pq)).scalars().all():
            results["policies"].append(
                {"id": p.id, "policy_number": p.policy_number, "status": p.status}
            )

    return results
