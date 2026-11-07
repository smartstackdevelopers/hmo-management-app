"""Call the shared AI service case_summary workflow."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings

logger = logging.getLogger("hmore.case_summaries.ai_client")


def execute_case_summary(settings: Settings, *, organisation_id: UUID, user_id: UUID, role: str, packet: dict[str, Any]) -> dict[str, Any]:
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
    body = {
        "workflow_id": "case_summary",
        "message": "case_summary",
        "input_payload": {"packet": packet},
    }
    try:
        with httpx.Client(timeout=settings.ai_service_timeout_seconds) as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("case_summary_ai_unreachable error=%s", type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service unreachable") from exc
    if response.status_code == 402:
        detail = response.json() if response.content else {}
        raise HTTPException(status_code=402, detail=detail.get("detail") or {"error": "ai_budget_exceeded", "message": "Organisation AI usage limit has been reached"})
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail="Case summary generation failed")
    return response.json()
