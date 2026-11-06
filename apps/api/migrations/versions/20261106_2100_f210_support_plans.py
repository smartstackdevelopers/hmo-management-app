"""F2.10 support plans, goals, milestones, reviews, exports with RLS.

Revision ID: 20261106_2100_f210
Revises: 20261106_2000_f29
Create Date: 2026-11-06 21:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261106_2100_f210"
down_revision: Union[str, None] = "20261106_2000_f29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORG_TABLES = (
    "tenant_support_plans",
    "support_plan_contributors",
    "support_plan_goals",
    "support_plan_goal_changes",
    "support_plan_goal_progress_notes",
    "support_plan_milestones",
    "support_plan_milestone_changes",
    "support_plan_reviews",
    "support_plan_history_events",
    "support_plan_progress_exports",
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
        "tenant_support_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(64), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("support_objectives", sa.Text(), nullable=True),
        sa.Column("responsible_worker_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("planned_review_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hold_reason", sa.Text(), nullable=True),
        sa.Column("superseded_by_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supersedes_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("tenant_summary", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'under_review', 'on_hold', 'completed', 'closed')",
            name="ck_tenant_support_plans_status",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responsible_worker_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["superseded_by_plan_id"], ["tenant_support_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supersedes_plan_id"], ["tenant_support_plans.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "reference_number", name="uq_tenant_support_plans_org_ref"),
    )
    op.create_index("ix_tenant_support_plans_tenant_status", "tenant_support_plans", ["tenant_id", "status"])

    op.create_table(
        "support_plan_contributors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["tenant_support_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("plan_id", "user_id", name="uq_support_plan_contributors_plan_user"),
    )

    op.create_table(
        "support_plan_goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(64), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("intended_outcome", sa.Text(), nullable=True),
        sa.Column("responsible_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(32), nullable=False, server_default="not_started"),
        sa.Column("progress_notes", sa.Text(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("achieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'at_risk', 'achieved', 'on_hold', 'cancelled')",
            name="ck_support_plan_goals_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_support_plan_goals_priority",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["tenant_support_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "reference_number", name="uq_support_plan_goals_org_ref"),
    )
    op.create_index("ix_support_plan_goals_plan", "support_plan_goals", ["plan_id", "status"])

    op.create_table(
        "support_plan_goal_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("field_name", sa.String(64), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["goal_id"], ["support_plan_goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_support_plan_goal_changes_goal", "support_plan_goal_changes", ["goal_id", "created_at"])

    op.create_table(
        "support_plan_goal_progress_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("show_to_tenant", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["goal_id"], ["support_plan_goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_support_plan_goal_progress_goal", "support_plan_goal_progress_notes", ["goal_id", "created_at"]
    )

    op.create_table(
        "support_plan_milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(64), nullable=False),
        sa.Column("goal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("responsible_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'delayed', 'cancelled')",
            name="ck_support_plan_milestones_status",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["goal_id"], ["support_plan_goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "reference_number", name="uq_support_plan_milestones_org_ref"),
    )
    op.create_index("ix_support_plan_milestones_goal", "support_plan_milestones", ["goal_id", "target_date"])

    op.create_table(
        "support_plan_milestone_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("milestone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("field_name", sa.String(64), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["milestone_id"], ["support_plan_milestones.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_support_plan_milestone_changes_ms", "support_plan_milestone_changes", ["milestone_id", "created_at"]
    )

    op.create_table(
        "support_plan_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(64), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_type", sa.String(16), nullable=False),
        sa.Column("review_date", sa.Date(), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goals_reviewed", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("milestones_reviewed", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("progress_summary", sa.Text(), nullable=True),
        sa.Column("achievements", sa.Text(), nullable=True),
        sa.Column("challenges", sa.Text(), nullable=True),
        sa.Column("recommended_actions", sa.Text(), nullable=True),
        sa.Column("required_plan_changes", sa.Text(), nullable=True),
        sa.Column("follow_up_actions", sa.Text(), nullable=True),
        sa.Column("next_review_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("tenant_summary", sa.Text(), nullable=True),
        sa.Column("finalised_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "review_type IN ('weekly', 'monthly')",
            name="ck_support_plan_reviews_type",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'in_progress', 'finalised', 'superseded')",
            name="ck_support_plan_reviews_status",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["tenant_support_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "reference_number", name="uq_support_plan_reviews_org_ref"),
    )
    op.create_index("ix_support_plan_reviews_plan_date", "support_plan_reviews", ["plan_id", "review_date"])

    op.create_table(
        "support_plan_history_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_entity_type", sa.String(32), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["tenant_support_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_support_plan_history_plan", "support_plan_history_events", ["plan_id", "created_at"])

    op.create_table(
        "support_plan_progress_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("include_internal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["tenant_support_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["file_metadata.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_support_plan_exports_plan", "support_plan_progress_exports", ["plan_id", "created_at"])

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
