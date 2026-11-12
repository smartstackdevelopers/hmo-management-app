"""F7.3 backup and restore drill API."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.backup import service as backup_service
from app.db.session import get_session
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/backups", tags=["backups"])


class StartBackupBody(BaseModel):
    backup_type: Literal["database", "files_manifest", "config_manifest"]
    retention_tier: Literal["daily", "weekly", "monthly"] = "daily"
    force: bool = False


@router.get("/dashboard")
def dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return backup_service.dashboard(session, org)


@router.get("/history")
def history(
    limit: int = Query(default=50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return backup_service.list_runs(session, org, limit=limit)


@router.get("/schedules")
def schedules(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return backup_service.list_schedules(session, org)


@router.get("/retention")
def retention(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return backup_service.list_retention(session, org)


@router.post("/run")
def run_backup(
    body: StartBackupBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return backup_service.start_backup(
        session,
        org,
        backup_type=body.backup_type,
        retention_tier=body.retention_tier,
        force=body.force,
    )


@router.post("/restore-drills/{backup_run_id}")
def restore_drill(
    backup_run_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return backup_service.run_restore_drill(session, org, backup_run_id)
