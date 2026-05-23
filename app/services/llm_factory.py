from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.core.config import settings

SUPPORTED_PROVIDERS = ["gemini", "deepseek", "modal"]

# DeepSeek uses an OpenAI-compatible API
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def get_llm():
    """
    Factory function that returns the appropriate LLM based on LLM_PROVIDER setting.

    Set LLM_PROVIDER env var to switch between providers:
    - "gemini" (default): Uses Gemini 2.5 Flash
    - "deepseek": Uses DeepSeek V4 via OpenAI-compatible API
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            api_key=settings.GEMINI_AI_API_KEY
        )
    elif provider == "deepseek":
        return ChatOpenAI(
            model="deepseek-v4-flash",
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL
        )
    elif provider == "modal":
        return ChatOpenAI(
            model=settings.MODAL_MODEL_NAME,
            api_key="not-needed",
            base_url=settings.MODAL_LLM_URL,
            default_headers={
                "Modal-Key": settings.MODAL_KEY,
                "Modal-Secret": settings.MODAL_SECRET,
            }
        )
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'. "
            f"Supported providers: {SUPPORTED_PROVIDERS}"
        )
