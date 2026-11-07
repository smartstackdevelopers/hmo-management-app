"""Call shared AI service for report narrative from aggregated metrics only."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings

logger = logging.getLogger("hmore.report_drafts.ai_client")


def generate_narrative(
    settings: Settings,
    *,
    organisation_id: UUID,
    user_id: UUID,
    role: str,
    period_type: str,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    base = (settings.ai_service_base_url or "").strip()
    token = (settings.ai_service_token or "").strip()
    if not base or not token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is not configured")
    # Strip anything that looks like raw rows — only aggregates.
    compact = {
        "period_type": period_type,
        "period_start": metrics.get("period_start"),
        "period_end": metrics.get("period_end"),
        "sections": metrics.get("sections") or {},
        "unavailable": metrics.get("unavailable") or [],
    }
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
        "workflow_id": "report_draft_narrative",
        "message": "report_draft_narrative",
        "input_payload": compact,
    }
    try:
        with httpx.Client(timeout=settings.ai_service_timeout_seconds) as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("report_draft_ai_unreachable error=%s", type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is unavailable") from exc
    if response.status_code == 402:
        raise HTTPException(status_code=402, detail="AI usage limit reached")
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI service rejected report narrative")
    payload = response.json()
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="AI service returned an invalid narrative payload")
    return result
