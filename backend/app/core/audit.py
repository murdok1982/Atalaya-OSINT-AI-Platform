from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


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


async def log_audit(ctx: AuditContext, db: Any = None) -> None:
    """Write audit entry to DB (if db provided) and always to structured log."""
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

    if db is not None:
        try:
            from app.models.audit_log import AuditLog  # noqa: PLC0415
            from sqlalchemy import insert  # noqa: PLC0415

            await db.execute(
                insert(AuditLog).values(
                    id=str(uuid.uuid4()),
                    user_id=ctx.user_id,
                    action=ctx.action.value,
                    resource_type=ctx.resource_type,
                    resource_id=ctx.resource_id or "",
                    details=ctx.details,
                    ip_address=ctx.ip_address,
                    request_id=ctx.request_id,
                    success=ctx.success,
                    error_message=ctx.error_message,
                )
            )
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.error("audit_db_write_failed", error=str(exc))
