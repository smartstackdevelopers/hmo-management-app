"""Expo Push API client.

A ticket with status ``ok`` means Expo accepted the message. It is not evidence
that a device displayed it. Log mode never calls Expo and never reports sent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from app.core.config import Settings

logger = logging.getLogger("hmore.push.expo")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
PUSH_TITLE = "HMore"
PUSH_BODY = "You have a new notification. Open the app to read it."
DATA_KEYS = ("related_resource_type", "related_resource_id", "message_id")

HttpPost = Callable[[str, dict[str, Any], dict[str, str]], dict[str, Any]]


@dataclass(frozen=True)
class ExpoPushOutcome:
    """Result of one send attempt. ``sent`` is true only for an Expo ticket status of ok."""

    sent: bool
    provider: str
    ticket_id: str | None
    error: str | None
    deactivate_device: bool


def adapter_is_expo(settings: Settings) -> bool:
    mode = (settings.push_adapter_mode or "log").strip().lower()
    token = (settings.expo_access_token or "").strip()
    return mode == "expo" and bool(token)


def build_expo_payload(*, to_token: str, data: dict[str, str]) -> dict[str, Any]:
    """Title and body are fixed. Data is limited to routing ids."""
    safe_data = {key: str(data.get(key) or "")[:64] for key in DATA_KEYS}
    return {
        "to": to_token,
        "title": PUSH_TITLE,
        "body": PUSH_BODY,
        "data": safe_data,
        "sound": "default",
    }


def _default_http_post(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        body = response.json()
    if not isinstance(body, dict):
        raise ValueError("expo_response_not_object")
    return body


def _ticket(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, list):
        data = data[0] if data else {}
    if isinstance(data, dict):
        return data
    return {}


def _should_deactivate(error: str) -> bool:
    compact = error.replace("_", "").replace(" ", "").lower()
    return "devicenotregistered" in compact or "invalidexpopushtoken" in compact


def send_expo_push(
    *,
    settings: Settings,
    to_token: str,
    data: dict[str, str],
    http_post: HttpPost | None = None,
) -> ExpoPushOutcome:
    if not adapter_is_expo(settings):
        return ExpoPushOutcome(
            sent=False,
            provider="log",
            ticket_id=None,
            error="provider_not_configured: not_sent_provider_unconfigured",
            deactivate_device=False,
        )

    payload = build_expo_payload(to_token=to_token, data=data)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.expo_access_token}",
    }
    post = http_post or _default_http_post
    try:
        raw = post(EXPO_PUSH_URL, payload, headers)
    except Exception:
        logger.info("expo_push_http_failed")
        return ExpoPushOutcome(
            sent=False,
            provider="expo",
            ticket_id=None,
            error="expo_http_error",
            deactivate_device=False,
        )

    if raw.get("errors"):
        return ExpoPushOutcome(
            sent=False,
            provider="expo",
            ticket_id=None,
            error="expo_request_error",
            deactivate_device=False,
        )

    ticket = _ticket(raw)
    status = str(ticket.get("status") or "")
    if status == "ok" and ticket.get("id"):
        return ExpoPushOutcome(
            sent=True,
            provider="expo",
            ticket_id=str(ticket["id"])[:255],
            error=None,
            deactivate_device=False,
        )
    if status == "ok":
        return ExpoPushOutcome(
            sent=False,
            provider="expo",
            ticket_id=None,
            error="expo_ticket_missing_id",
            deactivate_device=False,
        )

    details = ticket.get("details") if isinstance(ticket.get("details"), dict) else {}
    error = str(details.get("error") or ticket.get("message") or "expo_error")[:500]
    return ExpoPushOutcome(
        sent=False,
        provider="expo",
        ticket_id=None,
        error=error,
        deactivate_device=_should_deactivate(error),
    )
