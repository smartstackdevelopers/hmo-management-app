"""F2.9 tenant meetings, appointments, follow-ups, needs/goals with RLS.

Revision ID: 20261106_2000_f29
Revises: 20261106_1900_f28
Create Date: 2026-11-06 20:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261106_2000_f29"
down_revision: Union[str, None] = "20261106_1900_f28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORG_TABLES = (
    "tenant_meetings",
    "tenant_meeting_participants",
    "tenant_appointments",
    "tenant_follow_ups",
    "tenant_follow_up_changes",
    "tenant_needs_goals",
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
        "tenant_meetings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(64), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("purpose", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Europe/London"),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("meeting_method", sa.String(64), nullable=True),
        sa.Column("responsible_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="scheduled"),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("tenant_visible_summary", sa.Text(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("agreed_actions", sa.Text(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('scheduled', 'confirmed', 'completed', 'cancelled')",
            name="ck_tenant_meetings_status",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "reference_number", name="uq_tenant_meetings_org_ref"),
    )
    op.create_index("ix_tenant_meetings_tenant_scheduled", "tenant_meetings", ["tenant_id", "scheduled_at"])
    op.create_index("ix_tenant_meetings_org", "tenant_meetings", ["organisation_id"])

    op.create_table(
        "tenant_meeting_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["meeting_id"], ["tenant_meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("meeting_id", "user_id", name="uq_meeting_participants_meeting_user"),
    )
    op.create_index("ix_meeting_participants_user", "tenant_meeting_participants", ["user_id"])

    op.create_table(
        "tenant_appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(64), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_kind", sa.String(32), nullable=False, server_default="support"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Europe/London"),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("method", sa.String(64), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="scheduled"),
        sa.Column("attendance_status", sa.String(32), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("linked_tenant_visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('scheduled', 'confirmed', 'completed', 'cancelled', 'missed', 'rescheduled')",
            name="ck_tenant_appointments_status",
        ),
        sa.CheckConstraint(
            "appointment_kind IN ('support', 'housing', 'administrative', 'property', 'other')",
            name="ck_tenant_appointments_kind",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_tenant_visit_id"], ["tenant_visits.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "reference_number", name="uq_tenant_appointments_org_ref"),
    )
    op.create_index("ix_tenant_appointments_tenant_start", "tenant_appointments", ["tenant_id", "starts_at"])
    op.create_index("ix_tenant_appointments_org", "tenant_appointments", ["organisation_id"])

    op.create_table(
        "tenant_follow_ups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(64), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_description", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column(
            "related_type",
            sa.String(64),
            nullable=False,
            server_default="none",
        ),
        sa.Column("related_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("show_to_tenant", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'awaiting_information', 'completed', 'cancelled')",
            name="ck_tenant_follow_ups_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_tenant_follow_ups_priority",
        ),
        sa.CheckConstraint(
            "related_type IN ('meeting', 'appointment', 'daily_log', 'handover', 'complaint', "
            "'maintenance', 'housing_application', 'incident', 'operational_task', 'tenant_visit', 'none')",
            name="ck_tenant_follow_ups_related_type",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "reference_number", name="uq_tenant_follow_ups_org_ref"),
    )
    op.create_index("ix_tenant_follow_ups_tenant_due", "tenant_follow_ups", ["tenant_id", "due_at"])
    op.create_index("ix_tenant_follow_ups_assignee_due", "tenant_follow_ups", ["assigned_user_id", "due_at"])

    op.create_table(
        "tenant_follow_up_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("follow_up_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("field_name", sa.String(64), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["follow_up_id"], ["tenant_follow_ups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_follow_up_changes_follow_up", "tenant_follow_up_changes", ["follow_up_id", "created_at"])

    op.create_table(
        "tenant_needs_goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_kind", sa.String(16), nullable=False),
        sa.Column("category_code", sa.String(64), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("responsible_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="identified"),
        sa.Column("review_at", sa.Date(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("record_kind IN ('need', 'goal')", name="ck_tenant_needs_goals_kind"),
        sa.CheckConstraint(
            "status IN ('identified', 'in_progress', 'achieved', 'paused', 'cancelled')",
            name="ck_tenant_needs_goals_status",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_tenant_needs_goals_tenant", "tenant_needs_goals", ["tenant_id", "created_at"])

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
    for table in reversed(ORG_TABLES):
        op.drop_table(table)
