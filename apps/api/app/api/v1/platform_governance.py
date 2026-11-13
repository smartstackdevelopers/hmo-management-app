"""F8.12 platform governance API."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models.enums import RecordStatus
from app.db.session import get_session
from app.platform_governance import service
from app.platform_governance.service import _branding, _org_settings
from app.rbac.context import AuthorizationContext
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context, get_platform_context

router = APIRouter(prefix="/platform-governance", tags=["platform-governance"])


class OrgGovSettingsBody(BaseModel):
    enabled: bool | None = None
    privacy_review_complete: bool | None = None
    notification_settings: dict[str, Any] | None = None


class PlatformBrandingBody(BaseModel):
    platform_name: str | None = Field(default=None, max_length=255)
    branding_json: dict[str, Any] | None = None
    regional_settings: dict[str, Any] | None = None
    security_settings: dict[str, Any] | None = None


class OrgRegistrationBody(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)


class RegistrationReviewBody(BaseModel):
    approve: bool
    notes: str | None = None


class OrgStatusBody(BaseModel):
    status: Literal["active", "archived"]


class CompliancePolicyBody(BaseModel):
    category_slug: str
    title: str = Field(min_length=1, max_length=255)
    policy_body: str | None = None


class IncidentBody(BaseModel):
    category: str
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    severity: str = "low"
    organisation_id: uuid.UUID | None = None


@router.get("/org/settings")
def get_org_settings(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.PLATFORM_GOVERNANCE_READ)
    return service.org_settings_dict(_org_settings(session, ctx.organisation_id))


@router.patch("/org/settings")
def patch_org_settings(
    body: OrgGovSettingsBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.update_org_settings(session, ctx, body.model_dump(exclude_unset=True))
    return service.org_settings_dict(row)


@router.get("/org/dashboard")
def org_dashboard(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    return service.organisation_dashboard(session, ctx)


@router.post("/org/compliance/policies")
def create_policy(
    body: CompliancePolicyBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.create_compliance_policy(session, ctx, body.model_dump())
    return {"id": str(row.id), "title": row.title, "status": row.status}


@router.post("/org/incidents")
def create_org_incident(
    body: IncidentBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.create_incident(session, ctx, ctx.authorization, body.model_dump())
    return {"id": str(row.id), "status": row.status}


@router.get("/platform/dashboard")
def platform_dashboard(
    session: Session = Depends(get_session),
    authz: AuthorizationContext = Depends(get_platform_context),
) -> dict[str, Any]:
    return service.platform_dashboard(session, authz)


@router.get("/platform/organisations")
def list_orgs(session: Session = Depends(get_session), authz: AuthorizationContext = Depends(get_platform_context)) -> list[dict[str, Any]]:
    return service.list_organisations(session, authz)


@router.patch("/platform/organisations/{organisation_id}/status")
def patch_org_status(
    organisation_id: uuid.UUID,
    body: OrgStatusBody,
    session: Session = Depends(get_session),
    authz: AuthorizationContext = Depends(get_platform_context),
) -> dict[str, Any]:
    status_val = RecordStatus.ACTIVE if body.status == "active" else RecordStatus.ARCHIVED
    org = service.set_organisation_status(session, authz, organisation_id, status_val)
    return {"id": str(org.id), "status": org.status.value}


@router.get("/platform/branding")
def get_branding(session: Session = Depends(get_session), authz: AuthorizationContext = Depends(get_platform_context)) -> dict[str, Any]:
    require_permission(authz, Permission.PLATFORM_GOVERNANCE_READ)
    from app.core.config import get_settings

    service.assert_platform_addon(get_settings())
    return service.platform_settings_dict(_branding(session))


@router.patch("/platform/branding")
def patch_branding(
    body: PlatformBrandingBody,
    session: Session = Depends(get_session),
    authz: AuthorizationContext = Depends(get_platform_context),
) -> dict[str, Any]:
    row = service.update_platform_branding(session, authz, body.model_dump(exclude_unset=True))
    return service.platform_settings_dict(row)


@router.post("/platform/org-registrations")
def submit_registration(
    body: OrgRegistrationBody,
    session: Session = Depends(get_session),
    authz: AuthorizationContext = Depends(get_platform_context),
) -> dict[str, Any]:
    row = service.submit_org_registration(session, authz, body.name, body.slug)
    return {"id": str(row.id), "status": row.status}


@router.post("/platform/org-registrations/{registration_id}/review")
def review_registration(
    registration_id: uuid.UUID,
    body: RegistrationReviewBody,
    session: Session = Depends(get_session),
    authz: AuthorizationContext = Depends(get_platform_context),
) -> dict[str, Any]:
    return service.review_org_registration(session, authz, registration_id, approve=body.approve, notes=body.notes)


@router.get("/platform/health")
def health_api(session: Session = Depends(get_session), authz: AuthorizationContext = Depends(get_platform_context)) -> dict[str, Any]:
    require_permission(authz, Permission.PLATFORM_GOVERNANCE_READ)
    from app.core.config import get_settings

    return service.system_health(session, get_settings())


@router.post("/platform/security/sync-alerts")
def sync_alerts(session: Session = Depends(get_session), authz: AuthorizationContext = Depends(get_platform_context)) -> dict[str, int]:
    return {"created": service.sync_security_alerts_from_audit(session, authz)}


@router.get("/compliance/categories")
def categories_api() -> list[dict[str, str]]:
    return service.list_categories()


@router.post("/org/ai/summary")
def ai_summary_org(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    return service.ai_admin_summary(session, ctx, ctx.authorization)


@router.post("/platform/ai/summary")
def ai_summary_platform(
    session: Session = Depends(get_session),
    authz: AuthorizationContext = Depends(get_platform_context),
) -> dict[str, Any]:
    return service.ai_admin_summary(session, None, authz)
