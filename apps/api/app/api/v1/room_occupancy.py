"""F6.5 Room Occupancy API — privacy-gated; no raw video endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.room_occupancy import alerts as alerts_mod
from app.room_occupancy import devices as devices_mod
from app.room_occupancy import gate as gate_mod
from app.room_occupancy import service as occupancy_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/room-occupancy", tags=["room-occupancy"])


class GateUpdateBody(BaseModel):
    feasibility_status: str | None = None
    dpia_status: str | None = None
    signage_status: str | None = None
    retention_policy_status: str | None = None
    camera_compatibility_status: str | None = None
    approved_room_purposes: list[Any] | None = None
    authorised_viewer_notes: str | None = None
    accuracy_requirements_notes: str | None = None
    documentation_refs: list[Any] | None = None
    notes: str | None = None
    live_counting_enabled: bool | None = None
    record_formal_approval: bool = False


class SettingsUpdateBody(BaseModel):
    near_capacity_percent: int | None = Field(default=None, ge=50, le=99)
    offline_after_seconds: int | None = Field(default=None, ge=30, le=86400)
    history_retention_days: int | None = Field(default=None, ge=7, le=3650)
    alert_retention_days: int | None = Field(default=None, ge=30, le=3650)


class DeviceCreateBody(BaseModel):
    device_key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    device_type: Literal["edge_people_counter", "onvif_camera", "rtsp_camera", "sensor"]
    property_id: uuid.UUID
    room_id: uuid.UUID | None = None
    supports_people_counting: bool = False
    compatibility_verified: bool = False
    config: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, Any] = Field(default_factory=dict)


class DeviceUpdateBody(BaseModel):
    name: str | None = None
    room_id: uuid.UUID | None = None
    clear_room: bool = False
    supports_people_counting: bool | None = None
    compatibility_verified: bool | None = None
    is_enabled: bool | None = None
    connection_status: str | None = None
    last_error: str | None = None
    config: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None


class CountIngestBody(BaseModel):
    device_id: uuid.UUID
    estimated_count: int = Field(ge=0, le=500)
    recorded_at: datetime | None = None


class CorrectCountBody(BaseModel):
    corrected_count: int = Field(ge=0, le=500)
    reason: str = Field(min_length=1, max_length=2000)


@router.get("/dashboard")
def dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return occupancy_service.dashboard(session, org)


@router.get("/approval-gate")
def get_approval_gate(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return gate_mod.get_gate(session, org)


@router.patch("/approval-gate")
def update_approval_gate(
    body: GateUpdateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return gate_mod.update_gate(session, org, **body.model_dump())


@router.get("/settings")
def get_settings(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    from app.room_occupancy.access import require_occupancy_read

    require_occupancy_read(org)
    return occupancy_service.settings_to_dict(gate_mod.get_or_create_settings(session, org))


@router.patch("/settings")
def patch_settings(
    body: SettingsUpdateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return occupancy_service.update_settings(session, org, **body.model_dump(exclude_unset=True))


@router.get("/devices")
def list_devices(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": devices_mod.list_devices(session, org)}


@router.post("/devices")
def create_device(
    body: DeviceCreateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return devices_mod.register_device(
        session,
        org,
        device_key=body.device_key,
        name=body.name,
        device_type=body.device_type,
        property_id=body.property_id,
        room_id=body.room_id,
        supports_people_counting=body.supports_people_counting,
        compatibility_verified=body.compatibility_verified,
        config=body.config,
        credentials=body.credentials,
    )


@router.patch("/devices/{device_id}")
def patch_device(
    device_id: uuid.UUID,
    body: DeviceUpdateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return devices_mod.update_device(session, org, device_id, **body.model_dump(exclude_unset=True))


@router.get("/rooms")
def list_rooms(
    property_id: uuid.UUID | None = None,
    floor: str | None = None,
    room_id: uuid.UUID | None = None,
    occupancy_status: str | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {
        "items": occupancy_service.list_room_states(
            session,
            org,
            property_id=property_id,
            floor=floor,
            room_id=room_id,
            occupancy_status=occupancy_status,
        )
    }


@router.post("/counts/ingest")
def ingest_count(
    body: CountIngestBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    """Edge count ingest — rejected unless privacy gate enables live counting."""
    return occupancy_service.ingest_count(
        session,
        org,
        device_id=body.device_id,
        estimated_count=body.estimated_count,
        recorded_at=body.recorded_at,
    )


@router.post("/rooms/{room_id}/correct")
def correct_count(
    room_id: uuid.UUID,
    body: CorrectCountBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return occupancy_service.correct_count(
        session, org, room_id, corrected_count=body.corrected_count, reason=body.reason
    )


@router.get("/history")
def history(
    room_id: uuid.UUID | None = None,
    limit: int = Query(100, ge=1, le=500),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": occupancy_service.list_history(session, org, room_id=room_id, limit=limit)}


@router.get("/reports/usage")
def usage_reports(
    room_id: uuid.UUID | None = None,
    period: Literal["daily", "weekly", "monthly"] = "daily",
    limit: int = Query(30, ge=1, le=90),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return occupancy_service.history_summary(session, org, room_id=room_id, period=period, limit=limit)


@router.get("/alerts")
def list_alerts(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": alerts_mod.list_alerts(session, org, status=status, limit=limit)}


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return alerts_mod.acknowledge_alert(session, org, alert_id)


@router.get("/corrections")
def list_corrections(
    limit: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": occupancy_service.list_corrections(session, org, limit=limit)}
