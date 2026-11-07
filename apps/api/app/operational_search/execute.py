"""Execute a validated search spec with ORM filters. Never accepts SQL text."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.complaints import Complaint
from app.db.models.compliance import StaffTrainingRecord
from app.db.models.housing import HousingApplication
from app.db.models.incidents import IncidentFollowUp
from app.db.models.maintenance import MaintenanceRequest
from app.db.models.managed_documents import ManagedDocument
from app.db.models.scheduling import OperationalTask
from app.db.models.support_ops import CaseAssignment
from app.db.models.support_plans import TenantSupportPlan
from app.operational_search.access import entity_allowed, org_wide
from app.operational_search.catalog import (
    ACTIVE_PLANS,
    OPEN_COMPLAINTS,
    OPEN_FOLLOW_UPS,
    OPEN_MAINTENANCE,
    OPEN_TASKS,
    PENDING_APPLICATIONS,
    RECORD_LINKS,
)
from app.tenancy.context import OrganisationContext


def _link(entity: str, row: Any) -> str:
    template = RECORD_LINKS[entity]
    incident_id = getattr(row, "incident_id", None)
    return template.format(id=row.id, incident_id=incident_id or row.id)


def _assigned_tenants(session: Session, ctx: OrganisationContext) -> list[uuid.UUID]:
    return list(
        session.scalars(
            select(CaseAssignment.tenant_id).where(
                CaseAssignment.organisation_id == ctx.organisation_id,
                CaseAssignment.support_worker_user_id == ctx.user_id,
                CaseAssignment.status == "active",
            )
        )
    )


def _item(entity: str, row: Any, *, title: str, status: str, when: str | None, summary: str) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "record_type": entity,
        "title": title,
        "status": status,
        "relevant_date": when,
        "summary": summary,
        "href": _link(entity, row),
    }


def execute_spec(session: Session, ctx: OrganisationContext, spec: dict[str, Any]) -> dict[str, Any]:
    entity = spec["entity"]
    if not entity_allowed(ctx, entity):
        raise HTTPException(status_code=403, detail="You cannot search this record type")
    wide = org_wide(ctx, entity)
    org_id = ctx.organisation_id
    now = datetime.now(timezone.utc)
    today = date.today()
    preset = spec["preset"]
    limit = spec["limit"]
    offset = spec["offset"]
    newest = spec["sort"] == "newest"

    if entity == "maintenance_request":
        stmt = select(MaintenanceRequest).where(MaintenanceRequest.organisation_id == org_id)
        if not wide:
            stmt = stmt.where(MaintenanceRequest.assigned_user_id == ctx.user_id)
        if preset in {"open", "overdue_open", "assigned_to_me"}:
            stmt = stmt.where(MaintenanceRequest.status.in_(OPEN_MAINTENANCE))
        if preset == "overdue_open":
            stmt = stmt.where(MaintenanceRequest.scheduled_visit_at.is_not(None), MaintenanceRequest.scheduled_visit_at < now)
        if preset == "awaiting_approval":
            stmt = stmt.where(MaintenanceRequest.status == "awaiting_approval")
        order = MaintenanceRequest.reported_at.desc() if newest else MaintenanceRequest.reported_at.asc()
        rows = list(session.scalars(stmt.order_by(order).offset(offset).limit(limit)))
        items = [
            _item(
                entity,
                row,
                title=row.title,
                status=row.status,
                when=row.scheduled_visit_at.isoformat() if row.scheduled_visit_at else row.reported_at.isoformat(),
                summary=row.reference_number,
            )
            for row in rows
        ]
    elif entity == "complaint":
        stmt = select(Complaint).where(Complaint.organisation_id == org_id)
        if not wide:
            stmt = stmt.where(Complaint.assigned_user_id == ctx.user_id)
        if preset in {"open", "overdue_open", "assigned_to_me"}:
            stmt = stmt.where(Complaint.status.in_(OPEN_COMPLAINTS))
        if preset == "overdue_open":
            stmt = stmt.where(Complaint.response_due_at.is_not(None), Complaint.response_due_at < now)
        order = Complaint.submitted_at.desc() if newest else Complaint.submitted_at.asc()
        rows = list(session.scalars(stmt.order_by(order).offset(offset).limit(limit)))
        items = [
            _item(
                entity,
                row,
                title=row.title,
                status=row.status,
                when=(row.response_due_at or row.submitted_at).isoformat(),
                summary=row.reference_number,
            )
            for row in rows
        ]
    elif entity == "housing_application":
        stmt = select(HousingApplication).where(HousingApplication.organisation_id == org_id)
        if not wide:
            tenants = _assigned_tenants(session, ctx)
            stmt = stmt.where(HousingApplication.tenant_id.in_(tenants or [uuid.uuid4()]))
        statuses = PENDING_APPLICATIONS if preset == "awaiting_approval" else ("draft",) + PENDING_APPLICATIONS
        if preset != "expiring_soon":
            stmt = stmt.where(HousingApplication.status.in_(statuses))
        order = HousingApplication.created_at.desc() if newest else HousingApplication.created_at.asc()
        rows = list(session.scalars(stmt.order_by(order).offset(offset).limit(limit)))
        items = [
            _item(entity, row, title=row.reference_number, status=row.status, when=None, summary=row.priority)
            for row in rows
        ]
    elif entity == "incident_follow_up":
        stmt = select(IncidentFollowUp).where(IncidentFollowUp.organisation_id == org_id)
        if not wide:
            stmt = stmt.where(IncidentFollowUp.assigned_user_id == ctx.user_id)
        stmt = stmt.where(IncidentFollowUp.status.in_(OPEN_FOLLOW_UPS))
        if preset == "overdue_open":
            stmt = stmt.where(IncidentFollowUp.due_at.is_not(None), IncidentFollowUp.due_at < now)
        order = IncidentFollowUp.due_at.desc() if newest else IncidentFollowUp.due_at.asc()
        rows = list(session.scalars(stmt.order_by(order).offset(offset).limit(limit)))
        items = [
            _item(
                entity,
                row,
                title="Follow-up",
                status=row.status,
                when=row.due_at.isoformat() if row.due_at else None,
                summary=row.description[:160],
            )
            for row in rows
        ]
    elif entity == "support_plan":
        stmt = select(TenantSupportPlan).where(
            TenantSupportPlan.organisation_id == org_id,
            TenantSupportPlan.status.in_(ACTIVE_PLANS),
        )
        if not wide:
            tenants = _assigned_tenants(session, ctx)
            stmt = stmt.where(TenantSupportPlan.tenant_id.in_(tenants or [uuid.uuid4()]))
        if preset == "overdue_open":
            stmt = stmt.where(
                TenantSupportPlan.planned_review_date.is_not(None),
                TenantSupportPlan.planned_review_date < today,
            )
        order = TenantSupportPlan.planned_review_date.desc() if newest else TenantSupportPlan.planned_review_date.asc()
        rows = list(session.scalars(stmt.order_by(order).offset(offset).limit(limit)))
        items = [
            _item(
                entity,
                row,
                title=row.title,
                status=row.status,
                when=row.planned_review_date.isoformat() if row.planned_review_date else None,
                summary=row.reference_number,
            )
            for row in rows
        ]
    elif entity == "operational_task":
        stmt = select(OperationalTask).where(
            OperationalTask.organisation_id == org_id,
            OperationalTask.status.in_(OPEN_TASKS),
        )
        if not wide or preset == "assigned_to_me":
            stmt = stmt.where(OperationalTask.assigned_user_id == ctx.user_id)
        if preset == "overdue_open":
            stmt = stmt.where(OperationalTask.due_at.is_not(None), OperationalTask.due_at < now)
        order = OperationalTask.due_at.desc() if newest else OperationalTask.due_at.asc()
        rows = list(session.scalars(stmt.order_by(order).offset(offset).limit(limit)))
        items = [
            _item(
                entity,
                row,
                title=row.title,
                status=row.status,
                when=row.due_at.isoformat() if row.due_at else None,
                summary="Assigned task",
            )
            for row in rows
        ]
    elif entity == "managed_document":
        stmt = select(ManagedDocument).where(
            ManagedDocument.organisation_id == org_id,
            ManagedDocument.status == "active",
        )
        if preset == "expiring_soon":
            horizon = today + timedelta(days=30)
            stmt = stmt.where(
                ManagedDocument.expiry_date.is_not(None),
                ManagedDocument.expiry_date <= horizon,
            )
        order = ManagedDocument.expiry_date.desc() if newest else ManagedDocument.expiry_date.asc()
        rows = list(session.scalars(stmt.order_by(order).offset(offset).limit(limit)))
        items = [
            _item(
                entity,
                row,
                title=row.title,
                status=row.expiry_tracking,
                when=row.expiry_date.isoformat() if row.expiry_date else None,
                summary=row.reference_number,
            )
            for row in rows
        ]
    elif entity == "staff_training":
        stmt = select(StaffTrainingRecord).where(StaffTrainingRecord.organisation_id == org_id)
        if not wide:
            stmt = stmt.where(StaffTrainingRecord.staff_user_id == ctx.user_id)
        if preset == "expiring_soon":
            horizon = today + timedelta(days=30)
            stmt = stmt.where(
                StaffTrainingRecord.expiry_date.is_not(None),
                StaffTrainingRecord.expiry_date <= horizon,
            )
        order = StaffTrainingRecord.expiry_date.desc() if newest else StaffTrainingRecord.expiry_date.asc()
        rows = list(session.scalars(stmt.order_by(order).offset(offset).limit(limit)))
        items = [
            _item(
                entity,
                row,
                title=row.title,
                status=row.status,
                when=row.expiry_date.isoformat() if row.expiry_date else None,
                summary=row.category,
            )
            for row in rows
        ]
    else:
        raise HTTPException(status_code=422, detail="Unsupported entity")

    return {
        "items": items,
        "count": len(items),
        "limit": limit,
        "offset": offset,
        "entity": entity,
        "preset": preset,
    }
