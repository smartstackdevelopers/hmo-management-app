"""Core API budget reservation / reconciliation client (F3.3).

All billable AI executions must reserve budget through the core API before
dispatch. Hard-cap rejections are surfaced visibly to callers.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx

from app.core.config import Settings
from app.core.errors import AiServiceError

logger = logging.getLogger("hmore.ai.budget")


class BudgetExceededError(AiServiceError):
    def __init__(self, message: str, *, detail: dict[str, Any] | None = None) -> None:
        super().__init__("ai_budget_exceeded", message, status_code=402)
        self.detail = detail or {}


class BudgetClientError(AiServiceError):
    def __init__(self, message: str, *, status_code: int = 503) -> None:
        super().__init__("budget_client_error", message, status_code=status_code)


def _headers(settings: Settings) -> dict[str, str]:
    token = settings.ai_service_token.strip()
    if not token:
        raise BudgetClientError("AI_SERVICE_TOKEN is not configured")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def reserve_budget(
    settings: Settings,
    *,
    request_id: str,
    organisation_id: UUID,
    user_id: UUID | None,
    feature_id: str,
    workflow_id: str,
    billable: bool = True,
    cache_hit: bool = False,
) -> dict[str, Any]:
    """Reserve budget via core API. Raises BudgetExceededError on hard cap."""
    if not settings.core_api_base_url.strip():
        if settings.budget_enforcement_fail_open:
            logger.warning("budget_reserve_skipped reason=core_api_unconfigured fail_open=true")
            return {"permitted": True, "status": "skipped", "reason": "core_api_unconfigured"}
        raise BudgetClientError("CORE_API_BASE_URL is required for budget enforcement")

    url = f"{settings.core_api_base_url.rstrip('/')}/api/v1/internal/ai/budget/reserve"
    payload = {
        "request_id": request_id,
        "organisation_id": str(organisation_id),
        "user_id": str(user_id) if user_id else None,
        "feature_id": feature_id,
        "workflow_id": workflow_id,
        "billable": billable,
        "cache_hit": cache_hit,
    }
    try:
        with httpx.Client(timeout=settings.budget_http_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=_headers(settings))
    except httpx.HTTPError as exc:
        if settings.budget_enforcement_fail_open:
            logger.warning("budget_reserve_http_error fail_open=true error=%s", type(exc).__name__)
            return {"permitted": True, "status": "skipped", "reason": "http_error_fail_open"}
        raise BudgetClientError("Budget reservation request failed") from exc

    if response.status_code == 402:
        detail = {}
        try:
            body = response.json()
            detail = body.get("detail") if isinstance(body.get("detail"), dict) else body
        except Exception:  # noqa: BLE001
            detail = {}
        message = (
            (detail or {}).get("message")
            if isinstance(detail, dict)
            else None
        ) or "Organisation AI usage limit has been reached"
        raise BudgetExceededError(message, detail=detail if isinstance(detail, dict) else {})

    if response.status_code >= 400:
        if settings.budget_enforcement_fail_open:
            logger.warning(
                "budget_reserve_rejected status=%s fail_open=true",
                response.status_code,
            )
            return {"permitted": True, "status": "skipped", "reason": "http_status_fail_open"}
        raise BudgetClientError(f"Budget reservation failed ({response.status_code})")

    return response.json()


def reconcile_usage(
    settings: Settings,
    *,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    """Best-effort usage reconcile. Failures are logged; do not invent costs locally."""
    if not settings.core_api_base_url.strip():
        logger.debug("budget_reconcile_skipped reason=core_api_unconfigured")
        return None
    url = f"{settings.core_api_base_url.rstrip('/')}/api/v1/internal/ai/budget/reconcile"
    try:
        with httpx.Client(timeout=settings.budget_http_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=_headers(settings))
        if response.status_code >= 400:
            logger.warning("budget_reconcile_failed status=%s", response.status_code)
            return None
        return response.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("budget_reconcile_error error=%s", type(exc).__name__)
        return None
