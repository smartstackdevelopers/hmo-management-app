from __future__ import annotations

from dataclasses import dataclass

from app.routing.models import ModelTier, RoutingDecision
from app.routing.registry import ModelRegistry


@dataclass(frozen=True, slots=True)
class EscalationPolicy:
    enabled: bool
    max_attempts: int
    on_empty_output: bool
    on_validation_failure: bool
    require_capability: str | None = None


@dataclass(frozen=True, slots=True)
class RoutingRequest:
    workflow_id: str
    required_capabilities: frozenset[str]
    force_premium: bool = False
    quality_requirement: str | None = None  # "standard" | "high"


def select_initial(
    registry: ModelRegistry,
    *,
    default_low_cost_key: str,
    request: RoutingRequest,
) -> RoutingDecision:
    if request.force_premium or request.quality_requirement == "high":
        premiums = registry.list_enabled(tier=ModelTier.premium)
        if not premiums:
            # Do not silently invent premium — fall back to low-cost with reason.
            low = registry.default_low_cost(default_low_cost_key)
            return RoutingDecision(
                selected_key=low.key,
                provider=low.provider,
                model_id=low.model_id,
                tier=low.tier,
                reason="premium_requested_but_unavailable_using_low_cost",
            )
        chosen = premiums[0]
        return RoutingDecision(
            selected_key=chosen.key,
            provider=chosen.provider,
            model_id=chosen.model_id,
            tier=chosen.tier,
            reason="quality_requirement_high",
        )

    low = registry.default_low_cost(default_low_cost_key)
    if request.required_capabilities and not request.required_capabilities.issubset(low.capabilities):
        # Prefer an eligible model that covers capabilities without inventing ones.
        for model in registry.list_enabled():
            if request.required_capabilities.issubset(model.capabilities):
                return RoutingDecision(
                    selected_key=model.key,
                    provider=model.provider,
                    model_id=model.model_id,
                    tier=model.tier,
                    reason="capability_match",
                )
    return RoutingDecision(
        selected_key=low.key,
        provider=low.provider,
        model_id=low.model_id,
        tier=low.tier,
        reason="low_cost_default",
    )


def maybe_escalate(
    registry: ModelRegistry,
    *,
    policy: EscalationPolicy,
    previous: RoutingDecision,
    validation_failed: bool,
    empty_output: bool,
) -> RoutingDecision | None:
    if not policy.enabled:
        return None
    if previous.escalation_attempt >= policy.max_attempts:
        return None
    if previous.tier == ModelTier.premium:
        return None  # already premium — no further escalation loop

    justified = False
    reason = ""
    if validation_failed and policy.on_validation_failure:
        justified = True
        reason = "structured_output_validation_failed"
    elif empty_output and policy.on_empty_output:
        justified = True
        reason = "empty_output"
    if not justified:
        return None

    premiums = registry.list_enabled(tier=ModelTier.premium)
    if not premiums:
        return None
    chosen = premiums[0]
    if policy.require_capability and policy.require_capability not in chosen.capabilities:
        return None
    return RoutingDecision(
        selected_key=chosen.key,
        provider=chosen.provider,
        model_id=chosen.model_id,
        tier=chosen.tier,
        reason=reason,
        escalated_from=previous.selected_key,
        escalation_attempt=previous.escalation_attempt + 1,
    )
