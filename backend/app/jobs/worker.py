from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings

from app.jobs.tasks import run_coordinator_job
from app.jobs.geoint_scheduler import run_weekly_geoint_report, schedule_weekly_geoint


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
    functions = [run_coordinator_job, run_weekly_geoint_report]
    cron_jobs = [
        # Every Monday at 06:00 UTC — weekly geopolitical intelligence report
        cron(schedule_weekly_geoint, weekday=0, hour=6, minute=0),
    ]
    max_jobs = 10
    job_timeout = 1800  # 30 min — geoint pipeline can take longer than default
    keep_result = 86400  # 24 h
    queue_name = "atalaya:jobs"
    on_startup = startup
    on_shutdown = shutdown
