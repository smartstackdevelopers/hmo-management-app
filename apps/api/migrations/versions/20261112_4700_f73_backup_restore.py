"""F7.3 backup runs, schedules, restore drills, retention settings.

Revision ID: 20261112_4700_f73
Revises: 20261112_4600_f72
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261112_4700_f73"
down_revision: Union[str, None] = "20261112_4600_f72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backup_schedule_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("backup_type", sa.String(32), nullable=False),
        sa.Column("retention_tier", sa.String(16), nullable=False, server_default="daily"),
        sa.Column("cron_expression", sa.String(64), nullable=False, server_default="0 3 * * *"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_parallel", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("backup_type", "retention_tier", name="uq_backup_schedule_type_tier"),
    )

    op.create_table(
        "backup_retention_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("retention_tier", sa.String(16), nullable=False, unique=True),
        sa.Column("keep_count", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("approved_by_label", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "backup_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("backup_type", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False, server_default="platform"),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("verification_status", sa.String(16), nullable=False, server_default="not_started"),
        sa.Column("retention_tier", sa.String(16), nullable=False, server_default="daily"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("storage_location", sa.String(512), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("idempotency_key", name="uq_backup_runs_idempotency"),
    )
    op.create_index("ix_backup_runs_status_started", "backup_runs", ["status", "started_at"])
    op.create_index("ix_backup_runs_type_started", "backup_runs", ["backup_type", "started_at"])

    op.create_table(
        "restore_drill_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("environment_label", sa.String(64), nullable=False, server_default="isolated-test"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("backup_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("steps", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("record_counts", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("rpo_notes", sa.Text(), nullable=True),
        sa.Column("rto_seconds_measured", sa.Integer(), nullable=True),
        sa.Column("rpo_target_status", sa.String(32), nullable=False, server_default="pending_approval"),
        sa.Column("rto_target_status", sa.String(32), nullable=False, server_default="pending_approval"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["backup_run_id"], ["backup_runs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_restore_drill_started", "restore_drill_runs", ["started_at"])

    op.execute(
        sa.text(
            """
            INSERT INTO backup_schedule_configs (id, backup_type, retention_tier, cron_expression, enabled, notes)
            VALUES
              (gen_random_uuid(), 'database', 'daily', '0 3 * * *', true, 'Platform PostgreSQL — operator must configure storage'),
              (gen_random_uuid(), 'files_manifest', 'daily', '30 3 * * *', true, 'Private file metadata manifest'),
              (gen_random_uuid(), 'config_manifest', 'weekly', '0 4 * * 0', true, 'Alembic head and service config fingerprint');
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO backup_retention_settings (id, retention_tier, keep_count, notes)
            VALUES
              (gen_random_uuid(), 'daily', 7, 'Pending organisational approval'),
              (gen_random_uuid(), 'weekly', 4, 'Pending organisational approval'),
              (gen_random_uuid(), 'monthly', 12, 'Pending organisational approval');
            """
        )
    )


def downgrade() -> None:
    op.drop_table("restore_drill_runs")
    op.drop_table("backup_runs")
    op.drop_table("backup_retention_settings")
    op.drop_table("backup_schedule_configs")
