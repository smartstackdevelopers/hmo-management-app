"""F6.2 full reports & analytics: schedules, exports, early-warning alerts.

Revision ID: 20261111_4000_f62
Revises: 20261111_3900_f61
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261111_4000_f62"
down_revision: Union[str, None] = "20261111_3900_f61"
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
        "report_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_category", sa.String(32), nullable=False),
        sa.Column("export_format", sa.String(8), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("filters_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_metadata_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ready"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allowed_user_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["file_metadata_id"], ["file_metadata.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "report_category IN ('occupancy', 'housing', 'complaints', 'caseload', 'plans', 'dashboard')",
            name="ck_report_exports_category",
        ),
        sa.CheckConstraint("export_format IN ('csv', 'pdf', 'xlsx')", name="ck_report_exports_format"),
        sa.CheckConstraint("status IN ('ready', 'expired', 'revoked')", name="ck_report_exports_status"),
    )
    op.create_index("ix_report_exports_org_created", "report_exports", ["organisation_id", "created_at"])
    op.create_index("ix_report_exports_file_metadata_id", "report_exports", ["file_metadata_id"])
    _enable_rls("report_exports")

    op.create_table(
        "scheduled_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("report_category", sa.String(32), nullable=False),
        sa.Column("export_format", sa.String(8), nullable=False, server_default="csv"),
        sa.Column("frequency", sa.String(16), nullable=False),
        sa.Column("period_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("filters_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("recipient_user_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "report_category IN ('occupancy', 'housing', 'complaints', 'caseload', 'plans', 'dashboard')",
            name="ck_scheduled_reports_category",
        ),
        sa.CheckConstraint("frequency IN ('daily', 'weekly', 'monthly')", name="ck_scheduled_reports_frequency"),
        sa.CheckConstraint("export_format IN ('csv', 'pdf', 'xlsx')", name="ck_scheduled_reports_format"),
    )
    op.create_index("ix_scheduled_reports_org_enabled", "scheduled_reports", ["organisation_id", "is_enabled"])
    _enable_rls("scheduled_reports")

    op.create_table(
        "scheduled_report_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("report_export_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("period_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scheduled_report_id"], ["scheduled_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_export_id"], ["report_exports.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')",
            name="ck_scheduled_report_runs_status",
        ),
    )
    op.create_index(
        "ix_scheduled_report_runs_schedule",
        "scheduled_report_runs",
        ["scheduled_report_id", "created_at"],
    )
    _enable_rls("scheduled_report_runs")

    op.create_table(
        "early_warning_thresholds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("threshold_value", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "alert_type", name="uq_early_warning_thresholds_org_type"),
        sa.CheckConstraint(
            "alert_type IN ("
            "'overdue_complaints', 'pending_housing', 'overdue_followups', "
            "'overdue_plan_reviews', 'occupancy_drop', 'high_caseload'"
            ")",
            name="ck_early_warning_thresholds_type",
        ),
    )
    _enable_rls("early_warning_thresholds")

    op.create_table(
        "early_warning_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="warning"),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("threshold_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("related_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("dedupe_key", sa.String(200), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["acknowledged_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "dedupe_key", name="uq_early_warning_alerts_dedupe"),
        sa.CheckConstraint(
            "alert_type IN ("
            "'overdue_complaints', 'pending_housing', 'overdue_followups', "
            "'overdue_plan_reviews', 'occupancy_drop', 'high_caseload'"
            ")",
            name="ck_early_warning_alerts_type",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved', 'dismissed')",
            name="ck_early_warning_alerts_status",
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="ck_early_warning_alerts_severity",
        ),
    )
    op.create_index(
        "ix_early_warning_alerts_org_status",
        "early_warning_alerts",
        ["organisation_id", "status"],
    )
    _enable_rls("early_warning_alerts")


def downgrade() -> None:
    for table in (
        "early_warning_alerts",
        "early_warning_thresholds",
        "scheduled_report_runs",
        "scheduled_reports",
        "report_exports",
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.drop_table(table)
