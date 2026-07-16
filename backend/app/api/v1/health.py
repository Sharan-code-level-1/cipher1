"""Health and readiness endpoints."""
import time
from pathlib import Path

from fastapi import APIRouter, Depends
from redis import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.admin import HealthStatus

router = APIRouter()
_STARTED = time.time()


@router.get("/health", response_model=HealthStatus)
async def health(db: AsyncSession = Depends(get_db)) -> HealthStatus:
    settings = get_settings()
    db_status = "ok"
    redis_status = "ok"
    storage_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    try:
        r = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        r.ping()
        r.close()
    except Exception:
        redis_status = "degraded"
    try:
        p = Path(settings.file_storage_path)
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".health"
        test.write_text("ok")
        test.unlink(missing_ok=True)
    except Exception:
        storage_status = "error"

    overall = "ok" if db_status == "ok" and storage_status == "ok" else "degraded"
    return HealthStatus(
        status=overall,
        version=__version__,
        database=db_status,
        redis=redis_status,
        storage=storage_status,
        uptime_seconds=round(time.time() - _STARTED, 2),
    )
