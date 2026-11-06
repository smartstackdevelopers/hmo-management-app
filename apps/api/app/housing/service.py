"""F2.5 housing applications, waiting lists, and approval tracking."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.enums import HMoreRole
from app.db.models.housing import (
    HousingApplication,
    HousingApplicationDecision,
    HousingApplicationStatusHistory,
    WaitingListEntry,
)
from app.housing import access
from app.housing.schemas import (
    ApplicationCreate,
    ApplicationUpdate,
    DecisionCreate,
    InformationRequiredRequest,
    WaitingListAdd,
    WaitingListUpdate,
)
from app.records.pagination import offset_limit
from app.tenancy.context import OrganisationContext

APPLICATION_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"submitted", "withdrawn"}),
    "submitted": frozenset({"under_review", "information_required", "withdrawn", "closed"}),
    "under_review": frozenset(
        {"information_required", "approved", "rejected", "withdrawn", "closed"}
    ),
    "information_required": frozenset({"submitted", "under_review", "withdrawn", "closed"}),
    "approved": frozenset({"closed"}),
    "rejected": frozenset({"closed", "under_review"}),
    "withdrawn": frozenset({"closed"}),
    "closed": frozenset(),
}

PRIORITY_RANK = {"urgent": 0, "high": 1, "normal": 2, "low": 3}


def _now() -> datetime:
    return datetime.now(timezone.utc)


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


def _next_reference(session: Session, organisation_id: uuid.UUID) -> str:
    year = _now().year
    prefix = f"APP-{year}-"
    count = (
        session.scalar(
            select(func.count())
            .select_from(HousingApplication)
            .where(
                HousingApplication.organisation_id == organisation_id,
                HousingApplication.reference_number.like(f"{prefix}%"),
            )
        )
        or 0
    )
    return f"{prefix}{count + 1:05d}"


def _record_status(
    session: Session,
    ctx: OrganisationContext,
    application: HousingApplication,
    *,
    from_status: str | None,
    to_status: str,
    note: str | None = None,
) -> None:
    session.add(
        HousingApplicationStatusHistory(
            organisation_id=ctx.organisation_id,
            application_id=application.id,
            from_status=from_status,
            to_status=to_status,
            changed_by_user_id=ctx.user_id,
            note=note,
        )
    )


def _waiting_entry(
    session: Session, organisation_id: uuid.UUID, application_id: uuid.UUID
) -> WaitingListEntry | None:
    return session.scalar(
        select(WaitingListEntry).where(
            WaitingListEntry.organisation_id == organisation_id,
            WaitingListEntry.application_id == application_id,
            WaitingListEntry.status == "active",
        )
    )


def application_out_dict(session: Session, row: HousingApplication) -> dict[str, Any]:
    entry = _waiting_entry(session, row.organisation_id, row.id)
    return {
        "id": row.id,
        "organisation_id": row.organisation_id,
        "reference_number": row.reference_number,
        "tenant_id": row.tenant_id,
        "created_by_user_id": row.created_by_user_id,
        "reviewer_user_id": row.reviewer_user_id,
        "preferred_property_id": row.preferred_property_id,
        "accommodation_type": row.accommodation_type,
        "housing_requirements": row.housing_requirements,
        "household_summary": row.household_summary,
        "supporting_information": row.supporting_information,
        "priority": row.priority,
        "status": row.status,
        "information_required_notes": row.information_required_notes,
        "submitted_at": row.submitted_at,
        "decided_at": row.decided_at,
        "closed_at": row.closed_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "on_waiting_list": entry is not None,
        "waiting_list_position": entry.position if entry is not None else None,
    }


def create_application(
    session: Session, ctx: OrganisationContext, data: ApplicationCreate
) -> HousingApplication:
    access.require_application_create(ctx)
    access.assert_can_create_for_tenant(session, ctx, data.tenant_id)
    access.assert_property_in_org(session, ctx, data.preferred_property_id)
    row = HousingApplication(
        organisation_id=ctx.organisation_id,
        reference_number=_next_reference(session, ctx.organisation_id),
        tenant_id=data.tenant_id,
        created_by_user_id=ctx.user_id,
        preferred_property_id=data.preferred_property_id,
        accommodation_type=data.accommodation_type,
        housing_requirements=data.housing_requirements,
        household_summary=data.household_summary,
        supporting_information=data.supporting_information,
        priority=data.priority,
        status="draft",
    )
    session.add(row)
    session.flush()
    _record_status(session, ctx, row, from_status=None, to_status="draft", note="Created")
    _audit(
        session,
        ctx,
        action=audit_events.HOUSING_APPLICATION_CREATE,
        resource_type="housing_application",
        resource_id=row.id,
        summary="Housing application created",
        metadata={"ref": row.reference_number, "priority": row.priority},
    )
    if data.submit:
        return transition_application(session, ctx, row.id, "submitted")
    return row


def get_application(
    session: Session, ctx: OrganisationContext, application_id: uuid.UUID
) -> HousingApplication:
    access.require_application_read(ctx)
    row = session.get(HousingApplication, application_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    access.assert_can_view_application(session, ctx, row)
    return row


def list_applications(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    status_filter: str | None = None,
    priority: str | None = None,
    reviewer_user_id: uuid.UUID | None = None,
    q: str | None = None,
    pending_approvals: bool = False,
) -> tuple[list[HousingApplication], int]:
    access.require_application_read(ctx)
    stmt = select(HousingApplication).where(
        HousingApplication.organisation_id == ctx.organisation_id
    )
    if ctx.role == HMoreRole.TENANT:
        from app.db.models.tenant import Tenant

        tenant_ids = session.scalars(
            select(Tenant.id).where(
                Tenant.organisation_id == ctx.organisation_id,
                Tenant.user_id == ctx.user_id,
            )
        ).all()
        stmt = stmt.where(HousingApplication.tenant_id.in_(tenant_ids or [uuid.uuid4()]))
    elif ctx.role == HMoreRole.SUPPORT_WORKER:
        from app.db.models.support_ops import CaseAssignment

        tenant_ids = session.scalars(
            select(CaseAssignment.tenant_id).where(
                CaseAssignment.organisation_id == ctx.organisation_id,
                CaseAssignment.support_worker_user_id == ctx.user_id,
                CaseAssignment.status == "active",
            )
        ).all()
        stmt = stmt.where(HousingApplication.tenant_id.in_(tenant_ids or [uuid.uuid4()]))
    if status_filter:
        stmt = stmt.where(HousingApplication.status == status_filter)
    if priority:
        stmt = stmt.where(HousingApplication.priority == priority)
    if reviewer_user_id:
        stmt = stmt.where(HousingApplication.reviewer_user_id == reviewer_user_id)
    if pending_approvals:
        stmt = stmt.where(
            HousingApplication.status.in_(("submitted", "under_review", "information_required"))
        )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                HousingApplication.reference_number.ilike(like),
                HousingApplication.housing_requirements.ilike(like),
            )
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(
            stmt.order_by(HousingApplication.created_at.desc()).offset(offset).limit(limit)
        ).all()
    )
    return rows, total


def update_application(
    session: Session,
    ctx: OrganisationContext,
    application_id: uuid.UUID,
    data: ApplicationUpdate,
) -> HousingApplication:
    row = get_application(session, ctx, application_id)
    payload = data.model_dump(exclude_unset=True)
    status_note = payload.pop("status_note", None)
    target_status = payload.pop("status", None)
    reviewer = payload.pop("reviewer_user_id", None) if "reviewer_user_id" in payload else None

    if row.status not in {"draft", "information_required"} and ctx.role in {
        HMoreRole.TENANT,
        HMoreRole.SUPPORT_WORKER,
    }:
        if target_status is None and payload:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot amend application in current status",
            )

    if "preferred_property_id" in payload:
        access.assert_property_in_org(session, ctx, payload["preferred_property_id"])

    if reviewer is not None:
        access.require_application_review(ctx)
        access.assert_active_org_member(
            session, organisation_id=ctx.organisation_id, user_id=reviewer
        )
        row.reviewer_user_id = reviewer
        _audit(
            session,
            ctx,
            action=audit_events.HOUSING_APPLICATION_ASSIGN,
            resource_type="housing_application",
            resource_id=row.id,
            summary="Application reviewer assigned",
        )

    for key, value in payload.items():
        setattr(row, key, value)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.HOUSING_APPLICATION_UPDATE,
        resource_type="housing_application",
        resource_id=row.id,
        summary="Housing application updated",
        metadata={"status": row.status},
    )
    if target_status is not None:
        return transition_application(session, ctx, row.id, target_status, note=status_note)
    return row


def transition_application(
    session: Session,
    ctx: OrganisationContext,
    application_id: uuid.UUID,
    target: str,
    *,
    note: str | None = None,
) -> HousingApplication:
    row = get_application(session, ctx, application_id)
    allowed = APPLICATION_TRANSITIONS.get(row.status, frozenset())
    if target != row.status and target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition application from {row.status} to {target}",
        )

    if target == "submitted":
        if ctx.role == HMoreRole.TENANT:
            access.assert_can_view_application(session, ctx, row)
        elif ctx.role not in {
            HMoreRole.ORGANISATION_ADMIN,
            HMoreRole.SUPER_ADMIN,
            HMoreRole.SUPPORT_WORKER,
        }:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        if row.submitted_at is None:
            row.submitted_at = _now()
    elif target in {"under_review", "information_required", "approved", "rejected", "closed"}:
        access.require_application_review(ctx)
    elif target == "withdrawn":
        if ctx.role == HMoreRole.TENANT:
            access.assert_can_view_application(session, ctx, row)
        elif ctx.role not in {
            HMoreRole.ORGANISATION_ADMIN,
            HMoreRole.SUPER_ADMIN,
            HMoreRole.SUPPORT_WORKER,
        }:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if target == "closed":
        row.closed_at = _now()

    prev = row.status
    row.status = target
    session.flush()
    _record_status(session, ctx, row, from_status=prev, to_status=target, note=note)
    action = audit_events.HOUSING_APPLICATION_STATUS
    if target == "submitted":
        action = audit_events.HOUSING_APPLICATION_SUBMIT
    elif target == "withdrawn":
        action = audit_events.HOUSING_APPLICATION_WITHDRAW
    elif target == "closed":
        action = audit_events.HOUSING_APPLICATION_CLOSE
    _audit(
        session,
        ctx,
        action=action,
        resource_type="housing_application",
        resource_id=row.id,
        summary=f"Application status {prev} → {target}",
        metadata={"from": prev, "to": target},
    )
    return row


def request_information(
    session: Session,
    ctx: OrganisationContext,
    application_id: uuid.UUID,
    data: InformationRequiredRequest,
) -> HousingApplication:
    access.require_application_review(ctx)
    row = get_application(session, ctx, application_id)
    row.information_required_notes = data.notes
    session.flush()
    updated = transition_application(
        session, ctx, row.id, "information_required", note=data.notes[:500]
    )
    _audit(
        session,
        ctx,
        action=audit_events.HOUSING_APPLICATION_INFO_REQUIRED,
        resource_type="housing_application",
        resource_id=row.id,
        summary="Additional information requested",
    )
    return updated


def record_decision(
    session: Session,
    ctx: OrganisationContext,
    application_id: uuid.UUID,
    data: DecisionCreate,
) -> HousingApplicationDecision:
    access.require_application_review(ctx)
    row = get_application(session, ctx, application_id)
    # Separation of duties: creator cannot approve their own application.
    if row.created_by_user_id == ctx.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot decide on an application you created",
        )
    if row.status not in {"submitted", "under_review", "information_required"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is not awaiting a decision",
        )
    if data.decision == "rejected" and not data.decision_notes.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection requires decision notes",
        )
    now = _now()
    decision = HousingApplicationDecision(
        organisation_id=ctx.organisation_id,
        application_id=row.id,
        decision=data.decision,
        decided_by_user_id=ctx.user_id,
        decision_notes=data.decision_notes,
        decided_at=now,
    )
    session.add(decision)
    row.decided_at = now
    if row.reviewer_user_id is None:
        row.reviewer_user_id = ctx.user_id
    session.flush()
    target = "approved" if data.decision == "approved" else "rejected"
    transition_application(session, ctx, row.id, target, note=data.decision_notes[:500])
    _audit(
        session,
        ctx,
        action=(
            audit_events.HOUSING_APPLICATION_APPROVE
            if data.decision == "approved"
            else audit_events.HOUSING_APPLICATION_REJECT
        ),
        resource_type="housing_application",
        resource_id=row.id,
        summary=f"Application {data.decision}",
    )
    if data.decision == "approved" and data.add_to_waiting_list:
        add_to_waiting_list(
            session,
            ctx,
            WaitingListAdd(application_id=row.id, priority=row.priority),  # type: ignore[arg-type]
        )
    return decision


def list_history(
    session: Session, ctx: OrganisationContext, application_id: uuid.UUID
) -> list[HousingApplicationStatusHistory]:
    get_application(session, ctx, application_id)
    return list(
        session.scalars(
            select(HousingApplicationStatusHistory)
            .where(
                HousingApplicationStatusHistory.organisation_id == ctx.organisation_id,
                HousingApplicationStatusHistory.application_id == application_id,
            )
            .order_by(HousingApplicationStatusHistory.created_at.asc())
        ).all()
    )


def list_decisions(
    session: Session, ctx: OrganisationContext, application_id: uuid.UUID
) -> list[HousingApplicationDecision]:
    get_application(session, ctx, application_id)
    return list(
        session.scalars(
            select(HousingApplicationDecision)
            .where(
                HousingApplicationDecision.organisation_id == ctx.organisation_id,
                HousingApplicationDecision.application_id == application_id,
            )
            .order_by(HousingApplicationDecision.decided_at.asc())
        ).all()
    )


def _next_waiting_position(session: Session, organisation_id: uuid.UUID) -> int:
    # Lock org waiting-list rows for consistent position allocation.
    session.execute(
        select(WaitingListEntry.id)
        .where(
            WaitingListEntry.organisation_id == organisation_id,
            WaitingListEntry.status == "active",
        )
        .with_for_update()
    )
    max_pos = session.scalar(
        select(func.max(WaitingListEntry.position)).where(
            WaitingListEntry.organisation_id == organisation_id,
            WaitingListEntry.status == "active",
        )
    )
    return int(max_pos or 0) + 1


def add_to_waiting_list(
    session: Session, ctx: OrganisationContext, data: WaitingListAdd
) -> WaitingListEntry:
    access.require_waiting_list_manage(ctx)
    application = get_application(session, ctx, data.application_id)
    if application.status not in {"approved", "under_review", "submitted"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only submitted/approved applications can join the waiting list",
        )
    existing = session.scalar(
        select(WaitingListEntry).where(
            WaitingListEntry.organisation_id == ctx.organisation_id,
            WaitingListEntry.application_id == application.id,
            WaitingListEntry.status == "active",
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application is already on the waiting list",
        )
    if data.responsible_officer_user_id is not None:
        access.assert_active_org_member(
            session,
            organisation_id=ctx.organisation_id,
            user_id=data.responsible_officer_user_id,
        )
    position = _next_waiting_position(session, ctx.organisation_id)
    entry = WaitingListEntry(
        organisation_id=ctx.organisation_id,
        application_id=application.id,
        position=position,
        status="active",
        priority=data.priority or application.priority,
        responsible_officer_user_id=data.responsible_officer_user_id,
        added_at=_now(),
        last_reviewed_at=_now(),
        notes=data.notes,
    )
    session.add(entry)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.WAITING_LIST_ADD,
        resource_type="waiting_list_entry",
        resource_id=entry.id,
        summary="Added to waiting list",
        metadata={"position": position, "application_id": str(application.id)},
    )
    return entry


def update_waiting_list_entry(
    session: Session,
    ctx: OrganisationContext,
    entry_id: uuid.UUID,
    data: WaitingListUpdate,
) -> WaitingListEntry:
    access.require_waiting_list_manage(ctx)
    entry = session.get(WaitingListEntry, entry_id)
    if entry is None or entry.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waiting-list entry not found")
    payload = data.model_dump(exclude_unset=True)
    if "responsible_officer_user_id" in payload and payload["responsible_officer_user_id"]:
        access.assert_active_org_member(
            session,
            organisation_id=ctx.organisation_id,
            user_id=payload["responsible_officer_user_id"],
        )
    prev_priority = entry.priority
    for key, value in payload.items():
        setattr(entry, key, value)
    entry.last_reviewed_at = _now()
    session.flush()
    if "priority" in payload and payload["priority"] != prev_priority:
        _audit(
            session,
            ctx,
            action=audit_events.WAITING_LIST_PRIORITY,
            resource_type="waiting_list_entry",
            resource_id=entry.id,
            summary="Waiting-list priority updated",
            metadata={"from": prev_priority, "to": entry.priority},
        )
    if payload.get("status") == "removed":
        _audit(
            session,
            ctx,
            action=audit_events.WAITING_LIST_REMOVE,
            resource_type="waiting_list_entry",
            resource_id=entry.id,
            summary="Removed from waiting list",
        )
    return entry


def list_waiting_list(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    status_filter: str | None = "active",
) -> tuple[list[WaitingListEntry], int]:
    access.require_waiting_list_read(ctx)
    stmt = select(WaitingListEntry).where(
        WaitingListEntry.organisation_id == ctx.organisation_id
    )
    if status_filter:
        stmt = stmt.where(WaitingListEntry.status == status_filter)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    # Order by configured priority band then FIFO position — not a statutory ranking formula.
    rows = list(
        session.scalars(
            stmt.order_by(WaitingListEntry.position.asc()).offset(offset).limit(limit)
        ).all()
    )
    return rows, total


def waiting_list_out_dict(session: Session, entry: WaitingListEntry) -> dict[str, Any]:
    application = session.get(HousingApplication, entry.application_id)
    return {
        "id": entry.id,
        "organisation_id": entry.organisation_id,
        "application_id": entry.application_id,
        "position": entry.position,
        "status": entry.status,
        "priority": entry.priority,
        "responsible_officer_user_id": entry.responsible_officer_user_id,
        "added_at": entry.added_at,
        "last_reviewed_at": entry.last_reviewed_at,
        "notes": entry.notes,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "application_reference": application.reference_number if application else None,
        "application_status": application.status if application else None,
        "tenant_id": application.tenant_id if application else None,
    }
