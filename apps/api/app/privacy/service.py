"""F7.2 privacy management service — database-backed, no fabricated legal approval."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.privacy import (
    PrivacyDataSubjectRequest,
    PrivacyDeletionLog,
    PrivacyDpiaRegisterEntry,
    PrivacyInventoryItem,
    PrivacyRetentionPolicy,
    PrivacyRiskRegisterEntry,
    PrivacyTestRetentionRecord,
)
from app.privacy import access as privacy_access
from app.privacy.catalog import DEFAULT_DPIA_ACTIVITIES, INVENTORY_CATALOG
from app.privacy.constants import (
    DPIA_STATUSES,
    DSR_CATEGORIES,
    DSR_STATUSES,
    RETENTION_POLICY_STATUSES,
    RISK_SEVERITIES,
    RISK_STATUSES,
)
from app.room_occupancy import gate as occupancy_gate
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_dpia_status(status: str) -> None:
    if status not in DPIA_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid DPIA status")


def _validate_dsr(category: str, status: str) -> None:
    if category not in DSR_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid data subject request category")
    if status not in DSR_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid data subject request status")


def _inventory_dict(row: PrivacyInventoryItem) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "category_code": row.category_code,
        "title": row.title,
        "description": row.description,
        "purpose": row.purpose,
        "data_sources": row.data_sources,
        "roles_with_access": row.roles_with_access,
        "storage_locations": row.storage_locations,
        "processing_services": row.processing_services,
        "external_recipients": row.external_recipients,
        "retention_period_days": row.retention_period_days,
        "retention_notes": row.retention_notes,
        "deletion_method": row.deletion_method,
        "security_controls": row.security_controls,
        "lawful_basis_notes": row.lawful_basis_notes,
        "lawful_basis_confirmed": row.lawful_basis_confirmed,
        "last_reviewed_at": row.last_reviewed_at.isoformat() if row.last_reviewed_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _dpia_dict(row: PrivacyDpiaRegisterEntry) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "activity_key": row.activity_key,
        "title": row.title,
        "purpose": row.purpose,
        "personal_data_summary": row.personal_data_summary,
        "necessity_notes": row.necessity_notes,
        "risk_summary": row.risk_summary,
        "existing_safeguards": row.existing_safeguards,
        "additional_safeguards_required": row.additional_safeguards_required,
        "residual_risk_notes": row.residual_risk_notes,
        "status": row.status,
        "responsible_reviewer": row.responsible_reviewer,
        "review_due_at": row.review_due_at.isoformat() if row.review_due_at else None,
        "approval_reference": row.approval_reference,
        "approved_by_name": row.approved_by_name,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
        "notes": row.notes,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _dsr_dict(row: PrivacyDataSubjectRequest) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "request_category": row.request_category,
        "status": row.status,
        "subject_label": row.subject_label,
        "subject_user_id": str(row.subject_user_id) if row.subject_user_id else None,
        "request_summary": row.request_summary,
        "assigned_user_id": str(row.assigned_user_id) if row.assigned_user_id else None,
        "registered_at": row.registered_at.isoformat(),
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "completion_evidence": row.completion_evidence,
        "response_history": row.response_history or [],
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    privacy_access.require_privacy_read(ctx)
    org = ctx.organisation_id
    inv_count = session.scalar(
        select(func.count()).select_from(PrivacyInventoryItem).where(PrivacyInventoryItem.organisation_id == org)
    )
    dpia_rows = session.scalars(
        select(PrivacyDpiaRegisterEntry).where(PrivacyDpiaRegisterEntry.organisation_id == org)
    ).all()
    open_dsrs = session.scalar(
        select(func.count())
        .select_from(PrivacyDataSubjectRequest)
        .where(
            PrivacyDataSubjectRequest.organisation_id == org,
            PrivacyDataSubjectRequest.status.not_in(("completed", "cancelled", "rejected")),
        )
    )
    open_risks = session.scalar(
        select(func.count())
        .select_from(PrivacyRiskRegisterEntry)
        .where(
            PrivacyRiskRegisterEntry.organisation_id == org,
            PrivacyRiskRegisterEntry.status.in_(("open", "mitigating")),
        )
    )
    retention_active = session.scalar(
        select(func.count())
        .select_from(PrivacyRetentionPolicy)
        .where(PrivacyRetentionPolicy.organisation_id == org, PrivacyRetentionPolicy.status == "active")
    )
    dpia_by_status: dict[str, int] = {}
    for row in dpia_rows:
        dpia_by_status[row.status] = dpia_by_status.get(row.status, 0) + 1

    gate = occupancy_gate.get_or_create_gate(session, ctx)
    gate_view = occupancy_gate.gate_to_dict(gate)

    return {
        "inventory_item_count": inv_count or 0,
        "dpia_entry_count": len(dpia_rows),
        "dpia_by_status": dpia_by_status,
        "open_data_subject_requests": open_dsrs or 0,
        "open_privacy_risks": open_risks or 0,
        "active_retention_policies": retention_active or 0,
        "room_occupancy_privacy_gate": gate_view,
        "occupancy_live_status": (
            "BLOCKED"
            if not gate_view.get("gate_complete")
            else ("ENABLED" if gate_view.get("live_counting_enabled") else "GATE_COMPLETE_LIVE_OFF")
        ),
        "legal_approval_notice": (
            "Technical records only. DPIA 'approved' status requires documented authorised approval fields. "
            "This dashboard does not constitute legal certification."
        ),
        "outstanding_compliance_actions": _outstanding_actions(dpia_rows, inv_count or 0, gate_view),
    }


def _outstanding_actions(
    dpia_rows: list[PrivacyDpiaRegisterEntry], inv_count: int, gate_view: dict[str, Any]
) -> list[str]:
    actions: list[str] = []
    if inv_count == 0:
        actions.append("Bootstrap or complete the organisation data inventory.")
    unconfirmed = [r for r in dpia_rows if r.status != "approved"]
    if unconfirmed:
        actions.append(f"{len(unconfirmed)} DPIA entries are not in approved status.")
    if not gate_view.get("gate_complete"):
        actions.append(
            "Room occupancy live counting remains disabled — complete occupancy privacy gate (see Room Occupancy module)."
        )
    actions.append("Confirm lawful bases and retention periods with the organisation data controller / DPO.")
    return actions


def bootstrap_catalog(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    privacy_access.require_privacy_manage(ctx)
    existing = session.scalar(
        select(func.count()).select_from(PrivacyInventoryItem).where(PrivacyInventoryItem.organisation_id == ctx.organisation_id)
    )
    if (existing or 0) > 0:
        return {"created_inventory": 0, "created_dpia": 0, "message": "Inventory already present"}

    inv_created = 0
    for item in INVENTORY_CATALOG:
        row = PrivacyInventoryItem(
            organisation_id=ctx.organisation_id,
            category_code=item["category_code"],
            title=item["title"],
            description=item.get("description"),
            purpose=item.get("purpose"),
            data_sources=item.get("data_sources"),
            roles_with_access=item.get("roles_with_access"),
            storage_locations=item.get("storage_locations"),
            processing_services=item.get("processing_services"),
            external_recipients=item.get("external_recipients"),
            retention_period_days=item.get("retention_period_days"),
            retention_notes=item.get("retention_notes") or "Requires organisation legal confirmation — not set in software.",
            deletion_method=item.get("deletion_method"),
            security_controls=item.get("security_controls"),
            lawful_basis_notes=item.get("lawful_basis_notes"),
            lawful_basis_confirmed=False,
        )
        session.add(row)
        inv_created += 1

    dpia_created = 0
    for item in DEFAULT_DPIA_ACTIVITIES:
        row = PrivacyDpiaRegisterEntry(
            organisation_id=ctx.organisation_id,
            activity_key=item["activity_key"],
            title=item["title"],
            purpose=item.get("purpose"),
            personal_data_summary=item.get("personal_data_summary"),
            necessity_notes=item.get("necessity_notes"),
            risk_summary=item.get("risk_summary"),
            existing_safeguards=item.get("existing_safeguards"),
            status=item.get("status", "not_started"),
        )
        session.add(row)
        dpia_created += 1

    record_event(
        session,
        action=audit_events.PRIVACY_CATALOG_BOOTSTRAP,
        resource_type="privacy_register",
        resource_id=ctx.organisation_id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Bootstrapped privacy inventory and DPIA register templates",
        metadata={"inventory_created": inv_created, "dpia_created": dpia_created},
        raise_on_error=False,
    )
    session.flush()
    return {"created_inventory": inv_created, "created_dpia": dpia_created}


def list_inventory(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    privacy_access.require_privacy_read(ctx)
    rows = session.scalars(
        select(PrivacyInventoryItem)
        .where(PrivacyInventoryItem.organisation_id == ctx.organisation_id)
        .order_by(PrivacyInventoryItem.category_code)
    ).all()
    return [_inventory_dict(r) for r in rows]


def update_inventory(
    session: Session, ctx: OrganisationContext, item_id: uuid.UUID, body: dict[str, Any]
) -> dict[str, Any]:
    privacy_access.require_privacy_manage(ctx)
    row = session.get(PrivacyInventoryItem, item_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    for field in (
        "description",
        "purpose",
        "retention_period_days",
        "retention_notes",
        "lawful_basis_notes",
        "deletion_method",
        "security_controls",
    ):
        if field in body:
            setattr(row, field, body[field])
    if "lawful_basis_confirmed" in body:
        row.lawful_basis_confirmed = bool(body["lawful_basis_confirmed"])
    row.last_reviewed_at = _now()
    session.flush()
    record_event(
        session,
        action=audit_events.PRIVACY_INVENTORY_UPDATE,
        resource_type="privacy_inventory_item",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Updated privacy inventory item",
        metadata={"category_code": row.category_code},
        raise_on_error=False,
    )
    return _inventory_dict(row)


def list_dpia(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    privacy_access.require_privacy_read(ctx)
    rows = session.scalars(
        select(PrivacyDpiaRegisterEntry)
        .where(PrivacyDpiaRegisterEntry.organisation_id == ctx.organisation_id)
        .order_by(PrivacyDpiaRegisterEntry.activity_key)
    ).all()
    return [_dpia_dict(r) for r in rows]


def update_dpia(session: Session, ctx: OrganisationContext, entry_id: uuid.UUID, body: dict[str, Any]) -> dict[str, Any]:
    privacy_access.require_privacy_manage(ctx)
    row = session.get(PrivacyDpiaRegisterEntry, entry_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="DPIA entry not found")

    if "status" in body:
        status = str(body["status"])
        _validate_dpia_status(status)
        if status == "approved":
            ref = body.get("approval_reference") or row.approval_reference
            approver = body.get("approved_by_name") or row.approved_by_name
            if not ref or not approver:
                raise HTTPException(
                    status_code=400,
                    detail="Approved status requires approval_reference and approved_by_name",
                )
            row.approval_reference = ref
            row.approved_by_name = approver
            row.approved_at = _now()
        row.status = status

    for field in (
        "purpose",
        "personal_data_summary",
        "necessity_notes",
        "risk_summary",
        "existing_safeguards",
        "additional_safeguards_required",
        "residual_risk_notes",
        "responsible_reviewer",
        "notes",
        "approval_reference",
        "approved_by_name",
    ):
        if field in body:
            setattr(row, field, body[field])
    if "review_due_at" in body and body["review_due_at"]:
        row.review_due_at = date.fromisoformat(str(body["review_due_at"])[:10])

    session.flush()
    record_event(
        session,
        action=audit_events.PRIVACY_DPIA_UPDATE,
        resource_type="privacy_dpia",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Updated DPIA register entry",
        metadata={"activity_key": row.activity_key, "status": row.status},
        raise_on_error=False,
    )
    return _dpia_dict(row)


def list_retention_policies(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    privacy_access.require_privacy_read(ctx)
    rows = session.scalars(
        select(PrivacyRetentionPolicy)
        .where(PrivacyRetentionPolicy.organisation_id == ctx.organisation_id)
        .order_by(PrivacyRetentionPolicy.category_code)
    ).all()
    return [
        {
            "id": str(r.id),
            "category_code": r.category_code,
            "category_label": r.category_label,
            "retention_period_days": r.retention_period_days,
            "retention_notes": r.retention_notes,
            "status": r.status,
            "review_due_at": r.review_due_at.isoformat() if r.review_due_at else None,
            "legal_hold_exception_notes": r.legal_hold_exception_notes,
            "authorised_by_name": r.authorised_by_name,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        }
        for r in rows
    ]


def upsert_retention_policy(session: Session, ctx: OrganisationContext, body: dict[str, Any]) -> dict[str, Any]:
    privacy_access.require_privacy_manage(ctx)
    code = body.get("category_code")
    if not code:
        raise HTTPException(status_code=400, detail="category_code required")
    status = body.get("status", "draft")
    if status not in RETENTION_POLICY_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid retention policy status")
    if status == "active" and not body.get("authorised_by_name"):
        raise HTTPException(status_code=400, detail="Active retention policy requires authorised_by_name")

    row = session.scalar(
        select(PrivacyRetentionPolicy).where(
            PrivacyRetentionPolicy.organisation_id == ctx.organisation_id,
            PrivacyRetentionPolicy.category_code == code,
        )
    )
    if row is None:
        row = PrivacyRetentionPolicy(
            organisation_id=ctx.organisation_id,
            category_code=code,
            category_label=body.get("category_label") or code,
        )
        session.add(row)
    row.category_label = body.get("category_label") or row.category_label
    if "retention_period_days" in body:
        row.retention_period_days = body["retention_period_days"]
    if "retention_notes" in body:
        row.retention_notes = body["retention_notes"]
    row.status = status
    if body.get("review_due_at"):
        row.review_due_at = date.fromisoformat(str(body["review_due_at"])[:10])
    if body.get("legal_hold_exception_notes"):
        row.legal_hold_exception_notes = body["legal_hold_exception_notes"]
    if body.get("authorised_by_name"):
        row.authorised_by_name = body["authorised_by_name"]
    if status == "active":
        row.approved_at = _now()
    session.flush()
    record_event(
        session,
        action=audit_events.PRIVACY_RETENTION_UPDATE,
        resource_type="privacy_retention_policy",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Updated retention policy",
        metadata={"category_code": code, "status": status},
        raise_on_error=False,
    )
    session.refresh(row)
    return {
        "id": str(row.id),
        "category_code": row.category_code,
        "category_label": row.category_label,
        "retention_period_days": row.retention_period_days,
        "retention_notes": row.retention_notes,
        "status": row.status,
        "review_due_at": row.review_due_at.isoformat() if row.review_due_at else None,
        "legal_hold_exception_notes": row.legal_hold_exception_notes,
        "authorised_by_name": row.authorised_by_name,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
    }


def list_dsr(session: Session, ctx: OrganisationContext, status: str | None = None) -> list[dict[str, Any]]:
    privacy_access.require_privacy_read(ctx)
    stmt = select(PrivacyDataSubjectRequest).where(PrivacyDataSubjectRequest.organisation_id == ctx.organisation_id)
    if status:
        stmt = stmt.where(PrivacyDataSubjectRequest.status == status)
    rows = session.scalars(stmt.order_by(PrivacyDataSubjectRequest.registered_at.desc())).all()
    return [_dsr_dict(r) for r in rows]


def create_dsr(session: Session, ctx: OrganisationContext, body: dict[str, Any]) -> dict[str, Any]:
    privacy_access.require_privacy_manage(ctx)
    category = body.get("request_category", "access")
    _validate_dsr(category, "registered")
    if not body.get("subject_label"):
        raise HTTPException(status_code=400, detail="subject_label required")
    row = PrivacyDataSubjectRequest(
        organisation_id=ctx.organisation_id,
        request_category=category,
        status="registered",
        subject_label=body["subject_label"],
        subject_user_id=body.get("subject_user_id"),
        request_summary=body.get("request_summary"),
        assigned_user_id=body.get("assigned_user_id"),
        registered_at=_now(),
        due_at=date.fromisoformat(str(body["due_at"])[:10]) if body.get("due_at") else None,
        response_history=[
            {
                "at": _now().isoformat(),
                "by_user_id": str(ctx.user_id),
                "note": "Request registered",
            }
        ],
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.PRIVACY_DSR_CREATE,
        resource_type="privacy_dsr",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Registered data subject request",
        metadata={"category": category},
        raise_on_error=False,
    )
    return _dsr_dict(row)


def update_dsr(session: Session, ctx: OrganisationContext, dsr_id: uuid.UUID, body: dict[str, Any]) -> dict[str, Any]:
    privacy_access.require_privacy_manage(ctx)
    row = session.get(PrivacyDataSubjectRequest, dsr_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Data subject request not found")

    if "status" in body:
        status = str(body["status"])
        _validate_dsr(row.request_category, status)
        if status == "completed" and row.request_category == "erasure":
            if not body.get("completion_evidence") and not row.completion_evidence:
                raise HTTPException(
                    status_code=400,
                    detail="Erasure requests require completion_evidence and authorised review before completion",
                )
        row.status = status
        if status == "completed":
            row.completed_at = _now()
    if "assigned_user_id" in body:
        row.assigned_user_id = body["assigned_user_id"]
    if "completion_evidence" in body:
        row.completion_evidence = body["completion_evidence"]
    note = body.get("response_note")
    if note:
        history = list(row.response_history or [])
        history.append({"at": _now().isoformat(), "by_user_id": str(ctx.user.id), "note": note})
        row.response_history = history

    session.flush()
    record_event(
        session,
        action=audit_events.PRIVACY_DSR_UPDATE,
        resource_type="privacy_dsr",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Updated data subject request",
        metadata={"status": row.status},
        raise_on_error=False,
    )
    return _dsr_dict(row)


def list_risks(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    privacy_access.require_privacy_read(ctx)
    rows = session.scalars(
        select(PrivacyRiskRegisterEntry)
        .where(PrivacyRiskRegisterEntry.organisation_id == ctx.organisation_id)
        .order_by(PrivacyRiskRegisterEntry.created_at.desc())
    ).all()
    return [
        {
            "id": str(r.id),
            "title": r.title,
            "description": r.description,
            "severity": r.severity,
            "status": r.status,
            "mitigation_plan": r.mitigation_plan,
            "owner_label": r.owner_label,
            "target_review_at": r.target_review_at.isoformat() if r.target_review_at else None,
        }
        for r in rows
    ]


def create_risk(session: Session, ctx: OrganisationContext, body: dict[str, Any]) -> dict[str, Any]:
    privacy_access.require_privacy_manage(ctx)
    severity = body.get("severity", "medium")
    status = body.get("status", "open")
    if severity not in RISK_SEVERITIES or status not in RISK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid risk severity or status")
    row = PrivacyRiskRegisterEntry(
        organisation_id=ctx.organisation_id,
        title=body["title"],
        description=body.get("description"),
        severity=severity,
        status=status,
        mitigation_plan=body.get("mitigation_plan"),
        owner_label=body.get("owner_label"),
    )
    if body.get("target_review_at"):
        row.target_review_at = date.fromisoformat(str(body["target_review_at"])[:10])
    session.add(row)
    session.flush()
    return {
        "id": str(row.id),
        "title": row.title,
        "description": row.description,
        "severity": row.severity,
        "status": row.status,
        "mitigation_plan": row.mitigation_plan,
        "owner_label": row.owner_label,
        "target_review_at": row.target_review_at.isoformat() if row.target_review_at else None,
    }


def create_test_retention_record(session: Session, ctx: OrganisationContext, label: str, expire_days: int) -> dict[str, Any]:
    privacy_access.require_privacy_manage(ctx)
    row = PrivacyTestRetentionRecord(
        organisation_id=ctx.organisation_id,
        label=label,
        expires_at=_now() + timedelta(days=expire_days),
    )
    session.add(row)
    session.flush()
    return {"id": str(row.id), "label": row.label, "expires_at": row.expires_at.isoformat()}


def run_test_retention_purge(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    """Delete only privacy_test_retention_records past expiry — never production tenant data."""
    privacy_access.require_privacy_manage(ctx)
    now = _now()
    rows = session.scalars(
        select(PrivacyTestRetentionRecord).where(
            PrivacyTestRetentionRecord.organisation_id == ctx.organisation_id,
            PrivacyTestRetentionRecord.deleted_at.is_(None),
            PrivacyTestRetentionRecord.expires_at <= now,
        )
    ).all()
    count = 0
    for row in rows:
        row.deleted_at = now
        session.delete(row)
        count += 1
    log = PrivacyDeletionLog(
        organisation_id=ctx.organisation_id,
        scope="test_retention_records",
        records_deleted=count,
        performed_by_user_id=ctx.user_id,
        details={"purged_at": now.isoformat()},
    )
    session.add(log)
    session.flush()
    record_event(
        session,
        action=audit_events.PRIVACY_TEST_PURGE,
        resource_type="privacy_deletion",
        resource_id=log.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Purged expired privacy test retention records",
        metadata={"records_deleted": count},
        raise_on_error=False,
    )
    return {"records_deleted": count, "deletion_log_id": str(log.id)}
