"""Integration connector interfaces and provider adapters."""

from app.integrations.connectors.adapters import ADAPTERS, get_adapter
from app.integrations.connectors.base import ConnectionTestResult, ProviderAdapter, SyncResult
from app.integrations.connectors.rest import RestConnectorError, request_json

__all__ = [
    "ADAPTERS",
    "ConnectionTestResult",
    "ProviderAdapter",
    "RestConnectorError",
    "SyncResult",
    "get_adapter",
    "request_json",
]
