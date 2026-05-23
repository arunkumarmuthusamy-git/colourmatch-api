"""
AI Colour Matching App — Backend Configuration
Loads from .env file or environment variables
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "ColourMatch API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database — PostgreSQL for production (Neon), SQLite for local dev
    # Override with DATABASE_URL environment variable
    DATABASE_URL: str = "sqlite:///./colourmatch.db"

    # Server port (Render sets this via $PORT)
    PORT: int = 8000

    # JWT Authentication
    JWT_SECRET_KEY: str = "dev-secret-change-in-production-a1b2c3d4e5f6"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # AWS S3 (for photo storage — optional for local dev)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = "colourmatch-photos"

    # Free Trial Settings
    FREE_TRIAL_DAYS: int = 30
    FREE_TRIAL_SESSIONS: int = 20

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:8081,http://localhost:3000,http://localhost:19006"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
