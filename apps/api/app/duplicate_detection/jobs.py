"""Scheduled organisation-scoped duplicate detection sweeps."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.enums import HMoreRole, MembershipStatus
from app.duplicate_detection import service as dd_service
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenancy.context import OrganisationContext
from app.tenancy.jobs import validate_job_organisation_context
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

logger = logging.getLogger("hmore.duplicate_detection.jobs")


def _admin_ctx(session: Session, organisation_id: uuid.UUID) -> OrganisationContext:
    membership = session.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.role == HMoreRole.ORGANISATION_ADMIN,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise RuntimeError("No organisation admin for scheduled duplicate detection")
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


def run_org_sweep(session: Session, organisation_id: uuid.UUID) -> dict:
    apply_organisation_rls(session, organisation_id)
    from app.ai_feature_flags.enforce import skip_if_disabled
    from app.ai_usage.features import FEATURE_DUPLICATE_DETECTION

    skipped = skip_if_disabled(
        session, organisation_id=organisation_id, feature_id=FEATURE_DUPLICATE_DETECTION
    )
    if skipped:
        return skipped
    ctx = _admin_ctx(session, organisation_id)
    result = dd_service.run_detection(session, ctx, trigger="scheduled")
    session.commit()
    return {
        "organisation_id": str(organisation_id),
        "run_id": result["id"],
        "findings_created": result["findings_created"],
        "used_ai": result["used_ai"],
    }


def dispatch_scheduled_sweeps(session: Session) -> dict:
    apply_platform_rls_bypass(session)
    totals = {"organisations": 0, "completed": 0, "failed": 0}
    for org_id in session.scalars(select(Organisation.id)):
        totals["organisations"] += 1
        try:
            run_org_sweep(session, org_id)
            totals["completed"] += 1
        except Exception:  # noqa: BLE001
            session.rollback()
            apply_platform_rls_bypass(session)
            totals["failed"] += 1
            logger.exception("Scheduled duplicate detection failed organisation_id=%s", org_id)
    return totals


def dispatch_org_scheduled_sweep(session: Session, payload: dict) -> dict:
    ctx = validate_job_organisation_context(session, payload, require_actor=False)
    return run_org_sweep(session, ctx.organisation_id)
