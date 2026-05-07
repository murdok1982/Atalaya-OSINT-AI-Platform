from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(settings.LOG_LEVEL, settings.ENVIRONMENT)
    logger.info("atalaya_starting", environment=settings.ENVIRONMENT)

    from app.db.session import engine, get_redis_pool  # noqa: PLC0415
    from app.db.init_db import create_all_tables  # noqa: PLC0415
    import os  # noqa: PLC0415

    # Ensure storage directories exist
    for path in [settings.EVIDENCE_STORAGE_PATH, settings.REPORTS_STORAGE_PATH, settings.LOGS_PATH]:
        os.makedirs(path, exist_ok=True)

    if not settings.is_production:
        await create_all_tables()
        logger.info("database_ready")

    # Verify Redis connectivity (lazy — get_redis_pool may return None on init failure)
    redis_client = None
    try:
        redis_client = await get_redis_pool()
        if redis_client is not None:
            await redis_client.ping()
            logger.info("redis_ready")
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis_unavailable", error=str(exc))

    logger.info("atalaya_ready", host=settings.API_HOST, port=settings.API_PORT)

    yield

    logger.info("atalaya_shutting_down")
    await engine.dispose()
    if redis_client is not None:
        try:
            await redis_client.aclose()
        except Exception:  # noqa: BLE001
            pass
    logger.info("atalaya_stopped")
