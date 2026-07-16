"""AutoClaim AI FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import select

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import get_logger, setup_logging
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import AsyncSessionLocal, async_engine
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.models import User  # noqa: F401  — register full metadata via models package
from app import models  # noqa: F401

settings = get_settings()
setup_logging(settings.debug)
logger = get_logger("main")

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


async def seed_dev_users() -> None:
    if settings.is_production:
        return
    seeds = [
        ("admin@autoclaim.ai", "Admin@12345!", "Super Admin", "super_admin"),
        ("surveyor@autoclaim.ai", "Surveyor@12345!", "Lead Surveyor", "surveyor"),
        ("customer@autoclaim.ai", "Customer@12345!", "Demo Customer", "customer"),
        ("fraud@autoclaim.ai", "Fraud@12345!xx", "Fraud Analyst", "fraud_analyst"),
        ("officer@autoclaim.ai", "Officer@12345!", "Insurance Officer", "insurance_officer"),
        ("workshop@autoclaim.ai", "Workshop@1234!", "Repair Workshop", "repair_workshop"),
    ]
    async with AsyncSessionLocal() as db:
        for email, password, name, role in seeds:
            existing = await db.execute(select(User).where(User.email == email))
            if existing.scalar_one_or_none():
                continue
            db.add(
                User(
                    email=email,
                    password_hash=hash_password(password),
                    full_name=name,
                    role=role,
                    is_active=True,
                    is_verified=True,
                    preferences={},
                )
            )
        await db.commit()
        logger.info("seed_users_ready")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.file_storage_path).mkdir(parents=True, exist_ok=True)
    # Always ensure ORM tables exist for the current metadata (safe if SQL already applied).
    # Production Docker also runs Alembic on start; create_all is a no-op for existing tables.
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if not settings.is_production:
        await seed_dev_users()
    logger.info("app_started", version=__version__, env=settings.app_env)
    yield
    await async_engine.dispose()
    logger.info("app_stopped")


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Enterprise Vehicle Damage Assessment & Fraud Detection Platform",
    default_response_class=ORJSONResponse,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "details": exc.errors(),
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    logger.exception("unhandled_error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "health": "/api/v1/health",
    }


@app.get("/health")
async def health_alias():
    """Root health alias used by Docker HEALTHCHECK and load balancers."""
    return {"status": "ok", "version": __version__}
