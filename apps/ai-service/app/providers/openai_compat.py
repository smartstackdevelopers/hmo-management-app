from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.errors import ProviderError
from app.providers.base import LlmMessage, LlmRequest, LlmResponse, LlmUsage


class OpenAICompatibleProvider:
    """OpenAI-compatible chat completions. Requires a real API key — no silent fakes."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> None:
        if not api_key.strip():
            raise ProviderError("OPENAI_API_KEY is not configured")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout = timeout_seconds
        self._max_retries = max(0, max_retries)

    def is_available(self) -> bool:
        return bool(self._api_key)

    def complete(self, request: LlmRequest) -> LlmResponse:
        model = request.model or self._default_model
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"
        timeout = request.timeout_seconds or self._timeout
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(url, json=payload, headers=headers)
                if response.status_code == 429:
                    last_error = ProviderError("LLM provider rate limited")
                    time.sleep(min(2**attempt, 4))
                    continue
                if response.status_code >= 500:
                    last_error = ProviderError("LLM provider unavailable")
                    time.sleep(min(2**attempt, 4))
                    continue
                if response.status_code >= 400:
                    raise ProviderError("LLM provider rejected the request", status_code=502)
                data: dict[str, Any] = response.json()
                content = data["choices"][0]["message"]["content"]
                usage_raw = data.get("usage") or {}
                return LlmResponse(
                    provider=self.name,
                    model=data.get("model", model),
                    content=content,
                    usage=LlmUsage(
                        prompt_tokens=usage_raw.get("prompt_tokens"),
                        completion_tokens=usage_raw.get("completion_tokens"),
                        total_tokens=usage_raw.get("total_tokens"),
                    ),
                    provider_request_id=response.headers.get("x-request-id") or data.get("id"),
                    raw={"id": data.get("id")},
                )
            except ProviderError:
                raise
            except httpx.TimeoutException as exc:
                last_error = ProviderError("LLM provider timeout")
                if attempt >= self._max_retries:
                    raise last_error from exc
            except Exception as exc:  # noqa: BLE001
                last_error = ProviderError("LLM provider request failed")
                if attempt >= self._max_retries:
                    raise last_error from exc
        raise last_error or ProviderError("LLM provider request failed")
