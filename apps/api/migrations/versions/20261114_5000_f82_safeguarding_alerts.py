"""F8.2 optional advanced safeguarding alerts add-on tables.

Revision ID: 20261114_5000_f82
Revises: 20261113_4900_f81
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261114_5000_f82"
down_revision: Union[str, None] = "20261113_4900_f81"
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
        "organisation_safeguarding_alert_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("privacy_review_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.Column("ai_assist_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("default_notification_channel", sa.String(16), nullable=False, server_default="in_app"),
        sa.Column("escalation_targets", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("emergency_guidance_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", name="uq_safeguarding_alert_settings_org"),
        sa.CheckConstraint(
            "default_notification_channel IN ('in_app', 'email', 'push')",
            name="ck_safeguarding_alert_default_channel",
        ),
    )
    op.create_table(
        "safeguarding_alert_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", "slug", name="uq_safeguarding_alert_category_slug"),
    )
    op.create_table(
        "safeguarding_alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger_type", sa.String(64), nullable=False),
        sa.Column("trigger_config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("responsible_team", sa.String(64), nullable=False, server_default="support"),
        sa.Column("notification_method", sa.String(16), nullable=False, server_default="in_app"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["safeguarding_alert_categories.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "priority IN ('critical', 'high', 'medium', 'low')",
            name="ck_safeguarding_alert_rule_priority",
        ),
        sa.CheckConstraint(
            "notification_method IN ('in_app', 'email', 'push')",
            name="ck_safeguarding_alert_rule_notify",
        ),
    )
    op.create_table(
        "safeguarding_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(32), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source", sa.String(64), nullable=False, server_default="staff"),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(32), nullable=False, server_default="new"),
        sa.Column("priority", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("dedupe_key", sa.String(128), nullable=True),
        sa.Column("alert_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["category_id"], ["safeguarding_alert_categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rule_id"], ["safeguarding_alert_rules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "reference_number", name="uq_safeguarding_alerts_org_ref"),
        sa.UniqueConstraint("organisation_id", "dedupe_key", name="uq_safeguarding_alerts_dedupe"),
        sa.CheckConstraint(
            "status IN ('new', 'under_review', 'assigned', 'action_required', 'escalated', 'resolved', 'closed')",
            name="ck_safeguarding_alerts_status",
        ),
        sa.CheckConstraint(
            "priority IN ('critical', 'high', 'medium', 'low')",
            name="ck_safeguarding_alerts_priority",
        ),
        sa.CheckConstraint(
            "source_type IN ('manual', 'rule', 'tenant_report', 'ai_suggestion')",
            name="ck_safeguarding_alerts_source_type",
        ),
    )
    op.create_index("ix_safeguarding_alerts_org_status", "safeguarding_alerts", ["organisation_id", "status"])
    op.create_index("ix_safeguarding_alerts_org_priority", "safeguarding_alerts", ["organisation_id", "priority"])
    op.create_table(
        "safeguarding_alert_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["alert_id"], ["safeguarding_alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "safeguarding_alert_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_type", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["alert_id"], ["safeguarding_alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "review_type IN ('acknowledgement', 'assessment', 'supervisor', 'escalation_approval', 'closure')",
            name="ck_safeguarding_alert_review_type",
        ),
    )
    op.create_table(
        "safeguarding_alert_escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("target_role", sa.String(64), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["alert_id"], ["safeguarding_alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["acknowledged_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "safeguarding_alert_ai_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("suggestion_type", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("uncertainty_note", sa.Text(), nullable=True),
        sa.Column("human_approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("ai_request_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["alert_id"], ["safeguarding_alerts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "safeguarding_tenant_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(32), nullable=False),
        sa.Column("reporter_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("attachment_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="received"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["safeguarding_alert_categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["alert_id"], ["safeguarding_alerts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["attachment_file_id"], ["file_metadata.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "reference_number", name="uq_safeguarding_tenant_reports_ref"),
        sa.CheckConstraint(
            "status IN ('received', 'linked', 'closed')",
            name="ck_safeguarding_tenant_reports_status",
        ),
    )
    for table in (
        "organisation_safeguarding_alert_settings",
        "safeguarding_alert_categories",
        "safeguarding_alert_rules",
        "safeguarding_alerts",
        "safeguarding_alert_status_history",
        "safeguarding_alert_reviews",
        "safeguarding_alert_escalations",
        "safeguarding_alert_ai_suggestions",
        "safeguarding_tenant_reports",
    ):
        _enable_rls(table)


def downgrade() -> None:
    op.drop_table("safeguarding_tenant_reports")
    op.drop_table("safeguarding_alert_ai_suggestions")
    op.drop_table("safeguarding_alert_escalations")
    op.drop_table("safeguarding_alert_reviews")
    op.drop_table("safeguarding_alert_status_history")
    op.drop_table("safeguarding_alerts")
    op.drop_table("safeguarding_alert_rules")
    op.drop_table("safeguarding_alert_categories")
    op.drop_table("organisation_safeguarding_alert_settings")
