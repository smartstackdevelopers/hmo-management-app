"""F5.2 Help Near Me: service coordinates and outdated listing reports.

Extends ``community_services`` with geocoded coordinates. Adds report and
short-lived search rate-limit tables. No service rows or fake coordinates
are seeded.

Revision ID: 20261110_3500_f52
Revises: 20261110_3400_f51
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261110_3500_f52"
down_revision: Union[str, None] = "20261110_3400_f51"
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


def upgrade() -> None:
    op.add_column("community_services", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("community_services", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column(
        "community_services",
        sa.Column("geocode_provider", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "community_services",
        sa.Column(
            "geocode_status",
            sa.String(length=32),
            nullable=False,
            server_default="not_geocoded",
        ),
    )
    op.add_column(
        "community_services",
        sa.Column("geocoded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_community_services_geocode_status",
        "community_services",
        "geocode_status IN ('not_geocoded', 'verified', 'failed', 'manual')",
    )
    op.create_index(
        "ix_community_services_org_lat_lon",
        "community_services",
        ["organisation_id", "latitude", "longitude"],
    )

    op.create_table(
        "community_service_outdated_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="submitted",
        ),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_id"], ["community_services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "reason IN ("
            "'service_closed', 'address_incorrect', 'opening_hours_incorrect', "
            "'contact_incorrect', 'eligibility_incorrect', 'information_outdated', "
            "'cannot_locate', 'other'"
            ")",
            name="ck_cs_outdated_reports_reason",
        ),
        sa.CheckConstraint(
            "status IN ("
            "'submitted', 'under_review', 'information_confirmed', "
            "'listing_updated', 'reverified', 'rejected', 'closed'"
            ")",
            name="ck_cs_outdated_reports_status",
        ),
    )
    op.create_index(
        "ix_cs_outdated_reports_org_status",
        "community_service_outdated_reports",
        ["organisation_id", "status"],
    )
    op.create_index(
        "ix_cs_outdated_reports_service_created",
        "community_service_outdated_reports",
        ["service_id", "created_at"],
    )
    op.create_index(
        "ix_cs_outdated_reports_reporter_created",
        "community_service_outdated_reports",
        ["reporter_user_id", "created_at"],
    )
    op.execute(sa.text("ALTER TABLE community_service_outdated_reports ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE community_service_outdated_reports FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_policy("community_service_outdated_reports")))

    # Short-lived search events for rate limiting only (not a tenant location history store).
    op.create_table(
        "help_near_me_search_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("postcode_normalised", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_help_near_me_search_user_created",
        "help_near_me_search_events",
        ["user_id", "created_at"],
    )
    op.execute(sa.text("ALTER TABLE help_near_me_search_events ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE help_near_me_search_events FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_policy("help_near_me_search_events")))


def downgrade() -> None:
    for table in ("help_near_me_search_events", "community_service_outdated_reports"):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.drop_table(table)
    op.drop_index("ix_community_services_org_lat_lon", table_name="community_services")
    op.drop_constraint("ck_community_services_geocode_status", "community_services", type_="check")
    op.drop_column("community_services", "geocoded_at")
    op.drop_column("community_services", "geocode_status")
    op.drop_column("community_services", "geocode_provider")
    op.drop_column("community_services", "longitude")
    op.drop_column("community_services", "latitude")
