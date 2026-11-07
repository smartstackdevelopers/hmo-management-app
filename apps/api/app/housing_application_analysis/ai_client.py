"""Call the shared AI service housing_application_analysis workflow."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings

logger = logging.getLogger("hmore.housing_application_analysis.ai_client")


def explain_gaps(
    settings: Settings,
    *,
    organisation_id: UUID,
    user_id: UUID,
    role: str,
    findings: list[dict[str, Any]],
    application_reference: str,
) -> dict[str, Any]:
    base = (settings.ai_service_base_url or "").strip()
    token = (settings.ai_service_token or "").strip()
    if not base or not token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is not configured")
    url = f"{base.rstrip('/')}/api/v1/workflows/execute"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-HMore-Organisation-Id": str(organisation_id),
        "X-HMore-User-Id": str(user_id),
        "X-HMore-Role": role,
        "X-HMore-Features": "ai.workflow.execute",
    }
    compact = [
        {"code": item.get("code"), "outcome": item.get("outcome"), "title": item.get("title")}
        for item in findings
    ]
    body = {
        "workflow_id": "housing_application_analysis",
        "message": "housing_application_analysis",
        "input_payload": {
            "findings": compact,
            "application_reference": application_reference,
        },
    }
    try:
        with httpx.Client(timeout=settings.ai_service_timeout_seconds) as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("housing_application_ai_unreachable error=%s", type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is unavailable") from exc
    if response.status_code == 402:
        raise HTTPException(status_code=402, detail="AI usage limit reached")
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI service rejected the analysis request")
    return response.json()
