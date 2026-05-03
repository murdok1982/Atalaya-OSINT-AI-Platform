from __future__ import annotations

import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        if path.startswith("/api/docs") or path.startswith("/api/redoc") or path == "/health":
            return await call_next(request)

        if path.startswith("/api/v1/auth/login"):
            key = f"login:{client_ip}"
            allowed, info = await rate_limiter.is_allowed(
                key,
                max_requests=settings.RATE_LIMIT_LOGIN_PER_HOUR,
                window_seconds=3600,
            )
        else:
            key = f"api:{client_ip}"
            allowed, info = await rate_limiter.is_allowed(
                key,
                max_requests=settings.RATE_LIMIT_API_PER_MINUTE,
                window_seconds=60,
            )

        request.state.rate_limit_info = info

        if not allowed:
            logger.warning("rate_limit_exceeded", ip=client_ip, path=path, limit=info["limit"])
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": info["limit"],
                    "retry_after": info["reset"] - int(time.time()),
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["reset"] - int(time.time())),
                },
            )

        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response
