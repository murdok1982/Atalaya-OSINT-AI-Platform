from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class STIXType(str, Enum):
    INDICATOR = "indicator"
    OBSERVABLE = "observable"
    THREAT_ACTOR = "threat-actor"
    ATTACK_PATTERN = "attack-pattern"
    CAMPAIGN = "campaign"
    INCIDENT = "incident"
    INFRASTRUCTURE = "infrastructure"
    MALWARE = "malware"
    REPORT = "report"
    IDENTITY = "identity"
    LOCATION = "location"
    TOOL = "tool"


class KillChainPhase(str, Enum):
    RECONNAISSANCE = "reconnaissance"
    WEAPONIZATION = "weaponization"
    DELIVERY = "delivery"
    EXPLOITATION = "exploitation"
    INSTALLATION = "installation"
    COMMAND_AND_CONTROL = "command-and-control"
    ACTIONS_ON_OBJECTIVES = "actions-on-objectives"


@dataclass
class STIXObject:
    type: STIXType
    name: str
    description: str = ""
    labels: list[str] = field(default_factory=list)
    confidence: float = 0.0
    created: str = ""
    modified: str = ""
    id: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    kill_chain_phases: list[str] = field(default_factory=list)
    external_references: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"{self.type.value}--{uuid.uuid4()}"
        now = datetime.now(timezone.utc).isoformat()
        if not self.created:
            self.created = now
        if not self.modified:
            self.modified = now

    def to_stix_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "id": self.id,
            "created": self.created,
            "modified": self.modified,
            "name": self.name,
            "description": self.description,
            "labels": self.labels,
            "confidence": self.confidence,
            "properties": self.properties,
            "kill_chain_phases": self.kill_chain_phases,
            "external_references": self.external_references,
        }


@dataclass
class STIXBundle:
    id: str = ""
    type: str = "bundle"
    objects: list[STIXObject] = field(default_factory=list)
    spec_version: str = "2.1"

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"bundle--{uuid.uuid4()}"

    def add_object(self, obj: STIXObject) -> None:
        self.objects.append(obj)

    def to_json(self) -> str:
        return json.dumps({
            "id": self.id,
            "type": self.type,
            "spec_version": self.spec_version,
            "objects": [obj.to_stix_dict() for obj in self.objects],
        }, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "STIXBundle":
        data = json.loads(json_str)
        bundle = cls(id=data.get("id", ""))
        for obj_data in data.get("objects", []):
            bundle.objects.append(STIXObject(
                type=STIXType(obj_data.get("type", "indicator")),
                name=obj_data.get("name", ""),
                description=obj_data.get("description", ""),
                labels=obj_data.get("labels", []),
                confidence=obj_data.get("confidence", 0.0),
                id=obj_data.get("id", ""),
                created=obj_data.get("created", ""),
                modified=obj_data.get("modified", ""),
                properties=obj_data.get("properties", {}),
            ))
        return bundle

    def export_file(self, filepath: str) -> None:
        with open(filepath, "w") as f:
            f.write(self.to_json())
        logger.info("stix_bundle_exported", filepath=filepath, count=len(self.objects))


class TAXIIClient:
    """TAXII 2.1 client for threat intelligence sharing."""

    def __init__(self, server_url: str = "", username: str = "", password: str = "") -> None:
        self._server_url = server_url
        self._username = username
        self._password = password
        self._collections: list[dict[str, str]] = []

    async def discover_collections(self) -> list[dict[str, str]]:
        if not self._server_url:
            return []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self._server_url}/taxii2/",
                    auth=(self._username, self._password) if self._username else None,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self._collections = data.get("collections", [])
                    return self._collections
        except Exception as exc:
            logger.warning("taxii_discovery_failed", error=str(exc))
        return []

    async def push_bundle(self, bundle: STIXBundle, collection_id: str = "") -> bool:
        if not self._server_url:
            return False
        try:
            import httpx
            collection = collection_id or (self._collections[0]["id"] if self._collections else "")
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self._server_url}/taxii2/collections/{collection}/objects/",
                    json=json.loads(bundle.to_json()),
                    auth=(self._username, self._password) if self._username else None,
                    headers={"Content-Type": "application/stix+json; version=2.1"},
                )
                return resp.status_code in (200, 201, 202)
        except Exception as exc:
            logger.error("taxii_push_failed", error=str(exc))
            return False

    async def pull_indicators(self, collection_id: str = "") -> list[STIXObject]:
        indicators = []
        if not self._server_url:
            return indicators
        try:
            import httpx
            collection = collection_id or (self._collections[0]["id"] if self._collections else "")
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{self._server_url}/taxii2/collections/{collection}/objects/",
                    params={"type": "indicator"},
                    auth=(self._username, self._password) if self._username else None,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for obj_data in data.get("objects", []):
                        indicators.append(STIXObject(
                            type=STIXType(obj_data.get("type", "indicator")),
                            name=obj_data.get("name", ""),
                            description=obj_data.get("description", ""),
                            id=obj_data.get("id", ""),
                            confidence=obj_data.get("confidence", 0.0),
                        ))
        except Exception as exc:
            logger.error("taxii_pull_failed", error=str(exc))
        return indicators


stix_manager = STIXBundle()
