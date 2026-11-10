"""F4.1 tenant housing assignment and organisation catalogues.

Adds nullable assignment foreign keys on tenants and two RLS-scoped catalogue
tables. No community, job, training, or housing rows are inserted.

Revision ID: 20261110_2900_f41
Revises: 20261107_2800_f315
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261110_2900_f41"
down_revision: Union[str, None] = "20261107_2800_f315"
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
    op.add_column(
        "tenants",
        sa.Column("assigned_property_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("assigned_room_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_tenants_assigned_property_id", "tenants", ["assigned_property_id"])
    op.create_index("ix_tenants_assigned_room_id", "tenants", ["assigned_room_id"])
    op.create_foreign_key(
        "fk_tenants_assigned_property_id_properties",
        "tenants",
        "properties",
        ["assigned_property_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_tenants_assigned_room_id_rooms",
        "tenants",
        "rooms",
        ["assigned_room_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "community_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("address_line", sa.String(255), nullable=True),
        sa.Column("opening_hours", sa.String(255), nullable=True),
        sa.Column("eligibility", sa.Text(), nullable=True),
        sa.Column("contact", sa.String(255), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "category IN ('food_bank', 'kitchen', 'clothing_bank', 'local_service')",
            name="ck_community_services_category",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_community_services_organisation_id", "community_services", ["organisation_id"])
    op.create_index(
        "ix_community_services_org_published",
        "community_services",
        ["organisation_id", "is_published"],
    )
    _enable_rls("community_services")

    op.create_table(
        "opportunity_listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("eligibility", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "kind IN ('job', 'training')",
            name="ck_opportunity_listings_kind",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_opportunity_listings_organisation_id", "opportunity_listings", ["organisation_id"])
    op.create_index(
        "ix_opportunity_listings_org_kind_published",
        "opportunity_listings",
        ["organisation_id", "kind", "is_published"],
    )
    _enable_rls("opportunity_listings")


def downgrade() -> None:
    for table in ("opportunity_listings", "community_services"):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.drop_table(table)
    op.drop_constraint("fk_tenants_assigned_room_id_rooms", "tenants", type_="foreignkey")
    op.drop_constraint("fk_tenants_assigned_property_id_properties", "tenants", type_="foreignkey")
    op.drop_index("ix_tenants_assigned_room_id", table_name="tenants")
    op.drop_index("ix_tenants_assigned_property_id", table_name="tenants")
    op.drop_column("tenants", "assigned_room_id")
    op.drop_column("tenants", "assigned_property_id")
