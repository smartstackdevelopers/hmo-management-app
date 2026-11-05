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

    # Private file storage (F1.8) — never commit real credentials.
    # provider: memory | local | s3
    storage_provider: str = Field(default="memory")
    storage_local_root: str = Field(default=".hmore-private-storage")
    storage_max_upload_bytes: int = Field(default=10 * 1024 * 1024)
    storage_allowed_content_types: str = Field(
        default=(
            "application/pdf,image/jpeg,image/png,image/webp,"
            "text/plain,application/msword,"
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    )
    # S3-compatible (AWS S3, MinIO, etc.) — private bucket only
    s3_endpoint_url: str | None = None
    s3_region: str = Field(default="eu-west-2")
    s3_bucket: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_force_path_style: bool = Field(default=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
