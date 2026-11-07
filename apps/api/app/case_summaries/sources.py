"""Collect authorised case facts for one tenant. Does not copy records into new case tables."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import nulls_last, select
from sqlalchemy.orm import Session

from app.db.models.complaints import Complaint
from app.db.models.incidents import Incident
from app.db.models.maintenance import MaintenanceRequest
from app.db.models.managed_documents import ManagedDocument, ManagedDocumentLink
from app.db.models.support_ops import DailyLog
from app.db.models.support_plans import SupportPlanGoal, TenantSupportPlan
from app.db.models.tenant import Tenant
from app.db.models.tenant_timeline import TenantAppointment, TenantFollowUp, TenantMeeting


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _stamp(row) -> str | None:
    return _iso(getattr(row, "updated_at", None))


def collect_case_packet(session: Session, *, organisation_id: uuid.UUID, tenant: Tenant) -> dict[str, Any]:
    org_id = organisation_id
    tenant_id = tenant.id
    sources: list[dict[str, Any]] = [
        {"type": "tenant", "id": str(tenant.id), "updated_at": _stamp(tenant)}
    ]

    notes = list(
        session.scalars(
            select(DailyLog)
            .where(
                DailyLog.organisation_id == org_id,
                DailyLog.tenant_id == tenant_id,
                DailyLog.status != "voided",
            )
            .order_by(DailyLog.log_date.desc())
            .limit(20)
        )
    )
    note_items = []
    for row in notes:
        sources.append({"type": "daily_log", "id": str(row.id), "updated_at": _stamp(row)})
        note_items.append(
            {
                "id": str(row.id),
                "kind": "daily_note",
                "log_date": row.log_date.isoformat(),
                "when": row.log_date.isoformat(),
                "summary": row.summary,
                "notes": (row.notes or "")[:400],
                "status": row.status,
                "follow_up_required": row.follow_up_required,
            }
        )

    meetings = list(
        session.scalars(
            select(TenantMeeting)
            .where(TenantMeeting.organisation_id == org_id, TenantMeeting.tenant_id == tenant_id)
            .order_by(TenantMeeting.scheduled_at.desc())
            .limit(20)
        )
    )
    meeting_items = []
    for row in meetings:
        sources.append({"type": "meeting", "id": str(row.id), "updated_at": _stamp(row)})
        meeting_items.append(
            {
                "id": str(row.id),
                "kind": "meeting",
                "title": row.title,
                "when": _iso(row.scheduled_at),
                "status": row.status,
            }
        )

    appointments = list(
        session.scalars(
            select(TenantAppointment)
            .where(TenantAppointment.organisation_id == org_id, TenantAppointment.tenant_id == tenant_id)
            .order_by(TenantAppointment.starts_at.desc())
            .limit(20)
        )
    )
    appointment_items = []
    for row in appointments:
        sources.append({"type": "appointment", "id": str(row.id), "updated_at": _stamp(row)})
        appointment_items.append(
            {
                "id": str(row.id),
                "kind": "appointment",
                "title": row.title,
                "when": _iso(row.starts_at),
                "status": row.status,
            }
        )

    follow_ups = list(
        session.scalars(
            select(TenantFollowUp)
            .where(TenantFollowUp.organisation_id == org_id, TenantFollowUp.tenant_id == tenant_id)
            .order_by(nulls_last(TenantFollowUp.due_at.desc()))
            .limit(20)
        )
    )
    follow_items = []
    for row in follow_ups:
        sources.append({"type": "follow_up", "id": str(row.id), "updated_at": _stamp(row)})
        follow_items.append(
            {
                "id": str(row.id),
                "action": row.action_description[:300],
                "due_at": _iso(row.due_at),
                "status": row.status,
            }
        )

    plans = list(
        session.scalars(
            select(TenantSupportPlan)
            .where(TenantSupportPlan.organisation_id == org_id, TenantSupportPlan.tenant_id == tenant_id)
            .order_by(TenantSupportPlan.updated_at.desc())
            .limit(10)
        )
    )
    plan_items = []
    plan_ids = []
    for row in plans:
        plan_ids.append(row.id)
        sources.append({"type": "support_plan", "id": str(row.id), "updated_at": _stamp(row), "version": row.version_number})
        plan_items.append(
            {
                "id": str(row.id),
                "kind": "support_plan",
                "title": row.title,
                "status": row.status,
                "objectives": (row.support_objectives or "")[:300] or None,
            }
        )

    goals = []
    if plan_ids:
        goal_rows = list(
            session.scalars(
                select(SupportPlanGoal)
                .where(SupportPlanGoal.organisation_id == org_id, SupportPlanGoal.plan_id.in_(plan_ids))
                .limit(30)
            )
        )
        for row in goal_rows:
            sources.append({"type": "support_plan_goal", "id": str(row.id), "updated_at": _stamp(row)})
            goals.append({"id": str(row.id), "kind": "goal", "title": row.title, "status": row.status})

    incidents = list(
        session.scalars(
            select(Incident)
            .where(Incident.organisation_id == org_id, Incident.tenant_id == tenant_id)
            .order_by(Incident.occurred_at.desc())
            .limit(10)
        )
    )
    incident_items = []
    for row in incidents:
        sources.append({"type": "incident", "id": str(row.id), "updated_at": _stamp(row)})
        incident_items.append(
            {
                "id": str(row.id),
                "kind": "incident",
                "title": row.title,
                "when": _iso(row.occurred_at),
                "status": row.status,
                "severity": row.severity,
            }
        )

    complaints = list(
        session.scalars(
            select(Complaint)
            .where(Complaint.organisation_id == org_id, Complaint.tenant_id == tenant_id)
            .order_by(Complaint.submitted_at.desc())
            .limit(10)
        )
    )
    complaint_items = []
    for row in complaints:
        sources.append({"type": "complaint", "id": str(row.id), "updated_at": _stamp(row)})
        complaint_items.append(
            {
                "id": str(row.id),
                "kind": "complaint",
                "title": row.title,
                "when": _iso(row.submitted_at),
                "status": row.status,
            }
        )

    maintenance = list(
        session.scalars(
            select(MaintenanceRequest)
            .where(MaintenanceRequest.organisation_id == org_id, MaintenanceRequest.tenant_id == tenant_id)
            .order_by(MaintenanceRequest.created_at.desc())
            .limit(10)
        )
    )
    maintenance_items = []
    for row in maintenance:
        sources.append({"type": "maintenance", "id": str(row.id), "updated_at": _stamp(row)})
        maintenance_items.append(
            {
                "id": str(row.id),
                "kind": "maintenance",
                "title": row.title,
                "when": _iso(row.created_at),
                "status": row.status,
                "priority": row.priority,
            }
        )

    links = list(
        session.scalars(
            select(ManagedDocumentLink).where(
                ManagedDocumentLink.organisation_id == org_id,
                ManagedDocumentLink.link_type == "tenant",
                ManagedDocumentLink.link_id == tenant_id,
            )
        )
    )
    documents = []
    for link in links[:10]:
        document = session.get(ManagedDocument, link.document_id)
        if document is None or document.organisation_id != org_id:
            continue
        sources.append({"type": "document", "id": str(document.id), "updated_at": _stamp(document)})
        if document.access_classification == "restricted":
            documents.append({"id": str(document.id), "title": "Restricted document (metadata withheld)", "status": document.status})
        else:
            documents.append({"id": str(document.id), "title": document.title, "status": document.status})

    return {
        "profile": {
            "id": str(tenant.id),
            "preferred_name": tenant.preferred_name,
            "tenancy_reference": tenant.tenancy_reference,
            "status": tenant.status.value if hasattr(tenant.status, "value") else str(tenant.status),
            "needs_goals": (tenant.needs_goals or "")[:500] or None,
        },
        "daily_notes": note_items,
        "meetings": meeting_items,
        "appointments": appointment_items,
        "follow_ups": follow_items,
        "support_plans": plan_items,
        "goals": goals,
        "incidents": incident_items,
        "complaints": complaint_items,
        "maintenance": maintenance_items,
        "documents": documents,
        "sources": sources,
    }
