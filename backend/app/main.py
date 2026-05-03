from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.events import lifespan
from app.core.logging import configure_logging
from app.core.middleware import RateLimitMiddleware
from app.core.waf import WAFSecurityHeadersMiddleware

configure_logging(settings.LOG_LEVEL, settings.ENVIRONMENT)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    from app.core.events_bus import event_bus
    from app.core.token_blacklist import token_blacklist
    from app.core.rate_limiter import rate_limiter
    from app.db.database import get_redis
    from app.core.security import token_blacklist as tb

    await event_bus.initialize()

    redis_client = await get_redis()
    if redis_client:
        tb._redis = redis_client
        rate_limiter._redis = redis_client

    yield

    await event_bus.shutdown()


app = FastAPI(
    title="Atalaya OSINT Platform",
    description="Open-source intelligence operations platform — State-grade intelligence collection, analysis, and reporting",
    version="2.0.0",
    lifespan=app_lifespan,
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
)

# CORS — never wildcard in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "X-Request-ID"],
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(WAFSecurityHeadersMiddleware)

if settings.is_production:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)


@app.middleware("http")
async def add_request_id(request: Request, call_next: Any) -> Any:
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    request.state.tenant_id = settings.DEFAULT_TENANT_ID
    request.state.classification = settings.DEFAULT_CLASSIFICATION
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def security_checks(request: Request, call_next: Any) -> Any:
    from app.core.bruteforce import BruteForceProtector

    client_ip = request.client.host if request.client else "unknown"

    if BruteForceProtector.is_ip_blocked(client_ip):
        return JSONResponse(
            status_code=403,
            content={"detail": "IP address temporarily blocked due to suspicious activity"},
        )

    user_agent = request.headers.get("user-agent", "")
    if not user_agent:
        return JSONResponse(
            status_code=400,
            content={"detail": "User-Agent header is required"},
        )

    return await call_next(request)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Any) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Not found", "path": str(request.url.path)},
    )


@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc: Any) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Any) -> JSONResponse:
    from app.core.logging import get_logger
    logger = get_logger("main")
    logger.error("unhandled_exception", path=str(request.url.path), error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, Any]:
    from app.db.database import check_database_connection, check_redis_connection

    db_ok = await check_database_connection()
    redis_ok = await check_redis_connection()

    status = "healthy" if (db_ok and redis_ok) else "degraded"

    return {
        "status": status,
        "version": settings.APP_VERSION,
        "timestamp": __import__("time").time(),
        "checks": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        },
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check() -> dict[str, Any]:
    from app.db.database import check_database_connection, check_redis_connection
    from app.core.events_bus import event_bus

    db_ok = await check_database_connection()
    redis_ok = await check_redis_connection()
    kafka_ok = event_bus._kafka_producer is not None if event_bus._initialized else True

    all_ok = db_ok and redis_ok and kafka_ok

    return {
        "ready": all_ok,
        "checks": {
            "database": db_ok,
            "redis": redis_ok,
            "kafka": kafka_ok,
        },
    }


# Register API router
from app.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")
