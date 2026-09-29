from fastapi import APIRouter

from app.api.routes import login, private, users, utils
from app.core.config import settings

# Phase 2: documents/ingestion router
# from app.ingestion.router import router as documents_router

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
# api_router.include_router(documents_router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
