"""F2.10 support plans — business logic."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, false, func, or_, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.support_plans import (
    SupportPlanContributor,
    SupportPlanGoal,
    SupportPlanGoalChange,
    SupportPlanGoalProgressNote,
    SupportPlanHistoryEvent,
    SupportPlanMilestone,
    SupportPlanMilestoneChange,
    SupportPlanProgressExport,
    SupportPlanReview,
    TenantSupportPlan,
)
from app.db.models.enums import HMoreRole
from app.evidence.pdf import build_simple_pdf
from app.records.pagination import offset_limit
from app.storage import service as file_service
from app.support_plans import access as sp_access
from app.support_plans.schemas import (
    ExportCreate,
    GoalAchieveBody,
    GoalCancelBody,
    GoalCreate,
    GoalProgressNoteCreate,
    GoalUpdate,
    MilestoneCancelBody,
    MilestoneCompleteBody,
    MilestoneCreate,
    MilestoneUpdate,
    PlanTransitionBody,
    ReviewCreate,
    ReviewUpdate,
    SupportPlanCreate,
    SupportPlanReviseCreate,
    SupportPlanUpdate,
)
from app.tenancy.context import OrganisationContext

NOW = lambda: datetime.now(timezone.utc)

PLAN_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"active", "closed"}),
    "active": frozenset({"under_review", "on_hold", "completed", "closed"}),
    "under_review": frozenset({"active", "on_hold", "completed", "closed"}),
    "on_hold": frozenset({"active", "under_review", "completed", "closed"}),
    "completed": frozenset({"closed"}),
    "closed": frozenset(),
}

GOAL_TRANSITIONS: dict[str, frozenset[str]] = {
    "not_started": frozenset({"in_progress", "on_hold", "cancelled"}),
    "in_progress": frozenset({"at_risk", "achieved", "on_hold", "cancelled", "not_started"}),
    "at_risk": frozenset({"in_progress", "achieved", "on_hold", "cancelled"}),
    "achieved": frozenset(),
    "on_hold": frozenset({"not_started", "in_progress", "cancelled"}),
    "cancelled": frozenset(),
}

MILESTONE_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"in_progress", "cancelled", "delayed"}),
    "in_progress": frozenset({"completed", "delayed", "cancelled", "pending"}),
    "delayed": frozenset({"in_progress", "completed", "cancelled", "pending"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}

REVIEW_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"in_progress", "finalised"}),
    "in_progress": frozenset({"draft", "finalised"}),
    "finalised": frozenset({"superseded"}),
    "superseded": frozenset(),
}

PLAN_EDITABLE_STATUSES = frozenset({"draft", "under_review", "on_hold"})


def _next_ref(session: Session, org_id: uuid.UUID, model: type, prefix: str) -> str:
    year = NOW().year
    pat = f"{prefix}-{year}-"
    count = (
        session.scalar(
            select(func.count()).select_from(model).where(
                model.organisation_id == org_id,
                model.reference_number.like(f"{pat}%"),
            )
        )
        or 0
    )
    return f"{pat}{count + 1:05d}"


def _audit(
    session: Session,
    ctx: OrganisationContext,
    *,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
    summary: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    record_event(
        session,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary=summary,
        metadata=metadata or {},
    )


def _history(
    session: Session,
    org_id: uuid.UUID,
    plan_id: uuid.UUID,
    event_type: str,
    summary: str,
    *,
    actor_user_id: uuid.UUID | None,
    detail: str | None = None,
    related_entity_type: str | None = None,
    related_entity_id: uuid.UUID | None = None,
) -> None:
    session.add(
        SupportPlanHistoryEvent(
            organisation_id=org_id,
            plan_id=plan_id,
            event_type=event_type,
            summary=summary[:500],
            detail=detail,
            actor_user_id=actor_user_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )
    )


def _plan_view(plan: TenantSupportPlan, ctx: OrganisationContext, *, internal: bool) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": str(plan.id),
        "organisation_id": str(plan.organisation_id),
        "reference_number": plan.reference_number,
        "tenant_id": str(plan.tenant_id),
        "title": plan.title,
        "description": plan.description,
        "support_objectives": plan.support_objectives,
        "responsible_worker_user_id": str(plan.responsible_worker_user_id),
        "start_date": plan.start_date.isoformat() if plan.start_date else None,
        "planned_review_date": plan.planned_review_date.isoformat() if plan.planned_review_date else None,
        "status": plan.status,
        "completed_at": plan.completed_at.isoformat() if plan.completed_at else None,
        "closed_at": plan.closed_at.isoformat() if plan.closed_at else None,
        "hold_reason": plan.hold_reason,
        "superseded_by_plan_id": str(plan.superseded_by_plan_id) if plan.superseded_by_plan_id else None,
        "supersedes_plan_id": str(plan.supersedes_plan_id) if plan.supersedes_plan_id else None,
        "version_number": plan.version_number,
        "tenant_summary": plan.tenant_summary,
        "created_by_user_id": str(plan.created_by_user_id) if plan.created_by_user_id else None,
        "updated_by_user_id": str(plan.updated_by_user_id) if plan.updated_by_user_id else None,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }
    if internal and sp_access.can_view_internal_notes(ctx):
        d["internal_notes"] = plan.internal_notes
    else:
        d["internal_notes"] = None
    return d


def _goal_field_change(
    session: Session,
    org_id: uuid.UUID,
    goal_id: uuid.UUID,
    field: str,
    old: str | None,
    new: str | None,
    user_id: uuid.UUID | None,
) -> None:
    if old == new:
        return
    session.add(
        SupportPlanGoalChange(
            organisation_id=org_id,
            goal_id=goal_id,
            field_name=field,
            old_value=old,
            new_value=new,
            changed_by_user_id=user_id,
        )
    )


def _ms_field_change(
    session: Session,
    org_id: uuid.UUID,
    ms_id: uuid.UUID,
    field: str,
    old: str | None,
    new: str | None,
    user_id: uuid.UUID | None,
) -> None:
    if old == new:
        return
    session.add(
        SupportPlanMilestoneChange(
            organisation_id=org_id,
            milestone_id=ms_id,
            field_name=field,
            old_value=old,
            new_value=new,
            changed_by_user_id=user_id,
        )
    )


def _get_plan(session: Session, ctx: OrganisationContext, plan_id: uuid.UUID) -> TenantSupportPlan:
    plan = session.get(TenantSupportPlan, plan_id)
    if plan is None or plan.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    return plan


def _assert_plan_manageable(plan: TenantSupportPlan, ctx: OrganisationContext) -> None:
    if plan.status not in PLAN_EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This plan cannot be edited in its current status",
        )


def _transition_plan(plan: TenantSupportPlan, new_status: str) -> None:
    allowed = PLAN_TRANSITIONS.get(plan.status, frozenset())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid plan status transition: {plan.status} -> {new_status}",
        )
    plan.status = new_status
    plan.updated_by_user_id = plan.updated_by_user_id  # noqa — set by caller


def list_contributor_user_ids(session: Session, plan_id: uuid.UUID) -> list[uuid.UUID]:
    rows = session.scalars(
        select(SupportPlanContributor.user_id).where(SupportPlanContributor.plan_id == plan_id)
    ).all()
    return list(rows)


def create_plan(session: Session, ctx: OrganisationContext, body: SupportPlanCreate) -> dict[str, Any]:
    sp_access.assert_tenant_scope_for_manage(session, ctx, body.tenant_id)
    sp_access.assert_worker_membership(session, ctx.organisation_id, body.responsible_worker_user_id)

    ref = _next_ref(session, ctx.organisation_id, TenantSupportPlan, "SP")
    plan = TenantSupportPlan(
        organisation_id=ctx.organisation_id,
        reference_number=ref,
        tenant_id=body.tenant_id,
        title=body.title.strip(),
        description=body.description,
        support_objectives=body.support_objectives,
        responsible_worker_user_id=body.responsible_worker_user_id,
        start_date=body.start_date,
        planned_review_date=body.planned_review_date,
        status="draft",
        internal_notes=body.internal_notes,
        tenant_summary=body.tenant_summary,
        created_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
        version_number=1,
    )
    session.add(plan)
    session.flush()

    for uid in body.contributor_user_ids:
        if uid == body.responsible_worker_user_id:
            continue
        session.add(
            SupportPlanContributor(
                organisation_id=ctx.organisation_id,
                plan_id=plan.id,
                user_id=uid,
            )
        )

    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "plan_created",
        f"Support plan {ref} created",
        actor_user_id=ctx.user_id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_CREATE,
        resource_type="support_plan",
        resource_id=plan.id,
        summary=f"Created support plan {ref}",
        metadata={"tenant_id": str(body.tenant_id)},
    )
    session.flush()
    internal = sp_access.can_view_internal_notes(ctx)
    return {
        **_plan_view(plan, ctx, internal=internal),
        "contributor_user_ids": [str(u) for u in list_contributor_user_ids(session, plan.id)],
    }


def list_plans(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    status_filter: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    stmt = select(TenantSupportPlan).where(
        TenantSupportPlan.organisation_id == ctx.organisation_id,
        TenantSupportPlan.tenant_id == tenant_id,
    )
    if status_filter:
        stmt = stmt.where(TenantSupportPlan.status == status_filter)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(
            stmt.order_by(TenantSupportPlan.created_at.desc()).offset(offset).limit(limit)
        )
    )
    internal = sp_access.can_view_internal_notes(ctx)
    return (
        [
            {
                **_plan_view(p, ctx, internal=internal),
                "contributor_user_ids": [str(u) for u in list_contributor_user_ids(session, p.id)],
            }
            for p in rows
        ],
        total,
    )


def get_plan(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    internal = sp_access.can_view_internal_notes(ctx)
    return {
        **_plan_view(plan, ctx, internal=internal),
        "contributor_user_ids": [str(u) for u in list_contributor_user_ids(session, plan.id)],
    }


def update_plan(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, body: SupportPlanUpdate
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    _assert_plan_manageable(plan, ctx)

    if body.title is not None:
        plan.title = body.title.strip()
    if body.description is not None:
        plan.description = body.description
    if body.support_objectives is not None:
        plan.support_objectives = body.support_objectives
    if body.responsible_worker_user_id is not None:
        sp_access.assert_worker_membership(session, ctx.organisation_id, body.responsible_worker_user_id)
        plan.responsible_worker_user_id = body.responsible_worker_user_id
    if body.start_date is not None:
        plan.start_date = body.start_date
    if body.planned_review_date is not None:
        plan.planned_review_date = body.planned_review_date
    if body.internal_notes is not None:
        if not sp_access.can_view_internal_notes(ctx):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        plan.internal_notes = body.internal_notes
    if body.tenant_summary is not None:
        plan.tenant_summary = body.tenant_summary
    if body.contributor_user_ids is not None:
        session.execute(delete(SupportPlanContributor).where(SupportPlanContributor.plan_id == plan.id))
        for uid in body.contributor_user_ids:
            if uid == plan.responsible_worker_user_id:
                continue
            session.add(
                SupportPlanContributor(
                    organisation_id=ctx.organisation_id,
                    plan_id=plan.id,
                    user_id=uid,
                )
            )

    plan.updated_by_user_id = ctx.user_id
    _history(session, ctx.organisation_id, plan.id, "plan_updated", "Support plan updated", actor_user_id=ctx.user_id)
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_UPDATE,
        resource_type="support_plan",
        resource_id=plan.id,
        summary="Updated support plan",
    )
    session.flush()
    internal = sp_access.can_view_internal_notes(ctx)
    return {
        **_plan_view(plan, ctx, internal=internal),
        "contributor_user_ids": [str(u) for u in list_contributor_user_ids(session, plan.id)],
    }


def activate_plan(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    old = plan.status
    _transition_plan(plan, "active")
    plan.updated_by_user_id = ctx.user_id
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "plan_status",
        f"Plan activated ({old} -> active)",
        actor_user_id=ctx.user_id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_ACTIVATE,
        resource_type="support_plan",
        resource_id=plan.id,
        summary="Activated support plan",
        metadata={"from": old},
    )
    session.flush()
    return get_plan(session, ctx, tenant_id, plan_id)


def hold_plan(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, body: PlanTransitionBody
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    if not body.hold_reason or not body.hold_reason.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="hold_reason is required")
    old = plan.status
    _transition_plan(plan, "on_hold")
    plan.hold_reason = body.hold_reason.strip()
    plan.updated_by_user_id = ctx.user_id
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "plan_status",
        f"Plan placed on hold ({old} -> on_hold)",
        actor_user_id=ctx.user_id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_HOLD,
        resource_type="support_plan",
        resource_id=plan.id,
        summary="Support plan on hold",
        metadata={"from": old},
    )
    session.flush()
    return get_plan(session, ctx, tenant_id, plan_id)


def complete_plan(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    old = plan.status
    _transition_plan(plan, "completed")
    plan.completed_at = NOW()
    plan.updated_by_user_id = ctx.user_id
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "plan_status",
        f"Plan completed ({old} -> completed)",
        actor_user_id=ctx.user_id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_COMPLETE,
        resource_type="support_plan",
        resource_id=plan.id,
        summary="Support plan completed",
        metadata={"from": old},
    )
    session.flush()
    return get_plan(session, ctx, tenant_id, plan_id)


def close_plan(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    old = plan.status
    _transition_plan(plan, "closed")
    plan.closed_at = NOW()
    plan.updated_by_user_id = ctx.user_id
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "plan_status",
        f"Plan closed ({old} -> closed)",
        actor_user_id=ctx.user_id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_CLOSE,
        resource_type="support_plan",
        resource_id=plan.id,
        summary="Support plan closed",
        metadata={"from": old},
    )
    session.flush()
    return get_plan(session, ctx, tenant_id, plan_id)


def start_plan_review(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    old = plan.status
    _transition_plan(plan, "under_review")
    plan.updated_by_user_id = ctx.user_id
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "plan_status",
        f"Plan under review ({old} -> under_review)",
        actor_user_id=ctx.user_id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_REVIEW_START,
        resource_type="support_plan",
        resource_id=plan.id,
        summary="Support plan marked under review",
        metadata={"from": old},
    )
    session.flush()
    return get_plan(session, ctx, tenant_id, plan_id)


def resume_plan(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    old = plan.status
    _transition_plan(plan, "active")
    plan.hold_reason = None
    plan.updated_by_user_id = ctx.user_id
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "plan_status",
        f"Plan resumed ({old} -> active)",
        actor_user_id=ctx.user_id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_ACTIVATE,
        resource_type="support_plan",
        resource_id=plan.id,
        summary="Support plan resumed from hold",
        metadata={"from": old},
    )
    session.flush()
    return get_plan(session, ctx, tenant_id, plan_id)


def revise_plan(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, body: SupportPlanReviseCreate
) -> dict[str, Any]:
    """New draft plan superseding the given plan."""
    old = _get_plan(session, ctx, plan_id)
    if old.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    if old.superseded_by_plan_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This plan was already superseded"
        )

    sp_access.assert_worker_membership(session, ctx.organisation_id, body.responsible_worker_user_id)

    ref = _next_ref(session, ctx.organisation_id, TenantSupportPlan, "SP")
    new_plan = TenantSupportPlan(
        organisation_id=ctx.organisation_id,
        reference_number=ref,
        tenant_id=tenant_id,
        title=body.title.strip(),
        description=body.description,
        support_objectives=body.support_objectives,
        responsible_worker_user_id=body.responsible_worker_user_id,
        start_date=body.start_date,
        planned_review_date=body.planned_review_date,
        status="draft",
        internal_notes=body.internal_notes,
        tenant_summary=body.tenant_summary,
        supersedes_plan_id=old.id,
        version_number=old.version_number + 1,
        created_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
    )
    session.add(new_plan)
    session.flush()

    old.superseded_by_plan_id = new_plan.id
    old.status = "closed"
    old.closed_at = NOW()
    old.updated_by_user_id = ctx.user_id

    for uid in body.contributor_user_ids:
        if uid == body.responsible_worker_user_id:
            continue
        session.add(
            SupportPlanContributor(
                organisation_id=ctx.organisation_id,
                plan_id=new_plan.id,
                user_id=uid,
            )
        )

    _history(
        session,
        ctx.organisation_id,
        old.id,
        "plan_superseded",
        f"Superseded by plan {ref}",
        actor_user_id=ctx.user_id,
        related_entity_type="support_plan",
        related_entity_id=new_plan.id,
    )
    _history(
        session,
        ctx.organisation_id,
        new_plan.id,
        "plan_created",
        f"Revised plan {ref} (supersedes {old.reference_number})",
        actor_user_id=ctx.user_id,
        related_entity_type="support_plan",
        related_entity_id=old.id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_REVISE,
        resource_type="support_plan",
        resource_id=new_plan.id,
        summary=f"Created revised support plan {ref}",
        metadata={"supersedes": str(old.id)},
    )
    session.flush()
    return get_plan(session, ctx, tenant_id, new_plan.id)


def plan_history(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID
) -> list[dict[str, Any]]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    rows = list(
        session.scalars(
            select(SupportPlanHistoryEvent)
            .where(
                SupportPlanHistoryEvent.plan_id == plan_id,
                SupportPlanHistoryEvent.organisation_id == ctx.organisation_id,
            )
            .order_by(SupportPlanHistoryEvent.created_at.asc())
        )
    )
    return [
        {
            "id": str(r.id),
            "event_type": r.event_type,
            "summary": r.summary,
            "detail": r.detail,
            "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
            "related_entity_type": r.related_entity_type,
            "related_entity_id": str(r.related_entity_id) if r.related_entity_id else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def combined_progress_history(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Chronological mix of plan events, field changes, reviews (non-internal), exports."""
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    internal = sp_access.can_view_internal_notes(ctx)

    entries: list[dict[str, Any]] = []

    for r in plan_history(session, ctx, tenant_id, plan_id):
        entries.append({**r, "source": "plan_event", "sort_at": r.get("created_at")})

    for g in session.scalars(
        select(SupportPlanGoal.id).where(
            SupportPlanGoal.plan_id == plan_id,
            SupportPlanGoal.organisation_id == ctx.organisation_id,
        )
    ):
        for c in goal_change_history(session, ctx, tenant_id, plan_id, g):
            entries.append(
                {
                    **c,
                    "source": "goal_change",
                    "sort_at": c.get("created_at"),
                }
            )

    goals = list(
        session.scalars(
            select(SupportPlanGoal.id).where(
                SupportPlanGoal.plan_id == plan_id,
                SupportPlanGoal.organisation_id == ctx.organisation_id,
            )
        )
    )
    for gid in goals:
        for ms in session.scalars(select(SupportPlanMilestone.id).where(SupportPlanMilestone.goal_id == gid)):
            for c in milestone_history(session, ctx, tenant_id, plan_id, gid, ms):
                entries.append({**c, "source": "milestone_change", "sort_at": c.get("created_at")})

    rev_rows = list(
        session.scalars(
            select(SupportPlanReview).where(
                SupportPlanReview.plan_id == plan_id,
                SupportPlanReview.organisation_id == ctx.organisation_id,
            )
        )
    )
    for r in rev_rows:
        rv = _review_view(r, ctx)
        entries.append(
            {
                "id": str(r.id),
                "source": "review",
                "reference_number": r.reference_number,
                "review_type": r.review_type,
                "review_date": rv.get("review_date"),
                "status": r.status,
                "finalised_at": rv.get("finalised_at"),
                "progress_summary": r.progress_summary,
                "achievements": r.achievements,
                "challenges": r.challenges,
                "internal_notes": rv.get("internal_notes") if internal else None,
                "sort_at": (r.finalised_at or r.updated_at or r.created_at).isoformat()
                if (r.finalised_at or r.updated_at or r.created_at)
                else None,
            }
        )

    goal_ids_subq = (
        select(SupportPlanGoal.id)
        .where(
            SupportPlanGoal.plan_id == plan_id,
            SupportPlanGoal.organisation_id == ctx.organisation_id,
        )
        .scalar_subquery()
    )
    for n in session.scalars(
        select(SupportPlanGoalProgressNote).where(
            SupportPlanGoalProgressNote.organisation_id == ctx.organisation_id,
            SupportPlanGoalProgressNote.goal_id.in_(goal_ids_subq),
        )
    ):
        if ctx.role == HMoreRole.TENANT and not n.show_to_tenant:
            continue
        entries.append(
            {
                "id": str(n.id),
                "source": "goal_progress_note",
                "body": n.body,
                "show_to_tenant": n.show_to_tenant,
                "author_user_id": str(n.author_user_id) if n.author_user_id else None,
                "sort_at": n.created_at.isoformat() if n.created_at else None,
            }
        )

    def sort_key(e: dict[str, Any]) -> str:
        return e.get("sort_at") or e.get("created_at") or ""

    entries.sort(key=sort_key)
    return entries


