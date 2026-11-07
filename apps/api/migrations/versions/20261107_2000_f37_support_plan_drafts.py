"""F3.7 support-plan drafts. Operational plans change only on apply.

Revision ID: 20261107_2000_f37
Revises: 20261107_1800_f36
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261107_2000_f37"
down_revision: Union[str, None] = "20261107_1800_f36"
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
        "support_plan_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("content_origin", sa.String(32), nullable=False, server_default="ai"),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_refs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_id", sa.String(100), nullable=False, server_default="support_plan_draft"),
        sa.Column("feature_id", sa.String(100), nullable=False, server_default="ai.agent.support_planning"),
        sa.Column("prompt_id", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model_id", sa.String(128), nullable=True),
        sa.Column("generation_method", sa.String(32), nullable=False, server_default="structured_heuristic"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("edited_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("applied_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("application_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["tenant_support_plans.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "organisation_id",
            "tenant_id",
            "version_number",
            name="uq_support_plan_drafts_org_tenant_version",
        ),
        sa.CheckConstraint(
            "status IN ('draft','pending_review','approved','rejected','applied')",
            name="ck_support_plan_drafts_status",
        ),
        sa.CheckConstraint(
            "content_origin IN ('ai','human_edited')",
            name="ck_support_plan_drafts_origin",
        ),
    )
    op.create_index("ix_support_plan_drafts_org_status", "support_plan_drafts", ["organisation_id", "status"])
    _enable_rls("support_plan_drafts")


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON support_plan_drafts"))
    op.drop_index("ix_support_plan_drafts_org_status", table_name="support_plan_drafts")
    op.drop_table("support_plan_drafts")
