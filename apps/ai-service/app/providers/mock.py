from __future__ import annotations

import uuid

from app.providers.base import LlmRequest, LlmResponse, LlmUsage


class MockLlmProvider:
    """Explicit test/dev mock. Never used unless LLM_PROVIDER=mock."""

    name = "mock"

    def is_available(self) -> bool:
        return True

    def complete(self, request: LlmRequest) -> LlmResponse:
        last = request.messages[-1].content if request.messages else ""
        return LlmResponse(
            provider=self.name,
            model=request.model or "mock-model",
            content=f"[mock] {last}",
            usage=LlmUsage(prompt_tokens=None, completion_tokens=None, total_tokens=None),
            provider_request_id=str(uuid.uuid4()),
            raw={"mocked": True},
        )
