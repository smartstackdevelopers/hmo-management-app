"""F8.3 optional rent & tenancy payments — extends F6.1 rent_records."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrganisationRentPaymentSettings(Base):
    __tablename__ = "organisation_rent_payment_settings"
    __table_args__ = (
        UniqueConstraint("organisation_id", name="uq_rent_payment_settings_org"),
        CheckConstraint(
            "gateway_provider IN ('test', 'stripe', 'pending_approval')",
            name="ck_rent_payment_gateway_provider",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    privacy_review_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    gateway_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="test")
    gateway_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reminder_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    organisation_receipt_header: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RentObligationExtension(Base):
    __tablename__ = "rent_obligation_extensions"
    __table_args__ = (
        UniqueConstraint("rent_record_id", name="uq_rent_obligation_extension_record"),
        CheckConstraint(
            "payment_frequency IN ('monthly', 'weekly', 'custom')",
            name="ck_rent_obligation_frequency",
        ),
        CheckConstraint(
            "payment_status IN ('pending', 'due', 'partially_paid', 'paid', 'overdue', 'disputed', 'cancelled')",
            name="ck_rent_obligation_payment_status",
        ),
        Index("ix_rent_obligation_org_status", "organisation_id", "payment_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    rent_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rent_records.id", ondelete="CASCADE"), nullable=False
    )
    payment_frequency: Mapped[str] = mapped_column(String(32), nullable=False, default="monthly")
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    outstanding_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RentPayment(Base):
    __tablename__ = "rent_payments"
    __table_args__ = (
        UniqueConstraint("organisation_id", "payment_reference", name="uq_rent_payments_org_ref"),
        CheckConstraint(
            "payment_method IN ('bank_transfer', 'direct_debit', 'card', 'cash', 'other')",
            name="ck_rent_payments_method",
        ),
        CheckConstraint("source IN ('manual', 'gateway')", name="ck_rent_payments_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    rent_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rent_records.id", ondelete="CASCADE"), nullable=False
    )
    payment_reference: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gateway_transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    supporting_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RentPaymentDispute(Base):
    __tablename__ = "rent_payment_disputes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'under_review', 'resolved', 'closed')",
            name="ck_rent_payment_disputes_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    rent_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rent_records.id", ondelete="CASCADE"), nullable=False
    )
    raised_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RentArrearsPlan(Base):
    __tablename__ = "rent_arrears_plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="ck_rent_arrears_plans_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True
    )
    total_agreed: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    staff_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RentArrearsInstalment(Base):
    __tablename__ = "rent_arrears_instalments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('due', 'partially_paid', 'paid', 'missed')",
            name="ck_rent_arrears_instalment_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rent_arrears_plans.id", ondelete="CASCADE"), nullable=False
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="due")


class RentPaymentCheckoutSession(Base):
    __tablename__ = "rent_payment_checkout_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('created', 'completed', 'expired', 'failed', 'cancelled')",
            name="ck_rent_checkout_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    rent_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rent_records.id", ondelete="CASCADE"), nullable=False
    )
    tenant_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="test")
    provider_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RentPaymentWebhookEvent(Base):
    __tablename__ = "rent_payment_webhook_events"
    __table_args__ = (
        UniqueConstraint("organisation_id", "provider", "provider_event_id", name="uq_rent_webhook_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RentPaymentReceipt(Base):
    __tablename__ = "rent_payment_receipts"
    __table_args__ = (UniqueConstraint("organisation_id", "receipt_number", name="uq_rent_receipt_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    rent_payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rent_payments.id", ondelete="CASCADE"), nullable=False
    )
    receipt_number: Mapped[str] = mapped_column(String(32), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
