"""F8.6 digital ID and e-signatures service."""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.digital_id_esign import (
    DigitalIdentityDocument,
    DigitalIdentityDocumentCategory,
    DigitalIdentityProviderRequest,
    DigitalIdentityRecord,
    DigitalIdentityVerificationReview,
    EsignProviderWebhookEvent,
    EsignSignatureEvent,
    EsignSigner,
    EsignSigningRequest,
    EsignTemplate,
    OrganisationDigitalIdEsignSettings,
)
from app.db.models.file_metadata import FileMetadata
from app.digital_id_esign import access
from app.digital_id_esign.constants import (
    ADDON_DISCLAIMER,
    ADVANCED_CONSENT_PHRASE,
    DEFAULT_ESIGN_TEMPLATES,
    IDENTITY_DOCUMENT_CATEGORIES,
    SIGNATURE_METHODS,
)
from app.digital_id_esign.providers import sandbox_esign_envelope_create, sandbox_identity_check_create
from app.ops.notifications import ReminderMessage, get_notification_provider
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _settings(session: Session, org_id: UUID) -> OrganisationDigitalIdEsignSettings:
    row = session.scalars(
        select(OrganisationDigitalIdEsignSettings).where(OrganisationDigitalIdEsignSettings.organisation_id == org_id)
    ).first()
    if row is None:
        row = OrganisationDigitalIdEsignSettings(organisation_id=org_id)
        session.add(row)
        session.flush()
    return row


def assert_addon(session: Session, settings: Settings, org_id: UUID) -> OrganisationDigitalIdEsignSettings:
    if not settings.digital_id_esign_global_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Digital ID / e-sign add-on disabled platform-wide")
    row = _settings(session, org_id)
    if not row.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Digital ID / e-sign disabled for organisation")
    return row


def settings_dict(row: OrganisationDigitalIdEsignSettings) -> dict[str, Any]:
    return {
        "organisation_id": str(row.organisation_id),
        "enabled": row.enabled,
        "privacy_review_complete": row.privacy_review_complete,
        "identity_provider": row.identity_provider,
        "esign_provider": row.esign_provider,
        "mfa_required_for_sign": row.mfa_required_for_sign,
        "reminder_config": row.reminder_config,
        "disclaimer": ADDON_DISCLAIMER,
    }


def update_settings(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> OrganisationDigitalIdEsignSettings:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_MANAGE)
    row = assert_addon(session, get_settings(), ctx.organisation_id)
    for key in ("enabled", "privacy_review_complete", "mfa_required_for_sign"):
        if data.get(key) is not None:
            setattr(row, key, bool(data[key]))
    if data.get("identity_provider") is not None:
        row.identity_provider = str(data["identity_provider"])
    if data.get("esign_provider") is not None:
        row.esign_provider = str(data["esign_provider"])
    if data.get("reminder_config") is not None:
        row.reminder_config = data["reminder_config"]
    session.flush()
    record_event(
        session,
        action=audit_events.DIGITAL_ID_ESIGN_SETTINGS_UPDATE,
        resource_type="digital_id_esign_settings",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Digital ID / e-sign settings updated",
    )
    return row


def ensure_identity_categories(session: Session, org_id: UUID) -> None:
    if session.scalar(select(func.count()).select_from(DigitalIdentityDocumentCategory).where(DigitalIdentityDocumentCategory.organisation_id == org_id)):
        return
    for idx, (slug, name) in enumerate(IDENTITY_DOCUMENT_CATEGORIES):
        session.add(DigitalIdentityDocumentCategory(organisation_id=org_id, slug=slug, name=name, sort_order=idx))
    session.flush()


def ensure_templates(session: Session, org_id: UUID) -> None:
    if session.scalar(select(func.count()).select_from(EsignTemplate).where(EsignTemplate.organisation_id == org_id)):
        return
    for slug, name in DEFAULT_ESIGN_TEMPLATES:
        session.add(
            EsignTemplate(
                organisation_id=org_id,
                slug=slug,
                name=name,
                description="Draft template — requires legal approval before production use.",
                approved_for_production=False,
            )
        )
    session.flush()


