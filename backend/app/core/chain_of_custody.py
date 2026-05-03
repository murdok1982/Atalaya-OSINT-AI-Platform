from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CustodyEntry:
    timestamp: float
    actor: str
    action: str
    purpose: str = ""
    signature: str = ""


@dataclass
class ChainOfCustody:
    evidence_id: str
    evidence_hash: str
    collected_at: float
    collected_by: str
    custody_chain: list[CustodyEntry] = field(default_factory=list)
    integrity_verified: bool = True
    last_verification: float = 0.0

    def add_custody(self, actor: str, action: str, purpose: str = "") -> None:
        entry = CustodyEntry(
            timestamp=time.time(),
            actor=actor,
            action=action,
            purpose=purpose,
        )
        custody_data = f"{entry.timestamp}:{entry.actor}:{entry.action}:{entry.purpose}"
        entry.signature = hashlib.sha256(custody_data.encode()).hexdigest()[:32]
        self.custody_chain.append(entry)
        logger.info("custody_entry_added", evidence_id=self.evidence_id, actor=actor, action=action)

    def verify_integrity(self, current_hash: str) -> bool:
        self.integrity_verified = current_hash == self.evidence_hash
        self.last_verification = time.time()
        if not self.integrity_verified:
            logger.critical("evidence_integrity_compromised", evidence_id=self.evidence_id)
        return self.integrity_verified

    def export_chain(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_hash": self.evidence_hash,
            "collected_at": self.collected_at,
            "collected_by": self.collected_by,
            "custody_chain": [
                {
                    "timestamp": e.timestamp,
                    "actor": e.actor,
                    "action": e.action,
                    "purpose": e.purpose,
                    "signature": e.signature,
                }
                for e in self.custody_chain
            ],
            "integrity_verified": self.integrity_verified,
            "last_verification": self.last_verification,
            "total_transfers": len(self.custody_chain),
        }


class ImmutableAuditChain:
    """Blockchain-style immutable audit log with hash chaining."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []
        self._last_hash = "genesis"

    def add_entry(self, action: str, user_id: str, resource: str, details: dict[str, Any] | None = None) -> str:
        entry_data = {
            "index": len(self._entries),
            "timestamp": time.time(),
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "details": details or {},
            "previous_hash": self._last_hash,
        }
        entry_json = json.dumps(entry_data, sort_keys=True)
        entry_hash = hashlib.sha256(entry_json.encode()).hexdigest()
        entry_data["hash"] = entry_hash
        self._entries.append(entry_data)
        self._last_hash = entry_hash
        return entry_hash

    def verify_chain(self) -> bool:
        for i, entry in enumerate(self._entries):
            if i == 0:
                if entry.get("previous_hash") != "genesis":
                    return False
            else:
                prev_hash = self._entries[i - 1]["hash"]
                if entry.get("previous_hash") != prev_hash:
                    logger.critical("audit_chain_tampered", index=i)
                    return False

            temp_entry = {k: v for k, v in entry.items() if k != "hash"}
            entry_json = json.dumps(temp_entry, sort_keys=True)
            computed_hash = hashlib.sha256(entry_json.encode()).hexdigest()
            if entry.get("hash") != computed_hash:
                logger.critical("audit_entry_tampered", index=i)
                return False
        return True

    def get_entries(self, start: int = 0, end: int | None = None) -> list[dict[str, Any]]:
        return self._entries[start:end]

    def get_entry_count(self) -> int:
        return len(self._entries)


audit_chain = ImmutableAuditChain()
