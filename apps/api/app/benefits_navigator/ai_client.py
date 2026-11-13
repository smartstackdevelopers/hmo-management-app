"""AI Gateway client for benefits navigator (optional org flag)."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings

logger = logging.getLogger("hmore.benefits_navigator.ai_client")


def ask_benefits_navigator(
    settings: Settings,
    *,
    organisation_id: UUID,
    user_id: UUID,
    role: str,
    question: str,
    benefit_snippets: list[dict[str, Any]],
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
        "workflow_id": "benefits_navigator",
        "message": "benefits_navigator",
        "input_payload": {
            "question": question,
            "benefit_snippets": benefit_snippets,
            "notice": "Never guarantee eligibility; cite sources.",
        },
    }
    try:
        with httpx.Client(timeout=settings.ai_service_timeout_seconds) as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("benefits_navigator_ai_unreachable error=%s", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is unavailable") from exc
    if response.status_code >= 400:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="AI service rejected the request")
    return response.json()
