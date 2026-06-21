from pathlib import Path

from pydantic_settings import BaseSettings


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    APP_NAME: str = "Open Analytics"
    APP_ENV: str = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    DUCKDB_PATH: str = "app/db/open_analytics.duckdb"

    JWT_SECRET_KEY: str = "change_this_secret_key_later"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720
    UPSTOX_NOTIFIER_WEBHOOK_URL: str = (
        "https://api.openanalytics.co.in/api/v1/connections/upstox/notifier"
    )

    class Config:
        env_file = str(BACKEND_ROOT / ".env")


settings = Settings()
