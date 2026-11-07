from __future__ import annotations

from typing import Any
from uuid import UUID

from app.cache.service import get_cache_service
from app.core.config import Settings
from app.core.errors import ProviderError, WorkflowError
from app.providers.base import LlmMessage, LlmRequest
from app.providers.factory import get_llm_provider
from app.providers.mock import MockLlmProvider
from app.routing.models import RoutingDecision
from app.routing.service import escalate_if_needed, route_for_workflow


def _provider_for_decision(settings: Settings, decision: RoutingDecision):
    """Bind provider using registry decision — never invent a silent fake for openai."""
    if decision.provider == "mock" or settings.llm_provider == "mock":
        return MockLlmProvider()
    provider = get_llm_provider(settings)
    if provider is None:
        raise ProviderError("No LLM provider configured for routed completion")
    if settings.llm_provider != "none" and decision.provider not in {settings.llm_provider, "mock"}:
        # Registry provider must match configured runtime provider family.
        raise ProviderError(
            f"Model provider '{decision.provider}' is not active (LLM_PROVIDER={settings.llm_provider})"
        )
    return provider


def run_routed_completion(
    *,
    settings: Settings,
    organisation_id: UUID,
    workflow_id: str,
    prompt_id: str,
    prompt_version: str,
    rendered_prompt: str,
    user_message: str,
    quality_requirement: str | None = None,
    cache_eligible: bool = True,
) -> dict[str, Any]:
    decision = route_for_workflow(
        settings,
        workflow_id=workflow_id,
        quality_requirement=quality_requirement,
    )
    cache = get_cache_service(settings)

    def _call(current: RoutingDecision) -> dict[str, Any]:
        provider = _provider_for_decision(settings, current)
        response = provider.complete(
            LlmRequest(
                model=current.model_id,
                messages=[
                    LlmMessage(role="system", content=rendered_prompt[:8000]),
                    LlmMessage(role="user", content=user_message[:4000]),
                ],
                timeout_seconds=settings.llm_timeout_seconds,
            )
        )
        return {
            "content": response.content,
            "provider": response.provider,
            "model_id": response.model,
            "provider_request_id": response.provider_request_id,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "routing": current.model_dump(),
        }

    fingerprint = {
        "msg_sha": __import__("hashlib").sha256(user_message.encode("utf-8")).hexdigest(),
        "quality": quality_requirement or "standard",
    }

    def compute() -> dict[str, Any]:
        first = _call(decision)
        empty = not (first.get("content") or "").strip()
        # Simple structural validation: require non-empty printable content.
        validation_failed = empty
        escalated = escalate_if_needed(
            settings,
            decision,
            validation_failed=validation_failed,
            empty_output=empty,
        )
        if escalated is None:
            first["escalation"] = None
            return first
        second = _call(escalated)
        second["escalation"] = {
            "from": decision.selected_key,
            "to": escalated.selected_key,
            "reason": escalated.reason,
            "attempt": escalated.escalation_attempt,
        }
        return second

    try:
        payload, cache_status = cache.get_or_compute(
            organisation_id=organisation_id,
            workflow_id=workflow_id,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            provider=decision.provider,
            model_id=decision.model_id,
            input_fingerprint=fingerprint,
            eligible=cache_eligible,
            compute=compute,
        )
    except ProviderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise WorkflowError("Routed completion failed", status_code=500) from exc

    payload = dict(payload)
    payload["cache_status"] = cache_status
    return payload
