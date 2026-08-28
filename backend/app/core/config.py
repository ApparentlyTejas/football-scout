from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    environment: str = "development"

    database_url: str = ""
    redis_url: str = ""

    api_football_key: str = ""

    llm_api_key: str = ""
    embedding_api_key: str = ""

    jwt_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
