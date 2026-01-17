from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

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

    # App Config
    model_config = SettingsConfigDict(
        env_file=".env",              # Tell Pydantic to read from .env
        env_file_encoding="utf-8",
        case_sensitive=True           # MONGODB_URL must be uppercase in .env
    )

# Instantiate the settings object
settings = Settings()
