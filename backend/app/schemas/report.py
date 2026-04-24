from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.report import ReportFormat, ReportType


class ReportGenerateRequest(BaseModel):
    case_id: str
    report_type: ReportType = ReportType.EXECUTIVE_SUMMARY
    entity_ids: list[str] = []
    format: ReportFormat = ReportFormat.MARKDOWN


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    job_id: str | None
    title: str
    summary: str
    report_type: str
    format: str
    content: str | None
    generated_by: str
    word_count: int
    entity_ids: list[str]
    created_at: datetime


class ReportListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    title: str
    report_type: str
    format: str
    generated_by: str
    word_count: int
    created_at: datetime
