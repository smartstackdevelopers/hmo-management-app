"""Privacy approval gate — never auto-approve DPIA/feasibility."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.room_occupancy import RoomOccupancyApprovalGate, RoomOccupancySettings
from app.room_occupancy import access
from app.room_occupancy.constants import APPROVED_ONLY, GATE_STATUSES, REQUIRED_GATE_FIELDS
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def outstanding_requirements(gate: RoomOccupancyApprovalGate) -> list[str]:
    missing: list[str] = []
    for field in REQUIRED_GATE_FIELDS:
        if getattr(gate, field) != APPROVED_ONLY:
            missing.append(field)
    if not gate.approved_room_purposes:
        missing.append("approved_room_purposes")
    if not gate.authorised_viewer_notes:
        missing.append("authorised_viewer_notes")
    if not gate.accuracy_requirements_notes:
        missing.append("accuracy_requirements_notes")
    if not gate.approval_date or not gate.approved_by_user_id:
        missing.append("formal_approval_record")
    return missing


def is_gate_complete(gate: RoomOccupancyApprovalGate) -> bool:
    return len(outstanding_requirements(gate)) == 0


def gate_to_dict(gate: RoomOccupancyApprovalGate) -> dict[str, Any]:
    outstanding = outstanding_requirements(gate)
    complete = len(outstanding) == 0
    return {
        "id": str(gate.id),
        "organisation_id": str(gate.organisation_id),
        "feasibility_status": gate.feasibility_status,
        "dpia_status": gate.dpia_status,
        "signage_status": gate.signage_status,
        "retention_policy_status": gate.retention_policy_status,
        "camera_compatibility_status": gate.camera_compatibility_status,
        "approved_room_purposes": gate.approved_room_purposes or [],
        "authorised_viewer_notes": gate.authorised_viewer_notes,
        "accuracy_requirements_notes": gate.accuracy_requirements_notes,
        "documentation_refs": gate.documentation_refs or [],
        "approval_date": gate.approval_date.isoformat() if gate.approval_date else None,
        "approved_by_user_id": str(gate.approved_by_user_id) if gate.approved_by_user_id else None,
        "live_counting_enabled": bool(gate.live_counting_enabled) and complete,
        "live_counting_requested": bool(gate.live_counting_enabled),
        "gate_complete": complete,
        "outstanding_requirements": outstanding,
        "notes": gate.notes,
        "updated_at": gate.updated_at.isoformat() if gate.updated_at else None,
        "privacy_notice": (
            "Live camera/RTSP activation and count ingestion remain disabled until every "
            "approval requirement is recorded as approved by an authorised administrator. "
            "HMore never auto-approves DPIA or feasibility."
        ),
    }


def get_or_create_gate(session: Session, ctx: OrganisationContext) -> RoomOccupancyApprovalGate:
    row = session.scalar(
        select(RoomOccupancyApprovalGate).where(
            RoomOccupancyApprovalGate.organisation_id == ctx.organisation_id
        )
    )
    if row is not None:
        return row
    row = RoomOccupancyApprovalGate(organisation_id=ctx.organisation_id)
    session.add(row)
    session.flush()
    return row


def get_or_create_settings(session: Session, ctx: OrganisationContext) -> RoomOccupancySettings:
    row = session.scalar(
        select(RoomOccupancySettings).where(RoomOccupancySettings.organisation_id == ctx.organisation_id)
    )
    if row is not None:
        return row
    row = RoomOccupancySettings(organisation_id=ctx.organisation_id)
    session.add(row)
    session.flush()
    return row


def get_gate(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    access.require_occupancy_read(ctx)
    return gate_to_dict(get_or_create_gate(session, ctx))


def update_gate(
    session: Session,
    ctx: OrganisationContext,
    *,
    feasibility_status: str | None = None,
    dpia_status: str | None = None,
    signage_status: str | None = None,
    retention_policy_status: str | None = None,
    camera_compatibility_status: str | None = None,
    approved_room_purposes: list[Any] | None = None,
    authorised_viewer_notes: str | None = None,
    accuracy_requirements_notes: str | None = None,
    documentation_refs: list[Any] | None = None,
    notes: str | None = None,
    live_counting_enabled: bool | None = None,
    record_formal_approval: bool = False,
) -> dict[str, Any]:
    access.require_occupancy_settings(ctx)
    gate = get_or_create_gate(session, ctx)

    def _set_status(attr: str, value: str | None) -> None:
        if value is None:
            return
        if value not in GATE_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid {attr}")
        # Never silently invent "approved" — caller must send approved explicitly
        setattr(gate, attr, value)

    _set_status("feasibility_status", feasibility_status)
    _set_status("dpia_status", dpia_status)
    _set_status("signage_status", signage_status)
    _set_status("retention_policy_status", retention_policy_status)
    _set_status("camera_compatibility_status", camera_compatibility_status)

    if approved_room_purposes is not None:
        gate.approved_room_purposes = list(approved_room_purposes)
    if authorised_viewer_notes is not None:
        gate.authorised_viewer_notes = authorised_viewer_notes
    if accuracy_requirements_notes is not None:
        gate.accuracy_requirements_notes = accuracy_requirements_notes
    if documentation_refs is not None:
        gate.documentation_refs = list(documentation_refs)
    if notes is not None:
        gate.notes = notes

    if record_formal_approval:
        if not all(getattr(gate, f) == APPROVED_ONLY for f in REQUIRED_GATE_FIELDS):
            raise HTTPException(
                status_code=400,
                detail="Cannot record formal approval until all gate statuses are approved",
            )
        if not gate.approved_room_purposes:
            raise HTTPException(status_code=400, detail="approved_room_purposes required")
        if not gate.authorised_viewer_notes or not gate.accuracy_requirements_notes:
            raise HTTPException(status_code=400, detail="Authorised viewers and accuracy notes required")
        gate.approval_date = _now()
        gate.approved_by_user_id = ctx.user_id

    if live_counting_enabled is not None:
        if live_counting_enabled and not is_gate_complete(gate):
            raise HTTPException(
                status_code=400,
                detail="Cannot enable live counting until the privacy approval gate is complete",
            )
        gate.live_counting_enabled = live_counting_enabled

    # If gate becomes incomplete, force live counting off
    if not is_gate_complete(gate):
        gate.live_counting_enabled = False

    session.flush()
    record_event(
        session,
        action=audit_events.ROOM_OCCUPANCY_GATE_UPDATE,
        resource_type="room_occupancy_approval_gate",
        resource_id=gate.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Updated room occupancy approval gate",
        metadata={"gate_complete": is_gate_complete(gate), "live_enabled": gate.live_counting_enabled},
        raise_on_error=False,
    )
    return gate_to_dict(gate)


def assert_live_counting_allowed(session: Session, organisation_id: uuid.UUID) -> RoomOccupancyApprovalGate:
    gate = session.scalar(
        select(RoomOccupancyApprovalGate).where(
            RoomOccupancyApprovalGate.organisation_id == organisation_id
        )
    )
    if gate is None or not is_gate_complete(gate) or not gate.live_counting_enabled:
        raise HTTPException(
            status_code=403,
            detail=(
                "Live occupancy counting is disabled. Complete the privacy approval gate "
                "(feasibility, DPIA, signage, retention, camera compatibility) and enable live counting."
            ),
        )
    return gate
