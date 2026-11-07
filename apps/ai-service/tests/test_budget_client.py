"""F3.3 budget client — mocked HTTP (not real billing)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.budget.client import BudgetExceededError, reconcile_usage, reserve_budget
from app.budget.features import feature_for_workflow
from app.core.config import Settings


def _settings(**overrides) -> Settings:
    base = {
        "ai_service_token": "test-token",
        "core_api_base_url": "http://core.test",
        "budget_enforcement_fail_open": False,
        "budget_http_timeout_seconds": 1.0,
    }
    base.update(overrides)
    return Settings(**base)


def test_feature_map() -> None:
    assert feature_for_workflow("foundation_ping") == "ai.infra.foundation"
    assert feature_for_workflow("foundation_routed_echo") == "ai.infra.routing"


def test_reserve_skipped_when_core_unconfigured_fail_open() -> None:
    settings = _settings(core_api_base_url="", budget_enforcement_fail_open=True)
    result = reserve_budget(
        settings,
        request_id="req-1",
        organisation_id=uuid4(),
        user_id=uuid4(),
        feature_id="ai.infra.routing",
        workflow_id="foundation_routed_echo",
    )
    assert result["permitted"] is True
    assert result["status"] == "skipped"


def test_reserve_raises_on_402() -> None:
    settings = _settings()
    mock_response = MagicMock()
    mock_response.status_code = 402
    mock_response.json.return_value = {
        "detail": {
            "error": "ai_budget_exceeded",
            "message": "Organisation AI usage limit has been reached for this period",
        }
    }
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_response

    with patch("app.budget.client.httpx.Client", return_value=mock_client):
        with pytest.raises(BudgetExceededError) as exc:
            reserve_budget(
                settings,
                request_id="req-2",
                organisation_id=uuid4(),
                user_id=uuid4(),
                feature_id="ai.infra.routing",
                workflow_id="foundation_routed_echo",
            )
    assert "usage limit" in exc.value.message.lower()
    http = exc.value.to_http()
    assert http.status_code == 402


def test_reserve_success() -> None:
    settings = _settings()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"permitted": True, "status": "open", "reserved_amount": "0.05"}
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_response

    with patch("app.budget.client.httpx.Client", return_value=mock_client):
        result = reserve_budget(
            settings,
            request_id="req-3",
            organisation_id=uuid4(),
            user_id=uuid4(),
            feature_id="ai.infra.routing",
            workflow_id="foundation_routed_echo",
        )
    assert result["permitted"] is True


def test_reconcile_best_effort_on_http_error() -> None:
    settings = _settings()
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.side_effect = httpx.ConnectError("down")

    with patch("app.budget.client.httpx.Client", return_value=mock_client):
        assert reconcile_usage(settings, payload={"request_id": "x"}) is None
