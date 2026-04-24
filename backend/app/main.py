from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.events import lifespan
from app.core.logging import configure_logging

configure_logging(settings.LOG_LEVEL, settings.ENVIRONMENT)

app = FastAPI(
    title="Atalaya OSINT Platform",
    description="Open-source intelligence operations platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
)

# CORS — never wildcard in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.is_production:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])


@app.middleware("http")
async def add_request_id(request: Request, call_next: Any) -> Any:
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Any) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Not found", "path": str(request.url.path)},
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Any) -> JSONResponse:
    from app.core.logging import get_logger  # noqa: PLC0415
    logger = get_logger("main")
    logger.error("unhandled_exception", path=str(request.url.path), error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"name": "Atalaya OSINT Platform", "version": "0.1.0", "status": "running"}


# Register API router
from app.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")
