from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.routing.models import ModelTier, RoutingDecision
from app.routing.policy import EscalationPolicy, maybe_escalate
from app.routing.service import build_registry, escalate_if_needed, route_for_workflow
from tests.conftest import auth_headers


def test_low_cost_default_selection() -> None:
    settings = get_settings()
    decision = route_for_workflow(settings, workflow_id="foundation_routed_echo")
    assert decision.tier == ModelTier.low_cost
    assert decision.reason == "low_cost_default"


def test_premium_quality_requirement() -> None:
    settings = get_settings()
    decision = route_for_workflow(
        settings,
        workflow_id="foundation_routed_echo",
        quality_requirement="high",
    )
    assert decision.tier == ModelTier.premium
    assert decision.reason == "quality_requirement_high"


def test_escalation_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_ESCALATION_ENABLED", "false")
    get_settings.cache_clear()
    settings = get_settings()
    previous = route_for_workflow(settings, workflow_id="x")
    assert escalate_if_needed(settings, previous, empty_output=True) is None


def test_max_escalation_attempts() -> None:
    registry = build_registry(get_settings())
    previous = RoutingDecision(
        selected_key="default_low_cost",
        provider="mock",
        model_id="gpt-4o-mini",
        tier=ModelTier.low_cost,
        reason="low_cost_default",
        escalation_attempt=1,
    )
    policy = EscalationPolicy(enabled=True, max_attempts=1, on_empty_output=True, on_validation_failure=True)
    assert maybe_escalate(registry, policy=policy, previous=previous, validation_failed=True, empty_output=True) is None


def test_models_list_api(client: TestClient) -> None:
    response = client.get("/api/v1/models", headers=auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["default_model_key"] == "default_low_cost"
    assert any(m["tier"] == "low_cost" for m in body["models"])


def test_routed_workflow_uses_mock_and_cache(client: TestClient) -> None:
    headers = auth_headers()
    first = client.post(
        "/api/v1/workflows/execute",
        headers=headers,
        json={"workflow_id": "foundation_routed_echo", "message": "cache-me"},
    )
    assert first.status_code == 200
    assert first.json()["result"]["cache_status"] in {"miss", "lock_miss"}
    assert first.json()["result"]["content"].startswith("[mock]")
    assert first.json()["usage"]["cache_hit"] is False

    second = client.post(
        "/api/v1/workflows/execute",
        headers=headers,
        json={"workflow_id": "foundation_routed_echo", "message": "cache-me"},
    )
    assert second.status_code == 200
    assert second.json()["result"]["cache_status"] == "hit"
    assert second.json()["usage"]["cache_hit"] is True
