"""F2.3 staff training records and safeguarding reminders with RLS.

Revision ID: 20261106_1400_f23
Revises: 20261106_1200_f22
Create Date: 2026-11-06 14:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261106_1400_f23"
down_revision: Union[str, None] = "20261106_1200_f22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORG_TABLES = (
    "staff_training_records",
    "safeguarding_reminders",
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
        "staff_training_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("category", sa.String(64), nullable=False, server_default="general"),
        sa.Column("provider", sa.String(255), nullable=True),
        sa.Column("completion_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("required_by_date", sa.Date(), nullable=True),
        sa.Column("evidence_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="not_started"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed', 'exempt')",
            name="ck_staff_training_status",
        ),
        sa.CheckConstraint(
            "expiry_date IS NULL OR completion_date IS NULL OR expiry_date >= completion_date",
            name="ck_staff_training_expiry_after_completion",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["evidence_file_id"], ["file_metadata.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_staff_training_records_organisation_id", "staff_training_records", ["organisation_id"])
    op.create_index("ix_staff_training_records_staff_user_id", "staff_training_records", ["staff_user_id"])
    op.create_index("ix_staff_training_staff_expiry", "staff_training_records", ["staff_user_id", "expiry_date"])
    op.create_index("ix_staff_training_org_status", "staff_training_records", ["organisation_id", "status"])
    op.create_index("ix_staff_training_org_category", "staff_training_records", ["organisation_id", "category"])

    op.create_table(
        "safeguarding_reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("related_staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(64), nullable=False, server_default="follow_up"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'acknowledged', 'completed', 'cancelled', 'overdue')",
            name="ck_safeguarding_reminders_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_safeguarding_reminders_priority",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["related_staff_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_safeguarding_reminders_organisation_id", "safeguarding_reminders", ["organisation_id"])
    op.create_index("ix_safeguarding_reminders_assigned_user_id", "safeguarding_reminders", ["assigned_user_id"])
    op.create_index("ix_safeguarding_reminders_tenant_id", "safeguarding_reminders", ["tenant_id"])
    op.create_index(
        "ix_safeguarding_reminders_assignee_due", "safeguarding_reminders", ["assigned_user_id", "due_at"]
    )
    op.create_index(
        "ix_safeguarding_reminders_org_status", "safeguarding_reminders", ["organisation_id", "status"]
    )

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
    op.drop_table("safeguarding_reminders")
    op.drop_table("staff_training_records")
