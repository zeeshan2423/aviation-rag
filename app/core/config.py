"""
Centralized Configuration Engine for Aviation RAG.
Uses Pydantic Settings to manage environment variables, API keys, and model parameters.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Production-grade configuration engine using Pydantic.
    Enforces strict typing and validation for environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Keys (Required)
    GEMINI_API_KEY: str
    VOYAGE_API_KEY: str = os.getenv("VOYAGE_API_KEY", "") # Fallback for safety if local

    # Model Configuration
    LLM_MODEL_NAME: str = "gemini-3.1-flash-lite-preview"
    EMBEDDING_MODEL_NAME: str = "voyage-large-2"
    RERANK_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Infrastructure
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    VEC_STORE_PATH: str = "vectorstore"

    # Thresholds
    MIN_RERANK_SCORE: float = 2.0
    CAUTION_RERANK_SCORE: float = 5.0

    # Logging
    LOG_LEVEL: str = "INFO"

# Create a singleton instance for project-wide use
settings = Settings()
