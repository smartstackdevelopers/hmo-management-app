"""S2S client from core API to the shared AI service (F3.4)."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx

from app.core.config import Settings
from fastapi import HTTPException, status

logger = logging.getLogger("hmore.notes_analysis.ai_client")


def execute_notes_analysis_workflow(
    settings: Settings,
    *,
    organisation_id: UUID,
    user_id: UUID,
    role: str,
    note_payload: dict[str, Any],
) -> dict[str, Any]:
    base = (getattr(settings, "ai_service_base_url", None) or "").strip()
    token = (settings.ai_service_token or "").strip()
    if not base:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI_SERVICE_BASE_URL is not configured",
        )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI_SERVICE_TOKEN is not configured",
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
        "workflow_id": "notes_analysis",
        "message": "notes_analysis",
        "require_human_gate": False,
        "input_payload": {"note": note_payload},
    }
    try:
        with httpx.Client(timeout=getattr(settings, "ai_service_timeout_seconds", 60.0)) as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("ai_service_unreachable error=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service unreachable",
        ) from exc

    if response.status_code == 402:
        detail = response.json() if response.content else {}
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=detail.get("detail")
            or {
                "error": "ai_budget_exceeded",
                "message": "Organisation AI usage limit has been reached",
            },
        )
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:  # noqa: BLE001
            detail = {"message": response.text[:300]}
        raise HTTPException(status_code=response.status_code, detail=detail)

    return response.json()
