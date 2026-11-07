"""F3.6 document checker results and configurable rules.

Revision ID: 20261107_1800_f36
Revises: 20261107_1600_f35
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261107_1800_f36"
down_revision: Union[str, None] = "20261107_1600_f35"
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
        "document_check_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_code", sa.String(64), nullable=False, server_default=""),
        sa.Column("rule_kind", sa.String(64), nullable=False),
        sa.Column("parameter", sa.String(200), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "organisation_id",
            "category_code",
            "rule_kind",
            "parameter",
            name="uq_document_check_rules_org_cat_kind_param",
        ),
        sa.CheckConstraint(
            "rule_kind IN ('require_extracted_text','require_expiry_date','expiry_not_past','require_phrase')",
            name="ck_document_check_rules_kind",
        ),
    )
    _enable_rls("document_check_rules")

    op.create_table(
        "document_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("checker_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="processing"),
        sa.Column("extraction_status", sa.String(32), nullable=False, server_default="failed"),
        sa.Column("detected_type", sa.String(150), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("ai_status", sa.String(32), nullable=False, server_default="not_needed"),
        sa.Column("ai_error", sa.String(200), nullable=True),
        sa.Column("prompt_id", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model_id", sa.String(128), nullable=True),
        sa.Column("generation_method", sa.String(32), nullable=True),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_id"], ["managed_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_version_id"], ["managed_document_versions.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('processing','completed','needs_review','extraction_failed','processing_failed')",
            name="ck_document_checks_status",
        ),
        sa.CheckConstraint(
            "ai_status IN ('not_needed','completed','heuristic','skipped_budget','skipped_unavailable','failed')",
            name="ck_document_checks_ai_status",
        ),
    )
    op.create_index("ix_document_checks_doc_version", "document_checks", ["document_id", "document_version_id"])
    op.create_index("ix_document_checks_org_status", "document_checks", ["organisation_id", "status"])
    _enable_rls("document_checks")

    op.create_table(
        "document_check_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("needs_human_verification", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("origin", sa.String(32), nullable=False, server_default="rule"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["check_id"], ["document_checks.id"], ondelete="CASCADE"),
        sa.CheckConstraint("source IN ('rule','ocr','ai')", name="ck_document_check_findings_source"),
        sa.CheckConstraint(
            "outcome IN ('pass','fail','warning','not_performed')",
            name="ck_document_check_findings_outcome",
        ),
        sa.CheckConstraint(
            "review_status IN ('pending','confirmed','dismissed')",
            name="ck_document_check_findings_review",
        ),
    )
    op.create_index("ix_document_check_findings_check", "document_check_findings", ["check_id"])
    _enable_rls("document_check_findings")

    op.create_table(
        "document_check_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_finding_code", sa.String(64), nullable=False),
        sa.Column("needs_human_verification", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("origin", sa.String(32), nullable=False, server_default="structured_heuristic"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["check_id"], ["document_checks.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_document_check_observations_check", "document_check_observations", ["check_id"])
    _enable_rls("document_check_observations")


def downgrade() -> None:
    for table in (
        "document_check_observations",
        "document_check_findings",
        "document_checks",
        "document_check_rules",
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
        op.drop_table(table)
