"""F8.3 optional rent & tenancy payments add-on.

Revision ID: 20261115_5100_f83
Revises: 20261114_5000_f82
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261115_5100_f83"
down_revision: Union[str, None] = "20261114_5000_f82"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _policy(table: str) -> str:
    return f"""
    CREATE POLICY hmore_org_isolation ON {table}
      FOR ALL
      USING (
        current_setting('app.rls_bypass', true) = 'on'
        OR organisation_id::text = NULLIF(current_setting('app.organisation_id', true), '')
      )
      WITH CHECK (
        current_setting('app.rls_bypass', true) = 'on'
        OR organisation_id::text = NULLIF(current_setting('app.organisation_id', true), '')
      );
    """


def _enable_rls(table: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_policy(table)))


def upgrade() -> None:
    op.create_table(
        "organisation_rent_payment_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("privacy_review_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("default_currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("gateway_provider", sa.String(32), nullable=False, server_default="test"),
        sa.Column("gateway_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reminder_config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("organisation_receipt_header", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", name="uq_rent_payment_settings_org"),
        sa.CheckConstraint(
            "gateway_provider IN ('test', 'stripe', 'pending_approval')",
            name="ck_rent_payment_gateway_provider",
        ),
    )
    op.create_table(
        "rent_obligation_extensions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rent_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_frequency", sa.String(32), nullable=False, server_default="monthly"),
        sa.Column("payment_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("outstanding_balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rent_record_id"], ["rent_records.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("rent_record_id", name="uq_rent_obligation_extension_record"),
        sa.CheckConstraint(
            "payment_frequency IN ('monthly', 'weekly', 'custom')",
            name="ck_rent_obligation_frequency",
        ),
        sa.CheckConstraint(
            "payment_status IN ('pending', 'due', 'partially_paid', 'paid', 'overdue', 'disputed', 'cancelled')",
            name="ck_rent_obligation_payment_status",
        ),
    )
    op.create_index("ix_rent_obligation_org_status", "rent_obligation_extensions", ["organisation_id", "payment_status"])
    op.create_table(
        "rent_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rent_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_reference", sa.String(64), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(32), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("gateway_transaction_id", sa.String(128), nullable=True),
        sa.Column("supporting_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rent_record_id"], ["rent_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supporting_file_id"], ["file_metadata.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "payment_reference", name="uq_rent_payments_org_ref"),
        sa.CheckConstraint(
            "payment_method IN ('bank_transfer', 'direct_debit', 'card', 'cash', 'other')",
            name="ck_rent_payments_method",
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'gateway')",
            name="ck_rent_payments_source",
        ),
    )
    op.create_table(
        "rent_payment_disputes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rent_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raised_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rent_record_id"], ["rent_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raised_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "status IN ('open', 'under_review', 'resolved', 'closed')",
            name="ck_rent_payment_disputes_status",
        ),
    )
    op.create_table(
        "rent_arrears_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("total_agreed", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("staff_notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="ck_rent_arrears_plans_status",
        ),
    )
    op.create_table(
        "rent_arrears_instalments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="due"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["rent_arrears_plans.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('due', 'partially_paid', 'paid', 'missed')",
            name="ck_rent_arrears_instalment_status",
        ),
    )
    op.create_table(
        "rent_payment_checkout_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rent_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="test"),
        sa.Column("provider_session_id", sa.String(128), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="created"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rent_record_id"], ["rent_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('created', 'completed', 'expired', 'failed', 'cancelled')",
            name="ck_rent_checkout_status",
        ),
    )
    op.create_table(
        "rent_payment_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_event_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", "provider", "provider_event_id", name="uq_rent_webhook_event"),
    )
    op.create_table(
        "rent_payment_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rent_payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_number", sa.String(32), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rent_payment_id"], ["rent_payments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", "receipt_number", name="uq_rent_receipt_number"),
    )
    for table in (
        "organisation_rent_payment_settings",
        "rent_obligation_extensions",
        "rent_payments",
        "rent_payment_disputes",
        "rent_arrears_plans",
        "rent_arrears_instalments",
        "rent_payment_checkout_sessions",
        "rent_payment_webhook_events",
        "rent_payment_receipts",
    ):
        _enable_rls(table)


def downgrade() -> None:
    op.drop_table("rent_payment_receipts")
    op.drop_table("rent_payment_webhook_events")
    op.drop_table("rent_payment_checkout_sessions")
    op.drop_table("rent_arrears_instalments")
    op.drop_table("rent_arrears_plans")
    op.drop_table("rent_payment_disputes")
    op.drop_table("rent_payments")
    op.drop_table("rent_obligation_extensions")
    op.drop_table("organisation_rent_payment_settings")
