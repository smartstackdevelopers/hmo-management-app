"""F7.2 privacy management — inventory, DPIA register, DSR, retention, risks.

Revision ID: 20261112_4600_f72
Revises: 20261111_4500_f67
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261112_4600_f72"
down_revision: Union[str, None] = "20261111_4500_f67"
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
        "privacy_inventory_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("data_sources", sa.Text(), nullable=True),
        sa.Column("roles_with_access", sa.Text(), nullable=True),
        sa.Column("storage_locations", sa.Text(), nullable=True),
        sa.Column("processing_services", sa.Text(), nullable=True),
        sa.Column("external_recipients", sa.Text(), nullable=True),
        sa.Column("retention_period_days", sa.Integer(), nullable=True),
        sa.Column("retention_notes", sa.Text(), nullable=True),
        sa.Column("deletion_method", sa.Text(), nullable=True),
        sa.Column("security_controls", sa.Text(), nullable=True),
        sa.Column("lawful_basis_notes", sa.Text(), nullable=True),
        sa.Column("lawful_basis_confirmed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organisation_id", "category_code", name="uq_privacy_inventory_org_code"),
    )
    op.create_index("ix_privacy_inventory_org", "privacy_inventory_items", ["organisation_id"])

    op.create_table(
        "privacy_dpia_register",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_key", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("personal_data_summary", sa.Text(), nullable=True),
        sa.Column("necessity_notes", sa.Text(), nullable=True),
        sa.Column("risk_summary", sa.Text(), nullable=True),
        sa.Column("existing_safeguards", sa.Text(), nullable=True),
        sa.Column("additional_safeguards_required", sa.Text(), nullable=True),
        sa.Column("residual_risk_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="not_started"),
        sa.Column("responsible_reviewer", sa.String(200), nullable=True),
        sa.Column("review_due_at", sa.Date(), nullable=True),
        sa.Column("approval_reference", sa.String(200), nullable=True),
        sa.Column("approved_by_name", sa.String(200), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organisation_id", "activity_key", name="uq_privacy_dpia_org_activity"),
    )
    op.create_index("ix_privacy_dpia_org_status", "privacy_dpia_register", ["organisation_id", "status"])

    op.create_table(
        "privacy_retention_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_code", sa.String(64), nullable=False),
        sa.Column("category_label", sa.String(200), nullable=False),
        sa.Column("retention_period_days", sa.Integer(), nullable=True),
        sa.Column("retention_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("review_due_at", sa.Date(), nullable=True),
        sa.Column("legal_hold_exception_notes", sa.Text(), nullable=True),
        sa.Column("authorised_by_name", sa.String(200), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organisation_id", "category_code", name="uq_privacy_retention_org_code"),
    )
    op.create_index("ix_privacy_retention_org", "privacy_retention_policies", ["organisation_id", "status"])

    op.create_table(
        "privacy_data_subject_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_category", sa.String(32), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="registered"),
        sa.Column("subject_label", sa.String(200), nullable=False),
        sa.Column("subject_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_summary", sa.Text(), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_evidence", sa.Text(), nullable=True),
        sa.Column("response_history", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_privacy_dsr_org_status", "privacy_data_subject_requests", ["organisation_id", "status"])
    op.create_index("ix_privacy_dsr_org_registered", "privacy_data_subject_requests", ["organisation_id", "registered_at"])

    op.create_table(
        "privacy_risk_register",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("mitigation_plan", sa.Text(), nullable=True),
        sa.Column("owner_label", sa.String(200), nullable=True),
        sa.Column("target_review_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_privacy_risks_org_status", "privacy_risk_register", ["organisation_id", "status"])

    op.create_table(
        "privacy_deletion_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("records_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("performed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["performed_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_privacy_deletion_logs_org", "privacy_deletion_logs", ["organisation_id", "created_at"])

    op.create_table(
        "privacy_test_retention_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_privacy_test_retention_org_expires",
        "privacy_test_retention_records",
        ["organisation_id", "expires_at"],
    )

    for table in (
        "privacy_inventory_items",
        "privacy_dpia_register",
        "privacy_retention_policies",
        "privacy_data_subject_requests",
        "privacy_risk_register",
        "privacy_deletion_logs",
        "privacy_test_retention_records",
    ):
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(
        (
            "privacy_test_retention_records",
            "privacy_deletion_logs",
            "privacy_risk_register",
            "privacy_data_subject_requests",
            "privacy_retention_policies",
            "privacy_dpia_register",
            "privacy_inventory_items",
        )
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.drop_table(table)
