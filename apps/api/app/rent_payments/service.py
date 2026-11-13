"""F8.3 rent & tenancy payments — extends rent_records (F6.1)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.enums import HMoreRole
from app.db.models.landlord_enterprise import RentRecord
from app.db.models.organisation import Organisation
from app.db.models.rent_payments import (
    OrganisationRentPaymentSettings,
    RentArrearsInstalment,
    RentArrearsPlan,
    RentObligationExtension,
    RentPayment,
    RentPaymentCheckoutSession,
    RentPaymentDispute,
    RentPaymentReceipt,
    RentPaymentWebhookEvent,
)
from app.evidence.pdf import build_simple_pdf
from app.ops.notifications import ReminderMessage, get_notification_provider
from app.rent_payments import access, providers
from app.rent_payments.constants import ADDON_DISCLAIMER, PAYMENT_METHODS, PAYMENT_STATUSES
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _settings(session: Session, org_id: UUID) -> OrganisationRentPaymentSettings:
    row = session.scalars(
        select(OrganisationRentPaymentSettings).where(OrganisationRentPaymentSettings.organisation_id == org_id)
    ).first()
    if row is None:
        row = OrganisationRentPaymentSettings(organisation_id=org_id)
        session.add(row)
        session.flush()
    return row


def assert_addon(session: Session, settings: Settings, org_id: UUID) -> OrganisationRentPaymentSettings:
    if not settings.rent_payments_global_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Rent payments add-on is not enabled platform-wide")
    row = _settings(session, org_id)
    if not row.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Rent payments disabled for organisation")
    return row


def settings_dict(row: OrganisationRentPaymentSettings) -> dict[str, Any]:
    return {
        "organisation_id": str(row.organisation_id),
        "enabled": row.enabled,
        "privacy_review_complete": row.privacy_review_complete,
        "default_currency": row.default_currency,
        "gateway_provider": row.gateway_provider,
        "gateway_enabled": row.gateway_enabled,
        "reminder_config": row.reminder_config,
        "organisation_receipt_header": row.organisation_receipt_header,
        "disclaimer": ADDON_DISCLAIMER,
    }


def update_settings(session: Session, ctx: OrganisationContext, payload: dict[str, Any]) -> dict[str, Any]:
    row = _settings(session, ctx.organisation_id)
    for key in (
        "enabled",
        "privacy_review_complete",
        "default_currency",
        "gateway_provider",
        "gateway_enabled",
        "reminder_config",
        "organisation_receipt_header",
    ):
        if key in payload and payload[key] is not None:
            setattr(row, key, payload[key])
    if row.gateway_provider == "stripe" and not get_settings().rent_stripe_secret_key:
        row.gateway_provider = "pending_approval"
        row.gateway_enabled = False
    session.flush()
    record_event(
        session,
        action=audit_events.RENT_PAYMENTS_SETTINGS_UPDATE,
        resource_type="rent_payment_settings",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Rent payment settings updated",
    )
    return settings_dict(row)


def get_or_create_extension(session: Session, record: RentRecord) -> RentObligationExtension:
    ext = session.scalar(
        select(RentObligationExtension).where(RentObligationExtension.rent_record_id == record.id)
    )
    if ext is None:
        ext = RentObligationExtension(
            organisation_id=record.organisation_id,
            rent_record_id=record.id,
            outstanding_balance=record.amount,
        )
        session.add(ext)
        session.flush()
    return ext


def recompute_obligation(session: Session, record: RentRecord) -> RentObligationExtension:
    ext = get_or_create_extension(session, record)
    verified_paid = session.scalar(
        select(func.coalesce(func.sum(RentPayment.amount), 0)).where(
            RentPayment.rent_record_id == record.id,
            RentPayment.verified.is_(True),
        )
    ) or Decimal("0")
    ext.amount_paid = Decimal(str(verified_paid))
    ext.outstanding_balance = max(Decimal("0"), record.amount - ext.amount_paid)
    open_dispute = session.scalar(
        select(func.count())
        .select_from(RentPaymentDispute)
        .where(
            RentPaymentDispute.rent_record_id == record.id,
            RentPaymentDispute.status.in_(("open", "under_review")),
        )
    )
    if record.status == "cancelled" or record.is_archived:
        ext.payment_status = "cancelled"
    elif open_dispute:
        ext.payment_status = "disputed"
    elif ext.amount_paid >= record.amount and ext.amount_paid > 0:
        ext.payment_status = "paid"
    elif ext.amount_paid > 0:
        ext.payment_status = "partially_paid"
    elif record.due_date and record.due_date < date.today():
        ext.payment_status = "overdue"
    elif record.due_date and record.due_date <= date.today():
        ext.payment_status = "due"
    else:
        ext.payment_status = "pending"
    session.flush()
    return ext


def obligation_view(session: Session, record: RentRecord, ext: RentObligationExtension) -> dict[str, Any]:
    return {
        "rent_record_id": str(record.id),
        "property_id": str(record.property_id),
        "tenant_id": str(record.tenant_id) if record.tenant_id else None,
        "tenancy_reference": record.tenancy_reference,
        "rent_amount": str(record.amount),
        "currency": record.currency,
        "due_date": record.due_date.isoformat() if record.due_date else None,
        "period_start": record.period_start.isoformat(),
        "period_end": record.period_end.isoformat(),
        "payment_frequency": ext.payment_frequency,
        "payment_status": ext.payment_status,
        "amount_paid": str(ext.amount_paid),
        "outstanding_balance": str(ext.outstanding_balance),
        "legacy_ledger_status": record.status,
        "created_at": record.created_at.isoformat(),
        "updated_at": ext.updated_at.isoformat(),
    }


def sync_obligations(session: Session, org_id: UUID) -> int:
    rows = session.scalars(
        select(RentRecord).where(
            RentRecord.organisation_id == org_id,
            RentRecord.is_archived.is_(False),
        )
    ).all()
    for row in rows:
        recompute_obligation(session, row)
    return len(rows)


def _next_payment_ref(session: Session, org_id: UUID) -> str:
    year = _now().year
    prefix = f"RPAY-{year}-"
    n = (
        session.scalar(
            select(func.count())
            .select_from(RentPayment)
            .where(RentPayment.organisation_id == org_id, RentPayment.payment_reference.like(f"{prefix}%"))
        )
        or 0
    )
    return f"{prefix}{n + 1:06d}"


def record_payment(
    session: Session,
    ctx: OrganisationContext,
    *,
    rent_record_id: UUID,
    amount: Decimal,
    payment_method: str,
    payment_date: date,
    payment_reference: str | None,
    notes: str | None,
    verify_immediately: bool,
    supporting_file_id: UUID | None,
) -> RentPayment:
    assert_addon(session, get_settings(), ctx.organisation_id)
    if payment_method not in PAYMENT_METHODS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid payment method")
    record = session.get(RentRecord, rent_record_id)
    if record is None or record.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Rent record not found")
    access.assert_rent_record_visible(session, ctx, record)
    ref = payment_reference or _next_payment_ref(session, ctx.organisation_id)
    dup = session.scalar(
        select(RentPayment).where(
            RentPayment.organisation_id == ctx.organisation_id,
            RentPayment.payment_reference == ref,
        )
    )
    if dup is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Duplicate payment reference")
    if amount <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Amount must be positive")
    payment = RentPayment(
        organisation_id=ctx.organisation_id,
        rent_record_id=record.id,
        payment_reference=ref,
        amount=amount,
        currency=record.currency,
        payment_date=payment_date,
        payment_method=payment_method,
        source="manual",
        verified=bool(verify_immediately),
        notes=notes,
        supporting_file_id=supporting_file_id,
        recorded_by_user_id=ctx.user_id,
    )
    session.add(payment)
    session.flush()
    recompute_obligation(session, record)
    if payment.verified:
        issue_receipt(session, ctx, payment)
    record_event(
        session,
        action=audit_events.RENT_PAYMENT_RECORDED,
        resource_type="rent_payment",
        resource_id=str(payment.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Rent payment recorded",
        metadata={"verified": payment.verified, "source": payment.source},
    )
    _notify_payment_event(session, ctx.organisation_id, record, "payment_recorded")
    return payment


def verify_payment(session: Session, ctx: OrganisationContext, payment_id: UUID) -> RentPayment:
    access.require_manage(ctx)
    payment = session.get(RentPayment, payment_id)
    if payment is None or payment.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.verified:
        return payment
    payment.verified = True
    session.flush()
    record = session.get(RentRecord, payment.rent_record_id)
    if record:
        recompute_obligation(session, record)
        issue_receipt(session, ctx, payment)
        _notify_payment_event(session, ctx.organisation_id, record, "payment_verified")
    record_event(
        session,
        action=audit_events.RENT_PAYMENT_VERIFIED,
        resource_type="rent_payment",
        resource_id=str(payment.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Rent payment verified",
    )
    return payment


def issue_receipt(session: Session, ctx: OrganisationContext, payment: RentPayment) -> RentPaymentReceipt:
    existing = session.scalar(
        select(RentPaymentReceipt).where(RentPaymentReceipt.rent_payment_id == payment.id)
    )
    if existing:
        return existing
    year = _now().year
    n = (
        session.scalar(
            select(func.count()).select_from(RentPaymentReceipt).where(
                RentPaymentReceipt.organisation_id == ctx.organisation_id,
                RentPaymentReceipt.receipt_number.like(f"RCPT-{year}-%"),
            )
        )
        or 0
    )
    receipt = RentPaymentReceipt(
        organisation_id=ctx.organisation_id,
        rent_payment_id=payment.id,
        receipt_number=f"RCPT-{year}-{n + 1:06d}",
    )
    session.add(receipt)
    session.flush()
    record_event(
        session,
        action=audit_events.RENT_PAYMENT_RECEIPT_ISSUED,
        resource_type="rent_payment_receipt",
        resource_id=str(receipt.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Rent payment receipt issued",
    )
    return receipt


def receipt_pdf(session: Session, ctx: OrganisationContext, receipt_id: UUID) -> bytes:
    receipt = session.get(RentPaymentReceipt, receipt_id)
    if receipt is None or receipt.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    payment = session.get(RentPayment, receipt.rent_payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Payment not found")
    record = session.get(RentRecord, payment.rent_record_id)
    if record:
        access.assert_rent_record_visible(session, ctx, record)
    if not payment.verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Receipt only for verified payments")
    org = session.get(Organisation, ctx.organisation_id)
    settings = _settings(session, ctx.organisation_id)
    header = settings.organisation_receipt_header or (org.name if org else "Organisation")
    ext = get_or_create_extension(session, record) if record else None
    lines = [
        f"Receipt: {receipt.receipt_number}",
        f"Payment reference: {payment.payment_reference}",
        f"Amount: {payment.amount} {payment.currency}",
        f"Date: {payment.payment_date.isoformat()}",
        f"Method: {payment.payment_method} ({payment.source})",
        f"Organisation: {header}",
    ]
    if record and ext:
        lines.append(f"Outstanding after payment: {ext.outstanding_balance} {payment.currency}")
    lines.append("This receipt reflects a verified or authorised recorded payment.")
    return build_simple_pdf("Rent payment receipt", lines)


def landlord_dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    access.require_read(ctx)
    sync_obligations(session, ctx.organisation_id)
    exts = session.scalars(
        select(RentObligationExtension).where(RentObligationExtension.organisation_id == ctx.organisation_id)
    ).all()
    total_due = Decimal("0")
    total_received = Decimal("0")
    outstanding = Decimal("0")
    status_counts = {s: 0 for s in PAYMENT_STATUSES}
    for ext in exts:
        status_counts[ext.payment_status] = status_counts.get(ext.payment_status, 0) + 1
        total_received += ext.amount_paid
        outstanding += ext.outstanding_balance
        rec = session.get(RentRecord, ext.rent_record_id)
        if rec:
            total_due += rec.amount
    return {
        "total_rent_due": str(total_due),
        "total_rent_received": str(total_received),
        "outstanding_rent": str(outstanding),
        "overdue_count": status_counts.get("overdue", 0),
        "partially_paid_count": status_counts.get("partially_paid", 0),
        "by_status": status_counts,
        "disclaimer": ADDON_DISCLAIMER,
    }


def list_obligations(
    session: Session,
    ctx: OrganisationContext,
    *,
    tenant_id: UUID | None = None,
    property_id: UUID | None = None,
    payment_status: str | None = None,
) -> list[dict[str, Any]]:
    access.require_read(ctx)
    q = select(RentRecord).where(
        RentRecord.organisation_id == ctx.organisation_id,
        RentRecord.is_archived.is_(False),
    )
    if ctx.role == HMoreRole.TENANT:
        tenant_id = access.resolve_own_tenant(session, ctx)
    if tenant_id:
        q = q.where(RentRecord.tenant_id == tenant_id)
    if property_id:
        q = q.where(RentRecord.property_id == property_id)
    records = session.scalars(q.order_by(RentRecord.due_date.desc())).all()
    out: list[dict[str, Any]] = []
    for rec in records:
        access.assert_rent_record_visible(session, ctx, rec)
        ext = recompute_obligation(session, rec)
        if payment_status and ext.payment_status != payment_status:
            continue
        out.append(obligation_view(session, rec, ext))
    return out


def create_checkout_session(
    session: Session,
    ctx: OrganisationContext,
    rent_record_id: UUID,
) -> dict[str, Any]:
    assert_addon(session, get_settings(), ctx.organisation_id)
    require_pay = Permission.RENT_PAYMENTS_PAY_OWN
    from app.rbac.service import require_permission

    require_permission(ctx.authorization, require_pay)
    record = session.get(RentRecord, rent_record_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Rent record not found")
    access.assert_rent_record_visible(session, ctx, record)
    settings = _settings(session, ctx.organisation_id)
    if not settings.gateway_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Payment gateway not enabled")
    ext = recompute_obligation(session, record)
    amount = ext.outstanding_balance
    if amount <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No outstanding balance")
    provider = settings.gateway_provider if settings.gateway_provider != "pending_approval" else "test"
    checkout = providers.create_checkout_session(
        amount=amount,
        currency=record.currency,
        provider=provider,
        settings=get_settings(),
    )
    row = RentPaymentCheckoutSession(
        organisation_id=ctx.organisation_id,
        rent_record_id=record.id,
        tenant_user_id=ctx.user_id,
        provider=provider,
        provider_session_id=checkout.provider_session_id,
        amount=amount,
        currency=record.currency,
        expires_at=_now() + timedelta(hours=1),
    )
    session.add(row)
    session.flush()
    return {
        "session_id": str(row.id),
        "provider_session_id": checkout.provider_session_id,
        "checkout_url": checkout.checkout_url,
        "mode": checkout.mode,
        "amount": str(amount),
        "currency": record.currency,
    }


def process_webhook(
    session: Session,
    *,
    organisation_id: UUID,
    provider: str,
    provider_event_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    assert_addon(session, get_settings(), organisation_id)
    existing = session.scalar(
        select(RentPaymentWebhookEvent).where(
            RentPaymentWebhookEvent.organisation_id == organisation_id,
            RentPaymentWebhookEvent.provider == provider,
            RentPaymentWebhookEvent.provider_event_id == provider_event_id,
        )
    )
    if existing and existing.processed:
        return {"status": "duplicate"}
    if existing is None:
        existing = RentPaymentWebhookEvent(
            organisation_id=organisation_id,
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            payload=payload,
        )
        session.add(existing)
        session.flush()
    if event_type in {"checkout.session.completed", "payment_intent.succeeded", "test.payment.succeeded"}:
        session_id = payload.get("checkout_session_id") or payload.get("provider_session_id")
        checkout = session.scalar(
            select(RentPaymentCheckoutSession).where(
                RentPaymentCheckoutSession.organisation_id == organisation_id,
                RentPaymentCheckoutSession.provider_session_id == str(session_id),
            )
        )
        if checkout:
            ref = f"GW-{provider_event_id[:40]}"
            pay = RentPayment(
                organisation_id=organisation_id,
                rent_record_id=checkout.rent_record_id,
                payment_reference=ref,
                amount=checkout.amount,
                currency=checkout.currency,
                payment_date=date.today(),
                payment_method="card",
                source="gateway",
                verified=True,
                gateway_transaction_id=provider_event_id,
            )
            session.add(pay)
            checkout.status = "completed"
            record = session.get(RentRecord, checkout.rent_record_id)
            if record:
                recompute_obligation(session, record)
    existing.processed = True
    session.flush()
    record_event(
        session,
        action=audit_events.RENT_PAYMENT_WEBHOOK_RECEIVED,
        resource_type="rent_payment_webhook",
        resource_id=str(existing.id),
        organisation_id=organisation_id,
        actor_user_id=None,
        actor_role="system",
        outcome=AuditOutcome.SUCCESS,
        summary="Rent payment webhook processed",
        metadata={"event_type": event_type},
    )
    return {"status": "processed"}


def raise_dispute(
    session: Session,
    ctx: OrganisationContext,
    rent_record_id: UUID,
    reason: str,
) -> RentPaymentDispute:
    record = session.get(RentRecord, rent_record_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Rent record not found")
    access.assert_rent_record_visible(session, ctx, record)
    dispute = RentPaymentDispute(
        organisation_id=ctx.organisation_id,
        rent_record_id=record.id,
        raised_by_user_id=ctx.user_id,
        reason=reason,
    )
    session.add(dispute)
    recompute_obligation(session, record)
    session.flush()
    record_event(
        session,
        action=audit_events.RENT_PAYMENT_DISPUTE_RAISED,
        resource_type="rent_payment_dispute",
        resource_id=str(dispute.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Rent payment dispute raised",
    )
    return dispute


def create_arrears_plan(
    session: Session,
    ctx: OrganisationContext,
    *,
    tenant_id: UUID,
    property_id: UUID | None,
    total_agreed: Decimal,
    currency: str,
    instalments: list[tuple[date, Decimal]],
    staff_notes: str | None,
) -> RentArrearsPlan:
    access.require_manage(ctx)
    plan = RentArrearsPlan(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant_id,
        property_id=property_id,
        total_agreed=total_agreed,
        currency=currency,
        staff_notes=staff_notes,
        created_by_user_id=ctx.user_id,
    )
    session.add(plan)
    session.flush()
    for due, amt in instalments:
        session.add(
            RentArrearsInstalment(
                organisation_id=ctx.organisation_id,
                plan_id=plan.id,
                due_date=due,
                amount=amt,
            )
        )
    session.flush()
    record_event(
        session,
        action=audit_events.RENT_ARREARS_PLAN_CREATED,
        resource_type="rent_arrears_plan",
        resource_id=str(plan.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Rent arrears payment plan recorded",
    )
    return plan


def _notify_payment_event(session: Session, org_id: UUID, record: RentRecord, kind: str) -> None:
    if record.tenant_id is None:
        return
    from app.db.models.tenant import Tenant

    tenant = session.get(Tenant, record.tenant_id)
    if tenant is None or tenant.user_id is None:
        return
    settings = _settings(session, org_id)
    cfg = settings.reminder_config or {}
    if not cfg.get("enabled", True):
        return
    subject_map = {
        "payment_recorded": "Rent payment recorded",
        "payment_verified": "Rent payment confirmed",
        "due_reminder": "Rent payment due soon",
        "overdue_reminder": "Rent payment overdue",
    }
    body = "Please open HMore to view your rent payment details."
    provider = get_notification_provider()
    provider.send(
        session,
        ReminderMessage(
            organisation_id=str(org_id),
            recipient_user_id=str(tenant.user_id),
            subject=subject_map.get(kind, "Rent payment update"),
            body=body,
            channel="in_app",
            target_type="rent_record",
            target_id=str(record.id),
            idempotency_key=f"rent-pay:{record.id}:{kind}:{date.today().isoformat()}",
            essential_operational=True,
        ),
    )


def send_rent_reminders(session: Session, organisation_id: UUID) -> int:
    """Respectful due/overdue reminders — no threats."""
    settings = _settings(session, organisation_id)
    if not settings.enabled:
        return 0
    sent = 0
    records = session.scalars(
        select(RentRecord).where(RentRecord.organisation_id == organisation_id, RentRecord.is_archived.is_(False))
    ).all()
    today = date.today()
    lead = int((settings.reminder_config or {}).get("due_lead_days", 3))
    for rec in records:
        ext = recompute_obligation(session, rec)
        if rec.due_date is None:
            continue
        if ext.payment_status in {"paid", "cancelled"}:
            continue
        if rec.due_date == today + timedelta(days=lead):
            _notify_payment_event(session, organisation_id, rec, "due_reminder")
            sent += 1
        elif ext.payment_status == "overdue":
            _notify_payment_event(session, organisation_id, rec, "overdue_reminder")
            sent += 1
    return sent
