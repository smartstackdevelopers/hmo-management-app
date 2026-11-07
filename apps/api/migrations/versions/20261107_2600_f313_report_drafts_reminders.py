"""F3.13 operational report drafts and overdue reminder scan.

Revision ID: 20261107_2600_f313
Revises: 20261107_2500_f311
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261107_2600_f313"
down_revision: Union[str, None] = "20261107_2500_f311"
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


def upgrade() -> None:
    op.create_table(
        "operational_report_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_type", sa.String(16), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone_name", sa.String(64), nullable=False, server_default="Europe/London"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("narrative_text", sa.Text(), nullable=True),
        sa.Column("edited_body", sa.Text(), nullable=True),
        sa.Column("ai_status", sa.String(32), nullable=False, server_default="skipped"),
        sa.Column(
            "ai_notice",
            sa.String(255),
            nullable=False,
            server_default="AI-GENERATED DRAFT — REQUIRES HUMAN REVIEW",
        ),
        sa.Column("distributed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("period_type IN ('weekly','monthly')", name="ck_report_drafts_period_type"),
        sa.CheckConstraint(
            "status IN ('draft','approved','rejected')",
            name="ck_report_drafts_status",
        ),
        sa.CheckConstraint(
            "ai_status IN ('generated','skipped','failed','unavailable','cap_reached')",
            name="ck_report_drafts_ai_status",
        ),
        sa.CheckConstraint("distributed = false", name="ck_report_drafts_no_auto_distribute"),
        sa.CheckConstraint("period_end > period_start", name="ck_report_drafts_period_order"),
        sa.UniqueConstraint(
            "organisation_id",
            "period_type",
            "period_start",
            "period_end",
            "version",
            name="uq_operational_report_drafts_period_version",
        ),
    )
    op.create_index(
        "ix_operational_report_drafts_org_period",
        "operational_report_drafts",
        ["organisation_id", "period_start"],
    )
    op.create_index(
        "ix_operational_report_drafts_org_status",
        "operational_report_drafts",
        ["organisation_id", "status"],
    )
    op.execute(sa.text("ALTER TABLE operational_report_drafts ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE operational_report_drafts FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_policy("operational_report_drafts")))


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON operational_report_drafts"))
    op.drop_table("operational_report_drafts")
