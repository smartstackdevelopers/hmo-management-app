"""F2.7 complaints workflow services."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.complaints import access
from app.complaints.schemas import (
    AssignRequest,
    AssociateFileRequest,
    CategoryCreate,
    ComplaintCreate,
    ComplaintUpdate,
    DeadlineUpdateRequest,
    EscalateRequest,
    NoteCreate,
    PriorityRequest,
    ResolveEscalationRequest,
    StatusTransitionRequest,
)
from app.db.models.complaints import (
    Complaint,
    ComplaintCategory,
    ComplaintDeadlineChange,
    ComplaintDeadlineRule,
    ComplaintEscalation,
    ComplaintFile,
    ComplaintHistoryEvent,
    ComplaintNote,
    ComplaintStatusHistory,
)
from app.db.models.enums import HMoreRole
from app.db.models.file_metadata import FileMetadata
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.support.access import assert_tenant_support_access
from app.tenancy.context import OrganisationContext

COMPLAINT_TRANSITIONS: dict[str, frozenset[str]] = {
    "submitted": frozenset({"acknowledged", "withdrawn", "under_review"}),
    "acknowledged": frozenset({"under_review", "investigation", "awaiting_information", "withdrawn"}),
    "under_review": frozenset(
        {"investigation", "awaiting_information", "escalated", "resolved", "withdrawn"}
    ),
    "investigation": frozenset(
        {"awaiting_information", "escalated", "resolved", "under_review"}
    ),
    "awaiting_information": frozenset({"under_review", "investigation", "escalated", "withdrawn"}),
    "escalated": frozenset({"investigation", "under_review", "resolved"}),
    "resolved": frozenset({"closed", "reopened"}),
    "closed": frozenset({"reopened"}),
    "reopened": frozenset({"under_review", "investigation", "escalated", "resolved", "withdrawn"}),
    "withdrawn": frozenset(),
}

OPEN_STATUSES = frozenset(
    {
        "submitted",
        "acknowledged",
        "under_review",
        "investigation",
        "awaiting_information",
        "escalated",
        "reopened",
    }
)

DEFAULT_CATEGORIES = (
    ("general", "General", 10),
    ("housing", "Housing / accommodation", 20),
    ("support", "Support service", 30),
    ("maintenance", "Maintenance / repairs (non-work-order)", 40),
    ("staff", "Staff conduct", 50),
)

DEFAULT_DEADLINE_RULES = (
    # Operational targets only — not statutory.
    ("low", 72, 240, False),
    ("normal", 48, 120, True),
    ("high", 24, 72, True),
    ("urgent", 8, 24, True),
)

REASON_REQUIRED_STATUSES = frozenset({"closed", "withdrawn", "reopened", "resolved"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit(
    session: Session,
    ctx: OrganisationContext,
    *,
    action: str,
    resource_id: uuid.UUID,
    summary: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    record_event(
        session,
        action=action,
        resource_type="complaint",
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
    ctx: OrganisationContext,
    complaint: Complaint,
    *,
    event_type: str,
    summary: str,
    detail: str | None = None,
    tenant_visible: bool = True,
) -> None:
    session.add(
        ComplaintHistoryEvent(
            organisation_id=ctx.organisation_id,
            complaint_id=complaint.id,
            event_type=event_type,
            summary=summary,
            detail=detail,
            actor_user_id=ctx.user_id,
            is_tenant_visible=tenant_visible,
        )
    )


def _file_ids(session: Session, complaint_id: uuid.UUID, *, tenant_only: bool) -> list[uuid.UUID]:
    stmt = select(ComplaintFile.file_id).where(ComplaintFile.complaint_id == complaint_id)
    if tenant_only:
        stmt = stmt.where(ComplaintFile.is_tenant_visible.is_(True))
    return list(session.scalars(stmt).all())


def _has_open_escalation(session: Session, complaint_id: uuid.UUID) -> bool:
    return (
        session.scalar(
            select(func.count())
            .select_from(ComplaintEscalation)
            .where(
                ComplaintEscalation.complaint_id == complaint_id,
                ComplaintEscalation.status == "open",
            )
        )
        or 0
    ) > 0


def is_overdue(complaint: Complaint, now: datetime | None = None) -> bool:
    now = now or _now()
    if complaint.status not in OPEN_STATUSES:
        return False
    if complaint.response_due_at and complaint.response_due_at < now:
        return True
    if (
        complaint.status == "submitted"
        and complaint.acknowledge_due_at
        and complaint.acknowledge_due_at < now
        and complaint.acknowledged_at is None
    ):
        return True
    return False


def complaint_out_dict(
    session: Session, ctx: OrganisationContext, row: Complaint
) -> dict[str, Any]:
    tenant_view = ctx.role == HMoreRole.TENANT
    data = {
        "id": row.id,
        "organisation_id": row.organisation_id,
        "reference_number": row.reference_number,
        "title": row.title,
        "description": row.description,
        "category_code": row.category_code,
        "priority": row.priority,
        "status": row.status,
        "tenant_id": row.tenant_id,
        "submitted_by_user_id": row.submitted_by_user_id,
        "assigned_user_id": row.assigned_user_id,
        "property_id": row.property_id,
        "housing_application_id": row.housing_application_id,
        "submitted_at": row.submitted_at,
        "acknowledged_at": row.acknowledged_at,
        "acknowledge_due_at": row.acknowledge_due_at,
        "response_due_at": row.response_due_at,
        "resolved_at": row.resolved_at,
        "closed_at": row.closed_at,
        "resolution_summary": None if tenant_view else row.resolution_summary,
        "tenant_visible_summary": row.tenant_visible_summary,
        "is_overdue": is_overdue(row),
        "open_escalation": _has_open_escalation(session, row.id),
        "file_ids": _file_ids(session, row.id, tenant_only=tenant_view),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
    return data


def ensure_defaults(session: Session, ctx: OrganisationContext) -> None:
    access.require_complaints_manage(ctx)
    cats = session.scalars(
        select(ComplaintCategory).where(ComplaintCategory.organisation_id == ctx.organisation_id)
    ).first()
    if cats is None:
        for code, title, order in DEFAULT_CATEGORIES:
            session.add(
                ComplaintCategory(
                    organisation_id=ctx.organisation_id,
                    code=code,
                    title=title,
                    description="Organisation-configurable category — not a statutory classification.",
                    sort_order=order,
                    is_active=True,
                )
            )
    rules = session.scalars(
        select(ComplaintDeadlineRule).where(
            ComplaintDeadlineRule.organisation_id == ctx.organisation_id
        )
    ).first()
    if rules is None:
        for priority, ack, resp, auto_esc in DEFAULT_DEADLINE_RULES:
            session.add(
                ComplaintDeadlineRule(
                    organisation_id=ctx.organisation_id,
                    priority=priority,
                    acknowledge_hours=ack,
                    response_hours=resp,
                    auto_escalate_overdue=auto_esc,
                    notes="Internal operational target — not a statutory deadline.",
                )
            )
    session.flush()


def list_categories(session: Session, ctx: OrganisationContext) -> list[ComplaintCategory]:
    access.require_complaints_read(ctx)
    return list(
        session.scalars(
            select(ComplaintCategory)
            .where(
                ComplaintCategory.organisation_id == ctx.organisation_id,
                ComplaintCategory.is_active.is_(True),
            )
            .order_by(ComplaintCategory.sort_order.asc())
        ).all()
    )


def create_category(
    session: Session, ctx: OrganisationContext, data: CategoryCreate
) -> ComplaintCategory:
    access.require_complaints_manage(ctx)
    row = ComplaintCategory(
        organisation_id=ctx.organisation_id,
        code=data.code,
        title=data.title,
        description=data.description,
        sort_order=data.sort_order,
        is_active=True,
    )
    session.add(row)
    session.flush()
    return row


def _deadline_rule(session: Session, org_id: uuid.UUID, priority: str) -> ComplaintDeadlineRule | None:
    return session.scalar(
        select(ComplaintDeadlineRule).where(
            ComplaintDeadlineRule.organisation_id == org_id,
            ComplaintDeadlineRule.priority == priority,
        )
    )


def _apply_deadlines(session: Session, complaint: Complaint) -> None:
    rule = _deadline_rule(session, complaint.organisation_id, complaint.priority)
    if rule is None:
        # Safe operational fallbacks (documented as non-statutory).
        ack_h, resp_h = {"low": (72, 240), "normal": (48, 120), "high": (24, 72), "urgent": (8, 24)}.get(
            complaint.priority, (48, 120)
        )
    else:
        ack_h, resp_h = rule.acknowledge_hours, rule.response_hours
    base = complaint.submitted_at
    complaint.acknowledge_due_at = base + timedelta(hours=ack_h)
    complaint.response_due_at = base + timedelta(hours=resp_h)


def _next_reference(session: Session, org_id: uuid.UUID) -> str:
    day = _now().strftime("%Y%m%d")
    prefix = f"CMP-{day}-"
    count = (
        session.scalar(
            select(func.count())
            .select_from(Complaint)
            .where(
                Complaint.organisation_id == org_id,
                Complaint.reference_number.like(f"{prefix}%"),
            )
        )
        or 0
    )
    return f"{prefix}{count + 1:04d}"


def create_complaint(
    session: Session, ctx: OrganisationContext, data: ComplaintCreate
) -> Complaint:
    access.require_complaints_create(ctx)
    # Seed defaults lazily for manage; for tenant create ensure rules exist via bypass seed.
    existing_rules = session.scalar(
        select(func.count())
        .select_from(ComplaintDeadlineRule)
        .where(ComplaintDeadlineRule.organisation_id == ctx.organisation_id)
    )
    if not existing_rules and ctx.role == HMoreRole.ORGANISATION_ADMIN:
        ensure_defaults(session, ctx)

    tenant_id = data.tenant_id
    if ctx.role == HMoreRole.TENANT:
        own = access.resolve_own_tenant_id(session, ctx)
        tenant_id = own
    elif ctx.role == HMoreRole.SUPPORT_WORKER:
        if tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tenant_id required when creating on behalf of a tenant",
            )
        assert_tenant_support_access(session, ctx, tenant_id)

    row = Complaint(
        organisation_id=ctx.organisation_id,
        reference_number=_next_reference(session, ctx.organisation_id),
        title=data.title,
        description=data.description,
        category_code=data.category_code,
        priority=data.priority,
        status="submitted",
        tenant_id=tenant_id,
        submitted_by_user_id=ctx.user_id,
        property_id=data.property_id,
        housing_application_id=data.housing_application_id,
        submitted_at=_now(),
    )
    _apply_deadlines(session, row)
    session.add(row)
    session.flush()
    session.add(
        ComplaintStatusHistory(
            organisation_id=ctx.organisation_id,
            complaint_id=row.id,
            from_status=None,
            to_status="submitted",
            changed_by_user_id=ctx.user_id,
            note="Complaint submitted",
        )
    )
    _history(
        session,
        ctx,
        row,
        event_type="submitted",
        summary="Complaint submitted",
        tenant_visible=True,
    )
    _audit(
        session,
        ctx,
        action=audit_events.COMPLAINT_CREATE,
        resource_id=row.id,
        summary="Complaint created",
        metadata={"reference": row.reference_number, "priority": row.priority},
    )
    return row


def get_complaint(session: Session, ctx: OrganisationContext, complaint_id: uuid.UUID) -> Complaint:
    row = session.get(Complaint, complaint_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    access.assert_can_view_complaint(session, ctx, row)
    return row


def list_complaints(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    status_filter: str | None = None,
    priority: str | None = None,
    overdue_only: bool = False,
    escalated_only: bool = False,
    q: str | None = None,
) -> tuple[list[Complaint], int]:
    access.require_complaints_read(ctx)
    stmt = select(Complaint).where(Complaint.organisation_id == ctx.organisation_id)
    if ctx.role == HMoreRole.TENANT:
        own = access.resolve_own_tenant_id(session, ctx)
        clauses = [Complaint.submitted_by_user_id == ctx.user_id]
        if own:
            clauses.append(Complaint.tenant_id == own)
        stmt = stmt.where(or_(*clauses))
    elif ctx.role == HMoreRole.SUPPORT_WORKER:
        from app.db.models.support_ops import CaseAssignment

        assigned_tenants = select(CaseAssignment.tenant_id).where(
            CaseAssignment.organisation_id == ctx.organisation_id,
            CaseAssignment.support_worker_user_id == ctx.user_id,
            CaseAssignment.status == "active",
        )
        stmt = stmt.where(
            or_(
                Complaint.assigned_user_id == ctx.user_id,
                Complaint.tenant_id.in_(assigned_tenants),
            )
        )
    elif ctx.role == HMoreRole.LANDLORD:
        from app.db.models.property import Property

        props = select(Property.id).where(
            Property.organisation_id == ctx.organisation_id,
            or_(Property.landlord_user_id == ctx.user_id, Property.landlord_user_id.is_(None)),
        )
        stmt = stmt.where(Complaint.property_id.in_(props))

    if status_filter:
        stmt = stmt.where(Complaint.status == status_filter)
    if priority:
        stmt = stmt.where(Complaint.priority == priority)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Complaint.title.ilike(like), Complaint.reference_number.ilike(like))
        )
    if escalated_only:
        open_esc = select(ComplaintEscalation.complaint_id).where(
            ComplaintEscalation.organisation_id == ctx.organisation_id,
            ComplaintEscalation.status == "open",
        )
        stmt = stmt.where(
            or_(Complaint.status == "escalated", Complaint.id.in_(open_esc))
        )

    rows = list(
        session.scalars(
            stmt.order_by(Complaint.submitted_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
    )
    if overdue_only:
        rows = [r for r in rows if is_overdue(r)]
    total = (
        session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    )
    if overdue_only:
        # Approximate: recount filtered page universe (acceptable for operational dashboard).
        all_rows = list(session.scalars(stmt.order_by(None)).all())
        total = sum(1 for r in all_rows if is_overdue(r))
    return rows, total


def update_complaint(
    session: Session, ctx: OrganisationContext, complaint_id: uuid.UUID, data: ComplaintUpdate
) -> Complaint:
    row = get_complaint(session, ctx, complaint_id)
    if row.status in {"closed", "withdrawn"} and ctx.role != HMoreRole.ORGANISATION_ADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complaint is closed")
    if ctx.role == HMoreRole.TENANT:
        own = access.resolve_own_tenant_id(session, ctx)
        if row.submitted_by_user_id != ctx.user_id and row.tenant_id != own:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if row.status not in {"submitted", "awaiting_information", "reopened"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant can only update complaints awaiting their input",
            )
    elif ctx.role == HMoreRole.ORGANISATION_ADMIN:
        access.require_complaints_manage(ctx)
    elif ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.COMPLAINTS_READ_ASSIGNED)
    elif ctx.role != HMoreRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(row, key, value)
    session.flush()
    _history(session, ctx, row, event_type="updated", summary="Complaint details updated", tenant_visible=False)
    _audit(session, ctx, action=audit_events.COMPLAINT_UPDATE, resource_id=row.id, summary="Complaint updated")
    return row


def assign_complaint(
    session: Session, ctx: OrganisationContext, complaint_id: uuid.UUID, data: AssignRequest
) -> Complaint:
    row = get_complaint(session, ctx, complaint_id)
    if ctx.role == HMoreRole.SUPER_ADMIN:
        pass
    elif ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.COMPLAINTS_ASSIGN)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    prev = row.assigned_user_id
    row.assigned_user_id = data.assigned_user_id
    session.flush()
    _history(
        session,
        ctx,
        row,
        event_type="assignment",
        summary="Complaint assignment updated",
        detail=data.note,
        tenant_visible=False,
    )
    _audit(
        session,
        ctx,
        action=audit_events.COMPLAINT_ASSIGN,
        resource_id=row.id,
        summary="Complaint assigned",
        metadata={
            "from": str(prev) if prev else None,
            "to": str(data.assigned_user_id) if data.assigned_user_id else None,
        },
    )
    return row


def change_priority(
    session: Session, ctx: OrganisationContext, complaint_id: uuid.UUID, data: PriorityRequest
) -> Complaint:
    row = get_complaint(session, ctx, complaint_id)
    if ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    require_permission(ctx.authorization, Permission.COMPLAINTS_PRIORITY_MANAGE)
    prev = row.priority
    row.priority = data.priority
    _apply_deadlines(session, row)
    session.flush()
    _history(
        session,
        ctx,
        row,
        event_type="priority_change",
        summary=f"Priority {prev} → {data.priority}",
        detail=data.reason,
        tenant_visible=True,
    )
    _audit(
        session,
        ctx,
        action=audit_events.COMPLAINT_PRIORITY,
        resource_id=row.id,
        summary="Complaint priority changed",
        metadata={"from": prev, "to": data.priority},
    )
    return row


def transition_status(
    session: Session,
    ctx: OrganisationContext,
    complaint_id: uuid.UUID,
    data: StatusTransitionRequest,
) -> Complaint:
    row = get_complaint(session, ctx, complaint_id)
    target = data.status
    allowed = COMPLAINT_TRANSITIONS.get(row.status, frozenset())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {row.status} to {target}",
        )
    if target in REASON_REQUIRED_STATUSES and not (data.note or data.resolution_summary):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explanation required for this status change",
        )
    if target in {"closed", "reopened"}:
        if ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        require_permission(ctx.authorization, Permission.COMPLAINTS_CLOSE)
    elif ctx.role == HMoreRole.TENANT:
        if target != "withdrawn" or row.submitted_by_user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.COMPLAINTS_READ_ASSIGNED)
        if target in {"escalated", "resolved", "closed", "reopened"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.COMPLAINTS_MANAGE)
    elif ctx.role != HMoreRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    prev = row.status
    row.status = target
    now = _now()
    if target == "acknowledged":
        row.acknowledged_at = now
    if target == "resolved":
        row.resolved_at = now
        if data.resolution_summary:
            row.resolution_summary = data.resolution_summary
        if data.tenant_visible_summary:
            row.tenant_visible_summary = data.tenant_visible_summary
    if target == "closed":
        row.closed_at = now
    if target == "reopened":
        row.closed_at = None
        row.resolved_at = None

    session.add(
        ComplaintStatusHistory(
            organisation_id=ctx.organisation_id,
            complaint_id=row.id,
            from_status=prev,
            to_status=target,
            changed_by_user_id=ctx.user_id,
            note=(data.note or data.resolution_summary or "")[:1000] or None,
        )
    )
    _history(
        session,
        ctx,
        row,
        event_type="status_change",
        summary=f"Status {prev} → {target}",
        detail=data.note,
        tenant_visible=True,
    )
    action = audit_events.COMPLAINT_STATUS
    if target == "resolved":
        action = audit_events.COMPLAINT_RESOLVE
    elif target == "closed":
        action = audit_events.COMPLAINT_CLOSE
    elif target == "reopened":
        action = audit_events.COMPLAINT_REOPEN
    _audit(
        session,
        ctx,
        action=action,
        resource_id=row.id,
        summary=f"Complaint status {prev} → {target}",
        metadata={"from": prev, "to": target},
    )
    session.flush()
    return row


def add_note(
    session: Session, ctx: OrganisationContext, complaint_id: uuid.UUID, data: NoteCreate
) -> ComplaintNote:
    row = get_complaint(session, ctx, complaint_id)
    if ctx.role == HMoreRole.TENANT:
        if data.visibility != "tenant_visible":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenants cannot create internal notes",
            )
    else:
        if ctx.role == HMoreRole.ORGANISATION_ADMIN:
            require_permission(ctx.authorization, Permission.COMPLAINTS_NOTES_ADD)
        elif ctx.role == HMoreRole.SUPPORT_WORKER:
            require_permission(ctx.authorization, Permission.COMPLAINTS_NOTES_ADD)
        elif ctx.role != HMoreRole.SUPER_ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if data.visibility == "internal" and not access.can_view_internal_notes(ctx):
            # Creating internal requires notes.add; OA/SW with notes.add can create internal.
            if ctx.role == HMoreRole.SUPPORT_WORKER:
                pass  # SW may add internal investigation notes they author
            elif ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    note = ComplaintNote(
        organisation_id=ctx.organisation_id,
        complaint_id=row.id,
        author_user_id=ctx.user_id,
        visibility=data.visibility,
        body=data.body,
        is_follow_up=data.is_follow_up,
    )
    session.add(note)
    session.flush()
    _history(
        session,
        ctx,
        row,
        event_type="note",
        summary="Follow-up recorded" if data.is_follow_up else "Investigation note added",
        tenant_visible=data.visibility == "tenant_visible",
    )
    _audit(
        session,
        ctx,
        action=audit_events.COMPLAINT_NOTE_CREATE,
        resource_id=row.id,
        summary="Complaint note created",
        metadata={"visibility": data.visibility, "note_id": str(note.id)},
    )
    return note


def list_notes(
    session: Session, ctx: OrganisationContext, complaint_id: uuid.UUID
) -> list[ComplaintNote]:
    get_complaint(session, ctx, complaint_id)
    stmt = select(ComplaintNote).where(
        ComplaintNote.organisation_id == ctx.organisation_id,
        ComplaintNote.complaint_id == complaint_id,
    )
    if not access.can_view_internal_notes(ctx) or ctx.role == HMoreRole.TENANT:
        stmt = stmt.where(ComplaintNote.visibility == "tenant_visible")
    return list(session.scalars(stmt.order_by(ComplaintNote.created_at.asc())).all())


def update_deadlines(
    session: Session,
    ctx: OrganisationContext,
    complaint_id: uuid.UUID,
    data: DeadlineUpdateRequest,
) -> Complaint:
    row = get_complaint(session, ctx, complaint_id)
    if ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    require_permission(ctx.authorization, Permission.COMPLAINTS_DEADLINES_MANAGE)
    changes: list[tuple[str, datetime | None, datetime | None]] = []
    if data.acknowledge_due_at is not None:
        changes.append(("acknowledge_due_at", row.acknowledge_due_at, data.acknowledge_due_at))
        row.acknowledge_due_at = data.acknowledge_due_at
    if data.response_due_at is not None:
        changes.append(("response_due_at", row.response_due_at, data.response_due_at))
        row.response_due_at = data.response_due_at
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No deadline fields provided")
    for field, prev, new in changes:
        session.add(
            ComplaintDeadlineChange(
                organisation_id=ctx.organisation_id,
                complaint_id=row.id,
                field_name=field,
                previous_value=prev,
                new_value=new,
                reason=data.reason,
                changed_by_user_id=ctx.user_id,
            )
        )
    session.flush()
    _history(
        session,
        ctx,
        row,
        event_type="deadline_change",
        summary="Operational deadline updated",
        detail=data.reason,
        tenant_visible=False,
    )
    _audit(
        session,
        ctx,
        action=audit_events.COMPLAINT_DEADLINE,
        resource_id=row.id,
        summary="Complaint deadline changed",
    )
    return row


def escalate_complaint(
    session: Session, ctx: OrganisationContext, complaint_id: uuid.UUID, data: EscalateRequest
) -> ComplaintEscalation:
    row = get_complaint(session, ctx, complaint_id)
    if ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    require_permission(ctx.authorization, Permission.COMPLAINTS_ESCALATE)
    key = data.idempotency_key or f"manual:{ctx.user_id}:{row.id}:{_now().strftime('%Y%m%d%H%M')}"
    existing = session.scalar(
        select(ComplaintEscalation).where(
            ComplaintEscalation.complaint_id == row.id,
            ComplaintEscalation.idempotency_key == key,
        )
    )
    if existing is not None:
        return existing
    esc = ComplaintEscalation(
        organisation_id=ctx.organisation_id,
        complaint_id=row.id,
        idempotency_key=key,
        reason=data.reason,
        escalated_by_user_id=ctx.user_id,
        recipient_role=data.recipient_role,
        recipient_user_id=data.recipient_user_id,
        previous_assigned_user_id=row.assigned_user_id,
        status="open",
        escalated_at=_now(),
    )
    session.add(esc)
    if row.status not in {"resolved", "closed", "withdrawn"}:
        prev = row.status
        row.status = "escalated"
        session.add(
            ComplaintStatusHistory(
                organisation_id=ctx.organisation_id,
                complaint_id=row.id,
                from_status=prev,
                to_status="escalated",
                changed_by_user_id=ctx.user_id,
                note=data.reason[:1000],
            )
        )
    session.flush()
    _history(
        session,
        ctx,
        row,
        event_type="escalation",
        summary="Complaint escalated",
        detail=data.reason,
        tenant_visible=True,
    )
    _audit(
        session,
        ctx,
        action=audit_events.COMPLAINT_ESCALATE,
        resource_id=row.id,
        summary="Complaint escalated",
        metadata={"escalation_id": str(esc.id)},
    )
    return esc


def resolve_escalation(
    session: Session,
    ctx: OrganisationContext,
    escalation_id: uuid.UUID,
    data: ResolveEscalationRequest,
) -> ComplaintEscalation:
    if ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    require_permission(ctx.authorization, Permission.COMPLAINTS_ESCALATE)
    esc = session.get(ComplaintEscalation, escalation_id)
    if esc is None or esc.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found")
    get_complaint(session, ctx, esc.complaint_id)
    if esc.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escalation not open")
    esc.status = "resolved"
    esc.outcome = data.outcome
    esc.resolved_at = _now()
    esc.resolved_by_user_id = ctx.user_id
    session.flush()
    complaint = session.get(Complaint, esc.complaint_id)
    if complaint:
        _history(
            session,
            ctx,
            complaint,
            event_type="escalation_resolved",
            summary="Escalation resolved",
            detail=data.outcome,
            tenant_visible=False,
        )
        _audit(
            session,
            ctx,
            action=audit_events.COMPLAINT_ESCALATION_RESOLVE,
            resource_id=complaint.id,
            summary="Complaint escalation resolved",
            metadata={"escalation_id": str(esc.id)},
        )
    return esc


def list_escalations(
    session: Session, ctx: OrganisationContext, complaint_id: uuid.UUID
) -> list[ComplaintEscalation]:
    get_complaint(session, ctx, complaint_id)
    return list(
        session.scalars(
            select(ComplaintEscalation)
            .where(
                ComplaintEscalation.organisation_id == ctx.organisation_id,
                ComplaintEscalation.complaint_id == complaint_id,
            )
            .order_by(ComplaintEscalation.escalated_at.desc())
        ).all()
    )


def list_history(
    session: Session, ctx: OrganisationContext, complaint_id: uuid.UUID
) -> list[ComplaintHistoryEvent]:
    get_complaint(session, ctx, complaint_id)
    stmt = select(ComplaintHistoryEvent).where(
        ComplaintHistoryEvent.organisation_id == ctx.organisation_id,
        ComplaintHistoryEvent.complaint_id == complaint_id,
    )
    if ctx.role == HMoreRole.TENANT or not access.can_view_internal_notes(ctx):
        stmt = stmt.where(ComplaintHistoryEvent.is_tenant_visible.is_(True))
    return list(session.scalars(stmt.order_by(ComplaintHistoryEvent.created_at.asc())).all())


def associate_file(
    session: Session,
    ctx: OrganisationContext,
    complaint_id: uuid.UUID,
    data: AssociateFileRequest,
) -> Complaint:
    row = get_complaint(session, ctx, complaint_id)
    if ctx.role == HMoreRole.TENANT:
        data_visible = True
    else:
        data_visible = data.is_tenant_visible
        if ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    meta = session.get(FileMetadata, data.file_id)
    if meta is None or meta.organisation_id != ctx.organisation_id or meta.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    meta.resource_type = "complaint"
    meta.resource_id = str(row.id)
    existing = session.scalar(
        select(ComplaintFile).where(
            ComplaintFile.complaint_id == row.id, ComplaintFile.file_id == data.file_id
        )
    )
    if existing is None:
        session.add(
            ComplaintFile(
                organisation_id=ctx.organisation_id,
                complaint_id=row.id,
                file_id=data.file_id,
                associated_by_user_id=ctx.user_id,
                is_tenant_visible=data_visible,
            )
        )
    session.flush()
    _history(
        session,
        ctx,
        row,
        event_type="file_associated",
        summary="Supporting file associated",
        tenant_visible=data_visible,
    )
    _audit(
        session,
        ctx,
        action=audit_events.COMPLAINT_FILE_ASSOCIATE,
        resource_id=row.id,
        summary="Complaint file associated",
        metadata={"file_id": str(data.file_id)},
    )
    return row


def dashboard_stats(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    rows, _ = list_complaints(session, ctx, page=1, page_size=500)
    now = _now()
    by_priority = {"low": 0, "normal": 0, "high": 0, "urgent": 0}
    open_count = 0
    awaiting = 0
    upcoming = 0
    overdue = 0
    escalated = 0
    recently_resolved = 0
    week_ago = now - timedelta(days=7)
    for row in rows:
        by_priority[row.priority] = by_priority.get(row.priority, 0) + 1
        if row.status in OPEN_STATUSES:
            open_count += 1
        if row.status in {"under_review", "investigation", "submitted", "acknowledged"}:
            awaiting += 1
        if is_overdue(row, now):
            overdue += 1
        elif row.response_due_at and now <= row.response_due_at <= now + timedelta(days=3):
            if row.status in OPEN_STATUSES:
                upcoming += 1
        if row.status == "escalated" or _has_open_escalation(session, row.id):
            escalated += 1
        if row.status == "resolved" and row.resolved_at and row.resolved_at >= week_ago:
            recently_resolved += 1
    return {
        "total": len(rows),
        "open_count": open_count,
        "by_priority": by_priority,
        "awaiting_investigation": awaiting,
        "upcoming_deadlines": upcoming,
        "overdue": overdue,
        "escalated": escalated,
        "recently_resolved": recently_resolved,
    }
