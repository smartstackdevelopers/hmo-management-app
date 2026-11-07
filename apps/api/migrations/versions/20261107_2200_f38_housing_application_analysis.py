"""F3.8 housing application checklist analysis. No housing decisions.

Revision ID: 20261107_2200_f38
Revises: 20261107_2000_f37
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261107_2200_f38"
down_revision: Union[str, None] = "20261107_2000_f37"
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
        "housing_application_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending_review"),
        sa.Column("checklist_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("gap_narrative", sa.Text(), nullable=False),
        sa.Column("source_refs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_id", sa.String(100), nullable=False, server_default="housing_application_analysis"),
        sa.Column("feature_id", sa.String(100), nullable=False, server_default="ai.agent.housing_application"),
        sa.Column("prompt_id", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model_id", sa.String(128), nullable=True),
        sa.Column("generation_method", sa.String(32), nullable=False, server_default="structured_heuristic"),
        sa.Column("ai_status", sa.String(32), nullable=False, server_default="not_needed"),
        sa.Column("ai_error", sa.String(200), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["application_id"], ["housing_applications.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "organisation_id",
            "application_id",
            "version_number",
            name="uq_housing_application_analyses_org_app_version",
        ),
        sa.CheckConstraint(
            "status IN ('pending_review','reviewed')",
            name="ck_housing_application_analyses_status",
        ),
        sa.CheckConstraint(
            "ai_status IN ('not_needed','completed','heuristic','skipped_budget','skipped_unavailable','failed')",
            name="ck_housing_application_analyses_ai_status",
        ),
    )
    op.create_index(
        "ix_housing_application_analyses_org_status",
        "housing_application_analyses",
        ["organisation_id", "status"],
    )
    _enable_rls("housing_application_analyses")

    op.create_table(
        "housing_application_analysis_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("related_checklist_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("needs_human_verification", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["analysis_id"], ["housing_application_analyses.id"], ondelete="CASCADE"),
        sa.CheckConstraint("source IN ('rule','evidence','document','ai')", name="ck_housing_app_findings_source"),
        sa.CheckConstraint(
            "outcome IN ('complete','missing','incomplete','needs_review','not_applicable','not_performed')",
            name="ck_housing_app_findings_outcome",
        ),
        sa.CheckConstraint(
            "review_status IN ('pending','confirmed','dismissed')",
            name="ck_housing_app_findings_review",
        ),
    )
    op.create_index(
        "ix_housing_app_analysis_findings_analysis",
        "housing_application_analysis_findings",
        ["analysis_id"],
    )
    _enable_rls("housing_application_analysis_findings")


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON housing_application_analysis_findings"))
    op.drop_index("ix_housing_app_analysis_findings_analysis", table_name="housing_application_analysis_findings")
    op.drop_table("housing_application_analysis_findings")
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON housing_application_analyses"))
    op.drop_index("ix_housing_application_analyses_org_status", table_name="housing_application_analyses")
    op.drop_table("housing_application_analyses")
