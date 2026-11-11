"""Optional AI explanation via shared LangGraph gateway (FEATURE_JOB_MATCHING)."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.tenancy.context import OrganisationContext

logger = logging.getLogger("hmore.job_matching.ai_client")


def explain_job_match(
    session,
    ctx: OrganisationContext,
    *,
    job: dict[str, Any],
    profile_summary: dict[str, Any],
    match: dict[str, Any],
    question: str | None = None,
) -> str:
    settings = get_settings()
    base = (getattr(settings, "ai_service_base_url", None) or "").strip()
    token = (settings.ai_service_token or "").strip()
    if not base or not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI job matching explanation is unavailable",
        )

    from app.ai_feature_flags.service import require_feature_available
    from app.ai_usage.features import FEATURE_JOB_MATCHING

    require_feature_available(session, ctx, FEATURE_JOB_MATCHING)

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
        "workflow_id": "job_match_explain",
        "message": "job_match_explain",
        "require_human_gate": True,
        "input_payload": {
            "job": job,
            "profile_summary": profile_summary,
            "match": match,
            "question": question,
            "rules": [
                "Explain using only the provided job and profile facts.",
                "Never invent vacancies, employers, salaries, requirements or qualifications.",
                "Never claim the tenant is guaranteed a job.",
                "Never submit an application.",
                "Identify suggestions clearly as suggestions.",
            ],
        },
    }
    try:
        with httpx.Client(timeout=getattr(settings, "ai_service_timeout_seconds", 60.0)) as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("job_match_explain unreachable: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI job matching explanation is unavailable",
        ) from exc

    if response.status_code == 402:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="AI usage limit reached")
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI job matching explanation is unavailable",
        )
    payload = response.json() if response.content else {}
    if isinstance(payload, dict):
        for key in ("explanation", "text", "suggested_text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        result = payload.get("result") or payload.get("output") or {}
        if isinstance(result, dict):
            for key in ("explanation", "text", "suggested_text"):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI job matching explanation returned no usable text",
    )
