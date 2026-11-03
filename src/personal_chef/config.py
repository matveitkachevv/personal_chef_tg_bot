from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: SecretStr = SecretStr("")
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_chef"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.0-flash"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
