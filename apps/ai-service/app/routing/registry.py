from __future__ import annotations

import json
from typing import Iterable

from app.core.errors import ValidationServiceError, WorkflowError
from app.routing.models import ModelConfig, ModelTier


class ModelRegistry:
    def __init__(self, models: Iterable[ModelConfig]) -> None:
        self._models = {m.key: m for m in models}
        if not self._models:
            raise ValidationServiceError("Model registry is empty")

    def get(self, key: str) -> ModelConfig:
        model = self._models.get(key)
        if not model:
            raise WorkflowError(f"Unknown model key '{key}'", status_code=404)
        if not model.enabled:
            raise WorkflowError(f"Model '{key}' is disabled", status_code=503)
        return model

    def list_enabled(self, *, tier: ModelTier | None = None) -> list[ModelConfig]:
        items = [m for m in self._models.values() if m.enabled and m.routing_eligible]
        if tier is not None:
            items = [m for m in items if m.tier == tier]
        return sorted(items, key=lambda m: m.key)

    def default_low_cost(self, default_key: str) -> ModelConfig:
        model = self.get(default_key)
        if model.tier != ModelTier.low_cost:
            raise ValidationServiceError("Default model must be low_cost tier")
        return model

    def summaries(self) -> list[dict]:
        return [
            {
                "key": m.key,
                "provider": m.provider,
                "model_id": m.model_id,
                "tier": m.tier.value,
                "enabled": m.enabled,
                "capabilities": sorted(m.capabilities),
                "routing_eligible": m.routing_eligible,
            }
            for m in sorted(self._models.values(), key=lambda x: x.key)
        ]


def parse_models_json(raw: str) -> list[ModelConfig]:
    """Parse AI_MODEL_REGISTRY_JSON. Empty → built-in registry from provider settings."""
    text = (raw or "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationServiceError("AI_MODEL_REGISTRY_JSON is not valid JSON") from exc
    if not isinstance(data, list):
        raise ValidationServiceError("AI_MODEL_REGISTRY_JSON must be a JSON array")
    models: list[ModelConfig] = []
    for item in data:
        caps = item.get("capabilities") or []
        models.append(
            ModelConfig(
                key=item["key"],
                provider=item["provider"],
                model_id=item["model_id"],
                tier=ModelTier(item["tier"]),
                enabled=bool(item.get("enabled", True)),
                capabilities=frozenset(caps),
                max_context_tokens=item.get("max_context_tokens"),
                max_output_tokens=item.get("max_output_tokens"),
                timeout_seconds=item.get("timeout_seconds"),
                routing_eligible=bool(item.get("routing_eligible", True)),
                deployment_scope=item.get("deployment_scope", "all"),
            )
        )
    return models


def build_default_registry(*, provider: str, low_model: str, premium_model: str | None) -> ModelRegistry:
    """Built-in registry when no JSON configured — uses configured provider ids only."""
    models = [
        ModelConfig(
            key="default_low_cost",
            provider=provider if provider != "none" else "mock",
            model_id=low_model,
            tier=ModelTier.low_cost,
            enabled=True,
            capabilities=frozenset({"chat", "text"}),
        )
    ]
    if premium_model:
        models.append(
            ModelConfig(
                key="default_premium",
                provider=provider if provider != "none" else "mock",
                model_id=premium_model,
                tier=ModelTier.premium,
                enabled=True,
                capabilities=frozenset({"chat", "text", "structured"}),
            )
        )
    return ModelRegistry(models)
