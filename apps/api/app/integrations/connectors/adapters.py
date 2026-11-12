"""Stub provider adapters for Council / HR / Finance / Community categories.

These adapters implement the foundation contract. They do not invent live partner
endpoints. A connection is only marked connected after a real successful HTTPS
health check against the configured base URL.
"""

from __future__ import annotations

from typing import Any

from app.integrations.connectors.base import ConnectionTestResult, SyncResult
from app.integrations.connectors.rest import health_check_url


class _GenericRestAdapter:
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
    ) -> ConnectionTestResult:
        if auth_type != "none" and not credentials and auth_type != "oauth2":
            # oauth2 may still fail inside health check without token
            if auth_type in {"api_key", "bearer"} and not credentials:
                return ConnectionTestResult(
                    ok=False,
                    status="not_configured",
                    detail="Credentials are required before a connection test",
                )
        if auth_type == "oauth2":
            # Validate OAuth configuration shape without claiming a token exchange succeeded
            if not config.get("oauth_client_id"):
                return ConnectionTestResult(
                    ok=False,
                    status="not_configured",
                    detail="oauth_client_id is required in non-secret config for OAuth2",
                )
            if not credentials.get("client_secret") and not credentials.get("bearer_token"):
                return ConnectionTestResult(
                    ok=False,
                    status="not_configured",
                    detail="OAuth2 requires encrypted client_secret and/or bearer_token",
                )
        return health_check_url(
            base_url=base_url,
            auth_type=auth_type,
            credentials=credentials,
            config=config,
            timeout_seconds=timeout_seconds,
        )

    def health_sync(
        self,
        *,
        base_url: str | None,
        auth_type: str,
        config: dict[str, Any],
        credentials: dict[str, str],
        timeout_seconds: float,
    ) -> SyncResult:
        result = self.test_connection(
            base_url=base_url,
            auth_type=auth_type,
            config=config,
            credentials=credentials,
            timeout_seconds=timeout_seconds,
        )
        if result.ok:
            return SyncResult(success_count=1, failure_count=0, detail=result.detail)
        return SyncResult(success_count=0, failure_count=1, detail=result.detail, errors=[result.detail])


class CouncilGenericAdapter(_GenericRestAdapter):
    provider_key = "council_generic"
    category = "council"


class HrGenericAdapter(_GenericRestAdapter):
    provider_key = "hr_generic"
    category = "hr"


class FinanceGenericAdapter(_GenericRestAdapter):
    provider_key = "finance_generic"
    category = "finance"


class CommunityServiceGenericAdapter(_GenericRestAdapter):
    provider_key = "community_service_generic"
    category = "community_service"


ADAPTERS: dict[str, _GenericRestAdapter] = {
    CouncilGenericAdapter.provider_key: CouncilGenericAdapter(),
    HrGenericAdapter.provider_key: HrGenericAdapter(),
    FinanceGenericAdapter.provider_key: FinanceGenericAdapter(),
    CommunityServiceGenericAdapter.provider_key: CommunityServiceGenericAdapter(),
}


def get_adapter(provider_key: str) -> _GenericRestAdapter:
    adapter = ADAPTERS.get(provider_key)
    if adapter is None:
        raise KeyError(f"Unknown provider_key: {provider_key}")
    return adapter
