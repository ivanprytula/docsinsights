from fastapi import APIRouter

from app.api.routes import login, private, users, utils
from app.core.config import settings
from app.ingestion.router import router as documents_router
from app.retrieval.router import router as search_router

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(documents_router)
api_router.include_router(search_router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
