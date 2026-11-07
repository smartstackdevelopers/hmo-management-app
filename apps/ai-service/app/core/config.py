from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "HMore AI Service"
    environment: str = Field(default="development")
    api_v1_prefix: str = "/api/v1"
    log_level: str = "info"

    # Server-to-server shared secret (core API → AI service). Required for protected routes.
    ai_service_token: str = Field(default="", validation_alias="AI_SERVICE_TOKEN")

    # LLM provider: "none" | "mock" | "openai"
    llm_provider: str = Field(default="none", validation_alias="LLM_PROVIDER")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", validation_alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    llm_timeout_seconds: float = Field(default=30.0, validation_alias="LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=1, validation_alias="LLM_MAX_RETRIES")

    max_request_bytes: int = Field(default=262_144, validation_alias="AI_MAX_REQUEST_BYTES")
    workflow_timeout_seconds: float = Field(default=60.0, validation_alias="AI_WORKFLOW_TIMEOUT_SECONDS")

    default_allowed_features: str = Field(
        default="ai.foundation,ai.workflow.execute,ai.prompts.read,ai.approvals",
        validation_alias="AI_DEFAULT_ALLOWED_FEATURES",
    )

    @field_validator("llm_provider")
    @classmethod
    def _normalise_provider(cls, value: str) -> str:
        normalised = (value or "none").strip().lower()
        if normalised not in {"none", "mock", "openai"}:
            raise ValueError("LLM_PROVIDER must be one of: none, mock, openai")
        return normalised

    @property
    def allowed_features(self) -> frozenset[str]:
        return frozenset(part.strip() for part in self.default_allowed_features.split(",") if part.strip())

    @property
    def service_auth_configured(self) -> bool:
        return bool(self.ai_service_token.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
