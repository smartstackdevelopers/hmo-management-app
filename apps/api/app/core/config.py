from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "HMore API"
    environment: str = Field(default="development")
    api_v1_prefix: str = "/api/v1"
    log_level: str = "info"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str | None = None
    test_database_url: str | None = None

    # Auth0 — never commit real secrets. Domain has no scheme.
    auth0_domain: str | None = None
    auth0_audience: str | None = None
    auth0_issuer: str | None = None
    auth0_require_mfa_claim: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
