"""Vehicle and policy endpoints."""
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_meta, get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models.vehicle import Policy, Vehicle
from app.schemas.vehicle import PolicyCreate, PolicyOut, VehicleCreate, VehicleOut
from app.services.audit import write_audit

router = APIRouter()


@router.post("", response_model=VehicleOut, status_code=201)
async def create_vehicle(
    body: VehicleCreate,
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    v = Vehicle(owner_id=user.id, **body.model_dump())
    db.add(v)
    await db.flush()
    ip, ua = client_meta(request)
    await write_audit(
        db,
        action="vehicle.create",
        resource_type="vehicle",
        resource_id=v.id,
        actor_id=user.id,
        actor_email=user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return VehicleOut.model_validate(v)


@router.get("", response_model=List[VehicleOut])
async def list_vehicles(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Vehicle)
    if user.role == "customer":
        q = q.where(Vehicle.owner_id == user.id)
    result = await db.execute(q.order_by(Vehicle.created_at.desc()))
    return [VehicleOut.model_validate(v) for v in result.scalars().all()]


@router.post("/policies", response_model=PolicyOut, status_code=201)
async def create_policy(
    body: PolicyCreate,
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    v = await db.get(Vehicle, body.vehicle_id)
    if not v:
        raise NotFoundError("Vehicle not found")
    if user.role == "customer" and v.owner_id != user.id:
        raise ForbiddenError("Not your vehicle")
    p = Policy(**body.model_dump(), status="active")
    db.add(p)
    await db.flush()
    return PolicyOut.model_validate(p)


@router.get("/{vehicle_id}/policies", response_model=List[PolicyOut])
async def list_policies(
    vehicle_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    v = await db.get(Vehicle, vehicle_id)
    if not v:
        raise NotFoundError("Vehicle not found")
    if user.role == "customer" and v.owner_id != user.id:
        raise ForbiddenError("Not your vehicle")
    result = await db.execute(select(Policy).where(Policy.vehicle_id == vehicle_id))
    return [PolicyOut.model_validate(p) for p in result.scalars().all()]


@router.get("/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle(
    vehicle_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    v = await db.get(Vehicle, vehicle_id)
    if not v:
        raise NotFoundError("Vehicle not found")
    if user.role == "customer" and v.owner_id != user.id:
        raise ForbiddenError("Not your vehicle")
    return VehicleOut.model_validate(v)
