from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, ClassVar

from app.core.logging import get_logger

logger = get_logger(__name__)


class SlidingWindowRateLimiter:
    """Token bucket + sliding window rate limiter with Redis support."""

    def __init__(self, redis_client: Any = None) -> None:
        self._redis = redis_client
        self._prefix = "ratelimit:"
        self._local_windows: ClassVar[dict[str, list[float]]] = defaultdict(list)
        self._local_limits: ClassVar[dict[str, tuple[int, int]]] = {}

    async def is_allowed(self, key: str, max_requests: int = 60, window_seconds: int = 60) -> tuple[bool, dict[str, int]]:
        if self._redis:
            return await self._check_redis(key, max_requests, window_seconds)
        return self._check_local(key, max_requests, window_seconds)

    async def _check_redis(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, dict[str, int]]:
        try:
            redis_key = f"{self._prefix}{key}"
            now = time.time()
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
            pipe.zcard(redis_key)
            pipe.zadd(redis_key, {f"{now}:{id(key)}": now})
            pipe.expire(redis_key, window_seconds + 1)
            results = await pipe.execute()

            current_count = results[1]
            remaining = max(0, max_requests - current_count - 1)
            reset_time = int(now + window_seconds)

            info = {
                "limit": max_requests,
                "remaining": remaining,
                "reset": reset_time,
                "current": current_count + 1,
            }

            if current_count >= max_requests:
                return False, info
            return True, info
        except Exception as exc:
            logger.error("rate_limiter_redis_error", error=str(exc))
            return True, {"limit": max_requests, "remaining": -1, "reset": int(time.time() + window_seconds)}

    def _check_local(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, dict[str, int]]:
        now = time.time()
        window = self._local_windows[key]
        cutoff = now - window_seconds
        self._local_windows[key] = [t for t in window if t > cutoff]

        current_count = len(self._local_windows[key])
        remaining = max(0, max_requests - current_count - 1)
        reset_time = int(now + window_seconds)

        info = {
            "limit": max_requests,
            "remaining": remaining,
            "reset": reset_time,
            "current": current_count + 1,
        }

        if current_count >= max_requests:
            return False, info

        self._local_windows[key].append(now)
        return True, info

    async def get_usage(self, key: str, window_seconds: int = 60) -> int:
        if self._redis:
            try:
                redis_key = f"{self._prefix}{key}"
                now = time.time()
                await self._redis.zremrangebyscore(redis_key, 0, now - window_seconds)
                return await self._redis.zcard(redis_key)
            except Exception:
                return 0
        now = time.time()
        cutoff = now - window_seconds
        return len([t for t in self._local_windows.get(key, []) if t > cutoff])

    async def reset(self, key: str) -> None:
        if self._redis:
            await self._redis.delete(f"{self._prefix}{key}")
        self._local_windows.pop(key, None)

    async def cleanup(self) -> None:
        now = time.time()
        expired = [k for k, v in self._local_windows.items() if not v or all(t < now - 300 for t in v)]
        for k in expired:
            del self._local_windows[k]


rate_limiter = SlidingWindowRateLimiter()
