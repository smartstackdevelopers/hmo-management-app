"""Auth0 Management API is optional and unused by this MVP.

The current device revokes its own refresh token by calling Auth0
``/oauth/revoke`` with the refresh token it already holds. Revoking refresh
tokens for other devices would need Management API credentials
(``AUTH0_MGMT_DOMAIN``, ``AUTH0_MGMT_CLIENT_ID``, ``AUTH0_MGMT_CLIENT_SECRET``).
This module records whether those values are present. It does not request a
management token and it does not call Auth0.
"""

from __future__ import annotations

from app.core.config import Settings


def management_api_revocation(settings: Settings) -> dict[str, bool]:
    configured = bool(
        settings.auth0_mgmt_domain and settings.auth0_mgmt_client_id and settings.auth0_mgmt_client_secret
    )
    return {"configured": configured, "called": False}
