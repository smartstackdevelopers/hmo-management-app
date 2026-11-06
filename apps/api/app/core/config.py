from functools import lru_cache

from pydantic import Field, field_validator
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

    # F2.2 reminder lead times (minutes before event). Configurable via env.
    reminder_shift_lead_minutes: int = Field(default=60, ge=1, le=7 * 24 * 60)
    reminder_visit_lead_minutes: int = Field(default=120, ge=1, le=7 * 24 * 60)
    reminder_task_due_lead_minutes: int = Field(default=1440, ge=1, le=14 * 24 * 60)
    # F2.3 training / safeguarding reminder lead times (configurable; not statutory).
    reminder_training_expiry_lead_days: int = Field(default=30, ge=1, le=365)
    reminder_safeguarding_lead_minutes: int = Field(default=1440, ge=1, le=14 * 24 * 60)
    reminder_dispatch_batch_size: int = Field(default=100, ge=1, le=1000)

    # Comma-separated browser origins allowed for CORS (never "*' in production).
    cors_allowed_origins: str = Field(default="http://localhost:3000")
    # When true (recommended in production), reject clearly insecure absolute URLs in CORS list.
    enforce_https_origins: bool = Field(default=False)

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

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return (value or "development").strip().lower()

    @property
    def is_production(self) -> bool:
        return self.environment in {"production", "prod"}

    @property
    def is_development(self) -> bool:
        return self.environment in {"development", "dev", "local", "test"}

    def cors_origins_list(self) -> list[str]:
        return [part.strip() for part in self.cors_allowed_origins.split(",") if part.strip()]

    def production_validation_errors(self) -> list[str]:
        """Return blocking configuration problems for production boots."""
        errors: list[str] = []
        if not self.is_production:
            return errors

        if not self.database_url:
            errors.append("DATABASE_URL is required in production")
        elif self.database_url.startswith("sqlite"):
            errors.append("SQLite is not allowed in production")

        if not self.auth0_domain:
            errors.append("AUTH0_DOMAIN is required in production")
        if not self.auth0_audience:
            errors.append("AUTH0_AUDIENCE is required in production")

        provider = (self.storage_provider or "").strip().lower()
        if provider == "memory":
            errors.append("STORAGE_PROVIDER=memory is not allowed in production")
        if provider == "s3":
            if not self.s3_bucket:
                errors.append("S3_BUCKET is required when STORAGE_PROVIDER=s3")
            # Access keys may be omitted when the runtime uses an IAM role — that is preferred.
            if bool(self.s3_access_key_id) ^ bool(self.s3_secret_access_key):
                errors.append(
                    "S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY must both be set or both omitted "
                    "(omit when using IAM roles)"
                )

        origins = self.cors_origins_list()
        if not origins:
            errors.append("CORS_ALLOWED_ORIGINS must list at least one origin in production")
        if "*" in origins:
            errors.append("CORS_ALLOWED_ORIGINS must not use '*' in production")
        if self.enforce_https_origins or self.is_production:
            for origin in origins:
                if origin.startswith("http://") and "localhost" not in origin:
                    errors.append(f"Insecure CORS origin not allowed in production: {origin}")

        return errors

    def assert_safe_for_runtime(self) -> None:
        errors = self.production_validation_errors()
        if errors:
            joined = "; ".join(errors)
            raise RuntimeError(f"Unsafe production configuration: {joined}")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Validate eagerly so misconfigured production containers fail at import/startup.
    settings.assert_safe_for_runtime()
    return settings


def reset_settings_cache() -> None:
    get_settings.cache_clear()
