"""F6.4 integration hub foundation tables.

Revision ID: 20261111_4200_f64
Revises: 20261111_4100_f63
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261111_4200_f64"
down_revision: Union[str, None] = "20261111_4100_f63"
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
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("provider_name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("api_base_url", sa.String(500), nullable=True),
        sa.Column("auth_type", sa.String(32), nullable=False, server_default="api_key"),
        sa.Column("config_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column("credentials_meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("connection_status", sa.String(32), nullable=False, server_default="not_configured"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("health_status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("last_connection_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failed_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "provider_key", name="uq_integrations_org_provider"),
        sa.CheckConstraint(
            "category IN ('council', 'hr', 'finance', 'community_service')",
            name="ck_integrations_category",
        ),
        sa.CheckConstraint(
            "auth_type IN ('api_key', 'bearer', 'oauth2', 'none')",
            name="ck_integrations_auth_type",
        ),
        sa.CheckConstraint(
            "connection_status IN ('not_configured', 'configured', 'connected', 'failed', 'disabled')",
            name="ck_integrations_connection_status",
        ),
    )
    op.create_index("ix_integrations_org_category", "integrations", ["organisation_id", "category"])
    op.create_index("ix_integrations_org_status", "integrations", ["organisation_id", "connection_status"])
    _enable_rls("integrations")

    op.create_table(
        "integration_field_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(200), nullable=False, server_default="default"),
        sa.Column("mappings_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "organisation_id",
            "integration_id",
            "version",
            name="uq_integration_field_mappings_version",
        ),
        sa.CheckConstraint("version >= 1", name="ck_integration_field_mappings_version"),
    )
    op.create_index("ix_integration_field_mappings_integration_id", "integration_field_mappings", ["integration_id"])
    _enable_rls("integration_field_mappings")

    op.create_table(
        "integration_sync_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.String(32), nullable=False, server_default="health_check"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("result_summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "idempotency_key", name="uq_integration_sync_jobs_idempotency"),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_integration_sync_jobs_status",
        ),
        sa.CheckConstraint(
            "direction IN ('import', 'export', 'bidirectional', 'health_check')",
            name="ck_integration_sync_jobs_direction",
        ),
    )
    op.create_index(
        "ix_integration_sync_jobs_integration",
        "integration_sync_jobs",
        ["integration_id", "created_at"],
    )
    _enable_rls("integration_sync_jobs")

    op.create_table(
        "integration_activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome", sa.String(16), nullable=False, server_default="success"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_integration_activity_logs_integration",
        "integration_activity_logs",
        ["integration_id", "created_at"],
    )
    _enable_rls("integration_activity_logs")


def downgrade() -> None:
    for table in (
        "integration_activity_logs",
        "integration_sync_jobs",
        "integration_field_mappings",
        "integrations",
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.drop_table(table)
