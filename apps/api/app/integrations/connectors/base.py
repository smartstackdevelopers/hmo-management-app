"""Provider adapter protocol for Integration Hub connectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ConnectionTestResult:
    ok: bool
    status: str  # connected | failed | not_configured
    detail: str
    http_status: int | None = None
    latency_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncResult:
    success_count: int = 0
    failure_count: int = 0
    detail: str = ""
    records: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@runtime_checkable
class ProviderAdapter(Protocol):
    provider_key: str
    category: str

    def test_connection(
        self,
        *,
        base_url: str | None,
        auth_type: str,
        config: dict[str, Any],
        credentials: dict[str, str],
        timeout_seconds: float,
    ) -> ConnectionTestResult: ...

    def health_sync(
        self,
        *,
        base_url: str | None,
        auth_type: str,
        config: dict[str, Any],
        credentials: dict[str, str],
        timeout_seconds: float,
    ) -> SyncResult: ...
