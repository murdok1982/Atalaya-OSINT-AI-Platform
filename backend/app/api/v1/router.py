from fastapi import APIRouter

from app.api.v1 import auth, cases, entities, evidence, jobs, reports, health, config_router

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(entities.router, prefix="/entities", tags=["entities"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["evidence"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(config_router.router, prefix="/config", tags=["config"])
