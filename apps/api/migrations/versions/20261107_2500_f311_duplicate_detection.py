"""F3.11 duplicate detection via search. No AI per record. No auto merge/delete.

Revision ID: 20261107_2500_f311
Revises: 20261107_2400_f310
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261107_2500_f311"
down_revision: Union[str, None] = "20261107_2400_f310"
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
        "duplicate_detection_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("scope_record_types_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_record_type", sa.String(64), nullable=True),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_scanned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidates_compared", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("findings_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("findings_deduplicated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.String(500), nullable=True),
        sa.Column("used_ai", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("trigger IN ('manual','scheduled','record')", name="ck_duplicate_runs_trigger"),
        sa.CheckConstraint("status IN ('running','completed','failed')", name="ck_duplicate_runs_status"),
        sa.CheckConstraint("used_ai = false", name="ck_duplicate_runs_no_ai"),
    )
    op.create_index(
        "ix_duplicate_detection_runs_org_started",
        "duplicate_detection_runs",
        ["organisation_id", "started_at"],
    )
    _enable_rls("duplicate_detection_runs")

    op.create_table(
        "duplicate_detection_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_seen_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_type", sa.String(64), nullable=False),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dedupe_key", sa.String(220), nullable=False),
        sa.Column("match_strength", sa.String(32), nullable=False, server_default="possible"),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("matching_fields_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("matching_reasons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["run_id"], ["duplicate_detection_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["first_run_id"], ["duplicate_detection_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_seen_run_id"], ["duplicate_detection_runs.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "record_type IN ('tenant','housing_application','file_metadata')",
            name="ck_duplicate_findings_record_type",
        ),
        sa.CheckConstraint(
            "match_strength IN ('exact','strong','possible')",
            name="ck_duplicate_findings_strength",
        ),
        sa.CheckConstraint(
            "review_status IN ('pending','confirmed_duplicate','not_duplicate','deferred')",
            name="ck_duplicate_findings_review",
        ),
        sa.CheckConstraint("source_record_id <> candidate_record_id", name="ck_duplicate_findings_distinct"),
    )
    op.create_index("ix_duplicate_findings_org_status", "duplicate_detection_findings", ["organisation_id", "review_status"])
    op.create_index("ix_duplicate_findings_run", "duplicate_detection_findings", ["run_id"])
    op.create_index("ix_duplicate_findings_dedupe", "duplicate_detection_findings", ["organisation_id", "dedupe_key"])
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_duplicate_findings_open_dedupe "
            "ON duplicate_detection_findings (organisation_id, dedupe_key) "
            "WHERE review_status IN ('pending','deferred','confirmed_duplicate')"
        )
    )
    _enable_rls("duplicate_detection_findings")

    # Supporting indexes for candidate generation (expression / composite).
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_tenants_org_lower_email "
            "ON tenants (organisation_id, lower(email)) "
            "WHERE email IS NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_tenants_org_lower_preferred_name "
            "ON tenants (organisation_id, lower(preferred_name))"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_file_metadata_org_checksum "
            "ON file_metadata (organisation_id, checksum_sha256) "
            "WHERE checksum_sha256 IS NOT NULL AND status = 'active'"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_housing_applications_org_tenant_status "
            "ON housing_applications (organisation_id, tenant_id, status)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_housing_applications_org_tenant_status"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_file_metadata_org_checksum"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_tenants_org_lower_preferred_name"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_tenants_org_lower_email"))
    op.execute(sa.text("DROP INDEX IF EXISTS uq_duplicate_findings_open_dedupe"))
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON duplicate_detection_findings"))
    op.drop_table("duplicate_detection_findings")
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON duplicate_detection_runs"))
    op.drop_table("duplicate_detection_runs")
