"""Occupancy site-survey service. Does not implement cameras or occupancy counting."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.file_metadata import FileMetadata
from app.db.models.occupancy_survey import (
    OccupancySiteSurvey,
    OccupancySurveyFinding,
    OccupancySurveyRoomAssessment,
)
from app.db.models.property import Property
from app.db.models.room import Room
from app.occupancy.access import require_survey_read, require_survey_write
from app.occupancy.schemas import (
    FindingCreate,
    FindingUpdate,
    RoomAssessmentIn,
    SurveyCreate,
    SurveyUpdate,
)
from app.records.pagination import offset_limit
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation

FEASIBILITY_STATUSES = frozenset(
    {
        "suitable",
        "suitable_with_actions",
        "not_suitable",
        "further_assessment_required",
    }
)
SURVEY_STATUSES = frozenset({"draft", "in_progress", "completed", "superseded"})


def _public_survey(row: OccupancySiteSurvey) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "property_id": str(row.property_id),
        "status": row.status,
        "survey_date": row.survey_date.isoformat() if row.survey_date else None,
        "surveyor_user_id": str(row.surveyor_user_id) if row.surveyor_user_id else None,
        "surveyor_display_name": row.surveyor_display_name,
        "site_contact_notes": row.site_contact_notes,
        "building_assessment": row.building_assessment,
        "facilities_assessment": row.facilities_assessment,
        "health_safety_assessment": row.health_safety_assessment,
        "accessibility_assessment": row.accessibility_assessment,
        "camera_feasibility_notes": row.camera_feasibility_notes,
        "feasibility_status": row.feasibility_status,
        "feasibility_summary": row.feasibility_summary,
        "missing_information": row.missing_information,
        "recommendations": row.recommendations,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "disclaimer": (
            "Feasibility status is an operational assessment only — not a legal or "
            "regulatory certification. Camera/occupancy software is out of scope for F1.10."
        ),
    }


def create_survey(
    session: Session, ctx: OrganisationContext, data: SurveyCreate
) -> dict[str, Any]:
    require_survey_write(ctx)
    prop = session.get(Property, data.property_id)
    if prop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    assert_same_organisation(ctx, prop.organisation_id)

    row = OccupancySiteSurvey(
        organisation_id=ctx.organisation_id,
        property_id=prop.id,
        status="draft",
        survey_date=data.survey_date,
        surveyor_user_id=ctx.user_id,
        surveyor_display_name=data.surveyor_display_name,
        site_contact_notes=data.site_contact_notes,
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.OCCUPANCY_SURVEY_CREATE,
        resource_type="occupancy_site_survey",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Occupancy site survey created",
        metadata={"property_id": str(prop.id)},
    )
    return _public_survey(row)


def list_surveys(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    property_id: uuid.UUID | None = None,
) -> tuple[list[dict[str, Any]], int]:
    require_survey_read(ctx)
    stmt = select(OccupancySiteSurvey).where(
        OccupancySiteSurvey.organisation_id == ctx.organisation_id
    )
    if property_id:
        stmt = stmt.where(OccupancySiteSurvey.property_id == property_id)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(
            stmt.order_by(OccupancySiteSurvey.created_at.desc(), OccupancySiteSurvey.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return [_public_survey(row) for row in rows], total


def get_survey(
    session: Session, ctx: OrganisationContext, survey_id: uuid.UUID
) -> OccupancySiteSurvey:
    require_survey_read(ctx)
    row = session.get(OccupancySiteSurvey, survey_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey not found")
    assert_same_organisation(ctx, row.organisation_id)
    return row


def update_survey(
    session: Session,
    ctx: OrganisationContext,
    survey_id: uuid.UUID,
    data: SurveyUpdate,
) -> dict[str, Any]:
    require_survey_write(ctx)
    row = session.get(OccupancySiteSurvey, survey_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey not found")
    assert_same_organisation(ctx, row.organisation_id)
    if row.status == "completed" and data.status not in (None, "superseded"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completed surveys can only be superseded",
        )

    payload = data.model_dump(exclude_unset=True)
    if "feasibility_status" in payload and payload["feasibility_status"] is not None:
        if payload["feasibility_status"] not in FEASIBILITY_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid feasibility_status"
            )
    if "status" in payload and payload["status"] is not None:
        if payload["status"] not in SURVEY_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
        if payload["status"] == "completed":
            if not payload.get("feasibility_status") and not row.feasibility_status:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="feasibility_status is required to complete a survey",
                )
            row.completed_at = datetime.now(timezone.utc)

    for key, value in payload.items():
        setattr(row, key, value)
    session.add(row)
    session.flush()
    action = (
        audit_events.OCCUPANCY_SURVEY_COMPLETE
        if payload.get("status") == "completed"
        else audit_events.OCCUPANCY_SURVEY_UPDATE
    )
    record_event(
        session,
        action=action,
        resource_type="occupancy_site_survey",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Occupancy site survey updated",
        metadata={"status": row.status, "feasibility_status": row.feasibility_status},
    )
    return _public_survey(row)


def upsert_room_assessment(
    session: Session,
    ctx: OrganisationContext,
    survey_id: uuid.UUID,
    data: RoomAssessmentIn,
) -> dict[str, Any]:
    require_survey_write(ctx)
    survey = session.get(OccupancySiteSurvey, survey_id)
    if survey is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey not found")
    assert_same_organisation(ctx, survey.organisation_id)
    if data.room_id:
        room = session.get(Room, data.room_id)
        if room is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
        assert_same_organisation(ctx, room.organisation_id)
        if room.property_id != survey.property_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Room does not belong to the surveyed property",
            )

    row = OccupancySurveyRoomAssessment(
        organisation_id=ctx.organisation_id,
        survey_id=survey.id,
        room_id=data.room_id,
        room_label=data.room_label.strip(),
        assessment=data.assessment or {},
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.OCCUPANCY_SURVEY_ROOM_ASSESS,
        resource_type="occupancy_survey_room_assessment",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Room assessment added to occupancy survey",
        metadata={"survey_id": str(survey.id), "room_label": row.room_label},
    )
    return {
        "id": str(row.id),
        "survey_id": str(row.survey_id),
        "room_id": str(row.room_id) if row.room_id else None,
        "room_label": row.room_label,
        "assessment": row.assessment,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_room_assessments(
    session: Session, ctx: OrganisationContext, survey_id: uuid.UUID
) -> list[dict[str, Any]]:
    get_survey(session, ctx, survey_id)
    rows = list(
        session.scalars(
            select(OccupancySurveyRoomAssessment).where(
                OccupancySurveyRoomAssessment.survey_id == survey_id,
                OccupancySurveyRoomAssessment.organisation_id == ctx.organisation_id,
            )
        )
    )
    return [
        {
            "id": str(row.id),
            "survey_id": str(row.survey_id),
            "room_id": str(row.room_id) if row.room_id else None,
            "room_label": row.room_label,
            "assessment": row.assessment,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]


def _validate_evidence(
    session: Session, ctx: OrganisationContext, evidence_file_id: uuid.UUID | None
) -> None:
    if evidence_file_id is None:
        return
    file_row = session.get(FileMetadata, evidence_file_id)
    if file_row is None or file_row.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evidence file not found")
    assert_same_organisation(ctx, file_row.organisation_id)


def add_finding(
    session: Session,
    ctx: OrganisationContext,
    survey_id: uuid.UUID,
    data: FindingCreate,
) -> dict[str, Any]:
    require_survey_write(ctx)
    survey = session.get(OccupancySiteSurvey, survey_id)
    if survey is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey not found")
    assert_same_organisation(ctx, survey.organisation_id)
    _validate_evidence(session, ctx, data.evidence_file_id)
    if data.related_room_id:
        room = session.get(Room, data.related_room_id)
        if room is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
        assert_same_organisation(ctx, room.organisation_id)

    row = OccupancySurveyFinding(
        organisation_id=ctx.organisation_id,
        survey_id=survey.id,
        category=data.category.strip(),
        severity=data.severity,
        description=data.description.strip(),
        recommended_action=data.recommended_action,
        related_room_id=data.related_room_id,
        responsible_notes=data.responsible_notes,
        target_date=data.target_date,
        evidence_file_id=data.evidence_file_id,
        notes=data.notes,
        status="open",
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.OCCUPANCY_SURVEY_FINDING_CREATE,
        resource_type="occupancy_survey_finding",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Occupancy survey finding recorded",
        metadata={"category": row.category, "severity": row.severity},
    )
    return _public_finding(row)


def update_finding(
    session: Session,
    ctx: OrganisationContext,
    finding_id: uuid.UUID,
    data: FindingUpdate,
) -> dict[str, Any]:
    require_survey_write(ctx)
    row = session.get(OccupancySurveyFinding, finding_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    assert_same_organisation(ctx, row.organisation_id)
    payload = data.model_dump(exclude_unset=True)
    if "evidence_file_id" in payload:
        _validate_evidence(session, ctx, payload["evidence_file_id"])
    for key, value in payload.items():
        setattr(row, key, value)
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.OCCUPANCY_SURVEY_FINDING_UPDATE,
        resource_type="occupancy_survey_finding",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Occupancy survey finding updated",
        metadata={"status": row.status},
    )
    return _public_finding(row)


def list_findings(
    session: Session, ctx: OrganisationContext, survey_id: uuid.UUID
) -> list[dict[str, Any]]:
    get_survey(session, ctx, survey_id)
    rows = list(
        session.scalars(
            select(OccupancySurveyFinding).where(
                OccupancySurveyFinding.survey_id == survey_id,
                OccupancySurveyFinding.organisation_id == ctx.organisation_id,
            )
        )
    )
    return [_public_finding(row) for row in rows]


def _public_finding(row: OccupancySurveyFinding) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "survey_id": str(row.survey_id),
        "category": row.category,
        "severity": row.severity,
        "description": row.description,
        "recommended_action": row.recommended_action,
        "related_room_id": str(row.related_room_id) if row.related_room_id else None,
        "responsible_notes": row.responsible_notes,
        "target_date": row.target_date.isoformat() if row.target_date else None,
        "status": row.status,
        "evidence_file_id": str(row.evidence_file_id) if row.evidence_file_id else None,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
