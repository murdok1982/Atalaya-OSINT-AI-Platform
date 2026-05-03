from __future__ import annotations

import time
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class TokenBlacklist:
    """Redis-backed JWT token revocation system."""

    def __init__(self, redis_client: Any = None) -> None:
        self._redis = redis_client
        self._prefix = "token:blacklist:"
        self._local_cache: dict[str, float] = {}

    async def add(self, token_jti: str, expires_at: float) -> None:
        if self._redis:
            try:
                ttl = int(expires_at - time.time())
                if ttl > 0:
                    await self._redis.set(f"{self._prefix}{token_jti}", "1", ex=ttl)
            except Exception as exc:
                logger.error("token_blacklist_redis_failed", error=str(exc))
        self._local_cache[token_jti] = expires_at
        logger.info("token_blacklisted", jti=token_jti)

    async def is_blacklisted(self, token_jti: str) -> bool:
        if token_jti in self._local_cache:
            if self._local_cache[token_jti] < time.time():
                del self._local_cache[token_jti]
                return False
            return True

        if self._redis:
            try:
                result = await self._redis.get(f"{self._prefix}{token_jti}")
                return result is not None
            except Exception as exc:
                logger.error("token_blacklist_check_failed", error=str(exc))
                return False

        return False

    async def cleanup_expired(self) -> int:
        now = time.time()
        expired = [k for k, v in self._local_cache.items() if v < now]
        for k in expired:
            del self._local_cache[k]
        return len(expired)

    async def revoke_all_user_tokens(self, user_id: str, expires_at: float) -> None:
        if self._redis:
            try:
                await self._redis.set(f"{self._prefix}user:{user_id}:revoked_at", str(time.time()), ex=int(expires_at - time.time()) + 86400)
            except Exception as exc:
                logger.error("user_token_revocation_failed", user_id=user_id, error=str(exc))
        logger.info("all_user_tokens_revoked", user_id=user_id)

    async def is_user_revoked(self, user_id: str) -> bool:
        if self._redis:
            try:
                result = await self._redis.get(f"{self._prefix}user:{user_id}:revoked_at")
                return result is not None
            except Exception:
                return False
        return False


token_blacklist = TokenBlacklist()
