"""AI personal development assistant client."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings

logger = logging.getLogger("hmore.tenant_engagement.ai_client")


def suggest_development(
    settings: Settings,
    *,
    organisation_id: UUID,
    user_id: UUID,
    role: str,
    prompt: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    base = (settings.ai_service_base_url or "").strip()
    token = (settings.ai_service_token or "").strip()
    if not base or not token:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is not configured")
    url = f"{base.rstrip('/')}/api/v1/workflows/execute"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-HMore-Organisation-Id": str(organisation_id),
        "X-HMore-User-Id": str(user_id),
        "X-HMore-Role": role,
        "X-HMore-Features": "ai.workflow.execute",
    }
    body = {
        "workflow_id": "tenant_engagement",
        "message": "tenant_engagement",
        "input_payload": {"prompt": prompt, "context": context, "no_clinical_or_housing_decisions": True},
    }
    try:
        with httpx.Client(timeout=settings.ai_service_timeout_seconds) as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("tenant_engagement_ai_unreachable error=%s", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is unavailable") from exc
    if response.status_code >= 400:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="AI service rejected the request")
    return response.json()
