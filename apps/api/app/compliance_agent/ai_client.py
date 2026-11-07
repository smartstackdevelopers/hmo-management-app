"""Call shared AI service compliance_explanation workflow."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings

logger = logging.getLogger("hmore.compliance_agent.ai_client")


def explain_findings(
    settings: Settings,
    *,
    organisation_id: UUID,
    user_id: UUID,
    role: str,
    findings: list[dict[str, Any]],
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
        {
            "rule_id": item.get("rule_id"),
            "result": item.get("result"),
            "title": item.get("title"),
            "module": item.get("module"),
            "rule_source": item.get("rule_source"),
        }
        for item in findings
    ]
    body = {
        "workflow_id": "compliance_explanation",
        "message": "compliance_explanation",
        "input_payload": {"findings": compact},
    }
    try:
        with httpx.Client(timeout=settings.ai_service_timeout_seconds) as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("compliance_ai_unreachable error=%s", type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is unavailable") from exc
    if response.status_code == 402:
        raise HTTPException(status_code=402, detail="AI usage limit reached")
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI service rejected the explanation request")
    return response.json()
