"""F3.5 case summary versions.

Revision ID: 20261107_1600_f35
Revises: 20261107_1400_f34
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261107_1600_f35"
down_revision: Union[str, None] = "20261107_1400_f34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

POLICY_SQL = """
CREATE POLICY hmore_org_isolation ON case_summaries
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
        "case_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_id", sa.String(100), nullable=False, server_default="case_summary"),
        sa.Column("feature_id", sa.String(100), nullable=False, server_default="ai.workflow.case_summaries"),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("prompt_id", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model_id", sa.String(128), nullable=True),
        sa.Column("generation_method", sa.String(32), nullable=False, server_default="structured_heuristic"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending_review"),
        sa.Column("sections_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("missing_information_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("recorded_concerns_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("source_refs_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("covered_from", sa.String(32), nullable=True),
        sa.Column("covered_to", sa.String(32), nullable=True),
        sa.Column("uncertainty_notes", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organisation_id", "tenant_id", "version_number", name="uq_case_summaries_org_tenant_version"),
        sa.CheckConstraint(
            "status IN ('pending_review','approved','rejected','failed')",
            name="ck_case_summaries_status",
        ),
        sa.CheckConstraint(
            "generation_method IN ('llm','structured_heuristic')",
            name="ck_case_summaries_method",
        ),
    )
    op.create_index("ix_case_summaries_org_tenant", "case_summaries", ["organisation_id", "tenant_id"])
    op.create_index("ix_case_summaries_org_status", "case_summaries", ["organisation_id", "status"])
    op.execute(sa.text("ALTER TABLE case_summaries ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE case_summaries FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(POLICY_SQL))


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON case_summaries"))
    op.execute(sa.text("ALTER TABLE case_summaries DISABLE ROW LEVEL SECURITY"))
    op.drop_table("case_summaries")
