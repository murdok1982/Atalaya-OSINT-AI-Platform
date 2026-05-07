from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_GENESIS_HASH = "genesis"
_chain_lock = asyncio.Lock()


def _compute_chain_hash(
    prev_hash: str,
    index: int,
    timestamp: float,
    action: str,
    user_id: str,
    resource: str,
    details: dict[str, Any] | None,
) -> str:
    payload = {
        "previous_hash": prev_hash,
        "index": index,
        "timestamp": timestamp,
        "action": action,
        "user_id": user_id,
        "resource": resource,
        "details": details or {},
    }
    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


class AuditAction(str, Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    TOOL_CALL = "TOOL_CALL"
    AGENT_RUN = "AGENT_RUN"
    UPLOAD = "UPLOAD"
    DOWNLOAD = "DOWNLOAD"


@dataclass
class AuditContext:
    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    request_id: str = ""
    success: bool = True
    error_message: str = ""


async def _append_to_chain(ctx: AuditContext, db: Any) -> None:
    """Append a tamper-evident entry to audit_chain. Caller must hold _chain_lock."""
    from app.models.intel_records import AuditChainEntry  # noqa: PLC0415
    from sqlalchemy import select, func, desc  # noqa: PLC0415

    last_row = (
        await db.execute(select(AuditChainEntry).order_by(desc(AuditChainEntry.index)).limit(1))
    ).scalar_one_or_none()
    next_index = 0 if last_row is None else int(last_row.index) + 1
    prev_hash = _GENESIS_HASH if last_row is None else last_row.hash_value
    ts = time.time()
    resource = f"{ctx.resource_type}:{ctx.resource_id or ''}"
    details_payload = dict(ctx.details or {})
    if ctx.success is False:
        details_payload["__success"] = False
        if ctx.error_message:
            details_payload["__error"] = ctx.error_message

    chain_hash = _compute_chain_hash(
        prev_hash, next_index, ts, ctx.action.value, ctx.user_id, resource, details_payload,
    )
    db.add(AuditChainEntry(
        id=str(uuid.uuid4()),
        index=next_index,
        timestamp=ts,
        action=ctx.action.value,
        user_id=ctx.user_id,
        resource=resource,
        details=details_payload,
        previous_hash=prev_hash,
        hash_value=chain_hash,
    ))


async def log_audit(ctx: AuditContext, db: Any = None) -> None:
    """Write audit entry to DB (if db provided) and always to structured log.

    Also appends a tamper-evident hash-chained record to ``audit_chain`` when DB
    is available and ``settings.AUDIT_HASH_CHAIN`` is enabled.
    """
    entry = {
        "audit": True,
        "user_id": ctx.user_id,
        "action": ctx.action.value,
        "resource_type": ctx.resource_type,
        "resource_id": ctx.resource_id,
        "ip_address": ctx.ip_address,
        "request_id": ctx.request_id,
        "success": ctx.success,
        "details": ctx.details,
    }
    if ctx.error_message:
        entry["error"] = ctx.error_message

    logger.info("audit_event", **entry)

    if db is None:
        return

    try:
        from app.models.audit_log import AuditLog  # noqa: PLC0415
        from sqlalchemy import insert  # noqa: PLC0415
        from app.core.config import settings  # noqa: PLC0415

        await db.execute(
            insert(AuditLog).values(
                id=str(uuid.uuid4()),
                user_id=ctx.user_id or "",
                action=ctx.action.value,
                resource_type=ctx.resource_type,
                resource_id=ctx.resource_id or "",
                details=ctx.details or {},
                ip_address=ctx.ip_address,
                request_id=ctx.request_id,
                success=ctx.success,
                error_message=ctx.error_message,
            )
        )

        if settings.AUDIT_HASH_CHAIN:
            async with _chain_lock:
                await _append_to_chain(ctx, db)

        await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.error("audit_db_write_failed", error=str(exc))
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass


async def verify_audit_chain(db: Any) -> dict[str, Any]:
    """Re-walks the audit_chain table and recomputes every hash.

    Returns a dict ``{ok: bool, total: int, broken_at: int|None, last_hash: str}``.
    """
    from app.models.intel_records import AuditChainEntry  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415

    rows = (
        await db.execute(select(AuditChainEntry).order_by(AuditChainEntry.index.asc()))
    ).scalars().all()

    expected_prev = _GENESIS_HASH
    last_hash = _GENESIS_HASH
    for i, row in enumerate(rows):
        if int(row.index) != i:
            return {"ok": False, "total": len(rows), "broken_at": i, "reason": "index_gap",
                    "last_hash": last_hash}
        if row.previous_hash != expected_prev:
            return {"ok": False, "total": len(rows), "broken_at": i, "reason": "previous_hash",
                    "last_hash": last_hash}
        recomputed = _compute_chain_hash(
            expected_prev, int(row.index), float(row.timestamp), row.action,
            row.user_id, row.resource, row.details,
        )
        if recomputed != row.hash_value:
            return {"ok": False, "total": len(rows), "broken_at": i, "reason": "hash_mismatch",
                    "last_hash": last_hash}
        expected_prev = row.hash_value
        last_hash = row.hash_value

    return {"ok": True, "total": len(rows), "broken_at": None, "last_hash": last_hash}
