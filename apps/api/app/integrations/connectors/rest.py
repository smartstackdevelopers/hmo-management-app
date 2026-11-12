"""Reusable REST connector with auth, timeout, retry, and rate-limit handling."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.integrations.connectors.base import ConnectionTestResult


class RestConnectorError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def _require_https(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        # Allow http only for localhost test harnesses
        host = (parsed.hostname or "").lower()
        if host not in {"localhost", "127.0.0.1", "::1"}:
            raise RestConnectorError("External integration URLs must use HTTPS")


def build_auth_headers(auth_type: str, credentials: dict[str, str], config: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if auth_type == "none":
        return headers
    if auth_type == "api_key":
        header_name = str(config.get("api_key_header") or "X-API-Key")
        key = credentials.get("api_key")
        if not key:
            raise RestConnectorError("api_key credential required")
        headers[header_name] = key
        return headers
    if auth_type == "bearer":
        token = credentials.get("bearer_token")
        if not token:
            raise RestConnectorError("bearer_token credential required")
        headers["Authorization"] = f"Bearer {token}"
        return headers
    if auth_type == "oauth2":
        # Foundation: use provided bearer/access token; full OAuth dance is future work.
        token = credentials.get("bearer_token") or credentials.get("refresh_token")
        if not token:
            raise RestConnectorError("OAuth2 requires bearer_token (or configured access token)")
        headers["Authorization"] = f"Bearer {token}"
        # Keep client_id in non-secret config; client_secret stays encrypted only.
        if config.get("oauth_client_id"):
            headers["X-OAuth-Client-Id"] = str(config["oauth_client_id"])
        return headers
    raise RestConnectorError(f"Unsupported auth_type: {auth_type}")


def request_json(
    *,
    method: str,
    base_url: str,
    path: str = "",
    auth_type: str = "none",
    credentials: dict[str, str] | None = None,
    config: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout_seconds: float = 10.0,
    max_retries: int = 2,
) -> tuple[int, Any, int]:
    """Perform JSON HTTP request with basic retry on 429/5xx. Returns (status, body, latency_ms)."""
    credentials = credentials or {}
    config = config or {}
    if not base_url:
        raise RestConnectorError("api_base_url is required")
    _require_https(base_url)
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/")) if path else base_url
    headers = build_auth_headers(auth_type, credentials, config)
    attempt = 0
    last_error: Exception | None = None
    while attempt <= max_retries:
        attempt += 1
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
                response = client.request(method.upper(), url, headers=headers, params=params, json=json_body)
            latency_ms = int((time.perf_counter() - started) * 1000)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt <= max_retries:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else min(2**attempt, 8)
                    time.sleep(delay)
                    continue
                raise RestConnectorError(
                    f"Upstream error {response.status_code}",
                    status_code=response.status_code,
                    retryable=True,
                )
            if response.status_code >= 400:
                raise RestConnectorError(
                    f"Upstream rejected request ({response.status_code})",
                    status_code=response.status_code,
                    retryable=False,
                )
            if not response.content:
                return response.status_code, None, latency_ms
            try:
                return response.status_code, response.json(), latency_ms
            except ValueError as exc:
                raise RestConnectorError("Invalid JSON response from upstream") from exc
        except httpx.TimeoutException as exc:
            last_error = RestConnectorError("Connection timed out", retryable=True)
            if attempt <= max_retries:
                time.sleep(min(2**attempt, 8))
                continue
            raise last_error from exc
        except httpx.HTTPError as exc:
            last_error = RestConnectorError(f"HTTP error: {exc}", retryable=True)
            if attempt <= max_retries:
                time.sleep(min(2**attempt, 8))
                continue
            raise last_error from exc
    raise last_error or RestConnectorError("Request failed")


def health_check_url(
    *,
    base_url: str | None,
    auth_type: str,
    credentials: dict[str, str],
    config: dict[str, Any],
    timeout_seconds: float = 10.0,
) -> ConnectionTestResult:
    if not base_url:
        return ConnectionTestResult(
            ok=False,
            status="not_configured",
            detail="api_base_url is required for a live connection test",
        )
    path = str(config.get("health_path") or "/health")
    try:
        status_code, _body, latency = request_json(
            method="GET",
            base_url=base_url,
            path=path,
            auth_type=auth_type,
            credentials=credentials,
            config=config,
            timeout_seconds=timeout_seconds,
            max_retries=1,
        )
        return ConnectionTestResult(
            ok=True,
            status="connected",
            detail=f"Health check succeeded ({status_code})",
            http_status=status_code,
            latency_ms=latency,
        )
    except RestConnectorError as exc:
        return ConnectionTestResult(
            ok=False,
            status="failed",
            detail=str(exc),
            http_status=exc.status_code,
        )
