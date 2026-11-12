"""F6.6 Optional Finance & Budgets — ledger records and budgets (no payment gateway)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class FinanceRecord(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Authorised financial ledger entry. Optional link to rent_records — does not duplicate rent."""

    __tablename__ = "finance_records"
    __table_args__ = (
        Index("ix_finance_records_org_date", "organisation_id", "effective_date"),
        Index("ix_finance_records_org_type", "organisation_id", "record_type"),
        Index("ix_finance_records_org_status", "organisation_id", "status"),
        CheckConstraint(
            "record_type IN ('income', 'expense', 'other')",
            name="ck_finance_records_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'posted', 'voided')",
            name="ck_finance_records_status",
        ),
        CheckConstraint("amount >= 0", name="ck_finance_records_amount"),
    )

    record_type: Mapped[str] = mapped_column(String(16), nullable=False)
    category_code: Mapped[str] = mapped_column(String(64), nullable=False)
    category_label: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP", server_default="GBP")
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", server_default="draft")
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True
    )
    rent_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rent_records.id", ondelete="SET NULL"), nullable=True
    )
    supporting_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="SET NULL"), nullable=True
    )
    history_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class FinanceBudget(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Budget period with planned amounts (actuals computed from finance_records)."""

    __tablename__ = "finance_budgets"
    __table_args__ = (
        Index("ix_finance_budgets_org_period", "organisation_id", "period_start", "period_end"),
        CheckConstraint(
            "status IN ('draft', 'active', 'closed')",
            name="ck_finance_budgets_status",
        ),
        CheckConstraint("period_end >= period_start", name="ck_finance_budgets_period"),
        UniqueConstraint(
            "organisation_id",
            "name",
            "period_start",
            "period_end",
            name="uq_finance_budgets_org_name_period",
        ),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP", server_default="GBP")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", server_default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class FinanceBudgetLine(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "finance_budget_lines"
    __table_args__ = (
        UniqueConstraint("budget_id", "category_code", name="uq_finance_budget_lines_cat"),
        CheckConstraint("planned_amount >= 0", name="ck_finance_budget_lines_planned"),
    )

    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("finance_budgets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_code: Mapped[str] = mapped_column(String(64), nullable=False)
    category_label: Mapped[str] = mapped_column(String(120), nullable=False)
    planned_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
