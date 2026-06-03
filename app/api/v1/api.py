from fastapi import APIRouter

from app.api.v1 import auth, config, documents, metrics, qa


api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

api_router.include_router(config.router, prefix="/config", tags=["config"])

api_router.include_router(documents.router, prefix="/documents", tags=["documents"])

api_router.include_router(qa.router, prefix="/ask", tags=["ask"])

api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])