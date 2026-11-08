"""F3.15 organisation AI feature flags API. F3.15 itself is not flag-gated."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.ai_feature_flags import service as ff_service
from app.db.session import get_session
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/ai-feature-flags", tags=["ai-feature-flags"])


class UpdateFeatureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    pilot_enabled: bool | None = None
    change_reason: str | None = Field(default=None, max_length=2000)
    expected_revision: int | None = Field(default=None, ge=0)


@router.get("/registry")
def get_registry(
    org: OrganisationContext = Depends(get_organisation_context),
) -> dict:
    from app.ai_feature_flags import access as ff_access

    ff_access.require_read(org)
    return {"items": ff_service.list_registry()}


@router.get("")
def list_config(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return ff_service.list_organisation_config(session, org)


@router.get("/history")
def history(
    feature_id: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return ff_service.list_history(session, org, feature_id=feature_id, limit=limit)


@router.get("/{feature_id}")
def get_one(
    feature_id: str,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return ff_service.get_feature_config(session, org, feature_id)


@router.put("/{feature_id}")
def put_feature(
    feature_id: str,
    body: UpdateFeatureRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = ff_service.update_feature(
        session,
        org,
        feature_id,
        enabled=body.enabled,
        pilot_enabled=body.pilot_enabled,
        change_reason=body.change_reason,
        expected_revision=body.expected_revision,
    )
    session.commit()
    return result