def get_or_create_identity(session: Session, ctx: OrganisationContext, user_id: UUID | None = None) -> DigitalIdentityRecord:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_IDENTITY_SUBMIT)
    assert_addon(session, get_settings(), ctx.organisation_id)
    ensure_identity_categories(session, ctx.organisation_id)
    target = user_id or ctx.user_id
    row = session.scalar(
        select(DigitalIdentityRecord).where(
            DigitalIdentityRecord.organisation_id == ctx.organisation_id,
            DigitalIdentityRecord.user_id == target,
        )
    )
    if row is None:
        row = DigitalIdentityRecord(organisation_id=ctx.organisation_id, user_id=target, verification_status="not_started")
        session.add(row)
        session.flush()
        record_event(
            session,
            action=audit_events.DIGITAL_ID_RECORD_CREATED,
            resource_type="digital_identity_record",
            resource_id=str(row.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value if ctx.role else None,
            outcome=AuditOutcome.SUCCESS,
            summary="Digital identity record created",
        )
    return row


def submit_identity_document(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> DigitalIdentityDocument:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_IDENTITY_SUBMIT)
    record = get_or_create_identity(session, ctx)
    if record.user_id != ctx.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Cannot submit documents for another user")
    file_id = data["file_id"]
    meta = session.get(FileMetadata, file_id)
    if meta is None or meta.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="File not found")
    doc = DigitalIdentityDocument(
        organisation_id=ctx.organisation_id,
        identity_record_id=record.id,
        category_slug=data["category_slug"],
        file_id=file_id,
        document_status="pending",
        expires_at=data.get("expires_at"),
    )
    session.add(doc)
    record.verification_status = "pending"
    session.flush()
    record_event(
        session,
        action=audit_events.DIGITAL_ID_DOCUMENT_SUBMITTED,
        resource_type="digital_identity_document",
        resource_id=str(doc.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Identity document submitted",
    )
    return doc


def review_identity(
    session: Session, ctx: OrganisationContext, record_id: UUID, *, decision: str, notes: str | None
) -> DigitalIdentityRecord:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_IDENTITY_VERIFY)
    record = session.get(DigitalIdentityRecord, record_id)
    if record is None or record.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Record not found")
    session.add(
        DigitalIdentityVerificationReview(
            organisation_id=ctx.organisation_id,
            identity_record_id=record.id,
            reviewer_user_id=ctx.user_id,
            decision=decision,
            notes=notes,
        )
    )
    if decision == "verified":
        record.verification_status = "verified"
        record.verified_at = _now()
        record.reviewer_user_id = ctx.user_id
    elif decision == "rejected":
        record.verification_status = "rejected"
    elif decision == "suspend":
        record.verification_status = "suspended"
    else:
        record.verification_status = "under_review"
    session.flush()
    _notify_user(session, ctx.organisation_id, record.user_id, "Identity verification updated")
    return record


def create_provider_verification(session: Session, ctx: OrganisationContext, record_id: UUID) -> DigitalIdentityProviderRequest:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_IDENTITY_SUBMIT)
    settings_row = assert_addon(session, get_settings(), ctx.organisation_id)
    record = session.get(DigitalIdentityRecord, record_id)
    if record is None or record.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Record not found")
    access.assert_identity_owner(ctx, record)
    if settings_row.identity_provider != "sandbox" and settings_row.identity_provider != "manual":
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail="Paid identity provider not activated")
    result = sandbox_identity_check_create()
    req = DigitalIdentityProviderRequest(
        organisation_id=ctx.organisation_id,
        identity_record_id=record.id,
        provider=settings_row.identity_provider,
        provider_ref=result["provider_ref"],
        status=result["status"],
        result_payload=result,
    )
    session.add(req)
    record.verification_status = "under_review"
    record.verification_method = settings_row.identity_provider
    session.flush()
    return req


def _file_hash(session: Session, file_id: UUID, org_id: UUID) -> str:
    meta = session.get(FileMetadata, file_id)
    if meta is None or meta.organisation_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="File not found")
    if meta.checksum_sha256:
        return meta.checksum_sha256.lower()
    return hashlib.sha256(f"{org_id}:{file_id}".encode()).hexdigest()


def _next_esign_ref(session: Session, org_id: UUID) -> str:
    year = _now().year
    prefix = f"ESG-{year}-"
    n = session.scalar(
        select(func.count()).select_from(EsignSigningRequest).where(
            EsignSigningRequest.organisation_id == org_id,
            EsignSigningRequest.reference_number.like(f"{prefix}%"),
        )
    ) or 0
    return f"{prefix}{n + 1:05d}"


