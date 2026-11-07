from __future__ import annotations

from fastapi import Depends, Header, Request

from app.auth.service_token import verify_service_token
from app.context.trusted import TrustedCallerContext, build_trusted_context
from app.core.config import Settings, get_settings
from app.core.correlation import set_correlation_id
from app.core.errors import AiServiceError, ForbiddenError


def get_settings_dep() -> Settings:
    return get_settings()


async def require_service_auth(
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-Id"),
    x_organisation_id: str | None = Header(default=None, alias="X-HMore-Organisation-Id"),
    x_user_id: str | None = Header(default=None, alias="X-HMore-User-Id"),
    x_role: str | None = Header(default=None, alias="X-HMore-Role"),
    x_features: str | None = Header(default=None, alias="X-HMore-Features"),
    settings: Settings = Depends(get_settings_dep),
) -> TrustedCallerContext:
    """Authenticate S2S caller and build trusted org/user context from signed headers only."""
    set_correlation_id(x_correlation_id)
    try:
        verify_service_token(settings, authorization)
        ctx = build_trusted_context(
            organisation_id=x_organisation_id,
            user_id=x_user_id,
            role=x_role,
            features_header=x_features,
            defaults=settings.allowed_features,
        )
    except AiServiceError as exc:
        raise exc.to_http() from exc
    request.state.trusted_context = ctx
    return ctx


def require_feature(feature: str):
    async def _checker(ctx: TrustedCallerContext = Depends(require_service_auth)) -> TrustedCallerContext:
        if feature not in ctx.features:
            raise ForbiddenError(f"Feature '{feature}' is not authorised for this caller").to_http()
        return ctx

    return _checker
