"""F1.4 session-control foundation on top of Auth0 (F1.3).

Auth0 owns login sessions and token lifetimes. HMore API is stateless for access
tokens. This module documents and exposes authorization freshness checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.rbac.context import AuthorizationContext


@dataclass(frozen=True)
class SessionPolicySummary:
    provider: str
    access_token_validation: str
    logout: str
    revocation: str
    role_change_strategy: str
    authorization_version: int


def describe_session_policy(ctx: AuthorizationContext | None = None) -> SessionPolicySummary:
    return SessionPolicySummary(
        provider="Auth0",
        access_token_validation=(
            "API rejects missing/invalid/expired access tokens (iss, aud, signature, exp)."
        ),
        logout=(
            "Web: /auth/logout clears the Auth0 SDK session cookie and ends the Auth0 SSO "
            "session. Mobile: clear SecureStore tokens and call Auth0 /v2/logout."
        ),
        revocation=(
            "Refresh-token revocation is Auth0-managed. Access tokens remain valid until "
            "expiry; use short access-token lifetimes. HMore does not invent a second "
            "token store."
        ),
        role_change_strategy=(
            "Role changes increment users.authorization_version. Clients should refresh "
            "permissions from /api/v1/rbac/me after role changes. Stale permission caches "
            "must not be trusted."
        ),
        authorization_version=ctx.authorization_version if ctx else 0,
    )


def session_policy_payload(ctx: AuthorizationContext | None = None) -> dict[str, Any]:
    summary = describe_session_policy(ctx)
    return {
        "provider": summary.provider,
        "access_token_validation": summary.access_token_validation,
        "logout": summary.logout,
        "revocation": summary.revocation,
        "role_change_strategy": summary.role_change_strategy,
        "authorization_version": summary.authorization_version,
    }
