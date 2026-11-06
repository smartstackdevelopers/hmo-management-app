"""F2.6 evidence checklist and pack APIs."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.evidence import service as evidence_service
from app.evidence.schemas import (
    AssociateFileRequest,
    ChecklistItemCreate,
    ChecklistItemOut,
    ChecklistItemUpdate,
    EvidencePackOut,
    GeneratePackRequest,
    ReadinessOut,
    ReviewHistoryOut,
    TemplateCreate,
    TemplateOut,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter()
apps_router = APIRouter(
    prefix="/housing-applications/{application_id}/evidence",
    tags=["evidence"],
)
items_router = APIRouter(prefix="/evidence-items", tags=["evidence"])
packs_router = APIRouter(prefix="/evidence-packs", tags=["evidence"])
templates_router = APIRouter(prefix="/evidence-templates", tags=["evidence"])


@templates_router.get("", response_model=list[TemplateOut])
def list_templates(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return evidence_service.list_templates(session, org)


@templates_router.post("", response_model=TemplateOut, status_code=201)
def create_template(
    body: TemplateCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return evidence_service.create_template(session, org, body)


@templates_router.post("/seed-defaults", response_model=list[TemplateOut])
def seed_default_templates(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return evidence_service.ensure_default_templates(session, org)


@apps_router.get("", response_model=list[ChecklistItemOut])
def list_checklist(
    application_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    rows = evidence_service.list_checklist(session, org, application_id)
    return [evidence_service.item_out_dict(session, row) for row in rows]


@apps_router.post("", response_model=ChecklistItemOut, status_code=201)
def create_checklist_item(
    application_id: uuid.UUID,
    body: ChecklistItemCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = evidence_service.create_checklist_item(session, org, application_id, body)
    return evidence_service.item_out_dict(session, row)


@apps_router.post("/seed", response_model=list[ChecklistItemOut])
def seed_checklist(
    application_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    rows = evidence_service.seed_checklist_from_templates(session, org, application_id)
    return [evidence_service.item_out_dict(session, row) for row in rows]


@apps_router.get("/readiness", response_model=ReadinessOut)
def checklist_readiness(
    application_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return evidence_service.readiness(session, org, application_id)


@apps_router.post("/packs", response_model=EvidencePackOut, status_code=201)
def generate_pack(
    application_id: uuid.UUID,
    body: GeneratePackRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return evidence_service.generate_pack(session, org, application_id, body)


@apps_router.get("/packs", response_model=list[EvidencePackOut])
def list_packs(
    application_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return evidence_service.list_packs(session, org, application_id)


@items_router.get("/{item_id}", response_model=ChecklistItemOut)
def get_item(
    item_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return evidence_service.item_out_dict(
        session, evidence_service.get_checklist_item(session, org, item_id)
    )


@items_router.patch("/{item_id}", response_model=ChecklistItemOut)
def patch_item(
    item_id: uuid.UUID,
    body: ChecklistItemUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return evidence_service.item_out_dict(
        session, evidence_service.update_checklist_item(session, org, item_id, body)
    )


@items_router.post("/{item_id}/files", response_model=ChecklistItemOut)
def associate_file(
    item_id: uuid.UUID,
    body: AssociateFileRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return evidence_service.item_out_dict(
        session, evidence_service.associate_file(session, org, item_id, body)
    )


@items_router.post("/{item_id}/upload", response_model=ChecklistItemOut, status_code=201)
async def upload_evidence_file(
    item_id: uuid.UUID,
    upload: UploadFile = File(...),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    data = await upload.read()
    row = evidence_service.upload_and_associate(
        session,
        org,
        item_id,
        filename=upload.filename,
        content_type=upload.content_type,
        data=data,
    )
    return evidence_service.item_out_dict(session, row)


@items_router.get("/{item_id}/history", response_model=list[ReviewHistoryOut])
def item_history(
    item_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return evidence_service.list_review_history(session, org, item_id)


@packs_router.get("/{pack_id}", response_model=EvidencePackOut)
def get_pack(
    pack_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return evidence_service.get_pack(session, org, pack_id)


@packs_router.get("/{pack_id}/download")
def download_pack(
    pack_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Response:
    _pack, content, content_type, filename = evidence_service.download_pack_bytes(
        session, org, pack_id
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


router.include_router(templates_router)
router.include_router(apps_router)
router.include_router(items_router)
router.include_router(packs_router)
