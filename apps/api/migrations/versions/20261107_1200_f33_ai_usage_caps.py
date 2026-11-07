"""F3.3 organisation AI budgets, pricing, usage metering and reservations.

Revision ID: 20261107_1200_f33
Revises: 20261107_0000_f213
Create Date: 2026-11-07 12:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261107_1200_f33"
down_revision: Union[str, None] = "20261107_0000_f213"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORG_TABLES = (
    "organisation_ai_budgets",
    "ai_usage_records",
    "ai_budget_reservations",
)

POLICY_SQL = """
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


def upgrade() -> None:
    op.create_table(
        "organisation_ai_budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("monthly_limit", sa.Numeric(12, 4), nullable=False),
        sa.Column("period_kind", sa.String(16), nullable=False, server_default="calendar_month"),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("warning_threshold_pct", sa.Numeric(5, 2), nullable=False, server_default="80.00"),
        sa.Column("default_reservation_amount", sa.Numeric(12, 4), nullable=False, server_default="0.0500"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("monthly_limit >= 0", name="ck_org_ai_budgets_limit_nonneg"),
        sa.CheckConstraint("warning_threshold_pct >= 0 AND warning_threshold_pct <= 100", name="ck_org_ai_budgets_warn"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_org_ai_budgets_org_active", "organisation_ai_budgets", ["organisation_id", "active"])

    op.create_table(
        "ai_model_pricing",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model_id", sa.String(128), nullable=False),
        sa.Column("pricing_version", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("input_price_per_1k_tokens", sa.Numeric(12, 6), nullable=False),
        sa.Column("output_price_per_1k_tokens", sa.Numeric(12, 6), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("input_price_per_1k_tokens >= 0", name="ck_ai_pricing_input_nonneg"),
        sa.CheckConstraint("output_price_per_1k_tokens >= 0", name="ck_ai_pricing_output_nonneg"),
        sa.UniqueConstraint("provider", "model_id", "pricing_version", name="uq_ai_model_pricing_provider_model_version"),
    )

    op.create_table(
        "ai_usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_id", sa.String(100), nullable=False),
        sa.Column("feature_id", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model_id", sa.String(128), nullable=True),
        sa.Column("prompt_id", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("provider_request_id", sa.String(128), nullable=True),
        sa.Column("batch_job_id", sa.String(64), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=True),
        sa.Column("escalation_occurred", sa.Boolean(), nullable=True),
        sa.Column("escalation_reason", sa.String(128), nullable=True),
        sa.Column("execution_status", sa.String(32), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("cost_amount", sa.Numeric(12, 6), nullable=True),
        sa.Column("cost_status", sa.String(32), nullable=False, server_default="unavailable"),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("pricing_version", sa.String(64), nullable=True),
        sa.Column("period_key", sa.String(7), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("request_id", name="uq_ai_usage_records_request_id"),
        sa.CheckConstraint(
            "execution_status IN ('completed','failed','rejected_budget','cancelled')",
            name="ck_ai_usage_execution_status",
        ),
        sa.CheckConstraint(
            "cost_status IN ('actual','estimated','unavailable')",
            name="ck_ai_usage_cost_status",
        ),
    )
    op.create_index("ix_ai_usage_org_period", "ai_usage_records", ["organisation_id", "period_key"])
    op.create_index("ix_ai_usage_org_feature", "ai_usage_records", ["organisation_id", "feature_id"])

    op.create_table(
        "ai_budget_reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("feature_id", sa.String(100), nullable=False),
        sa.Column("workflow_id", sa.String(100), nullable=False),
        sa.Column("reserved_amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("period_key", sa.String(7), nullable=False),
        sa.Column("reconciled_amount", sa.Numeric(12, 6), nullable=True),
        sa.Column("usage_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usage_record_id"], ["ai_usage_records.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("request_id", name="uq_ai_budget_reservations_request_id"),
        sa.CheckConstraint(
            "status IN ('open','reconciled','released','expired')",
            name="ck_ai_budget_res_status",
        ),
    )
    op.create_index("ix_ai_budget_res_org_status", "ai_budget_reservations", ["organisation_id", "status"])

    for table in ORG_TABLES:
        op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(POLICY_SQL.format(table=table)))


def downgrade() -> None:
    for table in reversed(ORG_TABLES):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
    op.drop_table("ai_budget_reservations")
    op.drop_table("ai_usage_records")
    op.drop_table("ai_model_pricing")
    op.drop_table("organisation_ai_budgets")
