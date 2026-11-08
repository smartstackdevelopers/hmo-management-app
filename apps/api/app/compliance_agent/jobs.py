"""Scheduled compliance sweeps via existing Celery infrastructure."""

from __future__ import annotations

import logging
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compliance_agent import service as compliance_service
from app.core.config import get_settings
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.enums import HMoreRole, MembershipStatus
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenancy.context import OrganisationContext
from app.tenancy.jobs import validate_job_organisation_context
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

logger = logging.getLogger("hmore.compliance_agent.jobs")


def _system_ctx(session: Session, organisation_id: uuid.UUID) -> OrganisationContext:
    membership = session.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.role == HMoreRole.ORGANISATION_ADMIN,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise RuntimeError("No organisation admin available for scheduled compliance sweep")
    user = session.get(User, membership.user_id)
    if user is None:
        raise RuntimeError("Organisation admin user missing for scheduled compliance sweep")
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


def run_org_sweep(session: Session, organisation_id: uuid.UUID, *, trigger: str = "scheduled") -> dict:
    apply_organisation_rls(session, organisation_id)
    from app.ai_feature_flags.enforce import skip_if_disabled
    from app.ai_usage.features import FEATURE_COMPLIANCE

    skipped = skip_if_disabled(session, organisation_id=organisation_id, feature_id=FEATURE_COMPLIANCE)
    if skipped:
        return skipped
    ctx = _system_ctx(session, organisation_id)
    result = compliance_service.run_sweep(
        session,
        ctx,
        trigger=trigger,
        settings=get_settings(),
    )
    session.commit()
    return {
        "organisation_id": str(organisation_id),
        "sweep_id": result["id"],
        "status": result["status"],
        "findings_created": result["findings_created"],
        "ai_status": result["ai_status"],
    }


def dispatch_scheduled_sweeps(session: Session) -> dict:
    """Platform beat job: one scheduled sweep per organisation."""
    apply_platform_rls_bypass(session)
    org_ids = list(session.scalars(select(Organisation.id)))
    totals = {"organisations": 0, "completed": 0, "failed": 0}
    for org_id in org_ids:
        totals["organisations"] += 1
        try:
            run_org_sweep(session, org_id, trigger="scheduled")
            totals["completed"] += 1
        except Exception:  # noqa: BLE001
            session.rollback()
            apply_platform_rls_bypass(session)
            totals["failed"] += 1
            logger.exception("Scheduled compliance sweep failed organisation_id=%s", org_id)
    logger.info("dispatch_scheduled_compliance_sweeps result=%s", totals)
    return totals


def dispatch_org_scheduled_sweep(session: Session, payload: dict) -> dict:
    ctx = validate_job_organisation_context(session, payload, require_actor=False)
    return run_org_sweep(session, ctx.organisation_id, trigger="scheduled")
