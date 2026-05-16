from fastapi import APIRouter

from app.core.config import settings
from app.services.embeddings import EMBEDDING_MODEL

router = APIRouter()

LLM_MODELS = {
    "gemini": "gemini-2.5-flash",
    "deepseek": "deepseek-chat",
}


@router.get("/")
async def get_config():
    """
    Returns the current model configuration.
    """
    provider = settings.LLM_PROVIDER.lower()
    return {
        "llm_provider": provider,
        "llm_model": LLM_MODELS.get(provider, "unknown"),
        "embedding_model": EMBEDDING_MODEL,
    }
