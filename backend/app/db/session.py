from __future__ import annotations

from typing import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=not settings.is_production,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

redis_client: aioredis.Redis | None = None


async def get_redis_pool() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_kwargs = {
            "url": settings.REDIS_URL,
            "encoding": "utf-8",
            "decode_responses": True,
            "max_connections": settings.REDIS_MAX_CONNECTIONS,
        }
        if settings.REDIS_PASSWORD:
            redis_kwargs["password"] = settings.REDIS_PASSWORD
        redis_client = aioredis.from_url(**redis_kwargs)
    return redis_client


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis() -> aioredis.Redis:
    return await get_redis_pool()


async def check_database_connection() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            return True
    except Exception as exc:
        logger.error("db_health_check_failed", error=str(exc))
        return False


async def check_redis_connection() -> bool:
    try:
        r = await get_redis_pool()
        await r.ping()
        return True
    except Exception as exc:
        logger.error("redis_health_check_failed", error=str(exc))
        return False


async def close_connections() -> None:
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
    await engine.dispose()
