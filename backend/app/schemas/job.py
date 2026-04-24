from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.job import JobStatus


class JobCreate(BaseModel):
    case_id: str | None = None
    job_type: str = "COORDINATOR"
    task_description: str | None = None
    input_params: dict[str, Any] = {}


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    job_type: str
    status: str
    arq_job_id: str | None
    created_by: str
    result_summary: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    findings_count: int
    input_params: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    job_type: str
    status: str
    created_by: str
    findings_count: int
    duration_seconds: float | None
    created_at: datetime
    completed_at: datetime | None
