from pathlib import Path

from pydantic_settings import BaseSettings
import os


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    APP_NAME: str = "Open Analytics"
    APP_ENV: str = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    CORS_ORIGINS : str = os.getenv("CORS_ORIGINS")

    DUCKDB_PATH: str = "app/db/open_analytics.duckdb"

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = str(BACKEND_ROOT / ".env")


settings = Settings()
