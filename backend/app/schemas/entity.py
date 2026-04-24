from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.entity import EntityType


class EntityCreate(BaseModel):
    case_id: str
    entity_type: EntityType
    value: str
    display_name: str = ""
    attributes: dict[str, Any] = {}
    confidence_score: float = 0.5
    is_target: bool = False
    tags: list[str] = []
    notes: str = ""


class EntityUpdate(BaseModel):
    display_name: str | None = None
    attributes: dict[str, Any] | None = None
    confidence_score: float | None = None
    is_target: bool | None = None
    tags: list[str] | None = None
    notes: str | None = None


class EntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    entity_type: str
    value: str
    display_name: str
    attributes: dict[str, Any]
    confidence_score: float
    is_target: bool
    tags: list[str]
    notes: str
    merged_into_id: str | None
    created_at: datetime
    updated_at: datetime


class EntityMergeRequest(BaseModel):
    target_entity_id: str
    reason: str = ""


class MergeProposal(BaseModel):
    source_id: str
    target_id: str
    confidence: float
    reasoning: str
    matching_attributes: list[str]
