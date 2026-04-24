from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DBSession, require_scope
from app.core.config import settings
from app.models.evidence import Evidence
from app.schemas.evidence import EvidenceCreate, EvidenceListItem, EvidenceResponse

router = APIRouter()


@router.get("", response_model=list[EvidenceListItem])
async def list_evidence(
    db: DBSession,
    user: Annotated[object, Depends(require_scope("read:cases"))],
    case_id: str | None = None,
    entity_id: str | None = None,
    evidence_type: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[EvidenceListItem]:
    q = select(Evidence)
    if case_id:
        q = q.where(Evidence.case_id == case_id)
    if entity_id:
        q = q.where(Evidence.entity_id == entity_id)
    if evidence_type:
        q = q.where(Evidence.evidence_type == evidence_type)
    q = q.order_by(Evidence.collected_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return [EvidenceListItem.model_validate(e) for e in result.scalars().all()]


@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    body: EvidenceCreate,
    db: DBSession,
    user: Annotated[object, Depends(require_scope("write:cases"))],
) -> EvidenceResponse:
    content_hash = ""
    if body.content_text:
        content_hash = hashlib.sha256(body.content_text.encode()).hexdigest()

    evidence = Evidence(
        **body.model_dump(),
        content_hash=content_hash,
        collected_at=datetime.now(timezone.utc),
        collected_by=str(user.id),  # type: ignore[attr-defined]
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    return EvidenceResponse.model_validate(evidence)


@router.post("/upload", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    case_id: str,
    db: DBSession,
    user: Annotated[object, Depends(require_scope("write:cases"))],
    file: UploadFile = File(...),
) -> EvidenceResponse:
    if file.size and file.size > settings.max_file_size_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    content_hash = hashlib.sha256(content).hexdigest()
    ev_id = str(uuid.uuid4())
    case_dir = os.path.join(settings.EVIDENCE_STORAGE_PATH, case_id)
    os.makedirs(case_dir, exist_ok=True)
    file_path = os.path.join(case_dir, f"{ev_id}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(content)

    evidence = Evidence(
        id=ev_id,
        case_id=case_id,
        title=file.filename or ev_id,
        evidence_type="FILE",
        content_hash=content_hash,
        content_file_path=file_path,
        file_size_bytes=len(content),
        collected_at=datetime.now(timezone.utc),
        collected_by=str(user.id),  # type: ignore[attr-defined]
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    return EvidenceResponse.model_validate(evidence)


@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: str,
    db: DBSession,
    user: Annotated[object, Depends(require_scope("read:cases"))],
) -> EvidenceResponse:
    ev = await _get_or_404(db, evidence_id)
    return EvidenceResponse.model_validate(ev)


@router.get("/{evidence_id}/content")
async def get_evidence_content(
    evidence_id: str,
    db: DBSession,
    user: Annotated[object, Depends(require_scope("read:cases"))],
) -> FileResponse:
    ev = await _get_or_404(db, evidence_id)
    if not ev.content_file_path or not os.path.exists(ev.content_file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(ev.content_file_path)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: str,
    db: DBSession,
    user: Annotated[object, Depends(require_scope("admin"))],
) -> None:
    ev = await _get_or_404(db, evidence_id)
    if ev.content_file_path and os.path.exists(ev.content_file_path):
        os.remove(ev.content_file_path)
    await db.delete(ev)
    await db.commit()


async def _get_or_404(db: AsyncSession, evidence_id: str) -> Evidence:
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    ev = result.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return ev
