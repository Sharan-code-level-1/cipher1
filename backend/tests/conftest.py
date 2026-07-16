"""Pytest fixtures using SQLite for unit isolation where possible."""
import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("FILE_STORAGE_PATH", "/tmp/autoclaim-test-uploads")

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app import models  # noqa: F401 — register full metadata
from app.main import app
from app.models.user import User


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    Session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    Session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with Session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def customer_user(db_session):
    u = User(
        email="testcustomer@example.com",
        password_hash=hash_password("Customer@12345!"),
        full_name="Test Customer",
        role="customer",
        is_active=True,
        is_verified=True,
        preferences={},
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u
