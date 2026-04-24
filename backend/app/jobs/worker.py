from __future__ import annotations

from arq.connections import RedisSettings

from app.jobs.tasks import run_coordinator_job


async def startup(ctx: dict) -> None:
    from app.core.config import settings  # noqa: PLC0415
    from app.core.logging import configure_logging  # noqa: PLC0415
    from app.db.session import engine  # noqa: PLC0415

    configure_logging(settings.LOG_LEVEL, settings.ENVIRONMENT)


async def shutdown(ctx: dict) -> None:
    from app.db.session import engine, redis_client  # noqa: PLC0415
    await engine.dispose()


class WorkerSettings:
    from app.core.config import settings as _settings

    redis_settings = RedisSettings.from_dsn(_settings.REDIS_URL)
    functions = [run_coordinator_job]
    max_jobs = 10
    job_timeout = 600
    keep_result = 3600
    queue_name = "atalaya:jobs"
    on_startup = startup
    on_shutdown = shutdown
