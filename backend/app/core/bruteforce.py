from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import ClassVar

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AttemptRecord:
    count: int = 0
    last_attempt: float = 0.0
    locked_until: float = 0.0
    ip_addresses: list[str] = field(default_factory=list)


class BruteForceProtector:
    """Progressive brute-force protection with account lockout and IP throttling."""

    MAX_ATTEMPTS: int = 5
    LOCKOUT_SECONDS: int = 300
    IP_MAX_ATTEMPTS: int = 20
    IP_LOCKOUT_SECONDS: int = 900
    PROGRESSIVE_MULTIPLIER: float = 2.0

    _attempts: ClassVar[dict[str, AttemptRecord]] = {}
    _ip_attempts: ClassVar[dict[str, AttemptRecord]] = {}

    @classmethod
    def is_locked(cls, identifier: str) -> bool:
        record = cls._attempts.get(identifier)
        if not record:
            return False
        if record.locked_until > time.time():
            return True
        if record.locked_until > 0:
            record.locked_until = 0
            record.count = 0
        return False

    @classmethod
    def is_ip_blocked(cls, ip: str) -> bool:
        record = cls._ip_attempts.get(ip)
        if not record:
            return False
        if record.locked_until > time.time():
            return True
        if record.locked_until > 0:
            record.locked_until = 0
            record.count = 0
        return False

    @classmethod
    def record_failure(cls, identifier: str, ip: str = "") -> None:
        record = cls._attempts.get(identifier, AttemptRecord())
        record.count += 1
        record.last_attempt = time.time()
        if ip and ip not in record.ip_addresses:
            record.ip_addresses.append(ip)

        if record.count >= cls.MAX_ATTEMPTS:
            lockout = cls.LOCKOUT_SECONDS * (cls.PROGRESSIVE_MULTIPLIER ** (record.count - cls.MAX_ATTEMPTS))
            record.locked_until = time.time() + lockout
            logger.warning("account_locked", identifier=identifier, lockout_seconds=lockout, attempts=record.count)

        cls._attempts[identifier] = record

        if ip:
            cls._record_ip_failure(ip)

    @classmethod
    def _record_ip_failure(cls, ip: str) -> None:
        record = cls._ip_attempts.get(ip, AttemptRecord())
        record.count += 1
        record.last_attempt = time.time()

        if record.count >= cls.IP_MAX_ATTEMPTS:
            record.locked_until = time.time() + cls.IP_LOCKOUT_SECONDS
            logger.warning("ip_blocked", ip=ip, lockout_seconds=cls.IP_LOCKOUT_SECONDS)

        cls._ip_attempts[ip] = record

    @classmethod
    def record_success(cls, identifier: str, ip: str = "") -> None:
        cls._attempts.pop(identifier, None)
        if ip:
            cls._ip_attempts.pop(ip, None)

    @classmethod
    def get_remaining_attempts(cls, identifier: str) -> int:
        record = cls._attempts.get(identifier)
        if not record:
            return cls.MAX_ATTEMPTS
        return max(0, cls.MAX_ATTEMPTS - record.count)

    @classmethod
    def cleanup_expired(cls) -> int:
        now = time.time()
        removed = 0
        expired = [k for k, v in cls._attempts.items() if v.locked_until > 0 and v.locked_until < now]
        for k in expired:
            del cls._attempts[k]
            removed += 1
        expired_ip = [k for k, v in cls._ip_attempts.items() if v.locked_until > 0 and v.locked_until < now]
        for k in expired_ip:
            del cls._ip_attempts[k]
            removed += 1
        return removed
