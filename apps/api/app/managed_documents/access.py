"""Authorisation for F2.11 managed documents."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.complaints.access import assert_can_view_complaint
from app.db.models.complaints import Complaint
from app.db.models.enums import HMoreRole
from app.db.models.housing import HousingApplication
from app.db.models.managed_documents import (
    ManagedDocument,
    ManagedDocumentAccessGrant,
    ManagedDocumentCategory,
    ManagedDocumentLink,
    OrganisationDocumentSettings,
)
from app.db.models.maintenance import MaintenanceRequest
from app.db.models.property import Property
from app.db.models.support_ops import CaseAssignment
from app.db.models.support_plans import TenantSupportPlan
from app.db.models.tenant import Tenant
from app.housing.access import assert_can_view_application
from app.maintenance.access import assert_can_view_request
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.support.access import get_tenant_or_404
from app.tenancy.context import OrganisationContext

NOW = lambda: datetime.now(timezone.utc)


def _cls_rank(s: str) -> int:
    return {"standard": 1, "confidential": 2, "restricted": 3}.get(s, 1)


def effective_classification(doc: ManagedDocument, category: ManagedDocumentCategory | None) -> str:
    d = doc.access_classification or "standard"
    c = category.access_classification if category else "standard"
    return d if _cls_rank(d) >= _cls_rank(c) else c


def require_meta(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.DOCUMENTS_READ_META)


def require_content(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.DOCUMENTS_READ_CONTENT)


def require_upload(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.DOCUMENTS_UPLOAD)


def require_version(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.DOCUMENTS_VERSION)


def require_archive(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.DOCUMENTS_ARCHIVE)


def require_expiry_manage(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.DOCUMENTS_MANAGE_EXPIRY)


def require_retention_manage(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.DOCUMENTS_MANAGE_RETENTION)


def require_restricted_view(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.DOCUMENTS_VIEW_RESTRICTED)


def require_access_request(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.DOCUMENTS_ACCESS_REQUEST)


def require_access_approve(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.DOCUMENTS_ACCESS_APPROVE)


def require_sign_request(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.DOCUMENTS_SIGN_REQUEST)


def require_sign_complete(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.DOCUMENTS_SIGN_COMPLETE)


def require_categories(ctx: OrganisationContext) -> None:
    if ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    require_permission(ctx.authorization, Permission.DOCUMENTS_MANAGE_CATEGORIES)


def require_settings(ctx: OrganisationContext) -> None:
    if ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    require_permission(ctx.authorization, Permission.DOCUMENTS_MANAGE_SETTINGS)


def active_grant(session: Session, document_id: uuid.UUID, user_id: uuid.UUID) -> ManagedDocumentAccessGrant | None:
    return session.scalar(
        select(ManagedDocumentAccessGrant).where(
            ManagedDocumentAccessGrant.document_id == document_id,
            ManagedDocumentAccessGrant.user_id == user_id,
            ManagedDocumentAccessGrant.revoked_at.is_(None),
            ManagedDocumentAccessGrant.expires_at > NOW(),
        )
    )


def _sw_has_tenant(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> bool:
    return (
        session.scalar(
            select(CaseAssignment.id).where(
                CaseAssignment.organisation_id == ctx.organisation_id,
                CaseAssignment.tenant_id == tenant_id,
                CaseAssignment.support_worker_user_id == ctx.user_id,
                CaseAssignment.status == "active",
            )
        )
        is not None
    )


def link_visible(session: Session, ctx: OrganisationContext, link: ManagedDocumentLink) -> bool:
    if link.organisation_id != ctx.organisation_id:
        return False
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return True
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        return True

    if link.link_type == "tenant":
        t = session.get(Tenant, link.link_id)
        if t is None or t.organisation_id != ctx.organisation_id:
            return False
        if ctx.role == HMoreRole.TENANT:
            return t.user_id == ctx.user_id
        if ctx.role == HMoreRole.SUPPORT_WORKER:
            return _sw_has_tenant(session, ctx, t.id)
        return False

    if link.link_type == "property":
        p = session.get(Property, link.link_id)
        if p is None or p.organisation_id != ctx.organisation_id:
            return False
        if ctx.role == HMoreRole.LANDLORD:
            return p.landlord_user_id == ctx.user_id
        if ctx.role == HMoreRole.SUPPORT_WORKER:
            return True
        return False

    if link.link_type == "housing_application":
        app = session.get(HousingApplication, link.link_id)
        if app is None or app.organisation_id != ctx.organisation_id:
            return False
        try:
            assert_can_view_application(session, ctx, app)
            return True
        except HTTPException:
            return False

    if link.link_type == "support_plan":
        plan = session.get(TenantSupportPlan, link.link_id)
        if plan is None or plan.organisation_id != ctx.organisation_id:
            return False
        if ctx.role == HMoreRole.SUPPORT_WORKER:
            return _sw_has_tenant(session, ctx, plan.tenant_id)
        if ctx.role == HMoreRole.ORGANISATION_ADMIN:
            return True
        return False

    if link.link_type == "complaint":
        c = session.get(Complaint, link.link_id)
        if c is None:
            return False
        try:
            assert_can_view_complaint(session, ctx, c)
            return True
        except HTTPException:
            return False

    if link.link_type == "maintenance":
        m = session.get(MaintenanceRequest, link.link_id)
        if m is None:
            return False
        try:
            assert_can_view_request(session, ctx, m)
            return True
        except HTTPException:
            return False

    if link.link_type == "other":
        return ctx.role == HMoreRole.ORGANISATION_ADMIN

    return False


def validate_link_for_write(session: Session, ctx: OrganisationContext, link: ManagedDocumentLink) -> None:
    """Ensure the actor may attach this business link (raises HTTPException)."""
    if link.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid link")
    if link.link_type == "tenant":
        get_tenant_or_404(session, ctx, link.link_id)
        if ctx.role == HMoreRole.SUPPORT_WORKER and not _sw_has_tenant(session, ctx, link.link_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if ctx.role == HMoreRole.TENANT:
            t = session.get(Tenant, link.link_id)
            if t is None or t.user_id != ctx.user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if ctx.role == HMoreRole.LANDLORD:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return
    if link.link_type == "property":
        p = session.get(Property, link.link_id)
        if p is None or p.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid property")
        if ctx.role == HMoreRole.LANDLORD and p.landlord_user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return
    if link.link_type == "housing_application":
        app = session.get(HousingApplication, link.link_id)
        if app is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid application")
        assert_can_view_application(session, ctx, app)
        return
    if link.link_type == "support_plan":
        plan = session.get(TenantSupportPlan, link.link_id)
        if plan is None or plan.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid support plan")
        if ctx.role == HMoreRole.SUPPORT_WORKER and not _sw_has_tenant(session, ctx, plan.tenant_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return
    if link.link_type == "complaint":
        c = session.get(Complaint, link.link_id)
        if c is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid complaint")
        assert_can_view_complaint(session, ctx, c)
        return
    if link.link_type == "maintenance":
        m = session.get(MaintenanceRequest, link.link_id)
        if m is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid maintenance request")
        assert_can_view_request(session, ctx, m)
        return
    if link.link_type == "other":
        if ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def document_visible(session: Session, ctx: OrganisationContext, doc: ManagedDocument) -> bool:
    if doc.organisation_id != ctx.organisation_id:
        return False
    cat = session.get(ManagedDocumentCategory, doc.category_id)
    eff = effective_classification(doc, cat)
    if eff == "restricted":
        has = ctx.authorization and ctx.authorization.has_permission(Permission.DOCUMENTS_VIEW_RESTRICTED)
        if not has and not active_grant(session, doc.id, ctx.user_id):
            return False
    elif eff == "confidential":
        has = ctx.authorization and ctx.authorization.has_permission(Permission.DOCUMENTS_VIEW_RESTRICTED)
        if not has and ctx.role in {
            HMoreRole.TENANT,
            HMoreRole.LANDLORD,
            HMoreRole.MAINTENANCE_CONTRACTOR,
        }:
            if not active_grant(session, doc.id, ctx.user_id):
                return False

    if active_grant(session, doc.id, ctx.user_id):
        return True

    if ctx.role == HMoreRole.SUPER_ADMIN:
        return True
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        return True

    links = list(
        session.scalars(select(ManagedDocumentLink).where(ManagedDocumentLink.document_id == doc.id))
    )
    if not links:
        if doc.uploaded_by_user_id == ctx.user_id:
            return True
        return ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}

    return any(link_visible(session, ctx, ln) for ln in links)


def assert_document_readable(session: Session, ctx: OrganisationContext, doc_id: uuid.UUID) -> ManagedDocument:
    require_meta(ctx)
    doc = session.get(ManagedDocument, doc_id)
    if doc is None or doc.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if not document_visible(session, ctx, doc):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


def get_or_create_settings(session: Session, org_id: uuid.UUID) -> OrganisationDocumentSettings:
    row = session.scalar(
        select(OrganisationDocumentSettings).where(OrganisationDocumentSettings.organisation_id == org_id)
    )
    if row:
        return row
    row = OrganisationDocumentSettings(organisation_id=org_id)
    session.add(row)
    session.flush()
    return row
