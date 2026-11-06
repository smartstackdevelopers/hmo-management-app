"""F2.5 housing applications, decisions, waiting lists with RLS.

Revision ID: 20261106_1600_f25
Revises: 20261106_1500_f24
Create Date: 2026-11-06 16:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261106_1600_f25"
down_revision: Union[str, None] = "20261106_1500_f24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORG_TABLES = (
    "housing_applications",
    "housing_application_status_history",
    "housing_application_decisions",
    "waiting_list_entries",
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
        "housing_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(64), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("preferred_property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("accommodation_type", sa.String(64), nullable=True),
        sa.Column("housing_requirements", sa.Text(), nullable=False),
        sa.Column("household_summary", sa.Text(), nullable=True),
        sa.Column("supporting_information", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("information_required_notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'under_review', 'information_required', "
            "'approved', 'rejected', 'withdrawn', 'closed')",
            name="ck_housing_applications_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_housing_applications_priority",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["preferred_property_id"], ["properties.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "reference_number", name="uq_housing_applications_org_ref"),
    )
    op.create_index("ix_housing_applications_organisation_id", "housing_applications", ["organisation_id"])
    op.create_index("ix_housing_applications_tenant_id", "housing_applications", ["tenant_id"])
    op.create_index("ix_housing_applications_reviewer_user_id", "housing_applications", ["reviewer_user_id"])
    op.create_index("ix_housing_applications_org_status", "housing_applications", ["organisation_id", "status"])
    op.create_index("ix_housing_applications_tenant", "housing_applications", ["tenant_id", "status"])
    op.create_index("ix_housing_applications_reviewer", "housing_applications", ["reviewer_user_id", "status"])

    op.create_table(
        "housing_application_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["application_id"], ["housing_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_housing_app_status_history_organisation_id",
        "housing_application_status_history",
        ["organisation_id"],
    )
    op.create_index(
        "ix_housing_app_status_history_application_id",
        "housing_application_status_history",
        ["application_id"],
    )
    op.create_index(
        "ix_housing_app_status_history_app",
        "housing_application_status_history",
        ["application_id", "created_at"],
    )

    op.create_table(
        "housing_application_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_notes", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_housing_application_decisions_decision",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["application_id"], ["housing_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_housing_app_decisions_organisation_id", "housing_application_decisions", ["organisation_id"]
    )
    op.create_index(
        "ix_housing_app_decisions_application_id", "housing_application_decisions", ["application_id"]
    )
    op.create_index(
        "ix_housing_app_decisions_app", "housing_application_decisions", ["application_id", "created_at"]
    )

    op.create_table(
        "waiting_list_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("responsible_officer_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'removed', 'allocated')",
            name="ck_waiting_list_entries_status",
        ),
        sa.CheckConstraint("position > 0", name="ck_waiting_list_entries_position_positive"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["application_id"], ["housing_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responsible_officer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "application_id", name="uq_waiting_list_org_application"),
        sa.UniqueConstraint("organisation_id", "position", name="uq_waiting_list_org_position"),
    )
    op.create_index("ix_waiting_list_entries_organisation_id", "waiting_list_entries", ["organisation_id"])
    op.create_index("ix_waiting_list_entries_application_id", "waiting_list_entries", ["application_id"])
    op.create_index("ix_waiting_list_org_status", "waiting_list_entries", ["organisation_id", "status"])

    for table in ORG_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(POLICY_SQL.format(table=table))
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO hmore_app")


def downgrade() -> None:
    for table in reversed(ORG_TABLES):
        op.execute(f"REVOKE SELECT, INSERT, UPDATE, DELETE ON {table} FROM hmore_app")
        op.execute(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("waiting_list_entries")
    op.drop_table("housing_application_decisions")
    op.drop_table("housing_application_status_history")
    op.drop_table("housing_applications")
