from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import Base, get_db, get_redis
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://localhost:5432/atalaya_test"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    mock_redis = AsyncMock()

    async def override_get_db():
        yield db_session

    async def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_user_data() -> dict:
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestP@ssw0rd123!",
        "full_name": "Test User",
    }


@pytest.fixture
def mock_admin_data() -> dict:
    return {
        "username": "admin",
        "email": "admin@atalaya.local",
        "password": "AdminP@ssw0rd123!",
        "full_name": "Admin User",
        "scopes": ["admin", "read:cases", "write:cases", "execute:jobs"],
    }
