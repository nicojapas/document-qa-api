from fastapi import APIRouter

from app.services.embeddings import EMBEDDING_MODEL
from app.services.llm_factory import get_available_models, get_default_model

router = APIRouter()


@router.get("/")
async def get_config():
    """
    Returns the current model configuration and available models.
    """
    return {
        "llm_model": get_default_model(),
        "available_models": get_available_models(),
        "embedding_model": EMBEDDING_MODEL,
    }
