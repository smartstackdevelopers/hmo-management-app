"""F2.8 maintenance request services."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.idempotency.service import assert_if_match, without_match_field
from app.audit.service import AuditOutcome, record_event
from app.db.models.enums import HMoreRole
from app.db.models.file_metadata import FileMetadata
from app.db.models.maintenance import (
    MaintenanceApproval,
    MaintenanceCategory,
    MaintenanceEmergencyContent,
    MaintenanceHistoryEvent,
    MaintenanceNote,
    MaintenancePriorityChange,
    MaintenanceRequest,
    MaintenanceRequestFile,
    MaintenanceStatusHistory,
    MaintenanceVisit,
)
from app.db.models.property import Property
from app.db.models.room import Room
from app.db.models.scheduling import TenantVisit
from app.db.models.support_ops import CaseAssignment
from app.db.models.tenant import Tenant
from app.maintenance import access
from app.maintenance.schemas import (
    ApprovalDecisionRequest,
    AssociatePhotoRequest,
    AssignRequest,
    CategoryCreate,
    CompleteRequest,
    EmergencyContentUpdate,
    MaintenanceCreate,
    MaintenanceUpdate,
    NoteCreate,
    PriorityRequest,
    ScheduleVisitRequest,
    StatusTransitionRequest,
    VisitCancelRequest,
    VisitCompleteRequest,
    VisitRescheduleRequest,
)
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.support.access import assert_tenant_support_access
from app.storage import service as file_service
from app.tenancy.context import OrganisationContext

MAINT_TRANSITIONS: dict[str, frozenset[str]] = {
    "submitted": frozenset({"acknowledged", "under_review", "cancelled"}),
    "acknowledged": frozenset({"under_review", "cancelled"}),
    "under_review": frozenset(
        {"awaiting_approval", "assigned", "scheduled", "in_progress", "cancelled", "on_hold"}
    ),
    "awaiting_approval": frozenset(),  # use approval endpoint
    "approved": frozenset({"assigned", "scheduled", "in_progress", "cancelled"}),
    "rejected": frozenset({"closed", "cancelled"}),
    "assigned": frozenset({"scheduled", "in_progress", "on_hold", "cancelled"}),
    "scheduled": frozenset({"in_progress", "on_hold", "cancelled"}),
    "in_progress": frozenset({"awaiting_parts", "on_hold", "completed", "cancelled"}),
    "awaiting_parts": frozenset({"in_progress", "on_hold", "cancelled"}),
    "on_hold": frozenset({"in_progress", "assigned", "cancelled"}),
    "completed": frozenset({"closed", "reopened"}),
    "closed": frozenset({"reopened"}),
    "reopened": frozenset({"under_review", "assigned", "in_progress", "cancelled"}),
    "cancelled": frozenset(),
}

OPEN_STATUSES = frozenset(
    {
        "submitted",
        "acknowledged",
        "under_review",
        "awaiting_approval",
        "approved",
        "rejected",
        "assigned",
        "scheduled",
        "in_progress",
        "awaiting_parts",
        "on_hold",
        "reopened",
    }
)

REASON_STATUSES = frozenset({"rejected", "cancelled", "reopened", "on_hold"})

DEFAULT_CATEGORIES: tuple[tuple[str, str, int, bool, str | None], ...] = (
    ("plumbing", "Plumbing", 10, False, None),
    ("electrical", "Electrical", 20, False, None),
    ("heating", "Heating", 30, True, "gas"),
    ("water_leak", "Water leaks", 40, False, None),
    ("structural", "Structural issues", 50, False, None),
    ("doors_windows", "Doors and windows", 60, False, None),
    ("appliances", "Appliances", 70, False, None),
    ("safety", "Safety-related maintenance", 80, True, "fire"),
    ("general", "General repairs", 90, False, None),
    ("other", "Other", 100, False, None),
)


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
        resource_type="maintenance_request",
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
    row: MaintenanceRequest,
    *,
    event_type: str,
    summary: str,
    detail: str | None = None,
    tenant_visible: bool = True,
) -> None:
    session.add(
        MaintenanceHistoryEvent(
            organisation_id=ctx.organisation_id,
            request_id=row.id,
            event_type=event_type,
            summary=summary,
            detail=detail,
            actor_user_id=ctx.user_id,
            is_tenant_visible=tenant_visible,
        )
    )


def _next_ref(session: Session, org_id: uuid.UUID) -> str:
    day = _now().strftime("%Y%m%d")
    prefix = f"MR-{day}-"
    count = (
        session.scalar(
            select(func.count())
            .select_from(MaintenanceRequest)
            .where(
                MaintenanceRequest.organisation_id == org_id,
                MaintenanceRequest.reference_number.like(f"{prefix}%"),
            )
        )
        or 0
    )
    return f"{prefix}{count + 1:04d}"


def ensure_defaults(session: Session, ctx: OrganisationContext) -> None:
    access.require_maintenance_manage(ctx)
    existing = session.scalars(
        select(MaintenanceCategory).where(MaintenanceCategory.organisation_id == ctx.organisation_id)
    ).first()
    if existing is None:
        for code, title, order, trig, kind in DEFAULT_CATEGORIES:
            session.add(
                MaintenanceCategory(
                    organisation_id=ctx.organisation_id,
                    code=code,
                    title=title,
                    description="Operational category — not a statutory classification.",
                    triggers_emergency_panel=trig,
                    emergency_kind=kind,
                    sort_order=order,
                    is_active=True,
                )
            )
        for kind, title, body in (
            (
                "gas",
                "Gas emergency — operational guidance (requires formal approval)",
                "Placeholder: your organisation must replace this with approved gas safety guidance. "
                "Do not attempt repairs yourself. If you smell gas or suspect a leak, leave the area, "
                "avoid ignition sources, and contact your organisation's emergency procedures or the "
                "National Gas Emergency Service using the number your organisation publishes. "
                "This system is not an emergency reporting channel.",
            ),
            (
                "fire",
                "Fire safety — operational guidance (requires formal approval)",
                "Placeholder: your organisation must replace this with approved fire-safety guidance. "
                "If there is immediate danger to life, follow your organisation's evacuation plan and "
                "contact the emergency services. Do not use this screen as a substitute for calling "
                "999 when appropriate.",
            ),
        ):
            session.add(
                MaintenanceEmergencyContent(
                    organisation_id=ctx.organisation_id,
                    kind=kind,
                    title=title,
                    body=body,
                    requires_formal_approval=True,
                    approved_for_use=False,
                )
            )
    session.flush()


def category_emergency_kind(session: Session, org_id: uuid.UUID, code: str) -> str | None:
    row = session.scalar(
        select(MaintenanceCategory).where(
            MaintenanceCategory.organisation_id == org_id,
            MaintenanceCategory.code == code,
            MaintenanceCategory.is_active.is_(True),
        )
    )
    if row is None:
        return None
    return row.emergency_kind if row.triggers_emergency_panel else None


def request_out_dict(session: Session, ctx: OrganisationContext, row: MaintenanceRequest) -> dict[str, Any]:
    file_ids = list(
        session.scalars(
            select(MaintenanceRequestFile.file_id).where(MaintenanceRequestFile.request_id == row.id)
        ).all()
    )
    ek = category_emergency_kind(session, ctx.organisation_id, row.category_code)
    show_panel = row.priority == "emergency" or ek is not None
    work_notes = row.work_notes if ctx.role != HMoreRole.TENANT else None
    return {
        "id": row.id,
        "reference_number": row.reference_number,
        "title": row.title,
        "description": row.description,
        "category_code": row.category_code,
        "priority": row.priority,
        "status": row.status,
        "property_id": row.property_id,
        "room_id": row.room_id,
        "tenant_id": row.tenant_id,
        "reported_by_user_id": row.reported_by_user_id,
        "assigned_user_id": row.assigned_user_id,
        "requires_approval": row.requires_approval,
        "approval_status": row.approval_status,
        "scheduled_visit_at": row.scheduled_visit_at,
        "visit_timezone": row.visit_timezone,
        "reported_at": row.reported_at,
        "acknowledged_at": row.acknowledged_at,
        "completed_at": row.completed_at,
        "closed_at": row.closed_at,
        "work_notes": work_notes,
        "completion_summary": row.completion_summary,
        "is_emergency_priority": row.priority == "emergency",
        "show_emergency_panel": show_panel,
        "emergency_kind_hint": ek,
        "file_ids": file_ids,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def create_request(session: Session, ctx: OrganisationContext, data: MaintenanceCreate) -> MaintenanceRequest:
    access.require_maintenance_create(ctx)
    prop = session.get(Property, data.property_id)
    if prop is None or prop.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid property")
    access.assert_room_belongs(session, data.property_id, data.room_id)

    tenant_id = data.tenant_id
    if ctx.role == HMoreRole.TENANT:
        own = access.resolve_own_tenant_id(session, ctx)
        tenant_id = own
        if tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant profile not linked"
            )
        if data.priority == "emergency":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Emergency priority must be set by authorised staff after review — use Urgent for now",
            )
    elif ctx.role == HMoreRole.SUPPORT_WORKER:
        if tenant_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id required")
        assert_tenant_support_access(session, ctx, tenant_id)

    if ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}:
        if data.priority == "emergency":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot set emergency priority")

    row = MaintenanceRequest(
        organisation_id=ctx.organisation_id,
        reference_number=_next_ref(session, ctx.organisation_id),
        title=data.title,
        description=data.description,
        category_code=data.category_code,
        priority=data.priority,
        status="submitted",
        property_id=data.property_id,
        room_id=data.room_id,
        tenant_id=tenant_id,
        reported_by_user_id=ctx.user_id,
        requires_approval=data.requires_approval,
        approval_status="pending" if data.requires_approval else None,
        reported_at=_now(),
        visit_timezone="Europe/London",
    )
    if data.requires_approval:
        row.status = "awaiting_approval"
    session.add(row)
    session.flush()
    session.add(
        MaintenanceStatusHistory(
            organisation_id=ctx.organisation_id,
            request_id=row.id,
            from_status=None,
            to_status=row.status,
            changed_by_user_id=ctx.user_id,
            note="Request created",
        )
    )
    _history(session, ctx, row, event_type="created", summary="Maintenance request submitted")
    _audit(session, ctx, action=audit_events.MAINTENANCE_CREATE, resource_id=row.id, summary="Maintenance created")
    return row


def get_request(session: Session, ctx: OrganisationContext, request_id: uuid.UUID) -> MaintenanceRequest:
    row = session.get(MaintenanceRequest, request_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found")
    access.assert_can_view_request(session, ctx, row)
    return row


def _scoped_requests_stmt(session: Session, ctx: OrganisationContext) -> Any:
    """Role-scoped filter for maintenance requests (list and aggregates)."""
    stmt = select(MaintenanceRequest).where(MaintenanceRequest.organisation_id == ctx.organisation_id)
    if ctx.role == HMoreRole.TENANT:
        own = access.resolve_own_tenant_id(session, ctx)
        stmt = stmt.where(
            or_(
                MaintenanceRequest.tenant_id == own,
                MaintenanceRequest.reported_by_user_id == ctx.user_id,
            )
        )
    elif ctx.role == HMoreRole.LANDLORD:
        props = select(Property.id).where(
            Property.organisation_id == ctx.organisation_id,
            or_(Property.landlord_user_id == ctx.user_id, Property.landlord_user_id.is_(None)),
        )
        stmt = stmt.where(MaintenanceRequest.property_id.in_(props))
    elif ctx.role == HMoreRole.SUPPORT_WORKER:
        assigned_tenants = select(CaseAssignment.tenant_id).where(
            CaseAssignment.organisation_id == ctx.organisation_id,
            CaseAssignment.support_worker_user_id == ctx.user_id,
            CaseAssignment.status == "active",
        )
        stmt = stmt.where(
            or_(
                MaintenanceRequest.tenant_id.in_(assigned_tenants),
                MaintenanceRequest.assigned_user_id == ctx.user_id,
            )
        )
    elif ctx.role == HMoreRole.MAINTENANCE_CONTRACTOR:
        visit_req = select(MaintenanceVisit.request_id).where(
            MaintenanceVisit.organisation_id == ctx.organisation_id,
            MaintenanceVisit.assignee_user_id == ctx.user_id,
        )
        stmt = stmt.where(
            or_(MaintenanceRequest.assigned_user_id == ctx.user_id, MaintenanceRequest.id.in_(visit_req))
        )
    return stmt


def list_requests(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    status_filter: str | None,
    priority: str | None,
    property_id: uuid.UUID | None,
    pending_approval: bool,
    q: str | None,
) -> tuple[list[MaintenanceRequest], int]:
    access.require_maintenance_read(ctx)
    stmt = _scoped_requests_stmt(session, ctx)

    if status_filter:
        stmt = stmt.where(MaintenanceRequest.status == status_filter)
    if priority:
        stmt = stmt.where(MaintenanceRequest.priority == priority)
    if property_id:
        stmt = stmt.where(MaintenanceRequest.property_id == property_id)
    if pending_approval:
        stmt = stmt.where(
            MaintenanceRequest.requires_approval.is_(True),
            MaintenanceRequest.approval_status == "pending",
            MaintenanceRequest.status == "awaiting_approval",
        )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                MaintenanceRequest.title.ilike(like),
                MaintenanceRequest.reference_number.ilike(like),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())  # type: ignore[assignment]
    total = session.scalar(count_stmt) or 0
    rows = list(
        session.scalars(
            stmt.order_by(MaintenanceRequest.reported_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, int(total)


def update_request(
    session: Session, ctx: OrganisationContext, request_id: uuid.UUID, data: MaintenanceUpdate
) -> MaintenanceRequest:
    row = get_request(session, ctx, request_id)
    if row.status in {"closed", "cancelled"} and ctx.role not in {
        HMoreRole.ORGANISATION_ADMIN,
        HMoreRole.SUPER_ADMIN,
    }:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request is closed")
    if ctx.role == HMoreRole.TENANT:
        if row.status not in {"submitted", "reopened"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update")
    elif ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_MANAGE)
    elif ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.MAINTENANCE_CREATE_ASSIGNED)
    elif ctx.role == HMoreRole.SUPER_ADMIN:
        pass
    elif ctx.role == HMoreRole.MAINTENANCE_CONTRACTOR:
        require_permission(ctx.authorization, Permission.MAINTENANCE_READ_ASSIGNED)
        if row.assigned_user_id != ctx.user_id:
            v = session.scalar(
                select(MaintenanceVisit).where(
                    MaintenanceVisit.request_id == row.id,
                    MaintenanceVisit.assignee_user_id == ctx.user_id,
                )
            )
            if v is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    assert_if_match(row.updated_at, data.if_match_updated_at)
    for k, v in without_match_field(data.model_dump(exclude_unset=True)).items():
        setattr(row, k, v)
    session.flush()
    _history(session, ctx, row, event_type="updated", summary="Request updated", tenant_visible=True)
    _audit(session, ctx, action=audit_events.MAINTENANCE_UPDATE, resource_id=row.id, summary="Maintenance updated")
    return row


def assign_request(
    session: Session, ctx: OrganisationContext, request_id: uuid.UUID, data: AssignRequest
) -> MaintenanceRequest:
    row = get_request(session, ctx, request_id)
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_ASSIGN)
    elif ctx.role != HMoreRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    prev = row.assigned_user_id
    row.assigned_user_id = data.assigned_user_id
    if row.status in {"submitted", "acknowledged", "under_review", "approved"}:
        row.status = "assigned"
    session.flush()
    _history(
        session,
        ctx,
        row,
        event_type="assignment",
        summary="Assignment updated",
        detail=data.note,
        tenant_visible=False,
    )
    _audit(
        session,
        ctx,
        action=audit_events.MAINTENANCE_ASSIGN,
        resource_id=row.id,
        summary="Maintenance assigned",
        metadata={"from": str(prev), "to": str(data.assigned_user_id)},
    )
    return row


def change_priority(
    session: Session, ctx: OrganisationContext, request_id: uuid.UUID, data: PriorityRequest
) -> MaintenanceRequest:
    row = get_request(session, ctx, request_id)
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_PRIORITY_MANAGE)
    elif ctx.role != HMoreRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    prev = row.priority
    row.priority = data.priority
    session.add(
        MaintenancePriorityChange(
            organisation_id=ctx.organisation_id,
            request_id=row.id,
            from_priority=prev,
            to_priority=data.priority,
            reason=data.reason,
            changed_by_user_id=ctx.user_id,
        )
    )
    session.flush()
    _history(
        session,
        ctx,
        row,
        event_type="priority",
        summary=f"Priority {prev} → {data.priority}",
        detail=data.reason,
        tenant_visible=True,
    )
    _audit(
        session,
        ctx,
        action=audit_events.MAINTENANCE_PRIORITY,
        resource_id=row.id,
        summary="Priority changed",
        metadata={"from": prev, "to": data.priority},
    )
    return row


def _approval_gate(row: MaintenanceRequest, target: str) -> None:
    if row.requires_approval and row.approval_status != "approved":
        if target in {
            "assigned",
            "scheduled",
            "in_progress",
            "awaiting_parts",
            "completed",
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approval required before this transition",
            )


def transition_status(
    session: Session, ctx: OrganisationContext, request_id: uuid.UUID, data: StatusTransitionRequest
) -> MaintenanceRequest:
    row = get_request(session, ctx, request_id)
    target = data.status

    if ctx.role == HMoreRole.TENANT:
        if target not in {"cancelled"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if row.reported_by_user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif ctx.role == HMoreRole.MAINTENANCE_CONTRACTOR:
        require_permission(ctx.authorization, Permission.MAINTENANCE_COMPLETE)
        if target not in {"in_progress", "on_hold"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if row.assigned_user_id != ctx.user_id:
            # allow if visit assignee
            v = session.scalar(
                select(MaintenanceVisit).where(
                    MaintenanceVisit.request_id == row.id,
                    MaintenanceVisit.assignee_user_id == ctx.user_id,
                )
            )
            if v is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif target in {"closed", "reopened"}:
        if ctx.role == HMoreRole.ORGANISATION_ADMIN:
            require_permission(ctx.authorization, Permission.MAINTENANCE_CLOSE_REOPEN)
        elif ctx.role != HMoreRole.SUPER_ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.MAINTENANCE_CREATE_ASSIGNED)
        if target in {
            "assigned",
            "approved",
            "rejected",
            "awaiting_approval",
            "closed",
            "reopened",
        }:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_MANAGE)
    elif ctx.role == HMoreRole.SUPER_ADMIN:
        pass
    elif ctx.role == HMoreRole.LANDLORD:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    allowed = MAINT_TRANSITIONS.get(row.status, frozenset())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {row.status} to {target}",
        )
    if target in REASON_STATUSES and not data.note:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reason required")

    _approval_gate(row, target)
    assert_if_match(row.updated_at, data.if_match_updated_at)

    if target == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use POST /complete with work notes",
        )

    prev = row.status
    row.status = target
    now = _now()
    if target == "acknowledged":
        row.acknowledged_at = now
    if target == "closed":
        row.closed_at = now

    session.add(
        MaintenanceStatusHistory(
            organisation_id=ctx.organisation_id,
            request_id=row.id,
            from_status=prev,
            to_status=target,
            changed_by_user_id=ctx.user_id,
            note=data.note,
        )
    )
    _history(session, ctx, row, event_type="status", summary=f"Status {prev} → {target}", detail=data.note)
    audit_action = audit_events.MAINTENANCE_STATUS
    if target == "closed":
        audit_action = audit_events.MAINTENANCE_CLOSE
    elif target == "reopened":
        audit_action = audit_events.MAINTENANCE_REOPEN
    _audit(
        session,
        ctx,
        action=audit_action,
        resource_id=row.id,
        summary=f"Status {prev} → {target}",
    )
    session.flush()
    return row


def record_approval(
    session: Session, ctx: OrganisationContext, request_id: uuid.UUID, data: ApprovalDecisionRequest
) -> MaintenanceRequest:
    row = get_request(session, ctx, request_id)
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_APPROVE)
    elif ctx.role != HMoreRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if not row.requires_approval or row.status != "awaiting_approval":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not awaiting approval")
    if data.decision == "rejected" and not (data.reason and data.reason.strip()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reason required for rejection")
    row.approval_status = data.decision
    prev = row.status
    if data.decision == "approved":
        row.status = "approved"
    else:
        row.status = "rejected"
    session.add(
        MaintenanceApproval(
            organisation_id=ctx.organisation_id,
            request_id=row.id,
            approver_user_id=ctx.user_id,
            decision=data.decision,
            reason=data.reason,
            decided_at=_now(),
        )
    )
    session.add(
        MaintenanceStatusHistory(
            organisation_id=ctx.organisation_id,
            request_id=row.id,
            from_status=prev,
            to_status=row.status,
            changed_by_user_id=ctx.user_id,
            note=data.reason,
        )
    )
    _history(
        session,
        ctx,
        row,
        event_type="approval",
        summary=f"Approval {data.decision}",
        detail=data.reason,
    )
    _audit(
        session,
        ctx,
        action=audit_events.MAINTENANCE_APPROVAL,
        resource_id=row.id,
        summary="Maintenance approval decision",
        metadata={"decision": data.decision},
    )
    session.flush()
    return row


def schedule_visit(
    session: Session, ctx: OrganisationContext, request_id: uuid.UUID, data: ScheduleVisitRequest
) -> MaintenanceVisit:
    row = get_request(session, ctx, request_id)
    if ctx.role not in {
        HMoreRole.SUPER_ADMIN,
        HMoreRole.ORGANISATION_ADMIN,
        HMoreRole.SUPPORT_WORKER,
        HMoreRole.MAINTENANCE_CONTRACTOR,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_SCHEDULE)
    _approval_gate(row, "scheduled")

    assignee = data.assignee_user_id or row.assigned_user_id
    if ctx.role == HMoreRole.MAINTENANCE_CONTRACTOR:
        if row.assigned_user_id not in (None, ctx.user_id):
            v0 = session.scalar(
                select(MaintenanceVisit).where(
                    MaintenanceVisit.request_id == row.id,
                    MaintenanceVisit.assignee_user_id == ctx.user_id,
                )
            )
            if v0 is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if assignee is not None and assignee != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Contractor may only schedule own visits")
        assignee = ctx.user_id
    if data.link_tenant_visit_id is not None:
        tv = session.get(TenantVisit, data.link_tenant_visit_id)
        if tv is None or tv.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant visit")

    if assignee is not None:
        conflict = session.scalar(
            select(MaintenanceVisit).where(
                MaintenanceVisit.organisation_id == ctx.organisation_id,
                MaintenanceVisit.status.in_(("scheduled", "rescheduled")),
                MaintenanceVisit.scheduled_at == data.scheduled_at,
                MaintenanceVisit.assignee_user_id == assignee,
            )
        )
        if conflict is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Scheduling conflict")

    visit = MaintenanceVisit(
        organisation_id=ctx.organisation_id,
        request_id=row.id,
        assignee_user_id=assignee,
        scheduled_at=data.scheduled_at,
        timezone=data.timezone,
        status="scheduled",
        linked_tenant_visit_id=data.link_tenant_visit_id,
    )
    session.add(visit)
    row.scheduled_visit_at = data.scheduled_at
    row.visit_timezone = data.timezone
    row.status = "scheduled"
    if data.link_tenant_visit_id:
        row.linked_tenant_visit_id = data.link_tenant_visit_id
    session.flush()
    _history(
        session,
        ctx,
        row,
        event_type="schedule",
        summary="Visit scheduled",
        tenant_visible=True,
    )
    _audit(session, ctx, action=audit_events.MAINTENANCE_SCHEDULE, resource_id=row.id, summary="Visit scheduled")
    return visit


def get_visit(
    session: Session, ctx: OrganisationContext, request_id: uuid.UUID, visit_id: uuid.UUID
) -> MaintenanceVisit:
    row = session.get(MaintenanceVisit, visit_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.request_id != request_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    get_request(session, ctx, request_id)
    return row


def reschedule_visit(
    session: Session,
    ctx: OrganisationContext,
    request_id: uuid.UUID,
    visit_id: uuid.UUID,
    data: VisitRescheduleRequest,
) -> MaintenanceVisit:
    visit = get_visit(session, ctx, request_id, visit_id)
    if ctx.role not in {
        HMoreRole.SUPER_ADMIN,
        HMoreRole.ORGANISATION_ADMIN,
        HMoreRole.SUPPORT_WORKER,
        HMoreRole.MAINTENANCE_CONTRACTOR,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ctx.role == HMoreRole.MAINTENANCE_CONTRACTOR and visit.assignee_user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_SCHEDULE)
    if visit.status not in {"scheduled", "rescheduled"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Visit cannot be rescheduled")
    req = get_request(session, ctx, request_id)
    _approval_gate(req, "scheduled")

    assignee = data.assignee_user_id if data.assignee_user_id is not None else visit.assignee_user_id
    if assignee is not None:
        conflict = session.scalar(
            select(MaintenanceVisit).where(
                MaintenanceVisit.organisation_id == ctx.organisation_id,
                MaintenanceVisit.id != visit.id,
                MaintenanceVisit.status.in_(("scheduled", "rescheduled")),
                MaintenanceVisit.scheduled_at == data.scheduled_at,
                MaintenanceVisit.assignee_user_id == assignee,
            )
        )
        if conflict is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Scheduling conflict")
    prev = visit.scheduled_at
    visit.scheduled_at = data.scheduled_at
    visit.timezone = data.timezone
    visit.assignee_user_id = assignee
    visit.status = "rescheduled"
    req.scheduled_visit_at = data.scheduled_at
    req.visit_timezone = data.timezone
    if req.status not in {"completed", "closed", "cancelled"}:
        req.status = "scheduled"
    session.flush()
    _history(
        session,
        ctx,
        req,
        event_type="schedule",
        summary=f"Visit rescheduled from {prev.isoformat()}",
        tenant_visible=True,
    )
    _audit(session, ctx, action=audit_events.MAINTENANCE_SCHEDULE, resource_id=req.id, summary="Visit rescheduled")
    return visit


def cancel_visit(
    session: Session,
    ctx: OrganisationContext,
    request_id: uuid.UUID,
    visit_id: uuid.UUID,
    data: VisitCancelRequest,
) -> MaintenanceVisit:
    visit = get_visit(session, ctx, request_id, visit_id)
    if ctx.role not in {
        HMoreRole.SUPER_ADMIN,
        HMoreRole.ORGANISATION_ADMIN,
        HMoreRole.SUPPORT_WORKER,
        HMoreRole.MAINTENANCE_CONTRACTOR,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ctx.role == HMoreRole.MAINTENANCE_CONTRACTOR and visit.assignee_user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_SCHEDULE)
    if visit.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already cancelled")
    visit.status = "cancelled"
    visit.cancel_reason = data.reason
    req = get_request(session, ctx, request_id)
    other_active = session.scalar(
        select(func.count())
        .select_from(MaintenanceVisit)
        .where(
            MaintenanceVisit.request_id == req.id,
            MaintenanceVisit.id != visit.id,
            MaintenanceVisit.status.in_(("scheduled", "rescheduled")),
        )
    )
    if (other_active or 0) == 0:
        req.scheduled_visit_at = None
    session.flush()
    _history(session, ctx, req, event_type="schedule", summary="Visit cancelled", detail=data.reason)
    _audit(session, ctx, action=audit_events.MAINTENANCE_SCHEDULE, resource_id=req.id, summary="Visit cancelled")
    return visit


def complete_visit(
    session: Session,
    ctx: OrganisationContext,
    request_id: uuid.UUID,
    visit_id: uuid.UUID,
    data: VisitCompleteRequest,
) -> MaintenanceVisit:
    visit = get_visit(session, ctx, request_id, visit_id)
    if ctx.role not in {
        HMoreRole.SUPER_ADMIN,
        HMoreRole.ORGANISATION_ADMIN,
        HMoreRole.SUPPORT_WORKER,
        HMoreRole.MAINTENANCE_CONTRACTOR,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ctx.role == HMoreRole.MAINTENANCE_CONTRACTOR and visit.assignee_user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_SCHEDULE)
    if visit.status in {"cancelled", "completed", "missed"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Visit already finalised")
    now = _now()
    if data.missed:
        visit.status = "missed"
    else:
        if not (data.work_notes and data.work_notes.strip()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="work_notes required when visit completed"
            )
        visit.status = "completed"
        visit.completed_at = now
        visit.work_notes = data.work_notes
    session.flush()
    req = get_request(session, ctx, request_id)
    _history(
        session,
        ctx,
        req,
        event_type="schedule",
        summary="Visit marked missed" if data.missed else "Visit completed",
        detail=data.work_notes,
    )
    _audit(session, ctx, action=audit_events.MAINTENANCE_SCHEDULE, resource_id=req.id, summary="Visit outcome recorded")
    return visit


def list_categories(session: Session, ctx: OrganisationContext) -> list[MaintenanceCategory]:
    access.require_maintenance_read(ctx)
    return list(
        session.scalars(
            select(MaintenanceCategory)
            .where(
                MaintenanceCategory.organisation_id == ctx.organisation_id,
                MaintenanceCategory.is_active.is_(True),
            )
            .order_by(MaintenanceCategory.sort_order.asc(), MaintenanceCategory.code.asc())
        ).all()
    )


def create_category(
    session: Session, ctx: OrganisationContext, data: CategoryCreate
) -> MaintenanceCategory:
    access.require_maintenance_manage(ctx)
    dup = session.scalar(
        select(MaintenanceCategory).where(
            MaintenanceCategory.organisation_id == ctx.organisation_id,
            MaintenanceCategory.code == data.code,
        )
    )
    if dup is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category code already exists")
    row = MaintenanceCategory(
        organisation_id=ctx.organisation_id,
        code=data.code,
        title=data.title,
        description=data.description,
        triggers_emergency_panel=data.triggers_emergency_panel,
        emergency_kind=data.emergency_kind,
        sort_order=data.sort_order,
        is_active=True,
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.MAINTENANCE_UPDATE,
        resource_type="maintenance_category",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Maintenance category created",
        metadata={"code": row.code},
    )
    return row


def add_note(session: Session, ctx: OrganisationContext, request_id: uuid.UUID, data: NoteCreate) -> MaintenanceNote:
    row = get_request(session, ctx, request_id)
    if ctx.role == HMoreRole.TENANT:
        if data.visibility != "tenant_visible":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenants may only add tenant-visible notes")
    elif ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_NOTES_ADD)
    assert_if_match(row.updated_at, data.if_match_updated_at)
    note = MaintenanceNote(
        organisation_id=ctx.organisation_id,
        request_id=row.id,
        author_user_id=ctx.user_id,
        visibility=data.visibility,
        body=data.body,
    )
    session.add(note)
    session.flush()
    _history(
        session,
        ctx,
        row,
        event_type="note",
        summary="Note added",
        tenant_visible=data.visibility == "tenant_visible",
    )
    _audit(session, ctx, action=audit_events.MAINTENANCE_NOTE, resource_id=row.id, summary="Note added")
    return note


def list_notes(session: Session, ctx: OrganisationContext, request_id: uuid.UUID) -> list[MaintenanceNote]:
    get_request(session, ctx, request_id)
    stmt = select(MaintenanceNote).where(MaintenanceNote.request_id == request_id)
    if ctx.role == HMoreRole.TENANT:
        stmt = stmt.where(MaintenanceNote.visibility == "tenant_visible")
    return list(session.scalars(stmt.order_by(MaintenanceNote.created_at.asc())).all())


def associate_photo(
    session: Session, ctx: OrganisationContext, request_id: uuid.UUID, data: AssociatePhotoRequest
) -> MaintenanceRequest:
    row = get_request(session, ctx, request_id)
    if ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_PHOTO_UPLOAD)
    meta = session.get(FileMetadata, data.file_id)
    if meta is None or meta.organisation_id != ctx.organisation_id or meta.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    meta.resource_type = "maintenance_request"
    meta.resource_id = str(row.id)
    existing = session.scalar(
        select(MaintenanceRequestFile).where(
            MaintenanceRequestFile.request_id == row.id,
            MaintenanceRequestFile.file_id == data.file_id,
        )
    )
    if existing is None:
        session.add(
            MaintenanceRequestFile(
                organisation_id=ctx.organisation_id,
                request_id=row.id,
                file_id=data.file_id,
                caption=data.caption,
                photo_kind=data.photo_kind,
                associated_by_user_id=ctx.user_id,
            )
        )
    session.flush()
    _history(session, ctx, row, event_type="photo", summary="Photograph associated", tenant_visible=True)
    _audit(session, ctx, action=audit_events.MAINTENANCE_FILE, resource_id=row.id, summary="Photo linked")
    return row


def list_request_files(
    session: Session, ctx: OrganisationContext, request_id: uuid.UUID
) -> list[MaintenanceRequestFile]:
    get_request(session, ctx, request_id)
    if ctx.role == HMoreRole.SUPER_ADMIN:
        pass
    else:
        require_permission(ctx.authorization, Permission.MAINTENANCE_PHOTO_READ)
    return list(
        session.scalars(
            select(MaintenanceRequestFile)
            .where(MaintenanceRequestFile.request_id == request_id)
            .order_by(MaintenanceRequestFile.created_at.asc())
        ).all()
    )


def upload_photo(
    session: Session,
    ctx: OrganisationContext,
    request_id: uuid.UUID,
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
    caption: str | None,
    photo_kind: str,
) -> MaintenanceRequest:
    row = get_request(session, ctx, request_id)
    if ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_PHOTO_UPLOAD)
    stored = file_service.upload_file(
        session,
        ctx,
        filename=filename,
        declared_content_type=content_type,
        data=data,
        resource_type="maintenance_request",
        resource_id=str(row.id),
    )
    return associate_photo(
        session,
        ctx,
        request_id,
        AssociatePhotoRequest(
            file_id=uuid.UUID(stored["id"]),
            caption=caption,
            photo_kind=photo_kind,  # type: ignore[arg-type]
        ),
    )


def complete_request(
    session: Session, ctx: OrganisationContext, request_id: uuid.UUID, data: CompleteRequest
) -> MaintenanceRequest:
    row = get_request(session, ctx, request_id)
    if ctx.role not in {
        HMoreRole.SUPER_ADMIN,
        HMoreRole.ORGANISATION_ADMIN,
        HMoreRole.MAINTENANCE_CONTRACTOR,
        HMoreRole.SUPPORT_WORKER,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_COMPLETE)
    if ctx.role == HMoreRole.MAINTENANCE_CONTRACTOR and row.assigned_user_id != ctx.user_id:
        v = session.scalar(
            select(MaintenanceVisit).where(
                MaintenanceVisit.request_id == row.id,
                MaintenanceVisit.assignee_user_id == ctx.user_id,
            )
        )
        if v is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    assert_if_match(row.updated_at, data.if_match_updated_at)
    _approval_gate(row, "completed")
    prev = row.status
    row.status = "completed"
    row.completed_at = _now()
    row.work_notes = data.work_notes
    row.completion_summary = data.completion_summary or data.work_notes[:500]
    session.add(
        MaintenanceStatusHistory(
            organisation_id=ctx.organisation_id,
            request_id=row.id,
            from_status=prev,
            to_status="completed",
            changed_by_user_id=ctx.user_id,
            note="Completed",
        )
    )
    _history(session, ctx, row, event_type="complete", summary="Work completed", tenant_visible=True)
    _audit(session, ctx, action=audit_events.MAINTENANCE_COMPLETE, resource_id=row.id, summary="Completed")
    session.flush()
    return row


def list_history(session: Session, ctx: OrganisationContext, request_id: uuid.UUID) -> list[MaintenanceHistoryEvent]:
    get_request(session, ctx, request_id)
    stmt = select(MaintenanceHistoryEvent).where(MaintenanceHistoryEvent.request_id == request_id)
    if ctx.role == HMoreRole.TENANT:
        stmt = stmt.where(MaintenanceHistoryEvent.is_tenant_visible.is_(True))
    return list(session.scalars(stmt.order_by(MaintenanceHistoryEvent.created_at.asc())).all())


def list_visits(session: Session, ctx: OrganisationContext, request_id: uuid.UUID) -> list[MaintenanceVisit]:
    get_request(session, ctx, request_id)
    return list(
        session.scalars(
            select(MaintenanceVisit)
            .where(MaintenanceVisit.request_id == request_id)
            .order_by(MaintenanceVisit.scheduled_at.asc())
        ).all()
    )


def emergency_content(session: Session, ctx: OrganisationContext, kind: str) -> MaintenanceEmergencyContent | None:
    access.require_maintenance_read(ctx)
    return session.scalar(
        select(MaintenanceEmergencyContent).where(
            MaintenanceEmergencyContent.organisation_id == ctx.organisation_id,
            MaintenanceEmergencyContent.kind == kind,
        )
    )


def update_emergency_content(
    session: Session, ctx: OrganisationContext, kind: str, data: EmergencyContentUpdate
) -> MaintenanceEmergencyContent:
    if ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_EMERGENCY_MANAGE)
    row = session.scalar(
        select(MaintenanceEmergencyContent).where(
            MaintenanceEmergencyContent.organisation_id == ctx.organisation_id,
            MaintenanceEmergencyContent.kind == kind,
        )
    )
    if row is None:
        row = MaintenanceEmergencyContent(
            organisation_id=ctx.organisation_id,
            kind=kind,
            title=data.title,
            body=data.body,
            approved_for_use=data.approved_for_use,
            last_updated_by_user_id=ctx.user_id,
        )
        session.add(row)
    else:
        row.title = data.title
        row.body = data.body
        row.approved_for_use = data.approved_for_use
        row.last_updated_by_user_id = ctx.user_id
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.MAINTENANCE_EMERGENCY_UPDATE,
        resource_id=row.id,
        summary=f"Emergency {kind} content updated",
    )
    return row


def dashboard_stats(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    access.require_maintenance_read(ctx)
    base = _scoped_requests_stmt(session, ctx).subquery()
    now = _now()
    week_ago = now - timedelta(days=7)

    total = session.scalar(select(func.count()).select_from(base)) or 0

    open_count = (
        session.scalar(
            select(func.count())
            .select_from(base)
            .where(base.c.status.in_(OPEN_STATUSES))
        )
        or 0
    )

    priority_rows = session.execute(
        select(base.c.priority, func.count())
        .select_from(base)
        .group_by(base.c.priority)
    ).all()
    by_priority = {str(p): int(c) for p, c in priority_rows}

    emergency = (
        session.scalar(
            select(func.count()).select_from(base).where(base.c.priority == "emergency")
        )
        or 0
    )

    urgent_emergency = (
        session.scalar(
            select(func.count())
            .select_from(base)
            .where(base.c.priority.in_(("urgent", "emergency")))
        )
        or 0
    )

    awaiting = (
        session.scalar(
            select(func.count())
            .select_from(base)
            .where(
                base.c.requires_approval.is_(True),
                base.c.approval_status == "pending",
                base.c.status == "awaiting_approval",
            )
        )
        or 0
    )

    scheduled = (
        session.scalar(select(func.count()).select_from(base).where(base.c.status == "scheduled")) or 0
    )

    in_progress = (
        session.scalar(select(func.count()).select_from(base).where(base.c.status == "in_progress")) or 0
    )

    overdue = (
        session.scalar(
            select(func.count())
            .select_from(base)
            .where(
                base.c.scheduled_visit_at.isnot(None),
                base.c.scheduled_visit_at < now,
                base.c.status.in_(("scheduled", "assigned")),
            )
        )
        or 0
    )

    recent = (
        session.scalar(
            select(func.count())
            .select_from(base)
            .where(
                base.c.status == "completed",
                base.c.completed_at.isnot(None),
                base.c.completed_at >= week_ago,
            )
        )
        or 0
    )

    return {
        "total": int(total),
        "open_count": int(open_count),
        "by_priority": by_priority,
        "emergency": int(emergency),
        "urgent_and_emergency": int(urgent_emergency),
        "awaiting_approval": int(awaiting),
        "scheduled_visits": int(scheduled),
        "in_progress": int(in_progress),
        "overdue_scheduled": int(overdue),
        "recently_completed": int(recent),
    }
