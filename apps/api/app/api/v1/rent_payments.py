"""F8.3 optional rent & tenancy payments API."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.rent_payments import access, service
from app.rent_payments.providers import verify_webhook_signature
from app.rent_payments.service import _settings
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context
from app.core.config import get_settings

router = APIRouter(prefix="/rent-payments", tags=["rent-payments"])


class SettingsBody(BaseModel):
    enabled: bool | None = None
    privacy_review_complete: bool | None = None
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    gateway_provider: str | None = None
    gateway_enabled: bool | None = None
    reminder_config: dict[str, Any] | None = None
    organisation_receipt_header: str | None = None


class RecordPaymentBody(BaseModel):
    rent_record_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    payment_method: str
    payment_date: date
    payment_reference: str | None = None
    notes: str | None = None
    verify_immediately: bool = False
    supporting_file_id: uuid.UUID | None = None


class DisputeBody(BaseModel):
    rent_record_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=4000)


class InstalmentBody(BaseModel):
    due_date: date
    amount: Decimal = Field(gt=0)


class ArrearsPlanBody(BaseModel):
    tenant_id: uuid.UUID
    property_id: uuid.UUID | None = None
    total_agreed: Decimal = Field(gt=0)
    currency: str = "GBP"
    instalments: list[InstalmentBody]
    staff_notes: str | None = None


class CheckoutBody(BaseModel):
    rent_record_id: uuid.UUID


class WebhookBody(BaseModel):
    organisation_id: uuid.UUID
    provider: str = "test"
    provider_event_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("/settings")
def get_settings_api(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.RENT_PAYMENTS_READ)
    return service.settings_dict(_settings(session, ctx.organisation_id))


@router.patch("/settings")
def patch_settings(
    body: SettingsBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.RENT_PAYMENTS_MANAGE)
    return service.update_settings(session, ctx, body.model_dump(exclude_unset=True))


@router.get("/dashboard")
def dashboard(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    access.require_read(ctx)
    return service.landlord_dashboard(session, ctx)


@router.get("/obligations")
def list_obligations(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
    tenant_id: uuid.UUID | None = None,
    property_id: uuid.UUID | None = None,
    payment_status: str | None = None,
) -> list[dict[str, Any]]:
    access.require_read(ctx)
    return service.list_obligations(
        session, ctx, tenant_id=tenant_id, property_id=property_id, payment_status=payment_status
    )


@router.post("/sync")
def sync_obligations(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.RENT_PAYMENTS_MANAGE)
    count = service.sync_obligations(session, ctx.organisation_id)
    return {"synced": count}


@router.post("/payments")
def record_payment(
    body: RecordPaymentBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    access.require_record(ctx)
    pay = service.record_payment(
        session,
        ctx,
        rent_record_id=body.rent_record_id,
        amount=body.amount,
        payment_method=body.payment_method,
        payment_date=body.payment_date,
        payment_reference=body.payment_reference,
        notes=body.notes,
        verify_immediately=body.verify_immediately,
        supporting_file_id=body.supporting_file_id,
    )
    return {
        "id": str(pay.id),
        "payment_reference": pay.payment_reference,
        "verified": pay.verified,
        "source": pay.source,
    }


@router.post("/payments/{payment_id}/verify")
def verify_payment(
    payment_id: uuid.UUID,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    pay = service.verify_payment(session, ctx, payment_id)
    return {"id": str(pay.id), "verified": pay.verified}


@router.get("/receipts/{receipt_id}/pdf")
def receipt_pdf(
    receipt_id: uuid.UUID,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> Response:
    access.require_read(ctx)
    pdf = service.receipt_pdf(session, ctx, receipt_id)
    return Response(content=pdf, media_type="application/pdf")


@router.post("/checkout-sessions")
def checkout(
    body: CheckoutBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    return service.create_checkout_session(session, ctx, body.rent_record_id)


@router.post("/disputes")
def dispute(
    body: DisputeBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    d = service.raise_dispute(session, ctx, body.rent_record_id, body.reason)
    return {"id": str(d.id), "status": d.status}


@router.post("/arrears-plans")
def arrears_plan(
    body: ArrearsPlanBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    plan = service.create_arrears_plan(
        session,
        ctx,
        tenant_id=body.tenant_id,
        property_id=body.property_id,
        total_agreed=body.total_agreed,
        currency=body.currency,
        instalments=[(i.due_date, i.amount) for i in body.instalments],
        staff_notes=body.staff_notes,
    )
    return {"id": str(plan.id), "status": plan.status}


@router.get("/reports/summary")
def reports_summary(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.RENT_PAYMENTS_REPORTS)
    dash = service.landlord_dashboard(session, ctx)
    return {"collection_summary": dash, "exports": ["csv", "pdf", "xlsx"], "note": "Use finance exports pattern for full extract."}


@router.post("/webhooks/provider")
def provider_webhook(
    body: WebhookBody,
    session: Session = Depends(get_session),
    x_webhook_signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
) -> dict[str, Any]:
    settings = get_settings()
    import json

    raw = json.dumps(body.model_dump(), sort_keys=True).encode()
    try:
        verify_webhook_signature(raw, x_webhook_signature, settings)
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return service.process_webhook(
        session,
        organisation_id=body.organisation_id,
        provider=body.provider,
        provider_event_id=body.provider_event_id,
        event_type=body.event_type,
        payload=body.payload,
    )
