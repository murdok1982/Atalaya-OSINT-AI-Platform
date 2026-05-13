from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.models.user import User

logger = get_logger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class GeointReportRequest(BaseModel):
    days_back: int = Field(default=7, ge=1, le=30, description="Días a recopilar")
    categories: list[Literal["economics", "security", "defense", "intelligence"]] | None = None
    regions: list[str] | None = None
    classification: Literal["UNCLASSIFIED", "CUI", "CONFIDENTIAL", "SECRET"] = "UNCLASSIFIED"


class GeointReportStatus(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    message: str
    file_path: str | None = None
    generated_at: str | None = None


class GeointReportSummary(BaseModel):
    filename: str
    path: str
    size_kb: float
    classification: str
    created_at: str


class SourceEntry(BaseModel):
    id: str
    name: str
    url: str
    language: str
    reliability: str
    categories: list[str]
    regions: list[str]
    active: bool
    source_type: str


# ---------------------------------------------------------------------------
# In-memory job tracker (replace with Redis/ARQ for production scale)
# ---------------------------------------------------------------------------
_running_jobs: dict[str, dict] = {}


def _get_reports_dir() -> str:
    base = getattr(settings, "REPORTS_STORAGE_PATH", "./data/reports")
    return os.path.join(base, "geoint")


async def _run_pipeline(job_id: str, request: GeointReportRequest) -> None:
    from app.intelligence.geoint_weekly import WeeklyGeointPipeline  # noqa: PLC0415

    _running_jobs[job_id]["status"] = "running"
    try:
        pipeline = WeeklyGeointPipeline()
        report = await pipeline.run(
            days_back=request.days_back,
            category_filter=request.categories,
            region_filter=request.regions,
            classification=request.classification,
        )
        _running_jobs[job_id].update({
            "status": "completed",
            "file_path": report.file_path,
            "generated_at": report.generated_at.isoformat(),
            "total_sources": report.total_sources,
            "message": f"Informe generado: {report.total_sources} fuentes procesadas",
        })
        logger.info("geoint_job_completed", job_id=job_id, file=report.file_path)
    except Exception as exc:
        logger.error("geoint_job_failed", job_id=job_id, error=str(exc))
        _running_jobs[job_id].update({
            "status": "failed",
            "message": f"Error: {exc}",
        })


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/generate",
    response_model=GeointReportStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Genera informe semanal de inteligencia geopolítica",
)
async def generate_weekly_report(
    request: GeointReportRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
) -> GeointReportStatus:
    import uuid  # noqa: PLC0415

    job_id = str(uuid.uuid4())
    _running_jobs[job_id] = {
        "status": "queued",
        "message": "Informe encolado para generación",
        "file_path": None,
        "generated_at": None,
    }

    background_tasks.add_task(_run_pipeline, job_id, request)

    logger.info("geoint_job_queued", job_id=job_id, user=str(current_user.id))
    return GeointReportStatus(
        job_id=job_id,
        status="queued",
        message="Informe encolado. Consulta /geoint/status/{job_id} para seguimiento.",
    )


@router.get(
    "/status/{job_id}",
    response_model=GeointReportStatus,
    summary="Consulta estado de generación de informe",
)
async def get_report_status(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> GeointReportStatus:
    job = _running_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    return GeointReportStatus(
        job_id=job_id,
        status=job["status"],
        message=job["message"],
        file_path=job.get("file_path"),
        generated_at=job.get("generated_at"),
    )


@router.get(
    "/reports",
    response_model=list[GeointReportSummary],
    summary="Lista informes geopolíticos generados",
)
async def list_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[GeointReportSummary]:
    reports_dir = _get_reports_dir()
    if not os.path.exists(reports_dir):
        return []

    files = sorted(
        [f for f in os.listdir(reports_dir) if f.endswith(".md")],
        reverse=True,
    )[:limit]

    result: list[GeointReportSummary] = []
    for fname in files:
        fpath = os.path.join(reports_dir, fname)
        stat = os.stat(fpath)
        # Extract classification from filename: geoint_weekly_YYYYMMDD_HHMMSS_classification.md
        parts = fname.replace(".md", "").split("_")
        classification = parts[-1].upper() if len(parts) >= 4 else "UNKNOWN"

        result.append(GeointReportSummary(
            filename=fname,
            path=fpath,
            size_kb=round(stat.st_size / 1024, 1),
            classification=classification,
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
        ))

    return result


@router.get(
    "/reports/{filename}",
    summary="Obtiene contenido de un informe geopolítico",
)
async def get_report_content(
    filename: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    # Prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")

    reports_dir = _get_reports_dir()
    file_path = os.path.join(reports_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Informe no encontrado")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {"filename": filename, "content": content}


@router.get(
    "/sources",
    response_model=list[SourceEntry],
    summary="Lista fuentes OSINT aprobadas para inteligencia geopolítica",
)
async def list_sources(
    current_user: Annotated[User, Depends(get_current_user)],
    source_type: Literal["rss", "youtube", "all"] = Query(default="all"),
    category: str | None = Query(default=None),
    active_only: bool = Query(default=True),
) -> list[SourceEntry]:
    sources_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "config", "geoint_sources.json")
    )
    if not os.path.exists(sources_path):
        raise HTTPException(status_code=503, detail="Archivo de fuentes no encontrado")

    with open(sources_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries: list[SourceEntry] = []

    if source_type in ("rss", "all"):
        for group in data.get("rss_feeds", {}).values():
            for src in group:
                if active_only and not src.get("active", True):
                    continue
                if category and category not in src.get("categories", []):
                    continue
                entries.append(SourceEntry(
                    id=src["id"],
                    name=src["name"],
                    url=src["url"],
                    language=src.get("language", "en"),
                    reliability=src.get("reliability", "U"),
                    categories=src.get("categories", []),
                    regions=src.get("regions", []),
                    active=src.get("active", True),
                    source_type="rss",
                ))

    if source_type in ("youtube", "all"):
        for group in data.get("youtube_channels", {}).values():
            for ch in group:
                if active_only and not ch.get("active", True):
                    continue
                if category and category not in ch.get("categories", []):
                    continue
                entries.append(SourceEntry(
                    id=ch["id"],
                    name=ch["name"],
                    url=f"https://www.youtube.com/channel/{ch['channel_id']}",
                    language=ch.get("language", "en"),
                    reliability=ch.get("reliability", "U"),
                    categories=ch.get("categories", []),
                    regions=ch.get("regions", []),
                    active=ch.get("active", True),
                    source_type="youtube",
                ))

    return entries
