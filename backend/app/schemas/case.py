from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.case import CaseClassification, CasePriority, CaseStatus


class CaseCreate(BaseModel):
    title: str
    description: str = ""
    priority: CasePriority = CasePriority.MEDIUM
    classification: CaseClassification = CaseClassification.UNCLASSIFIED
    tags: list[str] = []
    scope_notes: str = ""


class CaseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: CaseStatus | None = None
    priority: CasePriority | None = None
    classification: CaseClassification | None = None
    tags: list[str] | None = None
    scope_notes: str | None = None


class CaseStatusUpdate(BaseModel):
    status: CaseStatus


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    status: str
    priority: str
    classification: str
    tags: list[str]
    operator_id: str
    scope_notes: str
    created_at: datetime
    updated_at: datetime
    entity_count: int = 0
    evidence_count: int = 0
    job_count: int = 0


class CaseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: str
    priority: str
    classification: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    entity_count: int = 0
    evidence_count: int = 0
    job_count: int = 0
