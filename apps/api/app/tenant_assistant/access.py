"""RBAC and pilot gate for F3.10 Tenant Assistant."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.core.config import Settings, get_settings
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def pilot_org_ids(settings: Settings | None = None) -> set[uuid.UUID]:
    settings = settings or get_settings()
    raw = (settings.tenant_assistant_pilot_organisation_ids or "").strip()
    if not raw:
        return set()
    out: set[uuid.UUID] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        out.add(uuid.UUID(part))
    return out


def require_pilot_enabled(ctx: OrganisationContext, settings: Settings | None = None) -> None:
    allowed = pilot_org_ids(settings)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant Assistant pilot is not enabled for any organisation",
        )
    if ctx.organisation_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant Assistant pilot is not enabled for this organisation",
        )


def require_tenant_ask(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        # Super Admin may diagnose availability but does not ask as a tenant.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant Assistant is for tenant accounts")
    if ctx.role != HMoreRole.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant Assistant is for tenant accounts")
    require_permission(ctx.authorization, Permission.AI_TENANT_ASSISTANT_ASK)


def require_tenant_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role != HMoreRole.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant Assistant history is tenant-only")
    require_permission(ctx.authorization, Permission.AI_TENANT_ASSISTANT_READ)
