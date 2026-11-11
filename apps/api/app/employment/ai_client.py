"""Optional CV wording assist via the shared AI gateway.

Never invents employment facts. Callers must require human approval before saving.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.tenancy.context import OrganisationContext

logger = logging.getLogger("hmore.employment.ai_client")


def rewrite_cv_text(
    session,
    ctx: OrganisationContext,
    *,
    original_text: str,
    field: str,
) -> str:
    settings = get_settings()
    base = (getattr(settings, "ai_service_base_url", None) or "").strip()
    token = (settings.ai_service_token or "").strip()
    if not base or not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI CV assistance is unavailable",
        )

    try:
        from app.ai_feature_flags.service import require_feature_available
        from app.ai_usage.features import FEATURE_CV_WORDING

        require_feature_available(session, ctx, FEATURE_CV_WORDING)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        # Feature not registered in this environment — still allow gateway attempt.
        pass

    url = f"{base.rstrip('/')}/api/v1/workflows/execute"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-HMore-Organisation-Id": str(ctx.organisation_id),
        "X-HMore-User-Id": str(ctx.user_id),
        "X-HMore-Role": ctx.role.value if ctx.role else "tenant",
        "X-HMore-Features": "ai.workflow.execute,ai.foundation",
    }
    body: dict[str, Any] = {
        "workflow_id": "cv_wording_assist",
        "message": "cv_wording_assist",
        "require_human_gate": True,
        "input_payload": {
            "field": field,
            "text": original_text,
            "rules": [
                "Improve clarity and grammar only.",
                "Do not invent jobs, employers, dates, qualifications, certificates or achievements.",
                "Do not add skills that are not already stated.",
            ],
        },
    }
    try:
        with httpx.Client(timeout=getattr(settings, "ai_service_timeout_seconds", 60.0)) as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("cv_wording ai unreachable: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI CV assistance is unavailable",
        ) from exc

    if response.status_code == 402:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="AI usage limit reached")
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI CV assistance is unavailable",
        )
    payload = response.json() if response.content else {}
    # Accept a few common response shapes.
    if isinstance(payload, dict):
        for key in ("suggested_text", "rewritten_text", "text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        output = payload.get("output") or payload.get("result") or {}
        if isinstance(output, dict):
            for key in ("suggested_text", "rewritten_text", "text"):
                value = output.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI CV assistance returned no usable suggestion",
    )
