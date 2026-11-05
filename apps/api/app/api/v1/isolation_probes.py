"""F1.5 organisation-isolation probes (not full F1.6 CRUD)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context
from app.tenancy import isolation as iso

router = APIRouter(prefix="/isolation", tags=["isolation"])


class PropertyCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address_line1: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    postcode: str = Field(min_length=1, max_length=20)


class PropertyUpdateBody(BaseModel):
    name: str = Field(min_length=1, max_length=255)


def _serialize_property(row) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "name": row.name,
    }


@router.get("/properties")
def list_properties(
    ctx: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows = iso.list_properties_for_org(session, ctx)
    return {"items": [_serialize_property(row) for row in rows]}


@router.post("/properties")
def create_property(
    body: PropertyCreateBody,
    ctx: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    row = iso.create_property_for_org(
        session,
        ctx,
        name=body.name,
        address_line1=body.address_line1,
        city=body.city,
        postcode=body.postcode,
    )
    return _serialize_property(row)


@router.get("/properties/{property_id}")
def get_property(
    property_id: uuid.UUID,
    ctx: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    row = iso.require_property_for_org(session, ctx, property_id)
    return _serialize_property(row)


@router.patch("/properties/{property_id}")
def patch_property(
    property_id: uuid.UUID,
    body: PropertyUpdateBody,
    ctx: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    row = iso.update_property_for_org(session, ctx, property_id, name=body.name)
    return _serialize_property(row)


@router.delete("/properties/{property_id}")
def remove_property(
    property_id: uuid.UUID,
    ctx: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    iso.delete_property_for_org(session, ctx, property_id)
    return {"status": "deleted"}
