"""F3.3 organisation AI budgets, pricing, usage metering and reservations."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class OrganisationAiBudget(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "organisation_ai_budgets"
    __table_args__ = (
        Index("ix_org_ai_budgets_org_active", "organisation_id", "active"),
    )

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    period_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="calendar_month")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    warning_threshold_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("80.00"))
    default_reservation_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0.0500")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AiModelPricing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Operator-configured pricing — never invent unverified market prices in code."""

    __tablename__ = "ai_model_pricing"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "model_id",
            "pricing_version",
            name="uq_ai_model_pricing_provider_model_version",
        ),
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    pricing_version: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    input_price_per_1k_tokens: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    output_price_per_1k_tokens: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AiUsageRecord(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "ai_usage_records"
    __table_args__ = (
        UniqueConstraint("request_id", name="uq_ai_usage_records_request_id"),
        Index("ix_ai_usage_org_period", "organisation_id", "period_key"),
        Index("ix_ai_usage_org_feature", "organisation_id", "feature_id"),
    )

    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_id: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    batch_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(nullable=True)
    cache_hit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    escalation_occurred: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    escalation_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    execution_status: Mapped[str] = mapped_column(String(32), nullable=False)
    # completed | failed | rejected_budget | cancelled
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    cost_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unavailable")
    # actual | estimated | unavailable
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    pricing_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    period_key: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")


class AiBudgetReservation(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "ai_budget_reservations"
    __table_args__ = (
        UniqueConstraint("request_id", name="uq_ai_budget_reservations_request_id"),
        Index("ix_ai_budget_res_org_status", "organisation_id", "status"),
    )

    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    feature_id: Mapped[str] = mapped_column(String(100), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=False)
    reserved_amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    # open | reconciled | released | expired
    period_key: Mapped[str] = mapped_column(String(7), nullable=False)
    reconciled_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    usage_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_usage_records.id", ondelete="SET NULL"), nullable=True
    )
