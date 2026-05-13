from __future__ import annotations

import os
from datetime import datetime, timezone

from app.core.logging import get_logger

logger = get_logger(__name__)


async def run_weekly_geoint_report(
    ctx: dict,
    days_back: int = 7,
    categories: list[str] | None = None,
    regions: list[str] | None = None,
    classification: str = "UNCLASSIFIED",
) -> dict:
    """
    ARQ background task: run the weekly geopolitical intelligence pipeline.
    Enqueue via: pool.enqueue_job("run_weekly_geoint_report")
    """
    from app.core.config import settings  # noqa: PLC0415
    from app.intelligence.geoint_weekly import WeeklyGeointPipeline  # noqa: PLC0415

    logger.info(
        "geoint_job_start",
        days_back=days_back,
        categories=categories,
        regions=regions,
        classification=classification,
    )

    try:
        pipeline = WeeklyGeointPipeline()
        report = await pipeline.run(
            days_back=days_back or getattr(settings, "GEOINT_DAYS_BACK", 7),
            category_filter=categories,
            region_filter=regions or getattr(settings, "GEOINT_DEFAULT_REGIONS", None),
            classification=classification or getattr(settings, "GEOINT_DEFAULT_CLASSIFICATION", "UNCLASSIFIED"),
        )

        result = {
            "success": True,
            "file_path": report.file_path,
            "total_sources": report.total_sources,
            "generated_at": report.generated_at.isoformat(),
            "model_used": report.model_used,
            "classification": report.classification,
            "period": {
                "start": report.period_start.isoformat(),
                "end": report.period_end.isoformat(),
            },
        }

        logger.info("geoint_job_completed", file=report.file_path, sources=report.total_sources)
        return result

    except Exception as exc:
        logger.error("geoint_job_failed", error=str(exc))
        return {"success": False, "error": str(exc)}


async def schedule_weekly_geoint(ctx: dict) -> dict:
    """
    Scheduled cron entry-point: called by ARQ cron scheduler every Monday at 06:00 UTC.
    Reads default parameters from settings.
    """
    from app.core.config import settings  # noqa: PLC0415

    if not getattr(settings, "GEOINT_WEEKLY_ENABLED", True):
        logger.info("geoint_weekly_disabled")
        return {"skipped": True, "reason": "GEOINT_WEEKLY_ENABLED=false"}

    return await run_weekly_geoint_report(
        ctx=ctx,
        days_back=getattr(settings, "GEOINT_DAYS_BACK", 7),
        regions=getattr(settings, "GEOINT_DEFAULT_REGIONS", None),
        classification=getattr(settings, "GEOINT_DEFAULT_CLASSIFICATION", "UNCLASSIFIED"),
    )
