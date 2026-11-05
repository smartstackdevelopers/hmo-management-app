from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.auth.deps import get_current_user, get_staff_user, get_token_claims, require_mfa
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def read_me(
    user: User = Depends(get_current_user),
    claims: dict[str, Any] = Depends(get_token_claims),
) -> dict[str, Any]:
    """Return the authenticated HMore user mapped from the Auth0 subject."""
    return {
        "id": str(user.id),
        "external_subject": user.external_subject,
        "email": user.email,
        "display_name": user.display_name,
        "token_sub": claims.get("sub"),
    }


@router.get("/staff-session")
def staff_session(
    user: User = Depends(get_staff_user),
    claims: dict[str, Any] = Depends(require_mfa),
) -> dict[str, Any]:
    """Staff/admin session probe. When AUTH0_REQUIRE_MFA_CLAIM is true, MFA is required.

    Role authorization is intentionally not applied here (F1.4).
    """
    return {
        "id": str(user.id),
        "external_subject": user.external_subject,
        "mfa": "mfa" in (claims.get("amr") or []),
    }
