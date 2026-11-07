"""Scheduled report draft generation for organisations (admin actor)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.report_drafts import service as draft_service
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

logger = logging.getLogger("hmore.report_drafts.jobs")


def _admin_ctx(session: Session, organisation_id: uuid.UUID) -> OrganisationContext:
    membership = session.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.role == HMoreRole.ORGANISATION_ADMIN,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise RuntimeError("No organisation admin for scheduled report draft")
    user = session.get(User, membership.user_id)
    if user is None:
        raise RuntimeError("Organisation admin user missing")
    authz = AuthorizationContext(
        user=user,
        memberships=[
            MembershipView(
                membership_id=membership.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                organisation_id=organisation_id,
                status=MembershipStatus.ACTIVE,
            )
        ],
        active_organisation_id=organisation_id,
        active_role=HMoreRole.ORGANISATION_ADMIN,
    )
    return OrganisationContext(
        user=user,
        organisation_id=organisation_id,
        role=HMoreRole.ORGANISATION_ADMIN,
        authorization=authz,
    )


def run_org_period(session: Session, organisation_id: uuid.UUID, period_type: str) -> dict:
    apply_organisation_rls(session, organisation_id)
    ctx = _admin_ctx(session, organisation_id)
    result = draft_service.generate_draft(
        session, ctx, period_type=period_type, regenerate=False, settings=get_settings()
    )
    session.commit()
    return {"organisation_id": str(organisation_id), "draft_id": result["id"], "period_type": period_type}


def dispatch_period_drafts(session: Session, period_type: str) -> dict:
    apply_platform_rls_bypass(session)
    totals = {"organisations": 0, "completed": 0, "failed": 0, "period_type": period_type}
    for org_id in session.scalars(
        select(Organisation.id).where(Organisation.status == RecordStatus.ACTIVE)
    ):
        totals["organisations"] += 1
        try:
            run_org_period(session, org_id, period_type)
            totals["completed"] += 1
        except Exception:  # noqa: BLE001
            session.rollback()
            apply_platform_rls_bypass(session)
            totals["failed"] += 1
            logger.exception("Scheduled report draft failed organisation_id=%s period=%s", org_id, period_type)
    return totals
