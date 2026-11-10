"""F4.4 daily log rewrite workflow. No live model calls."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.budget.features import feature_for_workflow
from app.core.config import Settings
from app.core.errors import WorkflowError
from app.graph.daily_log_rewrite import (
    DAILY_LOG_REWRITE_PROMPT_ID,
    run_daily_log_rewrite,
    validate_daily_log_rewrite_output,
)
from app.graph.runtime import SUPPORTED_WORKFLOWS, execute_workflow
from app.context.trusted import TrustedCallerContext
from app.prompts.store import reset_prompt_store_for_tests


def test_workflow_is_registered_and_budgeted() -> None:
    assert "daily_log_rewrite" in SUPPORTED_WORKFLOWS
    assert feature_for_workflow("daily_log_rewrite") == "ai.workflow.daily_log_rewrite"


def test_prompt_forbids_invented_facts() -> None:
    store = reset_prompt_store_for_tests()
    record, rendered = store.render(
        DAILY_LOG_REWRITE_PROMPT_ID,
        variables={"organisation_id": "org", "locale": "en-GB"},
    )
    assert record.prompt_id == "hmore.daily_log_rewrite.v1"
    assert record.version == "1.0.0"
    lowered = rendered.lower()
    assert "do not invent" in lowered
    assert "uncertainty" in lowered
    assert "confidence" in lowered
    assert "rewritten_text" in lowered


def test_schema_rejects_empty_text() -> None:
    with pytest.raises(WorkflowError):
        validate_daily_log_rewrite_output({"rewritten_text": "   "})


def test_output_drops_fabricated_sources_and_confidence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.graph.daily_log_rewrite.run_routed_completion",
        lambda **_k: {
            "content": json.dumps(
                {
                    "rewritten_text": "The visit happened. The outcome was unclear.",
                    "confidence": 0.99,
                    "source_refs": ["invented-record"],
                }
            ),
            "provider": "mock",
            "model_id": "mock-model",
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
            "cache_status": "miss",
        },
    )
    result = run_daily_log_rewrite(
        settings=Settings(LLM_PROVIDER="mock", AI_BUDGET_ENFORCEMENT_FAIL_OPEN=True),
        organisation_id=uuid4(),
        text="visit happened. outcome unclear",
        locale="en-GB",
    )
    assert result["rewritten_text"] == "The visit happened. The outcome was unclear."
    assert result["prompt_id"] == DAILY_LOG_REWRITE_PROMPT_ID
    assert "source_refs" not in result
    assert "confidence" not in result
    assert "confidence_kind" not in result


def test_missing_model_is_unavailable_not_a_fake_rewrite() -> None:
    with pytest.raises(WorkflowError) as exc:
        run_daily_log_rewrite(
            settings=Settings(LLM_PROVIDER="none", AI_BUDGET_ENFORCEMENT_FAIL_OPEN=True),
            organisation_id=uuid4(),
            text="Maybe the appointment was missed.",
        )
    assert exc.value.status_code == 503


def test_execute_workflow_reports_unavailable_without_a_model() -> None:
    settings = Settings(LLM_PROVIDER="none", AI_BUDGET_ENFORCEMENT_FAIL_OPEN=True, AI_SERVICE_TOKEN="t")
    ctx = TrustedCallerContext(
        organisation_id=uuid4(),
        user_id=uuid4(),
        role="support_worker",
        features=frozenset({"ai.workflow.execute"}),
    )
    with pytest.raises(WorkflowError) as exc:
        execute_workflow(
            workflow_id="daily_log_rewrite",
            ctx=ctx,
            settings=settings,
            input_payload={"text": "Note text", "locale": "en-GB"},
        )
    assert exc.value.status_code == 503
