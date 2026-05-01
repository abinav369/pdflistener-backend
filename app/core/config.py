from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "PDF Listener API"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = "sqlite:///./pdflistener.db"

    # File storage
    UPLOAD_DIR: str = "uploads"
    AUDIO_OUTPUT_DIR: str = "audio_output"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "doc", "docx"]

    # TTS (Text-to-Speech) — set to "gtts" (free) or "openai" (premium)
    TTS_ENGINE: str = "gtts"
    OPENAI_API_KEY: str = ""

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.AUDIO_OUTPUT_DIR, exist_ok=True)
