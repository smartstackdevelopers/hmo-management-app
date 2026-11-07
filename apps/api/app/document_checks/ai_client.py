"""Call the shared AI service only for gap explanations. Never sends the original file."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings

logger = logging.getLogger("hmore.document_checks.ai_client")


def explain_gaps(
    settings: Settings,
    *,
    organisation_id: UUID,
    user_id: UUID,
    role: str,
    findings: list[dict[str, Any]],
    excerpt: str,
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
    body = {
        "workflow_id": "document_check",
        "message": "document_check",
        "input_payload": {
            "findings": [
                {"code": item.get("code"), "outcome": item.get("outcome"), "title": item.get("title")}
                for item in findings
            ],
            "excerpt": excerpt[:1500],
        },
    }
    try:
        with httpx.Client(timeout=settings.ai_service_timeout_seconds) as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("document_check_ai_unreachable error=%s", type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service unreachable") from exc
    if response.status_code == 402:
        detail = response.json() if response.content else {}
        raise HTTPException(
            status_code=402,
            detail=detail.get("detail") or {"error": "ai_budget_exceeded", "message": "Organisation AI usage limit has been reached"},
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail="Document check AI analysis failed")
    return response.json()
