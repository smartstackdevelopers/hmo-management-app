from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings
from app.core.errors import ProviderError
from app.providers.base import LlmMessage, LlmRequest
from app.providers.factory import get_llm_provider
from app.providers.mock import MockLlmProvider
from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_mock_provider_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    get_settings.cache_clear()
    settings = get_settings()
    provider = get_llm_provider(settings)
    assert isinstance(provider, MockLlmProvider)
    result = provider.complete(
        LlmRequest(
            model="mock-model",
            messages=[LlmMessage(role="user", content="hello")],
            timeout_seconds=5,
        )
    )
    assert result.content.startswith("[mock]")
    assert result.usage.total_tokens is None  # mock does not invent token counts


def test_openai_without_key_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    with pytest.raises(ProviderError):
        get_llm_provider(get_settings())


def test_provider_status_none(client: TestClient) -> None:
    response = client.get("/api/v1/provider", headers=auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["configured_provider"] == "none"
    assert body["available"] is False


@pytest.mark.real_llm
def test_real_openai_integration_skipped_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Real provider integration — skipped unless OPENAI_API_KEY is present in the environment."""
    import os

    key = os.environ.get("OPENAI_API_KEY_REAL") or os.environ.get("OPENAI_API_KEY")
    if not key or key.startswith("test"):
        pytest.skip("Real OPENAI_API_KEY not available — not reporting as passed")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", key)
    get_settings.cache_clear()
    provider = get_llm_provider(get_settings())
    assert provider is not None and provider.is_available()
