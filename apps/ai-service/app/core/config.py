from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "HMore AI Service"
    environment: str = Field(default="development")
    api_v1_prefix: str = "/api/v1"
    # Model keys are optional. The foundation graph does not call a provider.
    openai_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
