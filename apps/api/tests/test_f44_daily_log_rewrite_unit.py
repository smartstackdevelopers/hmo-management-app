"""F4.4 daily-log rewrite unit tests. The AI client is mocked. No daily log is created."""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.ai_feature_flags.registry import get_definition
from app.ai_usage.features import FEATURE_DAILY_LOG_REWRITE, feature_for_workflow
from app.daily_log_rewrite import service as rewrite_service
from app.db.models.enums import HMoreRole
from app.support.schemas import DailyLogRewriteIn


def _worker():
    return SimpleNamespace(
        role=HMoreRole.SUPPORT_WORKER,
        organisation_id=uuid4(),
        user_id=uuid4(),
    )


def test_feature_is_pilot_and_fail_closed_for_existing_orgs() -> None:
    definition = get_definition(FEATURE_DAILY_LOG_REWRITE)
    assert definition is not None
    assert definition.phase_feature == "F4.4"
    assert definition.pilot_eligible is True
    assert definition.preserve_enabled_for_existing_orgs is False
    assert feature_for_workflow("daily_log_rewrite") == FEATURE_DAILY_LOG_REWRITE


def test_schema_rejects_blank_text() -> None:
    with pytest.raises(Exception):
        DailyLogRewriteIn.model_validate({"text": "   "})
    with pytest.raises(Exception):
        DailyLogRewriteIn.model_validate({"text": ""})
    parsed = DailyLogRewriteIn.model_validate({"text": "  hello  "})
    assert parsed.text == "hello"


def test_auth_denial_does_not_call_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"ai": False}
    monkeypatch.setattr(
        rewrite_service,
        "execute_daily_log_rewrite",
        lambda *a, **k: called.__setitem__("ai", True),
    )
    ctx = SimpleNamespace(role=HMoreRole.ORGANISATION_ADMIN, organisation_id=uuid4(), user_id=uuid4())
    with pytest.raises(HTTPException) as exc:
        rewrite_service.rewrite_daily_log_draft(MagicMock(), ctx, text="A note")
    assert exc.value.status_code == 403
    assert called["ai"] is False


def test_assignment_denial_does_not_call_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"ai": False}
    monkeypatch.setattr(rewrite_service.access, "require_daily_log_write", lambda ctx: None)

    def deny(*_a, **_k):
        raise HTTPException(status_code=403, detail="Not assigned to this tenant")

    monkeypatch.setattr(rewrite_service.access, "assert_tenant_support_access", deny)
    monkeypatch.setattr(
        rewrite_service,
        "execute_daily_log_rewrite",
        lambda *a, **k: called.__setitem__("ai", True),
    )
    with pytest.raises(HTTPException) as exc:
        rewrite_service.rewrite_daily_log_draft(
            MagicMock(), _worker(), text="A note", tenant_id=uuid4()
        )
    assert exc.value.status_code == 403
    assert called["ai"] is False


def test_feature_gate_blocks_before_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"ai": False, "feature": None}
    monkeypatch.setattr(rewrite_service.access, "require_daily_log_write", lambda ctx: None)

    def blocked(_session, _ctx, feature_id, **_k):
        called["feature"] = feature_id
        raise HTTPException(
            status_code=403,
            detail={"code": "ai_feature_disabled", "message": "This AI feature is not enabled"},
        )

    monkeypatch.setattr("app.ai_feature_flags.service.require_feature_available", blocked)
    monkeypatch.setattr(
        rewrite_service,
        "execute_daily_log_rewrite",
        lambda *a, **k: called.__setitem__("ai", True),
    )
    with pytest.raises(HTTPException) as exc:
        rewrite_service.rewrite_daily_log_draft(MagicMock(), _worker(), text="A note")
    assert exc.value.status_code == 403
    assert called["feature"] == FEATURE_DAILY_LOG_REWRITE
    assert called["ai"] is False


def test_success_returns_text_without_creating_a_daily_log(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rewrite_service.access, "require_daily_log_write", lambda ctx: None)
    monkeypatch.setattr("app.ai_feature_flags.service.require_feature_available", lambda *a, **k: None)
    monkeypatch.setattr(
        rewrite_service,
        "execute_daily_log_rewrite",
        lambda *_a, **_k: {
            "request_id": "req-44",
            "result": {
                "rewritten_text": "Staff visited and the outcome was unclear.",
                "prompt_id": "hmore.daily_log_rewrite.v1",
                "prompt_version": "1.0.0",
                "provider": "mock",
                "model_id": "mock-model",
            },
        },
    )
    monkeypatch.setattr(rewrite_service, "_record_activity", lambda *a, **k: "11111111-1111-4111-8111-111111111111")
    monkeypatch.setattr(rewrite_service, "record_event", lambda *a, **k: None)
    created = {"daily_log": False}
    monkeypatch.setattr(
        "app.support.service.create_daily_log",
        lambda *a, **k: created.__setitem__("daily_log", True),
    )
    session = MagicMock()
    result = rewrite_service.rewrite_daily_log_draft(session, _worker(), text="visited. outcome unclear")
    assert result["rewritten_text"] == "Staff visited and the outcome was unclear."
    assert result["activity_id"] == "11111111-1111-4111-8111-111111111111"
    assert result["request_id"] == "req-44"
    assert result["prompt_version"] == "1.0.0"
    assert created["daily_log"] is False
    assert session.add.call_count == 0
    source = inspect.getsource(rewrite_service.rewrite_daily_log_draft)
    assert "DailyLog" not in source
    assert "create_daily_log" not in source


def test_budget_cap_maps_to_402(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rewrite_service.access, "require_daily_log_write", lambda ctx: None)
    monkeypatch.setattr("app.ai_feature_flags.service.require_feature_available", lambda *a, **k: None)

    def capped(*_a, **_k):
        raise HTTPException(status_code=402, detail={"error": "ai_budget_exceeded", "message": "cap"})

    monkeypatch.setattr(rewrite_service, "execute_daily_log_rewrite", capped)
    recorded = {}

    def remember(*_a, **kwargs):
        recorded["status"] = kwargs.get("execution_status")
        recorded["error"] = kwargs.get("error_category")
        return None

    monkeypatch.setattr(rewrite_service, "_record_activity", remember)
    monkeypatch.setattr(rewrite_service, "record_event", lambda *a, **k: None)
    session = MagicMock()
    with pytest.raises(HTTPException) as exc:
        rewrite_service.rewrite_daily_log_draft(session, _worker(), text="A note")
    assert exc.value.status_code == 402
    assert exc.value.detail["error"] == "ai_budget_exceeded"
    assert recorded["status"] == "rejected_budget"
    assert recorded["error"] == "budget_cap"
    session.commit.assert_called()
