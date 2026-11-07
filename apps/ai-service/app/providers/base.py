from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class LlmMessage:
    role: str
    content: str


@dataclass(slots=True)
class LlmRequest:
    model: str
    messages: list[LlmMessage]
    timeout_seconds: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LlmUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(slots=True)
class LlmResponse:
    provider: str
    model: str
    content: str
    usage: LlmUsage
    provider_request_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class LlmProvider(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def complete(self, request: LlmRequest) -> LlmResponse: ...
