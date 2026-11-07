"""F3.7 draft generation, review, and apply through existing support-plan services."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event, record_event_independent
from app.case_summaries.compose import source_fingerprint
from app.case_summaries.sources import collect_case_packet
from app.core.config import Settings, get_settings
from app.db.models.case_summaries import CaseSummary
from app.db.models.support_plan_drafts import SupportPlanDraft
from app.db.models.support_plans import SupportPlanGoal, TenantSupportPlan
from app.support_plan_drafts import access as draft_access
from app.support_plan_drafts.ai_client import execute_support_plan_draft
from app.support_plan_drafts.compose import compose_support_plan_draft, validate_draft_content
from app.support_plans.schemas import GoalCreate, MilestoneCreate
from app.support_plans import service as plan_service
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation

OPEN_STATUSES = {"draft", "pending_review", "approved"}


def _denied(ctx: OrganisationContext, *, tenant_id: uuid.UUID | None = None, draft_id: uuid.UUID | None = None) -> None:
    record_event_independent(
        action=audit_events.AI_SUPPORT_PLAN_DRAFT_DENIED,
        resource_type="support_plan_draft" if draft_id else "tenant",
        resource_id=str(draft_id or tenant_id or ""),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.DENIED,
        summary="Support plan draft access denied",
        metadata={"tenant_id": str(tenant_id) if tenant_id else None, "draft_id": str(draft_id) if draft_id else None},
    )


def _guard(ctx: OrganisationContext, fn, *, tenant_id: uuid.UUID | None = None, draft_id: uuid.UUID | None = None):
    try:
        return fn()
    except HTTPException as exc:
        if exc.status_code == 403:
            _denied(ctx, tenant_id=tenant_id, draft_id=draft_id)
        raise


def _public(row: SupportPlanDraft, *, current_fingerprint: str | None = None) -> dict[str, Any]:
    stale = current_fingerprint is not None and current_fingerprint != row.source_fingerprint
    return {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "tenant_id": str(row.tenant_id),
        "plan_id": str(row.plan_id) if row.plan_id else None,
        "version_number": row.version_number,
        "status": row.status,
        "content_origin": row.content_origin,
        "ai_generated": True,
        "human_edited": row.content_origin == "human_edited",
        "is_operational_plan": False,
        "content": row.content_json or {},
        "source_refs": row.source_refs_json or [],
        "generation_method": row.generation_method,
        "prompt_id": row.prompt_id,
        "prompt_version": row.prompt_version,
        "provider": row.provider,
        "model_id": row.model_id,
        "feature_id": row.feature_id,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        "requested_by_user_id": str(row.requested_by_user_id) if row.requested_by_user_id else None,
        "edited_by_user_id": str(row.edited_by_user_id) if row.edited_by_user_id else None,
        "edited_at": row.edited_at.isoformat() if row.edited_at else None,
        "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
        "reviewed_by_user_id": str(row.reviewed_by_user_id) if row.reviewed_by_user_id else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "review_comment": row.review_comment,
        "applied_by_user_id": str(row.applied_by_user_id) if row.applied_by_user_id else None,
        "applied_at": row.applied_at.isoformat() if row.applied_at else None,
        "application": row.application_json,
        "stale": stale,
        "error_message": row.error_message,
    }


def _latest(session: Session, organisation_id: uuid.UUID, tenant_id: uuid.UUID) -> SupportPlanDraft | None:
    return session.scalars(
        select(SupportPlanDraft)
        .where(SupportPlanDraft.organisation_id == organisation_id, SupportPlanDraft.tenant_id == tenant_id)
        .order_by(SupportPlanDraft.version_number.desc())
        .limit(1)
    ).first()


def _next_version(session: Session, organisation_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
    current = session.scalar(
        select(func.max(SupportPlanDraft.version_number)).where(
            SupportPlanDraft.organisation_id == organisation_id,
            SupportPlanDraft.tenant_id == tenant_id,
        )
    )
    return int(current or 0) + 1


def _enrich(session: Session, packet: dict[str, Any], organisation_id: uuid.UUID, tenant_id: uuid.UUID) -> dict[str, Any]:
    summary = session.scalars(
        select(CaseSummary)
        .where(
            CaseSummary.organisation_id == organisation_id,
            CaseSummary.tenant_id == tenant_id,
            CaseSummary.status == "approved",
        )
        .order_by(CaseSummary.version_number.desc())
        .limit(1)
    ).first()
    enriched = dict(packet)
    sources = list(packet.get("sources") or [])
    approved = []
    if summary is not None:
        approved.append(
            {
                "id": str(summary.id),
                "version_number": summary.version_number,
                "status": summary.status,
            }
        )
        sources.append({"type": "case_summary", "id": str(summary.id), "updated_at": None, "version": summary.version_number})
    enriched["approved_case_summaries"] = approved
    enriched["sources"] = sources
    return enriched


def _load_plan(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, plan_id: uuid.UUID | None) -> TenantSupportPlan | None:
    if plan_id is None:
        return None
    plan = session.get(TenantSupportPlan, plan_id)
    if plan is None or plan.organisation_id != ctx.organisation_id or plan.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Support plan not found")
    return plan


def _goal_count(session: Session, plan_id: uuid.UUID) -> int:
    return int(
        session.scalar(select(func.count()).select_from(SupportPlanGoal).where(SupportPlanGoal.plan_id == plan_id)) or 0
    )


def generate_draft(
    session: Session,
    ctx: OrganisationContext,
    *,
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID | None = None,
    force: bool = False,
    settings: Settings | None = None,
) -> dict[str, Any]:
    _guard(ctx, lambda: draft_access.require_run(ctx), tenant_id=tenant_id)
    settings = settings or get_settings()
    tenant = _guard(ctx, lambda: draft_access.assert_case_access(session, ctx, tenant_id), tenant_id=tenant_id)
    plan = _load_plan(session, ctx, tenant.id, plan_id)
    before_goals = _goal_count(session, plan.id) if plan else 0
    before_status = plan.status if plan else None
    packet = _enrich(session, collect_case_packet(session, organisation_id=ctx.organisation_id, tenant=tenant), ctx.organisation_id, tenant.id)
    fingerprint = source_fingerprint(packet)
    existing = _latest(session, ctx.organisation_id, tenant.id)
    if (
        existing
        and not force
        and existing.source_fingerprint == fingerprint
        and existing.plan_id == (plan.id if plan else None)
        and existing.status in OPEN_STATUSES
    ):
        return {**_public(existing, current_fingerprint=fingerprint), "idempotent": True}

    record_event(
        session,
        action=audit_events.AI_SUPPORT_PLAN_DRAFT_REQUESTED,
        resource_type="tenant",
        resource_id=str(tenant.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Support plan draft requested",
        metadata={"tenant_id": str(tenant.id), "plan_id": str(plan.id) if plan else None, "force": force},
        raise_on_error=False,
    )
    try:
        if (settings.ai_service_base_url or "").strip():
            raw = execute_support_plan_draft(
                settings,
                organisation_id=ctx.organisation_id,
                user_id=ctx.user_id,
                role=ctx.role.value,
                packet=packet,
            )
            result = (raw.get("result") or {}).get("draft") or {}
            prompt_id = (raw.get("result") or {}).get("prompt_id")
            prompt_version = (raw.get("result") or {}).get("prompt_version")
            provider = (raw.get("result") or {}).get("provider")
            model_id = (raw.get("result") or {}).get("model_id")
            content = validate_draft_content(result.get("content") or result, packet)
            generation_method = result.get("generation_method") or "llm"
        else:
            if settings.is_production:
                raise HTTPException(status_code=503, detail="AI service is not configured")
            composed = compose_support_plan_draft(packet)
            content = composed["content"]
            prompt_id = "hmore.support_plan_draft.v1"
            prompt_version = "1.0.0"
            provider = "heuristic"
            model_id = "structured_heuristic_v1"
            generation_method = "structured_heuristic"
    except HTTPException as exc:
        record_event(
            session,
            action=audit_events.AI_SUPPORT_PLAN_DRAFT_FAILED,
            resource_type="tenant",
            resource_id=str(tenant.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.DENIED if exc.status_code == 402 else AuditOutcome.FAILURE,
            summary="Support plan draft was not generated",
            metadata={"tenant_id": str(tenant.id), "status_code": exc.status_code},
            raise_on_error=False,
        )
        raise
    except ValueError as exc:
        record_event(
            session,
            action=audit_events.AI_SUPPORT_PLAN_DRAFT_FAILED,
            resource_type="tenant",
            resource_id=str(tenant.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Support plan draft failed validation",
            metadata={"tenant_id": str(tenant.id)},
            raise_on_error=False,
        )
        raise HTTPException(status_code=422, detail="AI draft output was rejected") from exc

    row = SupportPlanDraft(
        id=uuid.uuid4(),
        organisation_id=ctx.organisation_id,
        tenant_id=tenant.id,
        plan_id=plan.id if plan else None,
        version_number=_next_version(session, ctx.organisation_id, tenant.id),
        source_fingerprint=fingerprint,
        status="draft",
        content_origin="ai",
        content_json=content,
        source_refs_json=list(packet.get("sources") or []),
        requested_by_user_id=ctx.user_id,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider,
        model_id=model_id,
        generation_method=generation_method,
        generated_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.flush()
    if plan is not None:
        session.refresh(plan)
        if plan.status != before_status or _goal_count(session, plan.id) != before_goals:
            raise HTTPException(status_code=500, detail="Draft generation must not change the support plan")
    record_event(
        session,
        action=audit_events.AI_SUPPORT_PLAN_DRAFT_REGENERATED if force else audit_events.AI_SUPPORT_PLAN_DRAFT_COMPLETED,
        resource_type="support_plan_draft",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Support plan draft generated",
        metadata={"tenant_id": str(tenant.id), "version_number": row.version_number, "plan_id": str(row.plan_id) if row.plan_id else None},
        raise_on_error=False,
    )
    return {**_public(row, current_fingerprint=fingerprint), "idempotent": False}


def _get_row(session: Session, ctx: OrganisationContext, draft_id: uuid.UUID) -> SupportPlanDraft:
    _guard(ctx, lambda: draft_access.require_read(ctx), draft_id=draft_id)
    row = session.get(SupportPlanDraft, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Support plan draft not found")
    try:
        assert_same_organisation(ctx, row.organisation_id)
    except HTTPException as exc:
        if exc.status_code == 403:
            _denied(ctx, tenant_id=row.tenant_id, draft_id=row.id)
        raise
    _guard(ctx, lambda: draft_access.assert_case_access(session, ctx, row.tenant_id), tenant_id=row.tenant_id, draft_id=row.id)
    return row


def get_draft(session: Session, ctx: OrganisationContext, draft_id: uuid.UUID) -> dict[str, Any]:
    row = _get_row(session, ctx, draft_id)
    tenant = draft_access.assert_case_access(session, ctx, row.tenant_id)
    packet = _enrich(session, collect_case_packet(session, organisation_id=ctx.organisation_id, tenant=tenant), ctx.organisation_id, tenant.id)
    return _public(row, current_fingerprint=source_fingerprint(packet))


def list_drafts(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: draft_access.require_read(ctx), tenant_id=tenant_id)
    _guard(ctx, lambda: draft_access.assert_case_access(session, ctx, tenant_id), tenant_id=tenant_id)
    rows = list(
        session.scalars(
            select(SupportPlanDraft)
            .where(SupportPlanDraft.organisation_id == ctx.organisation_id, SupportPlanDraft.tenant_id == tenant_id)
            .order_by(SupportPlanDraft.version_number.desc())
        )
    )
    return {"items": [_public(row) for row in rows]}


def edit_draft(session: Session, ctx: OrganisationContext, draft_id: uuid.UUID, content: dict[str, Any]) -> dict[str, Any]:
    _guard(ctx, lambda: draft_access.require_run(ctx), draft_id=draft_id)
    row = session.get(SupportPlanDraft, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Support plan draft not found")
    assert_same_organisation(ctx, row.organisation_id)
    _guard(ctx, lambda: draft_access.assert_case_access(session, ctx, row.tenant_id), tenant_id=row.tenant_id, draft_id=row.id)
    if row.status not in {"draft", "pending_review"}:
        raise HTTPException(status_code=409, detail="This draft can no longer be edited")
    packet = {"sources": row.source_refs_json or []}
    try:
        validated = validate_draft_content(content, packet)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Draft edit was rejected") from exc
    row.content_json = validated
    row.content_origin = "human_edited"
    row.edited_by_user_id = ctx.user_id
    row.edited_at = datetime.now(timezone.utc)
    row.status = "draft"
    row.submitted_at = None
    session.flush()
    record_event(
        session,
        action=audit_events.AI_SUPPORT_PLAN_DRAFT_EDITED,
        resource_type="support_plan_draft",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Support plan draft edited",
        metadata={"version_number": row.version_number},
        raise_on_error=False,
    )
    return _public(row)


def submit_draft(session: Session, ctx: OrganisationContext, draft_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: draft_access.require_run(ctx), draft_id=draft_id)
    row = _get_row(session, ctx, draft_id)
    if row.status != "draft":
        raise HTTPException(status_code=409, detail="Only a draft can be submitted")
    row.status = "pending_review"
    row.submitted_at = datetime.now(timezone.utc)
    session.flush()
    record_event(
        session,
        action=audit_events.AI_SUPPORT_PLAN_DRAFT_SUBMITTED,
        resource_type="support_plan_draft",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Support plan draft submitted for review",
        metadata={"version_number": row.version_number},
        raise_on_error=False,
    )
    return _public(row)


def decide_draft(
    session: Session,
    ctx: OrganisationContext,
    draft_id: uuid.UUID,
    *,
    decision: str,
    review_comment: str | None,
) -> dict[str, Any]:
    _guard(ctx, lambda: draft_access.require_review(ctx), draft_id=draft_id)
    row = session.get(SupportPlanDraft, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Support plan draft not found")
    assert_same_organisation(ctx, row.organisation_id)
    _guard(ctx, lambda: draft_access.assert_case_access(session, ctx, row.tenant_id), tenant_id=row.tenant_id, draft_id=row.id)
    if row.status != "pending_review":
        raise HTTPException(status_code=409, detail="Draft is not awaiting review")
    plan = _load_plan(session, ctx, row.tenant_id, row.plan_id)
    before_goals = _goal_count(session, plan.id) if plan else 0
    before_status = plan.status if plan else None
    row.status = "approved" if decision == "approve" else "rejected"
    row.reviewed_by_user_id = ctx.user_id
    row.reviewed_at = datetime.now(timezone.utc)
    row.review_comment = review_comment
    session.flush()
    if plan is not None and (plan.status != before_status or _goal_count(session, plan.id) != before_goals):
        raise HTTPException(status_code=500, detail="Review must not change the support plan")
    record_event(
        session,
        action=audit_events.AI_SUPPORT_PLAN_DRAFT_APPROVED if decision == "approve" else audit_events.AI_SUPPORT_PLAN_DRAFT_REJECTED,
        resource_type="support_plan_draft",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Support plan draft {row.status}",
        metadata={"version_number": row.version_number},
        raise_on_error=False,
    )
    return _public(row)


def apply_draft(session: Session, ctx: OrganisationContext, draft_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: draft_access.require_read(ctx), draft_id=draft_id)
    row = session.get(SupportPlanDraft, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Support plan draft not found")
    assert_same_organisation(ctx, row.organisation_id)
    tenant = _guard(
        ctx, lambda: draft_access.assert_can_apply(session, ctx, row.tenant_id), tenant_id=row.tenant_id, draft_id=row.id
    )
    if row.status == "applied":
        raise HTTPException(status_code=409, detail="This draft was already applied")
    if row.status != "approved":
        raise HTTPException(status_code=409, detail="Only an approved draft can be applied")
    if row.plan_id is None:
        raise HTTPException(status_code=409, detail="An existing support plan is required before suggestions can be added")
    packet = _enrich(
        session,
        collect_case_packet(session, organisation_id=ctx.organisation_id, tenant=tenant),
        ctx.organisation_id,
        tenant.id,
    )
    if source_fingerprint(packet) != row.source_fingerprint:
        raise HTTPException(status_code=409, detail="Source records changed. Regenerate the draft before applying it.")
    plan = _load_plan(session, ctx, row.tenant_id, row.plan_id)
    if plan is None or plan.status not in plan_service.PLAN_EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="The support plan cannot accept new goals in its current status")
    goals = (row.content_json or {}).get("suggested_goals") or []
    if not goals:
        raise HTTPException(status_code=409, detail="The draft has no suggestions to add")
    before_status = plan.status
    created_goals: list[str] = []
    created_milestones: list[str] = []
    try:
        for item in goals:
            created = plan_service.create_goal(
                session,
                ctx,
                row.tenant_id,
                plan.id,
                GoalCreate(
                    title=item["title"],
                    description=_goal_description(item),
                    intended_outcome=item.get("intended_outcome"),
                    responsible_user_id=None,
                    priority="normal",
                ),
            )
            created_goals.append(created["id"])
            for milestone in item.get("milestones") or []:
                made = plan_service.create_milestone(
                    session,
                    ctx,
                    row.tenant_id,
                    plan.id,
                    uuid.UUID(created["id"]),
                    MilestoneCreate(
                        title=milestone["title"],
                        description=milestone.get("description"),
                        target_date=None,
                        responsible_user_id=None,
                    ),
                )
                created_milestones.append(made["id"])
    except HTTPException as exc:
        record_event(
            session,
            action=audit_events.AI_SUPPORT_PLAN_DRAFT_APPLY_FAILED,
            resource_type="support_plan_draft",
            resource_id=str(row.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Approved draft was not applied",
            metadata={"status_code": exc.status_code},
            raise_on_error=False,
        )
        raise
    session.refresh(plan)
    if plan.status != before_status:
        raise HTTPException(status_code=500, detail="Applying a draft must not change the plan status")
    row.status = "applied"
    row.applied_by_user_id = ctx.user_id
    row.applied_at = datetime.now(timezone.utc)
    row.application_json = {
        "plan_id": str(plan.id),
        "goal_ids": created_goals,
        "milestone_ids": created_milestones,
        "plan_status_unchanged": plan.status,
    }
    session.flush()
    record_event(
        session,
        action=audit_events.AI_SUPPORT_PLAN_DRAFT_APPLIED,
        resource_type="support_plan_draft",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Approved support plan draft applied as new goals",
        metadata={"plan_id": str(plan.id), "goal_count": len(created_goals)},
        raise_on_error=False,
    )
    return _public(row)


def _goal_description(item: dict[str, Any]) -> str:
    lines = [str(item.get("description") or "").strip()]
    actions = [str(action).strip() for action in item.get("actions") or [] if str(action).strip()]
    if actions:
        lines.append("Suggested actions for staff to confirm:")
        lines.extend(f"- {action}" for action in actions)
    lines.append("No staff member was assigned by the draft.")
    return "\n".join(lines)[:4000]
