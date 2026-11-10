"""S2S client from the core API to the shared AI service (F4.4)."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings

logger = logging.getLogger("hmore.daily_log_rewrite.ai_client")


def execute_daily_log_rewrite(
    settings: Settings,
    *,
    organisation_id: UUID,
    user_id: UUID,
    role: str,
    text: str,
    locale: str = "en-GB",
) -> dict[str, Any]:
    base = (getattr(settings, "ai_service_base_url", None) or "").strip()
    token = (settings.ai_service_token or "").strip()
    if not base:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI rewrite is unavailable because AI_SERVICE_BASE_URL is not configured",
        )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI rewrite is unavailable because AI_SERVICE_TOKEN is not configured",
        )

    url = f"{base.rstrip('/')}/api/v1/workflows/execute"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-HMore-Organisation-Id": str(organisation_id),
        "X-HMore-User-Id": str(user_id),
        "X-HMore-Role": role,
        "X-HMore-Features": "ai.workflow.execute,ai.foundation,ai.routing.read",
    }
    body = {
        "workflow_id": "daily_log_rewrite",
        "message": "daily_log_rewrite",
        "require_human_gate": True,
        "input_payload": {"text": text, "locale": locale},
    }
    try:
        with httpx.Client(timeout=getattr(settings, "ai_service_timeout_seconds", 60.0)) as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("ai_service_unreachable error=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI rewrite is unavailable because the AI service could not be reached",
        ) from exc

    if response.status_code == 402:
        detail = response.json() if response.content else {}
        message = "Organisation AI usage limit has been reached"
        if isinstance(detail, dict):
            nested = detail.get("detail") if isinstance(detail.get("detail"), dict) else detail
            if isinstance(nested, dict) and isinstance(nested.get("message"), str) and nested["message"].strip():
                message = nested["message"].strip()[:300]
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"error": "ai_budget_exceeded", "message": message},
        )
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:  # noqa: BLE001
            detail = {"message": response.text[:300]}
        raise HTTPException(status_code=response.status_code, detail=detail)

    return response.json()
