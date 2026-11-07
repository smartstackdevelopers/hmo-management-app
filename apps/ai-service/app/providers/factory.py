from __future__ import annotations

from app.core.config import Settings
from app.core.errors import ProviderError
from app.providers.base import LlmProvider
from app.providers.mock import MockLlmProvider
from app.providers.openai_compat import OpenAICompatibleProvider


def get_llm_provider(settings: Settings) -> LlmProvider | None:
    """Return a configured provider, or None when LLM_PROVIDER=none.

    Never silently substitutes a mock when openai is requested without credentials.
    """
    mode = settings.llm_provider
    if mode == "none":
        return None
    if mode == "mock":
        return MockLlmProvider()
    if mode == "openai":
        key = (settings.openai_api_key or "").strip()
        if not key:
            raise ProviderError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set")
        return OpenAICompatibleProvider(
            api_key=key,
            base_url=settings.openai_base_url,
            default_model=settings.openai_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    raise ProviderError(f"Unsupported LLM_PROVIDER '{mode}'")
