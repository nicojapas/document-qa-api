from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.core.config import settings


# Model registry: maps model names to their configurations
AVAILABLE_MODELS = {
    "gemini-2.5-flash": {
        "provider": "gemini",
        "model_id": "gemini-2.5-flash",
    },
    "deepseek-v4-flash": {
        "provider": "deepseek",
        "model_id": "deepseek-v4-flash",
    },
    "qwen3-1.7b": {
        "provider": "modal",
        "model_id": "Qwen/Qwen3-1.7B",
    },
    "gpt-4o": {
        "provider": "openai",
        "model_id": "gpt-4o",
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "model_id": "gpt-4o-mini",
    },
}

# Default model per provider (for backwards compatibility)
DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "deepseek": "deepseek-v4-flash",
    "modal": "qwen3-1.7b",
    "openai": "gpt-4o-mini",
}


def get_available_models() -> list[str]:
    """Returns list of available model names."""
    return list(AVAILABLE_MODELS.keys())


def get_default_model() -> str:
    """Returns the default model based on LLM_PROVIDER setting."""
    provider = settings.LLM_PROVIDER.lower()
    return DEFAULT_MODELS.get(provider, "gemini-2.5-flash")


def get_llm_for_model(model_name: str | None = None):
    """
    Factory function that returns an LLM instance for the specified model.

    Args:
        model_name: Name of the model (e.g., "gemini-2.5-flash", "qwen3-1.7b")
                   If None, uses the default based on LLM_PROVIDER setting.
    """
    if model_name is None:
        model_name = get_default_model()

    if model_name not in AVAILABLE_MODELS:
        raise ValueError(
            f"Unknown model: '{model_name}'. "
            f"Available models: {list(AVAILABLE_MODELS.keys())}"
        )

    config = AVAILABLE_MODELS[model_name]
    provider = config["provider"]
    model_id = config["model_id"]

    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model_id,
            api_key=settings.GEMINI_AI_API_KEY
        )
    elif provider == "deepseek":
        return ChatOpenAI(
            model=model_id,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            stream_usage=True,
        )
    elif provider == "modal":
        return ChatOpenAI(
            model=model_id,
            api_key="not-needed",
            base_url=settings.MODAL_LLM_URL,
            default_headers={
                "Modal-Key": settings.MODAL_KEY,
                "Modal-Secret": settings.MODAL_SECRET,
            },
            stream_usage=True,
        )
    elif provider == "openai":
        return ChatOpenAI(
            model=model_id,
            api_key=settings.OPENAI_API_KEY,
            stream_usage=True,
        )
    else:
        raise ValueError(f"Unknown provider: '{provider}'")


def get_llm():
    """
    Legacy factory function for backwards compatibility.
    Returns the default LLM based on LLM_PROVIDER setting.
    """
    return get_llm_for_model(None)
