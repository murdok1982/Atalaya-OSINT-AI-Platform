from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, ClassVar

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SecretVersion:
    value_hash: str
    created_at: float
    expires_at: float
    is_active: bool = True
    rotated_by: str = ""


class SecretManager:
    """Manages secret rotation with versioning and automatic expiry."""

    _secrets: ClassVar[dict[str, list[SecretVersion]]] = {}
    _rotation_log: ClassVar[list[dict[str, Any]]] = []

    @classmethod
    def register_secret(cls, name: str, value: str, rotation_hours: int | None = None) -> str:
        value_hash = hashlib.sha256(value.encode()).hexdigest()[:16]
        hours = rotation_hours or settings.SECRET_ROTATION_HOURS
        version = SecretVersion(
            value_hash=value_hash,
            created_at=time.time(),
            expires_at=time.time() + (hours * 3600),
        )
        if name not in cls._secrets:
            cls._secrets[name] = []
        cls._secrets[name].append(version)
        logger.info("secret_registered", name=name, hash=value_hash, expires_in_hours=hours)
        return value_hash

    @classmethod
    def rotate_secret(cls, name: str, new_value: str, rotated_by: str = "system") -> tuple[str, str]:
        old_hash = cls.get_current_hash(name)
        value_hash = hashlib.sha256(new_value.encode()).hexdigest()[:16]
        hours = settings.SECRET_ROTATION_HOURS

        for secret_list in cls._secrets.values():
            for v in secret_list:
                if v.value_hash == old_hash:
                    v.is_active = False

        version = SecretVersion(
            value_hash=value_hash,
            created_at=time.time(),
            expires_at=time.time() + (hours * 3600),
            rotated_by=rotated_by,
        )
        if name not in cls._secrets:
            cls._secrets[name] = []
        cls._secrets[name].append(version)

        cls._rotation_log.append({
            "name": name,
            "old_hash": old_hash,
            "new_hash": value_hash,
            "rotated_by": rotated_by,
            "rotated_at": time.time(),
        })

        logger.info("secret_rotated", name=name, old_hash=old_hash, new_hash=value_hash, rotated_by=rotated_by)
        return value_hash, old_hash

    @classmethod
    def get_current_hash(cls, name: str) -> str:
        secrets_list = cls._secrets.get(name, [])
        for v in reversed(secrets_list):
            if v.is_active:
                return v.value_hash
        return ""

    @classmethod
    def is_secret_expired(cls, name: str) -> bool:
        secrets_list = cls._secrets.get(name, [])
        if not secrets_list:
            return True
        current = secrets_list[-1]
        return time.time() > current.expires_at

    @classmethod
    def get_expiring_secrets(cls, threshold_hours: int = 24) -> list[str]:
        expiring = []
        threshold = time.time() + (threshold_hours * 3600)
        for name, versions in cls._secrets.items():
            active = [v for v in versions if v.is_active]
            if active and active[-1].expires_at < threshold:
                expiring.append(name)
        return expiring

    @classmethod
    def cleanup_expired(cls) -> int:
        now = time.time()
        removed = 0
        for name in list(cls._secrets.keys()):
            cls._secrets[name] = [v for v in cls._secrets[name] if v.expires_at > now or v.is_active]
            if not cls._secrets[name]:
                del cls._secrets[name]
                removed += 1
        return removed

    @classmethod
    def get_rotation_history(cls, name: str = "") -> list[dict[str, Any]]:
        if name:
            return [r for r in cls._rotation_log if r["name"] == name]
        return cls._rotation_log

    @classmethod
    def generate_api_key(cls, prefix: str = "atalaya") -> str:
        raw = f"{prefix}_{secrets.token_urlsafe(32)}"
        cls.register_secret(f"api_key:{raw[:12]}...", raw, rotation_hours=8760)
        return raw

    @classmethod
    def verify_api_key(cls, api_key: str) -> bool:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        for name, versions in cls._secrets.items():
            if name.startswith("api_key:"):
                for v in versions:
                    if v.value_hash == key_hash and v.is_active:
                        return True
        return False


secret_manager = SecretManager()
