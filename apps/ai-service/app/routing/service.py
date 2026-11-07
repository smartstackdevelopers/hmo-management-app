from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.routing.policy import EscalationPolicy, RoutingRequest, maybe_escalate, select_initial
from app.routing.registry import ModelRegistry, build_default_registry, parse_models_json
from app.routing.models import RoutingDecision


def build_registry(settings: Settings) -> ModelRegistry:
    configured = parse_models_json(settings.ai_model_registry_json)
    if configured:
        return ModelRegistry(configured)
    return build_default_registry(
        provider=settings.llm_provider,
        low_model=settings.openai_model or "gpt-4o-mini",
        premium_model=settings.ai_premium_model_id or None,
    )


def escalation_policy(settings: Settings) -> EscalationPolicy:
    return EscalationPolicy(
        enabled=settings.ai_escalation_enabled,
        max_attempts=settings.ai_escalation_max_attempts,
        on_empty_output=settings.ai_escalate_on_empty_output,
        on_validation_failure=settings.ai_escalate_on_validation_failure,
    )


@lru_cache
def get_model_registry() -> ModelRegistry:
    return build_registry(get_settings())


def reset_registry_cache() -> None:
    get_model_registry.cache_clear()


def route_for_workflow(
    settings: Settings,
    *,
    workflow_id: str,
    required_capabilities: frozenset[str] | None = None,
    quality_requirement: str | None = None,
) -> RoutingDecision:
    registry = build_registry(settings)
    return select_initial(
        registry,
        default_low_cost_key=settings.ai_default_model_key,
        request=RoutingRequest(
            workflow_id=workflow_id,
            required_capabilities=required_capabilities or frozenset({"chat"}),
            quality_requirement=quality_requirement,
        ),
    )


def escalate_if_needed(
    settings: Settings,
    previous: RoutingDecision,
    *,
    validation_failed: bool = False,
    empty_output: bool = False,
) -> RoutingDecision | None:
    registry = build_registry(settings)
    return maybe_escalate(
        registry,
        policy=escalation_policy(settings),
        previous=previous,
        validation_failed=validation_failed,
        empty_output=empty_output,
    )
