"""F5.5 tenant wellbeing: check-ins, routines, resources, saved items.

Private check-in notes stay tenant-owned. Resource library is org-managed.

Revision ID: 20261110_3800_f55
Revises: 20261110_3700_f54
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261110_3800_f55"
down_revision: Union[str, None] = "20261110_3700_f54"
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
        "wellbeing_checkins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkin_date", sa.Date(), nullable=False),
        sa.Column("mood", sa.String(32), nullable=True),
        sa.Column("energy_level", sa.Integer(), nullable=True),
        sa.Column("stress_level", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("skipped", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "mood IS NULL OR mood IN ('very_good', 'good', 'okay', 'low', 'very_low')",
            name="ck_wellbeing_checkins_mood",
        ),
        sa.CheckConstraint(
            "energy_level IS NULL OR (energy_level >= 1 AND energy_level <= 5)",
            name="ck_wellbeing_checkins_energy",
        ),
        sa.CheckConstraint(
            "stress_level IS NULL OR (stress_level >= 1 AND stress_level <= 5)",
            name="ck_wellbeing_checkins_stress",
        ),
        sa.UniqueConstraint("tenant_id", "checkin_date", name="uq_wellbeing_checkins_tenant_date"),
    )
    op.create_index("ix_wellbeing_checkins_org_tenant_date", "wellbeing_checkins", ["organisation_id", "tenant_id", "checkin_date"])
    _enable_rls("wellbeing_checkins")

    op.create_table(
        "wellbeing_routines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(64), nullable=False, server_default="other"),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("recurrence", sa.String(32), nullable=False, server_default="daily"),
        sa.Column("weekday_mask", sa.Integer(), nullable=True),
        sa.Column("one_time_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reminder_minutes_before", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "recurrence IN ('daily', 'weekdays', 'weekly', 'one_time')",
            name="ck_wellbeing_routines_recurrence",
        ),
        sa.CheckConstraint(
            "reminder_minutes_before IS NULL OR (reminder_minutes_before >= 0 AND reminder_minutes_before <= 240)",
            name="ck_wellbeing_routines_reminder_minutes",
        ),
    )
    op.create_index("ix_wellbeing_routines_org_tenant_active", "wellbeing_routines", ["organisation_id", "tenant_id", "is_active"])
    _enable_rls("wellbeing_routines")

    op.create_table(
        "wellbeing_routine_completions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("routine_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["routine_id"], ["wellbeing_routines.id"], ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('completed', 'skipped')", name="ck_wellbeing_routine_completions_status"),
        sa.UniqueConstraint("routine_id", "activity_date", name="uq_wellbeing_routine_completions_day"),
    )
    op.create_index(
        "ix_wellbeing_routine_completions_org_tenant_date",
        "wellbeing_routine_completions",
        ["organisation_id", "tenant_id", "activity_date"],
    )
    _enable_rls("wellbeing_routine_completions")

    op.create_table(
        "wellbeing_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("activity_level", sa.String(32), nullable=True),
        sa.Column("equipment", sa.String(255), nullable=True),
        sa.Column("safety_notes", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="unverified"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("kind IN ('exercise', 'mindfulness')", name="ck_wellbeing_resources_kind"),
        sa.CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'rejected')",
            name="ck_wellbeing_resources_verification",
        ),
    )
    op.create_index("ix_wellbeing_resources_org_kind_active", "wellbeing_resources", ["organisation_id", "kind", "is_active"])
    _enable_rls("wellbeing_resources")

    op.create_table(
        "wellbeing_saved_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_id"], ["wellbeing_resources.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "resource_id", name="uq_wellbeing_saved_resources_tenant_resource"),
    )
    op.create_index("ix_wellbeing_saved_resources_org_tenant", "wellbeing_saved_resources", ["organisation_id", "tenant_id"])
    _enable_rls("wellbeing_saved_resources")

    op.create_table(
        "wellbeing_resource_completions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="completed"),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_id"], ["wellbeing_resources.id"], ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('completed', 'stopped')", name="ck_wellbeing_resource_completions_status"),
    )
    op.create_index(
        "ix_wellbeing_resource_completions_org_tenant",
        "wellbeing_resource_completions",
        ["organisation_id", "tenant_id"],
    )
    _enable_rls("wellbeing_resource_completions")

    op.create_table(
        "wellbeing_directory_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("contact_info", sa.String(255), nullable=True),
        sa.Column("opening_hours", sa.String(255), nullable=True),
        sa.Column("eligibility", sa.Text(), nullable=True),
        sa.Column("referral_info", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("community_service_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_clinical", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="unverified"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["community_service_id"], ["community_services.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'rejected')",
            name="ck_wellbeing_directory_verification",
        ),
    )
    op.create_index("ix_wellbeing_directory_org_active", "wellbeing_directory_entries", ["organisation_id", "is_active"])
    _enable_rls("wellbeing_directory_entries")


def downgrade() -> None:
    for table in (
        "wellbeing_directory_entries",
        "wellbeing_resource_completions",
        "wellbeing_saved_resources",
        "wellbeing_resources",
        "wellbeing_routine_completions",
        "wellbeing_routines",
        "wellbeing_checkins",
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.drop_table(table)
