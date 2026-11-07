"""F3.9 compliance agent sweeps and findings. No legal certification.

Revision ID: 20261107_2300_f39
Revises: 20261107_2200_f38
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261107_2300_f39"
down_revision: Union[str, None] = "20261107_2200_f38"
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
        "compliance_sweeps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("scope_modules_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rules_evaluated_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("records_evaluated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("findings_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("findings_deduplicated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.String(500), nullable=True),
        sa.Column("ai_status", sa.String(32), nullable=False, server_default="not_needed"),
        sa.Column("ai_error", sa.String(200), nullable=True),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.Column("prompt_id", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model_id", sa.String(128), nullable=True),
        sa.Column("feature_id", sa.String(100), nullable=False, server_default="ai.agent.compliance"),
        sa.Column("generation_method", sa.String(32), nullable=False, server_default="rules_only"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "trigger IN ('manual','scheduled')",
            name="ck_compliance_sweeps_trigger",
        ),
        sa.CheckConstraint(
            "status IN ('running','completed','failed')",
            name="ck_compliance_sweeps_status",
        ),
        sa.CheckConstraint(
            "ai_status IN ('not_needed','completed','skipped_budget','skipped_unavailable','failed','heuristic')",
            name="ck_compliance_sweeps_ai_status",
        ),
    )
    op.create_index("ix_compliance_sweeps_org_started", "compliance_sweeps", ["organisation_id", "started_at"])
    op.create_index("ix_compliance_sweeps_org_status", "compliance_sweeps", ["organisation_id", "status"])
    _enable_rls("compliance_sweeps")

    op.create_table(
        "compliance_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sweep_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_sweep_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_seen_sweep_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", sa.String(64), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("rule_name", sa.String(200), nullable=False),
        sa.Column("rule_source", sa.String(200), nullable=False),
        sa.Column("module", sa.String(64), nullable=False),
        sa.Column("source_record_type", sa.String(64), nullable=False),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dedupe_key", sa.String(200), nullable=False),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("evidence_refs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("resolution_status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("needs_human_verification", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("corrective_action_ref", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sweep_id"], ["compliance_sweeps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["first_sweep_id"], ["compliance_sweeps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_seen_sweep_id"], ["compliance_sweeps.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "result IN ('potential_gap','needs_review','unable_to_verify')",
            name="ck_compliance_findings_result",
        ),
        sa.CheckConstraint(
            "review_status IN ('pending','confirmed','dismissed','investigate')",
            name="ck_compliance_findings_review_status",
        ),
        sa.CheckConstraint(
            "resolution_status IN ('open','resolved')",
            name="ck_compliance_findings_resolution_status",
        ),
    )
    op.create_index("ix_compliance_findings_org_status", "compliance_findings", ["organisation_id", "review_status"])
    op.create_index("ix_compliance_findings_sweep", "compliance_findings", ["sweep_id"])
    op.create_index("ix_compliance_findings_rule", "compliance_findings", ["organisation_id", "rule_id"])
    op.create_index("ix_compliance_findings_dedupe", "compliance_findings", ["organisation_id", "dedupe_key"])
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_compliance_findings_open_dedupe "
            "ON compliance_findings (organisation_id, dedupe_key) "
            "WHERE resolution_status = 'open' AND review_status <> 'dismissed'"
        )
    )
    _enable_rls("compliance_findings")


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON compliance_findings"))
    op.drop_table("compliance_findings")
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON compliance_sweeps"))
    op.drop_table("compliance_sweeps")
