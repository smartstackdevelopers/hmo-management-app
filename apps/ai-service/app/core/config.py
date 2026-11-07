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

    ai_service_token: str = Field(default="", validation_alias="AI_SERVICE_TOKEN")

    # LLM provider: "none" | "mock" | "openai"
    llm_provider: str = Field(default="none", validation_alias="LLM_PROVIDER")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", validation_alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    llm_timeout_seconds: float = Field(default=30.0, validation_alias="LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=1, validation_alias="LLM_MAX_RETRIES")

    # F3.2 routing
    ai_default_model_key: str = Field(default="default_low_cost", validation_alias="AI_DEFAULT_MODEL_KEY")
    ai_premium_model_id: str | None = Field(default="gpt-4o", validation_alias="AI_PREMIUM_MODEL_ID")
    ai_model_registry_json: str = Field(default="", validation_alias="AI_MODEL_REGISTRY_JSON")
    ai_escalation_enabled: bool = Field(default=True, validation_alias="AI_ESCALATION_ENABLED")
    ai_escalation_max_attempts: int = Field(default=1, validation_alias="AI_ESCALATION_MAX_ATTEMPTS")
    ai_escalate_on_empty_output: bool = Field(default=True, validation_alias="AI_ESCALATE_ON_EMPTY_OUTPUT")
    ai_escalate_on_validation_failure: bool = Field(
        default=True, validation_alias="AI_ESCALATE_ON_VALIDATION_FAILURE"
    )

    # F3.2 cache
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    ai_cache_enabled: bool = Field(default=True, validation_alias="AI_CACHE_ENABLED")
    ai_cache_backend: str = Field(default="memory", validation_alias="AI_CACHE_BACKEND")  # none|memory|redis
    ai_cache_ttl_seconds: int = Field(default=300, validation_alias="AI_CACHE_TTL_SECONDS")
    ai_cache_lock_ttl_seconds: int = Field(default=30, validation_alias="AI_CACHE_LOCK_TTL_SECONDS")
    ai_cache_lock_wait_seconds: float = Field(default=0.05, validation_alias="AI_CACHE_LOCK_WAIT_SECONDS")
    ai_cache_fail_open: bool = Field(default=True, validation_alias="AI_CACHE_FAIL_OPEN")

    # F3.2 batch
    ai_batch_max_retries: int = Field(default=2, validation_alias="AI_BATCH_MAX_RETRIES")
    ai_batch_eager: bool = Field(default=True, validation_alias="AI_BATCH_EAGER")
    ai_batch_fail_open_to_eager: bool = Field(default=True, validation_alias="AI_BATCH_FAIL_OPEN_TO_EAGER")

    max_request_bytes: int = Field(default=262_144, validation_alias="AI_MAX_REQUEST_BYTES")
    workflow_timeout_seconds: float = Field(default=60.0, validation_alias="AI_WORKFLOW_TIMEOUT_SECONDS")

    default_allowed_features: str = Field(
        default=(
            "ai.foundation,ai.workflow.execute,ai.prompts.read,ai.approvals,"
            "ai.routing.read,ai.batch.submit,ai.batch.read"
        ),
        validation_alias="AI_DEFAULT_ALLOWED_FEATURES",
    )

    @field_validator("llm_provider")
    @classmethod
    def _normalise_provider(cls, value: str) -> str:
        normalised = (value or "none").strip().lower()
        if normalised not in {"none", "mock", "openai"}:
            raise ValueError("LLM_PROVIDER must be one of: none, mock, openai")
        return normalised

    @field_validator("ai_cache_backend")
    @classmethod
    def _normalise_cache(cls, value: str) -> str:
        normalised = (value or "memory").strip().lower()
        if normalised not in {"none", "memory", "redis"}:
            raise ValueError("AI_CACHE_BACKEND must be one of: none, memory, redis")
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
