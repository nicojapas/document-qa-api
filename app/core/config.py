from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "Document QA API"
    DESCRIPTION: str = "AI-powered RAG API with FastAPI and MongoDB"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # MongoDB Configuration
    # We use Field(..., env='...') to ensure it maps correctly if naming differs
    MONGODB_URL: str = Field(default="mongodb://localhost:27017")
    DATABASE_NAME: str = "document_qa_db"

    # AI Configuration (OpenAI, Anthropic, etc.)
    OPENAI_API_KEY: str = Field(default="sk-placeholder")
    GEMINI_AI_API_KEY: str = Field(default="xx-xxx")
    DEEPSEEK_API_KEY: str = Field(default="xx-xxx")

    # LLM Provider Selection: "gemini" or "deepseek"
    LLM_PROVIDER: str = Field(default="gemini")

    # Rate Limiting Configuration
    GLOBAL_DAILY_REQUEST_LIMIT: int = Field(default=100)  # Max requests per day globally
    MAX_FILE_SIZE_MB: int = Field(default=10)  # Max file size in MB
    MAX_CHUNKS_PER_DOCUMENT: int = Field(default=100)  # Max chunks to embed per document
    MAX_DOCUMENTS_TOTAL: int = Field(default=50)  # Max total documents in demo
    RATE_LIMIT_UPLOADS_PER_HOUR: str = Field(default="5/hour")  # Per-IP upload limit
    RATE_LIMIT_QUESTIONS_PER_HOUR: str = Field(default="30/hour")  # Per-IP question limit

    # Email Notification Configuration (for rate limit alerts)
    ALERT_EMAIL: str = Field(default="nicolasjapas@gmail.com")
    SMTP_HOST: Optional[str] = Field(default=None)
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    SMTP_FROM: Optional[str] = Field(default=None)

    # App Config
    model_config = SettingsConfigDict(
        env_file=".env",              # Tell Pydantic to read from .env
        env_file_encoding="utf-8",
        case_sensitive=True           # MONGODB_URL must be uppercase in .env
    )

# Instantiate the settings object
settings = Settings()
