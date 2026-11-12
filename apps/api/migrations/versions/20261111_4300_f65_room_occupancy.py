"""F6.5 room occupancy foundation tables.

Revision ID: 20261111_4300_f65
Revises: 20261111_4200_f64
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261111_4300_f65"
down_revision: Union[str, None] = "20261111_4200_f64"
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
        "room_occupancy_approval_gates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feasibility_status", sa.String(32), nullable=False, server_default="not_started"),
        sa.Column("dpia_status", sa.String(32), nullable=False, server_default="not_started"),
        sa.Column("signage_status", sa.String(32), nullable=False, server_default="not_started"),
        sa.Column("retention_policy_status", sa.String(32), nullable=False, server_default="not_started"),
        sa.Column("camera_compatibility_status", sa.String(32), nullable=False, server_default="not_started"),
        sa.Column("approved_room_purposes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("authorised_viewer_notes", sa.Text(), nullable=True),
        sa.Column("accuracy_requirements_notes", sa.Text(), nullable=True),
        sa.Column("documentation_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("approval_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("live_counting_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", name="uq_room_occupancy_approval_gates_org"),
    )
    _enable_rls("room_occupancy_approval_gates")

    op.create_table(
        "room_occupancy_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("near_capacity_percent", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("offline_after_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("history_retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("alert_retention_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organisation_id", name="uq_room_occupancy_settings_org"),
    )
    _enable_rls("room_occupancy_settings")

    op.create_table(
        "occupancy_counting_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_key", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("device_type", sa.String(32), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supports_people_counting", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("compatibility_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("stream_activation_allowed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("connection_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("last_communication_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("config_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column("credentials_meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "device_key", name="uq_occupancy_devices_org_key"),
    )
    op.create_index("ix_occupancy_devices_org_room", "occupancy_counting_devices", ["organisation_id", "room_id"])
    _enable_rls("occupancy_counting_devices")

    op.create_table(
        "room_occupancy_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estimated_count", sa.Integer(), nullable=True),
        sa.Column("max_capacity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("occupancy_percent", sa.Integer(), nullable=True),
        sa.Column("occupancy_status", sa.String(32), nullable=False, server_default="offline"),
        sa.Column("is_manual_correction", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("device_connection_status", sa.String(32), nullable=False, server_default="offline"),
        sa.Column("last_count_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="none"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["occupancy_counting_devices.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "room_id", name="uq_room_occupancy_states_org_room"),
    )
    op.create_index("ix_room_occupancy_states_status", "room_occupancy_states", ["organisation_id", "occupancy_status"])
    _enable_rls("room_occupancy_states")

    op.create_table(
        "room_occupancy_count_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("estimated_count", sa.Integer(), nullable=False),
        sa.Column("max_capacity", sa.Integer(), nullable=False),
        sa.Column("occupancy_status", sa.String(32), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="edge"),
        sa.Column("is_manual_correction", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["occupancy_counting_devices.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_room_occ_hist_org_room_at",
        "room_occupancy_count_history",
        ["organisation_id", "room_id", "recorded_at"],
    )
    _enable_rls("room_occupancy_count_history")

    op.create_table(
        "room_occupancy_manual_corrections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_estimated_count", sa.Integer(), nullable=True),
        sa.Column("corrected_count", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("corrected_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["corrected_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_room_occ_corr_org_room", "room_occupancy_manual_corrections", ["organisation_id", "room_id"])
    _enable_rls("room_occupancy_manual_corrections")

    op.create_table(
        "room_occupancy_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("alert_category", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("estimated_count", sa.Integer(), nullable=True),
        sa.Column("max_capacity", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("dedupe_key", sa.String(64), nullable=False, server_default="active"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["occupancy_counting_devices.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "organisation_id",
            "room_id",
            "alert_category",
            "dedupe_key",
            name="uq_room_occ_alerts_active_dedupe",
        ),
    )
    op.create_index("ix_room_occ_alerts_org_status", "room_occupancy_alerts", ["organisation_id", "status"])
    _enable_rls("room_occupancy_alerts")


def downgrade() -> None:
    for table in (
        "room_occupancy_alerts",
        "room_occupancy_manual_corrections",
        "room_occupancy_count_history",
        "room_occupancy_states",
        "occupancy_counting_devices",
        "room_occupancy_settings",
        "room_occupancy_approval_gates",
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.drop_table(table)
