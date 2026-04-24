from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.evidence import EvidenceType


class EvidenceCreate(BaseModel):
    case_id: str
    entity_id: str | None = None
    title: str
    description: str = ""
    evidence_type: EvidenceType
    source_url: str = ""
    content_text: str | None = None
    raw_data: dict[str, Any] = {}
    confidence_score: float = 0.7
    tags: list[str] = []
    is_sensitive: bool = False


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    entity_id: str | None
    title: str
    description: str
    evidence_type: str
    source_url: str
    content_hash: str
    content_text: str | None
    file_size_bytes: int
    collected_at: datetime
    collected_by: str
    confidence_score: float
    tags: list[str]
    is_sensitive: bool
    created_at: datetime


class EvidenceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    entity_id: str | None
    title: str
    evidence_type: str
    source_url: str
    content_hash: str
    collected_at: datetime
    confidence_score: float
    is_sensitive: bool