def create_signing_request(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> EsignSigningRequest:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_SIGN_REQUEST)
    settings_row = assert_addon(session, get_settings(), ctx.organisation_id)
    ensure_templates(session, ctx.organisation_id)
    file_id = data["file_id"]
    content_hash = _file_hash(session, file_id, ctx.organisation_id)
    row = EsignSigningRequest(
        organisation_id=ctx.organisation_id,
        reference_number=_next_esign_ref(session, ctx.organisation_id),
        title=data["title"],
        managed_document_id=data.get("managed_document_id"),
        file_id=file_id,
        template_id=data.get("template_id"),
        workflow_type=data.get("workflow_type", "parallel"),
        status="draft",
        content_hash_sha256=content_hash,
        created_by_user_id=ctx.user_id,
        expires_at=data.get("expires_at"),
    )
    session.add(row)
    session.flush()
    for idx, signer_id in enumerate(data.get("signer_user_ids") or []):
        session.add(
            EsignSigner(
                organisation_id=ctx.organisation_id,
                signing_request_id=row.id,
                signer_user_id=signer_id,
                signing_order=idx,
            )
        )
    session.flush()
    if settings_row.esign_provider == "sandbox":
        sandbox_esign_envelope_create(row.title)
    record_event(
        session,
        action=audit_events.DIGITAL_ID_ESIGN_REQUEST_CREATED,
        resource_type="esign_signing_request",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="E-sign signing request created",
    )
    return row


def send_signing_request(session: Session, ctx: OrganisationContext, request_id: UUID) -> EsignSigningRequest:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_SIGN_REQUEST)
    row = session.get(EsignSigningRequest, request_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Request not found")
    signers = session.scalars(select(EsignSigner).where(EsignSigner.signing_request_id == row.id)).all()
    if not signers:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="At least one signer required")
    row.status = "pending"
    session.flush()
    for s in signers:
        _notify_user(session, ctx.organisation_id, s.signer_user_id, "New document signing request")
    return row


def _sequential_gate(session: Session, signer: EsignSigner, request: EsignSigningRequest) -> None:
    if request.workflow_type != "sequential":
        return
    prior = session.scalars(
        select(EsignSigner).where(
            EsignSigner.signing_request_id == request.id,
            EsignSigner.signing_order < signer.signing_order,
        )
    ).all()
    for p in prior:
        if p.status != "signed":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Earlier signers must complete first")


def sign_document(session: Session, ctx: OrganisationContext, signer_id: UUID, data: dict[str, Any]) -> EsignSigner:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_SIGN)
    settings_row = assert_addon(session, get_settings(), ctx.organisation_id)
    if settings_row.mfa_required_for_sign:
        pass  # MFA enforced at auth layer when org enables — no bypass here
    signer = session.get(EsignSigner, signer_id)
    if signer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Signer not found")
    request = session.get(EsignSigningRequest, signer.signing_request_id)
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Request not found")
    access.assert_signer_may_sign(ctx, signer, request)
    if request.status not in ("pending", "draft"):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Signing request not open")
    if signer.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Signer already completed")
    _sequential_gate(session, signer, request)
    method = data.get("signature_method", "click_to_sign")
    if method not in SIGNATURE_METHODS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid signature method")
    consent = data.get("consent_text") or ADVANCED_CONSENT_PHRASE
    if method == "provider_advanced" and settings_row.esign_provider == "sandbox":
        method = "click_to_sign"
    signer.status = "signed"
    signer.signature_method = method
    signer.signed_at = _now()
    session.add(
        EsignSignatureEvent(
            organisation_id=ctx.organisation_id,
            signer_id=signer.id,
            event_type="signed",
            signature_method=method,
            consent_text=consent,
            evidence={
                "method": method,
                "disclaimer": ADDON_DISCLAIMER,
                "basic_vs_advanced": method != "provider_advanced",
            },
        )
    )
    session.flush()
    remaining = session.scalar(
        select(func.count()).select_from(EsignSigner).where(
            EsignSigner.signing_request_id == request.id,
            EsignSigner.status == "pending",
        )
    )
    if not remaining:
        request.status = "completed"
        request.completed_at = _now()
        _notify_user(session, ctx.organisation_id, request.created_by_user_id, "Document signing completed")
    record_event(
        session,
        action=audit_events.DIGITAL_ID_ESIGN_SIGNATURE_RECORDED,
        resource_type="esign_signer",
        resource_id=str(signer.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Signature recorded",
    )
    return signer


def reject_signing(session: Session, ctx: OrganisationContext, signer_id: UUID, reason: str | None) -> EsignSigner:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_SIGN)
    signer = session.get(EsignSigner, signer_id)
    if signer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Signer not found")
    request = session.get(EsignSigningRequest, signer.signing_request_id)
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Request not found")
    access.assert_signer_may_sign(ctx, signer, request)
    signer.status = "rejected"
    request.status = "rejected"
    session.add(
        EsignSignatureEvent(
            organisation_id=ctx.organisation_id,
            signer_id=signer.id,
            event_type="rejected",
            consent_text=reason,
            evidence={"reason": reason},
        )
    )
    session.flush()
    return signer


