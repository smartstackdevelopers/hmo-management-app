"""F3.4 Notes Analysis Agent persistence.

Revision ID: 20261107_1400_f34
Revises: 20261107_1200_f33
Create Date: 2026-11-07 14:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261107_1400_f34"
down_revision: Union[str, None] = "20261107_1200_f33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORG_TABLES = ("daily_log_ai_analyses", "daily_log_ai_suggestions")

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
        "daily_log_ai_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daily_log_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_note_version", sa.String(64), nullable=False),
        sa.Column("workflow_id", sa.String(100), nullable=False, server_default="notes_analysis"),
        sa.Column("feature_id", sa.String(100), nullable=False, server_default="ai.agent.notes_analysis"),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("prompt_id", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model_id", sa.String(128), nullable=True),
        sa.Column("generation_kind", sa.String(32), nullable=False, server_default="on_demand"),
        sa.Column("generation_method", sa.String(32), nullable=False, server_default="llm"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending_review"),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("key_observations_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("missing_details_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("suggested_actions_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("uncertainty_notes", sa.Text(), nullable=True),
        sa.Column("source_refs_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("batch_job_id", sa.String(64), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["daily_log_id"], ["daily_logs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "daily_log_id",
            "source_note_version",
            "generation_kind",
            name="uq_daily_log_ai_analysis_log_version_kind",
        ),
        sa.CheckConstraint(
            "status IN ('pending_review','approved','partially_approved','rejected','applied','failed')",
            name="ck_daily_log_ai_analyses_status",
        ),
        sa.CheckConstraint(
            "generation_kind IN ('on_demand','batch')",
            name="ck_daily_log_ai_analyses_kind",
        ),
        sa.CheckConstraint(
            "generation_method IN ('llm','structured_heuristic')",
            name="ck_daily_log_ai_analyses_method",
        ),
    )
    op.create_index("ix_daily_log_ai_analyses_org_status", "daily_log_ai_analyses", ["organisation_id", "status"])
    op.create_index(
        "ix_daily_log_ai_analyses_log_version",
        "daily_log_ai_analyses",
        ["daily_log_id", "source_note_version"],
    )
    op.create_index("ix_daily_log_ai_analyses_tenant_id", "daily_log_ai_analyses", ["tenant_id"])

    op.create_table(
        "daily_log_ai_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daily_log_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("is_interpretation", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("edited_body", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["analysis_id"], ["daily_log_ai_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["daily_log_id"], ["daily_logs.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "kind IN ('missing_detail','next_action','observation')",
            name="ck_daily_log_ai_suggestions_kind",
        ),
        sa.CheckConstraint(
            "review_status IN ('pending','approved','rejected','dismissed','applied','superseded')",
            name="ck_daily_log_ai_suggestions_status",
        ),
    )
    op.create_index(
        "ix_daily_log_ai_suggestions_status",
        "daily_log_ai_suggestions",
        ["organisation_id", "review_status"],
    )
    op.create_index("ix_daily_log_ai_suggestions_analysis", "daily_log_ai_suggestions", ["analysis_id"])

    for table in ORG_TABLES:
        op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(POLICY_SQL.format(table=table)))


def downgrade() -> None:
    for table in reversed(ORG_TABLES):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
    op.drop_table("daily_log_ai_suggestions")
    op.drop_table("daily_log_ai_analyses")
