from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.approval.service import reset_approval_service_for_tests
from app.batch.store import reset_batch_store_for_tests
from app.cache.service import reset_cache_service_for_tests
from app.core.config import get_settings
from app.main import app
from app.prompts.store import reset_prompt_store_for_tests
from app.routing.service import reset_registry_cache


ORG_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
ORG_B = uuid.UUID("22222222-2222-2222-2222-222222222222")
USER_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
SERVICE_TOKEN = "test-ai-service-token"


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_SERVICE_TOKEN", SERVICE_TOKEN)
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("AI_CACHE_BACKEND", "memory")
    monkeypatch.setenv("AI_CACHE_ENABLED", "true")
    monkeypatch.setenv("AI_BATCH_EAGER", "true")
    monkeypatch.setenv("AI_ESCALATION_ENABLED", "true")
    monkeypatch.setenv("AI_ESCALATION_MAX_ATTEMPTS", "1")
    get_settings.cache_clear()
    reset_registry_cache()
    reset_prompt_store_for_tests()
    reset_approval_service_for_tests()
    reset_batch_store_for_tests()
    reset_cache_service_for_tests()
    yield
    get_settings.cache_clear()
    reset_registry_cache()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def auth_headers(
    *,
    org_id: uuid.UUID = ORG_A,
    user_id: uuid.UUID = USER_A,
    role: str = "organisation_admin",
    features: str | None = None,
    token: str = SERVICE_TOKEN,
) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "X-HMore-Organisation-Id": str(org_id),
        "X-HMore-User-Id": str(user_id),
        "X-HMore-Role": role,
        "X-Correlation-Id": "test-correlation",
    }
    if features is not None:
        headers["X-HMore-Features"] = features
    return headers
