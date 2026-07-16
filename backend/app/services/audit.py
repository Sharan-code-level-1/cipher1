"""Audit logging service."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def write_audit(
    db: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    message: Optional[str] = None,
    before_state: Optional[dict] = None,
    after_state: Optional[dict] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
        message=message,
        before_state=before_state,
        after_state=after_state,
        metadata_json=metadata or {},
    )
    db.add(entry)
    await db.flush()
    return entry
