"""F6.6 optional finance & budgets module tables.

Revision ID: 20261111_4400_f66
Revises: 20261111_4300_f65
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261111_4400_f66"
down_revision: Union[str, None] = "20261111_4300_f65"
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
        "finance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_type", sa.String(16), nullable=False),
        sa.Column("category_code", sa.String(64), nullable=False),
        sa.Column("category_label", sa.String(120), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rent_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supporting_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("history_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rent_record_id"], ["rent_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supporting_file_id"], ["file_metadata.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["voided_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint("record_type IN ('income', 'expense', 'other')", name="ck_finance_records_type"),
        sa.CheckConstraint("status IN ('draft', 'posted', 'voided')", name="ck_finance_records_status"),
        sa.CheckConstraint("amount >= 0", name="ck_finance_records_amount"),
    )
    op.create_index("ix_finance_records_org_date", "finance_records", ["organisation_id", "effective_date"])
    op.create_index("ix_finance_records_org_type", "finance_records", ["organisation_id", "record_type"])
    op.create_index("ix_finance_records_org_status", "finance_records", ["organisation_id", "status"])
    _enable_rls("finance_records")

    op.create_table(
        "finance_budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "organisation_id", "name", "period_start", "period_end", name="uq_finance_budgets_org_name_period"
        ),
        sa.CheckConstraint("status IN ('draft', 'active', 'closed')", name="ck_finance_budgets_status"),
        sa.CheckConstraint("period_end >= period_start", name="ck_finance_budgets_period"),
    )
    op.create_index(
        "ix_finance_budgets_org_period", "finance_budgets", ["organisation_id", "period_start", "period_end"]
    )
    _enable_rls("finance_budgets")

    op.create_table(
        "finance_budget_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("budget_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_code", sa.String(64), nullable=False),
        sa.Column("category_label", sa.String(120), nullable=False),
        sa.Column("planned_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["budget_id"], ["finance_budgets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("budget_id", "category_code", name="uq_finance_budget_lines_cat"),
        sa.CheckConstraint("planned_amount >= 0", name="ck_finance_budget_lines_planned"),
    )
    op.create_index("ix_finance_budget_lines_budget", "finance_budget_lines", ["budget_id"])
    _enable_rls("finance_budget_lines")


def downgrade() -> None:
    for table in ("finance_budget_lines", "finance_budgets", "finance_records"):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.drop_table(table)