def verify_document_integrity(session: Session, ctx: OrganisationContext, request_id: UUID, file_hash: str | None) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_VERIFY_DOC)
    request = session.get(EsignSigningRequest, request_id)
    if request is None or request.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Request not found")
    current = _file_hash(session, request.file_id, ctx.organisation_id)
    supplied = (file_hash or current).lower()
    matches = current == request.content_hash_sha256 and supplied == request.content_hash_sha256
    return {
        "request_id": str(request.id),
        "stored_hash": request.content_hash_sha256,
        "current_file_hash": current,
        "matches_recorded_hash": matches,
        "tampering_suspected": not matches,
        "disclaimer": "Hash match indicates file consistency only — not legal tamper-proof status.",
    }


def signing_dashboard(session: Session, ctx: OrganisationContext, *, status: str | None) -> list[dict[str, Any]]:
    access.require_read(ctx)
    q = select(EsignSigningRequest).where(EsignSigningRequest.organisation_id == ctx.organisation_id)
    if status:
        q = q.where(EsignSigningRequest.status == status)
    rows = session.scalars(q.order_by(EsignSigningRequest.created_at.desc()).limit(100)).all()
    out: list[dict[str, Any]] = []
    for r in rows:
        signers = session.scalars(select(EsignSigner).where(EsignSigner.signing_request_id == r.id)).all()
        out.append(
            {
                "id": str(r.id),
                "reference_number": r.reference_number,
                "title": r.title,
                "status": r.status,
                "workflow_type": r.workflow_type,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "signers": [
                    {"user_id": str(s.signer_user_id), "status": s.status, "order": s.signing_order} for s in signers
                ],
            }
        )
    return out


def list_pending_for_user(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_SIGN)
    rows = session.scalars(
        select(EsignSigner)
        .join(EsignSigningRequest, EsignSigner.signing_request_id == EsignSigningRequest.id)
        .where(
            EsignSigner.organisation_id == ctx.organisation_id,
            EsignSigner.signer_user_id == ctx.user_id,
            EsignSigner.status == "pending",
            EsignSigningRequest.status == "pending",
        )
    ).all()
    result: list[dict[str, Any]] = []
    for s in rows:
        req = session.get(EsignSigningRequest, s.signing_request_id)
        if req:
            result.append({"signer_id": str(s.id), "request_id": str(req.id), "title": req.title, "reference": req.reference_number})
    return result


def process_provider_webhook(
    session: Session, org_id: UUID | None, provider: str, event_type: str, payload: dict[str, Any]
) -> EsignProviderWebhookEvent:
    row = EsignProviderWebhookEvent(
        organisation_id=org_id,
        provider=provider,
        event_type=event_type,
        payload=payload,
        processed=False,
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.DIGITAL_ID_ESIGN_WEBHOOK_RECEIVED,
        resource_type="esign_provider_webhook",
        resource_id=str(row.id),
        organisation_id=org_id,
        actor_user_id=None,
        actor_role=None,
        outcome=AuditOutcome.SUCCESS,
        summary="Provider webhook received (sandbox/manual processing)",
    )
    return row


def admin_stats(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_REPORTS)
    org = ctx.organisation_id
    identities = session.scalar(
        select(func.count()).select_from(DigitalIdentityRecord).where(DigitalIdentityRecord.organisation_id == org)
    ) or 0
    verified = (
        session.scalar(
            select(func.count()).select_from(DigitalIdentityRecord).where(
                DigitalIdentityRecord.organisation_id == org,
                DigitalIdentityRecord.verification_status == "verified",
            )
        )
        or 0
    )
    pending_sigs = (
        session.scalar(
            select(func.count()).select_from(EsignSigningRequest).where(
                EsignSigningRequest.organisation_id == org,
                EsignSigningRequest.status == "pending",
            )
        )
        or 0
    )
    completed = (
        session.scalar(
            select(func.count()).select_from(EsignSigningRequest).where(
                EsignSigningRequest.organisation_id == org,
                EsignSigningRequest.status == "completed",
            )
        )
        or 0
    )
    return {
        "identity_records": int(identities),
        "identity_verified": int(verified),
        "signing_pending": int(pending_sigs),
        "signing_completed": int(completed),
    }


def _notify_user(session: Session, org_id: UUID, user_id: UUID | None, subject: str) -> None:
    if user_id is None:
        return
    provider = get_notification_provider()
    provider.send(
        session,
        ReminderMessage(
            organisation_id=str(org_id),
            recipient_user_id=str(user_id),
            subject=subject,
            body="Open HMore for document or identity details.",
            channel="in_app",
            target_type="digital_id_esign",
            target_id=subject[:40],
            idempotency_key=f"die:{user_id}:{subject}:{date.today().isoformat()}",
            essential_operational=True,
        ),
    )
