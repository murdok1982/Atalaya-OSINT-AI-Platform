from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.api.deps import DBSession, require_scope
from app.models.report import Report
from app.schemas.report import ReportGenerateRequest, ReportListItem, ReportResponse

router = APIRouter()


@router.get("", response_model=list[ReportListItem])
async def list_reports(
    db: DBSession,
    user: Annotated[object, Depends(require_scope("read:reports"))],
    case_id: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[ReportListItem]:
    q = select(Report)
    if case_id:
        q = q.where(Report.case_id == case_id)
    q = q.order_by(Report.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return [ReportListItem.model_validate(r) for r in result.scalars().all()]


@router.post("/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_report(
    body: ReportGenerateRequest,
    db: DBSession,
    user: Annotated[object, Depends(require_scope("write:reports"))],
) -> dict:
    from app.models.job import Job, JobStatus, JobType  # noqa: PLC0415
    import uuid  # noqa: PLC0415

    job = Job(
        id=str(uuid.uuid4()),
        case_id=body.case_id,
        job_type=JobType.REPORT_GENERATION,
        status=JobStatus.PENDING,
        created_by=str(user.id),  # type: ignore[attr-defined]
        input_params={
            "report_type": body.report_type,
            "entity_ids": body.entity_ids,
            "format": body.format,
        },
    )
    db.add(job)
    await db.commit()
    return {"job_id": job.id, "message": "Report generation queued"}


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: DBSession,
    user: Annotated[object, Depends(require_scope("read:reports"))],
) -> ReportResponse:
    report = await _get_or_404(db, report_id)
    return ReportResponse.model_validate(report)


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    db: DBSession,
    user: Annotated[object, Depends(require_scope("read:reports"))],
) -> FileResponse:
    report = await _get_or_404(db, report_id)
    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found")
    return FileResponse(report.file_path)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    db: DBSession,
    user: Annotated[object, Depends(require_scope("write:reports"))],
) -> None:
    report = await _get_or_404(db, report_id)
    if report.file_path and os.path.exists(report.file_path):
        os.remove(report.file_path)
    await db.delete(report)
    await db.commit()


async def _get_or_404(db: AsyncSession, report_id: str) -> Report:
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report
