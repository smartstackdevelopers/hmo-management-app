"""F8.6 optional digital ID and advanced e-signatures API."""

from __future__ import annotations

import uuid
from datetime import date, datetime
import json
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.digital_id_esign import providers, service
from app.digital_id_esign.service import _settings
from app.db.session import get_session
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/digital-id-esign", tags=["digital-id-esign"])


class SettingsBody(BaseModel):
    enabled: bool | None = None
    privacy_review_complete: bool | None = None
    identity_provider: str | None = None
    esign_provider: str | None = None
    mfa_required_for_sign: bool | None = None
    reminder_config: dict[str, Any] | None = None


class IdentityDocumentBody(BaseModel):
    file_id: uuid.UUID
    category_slug: str = Field(min_length=1, max_length=64)
    expires_at: date | None = None


class IdentityReviewBody(BaseModel):
    decision: str = Field(pattern="^(verified|rejected|request_evidence|suspend)$")
    notes: str | None = None


class SigningRequestBody(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    file_id: uuid.UUID
    managed_document_id: uuid.UUID | None = None
    template_id: uuid.UUID | None = None
    workflow_type: str = Field(default="parallel", pattern="^(sequential|parallel)$")
    signer_user_ids: list[uuid.UUID] = Field(min_length=1)
    expires_at: datetime | None = None


class SignBody(BaseModel):
    signature_method: str = "click_to_sign"
    consent_text: str | None = None


class RejectBody(BaseModel):
    reason: str | None = None


@router.get("/settings")
def get_settings_api(
    session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_READ)
    return service.settings_dict(_settings(session, ctx.organisation_id))


@router.patch("/settings")
def patch_settings_api(
    body: SettingsBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.update_settings(session, ctx, body.model_dump(exclude_unset=True))
    return service.settings_dict(row)


@router.get("/identity/me")
def identity_me_api(
    session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)
) -> dict[str, Any]:
    row = service.get_or_create_identity(session, ctx)
    return {
        "id": str(row.id),
        "verification_status": row.verification_status,
        "verification_method": row.verification_method,
        "verified_at": row.verified_at.isoformat() if row.verified_at else None,
    }


@router.post("/identity/documents")
def submit_identity_doc_api(
    body: IdentityDocumentBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    doc = service.submit_identity_document(session, ctx, body.model_dump())
    return {"id": str(doc.id), "document_status": doc.document_status}


@router.post("/identity/{record_id}/review")
def review_identity_api(
    record_id: uuid.UUID,
    body: IdentityReviewBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.review_identity(session, ctx, record_id, decision=body.decision, notes=body.notes)
    return {"id": str(row.id), "verification_status": row.verification_status}


@router.post("/identity/{record_id}/provider-check")
def provider_check_api(
    record_id: uuid.UUID,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    req = service.create_provider_verification(session, ctx, record_id)
    return {"provider_ref": req.provider_ref, "status": req.status, "mode": req.result_payload.get("mode")}


@router.post("/signing-requests")
def create_signing_api(
    body: SigningRequestBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.create_signing_request(session, ctx, body.model_dump())
    return {"id": str(row.id), "reference_number": row.reference_number, "status": row.status}


@router.post("/signing-requests/{request_id}/send")
def send_signing_api(
    request_id: uuid.UUID,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.send_signing_request(session, ctx, request_id)
    return {"id": str(row.id), "status": row.status}


@router.get("/signing-requests/dashboard")
def dashboard_api(
    status: str | None = Query(default=None),
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> list[dict[str, Any]]:
    service.assert_addon(session, get_settings(), ctx.organisation_id)
    return service.signing_dashboard(session, ctx, status=status)


@router.get("/signing-requests/mine")
def my_pending_api(
    session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)
) -> list[dict[str, Any]]:
    service.assert_addon(session, get_settings(), ctx.organisation_id)
    return service.list_pending_for_user(session, ctx)


@router.post("/signers/{signer_id}/sign")
def sign_api(
    signer_id: uuid.UUID,
    body: SignBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    signer = service.sign_document(session, ctx, signer_id, body.model_dump())
    return {"id": str(signer.id), "status": signer.status, "method": signer.signature_method}


@router.post("/signers/{signer_id}/reject")
def reject_api(
    signer_id: uuid.UUID,
    body: RejectBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    signer = service.reject_signing(session, ctx, signer_id, body.reason)
    return {"id": str(signer.id), "status": signer.status}


@router.get("/signing-requests/{request_id}/verify-integrity")
def verify_integrity_api(
    request_id: uuid.UUID,
    file_hash: str | None = Query(default=None),
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    return service.verify_document_integrity(session, ctx, request_id, file_hash)


@router.get("/reports/dashboard")
def reports_api(
    session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)
) -> dict[str, Any]:
    return service.admin_stats(session, ctx)


@router.post("/webhooks/provider")
async def provider_webhook_api(
    request: Request,
    session: Session = Depends(get_session),
    x_webhook_signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
) -> dict[str, Any]:
    raw = await request.body()
    settings = get_settings()
    try:
        providers.verify_provider_webhook(raw, x_webhook_signature, settings)
    except ValueError as exc:
        return {"accepted": False, "reason": str(exc)}
    payload = json.loads(raw.decode() or "{}")
    row = service.process_provider_webhook(
        session, None, payload.get("provider", "sandbox"), payload.get("event_type", "unknown"), payload
    )
    return {"accepted": True, "event_id": str(row.id)}
