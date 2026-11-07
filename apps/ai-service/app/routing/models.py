from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ModelTier(str, Enum):
    low_cost = "low_cost"
    premium = "premium"


class ModelConfig(BaseModel):
    """Configured, operator-approved model entry — no invented pricing."""

    key: str
    provider: str
    model_id: str
    tier: ModelTier
    enabled: bool = True
    capabilities: frozenset[str] = Field(default_factory=frozenset)
    max_context_tokens: int | None = None
    max_output_tokens: int | None = None
    timeout_seconds: float | None = None
    routing_eligible: bool = True
    deployment_scope: str = "all"

    model_config = {"frozen": True, "arbitrary_types_allowed": True}


class RoutingDecision(BaseModel):
    selected_key: str
    provider: str
    model_id: str
    tier: ModelTier
    reason: str
    escalated_from: str | None = None
    escalation_attempt: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