def list_progress_exports(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    stmt = select(SupportPlanProgressExport).where(
        SupportPlanProgressExport.plan_id == plan_id,
        SupportPlanProgressExport.organisation_id == ctx.organisation_id,
    )
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(
            stmt.order_by(SupportPlanProgressExport.created_at.desc()).offset(offset).limit(limit)
        )
    )
    return (
        [
            {
                "export_id": str(r.id),
                "file_id": str(r.file_id),
                "generated_by_user_id": str(r.generated_by_user_id) if r.generated_by_user_id else None,
                "include_internal": r.include_internal,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        total,
    )


def _goal_view(g: SupportPlanGoal, ctx: OrganisationContext) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": str(g.id),
        "organisation_id": str(g.organisation_id),
        "reference_number": g.reference_number,
        "plan_id": str(g.plan_id),
        "title": g.title,
        "description": g.description,
        "intended_outcome": g.intended_outcome,
        "responsible_user_id": str(g.responsible_user_id) if g.responsible_user_id else None,
        "start_date": g.start_date.isoformat() if g.start_date else None,
        "target_date": g.target_date.isoformat() if g.target_date else None,
        "priority": g.priority,
        "status": g.status,
        "progress_notes": g.progress_notes,
        "achieved_at": g.achieved_at.isoformat() if g.achieved_at else None,
        "cancel_reason": g.cancel_reason,
        "created_by_user_id": str(g.created_by_user_id) if g.created_by_user_id else None,
        "updated_by_user_id": str(g.updated_by_user_id) if g.updated_by_user_id else None,
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "updated_at": g.updated_at.isoformat() if g.updated_at else None,
    }
    if sp_access.can_view_internal_notes(ctx):
        d["internal_notes"] = g.internal_notes
    else:
        d["internal_notes"] = None
    return d


def _assert_goal_plan(session: Session, ctx: OrganisationContext, plan: TenantSupportPlan, goal_id: uuid.UUID) -> SupportPlanGoal:
    g = session.get(SupportPlanGoal, goal_id)
    if g is None or g.organisation_id != ctx.organisation_id or g.plan_id != plan.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return g


def create_goal(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, body: GoalCreate
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    _assert_plan_manageable(plan, ctx)

    ref = _next_ref(session, ctx.organisation_id, SupportPlanGoal, "G")
    g = SupportPlanGoal(
        organisation_id=ctx.organisation_id,
        reference_number=ref,
        plan_id=plan.id,
        title=body.title.strip(),
        description=body.description.strip(),
        intended_outcome=body.intended_outcome,
        responsible_user_id=body.responsible_user_id,
        start_date=body.start_date,
        target_date=body.target_date,
        priority=body.priority,
        status="not_started",
        internal_notes=body.internal_notes,
        created_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
    )
    session.add(g)
    session.flush()
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "goal_created",
        f"Goal {ref}: {g.title}",
        actor_user_id=ctx.user_id,
        related_entity_type="goal",
        related_entity_id=g.id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_GOAL_CREATE,
        resource_type="support_plan_goal",
        resource_id=g.id,
        summary=f"Created goal {ref}",
        metadata={"plan_id": str(plan.id)},
    )
    session.flush()
    return _goal_view(g, ctx)


def list_goals(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID) -> list[dict[str, Any]]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    rows = list(
        session.scalars(
            select(SupportPlanGoal)
            .where(
                SupportPlanGoal.plan_id == plan_id,
                SupportPlanGoal.organisation_id == ctx.organisation_id,
            )
            .order_by(SupportPlanGoal.created_at.asc())
        )
    )
    return [_goal_view(g, ctx) for g in rows]


def get_goal(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, goal_id: uuid.UUID
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    g = _assert_goal_plan(session, ctx, plan, goal_id)
    return _goal_view(g, ctx)


def update_goal(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: GoalUpdate,
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    _assert_plan_manageable(plan, ctx)
    g = _assert_goal_plan(session, ctx, plan, goal_id)
    if g.status in {"achieved", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Goal is closed")

    if body.title is not None:
        g.title = body.title.strip()
    if body.description is not None:
        g.description = body.description.strip()
    if body.intended_outcome is not None:
        g.intended_outcome = body.intended_outcome
    if body.responsible_user_id is not None:
        g.responsible_user_id = body.responsible_user_id
    if body.start_date is not None:
        g.start_date = body.start_date
    if body.target_date is not None:
        old_td = g.target_date.isoformat() if g.target_date else None
        new_td = body.target_date.isoformat() if body.target_date else None
        _goal_field_change(
            session, ctx.organisation_id, g.id, "target_date", old_td, new_td, ctx.user_id
        )
        g.target_date = body.target_date
    if body.priority is not None:
        g.priority = body.priority
    if body.progress_notes is not None:
        g.progress_notes = body.progress_notes
    if body.internal_notes is not None:
        if not sp_access.can_view_internal_notes(ctx):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        g.internal_notes = body.internal_notes

    if body.status is not None:
        allowed = GOAL_TRANSITIONS.get(g.status, frozenset())
        if body.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invalid goal status transition: {g.status} -> {body.status}",
            )
        old_s = g.status
        g.status = body.status
        if body.status == "achieved":
            g.achieved_at = NOW()
        _goal_field_change(session, ctx.organisation_id, g.id, "status", old_s, body.status, ctx.user_id)
        _history(
            session,
            ctx.organisation_id,
            plan.id,
            "goal_status",
            f"Goal {g.reference_number} status {old_s} -> {body.status}",
            actor_user_id=ctx.user_id,
            related_entity_type="goal",
            related_entity_id=g.id,
        )
        _audit(
            session,
            ctx,
            action=audit_events.SUPPORT_PLAN_GOAL_STATUS,
            resource_type="support_plan_goal",
            resource_id=g.id,
            summary="Goal status changed",
            metadata={"from": old_s, "to": body.status},
        )

    g.updated_by_user_id = ctx.user_id
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "goal_updated",
        f"Goal {g.reference_number} updated",
        actor_user_id=ctx.user_id,
        related_entity_type="goal",
        related_entity_id=g.id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_GOAL_UPDATE,
        resource_type="support_plan_goal",
        resource_id=g.id,
        summary="Goal updated",
    )
    session.flush()
    return _goal_view(g, ctx)


def add_goal_progress_note(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: GoalProgressNoteCreate,
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    _assert_plan_manageable(plan, ctx)
    g = _assert_goal_plan(session, ctx, plan, goal_id)
    if body.show_to_tenant and not sp_access.can_view_internal_notes(ctx):
        # Tenants only see show_to_tenant notes; staff can create show_to_tenant
        pass
    note = SupportPlanGoalProgressNote(
        organisation_id=ctx.organisation_id,
        goal_id=g.id,
        author_user_id=ctx.user_id,
        body=body.body.strip(),
        show_to_tenant=body.show_to_tenant,
    )
    session.add(note)
    session.flush()
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "goal_progress_note",
        f"Progress note on goal {g.reference_number}",
        actor_user_id=ctx.user_id,
        related_entity_type="goal",
        related_entity_id=g.id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_GOAL_PROGRESS_NOTE,
        resource_type="support_plan_goal",
        resource_id=g.id,
        summary="Goal progress note added",
    )
    session.flush()
    return {
        "id": str(note.id),
        "goal_id": str(g.id),
        "body": note.body,
        "show_to_tenant": note.show_to_tenant,
        "author_user_id": str(note.author_user_id) if note.author_user_id else None,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


def list_goal_progress_notes(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, goal_id: uuid.UUID
) -> list[dict[str, Any]]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    g = _assert_goal_plan(session, ctx, plan, goal_id)
    stmt = select(SupportPlanGoalProgressNote).where(SupportPlanGoalProgressNote.goal_id == g.id)
    if ctx.role == HMoreRole.TENANT:
        stmt = stmt.where(SupportPlanGoalProgressNote.show_to_tenant.is_(True))
    rows = list(session.scalars(stmt.order_by(SupportPlanGoalProgressNote.created_at.asc())))
    return [
        {
            "id": str(r.id),
            "body": r.body,
            "show_to_tenant": r.show_to_tenant,
            "author_user_id": str(r.author_user_id) if r.author_user_id else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def achieve_goal(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: GoalAchieveBody,
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    _assert_plan_manageable(plan, ctx)
    g = _assert_goal_plan(session, ctx, plan, goal_id)
    allowed = GOAL_TRANSITIONS.get(g.status, frozenset())
    if "achieved" not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot achieve goal in status {g.status}",
        )
    old = g.status
    g.status = "achieved"
    g.achieved_at = NOW()
    if body.progress_notes:
        g.progress_notes = (g.progress_notes or "") + ("\n" if g.progress_notes else "") + body.progress_notes
    g.updated_by_user_id = ctx.user_id
    _goal_field_change(session, ctx.organisation_id, g.id, "status", old, "achieved", ctx.user_id)
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "goal_achieved",
        f"Goal {g.reference_number} achieved",
        actor_user_id=ctx.user_id,
        related_entity_type="goal",
        related_entity_id=g.id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_GOAL_STATUS,
        resource_type="support_plan_goal",
        resource_id=g.id,
        summary="Goal achieved",
        metadata={"from": old, "to": "achieved"},
    )
    session.flush()
    return _goal_view(g, ctx)


def cancel_goal(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: GoalCancelBody,
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    _assert_plan_manageable(plan, ctx)
    g = _assert_goal_plan(session, ctx, plan, goal_id)
    allowed = GOAL_TRANSITIONS.get(g.status, frozenset())
    if "cancelled" not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel goal in status {g.status}",
        )
    old = g.status
    g.status = "cancelled"
    g.cancel_reason = body.reason.strip()
    g.updated_by_user_id = ctx.user_id
    _goal_field_change(session, ctx.organisation_id, g.id, "status", old, "cancelled", ctx.user_id)
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "goal_cancelled",
        f"Goal {g.reference_number} cancelled",
        actor_user_id=ctx.user_id,
        related_entity_type="goal",
        related_entity_id=g.id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_GOAL_STATUS,
        resource_type="support_plan_goal",
        resource_id=g.id,
        summary="Goal cancelled",
        metadata={"from": old},
    )
    session.flush()
    return _goal_view(g, ctx)


def goal_change_history(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, goal_id: uuid.UUID
) -> list[dict[str, Any]]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    _assert_goal_plan(session, ctx, plan, goal_id)
    rows = list(
        session.scalars(
            select(SupportPlanGoalChange)
            .where(
                SupportPlanGoalChange.goal_id == goal_id,
                SupportPlanGoalChange.organisation_id == ctx.organisation_id,
            )
            .order_by(SupportPlanGoalChange.created_at.asc())
        )
    )
    return [
        {
            "id": str(r.id),
            "field_name": r.field_name,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "changed_by_user_id": str(r.changed_by_user_id) if r.changed_by_user_id else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def _ms_view(m: SupportPlanMilestone, ctx: OrganisationContext) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": str(m.id),
        "reference_number": m.reference_number,
        "goal_id": str(m.goal_id),
        "title": m.title,
        "description": m.description,
        "target_date": m.target_date.isoformat() if m.target_date else None,
        "responsible_user_id": str(m.responsible_user_id) if m.responsible_user_id else None,
        "status": m.status,
        "completion_notes": m.completion_notes,
        "completed_at": m.completed_at.isoformat() if m.completed_at else None,
        "cancel_reason": m.cancel_reason,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }
    if sp_access.can_view_internal_notes(ctx):
        d["internal_notes"] = m.internal_notes
    else:
        d["internal_notes"] = None
    return d


def _assert_milestone(
    session: Session, ctx: OrganisationContext, plan: TenantSupportPlan, goal_id: uuid.UUID, ms_id: uuid.UUID
) -> SupportPlanMilestone:
    g = _assert_goal_plan(session, ctx, plan, goal_id)
    m = session.get(SupportPlanMilestone, ms_id)
    if m is None or m.goal_id != g.id or m.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    return m


def create_milestone(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: MilestoneCreate,
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    _assert_plan_manageable(plan, ctx)
    _assert_goal_plan(session, ctx, plan, goal_id)
    ref = _next_ref(session, ctx.organisation_id, SupportPlanMilestone, "M")
    m = SupportPlanMilestone(
        organisation_id=ctx.organisation_id,
        reference_number=ref,
        goal_id=goal_id,
        title=body.title.strip(),
        description=body.description,
        target_date=body.target_date,
        responsible_user_id=body.responsible_user_id,
        status="pending",
        internal_notes=body.internal_notes,
        created_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
    )
    session.add(m)
    session.flush()
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "milestone_created",
        f"Milestone {ref}: {m.title}",
        actor_user_id=ctx.user_id,
        related_entity_type="milestone",
        related_entity_id=m.id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_MILESTONE_CREATE,
        resource_type="support_plan_milestone",
        resource_id=m.id,
        summary=f"Created milestone {ref}",
        metadata={"goal_id": str(goal_id)},
    )
    session.flush()
    return _ms_view(m, ctx)


def list_milestones(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, goal_id: uuid.UUID
) -> list[dict[str, Any]]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    _assert_goal_plan(session, ctx, plan, goal_id)
    rows = list(
        session.scalars(
            select(SupportPlanMilestone)
            .where(
                SupportPlanMilestone.goal_id == goal_id,
                SupportPlanMilestone.organisation_id == ctx.organisation_id,
            )
            .order_by(SupportPlanMilestone.target_date.asc().nulls_last())
        )
    )
    return [_ms_view(m, ctx) for m in rows]


def update_milestone(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    ms_id: uuid.UUID,
    body: MilestoneUpdate,
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    _assert_plan_manageable(plan, ctx)
    m = _assert_milestone(session, ctx, plan, goal_id, ms_id)
    if m.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Milestone is closed")

    if body.title is not None:
        m.title = body.title.strip()
    if body.description is not None:
        m.description = body.description
    if body.target_date is not None:
        old = m.target_date.isoformat() if m.target_date else None
        new = body.target_date.isoformat() if body.target_date else None
        _ms_field_change(session, ctx.organisation_id, m.id, "target_date", old, new, ctx.user_id)
        m.target_date = body.target_date
    if body.responsible_user_id is not None:
        m.responsible_user_id = body.responsible_user_id
    if body.completion_notes is not None:
        m.completion_notes = body.completion_notes
    if body.internal_notes is not None:
        if not sp_access.can_view_internal_notes(ctx):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        m.internal_notes = body.internal_notes

    if body.status is not None:
        allowed = MILESTONE_TRANSITIONS.get(m.status, frozenset())
        if body.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invalid milestone transition: {m.status} -> {body.status}",
            )
        old_s = m.status
        m.status = body.status
        if body.status == "completed":
            m.completed_at = NOW()
        _ms_field_change(session, ctx.organisation_id, m.id, "status", old_s, body.status, ctx.user_id)
        _history(
            session,
            ctx.organisation_id,
            plan.id,
            "milestone_status",
            f"Milestone {m.reference_number}: {old_s} -> {body.status}",
            actor_user_id=ctx.user_id,
            related_entity_type="milestone",
            related_entity_id=m.id,
        )
        _audit(
            session,
            ctx,
            action=audit_events.SUPPORT_PLAN_MILESTONE_UPDATE,
            resource_type="support_plan_milestone",
            resource_id=m.id,
            summary="Milestone status changed",
            metadata={"from": old_s, "to": body.status},
        )

    m.updated_by_user_id = ctx.user_id
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_MILESTONE_UPDATE,
        resource_type="support_plan_milestone",
        resource_id=m.id,
        summary="Milestone updated",
    )
    session.flush()
    return _ms_view(m, ctx)


def complete_milestone(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    ms_id: uuid.UUID,
    body: MilestoneCompleteBody,
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    _assert_plan_manageable(plan, ctx)
    m = _assert_milestone(session, ctx, plan, goal_id, ms_id)
    allowed = MILESTONE_TRANSITIONS.get(m.status, frozenset())
    if "completed" not in allowed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot complete milestone")
    old = m.status
    m.status = "completed"
    m.completed_at = NOW()
    if body.completion_notes:
        m.completion_notes = body.completion_notes
    m.updated_by_user_id = ctx.user_id
    _ms_field_change(session, ctx.organisation_id, m.id, "status", old, "completed", ctx.user_id)
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "milestone_completed",
        f"Milestone {m.reference_number} completed",
        actor_user_id=ctx.user_id,
        related_entity_type="milestone",
        related_entity_id=m.id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_MILESTONE_COMPLETE,
        resource_type="support_plan_milestone",
        resource_id=m.id,
        summary="Milestone completed",
        metadata={"from": old},
    )
    session.flush()
    return _ms_view(m, ctx)


def cancel_milestone(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    ms_id: uuid.UUID,
    body: MilestoneCancelBody,
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    _assert_plan_manageable(plan, ctx)
    m = _assert_milestone(session, ctx, plan, goal_id, ms_id)
    allowed = MILESTONE_TRANSITIONS.get(m.status, frozenset())
    if "cancelled" not in allowed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot cancel milestone")
    old = m.status
    m.status = "cancelled"
    m.cancel_reason = body.reason.strip()
    m.updated_by_user_id = ctx.user_id
    _ms_field_change(session, ctx.organisation_id, m.id, "status", old, "cancelled", ctx.user_id)
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "milestone_cancelled",
        f"Milestone {m.reference_number} cancelled",
        actor_user_id=ctx.user_id,
        related_entity_type="milestone",
        related_entity_id=m.id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_MILESTONE_CANCEL,
        resource_type="support_plan_milestone",
        resource_id=m.id,
        summary="Milestone cancelled",
        metadata={"from": old},
    )
    session.flush()
    return _ms_view(m, ctx)


def milestone_history(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, goal_id: uuid.UUID, ms_id: uuid.UUID
) -> list[dict[str, Any]]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    _assert_milestone(session, ctx, plan, goal_id, ms_id)
    rows = list(
        session.scalars(
            select(SupportPlanMilestoneChange)
            .where(
                SupportPlanMilestoneChange.milestone_id == ms_id,
                SupportPlanMilestoneChange.organisation_id == ctx.organisation_id,
            )
            .order_by(SupportPlanMilestoneChange.created_at.asc())
        )
    )
    return [
        {
            "id": str(r.id),
            "field_name": r.field_name,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "changed_by_user_id": str(r.changed_by_user_id) if r.changed_by_user_id else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def _review_view(r: SupportPlanReview, ctx: OrganisationContext) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": str(r.id),
        "reference_number": r.reference_number,
        "plan_id": str(r.plan_id),
        "tenant_id": str(r.tenant_id),
        "review_type": r.review_type,
        "review_date": r.review_date.isoformat() if r.review_date else None,
        "reviewer_user_id": str(r.reviewer_user_id),
        "goals_reviewed": r.goals_reviewed,
        "milestones_reviewed": r.milestones_reviewed,
        "progress_summary": r.progress_summary,
        "achievements": r.achievements,
        "challenges": r.challenges,
        "recommended_actions": r.recommended_actions,
        "required_plan_changes": r.required_plan_changes,
        "follow_up_actions": r.follow_up_actions,
        "next_review_date": r.next_review_date.isoformat() if r.next_review_date else None,
        "status": r.status,
        "tenant_summary": r.tenant_summary,
        "finalised_at": r.finalised_at.isoformat() if r.finalised_at else None,
        "created_by_user_id": str(r.created_by_user_id) if r.created_by_user_id else None,
        "updated_by_user_id": str(r.updated_by_user_id) if r.updated_by_user_id else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
    if sp_access.can_view_internal_notes(ctx):
        d["internal_notes"] = r.internal_notes
    else:
        d["internal_notes"] = None
    return d


def create_review(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, body: ReviewCreate
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)

    ref = _next_ref(session, ctx.organisation_id, SupportPlanReview, "R")
    r = SupportPlanReview(
        organisation_id=ctx.organisation_id,
        reference_number=ref,
        plan_id=plan.id,
        tenant_id=plan.tenant_id,
        review_type=body.review_type,
        review_date=body.review_date,
        reviewer_user_id=ctx.user_id,
        goals_reviewed=body.goals_reviewed,
        milestones_reviewed=body.milestones_reviewed,
        progress_summary=body.progress_summary,
        achievements=body.achievements,
        challenges=body.challenges,
        recommended_actions=body.recommended_actions,
        required_plan_changes=body.required_plan_changes,
        follow_up_actions=body.follow_up_actions,
        next_review_date=body.next_review_date,
        status=body.status,
        internal_notes=body.internal_notes,
        tenant_summary=body.tenant_summary,
        created_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
    )
    session.add(r)
    session.flush()
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "review_created",
        f"Review {ref} ({body.review_type})",
        actor_user_id=ctx.user_id,
        related_entity_type="review",
        related_entity_id=r.id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_REVIEW_CREATE,
        resource_type="support_plan_review",
        resource_id=r.id,
        summary=f"Created review {ref}",
        metadata={"plan_id": str(plan.id)},
    )
    session.flush()
    return _review_view(r, ctx)


def list_reviews(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    review_type: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    stmt = select(SupportPlanReview).where(
        SupportPlanReview.plan_id == plan_id,
        SupportPlanReview.organisation_id == ctx.organisation_id,
    )
    if review_type:
        stmt = stmt.where(SupportPlanReview.review_type == review_type)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(stmt.order_by(SupportPlanReview.review_date.desc()).offset(offset).limit(limit))
    )
    return ([_review_view(r, ctx) for r in rows], total)


def get_review(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, review_id: uuid.UUID
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    r = session.get(SupportPlanReview, review_id)
    if r is None or r.plan_id != plan_id or r.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return _review_view(r, ctx)


def update_review(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    review_id: uuid.UUID,
    body: ReviewUpdate,
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    r = session.get(SupportPlanReview, review_id)
    if r is None or r.plan_id != plan_id or r.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if r.status == "finalised":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Finalised reviews cannot be modified; create a new review",
        )
    if r.status == "superseded":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review is superseded")

    if body.review_date is not None:
        r.review_date = body.review_date
    if body.goals_reviewed is not None:
        r.goals_reviewed = body.goals_reviewed
    if body.milestones_reviewed is not None:
        r.milestones_reviewed = body.milestones_reviewed
    if body.progress_summary is not None:
        r.progress_summary = body.progress_summary
    if body.achievements is not None:
        r.achievements = body.achievements
    if body.challenges is not None:
        r.challenges = body.challenges
    if body.recommended_actions is not None:
        r.recommended_actions = body.recommended_actions
    if body.required_plan_changes is not None:
        r.required_plan_changes = body.required_plan_changes
    if body.follow_up_actions is not None:
        r.follow_up_actions = body.follow_up_actions
    if body.next_review_date is not None:
        r.next_review_date = body.next_review_date
    if body.tenant_summary is not None:
        r.tenant_summary = body.tenant_summary
    if body.internal_notes is not None:
        if not sp_access.can_view_internal_notes(ctx):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        r.internal_notes = body.internal_notes

    if body.status is not None:
        allowed = REVIEW_TRANSITIONS.get(r.status, frozenset())
        if body.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invalid review status transition: {r.status} -> {body.status}",
            )
        r.status = body.status

    r.updated_by_user_id = ctx.user_id
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_REVIEW_UPDATE,
        resource_type="support_plan_review",
        resource_id=r.id,
        summary="Review updated",
    )
    session.flush()
    return _review_view(r, ctx)


def finalise_review(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, review_id: uuid.UUID
) -> dict[str, Any]:
    sp_access.require_review_finalise(ctx)
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
    r = session.get(SupportPlanReview, review_id)
    if r is None or r.plan_id != plan_id or r.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if r.status == "finalised":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already finalised")
    if r.status not in {"draft", "in_progress"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review cannot be finalised")
    r.status = "finalised"
    r.finalised_at = NOW()
    r.updated_by_user_id = ctx.user_id
    if r.next_review_date is not None:
        plan.planned_review_date = r.next_review_date
    _history(
        session,
        ctx.organisation_id,
        plan.id,
        "review_finalised",
        f"Review {r.reference_number} finalised",
        actor_user_id=ctx.user_id,
        related_entity_type="review",
        related_entity_id=r.id,
    )
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_REVIEW_FINALISE,
        resource_type="support_plan_review",
        resource_id=r.id,
        summary="Review finalised",
    )
    session.flush()
    return _review_view(r, ctx)


def review_history(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID
) -> list[dict[str, Any]]:
    items, _ = list_reviews(session, ctx, tenant_id, plan_id, page=1, page_size=500)
    return sorted(items, key=lambda x: x.get("review_date") or "")


def progress_dashboard(
    session: Session,
    ctx: OrganisationContext,
    *,
    tenant_id: uuid.UUID | None,
    worker_user_id: uuid.UUID | None,
    plan_status: str | None,
    review_period_start: date | None,
    review_period_end: date | None,
) -> dict[str, Any]:
    """Aggregates for org; optional tenant and worker filters."""
    if ctx.role not in {
        HMoreRole.SUPER_ADMIN,
        HMoreRole.ORGANISATION_ADMIN,
        HMoreRole.SUPPORT_WORKER,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    sp_access.require_support_plan_read(ctx)

    from app.db.models.support_ops import CaseAssignment

    effective_worker = worker_user_id
    if ctx.role == HMoreRole.SUPPORT_WORKER and effective_worker is None:
        effective_worker = ctx.user_id

    p_stmt = select(TenantSupportPlan).where(TenantSupportPlan.organisation_id == ctx.organisation_id)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        caseload = list(
            session.scalars(
                select(CaseAssignment.tenant_id).where(
                    CaseAssignment.organisation_id == ctx.organisation_id,
                    CaseAssignment.support_worker_user_id == ctx.user_id,
                    CaseAssignment.status == "active",
                )
            )
        )
        if not caseload:
            p_stmt = p_stmt.where(false())
        elif tenant_id is None:
            p_stmt = p_stmt.where(TenantSupportPlan.tenant_id.in_(caseload))
    if tenant_id:
        sp_access.assert_tenant_scope(session, ctx, tenant_id)
        p_stmt = p_stmt.where(TenantSupportPlan.tenant_id == tenant_id)
    if effective_worker:
        p_stmt = p_stmt.where(
            or_(
                TenantSupportPlan.responsible_worker_user_id == effective_worker,
                TenantSupportPlan.id.in_(
                    select(SupportPlanContributor.plan_id).where(
                        SupportPlanContributor.user_id == effective_worker
                    )
                ),
            )
        )
    if plan_status:
        p_stmt = p_stmt.where(TenantSupportPlan.status == plan_status)

    plans = list(session.scalars(p_stmt))
    plan_ids = [p.id for p in plans]

    today = date.today()

    total_plans = len(plans)
    active_plans = sum(1 for p in plans if p.status == "active")
    under_review_plans = sum(1 for p in plans if p.status == "under_review")
    on_hold_plans = sum(1 for p in plans if p.status == "on_hold")

    goals_in_progress = 0
    goals_achieved = 0
    goals_at_risk = 0
    pending_ms = 0
    overdue_ms = 0

    if plan_ids:
        g_stmt = select(SupportPlanGoal).where(SupportPlanGoal.plan_id.in_(plan_ids))
        goals = list(session.scalars(g_stmt))
        goals_in_progress = sum(1 for g in goals if g.status == "in_progress")
        goals_achieved = sum(1 for g in goals if g.status == "achieved")
        goals_at_risk = sum(1 for g in goals if g.status == "at_risk")
        goal_ids = [g.id for g in goals]
        if goal_ids:
            ms_rows = list(session.scalars(select(SupportPlanMilestone).where(SupportPlanMilestone.goal_id.in_(goal_ids))))
            pending_ms = sum(1 for m in ms_rows if m.status in {"pending", "in_progress"})
            overdue_ms = sum(
                1
                for m in ms_rows
                if m.target_date
                and m.target_date < today
                and m.status not in {"completed", "cancelled"}
            )

    r_stmt = select(SupportPlanReview).where(SupportPlanReview.organisation_id == ctx.organisation_id)
    if plan_ids:
        r_stmt = r_stmt.where(SupportPlanReview.plan_id.in_(plan_ids))
    else:
        r_stmt = r_stmt.where(false())

    if review_period_start:
        r_stmt = r_stmt.where(SupportPlanReview.review_date >= review_period_start)
    if review_period_end:
        r_stmt = r_stmt.where(SupportPlanReview.review_date <= review_period_end)

    reviews = list(session.scalars(r_stmt))
    upcoming_reviews = sum(
        1
        for p in plans
        if p.planned_review_date
        and p.planned_review_date >= today
        and p.status in {"active", "under_review", "on_hold"}
    )
    overdue_reviews = sum(
        1
        for p in plans
        if p.planned_review_date
        and p.planned_review_date < today
        and p.status in {"active", "under_review", "on_hold"}
    )

    return {
        "total_plans": total_plans,
        "active_plans": active_plans,
        "plans_under_review": under_review_plans,
        "plans_on_hold": on_hold_plans,
        "goals_in_progress": goals_in_progress,
        "goals_achieved": goals_achieved,
        "goals_at_risk": goals_at_risk,
        "pending_milestones": pending_ms,
        "overdue_milestones": overdue_ms,
        "upcoming_reviews": upcoming_reviews,
        "overdue_reviews": overdue_reviews,
        "finalised_reviews_in_period": sum(1 for r in reviews if r.status == "finalised"),
    }


def _progress_export_lines(
    session: Session,
    ctx: OrganisationContext,
    plan: TenantSupportPlan,
    *,
    include_internal: bool,
) -> list[str]:
    lines = [
        f"Support plan {plan.reference_number}",
        f"Title: {plan.title}",
        f"Status: {plan.status}",
        f"Tenant: {plan.tenant_id}",
    ]
    if plan.support_objectives:
        lines.append(f"Objectives: {plan.support_objectives[:500]}")
    goals = list(
        session.scalars(
            select(SupportPlanGoal).where(SupportPlanGoal.plan_id == plan.id).order_by(SupportPlanGoal.reference_number)
        )
    )
    lines.append("")
    lines.append("Goals:")
    for g in goals:
        lines.append(f"  {g.reference_number} {g.title} — {g.status}")
        if g.target_date:
            lines.append(f"    Target: {g.target_date}")
    milestones: list[SupportPlanMilestone] = []
    for g in goals:
        milestones.extend(
            list(
                session.scalars(
                    select(SupportPlanMilestone).where(SupportPlanMilestone.goal_id == g.id)
                )
            )
        )
    lines.append("")
    lines.append("Milestones:")
    for m in milestones:
        lines.append(f"  {m.reference_number} {m.title} — {m.status}")
    reviews = list(
        session.scalars(
            select(SupportPlanReview)
            .where(SupportPlanReview.plan_id == plan.id, SupportPlanReview.status == "finalised")
            .order_by(SupportPlanReview.review_date.desc())
            .limit(12)
        )
    )
    lines.append("")
    lines.append("Recent finalised reviews:")
    for r in reviews:
        lines.append(f"  {r.reference_number} ({r.review_type}) {r.review_date}: {r.progress_summary or ''}"[:600])
        if r.achievements:
            lines.append(f"    Achievements: {r.achievements[:300]}")
        if r.challenges:
            lines.append(f"    Challenges: {r.challenges[:300]}")
    if include_internal and sp_access.can_view_internal_notes(ctx) and plan.internal_notes:
        lines.append("")
        lines.append(f"Internal notes: {plan.internal_notes[:400]}")
    lines.append("")
    lines.append(f"Generated at {NOW().isoformat()} UTC")
    lines.append("This document is a case-management summary, not a statutory assessment or legal certification.")
    return lines


def create_progress_export(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, body: ExportCreate
) -> dict[str, Any]:
    sp_access.require_export(ctx)
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)

    if body.include_internal and not sp_access.can_view_internal_notes(ctx):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot include internal content")

    title = f"Support plan progress — {plan.reference_number}"
    lines = _progress_export_lines(session, ctx, plan, include_internal=body.include_internal)
    pdf_bytes = build_simple_pdf(title, lines)

    meta = file_service.upload_file(
        session,
        ctx,
        filename=f"support-plan-{plan.reference_number}.pdf",
        declared_content_type="application/pdf",
        data=pdf_bytes,
        resource_type="support_plan_progress_export",
        resource_id=str(plan.id),
    )
    file_uuid = uuid.UUID(meta["id"])
    row = SupportPlanProgressExport(
        organisation_id=ctx.organisation_id,
        plan_id=plan.id,
        file_id=file_uuid,
        generated_by_user_id=ctx.user_id,
        include_internal=body.include_internal,
    )
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.SUPPORT_PLAN_EXPORT_GENERATE,
        resource_type="support_plan_progress_export",
        resource_id=row.id,
        summary="Generated support plan progress PDF",
        metadata={"plan_id": str(plan.id), "file_id": str(file_uuid)},
    )
    session.flush()
    return {
        "export_id": str(row.id),
        "file": meta,
        "plan_id": str(plan.id),
        "include_internal": body.include_internal,
    }


def get_export_metadata(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, export_id: uuid.UUID
) -> dict[str, Any]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    row = session.get(SupportPlanProgressExport, export_id)
    if row is None or row.plan_id != plan_id or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
    meta = file_service.get_file_metadata(session, ctx, row.file_id)
    return {"export_id": str(row.id), "file": meta, "include_internal": row.include_internal}


def download_export(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID, export_id: uuid.UUID
) -> tuple[Any, bytes, str]:
    plan = _get_plan(session, ctx, plan_id)
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support plan not found")
    sp_access.assert_tenant_scope(session, ctx, tenant_id)
    sp_access.require_export(ctx)
    row = session.get(SupportPlanProgressExport, export_id)
    if row is None or row.plan_id != plan_id or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")

    fmeta, data = file_service.download_file(session, ctx, row.file_id)
    record_event(
        session,
        action=audit_events.SUPPORT_PLAN_EXPORT_DOWNLOAD,
        resource_type="support_plan_progress_export",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Downloaded support plan progress export",
        metadata={"file_id": str(row.file_id)},
        raise_on_error=False,
    )
    session.flush()
    return fmeta, data, f"support-plan-{plan.reference_number}-export.pdf"

