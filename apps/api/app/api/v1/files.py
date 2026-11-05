"""Private file metadata and content API (F1.8)."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.rbac.context import AuthorizationContext
from app.rbac.deps import require_perm
from app.rbac.permissions import Permission
from app.storage import service as file_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", status_code=201)
async def upload_file(
    upload: UploadFile = File(...),
    resource_type: str | None = Form(default=None, max_length=100),
    resource_id: str | None = Form(default=None, max_length=100),
    _authz: AuthorizationContext = Depends(require_perm(Permission.FILES_MANAGE)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    data = await upload.read()
    return file_service.upload_file(
        session,
        org,
        filename=upload.filename,
        declared_content_type=upload.content_type,
        data=data,
        resource_type=resource_type,
        resource_id=resource_id,
    )


@router.get("")
def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    resource_type: str | None = Query(None, max_length=100),
    _authz: AuthorizationContext = Depends(require_perm(Permission.FILES_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    items, total = file_service.list_files(
        session, org, page=page, page_size=page_size, resource_type=resource_type
    )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/{file_id}")
def get_file_metadata(
    file_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(require_perm(Permission.FILES_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return file_service.get_file_metadata(session, org, file_id)


@router.get("/{file_id}/content")
def download_file_content(
    file_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(require_perm(Permission.FILES_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Response:
    row, data = file_service.download_file(session, org, file_id)
    disposition = (
        f"attachment; filename*=UTF-8''{quote(row.original_filename)}"
    )
    return Response(
        content=data,
        media_type=row.content_type,
        headers={
            "Content-Disposition": disposition,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{file_id}")
def delete_file(
    file_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(require_perm(Permission.FILES_MANAGE)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return file_service.delete_file(session, org, file_id)
