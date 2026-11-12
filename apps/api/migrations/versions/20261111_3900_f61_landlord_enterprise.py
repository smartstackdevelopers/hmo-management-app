"""F6.1 landlord enterprise: rent records ledger and property inspections.

Revision ID: 20261111_3900_f61
Revises: 20261110_3800_f55
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261111_3900_f61"
down_revision: Union[str, None] = "20261110_3800_f55"
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
        "rent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="due"),
        sa.Column("tenancy_reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_paid_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recorded_paid_note", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recorded_paid_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('due', 'outstanding', 'recorded_paid', 'waived', 'cancelled')",
            name="ck_rent_records_status",
        ),
        sa.CheckConstraint("period_end >= period_start", name="ck_rent_records_period"),
        sa.CheckConstraint("amount >= 0", name="ck_rent_records_amount"),
        sa.UniqueConstraint(
            "organisation_id",
            "property_id",
            "tenant_id",
            "period_start",
            "period_end",
            name="uq_rent_records_period_scope",
        ),
    )
    op.create_index(
        "ix_rent_records_org_property_period",
        "rent_records",
        ["organisation_id", "property_id", "period_start"],
    )
    op.create_index("ix_rent_records_org_status", "rent_records", ["organisation_id", "status"])
    op.create_index("ix_rent_records_tenant", "rent_records", ["tenant_id", "period_start"])
    _enable_rls("rent_records")

    op.create_table(
        "property_inspections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="scheduled"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("follow_up_actions", sa.Text(), nullable=True),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('scheduled', 'in_progress', 'completed', 'cancelled')",
            name="ck_property_inspections_status",
        ),
    )
    op.create_index(
        "ix_property_inspections_org_property",
        "property_inspections",
        ["organisation_id", "property_id", "scheduled_date"],
    )
    op.create_index(
        "ix_property_inspections_org_status",
        "property_inspections",
        ["organisation_id", "status"],
    )
    _enable_rls("property_inspections")


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON property_inspections"))
    op.drop_table("property_inspections")
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON rent_records"))
    op.drop_table("rent_records")
