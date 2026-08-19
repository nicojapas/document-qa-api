from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "Document QA API"
    DESCRIPTION: str = "AI-powered RAG API with FastAPI and MongoDB"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # CORS Configuration
    CORS_ORIGINS: str = Field(default="http://localhost:3000")

    # MongoDB Configuration
    # We use Field(..., env='...') to ensure it maps correctly if naming differs
    MONGODB_URL: str = Field(default="mongodb://localhost:27017")
    DATABASE_NAME: str = "document_qa_db"

    # AI Configuration (OpenAI, Anthropic, etc.)
    OPENAI_API_KEY: str = Field(default="sk-placeholder")
    GEMINI_AI_API_KEY: str = Field(default="xx-xxx")
    DEEPSEEK_API_KEY: str = Field(default="xx-xxx")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com")
    VOYAGE_API_KEY: str = Field(default="xx-xxx")

    # LLM Provider Selection: "gemini", "openai", "deepseek", or "modal"
    LLM_PROVIDER: str = Field(default="gemini")

    # Vector Store Selection: "mongodb" (Atlas Vector Search) or "faiss" (local)
    VECTOR_STORE: str = Field(default="mongodb")

    # Modal LLM Configuration
    MODAL_LLM_URL: str = Field(default="")
    MODAL_MODEL_NAME: str = Field(default="Qwen/Qwen3-1.7B")
    MODAL_KEY: str = Field(default="")
    MODAL_SECRET: str = Field(default="")

    # Rate Limiting Configuration
    GLOBAL_DAILY_REQUEST_LIMIT: int = Field(default=100)  # Max requests per day globally
    MAX_FILE_SIZE_MB: int = Field(default=10)  # Max file size in MB
    MAX_CHUNKS_PER_DOCUMENT: int = Field(default=100)  # Max chunks to embed per document
    MAX_DOCUMENTS_TOTAL: int = Field(default=50)  # Max total documents in demo
    RATE_LIMIT_UPLOADS_PER_HOUR: str = Field(default="5/hour")  # Per-IP upload limit
    RATE_LIMIT_QUESTIONS_PER_HOUR: str = Field(default="30/hour")  # Per-IP question limit

    # Email Notification Configuration (for rate limit alerts)
    ALERT_EMAIL: str = Field(default="")
    SMTP_HOST: Optional[str] = Field(default=None)
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    SMTP_FROM: Optional[str] = Field(default=None)

    # JWT Authentication
    JWT_SECRET_KEY: str = Field(default="CHANGE-ME-IN-PRODUCTION")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_DAYS: int = Field(default=30)

    # Demo user credentials (hashed password stored, not plaintext)
    DEMO_USER_EMAIL: str = Field(default="demo@example.com")
    DEMO_USER_PASSWORD_HASH: str = Field(default="")

    # Render API Configuration (for scripts - local use only)
    RENDER_API_KEY: str = Field(default="")
    RENDER_SERVICE_ID: str = Field(default="")

    # Observability Configuration
    LLM_LATENCY_THRESHOLD_MS: int = Field(default=5000)  # Alert if latency exceeds this (ms)
    ALERT_WEBHOOK_URL: Optional[str] = Field(default=None)  # Webhook for latency alerts

    # App Config
    model_config = SettingsConfigDict(
        env_file=".env",              # Tell Pydantic to read from .env
        env_file_encoding="utf-8",
        case_sensitive=True           # MONGODB_URL must be uppercase in .env
    )

# Instantiate the settings object
settings = Settings()
