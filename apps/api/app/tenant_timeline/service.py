"""F2.9 timeline aggregation and CRUD."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.complaints.access import assert_can_view_complaint, can_view_internal_notes as complaint_can_internal
from app.db.models.complaints import Complaint, ComplaintHistoryEvent
from app.db.models.enums import HMoreRole
from app.db.models.housing import HousingApplication, HousingApplicationStatusHistory
from app.db.models.incidents import Incident
from app.db.models.maintenance import MaintenanceHistoryEvent, MaintenanceRequest
from app.db.models.scheduling import OperationalTask, TenantVisit
from app.db.models.support_ops import DailyLog, Handover
from app.db.models.tenant_timeline import (
    TenantAppointment,
    TenantFollowUp,
    TenantFollowUpChange,
    TenantMeeting,
    TenantMeetingParticipant,
    TenantNeedGoal,
)
from app.housing.access import assert_can_view_application
from app.incidents.access import assert_can_view_incident
from app.maintenance.access import assert_can_view_request
from app.ops import access as ops_access
from app.records.pagination import offset_limit
from app.tenant_timeline import access as tl_access
from app.tenant_timeline.schemas import (
    AppointmentCancelRequest,
    AppointmentCreate,
    AppointmentUpdate,
    MeetingCancelRequest,
    MeetingCompleteRequest,
    MeetingCreate,
    MeetingUpdate,
    TenantFollowUpCompleteRequest,
    TenantFollowUpCreate,
    TenantFollowUpUpdate,
    MeetingOut,
    TenantFollowUpOut,
    TenantNeedGoalCreate,
    TenantNeedGoalUpdate,
    TenantNeedGoalOut,
    TimelineItemOut,
)
from app.tenancy.context import OrganisationContext

NOW = lambda: datetime.now(timezone.utc)


def _next_ref(session: Session, org_id: uuid.UUID, model, prefix: str) -> str:
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


MEETING_TRANSITIONS: dict[str, frozenset[str]] = {
    "scheduled": frozenset({"confirmed", "completed", "cancelled"}),
    "confirmed": frozenset({"completed", "cancelled"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}

APPOINTMENT_TRANSITIONS: dict[str, frozenset[str]] = {
    "scheduled": frozenset({"confirmed", "completed", "cancelled", "missed", "rescheduled"}),
    "confirmed": frozenset({"completed", "cancelled", "missed", "rescheduled"}),
    "rescheduled": frozenset({"scheduled", "confirmed", "completed", "cancelled", "missed"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
    "missed": frozenset(),
}

TENANT_FOLLOWUP_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"in_progress", "awaiting_information", "completed", "cancelled"}),
    "in_progress": frozenset({"awaiting_information", "completed", "cancelled", "open"}),
    "awaiting_information": frozenset({"in_progress", "completed", "cancelled", "open"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}

NEED_GOAL_TRANSITIONS: dict[str, frozenset[str]] = {
    "identified": frozenset({"in_progress", "achieved", "paused", "cancelled"}),
    "in_progress": frozenset({"achieved", "paused", "cancelled", "identified"}),
    "achieved": frozenset(),
    "paused": frozenset({"in_progress", "cancelled", "identified"}),
    "cancelled": frozenset(),
}


# --- Timeline ---


def _can_include_support_ops(ctx: OrganisationContext) -> bool:
    return ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}


def _can_include_ops_scheduling(ctx: OrganisationContext) -> bool:
    if ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        return True
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        return True
    return False


def _landlord_allowed_source(kind: str) -> bool:
    return kind in {"complaint", "complaint_event", "maintenance", "maintenance_event"}


def _timeline_skip_for_role(ctx: OrganisationContext, kind: str) -> bool:
    if ctx.role == HMoreRole.LANDLORD and not _landlord_allowed_source(kind):
        return True
    if ctx.role == HMoreRole.TENANT and kind not in {
        "complaint",
        "complaint_event",
        "maintenance",
        "maintenance_event",
        "housing_application",
        "housing_status",
        "meeting",
        "appointment",
        "tenant_follow_up",
    }:
        return True
    return False


def _tenant_can_view_complaint_event_row(
    session: Session, ctx: OrganisationContext, ev: ComplaintHistoryEvent
) -> bool:
    if not ev.is_tenant_visible:
        return False
    c = session.get(Complaint, ev.complaint_id)
    if c is None:
        return False
    try:
        assert_can_view_complaint(session, ctx, c)
    except HTTPException:
        return False
    return True


def _collect_timeline_items(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    *,
    activity_types: set[str] | None,
    date_from: datetime | None,
    date_to: datetime | None,
    assigned_user_id: uuid.UUID | None,
    search: str | None,
) -> list[TimelineItemOut]:
    items: list[TimelineItemOut] = []

    def want(kind: str) -> bool:
        if _timeline_skip_for_role(ctx, kind):
            return False
        if activity_types is None:
            return True
        return kind in activity_types

    # Internal support: daily logs
    if want("daily_log") and _can_include_support_ops(ctx):
        logs = session.scalars(
            select(DailyLog).where(
                DailyLog.organisation_id == ctx.organisation_id,
                DailyLog.tenant_id == tenant_id,
                DailyLog.status != "voided",
            )
        ).all()
        for row in logs:
            oc = row.logged_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            if assigned_user_id and row.author_user_id != assigned_user_id:
                continue
            can_view = True
            try:
                from app.support import service as support_service

                support_service.get_daily_log(session, ctx, row.id)
            except HTTPException:
                can_view = False
            items.append(
                TimelineItemOut(
                    dedupe_key=f"daily_log:{row.id}",
                    activity_type="daily_log",
                    occurred_at=oc,
                    sort_at=oc,
                    title=row.summary,
                    summary=row.activity_category,
                    status=row.status,
                    responsible_user_id=row.author_user_id,
                    reference=None,
                    resource_type="daily_log",
                    resource_id=row.id,
                    detail_api_path=f"/api/v1/daily-logs/{row.id}",
                    can_view=can_view,
                )
            )

    # Handovers
    if want("handover") and _can_include_support_ops(ctx):
        hrows = session.scalars(
            select(Handover).where(
                Handover.organisation_id == ctx.organisation_id,
                Handover.tenant_id == tenant_id,
            )
        ).all()
        for row in hrows:
            oc = row.handover_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            if assigned_user_id and row.created_by_user_id != assigned_user_id:
                continue
            can_view = True
            try:
                from app.support import service as support_service

                support_service.get_handover(session, ctx, row.id)
            except HTTPException:
                can_view = False
            items.append(
                TimelineItemOut(
                    dedupe_key=f"handover:{row.id}",
                    activity_type="handover",
                    occurred_at=oc,
                    sort_at=oc,
                    title=row.summary,
                    summary=row.priority,
                    status=row.status,
                    responsible_user_id=row.created_by_user_id,
                    reference=None,
                    resource_type="handover",
                    resource_id=row.id,
                    detail_api_path=f"/api/v1/handovers/{row.id}",
                    can_view=can_view,
                )
            )

    # Visits (F2.2)
    if want("tenant_visit") and _can_include_ops_scheduling(ctx):
        vrows = session.scalars(
            select(TenantVisit).where(
                TenantVisit.organisation_id == ctx.organisation_id,
                TenantVisit.tenant_id == tenant_id,
            )
        ).all()
        for row in vrows:
            oc = row.scheduled_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            if assigned_user_id and row.assigned_staff_user_id != assigned_user_id:
                continue
            can_view = True
            try:
                from app.ops import service as ops_service

                ops_service.get_visit(session, ctx, row.id)
            except HTTPException:
                can_view = False
            items.append(
                TimelineItemOut(
                    dedupe_key=f"tenant_visit:{row.id}",
                    activity_type="tenant_visit",
                    occurred_at=oc,
                    sort_at=oc or row.created_at,
                    title=row.purpose,
                    summary=row.visit_type,
                    status=row.status,
                    responsible_user_id=row.assigned_staff_user_id,
                    reference=None,
                    resource_type="tenant_visit",
                    resource_id=row.id,
                    detail_api_path=f"/api/v1/ops/visits/{row.id}",
                    can_view=can_view,
                )
            )

    # Operational tasks with tenant_id
    if want("operational_task") and _can_include_ops_scheduling(ctx):
        trows = session.scalars(
            select(OperationalTask).where(
                OperationalTask.organisation_id == ctx.organisation_id,
                OperationalTask.tenant_id == tenant_id,
            )
        ).all()
        for row in trows:
            oc = row.due_at or row.created_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            if assigned_user_id and row.assigned_user_id != assigned_user_id:
                continue
            can_view = True
            try:
                from app.ops import service as ops_service

                ops_service.get_task(session, ctx, row.id)
            except HTTPException:
                can_view = False
            items.append(
                TimelineItemOut(
                    dedupe_key=f"operational_task:{row.id}",
                    activity_type="operational_task",
                    occurred_at=oc,
                    sort_at=oc,
                    title=row.title,
                    summary=row.priority,
                    status=row.status,
                    responsible_user_id=row.assigned_user_id,
                    reference=None,
                    resource_type="operational_task",
                    resource_id=row.id,
                    detail_api_path=f"/api/v1/ops/tasks/{row.id}",
                    can_view=can_view,
                )
            )

    # Housing application + status history
    if want("housing_application"):
        apps = session.scalars(
            select(HousingApplication).where(
                HousingApplication.organisation_id == ctx.organisation_id,
                HousingApplication.tenant_id == tenant_id,
            )
        ).all()
        for app in apps:
            can_app = True
            try:
                assert_can_view_application(session, ctx, app)
            except HTTPException:
                can_app = False
            oc = app.submitted_at or app.created_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            if assigned_user_id and app.reviewer_user_id != assigned_user_id:
                continue
            items.append(
                TimelineItemOut(
                    dedupe_key=f"housing_application:{app.id}",
                    activity_type="housing_application",
                    occurred_at=oc,
                    sort_at=oc,
                    title=f"Housing application {app.reference_number}",
                    summary=app.status,
                    status=app.status,
                    responsible_user_id=app.reviewer_user_id,
                    reference=app.reference_number,
                    resource_type="housing_application",
                    resource_id=app.id,
                    detail_api_path=f"/api/v1/housing/applications/{app.id}",
                    can_view=can_app,
                )
            )
        hist = session.scalars(
            select(HousingApplicationStatusHistory).where(
                HousingApplicationStatusHistory.organisation_id == ctx.organisation_id,
                HousingApplicationStatusHistory.application_id.in_(
                    select(HousingApplication.id).where(
                        HousingApplication.organisation_id == ctx.organisation_id,
                        HousingApplication.tenant_id == tenant_id,
                    )
                ),
            )
        ).all()
        for h in hist:
            app = session.get(HousingApplication, h.application_id)
            if app is None:
                continue
            can_app = True
            try:
                assert_can_view_application(session, ctx, app)
            except HTTPException:
                can_app = False
            oc = h.created_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            items.append(
                TimelineItemOut(
                    dedupe_key=f"housing_status:{h.id}",
                    activity_type="housing_status",
                    occurred_at=oc,
                    sort_at=oc,
                    title=f"Application status: {h.to_status}",
                    summary=h.note,
                    status=h.to_status,
                    responsible_user_id=h.changed_by_user_id,
                    reference=app.reference_number,
                    resource_type="housing_application_status",
                    resource_id=h.id,
                    detail_api_path=f"/api/v1/housing/applications/{app.id}",
                    can_view=can_app,
                )
            )

    # Complaints + history events
    if want("complaint") or want("complaint_event"):
        crows = session.scalars(
            select(Complaint).where(
                Complaint.organisation_id == ctx.organisation_id,
                Complaint.tenant_id == tenant_id,
            )
        ).all()
        for row in crows:
            can_c = True
            try:
                assert_can_view_complaint(session, ctx, row)
            except HTTPException:
                can_c = False
            oc = row.submitted_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            if assigned_user_id and row.assigned_user_id != assigned_user_id:
                continue
            if want("complaint"):
                items.append(
                    TimelineItemOut(
                        dedupe_key=f"complaint:{row.id}",
                        activity_type="complaint",
                        occurred_at=oc,
                        sort_at=oc,
                        title=row.title,
                        summary=row.category_code,
                        status=row.status,
                        responsible_user_id=row.assigned_user_id,
                        reference=row.reference_number,
                        resource_type="complaint",
                        resource_id=row.id,
                        detail_api_path=f"/api/v1/complaints/{row.id}",
                        can_view=can_c,
                    )
                )
        evs = session.scalars(
            select(ComplaintHistoryEvent).where(
                ComplaintHistoryEvent.organisation_id == ctx.organisation_id,
                ComplaintHistoryEvent.complaint_id.in_(
                    select(Complaint.id).where(
                        Complaint.organisation_id == ctx.organisation_id,
                        Complaint.tenant_id == tenant_id,
                    )
                ),
            )
        ).all()
        for ev in evs:
            if ctx.role == HMoreRole.TENANT and not _tenant_can_view_complaint_event_row(session, ctx, ev):
                continue
            if ctx.role != HMoreRole.TENANT and not complaint_can_internal(ctx) and not ev.is_tenant_visible:
                continue
            oc = ev.created_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            c = session.get(Complaint, ev.complaint_id)
            if c is None:
                continue
            can_c = True
            try:
                assert_can_view_complaint(session, ctx, c)
            except HTTPException:
                can_c = False
            if not want("complaint_event"):
                continue
            items.append(
                TimelineItemOut(
                    dedupe_key=f"complaint_event:{ev.id}",
                    activity_type="complaint_event",
                    occurred_at=oc,
                    sort_at=oc,
                    title=ev.summary,
                    summary=ev.event_type,
                    status=None,
                    responsible_user_id=ev.actor_user_id,
                    reference=c.reference_number,
                    resource_type="complaint_history_event",
                    resource_id=ev.id,
                    detail_api_path=f"/api/v1/complaints/{c.id}",
                    can_view=can_c,
                )
            )

    # Maintenance requests + history
    if want("maintenance") or want("maintenance_event"):
        mrows = session.scalars(
            select(MaintenanceRequest).where(
                MaintenanceRequest.organisation_id == ctx.organisation_id,
                MaintenanceRequest.tenant_id == tenant_id,
            )
        ).all()
        for row in mrows:
            can_m = True
            try:
                assert_can_view_request(session, ctx, row)
            except HTTPException:
                can_m = False
            oc = row.reported_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            if assigned_user_id and row.assigned_user_id != assigned_user_id:
                continue
            if want("maintenance"):
                items.append(
                    TimelineItemOut(
                        dedupe_key=f"maintenance:{row.id}",
                        activity_type="maintenance",
                        occurred_at=oc,
                        sort_at=oc,
                        title=row.title,
                        summary=row.category_code,
                        status=row.status,
                        responsible_user_id=row.assigned_user_id,
                        reference=row.reference_number,
                        resource_type="maintenance_request",
                        resource_id=row.id,
                        detail_api_path=f"/api/v1/maintenance/{row.id}",
                        can_view=can_m,
                    )
                )
        mevs = session.scalars(
            select(MaintenanceHistoryEvent).where(
                MaintenanceHistoryEvent.organisation_id == ctx.organisation_id,
                MaintenanceHistoryEvent.request_id.in_(
                    select(MaintenanceRequest.id).where(
                        MaintenanceRequest.organisation_id == ctx.organisation_id,
                        MaintenanceRequest.tenant_id == tenant_id,
                    )
                ),
            )
        ).all()
        for ev in mevs:
            oc = ev.created_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            req = session.get(MaintenanceRequest, ev.request_id)
            if req is None:
                continue
            can_m = True
            try:
                assert_can_view_request(session, ctx, req)
            except HTTPException:
                can_m = False
            if not want("maintenance_event"):
                continue
            items.append(
                TimelineItemOut(
                    dedupe_key=f"maintenance_event:{ev.id}",
                    activity_type="maintenance_event",
                    occurred_at=oc,
                    sort_at=oc,
                    title=ev.summary,
                    summary=ev.event_type,
                    status=None,
                    responsible_user_id=ev.actor_user_id,
                    reference=req.reference_number,
                    resource_type="maintenance_history_event",
                    resource_id=ev.id,
                    detail_api_path=f"/api/v1/maintenance/{req.id}",
                    can_view=can_m,
                )
            )

    # Incidents
    if want("incident"):
        irows = session.scalars(
            select(Incident).where(
                Incident.organisation_id == ctx.organisation_id,
                Incident.tenant_id == tenant_id,
            )
        ).all()
        for row in irows:
            can_i = True
            try:
                assert_can_view_incident(ctx, row)
            except HTTPException:
                can_i = False
            oc = row.occurred_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            if assigned_user_id and row.reviewer_user_id != assigned_user_id:
                continue
            items.append(
                TimelineItemOut(
                    dedupe_key=f"incident:{row.id}",
                    activity_type="incident",
                    occurred_at=oc,
                    sort_at=oc,
                    title=row.title,
                    summary=row.category,
                    status=row.status,
                    responsible_user_id=row.reviewer_user_id,
                    reference=row.reference_number,
                    resource_type="incident",
                    resource_id=row.id,
                    detail_api_path=f"/api/v1/incidents/{row.id}",
                    can_view=can_i,
                )
            )

    # F2.9 entities
    if want("meeting"):
        for row in session.scalars(
            select(TenantMeeting).where(
                TenantMeeting.organisation_id == ctx.organisation_id,
                TenantMeeting.tenant_id == tenant_id,
            )
        ).all():
            oc = row.scheduled_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            if assigned_user_id and row.responsible_user_id != assigned_user_id:
                continue
            items.append(
                TimelineItemOut(
                    dedupe_key=f"tenant_meeting:{row.id}",
                    activity_type="meeting",
                    occurred_at=oc,
                    sort_at=oc,
                    title=row.title,
                    summary=row.purpose,
                    status=row.status,
                    responsible_user_id=row.responsible_user_id,
                    reference=row.reference_number,
                    resource_type="tenant_meeting",
                    resource_id=row.id,
                    detail_api_path=f"/api/v1/tenants/{tenant_id}/timeline/meetings/{row.id}",
                    can_view=True,
                )
            )

    if want("appointment"):
        for row in session.scalars(
            select(TenantAppointment).where(
                TenantAppointment.organisation_id == ctx.organisation_id,
                TenantAppointment.tenant_id == tenant_id,
            )
        ).all():
            oc = row.starts_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            if assigned_user_id and row.assigned_user_id != assigned_user_id:
                continue
            items.append(
                TimelineItemOut(
                    dedupe_key=f"tenant_appointment:{row.id}",
                    activity_type="appointment",
                    occurred_at=oc,
                    sort_at=oc,
                    title=row.title,
                    summary=row.appointment_kind,
                    status=row.status,
                    responsible_user_id=row.assigned_user_id,
                    reference=row.reference_number,
                    resource_type="tenant_appointment",
                    resource_id=row.id,
                    detail_api_path=f"/api/v1/tenants/{tenant_id}/timeline/appointments/{row.id}",
                    can_view=True,
                )
            )

    if want("tenant_follow_up"):
        fu_stmt = select(TenantFollowUp).where(
            TenantFollowUp.organisation_id == ctx.organisation_id,
            TenantFollowUp.tenant_id == tenant_id,
        )
        if ctx.role == HMoreRole.TENANT:
            fu_stmt = fu_stmt.where(TenantFollowUp.show_to_tenant.is_(True))
        for row in session.scalars(fu_stmt).all():
            oc = row.due_at or row.created_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            if assigned_user_id and row.assigned_user_id != assigned_user_id:
                continue
            items.append(
                TimelineItemOut(
                    dedupe_key=f"tenant_follow_up:{row.id}",
                    activity_type="tenant_follow_up",
                    occurred_at=oc,
                    sort_at=oc,
                    title=row.action_description[:255],
                    summary=row.priority,
                    status=row.status,
                    responsible_user_id=row.assigned_user_id,
                    reference=row.reference_number,
                    resource_type="tenant_follow_up",
                    resource_id=row.id,
                    detail_api_path=f"/api/v1/tenants/{tenant_id}/timeline/follow-ups/{row.id}",
                    can_view=True,
                )
            )

    if want("need") or want("goal"):
        for row in session.scalars(
            select(TenantNeedGoal).where(
                TenantNeedGoal.organisation_id == ctx.organisation_id,
                TenantNeedGoal.tenant_id == tenant_id,
            )
        ).all():
            if row.record_kind == "need" and not want("need"):
                continue
            if row.record_kind == "goal" and not want("goal"):
                continue
            oc = row.created_at
            if date_from and oc < date_from:
                continue
            if date_to and oc > date_to:
                continue
            if assigned_user_id and row.responsible_user_id != assigned_user_id:
                continue
            items.append(
                TimelineItemOut(
                    dedupe_key=f"tenant_need_goal:{row.id}",
                    activity_type=row.record_kind,
                    occurred_at=oc,
                    sort_at=oc,
                    title=row.title,
                    summary=row.category_code,
                    status=row.status,
                    responsible_user_id=row.responsible_user_id,
                    reference=None,
                    resource_type="tenant_need_goal",
                    resource_id=row.id,
                    detail_api_path=f"/api/v1/tenants/{tenant_id}/timeline/needs-goals/{row.id}",
                    can_view=True,
                )
            )

    if search:
        q = search.strip().lower()
        items = [
            i
            for i in items
            if q in (i.title or "").lower()
            or (i.summary and q in i.summary.lower())
            or (i.reference and q in i.reference.lower())
        ]

    # Deduplicate by dedupe_key (same event must not appear twice)
    seen: set[str] = set()
    out: list[TimelineItemOut] = []
    for i in items:
        if i.dedupe_key in seen:
            continue
        seen.add(i.dedupe_key)
        out.append(i)
    return out


def get_tenant_timeline(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    sort: str,
    activity_types: list[str] | None,
    date_from: datetime | None,
    date_to: datetime | None,
    assigned_user_id: uuid.UUID | None,
    search: str | None,
) -> dict[str, Any]:
    if sort not in ("newest", "oldest"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sort must be newest or oldest")
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    _audit(
        session,
        ctx,
        action=audit_events.TENANT_TIMELINE_READ,
        resource_type="tenant_timeline",
        resource_id=tenant_id,
        summary="Tenant timeline retrieved",
        metadata={"page": page, "page_size": page_size},
    )
    types_set = set(activity_types) if activity_types else None
    raw = _collect_timeline_items(
        session,
        ctx,
        tenant_id,
        activity_types=types_set,
        date_from=date_from,
        date_to=date_to,
        assigned_user_id=assigned_user_id,
        search=search,
    )
    reverse = sort == "newest"
    raw.sort(key=lambda x: x.sort_at, reverse=reverse)
    total = len(raw)
    offset, limit = offset_limit(page, page_size)
    page_items = raw[offset : offset + limit]
    return {
        "items": [i.model_dump(mode="json") for i in page_items],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


# --- Meetings ---


def _sync_meeting_participants(
    session: Session,
    ctx: OrganisationContext,
    meeting_id: uuid.UUID,
    user_ids: Sequence[uuid.UUID],
) -> None:
    session.execute(delete(TenantMeetingParticipant).where(TenantMeetingParticipant.meeting_id == meeting_id))
    for uid in user_ids:
        ops_access.assert_active_org_member(session, organisation_id=ctx.organisation_id, user_id=uid)
        session.add(
            TenantMeetingParticipant(
                organisation_id=ctx.organisation_id,
                meeting_id=meeting_id,
                user_id=uid,
            )
        )


def meeting_out(session: Session, row: TenantMeeting) -> dict[str, Any]:
    pids = list(
        session.scalars(
            select(TenantMeetingParticipant.user_id).where(
                TenantMeetingParticipant.meeting_id == row.id
            )
        ).all()
    )
    base = MeetingOut.model_validate(row).model_dump(mode="json")
    base["participant_user_ids"] = [str(x) for x in pids]
    return base


def create_meeting(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, data: MeetingCreate) -> dict[str, Any]:
    tl_access.require_meeting_create(ctx)
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    ref = _next_ref(session, ctx.organisation_id, TenantMeeting, "TM")
    row = TenantMeeting(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant_id,
        reference_number=ref,
        title=data.title.strip(),
        purpose=data.purpose.strip(),
        description=data.description,
        scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes,
        timezone=data.timezone,
        location=data.location,
        meeting_method=data.meeting_method,
        responsible_user_id=data.responsible_user_id,
        created_by_user_id=ctx.user_id,
        status=data.status,
        internal_notes=data.internal_notes,
        tenant_visible_summary=data.tenant_visible_summary,
    )
    session.add(row)
    session.flush()
    if data.participants and data.participants.user_ids:
        _sync_meeting_participants(session, ctx, row.id, data.participants.user_ids)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.TENANT_MEETING_CREATE,
        resource_type="tenant_meeting",
        resource_id=row.id,
        summary="Meeting scheduled",
        metadata={"reference": ref},
    )
    session.refresh(row)
    return meeting_out(session, row)


def get_meeting(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, meeting_id: uuid.UUID) -> dict[str, Any]:
    tl_access.require_meeting_read(ctx)
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    row = session.get(TenantMeeting, meeting_id)
    if row is None or row.tenant_id != tenant_id or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    payload = meeting_out(session, row)
    if not tl_access.can_view_meeting_internal_notes(ctx):
        payload["internal_notes"] = None
    return payload


def list_meetings(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, *, page: int, page_size: int
) -> tuple[list[dict[str, Any]], int]:
    tl_access.require_meeting_read(ctx)
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    offset, limit = offset_limit(page, page_size)
    stmt = select(TenantMeeting).where(
        TenantMeeting.organisation_id == ctx.organisation_id,
        TenantMeeting.tenant_id == tenant_id,
    )
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        session.scalars(stmt.order_by(TenantMeeting.scheduled_at.desc()).offset(offset).limit(limit)).all()
    )
    out = []
    show_internal = tl_access.can_view_meeting_internal_notes(ctx)
    for r in rows:
        d = meeting_out(session, r)
        if not show_internal:
            d["internal_notes"] = None
        out.append(d)
    return out, total


def update_meeting(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, meeting_id: uuid.UUID, data: MeetingUpdate
) -> dict[str, Any]:
    tl_access.require_meeting_create(ctx)
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    row = session.get(TenantMeeting, meeting_id)
    if row is None or row.tenant_id != tenant_id or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    payload = data.model_dump(exclude_unset=True)
    participants = payload.pop("participants", None)
    if "internal_notes" in payload and not tl_access.can_view_meeting_internal_notes(ctx):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update internal notes")
    for k, v in payload.items():
        setattr(row, k, v)
    if participants is not None:
        _sync_meeting_participants(session, ctx, row.id, participants.get("user_ids", []))
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.TENANT_MEETING_UPDATE,
        resource_type="tenant_meeting",
        resource_id=row.id,
        summary="Meeting updated",
    )
    session.refresh(row)
    return get_meeting(session, ctx, tenant_id, meeting_id)


def complete_meeting(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, meeting_id: uuid.UUID, data: MeetingCompleteRequest
) -> dict[str, Any]:
    tl_access.require_meeting_create(ctx)
    row = session.get(TenantMeeting, meeting_id)
    if row is None or row.tenant_id != tenant_id or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    target = "completed"
    allowed = MEETING_TRANSITIONS.get(row.status, frozenset())
    if target not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status transition")
    row.status = target
    row.completed_at = data.completed_at or NOW()
    if data.outcome is not None:
        row.outcome = data.outcome
    if data.agreed_actions is not None:
        row.agreed_actions = data.agreed_actions
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.TENANT_MEETING_COMPLETE,
        resource_type="tenant_meeting",
        resource_id=row.id,
        summary="Meeting completed",
    )
    session.refresh(row)
    return get_meeting(session, ctx, tenant_id, meeting_id)


def cancel_meeting(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, meeting_id: uuid.UUID, data: MeetingCancelRequest
) -> dict[str, Any]:
    tl_access.require_meeting_create(ctx)
    row = session.get(TenantMeeting, meeting_id)
    if row is None or row.tenant_id != tenant_id or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    target = "cancelled"
    if target not in MEETING_TRANSITIONS.get(row.status, frozenset()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status transition")
    row.status = target
    row.cancel_reason = data.cancel_reason
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.TENANT_MEETING_CANCEL,
        resource_type="tenant_meeting",
        resource_id=row.id,
        summary="Meeting cancelled",
    )
    session.refresh(row)
    return get_meeting(session, ctx, tenant_id, meeting_id)


# --- Appointments ---


def appointment_out(row: TenantAppointment) -> dict[str, Any]:
    return AppointmentOut.model_validate(row).model_dump(mode="json")


def create_appointment(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, data: AppointmentCreate
) -> dict[str, Any]:
    tl_access.require_appointment_manage(ctx)
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    if data.linked_tenant_visit_id:
        visit = session.get(TenantVisit, data.linked_tenant_visit_id)
        if visit is None or visit.organisation_id != ctx.organisation_id or visit.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid linked visit")
    ref = _next_ref(session, ctx.organisation_id, TenantAppointment, "TAP")
    row = TenantAppointment(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant_id,
        reference_number=ref,
        appointment_kind=data.appointment_kind,
        title=data.title.strip(),
        description=data.description,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        timezone=data.timezone,
        location=data.location,
        method=data.method,
        assigned_user_id=data.assigned_user_id,
        created_by_user_id=ctx.user_id,
        status=data.status,
        linked_tenant_visit_id=data.linked_tenant_visit_id,
    )
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.TENANT_APPOINTMENT_CREATE,
        resource_type="tenant_appointment",
        resource_id=row.id,
        summary="Appointment created",
        metadata={"reference": ref},
    )
    session.refresh(row)
    return appointment_out(row)


def get_appointment(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, aid: uuid.UUID) -> dict[str, Any]:
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    row = session.get(TenantAppointment, aid)
    if row is None or row.tenant_id != tenant_id or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment_out(row)


def list_appointments(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, *, page: int, page_size: int
) -> tuple[list[dict[str, Any]], int]:
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    if ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER, HMoreRole.TENANT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    offset, limit = offset_limit(page, page_size)
    stmt = select(TenantAppointment).where(
        TenantAppointment.organisation_id == ctx.organisation_id,
        TenantAppointment.tenant_id == tenant_id,
    )
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        session.scalars(stmt.order_by(TenantAppointment.starts_at.desc()).offset(offset).limit(limit)).all()
    )
    return [appointment_out(r) for r in rows], total


def update_appointment(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, aid: uuid.UUID, data: AppointmentUpdate
) -> dict[str, Any]:
    tl_access.require_appointment_manage(ctx)
    row = session.get(TenantAppointment, aid)
    if row is None or row.tenant_id != tenant_id or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    prev_status = row.status
    payload = data.model_dump(exclude_unset=True)
    if "status" in payload:
        target = payload["status"]
        if target != row.status:
            allowed = APPOINTMENT_TRANSITIONS.get(row.status, frozenset())
            if target not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot transition appointment from {row.status} to {target}",
                )
    if payload.get("linked_tenant_visit_id"):
        vid = payload["linked_tenant_visit_id"]
        visit = session.get(TenantVisit, vid)
        if visit is None or visit.organisation_id != ctx.organisation_id or visit.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid linked visit")
    for k, v in payload.items():
        setattr(row, k, v)
    session.flush()
    ap_action = audit_events.TENANT_APPOINTMENT_UPDATE
    if row.status == "cancelled" and prev_status != "cancelled":
        ap_action = audit_events.TENANT_APPOINTMENT_CANCEL
    _audit(
        session,
        ctx,
        action=ap_action,
        resource_type="tenant_appointment",
        resource_id=row.id,
        summary="Appointment updated",
    )
    session.refresh(row)
    return appointment_out(row)


def cancel_appointment(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, aid: uuid.UUID, data: AppointmentCancelRequest
) -> dict[str, Any]:
    return update_appointment(
        session,
        ctx,
        tenant_id,
        aid,
        AppointmentUpdate(status="cancelled", cancel_reason=data.cancel_reason),
    )


# --- Tenant follow-ups ---


def _follow_up_change(
    session: Session,
    ctx: OrganisationContext,
    follow_up_id: uuid.UUID,
    field_name: str,
    old: str | None,
    new: str | None,
) -> None:
    session.add(
        TenantFollowUpChange(
            organisation_id=ctx.organisation_id,
            follow_up_id=follow_up_id,
            changed_by_user_id=ctx.user_id,
            field_name=field_name,
            old_value=old,
            new_value=new,
        )
    )


def follow_up_out(row: TenantFollowUp) -> dict[str, Any]:
    d = TenantFollowUpOut.model_validate(row).model_dump(mode="json")
    now = NOW()
    d["overdue"] = bool(
        row.due_at
        and row.due_at < now
        and row.status not in ("completed", "cancelled")
    )
    return d


def create_follow_up(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, data: TenantFollowUpCreate
) -> dict[str, Any]:
    tl_access.require_followup_manage(ctx)
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    ops_access.assert_active_org_member(
        session, organisation_id=ctx.organisation_id, user_id=data.assigned_user_id
    )
    ref = _next_ref(session, ctx.organisation_id, TenantFollowUp, "TFU")
    row = TenantFollowUp(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant_id,
        reference_number=ref,
        action_description=data.action_description.strip(),
        instructions=data.instructions,
        assigned_user_id=data.assigned_user_id,
        created_by_user_id=ctx.user_id,
        due_at=data.due_at,
        priority=data.priority,
        status="open",
        internal_notes=data.internal_notes,
        related_type=data.related_type,
        related_id=data.related_id,
        show_to_tenant=data.show_to_tenant,
    )
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.TENANT_FOLLOW_UP_CREATE,
        resource_type="tenant_follow_up",
        resource_id=row.id,
        summary="Follow-up created",
        metadata={"reference": ref},
    )
    session.refresh(row)
    return follow_up_out(row)


def get_follow_up(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, fid: uuid.UUID) -> dict[str, Any]:
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    tl_access.require_followup_list(ctx)
    row = session.get(TenantFollowUp, fid)
    if row is None or row.tenant_id != tenant_id or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    if ctx.role == HMoreRole.TENANT:
        if not row.show_to_tenant:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return follow_up_out(row)
    if ctx.role == HMoreRole.SUPPORT_WORKER and row.assigned_user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return follow_up_out(row)


def list_follow_ups(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    status_filter: str | None,
    overdue_only: bool,
    upcoming_only: bool,
) -> tuple[list[dict[str, Any]], int]:
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    tl_access.require_followup_list(ctx)
    offset, limit = offset_limit(page, page_size)
    stmt = select(TenantFollowUp).where(
        TenantFollowUp.organisation_id == ctx.organisation_id,
        TenantFollowUp.tenant_id == tenant_id,
    )
    if ctx.role == HMoreRole.TENANT:
        stmt = stmt.where(TenantFollowUp.show_to_tenant.is_(True))
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(TenantFollowUp.assigned_user_id == ctx.user_id)
    if status_filter:
        stmt = stmt.where(TenantFollowUp.status == status_filter)
    now = NOW()
    if overdue_only:
        stmt = stmt.where(
            TenantFollowUp.due_at.is_not(None),
            TenantFollowUp.due_at < now,
            TenantFollowUp.status.not_in(("completed", "cancelled")),
        )
    if upcoming_only:
        stmt = stmt.where(
            TenantFollowUp.due_at.is_not(None),
            TenantFollowUp.due_at >= now,
            TenantFollowUp.status.not_in(("completed", "cancelled")),
        )
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(TenantFollowUp.due_at.asc().nullslast()).offset(offset).limit(limit)
        ).all()
    )
    return [follow_up_out(r) for r in rows], total


def update_follow_up(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, fid: uuid.UUID, data: TenantFollowUpUpdate
) -> dict[str, Any]:
    tl_access.require_followup_manage(ctx)
    row = session.get(TenantFollowUp, fid)
    if row is None or row.tenant_id != tenant_id or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    tl_access.assert_followup_updater(ctx, row.assigned_user_id)
    payload = data.model_dump(exclude_unset=True)
    new_status = payload.get("status")
    if new_status and new_status != row.status:
        if new_status not in TENANT_FOLLOWUP_TRANSITIONS.get(row.status, frozenset()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status transition")
    if "assigned_user_id" in payload and payload["assigned_user_id"] != row.assigned_user_id:
        tl_access.assert_followup_reassign_allowed(ctx)
        new_uid = payload["assigned_user_id"]
        ops_access.assert_active_org_member(session, organisation_id=ctx.organisation_id, user_id=new_uid)
        _follow_up_change(
            session,
            ctx,
            row.id,
            "assigned_user_id",
            str(row.assigned_user_id),
            str(new_uid),
        )
    if "due_at" in payload and payload["due_at"] != row.due_at:
        _follow_up_change(
            session,
            ctx,
            row.id,
            "due_at",
            str(row.due_at) if row.due_at else None,
            str(payload["due_at"]) if payload["due_at"] else None,
        )
    for k, v in payload.items():
        if k == "completed_at":
            continue
        setattr(row, k, v)
    if new_status == "completed":
        row.completed_at = payload.get("completed_at") or NOW()
    session.flush()
    fu_action = audit_events.TENANT_FOLLOW_UP_UPDATE
    if new_status == "completed":
        fu_action = audit_events.TENANT_FOLLOW_UP_COMPLETE
    elif new_status == "cancelled":
        fu_action = audit_events.TENANT_FOLLOW_UP_CANCEL
    _audit(
        session,
        ctx,
        action=fu_action,
        resource_type="tenant_follow_up",
        resource_id=row.id,
        summary="Follow-up updated",
    )
    session.refresh(row)
    return follow_up_out(row)


def complete_follow_up(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, fid: uuid.UUID, data: TenantFollowUpCompleteRequest
) -> dict[str, Any]:
    return update_follow_up(
        session,
        ctx,
        tenant_id,
        fid,
        TenantFollowUpUpdate(
            status="completed",
            completion_notes=data.completion_notes,
            completed_at=data.completed_at,
        ),
    )


# Needs / goals


def need_goal_out(row: TenantNeedGoal, *, include_internal: bool) -> dict[str, Any]:
    d = TenantNeedGoalOut.model_validate(row).model_dump(mode="json")
    if not include_internal:
        d["internal_notes"] = None
    return d


def create_need_goal(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, data: TenantNeedGoalCreate
) -> dict[str, Any]:
    tl_access.require_needs_manage(ctx)
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    row = TenantNeedGoal(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant_id,
        record_kind=data.record_kind,
        category_code=data.category_code,
        title=data.title.strip(),
        description=data.description.strip(),
        responsible_user_id=data.responsible_user_id,
        status=data.status,
        review_at=data.review_at,
        review_notes=data.review_notes,
        internal_notes=data.internal_notes,
        created_by_user_id=ctx.user_id,
    )
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.TENANT_NEED_GOAL_CREATE,
        resource_type="tenant_need_goal",
        resource_id=row.id,
        summary=f"{data.record_kind} recorded",
    )
    session.refresh(row)
    return need_goal_out(row, include_internal=True)


def list_need_goals(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, *, page: int, page_size: int
) -> tuple[list[dict[str, Any]], int]:
    tl_access.require_needs_read(ctx)
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    offset, limit = offset_limit(page, page_size)
    stmt = select(TenantNeedGoal).where(
        TenantNeedGoal.organisation_id == ctx.organisation_id,
        TenantNeedGoal.tenant_id == tenant_id,
    )
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        session.scalars(stmt.order_by(TenantNeedGoal.created_at.desc()).offset(offset).limit(limit)).all()
    )
    internal = ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}
    return [need_goal_out(r, include_internal=internal) for r in rows], total


def get_need_goal(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, nid: uuid.UUID) -> dict[str, Any]:
    tl_access.require_needs_read(ctx)
    tl_access.assert_timeline_tenant_scope(session, ctx, tenant_id)
    row = session.get(TenantNeedGoal, nid)
    if row is None or row.tenant_id != tenant_id or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    internal = ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}
    return need_goal_out(row, include_internal=internal)


def update_need_goal(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, nid: uuid.UUID, data: TenantNeedGoalUpdate
) -> dict[str, Any]:
    tl_access.require_needs_manage(ctx)
    row = session.get(TenantNeedGoal, nid)
    if row is None or row.tenant_id != tenant_id or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    payload = data.model_dump(exclude_unset=True)
    if "status" in payload:
        ns = payload["status"]
        if ns != row.status and ns not in NEED_GOAL_TRANSITIONS.get(row.status, frozenset()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status transition")
    for k, v in payload.items():
        setattr(row, k, v)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.TENANT_NEED_GOAL_UPDATE,
        resource_type="tenant_need_goal",
        resource_id=row.id,
        summary="Need/goal updated",
    )
    session.refresh(row)
    return need_goal_out(row, include_internal=True)
