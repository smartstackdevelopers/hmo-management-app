"""F3.3 unit tests — cost calculation and period helpers (no database)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.ai_usage.cost import calculate_token_cost
from app.ai_usage.features import feature_for_workflow, PLANNED_AGENT_FEATURES
from app.ai_usage.period import period_key_for, previous_period_key


def _pricing(**overrides):
    base = dict(
        provider="openai",
        model_id="gpt-4o-mini",
        pricing_version="v1",
        currency="GBP",
        input_price_per_1k_tokens=Decimal("0.150000"),
        output_price_per_1k_tokens=Decimal("0.600000"),
        effective_from=date(2026, 1, 1),
        effective_to=None,
        active=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_cost_from_verified_pricing() -> None:
    result = calculate_token_cost(
        input_tokens=1000,
        output_tokens=500,
        pricing=_pricing(),
    )
    assert result.cost_status == "actual"
    assert result.amount == Decimal("0.450000")
    assert result.pricing_version == "v1"
    assert result.currency == "GBP"


def test_missing_pricing_unavailable() -> None:
    result = calculate_token_cost(input_tokens=10, output_tokens=10, pricing=None)
    assert result.cost_status == "unavailable"
    assert result.amount is None
    assert result.reason == "pricing_missing"


def test_missing_tokens_unavailable() -> None:
    result = calculate_token_cost(input_tokens=None, output_tokens=10, pricing=_pricing())
    assert result.cost_status == "unavailable"
    assert result.amount is None


def test_cache_hit_not_billed_as_actual() -> None:
    result = calculate_token_cost(
        input_tokens=100,
        output_tokens=100,
        pricing=_pricing(),
        cache_hit=True,
    )
    assert result.cost_status == "unavailable"
    assert result.reason == "cache_hit_no_provider_billing_rule"


def test_decimal_precision() -> None:
    result = calculate_token_cost(
        input_tokens=1,
        output_tokens=1,
        pricing=_pricing(
            input_price_per_1k_tokens=Decimal("0.000001"),
            output_price_per_1k_tokens=Decimal("0.000001"),
        ),
    )
    assert result.cost_status == "actual"
    assert str(result.amount).count(".") == 1


def test_period_helpers() -> None:
    assert previous_period_key("2026-11") == "2026-10"
    assert previous_period_key("2026-01") == "2025-12"
    assert len(period_key_for()) == 7


def test_planned_agent_features_reserved() -> None:
    assert len(PLANNED_AGENT_FEATURES) == 6
    assert feature_for_workflow("foundation_routed_echo") == "ai.infra.routing"
    assert feature_for_workflow("unknown_future") == "ai.infra.unattributed"

